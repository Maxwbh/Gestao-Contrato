/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 300-310: Boletos (Lista e Geracao em Lote)
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
-- PAGINA 300: LISTA DE BOLETOS
-- ============================================================================
-- Tipo: Interactive Report
-- Template: Standard

/*
================================================================================
REGIAO: Interactive Report - Boletos
================================================================================
*/

-- Source SQL:
/*
SELECT
    b.id,
    b.parcela_id,
    c.numero_contrato,
    comp.nome AS comprador,
    im.nome AS imobiliaria,
    cb.descricao AS conta_bancaria,
    ban.nome AS banco,
    b.nosso_numero,
    b.numero_documento,
    TO_CHAR(b.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_formatado,
    b.valor,
    TO_CHAR(b.vencimento, 'DD/MM/YYYY') AS vencimento,
    b.vencimento AS vencimento_data,
    CASE
        WHEN b.status = 'PENDENTE' AND b.vencimento < TRUNC(SYSDATE) THEN 'VENCIDO'
        ELSE b.status
    END AS status_calc,
    CASE
        WHEN b.status = 'PAGO' THEN 'u-success'
        WHEN b.status = 'CANCELADO' THEN 'u-danger'
        WHEN b.vencimento < TRUNC(SYSDATE) THEN 'u-hot'
        WHEN b.vencimento <= TRUNC(SYSDATE) + 7 THEN 'u-warning'
        ELSE 'u-color-1'
    END AS status_css,
    b.linha_digitavel,
    b.codigo_barras,
    b.arquivo_pdf,
    b.criado_em,
    b.registrado,
    CASE b.registrado WHEN 1 THEN 'fa-check u-success' ELSE 'fa-times u-danger' END AS registrado_icon,
    b.remessa_id,
    ar.nome_arquivo AS arquivo_remessa,
    -- Para download
    CASE WHEN b.arquivo_pdf IS NOT NULL THEN
        '<button type="button" class="t-Button t-Button--icon t-Button--small" onclick="downloadBoleto(' || b.id || ')"><span class="fa fa-download"></span></button>'
    END AS btn_download
FROM gc_boleto b
JOIN gc_parcela p ON p.id = b.parcela_id
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria im ON im.id = c.imobiliaria_id
JOIN gc_conta_bancaria cb ON cb.id = b.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
LEFT JOIN gc_arquivo_remessa ar ON ar.id = b.remessa_id
WHERE (:P300_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P300_IMOBILIARIA_ID)
  AND (:P300_STATUS IS NULL OR b.status = :P300_STATUS
       OR (:P300_STATUS = 'VENCIDO' AND b.status = 'PENDENTE' AND b.vencimento < TRUNC(SYSDATE)))
  AND (:P300_DATA_INI IS NULL OR b.vencimento >= TO_DATE(:P300_DATA_INI, 'DD/MM/YYYY'))
  AND (:P300_DATA_FIM IS NULL OR b.vencimento <= TO_DATE(:P300_DATA_FIM, 'DD/MM/YYYY'))
  AND (:P300_REGISTRADO IS NULL OR b.registrado = :P300_REGISTRADO)
ORDER BY b.vencimento DESC, b.criado_em DESC
*/

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P300_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes (Todas)

-- P300_STATUS
-- Type: Select List
-- Label: Status
-- LOV: PENDENTE;Pendente,PAGO;Pago,CANCELADO;Cancelado,VENCIDO;Vencido
-- Display Null: Yes (Todos)

-- P300_DATA_INI
-- Type: Date Picker
-- Label: Vencimento De

-- P300_DATA_FIM
-- Type: Date Picker
-- Label: Vencimento Ate

-- P300_REGISTRADO
-- Type: Select List
-- Label: Registrado
-- LOV: 1;Sim,0;Nao
-- Display Null: Yes (Todos)

/*
================================================================================
CARDS SUMMARY - Resumo
================================================================================
*/

