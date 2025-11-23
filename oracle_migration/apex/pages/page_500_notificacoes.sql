/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 500-510: Notificacoes
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
-- PAGINA 500: CENTRAL DE NOTIFICACOES
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
    'Total Enviadas' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-paper-plane' AS icone,
    'u-color-1' AS css,
    1 AS ordem
FROM gc_notificacao
WHERE (:P500_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P500_IMOBILIARIA_ID)
  AND criado_em >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
UNION ALL
SELECT
    'E-mails' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-envelope' AS icone,
    'u-color-2' AS css,
    2 AS ordem
FROM gc_notificacao
WHERE tipo = 'EMAIL'
  AND (:P500_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P500_IMOBILIARIA_ID)
  AND criado_em >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
UNION ALL
SELECT
    'SMS' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-mobile' AS icone,
    'u-color-3' AS css,
    3 AS ordem
FROM gc_notificacao
WHERE tipo = 'SMS'
  AND (:P500_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P500_IMOBILIARIA_ID)
  AND criado_em >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
UNION ALL
SELECT
    'WhatsApp' AS titulo,
    TO_CHAR(COUNT(*), '999G999') AS valor,
    'fa-whatsapp' AS icone,
    'u-success' AS css,
    4 AS ordem
FROM gc_notificacao
WHERE tipo = 'WHATSAPP'
  AND (:P500_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P500_IMOBILIARIA_ID)
  AND criado_em >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
ORDER BY ordem
*/

/*
================================================================================
PAGE ITEM: Filtro
================================================================================
*/

-- P500_IMOBILIARIA_ID
-- Type: Select List
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes (Todas)

/*
================================================================================
REGIAO: Grafico - Notificacoes por Tipo
================================================================================
*/

-- Type: Chart (Pie)
-- Source SQL:
/*
SELECT
    tipo,
    CASE tipo
        WHEN 'EMAIL' THEN 'E-mail'
        WHEN 'SMS' THEN 'SMS'
        WHEN 'WHATSAPP' THEN 'WhatsApp'
    END AS label,
    COUNT(*) AS value
FROM gc_notificacao
WHERE (:P500_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P500_IMOBILIARIA_ID)
  AND criado_em >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
GROUP BY tipo
*/

/*
================================================================================
REGIAO: Ultimas Notificacoes
================================================================================
*/

-- Type: Interactive Report
-- Source SQL:
/*
SELECT
    n.id,
    n.tipo,
    CASE n.tipo
        WHEN 'EMAIL' THEN '<span class="fa fa-envelope"></span>'
        WHEN 'SMS' THEN '<span class="fa fa-mobile"></span>'
        WHEN 'WHATSAPP' THEN '<span class="fa fa-whatsapp"></span>'
    END AS tipo_icon,
    n.destinatario,
    n.assunto,
    SUBSTR(n.mensagem, 1, 100) || CASE WHEN LENGTH(n.mensagem) > 100 THEN '...' END AS mensagem_resumo,
    CASE n.status
        WHEN 'ENVIADO' THEN 'Enviado'
        WHEN 'ERRO' THEN 'Erro'
        WHEN 'PENDENTE' THEN 'Pendente'
    END AS status,
    CASE n.status
        WHEN 'ENVIADO' THEN 'u-success'
        WHEN 'ERRO' THEN 'u-danger'
        WHEN 'PENDENTE' THEN 'u-warning'
    END AS status_css,
    TO_CHAR(n.criado_em, 'DD/MM/YYYY HH24:MI') AS data_envio,
    n.erro_mensagem,
    comp.nome AS comprador,
    c.numero_contrato
FROM gc_notificacao n
LEFT JOIN gc_comprador comp ON comp.id = n.comprador_id
LEFT JOIN gc_contrato c ON c.id = n.contrato_id
WHERE (:P500_IMOBILIARIA_ID IS NULL OR n.imobiliaria_id = :P500_IMOBILIARIA_ID)
ORDER BY n.criado_em DESC
FETCH FIRST 100 ROWS ONLY
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Enviar Notificacao Manual
-- Action: Redirect to Page 501

-- Botao: Templates
-- Action: Redirect to Page 510

-- Botao: Configuracoes
-- Action: Redirect to Page 900

-- ============================================================================
-- PAGINA 501: ENVIAR NOTIFICACAO MANUAL
-- ============================================================================

/*
================================================================================
FORM: Envio Manual
================================================================================
*/

