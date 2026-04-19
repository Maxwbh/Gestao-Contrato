"""
Serviços para envio de notificações

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import logging
from uuid import uuid4
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
from .models import (
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp,
    TipoNotificacao
)

logger = logging.getLogger(__name__)


# =============================================================================
# SAFEGUARD DE AMBIENTE DE TESTE
# =============================================================================

def _destinatario_email_teste(destinatario_real: str) -> str:
    """
    Se TEST_MODE=True, substitui o e-mail pelo endereço de teste configurado.
    Registra um aviso indicando o destinatário original.
    """
    if getattr(settings, 'TEST_MODE', False):
        destino_teste = getattr(settings, 'TEST_RECIPIENT_EMAIL', 'receber@msbrasil.inf.br')
        if destinatario_real != destino_teste:
            logger.warning(
                '[TEST_MODE] E-mail redirecionado: %s → %s',
                destinatario_real, destino_teste
            )
        return destino_teste
    return destinatario_real


def _destinatario_telefone_teste(destinatario_real: str) -> str:
    """
    Se TEST_MODE=True, substitui o número pelo telefone de teste configurado.
    Registra um aviso indicando o destinatário original.
    """
    if getattr(settings, 'TEST_MODE', False):
        destino_teste = getattr(settings, 'TEST_RECIPIENT_PHONE', '+5531993257479')
        if destinatario_real != destino_teste:
            logger.warning(
                '[TEST_MODE] SMS/WhatsApp redirecionado: %s → %s',
                destinatario_real, destino_teste
            )
        return destino_teste
    return destinatario_real


class ServicoEmail:
    """Serviço para envio de e-mails"""

    @staticmethod
    def enviar(destinatario, assunto, mensagem):
        """
        Envia um e-mail.

        Returns:
            tuple[bool, str]: (True, message_id) em caso de sucesso; raise em caso de falha.
            O message_id é o Message-ID gerado para rastreamento (UUID@domínio).
        """
        try:
            # Safeguard: em TEST_MODE redireciona para e-mail de teste
            destinatario = _destinatario_email_teste(destinatario)

            # Gerar Message-ID único para rastreamento
            message_id = f"<{uuid4()}@gestao-contrato>"

            # Cabeçalhos: Message-ID + Return-Path (bounce monitoring)
            headers = {'Message-ID': message_id}
            bounce_addr = getattr(settings, 'BOUNCE_EMAIL_ADDRESS', '')
            if bounce_addr:
                headers['Return-Path'] = bounce_addr
                headers['Errors-To'] = bounce_addr

            # Buscar configuração ativa
            config = ConfiguracaoEmail.objects.filter(ativo=True).first()

            if not config:
                # Usar configurações padrão do settings
                from django.core.mail import EmailMessage as _EmailMessage
                email = _EmailMessage(
                    subject=assunto,
                    body=mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[destinatario],
                    headers=headers,
                )
                email.send(fail_silently=False)
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
                    headers=headers,
                )
                email.send()

            logger.info("E-mail enviado com sucesso para %s (id=%s)", destinatario, message_id)
            return True, message_id

        except Exception as e:
            logger.exception("Erro ao enviar e-mail para %s: %s", destinatario, e)
            raise


class ServicoSMS:
    """Serviço para envio de SMS"""

    @staticmethod
    def enviar(destinatario, mensagem):
        """
        Envia um SMS via Twilio.

        Returns:
            tuple[bool, str]: (True, twilio_sid) em caso de sucesso; raise em caso de falha.
        """
        try:
            # Safeguard: em TEST_MODE redireciona para telefone de teste
            destinatario = _destinatario_telefone_teste(destinatario)

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

            kwargs = {
                'body': mensagem,
                'from_': numero_remetente,
                'to': destinatario,
            }
            # Registrar callback de status se configurado (para rastreamento de entrega)
            status_callback = getattr(settings, 'TWILIO_STATUS_CALLBACK_URL', '')
            if status_callback:
                kwargs['status_callback'] = status_callback

            message = client.messages.create(**kwargs)

            logger.info("SMS enviado para %s. SID: %s", destinatario, message.sid)
            return True, message.sid

        except Exception as e:
            logger.exception("Erro ao enviar SMS para %s: %s", destinatario, e)
            raise


class ServicoWhatsApp:
    """Serviço para envio de mensagens via WhatsApp (Twilio, Meta, Evolution API, Z-API)"""

    @staticmethod
    def enviar(destinatario, mensagem):
        """
        Envia mensagem via WhatsApp usando o provedor configurado.

        Args:
            destinatario (str): Número do destinatário (com ou sem prefixo whatsapp:).
                                Evolution/Z-API: somente dígitos ou +55... aceitos.
            mensagem (str): Texto da mensagem.

        Returns:
            bool: True se enviado com sucesso.
        """
        try:
            # Safeguard: em TEST_MODE redireciona para telefone de teste
            destinatario = _destinatario_telefone_teste(destinatario)

            config = ConfiguracaoWhatsApp.objects.filter(ativo=True).first()

            if not config:
                # Fallback para Twilio via settings
                return ServicoWhatsApp._enviar_twilio(
                    destinatario, mensagem,
                    account_sid=getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
                    auth_token=getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
                    numero_remetente=getattr(settings, 'TWILIO_WHATSAPP_NUMBER', ''),
                )

            provedor = config.provedor

            if provedor == 'TWILIO':
                return ServicoWhatsApp._enviar_twilio(
                    destinatario, mensagem,
                    account_sid=config.account_sid,
                    auth_token=config.auth_token,
                    numero_remetente=config.numero_remetente,
                )
            elif provedor == 'META':
                return ServicoWhatsApp._enviar_meta(destinatario, mensagem, config)
            elif provedor == 'EVOLUTION':
                return ServicoWhatsApp._enviar_evolution(destinatario, mensagem, config)
            elif provedor == 'ZAPI':
                return ServicoWhatsApp._enviar_zapi(destinatario, mensagem, config)
            else:
                raise ValueError(f"Provedor WhatsApp desconhecido: {provedor}")

        except Exception as e:
            logger.exception("Erro ao enviar WhatsApp para %s: %s", destinatario, e)
            raise

    @staticmethod
    def _normalizar_numero(numero):
        """Remove tudo exceto dígitos e o '+' inicial."""
        import re
        # Remove prefixo whatsapp: se presente
        numero = re.sub(r'^whatsapp:', '', numero.strip())
        return numero

    @staticmethod
    def _enviar_twilio(destinatario, mensagem, account_sid, auth_token, numero_remetente):
        if not all([account_sid, auth_token, numero_remetente]):
            raise ValueError("Configuração Twilio incompleta (account_sid/auth_token/numero_remetente)")

        if not destinatario.startswith('whatsapp:'):
            destinatario = f'whatsapp:{destinatario}'
        if not numero_remetente.startswith('whatsapp:'):
            numero_remetente = f'whatsapp:{numero_remetente}'

        client = Client(account_sid, auth_token)

        kwargs = {'body': mensagem, 'from_': numero_remetente, 'to': destinatario}
        status_callback = getattr(settings, 'TWILIO_STATUS_CALLBACK_URL', '')
        if status_callback:
            kwargs['status_callback'] = status_callback

        message = client.messages.create(**kwargs)
        logger.info("WhatsApp (Twilio) enviado para %s. SID: %s", destinatario, message.sid)
        return True, message.sid

    @staticmethod
    def _enviar_meta(destinatario, mensagem, config):
        """Meta (Cloud API) — envia texto simples via /messages."""
        import urllib.request
        import json as _json
        numero = ServicoWhatsApp._normalizar_numero(destinatario).lstrip('+')
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": mensagem},
        }
        url = f"{config.api_url.rstrip('/')}/messages"
        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = _json.loads(resp.read())
        logger.info("WhatsApp (Meta) enviado para %s. Response: %s", numero, body)
        # Extrair ID da mensagem Meta (messages[0].id)
        ext_id = ''
        try:
            ext_id = body.get('messages', [{}])[0].get('id', '')
        except Exception:
            pass
        return True, ext_id

    @staticmethod
    def _enviar_evolution(destinatario, mensagem, config):
        """
        Evolution API v2 — POST /message/sendText/{instancia}
        Headers: apikey: <config.api_key>
        Body: {"number": "<numero>", "text": "<mensagem>"}
        """
        import urllib.request
        import json as _json
        if not all([config.api_url, config.api_key, config.instancia]):
            raise ValueError("Evolution API: api_url, api_key e instancia são obrigatórios")

        numero = ServicoWhatsApp._normalizar_numero(destinatario)
        # Evolution aceita formato: 5511999999999 (sem +)
        numero = numero.lstrip('+')

        url = f"{config.api_url.rstrip('/')}/message/sendText/{config.instancia}"
        payload = {"number": numero, "text": mensagem}
        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "apikey": config.api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = _json.loads(resp.read())
        logger.info("WhatsApp (Evolution) enviado para %s. Response: %s", numero, body)
        ext_id = ''
        try:
            ext_id = body.get('key', {}).get('id', '') or str(body.get('status', ''))
        except Exception:
            pass
        return True, ext_id

    @staticmethod
    def _enviar_zapi(destinatario, mensagem, config):
        """
        Z-API — POST /instances/{instancia}/token/{api_key}/send-text
        Header: Client-Token: <config.client_token>
        Body: {"phone": "<numero>", "message": "<mensagem>"}
        """
        import urllib.request
        import json as _json
        if not all([config.api_url, config.api_key, config.instancia]):
            raise ValueError("Z-API: api_url, api_key e instancia são obrigatórios")

        numero = ServicoWhatsApp._normalizar_numero(destinatario).lstrip('+')

        base = config.api_url.rstrip('/')
        url = f"{base}/instances/{config.instancia}/token/{config.api_key}/send-text"
        payload = {"phone": numero, "message": mensagem}
        headers = {"Content-Type": "application/json"}
        if config.client_token:
            headers["Client-Token"] = config.client_token

        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = _json.loads(resp.read())
        logger.info("WhatsApp (Z-API) enviado para %s. Response: %s", numero, body)
        ext_id = ''
        try:
            ext_id = body.get('zaapId', '') or body.get('messageId', '')
        except Exception:
            pass
        return True, ext_id


def enviar_notificacao(tipo, destinatario, assunto, mensagem):
    """
    Função unificada para envio de notificações.

    Args:
        tipo (str): Tipo de notificação (EMAIL, SMS, WHATSAPP)
        destinatario (str): Destinatário da notificação
        assunto (str): Assunto (usado apenas para e-mail)
        mensagem (str): Mensagem a ser enviada

    Returns:
        tuple[bool, str]: (sucesso, external_id).
            external_id é o Twilio MessageSid (SMS/WhatsApp) ou Message-ID do e-mail.
            Retorna (False, '') em caso de exceção.
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
        logger.exception("Erro ao enviar notificação %s para %s: %s", tipo, destinatario, e)
        return False, ''
