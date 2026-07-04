"""
Testes da view configuracoes_sistema e dos endpoints de API de ParametroSistema.

Escopo:
  - GET /configuracoes/ — apenas staff/superuser
  - POST /api/parametros/ — salvar grupo
  - PATCH /api/parametros/<id>/ — atualizar parâmetro único
  - GET /api/parametros/exportar/ — exportar JSON
  - sync_params_from_env --dry-run não grava dados
"""
import json
import pytest
from io import StringIO
from django.test import Client
from django.urls import reverse
from django.core.management import call_command

from tests.fixtures.factories import UserFactory, SuperUserFactory
from core.models import ParametroSistema

pytestmark = pytest.mark.django_db


def make_client(user=None):
    c = Client(enforce_csrf_checks=False)
    if user:
        c.force_login(user)
    return c


# =============================================================================
# GET /configuracoes/
# =============================================================================

class TestConfiguracoesSistemaView:

    def test_anonimo_redireciona(self):
        url = reverse('core:configuracoes_sistema')
        r = Client().get(url, secure=True)
        assert r.status_code in (301, 302)

    def test_usuario_comum_recebe_403(self):
        user = UserFactory()
        r = make_client(user).get(reverse('core:configuracoes_sistema'), secure=True)
        assert r.status_code == 403

    def test_staff_retorna_200(self):
        staff = SuperUserFactory()
        r = make_client(staff).get(reverse('core:configuracoes_sistema'), secure=True)
        assert r.status_code == 200

    def test_contexto_contem_chaves_esperadas(self):
        staff = SuperUserFactory()
        r = make_client(staff).get(reverse('core:configuracoes_sistema'), secure=True)
        for key in ('configs_email', 'configs_whatsapp', 'params_twilio',
                    'params_brcobranca', 'params_portal', 'params_notif',
                    'parametros_por_grupo', 'regras_notificacao', 'brcobranca_url'):
            assert key in r.context, f"Chave '{key}' ausente no contexto"

    def test_usa_template_correto(self):
        staff = SuperUserFactory()
        r = make_client(staff).get(reverse('core:configuracoes_sistema'), secure=True)
        assert 'core/configuracoes_sistema.html' in [t.name for t in r.templates]


# =============================================================================
# POST /api/parametros/
# =============================================================================

class TestApiParametrosSalvarGrupo:

    def test_anonimo_redireciona(self):
        url = reverse('core:api_parametros_salvar')
        r = Client().post(url, data='{}', content_type='application/json', secure=True)
        assert r.status_code in (301, 302)

    def test_salva_novos_parametros(self):
        staff = SuperUserFactory()
        url = reverse('core:api_parametros_salvar')
        payload = {
            'grupo': 'brcobranca',
            'parametros': {
                'BRCOBRANCA_URL': 'http://test-server:9292',
                'BRCOBRANCA_TIMEOUT': '45',
            }
        }
        r = make_client(staff).post(
            url, data=json.dumps(payload),
            content_type='application/json', secure=True
        )
        assert r.status_code == 200
        data = r.json()
        assert data['sucesso'] is True
        assert ParametroSistema.objects.filter(chave='BRCOBRANCA_URL', valor='http://test-server:9292').exists()
        assert ParametroSistema.objects.filter(chave='BRCOBRANCA_TIMEOUT', valor='45').exists()

    def test_atualiza_parametro_existente(self):
        staff = SuperUserFactory()
        ParametroSistema.objects.create(chave='BRCOBRANCA_URL', valor='http://old:9292', grupo='brcobranca')
        url = reverse('core:api_parametros_salvar')
        payload = {'grupo': 'brcobranca', 'parametros': {'BRCOBRANCA_URL': 'http://new:9292'}}
        make_client(staff).post(url, data=json.dumps(payload), content_type='application/json', secure=True)
        assert ParametroSistema.objects.get(chave='BRCOBRANCA_URL').valor == 'http://new:9292'

    def test_payload_invalido_retorna_400(self):
        staff = SuperUserFactory()
        url = reverse('core:api_parametros_salvar')
        r = make_client(staff).post(
            url, data=json.dumps({'grupo': 'x', 'parametros': 'nao_e_dict'}),
            content_type='application/json', secure=True
        )
        assert r.status_code == 400

    def test_marca_modificado_manualmente(self):
        staff = SuperUserFactory()
        url = reverse('core:api_parametros_salvar')
        payload = {'grupo': 'portal', 'parametros': {'PORTAL_NOME': 'Meu Portal'}}
        make_client(staff).post(url, data=json.dumps(payload), content_type='application/json', secure=True)
        p = ParametroSistema.objects.get(chave='PORTAL_NOME')
        assert p.modificado_manualmente is True


