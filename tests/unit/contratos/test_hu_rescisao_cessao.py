"""
HU Rescisão e Cessão Contratual — Seção 7.9.2
==============================================

Cobre os métodos G-11 (calcular_rescisao) e G-12 (calcular_cessao) do modelo
Contrato, bem como as views correspondentes.

Cenários testados:
  - Cálculo correto de saldo devedor (PRICE)
  - Fórmula de fruição, multa penal e despesas administrativas
  - Devolução nunca negativa
  - Valor pago inclui entrada + parcelas pagas + intermediárias pagas
  - Cálculo de cessão (taxa = saldo × percentual_cessao)
  - Views GET/POST com autenticação
  - Fluxo completo: criar, pagar parcelas, calcular rescisão
"""

import pytest
from decimal import Decimal
from datetime import date

from django.test import Client
from django.urls import reverse


# ---------------------------------------------------------------------------
# Constantes do contrato base
# ---------------------------------------------------------------------------

VALOR_TOTAL = Decimal('120000.00')
VALOR_ENTRADA = Decimal('20000.00')
VALOR_FINANCIADO = Decimal('100000.00')
NUMERO_PARCELAS = 24

# PMT linear (sem juros, apenas divisão): 100000 / 24 = 4166.67 (arredondado)
PMT_LINEAR = (VALOR_FINANCIADO / NUMERO_PARCELAS).quantize(Decimal('0.01'))

# Datas fixas para meses_ocupados determinístico
DATA_CONTRATO = date(2025, 1, 1)
DATA_RESCISAO_4M = date(2025, 5, 1)   # 4 meses após início
DATA_RESCISAO_12M = date(2026, 1, 1)  # 12 meses após início

# Defaults do modelo Contrato
PCT_FRUICAO = Decimal('0.5000')
PCT_PENAL = Decimal('10.0000')
PCT_ADM = Decimal('12.0000')
PCT_CESSAO = Decimal('3.0000')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio(db):
    """Cria domínio básico (imobiliária + conta + imóvel + comprador)."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    imob = ImobiliariaFactory(nome='Imobiliária Rescisão')
    ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador Rescisão')
    return imob, imovel, comprador


@pytest.fixture
def usuario_cli(db, dominio):
    """Usuário autenticado e Client Django."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(
        username='rescisao_user',
        password='Rescisao1!',
        email='rescisao@test.com',
    )
    c = Client()
    c.force_login(u)
    return u, c


def _criar_contrato(imob, imovel, comprador, numero='CTR-RESCISAO-001', **kwargs):
    """Helper para criar contrato com defaults sensatos para testes de rescisão."""
    from contratos.models import (
        Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
    )
    defaults = dict(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato=numero,
        data_contrato=DATA_CONTRATO,
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=VALOR_TOTAL,
        valor_entrada=VALOR_ENTRADA,
        numero_parcelas=NUMERO_PARCELAS,
        dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA,
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
        percentual_fruicao=PCT_FRUICAO,
        percentual_multa_rescisao_penal=PCT_PENAL,
        percentual_multa_rescisao_adm=PCT_ADM,
        percentual_cessao=PCT_CESSAO,
    )
    defaults.update(kwargs)
    return Contrato.objects.create(**defaults)


def _pagar_parcelas(contrato, quantidade):
    """Marca as primeiras `quantidade` parcelas NORMAL como pagas."""
    parcelas = list(
        contrato.parcelas.order_by('numero_parcela')[:quantidade]
    )
    for p in parcelas:
        p.pago = True
        p.valor_pago = p.valor_atual
        p.save(update_fields=['pago', 'valor_pago'])
    return parcelas


