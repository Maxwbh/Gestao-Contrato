"""
Configuração do Django Admin para o app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Contrato, TabelaJurosContrato, StatusContrato


class TabelaJurosInline(admin.TabularInline):
    model = TabelaJurosContrato
    extra = 0
    fields = ['ciclo_inicio', 'ciclo_fim', 'juros_mensal', 'observacoes']
    verbose_name = 'Faixa de Juros'
    verbose_name_plural = 'Tabela de Juros Escalantes'


@admin.register(TabelaJurosContrato)
class TabelaJurosContratoAdmin(admin.ModelAdmin):
    list_display = ['contrato', 'ciclo_inicio', 'ciclo_fim', 'juros_mensal', 'observacoes']
    list_filter = ['contrato__imobiliaria']
    search_fields = ['contrato__numero_contrato']
    autocomplete_fields = ['contrato']
    ordering = ['contrato', 'ciclo_inicio']


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
    inlines = [TabelaJurosInline]

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
                'dia_vencimento',
                'tipo_amortizacao',
            )
        }),
        ('Juros e Multa (Mora)', {
            'fields': (
                'percentual_juros_mora',
                'percentual_multa'
            )
        }),
        ('Correção Monetária', {
            'fields': (
                'tipo_correcao',
                'tipo_correcao_fallback',
                'prazo_reajuste_meses',
                'data_ultimo_reajuste',
                'spread_reajuste',
                'reajuste_piso',
                'reajuste_teto',
            )
        }),
        ('Parâmetros de Intermediárias', {
            'fields': (
                'intermediarias_reduzem_pmt',
                'intermediarias_reajustadas',
            ),
            'classes': ('collapse',),
            'description': 'Controla como as prestações intermediárias interagem com as parcelas mensais.'
        }),
        ('Cláusulas Contratuais', {
            'fields': (
                'percentual_fruicao',
                'percentual_multa_rescisao_penal',
                'percentual_multa_rescisao_adm',
                'percentual_cessao',
            ),
            'classes': ('collapse',),
            'description': 'Percentuais definidos em cláusula contratual para rescisão, fruição e cessão.'
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

    def save_related(self, request, form, formsets, change):
        """Após salvar inlines (TabelaJurosContrato), recalcula amortização."""
        super().save_related(request, form, formsets, change)
        contrato = form.instance
        # Só recalcula se o contrato já tem parcelas e TabelaJurosContrato definida
        if not (contrato.pk and contrato.parcelas.exists()):
            return
        if not TabelaJurosContrato.objects.filter(contrato=contrato).exists():
            return
        from decimal import Decimal
        from django.db.models import Sum
        base_pv = contrato.valor_financiado
        if contrato.intermediarias_reduzem_pmt:
            soma = contrato.intermediarias.aggregate(total=Sum('valor'))['total'] or Decimal('0')
            base_pv = max(base_pv - soma, Decimal('0.01'))
        contrato.recalcular_amortizacao(base_pv=base_pv)

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
        updated = queryset.update(status=StatusContrato.ATIVO)
        self.message_user(request, f'{updated} contrato(s) marcado(s) como ativo.')
    marcar_como_ativo.short_description = 'Marcar como Ativo'

    def marcar_como_suspenso(self, request, queryset):
        """Marca contratos selecionados como suspensos"""
        updated = queryset.update(status=StatusContrato.SUSPENSO)
        self.message_user(request, f'{updated} contrato(s) marcado(s) como suspenso.')
    marcar_como_suspenso.short_description = 'Marcar como Suspenso'

    def marcar_como_quitado(self, request, queryset):
        """Marca contratos selecionados como quitados"""
        updated = queryset.update(status=StatusContrato.QUITADO)
        self.message_user(request, f'{updated} contrato(s) marcado(s) como quitado.')
    marcar_como_quitado.short_description = 'Marcar como Quitado'
