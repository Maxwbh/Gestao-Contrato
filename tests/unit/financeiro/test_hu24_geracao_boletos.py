"""
HU-24 — Geração Mensal de Boletos (Fluxo da Contadora)
=======================================================

Cobre:
  - GeracaoBoletosService: elegibilidade, cascata de bloqueio (HU-06), conferência
  - boletos_painel (GET) — KPIs e agrupamento por imobiliária→contrato
  - boletos_painel_gerar (POST) — escopos todos/imobiliaria/contratos/parcela/intermediaria
  - quantidade (próximos N), bloqueio por reajuste, idempotência, falha parcial
  - tipo carnê (carne_url), IDOR, notificação consolidada por canal (RN-14)

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

def _gerar_boleto_fake(enviar_email=True, **kw):
    """Side-effect para Parcela.gerar_boleto: marca GERADO e retorna sucesso."""
    return {'sucesso': True, 'nosso_numero': '000123'}


@pytest.fixture
def base(db):
    """Imobiliária + conta + contrato FIXO (sem bloqueio) com parcelas NAO_GERADO."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import StatusBoleto, TipoParcela

    imob = ImobiliariaFactory(nome='Imob HU24')
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='001', principal=True, ativo=True,
        convenio='1234567', cobranca_registrada=True, layout_cnab='CNAB_240',
    )
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador HU24')

    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-HU24-1', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('120000.00'), valor_entrada=Decimal('20000.00'),
        numero_parcelas=12, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
    )
    # Garante parcelas NAO_GERADO/normais
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
        valor_boleto=Decimal('8333.33'),
    )
    return imob, conta, contrato


@pytest.fixture
def staff_cli(db):
    u = User.objects.create_user('hu24staff', password='x', is_staff=True)
    c = Client()
    c.force_login(u)
    return u, c


# ---------------------------------------------------------------------------
# Service — elegibilidade e conferência
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestElegibilidade:
    def test_proximas_elegiveis_respeita_quantidade(self, base):
        from financeiro.services.geracao_boletos_service import GeracaoBoletosService
        _, _, contrato = base
        elegiveis, bloq = GeracaoBoletosService().proximas_elegiveis(contrato, quantidade=3)
        assert len(elegiveis) == 3
        assert bloq == []

    def test_conferencia_kpis(self, base, staff_cli):
        from financeiro.services.geracao_boletos_service import GeracaoBoletosService
        imob, _, _ = base
        from core.models import Imobiliaria
        conf = GeracaoBoletosService().obter_conferencia(
            Imobiliaria.objects.filter(pk=imob.pk), quantidade=2,
        )
        assert conf['kpis']['a_gerar'] == 2
        assert conf['kpis']['contratos'] == 1
        assert len(conf['grupos']) == 1


@pytest.mark.django_db
class TestPainelView:
    def test_requer_login(self, base):
        resp = Client().get(reverse('financeiro:boletos_painel'))
        assert resp.status_code == 302

    def test_kpis_no_contexto(self, base, staff_cli):
        _, c = staff_cli
        resp = c.get(reverse('financeiro:boletos_painel') + '?quantidade=2')
        assert resp.status_code == 200
        assert resp.context['kpis']['a_gerar'] == 2
        assert resp.context['contas_boleto_api'] == []  # sem contas Boleto-API

    def test_contas_boleto_api_no_contexto(self, base, staff_cli):
        """Contas C6/Sicoob aparecem no aviso de cobrança registrada do painel."""
        _, c = staff_cli
        imob, conta, contrato = base
        conta.provider = 'c6'
        conta.save(update_fields=['provider'])
        resp = c.get(reverse('financeiro:boletos_painel'))
        assert resp.status_code == 200
        contas = resp.context['contas_boleto_api']
        assert len(contas) == 1 and contas[0].pk == conta.pk
        assert 'Cobrança registrada via Boleto-API' in resp.content.decode()


