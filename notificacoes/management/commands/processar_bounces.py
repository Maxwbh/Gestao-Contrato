"""
Management command: processar_bounces

Conecta à caixa de e-mail de bounces via IMAP (SSL), detecta NDR/DSN,
extrai o Message-ID do e-mail original e atualiza Notificacao.status_entrega
para 'bounced'.

Configurar nas env vars do Render (ou .env local):
  BOUNCE_EMAIL_ADDRESS  = bounces@msbrasil.inf.br   (usado no Return-Path dos envios)
  BOUNCE_IMAP_HOST      = imap.zoho.com             (padrão Zoho)
  BOUNCE_IMAP_PORT      = 993                       (IMAP SSL)
  BOUNCE_IMAP_USER      = bounces@msbrasil.inf.br
  BOUNCE_IMAP_PASSWORD  = <senha — definir manualmente no Render>
  BOUNCE_IMAP_FOLDER    = INBOX                     (pasta monitorada)

Agendar via cron-job.org:
  URL:    https://<app>.onrender.com/api/tasks/run-all/  (ou endpoint dedicado)
  Método: POST + Header X-Task-Token
  Agenda: a cada 30 minutos

Alternativamente, chamar direto:
  python manage.py processar_bounces
  python manage.py processar_bounces --dry-run
  python manage.py processar_bounces --limit 50

Desenvolvedor: Maxwell da Silva Oliveira — M&S do Brasil LTDA
"""

import email as _email_lib
import email.policy
import imaplib
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from notificacoes.models import Notificacao

logger = logging.getLogger(__name__)

# Keywords no subject que indicam NDR/bounce (case-insensitive)
_BOUNCE_SUBJECT_KEYWORDS = [
    'delivery status',
    'mail delivery',
    'undelivered',
    'returned mail',
    'delivery failure',
    'delivery notification',
    'failed delivery',
    'mailer-daemon',
    'delivery report',
    'non-delivery',
    'message delivery failure',
    'falha na entrega',
    'mensagem não entregue',
]


