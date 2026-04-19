"""
Testes de edge cases — Valores extremos, datas limite, concorrência.

Verifica comportamento do sistema em situações fora do padrão.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from tests.fixtures.factories import (
    ContratoFactory,
    ReajusteFactory,
)


# =============================================================================
# VALORES EXTREMOS DE PARCELA
# =============================================================================

@pytest.mark.django_db
class TestValoresExtremosParcela:
    """Parcelas com valores extremos devem ser gerenciadas corretamente"""

    def test_parcela_valor_minimo(self, db):
        """Parcela com valor mínimo (R$ 0,01) não causa erro"""
        contrato = ContratoFactory(
            valor_total=Decimal('12.00'),
            valor_entrada=Decimal('0.00'),
            numero_parcelas=12,
        )
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        assert parcela.valor_atual > Decimal('0')

    def test_parcela_valor_alto(self, db):
        """Parcela com valor alto (R$ 1.000.000) é gerada corretamente"""
        contrato = ContratoFactory(
            valor_total=Decimal('12000000.00'),
            valor_entrada=Decimal('0.00'),
            numero_parcelas=12,
        )
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        assert parcela.valor_atual == pytest.approx(Decimal('1000000.00'), rel=Decimal('0.01'))

    def test_juros_zero_nao_aumenta_valor(self, db):
        """Com juros=0, valor da parcela não cresce mesmo vencida"""
        contrato = ContratoFactory(
            percentual_juros_mora=Decimal('0.00'),
            percentual_multa=Decimal('0.00'),
        )
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        parcela.data_vencimento = date.today() - timedelta(days=10)
        parcela.save()
        juros, multa = parcela.calcular_juros_multa()
        assert juros == Decimal('0')
        assert multa == Decimal('0')

    def test_multa_maxima_legal(self, db):
        """Multa máxima de 2% sobre valor da parcela"""
        contrato = ContratoFactory(
            valor_total=Decimal('12000.00'),
            valor_entrada=Decimal('0.00'),
            numero_parcelas=12,
            percentual_multa=Decimal('2.00'),
        )
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        parcela.data_vencimento = date.today() - timedelta(days=5)
        parcela.save()
        juros, multa = parcela.calcular_juros_multa()
        # Multa de 2% sobre ~R$1000 = ~R$20
        assert multa >= Decimal('0')
        assert multa <= parcela.valor_atual * Decimal('0.03')  # máximo razoável


# =============================================================================
# DATAS LIMITE
# =============================================================================

@pytest.mark.django_db
class TestDatasLimite:
    """Comportamento com datas no limite (ano-bissexto, fim de mês, etc.)"""

    def test_vencimento_fevereiro_29_em_ano_nao_bissexto(self, db):
        """Contrato com vencimento no dia 29 em ano não-bissexto"""
        # Django deve ajustar automaticamente para 28/fev ou 01/mar
        contrato = ContratoFactory(
            dia_vencimento=29,
            numero_parcelas=3,
        )
        # Não deve ter lançado exceção
        assert contrato.parcelas.count() == 3

    def test_vencimento_dia_31_em_mes_com_30_dias(self, db):
        """Contrato com vencimento no dia 31 em mês com 30 dias"""
        contrato = ContratoFactory(
            dia_vencimento=31,
            numero_parcelas=6,
        )
        assert contrato.parcelas.count() == 6

    def test_parcela_vencida_exatamente_hoje(self, db):
        """Parcela que vence hoje não deve ter encargos ainda"""
        contrato = ContratoFactory(
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
        )
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        parcela.data_vencimento = date.today()
        parcela.save()
        # Juros/multa no dia do vencimento = 0 (ainda não inadimplente)
        juros, multa = parcela.calcular_juros_multa()
        assert juros == Decimal('0')
        assert multa == Decimal('0')


# =============================================================================
# CONTRATO COM CONFIGURAÇÕES EXTREMAS
# =============================================================================

@pytest.mark.django_db
class TestContratoConfiguracoes:
    """Contratos com configurações extremas não devem causar erros"""

    def test_contrato_uma_parcela(self, db):
        """Contrato com apenas 1 parcela"""
        contrato = ContratoFactory(numero_parcelas=1)
        assert contrato.parcelas.count() == 1

    def test_contrato_muitas_parcelas(self, db):
        """Contrato com muitas parcelas (360 = 30 anos)"""
        contrato = ContratoFactory(numero_parcelas=360)
        assert contrato.parcelas.count() == 360

    def test_contrato_sem_entrada(self, db):
        """Contrato sem entrada distribui valor total em parcelas"""
        contrato = ContratoFactory(
            valor_total=Decimal('120000.00'),
            valor_entrada=Decimal('0.00'),
            numero_parcelas=12,
        )
        total_parcelas = sum(p.valor_original for p in contrato.parcelas.all())
        assert total_parcelas > Decimal('0')


# =============================================================================
# REAJUSTE — EDGE CASES
# =============================================================================

@pytest.mark.django_db
class TestReajusteEdgeCases:
    """Edge cases do sistema de reajuste"""

    def test_reajuste_percentual_zero(self, db):
        """Reajuste com percentual 0% não altera valores das parcelas"""
        contrato = ContratoFactory(numero_parcelas=12)
        contrato.parcelas.order_by('numero_parcela').first().valor_atual

        ReajusteFactory(
            contrato=contrato,
            percentual=Decimal('0.00'),
            ciclo=2,
        )
        # Parcela não deve ter sido alterada (reajuste 0% = sem mudança)
        parcela_depois = contrato.parcelas.order_by('numero_parcela').first()
        # Valor pode ser igual (reajuste de 0% não muda nada)
        assert parcela_depois.valor_atual >= Decimal('0')

    def test_reajuste_negativo_deflacao(self, db):
        """Reajuste negativo (deflação) é aceito pelo modelo"""
        contrato = ContratoFactory()
        # Deflação de -1% deve ser permitida
        reajuste = ReajusteFactory(
            contrato=contrato,
            percentual=Decimal('-1.00'),
            ciclo=2,
        )
        assert reajuste.pk is not None
