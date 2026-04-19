"""
Data migration: seed ParametroSistema from current .env values.

Lê os valores atuais do .env via decouple.config() no momento em que
a migration é executada, preservando a configuração existente.
Usa get_or_create para ser idempotente (seguro para re-execução).
"""
from django.db import migrations

# (chave, grupo, tipo, default, descricao)
PARAMETROS = [
    # ── E-mail SMTP ──────────────────────────────────────────────────────────
    ('EMAIL_BACKEND',    'email', 'str',    'django.core.mail.backends.console.EmailBackend',
     'Backend Django de e-mail. Em produção: django.core.mail.backends.smtp.EmailBackend'),
    ('EMAIL_HOST',       'email', 'str',    'localhost',
     'Servidor SMTP. Ex.: smtp.zoho.com, smtp.gmail.com'),
    ('EMAIL_PORT',       'email', 'int',    '587',
     'Porta SMTP. 587 para TLS, 465 para SSL'),
    ('EMAIL_USE_TLS',    'email', 'bool',   'True',
     'Ativar STARTTLS (porta 587). Mutuamente exclusivo com EMAIL_USE_SSL'),
    ('EMAIL_USE_SSL',    'email', 'bool',   'False',
     'Ativar SSL nativo (porta 465). Mutuamente exclusivo com EMAIL_USE_TLS'),
    ('EMAIL_HOST_USER',  'email', 'str',    '',
     'Usuário SMTP (geralmente o endereço de e-mail remetente)'),
    ('EMAIL_HOST_PASSWORD', 'email', 'secret', '',
     'Senha SMTP ou senha de aplicativo'),
    ('DEFAULT_FROM_EMAIL', 'email', 'str',  'noreply@gestaocontrato.com.br',
     'Endereço remetente padrão para todos os e-mails do sistema'),
    ('EMAIL_TIMEOUT',    'email', 'int',    '10',
     'Timeout de conexão TCP com o servidor SMTP (segundos)'),

    # ── Twilio ───────────────────────────────────────────────────────────────
    ('TWILIO_ACCOUNT_SID',        'twilio', 'str',    '',
     'Account SID da conta Twilio'),
    ('TWILIO_AUTH_TOKEN',         'twilio', 'secret', '',
     'Auth Token da conta Twilio'),
    ('TWILIO_PHONE_NUMBER',       'twilio', 'str',    '',
     'Número Twilio para SMS (E.164, ex.: +15551234567)'),
    ('TWILIO_WHATSAPP_NUMBER',    'twilio', 'str',    '',
     'Número Twilio para WhatsApp (ex.: whatsapp:+15551234567)'),
    ('TWILIO_STATUS_CALLBACK_URL','twilio', 'str',    '',
     'URL de webhook para callbacks de status Twilio'),

    # ── Bounce / IMAP ────────────────────────────────────────────────────────
    ('BOUNCE_EMAIL_ADDRESS', 'imap', 'str',    '',
     'Endereço de e-mail que recebe os bounces'),
    ('BOUNCE_IMAP_HOST',     'imap', 'str',    'imap.zoho.com',
     'Servidor IMAP para leitura de bounces'),
    ('BOUNCE_IMAP_PORT',     'imap', 'int',    '993',
     'Porta IMAP (993 = SSL)'),
    ('BOUNCE_IMAP_USER',     'imap', 'str',    '',
     'Usuário IMAP'),
    ('BOUNCE_IMAP_PASSWORD', 'imap', 'secret', '',
     'Senha IMAP'),
    ('BOUNCE_IMAP_FOLDER',   'imap', 'str',    'INBOX',
     'Pasta IMAP monitorada'),

    # ── Modo de Teste ────────────────────────────────────────────────────────
    ('TEST_MODE',            'teste', 'bool',  'False',
     'Redireciona todos os envios para destinatários de teste. Nunca True em produção'),
    ('TEST_RECIPIENT_EMAIL', 'teste', 'str',   'receber@msbrasil.inf.br',
     'E-mail de destino em modo de teste'),
    ('TEST_RECIPIENT_PHONE', 'teste', 'str',   '+5531993257479',
     'Telefone de destino em modo de teste (E.164)'),

    # ── Notificações ─────────────────────────────────────────────────────────
    ('NOTIFICACAO_DIAS_ANTECEDENCIA',  'notificacao', 'int', '5',
     'Dias de antecedência para notificar vencimento próximo'),
    ('NOTIFICACAO_DIAS_INADIMPLENCIA', 'notificacao', 'int', '3',
     'Dias após vencimento para alertar inadimplência'),

    # ── Tarefas Agendadas ────────────────────────────────────────────────────
    ('TASK_TOKEN', 'tarefa', 'secret', '',
     'Token Bearer para autenticar chamadas à API /api/tasks/run-all/'),

    # ── BRCobrança ───────────────────────────────────────────────────────────
    ('BRCOBRANCA_URL',           'brcobranca', 'str', 'http://localhost:9292',
     'URL base da API BRCobrança (docker run -p 9292:9292 kivanio/brcobranca)'),
    ('BRCOBRANCA_TIMEOUT',       'brcobranca', 'int', '30',
     'Timeout para chamadas à API BRCobrança (segundos)'),
    ('BRCOBRANCA_MAX_TENTATIVAS','brcobranca', 'int', '3',
     'Número máximo de tentativas em caso de falha'),
    ('BRCOBRANCA_DELAY_INICIAL', 'brcobranca', 'int', '2',
     'Delay inicial de retry em segundos (dobra a cada tentativa)'),

    # ── Portal do Comprador ──────────────────────────────────────────────────
    ('PORTAL_EMAIL_VERIFICACAO', 'portal', 'bool', 'False',
     'Exige confirmação de e-mail após cadastro no portal (True = envia link)'),

    # ── Aplicação ────────────────────────────────────────────────────────────
    ('SITE_URL', 'aplicacao', 'str', 'http://localhost:8000',
     'URL pública do site sem barra final. Usada em links de e-mails'),

    # ── APIs BCB ─────────────────────────────────────────────────────────────
    ('BCBAPI_URL',    'bcb', 'str', 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados',
     'URL template da API de séries temporais do Banco Central'),
    ('IPCA_SERIE_ID', 'bcb', 'str', '433',
     'Código da série IPCA no BCB'),
    ('IGPM_SERIE_ID', 'bcb', 'str', '189',
     'Código da série IGP-M no BCB'),
    ('SELIC_SERIE_ID','bcb', 'str', '432',
     'Código da série SELIC no BCB'),
]


def seed_parametros(apps, schema_editor):
    try:
        from decouple import config as env_config
    except ImportError:
        import os
        def env_config(key, default=''):
            return os.environ.get(key, default)

    ParametroSistema = apps.get_model('core', 'ParametroSistema')

    for chave, grupo, tipo, default, descricao in PARAMETROS:
        valor = str(env_config(chave, default=default))
        ParametroSistema.objects.get_or_create(
            chave=chave,
            defaults={
                'valor': valor,
                'tipo': tipo,
                'grupo': grupo,
                'descricao': descricao,
            },
        )


def remove_parametros(apps, schema_editor):
    ParametroSistema = apps.get_model('core', 'ParametroSistema')
    chaves = [p[0] for p in PARAMETROS]
    ParametroSistema.objects.filter(chave__in=chaves).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_parametro_sistema'),
    ]

    operations = [
        migrations.RunPython(seed_parametros, reverse_code=remove_parametros),
    ]
