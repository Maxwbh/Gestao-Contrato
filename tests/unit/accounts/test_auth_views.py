"""
Testes das views de autenticação do app accounts

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from django.urls import reverse
from django.contrib.auth.models import User


# =============================================================================
# TESTES DE LOGIN
# =============================================================================

@pytest.mark.django_db
class TestLoginView:
    """Testes da view de login"""

    def test_login_get_retorna_formulario(self, client):
        """GET /accounts/login/ retorna formulário de login"""
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200
        assert 'form' in response.context

    def test_login_post_credenciais_validas(self, client, user_factory):
        """POST com credenciais válidas redireciona para dashboard"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()

        response = client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        assert response.url == reverse('core:dashboard')

    def test_login_post_credenciais_invalidas(self, client, user_factory):
        """POST com credenciais inválidas retorna erro"""
        user_factory(username='testuser', password='testpass123')

        response = client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'senhaerrada'
        })
        assert response.status_code == 200
        assert 'form' in response.context

    def test_login_post_usuario_inexistente(self, client):
        """POST com usuário inexistente retorna erro"""
        response = client.post(reverse('accounts:login'), {
            'username': 'naoexiste',
            'password': 'qualquersenha'
        })
        assert response.status_code == 200

    def test_login_redireciona_usuario_autenticado(self, client, user_factory):
        """Usuário já autenticado é redirecionado para dashboard"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('accounts:login'))
        assert response.status_code == 302
        assert response.url == reverse('core:dashboard')

    def test_login_com_next_redireciona_para_next(self, client, user_factory):
        """Login com parâmetro next redireciona para URL especificada"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()

        response = client.post(
            reverse('accounts:login') + '?next=/contratos/',
            {'username': 'testuser', 'password': 'testpass123'}
        )
        assert response.status_code == 302
        assert response.url == '/contratos/'


# =============================================================================
# TESTES DE LOGOUT
# =============================================================================

@pytest.mark.django_db
class TestLogoutView:
    """Testes da view de logout"""

    def test_logout_desloga_usuario(self, client, user_factory):
        """Logout desloga o usuário"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('accounts:logout'))
        assert response.status_code == 302

    def test_logout_redireciona_para_login(self, client, user_factory):
        """Logout redireciona para página de login"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('accounts:logout'))
        assert response.url == reverse('accounts:login')


# =============================================================================
# TESTES DE REGISTRO
# =============================================================================

