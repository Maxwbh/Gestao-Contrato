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

    path('<int:pk>/', views.ContratoDetailView.as_view(), name='detalhe'),
    path('<int:pk>/editar/', views.ContratoUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.ContratoDeleteView.as_view(), name='excluir'),

    # Parcelas
    path('<int:pk>/parcelas/', views.parcelas_contrato, name='parcelas'),
    path('<int:pk>/completar-parcelas/', views.api_completar_parcelas, name='completar_parcelas'),

    # CRUD de Índices de Reajuste
    path('indices/', views.IndiceReajusteListView.as_view(), name='indices_listar'),
    path('indices/novo/', views.IndiceReajusteCreateView.as_view(), name='indices_criar'),
    path('indices/<int:pk>/editar/', views.IndiceReajusteUpdateView.as_view(), name='indices_editar'),
    path('indices/<int:pk>/excluir/', views.IndiceReajusteDeleteView.as_view(), name='indices_excluir'),

    # API para importar índices
    path('indices/importar/', views.importar_indices_ibge, name='indices_importar'),

    # ===========================================================================
    # PRESTAÇÕES INTERMEDIÁRIAS
    # ===========================================================================
    # Listagem e detalhes
    path('<int:contrato_id>/intermediarias/', views.IntermediariasListView.as_view(), name='intermediarias_listar'),
    path('intermediarias/<int:pk>/', views.IntermediariasDetailView.as_view(), name='intermediarias_detalhe'),

    # CRUD de Intermediárias (API)
    path('<int:contrato_id>/intermediarias/criar/', views.criar_intermediaria, name='intermediarias_criar'),
    path('intermediarias/<int:pk>/atualizar/', views.atualizar_intermediaria, name='intermediarias_atualizar'),
    path('intermediarias/<int:pk>/excluir/', views.excluir_intermediaria, name='intermediarias_excluir'),

    # Pagamento e Boleto de Intermediárias
    path('intermediarias/<int:pk>/pagar/', views.pagar_intermediaria, name='intermediarias_pagar'),
    path('intermediarias/<int:pk>/gerar-boleto/', views.gerar_boleto_intermediaria, name='intermediarias_gerar_boleto'),

    # API de Intermediárias
    path('<int:contrato_id>/intermediarias/api/', views.api_intermediarias_contrato, name='intermediarias_api'),

    # ===========================================================================
    # G-11: Rescisão · G-12: Cessão de Direitos
    # ===========================================================================
    path('<int:pk>/rescisao/', views.calcular_rescisao_view, name='calcular_rescisao'),
    path('<int:pk>/cessao/', views.calcular_cessao_view, name='calcular_cessao'),

    # ===========================================================================
    # Q-04: Tabela de Juros Escalantes (TabelaJurosContrato)
    # ===========================================================================
    path('<int:pk>/tabela-juros/', views.api_tabela_juros_contrato, name='api_tabela_juros'),
    path('tabela-juros/<int:pk>/excluir/', views.api_tabela_juros_delete, name='api_tabela_juros_delete'),
]
