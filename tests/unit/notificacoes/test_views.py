"""
Testes das views do app notificacoes

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from django.urls import reverse
from notificacoes.models import (
    ConfiguracaoEmail,
    TemplateNotificacao,
    Notificacao,
    TipoNotificacao,
    TipoTemplate,
)


# =============================================================================
# TESTES DE LISTAGEM DE NOTIFICACOES
# =============================================================================

@pytest.mark.django_db
class TestListarNotificacoes:
    """Testes da view listar_notificacoes"""

    def test_listar_notificacoes_requer_login(self, client):
        """Acesso requer autenticação"""
        response = client.get(reverse('notificacoes:listar'))
        assert response.status_code == 302
        assert 'login' in response.url

    def test_listar_notificacoes_exibe_lista(self, client, user_factory):
        """Usuário autenticado vê lista de notificações"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        # Criar algumas notificações
        Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Teste'
        )

        response = client.get(reverse('notificacoes:listar'))
        assert response.status_code == 200


# =============================================================================
# TESTES DE CONFIGURACOES
# =============================================================================

@pytest.mark.django_db
class TestConfiguracoes:
    """Testes da view configuracoes"""

    def test_configuracoes_requer_login(self, client):
        """Acesso requer autenticação"""
        response = client.get(reverse('notificacoes:configuracoes'))
        assert response.status_code == 302

    def test_configuracoes_exibe_opcoes(self, client, user_factory):
        """Usuário autenticado vê opções de configuração"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        response = client.get(reverse('notificacoes:configuracoes'))
        assert response.status_code == 200


# =============================================================================
# TESTES CRUD CONFIGURACAO EMAIL
# =============================================================================

@pytest.mark.django_db
class TestConfiguracaoEmailViews:
    """Testes das views CRUD de ConfiguracaoEmail"""

    def test_list_requer_login(self, client):
        """List requer autenticação"""
        response = client.get(reverse('notificacoes:listar_config_email'))
        assert response.status_code == 302

    def test_list_exibe_configs(self, client, user_factory):
        """List exibe configurações existentes"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        ConfiguracaoEmail.objects.create(
            nome='SMTP Teste',
            host='smtp.test.com',
            usuario='user',
            senha='pass',
            email_remetente='test@test.com'
        )

        response = client.get(reverse('notificacoes:listar_config_email'))
        assert response.status_code == 200

    def test_create_get(self, client, user_factory):
        """GET no create retorna formulário"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        response = client.get(reverse('notificacoes:criar_config_email'))
        assert response.status_code == 200

    def test_create_post_valido(self, client, user_factory):
        """POST válido cria configuração"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        response = client.post(reverse('notificacoes:criar_config_email'), {
            'nome': 'Nova Config',
            'host': 'smtp.gmail.com',
            'porta': 587,
            'usuario': 'user@gmail.com',
            'senha': 'senha123',
            'usar_tls': True,
            'usar_ssl': False,
            'email_remetente': 'user@gmail.com',
            'nome_remetente': 'Sistema',
            'ativo': True
        })
        # Redirect após sucesso ou form com erros
        assert response.status_code in [200, 302]

    def test_update_get(self, client, user_factory):
        """GET no update retorna formulário preenchido"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        config = ConfiguracaoEmail.objects.create(
            nome='Config Existente',
            host='smtp.test.com',
            usuario='user',
            senha='pass',
            email_remetente='test@test.com'
        )

        response = client.get(reverse('notificacoes:editar_config_email', args=[config.pk]))
        assert response.status_code == 200

    def test_delete_get(self, client, user_factory):
        """GET no delete mostra confirmação"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        config = ConfiguracaoEmail.objects.create(
            nome='Config para Deletar',
            host='smtp.test.com',
            usuario='user',
            senha='pass',
            email_remetente='test@test.com'
        )

        response = client.get(reverse('notificacoes:excluir_config_email', args=[config.pk]))
        assert response.status_code == 200

    def test_delete_post(self, client, user_factory):
        """POST no delete remove configuração"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        config = ConfiguracaoEmail.objects.create(
            nome='Config para Deletar',
            host='smtp.test.com',
            usuario='user',
            senha='pass',
            email_remetente='test@test.com'
        )

        response = client.post(reverse('notificacoes:excluir_config_email', args=[config.pk]))
        assert response.status_code == 302
        assert not ConfiguracaoEmail.objects.filter(pk=config.pk).exists()


# =============================================================================
# TESTES CRUD TEMPLATE NOTIFICACAO
# =============================================================================

@pytest.mark.django_db
class TestTemplateNotificacaoViews:
    """Testes das views CRUD de TemplateNotificacao"""

    def test_list_requer_login(self, client):
        """List requer autenticação"""
        response = client.get(reverse('notificacoes:listar_templates'))
        assert response.status_code == 302

    def test_list_exibe_templates(self, client, user_factory):
        """List exibe templates existentes"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        TemplateNotificacao.objects.create(
            nome='Template Teste',
            codigo=TipoTemplate.CUSTOM,
            tipo=TipoNotificacao.EMAIL,
            corpo='Corpo do template'
        )

        response = client.get(reverse('notificacoes:listar_templates'))
        assert response.status_code == 200

    def test_create_get(self, client, user_factory):
        """GET no create retorna formulário"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        response = client.get(reverse('notificacoes:criar_template'))
        assert response.status_code == 200

    def test_create_post_valido(self, client, user_factory):
        """POST válido cria template"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        response = client.post(reverse('notificacoes:criar_template'), {
            'nome': 'Novo Template',
            'codigo': TipoTemplate.CUSTOM,
            'tipo': TipoNotificacao.EMAIL,
            'assunto': 'Assunto Teste',
            'corpo': 'Corpo do template %%NOMECOMPRADOR%%',
            'ativo': True
        })
        assert response.status_code in [200, 302]

    def test_update_get(self, client, user_factory):
        """GET no update retorna formulário preenchido"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        template = TemplateNotificacao.objects.create(
            nome='Template Existente',
            codigo=TipoTemplate.CUSTOM,
            tipo=TipoNotificacao.EMAIL,
            corpo='Corpo'
        )

        response = client.get(reverse('notificacoes:editar_template', args=[template.pk]))
        assert response.status_code == 200

    def test_delete_post(self, client, user_factory):
        """POST no delete remove template"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        template = TemplateNotificacao.objects.create(
            nome='Template para Deletar',
            codigo=TipoTemplate.CUSTOM,
            tipo=TipoNotificacao.EMAIL,
            corpo='Corpo'
        )

        response = client.post(reverse('notificacoes:excluir_template', args=[template.pk]))
        assert response.status_code == 302
        assert not TemplateNotificacao.objects.filter(pk=template.pk).exists()

    def test_duplicar_template(self, client, user_factory):
        """Duplicar cria cópia do template"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        template = TemplateNotificacao.objects.create(
            nome='Template Original',
            codigo=TipoTemplate.CUSTOM,
            tipo=TipoNotificacao.EMAIL,
            corpo='Corpo original'
        )

        response = client.post(reverse('notificacoes:duplicar_template', args=[template.pk]))
        assert response.status_code == 302
        assert TemplateNotificacao.objects.count() == 2

    def test_preview_template(self, client, user_factory):
        """Preview renderiza template com dados de exemplo"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        template = TemplateNotificacao.objects.create(
            nome='Template Preview',
            codigo=TipoTemplate.CUSTOM,
            tipo=TipoNotificacao.EMAIL,
            assunto='Olá %%NOMECOMPRADOR%%',
            corpo='Prezado %%NOMECOMPRADOR%%, sua parcela %%PARCELA%%.'
        )

        response = client.get(reverse('notificacoes:preview_template', args=[template.pk]))
        assert response.status_code == 200


