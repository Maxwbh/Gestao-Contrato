/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 900-950: Configuracoes do Sistema
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
-- PAGINA 900: CENTRAL DE CONFIGURACOES
-- ============================================================================
-- Tipo: Navigation
-- Template: Standard

/*
================================================================================
REGIAO: Menu de Configuracoes
================================================================================
*/

-- Type: List (Vertical Sidebar)
/*
<ul class="t-NavigationMenu">
    <li><a href="f?p=&APP_ID.:910:&SESSION."><span class="fa fa-envelope"></span> E-mail (SMTP)</a></li>
    <li><a href="f?p=&APP_ID.:920:&SESSION."><span class="fa fa-mobile"></span> SMS</a></li>
    <li><a href="f?p=&APP_ID.:930:&SESSION."><span class="fa fa-whatsapp"></span> WhatsApp</a></li>
    <li><a href="f?p=&APP_ID.:940:&SESSION."><span class="fa fa-bank"></span> Bancos</a></li>
    <li><a href="f?p=&APP_ID.:950:&SESSION."><span class="fa fa-cogs"></span> Parametros Gerais</a></li>
    <li><a href="f?p=&APP_ID.:960:&SESSION."><span class="fa fa-key"></span> API BRcobranca</a></li>
</ul>
*/

-- ============================================================================
-- PAGINA 910: CONFIGURACAO DE E-MAIL (SMTP)
-- ============================================================================

/*
================================================================================
FORM: Configuracao SMTP
================================================================================
*/

-- P910_ID (Hidden)

-- P910_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Help: Cada imobiliaria pode ter sua propria configuracao de email

-- P910_SERVIDOR_SMTP
-- Type: Text Field
-- Label: Servidor SMTP
-- Required: Yes
-- Default: smtp.gmail.com
-- Help: Ex: smtp.gmail.com, smtp.office365.com

-- P910_PORTA_SMTP
-- Type: Number Field
-- Label: Porta
-- Required: Yes
-- Default: 587
-- Help: Portas comuns: 25, 465, 587

-- P910_USUARIO_SMTP
-- Type: Text Field
-- Label: Usuario
-- Required: Yes
-- Help: Geralmente o endereco de e-mail

-- P910_SENHA_SMTP
-- Type: Password
-- Label: Senha
-- Required: Yes

-- P910_EMAIL_REMETENTE
-- Type: Text Field
-- Label: E-mail Remetente
-- Required: Yes

-- P910_NOME_REMETENTE
-- Type: Text Field
-- Label: Nome do Remetente
-- Required: Yes
-- Help: Ex: Sistema de Contratos - Imobiliaria XYZ

-- P910_USA_SSL
-- Type: Switch
-- Label: Usar SSL/TLS
-- Default: 1

-- P910_USA_AUTENTICACAO
-- Type: Switch
-- Label: Usar Autenticacao
-- Default: 1

-- P910_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
REGIAO: Testar Configuracao
================================================================================
*/

-- P910_EMAIL_TESTE
-- Type: Text Field
-- Label: E-mail para Teste
-- Placeholder: Digite um e-mail para enviar teste

-- Botao: Enviar E-mail de Teste
-- Action: Execute PL/SQL

/*
================================================================================
PROCESSO: Salvar Configuracao Email
================================================================================
*/

