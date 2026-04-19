# Adicionado suporte a vendedor Pessoa Física na Imobiliaria.
# G-10: ADEQUAÇÃO AO CONTRATO REAL — Seção 11.2

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_reajuste_desconto_periodo_referencia"),
    ]

    operations = [
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
        migrations.AlterField(
            model_name="imobiliaria",
            name="razao_social",
            field=models.CharField(
                blank=True,
                max_length=200,
                verbose_name="Razão Social / Nome Fantasia",
            ),
        ),
    ]
