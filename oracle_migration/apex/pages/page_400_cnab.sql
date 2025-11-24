/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 400-420: CNAB (Remessa e Retorno)
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
-- PAGINA 400: DASHBOARD CNAB
-- ============================================================================
-- Tipo: Dashboard
-- Template: Standard

/*
================================================================================
REGIAO: Cards Resumo
================================================================================
*/

-- Source SQL:
/*
SELECT
    'Remessas' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-upload' AS icone,
    'u-color-1' AS css,
    1 AS ordem
FROM gc_arquivo_remessa
WHERE status = 'GERADO'
  AND (:P400_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P400_IMOBILIARIA_ID)
UNION ALL
SELECT
    'Retornos' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-download' AS icone,
    'u-color-2' AS css,
    2 AS ordem
FROM gc_arquivo_retorno
WHERE (:P400_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P400_IMOBILIARIA_ID)
UNION ALL
SELECT
    'Aguardando Envio' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-clock-o' AS icone,
    'u-warning' AS css,
    3 AS ordem
FROM gc_arquivo_remessa
WHERE status = 'GERADO'
  AND enviado_banco = 0
  AND (:P400_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P400_IMOBILIARIA_ID)
UNION ALL
SELECT
    'Boletos Registrados' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-check-circle' AS icone,
    'u-success' AS css,
    4 AS ordem
FROM gc_boleto
WHERE registrado = 1
  AND (:P400_IMOBILIARIA_ID IS NULL OR conta_bancaria_id IN
       (SELECT id FROM gc_conta_bancaria WHERE imobiliaria_id = :P400_IMOBILIARIA_ID))
ORDER BY ordem
*/

/*
================================================================================
PAGE ITEM: Filtro
================================================================================
*/

-- P400_IMOBILIARIA_ID
-- Type: Select List
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes (Todas)

/*
================================================================================
REGIAO: Ultimas Remessas
================================================================================
*/

-- Type: Classic Report
-- Source SQL:
/*
SELECT
    ar.id,
    ar.nome_arquivo,
    ban.nome AS banco,
    TO_CHAR(ar.data_geracao, 'DD/MM/YYYY HH24:MI') AS data_geracao,
    ar.quantidade_boletos,
    TO_CHAR(ar.valor_total, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total,
    ar.status,
    CASE ar.enviado_banco WHEN 1 THEN 'Sim' ELSE 'Nao' END AS enviado,
    '<a href="f?p=&APP_ID.:410:&SESSION.::&DEBUG.:410:P410_ID:' || ar.id || '" class="t-Button t-Button--icon t-Button--small"><span class="fa fa-eye"></span></a>' AS ver
FROM gc_arquivo_remessa ar
JOIN gc_conta_bancaria cb ON cb.id = ar.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE (:P400_IMOBILIARIA_ID IS NULL OR ar.imobiliaria_id = :P400_IMOBILIARIA_ID)
ORDER BY ar.data_geracao DESC
FETCH FIRST 10 ROWS ONLY
*/

/*
================================================================================
REGIAO: Ultimos Retornos
================================================================================
*/

-- Type: Classic Report
-- Source SQL:
/*
SELECT
    ret.id,
    ret.nome_arquivo,
    ban.nome AS banco,
    TO_CHAR(ret.data_processamento, 'DD/MM/YYYY HH24:MI') AS data_processamento,
    ret.quantidade_registros,
    ret.quantidade_pagos,
    ret.quantidade_erros,
    CASE ret.processado WHEN 1 THEN 'Processado' ELSE 'Pendente' END AS status,
    '<a href="f?p=&APP_ID.:420:&SESSION.::&DEBUG.:420:P420_ID:' || ret.id || '" class="t-Button t-Button--icon t-Button--small"><span class="fa fa-eye"></span></a>' AS ver
FROM gc_arquivo_retorno ret
JOIN gc_conta_bancaria cb ON cb.id = ret.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE (:P400_IMOBILIARIA_ID IS NULL OR ret.imobiliaria_id = :P400_IMOBILIARIA_ID)
ORDER BY ret.data_processamento DESC
FETCH FIRST 10 ROWS ONLY
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Nova Remessa
-- Action: Redirect to Page 410 (modo criacao)

-- Botao: Processar Retorno
-- Action: Redirect to Page 420

-- Botao: Lista Completa Remessas
-- Action: Redirect to Page 411

-- Botao: Lista Completa Retornos
-- Action: Redirect to Page 421

-- ============================================================================
-- PAGINA 410: GERAR ARQUIVO REMESSA
-- ============================================================================
-- Tipo: Wizard
-- Template: Standard

/*
================================================================================
STEP 1: Selecao de Conta e Boletos
================================================================================
*/

