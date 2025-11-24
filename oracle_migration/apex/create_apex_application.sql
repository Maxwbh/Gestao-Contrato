/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Script de Criacao da Aplicacao APEX
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Linkedin: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================

Este script cria a estrutura base da aplicacao APEX.
Execute apos criar o Workspace APEX para o schema GESTAO_CONTRATO.

==============================================================================
*/

PROMPT
PROMPT ==============================================================================
PROMPT Criando Aplicacao APEX - Sistema de Gestao de Contratos
PROMPT ==============================================================================
PROMPT

-- ============================================================================
-- CONFIGURACOES APEX (executar como APEX_ADMIN ou no Application Builder)
-- ============================================================================

/*
INSTRUCOES MANUAIS PARA CRIAR A APLICACAO NO APEX:

1. Acesse o APEX Application Builder
2. Clique em "Create Application"
3. Configure:
   - Name: Sistema de Gestao de Contratos
   - Application ID: 100 (ou proximo disponivel)
   - Schema: GESTAO_CONTRATO
   - Authentication: Application Express Authentication
   - Theme: Universal Theme (Theme 42)

4. Adicione as seguintes paginas:
*/

-- ============================================================================
-- DEFINICAO DAS PAGINAS DA APLICACAO
-- ============================================================================

/*
PAGINAS DA APLICACAO:

Pagina 1 - Dashboard (Home)
  - Cards com totais: Contratos Ativos, Parcelas Vencidas, Valor a Receber
  - Grafico de receitas mensais
  - Lista de parcelas a vencer
  - Baseada em: vw_dashboard_imobiliaria

Pagina 10 - Contabilidades
  - Interactive Report
  - Formulario de edicao
  - Tabela: gc_contabilidade

Pagina 20 - Imobiliarias
  - Interactive Report com filtro por Contabilidade
  - Formulario de edicao com LOV de Contabilidade
  - Tabela: gc_imobiliaria

Pagina 30 - Contas Bancarias
  - Interactive Report com filtro por Imobiliaria
  - Formulario de edicao
  - LOV de Bancos (gc_banco)
  - Tabela: gc_conta_bancaria

Pagina 40 - Imoveis
  - Interactive Report com filtros
  - Formulario de edicao
  - Cards/Gallery view
  - Tabela: gc_imovel

Pagina 50 - Compradores
  - Interactive Report
  - Formulario dinamico (PF/PJ)
  - Busca por CPF/CNPJ
  - Tabela: gc_comprador

Pagina 100 - Contratos
  - Interactive Report
  - View: vw_contrato_detalhado
  - Filtros: Status, Imobiliaria, Periodo
  - Modal de detalhes

Pagina 110 - Contrato (Formulario)
  - Wizard de criacao
  - Selecao de Imovel (LOV filtrada)
  - Selecao/Cadastro de Comprador
  - Configuracao de parcelas
  - Gerar parcelas automaticamente
  - Tabela: gc_contrato

Pagina 120 - Parcelas do Contrato
  - Report de parcelas
  - View: vw_parcela_detalhada
  - Botoes: Registrar Pagamento, Gerar Boleto
  - Modal de pagamento

Pagina 200 - Parcelas (Todas)
  - Interactive Report
  - View: vw_parcela_detalhada
  - Filtros: Status, Vencidas, A Vencer
  - Bulk actions

Pagina 210 - Parcelas Vencidas
  - Report focado em cobranca
  - View: vw_parcelas_vencidas
  - Botoes de notificacao

Pagina 300 - Boletos
  - Interactive Report
  - View: vw_boletos
  - Botoes: Gerar Boleto, Baixar PDF
  - Integracao com BRcobranca

Pagina 310 - Gerar Boletos em Lote
  - Wizard de selecao
  - Selecao por contrato/periodo
  - Chamada a pkg_brcobranca.gerar_boletos_lote

Pagina 400 - CNAB Remessa
  - Lista de arquivos: vw_arquivos_remessa
  - Botao: Nova Remessa
  - Download de arquivo

Pagina 410 - Nova Remessa
  - Selecao de conta bancaria
  - Selecao de parcelas para remessa
  - Geracao via pkg_brcobranca

Pagina 420 - CNAB Retorno
  - Upload de arquivo
  - Processamento via pkg_brcobranca
  - Lista de itens processados

Pagina 500 - Notificacoes
  - Configuracoes de Email/SMS/WhatsApp
  - Templates de notificacao
  - Historico de envios

Pagina 600 - Indices de Reajuste
  - Interactive Report
  - View: vw_indices_reajuste
  - Importacao do BCB

Pagina 700 - Relatorios
  - Extrato de contrato
  - Posicao de carteira
  - Inadimplencia
  - Receitas por periodo

Pagina 900 - Configuracoes
  - Parametros do sistema
  - URL do BRcobranca
  - Configuracoes de notificacao

Pagina 9999 - Login
  - Pagina de autenticacao
*/

-- ============================================================================
-- SHARED COMPONENTS - LOVs
-- ============================================================================

