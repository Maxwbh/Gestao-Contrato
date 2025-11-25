/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Script de Migracao de Dados - PostgreSQL para Oracle
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Linkedin: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================

INSTRUCOES:
Este script fornece os comandos para migrar dados do PostgreSQL para Oracle.
Existem 3 metodos sugeridos:

1. SQL*Loader - Para grandes volumes de dados
2. External Tables - Para acesso direto a arquivos CSV
3. Database Link + Insert - Para ambientes conectados

Prerequisitos:
- Exportar dados do PostgreSQL para CSV usando:
  psql -d gestao_contrato -c "\COPY tabela TO '/path/tabela.csv' WITH CSV HEADER"

==============================================================================
*/

-- ============================================================================
-- METODO 1: SQL*LOADER - Control Files
-- ============================================================================

/*
Exemplo de uso do SQL*Loader:
$ sqlldr userid=user/pass@db control=contabilidade.ctl log=contabilidade.log

Gere os arquivos CSV no PostgreSQL:
\COPY core_contabilidade TO '/tmp/contabilidade.csv' WITH CSV HEADER
\COPY core_imobiliaria TO '/tmp/imobiliaria.csv' WITH CSV HEADER
...etc
*/

-- ============================================================================
-- METODO 2: External Tables (Oracle 23c)
-- ============================================================================

-- Criar diretorio para arquivos CSV
-- CREATE OR REPLACE DIRECTORY migration_dir AS '/opt/oracle/migration_data';
-- GRANT READ, WRITE ON DIRECTORY migration_dir TO gestao_contrato;

-- Exemplo de External Table para Contabilidade
/*
CREATE TABLE ext_contabilidade (
    id                NUMBER,
    nome              VARCHAR2(200),
    razao_social      VARCHAR2(200),
    cnpj              VARCHAR2(20),
    endereco          VARCHAR2(4000),
    telefone          VARCHAR2(20),
    email             VARCHAR2(254),
    responsavel       VARCHAR2(200),
    ativo             NUMBER,
    criado_em         VARCHAR2(30),
    atualizado_em     VARCHAR2(30)
)
ORGANIZATION EXTERNAL (
    TYPE ORACLE_LOADER
    DEFAULT DIRECTORY migration_dir
    ACCESS PARAMETERS (
        RECORDS DELIMITED BY NEWLINE
        SKIP 1
        FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '"'
        MISSING FIELD VALUES ARE NULL
        (
            id, nome, razao_social, cnpj, endereco, telefone, email,
            responsavel, ativo, criado_em, atualizado_em
        )
    )
    LOCATION ('contabilidade.csv')
)
REJECT LIMIT UNLIMITED;
*/

-- ============================================================================
-- METODO 3: INSERT Statements (para pequenos volumes)
-- ============================================================================

-- Procedure para gerar INSERT a partir do PostgreSQL
-- Execute no PostgreSQL para gerar os INSERTs:

/*
-- PostgreSQL: Gerar INSERTs para Contabilidade
SELECT 'INSERT INTO gc_contabilidade (nome, razao_social, cnpj, endereco, telefone, email, responsavel, ativo) VALUES (' ||
       quote_literal(nome) || ', ' ||
       quote_literal(razao_social) || ', ' ||
       quote_nullable(cnpj) || ', ' ||
       quote_nullable(endereco) || ', ' ||
       quote_literal(telefone) || ', ' ||
       quote_literal(email) || ', ' ||
       quote_literal(responsavel) || ', ' ||
       CASE ativo WHEN true THEN '1' ELSE '0' END ||
       ');'
FROM core_contabilidade;
*/

-- ============================================================================
-- SCRIPT DE MIGRACAO - USANDO DATABASE LINK (se disponivel)
-- ============================================================================

-- Criar Database Link para PostgreSQL (requer Oracle Gateway for ODBC)
/*
CREATE DATABASE LINK pg_gestao
CONNECT TO "gestao_user" IDENTIFIED BY "password"
USING 'pg_odbc_connection';
*/

-- ============================================================================
-- PROCEDURES DE MIGRACAO
-- ============================================================================

