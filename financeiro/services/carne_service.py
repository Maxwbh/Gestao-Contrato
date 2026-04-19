"""
Serviço de geração de Carnê em PDF.

Estratégia:
  1. Tenta gerar via BRCobrança POST /api/boleto/multi (PDF nativo do banco, com código de barras real)
  2. Fallback: gera PDF local com reportlab (sem código de barras, mas com linha digitável)

O fallback é usado quando:
  - BRCobrança não está disponível
  - Parcelas ainda não têm boleto gerado (sem nosso_número)
  - Conta bancária não está configurada

Usa reportlab (disponível no projeto) para o fallback.
"""
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, HexColor
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de layout do carnê (fallback ReportLab)
# ---------------------------------------------------------------------------
CINZA_CLARO = HexColor('#f5f5f5')
CINZA_BORDA = HexColor('#cccccc')
AZUL_TITULO = HexColor('#1a3a5c')

SLIP_HEIGHT = 9 * cm
PAGE_W, PAGE_H = A4
MARGIN_X = 1.5 * cm
SLIP_W = PAGE_W - 2 * MARGIN_X


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_valor(valor) -> str:
    if valor is None:
        return 'R$ 0,00'
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_data(d) -> str:
    if d is None:
        return '—'
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m/%Y')
    return str(d)


# ---------------------------------------------------------------------------
# Geração via BRCobrança (primária)
# ---------------------------------------------------------------------------

def _gerar_carne_brcobranca(parcelas, contrato):
    """
    Tenta gerar o carnê via BRCobrança POST /api/boleto/multi.
    Retorna bytes do PDF ou None em caso de falha.
    """
    try:
        from financeiro.services.boleto_service import BoletoService

        # Determinar conta bancária
        conta = None
        imob = getattr(contrato, 'imobiliaria', None)
        if imob:
            conta = imob.contas_bancarias.filter(ativo=True, principal=True).first()
        if not conta:
            logger.warning('gerar_carne_brcobranca: sem conta bancária ativa para contrato %s', contrato.pk)
            return None

        service = BoletoService()
        resultado = service.gerar_carne(list(parcelas), conta)
        if resultado.get('sucesso'):
            return resultado['pdf_content']

        logger.warning('gerar_carne_brcobranca: %s', resultado.get('erro', 'erro desconhecido'))
    except Exception as e:
        logger.warning('gerar_carne_brcobranca: exceção — %s', e)
    return None


# ---------------------------------------------------------------------------
# Fallback ReportLab
# ---------------------------------------------------------------------------

