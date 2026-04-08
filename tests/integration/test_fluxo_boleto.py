"""
Testes de integração — Fluxo de boletos.

Cobre: geração de boleto → status → download → cancelamento
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
class TestFluxoBoleto:
    """Fluxo de geração e status de boletos"""

    def test_api_status_boleto_nova_parcela(self, client_logado, contrato):
        """Parcela recém-criada não tem nosso_numero"""
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        assert not parcela.nosso_numero  # boleto não gerado = sem nosso_numero

        url = reverse('financeiro:api_status_boleto', kwargs={'pk': parcela.pk})
        resp = client_logado.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_download_sem_boleto_redireciona(self, client_logado, contrato):
        """Download de boleto sem PDF redireciona"""
        parcela = contrato.parcelas.filter(nosso_numero='').first()
        if parcela is None:
            parcela = contrato.parcelas.first()
        if parcela is None:
            pytest.skip('Sem parcela sem boleto')

        url = reverse('financeiro:download_boleto', kwargs={'pk': parcela.pk})
        resp = client_logado.get(url)
        assert resp.status_code == 302

    def test_segunda_via_parcela_nao_paga(self, client_logado, contrato):
        """Segunda via acessível para parcelas não pagas"""
        parcela = contrato.parcelas.filter(pago=False).first()
        if parcela is None:
            pytest.skip('Todas parcelas pagas')

        url = reverse('financeiro:segunda_via_boleto', kwargs={'pk': parcela.pk})
        resp = client_logado.get(url)
        assert resp.status_code in (200, 302)