CREATE OR REPLACE PACKAGE pkg_migration AS
    /*
    Package para migracao de dados do PostgreSQL para Oracle.
    Inclui procedures para cada tabela principal.
    */

    -- Migrar todas as tabelas
    PROCEDURE migrar_tudo(
        p_limpar_destino IN BOOLEAN DEFAULT FALSE
    );

    -- Migrar tabela especifica
    PROCEDURE migrar_contabilidades;
    PROCEDURE migrar_imobiliarias;
    PROCEDURE migrar_contas_bancarias;
    PROCEDURE migrar_imoveis;
    PROCEDURE migrar_compradores;
    PROCEDURE migrar_indices;
    PROCEDURE migrar_contratos;
    PROCEDURE migrar_parcelas;
    PROCEDURE migrar_reajustes;
    PROCEDURE migrar_notificacoes;

    -- Validar migracao
    PROCEDURE validar_migracao(
        p_erros OUT NUMBER,
        p_avisos OUT NUMBER
    );

    -- Limpar dados de destino
    PROCEDURE limpar_dados_destino;

END pkg_migration;
/

CREATE OR REPLACE PACKAGE BODY pkg_migration AS

    -- ========================================================================
    -- MIGRAR TUDO
    -- ========================================================================
    PROCEDURE migrar_tudo(
        p_limpar_destino IN BOOLEAN DEFAULT FALSE
    ) IS
    BEGIN
        IF p_limpar_destino THEN
            limpar_dados_destino;
        END IF;

        DBMS_OUTPUT.PUT_LINE('Iniciando migracao...');
        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando contabilidades...');
        migrar_contabilidades;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando imobiliarias...');
        migrar_imobiliarias;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando contas bancarias...');
        migrar_contas_bancarias;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando imoveis...');
        migrar_imoveis;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando compradores...');
        migrar_compradores;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando indices...');
        migrar_indices;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando contratos...');
        migrar_contratos;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando parcelas...');
        migrar_parcelas;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando reajustes...');
        migrar_reajustes;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migrando notificacoes...');
        migrar_notificacoes;

        DBMS_OUTPUT.PUT_LINE(SYSTIMESTAMP || ' - Migracao concluida!');
        COMMIT;
    END migrar_tudo;

    -- ========================================================================
    -- MIGRAR CONTABILIDADES
    -- ========================================================================
    PROCEDURE migrar_contabilidades IS
    BEGIN
        -- Exemplo usando External Table
        /*
        INSERT INTO gc_contabilidade (nome, razao_social, cnpj, endereco, telefone, email, responsavel, ativo)
        SELECT nome, razao_social, cnpj, endereco, telefone, email, responsavel, ativo
        FROM ext_contabilidade;
        */
        NULL; -- Implementar conforme metodo escolhido
    END migrar_contabilidades;

    -- ========================================================================
    -- MIGRAR IMOBILIARIAS
    -- ========================================================================
    PROCEDURE migrar_imobiliarias IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_imobiliarias;

    -- ========================================================================
    -- MIGRAR CONTAS BANCARIAS
    -- ========================================================================
    PROCEDURE migrar_contas_bancarias IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_contas_bancarias;

    -- ========================================================================
    -- MIGRAR IMOVEIS
    -- ========================================================================
    PROCEDURE migrar_imoveis IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_imoveis;

    -- ========================================================================
    -- MIGRAR COMPRADORES
    -- ========================================================================
    PROCEDURE migrar_compradores IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_compradores;

    -- ========================================================================
    -- MIGRAR INDICES
    -- ========================================================================
    PROCEDURE migrar_indices IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_indices;

    -- ========================================================================
    -- MIGRAR CONTRATOS
    -- ========================================================================
    PROCEDURE migrar_contratos IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_contratos;

    -- ========================================================================
    -- MIGRAR PARCELAS
    -- ========================================================================
    PROCEDURE migrar_parcelas IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_parcelas;

    -- ========================================================================
    -- MIGRAR REAJUSTES
    -- ========================================================================
    PROCEDURE migrar_reajustes IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_reajustes;

    -- ========================================================================
    -- MIGRAR NOTIFICACOES
    -- ========================================================================
    PROCEDURE migrar_notificacoes IS
    BEGIN
        NULL; -- Implementar conforme metodo escolhido
    END migrar_notificacoes;

    -- ========================================================================
    -- VALIDAR MIGRACAO
    -- ========================================================================
    PROCEDURE validar_migracao(
        p_erros OUT NUMBER,
        p_avisos OUT NUMBER
    ) IS
    BEGIN
        p_erros := 0;
        p_avisos := 0;

        -- Verificar integridade referencial
        FOR r IN (
            SELECT 'Imobiliaria sem contabilidade' AS problema, COUNT(*) AS qtd
            FROM gc_imobiliaria i
            WHERE NOT EXISTS (SELECT 1 FROM gc_contabilidade c WHERE c.id = i.contabilidade_id)
            UNION ALL
            SELECT 'Contrato sem imovel', COUNT(*)
            FROM gc_contrato c
            WHERE NOT EXISTS (SELECT 1 FROM gc_imovel i WHERE i.id = c.imovel_id)
            UNION ALL
            SELECT 'Contrato sem comprador', COUNT(*)
            FROM gc_contrato c
            WHERE NOT EXISTS (SELECT 1 FROM gc_comprador comp WHERE comp.id = c.comprador_id)
            UNION ALL
            SELECT 'Parcela sem contrato', COUNT(*)
            FROM gc_parcela p
            WHERE NOT EXISTS (SELECT 1 FROM gc_contrato c WHERE c.id = p.contrato_id)
        ) LOOP
            IF r.qtd > 0 THEN
                DBMS_OUTPUT.PUT_LINE('ERRO: ' || r.problema || ': ' || r.qtd || ' registros');
                p_erros := p_erros + r.qtd;
            END IF;
        END LOOP;

        -- Verificar totais
        DBMS_OUTPUT.PUT_LINE('---');
        DBMS_OUTPUT.PUT_LINE('Totais migrados:');

        FOR r IN (
            SELECT 'Contabilidades' AS tabela, COUNT(*) AS qtd FROM gc_contabilidade
            UNION ALL SELECT 'Imobiliarias', COUNT(*) FROM gc_imobiliaria
            UNION ALL SELECT 'Contas Bancarias', COUNT(*) FROM gc_conta_bancaria
            UNION ALL SELECT 'Imoveis', COUNT(*) FROM gc_imovel
            UNION ALL SELECT 'Compradores', COUNT(*) FROM gc_comprador
            UNION ALL SELECT 'Contratos', COUNT(*) FROM gc_contrato
            UNION ALL SELECT 'Parcelas', COUNT(*) FROM gc_parcela
        ) LOOP
            DBMS_OUTPUT.PUT_LINE('  ' || r.tabela || ': ' || r.qtd);
        END LOOP;

    END validar_migracao;

    -- ========================================================================
    -- LIMPAR DADOS DESTINO
    -- ========================================================================
    PROCEDURE limpar_dados_destino IS
    BEGIN
        -- Limpar na ordem inversa das dependencias
        DELETE FROM gc_item_retorno;
        DELETE FROM gc_arquivo_retorno;
        DELETE FROM gc_item_remessa;
        DELETE FROM gc_arquivo_remessa;
        DELETE FROM gc_notificacao;
        DELETE FROM gc_template_notificacao;
        DELETE FROM gc_historico_pagamento;
        DELETE FROM gc_reajuste;
        DELETE FROM gc_parcela;
        DELETE FROM gc_contrato;
        DELETE FROM gc_indice_reajuste;
        DELETE FROM gc_comprador;
        DELETE FROM gc_imovel;
        DELETE FROM gc_conta_bancaria;
        DELETE FROM gc_acesso_usuario;
        DELETE FROM gc_imobiliaria;
        DELETE FROM gc_contabilidade;
        DELETE FROM gc_config_email;
        DELETE FROM gc_config_sms;
        DELETE FROM gc_config_whatsapp;

        COMMIT;
        DBMS_OUTPUT.PUT_LINE('Dados de destino limpos com sucesso.');
    END limpar_dados_destino;

