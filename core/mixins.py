"""
Mixins reutilizáveis para views do sistema Gestão de Contratos.

Inclui mixins para:
- Controle de acesso
- Isolamento de tenant (imobiliária)
- Otimização de queries
- Paginação
"""
from django.core.exceptions import PermissionDenied
from .models import (
    get_contabilidades_usuario,
    get_imobiliarias_usuario,
    usuario_tem_acesso_imobiliaria,
    usuario_tem_acesso_contabilidade,
    usuario_tem_permissao_total,
)


def verificar_acesso_tenant(request, imobiliaria):
    """
    Helper para function-based views: levanta PermissionDenied se o usuário
    não tiver acesso à imobiliária do objeto.

    Uso típico (FBV):
        contrato = get_object_or_404(Contrato, pk=pk)
        verificar_acesso_tenant(request, contrato.imobiliaria)

        parcela = get_object_or_404(Parcela.objects.select_related('contrato'), pk=pk)
        verificar_acesso_tenant(request, parcela.contrato.imobiliaria)
    """
    if not request.user.is_authenticated:
        raise PermissionDenied
    if usuario_tem_permissao_total(request.user):
        return
    if not usuario_tem_acesso_imobiliaria(request.user, imobiliaria):
        raise PermissionDenied


class AcessoMixin:
    """
    Mixin para controle de acesso baseado nos registros de AcessoUsuario.

    Cada usuário pode ter múltiplos acessos:
    - Usuário A → Contabilidade A → Imobiliária A
    - Usuário A → Contabilidade A → Imobiliária B
    - Usuário A → Contabilidade B → Imobiliária E
    """

    def get_contabilidades_permitidas(self):
        """Retorna as contabilidades que o usuário pode acessar."""
        return get_contabilidades_usuario(self.request.user)

    def get_imobiliarias_permitidas(self, contabilidade=None):
        """Retorna as imobiliárias que o usuário pode acessar."""
        return get_imobiliarias_usuario(self.request.user, contabilidade)

    def pode_acessar_contabilidade(self, contabilidade):
        """Verifica se o usuário pode acessar uma contabilidade específica."""
        return usuario_tem_acesso_contabilidade(self.request.user, contabilidade)

    def pode_acessar_imobiliaria(self, imobiliaria):
        """Verifica se o usuário pode acessar uma imobiliária específica."""
        return usuario_tem_acesso_imobiliaria(self.request.user, imobiliaria)


class TenantMixin(AcessoMixin):
    """
    Isolamento de tenant para class-based views (Detail/Update/Delete/List).

    Para Detail/Update/Delete: sobrescreve get_object() — retorna 403 se o objeto
    pertencer a uma imobiliária à qual o usuário não tem acesso.

    Para List: sobrescreve get_queryset() — filtra automaticamente pela(s)
    imobiliária(s) que o usuário pode acessar.

    Atributo `tenant_field`: atributo dotted-path a partir do objeto até Imobiliaria.
      - Contrato:               'imobiliaria'
      - Parcela:                'contrato.imobiliaria'
      - PrestacaoIntermediaria: 'contrato.imobiliaria'
    Atributo `tenant_filter`:   lookup ORM equivalente (para filtro no queryset).
      - Contrato:               'imobiliaria__in'
      - Parcela:                'contrato__imobiliaria__in'
    """
    tenant_field = 'imobiliaria'
    tenant_filter = 'imobiliaria__in'

    def _resolve_tenant_imobiliaria(self, obj):
        """Navega o dotted path no objeto para obter a Imobiliaria."""
        val = obj
        for part in self.tenant_field.split('.'):
            val = getattr(val, part)
        return val

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not usuario_tem_permissao_total(self.request.user):
            imob = self._resolve_tenant_imobiliaria(obj)
            if not usuario_tem_acesso_imobiliaria(self.request.user, imob):
                raise PermissionDenied
        return obj

    def get_queryset(self):
        qs = super().get_queryset()
        if usuario_tem_permissao_total(self.request.user):
            return qs
        imobs = self.get_imobiliarias_permitidas()
        return qs.filter(**{self.tenant_filter: imobs})


class QuerysetOptimizationMixin:
    """
    Mixin para otimização de queries em ListViews.

    Uso:
        class MinhaListView(QuerysetOptimizationMixin, ListView):
            model = MeuModelo
            select_related_fields = ['campo_fk1', 'campo_fk2']
            prefetch_related_fields = ['campo_m2m', 'related_set']
    """
    select_related_fields = []
    prefetch_related_fields = []

    def get_queryset(self):
        """Aplica select_related e prefetch_related ao queryset."""
        queryset = super().get_queryset()

        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)

        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset


class PaginacaoMixin:
    """
    Mixin para adicionar paginação consistente às ListViews.

    Atributos:
        paginate_by: Número de itens por página (padrão: 25)
        max_paginate_by: Máximo de itens por página (padrão: 100)
    """
    paginate_by = 25
    max_paginate_by = 100

    def get_paginate_by(self, queryset):
        """Permite override do paginate_by via query parameter."""
        per_page = self.request.GET.get('per_page')
        if per_page:
            try:
                per_page = int(per_page)
                return min(per_page, self.max_paginate_by)
            except (ValueError, TypeError):
                pass
        return self.paginate_by


class FilterMixin:
    """
    Mixin para filtros de busca em ListViews.

    Uso:
        class MinhaListView(FilterMixin, ListView):
            model = MeuModelo
            search_fields = ['nome', 'descricao']
            filter_fields = {'status': 'status', 'tipo': 'tipo'}
    """
    search_fields = []
    filter_fields = {}

    def get_queryset(self):
        """Aplica filtros de busca ao queryset."""
        from django.db.models import Q

        queryset = super().get_queryset()

        # Busca textual
        search = self.request.GET.get('q', '').strip()
        if search and self.search_fields:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f'{field}__icontains': search})
            queryset = queryset.filter(q_objects)

        # Filtros específicos
        for param, field in self.filter_fields.items():
            value = self.request.GET.get(param)
            if value:
                queryset = queryset.filter(**{field: value})

        return queryset

    def get_context_data(self, **kwargs):
        """Adiciona parâmetros de filtro ao contexto."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['active_filters'] = {
            param: self.request.GET.get(param)
            for param in self.filter_fields
            if self.request.GET.get(param)
        }
        return context
