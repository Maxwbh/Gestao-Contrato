"""
Geração de PDF de Contrato de Promessa de Compra e Venda.

Gera um documento legal completo com:
  - Cabeçalho da imobiliária/vendedor
  - Qualificação das partes
  - Objeto (imóvel)
  - Cláusulas financeiras (preço, parcelas, correção, juros/multa)
  - Cláusula de rescisão e cessão
  - Tabela de parcelas (primeiras 24)
  - Assinatura das partes e testemunhas
"""
import io
from decimal import Decimal
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import black, white, HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

# ─── Paleta ───────────────────────────────────────────────────────────────────
AZUL       = HexColor('#1a3a5c')
AZUL_CLARO = HexColor('#dce8f5')
CINZA      = HexColor('#555555')
CINZA_LINHA = HexColor('#dddddd')
VERDE      = HexColor('#1b5e20')

PAGE_W, PAGE_H = A4


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fv(v) -> str:
    """Formata valor monetário em R$ 1.234,56"""
    if v is None:
        return 'R$ 0,00'
    return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _fd(d) -> str:
    """Formata data como dd/mm/yyyy"""
    if d is None:
        return '—'
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m/%Y')
    return str(d)


def _extenso_valor(v) -> str:
    """Retorna representação simples do valor para extenso no rodapé."""
    try:
        s = f"{float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {s}"
    except Exception:
        return str(v)


def _styles():
    base = getSampleStyleSheet()
    estilos = {}

    estilos['titulo'] = ParagraphStyle(
        'titulo', parent=base['Title'],
        fontName='Helvetica-Bold', fontSize=14,
        textColor=AZUL, alignment=TA_CENTER, spaceAfter=4,
    )
    estilos['subtitulo'] = ParagraphStyle(
        'subtitulo', parent=base['Normal'],
        fontName='Helvetica', fontSize=10,
        textColor=CINZA, alignment=TA_CENTER, spaceAfter=2,
    )
    estilos['clausula_titulo'] = ParagraphStyle(
        'clausula_titulo', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=AZUL, spaceBefore=10, spaceAfter=4,
    )
    estilos['corpo'] = ParagraphStyle(
        'corpo', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        leading=14, alignment=TA_JUSTIFY, spaceAfter=4,
    )
    estilos['assinatura'] = ParagraphStyle(
        'assinatura', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        alignment=TA_CENTER, spaceBefore=6,
    )
    estilos['rodape'] = ParagraphStyle(
        'rodape', parent=base['Normal'],
        fontName='Helvetica', fontSize=7,
        textColor=CINZA, alignment=TA_CENTER,
    )
    estilos['tabela_header'] = ParagraphStyle(
        'tabela_header', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8,
        textColor=white, alignment=TA_CENTER,
    )
    estilos['tabela_cel'] = ParagraphStyle(
        'tabela_cel', parent=base['Normal'],
        fontName='Helvetica', fontSize=8,
        alignment=TA_CENTER,
    )
    return estilos


# ─── Cabeçalho ────────────────────────────────────────────────────────────────

def _cabecalho(contrato, st) -> list:
    imob = contrato.imobiliaria
    elementos = []

    # Nome da imobiliária
    elementos.append(Paragraph(imob.nome.upper(), st['titulo']))

    # CNPJ / CPF
    doc = getattr(imob, 'documento', None) or getattr(imob, 'cnpj', '') or getattr(imob, 'cpf', '')
    if doc:
        elementos.append(Paragraph(f"CNPJ/CPF: {doc}", st['subtitulo']))

    # Endereço
    if imob.endereco:
        elementos.append(Paragraph(imob.endereco, st['subtitulo']))

    elementos.append(Spacer(1, 8))
    elementos.append(HRFlowable(width='100%', thickness=2, color=AZUL))
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph('CONTRATO DE PROMESSA DE COMPRA E VENDA', st['titulo']))
    elementos.append(HRFlowable(width='100%', thickness=1, color=AZUL_CLARO))
    elementos.append(Spacer(1, 4))

    # Número e data
    linha_num = (
        f"Contrato n.º <b>{contrato.numero_contrato}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Data: <b>{_fd(contrato.data_contrato)}</b>"
    )
    elementos.append(Paragraph(linha_num, st['subtitulo']))
    elementos.append(Spacer(1, 10))
    return elementos


# ─── Cláusula 1 — Das Partes ──────────────────────────────────────────────────

