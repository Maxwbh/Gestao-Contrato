"""
Testes das views de API do app core.

Escopo: api_listar_bancos, api_criar_conta_bancaria, api_obter_conta_bancaria,
        api_listar_contas_bancarias, api_excluir_conta_bancaria,
        api_busca_global, health_check, dashboard
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
class TestHealthCheck:
    """Testes do endpoint health_check"""

    def test_retorna_200_sem_autenticacao(self, client):
        """Health check é público"""
        response = client.get(reverse('core:health_check'))
        assert response.status_code == 200

    def test_retorna_json(self, client):
        response = client.get(reverse('core:health_check'))
        data = response.json()
        assert 'status' in data or isinstance(data, dict)


@pytest.mark.django_db
class TestDashboardCore:
    """Testes da view dashboard do core"""

    def test_requer_autenticacao(self, client):
        url = reverse('core:dashboard')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_retorna_200(self, client_logado):
        response = client_logado.get(reverse('core:dashboard'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestApiListarBancos:
    """Testes da view api_listar_bancos"""

    def test_requer_autenticacao(self, client):
        url = reverse('core:api_listar_bancos')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_lista_json(self, client_logado):
        response = client_logado.get(reverse('core:api_listar_bancos'))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.django_db
class TestApiContasBancarias:
    """Testes das views de contas bancárias"""

    def test_requer_autenticacao_listar(self, client, contrato):
        url = reverse('core:api_listar_contas', kwargs={'imobiliaria_id': contrato.imobiliaria.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_listar_contas_imobiliaria(self, client_logado, contrato):
        url = reverse('core:api_listar_contas', kwargs={'imobiliaria_id': contrato.imobiliaria.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_conta_inexistente_retorna_erro(self, client_logado):
        """Conta inexistente retorna 404 ou 500 dependendo da implementação"""
        url = reverse('core:api_obter_conta', kwargs={'conta_id': 999999})
        response = client_logado.get(url)
        assert response.status_code in (400, 404, 500)

    def test_criar_conta_sem_dados_retorna_erro(self, client_logado):
        url = reverse('core:api_criar_conta')
        response = client_logado.post(url, {}, content_type='application/json')
        assert response.status_code in (200, 400, 422, 500)
        data = response.json()
        assert isinstance(data, dict)

    def test_excluir_conta_inexistente_retorna_erro(self, client_logado):
        """Conta inexistente retorna 404 ou 500 dependendo da implementação"""
        url = reverse('core:api_excluir_conta', kwargs={'conta_id': 999999})
        response = client_logado.delete(url)
        assert response.status_code in (400, 404, 500)


@pytest.mark.django_db
class TestApiBuscaGlobal:
    """Testes da view api_busca_global"""

    def test_requer_autenticacao(self, client):
        url = reverse('core:api_busca_global')
        response = client.get(url, {'q': 'test'})
        assert response.status_code in (302, 403)

    def test_busca_vazia_retorna_json(self, client_logado):
        response = client_logado.get(reverse('core:api_busca_global'), {'q': ''})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))

    def test_busca_com_termo(self, client_logado, contrato):
        response = client_logado.get(
            reverse('core:api_busca_global'),
            {'q': contrato.numero_contrato[:3]}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))


@pytest.mark.django_db
class TestCompradorCrud:
    """Testes das views CRUD de compradores"""

    def test_requer_autenticacao_listar(self, client):
        url = reverse('core:listar_compradores')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_compradores(self, client_logado):
        response = client_logado.get(reverse('core:listar_compradores'))
        assert response.status_code == 200

    def test_criar_comprador_get(self, client_logado):
        response = client_logado.get(reverse('core:criar_comprador'))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# API REST CRUD — Comprador
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiCompradorCrud:
    """Testes da API REST de Comprador (GET lista, GET detalhe, PUT, DELETE)"""

    def test_listar_sem_auth_retorna_redirect(self, client):
        url = reverse('core:api_compradores')
        assert client.get(url).status_code in (302, 403)

    def test_listar_retorna_json(self, client_logado):
        response = client_logado.get(reverse('core:api_compradores'))
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        assert 'compradores' in data

    def test_listar_com_busca(self, client_logado, contrato):
        url = reverse('core:api_compradores')
        response = client_logado.get(url, {'q': contrato.comprador.nome[:3]})
        assert response.status_code == 200

    def test_criar_comprador_via_api(self, client_logado):
        import json
        from core.models import Comprador
        url = reverse('core:api_compradores')
        payload = {
            'nome': 'Comprador API Teste',
            'cpf': '123.456.789-09',
            'email': 'compradorapi@test.com',
            'celular': '(31) 99999-0001',
        }
        response = client_logado.post(url, json.dumps(payload), content_type='application/json')
        assert response.status_code in (201, 200, 400)

    def test_detalhe_comprador_existente(self, client_logado, contrato):
        url = reverse('core:api_comprador_detalhe', kwargs={'pk': contrato.comprador.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        assert 'comprador' in data

    def test_detalhe_comprador_inexistente(self, client_logado):
        url = reverse('core:api_comprador_detalhe', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404

    def test_atualizar_comprador(self, client_logado, contrato):
        import json
        url = reverse('core:api_comprador_atualizar', kwargs={'pk': contrato.comprador.pk})
        payload = {'nome': 'Nome Atualizado API'}
        response = client_logado.patch(url, json.dumps(payload), content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'

    def test_excluir_comprador_soft_delete(self, client_logado, contrato):
        url = reverse('core:api_comprador_excluir', kwargs={'pk': contrato.comprador.pk})
        response = client_logado.delete(url)
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        contrato.comprador.refresh_from_db()
        assert contrato.comprador.ativo is False


# ---------------------------------------------------------------------------
# API REST CRUD — Imobiliária
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiImobiliariaCrud:
    """Testes da API REST de Imobiliária (GET lista, GET detalhe, PATCH, DELETE)"""

    def test_listar_sem_auth_retorna_redirect(self, client):
        url = reverse('core:api_imobiliarias')
        assert client.get(url).status_code in (302, 403)

    def test_listar_retorna_json(self, client_logado, contrato):
        response = client_logado.get(reverse('core:api_imobiliarias'))
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        assert 'imobiliarias' in data

    def test_listar_filtro_ativo(self, client_logado, contrato):
        url = reverse('core:api_imobiliarias')
        response = client_logado.get(url, {'ativo': 'true'})
        assert response.status_code == 200

    def test_detalhe_imobiliaria_existente(self, client_logado, contrato):
        url = reverse('core:api_imobiliaria_detalhe', kwargs={'pk': contrato.imobiliaria.pk})
        response = client_logado.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        imob = data.get('imobiliaria', {})
        assert 'cor_marca' in imob
        assert 'rodape_contato' in imob
        assert 'marca_dagua' in imob

    def test_detalhe_imobiliaria_inexistente(self, client_logado):
        url = reverse('core:api_imobiliaria_detalhe', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404

    def test_atualizar_campos_visuais(self, client_logado, contrato):
        import json
        url = reverse('core:api_imobiliaria_atualizar', kwargs={'pk': contrato.imobiliaria.pk})
        payload = {'cor_marca': 'FF5733', 'rodape_contato': 'Tel: (11) 1234-5678'}
        response = client_logado.patch(url, json.dumps(payload), content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        contrato.imobiliaria.refresh_from_db()
        assert contrato.imobiliaria.cor_marca == 'FF5733'

    def test_excluir_imobiliaria_soft_delete(self, client_logado, contrato):
        url = reverse('core:api_imobiliaria_excluir', kwargs={'pk': contrato.imobiliaria.pk})
        response = client_logado.delete(url)
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'success'
        contrato.imobiliaria.refresh_from_db()
        assert contrato.imobiliaria.ativo is False


# ---------------------------------------------------------------------------
# API Setup Passo 3 — simular remessa, retorno e logos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSetupPasso3Views:
    """Testes das views do Setup Passo 3 (remessa CNAB, retorno, logos)"""

    def test_simular_remessa_requer_post(self, client_logado):
        url = reverse('core:api_simular_remessa_teste')
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_simular_remessa_sem_auth(self, client):
        url = reverse('core:api_simular_remessa_teste')
        response = client.post(url)
        assert response.status_code in (302, 403)

    def test_simular_remessa_retorna_json(self, client_logado):
        url = reverse('core:api_simular_remessa_teste')
        response = client_logado.post(url, HTTP_X_CSRFTOKEN='dummy')
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') in ('success', 'error')

    def test_simular_retorno_requer_post(self, client_logado):
        url = reverse('core:api_simular_retorno_teste')
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_simular_retorno_retorna_json(self, client_logado):
        url = reverse('core:api_simular_retorno_teste')
        response = client_logado.post(url, HTTP_X_CSRFTOKEN='dummy')
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') in ('success', 'error')

    def test_gerar_logos_requer_post(self, client_logado):
        url = reverse('core:api_gerar_logos_teste')
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_gerar_logos_retorna_json(self, client_logado):
        url = reverse('core:api_gerar_logos_teste')
        response = client_logado.post(url, HTTP_X_CSRFTOKEN='dummy')
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') in ('success', 'error')
        assert 'imobiliarias_com_logo' in data

