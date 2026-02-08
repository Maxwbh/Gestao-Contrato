#!/usr/bin/env bash
# Build script for Render deployment
# Desenvolvedor: Maxwell da Silva Oliveira

set -o errexit  # exit on error

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Não rodar makemigrations - tabelas já existem no banco
# echo "==> Making migrations..."
# python manage.py makemigrations --no-input

echo "==> Creating schema gestao_contrato if not exists..."
python << 'SCHEMAEOF'
import os
import psycopg2
from urllib.parse import urlparse

# Conectar sem search_path para criar o schema
database_url = os.environ.get('DATABASE_URL')
if database_url:
    result = urlparse(database_url)
    conn = psycopg2.connect(
        host=result.hostname,
        port=result.port or 5432,
        database=result.path[1:],
        user=result.username,
        password=result.password
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Criar schema separado para esta aplicacao
    cursor.execute("CREATE SCHEMA IF NOT EXISTS gestao_contrato")
    print('Schema gestao_contrato criado/verificado.')

    # Verificar se auth_user existe no schema gestao_contrato
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'gestao_contrato'
            AND table_name = 'auth_user'
        )
    """)
    auth_exists = cursor.fetchone()[0]

    if not auth_exists:
        # Verificar se django_migrations existe no schema gestao_contrato
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'gestao_contrato'
                AND table_name = 'django_migrations'
            )
        """)
        migrations_exists = cursor.fetchone()[0]

        if migrations_exists:
            print('ATENCAO: auth_user nao existe mas django_migrations tem registros.')
            print('Limpando django_migrations no schema gestao_contrato...')
            cursor.execute("DELETE FROM gestao_contrato.django_migrations")
            print('Tabela limpa - migracoes serao reaplicadas.')
        else:
            print('Schema novo - tabelas serao criadas.')
    else:
        print('auth_user existe no schema gestao_contrato - OK.')

    cursor.close()
    conn.close()
else:
    print('DATABASE_URL nao definida - usando SQLite local')
SCHEMAEOF

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Applying custom schema changes..."
python manage.py shell << 'SQLEOF'
from django.db import connection

def add_column_if_not_exists(cursor, table, column, column_def):
    """Adiciona coluna se não existir"""
    cursor.execute(f"""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = '{table}' AND column_name = '{column}'
    """)
    if not cursor.fetchone():
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
        print(f"  + Added {table}.{column}")
    else:
        print(f"  - {table}.{column} already exists")

