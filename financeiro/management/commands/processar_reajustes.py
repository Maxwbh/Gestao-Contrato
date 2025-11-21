"""
Django Management Command para processar reajustes de contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA

Uso:
    python manage.py processar_reajustes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from financeiro.tasks import processar_reajustes_pendentes


class Command(BaseCommand):
    help = 'Processa reajustes pendentes de todos os contratos ativos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f'Iniciando processamento de reajustes... [{timezone.now()}]'
        ))

        try:
            resultado = processar_reajustes_pendentes()

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Processamento concluído!'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Contratos processados: {resultado["processados"]}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Contratos reajustados: {resultado["reajustados"]}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Erro ao processar reajustes: {str(e)}'
            ))
            raise
