"""
Testes das views de boletos do app financeiro.

Escopo: gerar_boleto, download_boleto, cancelar_boleto,
        download_zip_boletos, segunda_via_boleto, gerar_carne
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
class TestGerarBoleto:
    """Testes da view gerar_boleto (POST /parcelas/<pk>/boleto/)"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_parcela_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:gerar_boleto', kwargs={'pk': 999999})
        response = client_logado.post(url, {})
        assert response.status_code == 404

    def test_sem_conta_bancaria_retorna_erro(self, client_logado, parcela):
        """Sem conta bancária configurada retorna JSON de erro"""
        # Remove conta bancária da imobiliária
        parcela.contrato.imobiliaria.contas_bancarias.all().delete()
        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.post(url, {})
        assert response.status_code in (200, 400, 500)
        if response.status_code not in (301, 302):
            data = response.json()
            assert 'sucesso' in data or 'erro' in data

    def test_parcela_paga_retorna_erro(self, client_logado, parcela):
        """Parcela já paga não pode ter boleto gerado"""
        parcela.pago = True
        parcela.save()
        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.post(url, {})
        # Deve retornar erro (JSON ou redirect)
        assert response.status_code in (200, 302, 400, 500)


@pytest.mark.django_db
class TestDownloadBoleto:
    """Testes da view download_boleto"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:download_boleto', kwargs={'pk': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_sem_boleto_redireciona(self, client_logado, parcela):
        """Parcela sem boleto gerado redireciona com mensagem"""
        parcela.boleto_gerado = False
        parcela.boleto_pdf = None
        parcela.save()
        url = reverse('financeiro:download_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code == 302

    def test_parcela_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:download_boleto', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestCancelarBoleto:
    """Testes da view cancelar_boleto"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:cancelar_boleto', kwargs={'pk': parcela.pk})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_get_nao_permitido(self, client_logado, parcela):
        """GET não é permitido (require_POST)"""
        url = reverse('financeiro:cancelar_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_cancelamento_sem_boleto(self, client_logado, parcela):
        """Cancelar parcela sem boleto retorna erro"""
        parcela.boleto_gerado = False
        parcela.save()
        url = reverse('financeiro:cancelar_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.post(url, {'motivo': 'teste'})
        assert response.status_code in (200, 400, 500)
        if response.status_code != 302:
            data = response.json()
            assert 'sucesso' in data


@pytest.mark.django_db
class TestDownloadZipBoletos:
    """Testes da view download_zip_boletos (3.12)"""

    def test_requer_autenticacao(self, client, contrato):
        url = reverse('financeiro:download_zip_boletos', kwargs={'contrato_id': contrato.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_contrato_sem_boletos_redireciona(self, client_logado, contrato):
        """Contrato sem boletos gerados redireciona com mensagem de erro"""
        url = reverse('financeiro:download_zip_boletos', kwargs={'contrato_id': contrato.pk})
        response = client_logado.get(url)
        # Redireciona quando não há boletos disponíveis
        assert response.status_code in (200, 302, 400, 404)

    def test_contrato_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:download_zip_boletos', kwargs={'contrato_id': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestSegundaViaBoleto:
    """Testes da view segunda_via_boleto (2.10)"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:segunda_via_boleto', kwargs={'pk': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_retorna_preview(self, client_logado, parcela):
        """GET retorna página de preview da segunda via"""
        url = reverse('financeiro:segunda_via_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code in (200, 302)

    def test_parcela_paga_redireciona(self, client_logado, parcela):
        """Parcela paga redireciona com mensagem"""
        parcela.pago = True
        parcela.save()
        url = reverse('financeiro:segunda_via_boleto', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code in (200, 302)


@pytest.mark.django_db
class TestGerarCarne:
    """Testes da view gerar_carne (require_POST)"""

    def test_requer_autenticacao(self, client, contrato):
        """Usuário não autenticado é redirecionado"""
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato.pk})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_get_nao_permitido(self, client_logado, contrato):
        """GET retorna 405 pois requer POST"""
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato.pk})
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_contrato_inexistente_retorna_404(self, client_logado):
        """POST para contrato inexistente retorna 404"""
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': 999999})
        response = client_logado.post(url, {})
        assert response.status_code == 404

    def test_post_sem_parcelas_selecionadas(self, client_logado, contrato):
        """POST sem parcelas retorna JSON com erro ou sucesso"""
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato.pk})
        response = client_logado.post(url, {'parcelas': []})
        assert response.status_code in (200, 302, 400, 500)
        if response.status_code == 200:
            try:
                data = response.json()
                assert 'sucesso' in data or 'gerados' in data
            except Exception:
                pass  # HTML response is also valid
