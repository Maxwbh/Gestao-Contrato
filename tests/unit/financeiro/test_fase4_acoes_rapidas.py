"""
F4-05: Testes para Fase 4 — Ações Rápidas
Cobre: pagar_parcela_ajax (inline + bulk), autenticação, validações.
"""
import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse

from tests.fixtures.factories import SuperUserFactory, ParcelaFactory


@pytest.fixture
def admin(db):
    return SuperUserFactory()


@pytest.fixture
def client_admin(client, admin):
    client.force_login(admin)
    return client


@pytest.fixture
def parcela(db):
    return ParcelaFactory()


def _pagar_url(hid):
    return reverse('financeiro:pagar_parcela_ajax', args=[hid])


# ── Autenticação / método ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPagarParcelaAuth:

    def test_requer_autenticacao(self, client, parcela):
        from core.hashids_utils import encode_id
        url = _pagar_url(encode_id(parcela.pk))
        response = client.post(url, {'data_pagamento': date.today().isoformat(), 'valor_pago': '100.00'})
        assert response.status_code in (302, 403)

    def test_get_retorna_405(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        url = _pagar_url(encode_id(parcela.pk))
        response = client_admin.get(url)
        assert response.status_code == 405


# ── Pagamento inline (F4-01) ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestPagarParcelaAjax:

    def test_pagamento_sucesso_retorna_json(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        url = _pagar_url(encode_id(parcela.pk))
        response = client_admin.post(url, {
            'data_pagamento': date.today().isoformat(),
            'valor_pago': str(parcela.valor_atual),
            'valor_juros': '0.00',
            'valor_multa': '0.00',
            'valor_desconto': '0.00',
            'forma_pagamento': 'PIX',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['sucesso'] is True

    def test_pagamento_marca_parcela_como_paga(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        assert not parcela.pago
        url = _pagar_url(encode_id(parcela.pk))
        client_admin.post(url, {
            'data_pagamento': date.today().isoformat(),
            'valor_pago': str(parcela.valor_atual),
            'valor_juros': '0.00',
            'valor_multa': '0.00',
            'valor_desconto': '0.00',
        })
        parcela.refresh_from_db()
        assert parcela.pago

    def test_pagamento_duplicado_retorna_400(self, client_admin, parcela):
        from core.hashids_utils import encode_id
        parcela.pago = True
        parcela.save()
        url = _pagar_url(encode_id(parcela.pk))
        response = client_admin.post(url, {
            'data_pagamento': date.today().isoformat(),
            'valor_pago': str(parcela.valor_atual),
        })
        assert response.status_code == 400
        data = response.json()
        assert data['sucesso'] is False


# ── Pagamento em massa (F4-04) ────────────────────────────────────────────────

@pytest.mark.django_db
class TestPagamentoMassa:

    def test_bulk_tres_parcelas(self, client_admin):
        from core.hashids_utils import encode_id
        parcelas = [ParcelaFactory() for _ in range(3)]
        for p in parcelas:
            url = _pagar_url(encode_id(p.pk))
            resp = client_admin.post(url, {
                'data_pagamento': date.today().isoformat(),
                'valor_pago': str(p.valor_atual),
                'valor_juros': '0.00',
                'valor_multa': '0.00',
                'valor_desconto': '0.00',
            })
            assert resp.json()['sucesso'] is True
        for p in parcelas:
            p.refresh_from_db()
            assert p.pago
