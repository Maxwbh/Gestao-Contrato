"""
URLs do app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('parcelas/', views.listar_parcelas, name='listar_parcelas'),
    path('parcelas/<int:pk>/', views.detalhe_parcela, name='detalhe_parcela'),
    path('parcelas/<int:pk>/pagar/', views.registrar_pagamento, name='registrar_pagamento'),
    path('reajustes/', views.listar_reajustes, name='listar_reajustes'),
]
