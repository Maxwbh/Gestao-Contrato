"""
Management command para enviar o relatório de inadimplência manualmente.

Uso:
    python manage.py enviar_relatorio_inadimplencia
    python manage.py enviar_relatorio_inadimplencia --frequencia semanal
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '34.5.1 — Envia relatório de inadimplência por e-mail'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequencia',
            choices=['diario', 'semanal'],
            default='diario',
            help='Frequência do relatório (diario ou semanal)',
        )

    def handle(self, *args, **options):
        from financeiro.tasks import enviar_relatorio_inadimplencia
        frequencia = options['frequencia']
        self.stdout.write(f'Enviando relatório de inadimplência ({frequencia})...')
        resultado = enviar_relatorio_inadimplencia(frequencia=frequencia)
        if resultado.get('enviado'):
            self.stdout.write(self.style.SUCCESS(
                f"Enviado para {resultado['destinatarios']} destinatário(s). "
                f"Total vencidas: {resultado.get('total_vencidas', 0)}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Não enviado: {resultado.get('motivo') or resultado.get('erro', 'erro desconhecido')}"
            ))
