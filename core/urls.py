"""
URLs do app Core

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Páginas principais
    path('', views.index, name='index'),
    path('setup/', views.setup, name='setup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/gerar-dados-teste/', views.gerar_dados_teste, name='gerar_dados_teste'),

    # CRUD Contabilidade
    path('contabilidades/', views.ContabilidadeListView.as_view(), name='listar_contabilidades'),
    path('contabilidades/novo/', views.ContabilidadeCreateView.as_view(), name='criar_contabilidade'),
    path('contabilidades/<int:pk>/editar/', views.ContabilidadeUpdateView.as_view(), name='editar_contabilidade'),
    path('contabilidades/<int:pk>/excluir/', views.ContabilidadeDeleteView.as_view(), name='excluir_contabilidade'),

    # CRUD Comprador
    path('compradores/', views.CompradorListView.as_view(), name='listar_compradores'),
    path('compradores/novo/', views.CompradorCreateView.as_view(), name='criar_comprador'),
    path('compradores/<int:pk>/editar/', views.CompradorUpdateView.as_view(), name='editar_comprador'),
    path('compradores/<int:pk>/excluir/', views.CompradorDeleteView.as_view(), name='excluir_comprador'),

    # CRUD Imóvel
    path('imoveis/', views.ImovelListView.as_view(), name='listar_imoveis'),
    path('imoveis/novo/', views.ImovelCreateView.as_view(), name='criar_imovel'),
    path('imoveis/<int:pk>/editar/', views.ImovelUpdateView.as_view(), name='editar_imovel'),
    path('imoveis/<int:pk>/excluir/', views.ImovelDeleteView.as_view(), name='excluir_imovel'),

    # CRUD Imobiliária
    path('imobiliarias/', views.ImobiliariaListView.as_view(), name='listar_imobiliarias'),
    path('imobiliarias/novo/', views.ImobiliariaCreateView.as_view(), name='criar_imobiliaria'),
    path('imobiliarias/<int:pk>/editar/', views.ImobiliariaUpdateView.as_view(), name='editar_imobiliaria'),
    path('imobiliarias/<int:pk>/excluir/', views.ImobiliariaDeleteView.as_view(), name='excluir_imobiliaria'),

    # API Conta Bancária
    path('api/bancos/', views.api_listar_bancos, name='api_listar_bancos'),
    path('api/imobiliarias/<int:imobiliaria_id>/contas/', views.api_listar_contas_bancarias, name='api_listar_contas'),
    path('api/contas/', views.api_criar_conta_bancaria, name='api_criar_conta'),
    path('api/contas/<int:conta_id>/', views.api_obter_conta_bancaria, name='api_obter_conta'),
    path('api/contas/<int:conta_id>/atualizar/', views.api_atualizar_conta_bancaria, name='api_atualizar_conta'),
    path('api/contas/<int:conta_id>/excluir/', views.api_excluir_conta_bancaria, name='api_excluir_conta'),
]