-- P410_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome

-- P410_CONTA_BANCARIA_ID
-- Type: Select List
-- Label: Conta Bancaria
-- Required: Yes
-- Cascading LOV Parent: P410_IMOBILIARIA_ID
-- LOV:
/*
SELECT
    ban.nome || ' - Ag: ' || cb.agencia || ' Cc: ' || cb.conta ||
    ' - Conv: ' || cb.convenio ||
    CASE cb.principal WHEN 1 THEN ' (Principal)' ELSE '' END AS d,
    cb.id AS r
FROM gc_conta_bancaria cb
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE cb.imobiliaria_id = :P410_IMOBILIARIA_ID
  AND cb.ativo = 1
  AND cb.cobranca_registrada = 1
ORDER BY cb.principal DESC, ban.nome
*/

-- P410_LAYOUT_CNAB
-- Type: Radio Group
-- Label: Layout
-- LOV: CNAB_240;CNAB 240,CNAB_400;CNAB 400
-- Default: Value from conta_bancaria.layout_cnab

/*
================================================================================
REGIAO: Boletos para Remessa
================================================================================
*/

-- Type: Interactive Grid (Selecao)
-- Condition: P410_CONTA_BANCARIA_ID IS NOT NULL
-- Source SQL:
/*
SELECT
    b.id,
    APEX_ITEM.CHECKBOX2(1, b.id, 'CHECKED') AS selecionar,
    c.numero_contrato,
    comp.nome AS comprador,
    b.nosso_numero,
    TO_CHAR(b.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    TO_CHAR(b.vencimento, 'DD/MM/YYYY') AS vencimento,
    b.numero_documento,
    CASE
        WHEN b.vencimento < TRUNC(SYSDATE) THEN 'Vencido'
        WHEN b.vencimento <= TRUNC(SYSDATE) + 3 THEN 'Proximo'
        ELSE 'Normal'
    END AS situacao
FROM gc_boleto b
JOIN gc_parcela p ON p.id = b.parcela_id
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE b.conta_bancaria_id = :P410_CONTA_BANCARIA_ID
  AND b.status = 'PENDENTE'
  AND b.registrado = 0
  AND b.remessa_id IS NULL
ORDER BY b.vencimento, b.nosso_numero
*/

/*
================================================================================
STEP 2: Configuracoes da Remessa
================================================================================
*/

-- P410_TIPO_OPERACAO
-- Type: Radio Group
-- Label: Tipo de Operacao
-- LOV: ENTRADA;Entrada de Titulos,BAIXA;Baixa de Titulos,ALTERACAO;Alteracao de Titulos
-- Default: ENTRADA

-- P410_SEQUENCIAL_ARQUIVO
-- Type: Number Field
-- Label: Sequencial do Arquivo
-- Default: Proximo sequencial da conta
-- Read Only: Yes (calculado automaticamente)

-- P410_OBSERVACAO
-- Type: Textarea
-- Label: Observacao (uso interno)

/*
================================================================================
STEP 3: Resumo e Geracao
================================================================================
*/

-- Regiao: Resumo
-- Display:
/*
  - Banco: [nome do banco]
  - Conta: [agencia/conta]
  - Convenio: [convenio]
  - Layout: [CNAB 240 ou 400]
  - Boletos selecionados: [quantidade]
  - Valor total: [R$ X.XXX,XX]
*/

-- Botao: Gerar Arquivo Remessa
-- Action: Execute Process + Download

/*
================================================================================
PROCESSO: Gerar Arquivo Remessa
================================================================================
*/

