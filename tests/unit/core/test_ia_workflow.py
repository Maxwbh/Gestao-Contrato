"""Testes do Workflow de IA (cascade de modelos configurável)."""
import json
import pytest
from django.urls import reverse


# ─── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def staff_client(db, client):
    from tests.fixtures.factories import SuperUserFactory
    user = SuperUserFactory()
    client.force_login(user)
    return client


@pytest.fixture
def wf(db):
    from core.models import WorkflowIA
    return WorkflowIA.objects.create(nome='WF Teste')


@pytest.fixture
def wf_com_tiers(wf):
    from core.models import WorkflowIATier
    WorkflowIATier.objects.create(workflow=wf, modelo='claude-haiku-4-5-20251001', ordem=1)
    WorkflowIATier.objects.create(workflow=wf, modelo='claude-sonnet-4-6', ordem=2)
    return wf


# ─── Model ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWorkflowIAModel:
    def test_criado_inativo(self, wf):
        assert wf.ativo is False

    def test_str_inativo(self, wf):
        assert '[ATIVO]' not in str(wf)

    def test_str_ativo(self, wf):
        wf.ativo = True
        assert '[ATIVO]' in str(wf)

    def test_ativar_desativa_outros(self, db):
        from core.models import WorkflowIA
        wf1 = WorkflowIA.objects.create(nome='A', ativo=True)
        wf2 = WorkflowIA.objects.create(nome='B')
        wf2.ativar()
        wf1.refresh_from_db()
        assert not wf1.ativo
        assert wf2.ativo

    def test_apenas_um_ativo(self, db):
        from core.models import WorkflowIA
        wf1 = WorkflowIA.objects.create(nome='A')
        wf2 = WorkflowIA.objects.create(nome='B')
        wf1.ativar()
        wf2.ativar()
        assert WorkflowIA.objects.filter(ativo=True).count() == 1


# ─── _carregar_tiers_workflow ────────────────────────────────────────────────

@pytest.mark.django_db
class TestCarregarTiersWorkflow:
    def test_sem_workflow_ativo_retorna_fallback(self):
        from contratos.services.importacao_ia import _carregar_tiers_workflow, _TIERS_CLAUDE
        result = _carregar_tiers_workflow()
        assert result == _TIERS_CLAUDE

    def test_workflow_ativo_retorna_db(self, wf_com_tiers):
        from contratos.services.importacao_ia import _carregar_tiers_workflow
        wf_com_tiers.ativar()
        result = _carregar_tiers_workflow()
        assert result == ('claude-haiku-4-5-20251001', 'claude-sonnet-4-6')

    def test_workflow_ativo_sem_tiers_retorna_fallback(self, wf):
        from contratos.services.importacao_ia import _carregar_tiers_workflow, _TIERS_CLAUDE
        wf.ativar()
        result = _carregar_tiers_workflow()
        assert result == _TIERS_CLAUDE

    def test_tier_desabilitado_ignorado(self, wf_com_tiers):
        from contratos.services.importacao_ia import _carregar_tiers_workflow
        from core.models import WorkflowIATier
        wf_com_tiers.ativar()
        WorkflowIATier.objects.filter(workflow=wf_com_tiers, ordem=1).update(habilitado=False)
        result = _carregar_tiers_workflow()
        assert 'claude-haiku-4-5-20251001' not in result
        assert 'claude-sonnet-4-6' in result