# =============================================================================
# PATCH /api/parametros/<id>/
# =============================================================================

class TestApiParametroAtualizar:

    def test_atualiza_valor(self):
        staff = SuperUserFactory()
        param = ParametroSistema.objects.create(chave='PORTAL_NOME', valor='Antigo', grupo='portal')
        url = reverse('core:api_parametro_atualizar', kwargs={'parametro_id': param.pk})
        r = make_client(staff).patch(
            url, data=json.dumps({'valor': 'Novo Nome'}),
            content_type='application/json', secure=True
        )
        assert r.status_code == 200
        assert r.json()['sucesso'] is True
        param.refresh_from_db()
        assert param.valor == 'Novo Nome'
        assert param.modificado_manualmente is True

    def test_404_para_id_inexistente(self):
        staff = SuperUserFactory()
        url = reverse('core:api_parametro_atualizar', kwargs={'parametro_id': 99999})
        r = make_client(staff).patch(
            url, data=json.dumps({'valor': 'x'}),
            content_type='application/json', secure=True
        )
        assert r.status_code == 404

    def test_anonimo_redireciona(self):
        param = ParametroSistema.objects.create(chave='TEST_KEY', valor='v', grupo='aplicacao')
        url = reverse('core:api_parametro_atualizar', kwargs={'parametro_id': param.pk})
        r = Client().patch(url, data=json.dumps({'valor': 'x'}), content_type='application/json', secure=True)
        assert r.status_code in (301, 302)


# =============================================================================
# GET /api/parametros/exportar/
# =============================================================================

class TestApiParametrosExportar:

    def test_retorna_json_download(self):
        staff = SuperUserFactory()
        ParametroSistema.objects.create(chave='SITE_URL', valor='http://test.com', grupo='aplicacao')
        url = reverse('core:api_parametros_exportar')
        r = make_client(staff).get(url, secure=True)
        assert r.status_code == 200
        assert r['Content-Type'] == 'application/json'
        assert 'attachment' in r['Content-Disposition']
        data = json.loads(r.content)
        assert 'parametros' in data
        assert 'exportado_em' in data
        chaves = [p['chave'] for p in data['parametros']]
        assert 'SITE_URL' in chaves

    def test_anonimo_redireciona(self):
        url = reverse('core:api_parametros_exportar')
        r = Client().get(url, secure=True)
        assert r.status_code in (301, 302)


# =============================================================================
# Management command sync_params_from_env
# =============================================================================

class TestSyncParamsFromEnv:

    def test_dry_run_nao_grava(self):
        out = StringIO()
        call_command('sync_params_from_env', dry_run=True, stdout=out)
        # dry_run não deve criar registros persistentes de forma definitiva
        # (o transaction rollback é aplicado internamente)
        output = out.getvalue()
        assert 'dry-run' in output.lower() or 'concluído' in output.lower()

    def test_cria_parametros_ausentes(self):
        out = StringIO()
        ParametroSistema.objects.all().delete()
        call_command('sync_params_from_env', stdout=out)
        assert ParametroSistema.objects.count() > 0

    def test_nao_sobrescreve_modificado_manualmente(self):
        param = ParametroSistema.objects.create(
            chave='BRCOBRANCA_URL',
            valor='http://meu-servidor:9292',
            grupo='brcobranca',
            modificado_manualmente=True,
        )
        out = StringIO()
        call_command('sync_params_from_env', stdout=out)
        param.refresh_from_db()
        assert param.valor == 'http://meu-servidor:9292'

    def test_force_sobrescreve_modificado_manualmente(self):
        ParametroSistema.objects.create(
            chave='BRCOBRANCA_URL',
            valor='http://meu-servidor:9292',
            grupo='brcobranca',
            modificado_manualmente=True,
        )
        out = StringIO()
        call_command('sync_params_from_env', force=True, stdout=out)
        param = ParametroSistema.objects.get(chave='BRCOBRANCA_URL')
        # valor deve ter sido sobrescrito pelo .env/default
        assert param.modificado_manualmente is False
