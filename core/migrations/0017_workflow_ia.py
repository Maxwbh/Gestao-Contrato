from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_log_auditoria_e_bloqueio_credito'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowIA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=100, verbose_name='Nome do Workflow')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
                ('ativo', models.BooleanField(
                    default=False,
                    help_text='Apenas um workflow pode estar ativo. Se nenhum, usa a cascade padrão.',
                    verbose_name='Ativo',
                )),
            ],
            options={
                'verbose_name': 'Workflow de IA',
                'verbose_name_plural': 'Workflows de IA',
                'ordering': ['-ativo', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='WorkflowIATier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modelo', models.CharField(
                    choices=[
                        ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5'),
                        ('claude-sonnet-4-6', 'Claude Sonnet 4.6'),
                        ('claude-opus-4-8', 'Claude Opus 4.8'),
                    ],
                    max_length=60,
                    verbose_name='Modelo',
                )),
                ('ordem', models.PositiveSmallIntegerField(verbose_name='Ordem')),
                ('habilitado', models.BooleanField(default=True, verbose_name='Habilitado')),
                ('workflow', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tiers',
                    to='core.workflowia',
                )),
            ],
            options={
                'verbose_name': 'Tier do Workflow de IA',
                'verbose_name_plural': 'Tiers do Workflow de IA',
                'ordering': ['workflow', 'ordem'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='workflowiatier',
            unique_together={('workflow', 'ordem')},
        ),
        migrations.AddIndex(
            model_name='workflowia',
            index=models.Index(fields=['ativo'], name='core_workfl_ativo_idx'),
        ),
    ]
