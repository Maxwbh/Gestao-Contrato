"""
Throttle compartilhado da BRCobrança — cooldown boletos → remessa.

Cobre o marcador de uso via cache e o cálculo do tempo restante de cooldown,
sem dormir de verdade (time.sleep é mockado).

Desenvolvedor: Maxwell da Silva Oliveira
"""
import pytest
from unittest.mock import patch

from django.core.cache import cache

from financeiro.services import brcobranca_throttle as throttle


@pytest.fixture(autouse=True)
def _limpar_cache():
    cache.delete(throttle._CACHE_KEY)
    yield
    cache.delete(throttle._CACHE_KEY)


def test_sem_marcador_nao_aguarda(settings):
    settings.BRCOBRANCA_REMESSA_COOLDOWN_S = 5
    with patch.object(throttle.time, 'sleep') as mock_sleep:
        aguardado = throttle.aguardar_cooldown_remessa()
    assert aguardado == 0.0
    mock_sleep.assert_not_called()


def test_cooldown_zero_desativa(settings):
    settings.BRCOBRANCA_REMESSA_COOLDOWN_S = 0
    throttle.marcar_uso_boleto()
    with patch.object(throttle.time, 'sleep') as mock_sleep:
        aguardado = throttle.aguardar_cooldown_remessa()
    assert aguardado == 0.0
    mock_sleep.assert_not_called()


def test_aguarda_tempo_restante(settings):
    settings.BRCOBRANCA_REMESSA_COOLDOWN_S = 5
    # Marca o uso "há 2s" → restante esperado ≈ 3s
    with patch.object(throttle.time, 'time', return_value=1000.0):
        throttle.marcar_uso_boleto()
    with patch.object(throttle.time, 'time', return_value=1002.0), \
         patch.object(throttle.time, 'sleep') as mock_sleep:
        aguardado = throttle.aguardar_cooldown_remessa()
    assert mock_sleep.call_count == 1
    assert 2.9 <= aguardado <= 3.1


def test_burst_antigo_nao_aguarda(settings):
    settings.BRCOBRANCA_REMESSA_COOLDOWN_S = 5
    # Marca o uso "há 10s" → já passou o cooldown
    with patch.object(throttle.time, 'time', return_value=1000.0):
        throttle.marcar_uso_boleto()
    with patch.object(throttle.time, 'time', return_value=1010.0), \
         patch.object(throttle.time, 'sleep') as mock_sleep:
        aguardado = throttle.aguardar_cooldown_remessa()
    assert aguardado == 0.0
    mock_sleep.assert_not_called()


def test_espera_limitada_ao_cooldown(settings):
    """Relógio/cache inconsistente não pode fazer a remessa dormir além do cooldown."""
    settings.BRCOBRANCA_REMESSA_COOLDOWN_S = 5
    # Marcador "no futuro" → restante calculado > cooldown; deve ser limitado.
    with patch.object(throttle.time, 'time', return_value=2000.0):
        throttle.marcar_uso_boleto()
    with patch.object(throttle.time, 'time', return_value=1000.0), \
         patch.object(throttle.time, 'sleep') as mock_sleep:
        aguardado = throttle.aguardar_cooldown_remessa()
    assert aguardado <= 5.0
    mock_sleep.assert_called_once()