/*
BEGIN
    MERGE INTO gc_configuracao_email cfg
    USING (SELECT :P910_IMOBILIARIA_ID AS imobiliaria_id FROM DUAL) src
    ON (cfg.imobiliaria_id = src.imobiliaria_id)
    WHEN MATCHED THEN
        UPDATE SET
            servidor_smtp = :P910_SERVIDOR_SMTP,
            porta_smtp = :P910_PORTA_SMTP,
            usuario_smtp = :P910_USUARIO_SMTP,
            senha_smtp = CASE WHEN :P910_SENHA_SMTP IS NOT NULL THEN :P910_SENHA_SMTP ELSE senha_smtp END,
            email_remetente = :P910_EMAIL_REMETENTE,
            nome_remetente = :P910_NOME_REMETENTE,
            usa_ssl = :P910_USA_SSL,
            usa_autenticacao = :P910_USA_AUTENTICACAO,
            ativo = :P910_ATIVO,
            atualizado_em = SYSTIMESTAMP
    WHEN NOT MATCHED THEN
        INSERT (imobiliaria_id, servidor_smtp, porta_smtp, usuario_smtp, senha_smtp,
                email_remetente, nome_remetente, usa_ssl, usa_autenticacao, ativo)
        VALUES (:P910_IMOBILIARIA_ID, :P910_SERVIDOR_SMTP, :P910_PORTA_SMTP, :P910_USUARIO_SMTP,
                :P910_SENHA_SMTP, :P910_EMAIL_REMETENTE, :P910_NOME_REMETENTE, :P910_USA_SSL,
                :P910_USA_AUTENTICACAO, :P910_ATIVO);
    COMMIT;
END;
*/

/*
================================================================================
PROCESSO: Enviar Email Teste
================================================================================
*/

/*
DECLARE
    v_resultado VARCHAR2(4000);
BEGIN
    v_resultado := pkg_notificacao.enviar_email_teste(
        p_imobiliaria_id => :P910_IMOBILIARIA_ID,
        p_destinatario => :P910_EMAIL_TESTE
    );

    IF v_resultado = 'OK' THEN
        APEX_APPLICATION.g_print_success_message := 'E-mail de teste enviado com sucesso!';
    ELSE
        RAISE_APPLICATION_ERROR(-20001, 'Erro: ' || v_resultado);
    END IF;
END;
*/

-- ============================================================================
-- PAGINA 920: CONFIGURACAO DE SMS
-- ============================================================================

/*
================================================================================
FORM: Configuracao SMS
================================================================================
*/

-- P920_IMOBILIARIA_ID
-- Type: Select List
-- Required: Yes

-- P920_PROVEDOR
-- Type: Select List
-- Label: Provedor SMS
-- Required: Yes
-- LOV: TWILIO;Twilio,ZENVIA;Zenvia,TOTALVOICE;TotalVoice,INFOBIP;Infobip
-- Help: Selecione o provedor de SMS

-- P920_API_URL
-- Type: Text Field
-- Label: URL da API
-- Required: Yes

-- P920_API_KEY
-- Type: Text Field
-- Label: API Key / Account SID
-- Required: Yes

-- P920_API_SECRET
-- Type: Password
-- Label: API Secret / Auth Token
-- Required: Yes

-- P920_NUMERO_REMETENTE
-- Type: Text Field
-- Label: Numero Remetente
-- Help: Numero de telefone para envio (formato: +5511999999999)

-- P920_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
PROCESSO: Salvar Configuracao SMS
================================================================================
*/

/*
BEGIN
    MERGE INTO gc_configuracao_sms cfg
    USING (SELECT :P920_IMOBILIARIA_ID AS imobiliaria_id FROM DUAL) src
    ON (cfg.imobiliaria_id = src.imobiliaria_id)
    WHEN MATCHED THEN
        UPDATE SET
            provedor = :P920_PROVEDOR,
            api_url = :P920_API_URL,
            api_key = :P920_API_KEY,
            api_secret = CASE WHEN :P920_API_SECRET IS NOT NULL THEN :P920_API_SECRET ELSE api_secret END,
            numero_remetente = :P920_NUMERO_REMETENTE,
            ativo = :P920_ATIVO,
            atualizado_em = SYSTIMESTAMP
    WHEN NOT MATCHED THEN
        INSERT (imobiliaria_id, provedor, api_url, api_key, api_secret, numero_remetente, ativo)
        VALUES (:P920_IMOBILIARIA_ID, :P920_PROVEDOR, :P920_API_URL, :P920_API_KEY,
                :P920_API_SECRET, :P920_NUMERO_REMETENTE, :P920_ATIVO);
    COMMIT;
END;
*/