def _clausula_partes(contrato, st) -> list:
    imob = contrato.imobiliaria
    comp = contrato.comprador
    elementos = []

    elementos.append(Paragraph('CLÁUSULA 1ª — DAS PARTES', st['clausula_titulo']))

    # Vendedor / Imobiliária
    doc_imob = getattr(imob, 'documento', None) or ''
    responsavel = getattr(imob, 'responsavel_financeiro', '') or ''
    texto_vendedor = (
        f"<b>VENDEDOR:</b> {imob.nome}"
        f"{', inscrita no CNPJ/CPF n.º ' + doc_imob if doc_imob else ''}"
        f"{', representada por ' + responsavel if responsavel else ''}"
        f"{', com endereço em ' + imob.endereco if imob.endereco else ''}."
    )
    elementos.append(Paragraph(texto_vendedor, st['corpo']))

    # Comprador
    cpf_comp = getattr(comp, 'cpf', '') or ''
    rg_comp = getattr(comp, 'rg', '') or ''
    end_comp = getattr(comp, 'endereco', '') or ''
    estado_civil = comp.get_estado_civil_display() if hasattr(comp, 'get_estado_civil_display') else ''

    texto_comprador = (
        f"<b>COMPRADOR:</b> {comp.nome}"
        f"{', CPF n.º ' + cpf_comp if cpf_comp else ''}"
        f"{', RG n.º ' + rg_comp if rg_comp else ''}"
        f"{', estado civil: ' + estado_civil if estado_civil else ''}"
        f"{', residente e domiciliado em ' + end_comp if end_comp else ''}."
    )
    elementos.append(Paragraph(texto_comprador, st['corpo']))

    # Cônjuge (se houver)
    conjuge_nome = getattr(comp, 'conjuge_nome', '') or ''
    if conjuge_nome:
        conjuge_cpf = getattr(comp, 'conjuge_cpf', '') or ''
        texto_conjuge = (
            f"<b>CÔNJUGE:</b> {conjuge_nome}"
            f"{', CPF n.º ' + conjuge_cpf if conjuge_cpf else ''}."
        )
        elementos.append(Paragraph(texto_conjuge, st['corpo']))

    return elementos


# ─── Cláusula 2 — Do Objeto ───────────────────────────────────────────────────

def _clausula_objeto(contrato, st) -> list:
    imovel = contrato.imovel
    elementos = []

    elementos.append(Paragraph('CLÁUSULA 2ª — DO OBJETO', st['clausula_titulo']))

    tipo = imovel.get_tipo_display() if hasattr(imovel, 'get_tipo_display') else ''
    loteamento = getattr(imovel, 'loteamento', '') or ''
    area = getattr(imovel, 'area', None)
    matricula = getattr(imovel, 'matricula', '') or ''
    inscricao = getattr(imovel, 'inscricao_municipal', '') or ''
    endereco_imovel = getattr(imovel, 'endereco', '') or ''

    texto = (
        f"O presente contrato tem como objeto a promessa de compra e venda do imóvel "
        f"identificado como <b>{imovel.identificacao}</b>"
        f"{', ' + tipo if tipo else ''}"
        f"{', Loteamento ' + loteamento if loteamento else ''}"
        f"{', com área de ' + str(area) + ' m²' if area else ''}"
        f"{', matrícula n.º ' + matricula if matricula else ''}"
        f"{', inscrição municipal ' + inscricao if inscricao else ''}"
        f"{', localizado em ' + endereco_imovel if endereco_imovel else ''}."
    )
    elementos.append(Paragraph(texto, st['corpo']))
    return elementos


# ─── Cláusula 3 — Preço e Forma de Pagamento ─────────────────────────────────

def _clausula_preco(contrato, st) -> list:
    elementos = []
    elementos.append(Paragraph('CLÁUSULA 3ª — DO PREÇO E FORMA DE PAGAMENTO', st['clausula_titulo']))

    amort = contrato.get_tipo_amortizacao_display() if hasattr(contrato, 'get_tipo_amortizacao_display') else 'Tabela Price'

    texto = (
        f"O preço total de venda é de <b>{_fv(contrato.valor_total)}</b>, "
        f"sendo o valor de entrada de <b>{_fv(contrato.valor_entrada)}</b> "
        f"e o saldo financiado de <b>{_fv(contrato.valor_financiado)}</b>, "
        f"dividido em <b>{contrato.numero_parcelas} parcelas mensais</b>, "
        f"com vencimento todo dia <b>{contrato.dia_vencimento}</b> de cada mês, "
        f"a partir de <b>{_fd(contrato.data_primeiro_vencimento)}</b>, "
        f"pelo sistema de amortização <b>{amort}</b>."
    )
    elementos.append(Paragraph(texto, st['corpo']))

    parcela_inicial = getattr(contrato, 'valor_parcela_original', None)
    if parcela_inicial:
        elementos.append(Paragraph(
            f"O valor da parcela inicial é de <b>{_fv(parcela_inicial)}</b>.",
            st['corpo']
        ))

    return elementos


# ─── Cláusula 4 — Correção Monetária ──────────────────────────────────────────

