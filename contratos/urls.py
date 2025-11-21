"""
URLs do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'contratos'

urlpatterns = [
    path('', views.listar_contratos, name='listar'),
    path('<int:pk>/', views.detalhe_contrato, name='detalhe'),
    path('<int:pk>/parcelas/', views.parcelas_contrato, name='parcelas'),
]
