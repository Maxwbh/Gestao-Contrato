"""
Testes para os modelos do sistema.
"""
import pytest
from decimal import Decimal
from datetime import date


@pytest.mark.django_db
class TestContabilidade:
    """Testes para o modelo Contabilidade."""

    def test_criar_contabilidade(self, contabilidade):
        """Deve criar contabilidade com sucesso."""
        assert contabilidade.pk is not None
        assert contabilidade.nome is not None
        assert contabilidade.ativo is True

    def test_str_representation(self, contabilidade):
        """String representation deve retornar o nome."""
        assert str(contabilidade) == contabilidade.nome


@pytest.mark.django_db
class TestImobiliaria:
    """Testes para o modelo Imobiliaria."""

    def test_criar_imobiliaria(self, imobiliaria):
        """Deve criar imobiliária com sucesso."""
        assert imobiliaria.pk is not None
        assert imobiliaria.nome is not None

    def test_imobiliaria_pertence_contabilidade(self, imobiliaria, contabilidade):
        """Imobiliária deve pertencer a uma contabilidade."""
        assert imobiliaria.contabilidade == contabilidade

    def test_str_representation(self, imobiliaria):
        """String representation deve retornar o nome."""
        assert str(imobiliaria) == imobiliaria.nome


@pytest.mark.django_db
class TestComprador:
    """Testes para o modelo Comprador."""

    def test_criar_comprador_pf(self, comprador_pf):
        """Deve criar comprador pessoa física."""
        assert comprador_pf.pk is not None
        assert comprador_pf.tipo_pessoa == 'PF'
        assert comprador_pf.nome == 'João da Silva'

    def test_criar_comprador_pj(self, comprador_pj):
        """Deve criar comprador pessoa jurídica."""
        assert comprador_pj.pk is not None
        assert comprador_pj.tipo_pessoa == 'PJ'

    def test_str_representation(self, comprador_pf):
        """String representation deve incluir o nome."""
        assert 'João da Silva' in str(comprador_pf)


@pytest.mark.django_db
class TestImovel:
    """Testes para o modelo Imovel."""

    def test_criar_imovel(self, imovel):
        """Deve criar imóvel com sucesso."""
        assert imovel.pk is not None
        assert imovel.tipo == 'LOTE'
        assert imovel.valor == Decimal('100000.00')

    def test_imovel_disponivel_por_padrao(self, imovel):
        """Imóvel deve estar disponível por padrão."""
        assert imovel.disponivel is True

    def test_str_representation(self, imovel):
        """String representation deve ser informativa."""
        assert imovel.identificacao in str(imovel)


@pytest.mark.django_db
class TestContrato:
    """Testes para o modelo Contrato."""

    def test_criar_contrato(self, contrato):
        """Deve criar contrato com sucesso."""
        assert contrato.pk is not None
        assert contrato.numero_contrato is not None
        assert contrato.valor_total is not None

    def test_contrato_vincula_imovel_comprador(self, contrato, imovel, comprador_pf):
        """Contrato deve vincular imóvel e comprador."""
        # Verify contrato has imovel and comprador linked
        assert contrato.imovel is not None
        assert contrato.comprador is not None

    def test_contrato_calcula_valor_financiado(self, contrato):
        """Valor financiado = valor_total - valor_entrada."""
        valor_financiado = contrato.valor_total - contrato.valor_entrada
        assert valor_financiado == contrato.valor_financiado

    def test_str_representation(self, contrato):
        """String representation deve incluir número do contrato."""
        assert contrato.numero_contrato in str(contrato)


@pytest.mark.django_db
class TestParcela:
    """Testes para o modelo Parcela."""

    def test_criar_parcela(self, parcela):
        """Deve criar parcela com sucesso."""
        assert parcela.pk is not None
        assert parcela.numero_parcela is not None
        assert parcela.valor_original is not None

    def test_parcela_status_pendente(self, parcela):
        """Parcela deve iniciar como pendente."""
        # Parcel status is stored as pago=False
        assert parcela.pago is False

    def test_parcela_pertence_contrato(self, parcela, contrato):
        """Parcela deve pertencer a um contrato."""
        assert parcela.contrato is not None

    def test_parcela_vencimento_futuro(self, parcela):
        """Data de vencimento deve estar no futuro."""
        assert parcela.data_vencimento > date.today()


@pytest.mark.django_db
class TestRelacionamentos:
    """Testes para relacionamentos entre modelos."""

    def test_cascata_contabilidade_imobiliaria(self, db, contabilidade):
        """Imobiliária pertence a contabilidade (FK protegida)."""
        from core.models import Imobiliaria
        from django.db.models import ProtectedError

        imob = Imobiliaria.objects.create(
            contabilidade=contabilidade,
            nome='Imob Temp',
            cnpj='12.345.678/0001-90',
            telefone='(31) 3333-0000',
            email='imob@temp.com',
            responsavel_financeiro='Responsavel Temp',
        )
        imob_id = imob.pk

        # FK is PROTECT, so deleting contabilidade with imobiliarias raises ProtectedError
        with pytest.raises(ProtectedError):
            contabilidade.delete()

        # Imobiliaria still exists (not deleted)
        assert Imobiliaria.objects.filter(pk=imob_id).exists()

    def test_imovel_imobiliaria_relacionamento(self, imovel, imobiliaria):
        """Imóvel deve estar relacionado à imobiliária."""
        assert imovel.imobiliaria == imobiliaria
        assert imovel in imobiliaria.imoveis.all()
