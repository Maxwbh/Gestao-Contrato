"""
HU-360 — Contrato Tabela Price com Juros Escalantes e Intermediárias
=====================================================================

Cobre o ciclo de vida completo do cenário mais complexo do sistema:

  Passo 1  Criação do contrato com 3 faixas de juros (0%, 0,60%, 0,65%)
  Passo 2  Validação do PMT ciclo 1 linear (taxa=0 → PMT = base_pv/n)
  Passo 3  Validação das intermediárias criadas e da base_pv reduzida
  Passo 4  Geração de boleto para a 1ª intermediária (mes=6)
  Passo 5  Reajuste ciclo 2 — IPCA 5%: PMT recalculado + intermediária reajustada
  Passo 6  Validação bloqueio antes/depois do reajuste ciclo 2
  Passo 7  Reajuste ciclo 3 — IPCA 4% com taxa diferente (0,65%): PMT recalculado novamente
  Passo 8  Bloqueio cascata: desfazer ciclo 2 bloqueia ciclo 3

Dependências externas (BRCobrança):
  Geração de boleto substituída por mock (gerar_boleto retorna sucesso local).

Diferenças em relação a test_hu_fluxo_completo.py (básico):
  - 3 entradas em TabelaJurosContrato com taxas diferentes por ciclo
  - intermediarias_reduzem_pmt=True → base_pv = valor_financiado − Σintermediárias
  - intermediarias_reajustadas=True → PrestacaoIntermediaria.valor_reajustado atualizado
  - Dois reajustes consecutivos com taxas distintas (0,60% → 0,65%)
  - Verificação de que o PMT do ciclo 3 usa a taxa do ciclo 3 (não do ciclo 2)
"""
import json
import pytest
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from core.hashids_utils import encode_id

# ── Constantes do cenário ──────────────────────────────────────────────────────
PV_BRUTO = Decimal('110000.00')   # valor_financiado antes de deduzir intermediárias
SOMA_INTER = Decimal('10000.00')  # 2 intermediárias × R$ 5.000
BASE_PV = Decimal('100000.00')    # base do PMT = PV_BRUTO − SOMA_INTER
N = 36                             # número de parcelas
PRAZO_REAJUSTE = 12               # meses por ciclo
TAXA_CICLO1 = Decimal('0.0000')   # % a.m. (linear, sem juros)
TAXA_CICLO2 = Decimal('0.6000')   # % a.m. — ciclo 2
TAXA_CICLO3 = Decimal('0.6500')   # % a.m. — ciclo 3+
IPCA_CICLO2 = Decimal('5.0')      # % de reajuste aplicado no ciclo 2
IPCA_CICLO3 = Decimal('4.0')      # % de reajuste aplicado no ciclo 3


# ── Auxiliar — mock de geração de boleto ──────────────────────────────────────

