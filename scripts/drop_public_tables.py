#!/usr/bin/env python
"""
Script para excluir todas as tabelas do schema public no Supabase.
CUIDADO: Isso apagará TODOS os dados no schema public!

Uso:
    python scripts/drop_public_tables.py

Desenvolvedor: Maxwell da Silva Oliveira
"""
import os
import psycopg2
from urllib.parse import urlparse, unquote

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print('ERRO: DATABASE_URL nao definida')
    exit(1)

result = urlparse(database_url)
password = unquote(result.password) if result.password else None

conn = psycopg2.connect(
    host=result.hostname,
    port=result.port or 5432,
    database=result.path[1:],
    user=result.username,
    password=password
)
conn.autocommit = True
cursor = conn.cursor()

print('=' * 60)
print('EXCLUINDO TODAS AS TABELAS DO SCHEMA PUBLIC')
print('=' * 60)

# Listar todas as tabelas no schema public
cursor.execute("""
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
""")
tables = cursor.fetchall()

if not tables:
    print('Nenhuma tabela encontrada no schema public.')
else:
    print(f'Encontradas {len(tables)} tabelas:')
    for table in tables:
        print(f'  - {table[0]}')

    print('')
    print('Excluindo tabelas...')

    # Desabilitar verificação de FK temporariamente
    cursor.execute("SET session_replication_role = 'replica'")

    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f'DROP TABLE IF EXISTS public."{table_name}" CASCADE')
            print(f'  [OK] {table_name}')
        except Exception as e:
            print(f'  [ERRO] {table_name}: {e}')

    # Reabilitar verificação de FK
    cursor.execute("SET session_replication_role = 'origin'")

    print('')
    print('Todas as tabelas do schema public foram excluidas.')

cursor.close()
conn.close()

print('=' * 60)
print('CONCLUIDO')
print('=' * 60)
