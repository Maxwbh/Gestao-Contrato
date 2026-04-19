# Gravar em paralelo os campos necessários para conciliação futura de boletos:
# - nosso_numero_formatado: valor completo impresso (convênio+seq+DV) para OFX
# - nosso_numero_dv: dígito verificador isolado para validação
# Vindos dos headers X-Nosso-Numero-Formatado e X-Nosso-Numero-DV (PR#33 da boleto_cnab_api),
# ou do endpoint /api/boleto/data (PR#32) como fallback.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0011_nosso_numero_unico_por_conta"),
    ]

    operations = [
        migrations.AddField(
            model_name="parcela",
            name="nosso_numero_formatado",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Nosso número completo conforme impresso no boleto "
                    "(convênio + sequencial + DV). Usado para conciliação OFX."
                ),
                max_length=30,
                verbose_name="Nosso Número Formatado",
            ),
        ),
        migrations.AddField(
            model_name="parcela",
            name="nosso_numero_dv",
            field=models.CharField(
                blank=True,
                help_text="Dígito verificador do nosso número (calculado pela API / banco).",
                max_length=2,
                verbose_name="DV do Nosso Número",
            ),
        ),
        migrations.AlterField(
            model_name="parcela",
            name="nosso_numero",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Sequencial bruto do nosso número (sem convênio, sem DV). "
                    "Usado para conciliação CNAB."
                ),
                max_length=30,
                verbose_name="Nosso Número",
            ),
        ),
    ]
