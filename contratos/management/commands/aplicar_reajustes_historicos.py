"""
Aplica os reajustes históricos dos contratos reais.

Uso:
    python manage.py aplicar_reajustes_historicos
    python manage.py aplicar_reajustes_historicos --dry-run

Validação automática contra planilha após cada ciclo.
Idempotente: pula ciclos já aplicados.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


# Valores esperados da planilha (para validação)
ESPERADO_HENRY = {
    2: Decimal('1034.48'),
    3: Decimal('1230.78'),
    4: Decimal('1234.92'),
    5: Decimal('1402.42'),
    6: Decimal('1588.78'),
}

ESPERADO_UANDA = {
    2: Decimal('1664.47'),
    3: Decimal('1928.10'),
    4: Decimal('2218.01'),
    5: Decimal('2589.60'),
    # ciclo 6 calculado em tempo real (sem planilha disponível)
}

TOLERANCIA = Decimal('0.02')  # ±R$ 0,02 (arredondamento)


class _DryRunRollback(Exception):
    pass


class Command(BaseCommand):
    help = 'Aplica reajustes históricos dos contratos Henry (IGPM) e Uanda (IPCA)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Simula sem persistir — exibe preview de cada ciclo',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('--- DRY RUN ---'))
        try:
            with transaction.atomic():
                self._executar(dry_run)
                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            self.stdout.write(self.style.WARNING('Rollback efetuado (dry-run).'))

    # ------------------------------------------------------------------

    def _executar(self, dry_run):
        from contratos.models import Contrato

        henry = Contrato.objects.filter(
            comprador__nome__icontains='Henry'
        ).select_related('comprador', 'imovel').first()

        uanda = Contrato.objects.filter(
            comprador__nome__icontains='Uanda'
        ).select_related('comprador', 'imovel').first()

        if not henry:
            self.stdout.write(self.style.ERROR('Contrato Henry não encontrado.'))
        else:
            self._aplicar_contrato(henry, ESPERADO_HENRY, dry_run)

        if not uanda:
            self.stdout.write(self.style.ERROR('Contrato Uanda não encontrado.'))
        else:
            self._aplicar_contrato(uanda, ESPERADO_UANDA, dry_run)

    # ------------------------------------------------------------------

    def _aplicar_contrato(self, contrato, esperados, dry_run):
        self.stdout.write(
            f'\n{"="*60}\n'
            f'{contrato.comprador.nome} | {contrato.imovel}\n'
            f'Data: {contrato.data_contrato} | Índice: {contrato.tipo_correcao} | '
            f'Prazo: {contrato.prazo_reajuste_meses}m\n'
            f'{"="*60}'
        )

        prazo = contrato.prazo_reajuste_meses
        max_ciclo = (contrato.numero_parcelas - 1) // prazo + 1

        aplicados = 0
        pulados = 0

        for ciclo in range(2, max_ciclo + 1):
            resultado = self._aplicar_ciclo(contrato, ciclo, esperados, dry_run)
            if resultado == 'ok':
                aplicados += 1
            elif resultado == 'pulado':
                pulados += 1
            elif resultado == 'futuro':
                self.stdout.write(f'  Ciclo {ciclo}+: data futura — parando.\n')
                break
            elif resultado == 'sem_indice':
                self.stdout.write(
                    self.style.WARNING(f'  Ciclo {ciclo}: índice não disponível — parando.\n')
                )
                break

        # Resumo
        pmt_atual = contrato.parcelas.filter(
            tipo_parcela='NORMAL', pago=False
        ).order_by('numero_parcela').first()
        self.stdout.write(
            f'\n  Resultado: {aplicados} ciclo(s) aplicado(s), {pulados} já existiam.\n'
            f'  PMT atual: R$ {pmt_atual.valor_atual if pmt_atual else "N/A"}\n'
        )

    # ------------------------------------------------------------------

    def _aplicar_ciclo(self, contrato, ciclo, esperados, dry_run):
        from financeiro.models import Reajuste
        from dateutil.relativedelta import relativedelta

        # Verificar se já aplicado
        if Reajuste.objects.filter(contrato=contrato, ciclo=ciclo, aplicado=True).exists():
            pmt = self._pmt_ciclo(contrato, ciclo)
            self.stdout.write(f'  Ciclo {ciclo}: [JÁ APLICADO] PMT=R$ {pmt}')
            self._validar(ciclo, pmt, esperados)
            return 'pulado'

        # Verificar se a data do ciclo chegou (hoje >= data_inicio_ciclo)
        data_inicio_ciclo = contrato.data_contrato + relativedelta(
            months=(ciclo - 1) * contrato.prazo_reajuste_meses
        )
        hoje = timezone.now().date()
        if hoje < data_inicio_ciclo:
            return 'futuro'

        # Obter preview
        preview = Reajuste.preview_reajuste(contrato, ciclo)

        if preview.get('erro'):
            if 'não disponível' in str(preview['erro']).lower() or \
               'índice' in str(preview['erro']).lower():
                return 'sem_indice'
            self.stdout.write(self.style.ERROR(
                f'  Ciclo {ciclo}: ERRO no preview — {preview["erro"]}'
            ))
            return 'erro'

        perc_final = preview['percentual_final']
        indice = preview['indice_tipo']
        tipo = preview.get('tipo_calculo', 'SIMPLES')
        novo_pmt = None

        if tipo == 'TABELA_PRICE' and preview.get('parcelas'):
            novo_pmt = preview['parcelas'][0].get('valor_novo')
        elif preview.get('parcelas'):
            novo_pmt = preview['parcelas'][0].get('valor_novo')

        self.stdout.write(
            f'  Ciclo {ciclo}: {indice} {perc_final:+.4f}% | '
            f'{data_inicio_ciclo.strftime("%b/%Y")} | {tipo} | '
            f'PMT previsto: R$ {novo_pmt}'
        )

        if dry_run:
            if novo_pmt:
                self._validar(ciclo, Decimal(str(novo_pmt)), esperados)
            return 'ok'

        # Criar e aplicar reajuste
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=hoje,
            indice_tipo=preview['indice_tipo'],
            percentual=preview['percentual_final'],
            percentual_bruto=preview['percentual_bruto'],
            spread_aplicado=preview.get('spread') or None,
            piso_aplicado=preview.get('piso'),
            teto_aplicado=preview.get('teto'),
            parcela_inicial=preview['parcela_inicial'],
            parcela_final=preview['parcela_final'],
            ciclo=ciclo,
            periodo_referencia_inicio=preview['periodo_referencia_inicio'],
            periodo_referencia_fim=preview['periodo_referencia_fim'],
            aplicado_manual=True,
            observacoes='Reajuste histórico aplicado via importar_contratos_reais',
        )
        resultado = reajuste.aplicar_reajuste()

        if not resultado.get('sucesso', True) and resultado.get('erro'):
            self.stdout.write(self.style.ERROR(
                f'    ERRO ao aplicar: {resultado["erro"]}'
            ))
            return 'erro'

        pmt_real = self._pmt_ciclo(contrato, ciclo)
        self.stdout.write(
            self.style.SUCCESS(f'    ✓ Aplicado — PMT real: R$ {pmt_real}')
        )
        self._validar(ciclo, pmt_real, esperados)
        return 'ok'

    # ------------------------------------------------------------------

    def _pmt_ciclo(self, contrato, ciclo):
        prazo = contrato.prazo_reajuste_meses
        parcela_inicial = (ciclo - 1) * prazo + 1
        parcela = contrato.parcelas.filter(
            numero_parcela=parcela_inicial,
            tipo_parcela='NORMAL',
        ).first()
        return parcela.valor_atual if parcela else None

    def _validar(self, ciclo, pmt_real, esperados):
        if pmt_real is None:
            return
        esperado = esperados.get(ciclo)
        if esperado is None:
            self.stdout.write(f'    ℹ Ciclo {ciclo}: sem valor de referência na planilha.')
            return
        diff = abs(pmt_real - esperado)
        if diff <= TOLERANCIA:
            self.stdout.write(
                self.style.SUCCESS(
                    f'    ✓ Validação: R$ {pmt_real} (esperado R$ {esperado}, diff R$ {diff}) OK'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'    ✗ DIVERGÊNCIA ciclo {ciclo}: obtido R$ {pmt_real} | '
                    f'esperado R$ {esperado} | diff R$ {diff}'
                )
            )
