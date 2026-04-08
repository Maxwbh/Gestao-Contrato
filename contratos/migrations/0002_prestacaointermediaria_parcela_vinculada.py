# Generated migration for contratos app
# Adds parcela_vinculada field to PrestacaoIntermediaria
# This is separate to avoid circular dependency with financeiro app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0001_initial'),
        ('financeiro', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='prestacaointermediaria',
            name='parcela_vinculada',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='intermediaria_origem',
                to='financeiro.parcela',
                verbose_name='Parcela Vinculada'
            ),
        ),
    ]
