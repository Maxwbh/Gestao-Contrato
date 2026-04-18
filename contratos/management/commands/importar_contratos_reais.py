"""
Importação de contratos reais — Residencial Parque das Nogueiras

Uso:
    python manage.py importar_contratos_reais
    python manage.py importar_contratos_reais --dry-run   # verifica sem salvar

Dados sensíveis (CPF/CNPJ) são omitidos.
Idempotente: seguro para executar múltiplas vezes.
"""
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel, ContaBancaria
from contratos.models import (
    Contrato, TipoCorrecao, TipoAmortizacao, StatusContrato, TabelaJurosContrato,
)


class Command(BaseCommand):
    help = 'Importa os contratos reais do Residencial Parque das Nogueiras'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a importação sem salvar nada no banco',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('--- DRY RUN: nenhum dado será salvo ---'))

        try:
            with transaction.atomic():
                self._importar(dry_run)
                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            self.stdout.write(self.style.WARNING('Rollback efetuado (dry-run).'))

    def _importar(self, dry_run):
        self.stdout.write('=== Importando contratos reais ===')

        contabilidade = self._criar_contabilidade()
        imobiliaria = self._criar_imobiliaria(contabilidade)
        self._criar_conta_bancaria(imobiliaria)

        self._importar_contrato_henry(imobiliaria)
        # --- Contrato 2 (Uanda Silva L16-QD) --------------------------------
        # TODO: importar após upload dos arquivos:
        #   docs/L 16 Q D 24032021.docx
        #   docs/Planilha_Uanda_Silva_IPCA_Saldo_Anual_Atualizado_Calculo_exato_2.xlsx
        # self._importar_contrato_uanda(imobiliaria)
        # --------------------------------------------------------------------

        self.stdout.write(self.style.SUCCESS('=== Importação concluída ==='))

    # ------------------------------------------------------------------
    # Contabilidade
    # ------------------------------------------------------------------
    def _criar_contabilidade(self):
        obj, created = Contabilidade.objects.get_or_create(
            nome='RPN Loteamentos',
            defaults=dict(
                razao_social='RPN Loteamentos',
                cnpj=None,
                endereco='Rua Celso Dutra, 60 — Parque das Nogueiras, Sete Lagoas/MG',
                telefone='(31) 00000-0000',
                email='rpn@parquedasnogueiras.com.br',
                responsavel='Mauro Lúcio Duarte Nogueira',
            ),
        )
        self._log('Contabilidade', obj.nome, created)
        return obj

    # ------------------------------------------------------------------
    # Imobiliária
    # ------------------------------------------------------------------
    def _criar_imobiliaria(self, contabilidade):
        obj, created = Imobiliaria.objects.get_or_create(
            nome='DIZATY IMOBILIÁRIA LTDA',
            defaults=dict(
                contabilidade=contabilidade,
                tipo_pessoa='PJ',
                razao_social='DIZATY IMOBILIÁRIA LTDA',
                cnpj='00.000.000/0001-00',   # placeholder — CNPJ real omitido (política de dados)
                cep='35700-067',
                logradouro='Rua Ouro Preto',
                numero='344',
                bairro='Jardim Cambuí',
                cidade='Sete Lagoas',
                estado='MG',
                telefone='(31) 00000-0000',
                email='dizaty@imobiliaria.com.br',
                responsavel_financeiro='DIZATY IMOBILIÁRIA LTDA',
            ),
        )
        self._log('Imobiliária', obj.nome, created)
        return obj

    # ------------------------------------------------------------------
    # Conta Bancária (Caixa Econômica — conta corrente do vendedor)
    # ------------------------------------------------------------------
    def _criar_conta_bancaria(self, imobiliaria):
        obj, created = ContaBancaria.objects.get_or_create(
            imobiliaria=imobiliaria,
            banco='104',
            agencia='2426',
            conta='2420-1',
            defaults=dict(
                descricao='Caixa — Conta Corrente Vendedor',
                principal=True,
            ),
        )
        self._log('ContaBancaria', str(obj), created)
        return obj

    # ------------------------------------------------------------------
    # Contrato 1 — Henry Magno de Oliveira Silva, Lote 13 Quadra C
    # Minuta: 22/07/2020 | IGPM | PRICE | 120 parcelas | R$ 86.334,81
    # ------------------------------------------------------------------
    def _importar_contrato_henry(self, imobiliaria):
        self.stdout.write('--- Contrato 1: Henry Magno / L13-QC ---')

        imovel = self._criar_imovel_henry(imobiliaria)
        comprador = self._criar_comprador_henry()
        contrato, created = self._criar_contrato_henry(imovel, comprador, imobiliaria)

        if created:
            self._criar_tabela_juros_henry(contrato)
            contrato.recalcular_amortizacao()
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Parcelas geradas e amortização calculada '
                    f'({contrato.parcelas.count()} parcelas, '
                    f'PMT ciclo-1 = R$ {contrato.valor_parcela_original})'
                )
            )
        else:
            self.stdout.write(self.style.WARNING('  Contrato já existe — nenhuma alteração.'))

    def _criar_imovel_henry(self, imobiliaria):
        obj, created = Imovel.objects.get_or_create(
            identificacao='Lote 13, Quadra C',
            loteamento='Residencial Parque das Nogueiras',
            defaults=dict(
                imobiliaria=imobiliaria,
                tipo=TipoImovel.LOTE,
                cep='35703-610',
                logradouro='Alameda Macieiras (antiga Rua C)',
                bairro='Parque das Nogueiras',
                cidade='Sete Lagoas',
                estado='MG',
                area=Decimal('360.15'),
                valor=Decimal('186334.81'),
                matricula='33.368',
                observacoes='Livro 2-BDGP, fl 282 — 1º Ofício de Registro de Imóveis de Sete Lagoas',
                disponivel=False,
            ),
        )
        self._log('Imóvel', str(obj), created)
        return obj

    def _criar_comprador_henry(self):
        obj, created = Comprador.objects.get_or_create(
            nome='Henry Magno de Oliveira Silva',
            defaults=dict(
                tipo_pessoa='PF',
                cpf='000.000.000-00',    # CPF omitido — política de dados
                estado_civil='SOLTEIRO',
                profissao='Empresário',
                logradouro='Rua Cracóvia',
                numero='259',
                bairro='Mangabeiras',
                cidade='Sete Lagoas',
                estado='MG',
                cep='35700-433',
                telefone='(31) 00000-0000',
                celular='(31) 00000-0000',
                email='henrymagno@exemplo.com.br',
            ),
        )
        self._log('Comprador', obj.nome, created)
        return obj

    def _criar_contrato_henry(self, imovel, comprador, imobiliaria):
        conta = ContaBancaria.objects.filter(imobiliaria=imobiliaria).first()
        obj, created = Contrato.objects.get_or_create(
            numero_contrato='L13-QC-22072020',
            defaults=dict(
                imovel=imovel,
                comprador=comprador,
                imobiliaria=imobiliaria,
                data_contrato=date(2020, 7, 22),
                data_primeiro_vencimento=date(2020, 8, 10),
                valor_total=Decimal('186334.81'),
                valor_entrada=Decimal('100000.00'),
                numero_parcelas=120,
                dia_vencimento=10,
                tipo_correcao=TipoCorrecao.IGPM,
                tipo_correcao_fallback=TipoCorrecao.INPC,   # cláusula 2.3
                prazo_reajuste_meses=12,
                tipo_amortizacao=TipoAmortizacao.PRICE,
                percentual_juros_mora=Decimal('1.00'),       # 0,033%/dia ≈ 1%/mês
                percentual_multa=Decimal('2.00'),
                percentual_fruicao=Decimal('0.5000'),
                percentual_multa_rescisao_penal=Decimal('10.0000'),
                percentual_multa_rescisao_adm=Decimal('12.0000'),
                status=StatusContrato.ATIVO,
                conta_bancaria_padrao=conta,
            ),
        )
        self._log('Contrato', obj.numero_contrato, created)
        return obj, created

    def _criar_tabela_juros_henry(self, contrato):
        """
        Juros escalantes por ciclo (conforme cláusula 2 da minuta):
          Ciclo 1 (Ano 1): 0,00% a.m. → PMT fixo R$ 719,46
          Ciclo 2 (Ano 2): 0,60% a.m.
          ...
          Ciclos 7+ (Anos 7–10): 0,85% a.m.
        """
        tabela = [
            (1, 1,    Decimal('0.0000')),
            (2, 2,    Decimal('0.6000')),
            (3, 3,    Decimal('0.6500')),
            (4, 4,    Decimal('0.7000')),
            (5, 5,    Decimal('0.7500')),
            (6, 6,    Decimal('0.8000')),
            (7, None, Decimal('0.8500')),   # ciclos 7 em diante (até ciclo 10)
        ]
        for ciclo_inicio, ciclo_fim, juros in tabela:
            TabelaJurosContrato.objects.create(
                contrato=contrato,
                ciclo_inicio=ciclo_inicio,
                ciclo_fim=ciclo_fim,
                juros_mensal=juros,
            )
        self.stdout.write(f'  TabelaJurosContrato: {len(tabela)} faixas criadas.')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log(self, model, identifier, created):
        if created:
            self.stdout.write(self.style.SUCCESS(f'  [CRIADO] {model}: {identifier}'))
        else:
            self.stdout.write(f'  [EXISTE] {model}: {identifier}')


class _DryRunRollback(Exception):
    """Sinaliza rollback no modo dry-run."""