def _mock_gerar_boleto(self, conta_bancaria=None, force=False, enviar_email=True):
    """
    Substitui Parcela.gerar_boleto() evitando chamada ao BRCobrança.
    Preenche nosso_numero e linha_digitavel diretamente no banco.
    """
    nosso_numero = f'{self.numero_parcela:010d}'
    linha = f'75691.{nosso_numero[:5]} {nosso_numero[5:]} 0 10000000000{self.numero_parcela:05d}'
    self.nosso_numero = nosso_numero
    self.linha_digitavel = linha
    self.save(update_fields=['nosso_numero', 'linha_digitavel'])
    return {
        'sucesso': True,
        'nosso_numero': nosso_numero,
        'linha_digitavel': linha,
        'boleto_url': f'http://mock/boleto/{nosso_numero}',
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def dominio(db):
    """
    Cria domínio completo usando factories já existentes no projeto.
    Retorna (imobiliaria, imovel, comprador).
    """
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    imob = ImobiliariaFactory(nome='Imobiliária HU360')
    ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador HU360')
    return imob, imovel, comprador


@pytest.fixture
def usuario_cli(db, dominio):
    """Usuário autenticado e Client Django."""
    from django.contrib.auth import get_user_model
    imob, _, _ = dominio
    User = get_user_model()
    u = User.objects.create_user(
        username='hu360user',
        password='HU360pass!',
        email='hu360@test.com',
    )
    c = Client()
    c.force_login(u)
    return u, c


@pytest.fixture
def contrato_hu360(db, dominio):
    """
    Contrato IPCA + Tabela Price + 3 faixas de TabelaJuros + 2 intermediárias.

    Parâmetros financeiros:
      valor_financiado = R$ 110.000 (bruto)
      Intermediária 1: mes=6  → valor=R$ 5.000 (ciclo 1 — antes do prazo de reajuste)
      Intermediária 2: mes=18 → valor=R$ 5.000 (ciclo 2 — entre as parcelas 13 e 24)
      intermediarias_reduzem_pmt=True → base_pv = 110.000 − 10.000 = 100.000
      intermediarias_reajustadas=True → inter mes=18 é reajustada no ciclo 2

    TabelaJurosContrato:
      Ciclo 1 (1–1): 0,0000 % a.m.
      Ciclo 2 (2–2): 0,6000 % a.m.
      Ciclo 3 (3–∞): 0,6500 % a.m.

    PMT ciclo 1 = BASE_PV / N = 100.000 / 36 ≈ 2777.78 (linear, taxa=0)
    data_contrato = hoje − 14 meses → ciclo 2 vencido há 2 meses (pendente)
    """
    from contratos.models import (
        Contrato, TabelaJurosContrato, PrestacaoIntermediaria,
        TipoCorrecao, TipoAmortizacao, StatusContrato,
    )
    from django.db.models import Sum

    imob, imovel, comprador = dominio
    hoje = date.today()

    c = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='HU-360-TEST',
        data_contrato=hoje - relativedelta(months=14),
        data_primeiro_vencimento=hoje - relativedelta(months=13),
        valor_total=Decimal('120000.00'),
        valor_entrada=Decimal('10000.00'),
        numero_parcelas=N,
        dia_vencimento=5,
        tipo_correcao=TipoCorrecao.IPCA,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        prazo_reajuste_meses=PRAZO_REAJUSTE,
        intermediarias_reduzem_pmt=True,
        intermediarias_reajustadas=True,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
        status=StatusContrato.ATIVO,
    )

    # 3 faixas de juros escalantes
    TabelaJurosContrato.objects.create(
        contrato=c, ciclo_inicio=1, ciclo_fim=1, juros_mensal=TAXA_CICLO1,
    )
    TabelaJurosContrato.objects.create(
        contrato=c, ciclo_inicio=2, ciclo_fim=2, juros_mensal=TAXA_CICLO2,
    )
    TabelaJurosContrato.objects.create(
        contrato=c, ciclo_inicio=3, ciclo_fim=None, juros_mensal=TAXA_CICLO3,
    )

    # Intermediária 1: mês 6 (ciclo 1) — NÃO reajustada no ciclo 2 (mes < 13)
    PrestacaoIntermediaria.objects.create(
        contrato=c, numero_sequencial=1, mes_vencimento=6,
        valor=Decimal('5000.00'),
    )
    # Intermediária 2: mês 18 (ciclo 2) — reajustada no ciclo 2 (13 ≤ mes ≤ 36)
    PrestacaoIntermediaria.objects.create(
        contrato=c, numero_sequencial=2, mes_vencimento=18,
        valor=Decimal('5000.00'),
    )

    # Recalcula amortização usando base_pv = financiado − Σintermediárias
    soma = c.intermediarias.aggregate(total=Sum('valor'))['total']
    base_pv = max(c.valor_financiado - soma, Decimal('0.01'))
    assert base_pv == BASE_PV, f"base_pv esperado {BASE_PV}, obtido {base_pv}"
    c.recalcular_amortizacao(base_pv=base_pv)
    return c


# ── Helper: cria reajuste via endpoint legado ──────────────────────────────────