-- ============================================================================
-- PAGINA 930: CONFIGURACAO DE WHATSAPP
-- ============================================================================

/*
================================================================================
FORM: Configuracao WhatsApp
================================================================================
*/

-- P930_IMOBILIARIA_ID
-- Type: Select List
-- Required: Yes

-- P930_PROVEDOR
-- Type: Select List
-- Label: Provedor WhatsApp
-- Required: Yes
-- LOV: EVOLUTION;Evolution API,TWILIO;Twilio WhatsApp,WPPCONNECT;WPPConnect,META;Meta Business API
-- Help: Selecione o provedor de WhatsApp

-- P930_API_URL
-- Type: Text Field
-- Label: URL da API
-- Required: Yes
-- Help: URL base da API do provedor

-- P930_API_KEY
-- Type: Text Field
-- Label: API Key / Token
-- Required: Yes

-- P930_INSTANCIA
-- Type: Text Field
-- Label: Instancia/Session
-- Help: Nome da instancia (para Evolution/WPPConnect)

-- P930_NUMERO_WHATSAPP
-- Type: Text Field
-- Label: Numero do WhatsApp
-- Required: Yes
-- Help: Numero conectado ao WhatsApp Business

-- P930_WEBHOOK_URL
-- Type: Text Field
-- Label: Webhook URL
-- Help: URL para receber callbacks (opcional)

-- P930_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
REGIAO: Status da Conexao
================================================================================
*/

-- Type: Region Display Selector
-- Source: Verificar status via API

/*
<div id="whatsapp-status" class="t-Alert">
    <div class="t-Alert-icon">
        <span class="fa fa-whatsapp"></span>
    </div>
    <div class="t-Alert-body">
        <span id="status-text">Verificando conexao...</span>
    </div>
</div>

<script>
apex.jQuery(function() {
    apex.server.process('VERIFICAR_STATUS_WHATSAPP', {
        x01: $v('P930_IMOBILIARIA_ID')
    }, {
        success: function(data) {
            if (data.connected) {
                $('#whatsapp-status').removeClass('t-Alert--danger').addClass('t-Alert--success');
                $('#status-text').text('Conectado: ' + data.phone);
            } else {
                $('#whatsapp-status').removeClass('t-Alert--success').addClass('t-Alert--danger');
                $('#status-text').text('Desconectado');
            }
        }
    });
});
</script>
*/

/*
================================================================================
PROCESSO: Salvar Configuracao WhatsApp
================================================================================
*/

/*
BEGIN
    MERGE INTO gc_configuracao_whatsapp cfg
    USING (SELECT :P930_IMOBILIARIA_ID AS imobiliaria_id FROM DUAL) src
    ON (cfg.imobiliaria_id = src.imobiliaria_id)
    WHEN MATCHED THEN
        UPDATE SET
            provedor = :P930_PROVEDOR,
            api_url = :P930_API_URL,
            api_key = CASE WHEN :P930_API_KEY IS NOT NULL THEN :P930_API_KEY ELSE api_key END,
            instancia = :P930_INSTANCIA,
            numero_whatsapp = :P930_NUMERO_WHATSAPP,
            webhook_url = :P930_WEBHOOK_URL,
            ativo = :P930_ATIVO,
            atualizado_em = SYSTIMESTAMP
    WHEN NOT MATCHED THEN
        INSERT (imobiliaria_id, provedor, api_url, api_key, instancia, numero_whatsapp, webhook_url, ativo)
        VALUES (:P930_IMOBILIARIA_ID, :P930_PROVEDOR, :P930_API_URL, :P930_API_KEY,
                :P930_INSTANCIA, :P930_NUMERO_WHATSAPP, :P930_WEBHOOK_URL, :P930_ATIVO);
    COMMIT;
END;
*/

