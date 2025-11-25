/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 10-11: Contabilidades (Lista e Formulario)
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
==============================================================================
*/

-- ============================================================================
-- PAGINA 10: LISTA DE CONTABILIDADES
-- ============================================================================
-- Tipo: Interactive Report
-- Template: Standard

/*
================================================================================
REGIAO: Interactive Report - Contabilidades
================================================================================
*/

-- Source SQL:
/*
SELECT
    id,
    nome,
    razao_social,
    cnpj,
    telefone,
    email,
    responsavel,
    CASE ativo WHEN 1 THEN 'Ativo' ELSE 'Inativo' END AS status,
    (SELECT COUNT(*) FROM gc_imobiliaria i WHERE i.contabilidade_id = c.id) AS qtd_imobiliarias,
    criado_em,
    atualizado_em
FROM gc_contabilidade c
ORDER BY nome
*/

-- Colunas:
-- ID: Hidden, Link to Page 11
-- NOME: Display, Link Column
-- RAZAO_SOCIAL: Display
-- CNPJ: Display, Format Mask: 99.999.999/9999-99
-- TELEFONE: Display
-- EMAIL: Display
-- RESPONSAVEL: Display
-- STATUS: Display, HTML Expression with badge
-- QTD_IMOBILIARIAS: Display, Alignment Center

-- Link Column: NOME
-- Target: Page 11, Set Items P11_ID = #ID#

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Criar Contabilidade
-- Position: Right of IR Search Bar
-- Action: Redirect to Page 11 (Clear Cache)
-- Hot: Yes

/*
================================================================================
COLUNAS COM FORMATACAO HTML
================================================================================
*/

-- Coluna STATUS - HTML Expression:
/*
<span class="u-badge #STATUS_CSS#">#STATUS#</span>
*/

-- Computed Column STATUS_CSS:
/*
CASE WHEN ativo = 1 THEN 'u-success' ELSE 'u-danger' END
*/

-- ============================================================================
-- PAGINA 11: FORMULARIO DE CONTABILIDADE
-- ============================================================================
-- Tipo: Form
-- Template: Standard
-- Data Source: Table/View - gc_contabilidade

/*
================================================================================
REGIAO: Formulario - Dados da Contabilidade
================================================================================
*/

-- P11_ID
-- Type: Hidden
-- Primary Key: Yes

-- P11_NOME
-- Type: Text Field
-- Label: Nome da Contabilidade
-- Required: Yes
-- Max Length: 200

-- P11_RAZAO_SOCIAL
-- Type: Text Field
-- Label: Razao Social
-- Required: Yes
-- Max Length: 200

-- P11_CNPJ
-- Type: Text Field
-- Label: CNPJ
-- Required: No
-- Max Length: 20
-- Format Mask: 99.999.999/9999-99

-- P11_ENDERECO
-- Type: Textarea
-- Label: Endereco
-- Required: Yes
-- Rows: 3

-- P11_TELEFONE
-- Type: Text Field
-- Label: Telefone
-- Required: Yes
-- Max Length: 20
-- Format Mask: (99) 99999-9999

-- P11_EMAIL
-- Type: Text Field
-- Label: E-mail
-- Required: Yes
-- Max Length: 254
-- Subtype: E-mail

-- P11_RESPONSAVEL
-- Type: Text Field
-- Label: Responsavel
-- Required: Yes
-- Max Length: 200

-- P11_ATIVO
-- Type: Switch
-- Label: Ativo
-- Default: 1

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: CANCEL
-- Position: Close
-- Action: Redirect to Page 10

-- Botao: DELETE
-- Position: Delete
-- Action: Submit Page
-- Condition: Item P11_ID is NOT NULL

-- Botao: SAVE
-- Position: Next
-- Action: Submit Page
-- Hot: Yes

-- Botao: CREATE
-- Position: Next
-- Action: Submit Page
-- Condition: Item P11_ID is NULL
-- Hot: Yes

/*
================================================================================
PROCESSES
================================================================================
*/

-- Process: Initialize Form
-- Type: Form - Initialization
-- When: Before Header

-- Process: Process Form
-- Type: Form - Automatic Row Processing (DML)
-- Table: gc_contabilidade
-- When: Submit

-- Process: Close Dialog
-- Type: Close Dialog
-- When: After Submit (Success)

/*
================================================================================
VALIDATIONS
================================================================================
*/

-- Validation: CNPJ Unico
-- Type: No Duplicate Value
-- Column: cnpj
-- Error Message: Este CNPJ ja esta cadastrado.

-- Validation: Email Valido
-- Type: Regular Expression
-- Expression: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
-- Item: P11_EMAIL
-- Error Message: E-mail invalido.

/*
================================================================================
BRANCHES
================================================================================
*/

-- Branch: Go To Page 10
-- When: After Processing
-- Target: Page 10
