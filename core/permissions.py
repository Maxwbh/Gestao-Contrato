"""
Decoradores e helpers de permissão para o sistema de Gestão de Contratos.

Papéis suportados via AcessoUsuario.pode_editar / pode_excluir:
  - Admin Contabilidade  : is_superuser ou is_staff
  - Admin Imobiliária    : is_staff (escopo limitado à imobiliária)
  - Gerente Imobiliária  : pode_editar=True, pode_excluir=True
  - Operador Imobiliária : pode_editar=True, pode_excluir=False
  - Operador Relatórios  : pode_editar=False, pode_excluir=False (somente leitura)

Rate limiting (Section 6 P3):
  - APIs de tarefa       : 30 req/min por IP
  - API de schema/docs   : 60 req/min por IP
  - Portal comprador     : 10 req/min por usuário
"""
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
import time
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITING — cache-based, sem dependência externa
# =============================================================================

def rate_limit(requests_per_minute, key_fn=None):
    """
    Decorator de rate limiting baseado no cache do Django.

    Args:
        requests_per_minute: limite de requisições por janela de 60s
        key_fn: função (request) → str para gerar a chave de cache.
                Por padrão usa o IP do cliente.

    Retorna 429 JSON se o limite for excedido.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if key_fn:
                key_base = key_fn(request)
            else:
                # IP real considerando proxy reverso
                ip = (
                    request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or request.META.get('REMOTE_ADDR', 'unknown')
                )
                key_base = ip

            # Janela de 60 segundos — chave inclui minuto atual para auto-reset
            window = int(time.time() // 60)
            cache_key = f'ratelimit:{view_func.__name__}:{key_base}:{window}'

            count = cache.get(cache_key, 0)
            if count >= requests_per_minute:
                logger.warning(
                    'Rate limit atingido: view=%s key=%s count=%d',
                    view_func.__name__, key_base, count
                )
                return JsonResponse(
                    {
                        'erro': 'Muitas requisições. Tente novamente em breve.',
                        'retry_after': 60,
                    },
                    status=429,
                )

            # Incrementa contador; TTL de 90s para cobrir bordas de janela
            cache.set(cache_key, count + 1, timeout=90)
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def rate_limit_by_user(requests_per_minute):
    """Rate limit por usuário autenticado (usa user.pk como chave)."""
    def key_fn(request):
        if request.user.is_authenticated:
            return f'user:{request.user.pk}'
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR', 'unknown')
        )
        return f'anon:{ip}'
    return rate_limit(requests_per_minute, key_fn=key_fn)


# =============================================================================
# DECORADORES DE PAPEL / PERMISSÃO
# =============================================================================

def requer_permissao_total(view_func):
    """
    Exige que o usuário seja superuser ou staff (Admin Contabilidade).
    Redireciona para login se não autenticado; retorna 403 se não autorizado.
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from core.models import usuario_tem_permissao_total
        if not usuario_tem_permissao_total(request.user):
            return HttpResponseForbidden(
                'Acesso negado. Esta operação requer permissão de administrador.'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def requer_pode_editar(imobiliaria_pk_kwarg='imobiliaria_pk'):
    """
    Exige que o usuário tenha pode_editar=True para a imobiliária
    identificada por `imobiliaria_pk_kwarg` na URL.

    Uso:
        @requer_pode_editar('pk')
        def minha_view(request, pk):
            ...
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from core.models import usuario_pode_editar, Imobiliaria, usuario_tem_permissao_total
            if usuario_tem_permissao_total(request.user):
                return view_func(request, *args, **kwargs)
            imobiliaria_pk = kwargs.get(imobiliaria_pk_kwarg)
            if imobiliaria_pk is None:
                imobiliaria_pk = request.POST.get(imobiliaria_pk_kwarg) or request.GET.get(imobiliaria_pk_kwarg)
            try:
                imobiliaria = Imobiliaria.objects.get(pk=imobiliaria_pk, ativo=True)
            except (Imobiliaria.DoesNotExist, ValueError, TypeError):
                return HttpResponseForbidden('Imobiliária não encontrada ou sem acesso.')
            if not usuario_pode_editar(request.user, imobiliaria):
                return HttpResponseForbidden(
                    'Acesso negado. Você não tem permissão para editar registros desta imobiliária.'
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def requer_pode_excluir(imobiliaria_pk_kwarg='imobiliaria_pk'):
    """
    Exige que o usuário tenha pode_excluir=True para a imobiliária.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from core.models import usuario_pode_excluir, Imobiliaria, usuario_tem_permissao_total
            if usuario_tem_permissao_total(request.user):
                return view_func(request, *args, **kwargs)
            imobiliaria_pk = kwargs.get(imobiliaria_pk_kwarg)
            try:
                imobiliaria = Imobiliaria.objects.get(pk=imobiliaria_pk, ativo=True)
            except (Imobiliaria.DoesNotExist, ValueError, TypeError):
                return HttpResponseForbidden('Imobiliária não encontrada ou sem acesso.')
            if not usuario_pode_excluir(request.user, imobiliaria):
                return HttpResponseForbidden(
                    'Acesso negado. Você não tem permissão para excluir registros desta imobiliária.'
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def requer_acesso_imobiliaria(imobiliaria_pk_kwarg='pk'):
    """
    Exige acesso básico (qualquer nível) à imobiliária.
    Bloqueia usuários sem AcessoUsuario para a imobiliária.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from core.models import usuario_tem_acesso_imobiliaria, Imobiliaria, usuario_tem_permissao_total
            if usuario_tem_permissao_total(request.user):
                return view_func(request, *args, **kwargs)
            imobiliaria_pk = kwargs.get(imobiliaria_pk_kwarg)
            try:
                imobiliaria = Imobiliaria.objects.get(pk=imobiliaria_pk, ativo=True)
            except (Imobiliaria.DoesNotExist, ValueError, TypeError):
                return HttpResponseForbidden('Imobiliária não encontrada ou sem acesso.')
            if not usuario_tem_acesso_imobiliaria(request.user, imobiliaria):
                return HttpResponseForbidden(
                    'Acesso negado. Você não tem acesso a esta imobiliária.'
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# LIMITES PRÉ-CONFIGURADOS (prontos para usar nas views)
# =============================================================================

# 30 req/min por IP — para APIs de tarefas/cron
task_api_rate_limit = rate_limit(30)

# 60 req/min por IP — para APIs de leitura pública
public_api_rate_limit = rate_limit(60)

# 10 req/min por usuário — para ações do portal comprador
portal_rate_limit = rate_limit_by_user(10)

# 5 req/min por IP — para ações de geração de boletos em massa
boleto_lote_rate_limit = rate_limit(5)