-- ============================================================================
-- PAGINA 940: CADASTRO DE BANCOS
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Bancos
================================================================================
*/

-- Source SQL:
/*
SELECT
    b.codigo,
    b.nome,
    b.nome_curto,
    CASE b.ativo WHEN 1 THEN 'Ativo' ELSE 'Inativo' END AS status,
    (SELECT COUNT(*) FROM gc_conta_bancaria cb WHERE cb.banco = b.codigo) AS contas_vinculadas
FROM gc_banco b
ORDER BY b.codigo
*/

/*
================================================================================
FORM MODAL: Banco
================================================================================
*/

-- P941_CODIGO
-- Type: Text Field
-- Label: Codigo
-- Required: Yes
-- Max Length: 3

-- P941_NOME
-- Type: Text Field
-- Label: Nome Completo
-- Required: Yes

-- P941_NOME_CURTO
-- Type: Text Field
-- Label: Nome Curto

-- P941_ATIVO
-- Type: Switch
-- Default: 1

-- ============================================================================
-- PAGINA 950: PARAMETROS GERAIS
-- ============================================================================

/*
================================================================================
FORM: Parametros do Sistema
================================================================================
*/

-- P950_NOME_SISTEMA
-- Type: Text Field
-- Label: Nome do Sistema
-- Default: Sistema de Gestao de Contratos

-- P950_VERSAO
-- Type: Display Only
-- Label: Versao

-- P950_DIAS_ALERTA_VENCIMENTO
-- Type: Number Field
-- Label: Dias para Alerta de Vencimento
-- Default: 7
-- Help: Parcelas que vencem em X dias serao destacadas

-- P950_PERCENTUAL_MULTA_PADRAO
-- Type: Number Field
-- Label: Percentual de Multa Padrao (%)
-- Default: 2

-- P950_PERCENTUAL_JUROS_PADRAO
-- Type: Number Field
-- Label: Percentual de Juros Padrao (% ao dia)
-- Default: 0.033

-- P950_DIAS_CARENCIA_ENCARGOS
-- Type: Number Field
-- Label: Dias de Carencia para Encargos
-- Default: 0

-- P950_FORMATO_NUMERO_CONTRATO
-- Type: Text Field
-- Label: Formato Numero Contrato
-- Default: {ANO}/{SEQ}
-- Help: Variaveis: {ANO}, {MES}, {SEQ}, {IMOB}

-- P950_PROXIMO_SEQUENCIAL
-- Type: Number Field
-- Label: Proximo Sequencial
-- Default: 1

-- P950_LOGO_URL
-- Type: Text Field
-- Label: URL do Logo
-- Help: URL para o logo do sistema (cabecalho de boletos)

-- P950_TIMEZONE
-- Type: Select List
-- Label: Fuso Horario
-- Default: America/Sao_Paulo

/*
================================================================================
PROCESSO: Salvar Parametros
================================================================================
*/

/*
BEGIN
    FOR param IN (
        SELECT 'NOME_SISTEMA' AS chave, :P950_NOME_SISTEMA AS valor FROM DUAL UNION ALL
        SELECT 'DIAS_ALERTA_VENCIMENTO', :P950_DIAS_ALERTA_VENCIMENTO FROM DUAL UNION ALL
        SELECT 'PERCENTUAL_MULTA_PADRAO', :P950_PERCENTUAL_MULTA_PADRAO FROM DUAL UNION ALL
        SELECT 'PERCENTUAL_JUROS_PADRAO', :P950_PERCENTUAL_JUROS_PADRAO FROM DUAL UNION ALL
        SELECT 'DIAS_CARENCIA_ENCARGOS', :P950_DIAS_CARENCIA_ENCARGOS FROM DUAL UNION ALL
        SELECT 'FORMATO_NUMERO_CONTRATO', :P950_FORMATO_NUMERO_CONTRATO FROM DUAL UNION ALL
        SELECT 'PROXIMO_SEQUENCIAL', :P950_PROXIMO_SEQUENCIAL FROM DUAL UNION ALL
        SELECT 'LOGO_URL', :P950_LOGO_URL FROM DUAL UNION ALL
        SELECT 'TIMEZONE', :P950_TIMEZONE FROM DUAL
    )
    LOOP
        MERGE INTO gc_parametro p
        USING (SELECT param.chave AS chave FROM DUAL) src
        ON (p.chave = src.chave)
        WHEN MATCHED THEN
            UPDATE SET valor = param.valor, atualizado_em = SYSTIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (chave, valor) VALUES (param.chave, param.valor);
    END LOOP;
    COMMIT;
END;
*/

