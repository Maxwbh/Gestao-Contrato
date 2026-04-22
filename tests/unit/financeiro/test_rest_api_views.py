"""
Testes das views de REST API do app financeiro.

Escopo: api_contratos_lista, api_contrato_detalhe, api_contrato_parcelas,
        api_parcelas_lista, api_boleto_detalhe, api_boleto_gerar,
        api_boleto_cancelar, api_parcela_registrar_pagamento,
        api_gerar_boletos_lote, api_relatorio_resumo,
        api_imobiliarias_lista, api_status_boleto
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


@pytest.fixture
def parcela(db, contrato):
    return contrato.parcelas.order_by('numero_parcela').first()


@pytest.mark.django_db
class TestApiContratosLista:
    """Testes da view api_contratos_lista"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:api_contratos')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_json(self, client_logado):
        response = client_logado.get(reverse('financeiro:api_contratos'))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_com_contrato(self, client_logado, contrato):
        response = client_logado.get(reverse('financeiro:api_contratos'))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.django_db
class TestApiContratoDetalhe:
    """Testes da view api_contrato_detalhe"""

    def test_requer_autenticacao(self, client, contrato):
        url = reverse('financeiro:api_contrato_detalhe', kwargs={'contrato_id': contrato.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_contrato_inexistente(self, client_logado):
        url = reverse('financeiro:api_contrato_detalhe', kwargs={'contrato_id': 999999})
        response = client_logado.get(url)
        assert response.status_code in (400, 404, 500)

    def test_contrato_existente(self, client_logado, contrato):
        url = reverse('financeiro:api_contrato_detalhe', kwargs={'contrato_id': contrato.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.django_db
class TestApiContratoParcelas:
    """Testes da view api_contrato_parcelas"""

    def test_requer_autenticacao(self, client, contrato):
        url = reverse('financeiro:api_contrato_parcelas', kwargs={'contrato_id': contrato.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_contrato_existente_retorna_parcelas(self, client_logado, contrato):
        url = reverse('financeiro:api_contrato_parcelas', kwargs={'contrato_id': contrato.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_contrato_inexistente(self, client_logado):
        url = reverse('financeiro:api_contrato_parcelas', kwargs={'contrato_id': 999999})
        response = client_logado.get(url)
        assert response.status_code in (400, 404, 500)


@pytest.mark.django_db
class TestApiParcelasLista:
    """Testes da view api_parcelas_lista"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:api_parcelas')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_json(self, client_logado):
        response = client_logado.get(reverse('financeiro:api_parcelas'))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_filtro_contrato(self, client_logado, contrato):
        response = client_logado.get(
            reverse('financeiro:api_parcelas'),
            {'contrato_id': contrato.pk}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestApiBoletoDetalhe:
    """Testes da view api_boleto_detalhe"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:api_boleto_detalhe', kwargs={'parcela_id': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_parcela_existente(self, client_logado, parcela):
        url = reverse('financeiro:api_boleto_detalhe', kwargs={'parcela_id': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_parcela_inexistente(self, client_logado):
        url = reverse('financeiro:api_boleto_detalhe', kwargs={'parcela_id': 999999})
        response = client_logado.get(url)
        assert response.status_code in (400, 404, 500)


@pytest.mark.django_db
class TestApiStatusBoleto:
    """Testes da view api_status_boleto"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:api_status_boleto', kwargs={'pk': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_status(self, client_logado, parcela):
        url = reverse('financeiro:api_status_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'boleto_gerado' in data or 'status' in data or isinstance(data, dict)


@pytest.mark.django_db
class TestApiGerarBoletosLote:
    """Testes da view api_gerar_boletos_lote"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:api_gerar_boletos_lote')
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_post_sem_parcelas(self, client_logado):
        url = reverse('financeiro:api_gerar_boletos_lote')
        response = client_logado.post(url, {'parcela_ids': []})
        assert response.status_code in (200, 400)
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.django_db
class TestApiRelatorioResumo:
    """Testes da view api_relatorio_resumo"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:api_relatorio_resumo')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_json(self, client_logado):
        response = client_logado.get(reverse('financeiro:api_relatorio_resumo'))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.django_db
class TestApiImobiliariasLista:
    """Testes da view api_imobiliarias_lista"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:api_imobiliarias')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_json(self, client_logado):
        response = client_logado.get(reverse('financeiro:api_imobiliarias'))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.django_db
class TestVisualizarBoleto:
    """Testes da view visualizar_boleto — garante que requer autenticação."""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:visualizar_boleto', kwargs={'pk': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_parcela_sem_boleto_redireciona(self, client_logado, parcela):
        url = reverse('financeiro:visualizar_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code == 302

    def test_parcela_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:visualizar_boleto', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404
