"""
Testes do helper de breadcrumbs e da renderização em views principais.

F1-01 / F1-05: breadcrumb universal aplicado em todos os fluxos de cadastro,
listagem e detalhe.
"""
import pytest
from django.test import Client
from django.urls import reverse

from tests.fixtures.factories import (
    SuperUserFactory, ImobiliariaFactory, CompradorFactory,
    ImovelFactory, ContratoFactory,
)
from core.breadcrumbs import bc, bc_dashboard

pytestmark = pytest.mark.django_db


def staff_client():
    c = Client(enforce_csrf_checks=False)
    c.force_login(SuperUserFactory())
    return c


# =============================================================================
# Helper functions
# =============================================================================

class TestBreadcrumbHelpers:

    def test_bc_sem_url(self):
        item = bc('Compradores')
        assert item == {'label': 'Compradores'}

    def test_bc_com_url_resolvida(self):
        item = bc('Compradores', 'core:listar_compradores')
        assert item['label'] == 'Compradores'
        assert item['url'] == '/compradores/'

    def test_bc_url_invalida_omite_url(self):
        item = bc('X', 'nao_existe:rota_inexistente')
        assert item == {'label': 'X'}

    def test_bc_com_icone(self):
        item = bc('Home', 'core:dashboard', icon='fas fa-home')
        assert item['icon'] == 'fas fa-home'

    def test_bc_dashboard_padrao(self):
        item = bc_dashboard()
        assert item['label'] == 'Dashboard'
        assert item['url'] == reverse('core:dashboard')
        assert item['icon'] == 'fas fa-home'


# =============================================================================
# Renderização nas views — verifica que `breadcrumb` está no contexto
# =============================================================================

class TestBreadcrumbNoContexto:

    def test_lista_compradores_tem_breadcrumb(self):
        r = staff_client().get(reverse('core:listar_compradores'), secure=True)
        assert r.status_code == 200
        assert 'breadcrumb' in r.context
        labels = [item['label'] for item in r.context['breadcrumb']]
        assert 'Dashboard' in labels and 'Compradores' in labels

    def test_novo_comprador_tem_breadcrumb(self):
        r = staff_client().get(reverse('core:criar_comprador'), secure=True)
        labels = [item['label'] for item in r.context['breadcrumb']]
        assert labels[-1] == 'Novo'

    def test_editar_comprador_tem_nome_no_breadcrumb(self):
        comp = CompradorFactory(nome='Maria Silva')
        r = staff_client().get(reverse('core:editar_comprador', kwargs={'pk': comp.pk}), secure=True)
        labels = [item['label'] for item in r.context['breadcrumb']]
        assert 'Maria Silva' in labels

    def test_lista_imoveis_tem_breadcrumb(self):
        r = staff_client().get(reverse('core:listar_imoveis'), secure=True)
        assert 'breadcrumb' in r.context
        assert any(it['label'] == 'Imóveis' for it in r.context['breadcrumb'])

    def test_lista_imobiliarias_tem_breadcrumb(self):
        r = staff_client().get(reverse('core:listar_imobiliarias'), secure=True)
        assert 'breadcrumb' in r.context
        assert any(it['label'] == 'Imobiliárias' for it in r.context['breadcrumb'])

    def test_lista_contratos_tem_breadcrumb(self):
        r = staff_client().get(reverse('contratos:listar'), secure=True)
        assert 'breadcrumb' in r.context
        assert any(it['label'] == 'Contratos' for it in r.context['breadcrumb'])

    def test_lista_parcelas_tem_breadcrumb(self):
        r = staff_client().get(reverse('financeiro:listar_parcelas'), secure=True)
        assert 'breadcrumb' in r.context
        labels = [item['label'] for item in r.context['breadcrumb']]
        assert 'Financeiro' in labels and 'Parcelas' in labels

    def test_lista_reajustes_tem_breadcrumb(self):
        r = staff_client().get(reverse('financeiro:listar_reajustes'), secure=True)
        assert 'breadcrumb' in r.context
        assert any(it['label'] == 'Reajustes' for it in r.context['breadcrumb'])


# =============================================================================
# HTML renderizado — verifica que <nav aria-label="breadcrumb"> aparece
# =============================================================================

class TestBreadcrumbHTMLRender:

    def test_breadcrumb_html_renderizado(self):
        r = staff_client().get(reverse('core:listar_compradores'), secure=True)
        html = r.content.decode('utf-8')
        assert 'aria-label="breadcrumb"' in html
        assert 'Compradores' in html

    def test_pagina_sem_breadcrumb_nao_renderiza_nav(self):
        # Dashboard não define breadcrumb — não deve haver <nav aria-label="breadcrumb">
        r = staff_client().get(reverse('core:dashboard'), secure=True)
        html = r.content.decode('utf-8')
        assert 'aria-label="breadcrumb"' not in html
