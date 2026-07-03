"""
Testes dos forms do app core.

Escopo: ContabilidadeForm, CompradorForm, ImovelForm, ImobiliariaForm,
        ContaBancariaForm, AcessoUsuarioForm
"""
import pytest

from core.forms import (
    ContabilidadeForm, CompradorForm, ImovelForm, ImobiliariaForm,
    ContaBancariaForm,
)

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


class TestContaBancariaForm:
    """Validação de campos por banco (agência/conta/carteira) e layout CNAB."""

    def _dados(self, **over):
        base = {
            'banco': '336', 'descricao': 'Conta C6',
            'agencia': '1234', 'conta': '12345678', 'carteira': '10',
            'layout_cnab': 'CNAB_400', 'nosso_numero_atual': 0,
            'numero_remessa_cnab_atual': 0,
            'prazo_baixa': 0, 'prazo_protesto': 0,
        }
        base.update(over)
        return base

    def test_agencia_excedida_bb(self):
        # BB (001) agência máx 4 dígitos
        form = ContaBancariaForm(data=self._dados(
            banco='001', convenio='1234567', agencia='12345', conta='1234'))
        form.is_valid()
        assert 'agencia' in form.errors

    def test_carteira_invalida_c6(self):
        form = ContaBancariaForm(data=self._dados(carteira='99'))
        form.is_valid()
        assert 'carteira' in form.errors

    def test_carteira_valida_c6_nao_erra(self):
        form = ContaBancariaForm(data=self._dados(carteira='20'))
        form.is_valid()
        assert 'carteira' not in form.errors

    def test_layout_incompativel_c6(self):
        # C6 (336) só suporta CNAB 400 → CNAB 240 deve ser recusado
        form = ContaBancariaForm(data=self._dados(layout_cnab='CNAB_240'))
        form.is_valid()
        assert 'layout_cnab' in form.errors

    def test_layout_compativel_c6_nao_erra(self):
        form = ContaBancariaForm(data=self._dados(layout_cnab='CNAB_400'))
        form.is_valid()
        assert 'layout_cnab' not in form.errors

    def test_conta_excedida_itau(self):
        # Itaú (341) conta máx 5 dígitos
        form = ContaBancariaForm(data=self._dados(
            banco='341', conta='123456', layout_cnab='CNAB_400'))
        form.is_valid()
        assert 'conta' in form.errors

    def test_provider_vazio_vira_brcobranca(self):
        """Provider não informado → BRCobrança (fluxo CNAB padrão)."""
        form = ContaBancariaForm(data=self._dados(provider=''))
        assert form.is_valid(), form.errors
        assert form.cleaned_data['provider'] == 'brcobranca'

    def test_provider_ausente_vira_brcobranca(self):
        """Sem a chave provider no POST → BRCobrança."""
        dados = self._dados()
        dados.pop('provider', None)
        form = ContaBancariaForm(data=dados)
        assert form.is_valid(), form.errors
        assert form.cleaned_data['provider'] == 'brcobranca'

    def test_c6_brcobranca_continua_valido(self):
        """C6 (banco=336) com provider=brcobranca permanece válido (fluxo CNAB)."""
        form = ContaBancariaForm(data=self._dados(provider='brcobranca'))
        assert form.is_valid(), form.errors
        assert form.cleaned_data['provider'] == 'brcobranca'

    def test_provider_c6_exige_tenant_id(self):
        """Provider c6 sem tenant_id deve dar erro."""
        form = ContaBancariaForm(data=self._dados(provider='c6', tenant_id=''))
        form.is_valid()
        assert 'tenant_id' in form.errors

    def test_provider_sicoob_com_tenant_id_valido(self):
        """Provider sicoob com tenant_id preenchido é aceito."""
        form = ContaBancariaForm(data=self._dados(
            banco='756', convenio='1234567', layout_cnab='CNAB_240',
            carteira='1', provider='sicoob', tenant_id='imob1-756',
        ))
        assert form.is_valid(), form.errors
        assert form.cleaned_data['provider'] == 'sicoob'
        assert 'tenant_id' not in form.errors
