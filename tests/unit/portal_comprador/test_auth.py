"""
Testes de autenticacao do app portal_comprador

Testa:
- Auto-cadastro
- Login/Logout
- Funcoes auxiliares (get_client_ip, registrar_log_acesso, get_comprador_from_request)
"""
import re
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from unittest.mock import Mock, patch

from portal_comprador.models import AcessoComprador, LogAcessoComprador
from portal_comprador.views import (
    get_client_ip,
    registrar_log_acesso,
    get_comprador_from_request,
    auto_cadastro,
    login_comprador,
    logout_comprador,
)
from tests.fixtures.factories import UserFactory, CompradorFactory


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.django_db
class TestGetClientIP:
    """Testes da funcao get_client_ip"""

    def test_ip_from_remote_addr(self, request_factory):
        """Testa obtencao do IP via REMOTE_ADDR"""
        request = request_factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'

        ip = get_client_ip(request)

        assert ip == '192.168.1.100'

    def test_ip_from_x_forwarded_for(self, request_factory):
        """Testa obtencao do IP via X-Forwarded-For (proxy)"""
        request = request_factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.50, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        ip = get_client_ip(request)

        assert ip == '10.0.0.50'


@pytest.mark.django_db
class TestRegistrarLogAcesso:
    """Testes da funcao registrar_log_acesso"""

    def test_registrar_log_acesso_completo(self, request_factory):
        """Testa registro de log com todos os dados"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        acesso = AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        request = request_factory.get('/portal/dashboard/')
        request.META['REMOTE_ADDR'] = '192.168.1.50'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 Test Browser'

        registrar_log_acesso(request, acesso, '/portal/dashboard/')

        log = LogAcessoComprador.objects.get(acesso_comprador=acesso)
        assert log.ip_acesso == '192.168.1.50'
        assert log.user_agent == 'Mozilla/5.0 Test Browser'
        assert log.pagina_acessada == '/portal/dashboard/'


@pytest.mark.django_db
class TestGetCompradorFromRequest:
    """Testes da funcao get_comprador_from_request"""

    def test_usuario_nao_autenticado(self, request_factory):
        """Testa com usuario nao autenticado"""
        request = request_factory.get('/')
        request.user = AnonymousUser()

        comprador = get_comprador_from_request(request)

        assert comprador is None

    def test_usuario_sem_acesso_comprador(self, request_factory):
        """Testa com usuario autenticado mas sem acesso de comprador"""
        request = request_factory.get('/')
        request.user = UserFactory()

        comprador = get_comprador_from_request(request)

        assert comprador is None

    def test_usuario_com_acesso_comprador(self, request_factory):
        """Testa com usuario autenticado com acesso de comprador"""
        comprador_obj = CompradorFactory(nome='Carlos Teste')
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador_obj,
            usuario=usuario
        )

        request = request_factory.get('/')
        request.user = usuario

        comprador = get_comprador_from_request(request)

        assert comprador is not None
        assert comprador.nome == 'Carlos Teste'


@pytest.mark.django_db
class TestAutoCadastroView:
    """Testes da view de auto-cadastro"""

    def test_auto_cadastro_get(self, client):
        """Testa acesso GET a pagina de auto-cadastro"""
        response = client.get('/portal/cadastro/')

        assert response.status_code == 200

    def test_auto_cadastro_usuario_logado_com_acesso(self, client):
        """Testa redirecionamento quando usuario ja tem acesso de comprador"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        client.force_login(usuario)
        response = client.get('/portal/cadastro/')

        assert response.status_code == 302
        assert '/portal/' in response.url  # Redirects to portal dashboard


@pytest.mark.django_db
class TestLoginCompradorView:
    """Testes da view de login"""

    def test_login_get(self, client):
        """Testa acesso GET a pagina de login"""
        response = client.get('/portal/login/')

        assert response.status_code == 200

    def test_login_usuario_ja_logado(self, client):
        """Testa redirecionamento quando usuario ja esta logado"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        client.force_login(usuario)
        response = client.get('/portal/login/')

        assert response.status_code == 302
        assert '/portal/' in response.url  # Redirects to portal dashboard


@pytest.mark.django_db
class TestLogoutCompradorView:
    """Testes da view de logout"""

    def test_logout_comprador(self, client):
        """Testa logout do comprador"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        client.force_login(usuario)
        response = client.get('/portal/logout/')

        assert response.status_code == 302
        assert 'login' in response.url


@pytest.mark.django_db
class TestAtivoFlag:
    """Testes do campo ativo no AcessoComprador"""

    def test_login_bloqueado_quando_inativo(self, client):
        """Acesso desativado impede login"""
        comprador = CompradorFactory()
        usuario = UserFactory(password='senha123')
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario,
            ativo=False,
        )

        response = client.post('/portal/login/', {
            'documento': re.sub(r'\D', '', comprador.cpf or comprador.cnpj or '12345678901'),
            'senha': 'senha123',
        })

        # Não redireciona para dashboard — permanece na página de login
        assert response.status_code in (200, 302)
        if response.status_code == 302:
            assert 'portal' not in response.url or 'login' in response.url

    def test_get_comprador_retorna_none_quando_inativo(self, request_factory):
        """get_comprador_from_request retorna None se acesso inativo"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario,
            ativo=False,
        )

        request = request_factory.get('/')
        request.user = usuario

        resultado = get_comprador_from_request(request)

        assert resultado is None

    def test_get_comprador_retorna_comprador_quando_ativo(self, request_factory):
        """get_comprador_from_request retorna comprador se acesso ativo"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario,
            ativo=True,
        )

        request = request_factory.get('/')
        request.user = usuario

        resultado = get_comprador_from_request(request)

        assert resultado == comprador

    def test_dashboard_bloqueado_quando_inativo(self, client):
        """Dashboard redireciona para login se acesso inativo"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario,
            ativo=False,
        )

        client.force_login(usuario)
        response = client.get('/portal/')

        assert response.status_code == 302
