/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Paginas 40-41: Imoveis (Lista e Formulario)
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
==============================================================================
*/

-- ============================================================================
-- PAGINA 40: LISTA DE IMOVEIS
-- ============================================================================
-- Tipo: Interactive Report com Cards View

/*
================================================================================
REGIAO: Interactive Report - Imoveis
================================================================================
*/

-- Source SQL:
/*
SELECT
    i.id,
    i.identificacao,
    i.loteamento,
    i.tipo,
    ti.descricao AS tipo_desc,
    i.cidade || '/' || i.estado AS cidade_uf,
    i.area,
    TO_CHAR(i.valor, 'L999G999G999D99', 'NLS_CURRENCY=R$') AS valor_formatado,
    i.valor,
    i.matricula,
    CASE i.disponivel WHEN 1 THEN 'Disponivel' ELSE 'Vendido' END AS status_disponibilidade,
    CASE i.disponivel WHEN 1 THEN 'u-success' ELSE 'u-warning' END AS status_css,
    im.nome AS imobiliaria,
    i.latitude,
    i.longitude,
    CASE WHEN i.latitude IS NOT NULL AND i.longitude IS NOT NULL THEN 'S' ELSE 'N' END AS tem_geolocalizacao,
    -- Para Cards View
    COALESCE(i.loteamento || ' - ', '') || i.identificacao AS card_title,
    ti.descricao || ' - ' || i.area || ' m²' AS card_subtitle,
    'fa-map-marker' AS card_icon
FROM gc_imovel i
JOIN gc_imobiliaria im ON im.id = i.imobiliaria_id
LEFT JOIN gc_tipo_imovel ti ON ti.codigo = i.tipo
WHERE i.ativo = 1
  AND (:P40_IMOBILIARIA_ID IS NULL OR i.imobiliaria_id = :P40_IMOBILIARIA_ID)
  AND (:P40_TIPO IS NULL OR i.tipo = :P40_TIPO)
  AND (:P40_DISPONIVEL IS NULL OR i.disponivel = :P40_DISPONIVEL)
  AND (:P40_LOTEAMENTO IS NULL OR UPPER(i.loteamento) LIKE '%' || UPPER(:P40_LOTEAMENTO) || '%')
ORDER BY i.loteamento, i.identificacao
*/

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P40_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome
-- Display Null: Yes

-- P40_TIPO
-- Type: Select List
-- Label: Tipo
-- LOV: SELECT descricao d, codigo r FROM gc_tipo_imovel ORDER BY descricao
-- Display Null: Yes

-- P40_DISPONIVEL
-- Type: Select List
-- Label: Disponibilidade
-- LOV: 1;Disponiveis,0;Vendidos
-- Display Null: Yes (Todos)

-- P40_LOTEAMENTO
-- Type: Text Field
-- Label: Loteamento

/*
================================================================================
CARDS VIEW ATTRIBUTES
================================================================================
*/

-- Card Title: CARD_TITLE
-- Card Subtitle: CARD_SUBTITLE
-- Card Icon: CARD_ICON
-- Badge Column: STATUS_DISPONIBILIDADE
-- Badge CSS Class: STATUS_CSS
-- Primary Key: ID
-- Link Target: Page 41, P41_ID=#ID#

/*
================================================================================
BOTOES
================================================================================
*/

-- Botao: Novo Imovel
-- Action: Redirect to Page 41

-- Botao: Alternar Visualizacao (Report/Cards)
-- Action: Execute JavaScript
/*
apex.region('imoveis_report').widget().interactiveReport('option', 'currentView', 'icon');
*/

-- ============================================================================
-- PAGINA 41: FORMULARIO DE IMOVEL
-- ============================================================================

/*
================================================================================
TAB 1: Dados do Imovel
================================================================================
*/

-- P41_ID (Hidden, PK)

-- P41_IMOBILIARIA_ID
-- Type: Select List
-- Label: Imobiliaria
-- Required: Yes
-- LOV: SELECT nome d, id r FROM gc_imobiliaria WHERE ativo = 1 ORDER BY nome

