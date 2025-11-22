"""
URLs do app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    # Dashboard Financeiro Geral
    path('dashboard/', views.DashboardFinanceiroView.as_view(), name='dashboard'),
    path('api/dashboard-dados/', views.api_dashboard_dados, name='api_dashboard_dados'),

    # Dashboard por Imobiliária
    path('imobiliaria/<int:imobiliaria_id>/dashboard/', views.dashboard_imobiliaria, name='dashboard_imobiliaria'),

    # Parcelas do Mês
    path('parcelas/mes/', views.parcelas_mes_atual, name='parcelas_mes'),

    # Parcelas
    path('parcelas/', views.listar_parcelas, name='listar_parcelas'),
    path('parcelas/<int:pk>/', views.detalhe_parcela, name='detalhe_parcela'),
    path('parcelas/<int:pk>/pagar/', views.registrar_pagamento, name='registrar_pagamento'),

    # Boletos
    path('parcelas/<int:pk>/boleto/gerar/', views.gerar_boleto_parcela, name='gerar_boleto'),
    path('parcelas/<int:pk>/boleto/download/', views.download_boleto, name='download_boleto'),
    path('parcelas/<int:pk>/boleto/visualizar/', views.visualizar_boleto, name='visualizar_boleto'),
    path('parcelas/<int:pk>/boleto/cancelar/', views.cancelar_boleto, name='cancelar_boleto'),
    path('parcelas/<int:pk>/boleto/status/', views.api_status_boleto, name='api_status_boleto'),
    path('contrato/<int:contrato_id>/boletos/gerar/', views.gerar_boletos_contrato, name='gerar_boletos_contrato'),

    # Reajustes
    path('reajustes/', views.listar_reajustes, name='listar_reajustes'),
]
