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
with connection.cursor() as cursor:
    # Verifica se a coluna cnpj ainda tem NOT NULL e remove
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
                RAISE NOTICE 'CNPJ constraint removed successfully';
            ELSE
                RAISE NOTICE 'CNPJ already nullable or column does not exist';
            END IF;
        END $$;
    """)
    print('Schema changes applied')
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
