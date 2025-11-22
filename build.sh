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

    print("Schema changes applied successfully!")
SQLEOF

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Creating superuser (if not exists)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@gestaocontrato.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
EOF

echo "==> Build completed successfully!"
