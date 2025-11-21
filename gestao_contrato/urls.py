"""
URL configuration for gestao_contrato project.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('contratos/', include('contratos.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('notificacoes/', include('notificacoes.urls')),
]

# Configuração para servir arquivos estáticos e de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customização do Admin
admin.site.site_header = "Gestão de Contratos - M&S do Brasil"
admin.site.site_title = "Gestão de Contratos"
admin.site.index_title = "Painel Administrativo"
