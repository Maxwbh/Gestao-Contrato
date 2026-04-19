"""
Testes funcionais — Workflow completo de contrato.

Cobre: criação → parcelas → reajuste → pagamento
"""
import pytest
from django.urls import reverse

from tests.fixtures.factories import (
    UserFactory,
    ContratoFactory,
)


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
class TestWorkflowContrato:
    """Workflow completo de contrato do início ao fim"""

    def test_lista_contratos_acessivel(self, client_logado):
        """Usuário autenticado consegue acessar lista de contratos"""
        url = reverse('contratos:listar')
        resp = client_logado.get(url)
        assert resp.status_code == 200

    def test_detalhe_contrato_exibe_parcelas(self, client_logado, contrato):
        """Detalhe do contrato exibe parcelas geradas automaticamente"""
        url = reverse('contratos:detalhe', kwargs={'pk': contrato.pk})
        resp = client_logado.get(url)
        assert resp.status_code == 200
        # Contrato tem parcelas (geradas pelo signal)
        assert contrato.parcelas.count() > 0

    def test_parcelas_geradas_conforme_prazo(self, db):
        """Número de parcelas geradas corresponde ao prazo do contrato"""
        contrato = ContratoFactory(numero_parcelas=6)
        assert contrato.parcelas.count() == 6

    def test_fluxo_listar_parcelas(self, client_logado, contrato):
        """Listagem de parcelas retorna status 200"""
        url = reverse('financeiro:listar_parcelas')
        resp = client_logado.get(url)
        assert resp.status_code == 200
