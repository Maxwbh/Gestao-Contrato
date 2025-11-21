"""
Configuração do Django Admin para o app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_contrato',
        'comprador',
        'imovel',
        'imobiliaria',
        'valor_total_formatado',
        'numero_parcelas',
        'status_badge',
        'data_contrato'
    ]
    list_filter = [
        'status',
        'tipo_correcao',
        'imobiliaria',
        'data_contrato',
        'criado_em'
    ]
    search_fields = [
        'numero_contrato',
        'comprador__nome',
        'comprador__cpf',
        'imovel__identificacao',
        'imovel__loteamento'
    ]
    readonly_fields = [
        'valor_financiado',
        'valor_parcela_original',
        'criado_em',
        'atualizado_em',
        'progresso_pagamento',
        'valor_total_pago',
        'saldo_devedor_atual'
    ]
    autocomplete_fields = ['imovel', 'comprador', 'imobiliaria']
    date_hierarchy = 'data_contrato'

    fieldsets = (
        ('Informações do Contrato', {
            'fields': (
                'numero_contrato',
                'data_contrato',
                'status'
            )
        }),
        ('Partes do Contrato', {
            'fields': (
                'imovel',
                'comprador',
                'imobiliaria'
            )
        }),
        ('Valores', {
            'fields': (
                'valor_total',
                'valor_entrada',
                'valor_financiado',
                'valor_parcela_original'
            )
        }),
        ('Configurações de Parcelas', {
            'fields': (
                'numero_parcelas',
                'data_primeiro_vencimento',
                'dia_vencimento'
            )
        }),
        ('Juros e Multa', {
            'fields': (
                'percentual_juros_mora',
                'percentual_multa'
            )
        }),
        ('Correção Monetária', {
            'fields': (
                'tipo_correcao',
                'prazo_reajuste_meses',
                'data_ultimo_reajuste'
            )
        }),
        ('Informações de Pagamento', {
            'fields': (
                'progresso_pagamento',
                'valor_total_pago',
                'saldo_devedor_atual'
            ),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': (
                'criado_em',
                'atualizado_em'
            ),
            'classes': ('collapse',)
        }),
    )

    def valor_total_formatado(self, obj):
        """Formata o valor total do contrato"""
        return f"R$ {obj.valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    valor_total_formatado.short_description = 'Valor Total'

    def status_badge(self, obj):
        """Exibe um badge colorido para o status"""
        colors = {
            'ATIVO': '#28a745',
            'QUITADO': '#007bff',
            'CANCELADO': '#dc3545',
            'SUSPENSO': '#ffc107'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def progresso_pagamento(self, obj):
        """Exibe o progresso de pagamento"""
        progresso = obj.calcular_progresso()
        return format_html(
            '<div style="width: 100%; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: #28a745; color: white; text-align: center; border-radius: 3px;">'
            '{:.1f}%'
            '</div>'
            '</div>',
            progresso,
            progresso
        )
    progresso_pagamento.short_description = 'Progresso'

    def valor_total_pago(self, obj):
        """Exibe o valor total já pago"""
        valor = obj.calcular_valor_pago()
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    valor_total_pago.short_description = 'Total Pago'

    def saldo_devedor_atual(self, obj):
        """Exibe o saldo devedor atual"""
        saldo = obj.calcular_saldo_devedor()
        return f"R$ {saldo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    saldo_devedor_atual.short_description = 'Saldo Devedor'

    actions = ['marcar_como_ativo', 'marcar_como_suspenso', 'marcar_como_quitado']

    def marcar_como_ativo(self, request, queryset):
        """Marca contratos selecionados como ativos"""
        updated = queryset.update(status='ATIVO')
        self.message_user(request, f'{updated} contrato(s) marcado(s) como ativo.')
    marcar_como_ativo.short_description = 'Marcar como Ativo'

    def marcar_como_suspenso(self, request, queryset):
        """Marca contratos selecionados como suspensos"""
        updated = queryset.update(status='SUSPENSO')
        self.message_user(request, f'{updated} contrato(s) marcado(s) como suspenso.')
    marcar_como_suspenso.short_description = 'Marcar como Suspenso'

    def marcar_como_quitado(self, request, queryset):
        """Marca contratos selecionados como quitados"""
        updated = queryset.update(status='QUITADO')
        self.message_user(request, f'{updated} contrato(s) marcado(s) como quitado.')
    marcar_como_quitado.short_description = 'Marcar como Quitado'
