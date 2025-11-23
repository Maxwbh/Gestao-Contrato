/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Package: PKG_BRCOBRANCA - Integracao com API BRcobranca
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Linkedin: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================

BRcobranca eh uma API Ruby/Docker para geracao de boletos bancarios brasileiros.
URL padrao: http://localhost:9292

Endpoints principais:
- POST /api/boleto           - Gera boleto PDF
- POST /api/boleto/multi     - Gera multiplos boletos PDF
- POST /api/remessa          - Gera arquivo de remessa CNAB
- POST /api/retorno          - Processa arquivo de retorno CNAB

Documentacao: https://github.com/akretion/boleto_cnab_api
==============================================================================
*/

CREATE OR REPLACE PACKAGE pkg_brcobranca AS
    /*
    Package para integracao com a API BRcobranca (boleto_cnab_api).
    Utiliza APEX_WEB_SERVICE ou UTL_HTTP para chamadas REST.

    Requisitos:
    - Oracle APEX instalado (para APEX_WEB_SERVICE) ou
    - ACL configurada para UTL_HTTP
    - BRcobranca API rodando (Docker: akretion/boleto_cnab_api)
    */

    -- Configuracao da API
    g_api_url VARCHAR2(200) := 'http://localhost:9292';

    -- Tipos de resposta
    TYPE t_boleto_response IS RECORD (
        sucesso        BOOLEAN,
        nosso_numero   VARCHAR2(30),
        codigo_barras  VARCHAR2(50),
        linha_digitavel VARCHAR2(60),
        pdf_base64     CLOB,
        pix_copia_cola CLOB,
        erro_mensagem  VARCHAR2(4000)
    );

    TYPE t_remessa_response IS RECORD (
        sucesso        BOOLEAN,
        conteudo       CLOB,
        nome_arquivo   VARCHAR2(100),
        erro_mensagem  VARCHAR2(4000)
    );

    -- ========================================================================
    -- PROCEDURES DE CONFIGURACAO
    -- ========================================================================

    -- Define a URL base da API BRcobranca
    PROCEDURE set_api_url(p_url IN VARCHAR2);

    -- Retorna a URL atual da API
    FUNCTION get_api_url RETURN VARCHAR2;

    -- ========================================================================
    -- GERACAO DE BOLETOS
    -- ========================================================================

    -- Gera boleto para uma parcela usando BRcobranca
    PROCEDURE gerar_boleto_brcobranca(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER DEFAULT NULL,
        p_formato           IN VARCHAR2 DEFAULT 'pdf', -- pdf, png, base64
        p_sucesso           OUT BOOLEAN,
        p_nosso_numero      OUT VARCHAR2,
        p_codigo_barras     OUT VARCHAR2,
        p_linha_digitavel   OUT VARCHAR2,
        p_pdf_content       OUT BLOB,
        p_msg_erro          OUT VARCHAR2
    );

    -- Gera multiplos boletos em lote
    PROCEDURE gerar_boletos_lote(
        p_contrato_id       IN NUMBER,
        p_conta_bancaria_id IN NUMBER DEFAULT NULL,
        p_apenas_pendentes  IN BOOLEAN DEFAULT TRUE,
        p_total_gerados     OUT NUMBER,
        p_total_erros       OUT NUMBER,
        p_msg_erro          OUT VARCHAR2
    );

    -- ========================================================================
    -- ARQUIVOS CNAB (REMESSA)
    -- ========================================================================

    -- Gera arquivo de remessa CNAB usando BRcobranca
    PROCEDURE gerar_remessa_brcobranca(
        p_arquivo_remessa_id IN NUMBER,
        p_sucesso            OUT BOOLEAN,
        p_conteudo           OUT CLOB,
        p_msg_erro           OUT VARCHAR2
    );

    -- Gera remessa para parcelas selecionadas
    PROCEDURE gerar_remessa_parcelas(
        p_conta_bancaria_id  IN NUMBER,
        p_parcelas_ids       IN VARCHAR2, -- IDs separados por virgula
        p_layout             IN VARCHAR2 DEFAULT 'cnab240',
        p_arquivo_remessa_id OUT NUMBER,
        p_conteudo           OUT CLOB,
        p_msg_erro           OUT VARCHAR2
    );

    -- ========================================================================
    -- ARQUIVOS CNAB (RETORNO)
    -- ========================================================================

    -- Processa arquivo de retorno usando BRcobranca
    PROCEDURE processar_retorno_brcobranca(
        p_arquivo_retorno_id IN NUMBER,
        p_conteudo           IN CLOB,
        p_total_processados  OUT NUMBER,
        p_total_erros        OUT NUMBER,
        p_msg_erro           OUT VARCHAR2
    );

    -- ========================================================================
    -- FUNCOES AUXILIARES
    -- ========================================================================

    -- Monta JSON do cedente (imobiliaria/beneficiario)
    FUNCTION montar_json_cedente(
        p_imobiliaria_id    IN NUMBER,
        p_conta_bancaria_id IN NUMBER
    ) RETURN CLOB;

    -- Monta JSON do sacado (comprador)
    FUNCTION montar_json_sacado(
        p_comprador_id IN NUMBER
    ) RETURN CLOB;

    -- Monta JSON do boleto completo
    FUNCTION montar_json_boleto(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER
    ) RETURN CLOB;

    -- Converte codigo do banco para nome BRcobranca
    FUNCTION get_banco_brcobranca(
        p_codigo_banco IN VARCHAR2
    ) RETURN VARCHAR2;

