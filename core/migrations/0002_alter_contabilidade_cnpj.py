# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contabilidade',
            name='cnpj',
            field=models.CharField(
                blank=True,
                help_text='Opcional. Suporta formato numérico atual e alfanumérico (preparado para 2026)',
                max_length=20,
                null=True,
                unique=True,
                verbose_name='CNPJ'
            ),
        ),
    ]
