"""
Fase 10 Boleto-API V2.2 — checkout (link de pagamento hospedado: cartão + Pix).
Cliente stateless com mocks (o gateway não é acessado).
"""
from unittest.mock import patch

import pytest

from financeiro.services.boleto_api_client import BoletoApiClient


def _resp(status_code, json_data=None):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_data if json_data is not None else {}
    if json_data is None:
        m.json.side_effect = ValueError('no json')
    m.text = str(json_data)
    return m


class TestCriarCheckout:
    def test_ok_normaliza_url_e_id(self):
        client = BoletoApiClient()
        data = {'id': 'chk_123', 'url': 'https://pay.bank/x', 'status': 'pendente',
                'expira_em': '2026-08-12', 'raw': {'k': 1}}
        with patch.object(client, '_request', return_value=_resp(201, data)):
            r = client.criar_checkout('t', 'inter', {}, {'valor': 100})
        assert r['sucesso'] is True
        assert r['checkout_id'] == 'chk_123'
        assert r['url'] == 'https://pay.bank/x'
        assert r['status'] == 'pendente'
        assert r['expira_em'] == '2026-08-12'

    def test_bearer_e_endpoint(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(201, {'id': 'c', 'url': 'u', 'status': 'pendente'})) as req:
            client.criar_checkout('t', 'inter', {}, {'valor': 100}, bapi_token='bapi_Z')
        assert req.call_args.args[0] == 'POST'
        assert req.call_args.args[1] == '/checkout'
        assert req.call_args.kwargs['headers'] == {'Authorization': 'Bearer bapi_Z'}

    def test_payload_leva_cartao_parcelas_pix(self):
        client = BoletoApiClient()
        checkout = {'valor': 100, 'tipo': 'credito', 'parcelas': 12,
                    'juros_por': 'emissor', 'pix': True,
                    'external_reference_id': 'GC0000012P0001'}
        with patch.object(client, '_request',
                          return_value=_resp(201, {'id': 'c', 'url': 'u', 'status': 'pendente'})) as req:
            client.criar_checkout('t', 'inter', {'billing_scheme': 'x'}, checkout)
        sent = req.call_args.kwargs['json']
        assert sent['provider'] == 'inter'
        assert sent['checkout']['tipo'] == 'credito'
        assert sent['checkout']['parcelas'] == 12
        assert sent['checkout']['pix'] is True
        assert sent['checkout']['external_reference_id'] == 'GC0000012P0001'
        assert sent['account_config'] == {'billing_scheme': 'x'}

    def test_credentials_incluidas_quando_passadas(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(201, {'id': 'c', 'url': 'u', 'status': 'pendente'})) as req:
            client.criar_checkout('t', 'inter', {}, {'valor': 1}, credentials={'client_id': 'a'})
        assert req.call_args.kwargs['json']['credentials'] == {'client_id': 'a'}

    def test_credentials_omitidas_por_padrao(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(201, {'id': 'c', 'url': 'u', 'status': 'pendente'})) as req:
            client.criar_checkout('t', 'inter', {}, {'valor': 1})
        assert 'credentials' not in req.call_args.kwargs['json']

    def test_status_erro_vira_falha(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(200, {'status': 'erro', 'detail': 'recusado'})):
            r = client.criar_checkout('t', 'inter', {}, {'valor': 1})
        assert r['sucesso'] is False and 'recusado' in r['erro']

    @pytest.mark.parametrize('code,motivo', [
        (401, 'credencial'), (422, 'validacao'), (400, 'http'),
    ])
    def test_erros_http_mapeados(self, code, motivo):
        client = BoletoApiClient()
        with patch.object(client, '_request', return_value=_resp(code, {'detail': 'x'})):
            r = client.criar_checkout('t', 'inter', {}, {'valor': 1})
        assert r['sucesso'] is False and r['motivo'] == motivo


class TestConsultarCancelarCheckout:
    def test_consultar_ok(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(200, {'id': 'c', 'url': 'u', 'status': 'liquidado'})) as req:
            r = client.consultar_checkout('c')
        assert req.call_args.args == ('GET', '/checkout/c')
        assert r['sucesso'] is True and r['status'] == 'liquidado'

    def test_cancelar_204_sem_body(self):
        client = BoletoApiClient()
        with patch.object(client, '_request', return_value=_resp(204, None)) as req:
            r = client.cancelar_checkout('c')
        assert req.call_args.args == ('DELETE', '/checkout/c')
        assert r == {'sucesso': True}

    def test_cancelar_200_com_body(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(200, {'id': 'c', 'status': 'baixado'})):
            r = client.cancelar_checkout('c')
        assert r['sucesso'] is True and r['status'] == 'baixado'


