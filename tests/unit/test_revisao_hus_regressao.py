"""
Regressões da revisão das HUs (teste ponta a ponta):

- HU-08/HU-16: 2ª via e remessa usam o sequencial do nosso número (não o
  valor formatado) e a 2ª via não consome sequencial da conta.
- HU-21/HU-28: comprador do portal não alcança a operação; usuário interno
  não alcança objetos de outra imobiliária.
- HU-04: sem pagamento em dobro, sem data futura, quitação automática.
- HU-05: desconto do reajuste aplicado uma única vez; API respeita a ordem
  dos ciclos.
- HU-11/HU-12: percentual 0% é respeitado (não cai no padrão).
- HU-19: webhook Evolution (formato Meta) exige apikey.
- HU-23: excluir remessa devolve os boletos ao pool.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from core.hashids_utils import encode_id
from financeiro.models import HistoricoPagamento, Parcela, Reajuste, StatusBoleto
from tests.fixtures.factories import (
    AcessoCompradorFactory, AcessoUsuarioFactory, ArquivoRemessaFactory,
    ContaBancariaFactory, ContratoFactory, ImobiliariaFactory, ImovelFactory,
    ItemRemessaFactory, ParcelaFactory, UserFactory,
)

pytestmark = pytest.mark.django_db


def _contrato(imobiliaria=None, **kw):
    imobiliaria = imobiliaria or ImobiliariaFactory()
    return ContratoFactory(imovel=ImovelFactory(imobiliaria=imobiliaria), **kw)


def _usuario_da(imobiliaria):
    user = UserFactory()
    AcessoUsuarioFactory(usuario=user, contabilidade=imobiliaria.contabilidade,
                         imobiliaria=imobiliaria)
    c = Client()
    c.force_login(user)
    return c


# ─── HU-08 / HU-16: sequencial do nosso número ───────────────────────────────

class TestNossoNumeroSequencial:

    @pytest.mark.parametrize('banco,convenio,formatado,dv,esperado', [
        ('001', '12345678', '12345678000000014', '3', '14'),   # BB: convênio + seq
        ('237', '', '06/00000000025-8', '8', '25'),            # Bradesco: cart/seq-dv
        ('336', '123456789012', '0000000026-4', '4', '26'),    # C6: seq-dv
        ('756', '123456789', '00000161', '1', '16'),           # Sicoob: seq + dv
        ('756', '123456789', '0000000015', '', '15'),          # sequencial simples
        ('341', '', '109/00000007-2', '2', '7'),               # Itaú
    ])
    def test_extrai_sequencial_por_banco(self, banco, convenio, formatado, dv, esperado):
        conta = ContaBancariaFactory(banco=banco, convenio=convenio)
        parcela = ParcelaFactory(conta_bancaria=conta, nosso_numero=formatado,
                                 nosso_numero_formatado=formatado, nosso_numero_dv=dv)
        assert parcela.get_nosso_numero_sequencial() == esperado

    def test_sem_boleto_retorna_vazio(self):
        assert ParcelaFactory().get_nosso_numero_sequencial() == ''

    def test_segunda_via_reusa_sequencial_e_nao_consome_contador(self):
        from financeiro.services.boleto_service import BoletoService
        conta = ContaBancariaFactory(banco='001', convenio='12345678', nosso_numero_atual=40)
        contrato = _contrato(conta.imobiliaria)
        parcela = ParcelaFactory(
            contrato=contrato, conta_bancaria=conta, status_boleto=StatusBoleto.GERADO,
            nosso_numero='12345678000000014', nosso_numero_formatado='12345678000000014',
        )
        with patch.object(BoletoService, '_chamar_api_boleto',
                          return_value={'sucesso': True, 'pdf_content': b'%PDF'}) as chamada:
            r = BoletoService().gerar_segunda_via(parcela, conta)
        assert r['sucesso'] is True
        enviado = chamada.call_args[0][1]['nosso_numero']
        assert int(str(enviado)) == 14            # sequencial, não os 17 dígitos
        conta.refresh_from_db()
        assert conta.nosso_numero_atual == 40     # contador intacto

    def test_segunda_via_sem_boleto_emitido_e_recusada(self):
        from financeiro.services.boleto_service import BoletoService
        conta = ContaBancariaFactory(nosso_numero_atual=7)
        parcela = ParcelaFactory(contrato=_contrato(conta.imobiliaria))
        with patch.object(BoletoService, '_chamar_api_boleto') as chamada:
            r = BoletoService().gerar_segunda_via(parcela, conta)
        assert r['sucesso'] is False
        chamada.assert_not_called()
        conta.refresh_from_db()
        assert conta.nosso_numero_atual == 7

    def test_remessa_envia_sequencial(self):
        from financeiro.services.cnab_service import CNABService
        conta = ContaBancariaFactory(banco='237', convenio='')
        parcela = ParcelaFactory(
            contrato=_contrato(conta.imobiliaria), conta_bancaria=conta,
            nosso_numero='06/00000000025-8', nosso_numero_formatado='06/00000000025-8',
            nosso_numero_dv='8', status_boleto=StatusBoleto.GERADO,
        )
        dados = CNABService()._montar_dados_boleto(parcela, conta)
        assert dados['nosso_numero'] == '25'


# ─── HU-21 / HU-28: isolamento de acesso ─────────────────────────────────────

class TestIsolamentoAcesso:

    def test_usuario_de_outra_imobiliaria_nao_paga_parcela(self):
        parcela = ParcelaFactory(contrato=_contrato())
        intruso = _usuario_da(ImobiliariaFactory())
        hoje = date.today().isoformat()

        r1 = intruso.post(
            reverse('financeiro:pagar_parcela_ajax', args=[encode_id(parcela.pk)]),
            {'valor_pago': '0.01', 'data_pagamento': hoje})
        r2 = intruso.post(
            f'/financeiro/api/parcelas/{parcela.pk}/pagamento/',
            json.dumps({'valor_pago': 0.01, 'data_pagamento': hoje}),
            content_type='application/json')

        assert r1.status_code == 403 and r2.status_code == 403
        parcela.refresh_from_db()
        assert parcela.pago is False

    def test_usuario_de_outra_imobiliaria_nao_ve_contrato(self):
        contrato = _contrato()
        intruso = _usuario_da(ImobiliariaFactory())
        for url in (
            f'/financeiro/contrato/{contrato.pk}/simulador/',
            f'/financeiro/contrato/{contrato.pk}/renegociar/',
            f'/contratos/{encode_id(contrato.pk)}/rescisao/',
            f'/financeiro/api/contratos/{contrato.pk}/parcelas/',
        ):
            assert intruso.get(url).status_code == 403, url

    def test_usuario_da_propria_imobiliaria_continua_acessando(self):
        contrato = _contrato()
        dono = _usuario_da(contrato.imobiliaria)
        assert dono.get(f'/financeiro/contrato/{contrato.pk}/simulador/').status_code == 200

    def test_comprador_do_portal_nao_entra_na_operacao(self):
        acesso = AcessoCompradorFactory()
        parcela = ParcelaFactory(contrato=_contrato())
        c = Client()
        c.force_login(acesso.usuario)

        for url in ('/contratos/', '/compradores/', '/financeiro/dashboard/'):
            resp = c.get(url)
            assert resp.status_code == 302 and resp['Location'].startswith('/portal/'), url

        resp = c.post(
            f'/financeiro/api/parcelas/{parcela.pk}/pagamento/',
            json.dumps({'valor_pago': 1, 'data_pagamento': date.today().isoformat()}),
            content_type='application/json')
        assert resp.status_code == 403
        parcela.refresh_from_db()
        assert parcela.pago is False

    def test_comprador_continua_usando_o_portal(self):
        acesso = AcessoCompradorFactory()
        c = Client()
        c.force_login(acesso.usuario)
        assert c.get('/portal/').status_code == 200


# ─── HU-04: pagamento ────────────────────────────────────────────────────────

class TestPagamento:

    def test_formulario_nao_registra_pagamento_em_dobro(self, client_admin):
        parcela = ParcelaFactory(contrato=_contrato(), valor_atual=Decimal('100.00'))
        url = reverse('financeiro:registrar_pagamento', args=[encode_id(parcela.pk)])
        dados = {'valor_pago': '100,00', 'data_pagamento': date.today().isoformat(),
                 'forma_pagamento': 'PIX'}
        client_admin.post(url, dados)
        client_admin.post(url, dados)
        assert HistoricoPagamento.objects.filter(parcela=parcela).count() == 1

    def test_data_futura_e_recusada(self, client_admin):
        parcela = ParcelaFactory(contrato=_contrato())
        futuro = (date.today() + timedelta(days=10)).isoformat()

        client_admin.post(
            reverse('financeiro:registrar_pagamento', args=[encode_id(parcela.pk)]),
            {'valor_pago': '100,00', 'data_pagamento': futuro, 'forma_pagamento': 'PIX'})
        r_ajax = client_admin.post(
            reverse('financeiro:pagar_parcela_ajax', args=[encode_id(parcela.pk)]),
            {'valor_pago': '100.00', 'data_pagamento': futuro})
        r_api = client_admin.post(
            f'/financeiro/api/parcelas/{parcela.pk}/pagamento/',
            json.dumps({'valor_pago': 100, 'data_pagamento': futuro}),
            content_type='application/json')

        assert r_ajax.status_code == 400 and r_api.status_code == 400
        parcela.refresh_from_db()
        assert parcela.pago is False

    def test_pagar_ultima_parcela_via_ajax_quita_o_contrato(self, client_admin):
        contrato = _contrato()
        Parcela.objects.filter(contrato=contrato).update(
            pago=True, data_pagamento=date.today(), valor_pago=Decimal('1.00'))
        ultima = ParcelaFactory(contrato=contrato, valor_atual=Decimal('100.00'))

        r = client_admin.post(
            reverse('financeiro:pagar_parcela_ajax', args=[encode_id(ultima.pk)]),
            {'valor_pago': '100.00', 'data_pagamento': date.today().isoformat()})

        assert r.status_code == 200
        contrato.refresh_from_db()
        assert contrato.status == 'QUITADO'


# ─── HU-05: reajuste ─────────────────────────────────────────────────────────

class TestReajuste:

    def test_desconto_nao_e_aplicado_em_dobro(self):
        # `percentual` já é gravado líquido; o desconto é só registro.
        r = Reajuste(percentual=Decimal('6.0000'), percentual_bruto=Decimal('8.0000'),
                     desconto_percentual=Decimal('2.0000'))
        assert r.percentual_liquido == Decimal('6.0000')

    def test_api_recusa_ciclo_fora_de_ordem(self, client_admin):
        contrato = _contrato()   # contrato recém-criado: nenhum ciclo pendente
        r = client_admin.post(
            f'/financeiro/contrato/{contrato.pk}/reajuste/api/',
            json.dumps({'ciclo': 5}), content_type='application/json')
        assert r.status_code == 400
        assert not Reajuste.objects.filter(contrato=contrato).exists()


# ─── HU-11 / HU-12: percentual zero ──────────────────────────────────────────

class TestPercentualZero:

    def test_cessao_com_zero_por_cento_nao_cobra_taxa(self):
        contrato = _contrato()
        contrato.percentual_cessao = Decimal('0')
        resultado = contrato.calcular_cessao()
        assert resultado['taxa_cessao'] == Decimal('0.00')
        assert resultado['percentual_cessao'] == Decimal('0')


# ─── HU-19: webhook Evolution (formato Meta) ─────────────────────────────────

class TestWebhookEvolutionMeta:

    PAYLOAD = {
        'object': 'whatsapp_business_account',
        'entry': [{'changes': [{'value': {
            'statuses': [{'id': 'wamid.x', 'status': 'read', 'recipient_id': '5511999'}],
            'messages': [],
        }, 'field': 'messages'}]}],
    }

    def test_sem_apikey_e_recusado(self, client):
        from tests.fixtures.factories import NotificacaoFactory
        notif = NotificacaoFactory(external_id='wamid.x', status_entrega='')
        r = client.post(reverse('notificacoes:webhook_evolution'),
                        json.dumps(self.PAYLOAD), content_type='application/json')
        assert r.status_code == 403
        notif.refresh_from_db()
        assert notif.status_entrega == ''

    def test_com_apikey_valida_e_aceito(self, client):
        from notificacoes.models import ConfiguracaoWhatsApp
        from tests.fixtures.factories import ConfiguracaoWhatsAppFactory
        ConfiguracaoWhatsAppFactory(provedor='EVOLUTION', instancia='i1',
                                    api_key='chave-meta', ativo=True)
        assert ConfiguracaoWhatsApp.objects.filter(api_key='chave-meta').exists()
        r = client.post(reverse('notificacoes:webhook_evolution'),
                        json.dumps(self.PAYLOAD), content_type='application/json',
                        HTTP_APIKEY='chave-meta')
        assert r.status_code == 200


# ─── HU-23: excluir remessa devolve boletos ao pool ──────────────────────────

class TestExcluirRemessa:

    def test_boletos_voltam_para_gerado(self, client_admin):
        conta = ContaBancariaFactory()
        parcela = ParcelaFactory(
            contrato=_contrato(conta.imobiliaria), conta_bancaria=conta,
            nosso_numero='0000000099', status_boleto=StatusBoleto.REGISTRADO)
        remessa = ArquivoRemessaFactory(conta_bancaria=conta)
        ItemRemessaFactory(arquivo_remessa=remessa, parcela=parcela)

        r = client_admin.post(
            reverse('financeiro:excluir_remessa', args=[encode_id(remessa.pk)]))

        assert r.status_code == 200
        parcela.refresh_from_db()
        assert parcela.status_boleto == StatusBoleto.GERADO


# ─── HU-18: relatórios restritos às imobiliárias do usuário ──────────────────

class TestRelatoriosPorTenant:

    def test_exportacao_nao_traz_contrato_de_outra_imobiliaria(self):
        meu = _contrato()
        alheio = _contrato()
        cliente = _usuario_da(meu.imobiliaria)

        resp = cliente.get('/financeiro/relatorios/exportar/posicao_contratos/?formato=csv')

        assert resp.status_code == 200
        corpo = b''.join(resp.streaming_content) if resp.streaming else resp.content
        texto = corpo.decode('utf-8', 'replace')
        assert meu.numero_contrato in texto
        assert alheio.numero_contrato not in texto

    def test_tela_de_relatorio_abre_para_usuario_comum(self):
        contrato = _contrato()
        cliente = _usuario_da(contrato.imobiliaria)
        for url in ('/financeiro/relatorios/prestacoes-a-pagar/',
                    '/financeiro/relatorios/prestacoes-pagas/',
                    '/financeiro/relatorios/posicao-contratos/'):
            assert cliente.get(url).status_code == 200, url
