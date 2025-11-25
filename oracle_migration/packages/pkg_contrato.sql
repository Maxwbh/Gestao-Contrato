/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Package: PKG_CONTRATO - Logica de Negocios de Contratos
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
==============================================================================
*/

CREATE OR REPLACE PACKAGE pkg_contrato AS
    /*
    Package para gerenciamento de contratos de venda de imoveis.
    Inclui funcoes para:
    - Geracao de parcelas
    - Calculo de juros e multa
    - Aplicacao de reajustes
    - Registro de pagamentos
    */

    -- Tipos
    TYPE t_parcela_rec IS RECORD (
        numero_parcela   NUMBER,
        data_vencimento  DATE,
        valor_original   NUMBER,
        valor_atual      NUMBER
    );

    TYPE t_parcela_tab IS TABLE OF t_parcela_rec;

    -- Constantes
    c_status_ativo     CONSTANT VARCHAR2(20) := 'ATIVO';
    c_status_quitado   CONSTANT VARCHAR2(20) := 'QUITADO';
    c_status_cancelado CONSTANT VARCHAR2(20) := 'CANCELADO';

    -- ========================================================================
    -- PROCEDURES DE CONTRATOS
    -- ========================================================================

    -- Gera todas as parcelas de um contrato
    PROCEDURE gerar_parcelas(
        p_contrato_id    IN NUMBER,
        p_gerar_boletos  IN BOOLEAN DEFAULT FALSE,
        p_conta_bancaria IN NUMBER DEFAULT NULL,
        p_msg_erro       OUT VARCHAR2
    );

    -- Calcula o progresso de pagamento do contrato (%)
    FUNCTION calcular_progresso(
        p_contrato_id IN NUMBER
    ) RETURN NUMBER;

    -- Calcula o valor total pago do contrato
    FUNCTION calcular_valor_pago(
        p_contrato_id IN NUMBER
    ) RETURN NUMBER;

    -- Calcula o saldo devedor do contrato
    FUNCTION calcular_saldo_devedor(
        p_contrato_id IN NUMBER
    ) RETURN NUMBER;

    -- Verifica se o contrato precisa de reajuste
    FUNCTION verificar_reajuste_necessario(
        p_contrato_id IN NUMBER
    ) RETURN BOOLEAN;

    -- Retorna a data do proximo reajuste
    FUNCTION obter_data_proximo_reajuste(
        p_contrato_id IN NUMBER
    ) RETURN DATE;

    -- ========================================================================
    -- PROCEDURES DE PARCELAS
    -- ========================================================================

    -- Calcula juros e multa de uma parcela
    PROCEDURE calcular_juros_multa(
        p_parcela_id     IN NUMBER,
        p_data_ref       IN DATE DEFAULT SYSDATE,
        p_valor_juros    OUT NUMBER,
        p_valor_multa    OUT NUMBER
    );

    -- Atualiza juros e multa de uma parcela
    PROCEDURE atualizar_juros_multa(
        p_parcela_id IN NUMBER
    );

    -- Registra pagamento de uma parcela
    PROCEDURE registrar_pagamento(
        p_parcela_id      IN NUMBER,
        p_valor_pago      IN NUMBER,
        p_data_pagamento  IN DATE DEFAULT SYSDATE,
        p_forma_pagamento IN VARCHAR2 DEFAULT 'DINHEIRO',
        p_observacoes     IN VARCHAR2 DEFAULT NULL,
        p_msg_erro        OUT VARCHAR2
    );

    -- Cancela pagamento de uma parcela
    PROCEDURE cancelar_pagamento(
        p_parcela_id IN NUMBER,
        p_msg_erro   OUT VARCHAR2
    );

    -- Retorna o valor total da parcela (atual + juros + multa - desconto)
    FUNCTION calcular_valor_total_parcela(
        p_parcela_id IN NUMBER
    ) RETURN NUMBER;

    -- Retorna os dias de atraso de uma parcela
    FUNCTION calcular_dias_atraso(
        p_parcela_id IN NUMBER
    ) RETURN NUMBER;

    -- ========================================================================
    -- PROCEDURES DE REAJUSTES
    -- ========================================================================

    -- Aplica reajuste em um contrato
    PROCEDURE aplicar_reajuste(
        p_contrato_id     IN NUMBER,
        p_indice_tipo     IN VARCHAR2,
        p_percentual      IN NUMBER,
        p_parcela_inicial IN NUMBER DEFAULT 1,
        p_parcela_final   IN NUMBER DEFAULT NULL,
        p_aplicado_manual IN BOOLEAN DEFAULT FALSE,
        p_observacoes     IN VARCHAR2 DEFAULT NULL,
        p_msg_erro        OUT VARCHAR2
    );

    -- Processa reajustes automaticos para todos os contratos
    PROCEDURE processar_reajustes_automaticos(
        p_data_referencia IN DATE DEFAULT SYSDATE,
        p_total_proc      OUT NUMBER,
        p_total_erro      OUT NUMBER
    );

    -- ========================================================================
    -- FUNCOES AUXILIARES
    -- ========================================================================

    -- Obtem o indice acumulado em um periodo
    FUNCTION obter_indice_acumulado(
        p_tipo_indice  IN VARCHAR2,
        p_ano_inicio   IN NUMBER,
        p_mes_inicio   IN NUMBER,
        p_ano_fim      IN NUMBER,
        p_mes_fim      IN NUMBER
    ) RETURN NUMBER;

