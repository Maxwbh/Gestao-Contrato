/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Script de Instalacao Completo
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Linkedin: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================

USO:
  sqlplus sys/password@localhost:1521/XEPDB1 as sysdba @install.sql

==============================================================================
*/

SET SERVEROUTPUT ON SIZE UNLIMITED
SET ECHO ON
SET TIMING ON
SET LINESIZE 200

WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT
PROMPT ==============================================================================
PROMPT Sistema de Gestao de Contratos - Oracle 23c / APEX 24
PROMPT Desenvolvedor: Maxwell da Silva Oliveira (maxwbh@gmail.com)
PROMPT Empresa: M&S do Brasil LTDA
PROMPT ==============================================================================
PROMPT

-- ============================================================================
-- CRIAR USUARIO/SCHEMA
-- ============================================================================
PROMPT Criando usuario GESTAO_CONTRATO...

DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM dba_users WHERE username = 'GESTAO_CONTRATO';
    IF v_count > 0 THEN
        EXECUTE IMMEDIATE 'DROP USER gestao_contrato CASCADE';
        DBMS_OUTPUT.PUT_LINE('Usuario existente removido.');
    END IF;
END;
/

CREATE USER gestao_contrato IDENTIFIED BY "GestaoContrato2024!"
    DEFAULT TABLESPACE users
    TEMPORARY TABLESPACE temp
    QUOTA UNLIMITED ON users;

GRANT CREATE SESSION TO gestao_contrato;
GRANT CREATE TABLE TO gestao_contrato;
GRANT CREATE VIEW TO gestao_contrato;
GRANT CREATE SEQUENCE TO gestao_contrato;
GRANT CREATE PROCEDURE TO gestao_contrato;
GRANT CREATE TRIGGER TO gestao_contrato;
GRANT CREATE TYPE TO gestao_contrato;
GRANT CREATE SYNONYM TO gestao_contrato;
GRANT CREATE DATABASE LINK TO gestao_contrato;

-- Grants para UTL_HTTP (integracao BRcobranca)
GRANT EXECUTE ON UTL_HTTP TO gestao_contrato;
GRANT EXECUTE ON DBMS_LOB TO gestao_contrato;
GRANT EXECUTE ON DBMS_OUTPUT TO gestao_contrato;

PROMPT Usuario criado com sucesso!

-- ============================================================================
-- MUDAR PARA O SCHEMA GESTAO_CONTRATO
-- ============================================================================
ALTER SESSION SET CURRENT_SCHEMA = gestao_contrato;

-- ============================================================================
-- EXECUTAR SCRIPTS DDL
-- ============================================================================
PROMPT
PROMPT Criando tabelas...
@ddl/01_create_tables.sql

PROMPT
PROMPT Criando triggers...
@triggers/01_audit_triggers.sql

PROMPT
PROMPT Criando packages...
@packages/pkg_contrato.sql
@packages/pkg_boleto.sql
@packages/pkg_brcobranca.sql

PROMPT
PROMPT Criando views...
@views/01_views.sql

-- ============================================================================
-- VERIFICAR OBJETOS CRIADOS
-- ============================================================================
PROMPT
PROMPT Verificando objetos criados...

SELECT object_type, COUNT(*) AS quantidade
FROM user_objects
WHERE object_type IN ('TABLE', 'VIEW', 'PACKAGE', 'PACKAGE BODY', 'TRIGGER', 'INDEX', 'SEQUENCE')
GROUP BY object_type
ORDER BY object_type;

-- ============================================================================
-- VERIFICAR PACKAGES COMPILADOS
-- ============================================================================
PROMPT
PROMPT Verificando packages...

SELECT object_name, object_type, status
FROM user_objects
WHERE object_type IN ('PACKAGE', 'PACKAGE BODY')
ORDER BY object_name, object_type;

-- ============================================================================
-- CRIAR DADOS INICIAIS DE TESTE
-- ============================================================================
PROMPT
PROMPT Criando dados de teste...

-- Contabilidade de exemplo
INSERT INTO gc_contabilidade (nome, razao_social, cnpj, endereco, telefone, email, responsavel)
VALUES ('Contabilidade Exemplo', 'Contabilidade Exemplo LTDA', '12.345.678/0001-90',
        'Rua Exemplo, 123 - Centro - Sao Paulo/SP', '(11) 99999-9999',
        'contato@exemplo.com', 'Administrador');

-- Imobiliaria de exemplo
INSERT INTO gc_imobiliaria (contabilidade_id, nome, razao_social, cnpj, logradouro, numero, bairro, cidade, estado, cep, telefone, email, responsavel_financeiro)
VALUES (1, 'Imobiliaria Teste', 'Imobiliaria Teste LTDA', '98.765.432/0001-10',
        'Avenida Principal', '1000', 'Centro', 'Sao Paulo', 'SP', '01310-100',
        '(11) 88888-8888', 'imobiliaria@teste.com', 'Financeiro Teste');

-- Conta bancaria de exemplo
INSERT INTO gc_conta_bancaria (imobiliaria_id, banco, descricao, principal, agencia, conta, convenio, carteira)
VALUES (1, '001', 'Conta Principal BB', 1, '1234-5', '12345-6', '1234567', '17');

COMMIT;

PROMPT
PROMPT ==============================================================================
PROMPT INSTALACAO CONCLUIDA COM SUCESSO!
PROMPT ==============================================================================
PROMPT
PROMPT Proximos passos:
PROMPT 1. Configure o APEX Workspace para o schema GESTAO_CONTRATO
PROMPT 2. Importe a aplicacao APEX
PROMPT 3. Configure a URL do BRcobranca:
PROMPT    BEGIN pkg_brcobranca.set_api_url('http://localhost:9292'); END;
PROMPT
PROMPT Credenciais:
PROMPT   Usuario: gestao_contrato
PROMPT   Senha: GestaoContrato2024!
PROMPT
PROMPT ==============================================================================

EXIT;
