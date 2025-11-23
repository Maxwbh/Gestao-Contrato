/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Package: PKG_BOLETO - Logica de Negocios de Boletos
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Linkedin: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================
*/

CREATE OR REPLACE PACKAGE pkg_boleto AS
    /*
    Package para gerenciamento de boletos bancarios.
    Inclui funcoes para:
    - Geracao de boletos
    - Geracao de nosso numero
    - Processamento de arquivos CNAB
    - Registro de pagamentos via boleto
    */

    -- Constantes de Status
    c_status_nao_gerado  CONSTANT VARCHAR2(15) := 'NAO_GERADO';
    c_status_gerado      CONSTANT VARCHAR2(15) := 'GERADO';
    c_status_registrado  CONSTANT VARCHAR2(15) := 'REGISTRADO';
    c_status_pago        CONSTANT VARCHAR2(15) := 'PAGO';
    c_status_vencido     CONSTANT VARCHAR2(15) := 'VENCIDO';
    c_status_cancelado   CONSTANT VARCHAR2(15) := 'CANCELADO';
    c_status_protestado  CONSTANT VARCHAR2(15) := 'PROTESTADO';
    c_status_baixado     CONSTANT VARCHAR2(15) := 'BAIXADO';

    -- ========================================================================
    -- PROCEDURES DE BOLETOS
    -- ========================================================================

    -- Gera o numero do documento para o boleto
    FUNCTION gerar_numero_documento(
        p_parcela_id IN NUMBER
    ) RETURN VARCHAR2;

    -- Obtem o proximo nosso numero disponivel
    FUNCTION obter_proximo_nosso_numero(
        p_conta_bancaria_id IN NUMBER
    ) RETURN VARCHAR2;

    -- Prepara dados para geracao de boleto
    PROCEDURE preparar_boleto(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER DEFAULT NULL,
        p_forcar            IN BOOLEAN DEFAULT FALSE,
        p_nosso_numero      OUT VARCHAR2,
        p_num_documento     OUT VARCHAR2,
        p_valor_boleto      OUT NUMBER,
        p_data_vencimento   OUT DATE,
        p_dados_sacado      OUT VARCHAR2,
        p_dados_beneficiario OUT VARCHAR2,
        p_msg_erro          OUT VARCHAR2
    );

    -- Registra geracao de boleto na parcela
    PROCEDURE registrar_boleto_gerado(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER,
        p_nosso_numero      IN VARCHAR2,
        p_codigo_barras     IN VARCHAR2 DEFAULT NULL,
        p_linha_digitavel   IN VARCHAR2 DEFAULT NULL,
        p_valor_boleto      IN NUMBER DEFAULT NULL,
        p_pix_copia_cola    IN CLOB DEFAULT NULL,
        p_msg_erro          OUT VARCHAR2
    );

    -- Cancela boleto
    PROCEDURE cancelar_boleto(
        p_parcela_id IN NUMBER,
        p_motivo     IN VARCHAR2 DEFAULT NULL,
        p_msg_erro   OUT VARCHAR2
    );

    -- Registra pagamento via boleto
    PROCEDURE registrar_pagamento_boleto(
        p_parcela_id       IN NUMBER,
        p_valor_pago       IN NUMBER,
        p_data_pagamento   IN DATE DEFAULT NULL,
        p_banco_pagador    IN VARCHAR2 DEFAULT NULL,
        p_agencia_pagadora IN VARCHAR2 DEFAULT NULL,
        p_msg_erro         OUT VARCHAR2
    );

    -- ========================================================================
    -- PROCEDURES DE ARQUIVOS CNAB
    -- ========================================================================

    -- Cria um novo arquivo de remessa
    PROCEDURE criar_arquivo_remessa(
        p_conta_bancaria_id IN NUMBER,
        p_layout            IN VARCHAR2 DEFAULT 'CNAB_240',
        p_arquivo_id        OUT NUMBER,
        p_numero_remessa    OUT NUMBER,
        p_msg_erro          OUT VARCHAR2
    );

    -- Adiciona parcela ao arquivo de remessa
    PROCEDURE adicionar_item_remessa(
        p_arquivo_remessa_id IN NUMBER,
        p_parcela_id         IN NUMBER,
        p_msg_erro           OUT VARCHAR2
    );

    -- Finaliza e calcula totais do arquivo de remessa
    PROCEDURE finalizar_remessa(
        p_arquivo_remessa_id IN NUMBER,
        p_msg_erro           OUT VARCHAR2
    );

    -- Marca remessa como enviada
    PROCEDURE marcar_remessa_enviada(
        p_arquivo_remessa_id IN NUMBER,
        p_msg_erro           OUT VARCHAR2
    );

    -- Processa item de retorno
    PROCEDURE processar_item_retorno(
        p_item_retorno_id IN NUMBER,
        p_msg_erro        OUT VARCHAR2
    );

    -- ========================================================================
    -- FUNCOES AUXILIARES
    -- ========================================================================

    -- Verifica se parcela pode ter boleto gerado
    FUNCTION pode_gerar_boleto(
        p_parcela_id IN NUMBER
    ) RETURN BOOLEAN;

    -- Verifica se boleto pode ser pago
    FUNCTION boleto_pode_ser_pago(
        p_parcela_id IN NUMBER
    ) RETURN BOOLEAN;

    -- Retorna estatisticas de boletos de um contrato
    PROCEDURE obter_estatisticas_boletos(
        p_contrato_id       IN NUMBER,
        p_total_boletos     OUT NUMBER,
        p_boletos_pagos     OUT NUMBER,
        p_boletos_vencidos  OUT NUMBER,
        p_boletos_pendentes OUT NUMBER,
        p_valor_total       OUT NUMBER,
        p_valor_pago        OUT NUMBER
    );