-- LOV: Contabilidades
/*
SELECT nome AS d, id AS r
FROM gc_contabilidade
WHERE ativo = 1
ORDER BY nome
*/

-- LOV: Imobiliarias (com filtro de contabilidade)
/*
SELECT nome AS d, id AS r
FROM gc_imobiliaria
WHERE ativo = 1
  AND (:P_CONTABILIDADE_ID IS NULL OR contabilidade_id = :P_CONTABILIDADE_ID)
ORDER BY nome
*/

-- LOV: Bancos
/*
SELECT nome AS d, codigo AS r
FROM gc_banco
ORDER BY codigo
*/

-- LOV: UFs
/*
SELECT nome AS d, sigla AS r
FROM gc_uf
ORDER BY nome
*/

-- LOV: Tipos de Imovel
/*
SELECT descricao AS d, codigo AS r
FROM gc_tipo_imovel
*/

-- LOV: Status de Contrato
/*
SELECT descricao AS d, codigo AS r
FROM gc_status_contrato
*/

-- LOV: Tipos de Correcao
/*
SELECT descricao AS d, codigo AS r
FROM gc_tipo_correcao
*/

-- LOV: Contas Bancarias
/*
SELECT display_value AS d, id AS r
FROM vw_lov_contas_bancarias
WHERE (:P_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P_IMOBILIARIA_ID)
*/

-- LOV: Compradores
/*
SELECT display_value AS d, id AS r
FROM vw_lov_compradores
*/

-- LOV: Imoveis Disponiveis
/*
SELECT display_value AS d, id AS r
FROM vw_lov_imoveis
WHERE disponivel = 1
  AND (:P_IMOBILIARIA_ID IS NULL OR imobiliaria_id = :P_IMOBILIARIA_ID)
*/

-- ============================================================================
-- PROCESSES - PL/SQL
-- ============================================================================

-- Process: Gerar Parcelas do Contrato
/*
DECLARE
    v_msg VARCHAR2(4000);
BEGIN
    pkg_contrato.gerar_parcelas(
        p_contrato_id   => :P110_ID,
        p_gerar_boletos => FALSE,
        p_msg_erro      => v_msg
    );

    IF v_msg IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20001, v_msg);
    END IF;
END;
*/

-- Process: Registrar Pagamento
/*
DECLARE
    v_msg VARCHAR2(4000);
BEGIN
    pkg_contrato.registrar_pagamento(
        p_parcela_id      => :P120_PARCELA_ID,
        p_valor_pago      => :P120_VALOR_PAGO,
        p_data_pagamento  => :P120_DATA_PAGAMENTO,
        p_forma_pagamento => :P120_FORMA_PAGAMENTO,
        p_observacoes     => :P120_OBSERVACOES,
        p_msg_erro        => v_msg
    );

    IF v_msg IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20001, v_msg);
    END IF;
END;
*/

-- Process: Gerar Boleto
/*
DECLARE
    v_sucesso        BOOLEAN;
    v_nosso_numero   VARCHAR2(30);
    v_codigo_barras  VARCHAR2(50);
    v_linha_digitavel VARCHAR2(60);
    v_pdf_content    BLOB;
    v_msg            VARCHAR2(4000);
BEGIN
    pkg_brcobranca.gerar_boleto_brcobranca(
        p_parcela_id        => :P300_PARCELA_ID,
        p_conta_bancaria_id => :P300_CONTA_BANCARIA_ID,
        p_sucesso           => v_sucesso,
        p_nosso_numero      => v_nosso_numero,
        p_codigo_barras     => v_codigo_barras,
        p_linha_digitavel   => v_linha_digitavel,
        p_pdf_content       => v_pdf_content,
        p_msg_erro          => v_msg
    );

    IF NOT v_sucesso THEN
        RAISE_APPLICATION_ERROR(-20001, 'Erro ao gerar boleto: ' || v_msg);
    END IF;

    :P300_SUCCESS_MSG := 'Boleto gerado com sucesso. Nosso Numero: ' || v_nosso_numero;
END;
*/

-- Process: Gerar Remessa CNAB
/*
DECLARE
    v_arquivo_id NUMBER;
    v_conteudo   CLOB;
    v_msg        VARCHAR2(4000);
BEGIN
    pkg_brcobranca.gerar_remessa_parcelas(
        p_conta_bancaria_id  => :P410_CONTA_BANCARIA_ID,
        p_parcelas_ids       => :P410_PARCELAS_SELECIONADAS,
        p_layout             => :P410_LAYOUT,
        p_arquivo_remessa_id => v_arquivo_id,
        p_conteudo           => v_conteudo,
        p_msg_erro           => v_msg
    );

    IF v_msg IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20001, 'Erro ao gerar remessa: ' || v_msg);
    END IF;

    :P410_ARQUIVO_ID := v_arquivo_id;
    :P410_SUCCESS_MSG := 'Remessa gerada com sucesso. ID: ' || v_arquivo_id;
END;
*/

-- ============================================================================
-- VALIDATIONS
-- ============================================================================

