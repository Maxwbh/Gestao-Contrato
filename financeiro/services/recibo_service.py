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
from reportlab.lib.colors import white, HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# ─── Cores ────────────────────────────────────────────────────────────────────
AZUL = HexColor('#1a3a5c')
AZUL_CLARO = HexColor('#e8f0f8')
VERDE = HexColor('#1b5e20')
CINZA = HexColor('#616161')
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
    bold = ParagraphStyle('bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=9)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=CINZA)
    centro = ParagraphStyle('centro', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    right = ParagraphStyle('right', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)

    story = []

    # ─── Cabeçalho ────────────────────────────────────────────────────────────
    imob = contrato.imobiliaria
    nome_empresa = imob.nome if imob else 'Imobiliária'
    cnpj_empresa = getattr(imob, 'cnpj', '') or ''
    end_empresa = getattr(imob, 'endereco', '') or ''

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
    comprador = contrato.comprador
    nome_comp = comprador.nome if comprador else '—'
    doc_comp = ''
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
    total_original = Decimal('0')
    total_desconto = Decimal('0')
    total_pago = Decimal('0')

    for h in historicos:
        parcela = h.parcela
        vo = h.valor_parcela or Decimal('0')
        vd = h.valor_desconto or Decimal('0')
        vp = h.valor_pago or Decimal('0')
        total_original += vo
        total_desconto += vd
        total_pago += vp

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
