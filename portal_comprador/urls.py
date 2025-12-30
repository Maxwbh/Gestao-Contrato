"""
URLs do Portal do Comprador
"""
from django.urls import path
from . import views

app_name = 'portal_comprador'

urlpatterns = [
    # ==========================================================================
    # AUTENTICAÇÃO
    # ==========================================================================
    path('cadastro/', views.auto_cadastro, name='auto_cadastro'),
    path('login/', views.login_comprador, name='login'),
    path('logout/', views.logout_comprador, name='logout'),

    # ==========================================================================
    # DASHBOARD
    # ==========================================================================
    path('', views.dashboard, name='dashboard'),

    # ==========================================================================
    # CONTRATOS
    # ==========================================================================
    path('contratos/', views.meus_contratos, name='meus_contratos'),
    path('contratos/<int:contrato_id>/', views.detalhe_contrato, name='detalhe_contrato'),

    # ==========================================================================
    # BOLETOS
    # ==========================================================================
    path('boletos/', views.meus_boletos, name='meus_boletos'),
    path('boletos/<int:parcela_id>/download/', views.download_boleto, name='download_boleto'),
    path('boletos/<int:parcela_id>/visualizar/', views.visualizar_boleto, name='visualizar_boleto'),

    # ==========================================================================
    # DADOS PESSOAIS
    # ==========================================================================
    path('meus-dados/', views.meus_dados, name='meus_dados'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),

    # ==========================================================================
    # API
    # ==========================================================================
    path('api/contratos/<int:contrato_id>/parcelas/', views.api_parcelas_contrato, name='api_parcelas_contrato'),
    path('api/resumo-financeiro/', views.api_resumo_financeiro, name='api_resumo_financeiro'),
]
