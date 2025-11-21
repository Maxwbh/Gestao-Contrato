"""
Django Management Command para enviar notificações de vencimento

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA

Uso:
    python manage.py enviar_notificacoes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from notificacoes.tasks import enviar_notificacoes_vencimento


class Command(BaseCommand):
    help = 'Envia notificações de parcelas a vencer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f'Iniciando envio de notificações... [{timezone.now()}]'
        ))

        try:
            notificacoes_criadas = enviar_notificacoes_vencimento()

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Envio concluído!'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Notificações criadas: {notificacoes_criadas}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Erro ao enviar notificações: {str(e)}'
            ))
            raise
