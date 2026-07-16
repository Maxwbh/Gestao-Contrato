"""
Fase 4 Boleto-API — webhook robusto: HMAC, idempotência por event_id, match por
cobranca_id/ext_ref/txid, mapa de status normalizado e ack de pix_automatico.
"""
import hashlib
import hmac
import json

import pytest
from django.urls import reverse

from financeiro.models import Parcela, EventoCobrancaApi, StatusCobranca, StatusBoleto

SECRET = 'test-webhook-secret'


def _sign(body: bytes, secret=SECRET):
    return 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(client, payload, sign=True, secret=SECRET):
    body = json.dumps(payload).encode()
    extra = {'HTTP_X_SIGNATURE': _sign(body, secret)} if sign else {}
    return client.post(reverse('financeiro:webhook_boleto_api'), data=body,
                       content_type='application/json', **extra)


def _parcela(**campos):
    from tests.fixtures.factories import ParcelaFactory
    p = ParcelaFactory(pago=False, status_boleto=StatusBoleto.REGISTRADO, **campos)
    return p


@pytest.mark.django_db
class TestWebhookFase4:
    def test_assinatura_invalida_401(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        body = json.dumps({'id': 'X'}).encode()
        r = client.post(reverse('financeiro:webhook_boleto_api'), data=body,
                        content_type='application/json', HTTP_X_SIGNATURE='sha256=errado')
        assert r.status_code == 401

    def test_liquidado_baixa_e_status(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        p = _parcela(cobranca_id='C1')
        r = _post(client, {'id': 'C1', 'status': 'liquidado', 'event': 'cobranca.atualizada',
                           'valor': '7500.00', 'paid_at': '2026-02-01T10:00:00'})
        assert r.status_code == 200 and r.json()['status'] == 'baixado'
        p.refresh_from_db()
        assert p.pago is True and p.status_cobranca == StatusCobranca.LIQUIDADA

    def test_idempotencia_por_event_id(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        _parcela(cobranca_id='C2')
        ev = {'id': 'C2', 'status': 'liquidado', 'event': 'cobranca.atualizada',
              'valor': '7500.00', 'event_id': 'EVT-1'}
        assert _post(client, ev).json()['status'] == 'baixado'
        assert _post(client, ev).json()['status'] == 'duplicado'

    def test_match_por_ext_ref(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        p = _parcela(cobranca_id='', ext_ref='E9')
        r = _post(client, {'ext_ref': 'E9', 'status': 'liquidado',
                           'event': 'cobranca.atualizada', 'valor': '7500.00'})
        assert r.json()['status'] == 'baixado'
        p.refresh_from_db(); assert p.pago is True

    def test_match_por_txid_pix_recebido(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        p = _parcela(cobranca_id='', pix_txid='TX9')
        r = _post(client, {'txid': 'TX9', 'event': 'pix.recebido', 'valor': '7500.00'})
        assert r.json()['status'] == 'baixado'
        p.refresh_from_db()
        assert p.pago is True and p.status_cobranca == StatusCobranca.LIQUIDADA

    def test_registrado_atualiza_sem_baixa(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        p = _parcela(cobranca_id='C3')
        r = _post(client, {'id': 'C3', 'status': 'registrado', 'event': 'cobranca.atualizada'})
        assert r.json()['status'] == 'atualizado'
        p.refresh_from_db()
        assert p.pago is False and p.status_cobranca == StatusCobranca.REGISTRADA

    def test_pix_automatico_ignorado(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        r = _post(client, {'event': 'pix_automatico.recorrencia', 'status': 'APROVADA',
                           'idRec': 'RN-1'})
        assert r.status_code == 200 and r.json()['status'] == 'ignorado'

    def test_sem_identificador_400(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        r = _post(client, {'status': 'liquidado', 'event': 'cobranca.atualizada'})
        assert r.status_code == 400

    def test_sem_parcela(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        r = _post(client, {'id': 'NAO-EXISTE', 'status': 'liquidado',
                           'event': 'cobranca.atualizada'})
        assert r.json()['status'] == 'sem_parcela'
