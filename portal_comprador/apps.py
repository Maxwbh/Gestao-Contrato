"""
Configuração do app Portal do Comprador
"""
from django.apps import AppConfig


class PortalCompradorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal_comprador'
    verbose_name = 'Portal do Comprador'
