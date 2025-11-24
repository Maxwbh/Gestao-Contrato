/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 100-120: Contratos e Parcelas
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
==============================================================================
*/

-- ============================================================================
-- PAGINA 100: LISTA DE CONTRATOS
-- ============================================================================

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
    c.data_contrato,
    c.data_primeiro_vencimento,
    c.valor_total,
    c.valor_entrada,
    c.valor_financiado,
    c.numero_parcelas,
    c.status,
    sc.descricao AS status_desc,
    CASE c.status
        WHEN 'ATIVO' THEN 'u-success'
        WHEN 'QUITADO' THEN 'u-color-1'
        WHEN 'CANCELADO' THEN 'u-danger'
        WHEN 'SUSPENSO' THEN 'u-warning'
    END AS status_css,
    c.tipo_correcao,
    tc.descricao AS tipo_correcao_desc,
    -- Imovel
    i.identificacao AS imovel,
    i.loteamento,
    -- Comprador
    comp.nome AS comprador,
    COALESCE(comp.cpf, comp.cnpj) AS comprador_doc,
    comp.celular AS comprador_celular,
    -- Imobiliaria
    imob.nome AS imobiliaria,
    -- Calculos
    pkg_contrato.calcular_progresso(c.id) AS progresso,
    pkg_contrato.calcular_saldo_devedor(c.id) AS saldo_devedor,
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id AND p.pago = 0 AND p.data_vencimento < TRUNC(SYSDATE)) AS parcelas_vencidas
FROM gc_contrato c
JOIN gc_imovel i ON i.id = c.imovel_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria imob ON imob.id = c.imobiliaria_id
LEFT JOIN gc_status_contrato sc ON sc.codigo = c.status
LEFT JOIN gc_tipo_correcao tc ON tc.codigo = c.tipo_correcao
WHERE (:P100_STATUS IS NULL OR c.status = :P100_STATUS)
  AND (:P100_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P100_IMOBILIARIA_ID)
  AND (:P100_BUSCA IS NULL OR
       UPPER(c.numero_contrato) LIKE '%' || UPPER(:P100_BUSCA) || '%' OR
       UPPER(comp.nome) LIKE '%' || UPPER(:P100_BUSCA) || '%' OR
       comp.cpf LIKE '%' || :P100_BUSCA || '%')
ORDER BY c.data_contrato DESC, c.numero_contrato
*/

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P100_STATUS
-- Type: Select List
-- LOV: SELECT descricao d, codigo r FROM gc_status_contrato ORDER BY codigo
-- Display Null: Yes (Todos)

-- P100_IMOBILIARIA_ID
-- Type: Select List
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes (Todas)

-- P100_BUSCA
-- Type: Text Field
-- Label: Buscar (Contrato, Comprador, CPF)
-- Submit on Enter: Yes

/*
================================================================================
COLUNAS ESPECIAIS
================================================================================
*/

-- Coluna PROGRESSO - HTML Expression:
/*
<div class="t-Progress t-Progress--small">
    <div class="t-Progress-bar" style="width: #PROGRESSO#%;">
        <span class="t-Progress-label">#PROGRESSO#%</span>
    </div>
</div>
*/

-- Coluna STATUS_DESC - HTML Expression:
/*
<span class="u-badge #STATUS_CSS#">#STATUS_DESC#</span>
*/

-- Coluna PARCELAS_VENCIDAS - HTML Expression (se > 0):
/*
<span class="u-badge u-danger">#PARCELAS_VENCIDAS# vencida(s)</span>
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Novo Contrato
-- Position: Right of Search Bar
-- Action: Redirect to Page 110
-- Hot: Yes

/*
================================================================================
ROW ACTIONS
================================================================================
*/

-- Action: Ver Parcelas
-- Icon: fa-list
-- Target: Page 120, P120_CONTRATO_ID=#ID#

-- Action: Gerar Boletos
-- Icon: fa-barcode
-- Target: Page 310, P310_CONTRATO_ID=#ID#

-- Action: Editar
-- Icon: fa-pencil
-- Target: Page 110, P110_ID=#ID#

-- ============================================================================
-- PAGINA 110: FORMULARIO DE CONTRATO (WIZARD)
-- ============================================================================

