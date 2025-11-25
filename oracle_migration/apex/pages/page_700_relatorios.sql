/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 700-750: Relatorios
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================
*/

-- ============================================================================
-- PAGINA 700: CENTRAL DE RELATORIOS
-- ============================================================================
-- Tipo: Navigation Cards
-- Template: Standard

/*
================================================================================
REGIAO: Cards de Relatorios
================================================================================
*/

-- Type: Cards (Static)
/*
<div class="t-Cards t-Cards--compact t-Cards--displayInitials t-Cards--4cols">

    <div class="t-Card">
        <a href="f?p=&APP_ID.:710:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-1"><span class="fa fa-file-text"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Contratos Ativos</h3>
                <h4 class="t-Card-subtitle">Lista completa de contratos</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:720:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-2"><span class="fa fa-clock-o"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Parcelas Vencidas</h3>
                <h4 class="t-Card-subtitle">Inadimplencia por periodo</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:730:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-3"><span class="fa fa-calendar"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Parcelas a Vencer</h3>
                <h4 class="t-Card-subtitle">Previsao de recebimentos</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:740:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-4"><span class="fa fa-money"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Fluxo de Caixa</h3>
                <h4 class="t-Card-subtitle">Recebimentos x Previsoes</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:750:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-5"><span class="fa fa-users"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Compradores</h3>
                <h4 class="t-Card-subtitle">Cadastro de clientes</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:760:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-6"><span class="fa fa-map-marker"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Imoveis</h3>
                <h4 class="t-Card-subtitle">Disponibilidade e vendas</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:770:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-7"><span class="fa fa-bar-chart"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Comissoes</h3>
                <h4 class="t-Card-subtitle">Vendas por corretor</h4>
            </div>
        </a>
    </div>

    <div class="t-Card">
        <a href="f?p=&APP_ID.:780:&SESSION." class="t-Card-wrap">
            <div class="t-Card-icon u-color-8"><span class="fa fa-pie-chart"></span></div>
            <div class="t-Card-titleWrap">
                <h3 class="t-Card-title">Dashboard Gerencial</h3>
                <h4 class="t-Card-subtitle">Visao consolidada</h4>
            </div>
        </a>
    </div>

</div>
*/

-- ============================================================================
-- PAGINA 710: RELATORIO - CONTRATOS ATIVOS
-- ============================================================================

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P710_IMOBILIARIA_ID
-- P710_STATUS (ATIVO, QUITADO, CANCELADO, TODOS)
-- P710_DATA_INI
-- P710_DATA_FIM
-- P710_LOTEAMENTO

/*
================================================================================
REGIAO: Interactive Report - Contratos
================================================================================
*/

-- Source SQL:
/*
SELECT
    c.id,
    c.numero_contrato,
    im.nome AS imobiliaria,
    comp.nome AS comprador,
    COALESCE(comp.cpf, comp.cnpj) AS documento,
    i.loteamento,
    i.identificacao AS imovel,
    c.status,
    TO_CHAR(c.data_contrato, 'DD/MM/YYYY') AS data_contrato,
    c.quantidade_parcelas,
    TO_CHAR(c.valor_total, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total,
    TO_CHAR(c.valor_entrada, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS entrada,
    TO_CHAR(c.valor_parcela_atual, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS parcela_atual,
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id AND p.status = 'PAGO') AS parcelas_pagas,
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id AND p.status = 'PENDENTE') AS parcelas_pendentes,
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id AND p.status = 'PENDENTE' AND p.data_vencimento < TRUNC(SYSDATE)) AS parcelas_vencidas,
    pkg_contrato.calcular_progresso(c.id) AS progresso,
    TO_CHAR(pkg_contrato.calcular_valor_pago(c.id), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_pago,
    TO_CHAR(pkg_contrato.calcular_saldo_devedor(c.id), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS saldo_devedor
FROM gc_contrato c
JOIN gc_imobiliaria im ON im.id = c.imobiliaria_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imovel i ON i.id = c.imovel_id
WHERE (:P710_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P710_IMOBILIARIA_ID)
  AND (:P710_STATUS IS NULL OR :P710_STATUS = 'TODOS' OR c.status = :P710_STATUS)
  AND (:P710_DATA_INI IS NULL OR c.data_contrato >= TO_DATE(:P710_DATA_INI, 'DD/MM/YYYY'))
  AND (:P710_DATA_FIM IS NULL OR c.data_contrato <= TO_DATE(:P710_DATA_FIM, 'DD/MM/YYYY'))
  AND (:P710_LOTEAMENTO IS NULL OR UPPER(i.loteamento) LIKE '%' || UPPER(:P710_LOTEAMENTO) || '%')
ORDER BY c.numero_contrato
*/

