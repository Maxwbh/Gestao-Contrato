"""
Migration: Adiciona token_publico à Parcela para links públicos de boleto sem autenticação.
"""
import uuid
from django.db import migrations, models


def gerar_tokens(apps, schema_editor):
    Parcela = apps.get_model('financeiro', 'Parcela')
    for p in Parcela.objects.filter(token_publico=None):
        p.token_publico = uuid.uuid4()
        p.save(update_fields=['token_publico'])


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0012_parcela_nosso_numero_formatado_dv'),
    ]

    operations = [
        # Step 1: add nullable (existing rows will be NULL)
        migrations.AddField(
            model_name='parcela',
            name='token_publico',
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                verbose_name='Token Público',
                help_text='Token UUID para link público do boleto (acesso sem senha)',
            ),
        ),
        # Step 2: populate existing rows
        migrations.RunPython(gerar_tokens, migrations.RunPython.noop),
        # Step 3: add unique constraint and make non-nullable
        migrations.AlterField(
            model_name='parcela',
            name='token_publico',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name='Token Público',
                help_text='Token UUID para link público do boleto (acesso sem senha)',
            ),
        ),
    ]