/*
================================================================================
WIZARD STEP 1: Dados Basicos
================================================================================
*/

-- P110_ID (Hidden, PK)

-- P110_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Cascade: Atualiza LOV de Imoveis

-- P110_NUMERO_CONTRATO
-- Type: Text Field
-- Label: Numero do Contrato
-- Required: Yes
-- Unique: Yes

-- P110_DATA_CONTRATO
-- Type: Date Picker
-- Label: Data do Contrato
-- Required: Yes
-- Default: SYSDATE

-- P110_STATUS
-- Type: Select List
-- Label: Status
-- Required: Yes
-- LOV: SELECT descricao d, codigo r FROM gc_status_contrato
-- Default: ATIVO
-- Read Only: When P110_ID is not null (exceto admin)

/*
================================================================================
WIZARD STEP 2: Imovel
================================================================================
*/

-- P110_IMOVEL_ID
-- Type: Select List (ou Popup LOV)
-- Label: Imovel
-- Required: Yes
-- LOV: (Cascade from Imobiliaria)
/*
SELECT
    COALESCE(loteamento || ' - ', '') || identificacao || ' (' || ti.descricao || ' - ' || area || ' m²)' AS d,
    i.id AS r
FROM gc_imovel i
LEFT JOIN gc_tipo_imovel ti ON ti.codigo = i.tipo
WHERE i.imobiliaria_id = :P110_IMOBILIARIA_ID
  AND i.disponivel = 1
  AND i.ativo = 1
ORDER BY i.loteamento, i.identificacao
*/

-- Display Only: Detalhes do Imovel selecionado
-- P110_IMOVEL_DISPLAY (Read Only)
-- Source: Based on P110_IMOVEL_ID

/*
================================================================================
WIZARD STEP 3: Comprador
================================================================================
*/

-- P110_COMPRADOR_ID
-- Type: Popup LOV
-- Label: Comprador
-- Required: Yes
-- LOV:
/*
SELECT
    nome || ' - ' || COALESCE(cpf, cnpj) AS d,
    id AS r
FROM gc_comprador
WHERE ativo = 1
ORDER BY nome
*/

-- Botao: Novo Comprador
-- Action: Redirect to Page 51 (Dialog Mode)

-- Display Only: Detalhes do Comprador
-- P110_COMPRADOR_DISPLAY (Read Only)

/*
================================================================================
WIZARD STEP 4: Valores e Parcelas
================================================================================
*/

-- P110_VALOR_TOTAL
-- Type: Number Field
-- Label: Valor Total do Contrato
-- Required: Yes
-- Format: 999G999G999D99

-- P110_VALOR_ENTRADA
-- Type: Number Field
-- Label: Valor de Entrada
-- Default: 0
-- Format: 999G999G999D99

-- P110_VALOR_FINANCIADO (Read Only - Calculado)
-- Type: Display Only
-- Label: Valor Financiado
-- Source: P110_VALOR_TOTAL - P110_VALOR_ENTRADA

-- P110_NUMERO_PARCELAS
-- Type: Number Field
-- Label: Numero de Parcelas
-- Required: Yes
-- Min: 1
-- Max: 600

-- P110_VALOR_PARCELA (Read Only - Calculado)
-- Type: Display Only
-- Label: Valor da Parcela
-- Source: (P110_VALOR_TOTAL - P110_VALOR_ENTRADA) / P110_NUMERO_PARCELAS

-- P110_DATA_PRIMEIRO_VENCIMENTO
-- Type: Date Picker
-- Label: Data do Primeiro Vencimento
-- Required: Yes

-- P110_DIA_VENCIMENTO
-- Type: Number Field
-- Label: Dia de Vencimento
-- Required: Yes
-- Min: 1
-- Max: 31

/*
================================================================================
WIZARD STEP 5: Juros, Multa e Correcao
================================================================================
*/

-- P110_PERCENTUAL_JUROS_MORA
-- Type: Number Field
-- Label: Juros de Mora (% ao mes)
-- Default: 1.00
-- Format: 999D99

-- P110_PERCENTUAL_MULTA
-- Type: Number Field
-- Label: Multa (%)
-- Default: 2.00
-- Format: 999D99

