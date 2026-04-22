"""
Management command: audit_nosso_numero

Audita a qualidade do campo nosso_numero nas Parcelas:
- Detecta duplicatas dentro da mesma conta bancária
- Detecta duplicatas globais (entre contas diferentes)
- Lista parcelas com boleto gerado mas nosso_numero em branco

Uso:
    python manage.py audit_nosso_numero
    python manage.py audit_nosso_numero --fix-duplicates
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from financeiro.models import Parcela, StatusBoleto


class Command(BaseCommand):
    help = 'Audita nosso_numero: duplicatas por conta, duplicatas globais, boletos sem nosso_numero'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-duplicates',
            action='store_true',
            help='Limpa nosso_numero de parcelas duplicadas dentro da mesma conta (mantém a mais antiga)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Auditoria nosso_numero ===\n'))

        # 1. Boletos gerados sem nosso_numero
        sem_nn = Parcela.objects.exclude(status_boleto=StatusBoleto.NAO_GERADO).filter(nosso_numero='')
        self.stdout.write(f'Boletos gerados sem nosso_numero: {sem_nn.count()}')
        for p in sem_nn[:20]:
            self.stdout.write(f'  Parcela #{p.pk} — {p.contrato.numero_contrato} p{p.numero_parcela}')
        if sem_nn.count() > 20:
            self.stdout.write(f'  ... e mais {sem_nn.count() - 20}')

        # 2. Duplicatas dentro da mesma conta bancária
        self.stdout.write('')
        self.stdout.write('Duplicatas por conta_bancaria + nosso_numero:')
        dups_conta = (
            Parcela.objects
            .exclude(nosso_numero='')
            .values('conta_bancaria', 'conta_bancaria__descricao', 'nosso_numero')
            .annotate(qtd=Count('id'))
            .filter(qtd__gt=1)
            .order_by('-qtd')
        )
        if not dups_conta.exists():
            self.stdout.write(self.style.SUCCESS('  Nenhuma duplicata por conta.'))
        else:
            self.stdout.write(self.style.ERROR(f'  {dups_conta.count()} grupo(s) duplicado(s):'))
            for d in dups_conta[:30]:
                self.stdout.write(
                    f"  Conta {d['conta_bancaria']} ({d['conta_bancaria__descricao']}) "
                    f"nosso_numero={d['nosso_numero']} — {d['qtd']} parcelas"
                )
                if options['fix_duplicates']:
                    self._fix_duplicates(d['conta_bancaria'], d['nosso_numero'])

        # 3. Duplicatas globais (mesmo nosso_numero em contas diferentes)
        self.stdout.write('')
        self.stdout.write('Mesmo nosso_numero em contas diferentes:')
        dups_global = (
            Parcela.objects
            .exclude(nosso_numero='')
            .values('nosso_numero')
            .annotate(qtd_contas=Count('conta_bancaria', distinct=True))
            .filter(qtd_contas__gt=1)
            .order_by('-qtd_contas')
        )
        if not dups_global.exists():
            self.stdout.write(self.style.SUCCESS('  Nenhum nosso_numero compartilhado entre contas.'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'  {dups_global.count()} nosso_numero(s) aparecem em múltiplas contas '
                    f'(esperado após migração de conta):'
                )
            )
            for d in dups_global[:20]:
                self.stdout.write(f"  nosso_numero={d['nosso_numero']} — {d['qtd_contas']} contas")

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('=== Fim da auditoria ==='))

    def _fix_duplicates(self, conta_bancaria_id, nosso_numero):
        """Limpa nosso_numero das parcelas duplicadas (mantém a mais antiga)."""
        parcelas = list(
            Parcela.objects
            .filter(conta_bancaria_id=conta_bancaria_id, nosso_numero=nosso_numero)
            .order_by('id')
        )
        # Manter a primeira (mais antiga), limpar as demais
        for p in parcelas[1:]:
            self.stdout.write(
                self.style.WARNING(f'    Limpando nosso_numero da parcela #{p.pk}')
            )
            p.nosso_numero = ''
            p.save(update_fields=['nosso_numero'])
