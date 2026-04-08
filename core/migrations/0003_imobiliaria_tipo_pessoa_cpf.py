# Adicionado suporte a vendedor Pessoa Física na Imobiliaria.
# G-10: ADEQUAÇÃO AO CONTRATO REAL — Seção 11.2
#
# Mudanças:
#   - ADD COLUMN tipo_pessoa  (varchar 2, default 'PJ', NOT NULL)
#   - ADD COLUMN cpf          (varchar 14, NULL)
#   - cnpj: DROP NOT NULL (torna opcional para PF)
#   - razao_social: DROP NOT NULL (torna opcional para PF)
#
# Tudo com IF NOT EXISTS / IF EXISTS para ser idempotente.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_reajuste_desconto_periodo_referencia"),
    ]

    operations = [
        # tipo_pessoa
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE core_imobiliaria
                            ADD COLUMN IF NOT EXISTS tipo_pessoa varchar(2) NOT NULL DEFAULT 'PJ';
                    """,
                    reverse_sql="ALTER TABLE core_imobiliaria DROP COLUMN IF EXISTS tipo_pessoa;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="imobiliaria",
                    name="tipo_pessoa",
                    field=models.CharField(
                        choices=[("PJ", "Pessoa Jurídica"), ("PF", "Pessoa Física")],
                        default="PJ",
                        max_length=2,
                        verbose_name="Tipo de Pessoa",
                    ),
                ),
            ],
        ),
        # cpf
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE core_imobiliaria ADD COLUMN IF NOT EXISTS cpf varchar(14) NULL;",
                    reverse_sql="ALTER TABLE core_imobiliaria DROP COLUMN IF EXISTS cpf;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="imobiliaria",
                    name="cpf",
                    field=models.CharField(
                        blank=True,
                        null=True,
                        max_length=14,
                        verbose_name="CPF",
                    ),
                ),
            ],
        ),
        # cnpj: tornar nullable no banco (DROP NOT NULL)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE core_imobiliaria ALTER COLUMN cnpj DROP NOT NULL;",
                    reverse_sql="UPDATE core_imobiliaria SET cnpj = 'PENDENTE-' || id::text WHERE cnpj IS NULL; ALTER TABLE core_imobiliaria ALTER COLUMN cnpj SET NOT NULL;",
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="imobiliaria",
                    name="cnpj",
                    field=models.CharField(
                        blank=True,
                        null=True,
                        max_length=20,
                        unique=True,
                        verbose_name="CNPJ",
                    ),
                ),
            ],
        ),
        # razao_social: tornar opcional (DROP NOT NULL)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE core_imobiliaria ALTER COLUMN razao_social DROP NOT NULL;",
                    reverse_sql="UPDATE core_imobiliaria SET razao_social = nome WHERE razao_social IS NULL; ALTER TABLE core_imobiliaria ALTER COLUMN razao_social SET NOT NULL;",
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="imobiliaria",
                    name="razao_social",
                    field=models.CharField(
                        blank=True,
                        max_length=200,
                        verbose_name="Razão Social / Nome Fantasia",
                    ),
                ),
            ],
        ),
    ]
