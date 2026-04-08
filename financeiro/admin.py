"""
Configuração do Django Admin para o app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Parcela, Reajuste, HistoricoPagamento


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_parcela_display',
        'contrato',
        'data_vencimento',
        'valor_total_display',
        'status_badge',
        'dias_atraso_display'
    ]
    list_filter = [
        'pago',
        'data_vencimento',
        'contrato__imobiliaria',
        'criado_em'
    ]
    search_fields = [
        'contrato__numero_contrato',
        'contrato__comprador__nome',
        'numero_parcela'
    ]
    readonly_fields = [
        'criado_em',
        'atualizado_em',
        'valor_total',
        'dias_atraso',
        'esta_vencida'
    ]
    autocomplete_fields = ['contrato']
    date_hierarchy = 'data_vencimento'

    fieldsets = (
        ('Informações da Parcela', {
            'fields': (
                'contrato',
                'numero_parcela',
                'data_vencimento'
            )
        }),
        ('Valores', {
            'fields': (
                'valor_original',
                'valor_atual',
                'valor_juros',
                'valor_multa',
                'valor_desconto',
                'valor_total'
            )
        }),
        ('Pagamento', {
            'fields': (
                'pago',
                'data_pagamento',
                'valor_pago'
            )
        }),
        ('Informações Adicionais', {
            'fields': (
                'dias_atraso',
                'esta_vencida',
                'observacoes'
            )
        }),
        ('Metadados', {
            'fields': (
                'criado_em',
                'atualizado_em'
            ),
            'classes': ('collapse',)
        }),
    )

    def numero_parcela_display(self, obj):
        """Exibe o número da parcela formatado"""
        return f"{obj.numero_parcela}/{obj.contrato.numero_parcelas}"
    numero_parcela_display.short_description = 'Parcela'
    numero_parcela_display.admin_order_field = 'numero_parcela'

    def valor_total_display(self, obj):
        """Exibe o valor total formatado"""
        valor = obj.valor_total
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    valor_total_display.short_description = 'Valor Total'

    def status_badge(self, obj):
        """Exibe um badge colorido para o status de pagamento"""
        if obj.pago:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Pago</span>'
            )
        elif obj.esta_vencida:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Vencido</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">Pendente</span>'
            )
    status_badge.short_description = 'Status'

    def dias_atraso_display(self, obj):
        """Exibe os dias de atraso"""
        dias = obj.dias_atraso
        if dias > 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{} dias</span>',
                dias
            )
        return '-'
    dias_atraso_display.short_description = 'Atraso'

    actions = ['atualizar_juros_multa', 'marcar_como_pago']

    def atualizar_juros_multa(self, request, queryset):
        """Atualiza juros e multa das parcelas selecionadas"""
        count = 0
        for parcela in queryset.filter(pago=False):
            parcela.atualizar_juros_multa()
            count += 1
        self.message_user(request, f'{count} parcela(s) atualizada(s).')
    atualizar_juros_multa.short_description = 'Atualizar Juros e Multa'

    def marcar_como_pago(self, request, queryset):
        """Marca as parcelas selecionadas como pagas"""
        count = 0
        hoje = timezone.now().date()
        for parcela in queryset.filter(pago=False):
            parcela.registrar_pagamento(
                valor_pago=parcela.valor_total,
                data_pagamento=hoje,
                observacoes='Marcado como pago via admin'
            )
            count += 1
        self.message_user(request, f'{count} parcela(s) marcada(s) como paga(s).')
    marcar_como_pago.short_description = 'Marcar como Pago'


@admin.register(Reajuste)
class ReajusteAdmin(admin.ModelAdmin):
    list_display = [
        'contrato',
        'data_reajuste',
        'indice_tipo',
        'percentual_display',
        'parcelas_afetadas',
        'aplicado_manual'
    ]
    list_filter = [
        'indice_tipo',
        'aplicado_manual',
        'data_reajuste',
        'contrato__imobiliaria'
    ]
    search_fields = [
        'contrato__numero_contrato',
        'contrato__comprador__nome'
    ]
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['contrato']
    date_hierarchy = 'data_reajuste'

    fieldsets = (
        ('Informações do Reajuste', {
            'fields': (
                'contrato',
                'data_reajuste',
                'indice_tipo',
                'percentual'
            )
        }),
        ('Parcelas Afetadas', {
            'fields': (
                'parcela_inicial',
                'parcela_final'
            )
        }),
        ('Configurações', {
            'fields': (
                'aplicado_manual',
                'observacoes'
            )
        }),
        ('Metadados', {
            'fields': (
                'criado_em',
                'atualizado_em'
            ),
            'classes': ('collapse',)
        }),
    )

    def percentual_display(self, obj):
        """Exibe o percentual formatado"""
        return f"{obj.percentual:.4f}%"
    percentual_display.short_description = 'Percentual'
    percentual_display.admin_order_field = 'percentual'

    def parcelas_afetadas(self, obj):
        """Exibe a faixa de parcelas afetadas"""
        return f"{obj.parcela_inicial} a {obj.parcela_final}"
    parcelas_afetadas.short_description = 'Parcelas'

    actions = ['aplicar_reajuste_selecionado']

    def aplicar_reajuste_selecionado(self, request, queryset):
        """Aplica os reajustes selecionados"""
        count = 0
        for reajuste in queryset:
            reajuste.aplicar_reajuste()
            count += 1
        self.message_user(request, f'{count} reajuste(s) aplicado(s).')
    aplicar_reajuste_selecionado.short_description = 'Aplicar Reajuste'


@admin.register(HistoricoPagamento)
class HistoricoPagamentoAdmin(admin.ModelAdmin):
    list_display = [
        'parcela',
        'data_pagamento',
        'valor_pago_display',
        'forma_pagamento',
        'criado_em'
    ]
    list_filter = [
        'forma_pagamento',
        'data_pagamento',
        'criado_em'
    ]
    search_fields = [
        'parcela__contrato__numero_contrato',
        'parcela__contrato__comprador__nome'
    ]
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['parcela']
    date_hierarchy = 'data_pagamento'

    fieldsets = (
        ('Informações do Pagamento', {
            'fields': (
                'parcela',
                'data_pagamento',
                'forma_pagamento'
            )
        }),
        ('Valores', {
            'fields': (
                'valor_pago',
                'valor_parcela',
                'valor_juros',
                'valor_multa',
                'valor_desconto'
            )
        }),
        ('Comprovante', {
            'fields': (
                'comprovante',
                'observacoes'
            )
        }),
        ('Metadados', {
            'fields': (
                'criado_em',
                'atualizado_em'
            ),
            'classes': ('collapse',)
        }),
    )

    def valor_pago_display(self, obj):
        """Exibe o valor pago formatado"""
        return f"R$ {obj.valor_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    valor_pago_display.short_description = 'Valor Pago'
    valor_pago_display.admin_order_field = 'valor_pago'
