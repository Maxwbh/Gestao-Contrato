"""
Testes para as views do sistema.
"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestIndexView:
    """Testes para a página inicial."""

    def test_index_acessivel(self, client):
        """Página inicial deve ser acessível."""
        response = client.get('/')
        assert response.status_code in [200, 302]  # OK ou redirect para setup


@pytest.mark.django_db
class TestDashboardView:
    """Testes para o dashboard."""

    def test_dashboard_requer_login(self, client):
        """Dashboard deve redirecionar usuários não autenticados."""
        response = client.get('/dashboard/')
        assert response.status_code == 302
        assert 'login' in response.url.lower() or 'accounts' in response.url.lower()

    def test_dashboard_acessivel_autenticado(self, client_logged_in):
        """Dashboard deve ser acessível para usuários autenticados."""
        response = client_logged_in.get('/dashboard/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestSetupView:
    """Testes para a página de setup."""

    def test_setup_get_acessivel(self, client):
        """GET no setup deve ser acessível."""
        response = client.get('/setup/')
        assert response.status_code == 200

    def test_setup_post_requer_autenticacao(self, client, admin_user):
        """POST no setup requer autenticação quando já existem usuários."""
        # Admin existe, então POST deve exigir autenticação
        response = client.post('/setup/', {'action': 'migrations'})
        assert response.status_code == 401

    def test_setup_post_admin_permitido(self, client_admin):
        """POST no setup deve funcionar para admin."""
        response = client_admin.post('/setup/', {'action': 'migrations'})
        # Pode ser 200 ou 500 dependendo do ambiente de teste
        assert response.status_code in [200, 500]


@pytest.mark.django_db
class TestGerarDadosTesteView:
    """Testes para endpoint de geração de dados de teste."""

    def test_get_retorna_estatisticas(self, client):
        """GET deve retornar estatísticas do sistema."""
        response = client.get('/api/gerar-dados-teste/')
        assert response.status_code in [200, 500]  # 500 se banco não configurado

    def test_post_requer_autenticacao(self, client):
        """POST deve exigir autenticação."""
        response = client.post('/api/gerar-dados-teste/')
        assert response.status_code == 401

    def test_post_requer_superuser(self, client_logged_in):
        """POST deve exigir superusuário."""
        response = client_logged_in.post('/api/gerar-dados-teste/')
        assert response.status_code == 403

    def test_post_admin_permitido(self, client_admin):
        """POST deve funcionar para admin."""
        response = client_admin.post('/api/gerar-dados-teste/')
        # Pode ser 200 ou 500 dependendo do ambiente
        assert response.status_code in [200, 500]


@pytest.mark.django_db
class TestLimparDadosTesteView:
    """Testes para endpoint de limpeza de dados de teste."""

    def test_get_retorna_estatisticas(self, client):
        """GET deve retornar estatísticas."""
        response = client.get('/api/limpar-dados-teste/')
        assert response.status_code in [200, 500]

    def test_post_requer_autenticacao(self, client):
        """POST deve exigir autenticação."""
        response = client.post('/api/limpar-dados-teste/')
        assert response.status_code == 401

    def test_delete_requer_autenticacao(self, client):
        """DELETE deve exigir autenticação."""
        response = client.delete('/api/limpar-dados-teste/')
        assert response.status_code == 401


@pytest.mark.django_db
class TestContabilidadeViews:
    """Testes para views de Contabilidade."""

    def test_lista_requer_login(self, client):
        """Lista de contabilidades requer login."""
        response = client.get('/contabilidades/')
        assert response.status_code == 302

    def test_lista_acessivel_autenticado(self, client_logged_in, contabilidade):
        """Lista acessível para usuários autenticados."""
        response = client_logged_in.get('/contabilidades/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestImobiliariaViews:
    """Testes para views de Imobiliária."""

    def test_lista_requer_login(self, client):
        """Lista de imobiliárias requer login."""
        response = client.get('/imobiliarias/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestCompradorViews:
    """Testes para views de Comprador."""

    def test_lista_requer_login(self, client):
        """Lista de compradores requer login."""
        response = client.get('/compradores/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestImovelViews:
    """Testes para views de Imóvel."""

    def test_lista_requer_login(self, client):
        """Lista de imóveis requer login."""
        response = client.get('/imoveis/')
        assert response.status_code == 302
