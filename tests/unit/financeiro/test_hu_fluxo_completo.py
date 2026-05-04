"""
HU — Fluxo Completo do Ciclo de Vida de um Contrato Imobiliário
================================================================

Cobre em sequência os 9 marcos de negócio:

  Passo 1  Criação do contrato (IPCA + Tabela Price + TabelaJuros 0,8%/mês · 36 parcelas)
  Passo 2  Validação das parcelas auto-geradas (count, PMT, amortização, saldo devedor)
  Passo 3  Pagamento manual da 1ª parcela via pagar_parcela_ajax
  Passo 4  Aplicação do reajuste ciclo 2 — 5 % (modo legado / informado)
  Passo 5  Geração de carnê para os próximos 20 meses (gerar_carne — parcelas 2-21)
  Passo 6  Validação do bloqueio do ciclo 3 (parcelas 25+ bloqueadas em lote)
  Passo 7  Geração do carnê PDF 6 meses (download_carne_pdf + mock BRCobrança)
  Passo 8  Quitação manual de 3 parcelas (pagar_parcela_ajax × 3)
  Passo 9  Quitação via extrato OFX (upload_ofx + mock BRCobrança)

Todos os passos correm dentro de uma única transação de banco de dados — o estado
persiste entre os passos e qualquer falha indica exatamente em qual marco o fluxo
quebrou.

Dependências externas (BRCobrança):
  Todos os pontos de integração com a API BRCobrança são substituídos por mocks,
  permitindo execução offline e determinística.
"""
import json
import pytest
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch, MagicMock

from django.test import Client
from django.urls import reverse

# ── Constantes do cenário ──────────────────────────────────────────────────────
PV = Decimal('120000.00')       # Valor financiado (130k total − 10k entrada)
TAXA_MENSAL = Decimal('0.8000') # Juros mensais da TabelaJuros
N = 36                          # Número de parcelas
PRAZO_REAJUSTE = 12             # Intervalo de reajuste em meses
PERCENTUAL_REAJUSTE = Decimal('5.0')  # Reajuste ciclo 2 informado


# ==============================================================================
# Auxiliar — mock de geração de boleto
# ==============================================================================

def _mock_gerar_boleto(self, conta_bancaria=None, force=False, enviar_email=True):
    """
    Substitui Parcela.gerar_boleto() evitando chamada ao BRCobrança.

    Atribui um nosso_numero sequencial baseado no número da parcela e persiste
    os campos no banco para que os passos seguintes (carnê PDF, OFX) encontrem
    boletos "gerados".
    """
    nosso_numero = f'{self.numero_parcela:010d}'
    linha = f'75691.{nosso_numero[:5]} {nosso_numero[5:]} 00000.000001 1 10000000000000'
    self.nosso_numero = nosso_numero
    self.linha_digitavel = linha
    self.save(update_fields=['nosso_numero', 'linha_digitavel'])
    return {
        'sucesso': True,
        'nosso_numero': nosso_numero,
        'linha_digitavel': linha,
        'codigo_barras': '75691' + nosso_numero + '000000000000001',
        'pdf_content': b'%PDF-1.4 MOCK_BOLETO',
    }


# ==============================================================================
# Auxiliar — resposta mock do BRCobrança para parse OFX
# ==============================================================================

