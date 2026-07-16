"""
Fase 1 Boleto-API — escolha do método de cobrança no contrato, validado contra
os métodos habilitados na imobiliária (lenient quando a lista está vazia).
"""
import pytest
from django.core.exceptions import ValidationError

from tests.fixtures.factories import ImobiliariaFactory, ImovelFactory, ContratoFactory


@pytest.mark.django_db
class TestContratoMetodoCobranca:
    def test_default_boleto_ok(self):
        contrato = ContratoFactory()
        assert contrato.metodo_cobranca == 'boleto'

    def test_metodo_habilitado_ok(self):
        imob = ImobiliariaFactory(metodos_cobranca=['boleto', 'pix_automatico'])
        imovel = ImovelFactory(imobiliaria=imob)
        contrato = ContratoFactory(imovel=imovel, metodo_cobranca='pix_automatico')
        assert contrato.metodo_cobranca == 'pix_automatico'

    def test_metodo_nao_habilitado_levanta(self):
        imob = ImobiliariaFactory(metodos_cobranca=['boleto'])
        imovel = ImovelFactory(imobiliaria=imob)
        with pytest.raises(ValidationError):
            ContratoFactory(imovel=imovel, metodo_cobranca='pix_automatico')

    def test_lenient_quando_lista_vazia(self):
        imob = ImobiliariaFactory(metodos_cobranca=[])
        imovel = ImovelFactory(imobiliaria=imob)
        contrato = ContratoFactory(imovel=imovel, metodo_cobranca='pix_automatico')
        assert contrato.metodo_cobranca == 'pix_automatico'
