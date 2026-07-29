"""
Revisão do cadastro C6/Sicoob × geração de boleto.

Uma conta cadastrada pelo formulário guarda as credenciais do banco **cifradas**,
mas ainda **sem `bapi_token`** (onboarding). A emissão deve, então, provisionar as
credenciais no gateway (POST /credenciais) antes de registrar a cobrança e
recadastrar automaticamente em 401/424 — sem isso, a 1ª geração de boleto falharia.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest


def _mock_cobranca_ok(cobranca_id='cob-1'):
    return {
        'sucesso': True, 'cobranca_id': cobranca_id,
        'nosso_numero': '0001', 'nosso_numero_formatado': '0001', 'nosso_numero_dv': '',
        'linha_digitavel': '111.222', 'codigo_barras': '00190000',
        'pix_copia_cola': '', 'pix_qrcode': '',
        'valor': Decimal('8333.33'), 'pdf_content': None,
    }


def _contrato_com_parcelas(imob, conta):
    from tests.fixtures.factories import ImovelFactory, CompradorFactory
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import StatusBoleto, TipoParcela

    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador API')
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-BAPI-EMISS', data_contrato=date(2025, 1, 1),
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
    return contrato


@pytest.fixture
def conta_sicoob_com_credenciais(db):
    from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaApiFactory
    imob = ImobiliariaFactory(nome='Imob Emissao')
    conta = ContaBancariaApiFactory(
        imobiliaria=imob, banco='756', provider='sicoob', principal=True)
    conta.credenciais = {'client_id': 'CID', 'client_secret': 'SEC'}
    conta.save()
    return imob, conta


_CRED = 'financeiro.services.boleto_api_client.BoletoApiClient.criar_credenciais'
_REG = 'financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca'


@pytest.mark.django_db
class TestCadastroCredenciaisEmissao:
    def test_onboarding_dispara_antes_de_emitir(self, conta_sicoob_com_credenciais):
        from financeiro.models import StatusBoleto
        imob, conta = conta_sicoob_com_credenciais
        contrato = _contrato_com_parcelas(imob, conta)
        parcela = contrato.parcelas.first()
        assert not conta.bapi_token  # recém-cadastrada: sem token

        with patch(_CRED, return_value={'sucesso': True, 'bapi_token': 'bapi_new'}) as onb, \
             patch(_REG, return_value=_mock_cobranca_ok('cob-xyz')) as reg:
            r = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)

        assert r['sucesso'] is True
        onb.assert_called_once()                       # provisionou credenciais
        conta.refresh_from_db()
        assert conta.bapi_token == 'bapi_new'          # token persistido
        # A cobrança foi registrada com o token recém-obtido.
        assert reg.call_args.kwargs.get('bapi_token') == 'bapi_new'
        parcela.refresh_from_db()
        assert parcela.status_boleto == StatusBoleto.REGISTRADO
        assert parcela.cobranca_id == 'cob-xyz'

    def test_recadastra_e_retenta_em_401(self, conta_sicoob_com_credenciais):
        imob, conta = conta_sicoob_com_credenciais
        contrato = _contrato_com_parcelas(imob, conta)
        parcela = contrato.parcelas.first()

        with patch(_CRED, return_value={'sucesso': True, 'bapi_token': 'bapi_x'}) as onb, \
             patch(_REG, side_effect=[{'sucesso': False, 'motivo': 'credencial'},
                                      _mock_cobranca_ok('cob-2')]) as reg:
            r = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)

        assert r['sucesso'] is True
        assert reg.call_count == 2   # 1ª falhou por credencial, 2ª ok
        assert onb.call_count == 2   # onboarding inicial + recadastro após 401

    def test_onboarding_falha_nao_emite(self, conta_sicoob_com_credenciais):
        imob, conta = conta_sicoob_com_credenciais
        contrato = _contrato_com_parcelas(imob, conta)
        parcela = contrato.parcelas.first()

        with patch(_CRED, return_value={'sucesso': False, 'erro': 'credencial inválida'}), \
             patch(_REG) as reg:
            r = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)

        assert r['sucesso'] is False
        reg.assert_not_called()      # não tenta registrar sem onboarding
        parcela.refresh_from_db()
        assert parcela.cobranca_id == ''


@pytest.mark.django_db
class TestSemCredenciaisMantemCompat:
    def test_sem_credenciais_nao_onboarda(self, db):
        """Conta sem credenciais no sistema mantém o fluxo antigo (gateway
        resolve por tenant_id) — não dispara onboarding."""
        from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaFactory
        imob = ImobiliariaFactory(nome='Imob Legacy')
        conta = ContaBancariaFactory(
            imobiliaria=imob, banco='336', provider='c6', tenant_id='tenant-legacy',
            account_config={'billing_scheme': 'BILL_1'}, principal=True)
        assert not conta.credenciais
        contrato = _contrato_com_parcelas(imob, conta)
        parcela = contrato.parcelas.first()

        with patch(_CRED) as onb, \
             patch(_REG, return_value=_mock_cobranca_ok('cob-legacy')) as reg:
            r = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)

        assert r['sucesso'] is True
        onb.assert_not_called()      # sem credenciais → sem onboarding
        reg.assert_called_once()
