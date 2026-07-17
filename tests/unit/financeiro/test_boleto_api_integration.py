"""
Testes de integração Boleto-API
================================
Cobre:
  - BoletoApiClient: registrar_cobranca, retry em 5xx, erro 4xx
  - Parcela._gerar_via_boleto_api: persiste cobranca_id e status REGISTRADO
  - webhook_boleto_api: assinatura HMAC, liquidado baixa idempotente, sem_parcela
  - Flag de feature: provider=brcobranca mantém fluxo CNAB original

Desenvolvedor: Maxwell da Silva Oliveira
"""
import hashlib
import hmac
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client
from django.urls import reverse

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import StatusBoleto, TipoParcela

    imob = ImobiliariaFactory(nome='Imob BoletoAPI')
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='336', principal=True, ativo=True,
        convenio='000000000001',
        provider='c6',
        tenant_id='tenant-abc',
        account_config={'agencia': '0001', 'conta': '123456', 'convenio': '000000000001'},
    )
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador API')

    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-BAPI-1', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000.00'), valor_entrada=Decimal('10000.00'),
        numero_parcelas=6, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
    )
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
        valor_boleto=Decimal('8333.33'),
    )
    return imob, conta, contrato


@pytest.fixture
def staff_cli(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user('bapi_staff', password='x', is_staff=True)
    c = Client(); c.force_login(u)
    return u, c


# ---------------------------------------------------------------------------
# BoletoApiClient
# ---------------------------------------------------------------------------

class TestBoletoApiClient:
    def _client(self):
        from financeiro.services.boleto_api_client import BoletoApiClient
        return BoletoApiClient()

    def _mock_response(self, status_code: int, json_data: dict):
        m = MagicMock()
        m.status_code = status_code
        m.json.return_value = json_data
        m.content = b'x'
        m.text = json.dumps(json_data)
        return m

    def test_registrar_cobranca_sucesso(self):
        resp_data = {
            'id': 'cob-001',
            'status': 'registrado',
            'linha_digitavel': '12345.67890',
            'codigo_barras': '001234',
            'pix_copia_cola': '',
            'nosso_numero': '0000042',
            'valor': 500.00,
            'pdf_base64': '',
        }
        client = self._client()
        with patch.object(client, '_request', return_value=self._mock_response(201, resp_data)):
            resultado = client.registrar_cobranca(
                'ten1', 'c6', {'conta': '123'}, {'valor': 500.0, 'vencimento': '2025-03-01'}
            )
        assert resultado['sucesso'] is True
        assert resultado['cobranca_id'] == 'cob-001'
        assert resultado['linha_digitavel'] == '12345.67890'

    def test_registrar_cobranca_4xx_retorna_erro(self):
        client = self._client()
        err_resp = self._mock_response(422, {'detail': 'Conta inválida'})
        with patch.object(client, '_request', return_value=err_resp):
            resultado = client.registrar_cobranca('t', 'c6', {}, {})
        assert resultado['sucesso'] is False
        assert '422' in resultado['erro']
        assert 'Conta inválida' in resultado['erro']

    def test_registrar_cobranca_conexao_falha(self):
        import requests as _req
        client = self._client()
        with patch.object(client, '_request', side_effect=_req.ConnectionError('unreachable')):
            resultado = client.registrar_cobranca('t', 'c6', {}, {})
        assert resultado['sucesso'] is False
        assert 'Falha de conexão' in resultado['erro']

    def test_retry_em_5xx(self):
        """_request deve retentar requests.request em 5xx até max_tentativas."""
        import requests as _req
        client = self._client()
        client.max_tentativas = 3
        client.delay_inicial = 0   # sem sleep no teste

        resp_5xx = self._mock_response(503, {'detail': 'unavailable'})
        resp_ok = self._mock_response(201, {
            'id': 'ok', 'status': 'registrado', 'valor': 1.0,
            'linha_digitavel': '12345', 'codigo_barras': '00190000',
            'nosso_numero': '1', 'pdf_base64': '',
        })
        calls = {'n': 0}

        def fake_http(method, url, **kwargs):
            calls['n'] += 1
            if calls['n'] < 3:
                return resp_5xx
            return resp_ok

        with patch('financeiro.services.boleto_api_client.requests.request',
                   side_effect=fake_http), \
             patch('financeiro.services.boleto_api_client.time.sleep'):
            resultado = client.registrar_cobranca('t', 'sicoob', {}, {'valor': 1.0})
        assert resultado['sucesso'] is True
        assert calls['n'] == 3


# ---------------------------------------------------------------------------
# Parcela._gerar_via_boleto_api
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGerarViaBoletoApi:
    def _mock_api_sucesso(self, cobranca_id='cob-999'):
        return {
            'sucesso': True,
            'cobranca_id': cobranca_id,
            'nosso_numero': '0001',
            'nosso_numero_formatado': '0001',
            'nosso_numero_dv': '',
            'linha_digitavel': '111.222',
            'codigo_barras': '00190000',
            'pix_copia_cola': '',
            'pix_qrcode': '',
            'valor': Decimal('8333.33'),
            'pdf_content': b'%PDF-fake',
        }

    def test_persiste_cobranca_id(self, base):
        _, conta, contrato = base
        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca',
                   return_value=self._mock_api_sucesso('cob-xyz')):
            resultado = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        parcela.refresh_from_db()
        assert resultado['sucesso'] is True
        assert parcela.cobranca_id == 'cob-xyz'

    def test_status_registrado(self, base):
        from financeiro.models import StatusBoleto
        _, conta, contrato = base
        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca',
                   return_value=self._mock_api_sucesso()):
            parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        parcela.refresh_from_db()
        assert parcela.status_boleto == StatusBoleto.REGISTRADO

    def test_falha_nao_persiste(self, base):
        _, conta, contrato = base
        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca',
                   return_value={'sucesso': False, 'erro': 'timeout'}):
            resultado = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        parcela.refresh_from_db()
        assert resultado['sucesso'] is False
        assert parcela.cobranca_id == ''  # não gravou

    def test_provider_brcobranca_usa_fluxo_cnab(self, base):
        """provider=brcobranca deve chamar BoletoService, não BoletoApiClient."""
        _, conta, contrato = base
        conta.provider = 'brcobranca'
        conta.save(update_fields=['provider'])

        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca') as mock_api, \
             patch('financeiro.services.boleto_service.BoletoService.gerar_boleto',
                   return_value={'sucesso': True, 'nosso_numero': 'NN1',
                                 'nosso_numero_formatado': 'NN1', 'nosso_numero_dv': '',
                                 'linha_digitavel': 'L', 'codigo_barras': 'C',
                                 'valor': Decimal('8333.33'), 'pdf_content': None,
                                 'pix_copia_cola': '', 'pix_qrcode': ''}) as mock_svc:
            parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        mock_api.assert_not_called()
        mock_svc.assert_called_once()


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

