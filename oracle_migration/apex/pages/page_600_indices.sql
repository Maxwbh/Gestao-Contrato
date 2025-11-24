/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 600-610: Indices de Reajuste
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
-- PAGINA 600: INDICES DE REAJUSTE
-- ============================================================================
-- Tipo: Interactive Report + Form Modal
-- Template: Standard

/*
================================================================================
REGIAO: Cards - Indices Atuais
================================================================================
*/

-- Source SQL:
/*
SELECT
    i.sigla,
    i.nome,
    TO_CHAR(
        (SELECT valor FROM gc_valor_indice vi
         WHERE vi.indice_id = i.id
         ORDER BY vi.data_referencia DESC
         FETCH FIRST 1 ROW ONLY),
        '999G999D9999'
    ) || '%' AS valor_atual,
    (SELECT TO_CHAR(data_referencia, 'MM/YYYY')
     FROM gc_valor_indice vi
     WHERE vi.indice_id = i.id
     ORDER BY vi.data_referencia DESC
     FETCH FIRST 1 ROW ONLY) AS referencia,
    CASE i.sigla
        WHEN 'IGPM' THEN 'fa-chart-line u-color-1'
        WHEN 'IPCA' THEN 'fa-chart-bar u-color-2'
        WHEN 'INPC' THEN 'fa-chart-area u-color-3'
        WHEN 'INCC' THEN 'fa-building u-color-4'
        ELSE 'fa-percent u-color-5'
    END AS icone_css
FROM gc_indice_reajuste i
WHERE i.ativo = 1
ORDER BY i.sigla
*/

/*
================================================================================
REGIAO: Interactive Report - Valores Historicos
================================================================================
*/

-- Source SQL:
/*
SELECT
    vi.id,
    ir.sigla,
    ir.nome AS indice,
    TO_CHAR(vi.data_referencia, 'MM/YYYY') AS referencia,
    vi.data_referencia,
    TO_CHAR(vi.valor, '999G999D9999') || '%' AS valor_formatado,
    vi.valor,
    vi.fonte,
    TO_CHAR(vi.criado_em, 'DD/MM/YYYY HH24:MI') AS criado_em
FROM gc_valor_indice vi
JOIN gc_indice_reajuste ir ON ir.id = vi.indice_id
WHERE (:P600_INDICE_ID IS NULL OR vi.indice_id = :P600_INDICE_ID)
  AND (:P600_ANO IS NULL OR EXTRACT(YEAR FROM vi.data_referencia) = :P600_ANO)
ORDER BY vi.data_referencia DESC, ir.sigla
*/

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P600_INDICE_ID
-- Type: Select List
-- Label: Indice
-- LOV: SELECT sigla || ' - ' || nome d, id r FROM gc_indice_reajuste WHERE ativo = 1 ORDER BY sigla
-- Display Null: Yes (Todos)

-- P600_ANO
-- Type: Select List
-- Label: Ano
-- LOV:
/*
SELECT DISTINCT EXTRACT(YEAR FROM data_referencia) AS d,
       EXTRACT(YEAR FROM data_referencia) AS r
FROM gc_valor_indice
ORDER BY 1 DESC
*/
-- Display Null: Yes (Todos)

/*
================================================================================
REGIAO: Grafico - Evolucao do Indice
================================================================================
*/

-- Type: Chart (Line)
-- Condition: P600_INDICE_ID IS NOT NULL
-- Source SQL:
/*
SELECT
    TO_CHAR(data_referencia, 'MM/YYYY') AS label,
    valor AS value
FROM gc_valor_indice
WHERE indice_id = :P600_INDICE_ID
ORDER BY data_referencia
FETCH LAST 24 ROWS ONLY
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Novo Indice
-- Action: Open Modal Page 601

-- Botao: Adicionar Valor
-- Action: Open Modal Page 602

-- Botao: Importar Valores
-- Action: Open Modal Page 603

-- ============================================================================
-- PAGINA 601: FORMULARIO DE INDICE (Modal)
-- ============================================================================

/*
================================================================================
FORM: Indice de Reajuste
================================================================================
*/

-- P601_ID (Hidden, PK)

-- P601_SIGLA
-- Type: Text Field
-- Label: Sigla
-- Required: Yes
-- Max Length: 10

-- P601_NOME
-- Type: Text Field
-- Label: Nome
-- Required: Yes

-- P601_DESCRICAO
-- Type: Textarea
-- Label: Descricao

-- P601_FONTE_PADRAO
-- Type: Text Field
-- Label: Fonte Padrao
-- Help: Ex: IBGE, FGV

-- P601_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
PROCESSO: Salvar Indice
================================================================================
*/

