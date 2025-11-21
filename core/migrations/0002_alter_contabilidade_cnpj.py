# Generated manually - SQL direto para compatibilidade

from django.db import migrations


class Migration(migrations.Migration):

    initial = True  # Permite rodar sem dependências específicas

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE core_contabilidade ALTER COLUMN cnpj DROP NOT NULL;",
            reverse_sql="ALTER TABLE core_contabilidade ALTER COLUMN cnpj SET NOT NULL;",
        ),
    ]