-- P41_TIPO
-- Type: Select List
-- Label: Tipo de Imovel
-- Required: Yes
-- LOV: SELECT descricao d, codigo r FROM gc_tipo_imovel ORDER BY descricao
-- Default: LOTE

-- P41_IDENTIFICACAO
-- Type: Text Field
-- Label: Identificacao
-- Required: Yes
-- Help: Ex: Quadra 1, Lote 15

-- P41_LOTEAMENTO
-- Type: Text Field
-- Label: Loteamento/Empreendimento

-- P41_AREA
-- Type: Number Field
-- Label: Area (m²)
-- Required: Yes
-- Format: 999G999D99

-- P41_VALOR
-- Type: Number Field
-- Label: Valor (R$)
-- Format: 999G999G999D99

-- P41_MATRICULA
-- Type: Text Field
-- Label: Matricula

-- P41_INSCRICAO_MUNICIPAL
-- Type: Text Field
-- Label: Inscricao Municipal

-- P41_DISPONIVEL
-- Type: Switch
-- Label: Disponivel para Venda
-- Default: 1

-- P41_OBSERVACOES
-- Type: Textarea
-- Label: Observacoes

/*
================================================================================
TAB 2: Endereco
================================================================================
*/

-- P41_CEP, P41_LOGRADOURO, P41_NUMERO, P41_COMPLEMENTO
-- P41_BAIRRO, P41_CIDADE, P41_ESTADO
-- (Mesma estrutura das imobiliarias)

/*
================================================================================
TAB 3: Geolocalizacao
================================================================================
*/

-- P41_LATITUDE
-- Type: Number Field
-- Label: Latitude
-- Format: 999D9999999

-- P41_LONGITUDE
-- Type: Number Field
-- Label: Longitude
-- Format: 999D9999999

-- Regiao: Mapa
-- Type: Map Region
-- Source: P41_LATITUDE, P41_LONGITUDE

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Buscar Coordenadas pelo Endereco
-- Event: Click Button (Buscar Coordenadas)
-- True Action: Execute JavaScript (Google Maps Geocoding API)

/*
var endereco = $v('P41_LOGRADOURO') + ', ' + $v('P41_NUMERO') + ' - ' +
               $v('P41_BAIRRO') + ', ' + $v('P41_CIDADE') + ' - ' + $v('P41_ESTADO');

// Chamar API de geocodificacao
apex.server.process('GEOCODE_ENDERECO', {
    x01: endereco
}, {
    success: function(data) {
        if (data.lat && data.lng) {
            $s('P41_LATITUDE', data.lat);
            $s('P41_LONGITUDE', data.lng);
            apex.region('mapa_imovel').refresh();
        }
    }
});
*/

-- ============================================================================
-- PAGINA 50: LISTA DE COMPRADORES
-- ============================================================================

/*
================================================================================
REGIAO: Interactive Report - Compradores
================================================================================
*/

-- Source SQL:
/*
SELECT
    c.id,
    c.nome,
    c.tipo_pessoa,
    CASE c.tipo_pessoa WHEN 'PF' THEN 'Pessoa Fisica' ELSE 'Pessoa Juridica' END AS tipo_desc,
    COALESCE(c.cpf, c.cnpj) AS documento,
    c.email,
    c.celular,
    c.cidade || '/' || c.estado AS cidade_uf,
    CASE c.notificar_email WHEN 1 THEN 'fa-check u-success' ELSE 'fa-times u-danger' END AS notif_email_icon,
    CASE c.notificar_sms WHEN 1 THEN 'fa-check u-success' ELSE 'fa-times u-danger' END AS notif_sms_icon,
    CASE c.notificar_whatsapp WHEN 1 THEN 'fa-check u-success' ELSE 'fa-times u-danger' END AS notif_whats_icon,
    (SELECT COUNT(*) FROM gc_contrato ct WHERE ct.comprador_id = c.id) AS total_contratos,
    CASE c.ativo WHEN 1 THEN 'Ativo' ELSE 'Inativo' END AS status
FROM gc_comprador c
WHERE c.ativo = 1 OR :P50_MOSTRAR_INATIVOS = 'S'
ORDER BY c.nome
*/

