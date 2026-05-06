from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_parametro_modificado_manualmente'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoteamentoOverlay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('nome_loteamento', models.CharField(db_index=True, max_length=200, verbose_name='Nome do Loteamento', help_text='Deve corresponder exatamente ao campo loteamento dos imóveis.')),
                ('imagem', models.ImageField(upload_to='loteamento/overlays/', verbose_name='Planta Baixa', help_text='Imagem da planta baixa (PNG/JPG). Recomendado: fundo transparente (PNG).')),
                ('lat_sw', models.DecimalField(decimal_places=7, max_digits=10, verbose_name='Latitude SW')),
                ('lng_sw', models.DecimalField(decimal_places=7, max_digits=10, verbose_name='Longitude SW')),
                ('lat_ne', models.DecimalField(decimal_places=7, max_digits=10, verbose_name='Latitude NE')),
                ('lng_ne', models.DecimalField(decimal_places=7, max_digits=10, verbose_name='Longitude NE')),
                ('opacidade', models.FloatField(default=0.7, verbose_name='Opacidade (0–1)', help_text='0 = invisível, 1 = opaco. Padrão: 0.7')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Overlay de Loteamento',
                'verbose_name_plural': 'Overlays de Loteamento',
                'ordering': ['nome_loteamento'],
            },
        ),
    ]