-- ============================================================================
-- PAGINA 960: CONFIGURACAO API BRCOBRANCA
-- ============================================================================

/*
================================================================================
FORM: Configuracao BRcobranca
================================================================================
*/

-- P960_API_URL
-- Type: Text Field
-- Label: URL da API BRcobranca
-- Required: Yes
-- Default: http://localhost:9292
-- Help: URL do servidor BRcobranca (Docker)

-- P960_TIMEOUT
-- Type: Number Field
-- Label: Timeout (segundos)
-- Default: 30

-- P960_RETENTATIVAS
-- Type: Number Field
-- Label: Numero de Retentativas
-- Default: 3

/*
================================================================================
REGIAO: Status da API
================================================================================
*/

-- Type: Region
/*
<div id="brcobranca-status" class="t-StatusList">
    <div class="t-StatusList-item">
        <span class="t-StatusList-marker" id="status-marker"></span>
        <span class="t-StatusList-label" id="status-label">Verificando...</span>
    </div>
</div>

<script>
apex.jQuery(function() {
    apex.server.process('VERIFICAR_STATUS_BRCOBRANCA', {}, {
        success: function(data) {
            if (data.online) {
                $('#status-marker').addClass('t-StatusList-marker--success');
                $('#status-label').text('API Online - Versao: ' + data.version);
            } else {
                $('#status-marker').addClass('t-StatusList-marker--danger');
                $('#status-label').text('API Offline');
            }
        },
        error: function() {
            $('#status-marker').addClass('t-StatusList-marker--danger');
            $('#status-label').text('Erro ao verificar status');
        }
    });
});
</script>
*/

/*
================================================================================
AJAX CALLBACK: VERIFICAR_STATUS_BRCOBRANCA
================================================================================
*/

/*
DECLARE
    v_response CLOB;
    v_url VARCHAR2(500);
BEGIN
    SELECT valor INTO v_url FROM gc_parametro WHERE chave = 'BRCOBRANCA_URL';

    v_response := APEX_WEB_SERVICE.make_rest_request(
        p_url => v_url || '/health',
        p_http_method => 'GET'
    );

    IF APEX_WEB_SERVICE.g_status_code = 200 THEN
        APEX_JSON.open_object;
        APEX_JSON.write('online', TRUE);
        APEX_JSON.write('version', APEX_JSON.get_varchar2(p_path => 'version', p_source => v_response));
        APEX_JSON.close_object;
    ELSE
        APEX_JSON.open_object;
        APEX_JSON.write('online', FALSE);
        APEX_JSON.close_object;
    END IF;

    HTP.p(APEX_JSON.get_clob_output);
EXCEPTION
    WHEN OTHERS THEN
        APEX_JSON.open_object;
        APEX_JSON.write('online', FALSE);
        APEX_JSON.write('error', SQLERRM);
        APEX_JSON.close_object;
        HTP.p(APEX_JSON.get_clob_output);
END;
*/

/*
================================================================================
PROCESSO: Salvar Configuracao BRcobranca
================================================================================
*/

