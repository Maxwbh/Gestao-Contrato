"""
Configuração do Django Admin para o app Notificações

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp,
    Notificacao, TemplateNotificacao
)
from .tasks import reenviar_notificacao


@admin.register(ConfiguracaoEmail)
class ConfiguracaoEmailAdmin(admin.ModelAdmin):
    list_display = ['nome', 'host', 'porta', 'email_remetente', 'ativo']
    list_filter = ['ativo', 'usar_tls', 'usar_ssl']
    search_fields = ['nome', 'host', 'email_remetente']
    readonly_fields = ['criado_em', 'atualizado_em']


@admin.register(ConfiguracaoSMS)
class ConfiguracaoSMSAdmin(admin.ModelAdmin):
    list_display = ['nome', 'provedor', 'numero_remetente', 'ativo']
    list_filter = ['provedor', 'ativo']
    search_fields = ['nome', 'numero_remetente']
    readonly_fields = ['criado_em', 'atualizado_em']


@admin.register(ConfiguracaoWhatsApp)
class ConfiguracaoWhatsAppAdmin(admin.ModelAdmin):
    list_display = ['nome', 'provedor', 'numero_remetente', 'ativo']
    list_filter = ['provedor', 'ativo']
    search_fields = ['nome', 'numero_remetente']
    readonly_fields = ['criado_em', 'atualizado_em']


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'tipo_badge',
        'destinatario',
        'parcela',
        'status_badge',
        'data_agendamento',
        'data_envio',
        'tentativas'
    ]
    list_filter = [
        'tipo',
        'status',
        'data_agendamento',
        'data_envio'
    ]
    search_fields = [
        'destinatario',
        'assunto',
        'mensagem',
        'parcela__contrato__numero_contrato',
        'parcela__contrato__comprador__nome'
    ]
    readonly_fields = ['criado_em', 'atualizado_em', 'data_envio', 'tentativas']
    date_hierarchy = 'data_agendamento'

    fieldsets = (
        ('Informações da Notificação', {
            'fields': (
                'parcela',
                'tipo',
                'destinatario'
            )
        }),
        ('Conteúdo', {
            'fields': (
                'assunto',
                'mensagem'
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'data_agendamento',
                'data_envio',
                'tentativas',
                'erro_mensagem'
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

    def tipo_badge(self, obj):
        """Exibe um badge colorido para o tipo"""
        colors = {
            'EMAIL': '#007bff',
            'SMS': '#28a745',
            'WHATSAPP': '#25d366'
        }
        color = colors.get(obj.tipo, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'

    def status_badge(self, obj):
        """Exibe um badge colorido para o status"""
        colors = {
            'PENDENTE': '#ffc107',
            'ENVIADA': '#28a745',
            'ERRO': '#dc3545',
            'CANCELADA': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = 'black' if obj.status == 'PENDENTE' else 'white'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            text_color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['reenviar_notificacoes', 'cancelar_notificacoes']

    def reenviar_notificacoes(self, request, queryset):
        """Reenvia as notificações selecionadas"""
        count = 0
        for notificacao in queryset:
            reenviar_notificacao.delay(notificacao.id)
            count += 1
        self.message_user(request, f'{count} notificação(ões) agendada(s) para reenvio.')
    reenviar_notificacoes.short_description = 'Reenviar Notificações'

    def cancelar_notificacoes(self, request, queryset):
        """Cancela as notificações selecionadas"""
        updated = queryset.update(status='CANCELADA')
        self.message_user(request, f'{updated} notificação(ões) cancelada(s).')
    cancelar_notificacoes.short_description = 'Cancelar Notificações'


@admin.register(TemplateNotificacao)
class TemplateNotificacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'ativo', 'criado_em']
    list_filter = ['tipo', 'ativo']
    search_fields = ['nome', 'assunto', 'corpo']
    readonly_fields = ['criado_em', 'atualizado_em']

    fieldsets = (
        ('Informações do Template', {
            'fields': (
                'nome',
                'tipo',
                'ativo'
            )
        }),
        ('Conteúdo', {
            'fields': (
                'assunto',
                'corpo'
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