/*
BEGIN
    IF :P601_ID IS NULL THEN
        INSERT INTO gc_indice_reajuste (sigla, nome, descricao, fonte_padrao, ativo)
        VALUES (UPPER(:P601_SIGLA), :P601_NOME, :P601_DESCRICAO, :P601_FONTE_PADRAO, :P601_ATIVO);
    ELSE
        UPDATE gc_indice_reajuste
        SET sigla = UPPER(:P601_SIGLA),
            nome = :P601_NOME,
            descricao = :P601_DESCRICAO,
            fonte_padrao = :P601_FONTE_PADRAO,
            ativo = :P601_ATIVO,
            atualizado_em = SYSTIMESTAMP
        WHERE id = :P601_ID;
    END IF;
END;
*/

-- ============================================================================
-- PAGINA 602: ADICIONAR VALOR DE INDICE (Modal)
-- ============================================================================

/*
================================================================================
FORM: Valor do Indice
================================================================================
*/

-- P602_ID (Hidden, PK)

-- P602_INDICE_ID
-- Type: Select List
-- Label: Indice
-- Required: Yes
-- LOV: SELECT sigla || ' - ' || nome d, id r FROM gc_indice_reajuste WHERE ativo = 1 ORDER BY sigla

-- P602_MES
-- Type: Select List
-- Label: Mes
-- Required: Yes
-- LOV: 1;Janeiro,2;Fevereiro,3;Marco,4;Abril,5;Maio,6;Junho,7;Julho,8;Agosto,9;Setembro,10;Outubro,11;Novembro,12;Dezembro

-- P602_ANO
-- Type: Number Field
-- Label: Ano
-- Required: Yes
-- Default: EXTRACT(YEAR FROM SYSDATE)

-- P602_VALOR
-- Type: Number Field
-- Label: Valor (%)
-- Required: Yes
-- Format: 999G999D9999

-- P602_FONTE
-- Type: Text Field
-- Label: Fonte

/*
================================================================================
PROCESSO: Salvar Valor
================================================================================
*/

/*
DECLARE
    v_data_ref DATE;
BEGIN
    v_data_ref := TO_DATE('01/' || LPAD(:P602_MES, 2, '0') || '/' || :P602_ANO, 'DD/MM/YYYY');

    IF :P602_ID IS NULL THEN
        INSERT INTO gc_valor_indice (indice_id, data_referencia, valor, fonte)
        VALUES (:P602_INDICE_ID, v_data_ref, :P602_VALOR, :P602_FONTE);
    ELSE
        UPDATE gc_valor_indice
        SET indice_id = :P602_INDICE_ID,
            data_referencia = v_data_ref,
            valor = :P602_VALOR,
            fonte = :P602_FONTE
        WHERE id = :P602_ID;
    END IF;
END;
*/

-- ============================================================================
-- PAGINA 603: IMPORTAR VALORES (Modal)
-- ============================================================================

/*
================================================================================
FORM: Importacao em Lote
================================================================================
*/

-- P603_INDICE_ID
-- Type: Select List
-- Label: Indice
-- Required: Yes

-- P603_FORMATO
-- Type: Radio Group
-- Label: Formato
-- LOV: CSV;CSV (MM/YYYY;Valor),MANUAL;Manual (lista)
-- Default: CSV

-- P603_DADOS
-- Type: Textarea
-- Label: Dados
-- Help: Para CSV: MM/YYYY;0.5 (uma linha por valor). Para Manual: MM/YYYY=0.5, MM/YYYY=0.3

/*
================================================================================
PROCESSO: Importar Valores
================================================================================
*/

/*
DECLARE
    v_linhas APEX_APPLICATION_GLOBAL.VC_ARR2;
    v_partes APEX_APPLICATION_GLOBAL.VC_ARR2;
    v_data_ref DATE;
    v_valor NUMBER;
    v_total NUMBER := 0;
BEGIN
    IF :P603_FORMATO = 'CSV' THEN
        v_linhas := APEX_STRING.SPLIT(:P603_DADOS, CHR(10));

        FOR i IN 1..v_linhas.COUNT LOOP
            IF TRIM(v_linhas(i)) IS NOT NULL THEN
                v_partes := APEX_STRING.SPLIT(v_linhas(i), ';');

                IF v_partes.COUNT >= 2 THEN
                    v_data_ref := TO_DATE('01/' || TRIM(v_partes(1)), 'DD/MM/YYYY');
                    v_valor := TO_NUMBER(REPLACE(TRIM(v_partes(2)), ',', '.'));

                    MERGE INTO gc_valor_indice vi
                    USING (SELECT :P603_INDICE_ID AS indice_id, v_data_ref AS data_ref FROM DUAL) src
                    ON (vi.indice_id = src.indice_id AND vi.data_referencia = src.data_ref)
                    WHEN MATCHED THEN
                        UPDATE SET valor = v_valor
                    WHEN NOT MATCHED THEN
                        INSERT (indice_id, data_referencia, valor, fonte)
                        VALUES (:P603_INDICE_ID, v_data_ref, v_valor, 'Importacao');

                    v_total := v_total + 1;
                END IF;
            END IF;
        END LOOP;
    END IF;

    COMMIT;
    APEX_APPLICATION.g_print_success_message := v_total || ' valores importados.';
END;
*/