-- P110_TIPO_CORRECAO
-- Type: Select List
-- Label: Tipo de Correcao Monetaria
-- Required: Yes
-- LOV: SELECT descricao d, codigo r FROM gc_tipo_correcao ORDER BY descricao
-- Default: IPCA

-- P110_PRAZO_REAJUSTE_MESES
-- Type: Number Field
-- Label: Prazo para Reajuste (meses)
-- Default: 12

/*
================================================================================
WIZARD STEP 6: Configuracoes de Boleto
================================================================================
*/

-- P110_USAR_CONFIG_BOLETO_IMOBILIARIA
-- Type: Switch
-- Label: Usar Configuracoes da Imobiliaria
-- Default: 1

-- (Campos condicionais quando Switch = 0)
-- P110_CONTA_BANCARIA_PADRAO_ID
-- P110_TIPO_VALOR_MULTA, P110_VALOR_MULTA_BOLETO
-- P110_TIPO_VALOR_JUROS, P110_VALOR_JUROS_BOLETO
-- P110_DIAS_CARENCIA_BOLETO
-- P110_INSTRUCAO_BOLETO_1, P110_INSTRUCAO_BOLETO_2

/*
================================================================================
WIZARD STEP 7: Confirmacao
================================================================================
*/

-- Regiao: Resumo do Contrato
-- Type: Static Content
-- Template: Alert (Info)

/*
<h3>Resumo do Contrato</h3>
<table class="t-Report">
    <tr><th>Numero:</th><td>&P110_NUMERO_CONTRATO.</td></tr>
    <tr><th>Comprador:</th><td>&P110_COMPRADOR_DISPLAY.</td></tr>
    <tr><th>Imovel:</th><td>&P110_IMOVEL_DISPLAY.</td></tr>
    <tr><th>Valor Total:</th><td>R$ &P110_VALOR_TOTAL.</td></tr>
    <tr><th>Entrada:</th><td>R$ &P110_VALOR_ENTRADA.</td></tr>
    <tr><th>Financiado:</th><td>R$ &P110_VALOR_FINANCIADO.</td></tr>
    <tr><th>Parcelas:</th><td>&P110_NUMERO_PARCELAS. x R$ &P110_VALOR_PARCELA.</td></tr>
    <tr><th>Primeiro Vencimento:</th><td>&P110_DATA_PRIMEIRO_VENCIMENTO.</td></tr>
</table>
*/

-- Checkbox: Gerar parcelas automaticamente
-- P110_GERAR_PARCELAS
-- Type: Checkbox
-- Default: Y

-- Checkbox: Gerar boletos automaticamente
-- P110_GERAR_BOLETOS
-- Type: Checkbox
-- Default: N

/*
================================================================================
PROCESSES
================================================================================
*/

-- Process: Initialize Form
-- Type: Form Initialization
-- When: Before Header

-- Process: Save Contract
-- Type: PL/SQL Code
-- When: On Submit