/*
BEGIN
    pkg_brcobranca.set_api_url(:P960_API_URL);

    MERGE INTO gc_parametro p
    USING (SELECT 'BRCOBRANCA_TIMEOUT' AS chave FROM DUAL) src
    ON (p.chave = src.chave)
    WHEN MATCHED THEN UPDATE SET valor = :P960_TIMEOUT
    WHEN NOT MATCHED THEN INSERT (chave, valor) VALUES ('BRCOBRANCA_TIMEOUT', :P960_TIMEOUT);

    MERGE INTO gc_parametro p
    USING (SELECT 'BRCOBRANCA_RETENTATIVAS' AS chave FROM DUAL) src
    ON (p.chave = src.chave)
    WHEN MATCHED THEN UPDATE SET valor = :P960_RETENTATIVAS
    WHEN NOT MATCHED THEN INSERT (chave, valor) VALUES ('BRCOBRANCA_RETENTATIVAS', :P960_RETENTATIVAS);

    COMMIT;
END;
*/

/*
================================================================================
BOTAO: Testar Conexao
================================================================================
*/

/*
DECLARE
    v_resultado VARCHAR2(4000);
BEGIN
    v_resultado := pkg_brcobranca.testar_conexao();

    IF v_resultado = 'OK' THEN
        APEX_APPLICATION.g_print_success_message := 'Conexao com BRcobranca estabelecida com sucesso!';
    ELSE
        RAISE_APPLICATION_ERROR(-20001, 'Erro: ' || v_resultado);
    END IF;
END;
*/

-- ============================================================================
-- PAGINA 970: LOGS DO SISTEMA
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Logs
================================================================================
*/

-- Source SQL:
/*
SELECT
    l.id,
    l.processo,
    l.nivel,
    CASE l.nivel
        WHEN 'ERROR' THEN 'u-danger'
        WHEN 'WARNING' THEN 'u-warning'
        WHEN 'INFO' THEN 'u-color-1'
        ELSE 'u-normal'
    END AS nivel_css,
    l.mensagem,
    l.dados,
    l.usuario,
    TO_CHAR(l.criado_em, 'DD/MM/YYYY HH24:MI:SS') AS data_hora,
    l.ip_origem
FROM gc_log l
WHERE (:P970_NIVEL IS NULL OR l.nivel = :P970_NIVEL)
  AND (:P970_PROCESSO IS NULL OR l.processo LIKE '%' || :P970_PROCESSO || '%')
  AND (:P970_DATA_INI IS NULL OR l.criado_em >= TO_DATE(:P970_DATA_INI, 'DD/MM/YYYY'))
  AND (:P970_DATA_FIM IS NULL OR l.criado_em <= TO_DATE(:P970_DATA_FIM, 'DD/MM/YYYY') + 1)
ORDER BY l.criado_em DESC
*/

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P970_NIVEL
-- Type: Select List
-- LOV: ERROR;Erro,WARNING;Aviso,INFO;Info,DEBUG;Debug
-- Display Null: Yes (Todos)

-- P970_PROCESSO
-- Type: Text Field
-- Label: Processo

-- P970_DATA_INI / P970_DATA_FIM
-- Type: Date Picker

/*
================================================================================
BOTAO: Limpar Logs Antigos
================================================================================
*/

/*
BEGIN
    DELETE FROM gc_log
    WHERE criado_em < ADD_MONTHS(SYSDATE, -3);

    COMMIT;

    APEX_APPLICATION.g_print_success_message :=
        SQL%ROWCOUNT || ' registros de log removidos.';
END;
*/

-- ============================================================================
-- PAGINA 980: USUARIOS E PERMISSOES
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Usuarios
================================================================================
*/

-- Source SQL:
/*
SELECT
    u.user_id,
    u.user_name,
    u.email,
    u.first_name || ' ' || u.last_name AS nome_completo,
    u.is_admin,
    u.locked,
    u.created_on,
    u.last_login
FROM apex_users u
ORDER BY u.user_name
*/

-- Nota: Gestao de usuarios via APEX Administration