/*
================================================================================
PAGE ITEMS - FILTROS
================================================================================
*/

-- P50_TIPO_PESSOA
-- Type: Select List
-- LOV: PF;Pessoa Fisica,PJ;Pessoa Juridica
-- Display Null: Yes (Todos)

-- P50_BUSCA
-- Type: Text Field
-- Label: Buscar (Nome, CPF, CNPJ)

-- P50_MOSTRAR_INATIVOS
-- Type: Switch
-- Default: N

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Busca Rapida
-- Event: Key Release
-- Selection: P50_BUSCA
-- Debounce: 500ms
-- True Action: Refresh Region

-- ============================================================================
-- PAGINA 51: FORMULARIO DE COMPRADOR
-- ============================================================================

/*
================================================================================
TAB 1: Dados Pessoais
================================================================================
*/

-- P51_ID (Hidden, PK)

-- P51_TIPO_PESSOA
-- Type: Radio Group
-- Label: Tipo de Pessoa
-- Required: Yes
-- LOV: PF;Pessoa Fisica,PJ;Pessoa Juridica
-- Default: PF

-- P51_NOME
-- Type: Text Field
-- Label: Nome Completo / Razao Social
-- Required: Yes

/*
================================================================================
GRUPO: Pessoa Fisica (Show when P51_TIPO_PESSOA = 'PF')
================================================================================
*/

-- P51_CPF
-- Type: Text Field
-- Label: CPF
-- Format Mask: 999.999.999-99
-- Condition: P51_TIPO_PESSOA = 'PF'

-- P51_RG
-- Type: Text Field
-- Label: RG

-- P51_DATA_NASCIMENTO
-- Type: Date Picker
-- Label: Data de Nascimento

-- P51_ESTADO_CIVIL
-- Type: Select List
-- Label: Estado Civil
-- LOV: SOLTEIRO;Solteiro(a),CASADO;Casado(a),DIVORCIADO;Divorciado(a),VIUVO;Viuvo(a),UNIAO_ESTAVEL;Uniao Estavel

-- P51_PROFISSAO
-- Type: Text Field
-- Label: Profissao

/*
================================================================================
GRUPO: Pessoa Juridica (Show when P51_TIPO_PESSOA = 'PJ')
================================================================================
*/

-- P51_CNPJ
-- Type: Text Field
-- Label: CNPJ
-- Format Mask: 99.999.999/9999-99
-- Condition: P51_TIPO_PESSOA = 'PJ'

-- P51_NOME_FANTASIA
-- Type: Text Field
-- Label: Nome Fantasia

-- P51_INSCRICAO_ESTADUAL
-- Type: Text Field
-- Label: Inscricao Estadual

-- P51_INSCRICAO_MUNICIPAL
-- Type: Text Field
-- Label: Inscricao Municipal

-- P51_RESPONSAVEL_LEGAL
-- Type: Text Field
-- Label: Responsavel Legal

-- P51_RESPONSAVEL_CPF
-- Type: Text Field
-- Label: CPF do Responsavel

/*
================================================================================
TAB 2: Endereco
================================================================================
*/

-- (Mesma estrutura de endereco - CEP, Logradouro, etc.)

/*
================================================================================
TAB 3: Contato e Notificacoes
================================================================================
*/

-- P51_TELEFONE
-- Type: Text Field
-- Label: Telefone
-- Required: Yes

-- P51_CELULAR
-- Type: Text Field
-- Label: Celular
-- Required: Yes

-- P51_EMAIL
-- Type: Text Field
-- Label: E-mail
-- Required: Yes

-- P51_NOTIFICAR_EMAIL
-- Type: Switch
-- Label: Notificar por E-mail
-- Default: 1