def _mock_brcobranca_ofx(nosso_numero: str, valor: Decimal, data_pgto: date):
    """
    Constrói o mock de resposta do endpoint /api/ofx/parse do BRCobrança
    com uma única transação de crédito identificada pelo nosso_número informado.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'transacoes': [
            {
                'fitid': f'HU-OFX-{nosso_numero}',
                'tipo': 'CREDIT',
                'data': str(data_pgto),
                'valor': float(valor),
                'memo': f'COBRANCA NOSSO NUMERO {nosso_numero} PAGO VIA OFX',
                'nosso_numero_extraido': nosso_numero,
            }
        ]
    }
    return mock_resp


# ==============================================================================
# HU — Fluxo Completo
# ==============================================================================

@pytest.mark.django_db
class TestHUFluxoCompleto:
    """
    História de Usuário — Ciclo de vida completo de um contrato imobiliário.

    Um único método de teste para garantir que os passos sejam executados em
    sequência e que o estado do banco persista entre eles dentro da mesma
    transação de teste.
    """

    def test_fluxo_completo_ciclo_vida_contrato(self, db):
        """
        Executa os 9 marcos em ordem. Uma falha em qualquer passo interrompe
        o fluxo e aponta o exato ponto de regressão no nome do assert.
        """
        # ── Imports locais (evitam problemas de carregamento antecipado) ─────
        from django.contrib.auth.models import User
        from contratos.models import (
            Contrato, TabelaJurosContrato, TipoCorrecao, TipoAmortizacao, StatusContrato,
        )
        from financeiro.models import Parcela, TipoParcela, Reajuste, HistoricoPagamento
        from financeiro.services.boleto_service import BoletoService
        from tests.fixtures.factories import (
            ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
        )

        # ── Usuário staff e cliente HTTP autenticado ─────────────────────────
        usuario = User.objects.create_user(
            username='hu_fluxo_staff', password='testpass', is_staff=True,
        )
        cli = Client()
        cli.force_login(usuario)

        # ── Infraestrutura: imobiliária, conta bancária, imóvel, comprador ───
        imob = ImobiliariaFactory(nome='Imob HU Fluxo Completo')
        conta = ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
        imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
        comprador = CompradorFactory(nome='Comprador HU Fluxo')

        # Datas: contrato criado há 14 meses → ciclo 2 vencido (há 2 meses)
        hoje = date.today()
        data_contrato = hoje - relativedelta(months=14)
        data_primeiro_vencimento = hoje - relativedelta(months=13)

        # ================================================================
        # PASSO 1 — Criação do contrato
        # ================================================================

        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel,
            comprador=comprador,
            numero_contrato='HU-FLUXO-001',
            data_contrato=data_contrato,
            data_primeiro_vencimento=data_primeiro_vencimento,
            valor_total=Decimal('130000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=N,
            dia_vencimento=5,
            tipo_correcao=TipoCorrecao.IPCA,
            tipo_amortizacao=TipoAmortizacao.PRICE,
            prazo_reajuste_meses=PRAZO_REAJUSTE,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            status=StatusContrato.ATIVO,
        )
        # Cria a tabela de juros e recalcula o plano de amortização Price
        TabelaJurosContrato.objects.create(
            contrato=contrato,
            ciclo_inicio=1,
            ciclo_fim=None,      # aplica a todos os ciclos
            juros_mensal=TAXA_MENSAL,
        )
        contrato.recalcular_amortizacao()

        assert contrato.pk is not None, "P1: contrato não foi salvo no banco"
        assert contrato.valor_financiado == PV, (
            f"P1: valor financiado esperado {PV}, obtido {contrato.valor_financiado}"
        )

        # ================================================================
        # PASSO 2 — Validação das parcelas auto-geradas
        # ================================================================

        parcelas = list(
            Parcela.objects.filter(
                contrato=contrato,
                tipo_parcela=TipoParcela.NORMAL,
            ).order_by('numero_parcela')
        )

        assert len(parcelas) == N, (
            f"P2: esperadas {N} parcelas, geradas {len(parcelas)}"
        )

        # PMT Price: PV × i / (1 − (1+i)^-n)
        i = TAXA_MENSAL / Decimal('100')
        pmt_esperado = (PV * i / (1 - (1 + i) ** (-N))).quantize(Decimal('0.01'))

        for p in parcelas[:-1]:  # última parcela pode ter ajuste de centavos
            assert p.valor_atual == pmt_esperado, (
                f"P2: parcela {p.numero_parcela} — PMT esperado {pmt_esperado}, "
                f"obtido {p.valor_atual}"
            )

        # Amortização e juros embutidos devem estar preenchidos em todos
        assert all(p.amortizacao is not None and p.amortizacao > 0 for p in parcelas[:-1]), (
            "P2: amortizacao não preenchida em alguma parcela"
        )
        assert all(p.juros_embutido is not None and p.juros_embutido >= 0 for p in parcelas[:-1]), (
            "P2: juros_embutido não preenchido em alguma parcela"
        )

        # Saldo devedor Price = Σ valor_atual das parcelas não pagas
        from django.db.models import Sum
        saldo = contrato.calcular_saldo_devedor()
        soma_pmt = contrato.parcelas.filter(
            tipo_parcela=TipoParcela.NORMAL, pago=False,
        ).aggregate(s=Sum('valor_atual'))['s']
        assert saldo == soma_pmt, (
            f"P2: saldo devedor {saldo} != Σ PMTs {soma_pmt}"
        )
        assert saldo > PV, "P2: saldo Price deve incluir juros futuros e ser > PV"

        # ================================================================
        # PASSO 3 — Pagamento manual da 1ª parcela
        # ================================================================

        parcela_1 = parcelas[0]
        url_pagar = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': parcela_1.pk})

        resp = cli.post(url_pagar, {
            'data_pagamento': str(hoje),
            'valor_pago': str(parcela_1.valor_atual),
            'forma_pagamento': 'TRANSFERENCIA',
            'observacoes': 'Pagamento HU — Passo 3',
        })

        assert resp.status_code == 200, (
            f"P3: pagar_parcela_ajax retornou {resp.status_code}"
        )
        dados_p3 = resp.json()
        assert dados_p3.get('sucesso') is True, f"P3: {dados_p3}"

        parcela_1.refresh_from_db()
        assert parcela_1.pago is True, "P3: parcela 1 deveria estar marcada como paga"

        # Histórico de pagamento deve existir com origem MANUAL
        assert HistoricoPagamento.objects.filter(
            parcela=parcela_1,
            origem_pagamento='MANUAL',
        ).exists(), "P3: HistoricoPagamento não criado"

        # ================================================================
        # PASSO 4 — Aplicação do reajuste ciclo 2 (5 % modo legado)
        # ================================================================

        # Confirma que o ciclo 2 está pendente antes de aplicar
        ciclo_pendente = Reajuste.calcular_ciclo_pendente(contrato)
        assert ciclo_pendente == 2, (
            f"P4: ciclo pendente esperado 2, obtido {ciclo_pendente}"
        )

        # Valor das parcelas antes do reajuste (ciclo 1 = linear)
        pmt_antes = parcelas[12].valor_atual  # parcela 13 (início do ciclo 2)

        # Aplica via endpoint legado: percentual informado, sem IndiceReajuste no banco
        url_reajuste = reverse(
            'financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato.pk}
        )
        resp = cli.post(
            url_reajuste,
            data=json.dumps({
                'percentual': str(PERCENTUAL_REAJUSTE),
                'parcela_inicial': PRAZO_REAJUSTE + 1,   # 13
                'parcela_final': N,                        # 36
                'observacoes': 'Reajuste ciclo 2 — HU Passo 4',
            }),
            content_type='application/json',
        )

        assert resp.status_code == 200, (
            f"P4: aplicar_reajuste_api retornou {resp.status_code} — {resp.content[:200]}"
        )
        dados_p4 = resp.json()
        assert dados_p4.get('sucesso') is True, f"P4: {dados_p4}"
        assert dados_p4.get('ciclo') == 2, "P4: ciclo aplicado deve ser 2"
        assert dados_p4.get('parcelas_afetadas', 0) > 0, "P4: nenhuma parcela foi reajustada"

        # Verifica que as parcelas do ciclo 2 têm o novo valor.
        # Modo Tabela Price: PMT_novo = PMT_atual × (1 + IPCA) × (1 + taxa_mensal)^prazo
        _taxa = TAXA_MENSAL / Decimal('100')
        _fator_juros = (Decimal('1') + _taxa) ** PRAZO_REAJUSTE
        _fator_ipca = Decimal('1') + PERCENTUAL_REAJUSTE / Decimal('100')
        pmt_reajustado = (pmt_antes * _fator_ipca * _fator_juros).quantize(Decimal('0.01'))
        parcela_13 = contrato.parcelas.get(numero_parcela=13)
        assert parcela_13.valor_atual == pmt_reajustado, (
            f"P4: parcela 13 esperada {pmt_reajustado}, obtida {parcela_13.valor_atual}"
        )

        # Contrato deve ter ciclo_reajuste_atual atualizado para 2
        contrato.refresh_from_db()
        assert contrato.ciclo_reajuste_atual == 2, (
            f"P4: ciclo_reajuste_atual esperado 2, obtido {contrato.ciclo_reajuste_atual}"
        )

        # Ciclo 3 é aniversário futuro (daqui ~10 meses) → não deve ser pendente imediato
        ciclo_pos = Reajuste.calcular_ciclo_pendente(contrato, antecipacao_meses=0)
        assert ciclo_pos is None or ciclo_pos == 3, (
            f"P4: após reajuste ciclo 2, ciclo pendente imediato deveria ser None ou 3, "
            f"obtido {ciclo_pos}"
        )

        # ================================================================
        # PASSO 5 — Gerar carnê para os próximos 20 meses (parcelas 2-21)
        # ================================================================

        # Seleciona as 20 primeiras parcelas não pagas (parcela 1 foi paga no P3)
        parcelas_carne_20 = list(
            Parcela.objects.filter(
                contrato=contrato,
                tipo_parcela=TipoParcela.NORMAL,
                pago=False,
            ).order_by('numero_parcela')[:20]
        )
        assert len(parcelas_carne_20) == 20, (
            f"P5: esperadas 20 parcelas, encontradas {len(parcelas_carne_20)}"
        )
        # Confirma que todas estão dentro do ciclo 1 e 2 (≤ parcela 24)
        assert all(p.numero_parcela <= 24 for p in parcelas_carne_20), (
            "P5: as 20 primeiras parcelas não pagas devem pertencer aos ciclos 1 e 2"
        )

        ids_20 = [p.pk for p in parcelas_carne_20]
        url_carne = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato.pk})

        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            resp = cli.post(
                url_carne,
                data=json.dumps({'parcelas': ids_20}),
                content_type='application/json',
            )

        assert resp.status_code == 200, f"P5: gerar_carne retornou {resp.status_code}"
        dados_p5 = resp.json()
        assert dados_p5.get('sucesso') is True, f"P5: {dados_p5}"
        assert dados_p5.get('gerados') == 20, (
            f"P5: esperados 20 boletos gerados, obtidos {dados_p5.get('gerados')}"
        )
        assert dados_p5.get('bloqueados') == 0, (
            f"P5: parcelas 2-21 não deveriam ter bloqueios, "
            f"obtidos {dados_p5.get('bloqueados')} bloqueados"
        )

        # Confirma que nosso_numero foi gravado nas parcelas pelo mock
        parcela_5 = contrato.parcelas.get(numero_parcela=5)
        parcela_5.refresh_from_db()
        assert parcela_5.nosso_numero == '0000000005', (
            f"P5: nosso_numero da parcela 5 esperado '0000000005', "
            f"obtido '{parcela_5.nosso_numero}'"
        )

        # ================================================================
        # PASSO 6 — Validar bloqueio do ciclo 3 (parcelas 25-36)
        # ================================================================

        # Ciclo 3 ainda não recebeu reajuste → deve bloquear geração em lote
        parcelas_ciclo3 = list(
            Parcela.objects.filter(
                contrato=contrato,
                tipo_parcela=TipoParcela.NORMAL,
                pago=False,
                numero_parcela__gte=PRAZO_REAJUSTE * 2 + 1,  # >= 25
            ).order_by('numero_parcela')
        )
        assert len(parcelas_ciclo3) > 0, "P6: deveria haver parcelas no ciclo 3"

        ids_ciclo3 = [p.pk for p in parcelas_ciclo3]

        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            resp = cli.post(
                url_carne,
                data=json.dumps({'parcelas': ids_ciclo3}),
                content_type='application/json',
            )

        assert resp.status_code == 200, f"P6: gerar_carne retornou {resp.status_code}"
        dados_p6 = resp.json()

        assert dados_p6.get('bloqueados') == len(parcelas_ciclo3), (
            f"P6: todas as {len(parcelas_ciclo3)} parcelas do ciclo 3 deveriam estar "
            f"bloqueadas, obtidos bloqueados={dados_p6.get('bloqueados')}, "
            f"gerados={dados_p6.get('gerados')}"
        )
        assert dados_p6.get('gerados') == 0, (
            "P6: nenhum boleto do ciclo 3 deve ser gerado sem reajuste aplicado"
        )

        # Valida via método direto do modelo: ciclo 3 ainda não venceu (~10 meses
        # à frente), portanto pode_gerar_boleto() retorna True. O bloqueio em lote
        # é feito pelo max_parcela_lote na view gerar_carne, não por este método.
        for p in parcelas_ciclo3[:3]:
            pode, motivo = contrato.pode_gerar_boleto(p.numero_parcela)
            assert pode is True, (
                f"P6: ciclo 3 ainda futuro — parcela {p.numero_parcela} deve ser "
                f"liberada pelo modelo (bloqueio de lote ocorre na view)"
            )

        # ================================================================
        # PASSO 7 — Geração do carnê PDF 6 meses
        # ================================================================

        # Usa as 6 primeiras parcelas que já têm boleto gerado (nosso_numero != '')
        parcelas_pdf_6 = list(
            Parcela.objects.filter(
                contrato=contrato,
                tipo_parcela=TipoParcela.NORMAL,
                pago=False,
            ).exclude(nosso_numero='').order_by('numero_parcela')[:6]
        )
        assert len(parcelas_pdf_6) == 6, (
            f"P7: esperadas 6 parcelas com boleto, encontradas {len(parcelas_pdf_6)}"
        )

        ids_pdf_6 = [p.pk for p in parcelas_pdf_6]
        url_carne_pdf = reverse(
            'financeiro:download_carne_pdf', kwargs={'contrato_id': contrato.pk}
        )
        pdf_mock = b'%PDF-1.4 CARNE_6_MESES_MOCK'

        with patch.object(
            BoletoService, 'gerar_carne',
            return_value={'sucesso': True, 'pdf_content': pdf_mock, 'total': 6},
        ):
            resp = cli.post(
                url_carne_pdf,
                data=json.dumps({'parcela_ids': ids_pdf_6}),
                content_type='application/json',
            )

        assert resp.status_code == 200, (
            f"P7: download_carne_pdf retornou {resp.status_code} — {resp.content[:200]}"
        )
        assert resp['Content-Type'] == 'application/pdf', (
            f"P7: Content-Type esperado 'application/pdf', obtido '{resp['Content-Type']}'"
        )
        assert b'PDF' in resp.content, "P7: conteúdo do response não contém bytes PDF"

        # ================================================================
        # PASSO 8 — Quitação manual de 3 parcelas
        # ================================================================

        # Pega as 3 primeiras parcelas ainda não pagas (parcela 2, 3, 4 — todas com boleto)
        parcelas_quitar = list(
            Parcela.objects.filter(
                contrato=contrato,
                tipo_parcela=TipoParcela.NORMAL,
                pago=False,
            ).order_by('numero_parcela')[:3]
        )
        assert len(parcelas_quitar) == 3, (
            f"P8: esperadas 3 parcelas para quitar, encontradas {len(parcelas_quitar)}"
        )

        for p in parcelas_quitar:
            url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': p.pk})
            resp = cli.post(url, {
                'data_pagamento': str(hoje),
                'valor_pago': str(p.valor_atual),
                'forma_pagamento': 'DINHEIRO',
                'observacoes': f'Quitação manual — parcela {p.numero_parcela} — P8',
            })
            assert resp.status_code == 200, (
                f"P8: parcela {p.numero_parcela} — pagar_parcela_ajax retornou {resp.status_code}"
            )
            assert resp.json().get('sucesso') is True, (
                f"P8: parcela {p.numero_parcela} — {resp.json()}"
            )
            p.refresh_from_db()
            assert p.pago is True, f"P8: parcela {p.numero_parcela} deveria estar paga"

        # Confirma criação dos 3 registros de histórico com origem MANUAL
        historico_manual = HistoricoPagamento.objects.filter(
            parcela__in=parcelas_quitar,
            origem_pagamento='MANUAL',
        )
        assert historico_manual.count() == 3, (
            f"P8: esperados 3 HistoricoPagamento MANUAL, encontrados {historico_manual.count()}"
        )

        # ================================================================
        # PASSO 9 — Quitação via extrato OFX
        # ================================================================

        # Seleciona a próxima parcela não paga que já tem nosso_numero (gerado no P5)
        parcela_ofx = Parcela.objects.filter(
            contrato=contrato,
            tipo_parcela=TipoParcela.NORMAL,
            pago=False,
        ).exclude(nosso_numero='').order_by('numero_parcela').first()

        assert parcela_ofx is not None, (
            "P9: necessária uma parcela não paga com nosso_numero para testar OFX"
        )

        nosso_numero_ofx = parcela_ofx.nosso_numero
        valor_ofx = parcela_ofx.valor_atual

        # Conteúdo OFX mínimo com uma transação de crédito
        ofx_bytes = (
            b"OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\n"
            b"ENCODING:USASCII\nCHARSET:1252\nCOMPRESSION:NONE\n"
            b"OLDFILEUID:NONE\nNEWFILEUID:NONE\n\n"
            b"<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><CURDEF>BRL</CURDEF>\n"
            b"<BANKTRANLIST>\n"
            b"<STMTTRN><TRNTYPE>CREDIT</TRNTYPE>"
            b"<DTPOSTED>20260501120000</DTPOSTED>"
            b"<TRNAMT>" + str(valor_ofx).encode() + b"</TRNAMT>"
            b"<FITID>HU-OFX-" + nosso_numero_ofx.encode() + b"</FITID>"
            b"<MEMO>COBRANCA NOSSO NUMERO " + nosso_numero_ofx.encode() + b" PAGO</MEMO>"
            b"</STMTTRN>\n"
            b"</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"
        )

        # Mock do BRCobrança para parsear o OFX e retornar nosso_numero_extraido
        mock_brcobranca = _mock_brcobranca_ofx(nosso_numero_ofx, valor_ofx, hoje)

        from django.core.files.uploadedfile import SimpleUploadedFile
        arquivo_ofx = SimpleUploadedFile(
            'extrato_hu.ofx', ofx_bytes, content_type='application/x-ofx',
        )
        url_ofx = reverse('financeiro:upload_ofx')

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_brcobranca):
            resp = cli.post(url_ofx, {
                'arquivo_ofx': arquivo_ofx,
                'dry_run': '0',
            })

        assert resp.status_code == 200, (
            f"P9: upload_ofx retornou {resp.status_code} — {resp.content[:300]}"
        )
        dados_p9 = resp.json()
        assert dados_p9.get('sucesso') is True, f"P9: {dados_p9}"
        assert dados_p9.get('reconciliadas', 0) >= 1, (
            f"P9: esperada ao menos 1 reconciliação, obtidas {dados_p9.get('reconciliadas')}"
        )
        assert parcela_ofx.pk in dados_p9.get('parcelas_quitadas', []), (
            f"P9: parcela {parcela_ofx.pk} (nº {parcela_ofx.numero_parcela}) "
            f"deveria constar em parcelas_quitadas"
        )

        # Confirma que a parcela foi marcada como paga no banco
        parcela_ofx.refresh_from_db()
        assert parcela_ofx.pago is True, (
            f"P9: parcela {parcela_ofx.numero_parcela} deveria estar marcada como paga após OFX"
        )

        # Confirma HistoricoPagamento com origem OFX
        assert HistoricoPagamento.objects.filter(
            parcela=parcela_ofx,
            origem_pagamento='OFX',
        ).exists(), (
            "P9: HistoricoPagamento com origem_pagamento='OFX' não foi criado"
        )

        # ── Resumo final (apenas informativo — não falha o teste) ───────────
        total_pagos = contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL, pago=True).count()
        total_pendentes = contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL, pago=False).count()

        assert total_pagos == 5, (     # P3(1) + P8(3) + P9(1) = 5
            f"Resumo: esperados 5 pagos, encontrados {total_pagos}"
        )
        assert total_pendentes == N - 5, (
            f"Resumo: esperados {N - 5} pendentes, encontrados {total_pendentes}"
        )


# ==============================================================================
# Testes unitários isolados — cada passo testado de forma independente
# ==============================================================================

@pytest.fixture
def dominio(db):
    """Retorna (imobiliaria, conta, imovel, comprador) prontos para uso."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    imob = ImobiliariaFactory()
    conta = ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory()
    return imob, conta, imovel, comprador


