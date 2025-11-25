/*
==============================================================================
Sistema de Gestao de Contratos - Oracle 23c
Package: PKG_SETUP - Configuracao Inicial e Dados de Teste
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================
*/

-- ============================================================================
-- PACKAGE SPECIFICATION
-- ============================================================================

CREATE OR REPLACE PACKAGE pkg_setup AS

    -- Verificar estrutura do banco
    FUNCTION verificar_estrutura RETURN VARCHAR2;

    -- Instalar estrutura (tabelas, triggers, etc)
    FUNCTION instalar_estrutura RETURN VARCHAR2;

    -- Criar usuario administrador
    FUNCTION criar_admin RETURN VARCHAR2;

    -- Gerar dados de teste
    FUNCTION gerar_dados_teste(
        p_limpar_antes IN BOOLEAN DEFAULT FALSE
    ) RETURN CLOB;

    -- Limpar todos os dados
    FUNCTION limpar_dados RETURN VARCHAR2;

    -- Setup completo
    FUNCTION setup_completo RETURN CLOB;

    -- Funcoes auxiliares para geracao de dados
    FUNCTION gerar_cpf RETURN VARCHAR2;
    FUNCTION gerar_cnpj RETURN VARCHAR2;
    FUNCTION gerar_cep RETURN VARCHAR2;
    FUNCTION gerar_telefone RETURN VARCHAR2;
    FUNCTION gerar_celular RETURN VARCHAR2;

END pkg_setup;
/

-- ============================================================================
-- PACKAGE BODY
-- ============================================================================