-- Regiao: Resumo de Boletos
-- Type: Cards
-- Source SQL:
/*
SELECT
    'Total Boletos' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-file-text' AS icone,
    'u-color-1' AS css
FROM gc_boleto
WHERE (:P300_IMOBILIARIA_ID IS NULL OR conta_bancaria_id IN
       (SELECT id FROM gc_conta_bancaria WHERE imobiliaria_id = :P300_IMOBILIARIA_ID))
UNION ALL
SELECT
    'Pendentes' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-clock-o' AS icone,
    'u-warning' AS css
FROM gc_boleto
WHERE status = 'PENDENTE' AND vencimento >= TRUNC(SYSDATE)
  AND (:P300_IMOBILIARIA_ID IS NULL OR conta_bancaria_id IN
       (SELECT id FROM gc_conta_bancaria WHERE imobiliaria_id = :P300_IMOBILIARIA_ID))
UNION ALL
SELECT
    'Vencidos' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-exclamation-triangle' AS icone,
    'u-hot' AS css
FROM gc_boleto
WHERE status = 'PENDENTE' AND vencimento < TRUNC(SYSDATE)
  AND (:P300_IMOBILIARIA_ID IS NULL OR conta_bancaria_id IN
       (SELECT id FROM gc_conta_bancaria WHERE imobiliaria_id = :P300_IMOBILIARIA_ID))
UNION ALL
SELECT
    'Valor Total' AS titulo,
    TO_CHAR(SUM(valor), 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    'fa-money' AS icone,
    'u-success' AS css
FROM gc_boleto
WHERE status = 'PENDENTE'
  AND (:P300_IMOBILIARIA_ID IS NULL OR conta_bancaria_id IN
       (SELECT id FROM gc_conta_bancaria WHERE imobiliaria_id = :P300_IMOBILIARIA_ID))
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Gerar Boletos em Lote
-- Action: Redirect to Page 310

-- Botao: Exportar PDF
-- Action: Submit Page (Process para download)

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Filtrar Report
-- Event: Change
-- Selection: P300_IMOBILIARIA_ID, P300_STATUS, P300_DATA_INI, P300_DATA_FIM, P300_REGISTRADO
-- True Action: Refresh Region (Interactive Report)

/*
================================================================================
JAVASCRIPT - Download Boleto
================================================================================
*/

/*
function downloadBoleto(boletoId) {
    apex.server.process('DOWNLOAD_BOLETO', {
        x01: boletoId
    }, {
        dataType: 'text',
        success: function(data) {
            if (data.startsWith('ERROR:')) {
                apex.message.showErrors([{
                    type: 'error',
                    location: 'page',
                    message: data.substring(6)
                }]);
            } else {
                // Abrir PDF em nova aba
                window.open(data, '_blank');
            }
        }
    });
}
*/

/*
================================================================================
AJAX CALLBACK: DOWNLOAD_BOLETO
================================================================================
*/

/*
DECLARE
    v_boleto_id NUMBER := APEX_APPLICATION.g_x01;
    v_pdf BLOB;
    v_filename VARCHAR2(200);
BEGIN
    SELECT arquivo_pdf, 'boleto_' || nosso_numero || '.pdf'
    INTO v_pdf, v_filename
    FROM gc_boleto
    WHERE id = v_boleto_id;

    IF v_pdf IS NOT NULL THEN
        -- Configurar headers para download
        OWA_UTIL.mime_header('application/pdf', FALSE);
        HTP.p('Content-Disposition: attachment; filename="' || v_filename || '"');
        OWA_UTIL.http_header_close;

        -- Enviar arquivo
        WPG_DOCLOAD.download_file(v_pdf);
    ELSE
        HTP.p('ERROR:Arquivo PDF não encontrado');
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        HTP.p('ERROR:Boleto não encontrado');
END;
*/

-- ============================================================================
-- PAGINA 301: DETALHES DO BOLETO
-- ============================================================================

/*
================================================================================
REGIAO: Informacoes do Boleto
================================================================================
*/

