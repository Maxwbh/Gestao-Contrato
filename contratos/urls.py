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
]
