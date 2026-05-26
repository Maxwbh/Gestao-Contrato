from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0012_add_minuta_contrato'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContratoImportacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('arquivo', models.FileField(help_text='PDF ou imagem do contrato', upload_to='importacoes_contrato/%Y/%m/', verbose_name='Arquivo')),
                ('status', models.CharField(choices=[('PENDENTE', 'Aguardando extração'), ('EXTRAINDO', 'Extraindo dados...'), ('REVISAO', 'Aguardando revisão'), ('CONCLUIDO', 'Concluído'), ('ERRO', 'Erro na extração')], default='PENDENTE', max_length=20, verbose_name='Status')),
                ('dados_extraidos', models.JSONField(blank=True, null=True, verbose_name='Dados Extraídos')),
                ('erros_extracao', models.TextField(blank=True, verbose_name='Erros de Extração')),
                ('contrato_criado', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='importacao_origem', to='contratos.contrato', verbose_name='Contrato Criado')),
                ('criado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='importacoes_contrato', to=settings.AUTH_USER_MODEL, verbose_name='Importado por')),
            ],
            options={
                'verbose_name': 'Importação de Contrato',
                'verbose_name_plural': 'Importações de Contratos',
                'ordering': ['-criado_em'],
            },
        ),
    ]