-- Source SQL:
/*
SELECT
    b.id,
    b.nosso_numero,
    b.numero_documento,
    TO_CHAR(b.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    TO_CHAR(b.vencimento, 'DD/MM/YYYY') AS vencimento,
    b.status,
    b.linha_digitavel,
    b.codigo_barras,
    CASE b.registrado WHEN 1 THEN 'Sim' ELSE 'Nao' END AS registrado,
    TO_CHAR(b.data_registro, 'DD/MM/YYYY HH24:MI') AS data_registro,
    TO_CHAR(b.criado_em, 'DD/MM/YYYY HH24:MI') AS criado_em,
    -- Dados do Contrato
    c.numero_contrato,
    comp.nome AS comprador,
    COALESCE(comp.cpf, comp.cnpj) AS documento,
    -- Dados Bancarios
    ban.nome AS banco,
    cb.agencia,
    cb.conta,
    cb.convenio,
    cb.carteira,
    im.nome AS imobiliaria
FROM gc_boleto b
JOIN gc_parcela p ON p.id = b.parcela_id
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria im ON im.id = c.imobiliaria_id
JOIN gc_conta_bancaria cb ON cb.id = b.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE b.id = :P301_ID
*/

/*
================================================================================
REGIAO: Linha Digitavel e Codigo de Barras
================================================================================
*/

-- Display Only com CSS para destaque
-- Botao: Copiar Linha Digitavel (clipboard)

/*
<div class="linha-digitavel-container">
    <span id="linha-digitavel">&P301_LINHA_DIGITAVEL.</span>
    <button type="button" class="t-Button t-Button--icon" onclick="copiarLinhaDigitavel()">
        <span class="fa fa-copy"></span>
    </button>
</div>

<script>
function copiarLinhaDigitavel() {
    var texto = document.getElementById('linha-digitavel').innerText;
    navigator.clipboard.writeText(texto).then(function() {
        apex.message.showPageSuccess('Linha digitável copiada!');
    });
}
</script>
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Cancelar Boleto
-- Condition: Status = PENDENTE
-- Action: Execute PL/SQL + Refresh

-- Botao: Baixar PDF
-- Condition: arquivo_pdf IS NOT NULL
-- Action: Download

-- Botao: Reenviar Email
-- Condition: Status = PENDENTE
-- Action: Open Modal (Enviar por Email)

/*
================================================================================
PROCESSO: Cancelar Boleto
================================================================================
*/

/*
BEGIN
    UPDATE gc_boleto
    SET status = 'CANCELADO',
        atualizado_em = SYSTIMESTAMP
    WHERE id = :P301_ID
      AND status = 'PENDENTE';

    -- Atualizar parcela
    UPDATE gc_parcela
    SET boleto_gerado = 0
    WHERE id = (SELECT parcela_id FROM gc_boleto WHERE id = :P301_ID);

    COMMIT;
END;
*/

-- ============================================================================
-- PAGINA 310: GERACAO DE BOLETOS EM LOTE
-- ============================================================================
-- Tipo: Wizard/Form
-- Template: Standard

/*
================================================================================
STEP 1: Selecao de Parcelas
================================================================================
*/

-- P310_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome

-- P310_CONTA_BANCARIA_ID
-- Type: Select List
-- Label: Conta Bancaria
-- Required: Yes
-- Cascading LOV Parent: P310_IMOBILIARIA_ID
-- LOV:
/*
SELECT
    b.nome || ' - ' || cb.agencia || '/' || cb.conta ||
    CASE cb.principal WHEN 1 THEN ' (Principal)' ELSE '' END AS d,
    cb.id AS r
FROM gc_conta_bancaria cb
JOIN gc_banco b ON b.codigo = cb.banco
WHERE cb.imobiliaria_id = :P310_IMOBILIARIA_ID
  AND cb.ativo = 1
ORDER BY cb.principal DESC, b.nome
*/

-- P310_DATA_VENCIMENTO_INI
-- Type: Date Picker
-- Label: Vencimento De
-- Required: Yes
-- Default: SYSDATE

-- P310_DATA_VENCIMENTO_FIM
-- Type: Date Picker
-- Label: Vencimento Ate
-- Required: Yes
-- Default: LAST_DAY(ADD_MONTHS(SYSDATE, 1))