-- P51_NOTIFICAR_SMS
-- Type: Switch
-- Label: Notificar por SMS
-- Default: 0

-- P51_NOTIFICAR_WHATSAPP
-- Type: Switch
-- Label: Notificar por WhatsApp
-- Default: 0

/*
================================================================================
TAB 4: Conjuge (Show when Estado Civil = CASADO ou UNIAO_ESTAVEL)
================================================================================
*/

-- P51_CONJUGE_NOME
-- Type: Text Field
-- Label: Nome do Conjuge

-- P51_CONJUGE_CPF
-- Type: Text Field
-- Label: CPF do Conjuge
-- Format Mask: 999.999.999-99

-- P51_CONJUGE_RG
-- Type: Text Field
-- Label: RG do Conjuge

/*
================================================================================
DYNAMIC ACTIONS
================================================================================
*/

-- DA: Alternar campos PF/PJ
-- Event: Change
-- Selection: P51_TIPO_PESSOA

/*
if ($v('P51_TIPO_PESSOA') === 'PF') {
    // Mostrar campos PF
    apex.item('P51_CPF').show();
    apex.item('P51_RG').show();
    apex.item('P51_DATA_NASCIMENTO').show();
    apex.item('P51_ESTADO_CIVIL').show();
    apex.item('P51_PROFISSAO').show();
    // Esconder campos PJ
    apex.item('P51_CNPJ').hide();
    apex.item('P51_NOME_FANTASIA').hide();
    apex.item('P51_INSCRICAO_ESTADUAL').hide();
    apex.item('P51_RESPONSAVEL_LEGAL').hide();
} else {
    // Inverso
    apex.item('P51_CPF').hide();
    // ... etc
    apex.item('P51_CNPJ').show();
    // ... etc
}
*/

-- DA: Mostrar Conjuge
-- Event: Change
-- Selection: P51_ESTADO_CIVIL
-- Condition: Value in ('CASADO', 'UNIAO_ESTAVEL')
-- True Action: Show Region (Conjuge)
-- False Action: Hide Region (Conjuge)

/*
================================================================================
VALIDATIONS
================================================================================
*/

-- Validation: CPF Valido (quando PF)
-- Type: PL/SQL Function Body Returning Boolean
/*
DECLARE
    v_cpf VARCHAR2(11);
    v_soma NUMBER;
    v_resto NUMBER;
    v_dv1 NUMBER;
    v_dv2 NUMBER;
BEGIN
    IF :P51_TIPO_PESSOA != 'PF' THEN
        RETURN TRUE;
    END IF;

    v_cpf := REGEXP_REPLACE(:P51_CPF, '[^0-9]', '');

    IF LENGTH(v_cpf) != 11 THEN
        RETURN FALSE;
    END IF;

    -- Verificar digitos iguais
    IF REGEXP_LIKE(v_cpf, '^(.)\1{10}$') THEN
        RETURN FALSE;
    END IF;

    -- Calcular DV1
    v_soma := 0;
    FOR i IN 1..9 LOOP
        v_soma := v_soma + TO_NUMBER(SUBSTR(v_cpf, i, 1)) * (11 - i);
    END LOOP;
    v_resto := MOD(v_soma, 11);
    v_dv1 := CASE WHEN v_resto < 2 THEN 0 ELSE 11 - v_resto END;

    -- Calcular DV2
    v_soma := 0;
    FOR i IN 1..10 LOOP
        v_soma := v_soma + TO_NUMBER(SUBSTR(v_cpf, i, 1)) * (12 - i);
    END LOOP;
    v_resto := MOD(v_soma, 11);
    v_dv2 := CASE WHEN v_resto < 2 THEN 0 ELSE 11 - v_resto END;

    RETURN TO_NUMBER(SUBSTR(v_cpf, 10, 1)) = v_dv1
       AND TO_NUMBER(SUBSTR(v_cpf, 11, 1)) = v_dv2;
END;
*/
-- Error Message: CPF invalido.
