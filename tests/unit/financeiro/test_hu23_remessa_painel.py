"""
HU-23 — Envio Mensal de Remessa CNAB (Fluxo da Contadora)
=========================================================

Cobre:
  - obter_boletos_elegiveis_painel() — vencimento>=hoje, cobranca_registrada, escopo
  - resolver_parcela_ids_por_escopo() — todos/imobiliaria/conta/boleto + acesso
  - remessa_painel (GET) — KPIs e agrupamento por conta
  - remessa_painel_gerar (POST) — geração por escopo, REGISTRADO, 1 arquivo/conta
  - download grava data_download → estado BAIXADO
  - cancelar_envio (RN-07) e marcar_enviada (auditoria)
  - retorno_painel (GET) + upload de retorno (RN-22 / CT-28)
  - rejeição CNAB devolve boleto a GERADO (RN-18 / CT-29)
  - IDOR: usuário sem acesso não gera (RN-11)

Desenvolvedor: Maxwell da Silva Oliveira
"""
import json
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_brcobranca_ok():
    m = MagicMock()
    m.status_code = 200
    m.content = b'0' * 240 + b'\n'
    return m


@pytest.fixture
def base(db):
    """Imobiliária + conta BB (com registro) + contrato com parcelas elegíveis futuras."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import (
        Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
    )
    from financeiro.models import StatusBoleto

    imob = ImobiliariaFactory(nome='Imob HU23')
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='001', principal=True, ativo=True,
        convenio='1234567', cobranca_registrada=True, layout_cnab='CNAB_240',
    )
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador HU23')

    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-HU23-1', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('120000.00'), valor_entrada=Decimal('20000.00'),
        numero_parcelas=12, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
        percentual_juros_mora=Decimal('1.00'), percentual_multa=Decimal('2.00'),
    )

    hoje = date.today()
    # 3 boletos elegíveis: um vence HOJE, dois no futuro
    vencs = {4: hoje, 5: hoje + timedelta(days=15), 6: hoje + timedelta(days=45)}
    for num, venc in vencs.items():
        contrato.parcelas.filter(numero_parcela=num).update(
            status_boleto=StatusBoleto.GERADO,
            nosso_numero=f'0000{num:02d}',
            valor_boleto=Decimal('8333.33'),
            conta_bancaria=conta,
            data_vencimento=venc,
        )
    # 1 boleto GERADO mas VENCIDO (não elegível — RN-01)
    contrato.parcelas.filter(numero_parcela=7).update(
        status_boleto=StatusBoleto.GERADO,
        nosso_numero='000007',
        valor_boleto=Decimal('8333.33'),
        conta_bancaria=conta,
        data_vencimento=hoje - timedelta(days=5),
    )
    return imob, conta, contrato


@pytest.fixture
def staff_cli(db):
    u = User.objects.create_user('hu23staff', password='x', is_staff=True)
    c = Client()
    c.force_login(u)
    return u, c


# ---------------------------------------------------------------------------
# Service: elegibilidade
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestElegibilidade:
    def test_exclui_vencidos_e_inclui_futuros(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        elegiveis = CNABService().obter_boletos_elegiveis_painel()
        nums = {p.numero_parcela for p in elegiveis}
        assert nums == {4, 5, 6}  # 7 (vencido) excluído

    def test_exclui_conta_sem_registro(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        conta.cobranca_registrada = False
        conta.save(update_fields=['cobranca_registrada'])
        elegiveis = CNABService().obter_boletos_elegiveis_painel()
        assert elegiveis == []

    def test_escopo_imobiliaria_restringe(self, base):
        from financeiro.services.cnab_service import CNABService
        from core.models import Imobiliaria
        imob, conta, contrato = base
        elegiveis = CNABService().obter_boletos_elegiveis_painel(
            imobiliarias=Imobiliaria.objects.filter(pk=imob.pk)
        )
        assert len(elegiveis) == 3


# ---------------------------------------------------------------------------
# Service: resolução de escopo
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestResolverEscopo:
    def test_escopo_todos(self, base):
        from financeiro.services.cnab_service import CNABService
        r = CNABService().resolver_parcela_ids_por_escopo('todos')
        assert r['erro'] is None
        assert len(r['parcela_ids']) == 3

    def test_escopo_conta(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        r = CNABService().resolver_parcela_ids_por_escopo('conta', conta_bancaria_id=conta.pk)
        assert len(r['parcela_ids']) == 3

    def test_escopo_boleto_ok(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        p5 = contrato.parcelas.get(numero_parcela=5)
        r = CNABService().resolver_parcela_ids_por_escopo('boleto', parcela_id=p5.pk)
        assert r['erro'] is None
        assert r['parcela_ids'] == [p5.pk]

    def test_escopo_boleto_vencido_erro(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        p7 = contrato.parcelas.get(numero_parcela=7)
        r = CNABService().resolver_parcela_ids_por_escopo('boleto', parcela_id=p7.pk)
        assert r['parcela_ids'] == []
        assert 'passado' in r['erro'].lower()

    def test_escopo_invalido(self, base):
        from financeiro.services.cnab_service import CNABService
        r = CNABService().resolver_parcela_ids_por_escopo('xpto')
        assert 'inválido' in r['erro'].lower()


# ---------------------------------------------------------------------------
# View: painel (GET)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPainelView:
    def test_requer_login(self, base):
        c = Client()
        resp = c.get(reverse('financeiro:remessa_painel'))
        assert resp.status_code == 302

    def test_kpis_e_grupos(self, base, staff_cli):
        _, c = staff_cli
        resp = c.get(reverse('financeiro:remessa_painel'))
        assert resp.status_code == 200
        assert resp.context['kpi_total_pendente'] == 3
        assert resp.context['kpi_bancos_ativos'] == 1   # 1 conta
        assert resp.context['kpi_vencendo_hoje'] == 1    # parcela 4 vence hoje
        assert len(resp.context['grupos']) == 1


# ---------------------------------------------------------------------------
# View: geração por escopo (POST)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGerarPorEscopo:
    def _post(self, c, body):
        return c.post(
            reverse('financeiro:remessa_painel_gerar'),
            data=json.dumps(body), content_type='application/json',
        )

    def test_gera_escopo_todos_e_transiciona_registrado(self, base, staff_cli):
        from financeiro.models import StatusBoleto, ArquivoRemessa
        _, c = staff_cli
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            resp = self._post(c, {'escopo': 'todos'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert data['total_gerados'] == 1  # 1 conta = 1 arquivo
        assert data['arquivos'][0]['total_boletos'] == 3
        # RN-14: boletos passaram a REGISTRADO
        imob, conta, contrato = base
        regs = contrato.parcelas.filter(
            numero_parcela__in=[4, 5, 6], status_boleto=StatusBoleto.REGISTRADO
        ).count()
        assert regs == 3
        # gerado_por gravado (RN-17)
        arq = ArquivoRemessa.objects.latest('data_geracao')
        assert arq.gerado_por is not None

    def test_gera_escopo_boleto_avulso(self, base, staff_cli):
        from financeiro.models import ArquivoRemessa
        imob, conta, contrato = base
        _, c = staff_cli
        p6 = contrato.parcelas.get(numero_parcela=6)
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            resp = self._post(c, {'escopo': 'boleto', 'parcela_id': p6.pk})
        data = resp.json()
        assert data['sucesso'] is True
        arq = ArquivoRemessa.objects.latest('data_geracao')
        assert arq.itens.count() == 1  # remessa avulsa de 1 título

    def test_escopo_sem_elegiveis_retorna_400(self, base, staff_cli):
        _, c = staff_cli
        # gera tudo primeiro
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            self._post(c, {'escopo': 'todos'})
            resp = self._post(c, {'escopo': 'todos'})  # nada mais elegível
        assert resp.status_code == 400
        assert resp.json()['sucesso'] is False


# ---------------------------------------------------------------------------
# Download → BAIXADO, marcar enviada, cancelar envio
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEstadosArquivo:
    def _gerar_um(self, c):
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            c.post(reverse('financeiro:remessa_painel_gerar'),
                   data=json.dumps({'escopo': 'todos'}), content_type='application/json')
        from financeiro.models import ArquivoRemessa
        return ArquivoRemessa.objects.latest('data_geracao')

    def test_download_marca_data_download(self, base, staff_cli):
        from core.hashids_utils import encode_id
        _, c = staff_cli
        arq = self._gerar_um(c)
        assert arq.data_download is None
        resp = c.get(reverse('financeiro:download_remessa', kwargs={'hid': encode_id(arq.pk)}))
        assert resp.status_code == 200
        arq.refresh_from_db()
        assert arq.data_download is not None
        assert arq.estado_ui == 'BAIXADO'

    def test_marcar_enviada_registra_usuario(self, base, staff_cli):
        from core.hashids_utils import encode_id
        from financeiro.models import StatusArquivoRemessa
        u, c = staff_cli
        arq = self._gerar_um(c)
        resp = c.post(reverse('financeiro:marcar_remessa_enviada', kwargs={'hid': encode_id(arq.pk)}))
        assert resp.status_code == 200
        arq.refresh_from_db()
        assert arq.status == StatusArquivoRemessa.ENVIADO
        assert arq.enviado_por_id == u.pk

    def test_cancelar_envio_reverte(self, base, staff_cli):
        from core.hashids_utils import encode_id
        from financeiro.models import StatusArquivoRemessa
        u, c = staff_cli
        arq = self._gerar_um(c)
        arq.marcar_enviado(usuario=u)
        resp = c.post(reverse('financeiro:remessa_cancelar_envio', kwargs={'hid': encode_id(arq.pk)}))
        assert resp.status_code == 200
        arq.refresh_from_db()
        assert arq.status == StatusArquivoRemessa.GERADO
        assert arq.data_envio is None


# ---------------------------------------------------------------------------
# IDOR / acesso
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestValidacaoPreGeracao:
    def test_detecta_vencimento_proximo(self, base):
        from financeiro.services.cnab_service import CNABService
        # parcela 4 vence hoje → 0 dias úteis < 1 → vencimento_proximo
        elegiveis = CNABService().obter_boletos_elegiveis_painel()
        res = CNABService().validar_boletos_para_remessa(elegiveis)
        assert 'vencimento_proximo' in res['por_tipo']

    def test_detecta_endereco_incompleto(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        contrato.comprador.cep = ''
        contrato.comprador.logradouro = ''
        contrato.comprador.endereco = ''
        contrato.comprador.save()
        elegiveis = CNABService().obter_boletos_elegiveis_painel()
        res = CNABService().validar_boletos_para_remessa(elegiveis)
        assert res['por_tipo'].get('endereco_incompleto', 0) >= 1

    def test_detecta_sem_nosso_numero(self, base):
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        elegiveis = CNABService().obter_boletos_elegiveis_painel()
        # força um boleto sem nosso_numero na lista validada
        elegiveis[0].nosso_numero = ''
        res = CNABService().validar_boletos_para_remessa(elegiveis)
        assert res['por_tipo'].get('sem_nosso_numero', 0) >= 1

    def test_dias_uteis_helper(self):
        from financeiro.services.cnab_service import CNABService
        from datetime import date
        # sexta (2026-06-12) → segunda (2026-06-15) = 1 dia útil (seg)
        assert CNABService._dias_uteis_ate(date(2026, 6, 12), date(2026, 6, 15)) == 1
        assert CNABService._dias_uteis_ate(date(2026, 6, 12), date(2026, 6, 12)) == 0


@pytest.mark.django_db
class TestApiValidar:
    def test_endpoint_retorna_alertas(self, base, staff_cli):
        _, c = staff_cli
        resp = c.get(reverse('financeiro:api_remessa_validar'))
        assert resp.status_code == 200
        data = resp.json()
        assert data['total_elegiveis'] == 3
        assert 'por_tipo' in data and 'alertas' in data

    def test_requer_login(self, base):
        resp = Client().get(reverse('financeiro:api_remessa_validar'))
        assert resp.status_code == 302


@pytest.mark.django_db
class TestBannerConclusao:
    def test_mes_concluido_quando_sem_pendentes_e_com_envio(self, base, staff_cli):
        import json as _json
        from core.hashids_utils import encode_id
        from financeiro.models import ArquivoRemessa
        u, c = staff_cli
        # gera todos e marca todos como enviados
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            c.post(reverse('financeiro:remessa_painel_gerar'),
                   data=_json.dumps({'escopo': 'todos'}), content_type='application/json')
        for arq in ArquivoRemessa.objects.all():
            c.post(reverse('financeiro:marcar_remessa_enviada', kwargs={'hid': encode_id(arq.pk)}))
        resp = c.get(reverse('financeiro:remessa_painel'))
        assert resp.context['kpi_total_pendente'] == 0
        assert resp.context['mes_concluido'] is True
        assert resp.context['bancos_enviados'] >= 1


@pytest.mark.django_db
class TestRejeicaoCNAB:
    """RN-18: rejeição do banco devolve o boleto a GERADO e marca o item REJEITADO."""

    def _gerar(self, c):
        import json as _json
        from financeiro.models import ArquivoRemessa
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            c.post(reverse('financeiro:remessa_painel_gerar'),
                   data=_json.dumps({'escopo': 'todos'}), content_type='application/json')
        return ArquivoRemessa.objects.latest('data_geracao')

    def test_rejeicao_devolve_boleto_para_gerado_e_reinclui(self, base, staff_cli):
        from financeiro.models import (
            StatusBoleto, ItemRemessa, ItemRetorno, ArquivoRetorno,
            StatusArquivoRetorno,
        )
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = base
        u, c = staff_cli
        self._gerar(c)  # gera remessa → boletos REGISTRADO
        p = contrato.parcelas.filter(status_boleto=StatusBoleto.REGISTRADO).first()
        assert p is not None
        item = p.itens_remessa.first()

        # Simula retorno de REJEIÇÃO (código 03)
        arq_ret = ArquivoRetorno.objects.create(
            conta_bancaria=conta, nome_arquivo='RET.RET', status=StatusArquivoRetorno.PENDENTE,
        )
        ir = ItemRetorno.objects.create(
            arquivo_retorno=arq_ret, parcela=p, nosso_numero=p.nosso_numero,
            codigo_ocorrencia='03', descricao_ocorrencia='Entrada Rejeitada',
            tipo_ocorrencia='REJEICAO',
        )
        assert ir.processar_baixa() is True

        # Boleto volta a GERADO; item marcado REJEITADO
        p.refresh_from_db(); item.refresh_from_db()
        assert p.status_boleto == StatusBoleto.GERADO
        assert item.status == ItemRemessa.Status.REJEITADO
        assert 'Rejeitada' in item.motivo_rejeicao

        # E volta a ser elegível para nova remessa (RN-18)
        elegiveis = CNABService().obter_boletos_elegiveis_painel()
        assert p.pk in {x.pk for x in elegiveis}


@pytest.mark.django_db
class TestAcoesHistorico:
    """Item A: regenerar/excluir expostos no painel (endpoints da HU-16)."""

    def _gerar(self, c):
        import json as _json
        from financeiro.models import ArquivoRemessa
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            c.post(reverse('financeiro:remessa_painel_gerar'),
                   data=_json.dumps({'escopo': 'todos'}), content_type='application/json')
        return ArquivoRemessa.objects.latest('data_geracao')

    def test_excluir_remessa_gerada_devolve_boletos(self, base, staff_cli):
        from core.hashids_utils import encode_id
        from financeiro.models import ArquivoRemessa, StatusBoleto
        imob, conta, contrato = base
        u, c = staff_cli
        arq = self._gerar(c)
        resp = c.post(reverse('financeiro:excluir_remessa', kwargs={'hid': encode_id(arq.pk)}))
        assert resp.status_code == 200 and resp.json()['sucesso'] is True
        assert not ArquivoRemessa.objects.filter(pk=arq.pk).exists()

    def test_excluir_remessa_enviada_bloqueado(self, base, staff_cli):
        from core.hashids_utils import encode_id
        u, c = staff_cli
        arq = self._gerar(c)
        arq.marcar_enviado(usuario=u)
        resp = c.post(reverse('financeiro:excluir_remessa', kwargs={'hid': encode_id(arq.pk)}))
        assert resp.status_code == 400


@pytest.mark.django_db
class TestRetornoPainel:
    """Passo 5 — tela dedicada de retorno (RN-22 / CT-28)."""

    def _gerar_e_enviar(self, c, u):
        import json as _json
        from financeiro.models import ArquivoRemessa
        with patch('financeiro.services.cnab_service.requests.post', return_value=_mock_brcobranca_ok()):
            c.post(reverse('financeiro:remessa_painel_gerar'),
                   data=_json.dumps({'escopo': 'todos'}), content_type='application/json')
        for arq in ArquivoRemessa.objects.all():
            arq.marcar_enviado(usuario=u)

    def test_requer_login(self, base):
        resp = Client().get(reverse('financeiro:retorno_painel'))
        assert resp.status_code == 302

    def test_card_upload_aparece_para_conta_enviada(self, base, staff_cli):
        """RN-22: conta com remessa ENVIADO vira card de upload de retorno."""
        u, c = staff_cli
        imob, conta, contrato = base
        self._gerar_e_enviar(c, u)
        resp = c.get(reverse('financeiro:retorno_painel'))
        assert resp.status_code == 200
        assert conta.pk in {x.pk for x in resp.context['contas_com_enviado']}

    def test_sem_envio_nao_mostra_card(self, base, staff_cli):
        u, c = staff_cli
        resp = c.get(reverse('financeiro:retorno_painel'))
        assert resp.status_code == 200
        assert list(resp.context['contas_com_enviado']) == []

    def test_upload_processa_e_retorna_resumo(self, base, staff_cli):
        """CT-28: upload + auto-processo retorna o resumo JSON documentado."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        u, c = staff_cli
        imob, conta, contrato = base
        fake = {
            'sucesso': True, 'total_registros': 3, 'registros_processados': 3,
            'registros_erro': 0, 'valor_total_pago': Decimal('100.00'),
        }
        ret_file = SimpleUploadedFile('RET.RET', b'0' * 240, content_type='application/octet-stream')
        with patch('financeiro.services.cnab_service.CNABService.processar_retorno', return_value=fake):
            resp = c.post(reverse('financeiro:remessa_retorno_upload'),
                          data={'conta_bancaria_id': conta.pk, 'arquivo': ret_file})
        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        for k in ('total_registros', 'registros_processados', 'registros_erro',
                  'rejeicoes', 'valor_total_pago', 'detalhe_url'):
            assert k in data
        assert data['total_registros'] == 3

    def test_upload_sem_arquivo_retorna_400(self, base, staff_cli):
        u, c = staff_cli
        imob, conta, contrato = base
        resp = c.post(reverse('financeiro:remessa_retorno_upload'),
                      data={'conta_bancaria_id': conta.pk})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAcesso:
    def test_usuario_sem_acesso_nao_gera(self, base):
        """Usuário comum sem AcessoUsuario não enxerga nenhuma imobiliária."""
        u = User.objects.create_user('semacesso', password='x')
        c = Client()
        c.force_login(u)
        imob, conta, contrato = base
        resp = c.post(
            reverse('financeiro:remessa_painel_gerar'),
            data=json.dumps({'escopo': 'conta', 'conta_bancaria_id': conta.pk}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert resp.json()['sucesso'] is False
