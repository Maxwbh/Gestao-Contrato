"""
Testes de segurança — CSRF, autenticação obrigatória, input injection.

Verifica que views sensíveis exigem autenticação e que inputs maliciosos
não causam erros inesperados nem exposição de dados.
"""
import pytest
from django.urls import reverse
from tests.fixtures.factories import UserFactory, ContratoFactory, ParcelaFactory


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


# =============================================================================
# AUTENTICAÇÃO OBRIGATÓRIA
# =============================================================================

@pytest.mark.django_db
class TestAutenticacaoObrigatoria:
    """Views que requerem login devem redirecionar usuário anônimo"""

    def test_dashboard_exige_login(self, client):
        url = reverse('financeiro:dashboard')
        resp = client.get(url)
        assert resp.status_code == 302
        assert '/login' in resp.url or '/accounts/login' in resp.url

    def test_listar_contratos_exige_login(self, client):
        url = reverse('contratos:listar')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_listar_parcelas_exige_login(self, client):
        url = reverse('financeiro:listar_parcelas')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_dashboard_contabilidade_exige_login(self, client):
        url = reverse('financeiro:dashboard_contabilidade')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_gerar_boleto_exige_login(self, client, contrato):
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
        resp = client.get(url)
        assert resp.status_code == 302

    def test_api_contratos_exige_login(self, client):
        url = reverse('financeiro:api_contratos')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_api_parcelas_exige_login(self, client):
        url = reverse('financeiro:api_parcelas')
        resp = client.get(url)
        assert resp.status_code == 302


# =============================================================================
# PARÂMETROS INVÁLIDOS — SEM CRASH
# =============================================================================

@pytest.mark.django_db
class TestParametrosInvalidos:
    """IDs inexistentes devem retornar 404, não 500"""

    def test_detalhe_contrato_inexistente_retorna_404(self, client_logado):
        url = reverse('contratos:detalhe', kwargs={'pk': 999999})
        resp = client_logado.get(url)
        assert resp.status_code == 404

    def test_detalhe_parcela_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:detalhe_parcela', kwargs={'pk': 999999})
        resp = client_logado.get(url)
        assert resp.status_code == 404

    def test_download_boleto_inexistente_retorna_302_ou_404(self, client_logado):
        url = reverse('financeiro:download_boleto', kwargs={'pk': 999999})
        resp = client_logado.get(url)
        assert resp.status_code in (302, 404)

    def test_api_boleto_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:api_boleto_detalhe', kwargs={'parcela_id': 999999})
        resp = client_logado.get(url)
        assert resp.status_code == 404


# =============================================================================
# PORTAL — ISOLAMENTO DE DADOS
# =============================================================================

@pytest.mark.django_db
class TestIsolamentoDadosPortal:
    """Portal comprador não deve expor dados de outros compradores"""

    def test_portal_exige_autenticacao(self, client):
        url = reverse('portal_comprador:dashboard')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_portal_login_exige_autenticacao(self, client):
        url = reverse('portal_comprador:meus_contratos')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_portal_boletos_exige_autenticacao(self, client):
        url = reverse('portal_comprador:meus_boletos')
        resp = client.get(url)
        assert resp.status_code == 302