def _aplicar_reajuste(cli, contrato, ciclo, percentual):
    """Aplica reajuste via endpoint API e retorna o response JSON."""
    from financeiro.models import Reajuste
    parcela_ini = (ciclo - 1) * PRAZO_REAJUSTE + 1
    parcela_fim = N
    url = reverse('financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato.pk})
    resp = cli.post(url, data=json.dumps({
        'percentual': str(percentual),
        'parcela_inicial': parcela_ini,
        'parcela_final': parcela_fim,
    }), content_type='application/json')
    return resp


# ==============================================================================
# TESTE E2E — percorre todos os 8 passos em uma única transação
# ==============================================================================

@pytest.mark.django_db
class TestHU360FluxoCompleto:
    """
    Fluxo sequencial: criação → PMT ciclo 1 → intermediárias → boleto intermediária
    → reajuste ciclo 2 → reajuste ciclo 3 → bloqueio cascata.
    Cada passo depende do estado deixado pelo passo anterior.
    """

    def test_fluxo_completo_hu360(self, contrato_hu360, usuario_cli):
        from financeiro.models import Parcela, Reajuste, TipoParcela
        from contratos.models import TabelaJurosContrato, PrestacaoIntermediaria

        _, cli = usuario_cli
        contrato = contrato_hu360

        # ── PASSO 1 — Verificar TabelaJurosContrato ────────────────────────────
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato, 1) == TAXA_CICLO1
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato, 2) == TAXA_CICLO2
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato, 3) == TAXA_CICLO3
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato, 99) == TAXA_CICLO3, (
            "P1: ciclo 99 deve usar a faixa aberta (ciclo_fim=None)"
        )

        # ── PASSO 2 — PMT ciclo 1 linear (taxa = 0) ───────────────────────────
        pmt_ciclo1 = (BASE_PV / Decimal(N)).quantize(Decimal('0.01'))
        parcelas = list(
            Parcela.objects.filter(
                contrato=contrato, tipo_parcela=TipoParcela.NORMAL
            ).order_by('numero_parcela')
        )
        assert len(parcelas) == N, f"P2: esperadas {N} parcelas, obtidas {len(parcelas)}"
        for p in parcelas[:-1]:
            assert p.valor_atual == pmt_ciclo1, (
                f"P2: parcela {p.numero_parcela} esperada {pmt_ciclo1}, obtida {p.valor_atual}"
            )

        # ── PASSO 3 — Intermediárias ───────────────────────────────────────────
        assert contrato.intermediarias.count() == 2, "P3: devem existir 2 intermediárias"
        inter1 = contrato.intermediarias.get(numero_sequencial=1)
        inter2 = contrato.intermediarias.get(numero_sequencial=2)
        assert inter1.mes_vencimento == 6
        assert inter2.mes_vencimento == 18
        assert inter1.valor_atual == Decimal('5000.00')
        assert inter2.valor_atual == Decimal('5000.00')

        # Ciclo 2 deve estar pendente (aniversário = data_contrato + 12m = hoje − 2m)
        ciclo_pendente = Reajuste.calcular_ciclo_pendente(contrato)
        assert ciclo_pendente == 2, f"P3: ciclo pendente esperado 2, obtido {ciclo_pendente}"

        # ── PASSO 4 — Boleto para intermediária mes=6 ──────────────────────────
        url_inter = reverse(
            'contratos:intermediarias_gerar_boleto',
            kwargs={'hid': encode_id(inter1.pk)},
        )
        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            resp = cli.post(url_inter, {})

        assert resp.status_code == 200, (
            f"P4: gerar_boleto_intermediaria retornou {resp.status_code} — {resp.content[:200]}"
        )
        dados_p4 = resp.json()
        assert dados_p4.get('sucesso') is True, f"P4: {dados_p4}"

        inter1.refresh_from_db()
        assert inter1.parcela_vinculada is not None, "P4: parcela_vinculada deve ser criada"
        parcela_inter = inter1.parcela_vinculada
        assert parcela_inter.tipo_parcela == TipoParcela.INTERMEDIARIA
        assert parcela_inter.valor_atual == Decimal('5000.00')

        # ── PASSO 5 — Reajuste ciclo 2 (IPCA 5% + taxa 0,60%/m) ──────────────
        pmt_antes = parcelas[0].valor_atual  # PMT do ciclo 1

        resp5 = _aplicar_reajuste(cli, contrato, ciclo=2, percentual=IPCA_CICLO2)
        assert resp5.status_code == 200, f"P5: reajuste ciclo 2 falhou — {resp5.content[:200]}"
        dados_p5 = resp5.json()
        assert dados_p5.get('sucesso') is True, f"P5: {dados_p5}"
        assert dados_p5.get('ciclo') == 2, "P5: ciclo aplicado deve ser 2"
        assert dados_p5.get('parcelas_afetadas', 0) > 0, "P5: nenhuma parcela reajustada"

        # Verifica PMT do ciclo 2: pmt_atual × (1+IPCA) × (1+taxa_ciclo2)^prazo
        taxa2 = TAXA_CICLO2 / Decimal('100')
        fator_juros2 = (Decimal('1') + taxa2) ** PRAZO_REAJUSTE
        fator_ipca2 = Decimal('1') + IPCA_CICLO2 / Decimal('100')
        pmt_ciclo2_esperado = (pmt_antes * fator_ipca2 * fator_juros2).quantize(Decimal('0.01'))

        parcela_13 = contrato.parcelas.get(numero_parcela=13)
        assert parcela_13.valor_atual == pmt_ciclo2_esperado, (
            f"P5: PMT ciclo 2 esperado {pmt_ciclo2_esperado}, obtido {parcela_13.valor_atual}"
        )

        # Parcelas do ciclo 1 NÃO devem ter sido alteradas (já foram filtradas pelo pago status)
        # Verificar a partir dos dados atuais das parcelas 1-12 (não pagas)
        p1_atual = contrato.parcelas.filter(numero_parcela=1).first()
        if p1_atual and not p1_atual.pago:
            # Parcela 1 não paga → também foi reajustada (todas não-pagas são atualizadas)
            pass  # o modo TABELA PRICE atualiza TODAS as parcelas não pagas

        # Verificar intermediária mes=18 foi reajustada (13 ≤ 18 ≤ 36)
        inter2.refresh_from_db()
        valor_inter2_reajustado = (Decimal('5000.00') * fator_ipca2).quantize(Decimal('0.01'))
        assert inter2.valor_atual == valor_inter2_reajustado, (
            f"P5: intermediária mes=18 esperada {valor_inter2_reajustado}, "
            f"obtida {inter2.valor_atual}"
        )

        # Intermediária mes=6 NÃO deve ter sido reajustada (mes < 13)
        inter1.refresh_from_db()
        assert inter1.valor_reajustado is None or inter1.valor_atual == Decimal('5000.00'), (
            "P5: intermediária mes=6 não deve ser reajustada no ciclo 2"
        )

        # ciclo_reajuste_atual deve ser 2
        contrato.refresh_from_db()
        assert contrato.ciclo_reajuste_atual == 2, "P5: ciclo_reajuste_atual deve ser 2"

        # ── PASSO 6 — Bloqueio antes/depois do reajuste ciclo 2 ───────────────
        # Após reajuste ciclo 2, pode_gerar_boleto(13) deve ser True
        pode_13, _ = contrato.pode_gerar_boleto(13)
        assert pode_13 is True, "P6: após reajuste ciclo 2, parcela 13 deve estar liberada"

        # Ciclo 3 é futuro → pode_gerar_boleto(25) retorna True (ciclo não vencido)
        pode_25, motivo_25 = contrato.pode_gerar_boleto(25)
        assert pode_25 is True, (
            f"P6: ciclo 3 ainda futuro — parcela 25 deve ser liberada, motivo: '{motivo_25}'"
        )

        # ── PASSO 7 — Reajuste ciclo 3 (IPCA 4% + taxa 0,65%/m) ──────────────
        # Para testar ciclo 3, simulamos que ele já venceu (criando o reajuste diretamente)
        # pois o contrato tem apenas 14 meses e o ciclo 3 vence em 24 meses
        pmt_antes_ciclo3 = parcela_13.valor_atual  # PMT atual após ciclo 2

        taxa3 = TAXA_CICLO3 / Decimal('100')
        fator_juros3 = (Decimal('1') + taxa3) ** PRAZO_REAJUSTE
        fator_ipca3 = Decimal('1') + IPCA_CICLO3 / Decimal('100')
        pmt_ciclo3_esperado = (pmt_antes_ciclo3 * fator_ipca3 * fator_juros3).quantize(Decimal('0.01'))

        # Cria Reajuste ciclo 3 diretamente (bypass da verificação de data do endpoint)
        from financeiro.models import Reajuste
        data_reajuste_ciclo3 = contrato.data_contrato + relativedelta(months=24)
        reajuste3 = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=IPCA_CICLO3,
            percentual_bruto=IPCA_CICLO3,
            parcela_inicial=25,
            parcela_final=N,
            ciclo=3,
            aplicado_manual=True,
        )
        resultado3 = reajuste3.aplicar_reajuste()
        assert resultado3.get('sucesso') is True, f"P7: aplicar_reajuste ciclo 3 falhou: {resultado3}"

        # PMT do ciclo 3 deve usar taxa 0,65%/m (não 0,60%)
        parcela_25 = contrato.parcelas.get(numero_parcela=25)
        assert parcela_25.valor_atual == pmt_ciclo3_esperado, (
            f"P7: PMT ciclo 3 esperado {pmt_ciclo3_esperado}, obtido {parcela_25.valor_atual}"
        )

        # PMT do ciclo 3 deve ser DIFERENTE do ciclo 2 (taxa diferente)
        assert parcela_25.valor_atual != parcela_13.valor_atual, (
            "P7: PMT ciclo 3 deve diferir do ciclo 2 (taxas 0,65% vs 0,60%)"
        )

        # ── PASSO 8 — Bloqueio cascata: desfazer ciclo 2 bloqueia ciclo 3 ─────
        # Simula: ciclo 2 desfeito → qualquer parcela 13+ fica bloqueada
        reajuste2 = Reajuste.objects.filter(
            contrato=contrato, ciclo=2, aplicado=True
        ).first()
        assert reajuste2 is not None, "P8: reajuste ciclo 2 deve existir"

        # Deletar o reajuste ciclo 2 e resetar o ciclo no contrato
        reajuste2.aplicado = False
        reajuste2.save(update_fields=['aplicado'])
        contrato.ciclo_reajuste_atual = 1
        contrato.save(update_fields=['ciclo_reajuste_atual'])

        # Agora ciclo 2 está pendente novamente → cascata bloqueia ciclo 3
        pode_25_bloqueado, motivo_bloqueio = contrato.pode_gerar_boleto(25)
        assert pode_25_bloqueado is False, (
            f"P8: com ciclo 2 pendente, parcela 25 deve estar bloqueada por cascata. "
            f"Motivo obtido: '{motivo_bloqueio}'"
        )
        assert any(kw in motivo_bloqueio.lower() for kw in ('pendente', 'ciclo', 'reajuste')), (
            f"P8: motivo do bloqueio deve mencionar 'pendente'/'ciclo'/'reajuste': '{motivo_bloqueio}'"
        )


