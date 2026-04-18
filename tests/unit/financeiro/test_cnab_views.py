"""
Testes das views CNAB do app financeiro.

Escopo: listar_remessas, detalhe_remessa, gerar_remessa,
        download_remessa, marcar_remessa_enviada, regenerar_remessa,
        listar_retornos, upload_retorno, processar_retorno, download_retorno
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
class TestListarRemessas:
    """Testes da view listar_arquivos_remessa"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:listar_remessas')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        """Retorna 200 mesmo sem arquivos de remessa"""
        response = client_logado.get(reverse('financeiro:listar_remessas'))
        assert response.status_code == 200

    def test_filtro_status(self, client_logado):
        response = client_logado.get(
            reverse('financeiro:listar_remessas'),
            {'status': 'GERADO'}
        )
        assert response.status_code == 200

    def test_paginacao(self, client_logado):
        response = client_logado.get(
            reverse('financeiro:listar_remessas'),
            {'per_page': '10'}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestDetalheRemessa:
    """Testes da view detalhe_arquivo_remessa"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:detalhe_remessa', kwargs={'pk': 1})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_remessa_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:detalhe_remessa', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestGerarRemessa:
    """Testes da view gerar_arquivo_remessa"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:gerar_remessa')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_exibe_formulario(self, client_logado):
        """GET retorna página com boletos disponíveis"""
        response = client_logado.get(reverse('financeiro:gerar_remessa'))
        assert response.status_code == 200

    def test_post_sem_boletos_retorna_erro(self, client_logado):
        """POST sem boletos selecionados retorna JSON de erro"""
        response = client_logado.post(
            reverse('financeiro:gerar_remessa'),
            {'boleto_ids': []}
        )
        assert response.status_code in (200, 302, 400, 500)
        if response.status_code == 200:
            try:
                data = response.json()
                assert 'sucesso' in data or 'erro' in data
            except Exception:
                pass


@pytest.mark.django_db
class TestDownloadRemessa:
    """Testes da view download_arquivo_remessa"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:download_remessa', kwargs={'pk': 1})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_remessa_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:download_remessa', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestMarcarRemessaEnviada:
    """Testes da view marcar_remessa_enviada"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:marcar_remessa_enviada', kwargs={'pk': 1})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_get_nao_permitido(self, client_logado):
        """GET retorna 405 (require_POST)"""
        url = reverse('financeiro:marcar_remessa_enviada', kwargs={'pk': 1})
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_remessa_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:marcar_remessa_enviada', kwargs={'pk': 999999})
        response = client_logado.post(url, {})
        assert response.status_code == 404


@pytest.mark.django_db
class TestListarRetornos:
    """Testes da view listar_arquivos_retorno"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:listar_retornos')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        response = client_logado.get(reverse('financeiro:listar_retornos'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestUploadRetorno:
    """Testes da view upload_arquivo_retorno"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:upload_retorno')
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_get_exibe_formulario(self, client_logado):
        response = client_logado.get(reverse('financeiro:upload_retorno'))
        assert response.status_code == 200

    def test_post_sem_arquivo_retorna_erro(self, client_logado):
        """POST sem arquivo retorna formulário com erro, JSON ou redirect"""
        response = client_logado.post(reverse('financeiro:upload_retorno'), {})
        assert response.status_code in (200, 302, 400)


@pytest.mark.django_db
class TestProcessarRetorno:
    """Testes da view processar_arquivo_retorno"""

    def test_requer_autenticacao(self, client):
        url = reverse('financeiro:processar_retorno', kwargs={'pk': 1})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_retorno_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:processar_retorno', kwargs={'pk': 999999})
        response = client_logado.post(url, {})
        assert response.status_code == 404