/*
BEGIN
    IF :P110_ID IS NULL THEN
        -- Insert
        INSERT INTO gc_contrato (
            imobiliaria_id, imovel_id, comprador_id,
            numero_contrato, data_contrato, data_primeiro_vencimento,
            valor_total, valor_entrada, numero_parcelas, dia_vencimento,
            percentual_juros_mora, percentual_multa,
            tipo_correcao, prazo_reajuste_meses, status,
            usar_config_boleto_imobiliaria, conta_bancaria_padrao_id
        ) VALUES (
            :P110_IMOBILIARIA_ID, :P110_IMOVEL_ID, :P110_COMPRADOR_ID,
            :P110_NUMERO_CONTRATO, :P110_DATA_CONTRATO, :P110_DATA_PRIMEIRO_VENCIMENTO,
            :P110_VALOR_TOTAL, NVL(:P110_VALOR_ENTRADA, 0), :P110_NUMERO_PARCELAS, :P110_DIA_VENCIMENTO,
            NVL(:P110_PERCENTUAL_JUROS_MORA, 1), NVL(:P110_PERCENTUAL_MULTA, 2),
            :P110_TIPO_CORRECAO, NVL(:P110_PRAZO_REAJUSTE_MESES, 12), :P110_STATUS,
            :P110_USAR_CONFIG_BOLETO_IMOBILIARIA, :P110_CONTA_BANCARIA_PADRAO_ID
        ) RETURNING id INTO :P110_ID;
    ELSE
        -- Update
        UPDATE gc_contrato SET
            imobiliaria_id = :P110_IMOBILIARIA_ID,
            imovel_id = :P110_IMOVEL_ID,
            comprador_id = :P110_COMPRADOR_ID,
            numero_contrato = :P110_NUMERO_CONTRATO,
            data_contrato = :P110_DATA_CONTRATO,
            percentual_juros_mora = :P110_PERCENTUAL_JUROS_MORA,
            percentual_multa = :P110_PERCENTUAL_MULTA,
            tipo_correcao = :P110_TIPO_CORRECAO,
            prazo_reajuste_meses = :P110_PRAZO_REAJUSTE_MESES,
            status = :P110_STATUS,
            usar_config_boleto_imobiliaria = :P110_USAR_CONFIG_BOLETO_IMOBILIARIA,
            conta_bancaria_padrao_id = :P110_CONTA_BANCARIA_PADRAO_ID,
            observacoes = :P110_OBSERVACOES
        WHERE id = :P110_ID;
    END IF;
END;
*/

-- Process: Generate Installments
-- Type: PL/SQL Code
-- Condition: P110_GERAR_PARCELAS = 'Y' AND P110_ID is not null (new record)

/*
DECLARE
    v_msg VARCHAR2(4000);
BEGIN
    pkg_contrato.gerar_parcelas(
        p_contrato_id   => :P110_ID,
        p_gerar_boletos => :P110_GERAR_BOLETOS = 'Y',
        p_msg_erro      => v_msg
    );

    IF v_msg IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20001, v_msg);
    END IF;
END;
*/

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Calcular Valor Financiado
-- Event: Change
-- Selection: P110_VALOR_TOTAL, P110_VALOR_ENTRADA
/*
var total = parseFloat($v('P110_VALOR_TOTAL')) || 0;
var entrada = parseFloat($v('P110_VALOR_ENTRADA')) || 0;
var financiado = total - entrada;
$s('P110_VALOR_FINANCIADO', financiado.toFixed(2));

// Recalcular parcela
var parcelas = parseInt($v('P110_NUMERO_PARCELAS')) || 1;
$s('P110_VALOR_PARCELA', (financiado / parcelas).toFixed(2));
*/

-- DA: Filtrar Imoveis por Imobiliaria
-- Event: Change
-- Selection: P110_IMOBILIARIA_ID
-- True Action: Refresh LOV P110_IMOVEL_ID

-- DA: Toggle Config Boleto
-- Event: Change
-- Selection: P110_USAR_CONFIG_BOLETO_IMOBILIARIA
-- True Action: Hide Region (Config Boleto Personalizada) when = 1
-- False Action: Show Region when = 0

-- ============================================================================
-- PAGINA 120: PARCELAS DO CONTRATO
-- ============================================================================

/*
================================================================================
PAGE ITEMS
================================================================================
*/

-- P120_CONTRATO_ID (Hidden - From URL)

/*
================================================================================
REGIAO 1: Cabecalho do Contrato
================================================================================
*/

-- Type: Static Content (Cards)
-- Source SQL:
/*
SELECT
    c.numero_contrato,
    comp.nome AS comprador,
    i.identificacao AS imovel,
    TO_CHAR(c.valor_total, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total,
    c.numero_parcelas,
    pkg_contrato.calcular_progresso(c.id) AS progresso,
    pkg_contrato.calcular_valor_pago(c.id) AS valor_pago,
    pkg_contrato.calcular_saldo_devedor(c.id) AS saldo_devedor,
    c.status
FROM gc_contrato c
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imovel i ON i.id = c.imovel_id
WHERE c.id = :P120_CONTRATO_ID
*/

/*
================================================================================
REGIAO 2: Lista de Parcelas
================================================================================
*/

-- Type: Interactive Report
-- Source: vw_parcela_detalhada
-- WHERE contrato_id = :P120_CONTRATO_ID