/*
DECLARE
    v_boletos APEX_APPLICATION_GLOBAL.VC_ARR2 := APEX_APPLICATION.g_f01;
    v_conta_id NUMBER := :P410_CONTA_BANCARIA_ID;
    v_layout VARCHAR2(20) := :P410_LAYOUT_CNAB;
    v_remessa_id NUMBER;
    v_arquivo CLOB;
    v_nome_arquivo VARCHAR2(100);
    v_boletos_str VARCHAR2(32767);
BEGIN
    -- Converter array para string separada por virgula
    FOR i IN 1..v_boletos.COUNT LOOP
        v_boletos_str := v_boletos_str || v_boletos(i);
        IF i < v_boletos.COUNT THEN
            v_boletos_str := v_boletos_str || ',';
        END IF;
    END LOOP;

    -- Gerar arquivo via BRcobranca
    v_arquivo := pkg_brcobranca.gerar_remessa_brcobranca(
        p_conta_bancaria_id => v_conta_id,
        p_boletos_ids => v_boletos_str,
        p_layout => v_layout
    );

    -- Verificar erro
    IF INSTR(v_arquivo, 'ERROR:') = 1 THEN
        RAISE_APPLICATION_ERROR(-20001, SUBSTR(v_arquivo, 7));
    END IF;

    -- Gerar nome do arquivo
    SELECT
        UPPER(b.codigo) || '_REM_' ||
        TO_CHAR(SYSDATE, 'YYYYMMDD_HH24MISS') || '.txt'
    INTO v_nome_arquivo
    FROM gc_conta_bancaria cb
    JOIN gc_banco b ON b.codigo = cb.banco
    WHERE cb.id = v_conta_id;

    -- Criar registro da remessa
    INSERT INTO gc_arquivo_remessa (
        imobiliaria_id, conta_bancaria_id, nome_arquivo,
        conteudo, layout, data_geracao, status,
        quantidade_boletos, valor_total, sequencial_arquivo, observacao
    ) VALUES (
        :P410_IMOBILIARIA_ID, v_conta_id, v_nome_arquivo,
        v_arquivo, v_layout, SYSTIMESTAMP, 'GERADO',
        v_boletos.COUNT,
        (SELECT SUM(valor) FROM gc_boleto WHERE id IN (SELECT COLUMN_VALUE FROM TABLE(APEX_STRING.SPLIT(v_boletos_str, ',')))),
        :P410_SEQUENCIAL_ARQUIVO, :P410_OBSERVACAO
    ) RETURNING id INTO v_remessa_id;

    -- Atualizar boletos
    UPDATE gc_boleto
    SET remessa_id = v_remessa_id,
        atualizado_em = SYSTIMESTAMP
    WHERE id IN (SELECT TO_NUMBER(COLUMN_VALUE) FROM TABLE(APEX_STRING.SPLIT(v_boletos_str, ',')));

    COMMIT;

    -- Salvar ID para download
    :P410_REMESSA_ID := v_remessa_id;
END;
*/

/*
================================================================================
PROCESSO: Download Arquivo Remessa
================================================================================
*/

/*
DECLARE
    v_arquivo CLOB;
    v_nome VARCHAR2(200);
BEGIN
    SELECT conteudo, nome_arquivo
    INTO v_arquivo, v_nome
    FROM gc_arquivo_remessa
    WHERE id = :P410_REMESSA_ID;

    -- Configurar headers
    OWA_UTIL.mime_header('text/plain', FALSE);
    HTP.p('Content-Disposition: attachment; filename="' || v_nome || '"');
    HTP.p('Content-Length: ' || DBMS_LOB.getlength(v_arquivo));
    OWA_UTIL.http_header_close;

    -- Enviar conteudo
    WPG_DOCLOAD.download_file(v_arquivo);
END;
*/

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Atualizar Boletos ao Selecionar Conta
-- Event: Change
-- Selection: P410_CONTA_BANCARIA_ID
-- True Action: Refresh Region (Interactive Grid)

-- DA: Atualizar Layout Default
-- Event: Change
-- Selection: P410_CONTA_BANCARIA_ID
-- True Action: Set Value (P410_LAYOUT_CNAB from conta_bancaria.layout_cnab)

-- ============================================================================
-- PAGINA 411: LISTA DE ARQUIVOS REMESSA
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Remessas
================================================================================
*/

