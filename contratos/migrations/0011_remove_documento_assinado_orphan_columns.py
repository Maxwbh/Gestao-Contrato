# Removes orphaned columns that existed in production PostgreSQL but have no
# corresponding field in the Django model. These columns were left behind by
# a previous migration that was never applied via Django's migration framework.
# The NOT NULL constraint on documento_assinado_content_type was causing
# IntegrityError whenever a new Contrato row was inserted.

from django.db import migrations
from contratos.migrations._sql_compat import drop_column_if_exists


def drop_orphan_columns(apps, schema_editor):
    for col in ('documento_assinado_content_type', 'documento_assinado_object_id', 'documento_assinado'):
        drop_column_if_exists(schema_editor, 'contratos_contrato', col)


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0010_indicereajuste_numero_indice"),
    ]

    operations = [
        migrations.RunPython(drop_orphan_columns, migrations.RunPython.noop),
    ]
