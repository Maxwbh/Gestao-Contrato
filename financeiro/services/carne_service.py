"""
Serviço de geração de Carnê em PDF via BRCobrança API (POST /api/boleto/multi).
Toda a geração é delegada à API. Não existe fallback local.
"""
import logging

logger = logging.getLogger(__name__)


def gerar_carne_pdf(parcelas, contrato) -> bytes:
    """
    Gera carnê PDF: contas com provedor de API (C6/Sicoob) usam o gateway
    Boleto-API (POST /carne — cobranças REGISTRADAS, BAPI-37); as demais
    seguem o BRCobrança POST /api/boleto/multi.
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

    if getattr(conta, 'provider', 'brcobranca') not in ('', 'brcobranca'):
        return _gerar_carne_via_boleto_api(parcelas_list, contrato, conta)

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


def _gerar_carne_via_boleto_api(parcelas_list, contrato, conta) -> bytes:
    """
    BAPI-37 — carnê registrado via gateway (POST /carne): registra as N
    cobranças no banco e devolve o PDF; persiste cobranca_id/linha digitável/
    status REGISTRADA em cada parcela (mesma ordem do envio).
    """
    from financeiro.models import StatusCobranca
    from financeiro.services.boleto_api_client import BoletoApiClient

    comprador = contrato.comprador
    documento = (getattr(comprador, 'cnpj', '') or getattr(comprador, 'cpf', '') or '')
    documento = documento.replace('.', '').replace('/', '').replace('-', '')

    payload_parcelas = [{
        'valor': float(p.valor_boleto or p.valor_atual or 0),
        'vencimento': p.data_vencimento.isoformat() if p.data_vencimento else '',
        'seu_numero': str(p.numero_documento
                          or f'{contrato.numero_contrato}/{p.numero_parcela}'),
        'pagador': {'nome': comprador.nome[:60], 'documento': documento},
    } for p in parcelas_list]

    r = BoletoApiClient().gerar_carne(
        conta.tenant_id, conta.provider,
        getattr(conta, 'account_config', None) or {}, conta.banco,
        payload_parcelas, bapi_token=(conta.bapi_token or None))
    if not r.get('sucesso'):
        erro = r.get('erro', 'erro desconhecido')
        logger.error('[Carnê] Boleto-API falhou para contrato %s — %s', contrato.pk, erro)
        raise RuntimeError(f'Não foi possível gerar o carnê via Boleto-API: {erro}')

    # Persiste o rastreio da cobrança registrada em cada parcela (ordem do envio)
    for parcela, cob in zip(parcelas_list, r.get('cobrancas') or []):
        parcela.conta_bancaria = conta
        parcela.cobranca_id = cob.get('cobranca_id', '') or parcela.cobranca_id
        parcela.linha_digitavel = cob.get('linha_digitavel', '') or parcela.linha_digitavel
        parcela.codigo_barras = cob.get('codigo_barras', '') or parcela.codigo_barras
        parcela.nosso_numero = cob.get('nosso_numero', '') or parcela.nosso_numero
        parcela.registrar_emissao(provider=conta.provider, metodo='carne',
                                  status=StatusCobranca.REGISTRADA,
                                  ext_ref=cob.get('ext_ref', '') or None)
        parcela.save()

    return r.get('carne_pdf_content') or b''


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