@pytest.fixture
def usuario_cli(db):
    """Retorna (usuario, client) autenticado como staff."""
    from django.contrib.auth.models import User
    u = User.objects.create_user(username='hu_unit_staff', password='pass', is_staff=True)
    c = Client()
    c.force_login(u)
    return u, c


@pytest.fixture
def contrato_36m(db, dominio):
    """
    Contrato IPCA + Price + TabelaJuros (0,8%/mês), 36 parcelas, criado há 14 meses.
    Garante que o ciclo 2 está vencido e pendente de reajuste.
    """
    from contratos.models import (
        Contrato, TabelaJurosContrato, TipoCorrecao, TipoAmortizacao, StatusContrato,
    )
    imob, conta, imovel, comprador = dominio
    hoje = date.today()
    c = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='HU-UNIT-001',
        data_contrato=hoje - relativedelta(months=14),
        data_primeiro_vencimento=hoje - relativedelta(months=13),
        valor_total=Decimal('130000.00'), valor_entrada=Decimal('10000.00'),
        numero_parcelas=N, dia_vencimento=5,
        tipo_correcao=TipoCorrecao.IPCA,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        prazo_reajuste_meses=PRAZO_REAJUSTE,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
        status=StatusContrato.ATIVO,
    )
    TabelaJurosContrato.objects.create(
        contrato=c, ciclo_inicio=1, ciclo_fim=None, juros_mensal=TAXA_MENSAL,
    )
    c.recalcular_amortizacao()
    return c


