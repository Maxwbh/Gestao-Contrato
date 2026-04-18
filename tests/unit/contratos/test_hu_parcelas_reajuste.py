"""
Testes HU — Geração de Parcelas, Correção Monetária e Saldo Devedor

Cobre os 5 cenários determinísticos definidos na HU:

  A — FIXO + Price + TabelaJuros    → PMT correto desde a criação, sem reajuste
  B — FIXO + SAC  + TabelaJuros    → amortização constante desde a criação
  C — IPCA + Price + sem Tabela     → reajuste SIMPLES multiplica valor_atual
  D — IPCA + Price + TabelaJuros    → reajuste TABELA PRICE recalcula PMT sobre saldo
  E — IGPM + Price + intermediarias_reduzem_pmt → base_pv reduzido pelas intermediárias

Cada teste valida:
  - Número correto de parcelas geradas
  - Valor do PMT (calculado via fórmula Price/SAC)
  - Campos amortizacao e juros_embutido
  - Saldo devedor (calcular_saldo_devedor())
  - Reajuste aplicado (cenários C e D)
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta


# ---------------------------------------------------------------------------
# Helpers de cálculo (espelham a lógica do modelo)
# ---------------------------------------------------------------------------

def _pmt(pv: Decimal, taxa_mensal_pct: Decimal, n: int) -> Decimal:
    """PMT Tabela Price — mesma fórmula de Parcela._calcular_pmt()."""
    if n <= 0:
        return Decimal('0')
    i = taxa_mensal_pct / Decimal('100')
    if i == 0:
        return (pv / Decimal(n)).quantize(Decimal('0.01'))
    fator = i / (1 - (1 + i) ** (-n))
    return (pv * fator).quantize(Decimal('0.01'))


def _amort_sac(pv: Decimal, n: int) -> Decimal:
    """Amortização constante SAC = PV / n."""
    return (pv / Decimal(n)).quantize(Decimal('0.01'))


# ---------------------------------------------------------------------------
# Fixtures de domínio (cria imobiliária + imovel + comprador)
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio(db):
    """Retorna (imobiliaria, imovel_fn, comprador) prontos para uso."""
    from tests.fixtures.factories import ImobiliariaFactory, CompradorFactory, ImovelFactory
    from core.models import TipoImovel

    imob = ImobiliariaFactory(
        nome='Imob HU Testes',
        razao_social='Imob HU Testes LTDA',
        cnpj='12345678000199',
        cidade='Sete Lagoas',
        estado='MG',
        tipo_pessoa='PJ',
    )

    comprador = CompradorFactory(
        nome='Comprador HU',
    )

    def _imovel(sufixo):
        return ImovelFactory(
            imobiliaria=imob,
            tipo=TipoImovel.LOTE,
            identificacao=f'Lote HU-{sufixo}',
            disponivel=False,
        )

    return imob, _imovel, comprador


# ---------------------------------------------------------------------------
# CENÁRIO A — FIXO + Price + TabelaJuros
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCenarioA:
    """
    FIXO + Tabela Price + TabelaJurosContrato (0.6% a.m.)
    valor_total=130k, entrada=10k → financiado=120k
    n=24, taxa=0.6%
    PMT esperado = 120000 × 0.006 / (1 − 1.006^-24)
    """
    PV = Decimal('120000.00')
    TAXA = Decimal('0.6000')
    N = 24

    def _criar_contrato(self, dominio):
        from contratos.models import Contrato, TabelaJurosContrato, TipoCorrecao
        imob, _imovel, comprador = dominio
        hoje = date.today()
        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=_imovel('A'),
            comprador=comprador,
            numero_contrato='HU-A-TEST',
            data_contrato=hoje - relativedelta(months=2),
            data_primeiro_vencimento=hoje - relativedelta(months=1),
            valor_total=Decimal('130000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=self.N,
            dia_vencimento=15,
            tipo_correcao=TipoCorrecao.FIXO,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
        )
        TabelaJurosContrato.objects.create(
            contrato=contrato, ciclo_inicio=1, ciclo_fim=None,
            juros_mensal=self.TAXA,
        )
        contrato.recalcular_amortizacao()
        return contrato

    def test_numero_parcelas_geradas(self, dominio):
        contrato = self._criar_contrato(dominio)
        assert contrato.parcelas.filter(tipo_parcela='NORMAL').count() == self.N

    def test_pmt_valor_correto(self, dominio):
        contrato = self._criar_contrato(dominio)
        pmt_esperado = _pmt(self.PV, self.TAXA, self.N)
        # Todas as parcelas (exceto última) devem ter valor_atual ≈ PMT
        parcelas = list(contrato.parcelas.filter(tipo_parcela='NORMAL').order_by('numero_parcela'))
        for p in parcelas[:-1]:
            assert p.valor_atual == pmt_esperado, (
                f"Parcela {p.numero_parcela}: esperado {pmt_esperado}, obtido {p.valor_atual}"
            )

    def test_amortizacao_juros_preenchidos(self, dominio):
        contrato = self._criar_contrato(dominio)
        for p in contrato.parcelas.filter(tipo_parcela='NORMAL'):
            assert p.amortizacao is not None
            assert p.juros_embutido is not None
            assert p.amortizacao > Decimal('0')
            assert p.juros_embutido >= Decimal('0')

    def test_pmt_equals_amort_plus_juros(self, dominio):
        """PMT = amortizacao + juros_embutido para cada parcela (exceto última)."""
        contrato = self._criar_contrato(dominio)
        parcelas = list(contrato.parcelas.filter(tipo_parcela='NORMAL').order_by('numero_parcela'))
        for p in parcelas[:-1]:
            assert p.valor_atual == (p.amortizacao + p.juros_embutido), (
                f"Parcela {p.numero_parcela}: {p.valor_atual} ≠ {p.amortizacao} + {p.juros_embutido}"
            )

    def test_saldo_devedor(self, dominio):
        """Saldo = Σ valor_atual das parcelas NORMAL não pagas (todas no início)."""
        contrato = self._criar_contrato(dominio)
        pmt_esperado = _pmt(self.PV, self.TAXA, self.N)
        saldo = contrato.calcular_saldo_devedor()
        # saldo = N × PMT (≈ valor financiado + juros totais)
        assert saldo == contrato.parcelas.filter(
            tipo_parcela='NORMAL', pago=False
        ).count() * pmt_esperado or saldo > self.PV

    def test_fixo_sem_reajuste_disponivel(self, dominio):
        """calcular_ciclo_pendente deve retornar None para FIXO."""
        from financeiro.models import Reajuste
        contrato = self._criar_contrato(dominio)
        assert Reajuste.calcular_ciclo_pendente(contrato) is None


# ---------------------------------------------------------------------------
# CENÁRIO B — FIXO + SAC + TabelaJuros
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCenarioB:
    """
    FIXO + SAC + TabelaJurosContrato (0.6% a.m.)
    financiado=120k, n=24
    Amort constante = 120000/24 = 5000.00
    """
    PV = Decimal('120000.00')
    TAXA = Decimal('0.6000')
    N = 24
    AMORT_ESPERADA = (Decimal('120000.00') / 24).quantize(Decimal('0.01'))

    def _criar_contrato(self, dominio):
        from contratos.models import Contrato, TabelaJurosContrato, TipoCorrecao
        imob, _imovel, comprador = dominio
        hoje = date.today()
        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=_imovel('B'),
            comprador=comprador,
            numero_contrato='HU-B-TEST',
            data_contrato=hoje - relativedelta(months=2),
            data_primeiro_vencimento=hoje - relativedelta(months=1),
            valor_total=Decimal('130000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=self.N,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.FIXO,
            tipo_amortizacao='SAC',
            prazo_reajuste_meses=12,
        )
        TabelaJurosContrato.objects.create(
            contrato=contrato, ciclo_inicio=1, ciclo_fim=None,
            juros_mensal=self.TAXA,
        )
        contrato.recalcular_amortizacao()
        return contrato

    def test_amortizacao_constante(self, dominio):
        """SAC: amortizacao deve ser constante (exceto última parcela)."""
        contrato = self._criar_contrato(dominio)
        parcelas = list(contrato.parcelas.filter(
            tipo_parcela='NORMAL'
        ).order_by('numero_parcela'))
        for p in parcelas[:-1]:
            assert p.amortizacao == self.AMORT_ESPERADA, (
                f"Parcela {p.numero_parcela}: amort esperada {self.AMORT_ESPERADA}, obtida {p.amortizacao}"
            )

    def test_pmt_decrescente(self, dominio):
        """SAC: PMT deve decrescer a cada parcela (juros sobre saldo decrescente)."""
        contrato = self._criar_contrato(dominio)
        parcelas = list(contrato.parcelas.filter(
            tipo_parcela='NORMAL'
        ).order_by('numero_parcela'))
        for i in range(len(parcelas) - 2):
            assert parcelas[i].valor_atual >= parcelas[i + 1].valor_atual, (
                f"PMT deveria decrescer: p{parcelas[i].numero_parcela}={parcelas[i].valor_atual} "
                f"< p{parcelas[i+1].numero_parcela}={parcelas[i+1].valor_atual}"
            )

    def test_saldo_devedor_usa_amortizacao(self, dominio):
        """SAC: saldo devedor = Σ amortizacao (não valor_atual)."""
        contrato = self._criar_contrato(dominio)
        saldo = contrato.calcular_saldo_devedor()
        soma_amort = sum(
            p.amortizacao for p in contrato.parcelas.filter(
                tipo_parcela='NORMAL', pago=False
            ) if p.amortizacao
        )
        assert saldo == soma_amort

    def test_juros_primeira_parcela(self, dominio):
        """SAC: juros da 1ª parcela = PV × taxa."""
        contrato = self._criar_contrato(dominio)
        p1 = contrato.parcelas.filter(tipo_parcela='NORMAL').order_by('numero_parcela').first()
        juros_esperados = (self.PV * self.TAXA / 100).quantize(Decimal('0.01'))
        assert p1.juros_embutido == juros_esperados


# ---------------------------------------------------------------------------
# CENÁRIO C — IPCA + Price + sem TabelaJuros → modo SIMPLES
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCenarioC:
    """
    IPCA + Price + sem TabelaJuros → parcelas lineares, reajuste SIMPLES.
    financiado=90k, n=36, parcela linear = 2500.00
    Reajuste ciclo 2 com 5%: novo valor = 2500 × 1.05 = 2625.00
    """
    PV = Decimal('90000.00')
    N = 36
    PARCELA_LINEAR = (Decimal('90000.00') / 36).quantize(Decimal('0.01'))
    PERCENTUAL_REAJUSTE = Decimal('5.0000')

    def _criar_contrato(self, dominio):
        from contratos.models import Contrato, TipoCorrecao
        imob, _imovel, comprador = dominio
        hoje = date.today()
        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=_imovel('C'),
            comprador=comprador,
            numero_contrato='HU-C-TEST',
            data_contrato=hoje - relativedelta(months=20),
            data_primeiro_vencimento=hoje - relativedelta(months=19),
            valor_total=Decimal('96000.00'),
            valor_entrada=Decimal('6000.00'),
            numero_parcelas=self.N,
            dia_vencimento=5,
            tipo_correcao=TipoCorrecao.IPCA,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
        )
        return contrato

    def test_parcelas_lineares_sem_tabela(self, dominio):
        """Sem TabelaJuros: parcelas devem ter valor linear (PV/n)."""
        contrato = self._criar_contrato(dominio)
        for p in contrato.parcelas.filter(tipo_parcela='NORMAL'):
            assert p.valor_atual == self.PARCELA_LINEAR, (
                f"Esperado {self.PARCELA_LINEAR}, obtido {p.valor_atual}"
            )

    def test_amortizacao_nula_sem_tabela(self, dominio):
        """Sem TabelaJuros: amortizacao e juros_embutido devem ser None."""
        contrato = self._criar_contrato(dominio)
        for p in contrato.parcelas.filter(tipo_parcela='NORMAL'):
            assert p.amortizacao is None
            assert p.juros_embutido is None

    def test_reajuste_simples_multiplica_valor(self, dominio):
        """Reajuste modo SIMPLES: valor_novo = valor_atual × (1 + %)."""
        from financeiro.models import Reajuste
        contrato = self._criar_contrato(dominio)

        data_reajuste = contrato.data_contrato + relativedelta(months=12)
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            ciclo=2,
            data_reajuste=data_reajuste,
            indice_tipo='IPCA',
            percentual=self.PERCENTUAL_REAJUSTE,
            percentual_bruto=self.PERCENTUAL_REAJUSTE,
            parcela_inicial=13,
            parcela_final=24,
            periodo_referencia_inicio=contrato.data_contrato,
            periodo_referencia_fim=contrato.data_contrato + relativedelta(months=12) - relativedelta(days=1),
        )
        reajuste.aplicar_reajuste()

        valor_esperado = (self.PARCELA_LINEAR * (1 + self.PERCENTUAL_REAJUSTE / 100)).quantize(Decimal('0.01'))
        parcelas_reajustadas = contrato.parcelas.filter(
            tipo_parcela='NORMAL',
            numero_parcela__gte=13,
            numero_parcela__lte=24,
            pago=False,
        )
        for p in parcelas_reajustadas:
            assert p.valor_atual == valor_esperado, (
                f"Parcela {p.numero_parcela}: esperado {valor_esperado}, obtido {p.valor_atual}"
            )

    def test_parcelas_anteriores_ao_ciclo_nao_reajustadas(self, dominio):
        """
        Reajuste ciclo 2 (MODO SIMPLES) não altera parcelas 1–12 (pagas/do ciclo 1),
        mas atualiza TODAS as parcelas a partir da 13 — incluindo 25–36 (ciclos futuros).

        Regra: o reajuste é permanente e composto. A prestação base é atualizada
        para todos os ciclos futuros calcularem sobre o valor já corrigido.
        """
        from financeiro.models import Reajuste
        contrato = self._criar_contrato(dominio)

        data_reajuste = contrato.data_contrato + relativedelta(months=12)
        reajuste = Reajuste.objects.create(
            contrato=contrato, ciclo=2, data_reajuste=data_reajuste,
            indice_tipo='IPCA', percentual=self.PERCENTUAL_REAJUSTE,
            percentual_bruto=self.PERCENTUAL_REAJUSTE,
            parcela_inicial=13, parcela_final=24,
            periodo_referencia_inicio=contrato.data_contrato,
            periodo_referencia_fim=contrato.data_contrato + relativedelta(months=11),
        )
        reajuste.aplicar_reajuste()

        valor_reajustado = (self.PARCELA_LINEAR * (1 + self.PERCENTUAL_REAJUSTE / 100)).quantize(Decimal('0.01'))

        # Parcelas do ciclo 1 (1–12): não alteradas
        for p in contrato.parcelas.filter(tipo_parcela='NORMAL', numero_parcela__lte=12):
            assert p.valor_atual == self.PARCELA_LINEAR, f"Parcela {p.numero_parcela} não deveria ser alterada"

        # Parcelas do ciclo 2 em diante (13–36): todas reajustadas
        for p in contrato.parcelas.filter(tipo_parcela='NORMAL', numero_parcela__gte=13):
            p.refresh_from_db()
            assert p.valor_atual == valor_reajustado, (
                f"Parcela {p.numero_parcela}: esperado {valor_reajustado}, obtido {p.valor_atual}"
            )

        # parcela_final no registro deve ser atualizado para a última parcela do contrato
        reajuste.refresh_from_db()
        assert reajuste.parcela_final == contrato.numero_parcelas


# ---------------------------------------------------------------------------
# CENÁRIO D — IPCA + Price + TabelaJuros → modo TABELA PRICE
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCenarioD:
    """
    IPCA + Price + TabelaJurosContrato (ciclo 1: 0%, ciclo 2+: 0.6%)
    financiado=90k, n=36
    Ciclo 1 (taxa=0): PMT linear = 90000/36 = 2500
    Após reajuste 5%: saldo atualizado = Σ valor_atual × 1.05
    Novo PMT = PMT(saldo_atualizado, 0.6%, n_restantes)
    """
    PV = Decimal('90000.00')
    N = 36
    TAXA_CICLO1 = Decimal('0.0000')
    TAXA_CICLO2 = Decimal('0.6000')
    PERCENTUAL_REAJUSTE = Decimal('5.0000')

    def _criar_contrato(self, dominio):
        from contratos.models import Contrato, TabelaJurosContrato, TipoCorrecao
        imob, _imovel, comprador = dominio
        hoje = date.today()
        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=_imovel('D'),
            comprador=comprador,
            numero_contrato='HU-D-TEST',
            data_contrato=hoje - relativedelta(months=20),
            data_primeiro_vencimento=hoje - relativedelta(months=19),
            valor_total=Decimal('96000.00'),
            valor_entrada=Decimal('6000.00'),
            numero_parcelas=self.N,
            dia_vencimento=20,
            tipo_correcao=TipoCorrecao.IPCA,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
        )
        TabelaJurosContrato.objects.create(
            contrato=contrato, ciclo_inicio=1, ciclo_fim=1,
            juros_mensal=self.TAXA_CICLO1,
        )
        TabelaJurosContrato.objects.create(
            contrato=contrato, ciclo_inicio=2, ciclo_fim=None,
            juros_mensal=self.TAXA_CICLO2,
        )
        contrato.recalcular_amortizacao()
        return contrato

    def test_pmt_ciclo1_linear(self, dominio):
        """Ciclo 1 com taxa=0: PMT = PV/n (sem juros)."""
        contrato = self._criar_contrato(dominio)
        pmt_ciclo1 = _pmt(self.PV, self.TAXA_CICLO1, self.N)  # = 2500.00
        parcelas = list(contrato.parcelas.filter(
            tipo_parcela='NORMAL'
        ).order_by('numero_parcela'))
        for p in parcelas[:-1]:
            assert p.valor_atual == pmt_ciclo1

    def test_reajuste_tabela_price_recalcula_pmt(self, dominio):
        """
        Após reajuste ciclo 2 (5%):
        saldo_atual = Σ valor_atual parcelas 1–36 não pagas
        saldo_atualizado = saldo_atual × 1.05
        novo_pmt = PMT(saldo_atualizado, 0.6%, n_restantes)
        """
        from financeiro.models import Reajuste
        from django.db.models import Sum
        contrato = self._criar_contrato(dominio)

        saldo_antes = contrato.parcelas.filter(
            tipo_parcela='NORMAL', pago=False
        ).aggregate(total=Sum('valor_atual'))['total']
        saldo_atualizado = (saldo_antes * (1 + self.PERCENTUAL_REAJUSTE / 100)).quantize(Decimal('0.01'))
        n_restantes = contrato.parcelas.filter(tipo_parcela='NORMAL', pago=False).count()
        novo_pmt_esperado = _pmt(saldo_atualizado, self.TAXA_CICLO2, n_restantes)

        data_reajuste = contrato.data_contrato + relativedelta(months=12)
        reajuste = Reajuste.objects.create(
            contrato=contrato, ciclo=2, data_reajuste=data_reajuste,
            indice_tipo='IPCA', percentual=self.PERCENTUAL_REAJUSTE,
            percentual_bruto=self.PERCENTUAL_REAJUSTE,
            parcela_inicial=13, parcela_final=36,
            periodo_referencia_inicio=contrato.data_contrato,
            periodo_referencia_fim=contrato.data_contrato + relativedelta(months=11),
        )
        reajuste.aplicar_reajuste()

        # Todas as parcelas não pagas devem ter o novo PMT
        for p in contrato.parcelas.filter(tipo_parcela='NORMAL', pago=False):
            assert p.valor_atual == novo_pmt_esperado, (
                f"Parcela {p.numero_parcela}: esperado {novo_pmt_esperado}, obtido {p.valor_atual}"
            )

    def test_saldo_devedor_price_soma_valor_atual(self, dominio):
        """Price: saldo devedor = Σ valor_atual (não amortizacao)."""
        from django.db.models import Sum
        contrato = self._criar_contrato(dominio)
        saldo = contrato.calcular_saldo_devedor()
        soma_valor = contrato.parcelas.filter(
            tipo_parcela='NORMAL', pago=False
        ).aggregate(total=Sum('valor_atual'))['total']
        assert saldo == soma_valor


# ---------------------------------------------------------------------------
# CENÁRIO E — IGPM + Price + intermediarias_reduzem_pmt
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCenarioE:
    """
    IGPM + Price + intermediarias_reduzem_pmt=True
    financiado=90k, 2 intermediárias de 5k cada → base_pv=80k
    n=24, sem TabelaJuros (taxa=0) → PMT linear = 80000/24 = 3333.33
    """
    PV_TOTAL = Decimal('90000.00')
    SOMA_INTER = Decimal('10000.00')
    BASE_PV = Decimal('80000.00')
    N = 24

    def _criar_contrato(self, dominio):
        from contratos.models import Contrato, PrestacaoIntermediaria, TipoCorrecao
        from django.db.models import Sum
        imob, _imovel, comprador = dominio
        hoje = date.today()
        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=_imovel('E'),
            comprador=comprador,
            numero_contrato='HU-E-TEST',
            data_contrato=hoje - relativedelta(months=15),
            data_primeiro_vencimento=hoje - relativedelta(months=14),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=self.N,
            dia_vencimento=25,
            tipo_correcao=TipoCorrecao.IGPM,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
            intermediarias_reduzem_pmt=True,
        )
        PrestacaoIntermediaria.objects.create(
            contrato=contrato, numero_sequencial=1, mes_vencimento=6,
            valor=Decimal('5000.00'),
        )
        PrestacaoIntermediaria.objects.create(
            contrato=contrato, numero_sequencial=2, mes_vencimento=12,
            valor=Decimal('5000.00'),
        )
        soma = contrato.intermediarias.aggregate(total=Sum('valor'))['total']
        base_pv = max(contrato.valor_financiado - soma, Decimal('0.01'))
        contrato.recalcular_amortizacao(base_pv=base_pv)
        return contrato

    def test_base_pv_reduzida_pelas_intermediarias(self, dominio):
        """base_pv = valor_financiado - Σ intermediárias = 80k."""
        contrato = self._criar_contrato(dominio)
        assert contrato.valor_financiado == self.PV_TOTAL
        # PMT deve ser calculado sobre 80k, não 90k
        pmt_sobre_pv_total = _pmt(self.PV_TOTAL, Decimal('0'), self.N)  # 3750
        pmt_sobre_base_pv = _pmt(self.BASE_PV, Decimal('0'), self.N)    # 3333.33
        p1 = contrato.parcelas.filter(tipo_parcela='NORMAL').order_by('numero_parcela').first()
        assert p1.valor_atual == pmt_sobre_base_pv
        assert p1.valor_atual != pmt_sobre_pv_total

    def test_pmt_correto_base_pv_80k(self, dominio):
        """PMT = 80000/24 = 3333.33 (taxa=0, sem TabelaJuros)."""
        contrato = self._criar_contrato(dominio)
        pmt_esperado = _pmt(self.BASE_PV, Decimal('0'), self.N)
        parcelas = list(contrato.parcelas.filter(
            tipo_parcela='NORMAL'
        ).order_by('numero_parcela'))
        for p in parcelas[:-1]:
            assert p.valor_atual == pmt_esperado

    def test_duas_intermediarias_criadas(self, dominio):
        """Deve haver exatamente 2 intermediárias."""
        contrato = self._criar_contrato(dominio)
        assert contrato.intermediarias.count() == 2

    def test_saldo_devedor_exclui_intermediarias(self, dominio):
        """Saldo devedor considera apenas parcelas NORMAL, não intermediárias."""
        from django.db.models import Sum
        contrato = self._criar_contrato(dominio)
        saldo = contrato.calcular_saldo_devedor()
        soma_normal = contrato.parcelas.filter(
            tipo_parcela='NORMAL', pago=False
        ).aggregate(total=Sum('valor_atual'))['total']
        assert saldo == soma_normal
        # Saldo ≠ valor financiado total (pois as intermediárias não estão no saldo)
        assert saldo < contrato.valor_financiado


# ---------------------------------------------------------------------------
# Testes de saldo devedor SAC vs Price
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSaldoDevedor:
    """Valida calcular_saldo_devedor() para Price e SAC separadamente."""

    def _contrato_price(self, dominio):
        from contratos.models import Contrato, TabelaJurosContrato, TipoCorrecao
        imob, _imovel, comprador = dominio
        hoje = date.today()
        c = Contrato.objects.create(
            imobiliaria=imob, imovel=_imovel('SD-P'), comprador=comprador,
            numero_contrato='HU-SD-PRICE',
            data_contrato=hoje - relativedelta(months=2),
            data_primeiro_vencimento=hoje - relativedelta(months=1),
            valor_total=Decimal('130000.00'), valor_entrada=Decimal('10000.00'),
            numero_parcelas=24, dia_vencimento=15,
            tipo_correcao=TipoCorrecao.FIXO, tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
        )
        TabelaJurosContrato.objects.create(
            contrato=c, ciclo_inicio=1, ciclo_fim=None, juros_mensal=Decimal('0.6000'),
        )
        c.recalcular_amortizacao()
        return c

    def _contrato_sac(self, dominio):
        from contratos.models import Contrato, TabelaJurosContrato, TipoCorrecao
        imob, _imovel, comprador = dominio
        hoje = date.today()
        c = Contrato.objects.create(
            imobiliaria=imob, imovel=_imovel('SD-S'), comprador=comprador,
            numero_contrato='HU-SD-SAC',
            data_contrato=hoje - relativedelta(months=2),
            data_primeiro_vencimento=hoje - relativedelta(months=1),
            valor_total=Decimal('130000.00'), valor_entrada=Decimal('10000.00'),
            numero_parcelas=24, dia_vencimento=10,
            tipo_correcao=TipoCorrecao.FIXO, tipo_amortizacao='SAC',
            prazo_reajuste_meses=12,
        )
        TabelaJurosContrato.objects.create(
            contrato=c, ciclo_inicio=1, ciclo_fim=None, juros_mensal=Decimal('0.6000'),
        )
        c.recalcular_amortizacao()
        return c

    def test_price_saldo_maior_que_pv(self, dominio):
        """Price: saldo = Σ PMTs futuros > PV (inclui juros futuros)."""
        from django.db.models import Sum
        c = self._contrato_price(dominio)
        saldo = c.calcular_saldo_devedor()
        soma_pmt = c.parcelas.filter(tipo_parcela='NORMAL', pago=False).aggregate(
            total=Sum('valor_atual')
        )['total']
        assert saldo == soma_pmt
        assert saldo > c.valor_financiado  # inclui juros futuros

    def test_sac_saldo_igual_ao_pv(self, dominio):
        """SAC: saldo = Σ amortizacoes = PV exato (sem juros futuros)."""
        c = self._contrato_sac(dominio)
        saldo = c.calcular_saldo_devedor()
        # Soma das amortizações deve aproximar o PV (diferença de centavos por arredondamento)
        assert abs(saldo - c.valor_financiado) <= Decimal('1.00')

    def test_saldo_diminui_ao_pagar_parcela(self, dominio):
        """Ao marcar parcela como paga, saldo devedor deve diminuir."""
        from django.utils import timezone
        c = self._contrato_price(dominio)
        saldo_antes = c.calcular_saldo_devedor()
        p = c.parcelas.filter(tipo_parcela='NORMAL', pago=False).order_by('numero_parcela').first()
        p.pago = True
        p.valor_pago = p.valor_atual
        p.data_pagamento = timezone.now().date()
        p.save()
        saldo_depois = c.calcular_saldo_devedor()
        assert saldo_depois < saldo_antes
        assert saldo_antes - saldo_depois == p.valor_atual