@pytest.mark.django_db
class TestRegistroView:
    """Testes da view de registro"""

    def test_registro_get_retorna_formulario(self, client):
        """GET /accounts/registro/ retorna formulário de registro"""
        response = client.get(reverse('accounts:registro'))
        assert response.status_code == 200
        assert 'form' in response.context

    def test_registro_post_dados_validos(self, client):
        """POST com dados válidos cria usuário"""
        response = client.post(reverse('accounts:registro'), {
            'username': 'novousuario',
            'first_name': 'Novo',
            'last_name': 'Usuario',
            'email': 'novo@email.com',
            'password1': 'SenhaForte123!',
            'password2': 'SenhaForte123!'
        })
        assert response.status_code == 302
        assert User.objects.filter(username='novousuario').exists()

    def test_registro_post_dados_invalidos(self, client):
        """POST com dados inválidos retorna erro"""
        response = client.post(reverse('accounts:registro'), {
            'username': '',
            'email': 'invalido',
            'password1': '123',
            'password2': '456'
        })
        assert response.status_code == 200
        assert 'form' in response.context

    def test_registro_post_username_duplicado(self, client, user_factory):
        """POST com username duplicado retorna erro"""
        user_factory(username='existente')

        response = client.post(reverse('accounts:registro'), {
            'username': 'existente',
            'first_name': 'Teste',
            'last_name': 'Usuario',
            'email': 'outro@email.com',
            'password1': 'SenhaForte123!',
            'password2': 'SenhaForte123!'
        })
        assert response.status_code == 200
        assert 'form' in response.context

    def test_registro_post_email_duplicado(self, client, user_factory):
        """POST com email duplicado retorna erro"""
        user_factory(email='existente@email.com')

        response = client.post(reverse('accounts:registro'), {
            'username': 'novousuario',
            'first_name': 'Teste',
            'last_name': 'Usuario',
            'email': 'existente@email.com',
            'password1': 'SenhaForte123!',
            'password2': 'SenhaForte123!'
        })
        assert response.status_code == 200

    def test_registro_post_senhas_nao_coincidem(self, client):
        """POST com senhas diferentes retorna erro"""
        response = client.post(reverse('accounts:registro'), {
            'username': 'novousuario',
            'first_name': 'Teste',
            'last_name': 'Usuario',
            'email': 'novo@email.com',
            'password1': 'SenhaForte123!',
            'password2': 'OutraSenha456!'
        })
        assert response.status_code == 200

    def test_registro_redireciona_usuario_autenticado(self, client, user_factory):
        """Usuário já autenticado é redirecionado"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('accounts:registro'))
        assert response.status_code == 302


# =============================================================================
# TESTES DE PERFIL
# =============================================================================

@pytest.mark.django_db
class TestPerfilView:
    """Testes da view de perfil"""

    def test_perfil_requer_autenticacao(self, client):
        """Acesso ao perfil requer autenticação"""
        response = client.get(reverse('accounts:perfil'))
        assert response.status_code == 302
        assert 'login' in response.url

    def test_perfil_get_exibe_dados_usuario(self, client, user_factory):
        """GET exibe dados do usuário logado"""
        user = user_factory(username='testuser', first_name='Test', last_name='User')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('accounts:perfil'))
        assert response.status_code == 200
        assert 'form' in response.context

    def test_perfil_post_atualiza_dados(self, client, user_factory):
        """POST atualiza dados do usuário"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.post(reverse('accounts:perfil'), {
            'first_name': 'Novo Nome',
            'last_name': 'Novo Sobrenome',
            'email': 'novo@email.com'
        })
        assert response.status_code == 302

        user.refresh_from_db()
        assert user.first_name == 'Novo Nome'


# =============================================================================
# TESTES DE ALTERAR SENHA
# =============================================================================

@pytest.mark.django_db
class TestAlterarSenhaView:
    """Testes da view de alterar senha"""

    def test_alterar_senha_requer_autenticacao(self, client):
        """Acesso requer autenticação"""
        response = client.get(reverse('accounts:alterar_senha'))
        assert response.status_code == 302
        assert 'login' in response.url

    def test_alterar_senha_get_retorna_formulario(self, client, user_factory):
        """GET retorna formulário de alteração de senha"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('accounts:alterar_senha'))
        assert response.status_code == 200
        assert 'form' in response.context

    def test_alterar_senha_post_senha_valida(self, client, user_factory):
        """POST com dados válidos altera a senha"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.post(reverse('accounts:alterar_senha'), {
            'senha_atual': 'testpass123',
            'nova_senha': 'NovaSenha456!',
            'confirmar_senha': 'NovaSenha456!'
        })
        assert response.status_code == 302

    def test_alterar_senha_post_senha_atual_incorreta(self, client, user_factory):
        """POST com senha atual incorreta retorna erro"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.post(reverse('accounts:alterar_senha'), {
            'senha_atual': 'senhaerrada',
            'nova_senha': 'NovaSenha456!',
            'confirmar_senha': 'NovaSenha456!'
        })
        assert response.status_code == 200

    def test_alterar_senha_post_senhas_nao_coincidem(self, client, user_factory):
        """POST com senhas diferentes retorna erro"""
        user = user_factory(username='testuser')
        user.set_password('testpass123')
        user.save()
        client.login(username='testuser', password='testpass123')

        response = client.post(reverse('accounts:alterar_senha'), {
            'senha_atual': 'testpass123',
            'nova_senha': 'NovaSenha456!',
            'confirmar_senha': 'OutraSenha789!'
        })
        assert response.status_code == 200
