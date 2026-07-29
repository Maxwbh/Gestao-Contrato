"""
Fase 3 Boleto-API — cliente stateless (Bearer + erros), onboarding e emissão
multi-método (bolepix), tudo com mocks (gateway não é acessado).
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from financeiro.services.boleto_api_client import BoletoApiClient
from financeiro.services import boleto_api_onboarding as onb


def _resp(status_code, json_data):
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_data
    m.text = str(json_data)
    return m


# --------------------------------------------------------------------------- #
# Cliente: Bearer + mapeamento de erros
# --------------------------------------------------------------------------- #
class TestClienteBearerErros:
    def test_bearer_enviado(self):
        client = BoletoApiClient()
        ok = _resp(201, {'id': 'c1', 'status': 'registrado', 'valor': 10.0})
        with patch.object(client, '_request', return_value=ok) as req:
            client.registrar_cobranca('t', 'c6', {}, {'valor': 10}, bapi_token='bapi_XYZ')
        assert req.call_args.kwargs['headers'] == {'Authorization': 'Bearer bapi_XYZ'}

    def test_sem_token_sem_header(self):
        client = BoletoApiClient()
        ok = _resp(201, {'id': 'c1', 'status': 'ok', 'valor': 10.0})
        with patch.object(client, '_request', return_value=ok) as req:
            client.registrar_cobranca('t', 'c6', {}, {'valor': 10})
        assert req.call_args.kwargs['headers'] == {}

    @pytest.mark.parametrize('code,motivo', [
        (401, 'credencial'), (424, 'credencial'), (409, 'cip'),
        (422, 'validacao'), (400, 'http'),
    ])
    def test_classificacao_erro(self, code, motivo):
        client = BoletoApiClient()
        with patch.object(client, '_request', return_value=_resp(code, {'detail': 'x'})):
            r = client.registrar_cobranca('t', 'c6', {}, {'valor': 1})
        assert r['sucesso'] is False and r['motivo'] == motivo and r['codigo'] == code


# --------------------------------------------------------------------------- #
# Cliente: onboarding e novos métodos
# --------------------------------------------------------------------------- #
class TestClienteEndpoints:
    def test_criar_credenciais_ok(self):
        client = BoletoApiClient()
        with patch.object(client, '_request', return_value=_resp(201, {'bapi_token': 'bapi_new'})):
            r = client.criar_credenciais('t', 'c6', {'client_id': 'a'})
        assert r == {'sucesso': True, 'bapi_token': 'bapi_new'}

    def test_criar_credenciais_sem_token(self):
        client = BoletoApiClient()
        with patch.object(client, '_request', return_value=_resp(201, {})):
            r = client.criar_credenciais('t', 'c6', {})
        assert r['sucesso'] is False

    def test_emitir_bolepix_ext_ref(self):
        client = BoletoApiClient()
        data = {'id': 'b1', 'ext_ref': 'ext-9', 'status': 'ok', 'valor': 50.0,
                'linha_digitavel': '111', 'pix_copia_cola': 'EMV'}
        with patch.object(client, '_request', return_value=_resp(201, data)):
            r = client.emitir_bolepix('t', 'c6', {}, {'valor': 50}, bapi_token='bapi_1')
        assert r['sucesso'] is True and r['ext_ref'] == 'ext-9' and r['pix_copia_cola'] == 'EMV'

    def test_emitir_pix_txid(self):
        client = BoletoApiClient()
        with patch.object(client, '_request',
                          return_value=_resp(201, {'txid': 'TX1', 'emv': 'PIXEMV', 'valor': 30.0})):
            r = client.emitir_pix('t', 'sicoob', {}, {'valor': 30}, bapi_token='bapi_1')
        assert r['sucesso'] is True and r['txid'] == 'TX1' and r['pix_copia_cola'] == 'PIXEMV'


# --------------------------------------------------------------------------- #
# Serviço de onboarding
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestOnboardingServico:
    def _conta(self, com_credenciais=True):
        from tests.fixtures.factories import ContaBancariaApiFactory
        conta = ContaBancariaApiFactory(banco='336', provider='c6', tenant_id='ten-1')
        if com_credenciais:
            conta.credenciais = {'client_id': 'a', 'client_secret': 'b'}
            conta.save()
        return conta

    def test_onboard_sem_credenciais(self):
        conta = self._conta(com_credenciais=False)
        assert onb.onboard_conta(conta, client=MagicMock()).get('sucesso') is False

    def test_onboard_grava_token(self):
        conta = self._conta()
        cli = MagicMock()
        cli.criar_credenciais.return_value = {'sucesso': True, 'bapi_token': 'bapi_zz'}
        assert onb.onboard_conta(conta, client=cli)['sucesso'] is True
        conta.refresh_from_db()
        assert conta.bapi_token == 'bapi_zz' and conta.bapi_token_criado_em is not None

    def test_garantir_usa_token_existente(self):
        conta = self._conta()
        conta.set_bapi_token('bapi_ja'); conta.save()
        cli = MagicMock()
        assert onb.garantir_bapi_token(conta, client=cli) == {'sucesso': True, 'bapi_token': 'bapi_ja'}
        cli.criar_credenciais.assert_not_called()

    def test_retry_credencial_recadastra(self):
        conta = self._conta()
        conta.set_bapi_token('bapi_old'); conta.save()  # já tem token → garantir não onboarda
        cli = MagicMock()
        cli.criar_credenciais.return_value = {'sucesso': True, 'bapi_token': 'bapi_novo'}
        chamadas = [{'sucesso': False, 'motivo': 'credencial', 'codigo': 401},
                    {'sucesso': True, 'cobranca_id': 'ok'}]
        fn = MagicMock(side_effect=chamadas)
        r = onb.com_retry_credencial(conta, fn, client=cli)
        assert r['sucesso'] is True and fn.call_count == 2
        assert cli.criar_credenciais.call_count == 1  # recadastrou uma vez (só no retry)


# --------------------------------------------------------------------------- #
# Dispatch por método (bolepix) na emissão
# --------------------------------------------------------------------------- #
@pytest.fixture
def base_bolepix(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import StatusBoleto, TipoParcela

    imob = ImobiliariaFactory(metodos_cobranca=['boleto', 'bolepix'])
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='336', principal=True, ativo=True,
        convenio='000000000001', provider='c6', tenant_id='tenant-abc',
        account_config={'billing_scheme': 'padrao', 'chave_pix': 'x@y.z'},
    )
    conta.set_bapi_token('bapi_conta'); conta.save()
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory()
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-F3-1', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000.00'), valor_entrada=Decimal('10000.00'),
        numero_parcelas=6, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO, metodo_cobranca='bolepix',
    )
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
        valor_boleto=Decimal('8333.33'),
    )
    return conta, contrato


@pytest.mark.django_db
class TestDispatchBolepix:
    def _ok_bolepix(self):
        return {
            'sucesso': True, 'cobranca_id': 'cob-bp', 'ext_ref': 'ext-55',
            'nosso_numero': '0001', 'nosso_numero_formatado': '0001', 'nosso_numero_dv': '',
            'linha_digitavel': '111', 'codigo_barras': '00190000',
            'pix_copia_cola': 'EMV', 'pix_qrcode': '', 'valor': Decimal('8333.33'),
            'pdf_content': b'%PDF',
        }

    def test_bolepix_usa_endpoint_e_grava_rastreio(self, base_bolepix):
        from financeiro.models import MetodoCobranca, StatusCobranca
        conta, contrato = base_bolepix
        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.emitir_bolepix',
                   return_value=self._ok_bolepix()) as m_bp, \
             patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca') as m_reg:
            parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        m_bp.assert_called_once()
        m_reg.assert_not_called()
        # Bearer token da conta foi passado
        assert m_bp.call_args.kwargs.get('bapi_token') == 'bapi_conta'
        parcela.refresh_from_db()
        assert parcela.metodo_cobranca == MetodoCobranca.BOLETO_PIX
        assert parcela.status_cobranca == StatusCobranca.REGISTRADA
        assert parcela.ext_ref == 'ext-55'