-- Colunas principais:
-- NUMERO_PARCELA, DATA_VENCIMENTO, VALOR_ATUAL, VALOR_JUROS, VALOR_MULTA
-- VALOR_TOTAL, STATUS_PAGAMENTO, DIAS_ATRASO, STATUS_BOLETO

-- HTML Expression para STATUS_PAGAMENTO:
/*
<span class="u-badge #CASE WHEN pago = 1 THEN 'u-success' ELSE
    CASE WHEN data_vencimento < TRUNC(SYSDATE) THEN 'u-danger' ELSE 'u-warning' END
END#">#STATUS_PAGAMENTO#</span>
*/

/*
================================================================================
ROW ACTIONS
================================================================================
*/

-- Action: Registrar Pagamento
-- Icon: fa-check
-- Condition: pago = 0
-- Target: Open Modal Region (Modal Pagamento)

-- Action: Gerar Boleto
-- Icon: fa-barcode
-- Condition: pago = 0 AND status_boleto = 'NAO_GERADO'
-- Execute PL/SQL:
/*
DECLARE
    v_msg VARCHAR2(4000);
    v_sucesso BOOLEAN;
    v_nosso_numero VARCHAR2(30);
    v_codigo_barras VARCHAR2(50);
    v_linha_digitavel VARCHAR2(60);
    v_pdf BLOB;
BEGIN
    pkg_brcobranca.gerar_boleto_brcobranca(
        p_parcela_id   => :PARCELA_ID,
        p_sucesso      => v_sucesso,
        p_nosso_numero => v_nosso_numero,
        p_codigo_barras => v_codigo_barras,
        p_linha_digitavel => v_linha_digitavel,
        p_pdf_content  => v_pdf,
        p_msg_erro     => v_msg
    );
    IF NOT v_sucesso THEN
        RAISE_APPLICATION_ERROR(-20001, v_msg);
    END IF;
END;
*/

-- Action: Ver Boleto
-- Icon: fa-file-pdf-o
-- Condition: nosso_numero IS NOT NULL
-- Target: Download PDF (boleto_pdf)

-- Action: Cancelar Boleto
-- Icon: fa-times
-- Condition: status_boleto IN ('GERADO', 'REGISTRADO')
-- Execute PL/SQL

/*
================================================================================
MODAL: Registrar Pagamento
================================================================================
*/

-- P120_PARCELA_ID (Hidden)
-- P120_VALOR_A_PAGAR (Display Only - Valor Total)
-- P120_VALOR_PAGO (Number Field - Required)
-- P120_DATA_PAGAMENTO (Date Picker - Default SYSDATE)
-- P120_FORMA_PAGAMENTO (Select List - LOV gc_forma_pagamento)
-- P120_OBSERVACOES_PAG (Textarea)

-- Botao: Confirmar Pagamento
-- Process:
/*
DECLARE
    v_msg VARCHAR2(4000);
BEGIN
    pkg_contrato.registrar_pagamento(
        p_parcela_id      => :P120_PARCELA_ID,
        p_valor_pago      => :P120_VALOR_PAGO,
        p_data_pagamento  => :P120_DATA_PAGAMENTO,
        p_forma_pagamento => :P120_FORMA_PAGAMENTO,
        p_observacoes     => :P120_OBSERVACOES_PAG,
        p_msg_erro        => v_msg
    );

    IF v_msg IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20001, v_msg);
    END IF;
END;
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Voltar
-- Action: Redirect to Page 100

-- Botao: Gerar Todos os Boletos
-- Action: Execute Process
/*
DECLARE
    v_total NUMBER;
    v_erros NUMBER;
    v_msg VARCHAR2(4000);
BEGIN
    pkg_brcobranca.gerar_boletos_lote(
        p_contrato_id      => :P120_CONTRATO_ID,
        p_apenas_pendentes => TRUE,
        p_total_gerados    => v_total,
        p_total_erros      => v_erros,
        p_msg_erro         => v_msg
    );

    :P120_MSG := 'Boletos gerados: ' || v_total || '. Erros: ' || v_erros;
END;
*/

-- Botao: Aplicar Reajuste
-- Condition: Contract.tipo_correcao != 'FIXO'
-- Action: Open Modal (Aplicar Reajuste)