# ── Passo 1/2: parcelas geradas ───────────────────────────────────────────────

@pytest.mark.django_db
class TestCriacaoContrato:
    """Passo 1 e 2 — Criação e validação das parcelas."""

    def test_numero_parcelas(self, contrato_36m):
        """Devem ser geradas exatamente N parcelas NORMAL."""
        from financeiro.models import Parcela, TipoParcela
        assert contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).count() == N

    def test_pmt_price_correto(self, contrato_36m):
        """PMT de todas as parcelas (exceto última) deve seguir a fórmula Price."""
        from financeiro.models import Parcela, TipoParcela
        i = TAXA_MENSAL / Decimal('100')
        pmt = (PV * i / (1 - (1 + i) ** (-N))).quantize(Decimal('0.01'))
        parcelas = list(
            Parcela.objects.filter(
                contrato=contrato_36m, tipo_parcela=TipoParcela.NORMAL,
            ).order_by('numero_parcela')
        )
        for p in parcelas[:-1]:
            assert p.valor_atual == pmt, (
                f"Parcela {p.numero_parcela}: PMT esperado {pmt}, obtido {p.valor_atual}"
            )

    def test_amortizacao_e_juros_preenchidos(self, contrato_36m):
        """Todos os campos de amortização e juros devem estar preenchidos."""
        from financeiro.models import Parcela, TipoParcela
        for p in contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL):
            assert p.amortizacao is not None
            assert p.juros_embutido is not None

    def test_saldo_devedor_maior_que_pv(self, contrato_36m):
        """Saldo devedor Price inclui juros futuros, portanto deve ser > PV."""
        saldo = contrato_36m.calcular_saldo_devedor()
        assert saldo > contrato_36m.valor_financiado

    def test_ciclo_2_pendente_apos_14_meses(self, contrato_36m):
        """Com 14 meses de contrato, o ciclo 2 deve estar pendente de reajuste."""
        from financeiro.models import Reajuste
        ciclo = Reajuste.calcular_ciclo_pendente(contrato_36m)
        assert ciclo == 2


