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
]