def _assinatura(secret: str, body: bytes) -> str:
    return 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.django_db
class TestWebhookBoletoApi:
    URL = '/financeiro/webhooks/boleto-api/'

    def _post(self, payload: dict, secret: str = '', sig: str = ''):
        body = json.dumps(payload).encode()
        headers = {}
        if secret:
            headers['HTTP_X_SIGNATURE'] = _assinatura(secret, body)
        elif sig:
            headers['HTTP_X_SIGNATURE'] = sig
        return Client().post(
            self.URL,
            data=body,
            content_type='application/json',
            **headers,
        )

    def _criar_parcela_com_cobranca(self, cobranca_id='cob-123'):
        from tests.fixtures.factories import (
            ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
        )
        from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
        from financeiro.models import StatusBoleto, TipoParcela
        imob = ImobiliariaFactory()
        conta = ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True,
                                     provider='c6', tenant_id='t1')
        imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
        comprador = CompradorFactory()
        contrato = Contrato.objects.create(
            imobiliaria=imob, imovel=imovel, comprador=comprador,
            numero_contrato='CTR-WH-1', data_contrato=date(2025, 1, 1),
            data_primeiro_vencimento=date(2025, 2, 1),
            valor_total=Decimal('12000.00'), valor_entrada=Decimal('2000.00'),
            numero_parcelas=2, dia_vencimento=1,
            tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
            status=StatusContrato.ATIVO,
        )
        parcela = contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).first()
        parcela.cobranca_id = cobranca_id
        parcela.status_boleto = StatusBoleto.REGISTRADO
        parcela.save(update_fields=['cobranca_id', 'status_boleto'])
        return parcela

    # ---- Assinatura ----

    def test_assinatura_invalida_rejeita_401(self, settings):
        settings.EVENT_WEBHOOK_SECRET = 'segredo'
        resp = self._post({'id': 'x', 'status': 'liquidado'}, sig='sha256=invalido')
        assert resp.status_code == 401

    def test_sem_secret_em_debug_aceita(self, settings):
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        parcela = self._criar_parcela_com_cobranca('cob-nosig')
        resp = self._post({'id': 'cob-nosig', 'status': 'liquidado', 'valor': '100.00'})
        assert resp.status_code == 200

    def test_assinatura_valida_aceita(self, settings):
        settings.EVENT_WEBHOOK_SECRET = 'meu-segredo'
        parcela = self._criar_parcela_com_cobranca('cob-sig-ok')
        resp = self._post(
            {'id': 'cob-sig-ok', 'status': 'liquidado', 'valor': '100.00'},
            secret='meu-segredo',
        )
        assert resp.status_code == 200

    # ---- Processamento ----

    def test_liquidado_baixa_parcela(self, settings):
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        parcela = self._criar_parcela_com_cobranca('cob-liq')
        resp = self._post({
            'id': 'cob-liq', 'status': 'liquidado', 'event': 'payment.confirmed',
            'valor': '5000.00', 'paid_at': '2025-03-01T12:00:00',
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'baixado'
        parcela.refresh_from_db()
        assert parcela.pago is True

    def test_liquidado_idempotente(self, settings):
        """Segundo evento liquidado para a mesma cobrança não re-baixa a parcela."""
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        parcela = self._criar_parcela_com_cobranca('cob-idem')
        payload = {'id': 'cob-idem', 'status': 'liquidado', 'valor': '5000.00'}
        self._post(payload)
        resp2 = self._post(payload)
        data = resp2.json()
        assert data['status'] == 'duplicado'
        # Garantir que não foi baixada 2 vezes (o pagamento já estava registrado)
        parcela.refresh_from_db()
        assert parcela.pago is True

    def test_sem_parcela_vinculada(self, settings):
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = self._post({'id': 'cob-inexistente', 'status': 'liquidado', 'valor': '100'})
        assert resp.status_code == 200
        assert resp.json()['status'] == 'sem_parcela'

    def test_id_ausente_retorna_400(self, settings):
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = self._post({'status': 'liquidado'})  # sem 'id'
        assert resp.status_code == 400

    def test_json_invalido_retorna_400(self, settings):
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = Client().post(self.URL, data=b'nao-e-json', content_type='application/json')
        assert resp.status_code == 400

    def test_evento_nao_liquidado_nao_baixa(self, settings):
        """status != liquidado não deve baixar a parcela."""
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        parcela = self._criar_parcela_com_cobranca('cob-pend')
        self._post({'id': 'cob-pend', 'status': 'pendente', 'valor': '5000'})
        parcela.refresh_from_db()
        assert parcela.pago is False