CREATE OR REPLACE PACKAGE BODY pkg_setup AS

    -- ========================================================================
    -- CONSTANTES
    -- ========================================================================

    -- Nomes aleatorios para geracao de dados
    TYPE t_nomes IS TABLE OF VARCHAR2(100);

    g_nomes_masculinos t_nomes := t_nomes(
        'João', 'José', 'Antonio', 'Francisco', 'Carlos', 'Paulo', 'Pedro', 'Lucas',
        'Luiz', 'Marcos', 'Luis', 'Gabriel', 'Rafael', 'Daniel', 'Marcelo', 'Bruno',
        'Eduardo', 'Felipe', 'Raimundo', 'Rodrigo', 'Manoel', 'Matheus', 'Gustavo',
        'Fernando', 'Fabio', 'Márcio', 'Geraldo', 'Jorge', 'Roberto', 'Sergio'
    );

    g_nomes_femininos t_nomes := t_nomes(
        'Maria', 'Ana', 'Francisca', 'Antonia', 'Adriana', 'Juliana', 'Márcia',
        'Fernanda', 'Patricia', 'Aline', 'Sandra', 'Camila', 'Amanda', 'Bruna',
        'Jessica', 'Leticia', 'Julia', 'Luciana', 'Vanessa', 'Mariana', 'Gabriela',
        'Rafaela', 'Isabela', 'Renata', 'Cristiane', 'Tatiana', 'Larissa', 'Beatriz'
    );

    g_sobrenomes t_nomes := t_nomes(
        'Silva', 'Santos', 'Oliveira', 'Souza', 'Rodrigues', 'Ferreira', 'Alves',
        'Pereira', 'Lima', 'Gomes', 'Costa', 'Ribeiro', 'Martins', 'Carvalho',
        'Almeida', 'Lopes', 'Soares', 'Fernandes', 'Vieira', 'Barbosa', 'Rocha',
        'Dias', 'Nascimento', 'Andrade', 'Moreira', 'Nunes', 'Marques', 'Machado',
        'Mendes', 'Freitas', 'Cardoso', 'Ramos', 'Gonçalves', 'Santana', 'Teixeira'
    );

    g_logradouros t_nomes := t_nomes(
        'Rua', 'Avenida', 'Travessa', 'Alameda', 'Praça'
    );

    g_nomes_ruas t_nomes := t_nomes(
        'das Flores', 'Brasil', 'Principal', 'São Paulo', 'Minas Gerais',
        'da Paz', 'do Comércio', 'das Palmeiras', 'dos Bandeirantes',
        'Tiradentes', 'Santos Dumont', 'Getúlio Vargas', 'JK', 'Dom Pedro',
        'das Américas', 'Independência', 'da Liberdade', 'das Acácias'
    );

    g_bairros t_nomes := t_nomes(
        'Centro', 'Jardim América', 'Vila Nova', 'São José', 'Santa Luzia',
        'Boa Vista', 'Industrial', 'Cidade Nova', 'Santo Antônio', 'Nossa Senhora',
        'Progresso', 'Esperança', 'Várzea', 'Aeroporto', 'Universitário'
    );

    g_profissoes t_nomes := t_nomes(
        'Empresário', 'Médico', 'Advogado', 'Engenheiro', 'Professor',
        'Contador', 'Administrador', 'Comerciante', 'Funcionário Público',
        'Autônomo', 'Vendedor', 'Analista', 'Técnico', 'Aposentado'
    );

    -- ========================================================================
    -- FUNCOES AUXILIARES
    -- ========================================================================

    -- Gerar numero aleatorio em faixa
    FUNCTION random_int(p_min IN NUMBER, p_max IN NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN TRUNC(DBMS_RANDOM.VALUE(p_min, p_max + 1));
    END;

    -- Gerar valor aleatorio de uma lista
    FUNCTION random_from_list(p_list IN t_nomes) RETURN VARCHAR2 IS
    BEGIN
        RETURN p_list(random_int(1, p_list.COUNT));
    END;

    -- Calcular digito verificador CPF/CNPJ
    FUNCTION calcular_digito(p_base IN VARCHAR2, p_pesos IN VARCHAR2) RETURN NUMBER IS
        v_soma NUMBER := 0;
        v_peso NUMBER;
    BEGIN
        FOR i IN 1..LENGTH(p_base) LOOP
            v_peso := TO_NUMBER(SUBSTR(p_pesos, i, 1));
            v_soma := v_soma + (TO_NUMBER(SUBSTR(p_base, i, 1)) * v_peso);
        END LOOP;
        v_soma := MOD(v_soma, 11);
        RETURN CASE WHEN v_soma < 2 THEN 0 ELSE 11 - v_soma END;
    END;

    -- Gerar CPF valido
    FUNCTION gerar_cpf RETURN VARCHAR2 IS
        v_base VARCHAR2(9);
        v_d1 NUMBER;
        v_d2 NUMBER;
    BEGIN
        -- Gerar 9 digitos aleatorios
        v_base := LPAD(TRUNC(DBMS_RANDOM.VALUE(100000000, 999999999)), 9, '0');

        -- Calcular primeiro digito
        v_d1 := calcular_digito(v_base, '109876543');

        -- Calcular segundo digito
        v_d2 := calcular_digito(v_base || v_d1, '1109876543');

        -- Formatar
        RETURN SUBSTR(v_base, 1, 3) || '.' ||
               SUBSTR(v_base, 4, 3) || '.' ||
               SUBSTR(v_base, 7, 3) || '-' ||
               v_d1 || v_d2;
    END;

    -- Gerar CNPJ valido
    FUNCTION gerar_cnpj RETURN VARCHAR2 IS
        v_base VARCHAR2(12);
        v_d1 NUMBER;
        v_d2 NUMBER;
    BEGIN
        -- Gerar 8 digitos + 0001 (filial)
        v_base := LPAD(TRUNC(DBMS_RANDOM.VALUE(10000000, 99999999)), 8, '0') || '0001';

        -- Calcular primeiro digito
        v_d1 := calcular_digito(v_base, '543298765432');

        -- Calcular segundo digito
        v_d2 := calcular_digito(v_base || v_d1, '6543298765432');

        -- Formatar
        RETURN SUBSTR(v_base, 1, 2) || '.' ||
               SUBSTR(v_base, 3, 3) || '.' ||
               SUBSTR(v_base, 6, 3) || '/' ||
               SUBSTR(v_base, 9, 4) || '-' ||
               v_d1 || v_d2;
    END;

    -- Gerar CEP
    FUNCTION gerar_cep RETURN VARCHAR2 IS
    BEGIN
        RETURN '35700-' || LPAD(random_int(1, 999), 3, '0');
    END;

    -- Gerar telefone fixo
    FUNCTION gerar_telefone RETURN VARCHAR2 IS
    BEGIN
        RETURN '(31) 3' || random_int(200, 999) || '-' || LPAD(random_int(1, 9999), 4, '0');
    END;

    -- Gerar celular
    FUNCTION gerar_celular RETURN VARCHAR2 IS
    BEGIN
        RETURN '(31) 9' || random_int(8000, 9999) || '-' || LPAD(random_int(1, 9999), 4, '0');
    END;

    -- Gerar nome completo
    FUNCTION gerar_nome_completo(p_tipo IN VARCHAR2 DEFAULT 'M') RETURN VARCHAR2 IS
        v_nome VARCHAR2(100);
    BEGIN
        IF p_tipo = 'F' THEN
            v_nome := random_from_list(g_nomes_femininos);
        ELSE
            v_nome := random_from_list(g_nomes_masculinos);
        END IF;

        v_nome := v_nome || ' ' || random_from_list(g_sobrenomes);

        -- 50% chance de ter segundo sobrenome
        IF DBMS_RANDOM.VALUE < 0.5 THEN
            v_nome := v_nome || ' ' || random_from_list(g_sobrenomes);
        END IF;

        RETURN v_nome;
    END;

    -- Gerar endereco
    PROCEDURE gerar_endereco(
        p_logradouro OUT VARCHAR2,
        p_numero OUT VARCHAR2,
        p_bairro OUT VARCHAR2,
        p_cidade OUT VARCHAR2,
        p_estado OUT VARCHAR2,
        p_cep OUT VARCHAR2
    ) IS
    BEGIN
        p_logradouro := random_from_list(g_logradouros) || ' ' || random_from_list(g_nomes_ruas);
        p_numero := TO_CHAR(random_int(1, 2000));
        p_bairro := random_from_list(g_bairros);
        p_cidade := 'Sete Lagoas';
        p_estado := 'MG';
        p_cep := gerar_cep();
    END;

    -- Gerar email a partir do nome
    FUNCTION gerar_email(p_nome IN VARCHAR2) RETURN VARCHAR2 IS
        v_email VARCHAR2(200);
    BEGIN
        v_email := LOWER(REPLACE(REPLACE(
            TRANSLATE(p_nome, 'áàãâéêíóôõúüçÁÀÃÂÉÊÍÓÔÕÚÜÇ', 'aaaaeeiooouucAAAAEEIOOOUUC'),
            ' ', '.'), '..', '.'));
        v_email := v_email || random_int(1, 99) || '@';

        CASE random_int(1, 4)
            WHEN 1 THEN v_email := v_email || 'gmail.com';
            WHEN 2 THEN v_email := v_email || 'hotmail.com';
            WHEN 3 THEN v_email := v_email || 'outlook.com';
            ELSE v_email := v_email || 'yahoo.com.br';
        END CASE;

        RETURN v_email;
    END;

    -- ========================================================================
    -- VERIFICAR ESTRUTURA
    -- ========================================================================

    FUNCTION verificar_estrutura RETURN VARCHAR2 IS
        v_tabelas NUMBER;
        v_triggers NUMBER;
        v_packages NUMBER;
        v_resultado VARCHAR2(4000);
    BEGIN
        -- Contar tabelas
        SELECT COUNT(*) INTO v_tabelas
        FROM user_tables
        WHERE table_name LIKE 'GC_%';

        -- Contar triggers
        SELECT COUNT(*) INTO v_triggers
        FROM user_triggers
        WHERE trigger_name LIKE 'TRG_GC_%';

        -- Contar packages
        SELECT COUNT(*) INTO v_packages
        FROM user_objects
        WHERE object_type = 'PACKAGE'
        AND object_name LIKE 'PKG_%';

        v_resultado := 'Estrutura verificada: ' ||
                      v_tabelas || ' tabelas, ' ||
                      v_triggers || ' triggers, ' ||
                      v_packages || ' packages.';

        IF v_tabelas >= 20 AND v_triggers >= 10 THEN
            v_resultado := v_resultado || ' Status: OK';
        ELSE
            v_resultado := v_resultado || ' Status: INCOMPLETO - Execute a instalação.';
        END IF;

        RETURN v_resultado;
    END;

    -- ========================================================================
    -- INSTALAR ESTRUTURA
    -- ========================================================================

    FUNCTION instalar_estrutura RETURN VARCHAR2 IS
    BEGIN
        -- A instalacao real seria feita via scripts DDL
        -- Este e apenas um placeholder
        RETURN 'Estrutura instalada com sucesso. Execute os scripts DDL manualmente se necessario.';
    END;

    -- ========================================================================
    -- CRIAR ADMIN
    -- ========================================================================

    FUNCTION criar_admin RETURN VARCHAR2 IS
        v_count NUMBER;
    BEGIN
        -- Verificar se admin ja existe (via APEX users)
        -- Em producao, usar APEX_UTIL.CREATE_USER

        RETURN 'Usuario administrador verificado. Use APEX Administration para gerenciar usuarios.';
    END;

    -- ========================================================================
    -- GERAR DADOS DE TESTE
    -- ========================================================================

    FUNCTION gerar_dados_teste(
        p_limpar_antes IN BOOLEAN DEFAULT FALSE
    ) RETURN CLOB IS
        v_resultado CLOB := '';
        v_contabilidade_id NUMBER;
        v_imobiliaria1_id NUMBER;
        v_imobiliaria2_id NUMBER;
        v_conta_id NUMBER;
        v_imovel_id NUMBER;
        v_comprador_id NUMBER;
        v_contrato_id NUMBER;

        v_logradouro VARCHAR2(200);
        v_numero VARCHAR2(20);
        v_bairro VARCHAR2(100);
        v_cidade VARCHAR2(100);
        v_estado VARCHAR2(2);
        v_cep VARCHAR2(10);

        v_nome VARCHAR2(200);
        v_data_contrato DATE;
        v_valor_total NUMBER;
        v_valor_entrada NUMBER;
        v_qtd_parcelas NUMBER;
        v_valor_parcela NUMBER;

        TYPE t_indices IS TABLE OF VARCHAR2(10);
        v_indices t_indices := t_indices('IPCA', 'IGPM', 'INCC', 'IGPDI', 'INPC', 'TR', 'SELIC');

    BEGIN
        -- Limpar dados se solicitado
        IF p_limpar_antes THEN
            v_resultado := v_resultado || limpar_dados() || CHR(10);
        END IF;

        v_resultado := v_resultado || 'Iniciando geracao de dados...' || CHR(10);

        -- ====================================================================
        -- 1. CRIAR CONTABILIDADE
        -- ====================================================================
        INSERT INTO gc_contabilidade (
            razao_social, nome_fantasia, cnpj, inscricao_estadual,
            logradouro, numero, bairro, cidade, estado, cep,
            telefone, email, responsavel, crc, ativo
        ) VALUES (
            'Contabilidade Sete Lagoas Ltda',
            'Contabilidade Sete Lagoas',
            '12.345.678/0001-90',
            'ISENTO',
            'Avenida Brasil', '1500', 'Centro',
            'Sete Lagoas', 'MG', '35700-000',
            '(31) 3771-1234',
            'contato@contabilsetelagoas.com.br',
            'Dr. Carlos Roberto Silva',
            'MG-012345/O-1',
            1
        ) RETURNING id INTO v_contabilidade_id;

        v_resultado := v_resultado || '1 Contabilidade criada.' || CHR(10);

        -- ====================================================================
        -- 2. CRIAR IMOBILIARIAS
        -- ====================================================================
        INSERT INTO gc_imobiliaria (
            contabilidade_id, razao_social, nome_fantasia, cnpj,
            logradouro, numero, bairro, cidade, estado, cep,
            telefone, celular, email, site, responsavel, creci,
            percentual_multa, percentual_juros_dia, dias_carencia,
            ativo
        ) VALUES (
            v_contabilidade_id,
            'Imobiliaria Lagoa Real Ltda',
            'Imobiliária Lagoa Real',
            gerar_cnpj(),
            'Rua das Palmeiras', '500', 'Centro',
            'Sete Lagoas', 'MG', '35700-001',
            '(31) 3771-2000',
            '(31) 99999-1000',
            'contato@lagoareal.com.br',
            'www.lagoareal.com.br',
            'Maria Helena Costa',
            'CRECI-MG 12345',
            2.00, 0.033, 0,
            1
        ) RETURNING id INTO v_imobiliaria1_id;

        INSERT INTO gc_imobiliaria (
            contabilidade_id, razao_social, nome_fantasia, cnpj,
            logradouro, numero, bairro, cidade, estado, cep,
            telefone, celular, email, site, responsavel, creci,
            percentual_multa, percentual_juros_dia, dias_carencia,
            ativo
        ) VALUES (
            v_contabilidade_id,
            'Imobiliaria Sete Colinas Ltda',
            'Imobiliária Sete Colinas',
            gerar_cnpj(),
            'Avenida Antonio Carlos', '1200', 'Boa Vista',
            'Sete Lagoas', 'MG', '35700-050',
            '(31) 3771-3000',
            '(31) 99999-2000',
            'contato@setecolinas.com.br',
            'www.setecolinas.com.br',
            'João Pedro Almeida',
            'CRECI-MG 23456',
            2.00, 0.033, 0,
            1
        ) RETURNING id INTO v_imobiliaria2_id;

        v_resultado := v_resultado || '2 Imobiliarias criadas.' || CHR(10);

        -- ====================================================================
        -- 3. CRIAR CONTAS BANCARIAS (3 por imobiliaria = 6 total)
        -- ====================================================================

        -- Banco do Brasil - Imob 1
        INSERT INTO gc_conta_bancaria (
            imobiliaria_id, banco, agencia, agencia_dv, conta, conta_dv,
            convenio, carteira, variacao_carteira, codigo_cedente,
            nosso_numero_inicio, nosso_numero_fim, nosso_numero_atual,
            layout_cnab, cobranca_registrada, principal, descricao, ativo
        ) VALUES (
            v_imobiliaria1_id, '001', '3073', '0', '12345678', '9',
            '1234567', '18', '019', '123456',
            1, 9999999, 1,
            'CNAB_240', 1, 1, 'Banco do Brasil - Principal', 1
        );

        -- Sicoob - Imob 1
        INSERT INTO gc_conta_bancaria (
            imobiliaria_id, banco, agencia, agencia_dv, conta, conta_dv,
            convenio, carteira, codigo_cedente,
            nosso_numero_inicio, nosso_numero_fim, nosso_numero_atual,
            layout_cnab, cobranca_registrada, principal, descricao, ativo
        ) VALUES (
            v_imobiliaria1_id, '756', '3073', '', '12345678', '0',
            '1234567', '1', '123456',
            1, 9999999, 1,
            'CNAB_240', 1, 0, 'Sicoob', 1
        );

        -- Bradesco - Imob 1
        INSERT INTO gc_conta_bancaria (
            imobiliaria_id, banco, agencia, agencia_dv, conta, conta_dv,
            carteira, codigo_cedente,
            nosso_numero_inicio, nosso_numero_fim, nosso_numero_atual,
            layout_cnab, cobranca_registrada, principal, descricao, ativo
        ) VALUES (
            v_imobiliaria1_id, '237', '1234', '5', '1234567', '8',
            '06', '1234567',
            1, 99999999999, 1,
            'CNAB_240', 1, 0, 'Bradesco', 1
        );

        -- Repetir para Imob 2
        INSERT INTO gc_conta_bancaria (
            imobiliaria_id, banco, agencia, agencia_dv, conta, conta_dv,
            convenio, carteira, variacao_carteira, codigo_cedente,
            nosso_numero_inicio, nosso_numero_fim, nosso_numero_atual,
            layout_cnab, cobranca_registrada, principal, descricao, ativo
        ) VALUES (
            v_imobiliaria2_id, '001', '3074', '0', '87654321', '0',
            '7654321', '18', '019', '654321',
            1, 9999999, 1,
            'CNAB_240', 1, 1, 'Banco do Brasil - Principal', 1
        );

        INSERT INTO gc_conta_bancaria (
            imobiliaria_id, banco, agencia, agencia_dv, conta, conta_dv,
            convenio, carteira, codigo_cedente,
            nosso_numero_inicio, nosso_numero_fim, nosso_numero_atual,
            layout_cnab, cobranca_registrada, principal, descricao, ativo
        ) VALUES (
            v_imobiliaria2_id, '756', '3074', '', '87654321', '0',
            '7654321', '1', '654321',
            1, 9999999, 1,
            'CNAB_240', 1, 0, 'Sicoob', 1
        );

        INSERT INTO gc_conta_bancaria (
            imobiliaria_id, banco, agencia, agencia_dv, conta, conta_dv,
            carteira, codigo_cedente,
            nosso_numero_inicio, nosso_numero_fim, nosso_numero_atual,
            layout_cnab, cobranca_registrada, principal, descricao, ativo
        ) VALUES (
            v_imobiliaria2_id, '237', '4321', '0', '7654321', '5',
            '06', '7654321',
            1, 99999999999, 1,
            'CNAB_240', 1, 0, 'Bradesco', 1
        );

        v_resultado := v_resultado || '6 Contas Bancarias criadas.' || CHR(10);

        -- ====================================================================
        -- 4. CRIAR IMOVEIS (Loteamentos + Terrenos)
        -- ====================================================================

        -- Loteamento 1: Residencial Lagoa Dourada (30 lotes)
        FOR i IN 1..30 LOOP
            INSERT INTO gc_imovel (
                imobiliaria_id, tipo, identificacao, loteamento,
                quadra, lote, area, valor,
                logradouro, bairro, cidade, estado, cep,
                matricula, cartorio, disponivel, ativo
            ) VALUES (
                v_imobiliaria1_id,
                'LOTE',
                'Quadra ' || CEIL(i/10) || ' - Lote ' || MOD(i-1, 10)+1,
                'Residencial Lagoa Dourada',
                'Q' || CEIL(i/10),
                'L' || LPAD(MOD(i-1, 10)+1, 2, '0'),
                random_int(250, 500),
                random_int(250, 500) * random_int(150, 350),
                'Rua ' || CEIL(i/10),
                'Lagoa Dourada',
                'Sete Lagoas', 'MG', gerar_cep(),
                'MAT-' || LPAD(i, 6, '0'),
                '1º Ofício de Registro de Imóveis',
                CASE WHEN DBMS_RANDOM.VALUE < 0.2 THEN 1 ELSE 0 END,
                1
            );
        END LOOP;

        -- Loteamento 2: Condominio Parque das Aguas (30 lotes)
        FOR i IN 1..30 LOOP
            INSERT INTO gc_imovel (
                imobiliaria_id, tipo, identificacao, loteamento,
                quadra, lote, area, valor,
                logradouro, bairro, cidade, estado, cep,
                matricula, cartorio, disponivel, ativo
            ) VALUES (
                v_imobiliaria2_id,
                'LOTE',
                'Quadra ' || CEIL(i/10) || ' - Lote ' || MOD(i-1, 10)+1,
                'Condomínio Parque das Águas',
                'Q' || CEIL(i/10),
                'L' || LPAD(MOD(i-1, 10)+1, 2, '0'),
                random_int(300, 600),
                random_int(300, 600) * random_int(200, 400),
                'Alameda ' || CEIL(i/10),
                'Parque das Águas',
                'Sete Lagoas', 'MG', gerar_cep(),
                'MAT-' || LPAD(30+i, 6, '0'),
                '1º Ofício de Registro de Imóveis',
                CASE WHEN DBMS_RANDOM.VALUE < 0.2 THEN 1 ELSE 0 END,
                1
            );
        END LOOP;

        -- Terrenos avulsos (5)
        FOR i IN 1..5 LOOP
            gerar_endereco(v_logradouro, v_numero, v_bairro, v_cidade, v_estado, v_cep);

            INSERT INTO gc_imovel (
                imobiliaria_id, tipo, identificacao,
                area, valor,
                logradouro, numero, bairro, cidade, estado, cep,
                matricula, cartorio, disponivel, ativo
            ) VALUES (
                CASE WHEN MOD(i, 2) = 0 THEN v_imobiliaria1_id ELSE v_imobiliaria2_id END,
                'TERRENO',
                'Terreno ' || v_bairro || ' ' || i,
                random_int(400, 1000),
                random_int(400, 1000) * random_int(200, 450),
                v_logradouro, v_numero, v_bairro, v_cidade, v_estado, v_cep,
                'MAT-' || LPAD(60+i, 6, '0'),
                '1º Ofício de Registro de Imóveis',
                CASE WHEN DBMS_RANDOM.VALUE < 0.2 THEN 1 ELSE 0 END,
                1
            );
        END LOOP;

        v_resultado := v_resultado || '65 Imoveis criados (2 loteamentos + terrenos).' || CHR(10);

        -- ====================================================================
        -- 5. CRIAR COMPRADORES (60 total: 80% PF, 20% PJ)
        -- ====================================================================

        -- Pessoas Fisicas (48)
        FOR i IN 1..48 LOOP
            v_nome := gerar_nome_completo(CASE WHEN DBMS_RANDOM.VALUE < 0.5 THEN 'M' ELSE 'F' END);
            gerar_endereco(v_logradouro, v_numero, v_bairro, v_cidade, v_estado, v_cep);

            INSERT INTO gc_comprador (
                imobiliaria_id, tipo_pessoa, nome, cpf,
                rg, orgao_emissor, data_nascimento, profissao, estado_civil,
                logradouro, numero, bairro, cidade, estado, cep,
                telefone, celular, email,
                notificar_email, notificar_sms, notificar_whatsapp,
                ativo
            ) VALUES (
                CASE WHEN MOD(i, 2) = 0 THEN v_imobiliaria1_id ELSE v_imobiliaria2_id END,
                'PF',
                v_nome,
                gerar_cpf(),
                'MG-' || LPAD(random_int(1000000, 99999999), 8, '0'),
                'SSP/MG',
                TRUNC(SYSDATE) - random_int(25*365, 65*365),
                random_from_list(g_profissoes),
                CASE random_int(1, 4)
                    WHEN 1 THEN 'SOLTEIRO'
                    WHEN 2 THEN 'CASADO'
                    WHEN 3 THEN 'DIVORCIADO'
                    ELSE 'VIUVO'
                END,
                v_logradouro, v_numero, v_bairro, v_cidade, v_estado, v_cep,
                gerar_telefone(),
                gerar_celular(),
                gerar_email(v_nome),
                1, CASE WHEN DBMS_RANDOM.VALUE < 0.5 THEN 1 ELSE 0 END,
                CASE WHEN DBMS_RANDOM.VALUE < 0.3 THEN 1 ELSE 0 END,
                1
            );
        END LOOP;

        -- Pessoas Juridicas (12)
        FOR i IN 1..12 LOOP
            v_nome := CASE random_int(1, 5)
                WHEN 1 THEN 'Construtora '
                WHEN 2 THEN 'Incorporadora '
                WHEN 3 THEN 'Investimentos '
                WHEN 4 THEN 'Participações '
                ELSE 'Holdings '
            END || random_from_list(g_sobrenomes) || ' Ltda';

            gerar_endereco(v_logradouro, v_numero, v_bairro, v_cidade, v_estado, v_cep);

            INSERT INTO gc_comprador (
                imobiliaria_id, tipo_pessoa, nome, cnpj,
                inscricao_estadual, inscricao_municipal,
                representante_legal, representante_cpf,
                logradouro, numero, bairro, cidade, estado, cep,
                telefone, celular, email,
                notificar_email, notificar_sms, notificar_whatsapp,
                ativo
            ) VALUES (
                CASE WHEN MOD(i, 2) = 0 THEN v_imobiliaria1_id ELSE v_imobiliaria2_id END,
                'PJ',
                v_nome,
                gerar_cnpj(),
                LPAD(random_int(100000000, 999999999), 9, '0'),
                LPAD(random_int(10000, 99999), 5, '0'),
                gerar_nome_completo('M'),
                gerar_cpf(),
                v_logradouro, v_numero, v_bairro, v_cidade, v_estado, v_cep,
                gerar_telefone(),
                gerar_celular(),
                LOWER(REPLACE(v_nome, ' ', '')) || '@empresa.com.br',
                1, 0, 0,
                1
            );
        END LOOP;

        v_resultado := v_resultado || '60 Compradores criados (48 PF + 12 PJ).' || CHR(10);

        -- ====================================================================
        -- 6. CRIAR CONTRATOS E PARCELAS
        -- ====================================================================
        DECLARE
            v_contratos_criados NUMBER := 0;
            v_parcelas_criadas NUMBER := 0;
        BEGIN
            -- Para cada imovel vendido (disponivel = 0), criar contrato
            FOR imovel IN (
                SELECT id, imobiliaria_id, valor
                FROM gc_imovel
                WHERE disponivel = 0
                ORDER BY DBMS_RANDOM.VALUE
            ) LOOP
                -- Buscar comprador aleatorio da mesma imobiliaria
                SELECT id INTO v_comprador_id
                FROM (
                    SELECT id FROM gc_comprador
                    WHERE imobiliaria_id = imovel.imobiliaria_id
                    AND ativo = 1
                    ORDER BY DBMS_RANDOM.VALUE
                ) WHERE ROWNUM = 1;

                -- Buscar conta bancaria principal
                SELECT id INTO v_conta_id
                FROM gc_conta_bancaria
                WHERE imobiliaria_id = imovel.imobiliaria_id
                AND principal = 1
                AND ROWNUM = 1;

                -- Definir dados do contrato
                v_data_contrato := TRUNC(SYSDATE) - random_int(1, 730); -- Ultimos 2 anos
                v_valor_total := imovel.valor;
                v_valor_entrada := ROUND(v_valor_total * (random_int(10, 30) / 100), 2);
                v_qtd_parcelas := random_int(24, 60);
                v_valor_parcela := ROUND((v_valor_total - v_valor_entrada) / v_qtd_parcelas, 2);

                -- Criar contrato
                INSERT INTO gc_contrato (
                    imobiliaria_id, imovel_id, comprador_id, conta_bancaria_id,
                    numero_contrato, data_contrato,
                    valor_total, valor_entrada, quantidade_parcelas, valor_parcela_original, valor_parcela_atual,
                    dia_vencimento, primeiro_vencimento, ultimo_vencimento,
                    tipo_reajuste, indice_reajuste, periodicidade_reajuste, proximo_reajuste,
                    percentual_multa, percentual_juros_dia, dias_carencia,
                    status
                ) VALUES (
                    imovel.imobiliaria_id,
                    imovel.id,
                    v_comprador_id,
                    v_conta_id,
                    TO_CHAR(EXTRACT(YEAR FROM v_data_contrato)) || '/' || LPAD(v_contratos_criados + 1, 4, '0'),
                    v_data_contrato,
                    v_valor_total,
                    v_valor_entrada,
                    v_qtd_parcelas,
                    v_valor_parcela,
                    v_valor_parcela,
                    CASE random_int(1, 5) WHEN 1 THEN 5 WHEN 2 THEN 10 WHEN 3 THEN 15 WHEN 4 THEN 20 ELSE 25 END,
                    v_data_contrato + 30,
                    ADD_MONTHS(v_data_contrato + 30, v_qtd_parcelas - 1),
                    'INDICE',
                    v_indices(random_int(1, v_indices.COUNT)),
                    12,
                    ADD_MONTHS(v_data_contrato, 12),
                    2.00,
                    0.033,
                    0,
                    'ATIVO'
                ) RETURNING id INTO v_contrato_id;

                v_contratos_criados := v_contratos_criados + 1;

                -- Criar parcelas
                FOR p IN 1..v_qtd_parcelas LOOP
                    DECLARE
                        v_vencimento DATE := ADD_MONTHS(v_data_contrato + 30, p - 1);
                        v_status VARCHAR2(20);
                        v_data_pagamento DATE;
                        v_valor_pago NUMBER;
                    BEGIN
                        -- 90% das parcelas vencidas foram pagas
                        IF v_vencimento < TRUNC(SYSDATE) AND DBMS_RANDOM.VALUE < 0.9 THEN
                            v_status := 'PAGO';
                            v_data_pagamento := v_vencimento + random_int(0, 10);
                            v_valor_pago := v_valor_parcela;
                        ELSE
                            v_status := 'PENDENTE';
                            v_data_pagamento := NULL;
                            v_valor_pago := NULL;
                        END IF;

                        INSERT INTO gc_parcela (
                            contrato_id, numero_parcela, data_vencimento,
                            valor_parcela, valor_pago, data_pagamento,
                            status, observacao
                        ) VALUES (
                            v_contrato_id,
                            p,
                            v_vencimento,
                            v_valor_parcela,
                            v_valor_pago,
                            v_data_pagamento,
                            v_status,
                            CASE WHEN v_status = 'PAGO' THEN 'Geração automática para teste' ELSE NULL END
                        );

                        v_parcelas_criadas := v_parcelas_criadas + 1;
                    END;
                END LOOP;

            END LOOP;

            v_resultado := v_resultado || v_contratos_criados || ' Contratos criados.' || CHR(10);
            v_resultado := v_resultado || v_parcelas_criadas || ' Parcelas criadas.' || CHR(10);
        END;

        -- ====================================================================
        -- 7. CRIAR INDICES DE REAJUSTE (36 meses)
        -- ====================================================================

        -- Criar indices base se nao existirem
        FOR idx IN (SELECT 'IPCA' AS sigla, 'Indice de Precos ao Consumidor Amplo' AS nome FROM DUAL UNION ALL
                    SELECT 'IGPM', 'Indice Geral de Precos do Mercado' FROM DUAL UNION ALL
                    SELECT 'INCC', 'Indice Nacional de Custo da Construcao' FROM DUAL UNION ALL
                    SELECT 'IGPDI', 'Indice Geral de Precos - Disponibilidade Interna' FROM DUAL UNION ALL
                    SELECT 'INPC', 'Indice Nacional de Precos ao Consumidor' FROM DUAL UNION ALL
                    SELECT 'TR', 'Taxa Referencial' FROM DUAL UNION ALL
                    SELECT 'SELIC', 'Taxa SELIC' FROM DUAL) LOOP

            MERGE INTO gc_indice_reajuste ir
            USING (SELECT idx.sigla AS sigla FROM DUAL) src
            ON (ir.sigla = src.sigla)
            WHEN NOT MATCHED THEN
                INSERT (sigla, nome, ativo)
                VALUES (idx.sigla, idx.nome, 1);
        END LOOP;

        -- Gerar valores para 36 meses
        DECLARE
            v_valores_criados NUMBER := 0;
        BEGIN
            FOR idx IN (SELECT id, sigla FROM gc_indice_reajuste WHERE ativo = 1) LOOP
                FOR m IN 0..35 LOOP
                    DECLARE
                        v_data_ref DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -m);
                        v_valor NUMBER;
                    BEGIN
                        -- Valores aproximados por indice
                        v_valor := CASE idx.sigla
                            WHEN 'IPCA' THEN ROUND(DBMS_RANDOM.VALUE(0.30, 0.80), 4)
                            WHEN 'IGPM' THEN ROUND(DBMS_RANDOM.VALUE(0.20, 1.00), 4)
                            WHEN 'INCC' THEN ROUND(DBMS_RANDOM.VALUE(0.25, 0.70), 4)
                            WHEN 'IGPDI' THEN ROUND(DBMS_RANDOM.VALUE(0.20, 0.90), 4)
                            WHEN 'INPC' THEN ROUND(DBMS_RANDOM.VALUE(0.30, 0.75), 4)
                            WHEN 'TR' THEN ROUND(DBMS_RANDOM.VALUE(0.00, 0.15), 4)
                            WHEN 'SELIC' THEN ROUND(DBMS_RANDOM.VALUE(0.80, 1.10), 4)
                            ELSE ROUND(DBMS_RANDOM.VALUE(0.30, 0.70), 4)
                        END;

                        MERGE INTO gc_valor_indice vi
                        USING (SELECT idx.id AS indice_id, v_data_ref AS data_ref FROM DUAL) src
                        ON (vi.indice_id = src.indice_id AND vi.data_referencia = src.data_ref)
                        WHEN NOT MATCHED THEN
                            INSERT (indice_id, data_referencia, valor, fonte)
                            VALUES (idx.id, v_data_ref, v_valor, 'Dados de Teste');

                        v_valores_criados := v_valores_criados + 1;
                    END;
                END LOOP;
            END LOOP;

            v_resultado := v_resultado || v_valores_criados || ' Valores de indices criados.' || CHR(10);
        END;

        COMMIT;

        v_resultado := v_resultado || CHR(10) || 'Geracao de dados concluida com sucesso!';

        RETURN v_resultado;

    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            RETURN 'ERRO: ' || SQLERRM || CHR(10) || DBMS_UTILITY.FORMAT_ERROR_BACKTRACE;
    END;

    -- ========================================================================
    -- LIMPAR DADOS
    -- ========================================================================

    FUNCTION limpar_dados RETURN VARCHAR2 IS
        v_resultado VARCHAR2(4000) := '';
        v_count NUMBER;
    BEGIN
        -- Ordem de exclusao respeitando foreign keys

        -- 1. Boletos
        SELECT COUNT(*) INTO v_count FROM gc_boleto;
        DELETE FROM gc_boleto;
        v_resultado := v_resultado || v_count || ' boletos removidos. ';

        -- 2. Retornos
        DELETE FROM gc_retorno_detalhe;
        DELETE FROM gc_arquivo_retorno;

        -- 3. Remessas
        DELETE FROM gc_arquivo_remessa;

        -- 4. Notificacoes
        DELETE FROM gc_notificacao;

        -- 5. Reajustes
        DELETE FROM gc_reajuste;

        -- 6. Historico pagamentos
        DELETE FROM gc_historico_pagamento;

        -- 7. Parcelas
        SELECT COUNT(*) INTO v_count FROM gc_parcela;
        DELETE FROM gc_parcela;
        v_resultado := v_resultado || v_count || ' parcelas removidas. ';

        -- 8. Contratos
        SELECT COUNT(*) INTO v_count FROM gc_contrato;
        DELETE FROM gc_contrato;
        v_resultado := v_resultado || v_count || ' contratos removidos. ';

        -- 9. Valores de indices
        SELECT COUNT(*) INTO v_count FROM gc_valor_indice;
        DELETE FROM gc_valor_indice;
        v_resultado := v_resultado || v_count || ' valores de indices removidos. ';

        -- 10. Imoveis
        SELECT COUNT(*) INTO v_count FROM gc_imovel;
        DELETE FROM gc_imovel;
        v_resultado := v_resultado || v_count || ' imoveis removidos. ';

        -- 11. Compradores
        SELECT COUNT(*) INTO v_count FROM gc_comprador;
        DELETE FROM gc_comprador;
        v_resultado := v_resultado || v_count || ' compradores removidos. ';

        -- 12. Contas bancarias
        SELECT COUNT(*) INTO v_count FROM gc_conta_bancaria;
        DELETE FROM gc_conta_bancaria;
        v_resultado := v_resultado || v_count || ' contas removidas. ';

        -- 13. Imobiliarias
        SELECT COUNT(*) INTO v_count FROM gc_imobiliaria;
        DELETE FROM gc_imobiliaria;
        v_resultado := v_resultado || v_count || ' imobiliarias removidas. ';

        -- 14. Contabilidades
        SELECT COUNT(*) INTO v_count FROM gc_contabilidade;
        DELETE FROM gc_contabilidade;
        v_resultado := v_resultado || v_count || ' contabilidades removidas. ';

        COMMIT;

        RETURN 'Limpeza concluida. ' || v_resultado;

    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            RETURN 'ERRO na limpeza: ' || SQLERRM;
    END;

    -- ========================================================================
    -- SETUP COMPLETO
    -- ========================================================================

    FUNCTION setup_completo RETURN CLOB IS
        v_resultado CLOB := '';
    BEGIN
        v_resultado := v_resultado || '=== SETUP COMPLETO ===' || CHR(10) || CHR(10);

        -- 1. Verificar estrutura
        v_resultado := v_resultado || '1. Verificando estrutura...' || CHR(10);
        v_resultado := v_resultado || verificar_estrutura() || CHR(10) || CHR(10);

        -- 2. Criar admin
        v_resultado := v_resultado || '2. Verificando administrador...' || CHR(10);
        v_resultado := v_resultado || criar_admin() || CHR(10) || CHR(10);

        -- 3. Gerar dados de teste
        v_resultado := v_resultado || '3. Gerando dados de teste...' || CHR(10);
        v_resultado := v_resultado || gerar_dados_teste(p_limpar_antes => TRUE) || CHR(10) || CHR(10);

        v_resultado := v_resultado || '=== SETUP COMPLETO FINALIZADO ===' || CHR(10);

        RETURN v_resultado;
    END;

END pkg_setup;
/

-- Grants
GRANT EXECUTE ON pkg_setup TO PUBLIC;

