# Generated migration for portal_comprador app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcessoComprador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('ultimo_acesso', models.DateTimeField(blank=True, null=True, verbose_name='Último Acesso')),
                ('email_verificado', models.BooleanField(default=False, verbose_name='E-mail Verificado')),
                ('token_verificacao', models.CharField(blank=True, max_length=100, null=True, verbose_name='Token de Verificação')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('comprador', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='acesso_portal',
                    to='core.comprador',
                    verbose_name='Comprador'
                )),
                ('usuario', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='acesso_comprador',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuário'
                )),
            ],
            options={
                'verbose_name': 'Acesso do Comprador',
                'verbose_name_plural': 'Acessos dos Compradores',
            },
        ),
        migrations.CreateModel(
            name='LogAcessoComprador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_acesso', models.DateTimeField(auto_now_add=True, verbose_name='Data de Acesso')),
                ('ip_acesso', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP de Acesso')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('pagina_acessada', models.CharField(blank=True, max_length=255, verbose_name='Página Acessada')),
                ('acesso_comprador', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs_acesso',
                    to='portal_comprador.acessocomprador',
                    verbose_name='Acesso do Comprador'
                )),
            ],
            options={
                'verbose_name': 'Log de Acesso',
                'verbose_name_plural': 'Logs de Acesso',
                'ordering': ['-data_acesso'],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name='acessocomprador',
            index=models.Index(fields=['comprador'], name='portal_c_comprad_idx'),
        ),
        migrations.AddIndex(
            model_name='acessocomprador',
            index=models.Index(fields=['usuario'], name='portal_c_usuario_idx'),
        ),
        migrations.AddIndex(
            model_name='logacessocomprador',
            index=models.Index(fields=['acesso_comprador', 'data_acesso'], name='portal_l_acesso_idx'),
        ),
    ]