def _clausula_correcao(contrato, st) -> list:
    elementos = []
    elementos.append(Paragraph('CLÁUSULA 4ª — DA CORREÇÃO MONETÁRIA', st['clausula_titulo']))

    indice = contrato.get_tipo_correcao_display() if hasattr(contrato, 'get_tipo_correcao_display') else contrato.tipo_correcao
    prazo = contrato.prazo_reajuste_meses

    texto = (
        f"O saldo devedor e as parcelas mensais serão corrigidos pelo índice "
        f"<b>{indice}</b> a cada <b>{prazo} meses</b>."
    )
    if contrato.reajuste_piso is not None and contrato.reajuste_piso > 0:
        texto += f" O reajuste mínimo aplicado será de {contrato.reajuste_piso}%."
    if contrato.reajuste_teto is not None and contrato.reajuste_teto > 0:
        texto += f" O reajuste máximo aplicado será de {contrato.reajuste_teto}%."
    if contrato.spread_reajuste and contrato.spread_reajuste > 0:
        texto += f" Acrescido de spread de {contrato.spread_reajuste} pontos percentuais."

    elementos.append(Paragraph(texto, st['corpo']))
    return elementos


# ─── Cláusula 5 — Juros e Multa ───────────────────────────────────────────────

def _clausula_encargos(contrato, st) -> list:
    elementos = []
    elementos.append(Paragraph('CLÁUSULA 5ª — DOS ENCARGOS MORATÓRIOS', st['clausula_titulo']))

    texto = (
        f"Em caso de atraso no pagamento das parcelas, incidirão sobre o valor em atraso: "
        f"<b>multa de {contrato.percentual_multa}%</b> e "
        f"<b>juros de mora de {contrato.percentual_juros_mora}% ao mês</b>, "
        f"calculados pro rata die a partir do vencimento."
    )
    elementos.append(Paragraph(texto, st['corpo']))
    return elementos


# ─── Cláusula 6 — Rescisão ────────────────────────────────────────────────────

def _clausula_rescisao(contrato, st) -> list:
    elementos = []
    elementos.append(Paragraph('CLÁUSULA 6ª — DA RESCISÃO CONTRATUAL', st['clausula_titulo']))

    texto = (
        f"Em caso de rescisão por iniciativa do Comprador, serão retidos: "
        f"<b>{contrato.percentual_fruicao}% ao mês de fruição</b> pelo uso do imóvel, "
        f"<b>{contrato.percentual_multa_rescisao_penal}% de cláusula penal</b> e "
        f"<b>{contrato.percentual_multa_rescisao_adm}% de despesas administrativas</b>, "
        f"calculados sobre o valor atualizado do contrato."
    )
    elementos.append(Paragraph(texto, st['corpo']))
    return elementos


# ─── Cláusula 7 — Cessão ──────────────────────────────────────────────────────

def _clausula_cessao(contrato, st) -> list:
    elementos = []
    elementos.append(Paragraph('CLÁUSULA 7ª — DA CESSÃO DE DIREITOS', st['clausula_titulo']))

    texto = (
        f"A cessão de direitos decorrentes deste contrato está sujeita a autorização "
        f"expressa do Vendedor, com cobrança de taxa de <b>{contrato.percentual_cessao}%</b> "
        f"sobre o valor atualizado do contrato."
    )
    elementos.append(Paragraph(texto, st['corpo']))
    return elementos


# ─── Cláusula 8 — Foro ────────────────────────────────────────────────────────

def _clausula_foro(contrato, st) -> list:
    elementos = []
    elementos.append(Paragraph('CLÁUSULA 8ª — DO FORO', st['clausula_titulo']))

    imob = contrato.imobiliaria
    # Tentar extrair cidade do endereço da imobiliária
    cidade = ''
    if imob.endereco:
        partes = imob.endereco.split(',')
        if len(partes) >= 2:
            cidade = partes[-1].strip().split('/')[0].strip()

    texto = (
        f"As partes elegem o foro da comarca de <b>{cidade or '____________'}</b> "
        f"para dirimir quaisquer dúvidas decorrentes do presente contrato, "
        f"com renúncia a qualquer outro, por mais privilegiado que seja."
    )
    elementos.append(Paragraph(texto, st['corpo']))
    return elementos


# ─── Tabela de Parcelas ───────────────────────────────────────────────────────