def _draw_slip(c: canvas.Canvas, x: float, y: float, parcela, contrato) -> None:
    """Desenha 1 slip de boleto no canvas do ReportLab."""
    w = SLIP_W
    h = SLIP_HEIGHT

    # Fundo e borda
    c.setFillColor(white)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setStrokeColor(CINZA_BORDA)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, fill=0, stroke=1)

    # Linha tracejada de corte no topo
    c.setDash(4, 3)
    c.line(x, y + h, x + w, y + h)
    c.setDash()

    # --- Cabeçalho ---
    header_h = 1.0 * cm
    c.setFillColor(AZUL_TITULO)
    c.rect(x, y + h - header_h, w, header_h, fill=1, stroke=0)

    conta = None
    imob = getattr(contrato, 'imobiliaria', None)
    if imob:
        try:
            conta = imob.contas_bancarias.filter(ativo=True, principal=True).first()
        except Exception:
            pass

    bancos = {
        '001': 'Banco do Brasil', '237': 'Bradesco', '341': 'Itaú',
        '033': 'Santander', '104': 'Caixa Econômica', '748': 'Sicredi', '756': 'Sicoob',
    }
    banco_txt = bancos.get(getattr(conta, 'banco', ''), '') if conta else ''
    cedente_txt = banco_txt or getattr(getattr(contrato, 'imobiliaria', None), 'nome', 'Cedente')

    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 0.3 * cm, y + h - 0.7 * cm, cedente_txt)

    c.setFont('Helvetica', 8)
    c.drawRightString(
        x + w - 0.3 * cm, y + h - 0.7 * cm,
        f"Contrato {contrato.numero_contrato}  |  Parcela {parcela.numero_parcela}/{contrato.numero_parcelas}"
    )

    # --- Faixa nosso número / vencimento / valor ---
    y_mid = y + h - header_h - 1.5 * cm
    c.setFillColor(CINZA_CLARO)
    c.rect(x, y_mid, w, 1.4 * cm, fill=1, stroke=0)

    col1 = x + 0.3 * cm
    col2 = x + w * 0.42
    col3 = x + w * 0.72

    c.setFillColor(AZUL_TITULO)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(col1, y_mid + 0.9 * cm, 'Nosso Número')
    c.drawString(col2, y_mid + 0.9 * cm, 'Vencimento')
    c.drawString(col3, y_mid + 0.9 * cm, 'Valor do Documento')

    c.setFillColor(black)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(col1, y_mid + 0.25 * cm, parcela.nosso_numero or '—')
    c.drawString(col2, y_mid + 0.25 * cm, _fmt_data(parcela.data_vencimento))
    c.drawString(col3, y_mid + 0.25 * cm, _fmt_valor(parcela.valor_atual))

    # --- Sacado ---
    y_sacado = y_mid - 0.1 * cm
    c.setFillColor(black)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(col1, y_sacado - 0.5 * cm, 'Sacado:')
    comprador = getattr(contrato, 'comprador', None)
    sacado_nome = getattr(comprador, 'nome', '') if comprador else ''
    sacado_cpf = getattr(comprador, 'cpf', '') if comprador else ''
    imovel_id = getattr(getattr(contrato, 'imovel', None), 'identificacao', '')
    c.setFont('Helvetica', 8)
    c.drawString(col1 + 1.5 * cm, y_sacado - 0.5 * cm, f"{sacado_nome}  CPF: {sacado_cpf}")
    c.setFont('Helvetica', 7)
    c.drawString(col1, y_sacado - 0.9 * cm,
                 f"Imóvel: {imovel_id}  |  Juros mora: {contrato.percentual_juros_mora}% a.m.  "
                 f"|  Multa: {contrato.percentual_multa}%")

    # --- Linha digitável ---
    y_ld = y + 1.0 * cm
    linha = parcela.linha_digitavel or '(gere o boleto para obter a linha digitável)'
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(AZUL_TITULO)
    c.drawString(col1, y_ld + 0.5 * cm, 'Linha Digitável:')
    c.setFont('Courier-Bold', 9)
    c.setFillColor(black)
    c.drawString(col1, y_ld + 0.05 * cm, linha)

    c.setFont('Helvetica', 6)
    c.setFillColor(HexColor('#666666'))
    c.drawString(col1, y + 0.25 * cm,
                 f"Após o vencimento: multa {contrato.percentual_multa}% + "
                 f"juros {contrato.percentual_juros_mora}% a.m.")


