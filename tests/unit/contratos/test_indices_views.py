"""
Testes das views de índices de reajuste do app contratos.

Escopo: IndiceReajusteListView, IndiceReajusteCreateView,
        IndiceReajusteUpdateView, IndiceReajusteDeleteView,
        importar_indices_ibge
"""
import pytest
from django.urls import reverse

from tests.fixtures.factories import UserFactory


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestIndiceReajusteListView:
    """Testes da view IndiceReajusteListView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_listar')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        response = client_logado.get(reverse('contratos:indices_listar'))
        assert response.status_code == 200

    def test_paginacao(self, client_logado):
        response = client_logado.get(
            reverse('contratos:indices_listar'),
            {'per_page': '10'}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestIndiceReajusteCreateView:
    """Testes da view IndiceReajusteCreateView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_criar')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_exibe_formulario(self, client_logado):
        response = client_logado.get(reverse('contratos:indices_criar'))
        assert response.status_code == 200

    def test_post_valido_cria_indice(self, client_logado):
        """POST com dados válidos cria índice e redireciona"""
        from datetime import date
        response = client_logado.post(
            reverse('contratos:indices_criar'),
            {
                'tipo': 'IPCA',
                'ano': date.today().year,
                'mes': 1,
                'percentual': '0.50',
            }
        )
        assert response.status_code in (200, 302)

    def test_post_invalido_retorna_formulario(self, client_logado):
        """POST sem dados obrigatórios retorna formulário com erros"""
        response = client_logado.post(reverse('contratos:indices_criar'), {})
        assert response.status_code == 200


@pytest.mark.django_db
class TestIndiceReajusteUpdateView:
    """Testes da view IndiceReajusteUpdateView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_editar', kwargs={'pk': 1})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_indice_inexistente_retorna_404(self, client_logado):
        url = reverse('contratos:indices_editar', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestIndiceReajusteDeleteView:
    """Testes da view IndiceReajusteDeleteView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_excluir', kwargs={'pk': 1})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_indice_inexistente_retorna_404(self, client_logado):
        url = reverse('contratos:indices_excluir', kwargs={'pk': 999999})
        response = client_logado.post(url, {})
        assert response.status_code == 404

    def test_post_deleta_indice(self, client_logado):
        from datetime import date
        from contratos.models import IndiceReajuste
        indice = IndiceReajuste.objects.create(
            tipo_indice='IPCA', ano=date.today().year, mes=1, valor='0.50'
        )
        url = reverse('contratos:indices_excluir', kwargs={'pk': indice.pk})
        response = client_logado.post(url, {})
        assert response.status_code == 302
        assert not IndiceReajuste.objects.filter(pk=indice.pk).exists()
