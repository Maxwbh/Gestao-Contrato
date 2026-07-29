"""
Promove a QUITADO os contratos cuja totalidade de parcelas já está paga.

A quitação passou a ser automática no registro do pagamento, mas os contratos
que ficaram 100% pagos ANTES dessa mudança continuam marcados como ATIVO — é o
caso da listagem que mostrava "100.0% pago" com o selo Ativo (e ainda cobrava
reajuste). Este comando reconcilia a base existente.

    manage.py sincronizar_quitacao            # aplica
    manage.py sincronizar_quitacao --dry-run  # só relata
"""
from django.core.management.base import BaseCommand

from contratos.models import Contrato, StatusContrato


class Command(BaseCommand):
    help = 'Marca como QUITADO os contratos com todas as parcelas pagas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Apenas lista o que seria alterado, sem gravar.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        candidatos = (
            Contrato.objects
            .filter(status__in=[StatusContrato.ATIVO, StatusContrato.SUSPENSO])
            .prefetch_related('parcelas')
        )

        alterados = 0
        for contrato in candidatos:
            if not contrato.esta_totalmente_pago:
                continue
            alterados += 1
            self.stdout.write(
                f'   → {contrato.numero_contrato}: '
                f'{contrato.get_status_display()} → Quitado'
            )
            if not dry:
                contrato.sincronizar_quitacao()

        if alterados == 0:
            self.stdout.write(self.style.SUCCESS(
                'Nenhum contrato pendente de quitação.'))
        elif dry:
            self.stdout.write(self.style.WARNING(
                f'{alterados} contrato(s) seriam marcados como Quitado '
                f'(execute sem --dry-run para aplicar).'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{alterados} contrato(s) marcados como Quitado.'))