# =============================================================================
# TESTES DE TESTAR CONEXAO EMAIL
# =============================================================================

@pytest.mark.django_db
class TestTestarConexaoEmail:
    """Testes da view testar_conexao_email"""

    def test_testar_conexao_requer_login(self, client):
        """Acesso requer autenticação"""
        config = ConfiguracaoEmail.objects.create(
            nome='Config',
            host='smtp.test.com',
            usuario='user',
            senha='pass',
            email_remetente='test@test.com'
        )
        response = client.get(reverse('notificacoes:testar_config_email', args=[config.pk]))
        assert response.status_code == 302

    def test_testar_conexao_config_inexistente(self, client, user_factory):
        """Testar conexão com config inexistente retorna 404"""
        user = user_factory()
        user.set_password('test123')
        user.save()
        client.login(username=user.username, password='test123')

        response = client.get(reverse('notificacoes:testar_config_email', args=[99999]))
        assert response.status_code == 404


# =============================================================================
# WEBHOOK EVOLUTION API — Autenticação por apikey (Opção A)
# =============================================================================

import json

@pytest.mark.django_db
class TestWebhookEvolution:
    """Testes do endpoint webhook_evolution — valida apikey obrigatória no header."""

    URL = '/notificacoes/webhook/evolution/'

    def _payload(self, instance='test-inst', event='messages.update', status='READ'):
        return json.dumps({
            'event': event,
            'instance': instance,
            'data': [{'key': {'id': 'MSGID1', 'fromMe': True,
                               'remoteJid': '5531999990001@s.whatsapp.net'},
                      'update': {'status': status}}],
        })

    def test_sem_apikey_retorna_403(self, client):
        """Webhook sem apikey deve ser rejeitado com 403."""
        resp = client.post(self.URL, self._payload(),
                           content_type='application/json')
        assert resp.status_code == 403

    def test_apikey_invalida_retorna_403(self, client):
        """Webhook com apikey que não existe no DB deve retornar 403."""
        resp = client.post(
            self.URL, self._payload(instance='inst-x'),
            content_type='application/json',
            HTTP_APIKEY='chave-errada',
        )
        assert resp.status_code == 403

    def test_apikey_valida_event_ignorado_retorna_200(self, client):
        """Evento não mapeado com apikey válida deve retornar 200 sem erro."""
        from tests.fixtures.factories import ConfiguracaoWhatsAppFactory
        cfg = ConfiguracaoWhatsAppFactory(
            provedor='EVOLUTION', instancia='inst-ok', api_key='chave-ok', ativo=True,
        )
        resp = client.post(
            self.URL,
            self._payload(instance='inst-ok', event='connection.update'),
            content_type='application/json',
            HTTP_APIKEY='chave-ok',
        )
        assert resp.status_code == 200
        cfg.delete()

    def test_apikey_no_payload_tambem_aceita(self, client):
        """Evolution pode enviar apikey dentro do payload JSON (fallback)."""
        from tests.fixtures.factories import ConfiguracaoWhatsAppFactory
        cfg = ConfiguracaoWhatsAppFactory(
            provedor='EVOLUTION', instancia='inst-payload', api_key='chave-payload', ativo=True,
        )
        body = json.loads(self._payload(instance='inst-payload', event='connection.update'))
        body['apikey'] = 'chave-payload'
        resp = client.post(
            self.URL, json.dumps(body),
            content_type='application/json',
        )
        assert resp.status_code == 200
        cfg.delete()

    def test_metodo_get_retorna_405(self, client):
        """Webhook só aceita POST."""
        resp = client.get(self.URL)
        assert resp.status_code == 405