# ─── Views ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIaWorkflowViews:
    def test_list_requer_login(self, client):
        r = client.get(reverse('core:ia_workflow_list'))
        assert r.status_code == 302

    def test_list_200(self, staff_client):
        r = staff_client.get(reverse('core:ia_workflow_list'))
        assert r.status_code == 200

    def test_novo_cria_workflow(self, staff_client, db):
        from core.models import WorkflowIA
        r = staff_client.post(reverse('core:ia_workflow_novo'), {'nome': 'WF via test'})
        assert r.status_code == 302
        wf = WorkflowIA.objects.get(nome='WF via test')
        assert wf.tiers.count() == 3

    def test_editar_get_200(self, staff_client, wf):
        r = staff_client.get(reverse('core:ia_workflow_editar', kwargs={'pk': wf.pk}))
        assert r.status_code == 200

    def test_editar_post_salva_nome(self, staff_client, wf):
        staff_client.post(
            reverse('core:ia_workflow_editar', kwargs={'pk': wf.pk}),
            {'nome': 'Novo Nome', 'descricao': ''},
        )
        wf.refresh_from_db()
        assert wf.nome == 'Novo Nome'

    def test_ativar_post_json(self, staff_client, wf):
        r = staff_client.post(
            reverse('core:ia_workflow_ativar', kwargs={'pk': wf.pk}),
            content_type='application/json',
            data='{}',
        )
        assert r.status_code == 200
        assert r.json()['status'] == 'ok'
        wf.refresh_from_db()
        assert wf.ativo

    def test_excluir_ativo_bloqueado(self, staff_client, wf):
        wf.ativar()
        r = staff_client.post(
            reverse('core:ia_workflow_excluir', kwargs={'pk': wf.pk}),
            content_type='application/json',
            data='{}',
        )
        assert r.status_code == 400

    def test_excluir_inativo_ok(self, staff_client, wf):
        from core.models import WorkflowIA
        pk = wf.pk
        r = staff_client.post(
            reverse('core:ia_workflow_excluir', kwargs={'pk': pk}),
            content_type='application/json',
            data='{}',
        )
        assert r.status_code == 200
        assert not WorkflowIA.objects.filter(pk=pk).exists()

    def test_tiers_salvar_json(self, staff_client, wf):
        url = reverse('core:ia_workflow_tiers_salvar', kwargs={'pk': wf.pk})
        payload = {'tiers': [
            {'modelo': 'claude-haiku-4-5-20251001', 'habilitado': True},
            {'modelo': 'claude-opus-4-8', 'habilitado': True},
        ]}
        r = staff_client.post(url, content_type='application/json', data=json.dumps(payload))
        assert r.status_code == 200
        assert r.json()['count'] == 2
        assert wf.tiers.count() == 2

    def test_tiers_salvar_lista_vazia_apaga_tiers(self, staff_client, wf_com_tiers):
        url = reverse('core:ia_workflow_tiers_salvar', kwargs={'pk': wf_com_tiers.pk})
        r = staff_client.post(url, content_type='application/json', data=json.dumps({'tiers': []}))
        assert r.status_code == 200
        assert wf_com_tiers.tiers.count() == 0

    def test_tiers_salvar_modelo_invalido_ignorado(self, staff_client, wf):
        url = reverse('core:ia_workflow_tiers_salvar', kwargs={'pk': wf.pk})
        payload = {'tiers': [{'modelo': 'gpt-injetado', 'habilitado': True}]}
        r = staff_client.post(url, content_type='application/json', data=json.dumps(payload))
        assert r.status_code == 200
        assert wf.tiers.count() == 0  # modelo inválido ignorado

    def test_desativar_post_json_ok(self, staff_client, wf):
        wf.ativar()
        r = staff_client.post(
            reverse('core:ia_workflow_desativar', kwargs={'pk': wf.pk}),
            content_type='application/json',
            data='{}',
        )
        assert r.status_code == 200
        wf.refresh_from_db()
        assert not wf.ativo

    def test_reordenar_atualiza_ordem(self, staff_client, wf_com_tiers):
        tiers = list(wf_com_tiers.tiers.order_by('ordem'))
        assert tiers[0].modelo == 'claude-haiku-4-5-20251001'
        assert tiers[1].modelo == 'claude-sonnet-4-6'
        # Inverte a ordem
        ids_invertidos = [str(tiers[1].pk), str(tiers[0].pk)]
        r = staff_client.post(
            reverse('core:ia_workflow_tiers_reordenar', kwargs={'pk': wf_com_tiers.pk}),
            content_type='application/json',
            data=json.dumps({'ids': ids_invertidos}),
        )
        assert r.status_code == 200
        tiers_atualizados = list(wf_com_tiers.tiers.order_by('ordem'))
        assert tiers_atualizados[0].modelo == 'claude-sonnet-4-6'
        assert tiers_atualizados[1].modelo == 'claude-haiku-4-5-20251001'

    def test_reordenar_id_invalido_retorna_400(self, staff_client, wf):
        r = staff_client.post(
            reverse('core:ia_workflow_tiers_reordenar', kwargs={'pk': wf.pk}),
            content_type='application/json',
            data=json.dumps({'ids': ['nao-e-numero']}),
        )
        assert r.status_code == 400
