"""
34.6 P3 — PWA: Portal do Comprador Instalável

Testa:
  34.6.1 — manifest.json: campos obrigatórios, tema, start_url
  34.6.2 — service worker: servido no path correto, Content-Type correto
  34.6.3 — API Web Push subscribe/unsubscribe
  PushSubscriptionPortal: unicidade por (acesso, endpoint)
"""
import json
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def comprador_logado(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ImovelFactory, CompradorFactory, UserFactory,
    )
    from portal_comprador.models import AcessoComprador

    imob = ImobiliariaFactory()
    comprador = CompradorFactory()
    user = UserFactory()

    acesso = AcessoComprador.objects.create(
        comprador=comprador,
        usuario=user,
        email_verificado=True,
        ativo=True,
    )
    client = Client()
    client.force_login(user)
    return acesso, client


# ---------------------------------------------------------------------------
# 34.6.1 — manifest.json
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestManifestJson:

    def test_retorna_200(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        assert resp.status_code == 200

    def test_content_type_manifest(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        assert 'manifest+json' in resp['Content-Type'] or 'application/json' in resp['Content-Type']

    def test_campos_obrigatorios(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        data = json.loads(resp.content)
        for campo in ['name', 'short_name', 'start_url', 'display', 'theme_color', 'icons']:
            assert campo in data, f'Campo ausente: {campo}'

    def test_start_url_aponta_para_portal(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        data = json.loads(resp.content)
        assert data['start_url'].startswith('/portal/')

    def test_theme_color_teal(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        data = json.loads(resp.content)
        assert '#008' in data['theme_color'].lower() or '00897b' in data['theme_color'].lower()

    def test_display_standalone(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        data = json.loads(resp.content)
        assert data['display'] == 'standalone'

    def test_icons_tem_192_e_512(self):
        resp = Client().get(reverse('portal_comprador:manifest'))
        data = json.loads(resp.content)
        tamanhos = {icon['sizes'] for icon in data['icons']}
        assert '192x192' in tamanhos
        assert '512x512' in tamanhos


# ---------------------------------------------------------------------------
# 34.6.2 — Service Worker
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestServiceWorker:

    def test_retorna_200(self):
        resp = Client().get(reverse('portal_comprador:service_worker'))
        assert resp.status_code == 200

    def test_content_type_javascript(self):
        resp = Client().get(reverse('portal_comprador:service_worker'))
        assert 'javascript' in resp['Content-Type']

    def test_header_service_worker_allowed(self):
        resp = Client().get(reverse('portal_comprador:service_worker'))
        assert resp.get('Service-Worker-Allowed') == '/portal/'

    def test_conteudo_tem_fetch_listener(self):
        resp = Client().get(reverse('portal_comprador:service_worker'))
        content = resp.content.decode('utf-8')
        assert 'fetch' in content
        assert 'install' in content

    def test_conteudo_tem_push_listener(self):
        resp = Client().get(reverse('portal_comprador:service_worker'))
        content = resp.content.decode('utf-8')
        assert 'push' in content

    def test_404_se_arquivo_nao_encontrado(self, monkeypatch):
        # Code-review fix: SW vazio quebraria PWA permanentemente (cache do browser)
        import os
        original_exists = os.path.exists
        def fake_exists(p):
            if 'portal-sw.js' in p:
                return False
            return original_exists(p)
        monkeypatch.setattr(os.path, 'exists', fake_exists)
        resp = Client().get(reverse('portal_comprador:service_worker'))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 34.6.3 — API Web Push subscribe/unsubscribe
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiPushSubscribe:

    def test_subscribe_requer_login(self):
        url = reverse('portal_comprador:api_push_subscribe')
        resp = Client().post(
            url,
            data=json.dumps({'endpoint': 'https://fcm.example.com/1', 'keys': {'p256dh': 'abc', 'auth': 'xyz'}}),
            content_type='application/json',
        )
        # Deve redirecionar para login ou retornar 403
        assert resp.status_code in (302, 403)

    def test_subscribe_cria_assinatura(self, comprador_logado):
        acesso, client = comprador_logado
        url = reverse('portal_comprador:api_push_subscribe')
        payload = {
            'endpoint': 'https://fcm.example.com/push/1',
            'keys': {'p256dh': 'chave_p256dh_teste', 'auth': 'auth_secret_teste'},
        }
        resp = client.post(url, data=json.dumps(payload), content_type='application/json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert data['criado'] is True

    def test_subscribe_idempotente(self, comprador_logado):
        from portal_comprador.models import PushSubscriptionPortal
        acesso, client = comprador_logado
        url = reverse('portal_comprador:api_push_subscribe')
        payload = {
            'endpoint': 'https://fcm.example.com/push/2',
            'keys': {'p256dh': 'chave', 'auth': 'secret'},
        }
        client.post(url, data=json.dumps(payload), content_type='application/json')
        resp = client.post(url, data=json.dumps(payload), content_type='application/json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert data['criado'] is False  # segunda chamada: update, não create
        count = PushSubscriptionPortal.objects.filter(acesso_comprador=acesso).count()
        assert count == 1

    def test_subscribe_payload_invalido_retorna_400(self, comprador_logado):
        _, client = comprador_logado
        url = reverse('portal_comprador:api_push_subscribe')
        resp = client.post(url, data='nao_json', content_type='application/json')
        assert resp.status_code == 400

    def test_unsubscribe_remove_assinatura(self, comprador_logado):
        from portal_comprador.models import PushSubscriptionPortal
        acesso, client = comprador_logado
        endpoint = 'https://fcm.example.com/push/del'

        # Criar assinatura
        PushSubscriptionPortal.objects.create(
            acesso_comprador=acesso,
            endpoint=endpoint,
            p256dh='k',
            auth='a',
        )

        url = reverse('portal_comprador:api_push_unsubscribe')
        resp = client.post(
            url,
            data=json.dumps({'endpoint': endpoint}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert data['removidas'] == 1
        assert PushSubscriptionPortal.objects.filter(endpoint=endpoint).count() == 0

    def test_unsubscribe_endpoint_inexistente_retorna_zero(self, comprador_logado):
        _, client = comprador_logado
        url = reverse('portal_comprador:api_push_unsubscribe')
        resp = client.post(
            url,
            data=json.dumps({'endpoint': 'https://nao.existe/'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['removidas'] == 0


# ---------------------------------------------------------------------------
# Model: PushSubscriptionPortal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPushSubscriptionPortalModel:

    def test_unicidade_por_acesso_e_endpoint(self, comprador_logado):
        from portal_comprador.models import PushSubscriptionPortal
        from django.db import IntegrityError
        acesso, _ = comprador_logado
        endpoint = 'https://push.example.com/1'
        PushSubscriptionPortal.objects.create(
            acesso_comprador=acesso, endpoint=endpoint, p256dh='k', auth='a'
        )
        with pytest.raises(IntegrityError):
            PushSubscriptionPortal.objects.create(
                acesso_comprador=acesso, endpoint=endpoint, p256dh='k2', auth='a2'
            )

    def test_str_tem_nome_comprador(self, comprador_logado):
        from portal_comprador.models import PushSubscriptionPortal
        acesso, _ = comprador_logado
        sub = PushSubscriptionPortal.objects.create(
            acesso_comprador=acesso,
            endpoint='https://push.test/2',
            p256dh='k',
            auth='a',
        )
        assert acesso.comprador.nome in str(sub)
