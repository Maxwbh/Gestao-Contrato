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

    # Recuperação de senha
    path('esqueci-senha/', views.esqueci_senha, name='esqueci_senha'),
    path('redefinir-senha/<str:token>/', views.redefinir_senha, name='redefinir_senha'),

    # Verificação de e-mail
    path('verificar-email/<str:token>/', views.verificar_email, name='verificar_email'),
    path('reenviar-verificacao/', views.reenviar_verificacao, name='reenviar_verificacao'),

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

    # Fase 9 — APIs P2 do Portal do Comprador
    path('api/vencimentos/', views.api_portal_vencimentos, name='api_portal_vencimentos'),
    path('api/boletos/', views.api_portal_boletos, name='api_portal_boletos'),

    # 4-P3: segunda via e linha digitável
    path('api/boletos/<int:parcela_id>/segunda-via/', views.api_portal_segunda_via, name='api_portal_segunda_via'),
    path('api/boletos/<int:parcela_id>/linha-digitavel/', views.api_portal_linha_digitavel, name='api_portal_linha_digitavel'),
]
