"""
Atualiza os modelos Claude do WorkflowIATier: adiciona claude-sonnet-5
(Sonnet atual) aos choices e migra as linhas existentes do legado
claude-sonnet-4-6 (ainda disponível na API, mas a doc recomenda migrar;
mesmo preço de tabela e cutoff de conhecimento mais recente).
"""
from django.db import migrations, models


def _sonnet46_para_sonnet5(apps, schema_editor):
    WorkflowIATier = apps.get_model('core', 'WorkflowIATier')
    WorkflowIATier.objects.filter(modelo='claude-sonnet-4-6').update(
        modelo='claude-sonnet-5')


def _noop(apps, schema_editor):
    # Reverso intencionalmente vazio: claude-sonnet-5 segue válido nos choices.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_contabancaria_bapi_token_cifrado_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflowiatier',
            name='modelo',
            field=models.CharField(
                choices=[
                    ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5'),
                    ('claude-sonnet-5', 'Claude Sonnet 5'),
                    ('claude-opus-4-8', 'Claude Opus 4.8'),
                    ('claude-sonnet-4-6', 'Claude Sonnet 4.6 (legado)'),
                ],
                max_length=60,
                verbose_name='Modelo',
            ),
        ),
        migrations.RunPython(_sonnet46_para_sonnet5, _noop),
    ]