CLIENT = 'financeiro.services.boleto_api_client.BoletoApiClient'


def _parcela_c6(**kw):
    from tests.fixtures.factories import ParcelaFactory, ContaBancariaApiFactory
    from financeiro.models import StatusBoleto
    conta = ContaBancariaApiFactory(banco='336', provider='c6', tenant_id='ten-c6')
    conta.set_bapi_token('bapi_x')
    conta.save()
    defaults = dict(provider='c6', conta_bancaria=conta,
                    status_boleto=StatusBoleto.REGISTRADO, pago=False)
    defaults.update(kw)
    return ParcelaFactory(**defaults)


@pytest.mark.django_db
class TestGerarLinkPagamento:
    def test_sucesso_persiste_url_id_metodo(self):
        from core.models import MetodoCobranca
        from financeiro.models import StatusCobranca
        p = _parcela_c6()
        ok = {'sucesso': True, 'checkout_id': 'chk_9', 'url': 'https://pay/abc',
              'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            r = p.gerar_link_pagamento(tipo='credito', parcelas=12)
        assert r['sucesso'] is True and r['url'] == 'https://pay/abc'
        p.refresh_from_db()
        assert p.checkout_url == 'https://pay/abc'
        assert p.cobranca_id == 'chk_9'          # casa o webhook por payload['id']
        assert p.metodo_cobranca == MetodoCobranca.CHECKOUT
        assert p.status_cobranca == StatusCobranca.REGISTRADA
        assert m.call_args.kwargs.get('bapi_token') == 'bapi_x'

    def test_payload_cartao_parcelas_juros_pix_extref(self):
        p = _parcela_c6()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(tipo='credito', parcelas=6, juros_por='loja',
                                   oferecer_pix=True)
        chk = m.call_args.args[3]
        assert chk['tipo'] == 'credito' and chk['parcelas'] == 6
        assert chk['juros_por'] == 'loja' and chk['pix'] is True
        assert chk['external_reference_id'] == f'GC{p.contrato_id:07d}P{p.numero_parcela:04d}'
        assert chk['pagador']['nome']

    def test_parcela_paga_recusa(self):
        p = _parcela_c6(pago=True)
        r = p.gerar_link_pagamento()
        assert r['sucesso'] is False

    def test_config_do_cartao_da_conta_sobrepoe_imobiliaria(self):
        from decimal import Decimal
        p = _parcela_c6(valor_atual=Decimal('6000'))
        imob = p.contrato.imobiliaria
        imob.checkout_max_parcelas = 12
        imob.checkout_juros_por = 'emissor'
        imob.save()
        # conta define política própria (override): teto 6, juros 'loja'
        conta = p.conta_bancaria
        conta.card_max_parcelas = 6
        conta.card_juros_por = 'loja'
        conta.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(parcelas=12)  # sem juros_por → usa a conta
        chk = m.call_args.args[3]
        assert chk['parcelas'] == 6          # teto da conta
        assert chk['juros_por'] == 'loja'    # juros da conta

    def test_pix_no_link_default_da_conta(self):
        p = _parcela_c6()
        conta = p.conta_bancaria
        conta.pix_no_link = True
        conta.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(parcelas=1)  # sem oferecer_pix → usa a conta
        assert m.call_args.args[3]['pix'] is True

    def test_juros_por_default_da_imobiliaria(self):
        from core.models import JurosParcelamento
        p = _parcela_c6()
        imob = p.contrato.imobiliaria
        imob.checkout_juros_por = JurosParcelamento.LOJA
        imob.save(update_fields=['checkout_juros_por'])
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento()  # sem juros_por → usa a política da imobiliária
        assert m.call_args.args[3]['juros_por'] == 'loja'

    def test_juros_por_explicito_sobrepoe_imobiliaria(self):
        from core.models import JurosParcelamento
        p = _parcela_c6()
        imob = p.contrato.imobiliaria
        imob.checkout_juros_por = JurosParcelamento.LOJA
        imob.save(update_fields=['checkout_juros_por'])
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(juros_por='emissor')
        assert m.call_args.args[3]['juros_por'] == 'emissor'

    def test_teto_de_parcelas_da_imobiliaria(self):
        from decimal import Decimal
        p = _parcela_c6(valor_atual=Decimal('6000'))
        imob = p.contrato.imobiliaria
        imob.checkout_max_parcelas = 6
        imob.checkout_valor_minimo_parcela = Decimal('0')
        imob.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            r = p.gerar_link_pagamento(parcelas=12)  # pediu 12, teto é 6
        assert m.call_args.args[3]['parcelas'] == 6
        assert r['parcelas'] == 6

    def test_piso_por_parcela_reduz_parcelas(self):
        from decimal import Decimal
        p = _parcela_c6(valor_atual=Decimal('1000'))
        imob = p.contrato.imobiliaria
        imob.checkout_max_parcelas = 24
        imob.checkout_valor_minimo_parcela = Decimal('200')  # 1000/200 = 5
        imob.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(parcelas=12)
        assert m.call_args.args[3]['parcelas'] == 5

    def test_piso_zero_sem_limite_por_valor(self):
        from decimal import Decimal
        p = _parcela_c6(valor_atual=Decimal('100'))
        imob = p.contrato.imobiliaria
        imob.checkout_max_parcelas = 12
        imob.checkout_valor_minimo_parcela = Decimal('0')
        imob.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(parcelas=10)
        assert m.call_args.args[3]['parcelas'] == 10

    def test_parcelas_nunca_abaixo_de_um(self):
        from decimal import Decimal
        p = _parcela_c6(valor_atual=Decimal('50'))
        imob = p.contrato.imobiliaria
        imob.checkout_valor_minimo_parcela = Decimal('200')  # piso > valor total
        imob.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok) as m:
            p.gerar_link_pagamento(parcelas=6)
        assert m.call_args.args[3]['parcelas'] == 1

    @pytest.mark.parametrize('kw', [{'tipo': 'x'}, {'juros_por': 'z'}])
    def test_parametros_invalidos(self, kw):
        p = _parcela_c6()
        assert p.gerar_link_pagamento(**kw)['sucesso'] is False

    def test_sem_conta_api_usa_conta_da_imobiliaria(self):
        from tests.fixtures.factories import ParcelaFactory, ContaBancariaApiFactory
        p = ParcelaFactory(provider='', pago=False)
        conta = ContaBancariaApiFactory(
            banco='336', provider='c6', tenant_id='ten-c6',
            imobiliaria=p.contrato.imobiliaria, principal=True)
        conta.set_bapi_token('bapi_x'); conta.save()
        ok = {'sucesso': True, 'checkout_id': 'c', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok):
            r = p.gerar_link_pagamento()
        assert r['sucesso'] is True
        p.refresh_from_db()
        assert p.conta_bancaria_id == conta.id


