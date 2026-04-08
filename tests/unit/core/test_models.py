"""
Section 7.2 P2 — Unit tests for core models.

Tests: Contabilidade, Imobiliaria (PF/PJ validation, documento property),
Imovel, Comprador (PF/PJ), ContaBancaria creation.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from tests.fixtures.factories import (
    ContabilidadeFactory,
    ImobiliariaFactory,
    ImovelFactory,
    CompradorFactory,
    ContaBancariaFactory,
)


@pytest.mark.django_db
class TestContabilidadeModel:
    def test_create_contabilidade(self):
        c = ContabilidadeFactory.create()
        assert c.pk is not None
        assert c.nome.startswith('Contabilidade')
        assert c.ativo is True

    def test_str_representation(self):
        c = ContabilidadeFactory.create(nome='Contabil Alpha')
        assert str(c) == 'Contabil Alpha'

    def test_cnpj_unique(self):
        c1 = ContabilidadeFactory.create()
        c2 = ContabilidadeFactory.create()
        assert c1.cnpj != c2.cnpj


@pytest.mark.django_db
class TestImobiliariaModel:
    def test_create_pj(self):
        imob = ImobiliariaFactory.create(tipo_pessoa='PJ')
        assert imob.pk is not None
        assert imob.tipo_pessoa == 'PJ'
        assert imob.cnpj is not None

    def test_create_pf(self):
        imob = ImobiliariaFactory.create(tipo_pessoa='PF', cnpj=None, cpf='123.456.789-09')
        assert imob.pk is not None
        assert imob.tipo_pessoa == 'PF'
        assert imob.cpf == '123.456.789-09'

    def test_documento_property_pj(self):
        imob = ImobiliariaFactory.create(tipo_pessoa='PJ', cnpj='12.345.000/0001-00')
        assert imob.documento == '12.345.000/0001-00'

    def test_documento_property_pf(self):
        imob = ImobiliariaFactory.create(tipo_pessoa='PF', cnpj=None, cpf='123.456.789-09')
        assert imob.documento == '123.456.789-09'

    def test_missing_cnpj_for_pj_raises_error(self):
        imob = ImobiliariaFactory.build(tipo_pessoa='PJ', cnpj=None)
        with pytest.raises(ValidationError) as exc_info:
            imob.clean()
        assert 'cnpj' in exc_info.value.message_dict

    def test_missing_cpf_for_pf_raises_error(self):
        imob = ImobiliariaFactory.build(tipo_pessoa='PF', cnpj=None, cpf=None)
        with pytest.raises(ValidationError) as exc_info:
            imob.clean()
        assert 'cpf' in exc_info.value.message_dict

    def test_is_pf_property(self):
        imob_pf = ImobiliariaFactory.build(tipo_pessoa='PF')
        imob_pj = ImobiliariaFactory.build(tipo_pessoa='PJ')
        assert imob_pf.is_pf is True
        assert imob_pj.is_pf is False

    def test_cnpj_unique(self):
        imob1 = ImobiliariaFactory.create()
        imob2 = ImobiliariaFactory.create()
        assert imob1.cnpj != imob2.cnpj


@pytest.mark.django_db
class TestImovelModel:
    def test_create_imovel(self):
        imovel = ImovelFactory.create()
        assert imovel.pk is not None
        assert imovel.tipo == 'LOTE'
        assert imovel.area == Decimal('360.00')
        assert imovel.valor == Decimal('100000.00')
        assert imovel.disponivel is True
        assert imovel.ativo is True

    def test_str_with_loteamento(self):
        imovel = ImovelFactory.create(loteamento='Parque das Flores', identificacao='Lote 10')
        assert 'Parque das Flores' in str(imovel)
        assert 'Lote 10' in str(imovel)

    def test_str_without_loteamento(self):
        imovel = ImovelFactory.create(loteamento='', identificacao='Quadra B Lote 5')
        assert str(imovel) == 'Quadra B Lote 5'


@pytest.mark.django_db
class TestCompradorModel:
    def test_create_pf(self):
        comprador = CompradorFactory.create(tipo_pessoa='PF')
        assert comprador.pk is not None
        assert comprador.tipo_pessoa == 'PF'
        assert comprador.estado_civil == 'SOLTEIRO'

    def test_create_pj(self):
        comprador = CompradorFactory.create(tipo_pessoa='PJ', cpf=None, cnpj='12.345.678/0001-99')
        assert comprador.pk is not None
        assert comprador.tipo_pessoa == 'PJ'

    def test_str_pf_with_cpf(self):
        comprador = CompradorFactory.create(
            tipo_pessoa='PF', nome='João Silva', cpf='123.456.789-00'
        )
        s = str(comprador)
        assert 'João Silva' in s

    def test_ativo_default(self):
        comprador = CompradorFactory.create()
        assert comprador.ativo is True


@pytest.mark.django_db
class TestContaBancariaModel:
    def test_create_conta_bancaria(self):
        conta = ContaBancariaFactory.create()
        assert conta.pk is not None
        assert conta.banco == '001'
        assert conta.principal is True
        assert conta.ativo is True

    def test_only_one_principal(self):
        """Marking a second account as principal should unmark the first."""
        imobiliaria = ImobiliariaFactory.create()
        conta1 = ContaBancariaFactory.create(imobiliaria=imobiliaria, principal=True)
        conta2 = ContaBancariaFactory.create(imobiliaria=imobiliaria, principal=True)
        conta1.refresh_from_db()
        assert conta2.principal is True
        assert conta1.principal is False