def _tabela_parcelas(contrato, st) -> list:
    try:
        parcelas = list(
            contrato.parcelas.filter(
                tipo_parcela='NORMAL'
            ).order_by('numero_parcela')[:24]
        )
    except Exception:
        return []

    if not parcelas:
        return []

    elementos = []
    elementos.append(Paragraph('ANEXO I — CRONOGRAMA DE PARCELAS (primeiras 24)', st['clausula_titulo']))

    headers = ['Nº', 'Vencimento', 'Valor Parcela', 'Amortização', 'Juros']
    data = [[Paragraph(h, st['tabela_header']) for h in headers]]

    for p in parcelas:
        amort = getattr(p, 'valor_amortizacao', None)
        juros = getattr(p, 'valor_juros', None)
        data.append([
            Paragraph(str(p.numero_parcela), st['tabela_cel']),
            Paragraph(_fd(p.data_vencimento), st['tabela_cel']),
            Paragraph(_fv(p.valor_atual), st['tabela_cel']),
            Paragraph(_fv(amort) if amort else '—', st['tabela_cel']),
            Paragraph(_fv(juros) if juros else '—', st['tabela_cel']),
        ])

    col_widths = [1.2*cm, 3*cm, 3.5*cm, 3.5*cm, 3.5*cm]
    tabela = Table(data, colWidths=col_widths, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, AZUL_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.4, CINZA_LINHA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elementos.append(tabela)
    if len(parcelas) == 24:
        elementos.append(Paragraph(
            '* Tabela exibe as primeiras 24 parcelas. O cronograma completo é gerado com os boletos.',
            ParagraphStyle('obs', fontName='Helvetica-Oblique', fontSize=7, textColor=CINZA)
        ))
    return elementos


# ─── Assinaturas ──────────────────────────────────────────────────────────────

def _assinaturas(contrato, st) -> list:
    elementos = []
    elementos.append(Spacer(1, 20))
    elementos.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_LINHA))
    elementos.append(Spacer(1, 8))

    imob = contrato.imobiliaria
    comp = contrato.comprador
    cidade_data = f"___________________________, {_fd(date.today())}"
    elementos.append(Paragraph(cidade_data, st['assinatura']))
    elementos.append(Spacer(1, 20))

    # Linha de assinatura — 2 colunas
    sig_data = [
        [
            Paragraph('_' * 40, st['assinatura']),
            Paragraph('_' * 40, st['assinatura']),
        ],
        [
            Paragraph(f"<b>VENDEDOR</b><br/>{imob.nome}", st['assinatura']),
            Paragraph(f"<b>COMPRADOR</b><br/>{comp.nome}", st['assinatura']),
        ],
    ]
    if getattr(comp, 'conjuge_nome', ''):
        sig_data[0].append(Paragraph('_' * 40, st['assinatura']))
        sig_data[1].append(Paragraph(f"<b>CÔNJUGE</b><br/>{comp.conjuge_nome}", st['assinatura']))

    sig_table = Table(sig_data, colWidths=[PAGE_W * 0.42] * len(sig_data[0]))
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementos.append(sig_table)
    elementos.append(Spacer(1, 20))

    # Testemunhas
    elementos.append(Paragraph('Testemunhas:', st['corpo']))
    test_data = [
        [Paragraph('_' * 35, st['assinatura']), Paragraph('_' * 35, st['assinatura'])],
        [Paragraph('Nome: ______________________________', st['assinatura']),
         Paragraph('Nome: ______________________________', st['assinatura'])],
        [Paragraph('CPF: _______________________________', st['assinatura']),
         Paragraph('CPF: _______________________________', st['assinatura'])],
    ]
    test_table = Table(test_data, colWidths=[PAGE_W * 0.42, PAGE_W * 0.42])
    test_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elementos.append(test_table)
    return elementos


# ─── Função Principal ─────────────────────────────────────────────────────────

def gerar_contrato_pdf(contrato) -> bytes:
    """
    Gera o PDF do Contrato de Promessa de Compra e Venda.

    Args:
        contrato: instância de contratos.models.Contrato (com select_related preenchido)
    Returns:
        bytes do PDF gerado
    """
    buffer = io.BytesIO()
    st = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title=f'Contrato {contrato.numero_contrato}',
        author=contrato.imobiliaria.nome,
    )

    story = []
    story += _cabecalho(contrato, st)
    story += _clausula_partes(contrato, st)
    story += _clausula_objeto(contrato, st)
    story += _clausula_preco(contrato, st)
    story += _clausula_correcao(contrato, st)
    story += _clausula_encargos(contrato, st)
    story += _clausula_rescisao(contrato, st)
    story += _clausula_cessao(contrato, st)
    story += _clausula_foro(contrato, st)

    # Observações
    if contrato.observacoes:
        story.append(Paragraph('OBSERVAÇÕES', st['clausula_titulo']))
        story.append(Paragraph(contrato.observacoes, st['corpo']))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width='100%', thickness=1, color=CINZA_LINHA))

    # Tabela de parcelas
    story += _tabela_parcelas(contrato, st)

    # Assinaturas
    story += _assinaturas(contrato, st)

    # Rodapé de geração
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f'Documento gerado em {_fd(date.today())} pelo Sistema de Gestão de Contratos — M&amp;S do Brasil LTDA',
        st['rodape']
    ))

    doc.build(story)
    return buffer.getvalue()
