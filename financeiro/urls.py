"""
URLs do app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    # Dashboard Financeiro Geral
    path('dashboard/', views.DashboardFinanceiroView.as_view(), name='dashboard'),
    path('api/dashboard-dados/', views.api_dashboard_dados, name='api_dashboard_dados'),

    # Dashboard Consolidado da Contabilidade
    path('contabilidade/dashboard/', views.DashboardContabilidadeView.as_view(), name='dashboard_contabilidade'),
    path('api/dashboard-contabilidade/', views.api_dashboard_contabilidade, name='api_dashboard_contabilidade'),

    # Dashboard por Imobiliária
    path('imobiliaria/<int:imobiliaria_id>/dashboard/', views.dashboard_imobiliaria, name='dashboard_imobiliaria'),

    # Parcelas do Mês
    path('parcelas/mes/', views.parcelas_mes_atual, name='parcelas_mes'),

    # Parcelas
    path('parcelas/', views.listar_parcelas, name='listar_parcelas'),
    path('parcelas/<int:pk>/', views.detalhe_parcela, name='detalhe_parcela'),
    path('parcelas/<int:pk>/pagar/', views.registrar_pagamento, name='registrar_pagamento'),
    path('parcelas/<int:pk>/pagar-ajax/', views.pagar_parcela_ajax, name='pagar_parcela_ajax'),

    # Carne (multiplos boletos)
    path('contrato/<int:contrato_id>/gerar-carne/', views.gerar_carne, name='gerar_carne'),

    # Elegibilidade de parcelas para geracao de boletos
    path('api/contrato/<int:contrato_id>/parcelas-elegibilidade/', views.api_parcelas_elegibilidade, name='api_parcelas_elegibilidade'),

    # Geracao de boletos em lote (multiplos contratos)
    path('api/boletos/gerar-lote/', views.api_gerar_boletos_lote, name='api_gerar_boletos_lote'),

    # Boletos
    path('parcelas/<int:pk>/boleto/gerar/', views.gerar_boleto_parcela, name='gerar_boleto'),
    path('parcelas/<int:pk>/boleto/download/', views.download_boleto, name='download_boleto'),
    path('parcelas/<int:pk>/boleto/visualizar/', views.visualizar_boleto, name='visualizar_boleto'),
    path('parcelas/<int:pk>/boleto/cancelar/', views.cancelar_boleto, name='cancelar_boleto'),
    path('parcelas/<int:pk>/boleto/status/', views.api_status_boleto, name='api_status_boleto'),
    path('contrato/<int:contrato_id>/boletos/gerar/', views.gerar_boletos_contrato, name='gerar_boletos_contrato'),

    # Reajustes
    path('reajustes/', views.listar_reajustes, name='listar_reajustes'),
    path('contrato/<int:contrato_id>/reajuste/aplicar/', views.aplicar_reajuste_contrato, name='aplicar_reajuste'),
    path('contrato/<int:contrato_id>/reajuste/calcular/', views.calcular_reajuste_proporcional, name='calcular_reajuste'),
    path('reajuste/<int:pk>/excluir/', views.excluir_reajuste, name='excluir_reajuste'),
    path('api/indice-reajuste/', views.obter_indice_reajuste, name='api_indice_reajuste'),
    path('api/calcular-indice-acumulado/', views.api_calcular_indice_acumulado, name='api_calcular_indice_acumulado'),

    # ==========================================================================
    # CNAB - Arquivos de Remessa
    # ==========================================================================
    path('cnab/remessa/', views.listar_arquivos_remessa, name='listar_remessas'),
    path('cnab/remessa/gerar/', views.gerar_arquivo_remessa, name='gerar_remessa'),
    path('cnab/remessa/<int:pk>/', views.detalhe_arquivo_remessa, name='detalhe_remessa'),
    path('cnab/remessa/<int:pk>/regenerar/', views.regenerar_arquivo_remessa, name='regenerar_remessa'),
    path('cnab/remessa/<int:pk>/marcar-enviada/', views.marcar_remessa_enviada, name='marcar_remessa_enviada'),
    path('cnab/remessa/<int:pk>/download/', views.download_arquivo_remessa, name='download_remessa'),

    # CNAB - Arquivos de Retorno
    path('cnab/retorno/', views.listar_arquivos_retorno, name='listar_retornos'),
    path('cnab/retorno/upload/', views.upload_arquivo_retorno, name='upload_retorno'),
    path('cnab/retorno/<int:pk>/', views.detalhe_arquivo_retorno, name='detalhe_retorno'),
    path('cnab/retorno/<int:pk>/processar/', views.processar_arquivo_retorno, name='processar_retorno'),
    path('cnab/retorno/<int:pk>/download/', views.download_arquivo_retorno, name='download_retorno'),

    # ==========================================================================
    # RELATÓRIOS AVANÇADOS
    # ==========================================================================
    path('relatorios/prestacoes-a-pagar/', views.RelatorioPrestacoesAPagarView.as_view(), name='relatorio_prestacoes_a_pagar'),
    path('relatorios/prestacoes-pagas/', views.RelatorioPrestacoesPageasView.as_view(), name='relatorio_prestacoes_pagas'),
    path('relatorios/posicao-contratos/', views.RelatorioPosicaoContratosView.as_view(), name='relatorio_posicao_contratos'),
    path('relatorios/previsao-reajustes/', views.RelatorioPrevisaoReajustesView.as_view(), name='relatorio_previsao_reajustes'),
    path('relatorios/exportar/<str:tipo>/', views.exportar_relatorio, name='exportar_relatorio'),
    path('api/relatorios/resumo/', views.api_relatorio_resumo, name='api_relatorio_resumo'),

    # ==========================================================================
    # APIs REST
    # ==========================================================================
    # Imobiliárias
    path('api/imobiliarias/', views.api_imobiliarias_lista, name='api_imobiliarias'),
    path('api/imobiliaria/<int:imobiliaria_id>/dashboard/', views.api_imobiliaria_dashboard, name='api_imobiliaria_dashboard'),

    # Contratos
    path('api/contratos/', views.api_contratos_lista, name='api_contratos'),
    path('api/contratos/<int:contrato_id>/', views.api_contrato_detalhe, name='api_contrato_detalhe'),
    path('api/contratos/<int:contrato_id>/parcelas/', views.api_contrato_parcelas, name='api_contrato_parcelas'),
    path('api/contratos/<int:contrato_id>/reajustes/', views.api_contrato_reajustes, name='api_contrato_reajustes'),

    # Parcelas
    path('api/parcelas/', views.api_parcelas_lista, name='api_parcelas'),
    path('api/parcelas/<int:parcela_id>/pagamento/', views.api_parcela_registrar_pagamento, name='api_parcela_pagamento'),

    # ==========================================================================
    # APIs REST - BOLETO
    # ==========================================================================
    path('api/boletos/<int:parcela_id>/', views.api_boleto_detalhe, name='api_boleto_detalhe'),
    path('api/boletos/<int:parcela_id>/gerar/', views.api_boleto_gerar, name='api_boleto_gerar'),
    path('api/boletos/<int:parcela_id>/cancelar/', views.api_boleto_cancelar, name='api_boleto_cancelar'),
    path('api/boletos/lote/', views.api_boletos_lote, name='api_boletos_lote'),

    # ==========================================================================
    # APIs REST - CNAB REMESSA
    # ==========================================================================
    path('api/cnab/remessas/', views.api_cnab_remessa_listar, name='api_cnab_remessas'),
    path('api/cnab/remessas/<int:remessa_id>/', views.api_cnab_remessa_detalhe, name='api_cnab_remessa_detalhe'),
    path('api/cnab/remessas/gerar/', views.api_cnab_remessa_gerar, name='api_cnab_remessa_gerar'),
    path('api/cnab/boletos-disponiveis/', views.api_cnab_boletos_disponiveis, name='api_cnab_boletos_disponiveis'),

    # ==========================================================================
    # APIs REST - CNAB RETORNO
    # ==========================================================================
    path('api/cnab/retornos/', views.api_cnab_retorno_listar, name='api_cnab_retornos'),
    path('api/cnab/retornos/<int:retorno_id>/', views.api_cnab_retorno_detalhe, name='api_cnab_retorno_detalhe'),
    path('api/cnab/retornos/<int:retorno_id>/processar/', views.api_cnab_retorno_processar, name='api_cnab_retorno_processar'),

    # ==========================================================================
    # API - CONTAS BANCÁRIAS
    # ==========================================================================
    path('api/contas-bancarias/', views.api_contas_bancarias, name='api_contas_bancarias'),
]