/*
================================================================================
REGIAO: Totalizadores
================================================================================
*/

-- Source SQL:
/*
SELECT
    COUNT(*) AS total_contratos,
    TO_CHAR(SUM(c.valor_total), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total,
    TO_CHAR(SUM(pkg_contrato.calcular_valor_pago(c.id)), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS total_pago,
    TO_CHAR(SUM(pkg_contrato.calcular_saldo_devedor(c.id)), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS total_saldo
FROM gc_contrato c
WHERE (:P710_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P710_IMOBILIARIA_ID)
  AND (:P710_STATUS IS NULL OR :P710_STATUS = 'TODOS' OR c.status = :P710_STATUS)
*/

-- ============================================================================
-- PAGINA 720: RELATORIO - PARCELAS VENCIDAS (Inadimplencia)
-- ============================================================================

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P720_IMOBILIARIA_ID
-- P720_DIAS_ATRASO_MIN (ex: 1, 30, 60, 90)
-- P720_DIAS_ATRASO_MAX
-- P720_ORDENAR (DIAS_ATRASO, VALOR, COMPRADOR)

/*
================================================================================
REGIAO: Cards Resumo
================================================================================
*/

-- Source SQL:
/*
SELECT
    'Total Vencidas' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-exclamation-circle' AS icone,
    'u-danger' AS css
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
WHERE p.status = 'PENDENTE'
  AND p.data_vencimento < TRUNC(SYSDATE)
  AND (:P720_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P720_IMOBILIARIA_ID)
UNION ALL
SELECT
    'Valor Total' AS titulo,
    TO_CHAR(SUM(p.valor_parcela), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    'fa-money' AS icone,
    'u-hot' AS css
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
WHERE p.status = 'PENDENTE'
  AND p.data_vencimento < TRUNC(SYSDATE)
  AND (:P720_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P720_IMOBILIARIA_ID)
*/

/*
================================================================================
REGIAO: Interactive Report - Parcelas Vencidas
================================================================================
*/

