"""
Sincroniza parâmetros do .env com a tabela ParametroSistema.

Comportamento padrão:
  - Atualiza apenas registros cujo valor no .env é não-vazio e diferente do default.
  - NUNCA sobrescreve registros com modificado_manualmente=True (alterados pelo admin).
  - Use --force para forçar a sobrescrita mesmo de valores alterados manualmente.

Opções:
  --dry-run   Mostra o que seria alterado sem gravar.
  --force     Sobrescreve todos os registros, incluindo os alterados manualmente.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

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
     'Exige confirmação de e-mail após cadastro no portal'),

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


def _load_env_config():
    try:
        from decouple import config as env_config
        return env_config
    except ImportError:
        import os
        return lambda key, default='': os.environ.get(key, default)


class Command(BaseCommand):
    help = 'Sincroniza parâmetros do arquivo .env com a tabela ParametroSistema no banco.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Exibe o que seria alterado sem gravar no banco.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sobrescreve todos os registros com o valor do .env, '
                 'inclusive os alterados manualmente pelo admin.',
        )

    def handle(self, *args, **options):
        from core.models import ParametroSistema
        from core.parametros import invalidar_cache

        dry_run = options['dry_run']
        force = options['force']
        env_config = _load_env_config()

        atualizados = []
        ignorados = []
        criados = []

        with transaction.atomic():
            for chave, grupo, tipo, default, descricao in PARAMETROS:
                valor_env = str(env_config(chave, default=default))
                tem_valor_env = valor_env.strip() and valor_env != default

                obj, created = ParametroSistema.objects.get_or_create(
                    chave=chave,
                    defaults={
                        'valor': valor_env,
                        'tipo': tipo,
                        'grupo': grupo,
                        'descricao': descricao,
                    },
                )

                if created:
                    criados.append((chave, valor_env if tipo != 'secret' else '••••••••'))
                    continue

                # Valores alterados manualmente pelo admin têm prioridade
                if obj.modificado_manualmente and not force:
                    ignorados.append((chave, 'alterado manualmente — use --force para sobrescrever'))
                    continue

                deve_atualizar = force or tem_valor_env
                if deve_atualizar and obj.valor != valor_env:
                    valor_exibir = valor_env if tipo != 'secret' else '••••••••'
                    valor_anterior = obj.valor if tipo != 'secret' else '••••••••'
                    atualizados.append((chave, valor_anterior, valor_exibir))
                    if not dry_run:
                        obj.valor = valor_env
                        obj.modificado_manualmente = False
                        obj.save(update_fields=['valor', 'modificado_manualmente'])
                else:
                    ignorados.append((chave, ''))

            if dry_run:
                transaction.set_rollback(True)

        if criados:
            self.stdout.write(self.style.SUCCESS(f'\nCriados ({len(criados)}):'))
            for chave, val in criados:
                self.stdout.write(f'  + {chave} = {val}')

        if atualizados:
            label = '[DRY-RUN] Seriam atualizados' if dry_run else 'Atualizados'
            self.stdout.write(self.style.WARNING(f'\n{label} ({len(atualizados)}):'))
            for chave, antes, depois in atualizados:
                self.stdout.write(f'  ~ {chave}: "{antes}" → "{depois}"')

        protegidos = [(c, m) for c, m in ignorados if m]
        sem_mudanca = [(c, m) for c, m in ignorados if not m]

        if protegidos:
            self.stdout.write(self.style.ERROR(f'\nProtegidos — alterados manualmente ({len(protegidos)}):'))
            for chave, motivo in protegidos:
                self.stdout.write(f'  ! {chave}: {motivo}')

        if sem_mudanca:
            self.stdout.write(self.style.HTTP_INFO(
                f'\nSem alteração (valor igual ou .env com default): {len(sem_mudanca)}'
            ))

        if not dry_run and atualizados:
            invalidar_cache()
            self.stdout.write(self.style.SUCCESS('\nCache de parâmetros invalidado.'))

        total = len(criados) + len(atualizados)
        sufixo = ' (dry-run — nenhuma alteração gravada)' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\nConcluído: {total} parâmetro(s) processado(s){sufixo}.'
        ))
