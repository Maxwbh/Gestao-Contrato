"""
Testes dos modelos do app notificacoes

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from notificacoes.models import (
    ConfiguracaoEmail,
    ConfiguracaoSMS,
    ConfiguracaoWhatsApp,
    Notificacao,
    TemplateNotificacao,
    TipoNotificacao,
    StatusNotificacao,
    TipoTemplate,
)


# =============================================================================
# TESTES DE CONFIGURACAO EMAIL
# =============================================================================

@pytest.mark.django_db
class TestConfiguracaoEmail:
    """Testes do modelo ConfiguracaoEmail"""

    def test_criar_configuracao_email(self):
        """Criar configuração de email com sucesso"""
        config = ConfiguracaoEmail.objects.create(
            nome='Config Teste',
            host='smtp.gmail.com',
            porta=587,
            usuario='teste@gmail.com',
            senha='senha123',
            usar_tls=True,
            email_remetente='teste@gmail.com',
            nome_remetente='Sistema Teste',
            ativo=True
        )
        assert config.pk is not None
        assert config.nome == 'Config Teste'
        assert config.porta == 587
        assert config.usar_tls is True

    def test_configuracao_email_str(self):
        """__str__ retorna o nome da configuração"""
        config = ConfiguracaoEmail.objects.create(
            nome='SMTP Principal',
            host='smtp.example.com',
            usuario='user',
            senha='pass',
            email_remetente='noreply@example.com'
        )
        assert str(config) == 'SMTP Principal'


# =============================================================================
# TESTES DE CONFIGURACAO SMS
# =============================================================================

@pytest.mark.django_db
class TestConfiguracaoSMS:
    """Testes do modelo ConfiguracaoSMS"""

    def test_criar_configuracao_sms(self):
        """Criar configuração de SMS com sucesso"""
        config = ConfiguracaoSMS.objects.create(
            nome='Twilio SMS',
            provedor='TWILIO',
            account_sid='AC123456',
            auth_token='token123',
            numero_remetente='+5511999999999',
            ativo=True
        )
        assert config.pk is not None
        assert config.provedor == 'TWILIO'
        assert config.numero_remetente == '+5511999999999'

    def test_configuracao_sms_str(self):
        """__str__ retorna o nome da configuração"""
        config = ConfiguracaoSMS.objects.create(
            nome='SMS Twilio',
            account_sid='AC123',
            auth_token='token',
            numero_remetente='+55119999'
        )
        assert str(config) == 'SMS Twilio'


# =============================================================================
# TESTES DE CONFIGURACAO WHATSAPP
# =============================================================================

@pytest.mark.django_db
class TestConfiguracaoWhatsApp:
    """Testes do modelo ConfiguracaoWhatsApp"""

    def test_criar_configuracao_whatsapp(self):
        """Criar configuração de WhatsApp com sucesso"""
        config = ConfiguracaoWhatsApp.objects.create(
            nome='WhatsApp Business',
            provedor='TWILIO',
            account_sid='AC123456',
            auth_token='token123',
            numero_remetente='whatsapp:+5511999999999',
            ativo=True
        )
        assert config.pk is not None
        assert 'whatsapp:' in config.numero_remetente


# =============================================================================
# TESTES DE NOTIFICACAO
# =============================================================================

@pytest.mark.django_db
class TestNotificacao:
    """Testes do modelo Notificacao"""

    def test_criar_notificacao(self):
        """Criar notificação com sucesso"""
        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            assunto='Teste',
            mensagem='Mensagem de teste'
        )
        assert notif.pk is not None
        assert notif.status == StatusNotificacao.PENDENTE
        assert notif.tentativas == 0

    def test_notificacao_status_padrao_pendente(self):
        """Status padrão é PENDENTE"""
        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.SMS,
            destinatario='+5511999999999',
            mensagem='Teste SMS'
        )
        assert notif.status == StatusNotificacao.PENDENTE

    def test_notificacao_marcar_como_enviada(self):
        """marcar_como_enviada() atualiza status e data_envio"""
        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Teste'
        )
        notif.marcar_como_enviada()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ENVIADA
        assert notif.data_envio is not None

    def test_notificacao_marcar_erro(self):
        """marcar_erro() atualiza status, mensagem e tentativas"""
        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Teste'
        )
        notif.marcar_erro('Falha na conexão SMTP')

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ERRO
        assert notif.erro_mensagem == 'Falha na conexão SMTP'
        assert notif.tentativas == 1

    def test_notificacao_str(self):
        """__str__ retorna formato legível"""
        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Teste'
        )
        result = str(notif)
        assert 'E-mail' in result
        assert 'teste@email.com' in result


# =============================================================================
# TESTES DE TEMPLATE NOTIFICACAO
# =============================================================================

@pytest.mark.django_db
class TestTemplateNotificacao:
    """Testes do modelo TemplateNotificacao"""

    def test_criar_template(self):
        """Criar template com sucesso"""
        template = TemplateNotificacao.objects.create(
            nome='Template Boleto',
            codigo=TipoTemplate.BOLETO_CRIADO,
            tipo=TipoNotificacao.EMAIL,
            assunto='Boleto %%PARCELA%% gerado',
            corpo='Olá %%NOMECOMPRADOR%%, seu boleto foi gerado.'
        )
        assert template.pk is not None
        assert template.codigo == TipoTemplate.BOLETO_CRIADO

    def test_template_str(self):
        """__str__ retorna nome e tipo"""
        template = TemplateNotificacao.objects.create(
            nome='Lembrete Parcela',
            codigo=TipoTemplate.LEMBRETE_PARCELA,
            tipo=TipoNotificacao.SMS,
            corpo='Parcela %%PARCELA%% vence em %%DATAVENCIMENTO%%'
        )
        result = str(template)
        assert 'Lembrete Parcela' in result
        assert 'SMS' in result

    def test_template_renderizar(self):
        """renderizar() substitui TAGs pelo contexto"""
        template = TemplateNotificacao.objects.create(
            nome='Teste Render',
            codigo=TipoTemplate.CUSTOM,
            tipo=TipoNotificacao.EMAIL,
            assunto='Olá %%NOMECOMPRADOR%%',
            corpo='Prezado(a) %%NOMECOMPRADOR%%, sua parcela %%PARCELA%% vence em %%DATAVENCIMENTO%%.'
        )

        contexto = {
            'NOMECOMPRADOR': 'João Silva',
            'PARCELA': '5/24',
            'DATAVENCIMENTO': '15/04/2026'
        }

        assunto, corpo, *_ = template.renderizar(contexto)

        assert assunto == 'Olá João Silva'
        assert 'João Silva' in corpo
        assert '5/24' in corpo
        assert '15/04/2026' in corpo

    def test_template_get_template_global(self):
        """get_template() retorna template global quando não há específico"""
        template = TemplateNotificacao.objects.create(
            nome='Template Global',
            codigo=TipoTemplate.BOLETO_CRIADO,
            tipo=TipoNotificacao.EMAIL,
            corpo='Corpo do template',
            imobiliaria=None,
            ativo=True
        )

        found = TemplateNotificacao.get_template(
            codigo=TipoTemplate.BOLETO_CRIADO,
            imobiliaria=None,
            tipo=TipoNotificacao.EMAIL
        )

        assert found == template