END pkg_boleto;
/

CREATE OR REPLACE PACKAGE BODY pkg_boleto AS

    -- ========================================================================
    -- GERAR NUMERO DOCUMENTO
    -- ========================================================================
    FUNCTION gerar_numero_documento(
        p_parcela_id IN NUMBER
    ) RETURN VARCHAR2 IS
        v_numero_contrato VARCHAR2(50);
        v_numero_parcela  NUMBER;
    BEGIN
        SELECT c.numero_contrato, p.numero_parcela
        INTO v_numero_contrato, v_numero_parcela
        FROM gc_parcela p
        JOIN gc_contrato c ON c.id = p.contrato_id
        WHERE p.id = p_parcela_id;

        RETURN v_numero_contrato || '-' || LPAD(v_numero_parcela, 3, '0');
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN NULL;
    END gerar_numero_documento;

    -- ========================================================================
    -- OBTER PROXIMO NOSSO NUMERO
    -- ========================================================================
    FUNCTION obter_proximo_nosso_numero(
        p_conta_bancaria_id IN NUMBER
    ) RETURN VARCHAR2 IS
        v_nosso_numero NUMBER;
        v_banco        VARCHAR2(3);
        v_convenio     VARCHAR2(20);
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        -- Incrementar e retornar novo nosso numero
        UPDATE gc_conta_bancaria
        SET nosso_numero_atual = nosso_numero_atual + 1
        WHERE id = p_conta_bancaria_id
        RETURNING nosso_numero_atual, banco, convenio
        INTO v_nosso_numero, v_banco, v_convenio;

        COMMIT;

        -- Formatar de acordo com o banco
        CASE v_banco
            WHEN '001' THEN -- Banco do Brasil
                RETURN LPAD(v_convenio, 7, '0') || LPAD(v_nosso_numero, 10, '0');
            WHEN '104' THEN -- Caixa
                RETURN LPAD(v_nosso_numero, 15, '0');
            WHEN '237' THEN -- Bradesco
                RETURN LPAD(v_nosso_numero, 11, '0');
            WHEN '341' THEN -- Itau
                RETURN LPAD(v_nosso_numero, 8, '0');
            WHEN '033' THEN -- Santander
                RETURN LPAD(v_nosso_numero, 13, '0');
            WHEN '756' THEN -- Sicoob
                RETURN LPAD(v_nosso_numero, 10, '0');
            ELSE
                RETURN LPAD(v_nosso_numero, 15, '0');
        END CASE;
    EXCEPTION
        WHEN OTHERS THEN
            RETURN NULL;
    END obter_proximo_nosso_numero;

    -- ========================================================================
    -- PREPARAR BOLETO
    -- ========================================================================
    PROCEDURE preparar_boleto(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER DEFAULT NULL,
        p_forcar            IN BOOLEAN DEFAULT FALSE,
        p_nosso_numero      OUT VARCHAR2,
        p_num_documento     OUT VARCHAR2,
        p_valor_boleto      OUT NUMBER,
        p_data_vencimento   OUT DATE,
        p_dados_sacado      OUT VARCHAR2,
        p_dados_beneficiario OUT VARCHAR2,
        p_msg_erro          OUT VARCHAR2
    ) IS
        v_parcela       gc_parcela%ROWTYPE;
        v_contrato      gc_contrato%ROWTYPE;
        v_comprador     gc_comprador%ROWTYPE;
        v_imobiliaria   gc_imobiliaria%ROWTYPE;
        v_conta_id      NUMBER;
    BEGIN
        p_msg_erro := NULL;

        -- Buscar parcela
        SELECT * INTO v_parcela
        FROM gc_parcela WHERE id = p_parcela_id;

        -- Verificar se ja tem boleto e nao eh para forcar
        IF v_parcela.nosso_numero IS NOT NULL AND NOT p_forcar THEN
            p_nosso_numero := v_parcela.nosso_numero;
            p_num_documento := v_parcela.numero_documento;
            p_valor_boleto := v_parcela.valor_boleto;
            p_data_vencimento := v_parcela.data_vencimento;
            RETURN;
        END IF;

        -- Verificar se parcela esta paga
        IF v_parcela.pago = 1 THEN
            p_msg_erro := 'Parcela ja esta paga';
            RETURN;
        END IF;

        -- Buscar contrato
        SELECT * INTO v_contrato
        FROM gc_contrato WHERE id = v_parcela.contrato_id;

        -- Determinar conta bancaria
        IF p_conta_bancaria_id IS NOT NULL THEN
            v_conta_id := p_conta_bancaria_id;
        ELSIF v_contrato.conta_bancaria_padrao_id IS NOT NULL THEN
            v_conta_id := v_contrato.conta_bancaria_padrao_id;
        ELSE
            -- Buscar conta principal da imobiliaria
            SELECT id INTO v_conta_id
            FROM gc_conta_bancaria
            WHERE imobiliaria_id = v_contrato.imobiliaria_id
              AND principal = 1
              AND ativo = 1
            FETCH FIRST 1 ROW ONLY;
        END IF;

        IF v_conta_id IS NULL THEN
            p_msg_erro := 'Nenhuma conta bancaria disponivel';
            RETURN;
        END IF;

        -- Buscar comprador
        SELECT * INTO v_comprador
        FROM gc_comprador WHERE id = v_contrato.comprador_id;

        -- Buscar imobiliaria
        SELECT * INTO v_imobiliaria
        FROM gc_imobiliaria WHERE id = v_contrato.imobiliaria_id;

        -- Gerar dados
        p_nosso_numero := obter_proximo_nosso_numero(v_conta_id);
        p_num_documento := gerar_numero_documento(p_parcela_id);
        p_valor_boleto := v_parcela.valor_atual;
        p_data_vencimento := v_parcela.data_vencimento;

        -- Dados do sacado (comprador)
        p_dados_sacado := v_comprador.nome || '|' ||
                         COALESCE(v_comprador.cpf, v_comprador.cnpj) || '|' ||
                         v_comprador.logradouro || ', ' || v_comprador.numero || '|' ||
                         v_comprador.bairro || '|' ||
                         v_comprador.cidade || '|' ||
                         v_comprador.estado || '|' ||
                         v_comprador.cep;

        -- Dados do beneficiario (imobiliaria)
        p_dados_beneficiario := v_imobiliaria.razao_social || '|' ||
                               v_imobiliaria.cnpj || '|' ||
                               v_imobiliaria.logradouro || ', ' || v_imobiliaria.numero || '|' ||
                               v_imobiliaria.bairro || '|' ||
                               v_imobiliaria.cidade || '|' ||
                               v_imobiliaria.estado || '|' ||
                               v_imobiliaria.cep;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Dados nao encontrados para gerar boleto';
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao preparar boleto: ' || SQLERRM;
    END preparar_boleto;

    -- ========================================================================
    -- REGISTRAR BOLETO GERADO
    -- ========================================================================
    PROCEDURE registrar_boleto_gerado(
        p_parcela_id        IN NUMBER,
        p_conta_bancaria_id IN NUMBER,
        p_nosso_numero      IN VARCHAR2,
        p_codigo_barras     IN VARCHAR2 DEFAULT NULL,
        p_linha_digitavel   IN VARCHAR2 DEFAULT NULL,
        p_valor_boleto      IN NUMBER DEFAULT NULL,
        p_pix_copia_cola    IN CLOB DEFAULT NULL,
        p_msg_erro          OUT VARCHAR2
    ) IS
    BEGIN
        p_msg_erro := NULL;

        UPDATE gc_parcela
        SET conta_bancaria_id = p_conta_bancaria_id,
            nosso_numero = p_nosso_numero,
            numero_documento = gerar_numero_documento(p_parcela_id),
            codigo_barras = p_codigo_barras,
            linha_digitavel = p_linha_digitavel,
            valor_boleto = NVL(p_valor_boleto, valor_atual),
            status_boleto = c_status_gerado,
            data_geracao_boleto = SYSTIMESTAMP,
            pix_copia_cola = p_pix_copia_cola
        WHERE id = p_parcela_id;

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao registrar boleto: ' || SQLERRM;
            ROLLBACK;
    END registrar_boleto_gerado;

    -- ========================================================================
    -- CANCELAR BOLETO
    -- ========================================================================
    PROCEDURE cancelar_boleto(
        p_parcela_id IN NUMBER,
        p_motivo     IN VARCHAR2 DEFAULT NULL,
        p_msg_erro   OUT VARCHAR2
    ) IS
        v_status VARCHAR2(15);
    BEGIN
        p_msg_erro := NULL;

        SELECT status_boleto INTO v_status
        FROM gc_parcela WHERE id = p_parcela_id;

        IF v_status IN (c_status_nao_gerado, c_status_cancelado, c_status_pago) THEN
            p_msg_erro := 'Boleto nao pode ser cancelado. Status atual: ' || v_status;
            RETURN;
        END IF;

        UPDATE gc_parcela
        SET status_boleto = c_status_cancelado,
            motivo_rejeicao = p_motivo
        WHERE id = p_parcela_id;

        COMMIT;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Parcela nao encontrada';
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao cancelar boleto: ' || SQLERRM;
            ROLLBACK;
    END cancelar_boleto;

    -- ========================================================================
    -- REGISTRAR PAGAMENTO BOLETO
    -- ========================================================================
    PROCEDURE registrar_pagamento_boleto(
        p_parcela_id       IN NUMBER,
        p_valor_pago       IN NUMBER,
        p_data_pagamento   IN DATE DEFAULT NULL,
        p_banco_pagador    IN VARCHAR2 DEFAULT NULL,
        p_agencia_pagadora IN VARCHAR2 DEFAULT NULL,
        p_msg_erro         OUT VARCHAR2
    ) IS
        v_data_pag DATE;
    BEGIN
        p_msg_erro := NULL;
        v_data_pag := NVL(p_data_pagamento, SYSDATE);

        -- Atualizar dados do boleto
        UPDATE gc_parcela
        SET status_boleto = c_status_pago,
            data_pagamento_boleto = v_data_pag,
            valor_pago_boleto = p_valor_pago,
            banco_pagador = p_banco_pagador,
            agencia_pagadora = p_agencia_pagadora
        WHERE id = p_parcela_id;

        -- Registrar pagamento na parcela
        pkg_contrato.registrar_pagamento(
            p_parcela_id      => p_parcela_id,
            p_valor_pago      => p_valor_pago,
            p_data_pagamento  => v_data_pag,
            p_forma_pagamento => 'BOLETO',
            p_observacoes     => 'Pago via boleto. Banco: ' || p_banco_pagador ||
                                ' Ag: ' || p_agencia_pagadora,
            p_msg_erro        => p_msg_erro
        );

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao registrar pagamento boleto: ' || SQLERRM;
            ROLLBACK;
    END registrar_pagamento_boleto;

    -- ========================================================================
    -- CRIAR ARQUIVO REMESSA
    -- ========================================================================
    PROCEDURE criar_arquivo_remessa(
        p_conta_bancaria_id IN NUMBER,
        p_layout            IN VARCHAR2 DEFAULT 'CNAB_240',
        p_arquivo_id        OUT NUMBER,
        p_numero_remessa    OUT NUMBER,
        p_msg_erro          OUT VARCHAR2
    ) IS
        v_nome_arquivo VARCHAR2(100);
    BEGIN
        p_msg_erro := NULL;

        -- Obter proximo numero de remessa
        UPDATE gc_conta_bancaria
        SET numero_remessa_cnab_atual = numero_remessa_cnab_atual + 1
        WHERE id = p_conta_bancaria_id
        RETURNING numero_remessa_cnab_atual INTO p_numero_remessa;

        -- Nome do arquivo
        v_nome_arquivo := 'REM' || TO_CHAR(SYSDATE, 'YYYYMMDD') ||
                         '_' || LPAD(p_numero_remessa, 6, '0') || '.txt';

        -- Criar registro
        INSERT INTO gc_arquivo_remessa (
            conta_bancaria_id,
            numero_remessa,
            layout,
            arquivo_nome,
            status
        ) VALUES (
            p_conta_bancaria_id,
            p_numero_remessa,
            p_layout,
            v_nome_arquivo,
            'GERADO'
        ) RETURNING id INTO p_arquivo_id;

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao criar arquivo remessa: ' || SQLERRM;
            ROLLBACK;
    END criar_arquivo_remessa;

    -- ========================================================================
    -- ADICIONAR ITEM REMESSA
    -- ========================================================================
    PROCEDURE adicionar_item_remessa(
        p_arquivo_remessa_id IN NUMBER,
        p_parcela_id         IN NUMBER,
        p_msg_erro           OUT VARCHAR2
    ) IS
        v_parcela gc_parcela%ROWTYPE;
    BEGIN
        p_msg_erro := NULL;

        SELECT * INTO v_parcela
        FROM gc_parcela WHERE id = p_parcela_id;

        IF v_parcela.nosso_numero IS NULL THEN
            p_msg_erro := 'Parcela nao possui boleto gerado';
            RETURN;
        END IF;

        INSERT INTO gc_item_remessa (
            arquivo_remessa_id,
            parcela_id,
            nosso_numero,
            valor,
            data_vencimento
        ) VALUES (
            p_arquivo_remessa_id,
            p_parcela_id,
            v_parcela.nosso_numero,
            v_parcela.valor_boleto,
            v_parcela.data_vencimento
        );

        -- Marcar boleto como registrado
        UPDATE gc_parcela
        SET status_boleto = c_status_registrado,
            data_registro_boleto = SYSTIMESTAMP
        WHERE id = p_parcela_id;

        COMMIT;

    EXCEPTION
        WHEN DUP_VAL_ON_INDEX THEN
            p_msg_erro := 'Parcela ja esta incluida nesta remessa';
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Parcela nao encontrada';
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao adicionar item remessa: ' || SQLERRM;
            ROLLBACK;
    END adicionar_item_remessa;

    -- ========================================================================
    -- FINALIZAR REMESSA
    -- ========================================================================
    PROCEDURE finalizar_remessa(
        p_arquivo_remessa_id IN NUMBER,
        p_msg_erro           OUT VARCHAR2
    ) IS
        v_qtd   NUMBER;
        v_total NUMBER;
    BEGIN
        p_msg_erro := NULL;

        SELECT COUNT(*), NVL(SUM(valor), 0)
        INTO v_qtd, v_total
        FROM gc_item_remessa
        WHERE arquivo_remessa_id = p_arquivo_remessa_id;

        UPDATE gc_arquivo_remessa
        SET quantidade_boletos = v_qtd,
            valor_total = v_total
        WHERE id = p_arquivo_remessa_id;

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao finalizar remessa: ' || SQLERRM;
            ROLLBACK;
    END finalizar_remessa;

    -- ========================================================================
    -- MARCAR REMESSA ENVIADA
    -- ========================================================================
    PROCEDURE marcar_remessa_enviada(
        p_arquivo_remessa_id IN NUMBER,
        p_msg_erro           OUT VARCHAR2
    ) IS
    BEGIN
        p_msg_erro := NULL;

        UPDATE gc_arquivo_remessa
        SET status = 'ENVIADO',
            data_envio = SYSTIMESTAMP
        WHERE id = p_arquivo_remessa_id;

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao marcar remessa enviada: ' || SQLERRM;
            ROLLBACK;
    END marcar_remessa_enviada;

    -- ========================================================================
    -- PROCESSAR ITEM RETORNO
    -- ========================================================================
    PROCEDURE processar_item_retorno(
        p_item_retorno_id IN NUMBER,
        p_msg_erro        OUT VARCHAR2
    ) IS
        v_item gc_item_retorno%ROWTYPE;
    BEGIN
        p_msg_erro := NULL;

        SELECT * INTO v_item
        FROM gc_item_retorno WHERE id = p_item_retorno_id
        FOR UPDATE;

        IF v_item.processado = 1 THEN
            p_msg_erro := 'Item ja foi processado';
            RETURN;
        END IF;

        IF v_item.parcela_id IS NULL THEN
            p_msg_erro := 'Parcela nao identificada';
            UPDATE gc_item_retorno
            SET erro_processamento = p_msg_erro
            WHERE id = p_item_retorno_id;
            COMMIT;
            RETURN;
        END IF;

        -- Processar de acordo com o tipo de ocorrencia
        CASE v_item.tipo_ocorrencia
            WHEN 'LIQUIDACAO' THEN
                registrar_pagamento_boleto(
                    p_parcela_id     => v_item.parcela_id,
                    p_valor_pago     => NVL(v_item.valor_pago, v_item.valor_titulo),
                    p_data_pagamento => v_item.data_ocorrencia,
                    p_msg_erro       => p_msg_erro
                );

            WHEN 'ENTRADA' THEN
                UPDATE gc_parcela
                SET status_boleto = c_status_registrado,
                    data_registro_boleto = SYSTIMESTAMP
                WHERE id = v_item.parcela_id;

            WHEN 'BAIXA' THEN
                UPDATE gc_parcela
                SET status_boleto = c_status_baixado,
                    motivo_rejeicao = v_item.descricao_ocorrencia
                WHERE id = v_item.parcela_id;

            WHEN 'REJEICAO' THEN
                UPDATE gc_parcela
                SET status_boleto = c_status_cancelado,
                    motivo_rejeicao = v_item.descricao_ocorrencia
                WHERE id = v_item.parcela_id;

            WHEN 'PROTESTO' THEN
                UPDATE gc_parcela
                SET status_boleto = c_status_protestado
                WHERE id = v_item.parcela_id;

            ELSE
                NULL; -- Outros tipos
        END CASE;

        IF p_msg_erro IS NULL THEN
            UPDATE gc_item_retorno
            SET processado = 1
            WHERE id = p_item_retorno_id;
        ELSE
            UPDATE gc_item_retorno
            SET erro_processamento = p_msg_erro
            WHERE id = p_item_retorno_id;
        END IF;

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao processar item retorno: ' || SQLERRM;
            ROLLBACK;
    END processar_item_retorno;

    -- ========================================================================
    -- PODE GERAR BOLETO
    -- ========================================================================
    FUNCTION pode_gerar_boleto(
        p_parcela_id IN NUMBER
    ) RETURN BOOLEAN IS
        v_pago NUMBER;
    BEGIN
        SELECT pago INTO v_pago
        FROM gc_parcela WHERE id = p_parcela_id;

        RETURN v_pago = 0;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN FALSE;
    END pode_gerar_boleto;

    -- ========================================================================
    -- BOLETO PODE SER PAGO
    -- ========================================================================
    FUNCTION boleto_pode_ser_pago(
        p_parcela_id IN NUMBER
    ) RETURN BOOLEAN IS
        v_status VARCHAR2(15);
    BEGIN
        SELECT status_boleto INTO v_status
        FROM gc_parcela WHERE id = p_parcela_id;

        RETURN v_status IN (c_status_gerado, c_status_registrado, c_status_vencido);
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN FALSE;
    END boleto_pode_ser_pago;

    -- ========================================================================
    -- OBTER ESTATISTICAS BOLETOS
    -- ========================================================================
    PROCEDURE obter_estatisticas_boletos(
        p_contrato_id       IN NUMBER,
        p_total_boletos     OUT NUMBER,
        p_boletos_pagos     OUT NUMBER,
        p_boletos_vencidos  OUT NUMBER,
        p_boletos_pendentes OUT NUMBER,
        p_valor_total       OUT NUMBER,
        p_valor_pago        OUT NUMBER
    ) IS
    BEGIN
        SELECT
            COUNT(*),
            SUM(CASE WHEN status_boleto = 'PAGO' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status_boleto = 'VENCIDO' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status_boleto IN ('GERADO', 'REGISTRADO') THEN 1 ELSE 0 END),
            NVL(SUM(valor_boleto), 0),
            NVL(SUM(CASE WHEN status_boleto = 'PAGO' THEN valor_pago_boleto ELSE 0 END), 0)
        INTO
            p_total_boletos,
            p_boletos_pagos,
            p_boletos_vencidos,
            p_boletos_pendentes,
            p_valor_total,
            p_valor_pago
        FROM gc_parcela
        WHERE contrato_id = p_contrato_id
          AND status_boleto != 'NAO_GERADO';
    END obter_estatisticas_boletos;

END pkg_boleto;
/

-- Verificar compilacao
SELECT object_name, status
FROM user_objects
WHERE object_name = 'PKG_BOLETO';

SHOW ERRORS PACKAGE BODY pkg_boleto;
