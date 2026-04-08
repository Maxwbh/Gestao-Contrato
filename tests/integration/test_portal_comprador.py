"""
Testes de integração — Portal do Comprador.

Cobre: login portal → dashboard → contratos → boletos
"""
import pytest
from django.urls import reverse

from tests.fixtures.factories import UserFactory, ContratoFactory


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def contrato(db):
    return ContratoFactory()


@pytest.mark.django_db
class TestFluxoPortalComprador:
    """Fluxo do portal do comprador"""

    def test_login_portal_unauthenticated(self, client):
        """Página de login do portal carrega"""
        url = reverse('portal_comprador:login')
        resp = client.get(url)
        assert resp.status_code == 200

    def test_dashboard_portal_requer_autenticacao(self, client):
        """Dashboard do portal requer autenticação"""
        url = reverse('portal_comprador:dashboard')
        resp = client.get(url)
        assert resp.status_code in (302, 403)

    def test_meus_contratos_requer_autenticacao(self, client):
        """Lista de contratos do portal requer autenticação"""
        url = reverse('portal_comprador:meus_contratos')
        resp = client.get(url)
        assert resp.status_code in (302, 403)
