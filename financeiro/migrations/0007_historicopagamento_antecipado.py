from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0006_cnab_tables_idempotent'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicopagamento',
            name='antecipado',
            field=models.BooleanField(
                default=False,
                help_text='Pagamento de antecipação de parcelas com desconto',
                verbose_name='Antecipado',
            ),
        ),
    ]
