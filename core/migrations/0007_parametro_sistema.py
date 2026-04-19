from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_add_vertice_poligono'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParametroSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chave', models.CharField(max_length=100, unique=True, verbose_name='Chave')),
                ('valor', models.TextField(blank=True, default='', verbose_name='Valor')),
                ('tipo', models.CharField(
                    choices=[
                        ('str', 'Texto'),
                        ('int', 'Inteiro'),
                        ('bool', 'Booleano'),
                        ('secret', 'Senha / Token'),
                    ],
                    default='str',
                    max_length=10,
                    verbose_name='Tipo',
                )),
                ('grupo', models.CharField(
                    choices=[
                        ('email', 'E-mail SMTP'),
                        ('twilio', 'Twilio (SMS / WhatsApp)'),
                        ('imap', 'Bounce / IMAP'),
                        ('teste', 'Modo de Teste'),
                        ('notificacao', 'Notificações'),
                        ('tarefa', 'Tarefas Agendadas'),
                        ('brcobranca', 'BRCobrança'),
                        ('portal', 'Portal do Comprador'),
                        ('aplicacao', 'Aplicação'),
                        ('bcb', 'APIs BCB'),
                    ],
                    default='aplicacao',
                    max_length=20,
                    verbose_name='Grupo',
                )),
                ('descricao', models.CharField(blank=True, max_length=300, verbose_name='Descrição')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
            ],
            options={
                'verbose_name': 'Parâmetro do Sistema',
                'verbose_name_plural': 'Parâmetros do Sistema',
                'ordering': ['grupo', 'chave'],
            },
        ),
    ]
