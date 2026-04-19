"""
Migration SQL compatibility helpers for PostgreSQL + SQLite.
PostgreSQL supports IF NOT EXISTS / IF EXISTS; SQLite does not.
"""


def add_column_if_not_exists(schema_editor, table, col, col_def):
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.execute(
            f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}'
        )
    else:
        cursor = schema_editor.connection.cursor()
        cursor.execute(f'PRAGMA table_info("{table}")')
        if not any(row[1] == col for row in cursor.fetchall()):
            schema_editor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}')


def drop_column_if_exists(schema_editor, table, col):
    db = schema_editor.connection.vendor
    if db == 'postgresql':
        schema_editor.execute(
            f'ALTER TABLE {table} DROP COLUMN IF EXISTS "{col}"'
        )
    else:
        cursor = schema_editor.connection.cursor()
        cursor.execute(f'PRAGMA table_info("{table}")')
        if any(row[1] == col for row in cursor.fetchall()):
            schema_editor.execute(f'ALTER TABLE {table} DROP COLUMN "{col}"')
