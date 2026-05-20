"""
F3-05: Testes para Fase 3 — Visualização de Dados
- F3-01: quick-view endpoint (HTML retornado, 200)
- F3-02: cálculo MoM no contexto do dashboard
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.urls import reverse

from tests.fixtures.factories import UserFactory, SuperUserFactory, ContratoFactory, ParcelaFactory


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def superusuario(db):
    return SuperUserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.fixture
def client_admin(client, superusuario):
    client.force_login(superusuario)
    return client


@pytest.fixture
def parcela(db):
    return ParcelaFactory()


# ── F3-01: Quick-view endpoint ────────────────────────────────────────────────

@pytest.mark.django_db
class TestParcelaQuickview:

    def test_requer_autenticacao(self, client, parcela):
        from core.hashids_utils import encode_id
        hid = encode_id(parcela.pk)
        url = reverse('financeiro:api_parcela_quickview', args=[hid])
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_retorna_200_para_autenticado(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        hid = encode_id(parcela.pk)
        url = reverse('financeiro:api_parcela_quickview', args=[hid])
        response = client_admin.get(url)
        assert response.status_code == 200

    def test_html_contem_dados_da_parcela(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        hid = encode_id(parcela.pk)
        url = reverse('financeiro:api_parcela_quickview', args=[hid])
        response = client_admin.get(url)
        content = response.content.decode()
        assert str(parcela.numero_parcela) in content

    def test_post_retorna_405(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        hid = encode_id(parcela.pk)
        url = reverse('financeiro:api_parcela_quickview', args=[hid])
        response = client_admin.post(url)
        assert response.status_code == 405


# ── F3-02: MoM no contexto do dashboard ──────────────────────────────────────

@pytest.mark.django_db
class TestDashboardMoM:

    def test_mom_presente_no_contexto(self, client_logado):
        response = client_logado.get(reverse('financeiro:dashboard'))
        assert response.status_code == 200
        # Ambas as chaves devem existir no contexto (podem ser None se não há mês anterior)
        assert 'mom_recebido' in response.context
        assert 'mom_pagas' in response.context

    def test_mom_none_sem_dados_mes_anterior(self, client_logado):
        """Sem parcelas pagas no mês anterior, mom deve ser None."""
        response = client_logado.get(reverse('financeiro:dashboard'))
        assert response.status_code == 200
        # Sem factory de parcelas pagas no mês passado, valor anterior = 0 → None
        assert response.context['mom_recebido'] is None
