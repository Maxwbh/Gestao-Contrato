"""
Mixins reutilizáveis para views do sistema Gestão de Contratos.

Inclui mixins para:
- Controle de acesso
- Otimização de queries
- Paginação
"""
from django.core.paginator import Paginator
from .models import (
    get_contabilidades_usuario,
    get_imobiliarias_usuario,
    usuario_tem_acesso_imobiliaria,
    usuario_tem_acesso_contabilidade
)


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