-- Source SQL:
/*
SELECT
    ar.id,
    ar.nome_arquivo,
    im.nome AS imobiliaria,
    ban.nome AS banco,
    cb.agencia || '/' || cb.conta AS conta,
    ar.layout,
    TO_CHAR(ar.data_geracao, 'DD/MM/YYYY HH24:MI') AS data_geracao,
    ar.quantidade_boletos,
    TO_CHAR(ar.valor_total, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total,
    ar.status,
    CASE ar.enviado_banco WHEN 1 THEN 'Sim' ELSE 'Nao' END AS enviado,
    TO_CHAR(ar.data_envio, 'DD/MM/YYYY HH24:MI') AS data_envio,
    ar.sequencial_arquivo,
    ar.observacao
FROM gc_arquivo_remessa ar
JOIN gc_imobiliaria im ON im.id = ar.imobiliaria_id
JOIN gc_conta_bancaria cb ON cb.id = ar.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE (:P411_IMOBILIARIA_ID IS NULL OR ar.imobiliaria_id = :P411_IMOBILIARIA_ID)
  AND (:P411_STATUS IS NULL OR ar.status = :P411_STATUS)
  AND (:P411_DATA_INI IS NULL OR ar.data_geracao >= TO_DATE(:P411_DATA_INI, 'DD/MM/YYYY'))
  AND (:P411_DATA_FIM IS NULL OR ar.data_geracao <= TO_DATE(:P411_DATA_FIM, 'DD/MM/YYYY') + 1)
ORDER BY ar.data_geracao DESC
*/

/*
================================================================================
ACOES DO REPORT
================================================================================
*/

-- Link: Visualizar
-- Action: Redirect to Page 412 (Detalhe da Remessa)

-- Link: Download
-- Action: Download arquivo

-- Link: Marcar como Enviado
-- Condition: enviado_banco = 0
-- Action: Execute PL/SQL
/*
UPDATE gc_arquivo_remessa
SET enviado_banco = 1,
    data_envio = SYSTIMESTAMP
WHERE id = :ID;
COMMIT;
*/

-- ============================================================================
-- PAGINA 412: DETALHE DO ARQUIVO REMESSA
-- ============================================================================

/*
================================================================================
REGIAO: Informacoes da Remessa
================================================================================
*/

-- Source SQL:
/*
SELECT
    ar.nome_arquivo,
    im.nome AS imobiliaria,
    ban.nome AS banco,
    cb.agencia || '/' || cb.conta AS conta,
    cb.convenio,
    ar.layout,
    TO_CHAR(ar.data_geracao, 'DD/MM/YYYY HH24:MI:SS') AS data_geracao,
    ar.quantidade_boletos,
    TO_CHAR(ar.valor_total, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_total,
    ar.status,
    CASE ar.enviado_banco WHEN 1 THEN 'Sim' ELSE 'Nao' END AS enviado,
    TO_CHAR(ar.data_envio, 'DD/MM/YYYY HH24:MI:SS') AS data_envio,
    ar.sequencial_arquivo,
    ar.observacao
FROM gc_arquivo_remessa ar
JOIN gc_imobiliaria im ON im.id = ar.imobiliaria_id
JOIN gc_conta_bancaria cb ON cb.id = ar.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE ar.id = :P412_ID
*/

/*
================================================================================
REGIAO: Boletos da Remessa
================================================================================
*/

-- Type: Interactive Report
-- Source SQL:
/*
SELECT
    b.id,
    b.nosso_numero,
    b.numero_documento,
    c.numero_contrato,
    comp.nome AS comprador,
    TO_CHAR(b.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor,
    TO_CHAR(b.vencimento, 'DD/MM/YYYY') AS vencimento,
    b.status AS status_boleto,
    CASE b.registrado WHEN 1 THEN 'Sim' ELSE 'Nao' END AS registrado
FROM gc_boleto b
JOIN gc_parcela p ON p.id = b.parcela_id
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE b.remessa_id = :P412_ID
ORDER BY b.vencimento, b.nosso_numero
*/

/*
================================================================================
REGIAO: Conteudo do Arquivo
================================================================================
*/

-- Type: Display Only (PRE tag for fixed-width)
-- Source: ar.conteudo
-- CSS: font-family: monospace; white-space: pre; overflow-x: auto;

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Download
-- Action: Download arquivo

-- Botao: Marcar Enviado
-- Condition: enviado_banco = 0
-- Action: Execute PL/SQL + Refresh

-- Botao: Cancelar Remessa
-- Condition: enviado_banco = 0
-- Action: Execute PL/SQL + Redirect
/*
BEGIN
    -- Remover associacao dos boletos
    UPDATE gc_boleto
    SET remessa_id = NULL
    WHERE remessa_id = :P412_ID;

    -- Atualizar status da remessa
    UPDATE gc_arquivo_remessa
    SET status = 'CANCELADO'
    WHERE id = :P412_ID;

    COMMIT;
END;
*/

-- ============================================================================
-- PAGINA 420: PROCESSAR ARQUIVO RETORNO
-- ============================================================================
-- Tipo: Form com Upload
-- Template: Standard

/*
================================================================================
REGIAO: Upload de Arquivo
================================================================================
*/

