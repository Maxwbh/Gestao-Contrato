"""
Configuração do Django Admin para o app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from .models import Contabilidade, Imobiliaria, Imovel, Comprador


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
    list_display = ['nome', 'razao_social', 'cnpj', 'contabilidade', 'responsavel_financeiro', 'ativo']
    list_filter = ['ativo', 'contabilidade', 'criado_em']
    search_fields = ['nome', 'razao_social', 'cnpj', 'responsavel_financeiro']
    readonly_fields = ['criado_em', 'atualizado_em']
    autocomplete_fields = ['contabilidade']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('contabilidade', 'nome', 'razao_social', 'cnpj')
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