-- P501_TIPO
-- Type: Radio Group
-- Label: Tipo de Notificacao
-- Required: Yes
-- LOV: EMAIL;E-mail,SMS;SMS,WHATSAPP;WhatsApp
-- Default: EMAIL

-- P501_CONTRATO_ID
-- Type: Popup LOV
-- Label: Contrato
-- LOV:
/*
SELECT
    c.numero_contrato || ' - ' || comp.nome AS d,
    c.id AS r
FROM gc_contrato c
JOIN gc_comprador comp ON comp.id = c.comprador_id
WHERE c.status = 'ATIVO'
ORDER BY c.numero_contrato
*/

-- P501_COMPRADOR_ID
-- Type: Popup LOV
-- Label: Comprador (ou selecione contrato)
-- LOV: SELECT nome d, id r FROM gc_comprador WHERE ativo = 1 ORDER BY nome

-- P501_TEMPLATE_ID
-- Type: Select List
-- Label: Usar Template
-- LOV:
/*
SELECT nome d, id r
FROM gc_template_notificacao
WHERE tipo = :P501_TIPO
  AND ativo = 1
ORDER BY nome
*/
-- Display Null: Yes (Mensagem personalizada)

-- P501_DESTINATARIO
-- Type: Text Field
-- Label: Destinatario (Email/Telefone)
-- Required: Yes

-- P501_ASSUNTO
-- Type: Text Field
-- Label: Assunto
-- Condition: P501_TIPO = 'EMAIL'

-- P501_MENSAGEM
-- Type: Rich Text Editor (for EMAIL) / Textarea (for SMS/WHATSAPP)
-- Label: Mensagem
-- Required: Yes

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Preencher Destinatario ao Selecionar Comprador
-- Event: Change
-- Selection: P501_COMPRADOR_ID
-- True Action: Set Value
/*
DECLARE
    v_email VARCHAR2(200);
    v_celular VARCHAR2(20);
BEGIN
    SELECT email, celular INTO v_email, v_celular
    FROM gc_comprador WHERE id = :P501_COMPRADOR_ID;

    IF :P501_TIPO = 'EMAIL' THEN
        :P501_DESTINATARIO := v_email;
    ELSE
        :P501_DESTINATARIO := v_celular;
    END IF;
END;
*/

-- DA: Preencher Mensagem ao Selecionar Template
-- Event: Change
-- Selection: P501_TEMPLATE_ID
-- Condition: P501_TEMPLATE_ID IS NOT NULL
-- True Action: Set Value
/*
SELECT assunto, conteudo
INTO :P501_ASSUNTO, :P501_MENSAGEM
FROM gc_template_notificacao
WHERE id = :P501_TEMPLATE_ID
*/

-- DA: Alternar Campo Assunto
-- Event: Change
-- Selection: P501_TIPO
-- True Action: Show/Hide P501_ASSUNTO based on tipo = EMAIL

/*
================================================================================
PROCESSO: Enviar Notificacao
================================================================================
*/

/*
DECLARE
    v_notificacao_id NUMBER;
    v_resultado VARCHAR2(4000);
BEGIN
    -- Inserir notificacao
    INSERT INTO gc_notificacao (
        imobiliaria_id, comprador_id, contrato_id,
        tipo, destinatario, assunto, mensagem, status
    ) VALUES (
        (SELECT imobiliaria_id FROM gc_contrato WHERE id = :P501_CONTRATO_ID),
        :P501_COMPRADOR_ID,
        :P501_CONTRATO_ID,
        :P501_TIPO,
        :P501_DESTINATARIO,
        :P501_ASSUNTO,
        :P501_MENSAGEM,
        'PENDENTE'
    ) RETURNING id INTO v_notificacao_id;

    -- Enviar conforme tipo
    CASE :P501_TIPO
        WHEN 'EMAIL' THEN
            v_resultado := pkg_notificacao.enviar_email(v_notificacao_id);
        WHEN 'SMS' THEN
            v_resultado := pkg_notificacao.enviar_sms(v_notificacao_id);
        WHEN 'WHATSAPP' THEN
            v_resultado := pkg_notificacao.enviar_whatsapp(v_notificacao_id);
    END CASE;

    IF v_resultado = 'OK' THEN
        UPDATE gc_notificacao SET status = 'ENVIADO' WHERE id = v_notificacao_id;
        APEX_APPLICATION.g_print_success_message := 'Notificação enviada com sucesso!';
    ELSE
        UPDATE gc_notificacao
        SET status = 'ERRO', erro_mensagem = v_resultado
        WHERE id = v_notificacao_id;
        RAISE_APPLICATION_ERROR(-20001, 'Erro ao enviar: ' || v_resultado);
    END IF;

    COMMIT;
END;
*/