-- P420_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome

-- P420_CONTA_BANCARIA_ID
-- Type: Select List
-- Label: Conta Bancaria
-- Required: Yes
-- Cascading LOV Parent: P420_IMOBILIARIA_ID

-- P420_ARQUIVO
-- Type: File Browse
-- Label: Arquivo de Retorno (.ret, .txt)
-- Storage Type: BLOB column specified in table
-- Allowed File Types: .ret,.txt,.RET,.TXT

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Processar Retorno
-- Action: Submit + Execute Process

/*
================================================================================
PROCESSO: Processar Arquivo Retorno
================================================================================
*/

/*
DECLARE
    v_arquivo BLOB;
    v_conteudo CLOB;
    v_nome_arquivo VARCHAR2(200);
    v_retorno_id NUMBER;
    v_resultado CLOB;
    v_qtd_registros NUMBER;
    v_qtd_pagos NUMBER;
    v_qtd_erros NUMBER;
BEGIN
    -- Obter arquivo do upload
    SELECT blob_content, filename
    INTO v_arquivo, v_nome_arquivo
    FROM apex_application_temp_files
    WHERE name = :P420_ARQUIVO;

    -- Converter BLOB para CLOB
    v_conteudo := pkg_utils.blob_to_clob(v_arquivo);

    -- Criar registro do retorno
    INSERT INTO gc_arquivo_retorno (
        imobiliaria_id, conta_bancaria_id, nome_arquivo,
        conteudo, data_processamento, processado
    ) VALUES (
        :P420_IMOBILIARIA_ID, :P420_CONTA_BANCARIA_ID, v_nome_arquivo,
        v_conteudo, SYSTIMESTAMP, 0
    ) RETURNING id INTO v_retorno_id;

    -- Processar via BRcobranca
    v_resultado := pkg_brcobranca.processar_retorno_brcobranca(
        p_retorno_id => v_retorno_id
    );

    -- Verificar resultado
    IF INSTR(v_resultado, 'ERROR:') = 1 THEN
        RAISE_APPLICATION_ERROR(-20001, SUBSTR(v_resultado, 7));
    END IF;

    -- Atualizar estatisticas
    SELECT
        COUNT(*),
        SUM(CASE WHEN status = 'PAGO' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status = 'ERRO' THEN 1 ELSE 0 END)
    INTO v_qtd_registros, v_qtd_pagos, v_qtd_erros
    FROM gc_retorno_detalhe
    WHERE retorno_id = v_retorno_id;

    UPDATE gc_arquivo_retorno
    SET processado = 1,
        quantidade_registros = v_qtd_registros,
        quantidade_pagos = v_qtd_pagos,
        quantidade_erros = v_qtd_erros
    WHERE id = v_retorno_id;

    COMMIT;

    -- Redirecionar para detalhes
    :P420_RETORNO_ID := v_retorno_id;
END;
*/

/*
================================================================================
AFTER PROCESS: Redirect to Detail
================================================================================
*/

-- Branch: Redirect to Page 422 with P422_ID = &P420_RETORNO_ID.

-- ============================================================================
-- PAGINA 421: LISTA DE ARQUIVOS RETORNO
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Retornos
================================================================================
*/

-- Source SQL:
/*
SELECT
    ret.id,
    ret.nome_arquivo,
    im.nome AS imobiliaria,
    ban.nome AS banco,
    cb.agencia || '/' || cb.conta AS conta,
    TO_CHAR(ret.data_processamento, 'DD/MM/YYYY HH24:MI') AS data_processamento,
    ret.quantidade_registros,
    ret.quantidade_pagos,
    ret.quantidade_erros,
    CASE ret.processado WHEN 1 THEN 'Processado' ELSE 'Pendente' END AS status,
    ROUND(ret.quantidade_pagos / NULLIF(ret.quantidade_registros, 0) * 100, 1) || '%' AS taxa_sucesso
FROM gc_arquivo_retorno ret
JOIN gc_imobiliaria im ON im.id = ret.imobiliaria_id
JOIN gc_conta_bancaria cb ON cb.id = ret.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE (:P421_IMOBILIARIA_ID IS NULL OR ret.imobiliaria_id = :P421_IMOBILIARIA_ID)
  AND (:P421_DATA_INI IS NULL OR ret.data_processamento >= TO_DATE(:P421_DATA_INI, 'DD/MM/YYYY'))
  AND (:P421_DATA_FIM IS NULL OR ret.data_processamento <= TO_DATE(:P421_DATA_FIM, 'DD/MM/YYYY') + 1)
ORDER BY ret.data_processamento DESC
*/

