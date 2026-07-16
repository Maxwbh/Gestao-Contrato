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
        banco_pagador=f'boleto-api/{origem}', agencia_pagadora='', validar_minimo=False,
    )
    EventoCobrancaApi.objects.create(
        cobranca_id=parcela.cobranca_id or '', event=f'conciliacao.{origem}',
        status_cobranca='liquidado', parcela=parcela, valor=valor,
        status='baixado', payload_raw='',
    )
    logger.info('[BoletoAPI conciliacao/%s] parcela pk=%s baixada', origem, parcela.pk)
    return {'status': 'baixado', 'parcela_id': parcela.pk}
