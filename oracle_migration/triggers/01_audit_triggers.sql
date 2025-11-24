/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Script de Triggers - Auditoria e Auto-Atualizacao
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
==============================================================================
*/

-- ============================================================================
-- TRIGGERS DE ATUALIZACAO AUTOMATICA (similar ao auto_now do Django)
-- ============================================================================

-- Contabilidade
CREATE OR REPLACE TRIGGER trg_contab_update
    BEFORE UPDATE ON gc_contabilidade
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Imobiliaria
CREATE OR REPLACE TRIGGER trg_imob_update
    BEFORE UPDATE ON gc_imobiliaria
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Conta Bancaria
CREATE OR REPLACE TRIGGER trg_conta_update
    BEFORE UPDATE ON gc_conta_bancaria
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Imovel
CREATE OR REPLACE TRIGGER trg_imovel_update
    BEFORE UPDATE ON gc_imovel
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Comprador
CREATE OR REPLACE TRIGGER trg_comprador_update
    BEFORE UPDATE ON gc_comprador
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Indice Reajuste
CREATE OR REPLACE TRIGGER trg_indice_update
    BEFORE UPDATE ON gc_indice_reajuste
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Contrato
CREATE OR REPLACE TRIGGER trg_contrato_update
    BEFORE UPDATE ON gc_contrato
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Parcela
CREATE OR REPLACE TRIGGER trg_parcela_update
    BEFORE UPDATE ON gc_parcela
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Reajuste
CREATE OR REPLACE TRIGGER trg_reajuste_update
    BEFORE UPDATE ON gc_reajuste
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Historico Pagamento
CREATE OR REPLACE TRIGGER trg_hist_pag_update
    BEFORE UPDATE ON gc_historico_pagamento
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Arquivo Remessa
CREATE OR REPLACE TRIGGER trg_remessa_update
    BEFORE UPDATE ON gc_arquivo_remessa
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Item Remessa
CREATE OR REPLACE TRIGGER trg_item_rem_update
    BEFORE UPDATE ON gc_item_remessa
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Arquivo Retorno
CREATE OR REPLACE TRIGGER trg_retorno_update
    BEFORE UPDATE ON gc_arquivo_retorno
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Item Retorno
CREATE OR REPLACE TRIGGER trg_item_ret_update
    BEFORE UPDATE ON gc_item_retorno
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Config Email
CREATE OR REPLACE TRIGGER trg_cfg_email_update
    BEFORE UPDATE ON gc_config_email
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Config SMS
CREATE OR REPLACE TRIGGER trg_cfg_sms_update
    BEFORE UPDATE ON gc_config_sms
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Config WhatsApp
CREATE OR REPLACE TRIGGER trg_cfg_whats_update
    BEFORE UPDATE ON gc_config_whatsapp
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Notificacao
CREATE OR REPLACE TRIGGER trg_notif_update
    BEFORE UPDATE ON gc_notificacao
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Template Notificacao
CREATE OR REPLACE TRIGGER trg_template_update
    BEFORE UPDATE ON gc_template_notificacao
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- Acesso Usuario
CREATE OR REPLACE TRIGGER trg_acesso_update
    BEFORE UPDATE ON gc_acesso_usuario
    FOR EACH ROW
BEGIN
    :NEW.atualizado_em := SYSTIMESTAMP;
END;
/

-- ============================================================================
-- TRIGGER: Garantir apenas uma conta bancaria principal por imobiliaria
-- ============================================================================
CREATE OR REPLACE TRIGGER trg_conta_principal
    BEFORE INSERT OR UPDATE OF principal ON gc_conta_bancaria
    FOR EACH ROW
    WHEN (NEW.principal = 1)
BEGIN
    -- Desmarcar outras contas como principal
    UPDATE gc_conta_bancaria
    SET principal = 0
    WHERE imobiliaria_id = :NEW.imobiliaria_id
      AND id != NVL(:NEW.id, -1)
      AND principal = 1;
END;
/

-- ============================================================================
-- TRIGGER: Calcular valor financiado e parcela original no contrato
-- ============================================================================
CREATE OR REPLACE TRIGGER trg_contrato_calcular
    BEFORE INSERT OR UPDATE ON gc_contrato
    FOR EACH ROW
BEGIN
    -- Calcular valor financiado
    :NEW.valor_financiado := :NEW.valor_total - NVL(:NEW.valor_entrada, 0);

    -- Calcular valor da parcela original
    IF :NEW.numero_parcelas > 0 THEN
        :NEW.valor_parcela_original := ROUND(:NEW.valor_financiado / :NEW.numero_parcelas, 2);
    END IF;
END;
/

-- ============================================================================
-- TRIGGER: Atualizar status do boleto para VENCIDO automaticamente
-- ============================================================================
CREATE OR REPLACE TRIGGER trg_parcela_status_boleto
    BEFORE UPDATE ON gc_parcela
    FOR EACH ROW
BEGIN
    -- Se a parcela nao esta paga e ja venceu, marcar boleto como vencido
    IF :NEW.pago = 0
       AND :NEW.data_vencimento < TRUNC(SYSDATE)
       AND :NEW.status_boleto IN ('GERADO', 'REGISTRADO') THEN
        :NEW.status_boleto := 'VENCIDO';
    END IF;
END;
/

-- ============================================================================
-- TRIGGER: Marcar imovel como nao disponivel quando vinculado a contrato ativo
-- ============================================================================
CREATE OR REPLACE TRIGGER trg_contrato_imovel_disp
    AFTER INSERT OR UPDATE OF status ON gc_contrato
    FOR EACH ROW
BEGIN
    IF :NEW.status = 'ATIVO' THEN
        UPDATE gc_imovel
        SET disponivel = 0
        WHERE id = :NEW.imovel_id;
    ELSIF :NEW.status IN ('CANCELADO', 'QUITADO') AND :OLD.status = 'ATIVO' THEN
        -- Verificar se nao ha outros contratos ativos para o mesmo imovel
        DECLARE
            v_count NUMBER;
        BEGIN
            SELECT COUNT(*) INTO v_count
            FROM gc_contrato
            WHERE imovel_id = :NEW.imovel_id
              AND status = 'ATIVO'
              AND id != :NEW.id;

            IF v_count = 0 THEN
                UPDATE gc_imovel
                SET disponivel = 1
                WHERE id = :NEW.imovel_id;
            END IF;
        END;
    END IF;
END;
/

COMMIT;