-- ============================================================================
-- PAGINA 510: TEMPLATES DE NOTIFICACAO
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Templates
================================================================================
*/

-- Source SQL:
/*
SELECT
    t.id,
    t.nome,
    t.tipo,
    CASE t.tipo
        WHEN 'EMAIL' THEN 'E-mail'
        WHEN 'SMS' THEN 'SMS'
        WHEN 'WHATSAPP' THEN 'WhatsApp'
    END AS tipo_desc,
    t.assunto,
    SUBSTR(t.conteudo, 1, 100) || '...' AS conteudo_resumo,
    CASE t.ativo WHEN 1 THEN 'Ativo' ELSE 'Inativo' END AS status,
    TO_CHAR(t.criado_em, 'DD/MM/YYYY') AS criado_em
FROM gc_template_notificacao t
ORDER BY t.tipo, t.nome
*/

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Novo Template
-- Action: Redirect to Page 511

-- ============================================================================
-- PAGINA 511: FORMULARIO DE TEMPLATE
-- ============================================================================

/*
================================================================================
FORM: Template de Notificacao
================================================================================
*/

-- P511_ID (Hidden, PK)

-- P511_NOME
-- Type: Text Field
-- Label: Nome do Template
-- Required: Yes

-- P511_TIPO
-- Type: Select List
-- Label: Tipo
-- Required: Yes
-- LOV: EMAIL;E-mail,SMS;SMS,WHATSAPP;WhatsApp

-- P511_ASSUNTO
-- Type: Text Field
-- Label: Assunto
-- Condition: P511_TIPO = 'EMAIL'

-- P511_CONTEUDO
-- Type: Rich Text Editor
-- Label: Conteudo
-- Required: Yes
-- Help Text: Variaveis disponiveis: {COMPRADOR_NOME}, {CONTRATO_NUMERO}, {PARCELA_NUMERO}, {VALOR}, {VENCIMENTO}, {LINHA_DIGITAVEL}

-- P511_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
REGIAO: Variaveis Disponiveis
================================================================================
*/

-- Type: Static Content
/*
<div class="t-Alert t-Alert--info">
    <div class="t-Alert-body">
        <h3>Variáveis Disponíveis:</h3>
        <ul>
            <li><code>{COMPRADOR_NOME}</code> - Nome do comprador</li>
            <li><code>{COMPRADOR_DOCUMENTO}</code> - CPF/CNPJ do comprador</li>
            <li><code>{CONTRATO_NUMERO}</code> - Número do contrato</li>
            <li><code>{IMOVEL_IDENTIFICACAO}</code> - Identificação do imóvel</li>
            <li><code>{PARCELA_NUMERO}</code> - Número da parcela</li>
            <li><code>{VALOR}</code> - Valor da parcela</li>
            <li><code>{VENCIMENTO}</code> - Data de vencimento</li>
            <li><code>{LINHA_DIGITAVEL}</code> - Linha digitável do boleto</li>
            <li><code>{CODIGO_BARRAS}</code> - Código de barras</li>
            <li><code>{IMOBILIARIA_NOME}</code> - Nome da imobiliária</li>
            <li><code>{IMOBILIARIA_TELEFONE}</code> - Telefone da imobiliária</li>
        </ul>
    </div>
</div>
*/

/*
================================================================================
PROCESSO: Salvar Template
================================================================================
*/

/*
BEGIN
    IF :P511_ID IS NULL THEN
        INSERT INTO gc_template_notificacao (nome, tipo, assunto, conteudo, ativo)
        VALUES (:P511_NOME, :P511_TIPO, :P511_ASSUNTO, :P511_CONTEUDO, :P511_ATIVO);
    ELSE
        UPDATE gc_template_notificacao
        SET nome = :P511_NOME,
            tipo = :P511_TIPO,
            assunto = :P511_ASSUNTO,
            conteudo = :P511_CONTEUDO,
            ativo = :P511_ATIVO,
            atualizado_em = SYSTIMESTAMP
        WHERE id = :P511_ID;
    END IF;
END;
*/