-- P310_APENAS_SEM_BOLETO
-- Type: Switch
-- Label: Apenas Parcelas Sem Boleto
-- Default: 1

/*
================================================================================
REGIAO: Parcelas Disponiveis
================================================================================
*/

-- Type: Interactive Grid (Selecao)
-- Source SQL:
/*
SELECT
    p.id,
    APEX_ITEM.CHECKBOX2(1, p.id, 'CHECKED') AS selecionar,
    c.numero_contrato,
    comp.nome AS comprador,
    p.numero_parcela,
    TO_CHAR(p.valor_parcela, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    TO_CHAR(p.data_vencimento, 'DD/MM/YYYY') AS vencimento,
    CASE WHEN p.boleto_gerado = 1 THEN 'Sim' ELSE 'Nao' END AS boleto_existente,
    CASE
        WHEN p.data_vencimento < TRUNC(SYSDATE) THEN 'VENCIDA'
        WHEN p.data_vencimento <= TRUNC(SYSDATE) + 7 THEN 'PROXIMA'
        ELSE 'NORMAL'
    END AS situacao
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE c.imobiliaria_id = :P310_IMOBILIARIA_ID
  AND c.status = 'ATIVO'
  AND p.status = 'PENDENTE'
  AND p.data_vencimento BETWEEN :P310_DATA_VENCIMENTO_INI AND :P310_DATA_VENCIMENTO_FIM
  AND (:P310_APENAS_SEM_BOLETO = 0 OR p.boleto_gerado = 0)
ORDER BY p.data_vencimento, c.numero_contrato, p.numero_parcela
*/

/*
================================================================================
STEP 2: Configuracao do Boleto
================================================================================
*/

-- P310_INSTRUCAO1
-- Type: Text Field
-- Label: Instrucao 1
-- Default: Nao receber apos o vencimento

-- P310_INSTRUCAO2
-- Type: Text Field
-- Label: Instrucao 2

-- P310_INSTRUCAO3
-- Type: Text Field
-- Label: Instrucao 3

-- P310_LOCAL_PAGAMENTO
-- Type: Text Field
-- Label: Local de Pagamento
-- Default: Pagavel em qualquer banco ate o vencimento

-- P310_APLICAR_MULTA
-- Type: Switch
-- Label: Aplicar Multa
-- Default: Herdar da Imobiliaria

-- P310_APLICAR_JUROS
-- Type: Switch
-- Label: Aplicar Juros
-- Default: Herdar da Imobiliaria

/*
================================================================================
STEP 3: Confirmacao e Geracao
================================================================================
*/

-- Regiao: Resumo
-- Display: Total de parcelas selecionadas, Valor total, Conta bancaria

-- Botao: Gerar Boletos
-- Action: Execute Process + Redirect to Page 300

/*
================================================================================
PROCESSO: Gerar Boletos em Lote
================================================================================
*/