-- ============================================================================
-- PAGINA 610: APLICAR REAJUSTE EM LOTE
-- ============================================================================

/*
================================================================================
STEP 1: Selecao de Contratos
================================================================================
*/

-- P610_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes

-- P610_INDICE_ID
-- Type: Select List
-- Label: Indice de Reajuste
-- Required: Yes

-- P610_MES_REFERENCIA
-- Type: Date Picker
-- Label: Mes de Referencia
-- Format: MM/YYYY

/*
================================================================================
REGIAO: Contratos para Reajuste
================================================================================
*/

-- Type: Interactive Grid
-- Source SQL:
/*
SELECT
    c.id,
    APEX_ITEM.CHECKBOX2(1, c.id, 'CHECKED') AS selecionar,
    c.numero_contrato,
    comp.nome AS comprador,
    i.identificacao AS imovel,
    c.indice_reajuste AS indice_atual,
    TO_CHAR(c.proximo_reajuste, 'MM/YYYY') AS proximo_reajuste,
    TO_CHAR(c.valor_parcela_atual, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_atual,
    -- Valor projetado
    TO_CHAR(
        c.valor_parcela_atual * (1 + NVL((
            SELECT valor/100 FROM gc_valor_indice vi
            WHERE vi.indice_id = :P610_INDICE_ID
              AND vi.data_referencia = TRUNC(TO_DATE(:P610_MES_REFERENCIA, 'MM/YYYY'), 'MM')
        ), 0)),
        'L999G999G999D99', 'NLS_CURRENCY=R$'
    ) AS valor_projetado
FROM gc_contrato c
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imovel i ON i.id = c.imovel_id
WHERE c.imobiliaria_id = :P610_IMOBILIARIA_ID
  AND c.status = 'ATIVO'
  AND c.tipo_reajuste = 'INDICE'
  AND c.proximo_reajuste <= ADD_MONTHS(SYSDATE, 1)
ORDER BY c.proximo_reajuste, c.numero_contrato
*/

/*
================================================================================
STEP 2: Confirmacao
================================================================================
*/

-- Resumo:
-- - Total de contratos selecionados
-- - Indice aplicado: IGPM 0,50% (MM/YYYY)
-- - Valor total antes do reajuste
-- - Valor total apos reajuste
-- - Diferenca

/*
================================================================================
PROCESSO: Aplicar Reajuste
================================================================================
*/

/*
DECLARE
    v_contratos APEX_APPLICATION_GLOBAL.VC_ARR2 := APEX_APPLICATION.g_f01;
    v_indice_id NUMBER := :P610_INDICE_ID;
    v_mes_ref DATE := TRUNC(TO_DATE(:P610_MES_REFERENCIA, 'MM/YYYY'), 'MM');
    v_percentual NUMBER;
    v_total_aplicados NUMBER := 0;
BEGIN
    -- Obter percentual do indice
    SELECT valor INTO v_percentual
    FROM gc_valor_indice
    WHERE indice_id = v_indice_id
      AND data_referencia = v_mes_ref;

    FOR i IN 1..v_contratos.COUNT LOOP
        pkg_contrato.aplicar_reajuste(
            p_contrato_id => v_contratos(i),
            p_percentual => v_percentual,
            p_data_referencia => v_mes_ref,
            p_indice_id => v_indice_id
        );
        v_total_aplicados := v_total_aplicados + 1;
    END LOOP;

    COMMIT;
    APEX_APPLICATION.g_print_success_message :=
        'Reajuste aplicado em ' || v_total_aplicados || ' contrato(s).';
END;
*/

-- ============================================================================
-- PAGINA 620: HISTORICO DE REAJUSTES
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Historico
================================================================================
*/

-- Source SQL:
/*
SELECT
    r.id,
    c.numero_contrato,
    comp.nome AS comprador,
    ir.sigla AS indice,
    TO_CHAR(r.data_referencia, 'MM/YYYY') AS referencia,
    TO_CHAR(r.percentual_aplicado, '999D99') || '%' AS percentual,
    TO_CHAR(r.valor_anterior, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_anterior,
    TO_CHAR(r.valor_novo, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_novo,
    TO_CHAR(r.valor_novo - r.valor_anterior, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS diferenca,
    TO_CHAR(r.criado_em, 'DD/MM/YYYY HH24:MI') AS data_aplicacao,
    r.usuario_aplicacao
FROM gc_reajuste r
JOIN gc_contrato c ON c.id = r.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
LEFT JOIN gc_indice_reajuste ir ON ir.id = r.indice_id
WHERE (:P620_IMOBILIARIA_ID IS NULL OR c.imobiliaria_id = :P620_IMOBILIARIA_ID)
  AND (:P620_ANO IS NULL OR EXTRACT(YEAR FROM r.data_referencia) = :P620_ANO)
ORDER BY r.criado_em DESC
*/

