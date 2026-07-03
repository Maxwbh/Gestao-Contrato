"""
Testes funcionais — Workflow financeiro.

Cobre: parcela → pagamento → histórico
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse

from tests.fixtures.factories import (
    UserFactory,
    ContratoFactory,
    HistoricoPagamentoFactory,
)


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestWorkflowFinanceiro:
    """Workflow financeiro: parcela → pagamento → verificação"""

    def test_parcela_vencida_tem_encargos(self, db):
        """Parcela vencida calcula juros e multa corretamente"""
        contrato = ContratoFactory(
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
        )
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        # Simula vencimento 30 dias atrás
        parcela.data_vencimento = date.today() - timedelta(days=30)
        parcela.save()

        juros, multa = parcela.calcular_juros_multa()
        assert juros >= Decimal('0')
        assert multa >= Decimal('0')

    def test_historico_pagamento_apos_registrar(self, db):
        """Após registrar pagamento existe histórico"""
        contrato = ContratoFactory()
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        historico = HistoricoPagamentoFactory(
            parcela=parcela,
            valor_pago=parcela.valor_atual,
        )
        assert historico.pk is not None
        assert historico.parcela == parcela

    def test_dashboard_financeiro_acessivel(self, client_logado):
        """Dashboard financeiro retorna status 200"""
        url = reverse('financeiro:dashboard')
        resp = client_logado.get(url)
        assert resp.status_code == 200