# ---------------------------------------------------------------------------
# Geração por escopo
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGerarPorEscopo:
    def _post(self, c, body):
        return c.post(reverse('financeiro:boletos_painel_gerar'),
                      data=json.dumps(body), content_type='application/json')

    def test_escopo_todos(self, base, staff_cli):
        from financeiro.models import StatusBoleto
        _, c = staff_cli
        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m:
            def _se(self, enviar_email=True, **kw):
                self.status_boleto = StatusBoleto.GERADO
                self.save(update_fields=['status_boleto'])
                return {'sucesso': True, 'nosso_numero': 'X'}
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'todos', 'quantidade': 1, 'incluir_intermediarias': False})
        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert data['total_gerados'] == 1

    def test_escopo_contratos_proximos_3(self, base, staff_cli):
        from financeiro.models import StatusBoleto
        _, _, contrato = base
        _, c = staff_cli
        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m:
            def _se(self, enviar_email=True, **kw):
                self.status_boleto = StatusBoleto.GERADO; self.save(update_fields=['status_boleto'])
                return {'sucesso': True}
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 3, 'incluir_intermediarias': False})
        assert resp.json()['total_gerados'] == 3

    def test_escopo_invalido(self, base, staff_cli):
        _, c = staff_cli
        resp = self._post(c, {'escopo': 'xpto'})
        assert resp.status_code == 400
        assert resp.json()['sucesso'] is False

    def test_tipo_carne_expoe_url(self, base, staff_cli):
        from financeiro.models import StatusBoleto
        _, _, contrato = base
        _, c = staff_cli
        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'):
            def _se(self, enviar_email=True, **kw):
                self.status_boleto = StatusBoleto.GERADO; self.save(update_fields=['status_boleto'])
                return {'sucesso': True}
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 2, 'tipo': 'carne', 'incluir_intermediarias': False})
        data = resp.json()
        assert data['tipo'] == 'carne'
        assert len(data['carnes']) == 1 and 'carne_url' in data['carnes'][0]

    def test_falha_parcial_nao_aborta(self, base, staff_cli):
        _, _, contrato = base
        _, c = staff_cli
        chamadas = {'n': 0}
        from financeiro.models import StatusBoleto

        def _se(self, enviar_email=True, **kw):
            chamadas['n'] += 1
            if chamadas['n'] == 2:
                return {'sucesso': False, 'erro': 'Dados inválidos'}
            self.status_boleto = StatusBoleto.GERADO; self.save(update_fields=['status_boleto'])
            return {'sucesso': True}

        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'):
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 3, 'incluir_intermediarias': False})
        data = resp.json()
        assert data['total_gerados'] == 2
        assert data['total_erros'] == 1


# ---------------------------------------------------------------------------
# Bloqueio por reajuste (HU-06) + idempotência
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBloqueioEIdempotencia:
    def _post(self, c, body):
        return c.post(reverse('financeiro:boletos_painel_gerar'),
                      data=json.dumps(body), content_type='application/json')

    def test_bloqueio_reajuste_nao_gera(self, base, staff_cli):
        _, _, contrato = base
        _, c = staff_cli
        with patch('contratos.models.Contrato.pode_gerar_boleto', return_value=(False, 'Reajuste do ciclo 2 pendente')):
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 3, 'incluir_intermediarias': False})
        data = resp.json()
        assert data['total_gerados'] == 0
        assert data['total_bloqueados'] >= 1
        assert 'Reajuste' in data['bloqueados'][0]['motivo']

    def test_idempotencia_ja_gerado(self, base, staff_cli):
        from financeiro.models import StatusBoleto
        _, _, contrato = base
        _, c = staff_cli
        # marca todas como GERADO → nada elegível
        contrato.parcelas.update(status_boleto=StatusBoleto.GERADO)
        resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                              'quantidade': 3, 'incluir_intermediarias': False})
        assert resp.json()['total_gerados'] == 0


