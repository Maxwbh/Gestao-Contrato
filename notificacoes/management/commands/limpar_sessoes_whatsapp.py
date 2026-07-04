"""
Management command: remove sessões WhatsApp inativas há mais de N minutos.

Uso:
    python manage.py limpar_sessoes_whatsapp           # padrão: 30 min
    python manage.py limpar_sessoes_whatsapp --minutos 60
    python manage.py limpar_sessoes_whatsapp --dry-run  # apenas conta, não apaga
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Remove sessões WhatsApp inativas (updated_at > N minutos).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutos',
            type=int,
            default=30,
            help='Minutos de inatividade para considerar sessão expirada (padrão: 30).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas exibe quantas seriam removidas, sem deletar.',
        )

    def handle(self, *args, **options):
        from notificacoes.models import SessaoConversaWhatsApp

        minutos = options['minutos']
        dry_run = options['dry_run']
        limite = timezone.now() - timedelta(minutes=minutos)

        qs = SessaoConversaWhatsApp.objects.filter(atualizado_em__lt=limite)
        count = qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[dry-run] {count} sessão(ões) seriam removidas (inativas há >{minutos} min).'
                )
            )
            return

        qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f'Removidas {count} sessão(ões) inativas há mais de {minutos} minuto(s).'
            )
        )
