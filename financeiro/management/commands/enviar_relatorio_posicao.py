"""
Management command para enviar o relatório de posição de contratos manualmente.

Uso:
    python manage.py enviar_relatorio_posicao
    python manage.py enviar_relatorio_posicao --formato pdf
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '34.5.2 — Gera e envia relatório de posição de contratos por e-mail'

    def add_arguments(self, parser):
        parser.add_argument(
            '--formato',
            choices=['excel', 'pdf'],
            default='excel',
            help='Formato do relatório (excel ou pdf)',
        )

    def handle(self, *args, **options):
        from financeiro.tasks import enviar_relatorio_posicao_contratos
        formato = options['formato']
        self.stdout.write(f'Gerando relatório de posição ({formato})...')
        resultado = enviar_relatorio_posicao_contratos(formato=formato)
        if resultado.get('enviado'):
            self.stdout.write(self.style.SUCCESS(
                f"Enviado para {resultado['destinatarios']} destinatário(s). "
                f"Total contratos: {resultado.get('total_contratos', 0)}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Não enviado: {resultado.get('motivo') or resultado.get('erro', 'erro desconhecido')}"
            ))