/*
DECLARE
    v_parcelas APEX_APPLICATION_GLOBAL.VC_ARR2 := APEX_APPLICATION.g_f01;
    v_conta_id NUMBER := :P310_CONTA_BANCARIA_ID;
    v_total_gerados NUMBER := 0;
    v_total_erros NUMBER := 0;
    v_boleto_id NUMBER;
    v_nosso_numero VARCHAR2(20);
    v_num_documento VARCHAR2(30);
    v_resultado CLOB;
BEGIN
    FOR i IN 1..v_parcelas.COUNT LOOP
        BEGIN
            -- Obter proximo nosso numero
            v_nosso_numero := pkg_boleto.obter_proximo_nosso_numero(v_conta_id);

            -- Gerar numero do documento
            v_num_documento := pkg_boleto.gerar_numero_documento(
                p_contrato_id => (SELECT contrato_id FROM gc_parcela WHERE id = v_parcelas(i)),
                p_parcela_id => v_parcelas(i)
            );

            -- Chamar BRcobranca para gerar boleto
            v_resultado := pkg_brcobranca.gerar_boleto_brcobranca(
                p_parcela_id => v_parcelas(i),
                p_conta_bancaria_id => v_conta_id,
                p_nosso_numero => v_nosso_numero,
                p_instrucoes => :P310_INSTRUCAO1 || CHR(10) || :P310_INSTRUCAO2 || CHR(10) || :P310_INSTRUCAO3,
                p_local_pagamento => :P310_LOCAL_PAGAMENTO
            );

            -- Verificar resultado
            IF INSTR(v_resultado, 'ERROR') = 0 THEN
                v_total_gerados := v_total_gerados + 1;
            ELSE
                v_total_erros := v_total_erros + 1;
                -- Log do erro
                INSERT INTO gc_log_erro (processo, mensagem, dados)
                VALUES ('GERAR_BOLETO', v_resultado, 'Parcela ID: ' || v_parcelas(i));
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                v_total_erros := v_total_erros + 1;
                INSERT INTO gc_log_erro (processo, mensagem, dados)
                VALUES ('GERAR_BOLETO', SQLERRM, 'Parcela ID: ' || v_parcelas(i));
        END;
    END LOOP;

    COMMIT;

    -- Mensagem de resultado
    APEX_APPLICATION.g_print_success_message :=
        'Boletos gerados: ' || v_total_gerados ||
        CASE WHEN v_total_erros > 0 THEN ' | Erros: ' || v_total_erros ELSE '' END;
END;
*/

/*
================================================================================
DYNAMIC ACTIONS - STEP 1
================================================================================
*/

-- DA: Atualizar Parcelas
-- Event: Change
-- Selection: P310_IMOBILIARIA_ID, P310_DATA_VENCIMENTO_INI, P310_DATA_VENCIMENTO_FIM, P310_APENAS_SEM_BOLETO
-- True Action: Refresh Region (Interactive Grid)

-- DA: Limpar Conta ao Trocar Imobiliaria
-- Event: Change
-- Selection: P310_IMOBILIARIA_ID
-- True Action: Clear Item (P310_CONTA_BANCARIA_ID)
-- True Action: Refresh Item (P310_CONTA_BANCARIA_ID)

/*
================================================================================
BOTOES SELECAO
================================================================================
*/

-- Botao: Selecionar Todos
/*
$('input[name="f01"]').prop('checked', true);
*/

-- Botao: Desmarcar Todos
/*
$('input[name="f01"]').prop('checked', false);
*/

-- ============================================================================
-- PAGINA 320: SEGUNDA VIA DE BOLETO
-- ============================================================================

/*
================================================================================
REGIAO: Buscar Boleto
================================================================================
*/

-- P320_NOSSO_NUMERO
-- Type: Text Field
-- Label: Nosso Numero

-- P320_CPF_CNPJ
-- Type: Text Field
-- Label: CPF/CNPJ do Comprador

-- Botao: Buscar
-- Action: Submit

/*
================================================================================
REGIAO: Resultado da Busca
================================================================================
*/

-- Condition: P320_NOSSO_NUMERO IS NOT NULL OR P320_CPF_CNPJ IS NOT NULL

-- Source SQL:
/*
SELECT
    b.id,
    b.nosso_numero,
    c.numero_contrato,
    comp.nome AS comprador,
    TO_CHAR(b.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    TO_CHAR(b.vencimento, 'DD/MM/YYYY') AS vencimento,
    b.status,
    b.linha_digitavel
FROM gc_boleto b
JOIN gc_parcela p ON p.id = b.parcela_id
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE (b.nosso_numero = :P320_NOSSO_NUMERO OR :P320_NOSSO_NUMERO IS NULL)
  AND (REGEXP_REPLACE(comp.cpf, '[^0-9]', '') = REGEXP_REPLACE(:P320_CPF_CNPJ, '[^0-9]', '')
       OR REGEXP_REPLACE(comp.cnpj, '[^0-9]', '') = REGEXP_REPLACE(:P320_CPF_CNPJ, '[^0-9]', '')
       OR :P320_CPF_CNPJ IS NULL)
  AND b.status = 'PENDENTE'
ORDER BY b.vencimento
*/

-- Link Column: Download PDF
-- Link Column: Enviar por Email

