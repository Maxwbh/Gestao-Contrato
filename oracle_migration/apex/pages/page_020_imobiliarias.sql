/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 20-21: Imobiliarias (Lista e Formulario)
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
==============================================================================
*/

-- ============================================================================
-- PAGINA 20: LISTA DE IMOBILIARIAS
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Imobiliarias
================================================================================
*/

-- Source SQL:
/*
SELECT
    i.id,
    i.nome,
    i.razao_social,
    i.cnpj,
    i.cidade || '/' || i.estado AS cidade_uf,
    i.telefone,
    i.email,
    i.responsavel_financeiro,
    c.nome AS contabilidade,
    CASE i.ativo WHEN 1 THEN 'Ativo' ELSE 'Inativo' END AS status,
    (SELECT COUNT(*) FROM gc_contrato ct WHERE ct.imobiliaria_id = i.id AND ct.status = 'ATIVO') AS contratos_ativos,
    (SELECT COUNT(*) FROM gc_conta_bancaria cb WHERE cb.imobiliaria_id = i.id AND cb.ativo = 1) AS contas_bancarias
FROM gc_imobiliaria i
JOIN gc_contabilidade c ON c.id = i.contabilidade_id
ORDER BY i.nome
*/

-- Filtro por Contabilidade (Page Item P20_CONTABILIDADE_ID):
-- WHERE (:P20_CONTABILIDADE_ID IS NULL OR i.contabilidade_id = :P20_CONTABILIDADE_ID)

/*
================================================================================
PAGE ITEMS
================================================================================
*/

-- P20_CONTABILIDADE_ID
-- Type: Select List
-- Label: Filtrar por Contabilidade
-- LOV: SELECT nome d, id r FROM gc_contabilidade WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes
-- Null Display: -- Todas --
-- Submit When Enter Pressed: Yes

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Filtrar por Contabilidade
-- Event: Change
-- Selection: P20_CONTABILIDADE_ID
-- True Action: Refresh Region (Interactive Report)

-- ============================================================================
-- PAGINA 21: FORMULARIO DE IMOBILIARIA
-- ============================================================================
-- Tipo: Form
-- Template: Standard com Tabs

/*
================================================================================
TAB 1: Dados Gerais
================================================================================
*/

-- P21_ID (Hidden, PK)

-- P21_CONTABILIDADE_ID
-- Type: Select List
-- Label: Contabilidade
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_contabilidade WHERE ativo = 1 ORDER BY nome

-- P21_NOME
-- Type: Text Field
-- Label: Nome da Imobiliaria
-- Required: Yes

-- P21_RAZAO_SOCIAL
-- Type: Text Field
-- Label: Razao Social
-- Required: Yes

-- P21_CNPJ
-- Type: Text Field
-- Label: CNPJ
-- Required: Yes
-- Format Mask: 99.999.999/9999-99

-- P21_TELEFONE
-- Type: Text Field
-- Label: Telefone
-- Required: Yes

-- P21_EMAIL
-- Type: Text Field
-- Label: E-mail
-- Required: Yes

-- P21_RESPONSAVEL_FINANCEIRO
-- Type: Text Field
-- Label: Responsavel Financeiro
-- Required: Yes

-- P21_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
TAB 2: Endereco
================================================================================
*/

-- P21_CEP
-- Type: Text Field
-- Label: CEP
-- Max Length: 9
-- Format: 99999-999

-- P21_LOGRADOURO
-- Type: Text Field
-- Label: Logradouro

-- P21_NUMERO
-- Type: Text Field
-- Label: Numero

-- P21_COMPLEMENTO
-- Type: Text Field
-- Label: Complemento

-- P21_BAIRRO
-- Type: Text Field
-- Label: Bairro

-- P21_CIDADE
-- Type: Text Field
-- Label: Cidade

-- P21_ESTADO
-- Type: Select List
-- Label: UF
-- LOV: SELECT nome d, sigla r FROM gc_uf ORDER BY nome

/*
================================================================================
TAB 3: Configuracoes de Boleto
================================================================================
*/

