"""
Acesso aos Parâmetros do Sistema via banco de dados com cache.

Uso:
    from core.parametros import get_param

    host = get_param('EMAIL_HOST', 'localhost')
    debug = get_param('TEST_MODE', False)   # retorna bool tipado
"""
from django.core.cache import cache
from django.conf import settings as django_settings

CACHE_KEY = 'parametros_sistema_all'
CACHE_TTL = 300  # 5 minutos


def get_param(chave, default=None):
    """
    Lê um parâmetro do sistema.
    Prioridade: banco de dados (cache 5 min) → settings.* → default.
    """
    try:
        params = _get_all_cached()
        if chave in params:
            return params[chave].get_valor_tipado()
    except Exception:
        pass
    return getattr(django_settings, chave, default)


def invalidar_cache():
    """Limpa o cache dos parâmetros. Chamar após salvar no admin."""
    cache.delete(CACHE_KEY)


def _get_all_cached():
    cached = cache.get(CACHE_KEY)
    if cached is None:
        from core.models import ParametroSistema
        cached = {p.chave: p for p in ParametroSistema.objects.all()}
        cache.set(CACHE_KEY, cached, CACHE_TTL)
    return cached


def aplicar_em_settings():
    """
    Injeta todos os parâmetros do DB em django.conf.settings.
    Chamado em CoreConfig.ready() para que código legado que lê
    settings.* (inclusive o sistema de e-mail do Django) use os
    valores do banco sem necessitar de alterações.
    """
    import sys
    if 'pytest' in sys.modules:
        return
    try:
        params = _get_all_cached()
        for chave, param in params.items():
            setattr(django_settings, chave, param.get_valor_tipado())
    except Exception:
        pass