# ---------------------------------------------------------------------------
# Acesso / IDOR
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAcesso:
    def test_usuario_sem_acesso_nao_gera(self, base):
        _, _, contrato = base
        u = User.objects.create_user('hu24semacesso', password='x')
        c = Client(); c.force_login(u)
        resp = c.post(reverse('financeiro:boletos_painel_gerar'),
                      data=json.dumps({'escopo': 'contratos', 'contrato_ids': [contrato.pk]}),
                      content_type='application/json')
        data = resp.json()
        # sem acesso → contrato não resolve → nada gerado
        assert data['total_gerados'] == 0


# ---------------------------------------------------------------------------
# RN-14 — Notificação consolidada por canal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotificacaoConsolidada:
    def test_um_boleto_usa_individual(self, base):
        from financeiro.services.geracao_boletos_service import GeracaoBoletosService
        _, _, contrato = base
        p = contrato.parcelas.first()
        svc = GeracaoBoletosService()
        with patch('notificacoes.boleto_notificacao.BoletoNotificacaoService') as Mock:
            inst = Mock.return_value
            resumo = svc.notificar_lote(contrato, [p])
            assert inst.agendar_notificacao_boleto_criado.called
            assert resumo['individual'] is True

    def test_varios_boletos_sms_um_a_um_email_consolidado(self, base):
        from financeiro.services.geracao_boletos_service import GeracaoBoletosService
        _, _, contrato = base
        parcelas = list(contrato.parcelas.all()[:3])
        svc = GeracaoBoletosService()
        with patch('notificacoes.boleto_notificacao.BoletoNotificacaoService') as Mock, \
             patch.object(GeracaoBoletosService, '_pdf_consolidado', return_value=b'%PDF'), \
             patch.object(GeracaoBoletosService, '_enviar_consolidado', return_value=True) as menv:
            inst = Mock.return_value
            resumo = svc.notificar_lote(contrato, parcelas)
            # SMS um a um: 1 chamada por parcela
            assert inst.enviar_sms_boleto.call_count == 3
            assert resumo['sms'] == 3
            # e-mail e whatsapp consolidados: 2 chamadas a _enviar_consolidado
            assert menv.call_count == 2
            assert resumo['email_consolidado'] is True
            assert resumo['whatsapp_consolidado'] is True


# ---------------------------------------------------------------------------
# Pacing + abort em rate limit (HU-24 / BRCobrança Render free tier)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPacingAbort:
    def _post(self, c, body):
        return c.post(reverse('financeiro:boletos_painel_gerar'),
                      data=json.dumps(body), content_type='application/json')

    def test_abort_em_rate_limit(self, base, staff_cli):
        """Quando gerar_boleto sinaliza rate_limited, a geração para imediatamente."""
        from financeiro.models import StatusBoleto
        _, _, contrato = base
        _, c = staff_cli
        chamadas = {'n': 0}

        def _se(self, enviar_email=True, **kw):
            chamadas['n'] += 1
            if chamadas['n'] >= 3:
                return {
                    'sucesso': False,
                    'rate_limited': True,
                    'erro': 'Serviço de boletos temporariamente sobrecarregado. Tente novamente em instantes.',
                }
            self.status_boleto = StatusBoleto.GERADO
            self.save(update_fields=['status_boleto'])
            return {'sucesso': True}

        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'), \
             patch('financeiro.views.time'):
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 5, 'incluir_intermediarias': False})

        data = resp.json()
        assert data['sucesso'] is True
        assert data['total_gerados'] == 2
        assert data['rate_limit_abort'] is True
        assert chamadas['n'] == 3  # parou na 3ª chamada (rate_limited)

    def test_falha_comum_nao_aborta(self, base, staff_cli):
        """Erros normais (não rate_limited) não ativam o abort — comportamento tolerante a falhas."""
        from financeiro.models import StatusBoleto
        _, _, contrato = base
        _, c = staff_cli
        chamadas = {'n': 0}

        def _se(self, enviar_email=True, **kw):
            chamadas['n'] += 1
            if chamadas['n'] == 2:
                return {'sucesso': False, 'erro': 'Dados inválidos'}
            self.status_boleto = StatusBoleto.GERADO
            self.save(update_fields=['status_boleto'])
            return {'sucesso': True}

        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'), \
             patch('financeiro.views.time'):
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 3, 'incluir_intermediarias': False})

        data = resp.json()
        assert data['total_gerados'] == 2
        assert data['total_erros'] == 1
        assert data['rate_limit_abort'] is False

    def test_pacing_delay_entre_chamadas(self, base, staff_cli, settings):
        """Verifica que time.sleep é chamado N-1 vezes com o delay configurado."""
        from financeiro.models import StatusBoleto
        _, _, contrato = base
        _, c = staff_cli
        settings.BRCOBRANCA_INTER_BOLETO_DELAY_MS = 200

        def _se(self, enviar_email=True, **kw):
            self.status_boleto = StatusBoleto.GERADO
            self.save(update_fields=['status_boleto'])
            return {'sucesso': True}

        with patch('financeiro.models.Parcela.gerar_boleto', autospec=True) as m, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'), \
             patch('financeiro.views.time') as mock_time:
            m.side_effect = _se
            resp = self._post(c, {'escopo': 'contratos', 'contrato_ids': [contrato.pk],
                                  'quantidade': 3, 'incluir_intermediarias': False})

        data = resp.json()
        assert data['total_gerados'] == 3
        # delay antes da 2ª e 3ª chamada (não antes da 1ª)
        assert mock_time.sleep.call_count == 2
        mock_time.sleep.assert_called_with(0.2)  # 200 ms → 0.2 s


