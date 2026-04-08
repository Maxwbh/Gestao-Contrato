"""
Admin do Portal do Comprador
"""
from django.contrib import admin
from .models import AcessoComprador, LogAcessoComprador


@admin.register(AcessoComprador)
class AcessoCompradorAdmin(admin.ModelAdmin):
    list_display = ['comprador', 'usuario', 'data_criacao', 'ultimo_acesso', 'email_verificado', 'ativo']
    list_filter = ['email_verificado', 'ativo', 'data_criacao']
    search_fields = ['comprador__nome', 'comprador__cpf', 'comprador__cnpj', 'usuario__username']
    readonly_fields = ['data_criacao', 'ultimo_acesso']
    raw_id_fields = ['comprador', 'usuario']


@admin.register(LogAcessoComprador)
class LogAcessoCompradorAdmin(admin.ModelAdmin):
    list_display = ['acesso_comprador', 'data_acesso', 'ip_acesso', 'pagina_acessada']
    list_filter = ['data_acesso']
    search_fields = ['acesso_comprador__comprador__nome', 'ip_acesso', 'pagina_acessada']
    readonly_fields = ['data_acesso']
    date_hierarchy = 'data_acesso'
