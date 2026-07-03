# Generated migration for notificacoes app
# Includes notification models: ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp, Notificacao, TemplateNotificacao
#
# Desenvolvedor: Maxwell da Silva Oliveira
# Email: maxwbh@gmail.com

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        ('financeiro', '0001_initial'),
    ]

    operations = [
        # ConfiguracaoEmail
        migrations.CreateModel(
            name='ConfiguracaoEmail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome da Configuração')),
                ('host', models.CharField(max_length=255, verbose_name='Servidor SMTP')),
                ('porta', models.IntegerField(default=587, verbose_name='Porta')),
                ('usuario', models.CharField(max_length=255, verbose_name='Usuário')),
                ('senha', models.CharField(max_length=255, verbose_name='Senha')),
                ('usar_tls', models.BooleanField(default=True, verbose_name='Usar TLS')),
                ('usar_ssl', models.BooleanField(default=False, verbose_name='Usar SSL')),
                ('email_remetente', models.EmailField(max_length=254, verbose_name='E-mail Remetente')),
                ('nome_remetente', models.CharField(default='Sistema de Gestão de Contratos', max_length=100, verbose_name='Nome do Remetente')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Configuração de E-mail',
                'verbose_name_plural': 'Configurações de E-mail',
            },
        ),

        # ConfiguracaoSMS
        migrations.CreateModel(
            name='ConfiguracaoSMS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome da Configuração')),
                ('provedor', models.CharField(choices=[('TWILIO', 'Twilio'), ('NEXMO', 'Nexmo/Vonage'), ('AWS_SNS', 'AWS SNS')], default='TWILIO', max_length=50, verbose_name='Provedor')),
                ('account_sid', models.CharField(max_length=255, verbose_name='Account SID')),
                ('auth_token', models.CharField(max_length=255, verbose_name='Auth Token')),
                ('numero_remetente', models.CharField(help_text='Número de telefone do remetente (formato internacional)', max_length=20, verbose_name='Número Remetente')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Configuração de SMS',
                'verbose_name_plural': 'Configurações de SMS',
            },
        ),

        # ConfiguracaoWhatsApp
        migrations.CreateModel(
            name='ConfiguracaoWhatsApp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome da Configuração')),
                ('provedor', models.CharField(choices=[('TWILIO', 'Twilio'), ('META', 'Meta (WhatsApp Business API)')], default='TWILIO', max_length=50, verbose_name='Provedor')),
                ('account_sid', models.CharField(max_length=255, verbose_name='Account SID')),
                ('auth_token', models.CharField(max_length=255, verbose_name='Auth Token')),
                ('numero_remetente', models.CharField(help_text='Número de WhatsApp do remetente (formato: whatsapp:+5511999999999)', max_length=20, verbose_name='Número WhatsApp Remetente')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Configuração de WhatsApp',
                'verbose_name_plural': 'Configurações de WhatsApp',
            },
        ),

        # Notificacao
        migrations.CreateModel(
            name='Notificacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('tipo', models.CharField(choices=[('EMAIL', 'E-mail'), ('SMS', 'SMS'), ('WHATSAPP', 'WhatsApp')], max_length=20, verbose_name='Tipo')),
                ('destinatario', models.CharField(help_text='E-mail, telefone ou número WhatsApp do destinatário', max_length=255, verbose_name='Destinatário')),
                ('assunto', models.CharField(blank=True, help_text='Assunto da mensagem (usado em e-mails)', max_length=255, verbose_name='Assunto')),
                ('mensagem', models.TextField(verbose_name='Mensagem')),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('ENVIADA', 'Enviada'), ('ERRO', 'Erro'), ('CANCELADA', 'Cancelada')], default='PENDENTE', max_length=20, verbose_name='Status')),
                ('data_agendamento', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data de Agendamento')),
                ('data_envio', models.DateTimeField(blank=True, null=True, verbose_name='Data de Envio')),
                ('tentativas', models.IntegerField(default=0, verbose_name='Tentativas de Envio')),
                ('erro_mensagem', models.TextField(blank=True, verbose_name='Mensagem de Erro')),
                ('parcela', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notificacoes', to='financeiro.parcela', verbose_name='Parcela')),
            ],
            options={
                'verbose_name': 'Notificação',
                'verbose_name_plural': 'Notificações',
                'ordering': ['-data_agendamento'],
            },
        ),
        migrations.AddIndex(
            model_name='notificacao',
            index=models.Index(fields=['status', 'data_agendamento'], name='notificacoe_status_b79a2b_idx'),
        ),
        migrations.AddIndex(
            model_name='notificacao',
            index=models.Index(fields=['parcela'], name='notificacoe_parcela_f95d9b_idx'),
        ),

        # TemplateNotificacao
        migrations.CreateModel(
            name='TemplateNotificacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome do Template')),
                ('codigo', models.CharField(choices=[('BOLETO_CRIADO', 'Boleto Criado'), ('BOLETO_5_DIAS', 'Boleto - 5 dias para vencer'), ('BOLETO_VENCE_AMANHA', 'Boleto - Vence amanhã'), ('BOLETO_VENCEU_ONTEM', 'Boleto - Venceu ontem'), ('BOLETO_VENCIDO', 'Boleto Vencido'), ('PAGAMENTO_CONFIRMADO', 'Pagamento Confirmado'), ('CONTRATO_CRIADO', 'Contrato Criado'), ('LEMBRETE_PARCELA', 'Lembrete de Parcela'), ('CUSTOM', 'Personalizado')], default='CUSTOM', max_length=30, verbose_name='Tipo do Template')),
                ('tipo', models.CharField(choices=[('EMAIL', 'E-mail'), ('SMS', 'SMS'), ('WHATSAPP', 'WhatsApp')], max_length=20, verbose_name='Canal de Envio')),
                ('assunto', models.CharField(blank=True, help_text='Para e-mails. Suporta TAGs como %%NOMECOMPRADOR%%', max_length=255, verbose_name='Assunto')),
                ('corpo', models.TextField(help_text='Use TAGs como %%NOMECOMPRADOR%%, %%DATAVENCIMENTO%%, etc.', verbose_name='Corpo da Mensagem')),
                ('corpo_html', models.TextField(blank=True, help_text='Versão HTML do e-mail (opcional)', verbose_name='Corpo HTML')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('imobiliaria', models.ForeignKey(blank=True, help_text='Deixe vazio para template global', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='templates_notificacao', to='core.imobiliaria', verbose_name='Imobiliária')),
            ],
            options={
                'verbose_name': 'Template de Notificação',
                'verbose_name_plural': 'Templates de Notificação',
                'ordering': ['codigo', 'nome'],
                'unique_together': {('codigo', 'imobiliaria', 'tipo')},
            },
        ),
    ]
