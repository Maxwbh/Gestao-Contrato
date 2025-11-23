"""
Serviços para envio de notificações

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
from .models import (
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp,
    TipoNotificacao
)

logger = logging.getLogger(__name__)


class ServicoEmail:
    """Serviço para envio de e-mails"""

    @staticmethod
    def enviar(destinatario, assunto, mensagem):
        """
        Envia um e-mail

        Args:
            destinatario (str): E-mail do destinatário
            assunto (str): Assunto do e-mail
            mensagem (str): Corpo do e-mail

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Buscar configuração ativa
            config = ConfiguracaoEmail.objects.filter(ativo=True).first()

            if not config:
                # Usar configurações padrão do settings
                send_mail(
                    subject=assunto,
                    message=mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[destinatario],
                    fail_silently=False,
                )
            else:
                # Usar configuração personalizada
                from django.core.mail import EmailMessage
                from django.core.mail import get_connection

                connection = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=config.host,
                    port=config.porta,
                    username=config.usuario,
                    password=config.senha,
                    use_tls=config.usar_tls,
                    use_ssl=config.usar_ssl,
                )

                email = EmailMessage(
                    subject=assunto,
                    body=mensagem,
                    from_email=f"{config.nome_remetente} <{config.email_remetente}>",
                    to=[destinatario],
                    connection=connection,
                )
                email.send()

            logger.info(f"E-mail enviado com sucesso para {destinatario}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar e-mail para {destinatario}: {str(e)}")
            raise


class ServicoSMS:
    """Serviço para envio de SMS"""

    @staticmethod
    def enviar(destinatario, mensagem):
        """
        Envia um SMS

        Args:
            destinatario (str): Número de telefone do destinatário (formato internacional)
            mensagem (str): Mensagem a ser enviada

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Buscar configuração ativa
            config = ConfiguracaoSMS.objects.filter(ativo=True).first()

            if not config:
                # Tentar usar configurações do settings
                account_sid = settings.TWILIO_ACCOUNT_SID
                auth_token = settings.TWILIO_AUTH_TOKEN
                numero_remetente = settings.TWILIO_PHONE_NUMBER

                if not all([account_sid, auth_token, numero_remetente]):
                    raise ValueError("Configuração de SMS não encontrada")
            else:
                account_sid = config.account_sid
                auth_token = config.auth_token
                numero_remetente = config.numero_remetente

            # Enviar via Twilio
            client = Client(account_sid, auth_token)

            message = client.messages.create(
                body=mensagem,
                from_=numero_remetente,
                to=destinatario
            )

            logger.info(f"SMS enviado com sucesso para {destinatario}. SID: {message.sid}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar SMS para {destinatario}: {str(e)}")
            raise


class ServicoWhatsApp:
    """Serviço para envio de mensagens via WhatsApp"""

    @staticmethod
    def enviar(destinatario, mensagem):
        """
        Envia uma mensagem via WhatsApp

        Args:
            destinatario (str): Número WhatsApp do destinatário (formato: whatsapp:+5511999999999)
            mensagem (str): Mensagem a ser enviada

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Buscar configuração ativa
            config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()

            if not config:
                # Tentar usar configurações do settings
                account_sid = settings.TWILIO_ACCOUNT_SID
                auth_token = settings.TWILIO_AUTH_TOKEN
                numero_remetente = settings.TWILIO_WHATSAPP_NUMBER

                if not all([account_sid, auth_token, numero_remetente]):
                    raise ValueError("Configuração de WhatsApp não encontrada")
            else:
                account_sid = config.account_sid
                auth_token = config.auth_token
                numero_remetente = config.numero_remetente

            # Garantir formato correto do destinatário
            if not destinatario.startswith('whatsapp:'):
                destinatario = f'whatsapp:{destinatario}'

            # Garantir formato correto do remetente
            if not numero_remetente.startswith('whatsapp:'):
                numero_remetente = f'whatsapp:{numero_remetente}'

            # Enviar via Twilio
            client = Client(account_sid, auth_token)

            message = client.messages.create(
                body=mensagem,
                from_=numero_remetente,
                to=destinatario
            )

            logger.info(f"WhatsApp enviado com sucesso para {destinatario}. SID: {message.sid}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp para {destinatario}: {str(e)}")
            raise


def enviar_notificacao(tipo, destinatario, assunto, mensagem):
    """
    Função unificada para envio de notificações

    Args:
        tipo (str): Tipo de notificação (EMAIL, SMS, WHATSAPP)
        destinatario (str): Destinatário da notificação
        assunto (str): Assunto (usado apenas para e-mail)
        mensagem (str): Mensagem a ser enviada

    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    try:
        if tipo == TipoNotificacao.EMAIL:
            return ServicoEmail.enviar(destinatario, assunto, mensagem)
        elif tipo == TipoNotificacao.SMS:
            return ServicoSMS.enviar(destinatario, mensagem)
        elif tipo == TipoNotificacao.WHATSAPP:
            return ServicoWhatsApp.enviar(destinatario, mensagem)
        else:
            raise ValueError(f"Tipo de notificação inválido: {tipo}")

    except Exception as e:
        logger.error(f"Erro ao enviar notificação {tipo} para {destinatario}: {str(e)}")
        return False
