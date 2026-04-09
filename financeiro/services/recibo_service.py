"""
R-05: Serviço de geração de Recibo de Quitação Antecipada em PDF.

Usa ReportLab para gerar um recibo formal com:
- Cabeçalho da imobiliária (cedente)
- Dados do contrato e comprador
- Tabela de parcelas antecipadas (original vs. desconto vs. pago)
- Totais e economia
- Campo de assinatura
"""
import io
from decimal import Decimal
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# ─── Cores ────────────────────────────────────────────────────────────────────
AZUL        = HexColor('#1a3a5c')
AZUL_CLARO  = HexColor('#e8f0f8')
VERDE       = HexColor('#1b5e20')
CINZA       = HexColor('#616161')
CINZA_LINHA = HexColor('#e0e0e0')

PAGE_W, PAGE_H = A4


def _fmt_valor(v) -> str:
    if v is None:
        return 'R$ 0,00'
    return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_data(d) -> str:
    if d is None:
        return '—'
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m/%Y')
    return str(d)


def gerar_recibo_antecipacao_pdf(contrato, historicos) -> bytes:
    """
    Gera PDF de recibo de quitação antecipada.

    Args:
        contrato: instância de Contrato
        historicos: QuerySet/list de HistoricoPagamento (antecipado=True)
    Returns:
        bytes do PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    bold   = ParagraphStyle('bold',   parent=styles['Normal'], fontName='Helvetica-Bold')
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=9)
    small  = ParagraphStyle('small',  parent=styles['Normal'], fontSize=8, textColor=CINZA)
    titulo = ParagraphStyle('titulo', parent=styles['Normal'], fontSize=16,
                            fontName='Helvetica-Bold', textColor=AZUL, alignment=TA_CENTER)
    centro = ParagraphStyle('centro', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    right  = ParagraphStyle('right',  parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)

    story = []

    # ─── Cabeçalho ────────────────────────────────────────────────────────────
    imob   = contrato.imobiliaria
    nome_empresa = imob.nome if imob else 'Imobiliária'
    cnpj_empresa = getattr(imob, 'cnpj', '') or ''
    end_empresa  = getattr(imob, 'endereco', '') or ''

    cab_data = [
        [Paragraph(f'<b>{nome_empresa}</b>', ParagraphStyle('eh', fontSize=13, fontName='Helvetica-Bold', textColor=AZUL)),
         Paragraph('RECIBO DE QUITAÇÃO<br/><font size="10">ANTECIPAÇÃO DE PARCELAS</font>',
                   ParagraphStyle('rt', fontSize=14, fontName='Helvetica-Bold', textColor=AZUL, alignment=TA_RIGHT))],
        [Paragraph(f'CNPJ: {cnpj_empresa}', small),
         Paragraph(f'Nº Contrato: <b>{contrato.numero_contrato}</b>', right)],
        [Paragraph(end_empresa, small), Paragraph(f'Data: <b>{_fmt_data(date.today())}</b>', right)],
    ]
    cab_table = Table(cab_data, colWidths=[10 * cm, 7 * cm])
    cab_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(cab_table)
    story.append(HRFlowable(width='100%', thickness=2, color=AZUL, spaceAfter=8))

    # ─── Dados do contrato / comprador ────────────────────────────────────────
    comprador  = contrato.comprador
    nome_comp  = comprador.nome if comprador else '—'
    doc_comp   = ''
    if comprador:
        doc_comp = getattr(comprador, 'cpf', '') or getattr(comprador, 'cnpj', '') or ''

    imovel = contrato.imovel
    imovel_label = ''
    if imovel:
        imovel_label = imovel.identificacao or imovel.loteamento or f'Imóvel #{imovel.pk}'

    dados_data = [
        [Paragraph('<b>COMPRADOR</b>', small), Paragraph(nome_comp, normal),
         Paragraph('<b>CPF/CNPJ</b>', small), Paragraph(doc_comp, normal)],
        [Paragraph('<b>IMÓVEL</b>', small), Paragraph(imovel_label, normal),
         Paragraph('<b>DATA DO CONTRATO</b>', small), Paragraph(_fmt_data(contrato.data_contrato), normal)],
    ]
    dados_table = Table(dados_data, colWidths=[3 * cm, 6 * cm, 3.5 * cm, 4.5 * cm])
    dados_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), AZUL_CLARO),
        ('BACKGROUND', (2, 0), (2, -1), AZUL_CLARO),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, CINZA_LINHA),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(dados_table)
    story.append(Spacer(1, 10))

    # ─── Tabela de parcelas ───────────────────────────────────────────────────
    story.append(Paragraph('<b>PARCELAS QUITADAS POR ANTECIPAÇÃO</b>',
                           ParagraphStyle('sh', fontSize=10, fontName='Helvetica-Bold', textColor=AZUL, spaceBefore=4, spaceAfter=4)))

    header = [
        Paragraph('<b>Parcela</b>', ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=white)),
        Paragraph('<b>Vencimento</b>', ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=white)),
        Paragraph('<b>Valor Original</b>', ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=white, alignment=TA_RIGHT)),
        Paragraph('<b>Desconto</b>', ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=white, alignment=TA_RIGHT)),
        Paragraph('<b>Valor Pago</b>', ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=white, alignment=TA_RIGHT)),
        Paragraph('<b>Data Pag.</b>', ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=white)),
    ]

    rows = [header]
    total_original   = Decimal('0')
    total_desconto   = Decimal('0')
    total_pago       = Decimal('0')
    desconto_perc    = Decimal('0')

    for h in historicos:
        parcela = h.parcela
        vo = h.valor_parcela or Decimal('0')
        vd = h.valor_desconto or Decimal('0')
        vp = h.valor_pago or Decimal('0')
        total_original += vo
        total_desconto += vd
        total_pago     += vp

        row = [
            Paragraph(str(parcela.numero_parcela), normal),
            Paragraph(_fmt_data(parcela.data_vencimento), normal),
            Paragraph(_fmt_valor(vo), right),
            Paragraph(f'<font color="#c62828">− {_fmt_valor(vd)}</font>', right),
            Paragraph(f'<b>{_fmt_valor(vp)}</b>', right),
            Paragraph(_fmt_data(h.data_pagamento), normal),
        ]
        rows.append(row)

    # Linha de totais
    rows.append([
        Paragraph('<b>TOTAL</b>', bold),
        Paragraph('', normal),
        Paragraph(f'<b>{_fmt_valor(total_original)}</b>', right),
        Paragraph(f'<font color="#c62828"><b>− {_fmt_valor(total_desconto)}</b></font>', right),
        Paragraph(f'<b>{_fmt_valor(total_pago)}</b>', right),
        Paragraph('', normal),
    ])

    parc_table = Table(rows, colWidths=[2 * cm, 2.8 * cm, 3.2 * cm, 2.8 * cm, 3.2 * cm, 3 * cm])
    parc_table.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('TEXTCOLOR',  (0, 0), (-1, 0), white),
        # Linha de totais
        ('BACKGROUND', (0, -1), (-1, -1), AZUL_CLARO),
        ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
        # Grade
        ('GRID',       (0, 0), (-1, -1), 0.5, CINZA_LINHA),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, HexColor('#f5f5f5')]),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('ALIGN', (2, 0), (-2, -1), 'RIGHT'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
    ]))
    story.append(parc_table)
    story.append(Spacer(1, 10))

    # ─── Resumo ───────────────────────────────────────────────────────────────
    economia = total_original - total_pago
    perc_eco = (economia / total_original * 100).quantize(Decimal('0.01')) if total_original else Decimal('0')

    resumo_data = [
        ['Total de parcelas antecipadas:', str(len(rows) - 2)],
        ['Valor total original:', _fmt_valor(total_original)],
        ['Total de descontos concedidos:', f'− {_fmt_valor(total_desconto)}'],
        ['TOTAL PAGO:', _fmt_valor(total_pago)],
        ['Economia total:', f'{_fmt_valor(economia)} ({perc_eco}%)'],
    ]
    resumo_table = Table(resumo_data, colWidths=[9 * cm, 8 * cm], hAlign='RIGHT')
    resumo_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 3), (-1, 3), VERDE),
        ('TEXTCOLOR',  (0, 3), (-1, 3), white),
        ('FONTNAME',   (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTNAME',   (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('TEXTCOLOR',  (0, 4), (-1, 4), VERDE),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, CINZA_LINHA),
    ]))
    story.append(resumo_table)
    story.append(Spacer(1, 20))

    # ─── Declaração ───────────────────────────────────────────────────────────
    story.append(Paragraph(
        f'Declaro que recebi de <b>{nome_comp}</b> a importância de <b>{_fmt_valor(total_pago)}</b> '
        f'referente à quitação antecipada de {len(rows) - 2} parcela(s) do contrato '
        f'<b>{contrato.numero_contrato}</b>, com desconto de <b>{_fmt_valor(total_desconto)}</b>, '
        f'dando plena, rasa e irrevogável quitação pelas mesmas.',
        ParagraphStyle('decl', fontSize=9, spaceBefore=4, spaceAfter=16)
    ))

    # ─── Assinaturas ─────────────────────────────────────────────────────────
    sig_data = [
        [Paragraph('_' * 52, centro), Paragraph('_' * 52, centro)],
        [Paragraph(nome_empresa, centro), Paragraph(nome_comp, centro)],
        [Paragraph('Cedente', small_c := ParagraphStyle('sc', fontSize=8, textColor=CINZA, alignment=TA_CENTER)),
         Paragraph('Devedor', small_c)],
        [Paragraph(_fmt_data(date.today()), small_c), Paragraph('', small_c)],
    ]
    sig_table = Table(sig_data, colWidths=[8.5 * cm, 8.5 * cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(sig_table)

    # ─── Rodapé ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_LINHA))
    story.append(Paragraph(
        f'Documento gerado em {_fmt_data(date.today())} pelo sistema Gestão de Contratos. '
        f'Este documento possui validade legal mediante assinatura das partes.',
        ParagraphStyle('rodape', fontSize=7, textColor=CINZA, alignment=TA_CENTER, spaceBefore=4)
    ))

    doc.build(story)
    return buffer.getvalue()


# =============================================================================
# Recibo de Pagamento Individual (parcela quitada)
# =============================================================================

def gerar_recibo_pagamento_pdf(historico) -> bytes:
    """
    Gera recibo de pagamento para um HistoricoPagamento individual.

    Args:
        historico: instância de financeiro.models.HistoricoPagamento
    Returns:
        bytes do PDF
    """
    buffer = io.BytesIO()
    parcela  = historico.parcela
    contrato = parcela.contrato
    imob     = contrato.imobiliaria
    comp     = contrato.comprador

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    titulo  = ParagraphStyle('titulo',  parent=styles['Normal'], fontSize=16,
                             fontName='Helvetica-Bold', textColor=AZUL, alignment=TA_CENTER)
    negrito = ParagraphStyle('negrito', parent=styles['Normal'], fontName='Helvetica-Bold')
    normal  = ParagraphStyle('normal',  parent=styles['Normal'], fontSize=9)
    small   = ParagraphStyle('small',   parent=styles['Normal'], fontSize=8, textColor=CINZA)
    small_c = ParagraphStyle('small_c', parent=styles['Normal'], fontSize=8,
                             textColor=CINZA, alignment=TA_CENTER)
    centro  = ParagraphStyle('centro',  parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)

    story = []

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    nome_empresa = imob.nome if imob else '—'
    doc_empresa  = getattr(imob, 'documento', None) or getattr(imob, 'cnpj', '') or ''
    end_empresa  = getattr(imob, 'endereco', '') or ''

    story.append(Paragraph(nome_empresa.upper(), titulo))
    if doc_empresa:
        story.append(Paragraph(f'CNPJ/CPF: {doc_empresa}', ParagraphStyle('sub', fontSize=9,
                    textColor=CINZA, alignment=TA_CENTER)))
    if end_empresa:
        story.append(Paragraph(end_empresa, ParagraphStyle('sub2', fontSize=9,
                    textColor=CINZA, alignment=TA_CENTER)))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width='100%', thickness=2, color=AZUL))
    story.append(Spacer(1, 6))
    story.append(Paragraph('RECIBO DE PAGAMENTO', titulo))
    story.append(HRFlowable(width='100%', thickness=1, color=AZUL_CLARO))
    story.append(Spacer(1, 8))

    # Número do recibo e data de emissão
    num_recibo = f"{contrato.numero_contrato}-P{parcela.numero_parcela:03d}"
    story.append(Paragraph(
        f'<b>Recibo n.º {num_recibo}</b> &nbsp;&mdash;&nbsp; Emitido em {_fmt_data(date.today())}',
        ParagraphStyle('nr', fontSize=10, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 12))

    # ── Valor em destaque ─────────────────────────────────────────────────────
    valor_total_pago = historico.valor_pago
    val_data = [[
        Paragraph('VALOR RECEBIDO', ParagraphStyle('vl', fontName='Helvetica-Bold',
                  fontSize=11, textColor=white, alignment=TA_CENTER)),
        Paragraph(_fmt_valor(valor_total_pago), ParagraphStyle('vv', fontName='Helvetica-Bold',
                  fontSize=18, textColor=white, alignment=TA_CENTER)),
    ]]
    val_table = Table(val_data, colWidths=[6 * cm, 11 * cm])
    val_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), VERDE),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(val_table)
    story.append(Spacer(1, 14))

    # ── Dados do pagador ──────────────────────────────────────────────────────
    story.append(Paragraph('<b>DADOS DO PAGAMENTO</b>', negrito))
    story.append(Spacer(1, 4))

    cpf_comp = getattr(comp, 'cpf', '') or ''
    info_data = [
        ['Pagador (Comprador):', comp.nome + (f' — CPF {cpf_comp}' if cpf_comp else '')],
        ['Contrato n.º:',        contrato.numero_contrato],
        ['Imóvel:',              f"{parcela.contrato.imovel.identificacao} — {parcela.contrato.imovel.loteamento or ''}"],
        ['Parcela:',             f"{parcela.numero_parcela} / {contrato.numero_parcelas} "
                                 f"(vencimento: {_fmt_data(parcela.data_vencimento)})"],
        ['Data de Pagamento:',   _fmt_data(historico.data_pagamento)],
        ['Forma de Pagamento:',  historico.get_forma_pagamento_display() if hasattr(historico, 'get_forma_pagamento_display') else historico.forma_pagamento],
    ]

    # Detalhamento se há juros/multa
    if historico.valor_juros and historico.valor_juros > 0:
        info_data.append(['Valor da Parcela:', _fmt_valor(historico.valor_parcela)])
        info_data.append(['Juros de Mora:', _fmt_valor(historico.valor_juros)])
        info_data.append(['Multa:', _fmt_valor(historico.valor_multa)])
    if historico.valor_desconto and historico.valor_desconto > 0:
        info_data.append(['Desconto:', f'- {_fmt_valor(historico.valor_desconto)}'])

    info_data.append(['<b>TOTAL PAGO:</b>', f'<b>{_fmt_valor(valor_total_pago)}</b>'])

    tabela_info = Table(
        [[Paragraph(r[0], small), Paragraph(r[1], normal)] for r in info_data],
        colWidths=[5 * cm, 12 * cm],
    )
    tabela_info.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [white, AZUL_CLARO]),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('BOX',           (0, 0), (-1, -1), 0.5, CINZA_LINHA),
        ('GRID',          (0, 0), (-1, -1), 0.3, CINZA_LINHA),
        ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(tabela_info)

    # Observações
    if historico.observacoes:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f'<b>Observações:</b> {historico.observacoes}', normal))

    # ── Declaração ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f'Declaro que recebi de <b>{comp.nome}</b> a importância de '
        f'<b>{_fmt_valor(valor_total_pago)}</b> referente ao pagamento da parcela '
        f'n.º <b>{parcela.numero_parcela}</b> do contrato n.º <b>{contrato.numero_contrato}</b>, '
        f'dando plena, geral e irrevogável quitação pelo valor recebido.',
        ParagraphStyle('decl', fontSize=9, leading=14, alignment=TA_JUSTIFY)
    ))

    # ── Assinaturas ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_LINHA))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f'___________________________, {_fmt_data(date.today())}', centro))
    story.append(Spacer(1, 20))

    sig_data = [
        [Paragraph('_' * 40, small_c), Paragraph('_' * 40, small_c)],
        [Paragraph(f'<b>RECEBEDOR</b><br/>{nome_empresa}', small_c),
         Paragraph(f'<b>PAGADOR</b><br/>{comp.nome}', small_c)],
    ]
    sig_table = Table(sig_data, colWidths=[8.5 * cm, 8.5 * cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(sig_table)

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_LINHA))
    story.append(Paragraph(
        f'Documento gerado em {_fmt_data(date.today())} pelo sistema Gestão de Contratos — M&S do Brasil LTDA.',
        ParagraphStyle('rodape2', fontSize=7, textColor=CINZA, alignment=TA_CENTER, spaceBefore=4)
    ))

    doc.build(story)
    return buffer.getvalue()


# =============================================================================
# R-07: Declaração Anual de Quitação de Débitos — Lei 12.007/2009
# =============================================================================

DOURADO     = HexColor('#7B6000')
DOURADO_BG  = HexColor('#FFFDE7')
VERMELHO    = HexColor('#B71C1C')
VERDE_BG    = HexColor('#E8F5E9')


def _extenso_ano(ano: int) -> str:
    mapa = {
        2020: 'dois mil e vinte',
        2021: 'dois mil e vinte e um',
        2022: 'dois mil e vinte e dois',
        2023: 'dois mil e vinte e três',
        2024: 'dois mil e vinte e quatro',
        2025: 'dois mil e vinte e cinco',
        2026: 'dois mil e vinte e seis',
        2027: 'dois mil e vinte e sete',
        2028: 'dois mil e vinte e oito',
        2029: 'dois mil e vinte e nove',
        2030: 'dois mil e trinta',
    }
    return mapa.get(ano, str(ano))


def gerar_declaracao_quitacao_pdf(contrato, ano: int) -> bytes:
    """
    R-07: Gera a Declaração Anual de Quitação de Débitos (Lei 12.007/2009).

    Args:
        contrato: instância de Contrato com select_related de imobiliaria,
                  comprador e imovel já carregados.
        ano: ano de referência (ex: 2025).

    Returns:
        bytes com o PDF gerado.
    """
    from financeiro.models import Parcela

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    titulo_style = _s('DT',  fontSize=14, textColor=AZUL, alignment=TA_CENTER,
                      fontName='Helvetica-Bold', spaceAfter=4)
    subtit_style = _s('DS',  fontSize=10, textColor=AZUL, alignment=TA_CENTER,
                      fontName='Helvetica', spaceAfter=2)
    lei_style    = _s('DL',  fontSize=8,  textColor=CINZA, alignment=TA_CENTER,
                      fontName='Helvetica-Oblique', spaceAfter=12)
    corpo_style  = _s('DC',  fontSize=10, textColor=black, alignment=TA_LEFT,
                      fontName='Helvetica', leading=15, spaceAfter=8)
    cabec_style  = _s('DH',  fontSize=12, textColor=white, alignment=TA_CENTER,
                      fontName='Helvetica-Bold')
    small_c      = _s('DSC', fontSize=8,  textColor=CINZA, alignment=TA_CENTER,
                      fontName='Helvetica')
    rodape_s     = _s('DR',  fontSize=7,  textColor=CINZA, alignment=TA_CENTER,
                      fontName='Helvetica-Oblique', spaceBefore=4)

    imob   = contrato.imobiliaria
    comp   = contrato.comprador
    imovel = contrato.imovel

    doc_comp  = comp.cpf or comp.cnpj or '—'
    doc_label = 'CPF' if comp.tipo_pessoa == 'PF' else 'CNPJ'
    doc_imob  = imob.cnpj or imob.cpf or '—'
    cab_label = 'CNPJ' if imob.tipo_pessoa == 'PJ' else 'CPF'

    cidade_imob = getattr(imob, 'cidade', '') or ''
    estado_imob = getattr(imob, 'estado', '') or ''
    local = (f'{cidade_imob}/{estado_imob}' if cidade_imob and estado_imob
             else cidade_imob or 'local')

    # ── Parcelas do ano ───────────────────────────────────────────────────────
    parcelas_ano      = list(Parcela.objects.filter(
        contrato=contrato, data_vencimento__year=ano,
    ).order_by('numero_parcela'))
    parcelas_pagas    = [p for p in parcelas_ano if p.pago]
    parcelas_pend     = [p for p in parcelas_ano if not p.pago]
    todas_pagas       = len(parcelas_pend) == 0 and len(parcelas_pagas) > 0

    story = []

    # ── Cabeçalho da imobiliária ──────────────────────────────────────────────
    cab_rows = [[Paragraph(imob.nome.upper(), cabec_style)]]
    if doc_imob != '—':
        cab_rows.append([Paragraph(f'{cab_label}: {doc_imob}',
                                   _s('DCI', fontSize=9, textColor=white,
                                      alignment=TA_CENTER, fontName='Helvetica'))])
    if imob.endereco:
        cab_rows.append([Paragraph(imob.endereco,
                                   _s('DCE', fontSize=8,
                                      textColor=HexColor('#cfe2ff'),
                                      alignment=TA_CENTER, fontName='Helvetica'))])

    cab_table = Table([[r[0]] for r in cab_rows], colWidths=[17 * cm])
    cab_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), AZUL),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    story.append(cab_table)
    story.append(Spacer(1, 14))

    # ── Título ────────────────────────────────────────────────────────────────
    story.append(Paragraph('DECLARAÇÃO ANUAL DE QUITAÇÃO DE DÉBITOS', titulo_style))
    story.append(Paragraph(f'Ano de Referência: {ano}', subtit_style))
    story.append(Paragraph(
        'Conforme Art. 1º da Lei Federal nº 12.007, de 29 de julho de 2009', lei_style))
    story.append(HRFlowable(width='100%', thickness=1, color=AZUL))
    story.append(Spacer(1, 10))

    # ── Selo de status ────────────────────────────────────────────────────────
    if todas_pagas:
        selo_txt = '✔  TODAS AS PRESTAÇÕES DO ANO ESTÃO QUITADAS'
        selo_cor, selo_bg = VERDE, VERDE_BG
    elif parcelas_pagas:
        selo_txt = '⚠  EXISTEM PRESTAÇÕES PENDENTES NO ANO DE REFERÊNCIA'
        selo_cor, selo_bg = DOURADO, DOURADO_BG
    else:
        selo_txt = '✖  NENHUMA PRESTAÇÃO FOI PAGA NO ANO DE REFERÊNCIA'
        selo_cor, selo_bg = VERMELHO, HexColor('#FFEBEE')

    selo_s = _s('DS2', fontSize=10, textColor=selo_cor, alignment=TA_CENTER,
                fontName='Helvetica-Bold')
    selo_t = Table([[Paragraph(selo_txt, selo_s)]], colWidths=[17 * cm])
    selo_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), selo_bg),
        ('BOX',        (0, 0), (-1, -1), 1, selo_cor),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(selo_t)
    story.append(Spacer(1, 12))

    # ── Corpo da declaração ───────────────────────────────────────────────────
    imovel_str = getattr(imovel, 'identificacao', None) or str(imovel)
    if todas_pagas:
        corpo = (
            f'A empresa <b>{imob.nome}</b>, {cab_label} {doc_imob}, com sede em {local}, '
            f'DECLARA, para os devidos fins legais e em cumprimento ao disposto no Art. 1º '
            f'da Lei Federal nº 12.007/2009, que o(a) Sr(a). <b>{comp.nome}</b>, '
            f'{doc_label} <b>{doc_comp}</b>, referente ao '
            f'<b>Contrato nº {contrato.numero_contrato}</b> — Imóvel: {imovel_str} —, '
            f'<b>NÃO POSSUI DÉBITOS</b> em aberto relativos ao ano de '
            f'<b>{ano} ({_extenso_ano(ano)})</b>, tendo cumprido integralmente com suas '
            f'obrigações de pagamento no período.'
        )
    elif parcelas_pagas:
        corpo = (
            f'A empresa <b>{imob.nome}</b>, {cab_label} {doc_imob}, com sede em {local}, '
            f'DECLARA, em atenção ao Art. 1º da Lei Federal nº 12.007/2009, que o(a) '
            f'Sr(a). <b>{comp.nome}</b>, {doc_label} <b>{doc_comp}</b>, referente ao '
            f'<b>Contrato nº {contrato.numero_contrato}</b>, realizou pagamentos no ano '
            f'de <b>{ano}</b>, porém <b>ainda existem prestações pendentes</b> neste '
            f'período, conforme demonstrativo abaixo.'
        )
    else:
        corpo = (
            f'A empresa <b>{imob.nome}</b> DECLARA que o(a) Sr(a). '
            f'<b>{comp.nome}</b>, {doc_label} <b>{doc_comp}</b>, referente ao '
            f'<b>Contrato nº {contrato.numero_contrato}</b>, '
            f'<b>não efetuou pagamentos</b> referentes ao ano de <b>{ano}</b>, '
            f'estando as prestações do período em aberto.'
        )
    story.append(Paragraph(corpo, corpo_style))

    # ── Dados do contrato ─────────────────────────────────────────────────────
    story.append(Spacer(1, 4))
    th_s = _s('Dth', fontSize=8, textColor=CINZA, fontName='Helvetica-Bold')
    td_s = _s('Dtd', fontSize=9, textColor=black, fontName='Helvetica')
    dados_rows = [
        [Paragraph('Contrato nº', th_s),    Paragraph(contrato.numero_contrato, td_s),
         Paragraph('Data do Contrato', th_s), Paragraph(_fmt_data(contrato.data_contrato), td_s)],
        [Paragraph('Comprador', th_s),       Paragraph(comp.nome, td_s),
         Paragraph(f'{doc_label} Comprador', th_s), Paragraph(doc_comp, td_s)],
        [Paragraph('Imóvel', th_s),          Paragraph(imovel_str, td_s),
         Paragraph('Parcelas no Ano', th_s), Paragraph(f'{len(parcelas_ano)} parcela(s)', td_s)],
    ]
    dados_t = Table(dados_rows, colWidths=[3.5*cm, 6.5*cm, 3.5*cm, 3.5*cm])
    dados_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), AZUL_CLARO),
        ('BACKGROUND', (2, 0), (2, -1), AZUL_CLARO),
        ('GRID',       (0, 0), (-1, -1), 0.5, CINZA_LINHA),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]))
    story.append(dados_t)
    story.append(Spacer(1, 12))

    # ── Tabela de parcelas ────────────────────────────────────────────────────
    if parcelas_ano:
        story.append(Paragraph(
            f'Demonstrativo de Prestações — Exercício {ano}',
            _s('DDT', fontSize=10, textColor=AZUL, fontName='Helvetica-Bold', spaceAfter=6)
        ))

        th2 = _s('Dth2', fontSize=8, textColor=white, fontName='Helvetica-Bold',
                 alignment=TA_CENTER)
        tdc = _s('Dtdc', fontSize=8, textColor=black, fontName='Helvetica',
                 alignment=TA_CENTER)
        tdr = _s('Dtdr', fontSize=8, textColor=black, fontName='Helvetica',
                 alignment=TA_RIGHT)
        tdok  = _s('Dok',  fontSize=8, textColor=VERDE,   fontName='Helvetica-Bold',
                   alignment=TA_CENTER)
        tdnok = _s('Dnok', fontSize=8, textColor=VERMELHO, fontName='Helvetica-Bold',
                   alignment=TA_CENTER)

        rows = [[
            Paragraph('Parc.',          th2),
            Paragraph('Vencimento',     th2),
            Paragraph('Data Pgto',      th2),
            Paragraph('Valor Original', th2),
            Paragraph('Valor Pago',     th2),
            Paragraph('Situação',       th2),
        ]]
        total_orig = Decimal('0.00')
        total_pago = Decimal('0.00')
        for p in parcelas_ano:
            v_orig = p.valor_atual or Decimal('0.00')
            v_pago = p.valor_pago  or Decimal('0.00')
            total_orig += v_orig
            if p.pago:
                total_pago += v_pago
                dpg = Paragraph(_fmt_data(p.data_pagamento), tdc) if p.data_pagamento else Paragraph('—', tdc)
                rows.append([
                    Paragraph(str(p.numero_parcela), tdc),
                    Paragraph(_fmt_data(p.data_vencimento), tdc),
                    dpg,
                    Paragraph(_fmt_valor(v_orig), tdr),
                    Paragraph(_fmt_valor(v_pago), tdr),
                    Paragraph('QUITADA', tdok),
                ])
            else:
                rows.append([
                    Paragraph(str(p.numero_parcela), tdc),
                    Paragraph(_fmt_data(p.data_vencimento), tdc),
                    Paragraph('—', tdc),
                    Paragraph(_fmt_valor(v_orig), tdr),
                    Paragraph('—', tdr),
                    Paragraph('PENDENTE', tdnok),
                ])

        tot_r = _s('Dtr', fontSize=8, textColor=AZUL, fontName='Helvetica-Bold',
                   alignment=TA_RIGHT)
        tot_c2 = _s('Dtrc', fontSize=8, textColor=AZUL, fontName='Helvetica-Bold',
                    alignment=TA_CENTER)
        rows.append([
            Paragraph('TOTAL', tot_c2), Paragraph('', tot_c2), Paragraph('', tot_c2),
            Paragraph(_fmt_valor(total_orig), tot_r),
            Paragraph(_fmt_valor(total_pago), tot_r),
            Paragraph('', tot_c2),
        ])

        parc_t = Table(rows, colWidths=[1.5*cm, 3*cm, 3*cm, 3.5*cm, 3.5*cm, 2.5*cm])
        parc_t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  AZUL),
            ('BACKGROUND',    (0, -1), (-1, -1), AZUL_CLARO),
            ('ROWBACKGROUNDS',(0, 1), (-1, -2), [white, HexColor('#f9f9f9')]),
            ('GRID',          (0, 0), (-1, -1), 0.5, CINZA_LINHA),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]))
        story.append(parc_t)
        story.append(Spacer(1, 16))

    # ── Nota legal ────────────────────────────────────────────────────────────
    nota_s = _s('DN', fontSize=8, textColor=CINZA, fontName='Helvetica-Oblique',
                leading=11, spaceAfter=4)
    story.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_LINHA))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Esta declaração é emitida em cumprimento ao Art. 1º da Lei Federal nº 12.007, de 29 de '
        'julho de 2009, que obriga as pessoas jurídicas prestadoras de serviços contínuos a emitir, '
        'anualmente, declaração de quitação de débitos até o dia 30 de abril do ano subsequente ao '
        'de referência.',
        nota_s
    ))
    story.append(Paragraph(
        'Este documento não substitui o recibo de cada pagamento individual.',
        nota_s
    ))
    story.append(Spacer(1, 16))

    # ── Assinaturas ───────────────────────────────────────────────────────────
    story.append(Paragraph(
        f'{local}, {_fmt_data(date.today())}',
        _s('Dloc', fontSize=9, textColor=black, alignment=TA_CENTER,
           fontName='Helvetica', spaceAfter=20)
    ))
    sig_data = [
        [Paragraph('_' * 45, small_c), Paragraph('_' * 45, small_c)],
        [Paragraph(f'<b>DECLARANTE</b><br/>{imob.nome}', small_c),
         Paragraph(f'<b>DECLARATÁRIO</b><br/>{comp.nome}', small_c)],
    ]
    sig_t = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_t.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(sig_t)

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_LINHA))
    story.append(Paragraph(
        f'Documento gerado em {_fmt_data(date.today())} pelo sistema Gestão de Contratos '
        f'— M&amp;S do Brasil LTDA. | Lei 12.007/2009',
        rodape_s
    ))

    doc.build(story)
    return buffer.getvalue()
