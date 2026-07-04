"""
D-01: Middleware anti-enumeração.

Conta respostas 403/404 por IP em janela de 5 minutos.
Se o mesmo IP acumular > 30 erros, bloqueia por 1 hora (429).
D-02: Grava cada 403/404 em AcessoNegado (salvo bloqueados já registrados).
"""
import logging
import time

from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger(__name__)

_LIMITE = 30          # respostas de erro por janela
_JANELA_SEG = 300     # 5 minutos
_BAN_SEG = 3600       # 1 hora de ban
_SALVAR_LOG = True    # habilita gravação em AcessoNegado


def _get_ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return xff.split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'unknown')


class AntiEnumeracaoMiddleware:
    """D-01 + D-02."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = _get_ip(request)

        # Verificar se IP está banido
        ban_key = f'antienum_ban:{ip}'
        if cache.get(ban_key):
            return HttpResponse(
                'Muitas tentativas de acesso negado. Tente novamente em 1 hora.',
                status=429,
                content_type='text/plain; charset=utf-8',
            )

        response = self.get_response(request)

        if response.status_code in (403, 404):
            # Contador por janela deslizante (5 min)
            window = int(time.time() // _JANELA_SEG)
            count_key = f'antienum_cnt:{ip}:{window}'
            count = cache.get(count_key, 0) + 1
            cache.set(count_key, count, timeout=_JANELA_SEG + 60)

            if count >= _LIMITE:
                cache.set(ban_key, 1, timeout=_BAN_SEG)
                logger.warning(
                    '[AntiEnum] IP %s banido por 1h — %d erros %d/%d em 5 min',
                    ip, count, response.status_code, _LIMITE,
                )

            # D-02: gravar log assíncrono (fire-and-forget via try/except)
            if _SALVAR_LOG:
                try:
                    from core.models import AcessoNegado
                    usuario = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                    AcessoNegado.objects.create(
                        ip=ip,
                        usuario=usuario,
                        url=request.path[:500],
                        status_code=response.status_code,
                    )
                except Exception:
                    pass  # nunca deixar o log quebrar a resposta

        return response
