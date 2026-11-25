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


class TrocaSenhaObrigatoriaMiddleware:
    """
    HU-28.2: quando o usuário foi criado com senha inicial pelo gestor, obriga
    a troca no primeiro acesso — redireciona para a tela de troca de senha até
    que a flag `PerfilUsuario.deve_trocar_senha` seja limpa.
    """
    # Caminhos liberados mesmo com a flag ligada (senão o usuário fica preso).
    _ISENTOS = ('/accounts/alterar-senha/', '/accounts/logout/', '/accounts/login/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            path = request.path
            isento = (path.startswith(self._ISENTOS)
                      or path.startswith('/static/') or path.startswith('/media/'))
            if not isento:
                perfil = getattr(user, 'perfil', None)
                if perfil is not None and perfil.deve_trocar_senha:
                    from django.shortcuts import redirect
                    from django.contrib import messages
                    messages.info(request, 'Defina uma nova senha para continuar.')
                    return redirect('accounts:alterar_senha')
        return self.get_response(request)


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


class IsolamentoAcessoMiddleware:
    """
    Defesa em profundidade para o isolamento de acesso (HU-21 / HU-28):

    1. Comprador do portal (usuário com `acesso_comprador`, sem perfil interno)
       só navega em /portal/ e nos links públicos — nunca nas telas/APIs da
       operação ("os dois mundos nunca se cruzam").
    2. Usuário interno só alcança objetos (contrato, parcela, reajuste, remessa,
       retorno, conta, imobiliária…) das imobiliárias a que tem acesso, mesmo
       quando a view esquece de chamar `verificar_acesso_tenant`.

    O alvo é resolvido pelos parâmetros da rota; objeto inexistente segue para
    a view (que responde 404 normalmente).
    """
    _LIVRE_COMPRADOR = (
        '/portal/', '/b/', '/static/', '/media/', '/accounts/logout/',
        '/accounts/alterar-senha/', '/notificacoes/track/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and self._e_somente_comprador(user):
            path = request.path
            if not path.startswith(self._LIVRE_COMPRADOR):
                from django.http import JsonResponse
                from django.shortcuts import redirect
                if request.method != 'GET' or '/api/' in path:
                    return JsonResponse(
                        {'sucesso': False, 'erro': 'Acesso restrito ao portal do comprador.'},
                        status=403,
                    )
                return redirect('portal_comprador:dashboard')
        return self.get_response(request)

    @staticmethod
    def _e_somente_comprador(user) -> bool:
        if user.is_superuser or user.is_staff:
            return False
        if not hasattr(user, 'acesso_comprador'):
            return False
        from core.models import AcessoUsuario
        return not AcessoUsuario.objects.filter(usuario=user).exists()

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated or not view_kwargs:
            return None
        from core.models import usuario_tem_permissao_total, usuario_tem_acesso_imobiliaria
        if usuario_tem_permissao_total(user):
            return None
        match = getattr(request, 'resolver_match', None)
        if match is None or match.namespace not in ('financeiro', 'contratos', 'core'):
            return None
        try:
            imobiliaria = self._imobiliaria_do_alvo(match.namespace, match.route or '', view_kwargs)
        except Exception:  # resolução é best-effort — a view continua valendo
            logger.exception('IsolamentoAcesso: falha ao resolver o alvo de %s', request.path)
            return None
        if imobiliaria is not None and not usuario_tem_acesso_imobiliaria(user, imobiliaria):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return None

    @staticmethod
    def _imobiliaria_do_alvo(namespace, route, kw):
        from core.hashids_utils import decode_id
        from core.models import Imobiliaria, ContaBancaria

        def _um(qs, pk, caminho):
            if pk is None:
                return None
            obj = qs.filter(pk=pk).select_related(caminho).first()
            if obj is None:
                return None
            for attr in caminho.split('__'):
                obj = getattr(obj, attr, None)
                if obj is None:
                    return None
            return obj

        if 'imobiliaria_id' in kw:
            return Imobiliaria.objects.filter(pk=kw['imobiliaria_id']).first()
        if 'conta_id' in kw:
            return _um(ContaBancaria.objects, kw['conta_id'], 'imobiliaria')

        from contratos.models import Contrato
        if 'contrato_id' in kw:
            return _um(Contrato.objects, kw['contrato_id'], 'imobiliaria')
        if 'contrato_hid' in kw:
            return _um(Contrato.objects, decode_id(kw['contrato_hid']), 'imobiliaria')

        if 'hid' in kw:
            pk = decode_id(kw['hid'])
        elif 'pk' in kw:
            pk = kw['pk']
        else:
            pk = None

        if namespace == 'financeiro':
            from financeiro.models import Parcela, Reajuste, ArquivoRemessa, ArquivoRetorno
            if 'parcela_id' in kw:
                return _um(Parcela.objects, kw['parcela_id'], 'contrato__imobiliaria')
            if 'remessa_id' in kw:
                return _um(ArquivoRemessa.objects, kw['remessa_id'], 'conta_bancaria__imobiliaria')
            if 'retorno_id' in kw:
                return _um(ArquivoRetorno.objects, kw['retorno_id'], 'conta_bancaria__imobiliaria')
            if pk is None:
                return None
            if 'cnab/remessa/' in route:
                return _um(ArquivoRemessa.objects, pk, 'conta_bancaria__imobiliaria')
            if 'cnab/retorno/' in route:
                return _um(ArquivoRetorno.objects, pk, 'conta_bancaria__imobiliaria')
            if 'reajuste/' in route:
                return _um(Reajuste.objects, pk, 'contrato__imobiliaria')
            if 'parcelas/' in route:
                return _um(Parcela.objects, pk, 'contrato__imobiliaria')
            return None

        if namespace == 'contratos':
            if pk is None or 'indices/' in route or 'importar-pdf/' in route:
                return None
            from contratos.models import PrestacaoIntermediaria, MinutaContrato, TabelaJurosContrato
            if 'intermediarias/<str:hid>' in route:
                return _um(PrestacaoIntermediaria.objects, pk, 'contrato__imobiliaria')
            if 'minutas/<str:hid>' in route:
                return _um(MinutaContrato.objects, pk, 'contrato__imobiliaria')
            if 'tabela-juros/<str:hid>' in route:
                return _um(TabelaJurosContrato.objects, pk, 'contrato__imobiliaria')
            return _um(Contrato.objects, pk, 'imobiliaria')

        # core
        if pk is not None and 'imobiliarias/<int:pk>' in route:
            return Imobiliaria.objects.filter(pk=pk).first()
        return None
