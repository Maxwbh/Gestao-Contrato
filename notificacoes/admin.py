"""
Configuração do Django Admin para o app Notificações

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp,
    Notificacao, TemplateNotificacao, RegraNotificacao, StatusNotificacao,
    SessaoConversaWhatsApp, ComprovantePendente,
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
    list_display = ['nome', 'provedor', 'numero_remetente', 'instancia', 'ativo']
    list_filter = ['provedor', 'ativo']
    search_fields = ['nome', 'numero_remetente', 'instancia']
    list_editable = ['ativo']
    readonly_fields = ['criado_em', 'atualizado_em']

    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'provedor', 'ativo'),
        }),
        ('Twilio / Meta', {
            'fields': ('account_sid', 'auth_token', 'numero_remetente'),
            'description': 'Preencha apenas para provedores Twilio ou Meta.',
            'classes': ('collapse',),
        }),
        ('Evolution API / Z-API', {
            'fields': ('api_url', 'api_key', 'instancia', 'client_token'),
            'description': (
                'Evolution API v2: api_url = http://servidor:8080, api_key = apikey do servidor, instancia = nome da instância. '
                'Z-API: api_url = https://api.z-api.io, api_key = token, instancia = instance ID, client_token = Client-Token header.'
            ),
            'classes': ('collapse',),
        }),
        ('Evolution — Modo Cloud API (Meta oficial)', {
            'fields': ('modo_evolution', 'phone_number_id', 'meta_access_token'),
            'description': (
                'Apenas para Evolution API no modo Cloud API. '
                'Deixe <strong>modo_evolution = BAILEYS</strong> para uso padrão (self-hosted via QR Code).'
            ),
            'classes': ('collapse',),
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )


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
            StatusNotificacao.PENDENTE: '#ffc107',
            StatusNotificacao.ENVIADA: '#28a745',
            StatusNotificacao.ERRO: '#dc3545',
            StatusNotificacao.CANCELADA: '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = 'black' if obj.status == StatusNotificacao.PENDENTE else 'white'
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
        updated = queryset.update(status=StatusNotificacao.CANCELADA)
        self.message_user(request, f'{updated} notificação(ões) cancelada(s).')
    cancelar_notificacoes.short_description = 'Cancelar Notificações'


@admin.register(RegraNotificacao)
class RegraNotificacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_gatilho', 'dias_offset', 'tipo_notificacao', 'template', 'ativo']
    list_filter = ['tipo_gatilho', 'tipo_notificacao', 'ativo']
    search_fields = ['nome']
    list_editable = ['ativo']
    readonly_fields = ['criado_em', 'atualizado_em']

    fieldsets = (
        ('Gatilho', {
            'fields': ('nome', 'tipo_gatilho', 'dias_offset', 'ativo'),
        }),
        ('Canal e Conteúdo', {
            'fields': ('tipo_notificacao', 'template'),
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )


@admin.register(TemplateNotificacao)
class TemplateNotificacaoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'imobiliaria', 'canais_ativos', 'ativo', 'criado_em']
    list_filter = ['codigo', 'ativo', 'imobiliaria']
    search_fields = ['nome', 'assunto', 'corpo', 'corpo_html']
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['imobiliaria']

    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'nome', 'imobiliaria', 'ativo'),
            'description': (
                'Deixe <strong>Imobiliária</strong> em branco para template global '
                '(usado por todas as imobiliárias).'
            ),
        }),
        ('E-mail', {
            'fields': ('assunto', 'corpo_html'),
        }),
        ('SMS / Texto simples', {
            'fields': ('corpo',),
            'classes': ('collapse',),
        }),
        ('WhatsApp', {
            'fields': ('corpo_whatsapp',),
            'classes': ('collapse',),
        }),
        ('Canal legado', {
            'fields': ('tipo',),
            'classes': ('collapse',),
            'description': 'Campo legado — canal detectado automaticamente pelos campos preenchidos.',
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Canais')
    def canais_ativos(self, obj):
        canais = []
        if obj.tem_email:
            canais.append('E-mail')
        if obj.tem_sms:
            canais.append('SMS')
        if obj.tem_whatsapp:
            canais.append('WhatsApp')
        return ', '.join(canais) if canais else '—'


@admin.register(SessaoConversaWhatsApp)
class SessaoConversaWhatsAppAdmin(admin.ModelAdmin):
    list_display = ['numero_whatsapp', 'comprador', 'estado', 'ativo', 'atualizado_em']
    list_filter = ['estado', 'ativo']
    search_fields = ['numero_whatsapp', 'comprador__nome', 'comprador__cpf']
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['comprador']
    list_select_related = ['comprador']
    ordering = ['-atualizado_em']
    actions = ['encerrar_sessoes']

    @admin.action(description='Encerrar sessões selecionadas')
    def encerrar_sessoes(self, request, queryset):
        count = 0
        for sessao in queryset.filter(ativo=True):
            sessao.encerrar()
            count += 1
        self.message_user(request, f'{count} sessão(ões) encerrada(s).')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('comprador')


@admin.register(ComprovantePendente)
class ComprovantePendenteAdmin(admin.ModelAdmin):
    """C-11 — Fila de comprovantes recebidos via WhatsApp aguardando revisão."""

    list_display = ['id', 'comprador_nome', 'parcela', 'destinatario', 'criado_em', 'acoes']
    search_fields = ['destinatario', 'mensagem', 'parcela__contrato__numero_contrato']
    readonly_fields = ['destinatario', 'assunto', 'mensagem', 'criado_em', 'atualizado_em',
                       'parcela', 'tipo', 'status', 'erro_mensagem']
    ordering = ['-criado_em']
    date_hierarchy = 'criado_em'
    actions = ['marcar_confirmado', 'marcar_cancelado']

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(assunto__startswith='Comprovante recebido', status=StatusNotificacao.PENDENTE)
            .select_related('parcela__contrato__comprador')
        )

    def has_add_permission(self, request):
        return False

    def comprador_nome(self, obj):
        if obj.parcela and obj.parcela.contrato and obj.parcela.contrato.comprador:
            return obj.parcela.contrato.comprador.nome
        return obj.destinatario
    comprador_nome.short_description = 'Comprador'

    def acoes(self, obj):
        return format_html(
            '<a class="button" href="{}">Ver parcela</a>',
            f'/admin/financeiro/parcela/{obj.parcela_id}/change/' if obj.parcela_id else '#',
        )
    acoes.short_description = 'Ações'
    acoes.allow_tags = True

    @admin.action(description='Marcar comprovante como confirmado (cancelar notificação)')
    def marcar_confirmado(self, request, queryset):
        updated = queryset.update(status=StatusNotificacao.CANCELADA)
        self.message_user(request, f'{updated} comprovante(s) confirmado(s) — notificações canceladas.')

    @admin.action(description='Marcar como cancelado')
    def marcar_cancelado(self, request, queryset):
        updated = queryset.update(status=StatusNotificacao.CANCELADA)
        self.message_user(request, f'{updated} notificação(ões) cancelada(s).')
