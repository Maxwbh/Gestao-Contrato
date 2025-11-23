"""
URLs do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.urls import path
from . import views

app_name = 'contratos'

urlpatterns = [
    # CRUD de Contratos
    path('', views.ContratoListView.as_view(), name='listar'),
    path('novo/', views.ContratoCreateView.as_view(), name='criar'),
    path('<int:pk>/', views.ContratoDetailView.as_view(), name='detalhe'),
    path('<int:pk>/editar/', views.ContratoUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.ContratoDeleteView.as_view(), name='excluir'),

    # Parcelas
    path('<int:pk>/parcelas/', views.parcelas_contrato, name='parcelas'),

    # CRUD de Índices de Reajuste
    path('indices/', views.IndiceReajusteListView.as_view(), name='indices_listar'),
    path('indices/novo/', views.IndiceReajusteCreateView.as_view(), name='indices_criar'),
    path('indices/<int:pk>/editar/', views.IndiceReajusteUpdateView.as_view(), name='indices_editar'),
    path('indices/<int:pk>/excluir/', views.IndiceReajusteDeleteView.as_view(), name='indices_excluir'),

    # API para importar índices
    path('indices/importar/', views.importar_indices_ibge, name='indices_importar'),
]