@pytest.fixture
def contrato_com_parcelas(db, dominio):
    """
    Contrato de 24 parcelas lineares, 4 primeiras pagas.

    Estrutura financeira:
      valor_total      = R$ 120.000
      valor_entrada    = R$  20.000
      valor_financiado = R$ 100.000
      numero_parcelas  = 24
      PMT linear       ≈ R$  4.166,67
      data_contrato    = 2025-01-01

    Estado: 4 parcelas pagas (PMT_LINEAR cada).
    Saldo devedor  = 20 × PMT_LINEAR
    Valor pago     = 20.000 + 4 × PMT_LINEAR
    """
    imob, imovel, comprador = dominio
    contrato = _criar_contrato(imob, imovel, comprador)
    _pagar_parcelas(contrato, 4)
    return contrato


@pytest.fixture
def contrato_com_intermediaria_paga(db, dominio):
    """Contrato com 4 parcelas pagas + 1 intermediária paga de R$ 5.000."""
    from contratos.models import PrestacaoIntermediaria
    imob, imovel, comprador = dominio
    contrato = _criar_contrato(imob, imovel, comprador, numero='CTR-RESCISAO-002')
    _pagar_parcelas(contrato, 4)

    # Intermediária paga no mês 3
    PrestacaoIntermediaria.objects.create(
        contrato=contrato,
        numero_sequencial=1,
        mes_vencimento=3,
        valor=Decimal('5000.00'),
        paga=True,
        valor_pago=Decimal('5000.00'),
        data_pagamento=date(2025, 4, 1),
    )
    return contrato


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _saldo_esperado(contrato):
    """Soma valor_atual das parcelas NORMAL não pagas."""
    from django.db.models import Sum
    return (
        contrato.parcelas.filter(pago=False).aggregate(s=Sum('valor_atual'))['s']
        or Decimal('0.00')
    )


def _calc_esperado(contrato, data_rescisao):
    """Replica a fórmula de calcular_rescisao() para comparação."""
    from django.db.models import Sum

    saldo = _saldo_esperado(contrato)
    meses = max(
        0,
        (data_rescisao.year - contrato.data_contrato.year) * 12
        + (data_rescisao.month - contrato.data_contrato.month),
    )
    tot_parcelas = (
        contrato.parcelas.filter(pago=True).aggregate(t=Sum('valor_pago'))['t']
        or Decimal('0.00')
    )
    tot_inter = (
        contrato.intermediarias.filter(paga=True).aggregate(t=Sum('valor_pago'))['t']
        or Decimal('0.00')
    )
    tot_pago = (contrato.valor_entrada or Decimal('0')) + tot_parcelas + tot_inter

    pct_f = (contrato.percentual_fruicao or PCT_FRUICAO) / Decimal('100')
    pct_p = (contrato.percentual_multa_rescisao_penal or PCT_PENAL) / Decimal('100')
    pct_a = (contrato.percentual_multa_rescisao_adm or PCT_ADM) / Decimal('100')

    fruicao = (saldo * pct_f * meses).quantize(Decimal('0.01'))
    penal = (saldo * pct_p).quantize(Decimal('0.01'))
    adm = (saldo * pct_a).quantize(Decimal('0.01'))
    retencoes = fruicao + penal + adm
    devolucao = max(
        Decimal('0.00'),
        (tot_pago - retencoes).quantize(Decimal('0.01')),
    )
    return dict(
        saldo=saldo, meses=meses, tot_pago=tot_pago,
        fruicao=fruicao, penal=penal, adm=adm,
        retencoes=retencoes, devolucao=devolucao,
    )