class Command(BaseCommand):
    help = (
        'Lê a caixa IMAP de bounces, detecta NDR/DSN e atualiza '
        'Notificacao.status_entrega = "bounced" para e-mails não entregues.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Exibe os bounces detectados sem salvar no banco.',
        )
        parser.add_argument(
            '--limit', type=int, default=200,
            help='Número máximo de e-mails não lidos a processar por execução.',
        )
        parser.add_argument(
            '--folder', type=str, default='',
            help='Pasta IMAP a monitorar (substitui BOUNCE_IMAP_FOLDER).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        host = getattr(settings, 'BOUNCE_IMAP_HOST', 'imap.zoho.com')
        port = int(getattr(settings, 'BOUNCE_IMAP_PORT', 993))
        user = getattr(settings, 'BOUNCE_IMAP_USER', '')
        password = getattr(settings, 'BOUNCE_IMAP_PASSWORD', '')
        folder = options['folder'] or getattr(settings, 'BOUNCE_IMAP_FOLDER', 'INBOX')

        if not user or not password:
            self.stderr.write(
                self.style.ERROR(
                    '[processar_bounces] BOUNCE_IMAP_USER / BOUNCE_IMAP_PASSWORD '
                    'não configurados. Abortando.'
                )
            )
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('[processar_bounces] Modo DRY-RUN — nenhuma alteração será salva.'))

        try:
            mail = imaplib.IMAP4_SSL(host, port)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'[processar_bounces] Falha ao conectar {host}:{port} — {exc}'))
            logger.exception('[processar_bounces] IMAP connection error')
            return

        try:
            mail.login(user, password)
        except imaplib.IMAP4.error as exc:
            self.stderr.write(self.style.ERROR(f'[processar_bounces] Login falhou para {user} — {exc}'))
            mail.logout()
            return

        try:
            status, _ = mail.select(f'"{folder}"')
            if status != 'OK':
                # Tenta sem aspas
                status, _ = mail.select(folder)
            if status != 'OK':
                self.stderr.write(self.style.ERROR(f'[processar_bounces] Pasta "{folder}" não encontrada.'))
                mail.logout()
                return

            _, data = mail.search(None, 'UNSEEN')
            mail_ids = (data[0] or b'').split()

            if not mail_ids:
                self.stdout.write('[processar_bounces] Nenhum e-mail não lido na pasta.')
                mail.logout()
                return

            # Processa os `limit` mais recentes (maiores IDs)
            ids_para_processar = mail_ids[-limit:]
            self.stdout.write(
                f'[processar_bounces] {len(mail_ids)} não lido(s), processando até {len(ids_para_processar)}.'
            )

            processados = 0
            bounces_encontrados = 0
            atualizados = 0

            for mail_id in ids_para_processar:
                try:
                    _, msg_data = mail.fetch(mail_id, '(RFC822)')
                    if not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = _email_lib.message_from_bytes(raw, policy=_email_lib.policy.default)

                    processados += 1

                    if not self._is_bounce(msg):
                        continue

                    bounces_encontrados += 1
                    orig_id = self._extract_original_message_id(msg)

                    if orig_id:
                        if dry_run:
                            self.stdout.write(f'  [DRY-RUN] Bounce: {orig_id}')
                        else:
                            updated = Notificacao.objects.filter(external_id=orig_id).update(
                                status_entrega='bounced',
                                data_confirmacao=timezone.now(),
                            )
                            atualizados += updated
                            logger.info('[Bounce] Message-ID=%s → %d notificacao(s) atualizadas', orig_id, updated)
                            self.stdout.write(
                                self.style.SUCCESS(f'  Bounce: {orig_id} → {updated} registro(s)')
                            )

                    # Marcar como lido para não reprocessar
                    if not dry_run:
                        mail.store(mail_id, '+FLAGS', r'\Seen')

                except Exception as exc:
                    logger.exception('[processar_bounces] Erro ao processar mail_id=%s: %s', mail_id, exc)

            self.stdout.write(
                f'[processar_bounces] Concluído. '
                f'Processados={processados} | Bounces={bounces_encontrados} | Atualizados={atualizados}'
            )

        finally:
            try:
                mail.logout()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Detecção de bounce
    # ------------------------------------------------------------------

    def _is_bounce(self, msg) -> bool:
        """Retorna True se o e-mail for um NDR/DSN/bounce."""
        content_type = msg.get_content_type() or ''

        # Método 1: Content-Type multipart/report (RFC 3462)
        if content_type == 'multipart/report':
            return True

        # Método 2: Parte message/delivery-status (RFC 1894)
        for part in msg.walk():
            if part.get_content_type() == 'message/delivery-status':
                return True

        # Método 3: Subject contém keywords de bounce
        subject = (msg.get('Subject', '') or '').lower()
        if any(kw in subject for kw in _BOUNCE_SUBJECT_KEYWORDS):
            return True

        # Método 4: From é Mailer-Daemon ou MAILER-DAEMON
        sender = (msg.get('From', '') or '').lower()
        if 'mailer-daemon' in sender or 'postmaster' in sender:
            return True

        return False

    # ------------------------------------------------------------------
    # Extração do Message-ID original
    # ------------------------------------------------------------------

    def _extract_original_message_id(self, msg) -> str:
        """
        Extrai o Message-ID do e-mail original embutido no bounce.

        Estratégias (em ordem de confiabilidade):
        1. Parte message/rfc822 — e-mail original completo
        2. Parte message/rfc822-headers — cabeçalhos do original
        3. Cabeçalho References (último item)
        4. Cabeçalho In-Reply-To
        """
        # 1. Percorrer partes MIME
        for part in msg.walk():
            ct = part.get_content_type()

            if ct == 'message/rfc822':
                payload = part.get_payload()
                if isinstance(payload, list) and payload:
                    orig_id = (payload[0].get('Message-ID', '') or '').strip()
                    if orig_id:
                        return orig_id

            elif ct == 'message/rfc822-headers':
                raw_headers = part.get_payload(decode=True) or b''
                try:
                    parsed = _email_lib.message_from_bytes(raw_headers)
                    orig_id = (parsed.get('Message-ID', '') or '').strip()
                    if orig_id:
                        return orig_id
                except Exception:
                    pass

        # 2. Cabeçalho References
        refs = (msg.get('References', '') or '').strip()
        if refs:
            tokens = refs.split()
            for token in reversed(tokens):
                if token.startswith('<') and token.endswith('>'):
                    return token

        # 3. Cabeçalho In-Reply-To
        in_reply = (msg.get('In-Reply-To', '') or '').strip()
        if in_reply:
            return in_reply.split()[0] if in_reply else ''

        return ''
