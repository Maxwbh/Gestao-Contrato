"""
Testes das views principais do app core.

Escopo: index, dashboard, setup, roadmap, pagina_dados_teste
"""
import pytest
from django.urls import reverse

from tests.fixtures.factories import UserFactory, ContratoFactory


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestIndexView:
    """Testes da view index"""

    def test_index_redireciona_ou_retorna_200(self, client):
        """Index pode redirecionar para login ou exibir landing page"""
        response = client.get(reverse('core:index'))
        assert response.status_code in (200, 302)

    def test_index_autenticado(self, client_logado):
        response = client_logado.get(reverse('core:index'))
        assert response.status_code in (200, 302)


@pytest.mark.django_db
class TestDashboardView:
    """Testes da view dashboard do core"""

    def test_requer_autenticacao(self, client):
        response = client.get(reverse('core:dashboard'))
        assert response.status_code in (302, 403)

    def test_retorna_200(self, client_logado):
        response = client_logado.get(reverse('core:dashboard'))
        assert response.status_code == 200

    def test_contexto_tem_dados(self, client_logado):
        response = client_logado.get(reverse('core:dashboard'))
        assert response.status_code == 200
        # Template renderizado sem erro
        assert response.context is not None


@pytest.mark.django_db
class TestSetupView:
    """Testes da view setup"""

    def test_retorna_200_sem_autenticacao(self, client):
        """Setup é acessível sem login (permite configuração inicial)"""
        response = client.get(reverse('core:setup'))
        assert response.status_code == 200

    def test_retorna_200_autenticado(self, client_logado):
        response = client_logado.get(reverse('core:setup'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestRoadmapView:
    """Testes da view roadmap"""

    def test_acesso_roadmap(self, client):
        """Roadmap pode ser público ou protegido"""
        response = client.get(reverse('core:roadmap'))
        assert response.status_code in (200, 302, 403)

    def test_retorna_200_autenticado(self, client_logado):
        response = client_logado.get(reverse('core:roadmap'))
        assert response.status_code == 200
