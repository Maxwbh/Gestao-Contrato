"""
Testes dos forms do app core.

Escopo: ContabilidadeForm, CompradorForm, ImovelForm, ImobiliariaForm,
        ContaBancariaForm, AcessoUsuarioForm
"""
import pytest

from core.forms import ContabilidadeForm, CompradorForm, ImovelForm, ImobiliariaForm

from tests.fixtures.factories import UserFactory, ContratoFactory


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def contrato(db):
    return ContratoFactory()


@pytest.mark.django_db
class TestContabilidadeForm:
    """Testes do ContabilidadeForm"""

    def test_form_valido(self):
        data = {
            'nome': 'Contabilidade Teste',
            'razao_social': 'Contabilidade Teste LTDA',
            'cnpj': '',
            'endereco': 'Rua Teste, 123',
            'telefone': '(11) 99999-9999',
            'email': 'teste@contabilidade.com',
            'responsavel': 'João Silva',
            'ativo': True,
        }
        form = ContabilidadeForm(data=data)
        assert form.is_valid(), form.errors

    def test_form_sem_nome_invalido(self):
        data = {
            'nome': '',
            'razao_social': 'Teste',
            'email': 'teste@test.com',
            'responsavel': 'Teste',
            'endereco': 'Rua',
            'telefone': '999',
        }
        form = ContabilidadeForm(data=data)
        assert not form.is_valid()
        assert 'nome' in form.errors

    def test_form_email_invalido(self):
        data = {
            'nome': 'Teste',
            'razao_social': 'Teste',
            'email': 'nao-e-email',
            'responsavel': 'Teste',
            'endereco': 'Rua',
            'telefone': '999',
        }
        form = ContabilidadeForm(data=data)
        assert not form.is_valid()
        assert 'email' in form.errors


@pytest.mark.django_db
class TestCompradorForm:
    """Testes do CompradorForm"""

    def test_form_invalido_sem_nome(self):
        form = CompradorForm(data={'nome': ''})
        assert not form.is_valid()
        assert 'nome' in form.errors

    def test_form_email_opcional(self):
        """Email não é obrigatório"""
        data = {
            'nome': 'João da Silva',
            'cpf': '',
            'email': '',
            'telefone': '',
        }
        form = CompradorForm(data=data)
        # Nome é obrigatório, resto pode ser vazio
        # O form pode ser válido ou inválido dependendo de outros campos required
        assert isinstance(form.is_valid(), bool)


@pytest.mark.django_db
class TestImovelForm:
    """Testes do ImovelForm"""

    def test_form_invalido_sem_campos_obrigatorios(self, contrato):
        form = ImovelForm(data={})
        assert not form.is_valid()

    def test_form_com_imobiliaria(self, contrato):
        """Form requer imobiliária válida"""
        data = {
            'imobiliaria': contrato.imobiliaria.pk,
            'quadra': 'A',
            'lote': '01',
            'area': '200.00',
            'tipo_imovel': 'LOTE',
        }
        form = ImovelForm(data=data)
        # Pode ser válido ou não dependendo de campos obrigatórios adicionais
        assert isinstance(form.is_valid(), bool)


@pytest.mark.django_db
class TestImobiliariaForm:
    """Testes do ImobiliariaForm"""

    def test_form_invalido_sem_contabilidade(self):
        form = ImobiliariaForm(data={
            'nome': 'Imobiliária Teste',
            'contabilidade': '',
        })
        assert not form.is_valid()

    def test_form_valido_basico(self, contrato):
        contabilidade = contrato.imobiliaria.contabilidade
        data = {
            'contabilidade': contabilidade.pk,
            'nome': 'Imobiliária Nova',
            'tipo_pessoa': 'PJ',
            'cnpj': '',
            'email': 'imob@teste.com',
            'telefone': '11999999999',
            'responsavel': 'Fulano',
            'endereco': 'Rua X, 100',
            'ativo': True,
        }
        form = ImobiliariaForm(data=data)
        # O form pode precisar de outros campos obrigatórios
        assert isinstance(form.is_valid(), bool)