-- Source SQL:
/*
SELECT
    p.id,
    c.numero_contrato,
    comp.nome AS comprador,
    comp.celular,
    comp.email,
    i.identificacao AS imovel,
    p.numero_parcela,
    TO_CHAR(p.data_vencimento, 'DD/MM/YYYY') AS vencimento,
    TRUNC(SYSDATE) - p.data_vencimento AS dias_atraso,
    TO_CHAR(p.valor_parcela, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_original,
    TO_CHAR(pkg_contrato.calcular_juros_multa(p.id), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS encargos,
    TO_CHAR(p.valor_parcela + pkg_contrato.calcular_juros_multa(p.id), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_atualizado,
    CASE
        WHEN TRUNC(SYSDATE) - p.data_vencimento <= 30 THEN 'Ate 30 dias'
        WHEN TRUNC(SYSDATE) - p.data_vencimento <= 60 THEN '31-60 dias'
        WHEN TRUNC(SYSDATE) - p.data_vencimento <= 90 THEN '61-90 dias'
        ELSE 'Mais de 90 dias'
    END AS faixa_atraso,
    CASE
        WHEN TRUNC(SYSDATE) - p.data_vencimento <= 30 THEN 'u-warning'
        WHEN TRUNC(SYSDATE) - p.data_vencimento <= 60 THEN 'u-hot'
        ELSE 'u-danger'
    END AS faixa_css,
    (SELECT MAX(n.criado_em) FROM gc_notificacao n WHERE n.contrato_id = c.id AND n.tipo = 'COBRANCA') AS ultima_cobranca
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imovel i ON i.id = c.imovel_id
WHERE p.status = 'PENDENTE'
  AND p.data_vencimento < TRUNC(SYSDATE)
  AND c.status = 'ATIVO'
  AND (:P720_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P720_IMOBILIARIA_ID)
  AND (:P720_DIAS_ATRASO_MIN IS NULL OR TRUNC(SYSDATE) - p.data_vencimento >= :P720_DIAS_ATRASO_MIN)
  AND (:P720_DIAS_ATRASO_MAX IS NULL OR TRUNC(SYSDATE) - p.data_vencimento <= :P720_DIAS_ATRASO_MAX)
ORDER BY
    CASE :P720_ORDENAR
        WHEN 'DIAS_ATRASO' THEN TRUNC(SYSDATE) - p.data_vencimento
        WHEN 'VALOR' THEN p.valor_parcela
    END DESC,
    comp.nome
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Enviar Cobrancas
-- Action: Open Modal (selecionar parcelas e enviar notificacao)

-- Botao: Exportar Excel
-- Action: Download IR

-- ============================================================================
-- PAGINA 730: RELATORIO - PARCELAS A VENCER
-- ============================================================================

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P730_IMOBILIARIA_ID
-- P730_DIAS_FUTURO (7, 15, 30, 60)
-- P730_AGRUPAR (COMPRADOR, DATA, IMOVEL)

/*
================================================================================
REGIAO: Interactive Report - Parcelas a Vencer
================================================================================
*/

-- Source SQL:
/*
SELECT
    p.id,
    c.numero_contrato,
    comp.nome AS comprador,
    i.identificacao AS imovel,
    p.numero_parcela,
    TO_CHAR(p.data_vencimento, 'DD/MM/YYYY') AS vencimento,
    p.data_vencimento - TRUNC(SYSDATE) AS dias_para_vencer,
    TO_CHAR(p.valor_parcela, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    CASE p.boleto_gerado WHEN 1 THEN 'Sim' ELSE 'Nao' END AS boleto_gerado,
    CASE
        WHEN p.data_vencimento - TRUNC(SYSDATE) <= 3 THEN 'u-hot'
        WHEN p.data_vencimento - TRUNC(SYSDATE) <= 7 THEN 'u-warning'
        ELSE 'u-success'
    END AS dias_css
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imovel i ON i.id = c.imovel_id
WHERE p.status = 'PENDENTE'
  AND p.data_vencimento >= TRUNC(SYSDATE)
  AND p.data_vencimento <= TRUNC(SYSDATE) + NVL(:P730_DIAS_FUTURO, 30)
  AND c.status = 'ATIVO'
  AND (:P730_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P730_IMOBILIARIA_ID)
ORDER BY p.data_vencimento, comp.nome
*/

/*
================================================================================
REGIAO: Totais por Semana
================================================================================
*/

-- Type: Chart (Bar)
-- Source SQL:
/*
SELECT
    TO_CHAR(TRUNC(data_vencimento, 'IW'), 'DD/MM') AS semana,
    SUM(valor_parcela) AS valor
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
WHERE p.status = 'PENDENTE'
  AND p.data_vencimento BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 60
  AND c.status = 'ATIVO'
  AND (:P730_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P730_IMOBILIARIA_ID)
GROUP BY TRUNC(data_vencimento, 'IW')
ORDER BY TRUNC(data_vencimento, 'IW')
*/

-- ============================================================================
-- PAGINA 740: RELATORIO - FLUXO DE CAIXA
-- ============================================================================

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P740_IMOBILIARIA_ID
-- P740_ANO
-- P740_TIPO (MENSAL, DIARIO)

/*
================================================================================
REGIAO: Grafico - Fluxo de Caixa Mensal
================================================================================
*/

