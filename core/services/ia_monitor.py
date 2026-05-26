"""
Monitor de uso e custo das APIs de IA.

Registra cada chamada com tokens consumidos e custo estimado em USD.
Falha silenciosamente para nunca interromper o fluxo principal.
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Preço por milhão de tokens (USD) — (input/MTok, output/MTok)
_PRECOS: dict[str, tuple[float, float]] = {
    'claude-haiku-4-5-20251001': (0.80,   4.00),
    'claude-sonnet-4-6':         (3.00,  15.00),
    'claude-opus-4-7':           (15.00, 75.00),
    'gemini-2.0-flash':          (0.0,    0.0),   # free tier
    'gemini-1.5-flash':          (0.075,  0.30),
    'gemini-1.5-pro':            (1.25,   5.00),
}

PROVIDER_ANTHROPIC = 'ANTHROPIC'
PROVIDER_GOOGLE = 'GOOGLE'

OP_IMPORTACAO_PDF   = 'IMPORTACAO_PDF'
OP_CHATBOT_INTENT   = 'CHATBOT_INTENT'
OP_CHATBOT_HUMANIZE = 'CHATBOT_HUMANIZE'


def calcular_custo(modelo: str, tokens_input: int, tokens_output: int) -> Decimal:
    preco_in, preco_out = _PRECOS.get(modelo, (0.0, 0.0))
    custo = (tokens_input * preco_in + tokens_output * preco_out) / 1_000_000
    return Decimal(str(round(custo, 6)))


def registrar(
    *,
    provider: str,
    modelo: str,
    operacao: str,
    tokens_input: int,
    tokens_output: int,
    usuario=None,
    contrato_importacao=None,
) -> None:
    """Persiste um registro de uso de IA. Falha silenciosamente."""
    try:
        from core.models import RegistroUsoIA
        RegistroUsoIA.objects.create(
            provider=provider,
            modelo=modelo,
            operacao=operacao,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            custo_usd=calcular_custo(modelo, tokens_input, tokens_output),
            usuario=usuario,
            contrato_importacao=contrato_importacao,
        )
    except Exception as exc:
        logger.warning('ia_monitor.registrar falhou: %s', exc)
