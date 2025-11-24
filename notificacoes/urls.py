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
    path('configuracoes/', views.configuracoes, name='configuracoes'),

    # CRUD Configuracao de Email
    path('email/', views.ConfiguracaoEmailListView.as_view(), name='listar_config_email'),
    path('email/novo/', views.ConfiguracaoEmailCreateView.as_view(), name='criar_config_email'),
    path('email/<int:pk>/editar/', views.ConfiguracaoEmailUpdateView.as_view(), name='editar_config_email'),
    path('email/<int:pk>/excluir/', views.ConfiguracaoEmailDeleteView.as_view(), name='excluir_config_email'),
    path('email/<int:pk>/testar/', views.testar_conexao_email, name='testar_config_email'),

    # CRUD Templates de Notificacao (Mensagens de Email)
    path('templates/', views.TemplateNotificacaoListView.as_view(), name='listar_templates'),
    path('templates/novo/', views.TemplateNotificacaoCreateView.as_view(), name='criar_template'),
    path('templates/<int:pk>/editar/', views.TemplateNotificacaoUpdateView.as_view(), name='editar_template'),
    path('templates/<int:pk>/excluir/', views.TemplateNotificacaoDeleteView.as_view(), name='excluir_template'),
    path('templates/<int:pk>/duplicar/', views.duplicar_template, name='duplicar_template'),
    path('templates/<int:pk>/preview/', views.preview_template, name='preview_template'),
]