@pytest.mark.django_db
class TestCheckoutConciliacaoWebhook:
    def test_liquidacao_por_cobranca_id_da_baixa(self):
        """O webhook casa o pagamento do checkout por payload['id'] = checkout_id
        (gravado em cobranca_id), sem alterações no receptor."""
        from financeiro.views import _processar_evento_cobranca
        p = _parcela_c6()
        ok = {'sucesso': True, 'checkout_id': 'chk_pay', 'url': 'u', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok):
            p.gerar_link_pagamento()
        res = _processar_evento_cobranca(
            cobranca_id='chk_pay', status_cobranca='liquidado',
            event='checkout.pago', paid_at_str='2026-08-05T10:00:00',
            valor_str=str(p.valor_atual or p.valor_boleto or '0'),
            payload_raw='{}', event_id='ev-chk-1')
        assert res['status'] in ('baixado', 'ok') or 'parcela_id' in res
        p.refresh_from_db()
        assert p.pago is True


@pytest.mark.django_db
class TestViewLinkPagamento:
    def _login(self, client):
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.create_user(username='op', password='x', is_staff=True)
        client.force_login(u)
        return u

    def test_endpoint_gera_link(self, client):
        from django.urls import reverse
        self._login(client)
        p = _parcela_c6()
        ok = {'sucesso': True, 'checkout_id': 'c1', 'url': 'https://pay/z', 'status': 'pendente'}
        with patch(f'{CLIENT}.criar_checkout', return_value=ok):
            resp = client.post(
                reverse('financeiro:gerar_link_pagamento_parcela', args=[p.id]),
                {'tipo': 'credito', 'parcelas': '10', 'pix': '1'})
        assert resp.status_code == 200
        assert resp.json()['url'] == 'https://pay/z'

    def test_endpoint_get_bloqueado(self, client):
        from django.urls import reverse
        self._login(client)
        p = _parcela_c6()
        resp = client.get(reverse('financeiro:gerar_link_pagamento_parcela', args=[p.id]))
        assert resp.status_code == 405
