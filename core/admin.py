"""
Configuração do Django Admin para o app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Contabilidade, Imobiliaria, Imovel, Comprador, ParametroSistema
from .parametros import invalidar_cache


@admin.register(Contabilidade)
class ContabilidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'razao_social', 'cnpj', 'responsavel', 'ativo', 'criado_em']
    list_filter = ['ativo', 'criado_em']
    search_fields = ['nome', 'razao_social', 'cnpj', 'responsavel']
    readonly_fields = ['criado_em', 'atualizado_em']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'razao_social', 'cnpj')
        }),
        ('Contato', {
            'fields': ('endereco', 'telefone', 'email', 'responsavel')
        }),
        ('Status', {
            'fields': ('ativo', 'criado_em', 'atualizado_em')
        }),
    )


@admin.register(Imobiliaria)
class ImobiliariaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_pessoa', 'documento_display', 'contabilidade', 'responsavel_financeiro', 'ativo']
    list_filter = ['ativo', 'tipo_pessoa', 'contabilidade', 'criado_em']
    search_fields = ['nome', 'razao_social', 'cnpj', 'cpf', 'responsavel_financeiro']
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['contabilidade']
    fieldsets = (
        ('Tipo de Pessoa', {
            'fields': ('contabilidade', 'tipo_pessoa'),
            'description': 'Selecione PJ para empresa/imobiliária ou PF para vendedor pessoa física.',
        }),
        ('Identificação', {
            'fields': ('nome', 'razao_social', 'cnpj', 'cpf'),
            'description': 'Para PJ: preencha CNPJ. Para PF: preencha apenas CPF.',
        }),
        ('Contato', {
            'fields': ('endereco', 'telefone', 'email', 'responsavel_financeiro')
        }),
        ('Dados Bancários', {
            'fields': ('banco', 'agencia', 'conta', 'pix')
        }),
        ('Status', {
            'fields': ('ativo', 'criado_em', 'atualizado_em')
        }),
    )

    def documento_display(self, obj):
        return obj.documento or '—'
    documento_display.short_description = 'CNPJ / CPF'


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ['identificacao', 'loteamento', 'tipo', 'imobiliaria', 'area', 'disponivel', 'ativo']
    list_filter = ['tipo', 'disponivel', 'ativo', 'imobiliaria', 'criado_em']
    search_fields = ['identificacao', 'loteamento', 'endereco', 'matricula']
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['imobiliaria']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('imobiliaria', 'tipo', 'identificacao', 'loteamento')
        }),
        ('Localização', {
            'fields': ('endereco', 'area')
        }),
        ('Documentação', {
            'fields': ('matricula', 'inscricao_municipal')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Status', {
            'fields': ('disponivel', 'ativo', 'criado_em', 'atualizado_em')
        }),
    )


@admin.register(Comprador)
class CompradorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'email', 'celular', 'estado_civil', 'ativo']
    list_filter = ['estado_civil', 'ativo', 'notificar_email', 'notificar_sms', 'notificar_whatsapp', 'criado_em']
    search_fields = ['nome', 'cpf', 'email', 'telefone', 'celular']
    readonly_fields = ['criado_em', 'atualizado_em']
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome', 'cpf', 'rg', 'data_nascimento', 'estado_civil', 'profissao')
        }),
        ('Contato', {
            'fields': ('endereco', 'telefone', 'celular', 'email')
        }),
        ('Preferências de Notificação', {
            'fields': ('notificar_email', 'notificar_sms', 'notificar_whatsapp')
        }),
        ('Dados do Cônjuge', {
            'fields': ('conjuge_nome', 'conjuge_cpf', 'conjuge_rg'),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Status', {
            'fields': ('ativo', 'criado_em', 'atualizado_em')
        }),
    )


@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ['chave', 'valor_admin', 'tipo', 'grupo', 'modificado_manualmente', 'atualizado_em']
    list_filter = ['grupo', 'tipo', 'modificado_manualmente']
    search_fields = ['chave', 'descricao']
    ordering = ['grupo', 'chave']
    readonly_fields = ['atualizado_em', 'modificado_manualmente']
    list_per_page = 50

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['chave', 'atualizado_em', 'modificado_manualmente']
        return ['atualizado_em', 'modificado_manualmente']

    fieldsets = (
        (None, {
            'fields': ('chave', 'grupo', 'tipo', 'descricao')
        }),
        ('Valor', {
            'fields': ('valor',),
            'description': 'Campos do tipo Senha/Token são exibidos mascarados na listagem.',
        }),
        ('Auditoria', {
            'fields': ('atualizado_em', 'modificado_manualmente'),
            'classes': ('collapse',),
        }),
    )

    def valor_admin(self, obj):
        if obj.tipo == ParametroSistema.TIPO_SECRET and obj.valor:
            return format_html('<span style="color:#999">••••••••</span>')
        return obj.valor or format_html('<em style="color:#ccc">—</em>')
    valor_admin.short_description = 'Valor'

    def save_model(self, request, obj, form, change):
        obj.modificado_manualmente = True
        super().save_model(request, obj, form, change)
        invalidar_cache()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        invalidar_cache()
