"""
Serviço de geração de Carnê em PDF via BRCobrança API (POST /api/boleto/multi).
Toda a geração é delegada à API. Não existe fallback local.
"""
import logging

logger = logging.getLogger(__name__)


def gerar_carne_pdf(parcelas, contrato) -> bytes:
    """
    Gera carnê PDF via BRCobrança POST /api/boleto/multi.
    Levanta RuntimeError se a API estiver indisponível ou retornar erro.
    """
    from financeiro.services.boleto_service import BoletoService

    parcelas_list = list(parcelas)
    if not parcelas_list:
        raise ValueError('Nenhuma parcela informada para gerar o carnê')

    imob = getattr(contrato, 'imobiliaria', None)
    conta = imob.contas_bancarias.filter(ativo=True, principal=True).first() if imob else None
    if not conta:
        raise RuntimeError(
            f'Sem conta bancária ativa para o contrato {contrato.pk}. '
            'Configure uma conta bancária principal para a imobiliária.'
        )

    service = BoletoService()
    resultado = service.gerar_carne(parcelas_list, conta)
    if resultado.get('sucesso'):
        return resultado['pdf_content']

    erro = resultado.get('erro', 'erro desconhecido')
    logger.error(
        "[Carnê] BRCobrança falhou para contrato %s — %s\n"
        "  → Verifique se a API BRCobrança está rodando.",
        contrato.pk, erro,
    )
    raise RuntimeError(
        f'Não foi possível gerar o carnê via API BRCobrança: {erro}. '
        'Verifique os logs do servidor.'
    )


def gerar_carne_multiplos_contratos(contratos_parcelas: list) -> bytes:
    """
    Gera carnê PDF consolidado para múltiplos contratos.
    Cada contrato é processado via BRCobrança; os PDFs são concatenados com pypdf.
    """
    from pypdf import PdfWriter, PdfReader
    import io

    writer = PdfWriter()
    for item in contratos_parcelas:
        contrato = item['contrato']
        parcelas_list = list(item['parcelas'])
        if not parcelas_list:
            continue
        pdf_bytes = gerar_carne_pdf(parcelas_list, contrato)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
