"""
Testes para os modelos do sistema.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.db import IntegrityError


@pytest.mark.django_db
class TestContabilidade:
    """Testes para o modelo Contabilidade."""

    def test_criar_contabilidade(self, contabilidade):
        """Deve criar contabilidade com sucesso."""
        assert contabilidade.pk is not None
        assert contabilidade.nome == 'Contabilidade Teste'
        assert contabilidade.ativo is True

    def test_str_representation(self, contabilidade):
        """String representation deve retornar o nome."""
        assert str(contabilidade) == 'Contabilidade Teste'


@pytest.mark.django_db
class TestImobiliaria:
    """Testes para o modelo Imobiliaria."""

    def test_criar_imobiliaria(self, imobiliaria):
        """Deve criar imobiliária com sucesso."""
        assert imobiliaria.pk is not None
        assert imobiliaria.nome == 'Imobiliária Teste'

    def test_imobiliaria_pertence_contabilidade(self, imobiliaria, contabilidade):
        """Imobiliária deve pertencer a uma contabilidade."""
        assert imobiliaria.contabilidade == contabilidade

    def test_str_representation(self, imobiliaria):
        """String representation deve retornar o nome."""
        assert str(imobiliaria) == 'Imobiliária Teste'


@pytest.mark.django_db
class TestComprador:
    """Testes para o modelo Comprador."""

    def test_criar_comprador_pf(self, comprador_pf):
        """Deve criar comprador pessoa física."""
        assert comprador_pf.pk is not None
        assert comprador_pf.tipo == 'PF'
        assert comprador_pf.nome == 'João da Silva'

    def test_criar_comprador_pj(self, comprador_pj):
        """Deve criar comprador pessoa jurídica."""
        assert comprador_pj.pk is not None
        assert comprador_pj.tipo == 'PJ'

    def test_str_representation(self, comprador_pf):
        """String representation deve retornar o nome."""
        assert str(comprador_pf) == 'João da Silva'


@pytest.mark.django_db
class TestImovel:
    """Testes para o modelo Imovel."""

    def test_criar_imovel(self, imovel):
        """Deve criar imóvel com sucesso."""
        assert imovel.pk is not None
        assert imovel.tipo == 'LOTE'
        assert imovel.valor_venda == Decimal('150000.00')

    def test_imovel_disponivel_por_padrao(self, imovel):
        """Imóvel deve estar disponível por padrão."""
        assert imovel.disponivel is True

    def test_str_representation(self, imovel):
        """String representation deve ser informativa."""
        assert 'Lote 001' in str(imovel)


@pytest.mark.django_db
class TestContrato:
    """Testes para o modelo Contrato."""

    def test_criar_contrato(self, contrato):
        """Deve criar contrato com sucesso."""
        assert contrato.pk is not None
        assert contrato.numero == 'CT-001'
        assert contrato.valor_total == Decimal('150000.00')

    def test_contrato_vincula_imovel_comprador(self, contrato, imovel, comprador_pf):
        """Contrato deve vincular imóvel e comprador."""
        assert contrato.imovel == imovel
        assert contrato.comprador == comprador_pf

    def test_contrato_calcula_valor_financiado(self, contrato):
        """Valor financiado = valor_total - valor_entrada."""
        valor_financiado = contrato.valor_total - contrato.valor_entrada
        assert valor_financiado == Decimal('120000.00')

    def test_str_representation(self, contrato):
        """String representation deve incluir número do contrato."""
        assert 'CT-001' in str(contrato)


@pytest.mark.django_db
class TestParcela:
    """Testes para o modelo Parcela."""

    def test_criar_parcela(self, parcela):
        """Deve criar parcela com sucesso."""
        assert parcela.pk is not None
        assert parcela.numero_parcela == 1
        assert parcela.valor_original == Decimal('1000.00')

    def test_parcela_status_pendente(self, parcela):
        """Parcela deve iniciar como pendente."""
        assert parcela.status == 'PENDENTE'

    def test_parcela_pertence_contrato(self, parcela, contrato):
        """Parcela deve pertencer a um contrato."""
        assert parcela.contrato == contrato

    def test_parcela_vencimento_futuro(self, parcela):
        """Data de vencimento deve estar no futuro."""
        assert parcela.data_vencimento > date.today()


@pytest.mark.django_db
class TestRelacionamentos:
    """Testes para relacionamentos entre modelos."""

    def test_cascata_contabilidade_imobiliaria(self, db, contabilidade):
        """Excluir contabilidade deve excluir imobiliárias."""
        from core.models import Imobiliaria

        imob = Imobiliaria.objects.create(
            contabilidade=contabilidade,
            nome='Imob Temp',
            cnpj='12.345.678/0001-90'
        )
        imob_id = imob.pk

        contabilidade.delete()

        assert not Imobiliaria.objects.filter(pk=imob_id).exists()

    def test_imovel_imobiliaria_relacionamento(self, imovel, imobiliaria):
        """Imóvel deve estar relacionado à imobiliária."""
        assert imovel.imobiliaria == imobiliaria
        assert imovel in imobiliaria.imoveis.all()