END pkg_brcobranca;
/

CREATE OR REPLACE PACKAGE BODY pkg_brcobranca AS

    -- ========================================================================
    -- SET API URL
    -- ========================================================================
    PROCEDURE set_api_url(p_url IN VARCHAR2) IS
    BEGIN
        g_api_url := p_url;
    END set_api_url;

    -- ========================================================================
    -- GET API URL
    -- ========================================================================
    FUNCTION get_api_url RETURN VARCHAR2 IS
    BEGIN
        RETURN g_api_url;
    END get_api_url;

    -- ========================================================================
    -- GET BANCO BRCOBRANCA
    -- ========================================================================
    FUNCTION get_banco_brcobranca(
        p_codigo_banco IN VARCHAR2
    ) RETURN VARCHAR2 IS
    BEGIN
        RETURN CASE p_codigo_banco
            WHEN '001' THEN 'banco_brasil'
            WHEN '004' THEN 'banco_nordeste'
            WHEN '021' THEN 'banestes'
            WHEN '033' THEN 'santander'
            WHEN '041' THEN 'banrisul'
            WHEN '070' THEN 'brb'
            WHEN '077' THEN 'banco_inter'
            WHEN '104' THEN 'caixa'
            WHEN '133' THEN 'cresol'
            WHEN '136' THEN 'unicred'
            WHEN '237' THEN 'bradesco'
            WHEN '341' THEN 'itau'
            WHEN '422' THEN 'safra'
            WHEN '748' THEN 'sicredi'
            WHEN '756' THEN 'sicoob'
            ELSE 'banco_brasil' -- default
        END;
    END get_banco_brcobranca;

    -- ========================================================================
    -- MONTAR JSON CEDENTE
    -- ========================================================================
    FUNCTION montar_json_cedente(
        p_imobiliaria_id    IN NUMBER,
        p_conta_bancaria_id IN NUMBER
    ) RETURN CLOB IS
        v_imob   gc_imobiliaria%ROWTYPE;
        v_conta  gc_conta_bancaria%ROWTYPE;
        v_json   CLOB;
    BEGIN
        SELECT * INTO v_imob FROM gc_imobiliaria WHERE id = p_imobiliaria_id;
        SELECT * INTO v_conta FROM gc_conta_bancaria WHERE id = p_conta_bancaria_id;

        v_json := '{' ||
            '"cedente": "' || REPLACE(v_imob.razao_social, '"', '\"') || '",' ||
            '"cedente_endereco": "' || NVL(v_imob.logradouro, '') || ', ' || NVL(v_imob.numero, '') || '",' ||
            '"documento_cedente": "' || REPLACE(v_imob.cnpj, '.', '') || '",' ||
            '"agencia": "' || v_conta.agencia || '",' ||
            '"conta_corrente": "' || v_conta.conta || '",' ||
            '"convenio": "' || NVL(v_conta.convenio, '') || '",' ||
            '"carteira": "' || NVL(v_conta.carteira, '') || '"' ||
        '}';

        RETURN v_json;
    END montar_json_cedente;

    -- ========================================================================
    -- MONTAR JSON SACADO
    -- ========================================================================
    FUNCTION montar_json_sacado(
        p_comprador_id IN NUMBER
    ) RETURN CLOB IS
        v_compr  gc_comprador%ROWTYPE;
        v_doc    VARCHAR2(20);
        v_json   CLOB;
    BEGIN
        SELECT * INTO v_compr FROM gc_comprador WHERE id = p_comprador_id;

        v_doc := CASE v_compr.tipo_pessoa
            WHEN 'PF' THEN REPLACE(REPLACE(v_compr.cpf, '.', ''), '-', '')
            ELSE REPLACE(REPLACE(REPLACE(v_compr.cnpj, '.', ''), '-', ''), '/', '')
        END;

        v_json := '{' ||
            '"sacado": "' || REPLACE(v_compr.nome, '"', '\"') || '",' ||
            '"documento_sacado": "' || v_doc || '",' ||
            '"sacado_endereco": "' || NVL(v_compr.logradouro, '') || ', ' || NVL(v_compr.numero, '') || '",' ||
            '"bairro": "' || NVL(v_compr.bairro, '') || '",' ||
            '"cidade": "' || NVL(v_compr.cidade, '') || '",' ||
            '"uf": "' || NVL(v_compr.estado, '') || '",' ||
            '"cep": "' || REPLACE(NVL(v_compr.cep, ''), '-', '') || '"' ||
        '}';

        RETURN v_json;
    END montar_json_sacado;

    -- ========================================================================
    -- MONTAR JSON BOLETO
    -- ========================================================================
    FUNCTION montar_json_boleto(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER
    ) RETURN CLOB IS
        v_parcela    gc_parcela%ROWTYPE;
        v_contrato   gc_contrato%ROWTYPE;
        v_conta      gc_conta_bancaria%ROWTYPE;
        v_imob       gc_imobiliaria%ROWTYPE;
        v_compr      gc_comprador%ROWTYPE;
        v_nosso_num  VARCHAR2(30);
        v_num_doc    VARCHAR2(25);
        v_banco      VARCHAR2(30);
        v_json       CLOB;
        v_doc_sacado VARCHAR2(20);
        v_doc_cedente VARCHAR2(20);
    BEGIN
        -- Buscar dados
        SELECT * INTO v_parcela FROM gc_parcela WHERE id = p_parcela_id;
        SELECT * INTO v_contrato FROM gc_contrato WHERE id = v_parcela.contrato_id;
        SELECT * INTO v_conta FROM gc_conta_bancaria WHERE id = p_conta_bancaria_id;
        SELECT * INTO v_imob FROM gc_imobiliaria WHERE id = v_contrato.imobiliaria_id;
        SELECT * INTO v_compr FROM gc_comprador WHERE id = v_contrato.comprador_id;

        -- Obter proximo nosso numero se nao existir
        IF v_parcela.nosso_numero IS NULL THEN
            v_nosso_num := pkg_boleto.obter_proximo_nosso_numero(p_conta_bancaria_id);
        ELSE
            v_nosso_num := v_parcela.nosso_numero;
        END IF;

        v_num_doc := pkg_boleto.gerar_numero_documento(p_parcela_id);
        v_banco := get_banco_brcobranca(v_conta.banco);

        -- Formatar documentos
        v_doc_cedente := REPLACE(REPLACE(REPLACE(v_imob.cnpj, '.', ''), '-', ''), '/', '');
        v_doc_sacado := CASE v_compr.tipo_pessoa
            WHEN 'PF' THEN REPLACE(REPLACE(v_compr.cpf, '.', ''), '-', '')
            ELSE REPLACE(REPLACE(REPLACE(v_compr.cnpj, '.', ''), '-', ''), '/', '')
        END;

        -- Montar JSON para BRcobranca API
        v_json := '{' ||
            '"banco": "' || v_banco || '",' ||
            '"valor": ' || TO_CHAR(v_parcela.valor_atual, 'FM999999999990.00') || ',' ||
            '"cedente": "' || REPLACE(v_imob.razao_social, '"', '\"') || '",' ||
            '"documento_cedente": "' || v_doc_cedente || '",' ||
            '"sacado": "' || REPLACE(v_compr.nome, '"', '\"') || '",' ||
            '"sacado_documento": "' || v_doc_sacado || '",' ||
            '"agencia": "' || v_conta.agencia || '",' ||
            '"conta_corrente": "' || v_conta.conta || '",' ||
            '"convenio": "' || NVL(v_conta.convenio, '') || '",' ||
            '"carteira": "' || NVL(v_conta.carteira, '') || '",' ||
            '"nosso_numero": "' || v_nosso_num || '",' ||
            '"numero_documento": "' || v_num_doc || '",' ||
            '"data_vencimento": "' || TO_CHAR(v_parcela.data_vencimento, 'YYYY-MM-DD') || '",' ||
            '"data_documento": "' || TO_CHAR(SYSDATE, 'YYYY-MM-DD') || '",' ||
            '"sacado_endereco": "' || NVL(v_compr.logradouro, '') || ', ' || NVL(v_compr.numero, '') || '",' ||
            '"sacado_bairro": "' || NVL(v_compr.bairro, '') || '",' ||
            '"sacado_cidade": "' || NVL(v_compr.cidade, '') || '",' ||
            '"sacado_uf": "' || NVL(v_compr.estado, 'SP') || '",' ||
            '"sacado_cep": "' || REPLACE(NVL(v_compr.cep, '00000000'), '-', '') || '"' ||
        '}';

        RETURN v_json;
    END montar_json_boleto;

    -- ========================================================================
    -- GERAR BOLETO BRCOBRANCA
    -- ========================================================================
    PROCEDURE gerar_boleto_brcobranca(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER DEFAULT NULL,
        p_formato           IN VARCHAR2 DEFAULT 'pdf',
        p_sucesso           OUT BOOLEAN,
        p_nosso_numero      OUT VARCHAR2,
        p_codigo_barras     OUT VARCHAR2,
        p_linha_digitavel   OUT VARCHAR2,
        p_pdf_content       OUT BLOB,
        p_msg_erro          OUT VARCHAR2
    ) IS
        v_conta_id    NUMBER;
        v_parcela     gc_parcela%ROWTYPE;
        v_contrato    gc_contrato%ROWTYPE;
        v_json_req    CLOB;
        v_json_resp   CLOB;
        v_url         VARCHAR2(500);
        v_http_code   NUMBER;
    BEGIN
        p_sucesso := FALSE;
        p_msg_erro := NULL;

        -- Buscar parcela
        SELECT * INTO v_parcela FROM gc_parcela WHERE id = p_parcela_id;

        IF v_parcela.pago = 1 THEN
            p_msg_erro := 'Parcela ja esta paga';
            RETURN;
        END IF;

        -- Buscar contrato
        SELECT * INTO v_contrato FROM gc_contrato WHERE id = v_parcela.contrato_id;

        -- Determinar conta bancaria
        v_conta_id := COALESCE(
            p_conta_bancaria_id,
            v_contrato.conta_bancaria_padrao_id,
            (SELECT id FROM gc_conta_bancaria
             WHERE imobiliaria_id = v_contrato.imobiliaria_id
               AND principal = 1 AND ativo = 1
             FETCH FIRST 1 ROW ONLY)
        );

        IF v_conta_id IS NULL THEN
            p_msg_erro := 'Nenhuma conta bancaria disponivel';
            RETURN;
        END IF;

        -- Montar JSON do boleto
        v_json_req := montar_json_boleto(p_parcela_id, v_conta_id);

        -- URL da API
        v_url := g_api_url || '/api/boleto';

        -- Chamar API BRcobranca usando APEX_WEB_SERVICE
        BEGIN
            APEX_WEB_SERVICE.g_request_headers.DELETE;
            APEX_WEB_SERVICE.g_request_headers(1).name := 'Content-Type';
            APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

            v_json_resp := APEX_WEB_SERVICE.make_rest_request(
                p_url         => v_url,
                p_http_method => 'POST',
                p_body        => v_json_req
            );

            v_http_code := APEX_WEB_SERVICE.g_status_code;

            IF v_http_code = 200 OR v_http_code = 201 THEN
                -- Extrair dados da resposta JSON
                -- BRcobranca retorna PDF em base64
                p_nosso_numero := JSON_VALUE(v_json_resp, '$.nosso_numero');
                p_codigo_barras := JSON_VALUE(v_json_resp, '$.codigo_barras');
                p_linha_digitavel := JSON_VALUE(v_json_resp, '$.linha_digitavel');

                -- Decodificar PDF base64 se presente
                DECLARE
                    v_pdf_base64 CLOB;
                BEGIN
                    v_pdf_base64 := JSON_VALUE(v_json_resp, '$.pdf' RETURNING CLOB);
                    IF v_pdf_base64 IS NOT NULL THEN
                        p_pdf_content := APEX_WEB_SERVICE.clobbase642blob(v_pdf_base64);
                    END IF;
                END;

                -- Registrar boleto na parcela
                pkg_boleto.registrar_boleto_gerado(
                    p_parcela_id        => p_parcela_id,
                    p_conta_bancaria_id => v_conta_id,
                    p_nosso_numero      => p_nosso_numero,
                    p_codigo_barras     => p_codigo_barras,
                    p_linha_digitavel   => p_linha_digitavel,
                    p_valor_boleto      => v_parcela.valor_atual,
                    p_msg_erro          => p_msg_erro
                );

                IF p_msg_erro IS NULL THEN
                    -- Salvar PDF
                    IF p_pdf_content IS NOT NULL THEN
                        UPDATE gc_parcela
                        SET boleto_pdf = p_pdf_content,
                            boleto_pdf_nome = 'boleto_' || v_contrato.numero_contrato ||
                                             '_' || v_parcela.numero_parcela || '.pdf'
                        WHERE id = p_parcela_id;
                        COMMIT;
                    END IF;

                    p_sucesso := TRUE;
                END IF;
            ELSE
                p_msg_erro := 'Erro na API BRcobranca. HTTP ' || v_http_code ||
                             ': ' || SUBSTR(v_json_resp, 1, 500);
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                p_msg_erro := 'Erro ao chamar API BRcobranca: ' || SQLERRM;
        END;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Parcela nao encontrada: ' || p_parcela_id;
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao gerar boleto: ' || SQLERRM;
    END gerar_boleto_brcobranca;

    -- ========================================================================
    -- GERAR BOLETOS LOTE
    -- ========================================================================
    PROCEDURE gerar_boletos_lote(
        p_contrato_id       IN NUMBER,
        p_conta_bancaria_id IN NUMBER DEFAULT NULL,
        p_apenas_pendentes  IN BOOLEAN DEFAULT TRUE,
        p_total_gerados     OUT NUMBER,
        p_total_erros       OUT NUMBER,
        p_msg_erro          OUT VARCHAR2
    ) IS
        v_sucesso        BOOLEAN;
        v_nosso_numero   VARCHAR2(30);
        v_codigo_barras  VARCHAR2(50);
        v_linha_digitavel VARCHAR2(60);
        v_pdf_content    BLOB;
        v_msg            VARCHAR2(4000);
    BEGIN
        p_total_gerados := 0;
        p_total_erros := 0;
        p_msg_erro := NULL;

        FOR r IN (
            SELECT id
            FROM gc_parcela
            WHERE contrato_id = p_contrato_id
              AND pago = 0
              AND (
                  NOT p_apenas_pendentes
                  OR status_boleto = 'NAO_GERADO'
              )
            ORDER BY numero_parcela
        ) LOOP
            gerar_boleto_brcobranca(
                p_parcela_id        => r.id,
                p_conta_bancaria_id => p_conta_bancaria_id,
                p_sucesso           => v_sucesso,
                p_nosso_numero      => v_nosso_numero,
                p_codigo_barras     => v_codigo_barras,
                p_linha_digitavel   => v_linha_digitavel,
                p_pdf_content       => v_pdf_content,
                p_msg_erro          => v_msg
            );

            IF v_sucesso THEN
                p_total_gerados := p_total_gerados + 1;
            ELSE
                p_total_erros := p_total_erros + 1;
                p_msg_erro := NVL(p_msg_erro, '') || 'Parcela ' || r.id || ': ' || v_msg || CHR(10);
            END IF;
        END LOOP;

    END gerar_boletos_lote;

    -- ========================================================================
    -- GERAR REMESSA BRCOBRANCA
    -- ========================================================================
    PROCEDURE gerar_remessa_brcobranca(
        p_arquivo_remessa_id IN NUMBER,
        p_sucesso            OUT BOOLEAN,
        p_conteudo           OUT CLOB,
        p_msg_erro           OUT VARCHAR2
    ) IS
        v_remessa      gc_arquivo_remessa%ROWTYPE;
        v_conta        gc_conta_bancaria%ROWTYPE;
        v_imob         gc_imobiliaria%ROWTYPE;
        v_banco        VARCHAR2(30);
        v_json_req     CLOB;
        v_json_resp    CLOB;
        v_boletos_json CLOB;
        v_url          VARCHAR2(500);
        v_http_code    NUMBER;
        v_first        BOOLEAN := TRUE;
    BEGIN
        p_sucesso := FALSE;
        p_msg_erro := NULL;

        -- Buscar dados da remessa
        SELECT * INTO v_remessa FROM gc_arquivo_remessa WHERE id = p_arquivo_remessa_id;
        SELECT * INTO v_conta FROM gc_conta_bancaria WHERE id = v_remessa.conta_bancaria_id;
        SELECT * INTO v_imob FROM gc_imobiliaria WHERE id = v_conta.imobiliaria_id;

        v_banco := get_banco_brcobranca(v_conta.banco);

        -- Montar array de boletos
        v_boletos_json := '[';
        FOR r IN (
            SELECT p.*
            FROM gc_item_remessa ir
            JOIN gc_parcela p ON p.id = ir.parcela_id
            WHERE ir.arquivo_remessa_id = p_arquivo_remessa_id
            ORDER BY ir.id
        ) LOOP
            IF NOT v_first THEN
                v_boletos_json := v_boletos_json || ',';
            END IF;
            v_first := FALSE;

            v_boletos_json := v_boletos_json || montar_json_boleto(r.id, v_conta.id);
        END LOOP;
        v_boletos_json := v_boletos_json || ']';

        -- Montar JSON da remessa
        v_json_req := '{' ||
            '"banco": "' || v_banco || '",' ||
            '"tipo": "' || LOWER(REPLACE(v_remessa.layout, '_', '')) || '",' ||
            '"numero_remessa": ' || v_remessa.numero_remessa || ',' ||
            '"pagamentos": ' || v_boletos_json ||
        '}';

        -- URL da API
        v_url := g_api_url || '/api/remessa';

        -- Chamar API BRcobranca
        BEGIN
            APEX_WEB_SERVICE.g_request_headers.DELETE;
            APEX_WEB_SERVICE.g_request_headers(1).name := 'Content-Type';
            APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

            v_json_resp := APEX_WEB_SERVICE.make_rest_request(
                p_url         => v_url,
                p_http_method => 'POST',
                p_body        => v_json_req
            );

            v_http_code := APEX_WEB_SERVICE.g_status_code;

            IF v_http_code = 200 OR v_http_code = 201 THEN
                -- BRcobranca retorna o conteudo do arquivo CNAB
                p_conteudo := JSON_VALUE(v_json_resp, '$.remessa' RETURNING CLOB);

                IF p_conteudo IS NULL THEN
                    p_conteudo := v_json_resp; -- Pode retornar direto o conteudo
                END IF;

                -- Atualizar arquivo de remessa
                UPDATE gc_arquivo_remessa
                SET arquivo = UTL_RAW.cast_to_raw(p_conteudo),
                    status = 'GERADO'
                WHERE id = p_arquivo_remessa_id;

                pkg_boleto.finalizar_remessa(p_arquivo_remessa_id, p_msg_erro);

                IF p_msg_erro IS NULL THEN
                    p_sucesso := TRUE;
                END IF;

                COMMIT;
            ELSE
                p_msg_erro := 'Erro na API BRcobranca. HTTP ' || v_http_code ||
                             ': ' || SUBSTR(v_json_resp, 1, 500);
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                p_msg_erro := 'Erro ao chamar API BRcobranca: ' || SQLERRM;
        END;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Arquivo de remessa nao encontrado';
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao gerar remessa: ' || SQLERRM;
    END gerar_remessa_brcobranca;

    -- ========================================================================
    -- GERAR REMESSA PARCELAS
    -- ========================================================================
    PROCEDURE gerar_remessa_parcelas(
        p_conta_bancaria_id  IN NUMBER,
        p_parcelas_ids       IN VARCHAR2,
        p_layout             IN VARCHAR2 DEFAULT 'cnab240',
        p_arquivo_remessa_id OUT NUMBER,
        p_conteudo           OUT CLOB,
        p_msg_erro           OUT VARCHAR2
    ) IS
        v_numero_remessa NUMBER;
        v_sucesso        BOOLEAN;
        v_parcela_id     NUMBER;
        v_pos1           NUMBER := 1;
        v_pos2           NUMBER;
        v_lista          VARCHAR2(32000);
    BEGIN
        p_msg_erro := NULL;

        -- Criar arquivo de remessa
        pkg_boleto.criar_arquivo_remessa(
            p_conta_bancaria_id => p_conta_bancaria_id,
            p_layout            => UPPER(REPLACE(p_layout, 'cnab', 'CNAB_')),
            p_arquivo_id        => p_arquivo_remessa_id,
            p_numero_remessa    => v_numero_remessa,
            p_msg_erro          => p_msg_erro
        );

        IF p_msg_erro IS NOT NULL THEN
            RETURN;
        END IF;

        -- Adicionar parcelas
        v_lista := p_parcelas_ids || ',';
        LOOP
            v_pos2 := INSTR(v_lista, ',', v_pos1);
            EXIT WHEN v_pos2 = 0;

            v_parcela_id := TO_NUMBER(TRIM(SUBSTR(v_lista, v_pos1, v_pos2 - v_pos1)));

            IF v_parcela_id IS NOT NULL THEN
                pkg_boleto.adicionar_item_remessa(
                    p_arquivo_remessa_id => p_arquivo_remessa_id,
                    p_parcela_id         => v_parcela_id,
                    p_msg_erro           => p_msg_erro
                );

                IF p_msg_erro IS NOT NULL THEN
                    -- Log erro mas continua
                    DBMS_OUTPUT.PUT_LINE('Erro parcela ' || v_parcela_id || ': ' || p_msg_erro);
                    p_msg_erro := NULL;
                END IF;
            END IF;

            v_pos1 := v_pos2 + 1;
        END LOOP;

        -- Gerar arquivo via BRcobranca
        gerar_remessa_brcobranca(
            p_arquivo_remessa_id => p_arquivo_remessa_id,
            p_sucesso            => v_sucesso,
            p_conteudo           => p_conteudo,
            p_msg_erro           => p_msg_erro
        );

    END gerar_remessa_parcelas;

    -- ========================================================================
    -- PROCESSAR RETORNO BRCOBRANCA
    -- ========================================================================
    PROCEDURE processar_retorno_brcobranca(
        p_arquivo_retorno_id IN NUMBER,
        p_conteudo           IN CLOB,
        p_total_processados  OUT NUMBER,
        p_total_erros        OUT NUMBER,
        p_msg_erro           OUT VARCHAR2
    ) IS
        v_retorno    gc_arquivo_retorno%ROWTYPE;
        v_conta      gc_conta_bancaria%ROWTYPE;
        v_banco      VARCHAR2(30);
        v_json_req   CLOB;
        v_json_resp  CLOB;
        v_url        VARCHAR2(500);
        v_http_code  NUMBER;
        v_registros  JSON_ARRAY_T;
        v_registro   JSON_OBJECT_T;
        v_nosso_num  VARCHAR2(30);
        v_parcela_id NUMBER;
        v_msg        VARCHAR2(4000);
    BEGIN
        p_total_processados := 0;
        p_total_erros := 0;
        p_msg_erro := NULL;

        -- Buscar dados do retorno
        SELECT * INTO v_retorno FROM gc_arquivo_retorno WHERE id = p_arquivo_retorno_id;
        SELECT * INTO v_conta FROM gc_conta_bancaria WHERE id = v_retorno.conta_bancaria_id;

        v_banco := get_banco_brcobranca(v_conta.banco);

        -- Montar JSON da requisicao
        v_json_req := '{' ||
            '"banco": "' || v_banco || '",' ||
            '"tipo": "' || LOWER(REPLACE(v_retorno.layout, '_', '')) || '",' ||
            '"arquivo": "' || REPLACE(REPLACE(p_conteudo, CHR(10), '\n'), CHR(13), '') || '"' ||
        '}';

        -- URL da API
        v_url := g_api_url || '/api/retorno';

        -- Chamar API BRcobranca
        BEGIN
            APEX_WEB_SERVICE.g_request_headers.DELETE;
            APEX_WEB_SERVICE.g_request_headers(1).name := 'Content-Type';
            APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

            v_json_resp := APEX_WEB_SERVICE.make_rest_request(
                p_url         => v_url,
                p_http_method => 'POST',
                p_body        => v_json_req
            );

            v_http_code := APEX_WEB_SERVICE.g_status_code;

            IF v_http_code = 200 OR v_http_code = 201 THEN
                -- Processar array de registros retornados
                -- A API retorna um array com os registros processados

                -- Para cada registro no retorno
                FOR r IN (
                    SELECT jt.*
                    FROM JSON_TABLE(v_json_resp, '$.registros[*]'
                        COLUMNS (
                            nosso_numero    VARCHAR2(30) PATH '$.nosso_numero',
                            valor_pago      NUMBER       PATH '$.valor_pago',
                            data_ocorrencia VARCHAR2(10) PATH '$.data_ocorrencia',
                            codigo_ocorr    VARCHAR2(10) PATH '$.codigo_ocorrencia',
                            tipo_ocorr      VARCHAR2(20) PATH '$.tipo_ocorrencia'
                        )
                    ) jt
                ) LOOP
                    -- Buscar parcela pelo nosso numero
                    BEGIN
                        SELECT id INTO v_parcela_id
                        FROM gc_parcela
                        WHERE nosso_numero = r.nosso_numero
                          AND conta_bancaria_id = v_conta.id
                        FETCH FIRST 1 ROW ONLY;
                    EXCEPTION
                        WHEN NO_DATA_FOUND THEN
                            v_parcela_id := NULL;
                    END;

                    -- Inserir item de retorno
                    INSERT INTO gc_item_retorno (
                        arquivo_retorno_id,
                        parcela_id,
                        nosso_numero,
                        codigo_ocorrencia,
                        tipo_ocorrencia,
                        valor_pago,
                        data_ocorrencia
                    ) VALUES (
                        p_arquivo_retorno_id,
                        v_parcela_id,
                        r.nosso_numero,
                        r.codigo_ocorr,
                        NVL(r.tipo_ocorr, 'OUTROS'),
                        r.valor_pago,
                        TO_DATE(r.data_ocorrencia, 'YYYY-MM-DD')
                    ) RETURNING id INTO v_parcela_id; -- Reusar variavel

                    -- Processar item
                    pkg_boleto.processar_item_retorno(v_parcela_id, v_msg);

                    IF v_msg IS NULL THEN
                        p_total_processados := p_total_processados + 1;
                    ELSE
                        p_total_erros := p_total_erros + 1;
                    END IF;
                END LOOP;

                -- Atualizar arquivo de retorno
                UPDATE gc_arquivo_retorno
                SET status = CASE
                        WHEN p_total_erros = 0 THEN 'PROCESSADO'
                        WHEN p_total_processados > 0 THEN 'PROCESSADO_PARCIAL'
                        ELSE 'ERRO'
                    END,
                    data_processamento = SYSTIMESTAMP,
                    total_registros = p_total_processados + p_total_erros,
                    registros_processados = p_total_processados,
                    registros_erro = p_total_erros
                WHERE id = p_arquivo_retorno_id;

                COMMIT;
            ELSE
                p_msg_erro := 'Erro na API BRcobranca. HTTP ' || v_http_code ||
                             ': ' || SUBSTR(v_json_resp, 1, 500);
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                p_msg_erro := 'Erro ao processar retorno: ' || SQLERRM;
        END;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Arquivo de retorno nao encontrado';
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao processar retorno: ' || SQLERRM;
    END processar_retorno_brcobranca;

END pkg_brcobranca;
/

-- Verificar compilacao
SELECT object_name, status
FROM user_objects
WHERE object_name = 'PKG_BRCOBRANCA';

SHOW ERRORS PACKAGE BODY pkg_brcobranca;