END pkg_migration;
/

-- ============================================================================
-- MAPEAMENTO DE TABELAS POSTGRESQL -> ORACLE
-- ============================================================================
/*
PostgreSQL Table               -> Oracle Table
-----------------------------------------------
core_contabilidade             -> gc_contabilidade
core_imobiliaria               -> gc_imobiliaria
core_contabancaria             -> gc_conta_bancaria
core_imovel                    -> gc_imovel
core_comprador                 -> gc_comprador
core_acessousuario             -> gc_acesso_usuario
contratos_indicereajuste       -> gc_indice_reajuste
contratos_contrato             -> gc_contrato
financeiro_parcela             -> gc_parcela
financeiro_reajuste            -> gc_reajuste
financeiro_historicopagamento  -> gc_historico_pagamento
financeiro_arquivoremessa      -> gc_arquivo_remessa
financeiro_itemremessa         -> gc_item_remessa
financeiro_arquivoretorno      -> gc_arquivo_retorno
financeiro_itemretorno         -> gc_item_retorno
notificacoes_configuracaoemail -> gc_config_email
notificacoes_configuracaosms   -> gc_config_sms
notificacoes_configuracaowhatsapp -> gc_config_whatsapp
notificacoes_notificacao       -> gc_notificacao
notificacoes_templatenotificacao -> gc_template_notificacao
*/

