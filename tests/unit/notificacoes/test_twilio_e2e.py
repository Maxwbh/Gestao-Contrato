"""
Testes E2E para integração Twilio (SMS e WhatsApp)
Cobre envio, safeguard TEST_MODE e tratamento de erros

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from twilio.base.exceptions import TwilioRestException

from notificacoes.services import (
    ServicoSMS,
    ServicoWhatsApp,
    _destinatario_telefone_teste,
)


# =============================================================================
# SAFEGUARD TEST_MODE
# =============================================================================

class TestDestinatarioTelefoneTeste:
    """Testa a função de safeguard de redirecionamento em TEST_MODE"""

    def test_retorna_numero_original_sem_test_mode(self, settings):
        settings.TEST_MODE = False
        resultado = _destinatario_telefone_teste('+5511999999999')
        assert resultado == '+5511999999999'

    def test_redireciona_para_numero_teste_com_test_mode(self, settings):
        settings.TEST_MODE = True
        settings.TEST_RECIPIENT_PHONE = '+5531993257479'
        resultado = _destinatario_telefone_teste('+5511999999999')
        assert resultado == '+5531993257479'

    def test_nao_redireciona_se_ja_e_numero_teste(self, settings):
        settings.TEST_MODE = True
        settings.TEST_RECIPIENT_PHONE = '+5531993257479'
        resultado = _destinatario_telefone_teste('+5531993257479')
        assert resultado == '+5531993257479'

    def test_usa_default_quando_sem_configuracao(self, settings):
        settings.TEST_MODE = True
        # Remove TEST_RECIPIENT_PHONE para testar o default
        if hasattr(settings, 'TEST_RECIPIENT_PHONE'):
            delattr(settings, 'TEST_RECIPIENT_PHONE')
        resultado = _destinatario_telefone_teste('+5511999999999')
        assert resultado == '+5531993257479'  # default hardcoded


# =============================================================================
# SERVICO SMS
# =============================================================================

@pytest.mark.django_db
class TestServicoSMSEnvio:
    """Testes de envio de SMS via Twilio"""

    def test_enviar_sms_sucesso(self, mock_twilio_sms, settings):
        settings.TEST_MODE = False
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_PHONE_NUMBER = '+16067334990'

        sucesso, external_id = ServicoSMS.enviar('+5531999999999', 'Mensagem de teste')

        assert sucesso is True
        assert external_id  # message.sid capturado
        mock_twilio_sms.messages.create.assert_called_once()
        call_kwargs = mock_twilio_sms.messages.create.call_args
        assert call_kwargs.kwargs['body'] == 'Mensagem de teste'
        assert call_kwargs.kwargs['to'] == '+5531999999999'
        assert call_kwargs.kwargs['from_'] == '+16067334990'

    def test_enviar_sms_test_mode_redireciona(self, mock_twilio_sms, settings):
        settings.TEST_MODE = True
        settings.TEST_RECIPIENT_PHONE = '+5531993257479'
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_PHONE_NUMBER = '+16067334990'

        sucesso, external_id = ServicoSMS.enviar('+5511999888777', 'Cobrança parcela 5')

        assert sucesso is True
        call_kwargs = mock_twilio_sms.messages.create.call_args
        # Destinatário deve ser o número de teste, não o original
        assert call_kwargs.kwargs['to'] == '+5531993257479'

    def test_enviar_sms_propagates_twilio_exception(self, mock_twilio_error, settings):
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_PHONE_NUMBER = '+16067334990'

        with pytest.raises(TwilioRestException):
            ServicoSMS.enviar('+5531999999999', 'Mensagem teste')

    def test_enviar_sms_sem_credenciais_raises(self, settings):
        settings.TWILIO_ACCOUNT_SID = ''
        settings.TWILIO_AUTH_TOKEN = ''
        settings.TWILIO_PHONE_NUMBER = ''

        with pytest.raises((ValueError, Exception)):
            ServicoSMS.enviar('+5531999999999', 'Mensagem teste')

    def test_enviar_sms_mensagem_longa(self, mock_twilio_sms, settings):
        """SMS com mensagem de 160+ caracteres ainda é enviado"""
        settings.TEST_MODE = False
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_PHONE_NUMBER = '+16067334990'

        mensagem_longa = 'A' * 300
        sucesso, external_id = ServicoSMS.enviar('+5531999999999', mensagem_longa)

        assert sucesso is True
        call_kwargs = mock_twilio_sms.messages.create.call_args
        assert len(call_kwargs.kwargs['body']) == 300


# =============================================================================
# SERVICO WHATSAPP (Twilio)
# =============================================================================

@pytest.mark.django_db
class TestServicoWhatsAppTwilio:
    """Testes de envio de WhatsApp via Twilio"""

    def test_enviar_whatsapp_sucesso(self, mock_twilio_whatsapp, settings):
        settings.TEST_MODE = False
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_WHATSAPP_NUMBER = 'whatsapp:+16067334990'

        sucesso, external_id = ServicoWhatsApp.enviar('+5531999999999', 'Olá! Sua parcela vence amanhã.')

        assert sucesso is True
        assert external_id  # message.sid capturado
        mock_twilio_whatsapp.messages.create.assert_called_once()

    def test_enviar_whatsapp_adiciona_prefixo(self, mock_twilio_whatsapp, settings):
        """Número sem prefixo whatsapp: deve receber o prefixo automaticamente"""
        settings.TEST_MODE = False
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_WHATSAPP_NUMBER = 'whatsapp:+16067334990'

        ServicoWhatsApp.enviar('+5531999999999', 'Mensagem teste')

        call_kwargs = mock_twilio_whatsapp.messages.create.call_args
        assert call_kwargs.kwargs['to'].startswith('whatsapp:')
        assert call_kwargs.kwargs['from_'].startswith('whatsapp:')

    def test_enviar_whatsapp_test_mode_redireciona(self, mock_twilio_whatsapp, settings):
        settings.TEST_MODE = True
        settings.TEST_RECIPIENT_PHONE = '+5531993257479'
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_WHATSAPP_NUMBER = 'whatsapp:+16067334990'

        sucesso, external_id = ServicoWhatsApp.enviar('+5511888777666', 'Aviso vencimento')

        assert sucesso is True
        call_kwargs = mock_twilio_whatsapp.messages.create.call_args
        # Destinatário deve ser o número de teste com prefixo whatsapp:
        assert '+5531993257479' in call_kwargs.kwargs['to']

    def test_enviar_whatsapp_numero_ja_com_prefixo(self, mock_twilio_whatsapp, settings):
        """Número que já tem prefixo whatsapp: não deve duplicar o prefixo"""
        settings.TEST_MODE = False
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_WHATSAPP_NUMBER = 'whatsapp:+16067334990'

        ServicoWhatsApp.enviar('whatsapp:+5531999999999', 'Mensagem teste')

        call_kwargs = mock_twilio_whatsapp.messages.create.call_args
        to = call_kwargs.kwargs['to']
        assert to.count('whatsapp:') == 1

    def test_enviar_whatsapp_erro_twilio(self, mock_twilio_error, settings):
        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_WHATSAPP_NUMBER = 'whatsapp:+16067334990'

        with pytest.raises(TwilioRestException):
            ServicoWhatsApp.enviar('+5531999999999', 'Mensagem teste')

    def test_enviar_whatsapp_sem_credenciais_raises(self, settings):
        settings.TWILIO_ACCOUNT_SID = ''
        settings.TWILIO_AUTH_TOKEN = ''
        settings.TWILIO_WHATSAPP_NUMBER = ''

        with pytest.raises((ValueError, Exception)):
            ServicoWhatsApp.enviar('+5531999999999', 'Mensagem teste')


# =============================================================================
# FLUXO COMPLETO COM NOTIFICACAO MODEL
# =============================================================================

@pytest.mark.django_db
class TestFluxoCompletoNotificacao:
    """Testa o fluxo completo: criação de Notificação → envio via Twilio"""

    def test_notificacao_sms_enviada_com_sucesso(self, mock_twilio_sms, settings):
        from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao
        from notificacoes.tasks import processar_notificacoes_pendentes
        from django.utils import timezone
        from datetime import timedelta

        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_PHONE_NUMBER = '+16067334990'

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.SMS,
            destinatario='+5531999999999',
            assunto='',
            mensagem='Sua parcela vence em 3 dias.',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() - timedelta(minutes=1),
        )

        resultado = processar_notificacoes_pendentes()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ENVIADA
        assert resultado['enviadas'] >= 1

    def test_notificacao_whatsapp_enviada_com_sucesso(self, mock_twilio_whatsapp, settings):
        from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao
        from notificacoes.tasks import processar_notificacoes_pendentes
        from django.utils import timezone
        from datetime import timedelta

        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_WHATSAPP_NUMBER = 'whatsapp:+16067334990'

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.WHATSAPP,
            destinatario='+5531999999999',
            assunto='',
            mensagem='Aviso: parcela vencida.',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() - timedelta(minutes=1),
        )

        resultado = processar_notificacoes_pendentes()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ENVIADA
        assert resultado['enviadas'] >= 1

    def test_notificacao_sms_falha_twilio(self, mock_twilio_error, settings):
        """Notificação deve ser marcada como ERRO quando Twilio lança exceção"""
        from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao
        from notificacoes.tasks import processar_notificacoes_pendentes
        from django.utils import timezone
        from datetime import timedelta

        settings.TWILIO_ACCOUNT_SID = 'ACtest000000000000000000000000000000'
        settings.TWILIO_AUTH_TOKEN = 'test_auth_token_000000000000000000'
        settings.TWILIO_PHONE_NUMBER = '+16067334990'

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.SMS,
            destinatario='+5531999999999',
            assunto='',
            mensagem='Parcela vencida.',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() - timedelta(minutes=1),
        )

        resultado = processar_notificacoes_pendentes()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ERRO
        assert resultado['erros'] >= 1