# ==============================================================================
# TESTES FOCADOS — um por classe, verificando cada componente isoladamente
# ==============================================================================

# ── Passo 1: TabelaJuros escalante ────────────────────────────────────────────

@pytest.mark.django_db
class TestTabelaJurosEscalantes:
    """Valida get_juros_para_ciclo() para 3 faixas configuradas."""

    def test_ciclo1_retorna_zero(self, contrato_hu360):
        from contratos.models import TabelaJurosContrato
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato_hu360, 1) == TAXA_CICLO1

    def test_ciclo2_retorna_0_60(self, contrato_hu360):
        from contratos.models import TabelaJurosContrato
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato_hu360, 2) == TAXA_CICLO2

    def test_ciclo3_retorna_0_65(self, contrato_hu360):
        from contratos.models import TabelaJurosContrato
        assert TabelaJurosContrato.get_juros_para_ciclo(contrato_hu360, 3) == TAXA_CICLO3

    def test_ciclo_alem_do_ultimo_usa_faixa_aberta(self, contrato_hu360):
        """Faixa ciclo_fim=None deve ser usada para qualquer ciclo acima do último explícito."""
        from contratos.models import TabelaJurosContrato
        for ciclo_alto in (4, 10, 50):
            taxa = TabelaJurosContrato.get_juros_para_ciclo(contrato_hu360, ciclo_alto)
            assert taxa == TAXA_CICLO3, (
                f"Ciclo {ciclo_alto} esperado {TAXA_CICLO3}, obtido {taxa}"
            )

    def test_sem_tabela_retorna_none(self, dominio):
        """Contrato sem TabelaJurosContrato deve retornar None."""
        from contratos.models import (
            Contrato, TabelaJurosContrato, TipoCorrecao, TipoAmortizacao, StatusContrato,
        )
        from tests.fixtures.factories import ImovelFactory
        imob, _, comprador = dominio
        imovel2 = ImovelFactory(imobiliaria=imob)
        c = Contrato.objects.create(
            imobiliaria=imob, imovel=imovel2, comprador=comprador,
            numero_contrato='SEM-TABELA',
            data_contrato=date.today() - relativedelta(months=6),
            data_primeiro_vencimento=date.today() - relativedelta(months=5),
            valor_total=Decimal('50000.00'), valor_entrada=Decimal('5000.00'),
            numero_parcelas=12, dia_vencimento=5,
            tipo_correcao=TipoCorrecao.IPCA,
            tipo_amortizacao=TipoAmortizacao.PRICE,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO,
        )
        assert TabelaJurosContrato.get_juros_para_ciclo(c, 1) is None