END pkg_contrato;
/

CREATE OR REPLACE PACKAGE BODY pkg_contrato AS

    -- ========================================================================
    -- GERAR PARCELAS
    -- ========================================================================
    PROCEDURE gerar_parcelas(
        p_contrato_id    IN NUMBER,
        p_gerar_boletos  IN BOOLEAN DEFAULT FALSE,
        p_conta_bancaria IN NUMBER DEFAULT NULL,
        p_msg_erro       OUT VARCHAR2
    ) IS
        v_contrato        gc_contrato%ROWTYPE;
        v_data_vencimento DATE;
        v_valor_parcela   NUMBER(12,2);
        v_dia_venc        NUMBER;
        v_ultimo_dia      NUMBER;
        v_count           NUMBER;
    BEGIN
        p_msg_erro := NULL;

        -- Buscar dados do contrato
        SELECT * INTO v_contrato
        FROM gc_contrato
        WHERE id = p_contrato_id;

        -- Verificar se ja existem parcelas
        SELECT COUNT(*) INTO v_count
        FROM gc_parcela
        WHERE contrato_id = p_contrato_id;

        IF v_count > 0 THEN
            p_msg_erro := 'Contrato ja possui parcelas geradas';
            RETURN;
        END IF;

        -- Inicializar valores
        v_data_vencimento := v_contrato.data_primeiro_vencimento;
        v_valor_parcela := v_contrato.valor_parcela_original;

        -- Gerar cada parcela
        FOR i IN 1..v_contrato.numero_parcelas LOOP
            INSERT INTO gc_parcela (
                contrato_id,
                numero_parcela,
                data_vencimento,
                valor_original,
                valor_atual
            ) VALUES (
                p_contrato_id,
                i,
                v_data_vencimento,
                v_valor_parcela,
                v_valor_parcela
            );

            -- Calcular proximo vencimento
            v_data_vencimento := ADD_MONTHS(v_data_vencimento, 1);

            -- Ajustar dia de vencimento se necessario
            v_ultimo_dia := EXTRACT(DAY FROM LAST_DAY(v_data_vencimento));
            v_dia_venc := LEAST(v_contrato.dia_vencimento, v_ultimo_dia);

            v_data_vencimento := TRUNC(v_data_vencimento, 'MM') + v_dia_venc - 1;
        END LOOP;

        COMMIT;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Contrato nao encontrado: ' || p_contrato_id;
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao gerar parcelas: ' || SQLERRM;
            ROLLBACK;
    END gerar_parcelas;

    -- ========================================================================
    -- CALCULAR PROGRESSO
    -- ========================================================================
    FUNCTION calcular_progresso(
        p_contrato_id IN NUMBER
    ) RETURN NUMBER IS
        v_total_parcelas NUMBER;
        v_parcelas_pagas NUMBER;
    BEGIN
        SELECT COUNT(*),
               SUM(CASE WHEN pago = 1 THEN 1 ELSE 0 END)
        INTO v_total_parcelas, v_parcelas_pagas
        FROM gc_parcela
        WHERE contrato_id = p_contrato_id;

        IF v_total_parcelas = 0 THEN
            RETURN 0;
        END IF;

        RETURN ROUND((v_parcelas_pagas / v_total_parcelas) * 100, 2);
    END calcular_progresso;

    -- ========================================================================
    -- CALCULAR VALOR PAGO
    -- ========================================================================
    FUNCTION calcular_valor_pago(
        p_contrato_id IN NUMBER
    ) RETURN NUMBER IS
        v_valor_pago   NUMBER;
        v_valor_entrada NUMBER;
    BEGIN
        SELECT NVL(SUM(valor_pago), 0)
        INTO v_valor_pago
        FROM gc_parcela
        WHERE contrato_id = p_contrato_id
          AND pago = 1;

        SELECT NVL(valor_entrada, 0)
        INTO v_valor_entrada
        FROM gc_contrato
        WHERE id = p_contrato_id;

        RETURN v_valor_pago + v_valor_entrada;
    END calcular_valor_pago;

    -- ========================================================================
    -- CALCULAR SALDO DEVEDOR
    -- ========================================================================
    FUNCTION calcular_saldo_devedor(
        p_contrato_id IN NUMBER
    ) RETURN NUMBER IS
        v_valor_financiado NUMBER;
        v_valor_pago       NUMBER;
    BEGIN
        SELECT NVL(valor_financiado, 0)
        INTO v_valor_financiado
        FROM gc_contrato
        WHERE id = p_contrato_id;

        SELECT NVL(SUM(valor_pago), 0)
        INTO v_valor_pago
        FROM gc_parcela
        WHERE contrato_id = p_contrato_id
          AND pago = 1;

        RETURN GREATEST(v_valor_financiado - v_valor_pago, 0);
    END calcular_saldo_devedor;

    -- ========================================================================
    -- VERIFICAR REAJUSTE NECESSARIO
    -- ========================================================================
    FUNCTION verificar_reajuste_necessario(
        p_contrato_id IN NUMBER
    ) RETURN BOOLEAN IS
        v_contrato         gc_contrato%ROWTYPE;
        v_meses_desde_base NUMBER;
        v_data_base        DATE;
    BEGIN
        SELECT * INTO v_contrato
        FROM gc_contrato
        WHERE id = p_contrato_id;

        -- Se tipo de correcao eh FIXO, nao precisa reajuste
        IF v_contrato.tipo_correcao = 'FIXO' THEN
            RETURN FALSE;
        END IF;

        -- Determinar data base para calculo
        IF v_contrato.data_ultimo_reajuste IS NOT NULL THEN
            v_data_base := v_contrato.data_ultimo_reajuste;
        ELSE
            v_data_base := v_contrato.data_contrato;
        END IF;

        -- Calcular meses desde a data base
        v_meses_desde_base := MONTHS_BETWEEN(TRUNC(SYSDATE), v_data_base);

        RETURN v_meses_desde_base >= v_contrato.prazo_reajuste_meses;
    END verificar_reajuste_necessario;

    -- ========================================================================
    -- OBTER DATA PROXIMO REAJUSTE
    -- ========================================================================
    FUNCTION obter_data_proximo_reajuste(
        p_contrato_id IN NUMBER
    ) RETURN DATE IS
        v_contrato  gc_contrato%ROWTYPE;
        v_data_base DATE;
    BEGIN
        SELECT * INTO v_contrato
        FROM gc_contrato
        WHERE id = p_contrato_id;

        IF v_contrato.tipo_correcao = 'FIXO' THEN
            RETURN NULL;
        END IF;

        IF v_contrato.data_ultimo_reajuste IS NOT NULL THEN
            v_data_base := v_contrato.data_ultimo_reajuste;
        ELSE
            v_data_base := v_contrato.data_contrato;
        END IF;

        RETURN ADD_MONTHS(v_data_base, v_contrato.prazo_reajuste_meses);
    END obter_data_proximo_reajuste;

    -- ========================================================================
    -- CALCULAR JUROS E MULTA
    -- ========================================================================
    PROCEDURE calcular_juros_multa(
        p_parcela_id     IN NUMBER,
        p_data_ref       IN DATE DEFAULT SYSDATE,
        p_valor_juros    OUT NUMBER,
        p_valor_multa    OUT NUMBER
    ) IS
        v_parcela       gc_parcela%ROWTYPE;
        v_contrato      gc_contrato%ROWTYPE;
        v_dias_atraso   NUMBER;
    BEGIN
        p_valor_juros := 0;
        p_valor_multa := 0;

        -- Buscar parcela
        SELECT * INTO v_parcela
        FROM gc_parcela
        WHERE id = p_parcela_id;

        -- Se ja esta paga, nao calcular
        IF v_parcela.pago = 1 THEN
            RETURN;
        END IF;

        -- Se nao esta vencida, nao calcular
        IF TRUNC(p_data_ref) <= v_parcela.data_vencimento THEN
            RETURN;
        END IF;

        -- Buscar contrato
        SELECT * INTO v_contrato
        FROM gc_contrato
        WHERE id = v_parcela.contrato_id;

        -- Calcular dias de atraso
        v_dias_atraso := TRUNC(p_data_ref) - v_parcela.data_vencimento;

        -- Calcular multa (aplicada uma vez)
        p_valor_multa := ROUND(v_parcela.valor_atual * (v_contrato.percentual_multa / 100), 2);

        -- Calcular juros (proporcional aos dias de atraso)
        -- Juros = valor * (taxa_mensal / 30) * dias_atraso
        p_valor_juros := ROUND(
            v_parcela.valor_atual *
            (v_contrato.percentual_juros_mora / 100) *
            (v_dias_atraso / 30),
            2
        );

    END calcular_juros_multa;

    -- ========================================================================
    -- ATUALIZAR JUROS E MULTA
    -- ========================================================================
    PROCEDURE atualizar_juros_multa(
        p_parcela_id IN NUMBER
    ) IS
        v_juros NUMBER;
        v_multa NUMBER;
    BEGIN
        calcular_juros_multa(p_parcela_id, SYSDATE, v_juros, v_multa);

        UPDATE gc_parcela
        SET valor_juros = v_juros,
            valor_multa = v_multa
        WHERE id = p_parcela_id
          AND pago = 0;

        COMMIT;
    END atualizar_juros_multa;

    -- ========================================================================
    -- REGISTRAR PAGAMENTO
    -- ========================================================================
    PROCEDURE registrar_pagamento(
        p_parcela_id      IN NUMBER,
        p_valor_pago      IN NUMBER,
        p_data_pagamento  IN DATE DEFAULT SYSDATE,
        p_forma_pagamento IN VARCHAR2 DEFAULT 'DINHEIRO',
        p_observacoes     IN VARCHAR2 DEFAULT NULL,
        p_msg_erro        OUT VARCHAR2
    ) IS
        v_parcela     gc_parcela%ROWTYPE;
        v_juros       NUMBER;
        v_multa       NUMBER;
    BEGIN
        p_msg_erro := NULL;

        -- Buscar parcela
        SELECT * INTO v_parcela
        FROM gc_parcela
        WHERE id = p_parcela_id
        FOR UPDATE;

        -- Verificar se ja esta paga
        IF v_parcela.pago = 1 THEN
            p_msg_erro := 'Parcela ja esta paga';
            RETURN;
        END IF;

        -- Calcular juros e multa se houver atraso
        IF p_data_pagamento > v_parcela.data_vencimento THEN
            calcular_juros_multa(p_parcela_id, p_data_pagamento, v_juros, v_multa);
        ELSE
            v_juros := 0;
            v_multa := 0;
        END IF;

        -- Atualizar parcela
        UPDATE gc_parcela
        SET pago = 1,
            data_pagamento = p_data_pagamento,
            valor_pago = p_valor_pago,
            valor_juros = v_juros,
            valor_multa = v_multa,
            observacoes = CASE
                WHEN p_observacoes IS NOT NULL THEN p_observacoes
                ELSE observacoes
            END
        WHERE id = p_parcela_id;

        -- Registrar no historico
        INSERT INTO gc_historico_pagamento (
            parcela_id,
            data_pagamento,
            valor_pago,
            valor_parcela,
            valor_juros,
            valor_multa,
            valor_desconto,
            forma_pagamento,
            observacoes
        ) VALUES (
            p_parcela_id,
            p_data_pagamento,
            p_valor_pago,
            v_parcela.valor_atual,
            v_juros,
            v_multa,
            v_parcela.valor_desconto,
            p_forma_pagamento,
            p_observacoes
        );

        -- Verificar se todas as parcelas foram pagas
        DECLARE
            v_parcelas_pendentes NUMBER;
        BEGIN
            SELECT COUNT(*)
            INTO v_parcelas_pendentes
            FROM gc_parcela
            WHERE contrato_id = v_parcela.contrato_id
              AND pago = 0;

            IF v_parcelas_pendentes = 0 THEN
                UPDATE gc_contrato
                SET status = 'QUITADO'
                WHERE id = v_parcela.contrato_id;
            END IF;
        END;

        COMMIT;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Parcela nao encontrada: ' || p_parcela_id;
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao registrar pagamento: ' || SQLERRM;
            ROLLBACK;
    END registrar_pagamento;

    -- ========================================================================
    -- CANCELAR PAGAMENTO
    -- ========================================================================
    PROCEDURE cancelar_pagamento(
        p_parcela_id IN NUMBER,
        p_msg_erro   OUT VARCHAR2
    ) IS
        v_contrato_id NUMBER;
    BEGIN
        p_msg_erro := NULL;

        -- Buscar contrato da parcela
        SELECT contrato_id INTO v_contrato_id
        FROM gc_parcela
        WHERE id = p_parcela_id;

        -- Atualizar parcela
        UPDATE gc_parcela
        SET pago = 0,
            data_pagamento = NULL,
            valor_pago = NULL,
            valor_juros = 0,
            valor_multa = 0
        WHERE id = p_parcela_id;

        -- Reverter status do contrato se necessario
        UPDATE gc_contrato
        SET status = 'ATIVO'
        WHERE id = v_contrato_id
          AND status = 'QUITADO';

        COMMIT;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_msg_erro := 'Parcela nao encontrada: ' || p_parcela_id;
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao cancelar pagamento: ' || SQLERRM;
            ROLLBACK;
    END cancelar_pagamento;

    -- ========================================================================
    -- CALCULAR VALOR TOTAL PARCELA
    -- ========================================================================
    FUNCTION calcular_valor_total_parcela(
        p_parcela_id IN NUMBER
    ) RETURN NUMBER IS
        v_total NUMBER;
    BEGIN
        SELECT valor_atual + NVL(valor_juros, 0) + NVL(valor_multa, 0) - NVL(valor_desconto, 0)
        INTO v_total
        FROM gc_parcela
        WHERE id = p_parcela_id;

        RETURN v_total;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN 0;
    END calcular_valor_total_parcela;

    -- ========================================================================
    -- CALCULAR DIAS ATRASO
    -- ========================================================================
    FUNCTION calcular_dias_atraso(
        p_parcela_id IN NUMBER
    ) RETURN NUMBER IS
        v_data_venc DATE;
        v_pago      NUMBER;
    BEGIN
        SELECT data_vencimento, pago
        INTO v_data_venc, v_pago
        FROM gc_parcela
        WHERE id = p_parcela_id;

        IF v_pago = 1 THEN
            RETURN 0;
        END IF;

        IF TRUNC(SYSDATE) <= v_data_venc THEN
            RETURN 0;
        END IF;

        RETURN TRUNC(SYSDATE) - v_data_venc;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN 0;
    END calcular_dias_atraso;

    -- ========================================================================
    -- APLICAR REAJUSTE
    -- ========================================================================
    PROCEDURE aplicar_reajuste(
        p_contrato_id     IN NUMBER,
        p_indice_tipo     IN VARCHAR2,
        p_percentual      IN NUMBER,
        p_parcela_inicial IN NUMBER DEFAULT 1,
        p_parcela_final   IN NUMBER DEFAULT NULL,
        p_aplicado_manual IN BOOLEAN DEFAULT FALSE,
        p_observacoes     IN VARCHAR2 DEFAULT NULL,
        p_msg_erro        OUT VARCHAR2
    ) IS
        v_parcela_final NUMBER;
        v_fator_reajuste NUMBER;
        v_reajuste_id   NUMBER;
    BEGIN
        p_msg_erro := NULL;

        -- Determinar parcela final
        IF p_parcela_final IS NULL THEN
            SELECT MAX(numero_parcela)
            INTO v_parcela_final
            FROM gc_parcela
            WHERE contrato_id = p_contrato_id;
        ELSE
            v_parcela_final := p_parcela_final;
        END IF;

        -- Calcular fator de reajuste
        v_fator_reajuste := 1 + (p_percentual / 100);

        -- Aplicar reajuste nas parcelas nao pagas
        UPDATE gc_parcela
        SET valor_atual = ROUND(valor_atual * v_fator_reajuste, 2)
        WHERE contrato_id = p_contrato_id
          AND numero_parcela BETWEEN p_parcela_inicial AND v_parcela_final
          AND pago = 0;

        -- Registrar o reajuste
        INSERT INTO gc_reajuste (
            contrato_id,
            data_reajuste,
            indice_tipo,
            percentual,
            parcela_inicial,
            parcela_final,
            aplicado_manual,
            observacoes
        ) VALUES (
            p_contrato_id,
            SYSDATE,
            p_indice_tipo,
            p_percentual,
            p_parcela_inicial,
            v_parcela_final,
            CASE WHEN p_aplicado_manual THEN 1 ELSE 0 END,
            p_observacoes
        );

        -- Atualizar data do ultimo reajuste no contrato
        UPDATE gc_contrato
        SET data_ultimo_reajuste = SYSDATE
        WHERE id = p_contrato_id;

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            p_msg_erro := 'Erro ao aplicar reajuste: ' || SQLERRM;
            ROLLBACK;
    END aplicar_reajuste;

    -- ========================================================================
    -- PROCESSAR REAJUSTES AUTOMATICOS
    -- ========================================================================
    PROCEDURE processar_reajustes_automaticos(
        p_data_referencia IN DATE DEFAULT SYSDATE,
        p_total_proc      OUT NUMBER,
        p_total_erro      OUT NUMBER
    ) IS
        v_msg_erro VARCHAR2(4000);
        v_percentual NUMBER;
        v_ano_ref NUMBER;
        v_mes_ref NUMBER;
    BEGIN
        p_total_proc := 0;
        p_total_erro := 0;

        v_ano_ref := EXTRACT(YEAR FROM p_data_referencia);
        v_mes_ref := EXTRACT(MONTH FROM p_data_referencia);

        -- Percorrer contratos que precisam de reajuste
        FOR r_contrato IN (
            SELECT c.*
            FROM gc_contrato c
            WHERE c.status = 'ATIVO'
              AND c.tipo_correcao != 'FIXO'
              AND (
                  c.data_ultimo_reajuste IS NULL
                  OR MONTHS_BETWEEN(TRUNC(p_data_referencia), c.data_ultimo_reajuste) >= c.prazo_reajuste_meses
              )
        ) LOOP
            -- Buscar indice do mes anterior
            BEGIN
                SELECT valor INTO v_percentual
                FROM gc_indice_reajuste
                WHERE tipo_indice = r_contrato.tipo_correcao
                  AND ano = v_ano_ref
                  AND mes = v_mes_ref - 1
                ORDER BY data_importacao DESC
                FETCH FIRST 1 ROW ONLY;
            EXCEPTION
                WHEN NO_DATA_FOUND THEN
                    v_percentual := NULL;
            END;

            IF v_percentual IS NOT NULL THEN
                aplicar_reajuste(
                    p_contrato_id     => r_contrato.id,
                    p_indice_tipo     => r_contrato.tipo_correcao,
                    p_percentual      => v_percentual,
                    p_aplicado_manual => FALSE,
                    p_observacoes     => 'Reajuste automatico - ' || r_contrato.tipo_correcao || ' ' ||
                                        TO_CHAR(v_mes_ref - 1, '00') || '/' || v_ano_ref,
                    p_msg_erro        => v_msg_erro
                );

                IF v_msg_erro IS NULL THEN
                    p_total_proc := p_total_proc + 1;
                ELSE
                    p_total_erro := p_total_erro + 1;
                END IF;
            END IF;
        END LOOP;

    END processar_reajustes_automaticos;

    -- ========================================================================
    -- OBTER INDICE ACUMULADO
    -- ========================================================================
    FUNCTION obter_indice_acumulado(
        p_tipo_indice  IN VARCHAR2,
        p_ano_inicio   IN NUMBER,
        p_mes_inicio   IN NUMBER,
        p_ano_fim      IN NUMBER,
        p_mes_fim      IN NUMBER
    ) RETURN NUMBER IS
        v_acumulado NUMBER := 1;
    BEGIN
        FOR r IN (
            SELECT valor
            FROM gc_indice_reajuste
            WHERE tipo_indice = p_tipo_indice
              AND (
                  (ano > p_ano_inicio OR (ano = p_ano_inicio AND mes >= p_mes_inicio))
                  AND (ano < p_ano_fim OR (ano = p_ano_fim AND mes <= p_mes_fim))
              )
            ORDER BY ano, mes
        ) LOOP
            v_acumulado := v_acumulado * (1 + r.valor / 100);
        END LOOP;

        RETURN ROUND((v_acumulado - 1) * 100, 4);
    END obter_indice_acumulado;

END pkg_contrato;
/

-- Verificar compilacao
SELECT object_name, status
FROM user_objects
WHERE object_name = 'PKG_CONTRATO';

SHOW ERRORS PACKAGE BODY pkg_contrato;
