"""
Conciliação Boleto-API — baixa idempotente a partir do polling de boleto
(Sicoob) e da conciliação de Pix recebidos (rede de segurança do webhook).
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def baixar_por_conciliacao(parcela, valor=None, paid_at=None, origem='polling') -> dict:
    """
    Baixa a parcela a partir de uma conciliação (polling / Pix recebido).
    Idempotente: se já paga, retorna 'duplicado'. Respeita a máquina de estados
    (transiciona para LIQUIDADA) e registra o evento para auditoria.
    """
    from financeiro.models import EventoCobrancaApi, StatusCobranca
    if parcela.pago:
        return {'status': 'duplicado', 'parcela_id': parcela.pk}

    parcela.transicionar_cobranca(StatusCobranca.LIQUIDADA)
    parcela.registrar_pagamento_boleto(
        valor_pago=float(valor if valor is not None
                         else (parcela.valor_boleto or parcela.valor_atual or 0)),
        data_pagamento=paid_at or timezone.now(),
        # banco_pagador é varchar(10): usar o marcador fixo (como na baixa manual);
        # a origem (polling/pix/…) fica registrada no EventoCobrancaApi abaixo.
        banco_pagador='boleto-api', agencia_pagadora='', validar_minimo=False,
    )
    EventoCobrancaApi.objects.create(
        cobranca_id=parcela.cobranca_id or '', event=f'conciliacao.{origem}',
        status_cobranca='liquidado', parcela=parcela, valor=valor,
        status='baixado', payload_raw='',
    )
    logger.info('[BoletoAPI conciliacao/%s] parcela pk=%s baixada', origem, parcela.pk)
    return {'status': 'baixado', 'parcela_id': parcela.pk}


def conciliacao_financeira(imobiliaria, inicio, fim):
    """
    BAPI-32 — cruza os recebíveis do gateway (GET /conciliacao) com as parcelas
    liquidadas no sistema no período, por conta bancária de API da imobiliária.

    Retorna dict com:
      conferidos      — casou por cobranca_id/txid e o valor bate
      divergentes     — casou mas o valor difere (gateway × sistema)
      apenas_gateway  — banco liquidou e o sistema não tem parcela paga casada
      apenas_sistema  — parcela liquidada via API sem recebível no banco
      erros           — contas cuja consulta ao gateway falhou
    """
    from decimal import Decimal, InvalidOperation
    from core.models import ProviderBoleto
    from financeiro.models import Parcela, StatusCobranca
    from financeiro.services.boleto_api_client import BoletoApiClient

    def _dec(v):
        try:
            return Decimal(str(v or 0)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    client = BoletoApiClient()
    itens_gateway = []
    erros = []
    contas = imobiliaria.contas_bancarias.filter(ativo=True).exclude(
        provider=ProviderBoleto.BRCOBRANCA)
    for conta in contas:
        r = client.consultar_conciliacao(
            inicio.isoformat(), fim.isoformat(), conta.tenant_id, conta.provider,
            bapi_token=(conta.bapi_token or None))
        if r.get('sucesso'):
            itens_gateway.extend(r.get('itens') or [])
        else:
            erros.append({'conta': str(conta), 'erro': r.get('erro', '')})

    parcelas = list(
        Parcela.objects.filter(
            contrato__imobiliaria=imobiliaria,
            status_cobranca=StatusCobranca.LIQUIDADA,
            data_pagamento__gte=inicio, data_pagamento__lte=fim,
        ).select_related('contrato')
    )
    por_cobranca = {p.cobranca_id: p for p in parcelas if p.cobranca_id}
    por_txid = {p.pix_txid: p for p in parcelas if p.pix_txid}

    conferidos, divergentes, apenas_gateway = [], [], []
    casadas = set()
    for item in itens_gateway:
        cid = str(item.get('cobranca_id') or item.get('id') or '')
        txid = str(item.get('txid') or '')
        parcela = por_cobranca.get(cid) or por_txid.get(txid)
        valor_gw = _dec(item.get('valor'))
        if not parcela:
            apenas_gateway.append({'cobranca_id': cid, 'txid': txid, 'valor': valor_gw})
            continue
        casadas.add(parcela.pk)
        valor_sys = _dec(parcela.valor_pago or parcela.valor_boleto)
        registro = {'parcela': parcela, 'cobranca_id': cid, 'txid': txid,
                    'valor_gateway': valor_gw, 'valor_sistema': valor_sys}
        (conferidos if valor_gw == valor_sys else divergentes).append(registro)

    apenas_sistema = [p for p in parcelas if p.pk not in casadas]
    return {
        'conferidos': conferidos,
        'divergentes': divergentes,
        'apenas_gateway': apenas_gateway,
        'apenas_sistema': apenas_sistema,
        'erros': erros,
        'total_gateway': len(itens_gateway),
        'total_sistema': len(parcelas),
    }