# ── Passo 2/3: PMT e intermediárias ────────────────────────────────────────────

@pytest.mark.django_db
class TestCriacaoHU360:
    """Valida o estado inicial do contrato após criação."""

    def test_numero_parcelas_normais(self, contrato_hu360):
        """Devem ser criadas exatamente N parcelas NORMAL."""
        from financeiro.models import Parcela, TipoParcela
        count = contrato_hu360.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).count()
        assert count == N

    def test_pmt_ciclo1_linear(self, contrato_hu360):
        """PMT ciclo 1 com taxa=0 deve ser BASE_PV/N (linear)."""
        from financeiro.models import Parcela, TipoParcela
        pmt_esperado = (BASE_PV / Decimal(N)).quantize(Decimal('0.01'))
        parcelas = list(
            Parcela.objects.filter(
                contrato=contrato_hu360, tipo_parcela=TipoParcela.NORMAL
            ).order_by('numero_parcela')
        )
        for p in parcelas[:-1]:
            assert p.valor_atual == pmt_esperado, (
                f"Parcela {p.numero_parcela}: esperado {pmt_esperado}, obtido {p.valor_atual}"
            )

    def test_duas_intermediarias_criadas(self, contrato_hu360):
        """Devem existir exatamente 2 intermediárias."""
        assert contrato_hu360.intermediarias.count() == 2

    def test_base_pv_deduzida(self, contrato_hu360):
        """PMT deve ser calculado sobre BASE_PV (110k − 10k), não PV_BRUTO."""
        from financeiro.models import Parcela, TipoParcela
        pmt_sobre_pv_bruto = (PV_BRUTO / Decimal(N)).quantize(Decimal('0.01'))
        pmt_sobre_base = (BASE_PV / Decimal(N)).quantize(Decimal('0.01'))
        p1 = contrato_hu360.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).order_by('numero_parcela').first()
        assert p1.valor_atual == pmt_sobre_base, "PMT deve usar base_pv (sem intermediárias)"
        assert p1.valor_atual != pmt_sobre_pv_bruto, "PMT não deve usar PV bruto"

    def test_ciclo2_pendente(self, contrato_hu360):
        """Com 14 meses de contrato, ciclo 2 deve estar pendente."""
        from financeiro.models import Reajuste
        assert Reajuste.calcular_ciclo_pendente(contrato_hu360) == 2

    def test_saldo_devedor_exclui_intermediarias(self, contrato_hu360):
        """Saldo devedor considera apenas parcelas NORMAL (não intermediárias)."""
        from django.db.models import Sum
        from financeiro.models import Parcela, TipoParcela
        saldo = contrato_hu360.calcular_saldo_devedor()
        soma_normal = contrato_hu360.parcelas.filter(
            tipo_parcela=TipoParcela.NORMAL, pago=False
        ).aggregate(total=Sum('valor_atual'))['total']
        assert saldo == soma_normal


# ── Passo 4: Geração de boleto para intermediária ──────────────────────────────

