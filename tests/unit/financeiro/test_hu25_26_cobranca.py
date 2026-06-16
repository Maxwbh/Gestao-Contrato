"""
Testes das telas da contadora HU-25 (Hub Cobrança do Mês) e HU-26
(Painel de Conciliação & Saúde da Cobrança).

Escopo: cobranca_hub, api_cobranca_estado, painel_conciliacao_saude,
        api_conciliacao_saude.
"""
import json
import pytest
from django.urls import reverse

from tests.fixtures.factories import UserFactory, ContratoFactory


@pytest.fixture
def usuario(db):
    return UserFactory(is_staff=True)


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestCobrancaHub:
    """HU-25 — Hub Cobrança do Mês."""

    def test_requer_autenticacao(self, client):
        resp = client.get(reverse('financeiro:cobranca_hub'))
        assert resp.status_code in (302, 403)

    def test_get_retorna_200_com_estado(self, client_logado):
        resp = client_logado.get(reverse('financeiro:cobranca_hub'))
        assert resp.status_code == 200
        estado = resp.context['estado']
        for chave in ('passo1', 'passo2', 'passo3', 'recomendado', 'percentual'):
            assert chave in estado

    def test_filtro_competencia(self, client_logado):
        resp = client_logado.get(
            reverse('financeiro:cobranca_hub'), {'mes': 6, 'ano': 2026}
        )
        assert resp.status_code == 200
        assert resp.context['estado']['mes'] == 6
        assert resp.context['estado']['ano'] == 2026

    def test_api_estado_json(self, client_logado):
        resp = client_logado.get(reverse('financeiro:api_cobranca_estado'))
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['sucesso'] is True
        estado = data['estado']
        assert {'passo1', 'passo2', 'passo3'} <= set(estado.keys())
        # valor_gerar deve ser serializável (float)
        assert isinstance(estado['valor_gerar'], (int, float))

    def test_api_contagem_badge(self, client_logado):
        """HU-27: endpoint leve do badge retorna {a_gerar:int}."""
        resp = client_logado.get(reverse('financeiro:api_cobranca_contagem'))
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'a_gerar' in data
        assert isinstance(data['a_gerar'], int)
        # segunda chamada (cacheada) mantém o mesmo valor
        resp2 = client_logado.get(reverse('financeiro:api_cobranca_contagem'))
        assert json.loads(resp2.content)['a_gerar'] == data['a_gerar']


@pytest.mark.django_db
class TestConciliacaoSaude:
    """HU-26 — Painel de Conciliação & Saúde da Cobrança."""

    def test_requer_autenticacao(self, client):
        resp = client.get(reverse('financeiro:painel_conciliacao_saude'))
        assert resp.status_code in (302, 403)

    def test_get_retorna_200(self, client_logado):
        resp = client_logado.get(reverse('financeiro:painel_conciliacao_saude'))
        assert resp.status_code == 200
        assert 'pct_conciliado' in resp.context
        assert 'origem_rows' in resp.context
        assert 'aging' in resp.context

    def test_api_saude_json(self, client_logado):
        resp = client_logado.get(reverse('financeiro:api_conciliacao_saude'))
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['sucesso'] is True
        for chave in ('pct_conciliado', 'recebido', 'pendente', 'vencido', 'origem', 'aging'):
            assert chave in data
        # buckets de aging presentes
        assert {'a_vencer', 'd1_30', 'd31_60', 'd60_mais'} <= set(data['aging'].keys())
        # origens consolidadas
        assert {'CNAB', 'PIX', 'OFX', 'MANUAL'} <= set(data['origem'].keys())

    def test_pct_conciliado_sem_dados_e_zero(self, client_logado):
        data = json.loads(
            client_logado.get(reverse('financeiro:api_conciliacao_saude')).content
        )
        assert data['pct_conciliado'] == 0