-- ============================================================================
-- PAGINA 422: DETALHE DO ARQUIVO RETORNO
-- ============================================================================

/*
================================================================================
REGIAO: Informacoes do Retorno
================================================================================
*/

-- Source SQL:
/*
SELECT
    ret.nome_arquivo,
    im.nome AS imobiliaria,
    ban.nome AS banco,
    cb.agencia || '/' || cb.conta AS conta,
    TO_CHAR(ret.data_processamento, 'DD/MM/YYYY HH24:MI:SS') AS data_processamento,
    ret.quantidade_registros,
    ret.quantidade_pagos,
    ret.quantidade_erros,
    CASE ret.processado WHEN 1 THEN 'Processado' ELSE 'Pendente' END AS status
FROM gc_arquivo_retorno ret
JOIN gc_imobiliaria im ON im.id = ret.imobiliaria_id
JOIN gc_conta_bancaria cb ON cb.id = ret.conta_bancaria_id
JOIN gc_banco ban ON ban.codigo = cb.banco
WHERE ret.id = :P422_ID
*/

/*
================================================================================
REGIAO: Cards Resumo
================================================================================
*/

-- Source SQL:
/*
SELECT 'Total Registros' AS titulo, quantidade_registros AS valor, 'fa-list' AS icone, 'u-color-1' AS css FROM gc_arquivo_retorno WHERE id = :P422_ID
UNION ALL
SELECT 'Pagamentos OK' AS titulo, quantidade_pagos AS valor, 'fa-check-circle' AS icone, 'u-success' AS css FROM gc_arquivo_retorno WHERE id = :P422_ID
UNION ALL
SELECT 'Erros' AS titulo, quantidade_erros AS valor, 'fa-times-circle' AS icone, 'u-danger' AS css FROM gc_arquivo_retorno WHERE id = :P422_ID
*/

/*
================================================================================
REGIAO: Detalhes do Retorno
================================================================================
*/

-- Type: Interactive Report
-- Source SQL:
/*
SELECT
    rd.id,
    rd.nosso_numero,
    rd.codigo_ocorrencia,
    co.descricao AS ocorrencia,
    TO_CHAR(rd.valor_pago, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_pago,
    TO_CHAR(rd.data_pagamento, 'DD/MM/YYYY') AS data_pagamento,
    TO_CHAR(rd.data_credito, 'DD/MM/YYYY') AS data_credito,
    TO_CHAR(rd.valor_tarifa, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS tarifa,
    rd.status,
    CASE rd.status
        WHEN 'PAGO' THEN 'u-success'
        WHEN 'ERRO' THEN 'u-danger'
        ELSE 'u-warning'
    END AS status_css,
    rd.mensagem_erro,
    -- Dados do boleto associado
    b.id AS boleto_id,
    c.numero_contrato,
    comp.nome AS comprador
FROM gc_retorno_detalhe rd
LEFT JOIN gc_codigo_ocorrencia co ON co.codigo = rd.codigo_ocorrencia AND co.banco = rd.banco
LEFT JOIN gc_boleto b ON b.nosso_numero = rd.nosso_numero AND b.conta_bancaria_id = (SELECT conta_bancaria_id FROM gc_arquivo_retorno WHERE id = :P422_ID)
LEFT JOIN gc_parcela p ON p.id = b.parcela_id
LEFT JOIN gc_contrato c ON c.id = p.contrato_id
LEFT JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE rd.retorno_id = :P422_ID
ORDER BY rd.id
*/

/*
================================================================================
REGIAO: Conteudo do Arquivo
================================================================================
*/

-- Type: Display Only (PRE tag)
-- Source: ret.conteudo
-- Collapsible: Yes

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Reprocessar
-- Condition: quantidade_erros > 0
-- Action: Execute PL/SQL
/*
DECLARE
    v_resultado CLOB;
BEGIN
    v_resultado := pkg_brcobranca.processar_retorno_brcobranca(
        p_retorno_id => :P422_ID
    );

    IF INSTR(v_resultado, 'ERROR:') = 1 THEN
        RAISE_APPLICATION_ERROR(-20001, SUBSTR(v_resultado, 7));
    END IF;
END;
*/

-- Botao: Exportar Excel
-- Action: Download IR to Excel

-- Botao: Voltar
-- Action: Redirect to Page 421