# ── Passo 3: pagamento manual ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestPagamentoManual:
    """Passo 3 — Pagamento manual via pagar_parcela_ajax."""

    def test_pagamento_registra_pago(self, contrato_36m, usuario_cli):
        """POST em pagar_parcela_ajax deve marcar parcela como paga."""
        from financeiro.models import Parcela, TipoParcela, HistoricoPagamento
        _, cli = usuario_cli
        p = contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).order_by('numero_parcela').first()
        url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': p.pk})
        resp = cli.post(url, {
            'data_pagamento': str(date.today()),
            'valor_pago': str(p.valor_atual),
            'forma_pagamento': 'TRANSFERENCIA',
        })
        assert resp.status_code == 200
        assert resp.json()['sucesso'] is True
        p.refresh_from_db()
        assert p.pago is True

    def test_pagamento_cria_historico_manual(self, contrato_36m, usuario_cli):
        """Deve criar HistoricoPagamento com origem_pagamento='MANUAL'."""
        from financeiro.models import Parcela, TipoParcela, HistoricoPagamento
        _, cli = usuario_cli
        p = contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).order_by('numero_parcela').first()
        url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': p.pk})
        cli.post(url, {
            'data_pagamento': str(date.today()),
            'valor_pago': str(p.valor_atual),
            'forma_pagamento': 'PIX',
        })
        assert HistoricoPagamento.objects.filter(parcela=p, origem_pagamento='MANUAL').exists()

    def test_parcela_ja_paga_retorna_400(self, contrato_36m, usuario_cli):
        """Tentar pagar uma parcela já paga deve retornar 400."""
        from financeiro.models import Parcela, TipoParcela
        _, cli = usuario_cli
        p = contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).first()
        p.pago = True
        p.save()
        url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': p.pk})
        resp = cli.post(url, {
            'data_pagamento': str(date.today()),
            'valor_pago': str(p.valor_atual),
            'forma_pagamento': 'DINHEIRO',
        })
        assert resp.status_code == 400