-- Validation: CPF valido
/*
DECLARE
    v_cpf VARCHAR2(14) := REPLACE(REPLACE(:P50_CPF, '.', ''), '-', '');
    v_soma NUMBER := 0;
    v_resto NUMBER;
    v_dv1 NUMBER;
    v_dv2 NUMBER;
BEGIN
    IF LENGTH(v_cpf) != 11 THEN
        RETURN FALSE;
    END IF;

    -- Verifica se todos os digitos sao iguais
    IF REGEXP_LIKE(v_cpf, '^(.)\1{10}$') THEN
        RETURN FALSE;
    END IF;

    -- Calculo do primeiro digito verificador
    FOR i IN 1..9 LOOP
        v_soma := v_soma + TO_NUMBER(SUBSTR(v_cpf, i, 1)) * (11 - i);
    END LOOP;
    v_resto := MOD(v_soma, 11);
    v_dv1 := CASE WHEN v_resto < 2 THEN 0 ELSE 11 - v_resto END;

    -- Calculo do segundo digito verificador
    v_soma := 0;
    FOR i IN 1..10 LOOP
        v_soma := v_soma + TO_NUMBER(SUBSTR(v_cpf, i, 1)) * (12 - i);
    END LOOP;
    v_resto := MOD(v_soma, 11);
    v_dv2 := CASE WHEN v_resto < 2 THEN 0 ELSE 11 - v_resto END;

    RETURN TO_NUMBER(SUBSTR(v_cpf, 10, 1)) = v_dv1 AND TO_NUMBER(SUBSTR(v_cpf, 11, 1)) = v_dv2;
END;
*/

-- ============================================================================
-- DYNAMIC ACTIONS
-- ============================================================================

-- DA: Ao selecionar Contabilidade, filtrar Imobiliarias
/*
Event: Change
Selection: P_CONTABILIDADE_ID
True Action: Refresh - Region: Imobiliarias (ou LOV)
*/

-- DA: Ao selecionar Tipo Pessoa, mostrar/esconder campos
/*
Event: Change
Selection: P50_TIPO_PESSOA

When PF:
  Show: CPF, RG, Data Nascimento, Estado Civil, Profissao
  Hide: CNPJ, Nome Fantasia, Inscricao Estadual, Responsavel Legal

When PJ:
  Show: CNPJ, Nome Fantasia, Inscricao Estadual, Responsavel Legal
  Hide: CPF, RG, Data Nascimento, Estado Civil, Profissao
*/

-- DA: Calcular valor financiado automaticamente
/*
Event: Change
Selection: P110_VALOR_TOTAL, P110_VALOR_ENTRADA
True Action: Execute JavaScript
  $s('P110_VALOR_FINANCIADO',
     parseFloat($v('P110_VALOR_TOTAL') || 0) - parseFloat($v('P110_VALOR_ENTRADA') || 0));
*/

-- ============================================================================
-- AUTHORIZATION SCHEMES
-- ============================================================================

-- Auth: Is Administrator
/*
RETURN NVL(APEX_UTIL.GET_SESSION_STATE('APP_USER_IS_ADMIN'), 'N') = 'Y';
*/

-- Auth: Can Edit
/*
BEGIN
    SELECT 1 INTO :dummy
    FROM gc_acesso_usuario
    WHERE usuario_id = :APP_USER_ID
      AND imobiliaria_id = :P_IMOBILIARIA_ID
      AND pode_editar = 1
      AND ativo = 1;
    RETURN TRUE;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN FALSE;
END;
*/

-- ============================================================================
-- APPLICATION ITEMS
-- ============================================================================

/*
APP_USER_ID          - ID do usuario logado
APP_CONTABILIDADE_ID - Contabilidade selecionada
APP_IMOBILIARIA_ID   - Imobiliaria selecionada
APP_USER_IS_ADMIN    - Flag de administrador
BRCOBRANCA_URL       - URL da API BRcobranca
*/

-- ============================================================================
-- APPLICATION PROCESSES
-- ============================================================================

-- Process: On New Session (After Auth)
/*
BEGIN
    -- Obter ID do usuario
    SELECT id INTO :APP_USER_ID
    FROM apex_workspace_apex_users
    WHERE user_name = :APP_USER;

    -- Verificar se eh admin
    :APP_USER_IS_ADMIN := CASE
        WHEN apex_util.get_first_granted_role(:APP_USER) IN ('Administrator', 'ADMIN')
        THEN 'Y' ELSE 'N'
    END;

    -- Configurar BRcobranca URL
    :BRCOBRANCA_URL := pkg_brcobranca.get_api_url;

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        :APP_USER_ID := NULL;
        :APP_USER_IS_ADMIN := 'N';
END;
*/

PROMPT
PROMPT ==============================================================================
PROMPT Estrutura da aplicacao APEX definida.
PROMPT
PROMPT Para criar a aplicacao:
PROMPT 1. Acesse o APEX Application Builder
PROMPT 2. Use "Create Application" com as configuracoes acima
PROMPT 3. Adicione as paginas conforme documentado
PROMPT ==============================================================================
