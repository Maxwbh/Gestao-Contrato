"""
HU-28 — Cadastro e gestão de usuários do sistema.

Cobre: perfil (ADMIN/COMUM) + auto-criação, restrição a administradores,
cadastro com senha inicial × convite, escopo do cadastrador nos acessos,
troca de senha obrigatória, auto-registro fechado e exclusividade
Comprador × Usuário.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import (PerfilUsuario, AcessoUsuario, pode_gerenciar_usuarios,
                         usuario_deve_trocar_senha)

User = get_user_model()


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def contab_imobs(db):
    from tests.fixtures.factories import ContabilidadeFactory, ImobiliariaFactory
    cont = ContabilidadeFactory()
    im_a = ImobiliariaFactory(contabilidade=cont)
    im_b = ImobiliariaFactory(contabilidade=cont)
    return cont, im_a, im_b


@pytest.fixture
def admin_escopo(db, contab_imobs):
    """Administrador NÃO-superuser, com acesso só à imobiliária A."""
    from tests.fixtures.factories import UserFactory, AcessoUsuarioFactory
    cont, im_a, im_b = contab_imobs
    user = UserFactory()
    user.perfil.papel = PerfilUsuario.PAPEL_ADMIN
    user.perfil.save()
    AcessoUsuarioFactory(usuario=user, contabilidade=cont, imobiliaria=im_a)
    return user


# ── perfil + helpers ────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPerfilEHelpers:
    def test_perfil_criado_automaticamente(self):
        u = User.objects.create_user('novo', 'novo@x.com', 'x')
        assert hasattr(u, 'perfil')
        assert u.perfil.papel == PerfilUsuario.PAPEL_COMUM

    def test_pode_gerenciar_admin_papel(self, admin_escopo):
        assert pode_gerenciar_usuarios(admin_escopo)

    def test_comum_nao_pode_gerenciar(self):
        u = User.objects.create_user('comum', 'c@x.com', 'x')
        assert not pode_gerenciar_usuarios(u)

    def test_superuser_pode_gerenciar(self):
        from tests.fixtures.factories import SuperUserFactory
        assert pode_gerenciar_usuarios(SuperUserFactory())


# ── restrição da tela (RN-1) ────────────────────────────────────────────────
@pytest.mark.django_db
class TestRestricaoAdmin:
    def test_comum_recebe_403(self, client):
        u = User.objects.create_user('comum', 'c@x.com', 'x')
        client.force_login(u)
        assert client.get(reverse('core:listar_usuarios')).status_code == 403
        assert client.get(reverse('core:criar_usuario')).status_code == 403

    def test_admin_acessa(self, client, admin_escopo):
        client.force_login(admin_escopo)
        assert client.get(reverse('core:listar_usuarios')).status_code == 200
        assert client.get(reverse('core:criar_usuario')).status_code == 200

    def test_403_registra_auditoria(self, client):
        from core.models import LogAuditoria
        u = User.objects.create_user('comum', 'c@x.com', 'x')
        client.force_login(u)
        client.get(reverse('core:listar_usuarios'))
        assert LogAuditoria.objects.filter(acao='ACESSO_NEGADO_ESCOPO', usuario=u).exists()


# ── cadastro (28.1/28.2/28.7) ───────────────────────────────────────────────
@pytest.mark.django_db
class TestCadastro:
    def _payload(self, im_a, **over):
        data = {
            'first_name': 'Ana', 'last_name': 'Ribeiro', 'email': 'ana@x.com',
            'senha1': 'Contab@2026', 'senha2': 'Contab@2026',
            f'imob_{im_a.id}': 'on', f'edit_{im_a.id}': 'on',
        }
        data.update(over)
        return data

    def test_cria_com_senha_inicial(self, client, admin_escopo, contab_imobs):
        _, im_a, _ = contab_imobs
        client.force_login(admin_escopo)
        r = client.post(reverse('core:criar_usuario'), self._payload(im_a))
        assert r.status_code == 302
        u = User.objects.get(email='ana@x.com')
        assert u.username == 'ana@x.com' and u.has_usable_password()
        assert u.perfil.papel == PerfilUsuario.PAPEL_COMUM
        assert u.perfil.deve_trocar_senha is True
        assert AcessoUsuario.objects.filter(usuario=u, imobiliaria=im_a, pode_editar=True).exists()

    def test_switch_admin_define_papel(self, client, admin_escopo, contab_imobs):
        _, im_a, _ = contab_imobs
        client.force_login(admin_escopo)
        client.post(reverse('core:criar_usuario'), self._payload(im_a, is_admin='on'))
        assert User.objects.get(email='ana@x.com').perfil.papel == PerfilUsuario.PAPEL_ADMIN

    def test_convite_sem_senha(self, client, admin_escopo, contab_imobs):
        _, im_a, _ = contab_imobs
        client.force_login(admin_escopo)
        client.post(reverse('core:criar_usuario'),
                    self._payload(im_a, enviar_convite='on', senha1='', senha2=''))
        u = User.objects.get(email='ana@x.com')
        assert not u.has_usable_password()
        assert u.perfil.deve_trocar_senha is False

    def test_email_duplicado_bloqueado(self, client, admin_escopo, contab_imobs):
        _, im_a, _ = contab_imobs
        User.objects.create_user('ana@x.com', 'ana@x.com', 'x')
        client.force_login(admin_escopo)
        r = client.post(reverse('core:criar_usuario'), self._payload(im_a))
        assert r.status_code == 200  # re-renderiza com erro
        assert User.objects.filter(email='ana@x.com').count() == 1

    def test_ao_menos_um_acesso(self, client, admin_escopo, contab_imobs):
        _, im_a, _ = contab_imobs
        client.force_login(admin_escopo)
        data = self._payload(im_a)
        data.pop(f'imob_{im_a.id}')
        r = client.post(reverse('core:criar_usuario'), data)
        assert r.status_code == 200
        assert not User.objects.filter(email='ana@x.com').exists()

    def test_senha_fraca_rejeitada(self, client, admin_escopo, contab_imobs):
        _, im_a, _ = contab_imobs
        client.force_login(admin_escopo)
        r = client.post(reverse('core:criar_usuario'),
                        self._payload(im_a, senha1='123', senha2='123'))
        assert r.status_code == 200
        assert not User.objects.filter(email='ana@x.com').exists()

    def test_registra_auditoria(self, client, admin_escopo, contab_imobs):
        from core.models import LogAuditoria
        _, im_a, _ = contab_imobs
        client.force_login(admin_escopo)
        client.post(reverse('core:criar_usuario'), self._payload(im_a))
        assert LogAuditoria.objects.filter(acao='USUARIO_CRIADO').exists()
        assert LogAuditoria.objects.filter(acao='ACESSO_CONCEDIDO').exists()


# ── escopo do cadastrador (RN-2) ────────────────────────────────────────────
@pytest.mark.django_db
class TestEscopo:
    def test_form_so_mostra_imob_do_escopo(self, admin_escopo, contab_imobs):
        from core.forms import NovoUsuarioForm
        _, im_a, im_b = contab_imobs
        form = NovoUsuarioForm(cadastrador=admin_escopo)
        assert f'imob_{im_a.id}' in form.fields
        assert f'imob_{im_b.id}' not in form.fields  # fora do escopo

    def test_post_de_imob_alheia_ignorado(self, client, admin_escopo, contab_imobs):
        _, im_a, im_b = contab_imobs
        client.force_login(admin_escopo)
        # tenta forçar acesso à imob_b (fora do escopo) além da im_a
        data = {'first_name': 'Ana', 'last_name': 'R', 'email': 'ana@x.com',
                'senha1': 'Contab@2026', 'senha2': 'Contab@2026',
                f'imob_{im_a.id}': 'on', f'imob_{im_b.id}': 'on'}
        client.post(reverse('core:criar_usuario'), data)
        u = User.objects.get(email='ana@x.com')
        assert AcessoUsuario.objects.filter(usuario=u, imobiliaria=im_a).exists()
        assert not AcessoUsuario.objects.filter(usuario=u, imobiliaria=im_b).exists()

    def test_acessousuarioform_escopo(self, admin_escopo, contab_imobs):
        from core.forms import AcessoUsuarioForm
        _, im_a, im_b = contab_imobs
        form = AcessoUsuarioForm(cadastrador=admin_escopo)
        ids = set(form.fields['imobiliaria'].queryset.values_list('id', flat=True))
        assert im_a.id in ids and im_b.id not in ids


# ── troca de senha obrigatória (28.2) ───────────────────────────────────────
@pytest.mark.django_db
class TestTrocaSenha:
    def test_redireciona_ate_trocar(self, client):
        u = User.objects.create_user('x', 'x@x.com', 'Senha@123')
        u.perfil.deve_trocar_senha = True
        u.perfil.save()
        client.force_login(u)
        r = client.get(reverse('core:dashboard'))
        assert r.status_code == 302 and 'alterar-senha' in r.url

    def test_alterar_senha_limpa_flag(self, client):
        u = User.objects.create_user('x', 'x@x.com', 'Senha@123')
        u.perfil.deve_trocar_senha = True
        u.perfil.save()
        client.force_login(u)
        client.post(reverse('accounts:alterar_senha'), {
            'senha_atual': 'Senha@123', 'nova_senha': 'NovaSenha@456',
            'confirmar_senha': 'NovaSenha@456'})
        u.perfil.refresh_from_db()
        assert u.perfil.deve_trocar_senha is False

    def test_pagina_de_troca_e_isenta(self, client):
        u = User.objects.create_user('x', 'x@x.com', 'Senha@123')
        u.perfil.deve_trocar_senha = True
        u.perfil.save()
        client.force_login(u)
        assert client.get(reverse('accounts:alterar_senha')).status_code == 200


# ── auto-registro fechado (28.4) ────────────────────────────────────────────
@pytest.mark.django_db
class TestAutoRegistroFechado:
    def test_registro_redireciona_por_padrao(self, client):
        r = client.get(reverse('accounts:registro'))
        assert r.status_code == 302 and 'login' in r.url

    def test_registro_liberado_por_flag(self, client, settings):
        settings.PERMITIR_AUTO_REGISTRO = True
        assert client.get(reverse('accounts:registro')).status_code == 200


# ── exclusividade Comprador × Usuário (RN-5) ────────────────────────────────
@pytest.mark.django_db
class TestExclusividade:
    def test_comprador_nao_recebe_acesso_interno(self, contab_imobs):
        from django.core.exceptions import ValidationError
        from tests.fixtures.factories import CompradorFactory
        cont, im_a, _ = contab_imobs
        comprador = CompradorFactory()
        u = User.objects.create_user('comp', 'comp@x.com', 'x')
        from portal_comprador.models import AcessoComprador
        AcessoComprador.objects.create(comprador=comprador, usuario=u)
        with pytest.raises(ValidationError):
            AcessoUsuario.objects.create(usuario=u, contabilidade=cont, imobiliaria=im_a)


# ── ciclo de vida (28.6) ────────────────────────────────────────────────────
@pytest.mark.django_db
class TestCicloVida:
    def test_desativar(self, client, admin_escopo, contab_imobs):
        cont, im_a, _ = contab_imobs
        from tests.fixtures.factories import UserFactory, AcessoUsuarioFactory
        alvo = UserFactory()
        AcessoUsuarioFactory(usuario=alvo, contabilidade=cont, imobiliaria=im_a)
        client.force_login(admin_escopo)
        client.post(reverse('core:desativar_usuario', args=[alvo.pk]))
        alvo.refresh_from_db()
        assert alvo.is_active is False

    def test_nao_desativa_a_si(self, client, admin_escopo):
        client.force_login(admin_escopo)
        client.post(reverse('core:desativar_usuario', args=[admin_escopo.pk]))
        admin_escopo.refresh_from_db()
        assert admin_escopo.is_active is True
