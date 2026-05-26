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

    # Wizard
    path('wizard/', views.ContratoWizardView.as_view(), name='wizard'),
    path('wizard/<str:step>/', views.ContratoWizardView.as_view(), name='wizard'),
    path('wizard/api/preview-parcelas/', views.api_preview_parcelas, name='wizard_preview_parcelas'),
    path('wizard/api/imoveis/', views.api_wizard_imoveis, name='wizard_imoveis'),

    # CRUD de Índices de Reajuste (must come before <str:hid> catch-all)
    path('indices/', views.IndiceReajusteListView.as_view(), name='indices_listar'),
    path('indices/novo/', views.IndiceReajusteCreateView.as_view(), name='indices_criar'),
    path('indices/importar/', views.importar_indices_ibge, name='indices_importar'),
    path('indices/<str:hid>/editar/', views.IndiceReajusteUpdateView.as_view(), name='indices_editar'),
    path('indices/<str:hid>/excluir/', views.IndiceReajusteDeleteView.as_view(), name='indices_excluir'),

    # Tabela de juros (static prefix, must come before <str:hid> catch-all)
    path('tabela-juros/<str:hid>/excluir/', views.api_tabela_juros_delete, name='api_tabela_juros_delete'),

    # Intermediárias (static prefix, must come before <str:hid> catch-all)
    path('intermediarias/<str:hid>/', views.IntermediariasDetailView.as_view(), name='intermediarias_detalhe'),
    path('intermediarias/<str:hid>/atualizar/', views.atualizar_intermediaria, name='intermediarias_atualizar'),
    path('intermediarias/<str:hid>/excluir/', views.excluir_intermediaria, name='intermediarias_excluir'),
    path('intermediarias/<str:hid>/pagar/', views.pagar_intermediaria, name='intermediarias_pagar'),
    path('intermediarias/<str:hid>/gerar-boleto/', views.gerar_boleto_intermediaria, name='intermediarias_gerar_boleto'),

    # ===========================================================================
    # Importação de Contratos via IA (Upload PDF → Claude → Revisão → Criação)
    # Must come before <str:hid> catch-all to avoid shadowing
    # ===========================================================================
    path('importar-pdf/', views.upload_importacao, name='upload_importacao'),
    path('importar-pdf/<int:pk>/revisao/', views.revisao_importacao, name='revisao_importacao'),
    path('importar-pdf/<int:pk>/confirmar/', views.confirmar_importacao, name='confirmar_importacao'),

    # U-05: compat redirects (int:pk → hid) — manter por 30 dias
    path('<int:pk>/compat/', views.contrato_pk_compat, name='contrato_pk_compat'),
    path('<int:pk>/editar/compat/', views.contrato_pk_compat_editar, name='contrato_pk_compat_editar'),
    path('<int:pk>/excluir/compat/', views.contrato_pk_compat_excluir, name='contrato_pk_compat_excluir'),
    path('<int:pk>/parcelas/compat/', views.contrato_pk_compat_parcelas, name='contrato_pk_compat_parcelas'),

    # U-03: rotas com hashid (catch-all <str:hid> must come after all static prefixes)
    path('<str:hid>/', views.ContratoDetailView.as_view(), name='detalhe'),
    path('<str:hid>/editar/', views.ContratoUpdateView.as_view(), name='editar'),
    path('<str:hid>/excluir/', views.ContratoDeleteView.as_view(), name='excluir'),

    # Parcelas
    path('<str:hid>/parcelas/', views.parcelas_contrato, name='parcelas'),
    path('<str:hid>/completar-parcelas/', views.api_completar_parcelas, name='completar_parcelas'),

    # ===========================================================================
    # PRESTAÇÕES INTERMEDIÁRIAS
    # ===========================================================================
    path('<str:contrato_hid>/intermediarias/', views.IntermediariasListView.as_view(), name='intermediarias_listar'),
    path('<str:contrato_hid>/intermediarias/criar/', views.criar_intermediaria, name='intermediarias_criar'),
    path('<str:contrato_hid>/intermediarias/api/', views.api_intermediarias_contrato, name='intermediarias_api'),

    # ===========================================================================
    # G-11: Rescisão · G-12: Cessão de Direitos
    # ===========================================================================
    path('<str:hid>/rescisao/', views.calcular_rescisao_view, name='calcular_rescisao'),
    path('<str:hid>/cessao/', views.calcular_cessao_view, name='calcular_cessao'),

    # ===========================================================================
    # Q-04: Tabela de Juros Escalantes
    # ===========================================================================
    path('<str:hid>/tabela-juros/', views.api_tabela_juros_contrato, name='api_tabela_juros'),

    # ===========================================================================
    # 34.2 P1: Quadro-Resumo (Lei 6.766 art. 26) e Minutas de Contrato
    # ===========================================================================
    path('<str:hid>/quadro-resumo/', views.quadro_resumo_view, name='quadro_resumo'),
    path('<str:hid>/minutas/', views.minutas_listar, name='minutas_listar'),
    path('<str:hid>/minutas/nova/', views.minutas_criar, name='minutas_criar'),
    # Minuta-level routes use minuta pk (not contrato hid)
    path('minutas/<str:hid>/editar/', views.minutas_editar, name='minutas_editar'),
    path('minutas/<str:hid>/excluir/', views.minutas_excluir, name='minutas_excluir'),

]