def _gerar_carne_reportlab(parcelas_list, contrato) -> bytes:
    """Gera carnê PDF usando ReportLab (fallback sem código de barras)."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Carnê — Contrato {contrato.numero_contrato}")
    c.setAuthor('Gestão de Contratos')

    slips_per_page = max(1, int(PAGE_H // SLIP_HEIGHT))

    for i, parcela in enumerate(parcelas_list):
        page_pos = i % slips_per_page
        y_offset = PAGE_H - (page_pos + 1) * SLIP_HEIGHT
        if y_offset < 0:
            if page_pos > 0:
                c.showPage()
            y_offset = PAGE_H - SLIP_HEIGHT
        _draw_slip(c, MARGIN_X, y_offset, parcela, contrato)
        if (i + 1) % slips_per_page == 0 and i < len(parcelas_list) - 1:
            c.showPage()

    c.save()
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def gerar_carne_pdf(parcelas, contrato, usar_brcobranca: bool = True) -> bytes:
    """
    Gera carnê PDF para um contrato.

    Tenta BRCobrança (POST /api/boleto/multi) primeiro.
    Se falhar ou `usar_brcobranca=False`, usa ReportLab como fallback.

    Args:
        parcelas: QuerySet ou lista de Parcela
        contrato: instância de Contrato
        usar_brcobranca: se True (padrão), tenta BRCobrança primeiro

    Returns:
        bytes — conteúdo do PDF
    """
    parcelas_list = list(parcelas)
    if not parcelas_list:
        raise ValueError('Nenhuma parcela informada para gerar o carnê')

    if usar_brcobranca:
        pdf = _gerar_carne_brcobranca(parcelas_list, contrato)
        if pdf:
            return pdf
        logger.info('gerar_carne_pdf: BRCobrança indisponível, usando fallback ReportLab')

    return _gerar_carne_reportlab(parcelas_list, contrato)


def gerar_carne_multiplos_contratos(contratos_parcelas: list, usar_brcobranca: bool = True) -> bytes:
    """
    Gera carnê PDF consolidado para múltiplos contratos.

    Para cada contrato tenta BRCobrança; concatena os PDFs.
    Usa ReportLab para contratos onde BRCobrança falhou.

    Args:
        contratos_parcelas: lista de dicts {'contrato': <Contrato>, 'parcelas': QuerySet/list}
        usar_brcobranca: se True (padrão), tenta BRCobrança para cada contrato

    Returns:
        bytes — PDF único com todos os carnês
    """
    try:
        import pypdf  # noqa: F401
        _use_pypdf = True
    except ImportError:
        _use_pypdf = False

    if _use_pypdf:
        return _gerar_carne_multiplos_pypdf(contratos_parcelas, usar_brcobranca)
    else:
        return _gerar_carne_multiplos_reportlab(contratos_parcelas, usar_brcobranca)


def _gerar_carne_multiplos_pypdf(contratos_parcelas, usar_brcobranca):
    """Gera PDFs individuais e concatena via pypdf."""
    from pypdf import PdfWriter
    import io as _io
    writer = PdfWriter()
    for item in contratos_parcelas:
        contrato = item['contrato']
        parcelas = item['parcelas']
        parcelas_list = list(parcelas)
        if not parcelas_list:
            continue
        pdf_bytes = gerar_carne_pdf(parcelas_list, contrato, usar_brcobranca)
        reader = __import__('pypdf', fromlist=['PdfReader']).PdfReader(_io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    buf = _io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _gerar_carne_multiplos_reportlab(contratos_parcelas, usar_brcobranca):
    """Gera PDF único com slips de todos os contratos via ReportLab."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle('Carnês — Múltiplos Contratos')

    slips_per_page = max(1, int(PAGE_H // SLIP_HEIGHT))
    first_page = True

    for item in contratos_parcelas:
        contrato = item['contrato']
        parcelas_list = list(item['parcelas'])
        if not parcelas_list:
            continue

        # Tenta BRCobrança; se retornar, não podemos mesclar facilmente sem pypdf
        # Então apenas usa ReportLab para todos
        if not first_page:
            c.showPage()
        first_page = False

        for i, parcela in enumerate(parcelas_list):
            page_pos = i % slips_per_page
            y_offset = PAGE_H - (page_pos + 1) * SLIP_HEIGHT
            if y_offset < 0:
                if page_pos > 0:
                    c.showPage()
                y_offset = PAGE_H - SLIP_HEIGHT
            _draw_slip(c, MARGIN_X, y_offset, parcela, contrato)
            if (i + 1) % slips_per_page == 0 and i < len(parcelas_list) - 1:
                c.showPage()

    c.save()
    return buffer.getvalue()