# ---------------------------------------------------------------------------
# TestCalcularRescisaoEstrutura
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCalcularRescisaoEstrutura:
    """Verifica que o retorno de calcular_rescisao() tem todas as chaves."""

    def test_retorno_contem_todas_as_chaves(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert {
            'data_rescisao', 'saldo_devedor', 'meses_ocupados',
            'valor_pago_total', 'valor_entrada', 'valor_pago_parcelas',
            'valor_pago_intermediarias', 'percentual_fruicao',
            'fruicao', 'percentual_multa_penal', 'multa_penal',
            'percentual_desp_adm', 'desp_adm', 'total_retencoes', 'devolucao',
        } == set(r.keys())

    def test_data_rescisao_preservada_no_retorno(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['data_rescisao'] == DATA_RESCISAO_4M

    def test_sem_data_usa_hoje(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao()
        assert r['data_rescisao'] == date.today()


# ---------------------------------------------------------------------------
# TestFormulasRescisao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFormulasRescisao:
    """Verifica os cálculos internos de rescisão."""

    def test_saldo_devedor_soma_parcelas_nao_pagas(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['saldo_devedor'] == _saldo_esperado(contrato_com_parcelas)

    def test_meses_ocupados_correto(self, contrato_com_parcelas):
        # DATA_CONTRATO=2025-01-01, DATA_RESCISAO_4M=2025-05-01 → 4 meses
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['meses_ocupados'] == 4

    def test_meses_ocupados_12_meses(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_12M)
        assert r['meses_ocupados'] == 12

    def test_meses_ocupados_nunca_negativo(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(date(2024, 12, 1))
        assert r['meses_ocupados'] == 0

    def test_valor_pago_inclui_entrada(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['valor_entrada'] == VALOR_ENTRADA
        assert r['valor_pago_total'] >= VALOR_ENTRADA

    def test_valor_pago_inclui_parcelas_pagas(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        esperado = (PMT_LINEAR * 4).quantize(Decimal('0.01'))
        assert r['valor_pago_parcelas'] == esperado

    def test_valor_pago_inclui_intermediarias_pagas(self, contrato_com_intermediaria_paga):
        r = contrato_com_intermediaria_paga.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['valor_pago_intermediarias'] == Decimal('5000.00')
        esperado = (VALOR_ENTRADA + PMT_LINEAR * 4 + Decimal('5000.00')).quantize(Decimal('0.01'))
        assert r['valor_pago_total'] == esperado

    def test_fruicao_formula(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        saldo = r['saldo_devedor']
        esperado = (saldo * PCT_FRUICAO / Decimal('100') * 4).quantize(Decimal('0.01'))
        assert r['fruicao'] == esperado

    def test_multa_penal_formula(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        saldo = r['saldo_devedor']
        esperado = (saldo * PCT_PENAL / Decimal('100')).quantize(Decimal('0.01'))
        assert r['multa_penal'] == esperado

    def test_desp_adm_formula(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        saldo = r['saldo_devedor']
        esperado = (saldo * PCT_ADM / Decimal('100')).quantize(Decimal('0.01'))
        assert r['desp_adm'] == esperado

    def test_total_retencoes_soma_encargos(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['total_retencoes'] == r['fruicao'] + r['multa_penal'] + r['desp_adm']

    def test_devolucao_formula(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        esperado = max(
            Decimal('0.00'),
            (r['valor_pago_total'] - r['total_retencoes']).quantize(Decimal('0.01')),
        )
        assert r['devolucao'] == esperado

    def test_devolucao_nunca_negativa_encargos_altos(self, db, dominio):
        """Quando encargos superam valor pago, devolução = 0."""
        imob, imovel, comprador = dominio
        contrato = _criar_contrato(
            imob, imovel, comprador, numero='CTR-RESCISAO-NEG',
            percentual_fruicao=Decimal('5.0000'),
            percentual_multa_rescisao_penal=Decimal('50.0000'),
            percentual_multa_rescisao_adm=Decimal('40.0000'),
        )
        # Pagar só 1 parcela — valor pago mínimo
        _pagar_parcelas(contrato, 1)
        r = contrato.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['devolucao'] == Decimal('0.00')

    def test_percentuais_customizados_refletidos_no_resultado(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        assert r['percentual_fruicao'] == PCT_FRUICAO
        assert r['percentual_multa_penal'] == PCT_PENAL
        assert r['percentual_desp_adm'] == PCT_ADM

    def test_resultado_coincide_com_calculo_manual(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_rescisao(DATA_RESCISAO_4M)
        esp = _calc_esperado(contrato_com_parcelas, DATA_RESCISAO_4M)
        assert r['saldo_devedor'] == esp['saldo']
        assert r['meses_ocupados'] == esp['meses']
        assert r['fruicao'] == esp['fruicao']
        assert r['multa_penal'] == esp['penal']
        assert r['desp_adm'] == esp['adm']
        assert r['devolucao'] == esp['devolucao']


# ---------------------------------------------------------------------------
# TestCalcularCessao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCalcularCessao:
    """Testes do método G-12 calcular_cessao."""

    def test_retorno_contem_todas_as_chaves(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_cessao(DATA_RESCISAO_4M)
        assert {'data_cessao', 'saldo_devedor', 'percentual_cessao',
                'taxa_cessao', 'saldo_apos_cessao'} == set(r.keys())

    def test_taxa_cessao_formula_correta(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_cessao(DATA_RESCISAO_4M)
        saldo = _saldo_esperado(contrato_com_parcelas)
        esperado = (saldo * PCT_CESSAO / Decimal('100')).quantize(Decimal('0.01'))
        assert r['taxa_cessao'] == esperado

    def test_saldo_nao_se_altera_na_cessao(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_cessao(DATA_RESCISAO_4M)
        assert r['saldo_apos_cessao'] == r['saldo_devedor']

    def test_percentual_cessao_customizado(self, db, dominio):
        """Taxa de cessão diferente do padrão 3% é respeitada."""
        imob, imovel, comprador = dominio
        contrato = _criar_contrato(
            imob, imovel, comprador, numero='CTR-CESSAO-CUSTOM',
            percentual_cessao=Decimal('5.0000'),
        )
        r = contrato.calcular_cessao(DATA_RESCISAO_4M)
        assert r['percentual_cessao'] == Decimal('5.0000')
        saldo = _saldo_esperado(contrato)
        esperado = (saldo * Decimal('5.0000') / Decimal('100')).quantize(Decimal('0.01'))
        assert r['taxa_cessao'] == esperado

    def test_sem_data_usa_hoje(self, contrato_com_parcelas):
        r = contrato_com_parcelas.calcular_cessao()
        assert r['data_cessao'] == date.today()


# ---------------------------------------------------------------------------
# TestViewRescisao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestViewRescisao:
    """Testes da view calcular_rescisao_view."""

    def test_get_requer_autenticacao(self, client, contrato_com_parcelas):
        url = reverse('contratos:calcular_rescisao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = client.get(url)
        assert resp.status_code in (302, 403)

    def test_get_retorna_200_logado(self, usuario_cli, contrato_com_parcelas):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_rescisao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = cli.get(url)
        assert resp.status_code == 200

    def test_get_contrato_inexistente_retorna_404(self, usuario_cli):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_rescisao', kwargs={'pk': 999999})
        resp = cli.get(url)
        assert resp.status_code == 404

    def test_post_com_data_valida_processa_calculo(self, usuario_cli, contrato_com_parcelas):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_rescisao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = cli.post(url, data={'data_rescisao': '2025-05-01'})
        assert resp.status_code == 200

    def test_post_data_invalida_nao_causa_erro_500(self, usuario_cli, contrato_com_parcelas):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_rescisao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = cli.post(url, data={'data_rescisao': 'data-invalida'})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestViewCessao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestViewCessao:
    """Testes da view calcular_cessao_view."""

    def test_get_requer_autenticacao(self, client, contrato_com_parcelas):
        url = reverse('contratos:calcular_cessao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = client.get(url)
        assert resp.status_code in (302, 403)

    def test_get_retorna_200_logado(self, usuario_cli, contrato_com_parcelas):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_cessao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = cli.get(url)
        assert resp.status_code == 200

    def test_get_contrato_inexistente_retorna_404(self, usuario_cli):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_cessao', kwargs={'pk': 999999})
        resp = cli.get(url)
        assert resp.status_code == 404

    def test_post_com_data_valida_processa_calculo(self, usuario_cli, contrato_com_parcelas):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_cessao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = cli.post(url, data={'data_cessao': '2025-05-01'})
        assert resp.status_code == 200

    def test_post_data_invalida_nao_causa_erro_500(self, usuario_cli, contrato_com_parcelas):
        _, cli = usuario_cli
        url = reverse('contratos:calcular_cessao', kwargs={'pk': contrato_com_parcelas.pk})
        resp = cli.post(url, data={'data_cessao': 'invalido'})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestFluxoCompletoRescisaoCessao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFluxoCompletoRescisaoCessao:
    """
    E2E: Ciclo completo de um contrato que vai à rescisão e à cessão.

    Passos:
      1. Cria contrato de 24 parcelas lineares (entrada = R$ 20.000)
      2. Paga 6 parcelas consecutivas
      3. Calcula rescisão 6 meses após início — verifica todos os campos
      4. Calcula cessão — verifica taxa sobre saldo
      5. Confirma que calcular_saldo_devedor() == soma das parcelas não pagas
      6. Status permanece ATIVO (cálculos são simulações, não alteram status)
    """

    def test_fluxo_completo_rescisao_cessao(self, db, dominio):
        from contratos.models import StatusContrato

        imob, imovel, comprador = dominio
        contrato = _criar_contrato(imob, imovel, comprador, numero='CTR-E2E-RESCISAO')

        # Passo 2: pagar 6 parcelas
        _pagar_parcelas(contrato, 6)

        data_rescisao = date(2025, 7, 1)  # 6 meses após DATA_CONTRATO (2025-01-01)

        # Passo 3: calcular rescisão
        r = contrato.calcular_rescisao(data_rescisao)

        # Saldo = 18 parcelas não pagas × PMT_LINEAR
        saldo_esp = _saldo_esperado(contrato)
        assert r['saldo_devedor'] == saldo_esp

        # meses_ocupados = 6
        assert r['meses_ocupados'] == 6

        # Valor pago = entrada + 6 × PMT_LINEAR
        tot_pago_esp = (VALOR_ENTRADA + PMT_LINEAR * 6).quantize(Decimal('0.01'))
        assert r['valor_pago_total'] == tot_pago_esp

        # Fruição = saldo × 0.5% × 6
        fruicao_esp = (saldo_esp * Decimal('0.005') * 6).quantize(Decimal('0.01'))
        assert r['fruicao'] == fruicao_esp

        # Multa penal = saldo × 10%
        penal_esp = (saldo_esp * Decimal('0.10')).quantize(Decimal('0.01'))
        assert r['multa_penal'] == penal_esp

        # Desp adm = saldo × 12%
        adm_esp = (saldo_esp * Decimal('0.12')).quantize(Decimal('0.01'))
        assert r['desp_adm'] == adm_esp

        retencoes_esp = fruicao_esp + penal_esp + adm_esp
        devolucao_esp = max(
            Decimal('0.00'),
            (tot_pago_esp - retencoes_esp).quantize(Decimal('0.01')),
        )
        assert r['devolucao'] == devolucao_esp

        # Passo 4: cessão
        c = contrato.calcular_cessao(data_rescisao)
        taxa_esp = (saldo_esp * Decimal('0.03')).quantize(Decimal('0.01'))
        assert c['taxa_cessao'] == taxa_esp
        assert c['saldo_devedor'] == saldo_esp

        # Passo 5: calcular_saldo_devedor() == saldo_esp
        assert contrato.calcular_saldo_devedor() == saldo_esp

        # Passo 6: status permanece ATIVO
        contrato.refresh_from_db()
        assert contrato.status == StatusContrato.ATIVO
