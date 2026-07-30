"""
Regressões da geração de boleto OFFLINE (motor pyCobrança / cobranca_api).

Cobrem três defeitos que zeravam a geração de carnê em produção quando as
contas eram offline:

1. Sicoob (756) com carteira '01' (2 dígitos) estourava o campo livre do código
   de barras → HTTP 400 "base.too_long". A carteira deve ir com 1 dígito.
2. Bancos que não usam convênio (ex.: Bradesco) recebiam convenio='' e o motor
   rejeitava com "Convenio não é um número". Convênio vazio deve ser omitido.
3. O valor legado provider='brcobranca' (modo offline) era roteado para o
   gateway de cobrança registrada (Boleto-API), que não existe sem credenciais.
"""
import pytest
from unittest.mock import patch

from core.models import ProviderBoleto, PROVIDER_OFFLINE_LEGADO
from financeiro.services.boleto_service import BoletoService

from tests.fixtures.factories import (
    ContaBancariaFactory, ContratoFactory, ParcelaFactory, ImovelFactory,
)

pytestmark = pytest.mark.django_db


def _parcela(**conta_kwargs):
    conta = ContaBancariaFactory(**conta_kwargs)
    imob = conta.imobiliaria
    contrato = ContratoFactory(imobiliaria=imob, imovel=ImovelFactory(imobiliaria=imob))
    return ParcelaFactory(contrato=contrato), conta


class TestCarteiraSicoob:
    def test_carteira_01_normalizada_para_1_digito(self):
        """Sicoob: carteira armazenada '01' vira '1' no payload do boleto."""
        parcela, conta = _parcela(banco='756', carteira='01', convenio='1234567')
        dados, _ = BoletoService()._montar_dados_boleto(parcela, conta)
        assert dados['carteira'] == '1'

    @pytest.mark.parametrize('entrada,esperado', [
        ('01', '1'), ('1', '1'), ('03', '3'), ('9', '9'),
        ('00', '1'),   # inválida → default 1
        ('7', '1'),    # fora de {1,3,9} → default 1
    ])
    def test_carteiras_validas(self, entrada, esperado):
        parcela, conta = _parcela(banco='756', carteira=entrada, convenio='1234567')
        dados, _ = BoletoService()._montar_dados_boleto(parcela, conta)
        assert dados['carteira'] == esperado


class TestNossoNumeroCaixa:
    def test_caixa_nosso_numero_15_digitos(self):
        """Caixa (104): o motor SIGCB exige nosso_numero com exatamente 15 dígitos."""
        parcela, conta = _parcela(banco='104', carteira='1', convenio='123456')
        dados, _ = BoletoService()._montar_dados_boleto(parcela, conta)
        assert len(dados['nosso_numero']) == 15, dados['nosso_numero']
        assert dados['nosso_numero'].isdigit()


class TestConvenioVazio:
    def test_convenio_vazio_omitido_do_payload(self):
        """Bradesco não usa convênio: convenio='' não deve ir no payload."""
        parcela, conta = _parcela(banco='237', carteira='06', convenio='')
        dados, _ = BoletoService()._montar_dados_boleto(parcela, conta)
        assert 'convenio' not in dados

    def test_convenio_preenchido_permanece(self):
        parcela, conta = _parcela(banco='001', carteira='18', convenio='12345678')
        dados, _ = BoletoService()._montar_dados_boleto(parcela, conta)
        assert dados.get('convenio')


class TestRoteamentoProviderLegado:
    def test_brcobranca_legado_nao_vai_ao_gateway(self):
        """provider='brcobranca' (offline legado) usa o motor offline, não o BAPI."""
        parcela, conta = _parcela(
            banco='001', carteira='18', convenio='12345678',
            provider=PROVIDER_OFFLINE_LEGADO,
        )
        with patch.object(BoletoService, 'gerar_boleto',
                          return_value={'sucesso': False, 'erro': 'stub'}) as offline, \
             patch.object(type(parcela), '_gerar_via_boleto_api') as gateway:
            parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        offline.assert_called_once()
        gateway.assert_not_called()

    def test_e_boleto_api_falso_para_brcobranca(self):
        parcela, conta = _parcela(
            banco='001', provider=PROVIDER_OFFLINE_LEGADO,
        )
        parcela.provider = PROVIDER_OFFLINE_LEGADO
        assert parcela._e_boleto_api() is False

    def test_e_boleto_api_verdadeiro_para_sicoob_registrado(self):
        parcela, _ = _parcela(banco='001')
        parcela.provider = ProviderBoleto.SICOOB
        assert parcela._e_boleto_api() is True