-- Type: Chart (Combination - Bar + Line)
-- Source SQL:
/*
SELECT
    TO_CHAR(mes, 'MM/YYYY') AS periodo,
    recebido,
    previsto,
    ROUND(recebido / NULLIF(previsto, 0) * 100, 1) AS taxa_realizacao
FROM (
    SELECT
        TRUNC(data_vencimento, 'MM') AS mes,
        SUM(CASE WHEN status = 'PAGO' THEN valor_pago ELSE 0 END) AS recebido,
        SUM(valor_parcela) AS previsto
    FROM gc_parcela p
    JOIN gc_contrato c ON c.id = p.contrato_id
    WHERE EXTRACT(YEAR FROM p.data_vencimento) = :P740_ANO
      AND (:P740_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P740_IMOBILIARIA_ID)
    GROUP BY TRUNC(data_vencimento, 'MM')
)
ORDER BY mes
*/

/*
================================================================================
REGIAO: Tabela Fluxo de Caixa
================================================================================
*/

-- Type: Classic Report
-- Source SQL:
/*
SELECT
    TO_CHAR(mes, 'Month/YYYY', 'NLS_DATE_LANGUAGE=PORTUGUESE') AS periodo,
    TO_CHAR(previsto, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS previsto,
    TO_CHAR(recebido, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS recebido,
    TO_CHAR(previsto - recebido, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS diferenca,
    ROUND(recebido / NULLIF(previsto, 0) * 100, 1) || '%' AS taxa
FROM (
    SELECT
        TRUNC(data_vencimento, 'MM') AS mes,
        SUM(CASE WHEN status = 'PAGO' THEN valor_pago ELSE 0 END) AS recebido,
        SUM(valor_parcela) AS previsto
    FROM gc_parcela p
    JOIN gc_contrato c ON c.id = p.contrato_id
    WHERE EXTRACT(YEAR FROM p.data_vencimento) = :P740_ANO
      AND (:P740_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P740_IMOBILIARIA_ID)
    GROUP BY TRUNC(data_vencimento, 'MM')
)
ORDER BY mes
*/

-- ============================================================================
-- PAGINA 750: RELATORIO - COMPRADORES
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Compradores
================================================================================
*/

-- Source SQL:
/*
SELECT
    comp.id,
    comp.nome,
    CASE comp.tipo_pessoa WHEN 'PF' THEN 'Pessoa Fisica' ELSE 'Pessoa Juridica' END AS tipo,
    COALESCE(comp.cpf, comp.cnpj) AS documento,
    comp.email,
    comp.celular,
    comp.cidade || '/' || comp.estado AS cidade_uf,
    (SELECT COUNT(*) FROM gc_contrato c WHERE c.comprador_id = comp.id) AS total_contratos,
    (SELECT COUNT(*) FROM gc_contrato c WHERE c.comprador_id = comp.id AND c.status = 'ATIVO') AS contratos_ativos,
    TO_CHAR(
        (SELECT SUM(valor_total) FROM gc_contrato c WHERE c.comprador_id = comp.id),
        'L999G999G999D99', 'NLS_CURRENCY=R$'
    ) AS valor_total_contratos,
    TO_CHAR(
        (SELECT SUM(valor_pago) FROM gc_parcela p
         JOIN gc_contrato c ON c.id = p.contrato_id
         WHERE c.comprador_id = comp.id AND p.status = 'PAGO'),
        'L999G999G999D99', 'NLS_CURRENCY=R$'
    ) AS total_pago,
    (SELECT COUNT(*) FROM gc_parcela p
     JOIN gc_contrato c ON c.id = p.contrato_id
     WHERE c.comprador_id = comp.id AND p.status = 'PENDENTE' AND p.data_vencimento < TRUNC(SYSDATE)
    ) AS parcelas_atrasadas
FROM gc_comprador comp
WHERE comp.ativo = 1
ORDER BY comp.nome
*/

-- ============================================================================
-- PAGINA 760: RELATORIO - IMOVEIS
-- ============================================================================

/*
================================================================================
REGIAO: Cards Resumo
================================================================================
*/

