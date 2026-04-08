"""
Testes de integração — Notificações.

Cobre: listagem, configuração de e-mail, templates, disparo manual
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
class TestFluxoNotificacoes:
    """Fluxo básico de notificações"""

    def test_listar_notificacoes(self, client_logado):
        """Listagem de notificações carrega"""
        url = reverse('notificacoes:listar')
        resp = client_logado.get(url)
        assert resp.status_code == 200

    def test_listar_configuracoes_email(self, client_logado):
        """Listagem de configurações de e-mail carrega"""
        url = reverse('notificacoes:listar_config_email')
        resp = client_logado.get(url)
        assert resp.status_code == 200

    def test_notificar_inadimplente_parcela_paga_retorna_400(self, client_logado, contrato):
        """Tentativa de notificar parcela paga retorna 400"""
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        parcela.pago = True
        parcela.save()

        url = reverse('financeiro:notificar_inadimplente', kwargs={'pk': parcela.pk})
        resp = client_logado.post(url, {})
        assert resp.status_code == 400
        data = resp.json()
        assert not data['sucesso']
