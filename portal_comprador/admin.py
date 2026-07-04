"""
Admin do Portal do Comprador
"""
from django.contrib import admin, messages
from django.utils.html import format_html
from .models import AcessoComprador, LogAcessoComprador, ComprovantePagamentoUpload


@admin.register(AcessoComprador)
class AcessoCompradorAdmin(admin.ModelAdmin):
    list_display = ['comprador', 'usuario', 'data_criacao', 'ultimo_acesso', 'email_verificado', 'ativo']
    list_select_related = ['comprador', 'usuario']
    list_filter = ['email_verificado', 'ativo', 'data_criacao']
    search_fields = ['comprador__nome', 'comprador__cpf', 'comprador__cnpj', 'usuario__username']
    readonly_fields = ['data_criacao', 'ultimo_acesso']
    raw_id_fields = ['comprador', 'usuario']


@admin.register(LogAcessoComprador)
class LogAcessoCompradorAdmin(admin.ModelAdmin):
    list_display = ['acesso_comprador', 'data_acesso', 'ip_acesso', 'pagina_acessada']
    list_select_related = ['acesso_comprador', 'acesso_comprador__comprador']
    list_filter = ['data_acesso']
    search_fields = ['acesso_comprador__comprador__nome', 'ip_acesso', 'pagina_acessada']
    readonly_fields = ['data_acesso']
    date_hierarchy = 'data_acesso'


@admin.register(ComprovantePagamentoUpload)
class ComprovantePagamentoUploadAdmin(admin.ModelAdmin):
    list_display = [
        'parcela', 'comprador_nome', 'valor_informado',
        'data_pagamento_informada', 'forma_pagamento',
        'status_badge', 'criado_em',
    ]
    list_select_related = ['parcela', 'parcela__contrato', 'parcela__contrato__comprador', 'acesso_comprador']
    list_filter = ['status', 'forma_pagamento', 'criado_em']
    search_fields = [
        'parcela__contrato__numero_contrato',
        'parcela__contrato__comprador__nome',
        'parcela__contrato__comprador__cpf',
    ]
    readonly_fields = ['criado_em', 'atualizado_em', 'validado_em', 'validado_por', 'acesso_comprador']
    raw_id_fields = ['parcela']
    date_hierarchy = 'criado_em'
    actions = ['aprovar_selecionados', 'rejeitar_selecionados']

    fieldsets = (
        ('Pagamento', {
            'fields': ('parcela', 'valor_informado', 'data_pagamento_informada',
                       'forma_pagamento', 'comprovante', 'observacoes_comprador')
        }),
        ('Validação', {
            'fields': ('status', 'motivo_rejeicao', 'validado_em', 'validado_por')
        }),
        ('Origem', {
            'fields': ('acesso_comprador', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def comprador_nome(self, obj):
        return obj.parcela.contrato.comprador.nome
    comprador_nome.short_description = 'Comprador'

    def status_badge(self, obj):
        cores = {
            'PENDENTE': '#ffc107',
            'APROVADO': '#28a745',
            'REJEITADO': '#dc3545',
        }
        cor = cores.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px">{}</span>',
            cor, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'

    def aprovar_selecionados(self, request, queryset):
        ok = 0
        falhas = 0
        for comp in queryset.filter(status=ComprovantePagamentoUpload.STATUS_PENDENTE):
            if comp.aprovar(request.user):
                ok += 1
            else:
                falhas += 1
        if ok:
            self.message_user(request, f'{ok} comprovante(s) aprovado(s).', messages.SUCCESS)
        if falhas:
            self.message_user(request, f'{falhas} não puderam ser aprovados.', messages.WARNING)
    aprovar_selecionados.short_description = 'Aprovar comprovantes selecionados'

    def rejeitar_selecionados(self, request, queryset):
        count = 0
        for comp in queryset.filter(status=ComprovantePagamentoUpload.STATUS_PENDENTE):
            if comp.rejeitar(request.user, 'Rejeitado em lote via admin'):
                count += 1
        self.message_user(request, f'{count} comprovante(s) rejeitado(s).', messages.SUCCESS)
    rejeitar_selecionados.short_description = 'Rejeitar comprovantes selecionados'