# ── Passo 4: reajuste ciclo 2 ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestReajusteCiclo2:
    """Passo 4 — Aplicação do reajuste ciclo 2 via API modo legado."""

    def test_reajuste_aplica_5_pct_nas_parcelas_ciclo2(self, contrato_36m, usuario_cli):
        """Após 5% de reajuste, as parcelas do ciclo 2 devem ter valor aumentado."""
        from financeiro.models import Reajuste
        _, cli = usuario_cli

        pmt_antes = contrato_36m.parcelas.get(numero_parcela=13).valor_atual

        url = reverse('financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato_36m.pk})
        resp = cli.post(url, data=json.dumps({
            'percentual': '5.0',
            'parcela_inicial': 13,
            'parcela_final': 36,
        }), content_type='application/json')

        assert resp.status_code == 200
        assert resp.json()['sucesso'] is True

        parcela_13 = contrato_36m.parcelas.get(numero_parcela=13)
        # Modo Tabela Price: PMT_novo = PMT_atual × (1 + IPCA) × (1 + taxa_mensal)^prazo
        _taxa = TAXA_MENSAL / Decimal('100')
        _fator_juros = (Decimal('1') + _taxa) ** PRAZO_REAJUSTE
        pmt_esperado = (pmt_antes * Decimal('1.05') * _fator_juros).quantize(Decimal('0.01'))
        assert parcela_13.valor_atual == pmt_esperado

    def test_reajuste_atualiza_ciclo_no_contrato(self, contrato_36m, usuario_cli):
        """ciclo_reajuste_atual deve ser 2 após aplicar o reajuste."""
        _, cli = usuario_cli
        url = reverse('financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato_36m.pk})
        cli.post(url, data=json.dumps({
            'percentual': '5.0',
            'parcela_inicial': 13,
            'parcela_final': 36,
        }), content_type='application/json')
        contrato_36m.refresh_from_db()
        assert contrato_36m.ciclo_reajuste_atual == 2

    def test_reajuste_zero_retorna_erro(self, contrato_36m, usuario_cli):
        """Percentual zero deve ser rejeitado pelo endpoint."""
        _, cli = usuario_cli
        url = reverse('financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato_36m.pk})
        resp = cli.post(url, data=json.dumps({
            'percentual': '0',
            'parcela_inicial': 13,
            'parcela_final': 36,
        }), content_type='application/json')
        assert resp.status_code == 400
        assert resp.json()['sucesso'] is False


# ── Passo 5: geração de carnê 20 meses ────────────────────────────────────────

@pytest.mark.django_db
class TestGeracaoCarne20Meses:
    """Passo 5 — Geração de carnê para os próximos 20 meses."""

    def _aplicar_reajuste_ciclo2(self, contrato, cli):
        """Aplica o reajuste ciclo 2 para liberar geração de boletos do ciclo 2."""
        url = reverse('financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato.pk})
        cli.post(url, data=json.dumps({
            'percentual': '5.0',
            'parcela_inicial': 13,
            'parcela_final': 36,
        }), content_type='application/json')

    def test_gera_20_boletos_ciclos_1_e_2(self, contrato_36m, usuario_cli):
        """20 parcelas dos ciclos 1 e 2 devem ser geradas sem bloqueios."""
        from financeiro.models import Parcela, TipoParcela
        _, cli = usuario_cli
        self._aplicar_reajuste_ciclo2(contrato_36m, cli)

        ids = list(
            Parcela.objects.filter(
                contrato=contrato_36m, tipo_parcela=TipoParcela.NORMAL, pago=False,
            ).order_by('numero_parcela').values_list('pk', flat=True)[:20]
        )
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato_36m.pk})
        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            resp = cli.post(url, data=json.dumps({'parcelas': ids}), content_type='application/json')

        assert resp.status_code == 200
        d = resp.json()
        assert d['gerados'] == 20
        assert d['bloqueados'] == 0

    def test_sem_parcelas_retorna_400(self, contrato_36m, usuario_cli):
        """POST sem parcelas selecionadas deve retornar 400."""
        _, cli = usuario_cli
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato_36m.pk})
        resp = cli.post(url, data=json.dumps({'parcelas': []}), content_type='application/json')
        assert resp.status_code == 400


