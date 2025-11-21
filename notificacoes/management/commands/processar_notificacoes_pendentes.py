"""
Django Management Command para processar notificações pendentes

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA

Uso:
    python manage.py processar_notificacoes_pendentes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from notificacoes.tasks import processar_notificacoes_pendentes


class Command(BaseCommand):
    help = 'Processa e envia notificações pendentes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f'Processando notificações pendentes... [{timezone.now()}]'
        ))

        try:
            resultado = processar_notificacoes_pendentes()

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Processamento concluído!'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Notificações enviadas: {resultado["enviadas"]}'
            ))
            self.stdout.write(self.style.ERROR(
                f'   Erros: {resultado["erros"]}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Erro ao processar notificações: {str(e)}'
            ))
            raise