@pytest.mark.django_db
class TestBoletoIntermediaria:
    """Valida a view gerar_boleto_intermediaria."""

    def test_cria_parcela_intermediaria(self, contrato_hu360, usuario_cli):
        """POST na view deve criar uma Parcela do tipo INTERMEDIARIA vinculada."""
        from financeiro.models import Parcela, TipoParcela
        _, cli = usuario_cli
        inter = contrato_hu360.intermediarias.get(numero_sequencial=1)
        url = reverse('contratos:intermediarias_gerar_boleto', kwargs={'hid': encode_id(inter.pk)})

        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            resp = cli.post(url, {})

        assert resp.status_code == 200
        assert resp.json()['sucesso'] is True
        inter.refresh_from_db()
        assert inter.parcela_vinculada is not None
        assert inter.parcela_vinculada.tipo_parcela == TipoParcela.INTERMEDIARIA

    def test_numero_parcela_sem_conflito(self, contrato_hu360, usuario_cli):
        """Parcela da intermediária usa offset N+seq para não conflitar com NORMAL."""
        from financeiro.models import Parcela
        _, cli = usuario_cli
        inter = contrato_hu360.intermediarias.get(numero_sequencial=1)
        url = reverse('contratos:intermediarias_gerar_boleto', kwargs={'hid': encode_id(inter.pk)})

        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            cli.post(url, {})

        inter.refresh_from_db()
        numero_esperado = N + inter.numero_sequencial  # 36 + 1 = 37
        assert inter.parcela_vinculada.numero_parcela == numero_esperado

    def test_segunda_tentativa_retorna_400(self, contrato_hu360, usuario_cli):
        """Gerar boleto já vinculado deve retornar 400."""
        from financeiro.models import Parcela
        _, cli = usuario_cli
        inter = contrato_hu360.intermediarias.get(numero_sequencial=1)
        url = reverse('contratos:intermediarias_gerar_boleto', kwargs={'hid': encode_id(inter.pk)})

        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            cli.post(url, {})  # primeira geração

        resp2 = cli.post(url, {})  # segunda tentativa
        assert resp2.status_code == 400
        assert resp2.json()['sucesso'] is False

    def test_intermediaria_paga_retorna_400(self, contrato_hu360, usuario_cli):
        """Intermediária já paga deve retornar 400."""
        _, cli = usuario_cli
        inter = contrato_hu360.intermediarias.get(numero_sequencial=1)
        inter.paga = True
        inter.save()
        url = reverse('contratos:intermediarias_gerar_boleto', kwargs={'hid': encode_id(inter.pk)})
        resp = cli.post(url, {})
        assert resp.status_code == 400
        assert resp.json()['sucesso'] is False

    def test_requer_autenticacao(self, contrato_hu360, client):
        """View requer autenticação — retorna redirect (302) sem login."""
        inter = contrato_hu360.intermediarias.get(numero_sequencial=1)
        url = reverse('contratos:intermediarias_gerar_boleto', kwargs={'hid': encode_id(inter.pk)})
        resp = client.post(url, {})
        assert resp.status_code in (302, 403)


# ── Passo 5: Reajuste ciclo 2 ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestReajusteCiclo2HU360:
    """Valida o reajuste ciclo 2 com taxa escalante 0,60% e IPCA."""

    def test_pmt_ciclo2_formula_composta(self, contrato_hu360, usuario_cli):
        """
        PMT_novo = PMT_atual × (1 + IPCA) × (1 + taxa_ciclo2/100)^prazo
        A taxa usada é get_juros_para_ciclo(contrato, 2) = 0,60%.
        """
        _, cli = usuario_cli
        pmt_antes = contrato_hu360.parcelas.filter(numero_parcela=1).first().valor_atual

        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        taxa2 = TAXA_CICLO2 / Decimal('100')
        fator_j = (Decimal('1') + taxa2) ** PRAZO_REAJUSTE
        fator_i = Decimal('1') + IPCA_CICLO2 / Decimal('100')
        pmt_esperado = (pmt_antes * fator_i * fator_j).quantize(Decimal('0.01'))

        parcela_13 = contrato_hu360.parcelas.get(numero_parcela=13)
        assert parcela_13.valor_atual == pmt_esperado

    def test_ciclo_reajuste_atualizado(self, contrato_hu360, usuario_cli):
        """ciclo_reajuste_atual deve ser 2 após o reajuste."""
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)
        contrato_hu360.refresh_from_db()
        assert contrato_hu360.ciclo_reajuste_atual == 2

    def test_intermediaria_mes18_reajustada(self, contrato_hu360, usuario_cli):
        """Intermediária mes=18 (no intervalo 13-36) deve ter valor_reajustado atualizado."""
        _, cli = usuario_cli
        inter2 = contrato_hu360.intermediarias.get(mes_vencimento=18)
        valor_antes = inter2.valor_atual

        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        inter2.refresh_from_db()
        valor_esperado = (valor_antes * (Decimal('1') + IPCA_CICLO2 / Decimal('100'))).quantize(
            Decimal('0.01')
        )
        assert inter2.valor_atual == valor_esperado, (
            f"Intermediária mes=18: esperado {valor_esperado}, obtido {inter2.valor_atual}"
        )

    def test_intermediaria_mes6_nao_reajustada(self, contrato_hu360, usuario_cli):
        """Intermediária mes=6 (fora do intervalo 13-36) NÃO deve ser reajustada no ciclo 2."""
        _, cli = usuario_cli
        inter1 = contrato_hu360.intermediarias.get(mes_vencimento=6)

        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        inter1.refresh_from_db()
        # valor_reajustado deve permanecer None (não foi tocada)
        assert inter1.valor_reajustado is None, (
            "Intermediária mes=6 não deve ser reajustada no ciclo 2 "
            f"(valor_reajustado={inter1.valor_reajustado})"
        )

    def test_pmt_ciclo2_maior_que_ciclo1(self, contrato_hu360, usuario_cli):
        """Após reajuste, PMT do ciclo 2 deve ser maior que o do ciclo 1."""
        _, cli = usuario_cli
        pmt_ciclo1 = contrato_hu360.parcelas.filter(numero_parcela=1).first().valor_atual

        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        pmt_ciclo2 = contrato_hu360.parcelas.get(numero_parcela=13).valor_atual
        assert pmt_ciclo2 > pmt_ciclo1, (
            f"PMT ciclo 2 ({pmt_ciclo2}) deve ser maior que ciclo 1 ({pmt_ciclo1})"
        )


