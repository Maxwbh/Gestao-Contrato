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
    # U-05: compat redirect int:pk → hid
    path('parcelas/<int:pk>/compat/', views.parcela_pk_compat, name='parcela_pk_compat'),
    # U-03: rotas com hashid
    path('parcelas/<str:hid>/', views.detalhe_parcela, name='detalhe_parcela'),
    path('parcelas/<str:hid>/pagar/', views.registrar_pagamento, name='registrar_pagamento'),
    path('parcelas/<str:hid>/pagar-ajax/', views.pagar_parcela_ajax, name='pagar_parcela_ajax'),
    path('parcelas/<str:hid>/calcular-encargos/', views.api_calcular_encargos, name='api_calcular_encargos'),
    path('parcelas/<str:hid>/quickview/', views.api_parcela_quickview, name='api_parcela_quickview'),
    path('parcelas/<str:hid>/notificar/', views.notificar_inadimplente, name='notificar_inadimplente'),

    # Carne (multiplos boletos)
    path('contrato/<int:contrato_id>/gerar-carne/', views.gerar_carne, name='gerar_carne'),
    path('contrato/<int:contrato_id>/carne/pdf/', views.download_carne_pdf, name='download_carne_pdf'),
    path('api/carne/multiplos/', views.download_carne_pdf_multiplos, name='download_carne_multiplos'),
    path('contrato/<int:contrato_id>/boletos/zip/', views.download_zip_boletos, name='download_zip_boletos'),

    # Elegibilidade de parcelas para geracao de boletos
    path('api/contrato/<int:contrato_id>/parcelas-elegibilidade/', views.api_parcelas_elegibilidade, name='api_parcelas_elegibilidade'),

    # Geracao de boletos em lote (multiplos contratos)
    path('api/boletos/gerar-lote/', views.api_gerar_boletos_lote, name='api_gerar_boletos_lote'),
    # Geracao de boletos por parcelas selecionadas
    path('api/boletos/gerar-parcelas/', views.api_gerar_boletos_parcelas, name='api_gerar_boletos_parcelas'),

    # Boletos — U-03 hashid routes
    path('parcelas/<str:hid>/boleto/gerar/', views.gerar_boleto_parcela, name='gerar_boleto'),
    path('parcelas/<str:hid>/boleto/download/', views.download_boleto, name='download_boleto'),
    path('parcelas/<str:hid>/boleto/segunda-via/', views.segunda_via_boleto, name='segunda_via_boleto'),
    path('parcelas/<str:hid>/boleto/visualizar/', views.visualizar_boleto, name='visualizar_boleto'),
    path('parcelas/<str:hid>/boleto/cancelar/', views.cancelar_boleto, name='cancelar_boleto'),
    path('parcelas/<str:hid>/boleto/status/', views.api_status_boleto, name='api_status_boleto'),
    path('parcelas/<str:hid>/boleto/whatsapp/', views.enviar_boleto_whatsapp, name='boleto_whatsapp'),
    path('parcelas/<str:hid>/boleto/sms/', views.enviar_boleto_sms, name='boleto_sms'),
    path('parcelas/<str:hid>/boleto/email/', views.enviar_boleto_email, name='boleto_email'),
    path('contrato/<int:contrato_id>/boletos/gerar/', views.gerar_boletos_contrato, name='gerar_boletos_contrato'),

    # Reajustes
    path('reajustes/', views.listar_reajustes, name='listar_reajustes'),
    path('reajustes/pendentes/', views.reajustes_pendentes, name='reajustes_pendentes'),
    path('contrato/<int:contrato_id>/reajuste/', views.aplicar_reajuste_pagina, name='aplicar_reajuste'),
    path('contrato/<int:contrato_id>/reajuste/api/', views.aplicar_reajuste_contrato, name='aplicar_reajuste_api'),
    path('contrato/<int:contrato_id>/reajuste/preview/', views.preview_reajuste_contrato, name='preview_reajuste'),
    path('contrato/<int:contrato_id>/reajuste/calcular/', views.calcular_reajuste_proporcional, name='calcular_reajuste'),
    path('reajuste/<str:hid>/excluir/', views.excluir_reajuste, name='excluir_reajuste'),
    path('api/reajuste/<str:hid>/', views.api_reajuste_detail, name='api_reajuste_detail'),
    path('reajuste/<str:hid>/alterar-indice/', views.alterar_indice_reajuste, name='alterar_indice_reajuste'),
    path('reajustes/aplicar-lote/', views.aplicar_reajuste_lote, name='aplicar_reajuste_lote'),
    path('reajustes/aplicar-informado-lote/', views.aplicar_reajuste_informado_lote, name='aplicar_reajuste_informado_lote'),
    path('api/indice-reajuste/', views.obter_indice_reajuste, name='api_indice_reajuste'),
    path('api/calcular-indice-acumulado/', views.api_calcular_indice_acumulado, name='api_calcular_indice_acumulado'),

    # ==========================================================================
    # CNAB - Arquivos de Remessa
    # ==========================================================================
    path('cnab/remessa/', views.listar_arquivos_remessa, name='listar_remessas'),
    path('cnab/remessa/gerar/', views.gerar_arquivo_remessa, name='gerar_remessa'),
    # HU-23 — Painel de Remessa Mensal (fluxo da contadora)
    path('remessa/', views.remessa_painel, name='remessa_painel'),
    path('remessa/gerar/', views.remessa_painel_gerar, name='remessa_painel_gerar'),
    # HU-23 Passo 5 — Tela dedicada de Retorno Bancário
    path('retorno/', views.retorno_painel, name='retorno_painel'),
    path('retorno/upload/', views.remessa_painel_retorno_upload, name='remessa_retorno_upload'),
    # HU-24 — Geração Mensal de Boletos (tela dedicada)
    path('boletos/', views.boletos_painel, name='boletos_painel'),
    path('boletos/gerar/', views.boletos_painel_gerar, name='boletos_painel_gerar'),
    # HU-25 — Hub "Cobrança do Mês" (assistente de ciclo mensal)
    path('cobranca/', views.cobranca_hub, name='cobranca_hub'),
    path('api/cobranca/estado/', views.api_cobranca_estado, name='api_cobranca_estado'),
    # HU-26 — Painel de Conciliação & Saúde da Cobrança
    path('cobranca/conciliacao/', views.painel_conciliacao_saude, name='painel_conciliacao_saude'),
    path('api/conciliacao/saude/', views.api_conciliacao_saude, name='api_conciliacao_saude'),
    # Fase 9 — Painel de conciliação da cobrança registrada (Boleto-API)
    path('cobranca/conciliacao/boleto-api/', views.painel_conciliacao_boleto_api,
         name='painel_conciliacao_boleto_api'),
    # BAPI-32 — conciliação financeira (recebíveis do gateway × sistema)
    path('cobranca/conciliacao/boleto-api/financeira/',
         views.relatorio_conciliacao_financeira, name='relatorio_conciliacao_financeira'),
    # BAPI-14/15 — Pix avulso (2ª via / quitação) via Boleto-API
    path('parcelas/<int:parcela_id>/emitir-pix/', views.emitir_pix_parcela,
         name='emitir_pix_parcela'),
    path('api/remessa/validar/', views.api_remessa_validar, name='api_remessa_validar'),
    path('cnab/remessa/download-lote/', views.remessa_download_lote, name='remessa_download_lote'),
    path('cnab/remessa/<str:hid>/cancelar-envio/', views.remessa_cancelar_envio, name='remessa_cancelar_envio'),
    # U-05: compat redirect
    path('cnab/remessa/<int:pk>/compat/', views.remessa_pk_compat, name='remessa_pk_compat'),
    # U-03: hashid routes
    path('cnab/remessa/<str:hid>/', views.detalhe_arquivo_remessa, name='detalhe_remessa'),
    path('cnab/remessa/<str:hid>/regenerar/', views.regenerar_arquivo_remessa, name='regenerar_remessa'),
    path('cnab/remessa/<str:hid>/marcar-enviada/', views.marcar_remessa_enviada, name='marcar_remessa_enviada'),
    path('cnab/remessa/<str:hid>/excluir/', views.excluir_arquivo_remessa, name='excluir_remessa'),
    path('cnab/remessa/<str:hid>/download/', views.download_arquivo_remessa, name='download_remessa'),

    # ==========================================================================
    # Conciliação Bancária (hub unificado: CNAB Retorno + OFX + Baixa Manual)
    # ==========================================================================
    path('conciliacao/', views.dashboard_conciliacao, name='dashboard_conciliacao'),

    # ==========================================================================
    # OFX — Importação de Extrato Bancário
    # ==========================================================================
    path('cnab/ofx/upload/', views.upload_ofx, name='upload_ofx'),

    # CNAB - Arquivos de Retorno
    path('cnab/retorno/', views.listar_arquivos_retorno, name='listar_retornos'),
    path('cnab/retorno/upload/', views.upload_arquivo_retorno, name='upload_retorno'),
    # U-05: compat redirect
    path('cnab/retorno/<int:pk>/compat/', views.retorno_pk_compat, name='retorno_pk_compat'),
    # U-03: hashid routes
    path('cnab/retorno/<str:hid>/', views.detalhe_arquivo_retorno, name='detalhe_retorno'),
    path('cnab/retorno/<str:hid>/processar/', views.processar_arquivo_retorno, name='processar_retorno'),
    path('cnab/retorno/<str:hid>/download/', views.download_arquivo_retorno, name='download_retorno'),

    # ==========================================================================
    # RELATÓRIOS AVANÇADOS
    # ==========================================================================
    path('relatorios/prestacoes-a-pagar/', views.RelatorioPrestacoesAPagarView.as_view(), name='relatorio_prestacoes_a_pagar'),
    path('relatorios/prestacoes-pagas/', views.RelatorioPrestacoesPageasView.as_view(), name='relatorio_prestacoes_pagas'),
    path('relatorios/posicao-contratos/', views.RelatorioPosicaoContratosView.as_view(), name='relatorio_posicao_contratos'),
    path('relatorios/previsao-reajustes/', views.RelatorioPrevisaoReajustesView.as_view(), name='relatorio_previsao_reajustes'),
    path('relatorios/exportar/<str:tipo>/', views.exportar_relatorio, name='exportar_relatorio'),
    path('relatorios/exportar-consolidado/', views.exportar_relatorio_consolidado, name='exportar_relatorio_consolidado'),
    path('api/relatorios/resumo/', views.api_relatorio_resumo, name='api_relatorio_resumo'),

    # ==========================================================================
    # APIs REST
    # ==========================================================================
    # Imobiliárias
    path('api/imobiliarias/', views.api_imobiliarias_lista, name='api_imobiliarias'),
    path('api/imobiliaria/<int:imobiliaria_id>/dashboard/', views.api_imobiliaria_dashboard, name='api_imobiliaria_dashboard'),
    # 4-P3: novos endpoints
    path('api/contabilidade/relatorios/vencimentos/', views.api_contabilidade_relatorios_vencimentos, name='api_contabilidade_relatorios_vencimentos'),
    path('api/imobiliaria/<int:imobiliaria_id>/pendencias/', views.api_imobiliaria_pendencias, name='api_imobiliaria_pendencias'),

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
    path('api/boletos/revalidar/', views.api_boletos_revalidar, name='api_boletos_revalidar'),

    # ==========================================================================
    # APIs REST - CNAB REMESSA
    # ==========================================================================
    path('api/cnab/remessas/', views.api_cnab_remessa_listar, name='api_cnab_remessas'),
    path('api/cnab/remessas/<int:remessa_id>/', views.api_cnab_remessa_detalhe, name='api_cnab_remessa_detalhe'),
    path('api/cnab/remessas/gerar/', views.api_cnab_remessa_gerar, name='api_cnab_remessa_gerar'),
    path('api/cnab/boletos-disponiveis/', views.api_cnab_boletos_disponiveis, name='api_cnab_boletos_disponiveis'),
    path('api/cnab/boletos-pendentes/count/', views.api_cnab_boletos_pendentes_count, name='api_cnab_boletos_pendentes_count'),

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
    path('api/brcobranca/solicitar/', views.api_brcobranca_solicitar, name='api_brcobranca_solicitar'),

    # ==========================================================================
    # API - NOTIFICAÇÕES
    # ==========================================================================
    path('api/reajustes-pendentes/count/', views.api_reajustes_pendentes_count, name='api_reajustes_pendentes_count'),
    path('api/sidebar/pendencias/', views.api_sidebar_pendencias, name='api_sidebar_pendencias'),

    # ==========================================================================
    # FASE 9 — APIs P2 (Contabilidade + Imobiliária)
    # ==========================================================================
    path('api/contabilidade/vencimentos/', views.api_contabilidade_vencimentos, name='api_contabilidade_vencimentos'),
    path('api/contabilidade/boletos/gerar/massa/', views.api_contabilidade_boletos_massa, name='api_contabilidade_boletos_massa'),
    path('api/imobiliaria/<int:imobiliaria_id>/vencimentos/', views.api_imobiliaria_vencimentos, name='api_imobiliaria_vencimentos'),
    path('api/imobiliaria/<int:imobiliaria_id>/fluxo-caixa/', views.api_imobiliaria_fluxo_caixa, name='api_imobiliaria_fluxo_caixa'),

    # ==========================================================================
    # SEÇÃO 18 — SIMULADOR DE ANTECIPAÇÃO
    # ==========================================================================
    path('contrato/<int:contrato_id>/simulador/', views.simulador_antecipacao, name='simulador_antecipacao'),
    # R-05: Recibo PDF de quitação antecipada
    path('contrato/<int:contrato_id>/recibo-antecipacao.pdf', views.download_recibo_antecipacao, name='recibo_antecipacao'),

    # ==========================================================================
    # R-04 — RENEGOCIAÇÃO DE PARCELAS
    # ==========================================================================
    path('contrato/<int:contrato_id>/renegociar/', views.renegociar_parcelas, name='renegociar_parcelas'),

    # ==========================================================================
    # 34.3 P2 — PIX Webhook (POST público, autenticado por token)
    # ==========================================================================
    path('webhook/pix/', views.webhook_pix, name='webhook_pix'),

    # ==========================================================================
    # Boleto-API — webhook push de pagamento (X-Signature: sha256=<hmac>)
    # ==========================================================================
    path('webhooks/boleto-api/', views.webhook_boleto_api, name='webhook_boleto_api'),

    # ==========================================================================
    # 34.5 P3 — Relatórios Agendados e Exportação para BI
    # ==========================================================================
    # 34.5.3: endpoint público (token) para Power BI / Looker
    path('api/relatorios/posicao/', views.api_relatorio_posicao_bi, name='api_relatorio_posicao_bi'),
    # 34.5.4: dashboard executivo — série mensal para gráficos
    path('api/dashboard-executivo/', views.api_dashboard_executivo, name='api_dashboard_executivo'),
]