with connection.cursor() as cursor:
    # =========================================================================
    # CAMPOS TIMESTAMP (criado_em, atualizado_em) - TimeStampedModel
    # Também verifica created_at/updated_at para compatibilidade
    # =========================================================================
    print("Adding timestamp columns to all tables...")

    # Lista de tabelas que herdam de TimeStampedModel
    timestamp_tables = [
        'core_contabilidade',
        'core_imobiliaria',
        'core_imovel',
        'core_comprador',
        'core_contabancaria',
        'core_acessousuario',
        'contratos_contrato',
        'contratos_indicereajuste',
        'contratos_prestacaointermediaria',
        'financeiro_parcela',
        'financeiro_reajuste',
        'financeiro_historicopagamento',
        'financeiro_arquivoremessa',
        'financeiro_itemremessa',
        'financeiro_arquivoretorno',
        'financeiro_itemretorno',
        'notificacoes_templatenotificacao',
        'notificacoes_configuracaoemail',
        'notificacoes_configuracaosms',
        'notificacoes_configuracaowhatsapp',
        'notificacoes_notificacao',
        'portal_comprador_acessocomprador',
        'portal_comprador_logacessocomprador',
    ]

    for table in timestamp_tables:
        # Verificar se tabela existe
        cursor.execute(f"""
            SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'
        """)
        if cursor.fetchone():
            # Adicionar colunas em português (usadas pelo Django)
            add_column_if_not_exists(cursor, table, 'criado_em', "TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
            add_column_if_not_exists(cursor, table, 'atualizado_em', "TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

            # REMOVER colunas duplicadas em inglês (created_at, updated_at)
            # Primeiro migrar dados, depois dropar as colunas
            cursor.execute(f"""
                DO $$
                BEGIN
                    -- Se created_at existe, migrar dados para criado_em e DROPAR
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = '{table}' AND column_name = 'created_at'
                    ) THEN
                        -- Migrar dados de created_at para criado_em onde criado_em é NULL
                        UPDATE {table} SET criado_em = created_at WHERE criado_em IS NULL AND created_at IS NOT NULL;
                        -- Dropar a coluna duplicada
                        ALTER TABLE {table} DROP COLUMN created_at;
                        RAISE NOTICE 'Dropped column created_at from {table}';
                    END IF;

                    -- Se updated_at existe, migrar dados para atualizado_em e DROPAR
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = '{table}' AND column_name = 'updated_at'
                    ) THEN
                        -- Migrar dados de updated_at para atualizado_em onde atualizado_em é NULL
                        UPDATE {table} SET atualizado_em = updated_at WHERE atualizado_em IS NULL AND updated_at IS NOT NULL;
                        -- Dropar a coluna duplicada
                        ALTER TABLE {table} DROP COLUMN updated_at;
                        RAISE NOTICE 'Dropped column updated_at from {table}';
                    END IF;
                END $$;
            """)

    print("Timestamp columns checked/added.")
    print("")

    print("Checking core_contabilidade...")
    # CNPJ opcional
    cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'core_contabilidade'
                AND column_name = 'cnpj'
                AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE core_contabilidade ALTER COLUMN cnpj DROP NOT NULL;
                RAISE NOTICE 'CNPJ constraint removed';
            END IF;
        END $$;
    """)

    print("Checking core_imobiliaria...")
    # Endereço estruturado
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'cep', "VARCHAR(9) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'logradouro', "VARCHAR(200) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'numero', "VARCHAR(10) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'complemento', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'bairro', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'cidade', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'estado', "VARCHAR(2) DEFAULT ''")

    # Configurações de Boleto
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'tipo_valor_multa', "VARCHAR(10) DEFAULT 'percentual'")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'percentual_multa_padrao', "DECIMAL(10,2) DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'tipo_valor_juros', "VARCHAR(10) DEFAULT 'percentual'")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'percentual_juros_padrao', "DECIMAL(10,4) DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'dias_para_encargos_padrao', "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'boleto_sem_valor', "BOOLEAN DEFAULT FALSE")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'parcela_no_documento', "BOOLEAN DEFAULT FALSE")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'campo_desconto_abatimento_pdf', "BOOLEAN DEFAULT FALSE")

    # Descontos
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'tipo_valor_desconto', "VARCHAR(10) DEFAULT 'percentual'")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'percentual_desconto_padrao', "DECIMAL(10,2) DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'dias_para_desconto_padrao', "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'tipo_valor_desconto2', "VARCHAR(10) DEFAULT 'percentual'")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'desconto2_padrao', "DECIMAL(10,2) DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'dias_para_desconto2_padrao', "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'tipo_valor_desconto3', "VARCHAR(10) DEFAULT 'percentual'")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'desconto3_padrao', "DECIMAL(10,2) DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'dias_para_desconto3_padrao', "INTEGER DEFAULT 0")

    # Outros campos de boleto
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'instrucao_padrao', "VARCHAR(255) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'tipo_titulo', "VARCHAR(5) DEFAULT 'RC'")
    add_column_if_not_exists(cursor, 'core_imobiliaria', 'aceite', "BOOLEAN DEFAULT FALSE")

    print("Checking core_imovel...")
    # Loteamento opcional
    cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'core_imovel'
                AND column_name = 'loteamento'
                AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE core_imovel ALTER COLUMN loteamento DROP NOT NULL;
                RAISE NOTICE 'loteamento constraint removed';
            END IF;
        END $$;
    """)
    # Endereço estruturado
    add_column_if_not_exists(cursor, 'core_imovel', 'cep', "VARCHAR(9) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'logradouro', "VARCHAR(200) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'numero', "VARCHAR(10) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'complemento', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'bairro', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'cidade', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'estado', "VARCHAR(2) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_imovel', 'endereco', "TEXT DEFAULT ''")
    # Georreferenciamento
    add_column_if_not_exists(cursor, 'core_imovel', 'latitude', "DECIMAL(10,7) NULL")
    add_column_if_not_exists(cursor, 'core_imovel', 'longitude', "DECIMAL(10,7) NULL")
    # Valor
    add_column_if_not_exists(cursor, 'core_imovel', 'valor', "DECIMAL(12,2) NULL")

    print("Checking core_comprador...")
    # Tipo de pessoa
    add_column_if_not_exists(cursor, 'core_comprador', 'tipo_pessoa', "VARCHAR(2) DEFAULT 'PF'")
    # Dados PF
    add_column_if_not_exists(cursor, 'core_comprador', 'cpf', "VARCHAR(14) NULL")
    add_column_if_not_exists(cursor, 'core_comprador', 'rg', "VARCHAR(20) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'data_nascimento', "DATE NULL")
    # Garantir que data_nascimento aceite NULL (pode ter sido criada antes com NOT NULL)
    cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'core_comprador'
                AND column_name = 'data_nascimento'
                AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE core_comprador ALTER COLUMN data_nascimento DROP NOT NULL;
                RAISE NOTICE 'data_nascimento constraint removed';
            END IF;
        END $$;
    """)
    add_column_if_not_exists(cursor, 'core_comprador', 'estado_civil', "VARCHAR(50) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'profissao', "VARCHAR(100) DEFAULT ''")
    # Dados PJ
    add_column_if_not_exists(cursor, 'core_comprador', 'cnpj', "VARCHAR(20) NULL")
    add_column_if_not_exists(cursor, 'core_comprador', 'nome_fantasia', "VARCHAR(200) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'inscricao_estadual', "VARCHAR(20) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'inscricao_municipal', "VARCHAR(20) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'responsavel_legal', "VARCHAR(200) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'responsavel_cpf', "VARCHAR(14) DEFAULT ''")
    # Endereco
    add_column_if_not_exists(cursor, 'core_comprador', 'cep', "VARCHAR(9) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'logradouro', "VARCHAR(200) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'numero', "VARCHAR(10) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'complemento', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'bairro', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'cidade', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'estado', "VARCHAR(2) DEFAULT ''")
    # Contato
    add_column_if_not_exists(cursor, 'core_comprador', 'telefone', "VARCHAR(20) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'celular', "VARCHAR(20) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'email', "VARCHAR(254) DEFAULT ''")
    # Notificacoes
    add_column_if_not_exists(cursor, 'core_comprador', 'notificar_email', "BOOLEAN DEFAULT TRUE")
    add_column_if_not_exists(cursor, 'core_comprador', 'notificar_sms', "BOOLEAN DEFAULT FALSE")
    add_column_if_not_exists(cursor, 'core_comprador', 'notificar_whatsapp', "BOOLEAN DEFAULT TRUE")
    # Conjuge
    add_column_if_not_exists(cursor, 'core_comprador', 'conjuge_nome', "VARCHAR(200) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'conjuge_cpf', "VARCHAR(14) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'conjuge_rg', "VARCHAR(20) DEFAULT ''")
    # Observacoes e status
    add_column_if_not_exists(cursor, 'core_comprador', 'observacoes', "TEXT DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_comprador', 'ativo', "BOOLEAN DEFAULT TRUE")

    # Criar tabela core_contabancaria se não existir
    print("Checking core_contabancaria...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'core_contabancaria'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE core_contabancaria (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                imobiliaria_id INTEGER NOT NULL REFERENCES core_imobiliaria(id) ON DELETE CASCADE,
                banco VARCHAR(3) NOT NULL,
                descricao VARCHAR(150) NOT NULL,
                agencia VARCHAR(10) NOT NULL,
                agencia_dv VARCHAR(2) DEFAULT '',
                conta VARCHAR(15) NOT NULL,
                conta_dv VARCHAR(2) DEFAULT '',
                tipo_conta VARCHAR(20) DEFAULT 'corrente',
                convenio VARCHAR(20) DEFAULT '',
                carteira VARCHAR(10) DEFAULT '',
                variacao_carteira VARCHAR(10) DEFAULT '',
                nosso_numero_inicio BIGINT DEFAULT 1,
                nosso_numero_atual BIGINT DEFAULT 1,
                percentual_multa DECIMAL(10,2) DEFAULT 0,
                percentual_juros DECIMAL(10,4) DEFAULT 0,
                dias_baixa_automatica INTEGER DEFAULT 0,
                instrucao1 VARCHAR(255) DEFAULT '',
                instrucao2 VARCHAR(255) DEFAULT '',
                instrucao3 VARCHAR(255) DEFAULT '',
                conta_padrao BOOLEAN DEFAULT FALSE,
                ativo BOOLEAN DEFAULT TRUE
            )
        """)
        print("  + Created table core_contabancaria")
    else:
        print("  - core_contabancaria already exists")

    # Criar tabela core_acessousuario se não existir
    print("Checking core_acessousuario...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'core_acessousuario'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE core_acessousuario (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                usuario_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                contabilidade_id INTEGER NOT NULL REFERENCES core_contabilidade(id) ON DELETE CASCADE,
                imobiliaria_id INTEGER NOT NULL REFERENCES core_imobiliaria(id) ON DELETE CASCADE,
                pode_editar BOOLEAN DEFAULT TRUE,
                pode_excluir BOOLEAN DEFAULT FALSE,
                ativo BOOLEAN DEFAULT TRUE,
                UNIQUE(usuario_id, contabilidade_id, imobiliaria_id)
            )
        """)
        print("  + Created table core_acessousuario")
    else:
        print("  - core_acessousuario already exists")

    # Criar tabela contratos_indicereajuste se não existir
    print("Checking contratos_indicereajuste...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'contratos_indicereajuste'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE contratos_indicereajuste (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                tipo_indice VARCHAR(10) NOT NULL,
                ano INTEGER NOT NULL,
                mes INTEGER NOT NULL,
                valor DECIMAL(8,4) NOT NULL,
                valor_acumulado_ano DECIMAL(10,4) NULL,
                valor_acumulado_12m DECIMAL(10,4) NULL,
                fonte VARCHAR(100) DEFAULT '',
                data_importacao TIMESTAMP WITH TIME ZONE NULL,
                UNIQUE(tipo_indice, ano, mes)
            )
        """)
        cursor.execute("""
            CREATE INDEX idx_indicereajuste_tipo_ano_mes ON contratos_indicereajuste(tipo_indice, ano, mes)
        """)
        cursor.execute("""
            CREATE INDEX idx_indicereajuste_ano_mes ON contratos_indicereajuste(ano, mes)
        """)
        print("  + Created table contratos_indicereajuste")
    else:
        print("  - contratos_indicereajuste already exists")

    # Atualizar core_contabancaria com campos adicionais
    print("Updating core_contabancaria...")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'principal', "BOOLEAN DEFAULT FALSE")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'modalidade', "VARCHAR(5) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'tipo_pix', "VARCHAR(20) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'chave_pix', "VARCHAR(100) DEFAULT ''")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'cobranca_registrada', "BOOLEAN DEFAULT TRUE")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'prazo_baixa', "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'prazo_protesto', "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'layout_cnab', "VARCHAR(10) DEFAULT 'CNAB_240'")
    add_column_if_not_exists(cursor, 'core_contabancaria', 'numero_remessa_cnab_atual', "INTEGER DEFAULT 0")

    # Adicionar campos de boleto na tabela financeiro_parcela
    print("Checking financeiro_parcela for boleto fields...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'financeiro_parcela'
    """)
    if cursor.fetchone():
        # Campos de identificação do boleto
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'conta_bancaria_id', "INTEGER NULL REFERENCES core_contabancaria(id) ON DELETE SET NULL")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'nosso_numero', "VARCHAR(30) DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'numero_documento', "VARCHAR(25) DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'codigo_barras', "VARCHAR(50) DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'linha_digitavel', "VARCHAR(60) DEFAULT ''")

        # Arquivo PDF e URL
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'boleto_pdf', "VARCHAR(200) DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'boleto_url', "VARCHAR(500) DEFAULT ''")

        # Status e controle
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'status_boleto', "VARCHAR(15) DEFAULT 'NAO_GERADO'")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'data_geracao_boleto', "TIMESTAMP WITH TIME ZONE NULL")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'data_registro_boleto', "TIMESTAMP WITH TIME ZONE NULL")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'data_pagamento_boleto', "TIMESTAMP WITH TIME ZONE NULL")

        # Valores
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'valor_boleto', "DECIMAL(12,2) NULL")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'valor_pago_boleto', "DECIMAL(12,2) NULL")

        # Dados de retorno bancário
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'banco_pagador', "VARCHAR(10) DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'agencia_pagadora', "VARCHAR(10) DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'motivo_rejeicao', "VARCHAR(255) DEFAULT ''")

        # PIX (boleto híbrido)
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'pix_copia_cola', "TEXT DEFAULT ''")
        add_column_if_not_exists(cursor, 'financeiro_parcela', 'pix_qrcode', "TEXT DEFAULT ''")

        # Criar índices para boleto
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_parcela_status_boleto') THEN
                    CREATE INDEX idx_parcela_status_boleto ON financeiro_parcela(status_boleto);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_parcela_nosso_numero') THEN
                    CREATE INDEX idx_parcela_nosso_numero ON financeiro_parcela(nosso_numero);
                END IF;
            END $$;
        """)
        print("  + Boleto fields added/verified")
    else:
        print("  - financeiro_parcela table not found (will be created by migrations)")

    # Atualizar tabela notificacoes_templatenotificacao com novos campos
    print("Checking notificacoes_templatenotificacao...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'notificacoes_templatenotificacao'
    """)
    if cursor.fetchone():
        add_column_if_not_exists(cursor, 'notificacoes_templatenotificacao', 'codigo', "VARCHAR(30) DEFAULT 'CUSTOM'")
        add_column_if_not_exists(cursor, 'notificacoes_templatenotificacao', 'corpo_html', "TEXT DEFAULT ''")
        add_column_if_not_exists(cursor, 'notificacoes_templatenotificacao', 'imobiliaria_id', "INTEGER NULL REFERENCES core_imobiliaria(id) ON DELETE CASCADE")
        print("  + Template fields added/verified")
    else:
        print("  - notificacoes_templatenotificacao table not found (will be created by migrations)")

    # =========================================================================
    # CNAB - TABELAS DE REMESSA E RETORNO
    # =========================================================================

    # Criar tabela financeiro_arquivoremessa
    print("Checking financeiro_arquivoremessa...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'financeiro_arquivoremessa'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE financeiro_arquivoremessa (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                conta_bancaria_id INTEGER NOT NULL REFERENCES core_contabancaria(id) ON DELETE RESTRICT,
                numero_remessa INTEGER NOT NULL,
                layout VARCHAR(10) DEFAULT 'CNAB_240',
                arquivo VARCHAR(200) DEFAULT '',
                nome_arquivo VARCHAR(100) NOT NULL,
                status VARCHAR(15) DEFAULT 'GERADO',
                data_geracao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                data_envio TIMESTAMP WITH TIME ZONE NULL,
                quantidade_boletos INTEGER DEFAULT 0,
                valor_total DECIMAL(14,2) DEFAULT 0,
                observacoes TEXT DEFAULT '',
                erro_mensagem TEXT DEFAULT '',
                UNIQUE(conta_bancaria_id, numero_remessa)
            )
        """)
        cursor.execute("""
            CREATE INDEX idx_remessa_conta_numero ON financeiro_arquivoremessa(conta_bancaria_id, numero_remessa);
            CREATE INDEX idx_remessa_status ON financeiro_arquivoremessa(status);
            CREATE INDEX idx_remessa_data_geracao ON financeiro_arquivoremessa(data_geracao);
        """)
        print("  + Created table financeiro_arquivoremessa")
    else:
        print("  - financeiro_arquivoremessa already exists")

    # Criar tabela financeiro_itemremessa
    print("Checking financeiro_itemremessa...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'financeiro_itemremessa'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE financeiro_itemremessa (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                arquivo_remessa_id INTEGER NOT NULL REFERENCES financeiro_arquivoremessa(id) ON DELETE CASCADE,
                parcela_id INTEGER NOT NULL REFERENCES financeiro_parcela(id) ON DELETE RESTRICT,
                nosso_numero VARCHAR(30) NOT NULL,
                valor DECIMAL(12,2) NOT NULL,
                data_vencimento DATE NOT NULL,
                processado BOOLEAN DEFAULT FALSE,
                codigo_ocorrencia VARCHAR(10) DEFAULT '',
                descricao_ocorrencia VARCHAR(255) DEFAULT '',
                UNIQUE(arquivo_remessa_id, parcela_id)
            )
        """)
        print("  + Created table financeiro_itemremessa")
    else:
        print("  - financeiro_itemremessa already exists")

    # Criar tabela financeiro_arquivoretorno
    print("Checking financeiro_arquivoretorno...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'financeiro_arquivoretorno'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE financeiro_arquivoretorno (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                conta_bancaria_id INTEGER NOT NULL REFERENCES core_contabancaria(id) ON DELETE RESTRICT,
                arquivo VARCHAR(200) DEFAULT '',
                nome_arquivo VARCHAR(100) NOT NULL,
                layout VARCHAR(10) DEFAULT 'CNAB_240',
                status VARCHAR(20) DEFAULT 'PENDENTE',
                data_upload TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                data_processamento TIMESTAMP WITH TIME ZONE NULL,
                processado_por_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
                total_registros INTEGER DEFAULT 0,
                registros_processados INTEGER DEFAULT 0,
                registros_erro INTEGER DEFAULT 0,
                valor_total_pago DECIMAL(14,2) DEFAULT 0,
                observacoes TEXT DEFAULT '',
                erro_mensagem TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE INDEX idx_retorno_conta ON financeiro_arquivoretorno(conta_bancaria_id);
            CREATE INDEX idx_retorno_status ON financeiro_arquivoretorno(status);
            CREATE INDEX idx_retorno_data_upload ON financeiro_arquivoretorno(data_upload);
        """)
        print("  + Created table financeiro_arquivoretorno")
    else:
        print("  - financeiro_arquivoretorno already exists")

    # Criar tabela financeiro_itemretorno
    print("Checking financeiro_itemretorno...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'financeiro_itemretorno'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE financeiro_itemretorno (
                id SERIAL PRIMARY KEY,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                arquivo_retorno_id INTEGER NOT NULL REFERENCES financeiro_arquivoretorno(id) ON DELETE CASCADE,
                parcela_id INTEGER NULL REFERENCES financeiro_parcela(id) ON DELETE SET NULL,
                nosso_numero VARCHAR(30) NOT NULL,
                numero_documento VARCHAR(25) DEFAULT '',
                codigo_ocorrencia VARCHAR(10) NOT NULL,
                descricao_ocorrencia VARCHAR(255) DEFAULT '',
                tipo_ocorrencia VARCHAR(20) DEFAULT 'OUTROS',
                valor_titulo DECIMAL(12,2) NULL,
                valor_pago DECIMAL(12,2) NULL,
                valor_juros DECIMAL(12,2) NULL,
                valor_multa DECIMAL(12,2) NULL,
                valor_desconto DECIMAL(12,2) NULL,
                valor_tarifa DECIMAL(12,2) NULL,
                data_ocorrencia DATE NULL,
                data_credito DATE NULL,
                processado BOOLEAN DEFAULT FALSE,
                erro_processamento TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE INDEX idx_itemretorno_nosso_numero ON financeiro_itemretorno(nosso_numero);
            CREATE INDEX idx_itemretorno_codigo ON financeiro_itemretorno(codigo_ocorrencia);
            CREATE INDEX idx_itemretorno_tipo ON financeiro_itemretorno(tipo_ocorrencia);
        """)
        print("  + Created table financeiro_itemretorno")
    else:
        print("  - financeiro_itemretorno already exists")

    print("Schema changes applied successfully!")

    # =========================================================================
    # CAMPOS DE CONFIGURACAO DE BOLETO NO CONTRATO
    # =========================================================================
    print("Checking contratos_contrato for boleto config fields...")
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'contratos_contrato'
    """)
    if cursor.fetchone():
        # Usar configurações da imobiliária ou personalizadas
        add_column_if_not_exists(cursor, 'contratos_contrato', 'usar_config_boleto_imobiliaria', "BOOLEAN DEFAULT TRUE")

        # Conta bancária padrão para este contrato
        add_column_if_not_exists(cursor, 'contratos_contrato', 'conta_bancaria_padrao_id', "INTEGER NULL REFERENCES core_contabancaria(id) ON DELETE SET NULL")

        # Configurações de Multa
        add_column_if_not_exists(cursor, 'contratos_contrato', 'tipo_valor_multa', "VARCHAR(10) DEFAULT 'PERCENTUAL'")
        add_column_if_not_exists(cursor, 'contratos_contrato', 'valor_multa_boleto', "DECIMAL(10,2) DEFAULT 0")

        # Configurações de Juros
        add_column_if_not_exists(cursor, 'contratos_contrato', 'tipo_valor_juros', "VARCHAR(10) DEFAULT 'PERCENTUAL'")
        add_column_if_not_exists(cursor, 'contratos_contrato', 'valor_juros_boleto', "DECIMAL(10,4) DEFAULT 0")

        # Dias sem encargos
        add_column_if_not_exists(cursor, 'contratos_contrato', 'dias_carencia_boleto', "INTEGER DEFAULT 0")

        # Desconto
        add_column_if_not_exists(cursor, 'contratos_contrato', 'tipo_valor_desconto', "VARCHAR(10) DEFAULT 'PERCENTUAL'")
        add_column_if_not_exists(cursor, 'contratos_contrato', 'valor_desconto_boleto', "DECIMAL(10,2) DEFAULT 0")
        add_column_if_not_exists(cursor, 'contratos_contrato', 'dias_desconto_boleto', "INTEGER DEFAULT 0")

        # Instruções personalizadas
        add_column_if_not_exists(cursor, 'contratos_contrato', 'instrucao_boleto_1', "VARCHAR(255) DEFAULT ''")
        add_column_if_not_exists(cursor, 'contratos_contrato', 'instrucao_boleto_2', "VARCHAR(255) DEFAULT ''")
        add_column_if_not_exists(cursor, 'contratos_contrato', 'instrucao_boleto_3', "VARCHAR(255) DEFAULT ''")

        # Criar índice para conta bancária
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_contrato_conta_bancaria') THEN
                    CREATE INDEX idx_contrato_conta_bancaria ON contratos_contrato(conta_bancaria_padrao_id);
                END IF;
            END $$;
        """)
        print("  + Contrato boleto config fields added/verified")
    else:
        print("  - contratos_contrato table not found (will be created by migrations)")

    print("All schema changes applied successfully!")
SQLEOF

echo "==> Creating default email templates..."
python manage.py shell << 'TEMPLATEEOF'
try:
    from notificacoes.boleto_notificacao import criar_templates_padrao
    count = criar_templates_padrao()
    print(f"Templates criados: {count}")
except Exception as e:
    print(f"Aviso: Nao foi possivel criar templates padrao: {e}")
TEMPLATEEOF

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Creating superuser (if not exists)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()

# Criar usuario principal: maxwbh / a (Administrador)
if not User.objects.filter(username='maxwbh').exists():
    user = User.objects.create_superuser(
        username='maxwbh',
        email='maxwbh@gmail.com',
        password='a',
        first_name='Maxwell',
        last_name='Oliveira'
    )
    print('Superuser criado: maxwbh / a (Administrador)')
else:
    print('Superuser maxwbh ja existe')

# Manter usuario admin como backup
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@gestaocontrato.com', 'admin123')
    print('Superuser backup criado: admin / admin123')
else:
    print('Superuser admin ja existe')
EOF

echo "==> Checking if test data needs to be generated..."
python manage.py shell << 'TESTDATAEOF'
from core.models import Contabilidade, Imobiliaria

# Verificar se ja existe dados (primeira execucao)
if not Contabilidade.objects.exists() and not Imobiliaria.objects.exists():
    print('Banco vazio - gerando dados de teste na primeira execucao...')
    # Importar e executar comando de dados de teste
    from django.core.management import call_command
    try:
        call_command('gerar_dados_teste')
        print('Dados de teste gerados com sucesso!')
    except Exception as e:
        print(f'Aviso: Erro ao gerar dados de teste: {e}')
else:
    print('Dados ja existem - pulando geracao de dados de teste')
TESTDATAEOF

echo "==> Build completed successfully!"
