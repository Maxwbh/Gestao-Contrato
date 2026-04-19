"""
URLs do app Notificacoes

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'notificacoes'

urlpatterns = [
    # Notificacoes
    path('', views.listar_notificacoes, name='listar'),
    path('painel/', views.painel_mensagens, name='painel_mensagens'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),

    # Webhook Twilio (sem CSRF — validado por assinatura)
    path('webhook/twilio/', views.webhook_twilio, name='webhook_twilio'),

    # Ações AJAX
    path('<int:pk>/reenviar/', views.reenviar_notificacao_ajax, name='reenviar'),

    # Click-tracking de e-mail (sem login — acessado pelo destinatário)
    path('track/<uuid:token>/click/', views.track_click, name='track_click'),

    # CRUD Configuracao de Email
    path('email/', views.ConfiguracaoEmailListView.as_view(), name='listar_config_email'),
    path('email/novo/', views.ConfiguracaoEmailCreateView.as_view(), name='criar_config_email'),
    path('email/<int:pk>/editar/', views.ConfiguracaoEmailUpdateView.as_view(), name='editar_config_email'),
    path('email/<int:pk>/excluir/', views.ConfiguracaoEmailDeleteView.as_view(), name='excluir_config_email'),
    path('email/<int:pk>/testar/', views.testar_conexao_email, name='testar_config_email'),

    # CRUD Configuracao de WhatsApp
    path('whatsapp/', views.ConfiguracaoWhatsAppListView.as_view(), name='listar_config_whatsapp'),
    path('whatsapp/novo/', views.ConfiguracaoWhatsAppCreateView.as_view(), name='criar_config_whatsapp'),
    path('whatsapp/<int:pk>/editar/', views.ConfiguracaoWhatsAppUpdateView.as_view(), name='editar_config_whatsapp'),
    path('whatsapp/<int:pk>/excluir/', views.ConfiguracaoWhatsAppDeleteView.as_view(), name='excluir_config_whatsapp'),
    path('whatsapp/<int:pk>/testar/', views.testar_conexao_whatsapp, name='testar_config_whatsapp'),

    # CRUD Templates de Notificacao (Mensagens de Email)
    path('templates/', views.TemplateNotificacaoListView.as_view(), name='listar_templates'),
    path('templates/novo/', views.TemplateNotificacaoCreateView.as_view(), name='criar_template'),
    path('templates/<int:pk>/editar/', views.TemplateNotificacaoUpdateView.as_view(), name='editar_template'),
    path('templates/<int:pk>/excluir/', views.TemplateNotificacaoDeleteView.as_view(), name='excluir_template'),
    path('templates/<int:pk>/duplicar/', views.duplicar_template, name='duplicar_template'),
    path('templates/<int:pk>/preview/', views.preview_template, name='preview_template'),

    # 3.27 — Régua de Cobrança (RegraNotificacao) CRUD
    path('regras/', views.listar_regras_notificacao, name='listar_regras'),
    path('regras/novo/', views.criar_regra_notificacao, name='criar_regra'),
    path('regras/<int:pk>/editar/', views.editar_regra_notificacao, name='editar_regra'),
    path('regras/<int:pk>/excluir/', views.excluir_regra_notificacao, name='excluir_regra'),
    path('regras/<int:pk>/toggle/', views.toggle_regra_notificacao, name='toggle_regra'),
]