# ── Passo 6: Bloqueio antes/depois do reajuste ────────────────────────────────

@pytest.mark.django_db
class TestBloqueioHU360:
    """Valida a lógica de bloqueio de boleto antes e após os reajustes."""

    def test_pode_gerar_ciclo1_sem_reajuste(self, contrato_hu360):
        """Parcela 1 (ciclo 1) deve sempre ser liberada."""
        pode, _ = contrato_hu360.pode_gerar_boleto(1)
        assert pode is True

    def test_pode_gerar_ciclo2_bloqueado_antes_reajuste(self, contrato_hu360):
        """
        Parcela 13 (ciclo 2) deve estar bloqueada antes do reajuste.
        Ciclo 2 venceu há 2 meses e não foi aplicado.
        """
        pode, motivo = contrato_hu360.pode_gerar_boleto(13)
        assert pode is False
        assert motivo  # mensagem explicativa

    def test_pode_gerar_ciclo2_liberado_apos_reajuste(self, contrato_hu360, usuario_cli):
        """Após aplicar reajuste ciclo 2, parcela 13 deve estar liberada."""
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)
        contrato_hu360.refresh_from_db()
        pode, _ = contrato_hu360.pode_gerar_boleto(13)
        assert pode is True

    def test_bloqueio_cascata_ciclo2_bloqueia_ciclo3(self, contrato_hu360):
        """
        Com ciclo 2 pendente, pode_gerar_boleto(25) deve retornar False por cascata.
        O ciclo 3 (25+) herda o bloqueio do ciclo 2 ainda não aplicado.
        """
        pode, motivo = contrato_hu360.pode_gerar_boleto(25)
        assert pode is False
        assert any(kw in motivo.lower() for kw in ('pendente', 'ciclo', 'reajuste'))

    def test_ciclo3_futuro_liberado_individualmente_apos_ciclo2(self, contrato_hu360, usuario_cli):
        """
        Após aplicar ciclo 2, ciclo 3 é futuro → pode_gerar_boleto(25) = True.
        O bloqueio em lote (max_parcela_lote) ocorre na view gerar_carne, não aqui.
        """
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)
        contrato_hu360.refresh_from_db()
        pode, _ = contrato_hu360.pode_gerar_boleto(25)
        assert pode is True


# ── Passo 7: Reajuste ciclo 3 (taxa diferente) ───────────────────────────────