-- Source SQL:
/*
SELECT
    'Total Imoveis' AS titulo, COUNT(*) AS valor, 'fa-home' AS icone, 'u-color-1' AS css
FROM gc_imovel WHERE ativo = 1
UNION ALL
SELECT
    'Disponiveis' AS titulo, COUNT(*) AS valor, 'fa-check-circle' AS icone, 'u-success' AS css
FROM gc_imovel WHERE ativo = 1 AND disponivel = 1
UNION ALL
SELECT
    'Vendidos' AS titulo, COUNT(*) AS valor, 'fa-handshake-o' AS icone, 'u-warning' AS css
FROM gc_imovel WHERE ativo = 1 AND disponivel = 0
UNION ALL
SELECT
    'Valor Total' AS titulo,
    TO_CHAR(SUM(valor), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    'fa-money' AS icone, 'u-color-4' AS css
FROM gc_imovel WHERE ativo = 1
*/

/*
================================================================================
REGIAO: Interactive Report - Imoveis
================================================================================
*/

-- Source SQL:
/*
SELECT
    i.id,
    i.identificacao,
    i.loteamento,
    ti.descricao AS tipo,
    i.area || ' m²' AS area,
    TO_CHAR(i.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    i.matricula,
    i.cidade || '/' || i.estado AS localizacao,
    CASE i.disponivel WHEN 1 THEN 'Disponivel' ELSE 'Vendido' END AS status,
    CASE i.disponivel WHEN 1 THEN 'u-success' ELSE 'u-warning' END AS status_css,
    im.nome AS imobiliaria,
    -- Se vendido, mostrar dados do contrato
    (SELECT c.numero_contrato FROM gc_contrato c WHERE c.imovel_id = i.id AND c.status = 'ATIVO') AS contrato,
    (SELECT comp.nome FROM gc_contrato c JOIN gc_comprador comp ON comp.id = c.comprador_id WHERE c.imovel_id = i.id AND c.status = 'ATIVO') AS comprador
FROM gc_imovel i
JOIN gc_imobiliaria im ON im.id = i.imobiliaria_id
LEFT JOIN gc_tipo_imovel ti ON ti.codigo = i.tipo
WHERE i.ativo = 1
  AND (:P760_IMOBILIARIA_ID IS NULL OR i.imobiliaria_id = :P760_IMOBILIARIA_ID)
  AND (:P760_DISPONIVEL IS NULL OR i.disponivel = :P760_DISPONIVEL)
  AND (:P760_LOTEAMENTO IS NULL OR UPPER(i.loteamento) LIKE '%' || UPPER(:P760_LOTEAMENTO) || '%')
ORDER BY i.loteamento, i.identificacao
*/

-- ============================================================================
-- PAGINA 780: DASHBOARD GERENCIAL
-- ============================================================================

/*
================================================================================
REGIAO: KPIs Principais
================================================================================
*/

-- Cards com metricas principais:
-- - Total de Contratos Ativos
-- - Valor Total em Carteira
-- - Inadimplencia (%)
-- - Recebimentos do Mes

/*
================================================================================
REGIAO: Grafico - Vendas por Mes
================================================================================
*/

-- Type: Chart (Bar)
-- Source: Contratos por mes de assinatura

/*
================================================================================
REGIAO: Grafico - Inadimplencia
================================================================================
*/

-- Type: Chart (Gauge)
-- Source: % de parcelas vencidas / total

/*
================================================================================
REGIAO: Top 5 Loteamentos
================================================================================
*/

-- Source SQL:
/*
SELECT
    i.loteamento,
    COUNT(DISTINCT c.id) AS contratos,
    TO_CHAR(SUM(c.valor_total), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total
FROM gc_contrato c
JOIN gc_imovel i ON i.id = c.imovel_id
WHERE c.status = 'ATIVO'
GROUP BY i.loteamento
ORDER BY COUNT(*) DESC
FETCH FIRST 5 ROWS ONLY
*/

/*
================================================================================
REGIAO: Mapa de Calor - Recebimentos
================================================================================
*/

-- Type: Calendar Heatmap
-- Source: Pagamentos por dia