-- P21_TIPO_VALOR_MULTA
-- Type: Radio Group
-- Label: Tipo de Multa
-- LOV: PERCENTUAL;Percentual,REAL;Valor em Reais
-- Default: PERCENTUAL

-- P21_PERCENTUAL_MULTA_PADRAO
-- Type: Number Field
-- Label: Valor da Multa
-- Format: 999G999D99

-- P21_TIPO_VALOR_JUROS
-- Type: Radio Group
-- Label: Tipo de Juros
-- LOV: PERCENTUAL;Percentual,REAL;Valor em Reais
-- Default: PERCENTUAL

-- P21_PERCENTUAL_JUROS_PADRAO
-- Type: Number Field
-- Label: Juros ao Dia
-- Format: 999G999D9999

-- P21_DIAS_PARA_ENCARGOS_PADRAO
-- Type: Number Field
-- Label: Dias sem Encargos
-- Default: 0

-- P21_TIPO_VALOR_DESCONTO
-- Type: Radio Group
-- Label: Tipo de Desconto
-- Default: PERCENTUAL

-- P21_PERCENTUAL_DESCONTO_PADRAO
-- Type: Number Field
-- Label: Valor do Desconto

-- P21_DIAS_PARA_DESCONTO_PADRAO
-- Type: Number Field
-- Label: Dias para Desconto

-- P21_TIPO_TITULO
-- Type: Select List
-- Label: Tipo do Titulo
-- LOV: SELECT descricao d, codigo r FROM gc_tipo_titulo ORDER BY codigo
-- Default: RC

-- P21_INSTRUCAO_PADRAO
-- Type: Text Field
-- Label: Instrucao Padrao

-- P21_ACEITE
-- Type: Switch
-- Label: Aceite
-- Default: 0

/*
================================================================================
DYNAMIC ACTIONS - Busca CEP (ViaCEP)
================================================================================
*/

-- DA: Buscar CEP
-- Event: Change
-- Selection: P21_CEP
-- Condition: Length >= 8
-- True Action: Execute JavaScript Code

/*
var cep = $v('P21_CEP').replace(/\D/g, '');
if (cep.length === 8) {
    apex.server.process('BUSCAR_CEP', {
        x01: cep
    }, {
        success: function(data) {
            if (data.success) {
                $s('P21_LOGRADOURO', data.logradouro);
                $s('P21_BAIRRO', data.bairro);
                $s('P21_CIDADE', data.localidade);
                $s('P21_ESTADO', data.uf);
            }
        }
    });
}
*/

/*
================================================================================
AJAX CALLBACK: BUSCAR_CEP
================================================================================
*/

/*
DECLARE
    v_response CLOB;
    v_cep VARCHAR2(8) := APEX_APPLICATION.g_x01;
BEGIN
    v_response := APEX_WEB_SERVICE.make_rest_request(
        p_url => 'https://viacep.com.br/ws/' || v_cep || '/json/',
        p_http_method => 'GET'
    );

    IF APEX_WEB_SERVICE.g_status_code = 200 THEN
        APEX_JSON.parse(v_response);

        IF APEX_JSON.get_varchar2('erro') IS NULL THEN
            APEX_JSON.initialize_clob_output;
            APEX_JSON.open_object;
            APEX_JSON.write('success', TRUE);
            APEX_JSON.write('logradouro', APEX_JSON.get_varchar2('logradouro'));
            APEX_JSON.write('bairro', APEX_JSON.get_varchar2('bairro'));
            APEX_JSON.write('localidade', APEX_JSON.get_varchar2('localidade'));
            APEX_JSON.write('uf', APEX_JSON.get_varchar2('uf'));
            APEX_JSON.close_object;
            HTP.p(APEX_JSON.get_clob_output);
            APEX_JSON.free_output;
        ELSE
            APEX_JSON.open_object;
            APEX_JSON.write('success', FALSE);
            APEX_JSON.write('message', 'CEP nao encontrado');
            APEX_JSON.close_object;
        END IF;
    END IF;
END;
*/

