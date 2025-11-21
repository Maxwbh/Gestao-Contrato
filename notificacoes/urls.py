"""
URLs do app Notificações

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'notificacoes'

urlpatterns = [
    path('', views.listar_notificacoes, name='listar'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('templates/', views.listar_templates, name='templates'),
]
