"""
Cenários de geração de dados de teste das HUs BAPI (CENARIOS_TESTE_BOLETO_API.md
§1): o gerar_dados_teste monta BOLETO FAKE completo para contas Sicoob/C6 e
simula o ciclo de vida pelo pipeline REAL do webhook — sem chamar a API do
banco nem o gateway (qualquer tentativa de rede falha o teste).
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from core.models import MetodoCobranca
from financeiro.models import (
    EventoCobrancaApi, Parcela, StatusBoleto, StatusCobranca as S,
)
from financeiro.services.boleto_fake import crc16_ccitt


def _bloquear_rede():
    """Qualquer requisição HTTP durante os cenários fake é um erro de teste."""
    return patch(
        'requests.sessions.Session.request',
        side_effect=AssertionError('Cenário fake não pode chamar a rede'),
    )


def _criar_contrato(imob, conta, numero, parcelas=6):
    from contratos.models import (
        Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
    )
    from tests.fixtures.factories import CompradorFactory, ImovelFactory

    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=CompradorFactory(),
        numero_contrato=numero, data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000'), valor_entrada=Decimal('10000'),
        numero_parcelas=parcelas, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
    )
    return contrato


@pytest.fixture
def massa_bapi(db):
    """2 contas API (Sicoob + C6) e 3 contratos com parcelas vencidas."""
    from tests.fixtures.factories import ContaBancariaApiFactory, ImobiliariaFactory

    imob = ImobiliariaFactory(metodos_cobranca=['boleto'])
    conta_sicoob = ContaBancariaApiFactory(
        imobiliaria=imob, banco='756', provider='sicoob', tenant_id='t-756',
        carteira='01', ativo=True)
    conta_c6 = ContaBancariaApiFactory(
        imobiliaria=imob, banco='336', provider='c6', tenant_id='t-336',
        carteira='10', ativo=True)

    contratos = [
        (_criar_contrato(imob, conta_sicoob, 'CTR-BAPI-1', parcelas=12), conta_sicoob),
        (_criar_contrato(imob, conta_c6, 'CTR-BAPI-2', parcelas=6), conta_c6),
        (_criar_contrato(imob, conta_c6, 'CTR-BAPI-3', parcelas=6), conta_c6),
    ]
    pares = []
    for contrato, conta in contratos:
        parcelas = list(
            contrato.parcelas.filter(pago=False).order_by('numero_parcela')
        )
        # A última parcela de cada contrato fica sem boleto — insumo do
        # cenário AGUARDANDO_CIP (emissão 409 nunca completou).
        for parcela in parcelas[:-1]:
            pares.append((parcela, conta))
    return imob, contratos, pares


def _comando():
    from core.management.commands.gerar_dados_teste import Command
    return Command()


@pytest.mark.django_db
class TestBoletoFakeNaGeracao:
    """CT-07..CT-11 — emissão fake preenche o rastreio completo (BAPI-08..12)."""

    def test_boleto_fake_completo_sem_rede(self, massa_bapi):
        _, _, pares = massa_bapi
        with _bloquear_rede():
            gerados = _comando()._gerar_boletos_simulados(pares)
        assert gerados == len(pares)

        emitidas = Parcela.objects.exclude(provider='')
        assert emitidas.count() == len(pares)
        for p in emitidas:
            assert p.status_boleto == StatusBoleto.REGISTRADO
            assert p.status_cobranca == S.REGISTRADA
            assert p.cobranca_id.startswith('sim-')
            assert len(p.codigo_barras) == 44 and p.codigo_barras.isdigit()
            digitos = p.linha_digitavel.replace('.', '').replace(' ', '')
            assert len(digitos) == 47
            assert p.valor_boleto is not None
            assert bytes(p.boleto_pdf_db).startswith(b'%PDF')
            # CT-11: mesmo formato de txid da emissão real
            assert p.pix_txid == f'GC{p.contrato_id:07d}P{p.numero_parcela:04d}'

    def test_cobranca_id_unico_entre_contas(self, massa_bapi):
        _, _, pares = massa_bapi
        with _bloquear_rede():
            _comando()._gerar_boletos_simulados(pares)
        ids = list(Parcela.objects.exclude(cobranca_id='')
                   .values_list('cobranca_id', flat=True))
        assert len(ids) == len(set(ids))

    def test_bolepix_apenas_c6_com_ext_ref_e_pix(self, massa_bapi):
        imob, _, pares = massa_bapi
        with _bloquear_rede():
            _comando()._gerar_boletos_simulados(pares)

        bolepix = Parcela.objects.filter(metodo_cobranca=MetodoCobranca.BOLETO_PIX)
        assert bolepix.exists()
        assert set(bolepix.values_list('provider', flat=True)) == {'c6'}
        for p in bolepix:
            assert p.ext_ref.startswith('bp-336-')
            # CT-10: Pix copia-e-cola EMV com CRC válido para o portal
            assert p.pix_copia_cola[-4:] == crc16_ccitt(p.pix_copia_cola[:-4])
            # CT-07: coerência BAPI-06/07 — método habilitado e gravado
            assert p.contrato.metodo_cobranca == MetodoCobranca.BOLETO_PIX
        imob.refresh_from_db()
        assert MetodoCobranca.BOLETO_PIX in imob.metodos_cobranca

    def test_sicoob_sempre_boleto_sem_pix(self, massa_bapi):
        _, _, pares = massa_bapi
        with _bloquear_rede():
            _comando()._gerar_boletos_simulados(pares)
        sicoob = Parcela.objects.filter(provider='sicoob')
        assert set(sicoob.values_list('metodo_cobranca', flat=True)) == {'boleto'}
        assert not sicoob.exclude(pix_copia_cola='').exists()


@pytest.mark.django_db
class TestCicloCobrancaApi:
    """CT-13..CT-22 — ciclo de vida via pipeline real do webhook (BAPI-13..25)."""

    @pytest.fixture
    def ciclo(self, massa_bapi):
        _, _, pares = massa_bapi
        cmd = _comando()
        with _bloquear_rede():
            cmd._gerar_boletos_simulados(pares)
            stats = cmd.simular_ciclo_cobranca_api()
        return stats

    def test_distribui_todos_os_estados(self, ciclo):
        estados = set(
            Parcela.objects.exclude(status_cobranca='')
            .values_list('status_cobranca', flat=True)
        )
        assert {S.REGISTRADA, S.LIQUIDADA, S.BAIXADA, S.EXPIRADA,
                S.ESTORNADA, S.AGUARDANDO_CIP} <= estados

    def test_liquidadas_estao_pagas_com_evento_baixado(self, ciclo):
        liquidadas = Parcela.objects.filter(status_cobranca=S.LIQUIDADA)
        assert liquidadas.exists()
        for p in liquidadas:
            assert p.pago is True
            assert p.eventos_cobranca_api.filter(status='baixado').exists()

    def test_estornada_liquidou_antes_e_e_terminal(self, ciclo):
        p = Parcela.objects.filter(status_cobranca=S.ESTORNADA).first()
        assert p is not None
        assert p.eventos_cobranca_api.filter(status='baixado').exists()
        assert p.eventos_cobranca_api.filter(event='pix.devolvido').exists()
        # terminal (BAPI-23): nenhuma transição sai de ESTORNADA
        assert p.pode_transicionar_cobranca(S.REGISTRADA) is False

    def test_eventos_de_borda_registrados(self, ciclo):
        # BAPI-19: reenvio → duplicado | BAPI-24: fora de ordem → ignorado
        # BAPI-22: cobranca_id desconhecido → sem_parcela
        assert ciclo['eventos duplicados'] >= 1
        assert ciclo['eventos fora de ordem'] >= 1
        assert ciclo['eventos sem parcela'] >= 1
        assert EventoCobrancaApi.objects.filter(status='duplicado').exists()
        assert EventoCobrancaApi.objects.filter(status='ignorado').exists()
        assert EventoCobrancaApi.objects.filter(
            status='sem_parcela', cobranca_id='sim-000-inexistente').exists()

    def test_fora_de_ordem_preserva_estado(self, ciclo):
        evt = EventoCobrancaApi.objects.filter(status='ignorado').first()
        assert evt.parcela.status_cobranca == S.BAIXADA
        assert evt.parcela.pago is False

    def test_aguardando_cip_sem_cobranca_id_com_conta(self, ciclo):
        # BAPI-25: 409 na emissão → sem cobranca_id; conta atribuída para a
        # fila de reprocessamento (BAPI-33) reencontrar a parcela.
        cip = Parcela.objects.filter(status_cobranca=S.AGUARDANDO_CIP)
        assert cip.count() >= 1
        for p in cip:
            assert p.cobranca_id == ''
            assert p.conta_bancaria_id is not None
            assert p.pago is False

    def test_reexecucao_processa_restantes_sem_duplicar_baixas(self, massa_bapi):
        # Idempotência da geração: 2ª rodada não re-baixa parcelas pagas
        _, _, pares = massa_bapi
        cmd = _comando()
        with _bloquear_rede():
            cmd._gerar_boletos_simulados(pares)
            cmd.simular_ciclo_cobranca_api()
            pagas_antes = Parcela.objects.filter(pago=True).count()
            baixados_antes = EventoCobrancaApi.objects.filter(status='baixado').count()
            cmd2 = _comando()
            stats2 = cmd2.simular_ciclo_cobranca_api()
        # As que ficaram REGISTRADA na 1ª rodada entram no ciclo da 2ª
        pagas_depois = Parcela.objects.filter(pago=True).count()
        baixados_depois = EventoCobrancaApi.objects.filter(status='baixado').count()
        assert pagas_depois >= pagas_antes
        assert baixados_depois - baixados_antes == pagas_depois - pagas_antes
        assert stats2['eventos sem parcela'] >= 1
