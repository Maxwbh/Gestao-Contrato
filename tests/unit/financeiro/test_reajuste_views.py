"""
Testes das views de reajuste do app financeiro.

Escopo: listar_reajustes, reajustes_pendentes, aplicar_reajuste_pagina,
        preview_reajuste_contrato, excluir_reajuste, aplicar_reajuste_lote,
        obter_indice_reajuste
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
class TestListarReajustes:
    """Testes da view listar_reajustes"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:listar_reajustes')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        """Retorna 200 mesmo sem reajustes"""
        response = client_logado.get(reverse('financeiro:listar_reajustes'))
        assert response.status_code == 200

    def test_paginacao(self, client_logado):
        response = client_logado.get(
            reverse('financeiro:listar_reajustes'),
            {'per_page': '10'}
        )
        assert response.status_code == 200

    def test_paginacao_invalida_usa_padrao(self, client_logado):
        response = client_logado.get(
            reverse('financeiro:listar_reajustes'),
            {'per_page': 'xyz'}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestReajustesPendentes:
    """Testes da view reajustes_pendentes"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:reajustes_pendentes')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        """Retorna 200 sem contratos com reajuste pendente"""
        response = client_logado.get(reverse('financeiro:reajustes_pendentes'))
        assert response.status_code == 200

    def test_contexto_tem_total_pendentes(self, client_logado):
        response = client_logado.get(reverse('financeiro:reajustes_pendentes'))
        assert response.status_code == 200
        assert 'total_pendentes' in response.context


@pytest.mark.django_db
class TestPreviewReajusteContrato:
    """Testes da view preview_reajuste_contrato"""

    def test_requer_autenticacao(self, client, contrato):
        url = reverse('financeiro:preview_reajuste', kwargs={'contrato_id': contrato.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_contrato_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:preview_reajuste', kwargs={'contrato_id': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404

    def test_sem_ciclo_pendente_retorna_json(self, client_logado, contrato):
        """Contrato recém-criado sem ciclo pendente retorna JSON informativo"""
        url = reverse('financeiro:preview_reajuste', kwargs={'contrato_id': contrato.pk})
        response = client_logado.get(url)
        # Pode retornar JSON com ciclo_pendente=None ou com dados
        assert response.status_code == 200
        data = response.json()
        assert 'sucesso' in data


@pytest.mark.django_db
class TestExcluirReajuste:
    """Testes da view excluir_reajuste"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:excluir_reajuste', kwargs={'pk': 1})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_reajuste_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:excluir_reajuste', kwargs={'pk': 999999})
        response = client_logado.post(url, {})
        assert response.status_code == 404


@pytest.mark.django_db
class TestAplicarReajusteLote:
    """Testes da view aplicar_reajuste_lote"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:aplicar_reajuste_lote')
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_get_nao_permitido(self, client_logado):
        """GET retorna 405 (require_POST)"""
        url = reverse('financeiro:aplicar_reajuste_lote')
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_post_sem_contratos_retorna_json(self, client_logado):
        """POST sem contratos selecionados retorna JSON"""
        url = reverse('financeiro:aplicar_reajuste_lote')
        response = client_logado.post(url, {'contrato_ids': []})
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.json()
            assert 'sucesso' in data or 'resultados' in data
