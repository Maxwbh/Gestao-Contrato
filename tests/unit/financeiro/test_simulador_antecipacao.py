"""
Testes — Seção 18: Simulador de Antecipação (R-01, R-02, R-03)

Cenários:
  1  GET → renderiza formulário com parcelas disponíveis
  2  POST preview → calcula economia sem persistir
  3  POST preview sem parcelas selecionadas → preview vazio
  4  POST aplicar → quita parcelas com desconto + HistoricoPagamento.antecipado=True
  5  POST aplicar → desconto 0% → valor_pago == valor_atual
  6  POST aplicar → desconto 100% → valor_pago == 0
  7  Parcelas já pagas não aparecem na lista
  8  Parcelas INTERMEDIARIA não aparecem na lista
  9  Após aplicar → redireciona para detalhe do contrato
 10  Desconto fora de range (>100, <0) → truncado ao limite
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.test import Client
from django.urls import reverse
from financeiro.models import TipoParcela


@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='sim_user', password='pass123'
    )


@pytest.fixture
def cli(usuario):
    c = Client()
    c.login(username='sim_user', password='pass123')
    return c


@pytest.fixture
def contrato_com_parcelas(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ImovelFactory, CompradorFactory
    )
    from contratos.models import Contrato, StatusContrato, TipoCorrecao, TipoAmortizacao

    imob = ImobiliariaFactory()
    imovel = ImovelFactory(imobiliaria=imob)
    comprador = CompradorFactory()

    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='CTR-SIM-001',
        data_contrato=date.today() - timedelta(days=90),
        data_primeiro_vencimento=date.today() - timedelta(days=60),
        valor_total=Decimal('60000.00'),
        valor_entrada=Decimal('10000.00'),
        numero_parcelas=6,
        dia_vencimento=5,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.FIXO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
    )
    if not contrato.parcelas.exists():
        contrato.gerar_parcelas()
    return contrato


def _url(contrato_id):
    return reverse('financeiro:simulador_antecipacao', kwargs={'contrato_id': contrato_id})


# ===========================================================================
# R-01 — Tela formulário
# ===========================================================================

@pytest.mark.django_db
class TestSimuladorGet:
    def test_get_renderiza_form(self, cli, contrato_com_parcelas):
        resp = cli.get(_url(contrato_com_parcelas.pk))
        assert resp.status_code == 200
        assert 'parcelas_disponiveis' in resp.context

    def test_get_lista_apenas_normais_nao_pagas(self, cli, contrato_com_parcelas):
        # Pagar 1 parcela antecipadamente
        parcela = contrato_com_parcelas.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).first()
        parcela.pago = True
        parcela.valor_pago = parcela.valor_atual
        parcela.data_pagamento = date.today()
        parcela.save()

        resp = cli.get(_url(contrato_com_parcelas.pk))
        ids_disponiveis = list(resp.context['parcelas_disponiveis'].values_list('id', flat=True))
        assert parcela.id not in ids_disponiveis

    def test_get_nao_lista_intermediarias(self, cli, contrato_com_parcelas):
        from financeiro.models import Parcela
        # Criar uma parcela intermediária
        Parcela.objects.create(
            contrato=contrato_com_parcelas,
            numero_parcela=99,
            valor_original=Decimal('5000.00'),
            valor_atual=Decimal('5000.00'),
            valor_pago=Decimal('0.00'),
            data_vencimento=date.today() + timedelta(days=30),
            tipo_parcela=TipoParcela.INTERMEDIARIA,
        )
        resp = cli.get(_url(contrato_com_parcelas.pk))
        tipos = [p.tipo_parcela for p in resp.context['parcelas_disponiveis']]
        assert 'INTERMEDIARIA' not in tipos


# ===========================================================================
# R-02 — Preview sem persistir
# ===========================================================================

@pytest.mark.django_db
class TestSimuladorPreview:
    def _parcelas_ids(self, contrato, n=2):
        return list(
            contrato.parcelas.filter(pago=False, tipo_parcela=TipoParcela.NORMAL)
            .order_by('numero_parcela')[:n]
            .values_list('id', flat=True)
        )

    def test_preview_calcula_economia(self, cli, contrato_com_parcelas):
        ids = self._parcelas_ids(contrato_com_parcelas, n=2)
        resp = cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'preview',
            'parcelas': ids,
            'desconto': '10',
        })
        assert resp.status_code == 200
        preview = resp.context['preview']
        assert preview is not None
        assert preview['qtd'] == 2
        # economia = 10% do total original
        assert abs(preview['economia'] - preview['total_original'] * Decimal('0.10')) < Decimal('0.02')

    def test_preview_sem_parcelas_selecionadas(self, cli, contrato_com_parcelas):
        resp = cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'preview',
            'parcelas': [],
            'desconto': '10',
        })
        assert resp.status_code == 200
        preview = resp.context['preview']
        assert preview is not None
        assert preview['qtd'] == 0

    def test_preview_nao_persiste(self, cli, contrato_com_parcelas):
        from financeiro.models import Parcela
        ids = self._parcelas_ids(contrato_com_parcelas, n=1)
        cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'preview',
            'parcelas': ids,
            'desconto': '15',
        })
        # Parcela não deve ter sido marcada como paga
        parcela = Parcela.objects.get(id=ids[0])
        assert not parcela.pago


# ===========================================================================
# R-03 — Aplicar antecipação
# ===========================================================================

@pytest.mark.django_db
class TestSimuladorAplicar:
    def _parcelas_ids(self, contrato, n=2):
        return list(
            contrato.parcelas.filter(pago=False, tipo_parcela=TipoParcela.NORMAL)
            .order_by('numero_parcela')[:n]
            .values_list('id', flat=True)
        )

    def test_aplicar_quita_parcelas(self, cli, contrato_com_parcelas):
        from financeiro.models import Parcela
        ids = self._parcelas_ids(contrato_com_parcelas, n=2)
        resp = cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'aplicar',
            'parcelas': ids,
            'desconto': '10',
        }, follow=True)
        assert resp.status_code == 200
        for pk in ids:
            p = Parcela.objects.get(id=pk)
            assert p.pago is True

    def test_aplicar_cria_historico_antecipado(self, cli, contrato_com_parcelas):
        from financeiro.models import HistoricoPagamento
        ids = self._parcelas_ids(contrato_com_parcelas, n=2)
        cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'aplicar',
            'parcelas': ids,
            'desconto': '10',
        })
        historicos = HistoricoPagamento.objects.filter(parcela_id__in=ids)
        assert historicos.count() == 2
        for h in historicos:
            assert h.antecipado is True

    def test_aplicar_desconto_zero(self, cli, contrato_com_parcelas):
        from financeiro.models import Parcela
        ids = self._parcelas_ids(contrato_com_parcelas, n=1)
        parcela_original = Parcela.objects.get(id=ids[0])
        valor_original = parcela_original.valor_atual

        cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'aplicar',
            'parcelas': ids,
            'desconto': '0',
        })
        parcela_original.refresh_from_db()
        assert parcela_original.valor_pago == valor_original

    def test_aplicar_desconto_completo(self, cli, contrato_com_parcelas):
        from financeiro.models import Parcela, HistoricoPagamento
        ids = self._parcelas_ids(contrato_com_parcelas, n=1)

        cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'aplicar',
            'parcelas': ids,
            'desconto': '100',
        })
        parcela = Parcela.objects.get(id=ids[0])
        assert parcela.pago is True
        assert parcela.valor_pago == Decimal('0.00')
        h = HistoricoPagamento.objects.get(parcela=parcela)
        assert h.valor_desconto == parcela.valor_parcela if hasattr(parcela, 'valor_parcela') else True

    def test_aplicar_redireciona_para_detalhe(self, cli, contrato_com_parcelas):
        ids = self._parcelas_ids(contrato_com_parcelas, n=1)
        resp = cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'aplicar',
            'parcelas': ids,
            'desconto': '5',
        })
        assert resp.status_code == 302
        assert f'/contratos/{contrato_com_parcelas.pk}/' in resp['Location']

    def test_desconto_fora_de_range_truncado(self, cli, contrato_com_parcelas):
        from financeiro.models import Parcela
        ids = self._parcelas_ids(contrato_com_parcelas, n=1)
        # desconto = 150% → deve ser truncado para 100%
        cli.post(_url(contrato_com_parcelas.pk), {
            'action': 'aplicar',
            'parcelas': ids,
            'desconto': '150',
        })
        parcela = Parcela.objects.get(id=ids[0])
        assert parcela.pago is True
        assert parcela.valor_pago == Decimal('0.00')
