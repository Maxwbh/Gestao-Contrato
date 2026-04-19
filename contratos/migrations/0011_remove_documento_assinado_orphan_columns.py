# Removes orphaned columns that existed in production PostgreSQL but have no
# corresponding field in the Django model. These columns were left behind by
# a previous migration that was never applied via Django's migration framework.
# The NOT NULL constraint on documento_assinado_content_type was causing
# IntegrityError whenever a new Contrato row was inserted.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0010_indicereajuste_numero_indice"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'contratos_contrato'
                          AND column_name = 'documento_assinado_content_type'
                    ) THEN
                        ALTER TABLE contratos_contrato
                            DROP COLUMN documento_assinado_content_type;
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'contratos_contrato'
                          AND column_name = 'documento_assinado_object_id'
                    ) THEN
                        ALTER TABLE contratos_contrato
                            DROP COLUMN documento_assinado_object_id;
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'contratos_contrato'
                          AND column_name = 'documento_assinado'
                    ) THEN
                        ALTER TABLE contratos_contrato
                            DROP COLUMN documento_assinado;
                    END IF;
                END
                $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
