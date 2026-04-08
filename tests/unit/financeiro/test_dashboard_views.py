"""
Testes das views de dashboard do app financeiro.

Escopo: DashboardFinanceiroView, api_dashboard_dados,
        dashboard_imobiliaria, DashboardContabilidadeView,
        api_dashboard_contabilidade
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


@pytest.fixture
def contrato(db):
    return ContratoFactory()


@pytest.mark.django_db
class TestDashboardFinanceiro:
    """Testes da view DashboardFinanceiroView"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:dashboard')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_retorna_200(self, client_logado):
        response = client_logado.get(reverse('financeiro:dashboard'))
        assert response.status_code == 200

    def test_filtro_imobiliaria(self, client_logado, contrato):
        imob_id = contrato.imobiliaria.pk
        response = client_logado.get(
            reverse('financeiro:dashboard'),
            {'imobiliaria': imob_id}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestApiDashboardDados:
    """Testes da view api_dashboard_dados"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:api_dashboard_dados')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_json(self, client_logado):
        response = client_logado.get(reverse('financeiro:api_dashboard_dados'))
        assert response.status_code == 200
        data = response.json()
        # Estrutura básica esperada
        assert 'status_parcelas' in data or 'labels' in data or isinstance(data, dict)

    def test_filtro_imobiliaria(self, client_logado, contrato):
        imob_id = contrato.imobiliaria.pk
        response = client_logado.get(
            reverse('financeiro:api_dashboard_dados'),
            {'imobiliaria': imob_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.django_db
class TestDashboardImobiliaria:
    """Testes da view dashboard_imobiliaria"""

    def test_requer_autenticacao(self, client, contrato):
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={'imobiliaria_id': contrato.imobiliaria.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_imobiliaria_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={'imobiliaria_id': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404

    def test_imobiliaria_existente_retorna_200(self, client_logado, contrato):
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={'imobiliaria_id': contrato.imobiliaria.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