# ── Passo 6: bloqueio ciclo 3 ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestBloqueioReajusteCiclo3:
    """Passo 6 — Validação do bloqueio de geração para parcelas do ciclo 3."""

    def _aplicar_reajuste_ciclo2(self, contrato, cli):
        url = reverse('financeiro:aplicar_reajuste_api', kwargs={'contrato_id': contrato.pk})
        cli.post(url, data=json.dumps({
            'percentual': '5.0',
            'parcela_inicial': 13,
            'parcela_final': 36,
        }), content_type='application/json')

    def test_parcelas_ciclo3_bloqueadas_em_lote(self, contrato_36m, usuario_cli):
        """Parcelas 25+ devem ser bloqueadas pois ciclo 3 não foi reajustado."""
        from financeiro.models import Parcela, TipoParcela
        _, cli = usuario_cli
        self._aplicar_reajuste_ciclo2(contrato_36m, cli)

        ids_c3 = list(
            Parcela.objects.filter(
                contrato=contrato_36m, tipo_parcela=TipoParcela.NORMAL,
                pago=False, numero_parcela__gte=25,
            ).values_list('pk', flat=True)
        )
        assert len(ids_c3) > 0

        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato_36m.pk})
        with patch.object(Parcela, 'gerar_boleto', _mock_gerar_boleto):
            resp = cli.post(url, data=json.dumps({'parcelas': ids_c3}),
                            content_type='application/json')

        d = resp.json()
        assert d['bloqueados'] == len(ids_c3)
        assert d['gerados'] == 0

    def test_pode_gerar_boleto_retorna_true_para_ciclo_futuro(self, contrato_36m, usuario_cli):
        """pode_gerar_boleto() deve retornar True para ciclo 3 ainda futuro.

        O contrato tem 14 meses — ciclo 3 só vence em +10 meses. O método
        pode_gerar_boleto() não bloqueia ciclos futuros; o bloqueio em lote
        é feito pelo max_parcela_lote na view gerar_carne.
        """
        _, cli = usuario_cli
        self._aplicar_reajuste_ciclo2(contrato_36m, cli)
        contrato_36m.refresh_from_db()

        pode, motivo = contrato_36m.pode_gerar_boleto(25)
        assert pode is True
        assert motivo  # motivo explicativo não deve ser vazio


# ── Passo 7: carnê PDF 6 meses ────────────────────────────────────────────────

@pytest.mark.django_db
class TestCarnePDF6Meses:
    """Passo 7 — Geração do carnê PDF com 6 parcelas via BoletoService mock."""

    def test_download_carne_pdf_retorna_pdf(self, contrato_36m, usuario_cli):
        """POST em download_carne_pdf deve retornar Content-Type application/pdf."""
        from financeiro.models import Parcela, TipoParcela
        from financeiro.services.boleto_service import BoletoService
        _, cli = usuario_cli

        # Simula boletos já gerados nas 6 primeiras parcelas
        parcelas = list(
            contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL, pago=False)
            .order_by('numero_parcela')[:6]
        )
        for p in parcelas:
            p.nosso_numero = f'{p.numero_parcela:010d}'
            p.linha_digitavel = f'12345.{p.numero_parcela:05d} 00000.000001 1 10000000000000'
            p.save(update_fields=['nosso_numero', 'linha_digitavel'])

        ids = [p.pk for p in parcelas]
        url = reverse('financeiro:download_carne_pdf', kwargs={'contrato_id': contrato_36m.pk})

        with patch.object(BoletoService, 'gerar_carne',
                          return_value={'sucesso': True, 'pdf_content': b'%PDF-1.4 TEST', 'total': 6}):
            resp = cli.post(url, data=json.dumps({'parcela_ids': ids}),
                            content_type='application/json')

        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
        assert b'PDF' in resp.content

    def test_carne_pdf_sem_parcelas_retorna_400(self, contrato_36m, usuario_cli):
        """POST sem parcelas deve retornar 400."""
        _, cli = usuario_cli
        url = reverse('financeiro:download_carne_pdf', kwargs={'contrato_id': contrato_36m.pk})
        resp = cli.post(url, data=json.dumps({'parcela_ids': []}),
                        content_type='application/json')
        assert resp.status_code == 400

    def test_carne_pdf_get_lista_parcelas(self, contrato_36m, usuario_cli):
        """GET deve retornar JSON com lista de parcelas disponíveis."""
        _, cli = usuario_cli
        url = reverse('financeiro:download_carne_pdf', kwargs={'contrato_id': contrato_36m.pk})
        resp = cli.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert 'parcelas' in data
        assert len(data['parcelas']) == N


# ── Passo 8: quitação manual em lote ─────────────────────────────────────────

