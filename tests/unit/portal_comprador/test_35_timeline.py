"""
Testes para 35.5 — Linha do Tempo no Portal do Comprador.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.test import Client

from portal_comprador.models import AcessoComprador
from tests.fixtures.factories import (
    UserFactory,
    CompradorFactory,
    ContratoFactory,
    ParcelaFactory,
    HistoricoPagamentoFactory,
    ReajusteFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def comprador_logado(client):
    comprador = CompradorFactory()
    usuario = UserFactory()
    AcessoComprador.objects.create(comprador=comprador, usuario=usuario)
    client.force_login(usuario)
    return {'comprador': comprador, 'usuario': usuario, 'client': client}


class TestPortalTimeline:
    def test_requer_login(self, client):
        contrato = ContratoFactory()
        url = reverse('portal_comprador:portal_timeline', kwargs={'contrato_id': contrato.pk})
        resp = client.get(url, secure=True)
        assert resp.status_code == 302

    def test_comprador_ve_seu_contrato(self, comprador_logado):
        comprador = comprador_logado['comprador']
        cl = comprador_logado['client']
        contrato = ContratoFactory(comprador=comprador)
        url = reverse('portal_comprador:portal_timeline', kwargs={'contrato_id': contrato.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 200

    def test_comprador_nao_acessa_contrato_alheio(self, comprador_logado):
        cl = comprador_logado['client']
        outro_comprador = CompradorFactory()
        contrato_alheio = ContratoFactory(comprador=outro_comprador)
        url = reverse('portal_comprador:portal_timeline', kwargs={'contrato_id': contrato_alheio.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 404

    def test_eventos_em_ordem_cronologica(self, comprador_logado):
        comprador = comprador_logado['comprador']
        cl = comprador_logado['client']
        contrato = ContratoFactory(comprador=comprador)

        # Usa parcelas já criadas automaticamente pelo contrato
        parcelas = list(contrato.parcelas.order_by('numero_parcela')[:2])
        if len(parcelas) < 2:
            pytest.skip('Contrato não gerou parcelas suficientes')

        # Pagamento mais antigo
        HistoricoPagamentoFactory(
            parcela=parcelas[0],
            data_pagamento=date.today() - timedelta(days=60),
            valor_pago=Decimal('1000'),
        )
        # Pagamento mais recente
        HistoricoPagamentoFactory(
            parcela=parcelas[1],
            data_pagamento=date.today() - timedelta(days=10),
            valor_pago=Decimal('1000'),
        )

        url = reverse('portal_comprador:portal_timeline', kwargs={'contrato_id': contrato.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 200

        eventos = resp.context['eventos']
        assert len(eventos) >= 2
        datas = [e['data'] for e in eventos if e['data']]
        assert datas == sorted(datas)

    def test_reajuste_aparece_na_timeline(self, comprador_logado):
        comprador = comprador_logado['comprador']
        cl = comprador_logado['client']
        contrato = ContratoFactory(comprador=comprador)
        n = contrato.numero_parcelas
        ReajusteFactory(
            contrato=contrato,
            data_reajuste=date.today() - timedelta(days=30),
            indice_tipo='IPCA',
            percentual=Decimal('5.00'),
            parcela_inicial=1,
            parcela_final=n,
        )
        url = reverse('portal_comprador:portal_timeline', kwargs={'contrato_id': contrato.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 200
        eventos = resp.context['eventos']
        tipos = [e['tipo'] for e in eventos]
        assert 'reajuste' in tipos

    def test_contrato_sem_eventos_renderiza_vazio(self, comprador_logado):
        comprador = comprador_logado['comprador']
        cl = comprador_logado['client']
        contrato = ContratoFactory(comprador=comprador)
        url = reverse('portal_comprador:portal_timeline', kwargs={'contrato_id': contrato.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 200
        assert resp.context['eventos'] == []


class TestPortalTimelinePDF:
    def test_pdf_retorna_200_e_content_type(self, comprador_logado):
        comprador = comprador_logado['comprador']
        cl = comprador_logado['client']
        contrato = ContratoFactory(comprador=comprador)
        parcela = contrato.parcelas.first()
        HistoricoPagamentoFactory(
            parcela=parcela,
            data_pagamento=date.today() - timedelta(days=5),
            valor_pago=Decimal('500'),
        )
        url = reverse('portal_comprador:portal_timeline_pdf', kwargs={'contrato_id': contrato.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'

    def test_pdf_nome_arquivo_contem_numero_contrato(self, comprador_logado):
        comprador = comprador_logado['comprador']
        cl = comprador_logado['client']
        contrato = ContratoFactory(comprador=comprador)
        url = reverse('portal_comprador:portal_timeline_pdf', kwargs={'contrato_id': contrato.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code == 200
        disposition = resp.get('Content-Disposition', '')
        assert contrato.numero_contrato.replace('/', '-') in disposition or contrato.numero_contrato in disposition

    def test_pdf_nao_acessivel_para_contrato_alheio(self, comprador_logado):
        cl = comprador_logado['client']
        outro = CompradorFactory()
        contrato_alheio = ContratoFactory(comprador=outro)
        url = reverse('portal_comprador:portal_timeline_pdf', kwargs={'contrato_id': contrato_alheio.pk})
        resp = cl.get(url, secure=True)
        assert resp.status_code in (302, 404)
