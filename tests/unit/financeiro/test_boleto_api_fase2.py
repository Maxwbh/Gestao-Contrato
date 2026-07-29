"""
Fase 2 Boleto-API — campos de rastreio de emissão na Parcela e a fiação do
status normalizado na emissão via gateway.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from financeiro.models import Parcela, StatusCobranca, StatusBoleto, MetodoCobranca


class TestRegistrarEmissao:
    def test_defaults_em_branco(self):
        p = Parcela()
        assert p.provider == '' and p.metodo_cobranca == ''
        assert p.ext_ref == '' and p.status_cobranca == ''

    def test_seta_somente_informado(self):
        p = Parcela()
        p.registrar_emissao(provider='sicoob', metodo=MetodoCobranca.BOLETO,
                            status=StatusCobranca.REGISTRADA, cobranca_id='C1', ext_ref='E1')
        assert p.provider == 'sicoob'
        assert p.metodo_cobranca == 'boleto'
        assert p.status_cobranca == 'registrada'
        assert p.cobranca_id == 'C1' and p.ext_ref == 'E1'

    def test_nao_sobrescreve_com_vazio(self):
        p = Parcela(provider='c6', cobranca_id='ja')
        p.registrar_emissao(status=StatusCobranca.LIQUIDADA)  # provider/cobranca_id omitidos
        assert p.provider == 'c6' and p.cobranca_id == 'ja'
        assert p.status_cobranca == 'liquidada'


@pytest.fixture
def base_c6(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import TipoParcela

    imob = ImobiliariaFactory()
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='336', principal=True, ativo=True,
        convenio='000000000001', provider='c6', tenant_id='tenant-abc',
        account_config={'billing_scheme': 'padrao', 'chave_pix': 'x@y.z'},
    )
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory()
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-F2-1', data_contrato=date(2025, 1, 1),
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
    return conta, contrato


def _mock_ok(cobranca_id='cob-1'):
    return {
        'sucesso': True, 'cobranca_id': cobranca_id,
        'nosso_numero': '0001', 'nosso_numero_formatado': '0001', 'nosso_numero_dv': '',
        'linha_digitavel': '111.222', 'codigo_barras': '00190000',
        'pix_copia_cola': '', 'pix_qrcode': '', 'valor': Decimal('8333.33'),
        'pdf_content': b'%PDF-fake', 'ext_ref': 'ext-77',
    }


@pytest.mark.django_db
class TestEmissaoFiaStatusNormalizado:
    def test_emissao_registra_rastreio(self, base_c6):
        conta, contrato = base_c6
        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca',
                   return_value=_mock_ok('cob-xyz')):
            parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        parcela.refresh_from_db()
        assert parcela.provider == 'c6'
        assert parcela.metodo_cobranca == MetodoCobranca.BOLETO
        assert parcela.status_cobranca == StatusCobranca.REGISTRADA
        assert parcela.ext_ref == 'ext-77'
        assert parcela.status_boleto == StatusBoleto.REGISTRADO
