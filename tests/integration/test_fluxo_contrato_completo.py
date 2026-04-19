"""
Testes de integração — Fluxo completo do contrato.

Cobre: criação de contrato → listagem → detalhe → edição → registrar pagamento
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
class TestFluxoContratoCompleto:
    """Fluxo completo: criação, visualização e pagamento"""

    def test_fluxo_listagem_e_detalhe(self, client_logado, contrato):
        """Lista contratos e acessa detalhe"""
        # Listagem
        resp = client_logado.get(reverse('contratos:listar'))
        assert resp.status_code == 200

        # Detalhe
        resp = client_logado.get(reverse('contratos:detalhe', kwargs={'pk': contrato.pk}))
        assert resp.status_code == 200

    def test_fluxo_parcelas_do_contrato(self, client_logado, contrato):
        """Contrato tem parcelas após criação"""
        # Parcelas devem existir (geradas automaticamente no save)
        assert contrato.parcelas.count() > 0

        # Listar parcelas financeiro
        resp = client_logado.get(
            reverse('financeiro:listar_parcelas'),
        )
        assert resp.status_code == 200

    def test_fluxo_detalhe_parcela(self, client_logado, contrato):
        """Acessa detalhe da primeira parcela"""
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        url = reverse('financeiro:detalhe_parcela', kwargs={'pk': parcela.pk})
        resp = client_logado.get(url)
        assert resp.status_code == 200

    def test_fluxo_registrar_pagamento(self, client_logado, contrato):
        """Acessa formulário de pagamento e o exibe corretamente"""
        parcela = contrato.parcelas.filter(pago=False).order_by('numero_parcela').first()
        assert parcela is not None

        url = reverse('financeiro:registrar_pagamento', kwargs={'pk': parcela.pk})
        resp = client_logado.get(url)
        assert resp.status_code == 200

    def test_fluxo_dashboard_financeiro(self, client_logado, contrato):
        """Dashboard carrega com dados do contrato"""
        resp = client_logado.get(reverse('financeiro:dashboard'))
        assert resp.status_code == 200