@pytest.mark.django_db
class TestQuitacaoManualLote:
    """Passo 8 — Quitação manual de múltiplas parcelas."""

    def test_quitar_3_parcelas_sequencialmente(self, contrato_36m, usuario_cli):
        """Quitar 3 parcelas em sequência deve marcar todas como pagas."""
        from financeiro.models import Parcela, TipoParcela, HistoricoPagamento
        _, cli = usuario_cli
        parcelas = list(
            contrato_36m.parcelas.filter(tipo_parcela=TipoParcela.NORMAL, pago=False)
            .order_by('numero_parcela')[:3]
        )
        for p in parcelas:
            url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': p.pk})
            resp = cli.post(url, {
                'data_pagamento': str(date.today()),
                'valor_pago': str(p.valor_atual),
                'forma_pagamento': 'PIX',
            })
            assert resp.status_code == 200
            assert resp.json()['sucesso'] is True

        pagas = contrato_36m.parcelas.filter(
            tipo_parcela=TipoParcela.NORMAL, pago=True,
        ).count()
        assert pagas == 3
        assert HistoricoPagamento.objects.filter(
            parcela__in=parcelas,
        ).count() == 3


# ── Passo 9: quitação via OFX ────────────────────────────────────────────────

@pytest.mark.django_db
class TestQuitacaoOFX:
    """Passo 9 — Quitação via extrato OFX com reconciliação por nosso_numero."""

    def _construir_ofx(self, nosso_numero: str, valor: Decimal) -> bytes:
        """Monta conteúdo OFX mínimo com uma transação de crédito."""
        return (
            b"OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\n"
            b"ENCODING:USASCII\nCHARSET:1252\nCOMPRESSION:NONE\n"
            b"OLDFILEUID:NONE\nNEWFILEUID:NONE\n\n"
            b"<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><CURDEF>BRL</CURDEF>\n"
            b"<BANKTRANLIST>\n"
            b"<STMTTRN><TRNTYPE>CREDIT</TRNTYPE>"
            b"<DTPOSTED>20260501000000</DTPOSTED>"
            b"<TRNAMT>" + str(valor).encode() + b"</TRNAMT>"
            b"<FITID>UNIT-OFX-" + nosso_numero.encode() + b"</FITID>"
            b"<MEMO>COBRANCA NOSSO NUMERO " + nosso_numero.encode() + b" PAGO</MEMO>"
            b"</STMTTRN>\n"
            b"</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"
        )

    def test_ofx_quita_parcela_via_nosso_numero(self, contrato_36m, usuario_cli):
        """OFX com nosso_numero extraído pelo BRCobrança deve quitar a parcela correta."""
        from financeiro.models import Parcela, TipoParcela, HistoricoPagamento
        from django.core.files.uploadedfile import SimpleUploadedFile
        _, cli = usuario_cli

        # Prepara parcela com nosso_numero
        parcela = contrato_36m.parcelas.filter(
            tipo_parcela=TipoParcela.NORMAL, pago=False,
        ).order_by('numero_parcela').first()
        nn = f'{parcela.numero_parcela:010d}'
        parcela.nosso_numero = nn
        parcela.save(update_fields=['nosso_numero'])

        mock_resp = _mock_brcobranca_ofx(nn, parcela.valor_atual, date.today())
        ofx_bytes = self._construir_ofx(nn, parcela.valor_atual)
        arquivo = SimpleUploadedFile('extrato.ofx', ofx_bytes, content_type='application/x-ofx')

        url = reverse('financeiro:upload_ofx')
        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            resp = cli.post(url, {'arquivo_ofx': arquivo, 'dry_run': '0'})

        assert resp.status_code == 200
        d = resp.json()
        assert d['sucesso'] is True
        assert d['reconciliadas'] >= 1
        assert parcela.pk in d['parcelas_quitadas']

        parcela.refresh_from_db()
        assert parcela.pago is True
        assert HistoricoPagamento.objects.filter(
            parcela=parcela, origem_pagamento='OFX',
        ).exists()

    def test_ofx_dry_run_nao_quita(self, contrato_36m, usuario_cli):
        """dry_run=1 deve parsear o OFX sem marcar parcelas como pagas."""
        from financeiro.models import Parcela, TipoParcela
        from django.core.files.uploadedfile import SimpleUploadedFile
        _, cli = usuario_cli

        parcela = contrato_36m.parcelas.filter(
            tipo_parcela=TipoParcela.NORMAL, pago=False,
        ).order_by('numero_parcela').first()
        nn = f'{parcela.numero_parcela:010d}'
        parcela.nosso_numero = nn
        parcela.save(update_fields=['nosso_numero'])

        mock_resp = _mock_brcobranca_ofx(nn, parcela.valor_atual, date.today())
        ofx_bytes = self._construir_ofx(nn, parcela.valor_atual)
        arquivo = SimpleUploadedFile('extrato.ofx', ofx_bytes, content_type='application/x-ofx')

        url = reverse('financeiro:upload_ofx')
        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            resp = cli.post(url, {'arquivo_ofx': arquivo, 'dry_run': '1'})

        assert resp.status_code == 200
        assert resp.json()['dry_run'] is True
        parcela.refresh_from_db()
        assert parcela.pago is False, "dry_run não deve quitar parcelas"

    def test_ofx_sem_arquivo_retorna_400(self, contrato_36m, usuario_cli):
        """POST sem arquivo OFX deve retornar 400."""
        _, cli = usuario_cli
        url = reverse('financeiro:upload_ofx')
        resp = cli.post(url, {})
        assert resp.status_code == 400

    def test_ofx_extensao_invalida_retorna_400(self, contrato_36m, usuario_cli):
        """Arquivo com extensão .txt deve ser rejeitado."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        _, cli = usuario_cli
        arquivo = SimpleUploadedFile('extrato.txt', b'conteudo', content_type='text/plain')
        url = reverse('financeiro:upload_ofx')
        resp = cli.post(url, {'arquivo_ofx': arquivo})
        assert resp.status_code == 400
        assert '.ofx' in resp.json().get('erro', '').lower()