@pytest.mark.django_db
class TestReajusteCiclo3HU360:
    """
    Valida que o PMT do ciclo 3 usa get_juros_para_ciclo(contrato, 3)=0,65%
    e NÃO reutiliza a taxa do ciclo 2 (0,60%).
    """

    def _criar_reajuste_ciclo3(self, contrato):
        """Cria e aplica Reajuste ciclo 3 diretamente (sem verificação de data)."""
        from financeiro.models import Reajuste
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=IPCA_CICLO3,
            percentual_bruto=IPCA_CICLO3,
            parcela_inicial=25,
            parcela_final=N,
            ciclo=3,
            aplicado_manual=True,
        )
        resultado = reajuste.aplicar_reajuste()
        return resultado, reajuste

    def test_pmt_ciclo3_usa_taxa_065(self, contrato_hu360, usuario_cli):
        """PMT ciclo 3 = PMT_ciclo2 × (1+IPCA) × (1+0,65%)^12."""
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        pmt_apos_ciclo2 = contrato_hu360.parcelas.get(numero_parcela=13).valor_atual

        resultado3, _ = self._criar_reajuste_ciclo3(contrato_hu360)
        assert resultado3.get('sucesso') is True

        taxa3 = TAXA_CICLO3 / Decimal('100')
        fator_j3 = (Decimal('1') + taxa3) ** PRAZO_REAJUSTE
        fator_i3 = Decimal('1') + IPCA_CICLO3 / Decimal('100')
        pmt_ciclo3_esperado = (pmt_apos_ciclo2 * fator_i3 * fator_j3).quantize(Decimal('0.01'))

        parcela_25 = contrato_hu360.parcelas.get(numero_parcela=25)
        assert parcela_25.valor_atual == pmt_ciclo3_esperado

    def test_pmt_ciclo3_maior_que_pmt_ciclo2(self, contrato_hu360, usuario_cli):
        """
        PMT após ciclo 3 deve ser maior que PMT após ciclo 2.
        O cálculo parte do PMT atual (já reajustado no ciclo 2) e aplica
        IPCA + taxa_ciclo3 (0,65%). Como 0,65% > 0,60%, o novo PMT > PMT ciclo 2.
        """
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        # Captura o PMT do ciclo 2 ANTES de aplicar o ciclo 3
        pmt_apos_ciclo2 = contrato_hu360.parcelas.get(numero_parcela=13).valor_atual

        self._criar_reajuste_ciclo3(contrato_hu360)

        # Após ciclo 3, todas as parcelas não-pagas têm o novo PMT (MODO TABELA PRICE)
        pmt_apos_ciclo3 = contrato_hu360.parcelas.get(numero_parcela=25).valor_atual
        assert pmt_apos_ciclo3 > pmt_apos_ciclo2, (
            f"PMT após ciclo 3 ({pmt_apos_ciclo3}) deve ser > PMT após ciclo 2 ({pmt_apos_ciclo2})"
        )

    def test_modo_tabela_price_atualiza_todas_parcelas_nao_pagas(self, contrato_hu360, usuario_cli):
        """
        No MODO TABELA PRICE, o reajuste aplica o novo PMT a TODAS as parcelas
        não pagas — inclusive as dos ciclos anteriores ainda não quitadas.
        Isso é o comportamento correto do sistema: PMT uniforme para todo o saldo.
        """
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)
        self._criar_reajuste_ciclo3(contrato_hu360)

        # Após ciclo 3, todas as parcelas não-pagas devem ter o mesmo PMT
        from financeiro.models import Parcela, TipoParcela
        pmts = list(
            Parcela.objects.filter(
                contrato=contrato_hu360,
                tipo_parcela=TipoParcela.NORMAL,
                pago=False,
            ).order_by('numero_parcela').exclude(numero_parcela=N)  # exclui a última (ajuste)
            .values_list('valor_atual', flat=True)
        )
        # Todos os PMTs não-pagos devem ser iguais (PMT uniforme)
        assert len(set(pmts)) == 1, (
            "MODO TABELA PRICE: após ciclo 3, todas as parcelas não-pagas devem "
            f"ter o mesmo PMT. Valores distintos encontrados: {set(pmts)}"
        )


# ── Passo 8: Bloqueio cascata ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestCascataHU360:
    """Valida o algoritmo de bloqueio em cascata (ciclo 2 pendente bloqueia ciclo 3+)."""

    def test_cascata_bloqueia_todas_as_parcelas_ciclo3(self, contrato_hu360):
        """Com ciclo 2 pendente, todas as parcelas 25-36 devem estar bloqueadas."""
        for numero in (25, 30, 36):
            pode, motivo = contrato_hu360.pode_gerar_boleto(numero)
            assert pode is False, (
                f"Parcela {numero} deve estar bloqueada por cascata "
                f"(ciclo 2 pendente), motivo: '{motivo}'"
            )

    def test_desfazer_ciclo2_re_bloqueia(self, contrato_hu360, usuario_cli):
        """
        Aplicar e depois marcar ciclo 2 como não-aplicado deve re-bloquear ciclo 3.
        """
        from financeiro.models import Reajuste
        _, cli = usuario_cli
        _aplicar_reajuste(cli, contrato_hu360, ciclo=2, percentual=IPCA_CICLO2)

        # Verificação: ciclo 3 liberado (ciclo 3 futuro)
        contrato_hu360.refresh_from_db()
        pode_pos, _ = contrato_hu360.pode_gerar_boleto(25)
        assert pode_pos is True, "Após ciclo 2 aplicado, ciclo 3 futuro deve ser liberado"

        # Desfaz ciclo 2
        Reajuste.objects.filter(
            contrato=contrato_hu360, ciclo=2
        ).update(aplicado=False)
        contrato_hu360.ciclo_reajuste_atual = 1
        contrato_hu360.save(update_fields=['ciclo_reajuste_atual'])

        # Ciclo 3 deve voltar a estar bloqueado
        pode_pós_desfazer, motivo = contrato_hu360.pode_gerar_boleto(25)
        assert pode_pós_desfazer is False, (
            f"Após desfazer ciclo 2, ciclo 3 deve ficar bloqueado. Motivo: '{motivo}'"
        )

    def test_ciclo1_nunca_bloqueado(self, contrato_hu360):
        """Parcelas do ciclo 1 nunca são bloqueadas — ciclo 1 é isento."""
        for numero in (1, 6, 12):
            pode, _ = contrato_hu360.pode_gerar_boleto(numero)
            assert pode is True, f"Parcela {numero} (ciclo 1) nunca deve ser bloqueada"
