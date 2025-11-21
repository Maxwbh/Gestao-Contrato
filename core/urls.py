"""
URLs do app Core

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('setup/', views.setup, name='setup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/gerar-dados-teste/', views.gerar_dados_teste, name='gerar_dados_teste'),
]