-- ============================================================================
-- PAGINA 520: AGENDAMENTO DE NOTIFICACOES
-- ============================================================================

/*
================================================================================
REGIAO: Configuracao de Envio Automatico
================================================================================
*/

-- P520_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes

-- P520_DIAS_ANTES_VENCIMENTO
-- Type: Number Field
-- Label: Dias Antes do Vencimento
-- Help: Enviar lembrete X dias antes do vencimento
-- Default: 5

-- P520_ENVIAR_NO_VENCIMENTO
-- Type: Switch
-- Label: Enviar no Dia do Vencimento
-- Default: 1

-- P520_DIAS_APOS_VENCIMENTO
-- Type: Number Field
-- Label: Dias Apos Vencimento (Cobranca)
-- Help: Enviar cobranca X dias apos vencer
-- Default: 3

-- P520_INTERVALO_RECOBRANCA
-- Type: Number Field
-- Label: Intervalo entre Recobrancas (dias)
-- Default: 7

-- P520_MAXIMO_RECOBRANCAS
-- Type: Number Field
-- Label: Maximo de Recobrancas
-- Default: 3

/*
================================================================================
REGIAO: Templates por Evento
================================================================================
*/

-- P520_TEMPLATE_LEMBRETE_ID
-- Type: Select List
-- Label: Template de Lembrete
-- LOV: SELECT nome d, id r FROM gc_template_notificacao WHERE ativo = 1 ORDER BY nome

-- P520_TEMPLATE_VENCIMENTO_ID
-- Type: Select List
-- Label: Template Vencimento
-- LOV: ...

-- P520_TEMPLATE_COBRANCA_ID
-- Type: Select List
-- Label: Template de Cobranca
-- LOV: ...

/*
================================================================================
REGIAO: Canais de Envio
================================================================================
*/

-- P520_USAR_EMAIL
-- Type: Switch
-- Label: Enviar por E-mail
-- Default: 1

-- P520_USAR_SMS
-- Type: Switch
-- Label: Enviar por SMS
-- Default: 0

-- P520_USAR_WHATSAPP
-- Type: Switch
-- Label: Enviar por WhatsApp
-- Default: 0

/*
================================================================================
BOTAO: Salvar Configuracoes
================================================================================
*/

/*
BEGIN
    MERGE INTO gc_config_notificacao_auto cfg
    USING (SELECT :P520_IMOBILIARIA_ID AS imobiliaria_id FROM DUAL) src
    ON (cfg.imobiliaria_id = src.imobiliaria_id)
    WHEN MATCHED THEN
        UPDATE SET
            dias_antes_vencimento = :P520_DIAS_ANTES_VENCIMENTO,
            enviar_no_vencimento = :P520_ENVIAR_NO_VENCIMENTO,
            dias_apos_vencimento = :P520_DIAS_APOS_VENCIMENTO,
            intervalo_recobranca = :P520_INTERVALO_RECOBRANCA,
            maximo_recobrancas = :P520_MAXIMO_RECOBRANCAS,
            template_lembrete_id = :P520_TEMPLATE_LEMBRETE_ID,
            template_vencimento_id = :P520_TEMPLATE_VENCIMENTO_ID,
            template_cobranca_id = :P520_TEMPLATE_COBRANCA_ID,
            usar_email = :P520_USAR_EMAIL,
            usar_sms = :P520_USAR_SMS,
            usar_whatsapp = :P520_USAR_WHATSAPP
    WHEN NOT MATCHED THEN
        INSERT (imobiliaria_id, dias_antes_vencimento, enviar_no_vencimento,
                dias_apos_vencimento, intervalo_recobranca, maximo_recobrancas,
                template_lembrete_id, template_vencimento_id, template_cobranca_id,
                usar_email, usar_sms, usar_whatsapp)
        VALUES (:P520_IMOBILIARIA_ID, :P520_DIAS_ANTES_VENCIMENTO, :P520_ENVIAR_NO_VENCIMENTO,
                :P520_DIAS_APOS_VENCIMENTO, :P520_INTERVALO_RECOBRANCA, :P520_MAXIMO_RECOBRANCAS,
                :P520_TEMPLATE_LEMBRETE_ID, :P520_TEMPLATE_VENCIMENTO_ID, :P520_TEMPLATE_COBRANCA_ID,
                :P520_USAR_EMAIL, :P520_USAR_SMS, :P520_USAR_WHATSAPP);
    COMMIT;
END;
*/