-- ============================================================================
-- PAGINA 30: CONTAS BANCARIAS
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Contas Bancarias
================================================================================
*/

-- Source SQL:
/*
SELECT
    cb.id,
    b.nome AS banco,
    cb.descricao,
    cb.agencia,
    cb.conta,
    cb.convenio,
    cb.carteira,
    CASE cb.principal WHEN 1 THEN '<span class="u-badge u-success">Principal</span>' ELSE '' END AS principal_badge,
    cb.nosso_numero_atual,
    i.nome AS imobiliaria,
    CASE cb.ativo WHEN 1 THEN 'Ativo' ELSE 'Inativo' END AS status
FROM gc_conta_bancaria cb
JOIN gc_banco b ON b.codigo = cb.banco
JOIN gc_imobiliaria i ON i.id = cb.imobiliaria_id
WHERE (:P30_IMOBILIARIA_ID IS NULL OR cb.imobiliaria_id = :P30_IMOBILIARIA_ID)
ORDER BY cb.principal DESC, b.nome, cb.descricao
*/

/*
================================================================================
PAGE ITEM: Filtro Imobiliaria
================================================================================
*/

-- P30_IMOBILIARIA_ID
-- Type: Select List
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes
-- Null Display: -- Todas --

-- ============================================================================
-- PAGINA 31: FORMULARIO CONTA BANCARIA
-- ============================================================================

/*
================================================================================
ITENS DO FORMULARIO
================================================================================
*/

-- P31_ID (Hidden, PK)

-- P31_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome

-- P31_BANCO
-- Type: Select List
-- Label: Banco
-- Required: Yes
-- LOV: SELECT nome d, codigo r FROM gc_banco ORDER BY codigo

-- P31_DESCRICAO
-- Type: Text Field
-- Label: Descricao
-- Required: Yes
-- Help: Ex: Conta Principal, Conta Boletos

-- P31_PRINCIPAL
-- Type: Switch
-- Label: Conta Principal
-- Default: 0

-- P31_AGENCIA
-- Type: Text Field
-- Label: Agencia
-- Required: Yes

-- P31_CONTA
-- Type: Text Field
-- Label: Conta
-- Required: Yes

-- P31_CONVENIO
-- Type: Text Field
-- Label: Convenio/Codigo Cliente

-- P31_CARTEIRA
-- Type: Text Field
-- Label: Carteira

-- P31_NOSSO_NUMERO_ATUAL
-- Type: Number Field
-- Label: Nosso Numero Atual
-- Default: 0

-- P31_MODALIDADE
-- Type: Text Field
-- Label: Modalidade

-- P31_TIPO_PIX
-- Type: Select List
-- Label: Tipo Chave PIX
-- LOV: CPF;CPF,CNPJ;CNPJ,EMAIL;E-mail,TELEFONE;Telefone,ALEATORIA;Chave Aleatoria
-- Display Null: Yes

-- P31_CHAVE_PIX
-- Type: Text Field
-- Label: Chave PIX

-- P31_COBRANCA_REGISTRADA
-- Type: Switch
-- Label: Cobranca Registrada
-- Default: 1

-- P31_PRAZO_BAIXA
-- Type: Number Field
-- Label: Prazo para Baixa (dias)
-- Default: 0

-- P31_PRAZO_PROTESTO
-- Type: Number Field
-- Label: Prazo para Protesto (dias)
-- Default: 0

-- P31_LAYOUT_CNAB
-- Type: Select List
-- Label: Layout CNAB
-- LOV: CNAB_240;Layout 240,CNAB_400;Layout 400
-- Default: CNAB_240

-- P31_ATIVO
-- Type: Switch
-- Default: 1

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Mostrar/Esconder Chave PIX
-- Event: Change
-- Selection: P31_TIPO_PIX
-- True Action: Show Item P31_CHAVE_PIX when P31_TIPO_PIX is not null
-- False Action: Hide Item P31_CHAVE_PIX when P31_TIPO_PIX is null
