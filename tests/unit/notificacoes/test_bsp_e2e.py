"""
W-07 — BSP Brasileiro (Hablla / Poli Digital / Digisac)
========================================================
Cobre:
  - ServicoWhatsApp._enviar_bsp(): envio via API Meta-compatível
  - ServicoWhatsApp.enviar() roteamento para BSP
  - webhook_bsp() GET verificação hub.challenge
  - webhook_bsp() POST status update (delivery tracking)
  - webhook_bsp() POST inbound message → chatbot dispatch
  - webhook_bsp() assinatura X-Hub-Signature-256 inválida → 403
  - webhook_bsp() GET verify_token incorreto → 403
  - Campos obrigatórios ausentes → ValueError

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory
from django.urls import reverse

from notificacoes.models import ConfiguracaoWhatsApp, Notificacao
from notificacoes.services import ServicoWhatsApp


# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def config_bsp(db):
    return ConfiguracaoWhatsApp.objects.create(
        nome='BSP Teste',
        provedor='BSP',
        api_url='https://app.hablla.com',
        api_key='tok-hablla-123',
        phone_number_id='99887766554433',
        ativo=True,
    )


def _hub_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f'sha256={digest}'


# ─────────────────────────────────────────────────────────────────────────────
# ServicoWhatsApp._enviar_bsp
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEnviarBSP:

    def test_monta_url_e_payload_corretos(self, config_bsp):
        response_mock = MagicMock()
        response_mock.read.return_value = json.dumps(
            {'messages': [{'id': 'wamid.bsp001'}]}
        ).encode()
        response_mock.__enter__ = lambda s: s
        response_mock.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=response_mock) as mock_open:
            ok, ext_id = ServicoWhatsApp._enviar_bsp('+5511999999999', 'Olá BSP', config_bsp)

        assert ok is True
        assert ext_id == 'wamid.bsp001'

        req_arg = mock_open.call_args[0][0]
        assert req_arg.full_url == 'https://app.hablla.com/v1/99887766554433/messages'
        assert req_arg.get_header('Authorization') == 'Bearer tok-hablla-123'
        payload = json.loads(req_arg.data)
        assert payload['messaging_product'] == 'whatsapp'
        assert payload['to'] == '5511999999999'
        assert payload['type'] == 'text'
        assert payload['text']['body'] == 'Olá BSP'

    def test_normaliza_numero_sem_mais(self, config_bsp):
        response_mock = MagicMock()
        response_mock.read.return_value = json.dumps({'messages': [{'id': 'x'}]}).encode()
        response_mock.__enter__ = lambda s: s
        response_mock.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=response_mock) as mock_open:
            ServicoWhatsApp._enviar_bsp('5511888887777', 'teste', config_bsp)

        req_arg = mock_open.call_args[0][0]
        payload = json.loads(req_arg.data)
        assert payload['to'] == '5511888887777'

    def test_levanta_valueerror_sem_phone_number_id(self, db):
        config = ConfiguracaoWhatsApp(
            nome='BSP Sem ID',
            provedor='BSP',
            api_url='https://app.hablla.com',
            api_key='tok',
            phone_number_id='',
        )
        with pytest.raises(ValueError, match='phone_number_id'):
            ServicoWhatsApp._enviar_bsp('+5511999999999', 'msg', config)

    def test_levanta_valueerror_sem_api_url(self, db):
        config = ConfiguracaoWhatsApp(
            nome='BSP Sem URL',
            provedor='BSP',
            api_url='',
            api_key='tok',
            phone_number_id='123',
        )
        with pytest.raises(ValueError, match='api_url'):
            ServicoWhatsApp._enviar_bsp('+5511999999999', 'msg', config)

    def test_ext_id_vazio_quando_resposta_sem_messages(self, config_bsp):
        response_mock = MagicMock()
        response_mock.read.return_value = json.dumps({'error': 'bad'}).encode()
        response_mock.__enter__ = lambda s: s
        response_mock.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=response_mock):
            ok, ext_id = ServicoWhatsApp._enviar_bsp('+5511999999999', 'msg', config_bsp)

        assert ok is True
        assert ext_id == ''


# ─────────────────────────────────────────────────────────────────────────────
# ServicoWhatsApp.enviar() — roteamento BSP
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEnviarRoteamentoBSP:

    def test_roteia_para_enviar_bsp(self, config_bsp, settings):
        settings.TEST_MODE = False
        with patch.object(ServicoWhatsApp, '_enviar_bsp', return_value=(True, 'id1')) as mock_bsp:
            result = ServicoWhatsApp.enviar('+5511999999999', 'Mensagem BSP')

        mock_bsp.assert_called_once()
        ok, ext_id = result
        assert ok is True
        assert ext_id == 'id1'

    def test_nao_roteia_bsp_sem_config_ativa(self, db, settings):
        settings.TEST_MODE = False
        settings.TWILIO_ACCOUNT_SID = 'sid'
        settings.TWILIO_AUTH_TOKEN = 'tok'
        settings.TWILIO_WHATSAPP_NUMBER = '+1234'
        with patch.object(ServicoWhatsApp, '_enviar_twilio', return_value=(True, '')) as mock_twilio:
            ServicoWhatsApp.enviar('+5511999999999', 'fallback twilio')
        mock_twilio.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# webhook_bsp — GET (hub verification)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhookBSPGet:

    def test_challenge_retornado_com_verify_token_correto(self, client, config_bsp):
        url = reverse('notificacoes:webhook_bsp')
        resp = client.get(url, {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'tok-hablla-123',
            'hub.challenge': '9876543210',
        })
        assert resp.status_code == 200
        assert resp.content == b'9876543210'

    def test_403_quando_verify_token_errado(self, client, config_bsp):
        url = reverse('notificacoes:webhook_bsp')
        resp = client.get(url, {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'token-errado',
            'hub.challenge': '1234',
        })
        assert resp.status_code == 403

    def test_405_para_metodo_nao_permitido(self, client, config_bsp):
        url = reverse('notificacoes:webhook_bsp')
        resp = client.put(url)
        assert resp.status_code == 405


# ─────────────────────────────────────────────────────────────────────────────
# webhook_bsp — POST (status + inbound)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhookBSPPost:

    def _make_status_payload(self, wamid, status):
        return {
            'object': 'whatsapp_business_account',
            'entry': [{
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'statuses': [{'id': wamid, 'status': status, 'recipient_id': '5511999'}],
                        'messages': [],
                    },
                    'field': 'messages',
                }],
            }],
        }

    def test_atualiza_status_entrega_delivered(self, client, config_bsp, db):
        from tests.fixtures.factories import NotificacaoFactory
        notif = NotificacaoFactory(external_id='wamid.bsp-delivery', status_entrega='')

        body = json.dumps(self._make_status_payload('wamid.bsp-delivery', 'delivered')).encode()
        url = reverse('notificacoes:webhook_bsp')
        resp = client.post(url, data=body, content_type='application/json')

        assert resp.status_code == 200
        notif.refresh_from_db()
        assert notif.status_entrega == 'delivered'

    def test_atualiza_status_entrega_read(self, client, config_bsp, db):
        from tests.fixtures.factories import NotificacaoFactory
        notif = NotificacaoFactory(external_id='wamid.bsp-read', status_entrega='')

        body = json.dumps(self._make_status_payload('wamid.bsp-read', 'read')).encode()
        url = reverse('notificacoes:webhook_bsp')
        resp = client.post(url, data=body, content_type='application/json')

        assert resp.status_code == 200
        notif.refresh_from_db()
        assert notif.status_entrega == 'read'

    def test_retorna_200_sem_registros_correspondentes(self, client, config_bsp):
        body = json.dumps(self._make_status_payload('wamid.nao-existe', 'delivered')).encode()
        url = reverse('notificacoes:webhook_bsp')
        resp = client.post(url, data=body, content_type='application/json')
        assert resp.status_code == 200

    def test_400_para_payload_invalido(self, client, config_bsp):
        url = reverse('notificacoes:webhook_bsp')
        resp = client.post(url, data=b'nao-e-json{{{', content_type='application/json')
        assert resp.status_code == 400

    def test_assinatura_invalida_retorna_403(self, client, config_bsp):
        body = json.dumps(self._make_status_payload('id', 'sent')).encode()
        url = reverse('notificacoes:webhook_bsp')
        resp = client.post(
            url,
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=assinatura-errada',
        )
        assert resp.status_code == 403

    def test_assinatura_correta_aceita(self, client, config_bsp):
        body = json.dumps(self._make_status_payload('wamid.sig-ok', 'sent')).encode()
        sig = _hub_signature(body, 'tok-hablla-123')
        url = reverse('notificacoes:webhook_bsp')
        resp = client.post(
            url,
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        assert resp.status_code == 200

    def test_inbound_message_dispara_chatbot(self, client, config_bsp, db):
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {'phone_number_id': '99887766554433'},
                        'statuses': [],
                        'messages': [{
                            'from': '5511888887777',
                            'id': 'wamid.in01',
                            'type': 'text',
                            'text': {'body': 'olá'},
                        }],
                    },
                    'field': 'messages',
                }],
            }],
        }
        with patch('notificacoes.whatsapp_bot.WhatsAppBotService.processar') as mock_proc:
            body = json.dumps(payload).encode()
            url = reverse('notificacoes:webhook_bsp')
            resp = client.post(url, data=body, content_type='application/json')

        assert resp.status_code == 200
        mock_proc.assert_called_once()
        kwargs = mock_proc.call_args[1]
        assert kwargs['telefone'] == '5511888887777'
        assert kwargs['mensagem'] == 'olá'
