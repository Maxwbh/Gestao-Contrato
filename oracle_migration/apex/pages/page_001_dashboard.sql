/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Pagina 1 - Dashboard (Home)
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
==============================================================================
*/

-- ============================================================================
-- PAGINA 1: DASHBOARD
-- ============================================================================
-- Tipo: Home Page
-- Template: Standard
-- Theme: Universal Theme

/*
================================================================================
REGIAO 1: Cards de Resumo (Hero Region)
================================================================================
Tipo: Cards
Posicao: Body (1)
Template: Cards Container
*/

-- Source SQL para Cards
-- Card Region Source Type: SQL Query
/*
SELECT
    'Contratos Ativos' AS card_title,
    TO_CHAR(COUNT(*)) AS card_text,
    'fa-file-contract' AS card_icon,
    'u-color-1' AS card_color,
    'f?p=&APP_ID.:100:&SESSION.::NO::P100_STATUS:ATIVO' AS card_link
FROM gc_contrato
WHERE status = 'ATIVO'
UNION ALL
SELECT
    'Parcelas Vencidas',
    TO_CHAR(COUNT(*)),
    'fa-exclamation-triangle',
    'u-color-3',
    'f?p=&APP_ID.:210:&SESSION.'
FROM gc_parcela
WHERE pago = 0 AND data_vencimento < TRUNC(SYSDATE)
UNION ALL
SELECT
    'A Receber (30 dias)',
    TO_CHAR(NVL(SUM(valor_atual), 0), 'L999G999G999D99', 'NLS_CURRENCY=R$'),
    'fa-money-bill',
    'u-color-5',
    'f?p=&APP_ID.:200:&SESSION.'
FROM gc_parcela
WHERE pago = 0
  AND data_vencimento BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 30
UNION ALL
SELECT
    'Valor em Atraso',
    TO_CHAR(NVL(SUM(valor_atual), 0), 'L999G999G999D99', 'NLS_CURRENCY=R$'),
    'fa-clock',
    'u-color-4',
    'f?p=&APP_ID.:210:&SESSION.'
FROM gc_parcela
WHERE pago = 0 AND data_vencimento < TRUNC(SYSDATE)
*/

/*
================================================================================
REGIAO 2: Grafico de Receitas Mensais
================================================================================
Tipo: Chart
Posicao: Body (2)
Template: Standard
*/

-- Chart: Line Chart - Receitas dos ultimos 12 meses
-- Source SQL:
/*
SELECT
    TO_CHAR(data_pagamento, 'MM/YYYY') AS periodo,
    TO_DATE(TO_CHAR(data_pagamento, 'MM/YYYY'), 'MM/YYYY') AS periodo_order,
    SUM(valor_pago) AS valor_recebido
FROM gc_parcela
WHERE pago = 1
  AND data_pagamento >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -11)
GROUP BY TO_CHAR(data_pagamento, 'MM/YYYY'),
         TO_DATE(TO_CHAR(data_pagamento, 'MM/YYYY'), 'MM/YYYY')
ORDER BY periodo_order
*/

-- Chart Settings:
-- Type: Line
-- Label Column: PERIODO
-- Value Column: VALOR_RECEBIDO
-- Title: Receitas Mensais

/*
================================================================================
REGIAO 3: Parcelas a Vencer (Proximos 7 dias)
================================================================================
Tipo: Classic Report
Posicao: Body (3)
Template: Standard
*/

-- Source SQL:
/*
SELECT
    p.id,
    c.numero_contrato,
    comp.nome AS comprador,
    p.numero_parcela || '/' || c.numero_parcelas AS parcela,
    p.data_vencimento,
    p.valor_atual,
    CASE
        WHEN p.data_vencimento = TRUNC(SYSDATE) THEN 'Vence Hoje'
        WHEN p.data_vencimento = TRUNC(SYSDATE) + 1 THEN 'Vence Amanha'
        ELSE 'Vence em ' || (p.data_vencimento - TRUNC(SYSDATE)) || ' dias'
    END AS situacao,
    CASE
        WHEN p.data_vencimento = TRUNC(SYSDATE) THEN 'u-danger'
        WHEN p.data_vencimento <= TRUNC(SYSDATE) + 3 THEN 'u-warning'
        ELSE 'u-success'
    END AS css_class
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE p.pago = 0
  AND p.data_vencimento BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 7
ORDER BY p.data_vencimento
FETCH FIRST 10 ROWS ONLY
*/

/*
================================================================================
REGIAO 4: Parcelas Vencidas (Top 10)
================================================================================
Tipo: Classic Report
Posicao: Body (4)
Template: Standard
*/

-- Source SQL:
/*
SELECT
    p.id,
    c.numero_contrato,
    comp.nome AS comprador,
    comp.celular,
    p.numero_parcela || '/' || c.numero_parcelas AS parcela,
    p.data_vencimento,
    TRUNC(SYSDATE) - p.data_vencimento AS dias_atraso,
    p.valor_atual + NVL(p.valor_juros, 0) + NVL(p.valor_multa, 0) AS valor_total
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE p.pago = 0
  AND p.data_vencimento < TRUNC(SYSDATE)
ORDER BY dias_atraso DESC
FETCH FIRST 10 ROWS ONLY
*/

/*
================================================================================
REGIAO 5: Resumo por Imobiliaria
================================================================================
Tipo: Classic Report
Posicao: Body (5)
Template: Collapsible
*/

-- Source SQL:
/*
SELECT
    imobiliaria_nome,
    contratos_ativos,
    parcelas_pagas || '/' || total_parcelas AS parcelas,
    ROUND(parcelas_pagas * 100.0 / NULLIF(total_parcelas, 0), 1) || '%' AS progresso,
    TO_CHAR(valor_recebido, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS recebido,
    TO_CHAR(valor_a_receber, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS a_receber,
    parcelas_vencidas
FROM vw_dashboard_imobiliaria
ORDER BY imobiliaria_nome
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Novo Contrato
-- Position: Right of Title
-- Action: Redirect to Page 110

-- Botao: Gerar Boletos
-- Position: Right of Title
-- Action: Redirect to Page 310

/*
================================================================================
PAGE LOAD - DYNAMIC ACTIONS
================================================================================
*/

-- DA: Atualizar cards a cada 5 minutos
-- Event: Page Load
-- True Action: Execute JavaScript
/*
setInterval(function() {
    apex.region('cards_resumo').refresh();
}, 300000);
*/
