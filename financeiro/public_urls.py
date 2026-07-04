"""
URLs públicas de boleto — sem autenticação.
Montadas em /b/ no root URLconf.
"""
from django.urls import path
from . import views

app_name = 'boleto_publico'

urlpatterns = [
    path('<uuid:token>/', views.boleto_publico, name='visualizar'),
    path('<uuid:token>/download/', views.download_boleto_publico, name='download'),
]