-- ============================================================================
-- SCRIPT DE EXPORTACAO POSTGRESQL (executar no PostgreSQL)
-- ============================================================================
/*
-- Executar no PostgreSQL para gerar CSVs:

\COPY (SELECT id, nome, razao_social, cnpj, endereco, telefone, email, responsavel, ativo, criado_em, atualizado_em FROM core_contabilidade) TO '/tmp/gc_contabilidade.csv' WITH CSV HEADER;

\COPY (SELECT id, contabilidade_id, nome, razao_social, cnpj, cep, logradouro, numero, complemento, bairro, cidade, estado, endereco, telefone, email, responsavel_financeiro, banco, agencia, conta, pix, tipo_valor_multa, percentual_multa_padrao, tipo_valor_juros, percentual_juros_padrao, dias_para_encargos_padrao, boleto_sem_valor, parcela_no_documento, campo_desconto_abatimento_pdf, tipo_valor_desconto, percentual_desconto_padrao, dias_para_desconto_padrao, tipo_valor_desconto2, desconto2_padrao, dias_para_desconto2_padrao, tipo_valor_desconto3, desconto3_padrao, dias_para_desconto3_padrao, instrucao_padrao, tipo_titulo, aceite, ativo, criado_em, atualizado_em FROM core_imobiliaria) TO '/tmp/gc_imobiliaria.csv' WITH CSV HEADER;

\COPY (SELECT id, imobiliaria_id, banco, descricao, principal, agencia, conta, convenio, carteira, nosso_numero_atual, modalidade, tipo_pix, chave_pix, cobranca_registrada, prazo_baixa, prazo_protesto, layout_cnab, numero_remessa_cnab_atual, ativo, criado_em, atualizado_em FROM core_contabancaria) TO '/tmp/gc_conta_bancaria.csv' WITH CSV HEADER;

\COPY (SELECT id, imobiliaria_id, tipo, identificacao, loteamento, cep, logradouro, numero, complemento, bairro, cidade, estado, endereco, latitude, longitude, area, valor, matricula, inscricao_municipal, observacoes, disponivel, ativo, criado_em, atualizado_em FROM core_imovel) TO '/tmp/gc_imovel.csv' WITH CSV HEADER;

\COPY (SELECT id, tipo_pessoa, nome, cpf, rg, data_nascimento, estado_civil, profissao, cnpj, nome_fantasia, inscricao_estadual, inscricao_municipal, responsavel_legal, responsavel_cpf, cep, logradouro, numero, complemento, bairro, cidade, estado, endereco, telefone, celular, email, notificar_email, notificar_sms, notificar_whatsapp, conjuge_nome, conjuge_cpf, conjuge_rg, observacoes, ativo, criado_em, atualizado_em FROM core_comprador) TO '/tmp/gc_comprador.csv' WITH CSV HEADER;

\COPY (SELECT * FROM contratos_indicereajuste) TO '/tmp/gc_indice_reajuste.csv' WITH CSV HEADER;

\COPY (SELECT * FROM contratos_contrato) TO '/tmp/gc_contrato.csv' WITH CSV HEADER;

\COPY (SELECT * FROM financeiro_parcela) TO '/tmp/gc_parcela.csv' WITH CSV HEADER;

\COPY (SELECT * FROM financeiro_reajuste) TO '/tmp/gc_reajuste.csv' WITH CSV HEADER;
*/
