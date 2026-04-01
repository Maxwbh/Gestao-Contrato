# G-14: Testemunhas do contrato (4 campos texto/CPF)
# G-15: Prazo para lavratura de escritura (integer, default 90)
#
# Idempotente: ADD COLUMN IF NOT EXISTS em todos os campos.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0008_contrato_tipo_amortizacao"),
    ]

    operations = [
        # testemunha_1_nome
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE contratos_contrato ADD COLUMN IF NOT EXISTS testemunha_1_nome varchar(200) NOT NULL DEFAULT '';",
                    reverse_sql="ALTER TABLE contratos_contrato DROP COLUMN IF EXISTS testemunha_1_nome;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="contrato",
                    name="testemunha_1_nome",
                    field=models.CharField(blank=True, max_length=200, verbose_name="Testemunha 1 — Nome"),
                ),
            ],
        ),
        # testemunha_1_cpf
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE contratos_contrato ADD COLUMN IF NOT EXISTS testemunha_1_cpf varchar(14) NOT NULL DEFAULT '';",
                    reverse_sql="ALTER TABLE contratos_contrato DROP COLUMN IF EXISTS testemunha_1_cpf;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="contrato",
                    name="testemunha_1_cpf",
                    field=models.CharField(blank=True, max_length=14, verbose_name="Testemunha 1 — CPF"),
                ),
            ],
        ),
        # testemunha_2_nome
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE contratos_contrato ADD COLUMN IF NOT EXISTS testemunha_2_nome varchar(200) NOT NULL DEFAULT '';",
                    reverse_sql="ALTER TABLE contratos_contrato DROP COLUMN IF EXISTS testemunha_2_nome;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="contrato",
                    name="testemunha_2_nome",
                    field=models.CharField(blank=True, max_length=200, verbose_name="Testemunha 2 — Nome"),
                ),
            ],
        ),
        # testemunha_2_cpf
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE contratos_contrato ADD COLUMN IF NOT EXISTS testemunha_2_cpf varchar(14) NOT NULL DEFAULT '';",
                    reverse_sql="ALTER TABLE contratos_contrato DROP COLUMN IF EXISTS testemunha_2_cpf;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="contrato",
                    name="testemunha_2_cpf",
                    field=models.CharField(blank=True, max_length=14, verbose_name="Testemunha 2 — CPF"),
                ),
            ],
        ),
        # prazo_escritura_dias
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE contratos_contrato ADD COLUMN IF NOT EXISTS prazo_escritura_dias integer NULL DEFAULT 90;",
                    reverse_sql="ALTER TABLE contratos_contrato DROP COLUMN IF EXISTS prazo_escritura_dias;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="contrato",
                    name="prazo_escritura_dias",
                    field=models.IntegerField(
                        blank=True,
                        null=True,
                        default=90,
                        verbose_name="Prazo para Escritura (dias)",
                    ),
                ),
            ],
        ),
    ]
