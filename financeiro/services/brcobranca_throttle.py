"""
Throttle compartilhado da BRCobrança (cooldown boletos → remessa).

Problema: no ciclo de cobrança a geração de boletos (HU-24, Passo 1) dispara
dezenas de chamadas individuais à API BRCobrança e, em seguida, a remessa
(HU-23, Passo 2) é acionada — frequentemente em um request HTTP distinto e
próximo no tempo. No Render free tier isso esgota o rate limit e a remessa
recebe 429 logo na primeira tentativa.

Como os dois passos rodam em requests separados, um cooldown local em uma
única view não resolve. Aqui mantemos um MARCADOR DE USO compartilhado via
cache: a geração de boletos registra o instante do último burst e a remessa
aguarda o tempo restante do cooldown antes do primeiro POST — dando à cota
do rate limit tempo para se recuperar.

Desenvolvedor: Maxwell da Silva Oliveira
"""
import time
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Chave de cache do instante (epoch) do último uso da API por geração de boletos.
_CACHE_KEY = 'brcobranca:ultimo_uso_boleto'
# Janela em que o marcador continua válido (deve cobrir folgadamente o cooldown).
_CACHE_TIMEOUT = 600


def _cooldown_segundos() -> float:
    """Cooldown configurável boletos → remessa (s). 0 desativa."""
    try:
        return float(getattr(settings, 'BRCOBRANCA_REMESSA_COOLDOWN_S', 5))
    except (TypeError, ValueError):
        return 5.0


def marcar_uso_boleto() -> None:
    """Registra o instante atual como último uso da API por geração de boletos."""
    try:
        cache.set(_CACHE_KEY, time.time(), timeout=_CACHE_TIMEOUT)
    except Exception:
        # Cache indisponível não pode quebrar a geração — apenas degrada o cooldown.
        logger.debug('brcobranca_throttle: falha ao marcar uso (cache indisponível)')


def aguardar_cooldown_remessa() -> float:
    """
    Aguarda o tempo restante do cooldown desde o último burst de boletos.

    Retorna o número de segundos efetivamente aguardados (0 se não houve espera).
    Síncrono e curto por definição — coerente com o backoff que a remessa já
    aplica em 429.
    """
    cooldown = _cooldown_segundos()
    if cooldown <= 0:
        return 0.0
    try:
        ultimo = cache.get(_CACHE_KEY)
    except Exception:
        return 0.0
    if not ultimo:
        return 0.0
    restante = cooldown - (time.time() - ultimo)
    if restante <= 0:
        return 0.0
    restante = min(restante, cooldown)  # blinda contra relógio/cache inconsistente
    logger.info(
        '[Remessa] cooldown pós-geração de boletos: aguardando %.1fs antes do POST',
        restante,
    )
    time.sleep(restante)
    return restante