# ---------------------------------------------------------------------------
# Performance — conferência não escala consultas por contrato
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConferenciaPerformance:
    """Trava de regressão: obter_conferencia usa um nº de consultas LIMITADO,
    independente da quantidade de contratos (prefetch/annotate/batch).

    Antes da otimização eram ~3 consultas por contrato (parcelas + intermediárias
    + contagem) mais N+1 — o que tornava o hub/painel de cobrança lento.
    """

    def _criar_contratos(self, n):
        from decimal import Decimal
        from datetime import date
        from tests.fixtures.factories import (
            ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
        )
        from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
        from financeiro.models import StatusBoleto, TipoParcela

        imob = ImobiliariaFactory(nome='Imob Perf')
        conta = ContaBancariaFactory(
            imobiliaria=imob, banco='001', principal=True, ativo=True,
            convenio='1234567', cobranca_registrada=True, layout_cnab='CNAB_240',
        )
        for i in range(n):
            contrato = Contrato.objects.create(
                imobiliaria=imob, imovel=ImovelFactory(imobiliaria=imob, disponivel=False),
                comprador=CompradorFactory(nome=f'Comprador Perf {i}'),
                numero_contrato=f'CTR-PERF-{i}', data_contrato=date(2025, 1, 1),
                data_primeiro_vencimento=date(2025, 2, 1),
                valor_total=Decimal('120000.00'), valor_entrada=Decimal('20000.00'),
                numero_parcelas=12, dia_vencimento=1,
                tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
                status=StatusContrato.ATIVO,
            )
            contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
                status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
            )
        return imob

    def test_conferencia_consultas_limitadas(self, django_assert_max_num_queries):
        from financeiro.services.geracao_boletos_service import GeracaoBoletosService
        from core.models import Imobiliaria

        imob = self._criar_contratos(6)
        qs = Imobiliaria.objects.filter(pk=imob.pk)

        # 6 contratos: com a otimização o nº de consultas é ~constante (prefetch +
        # annotate + batch). O ceiling separa com folga do comportamento antigo
        # (~3 consultas/contrato → 18+).
        with django_assert_max_num_queries(12):
            conf = GeracaoBoletosService().obter_conferencia(qs, quantidade=2)

        assert conf['kpis']['contratos'] == 6
        assert conf['kpis']['a_gerar'] == 12  # 2 por contrato × 6
