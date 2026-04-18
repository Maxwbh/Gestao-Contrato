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
    Contrato, TipoCorrecao, TipoAmortizacao, StatusContrato,
    TabelaJurosContrato, PrestacaoIntermediaria, IndiceReajuste,
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
        self._criar_conta_caixa_vendedor_henry(imobiliaria)
        self._criar_conta_inter_vendedor_uanda(imobiliaria)

        self._importar_ipca_mensal()
        self._importar_contrato_henry(imobiliaria)
        self._importar_contrato_uanda(imobiliaria)

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
    # Contas Bancárias
    # ------------------------------------------------------------------
    def _criar_conta_caixa_vendedor_henry(self, imobiliaria):
        """Conta Corrente Caixa do vendedor — recebe parcelas do contrato L13-QC."""
        obj, created = ContaBancaria.objects.get_or_create(
            imobiliaria=imobiliaria,
            banco='104',
            agencia='2426',
            conta='2420-1',
            defaults=dict(
                descricao='Caixa CC — Vendedor (L13-QC Henry)',
                principal=True,
            ),
        )
        self._log('ContaBancaria', str(obj), created)
        return obj

    def _criar_conta_inter_vendedor_uanda(self, imobiliaria):
        """Conta Corrente Banco Inter do vendedor — recebe parcelas do contrato L16-QD."""
        obj, created = ContaBancaria.objects.get_or_create(
            imobiliaria=imobiliaria,
            banco='077',
            agencia='0001',
            conta='8851756-0',
            defaults=dict(
                descricao='Banco Inter CC — Vendedor (L16-QD Uanda)',
                principal=False,
            ),
        )
        self._log('ContaBancaria', str(obj), created)
        return obj

    # ------------------------------------------------------------------
    # Índices IPCA mensais (fonte: PDFs de cálculo exato Uanda)
    # ------------------------------------------------------------------
    def _importar_ipca_mensal(self):
        """
        Importa valores mensais do IPCA usados nos reajustes de Uanda (2024-2026).
        Fonte: Calculo atualizacao parcela IPCA 2024_2025 UANDA.pdf
               Calculo atualizacao parcela IPCA 2025_2026 UANDA.pdf
        """
        ipca_data = [
            # (ano, mês, valor_%)
            # Abr-2024 a Mar-2025
            (2024,  4, Decimal('0.3800')),
            (2024,  5, Decimal('0.4600')),
            (2024,  6, Decimal('0.2100')),
            (2024,  7, Decimal('0.3800')),
            (2024,  8, Decimal('-0.0200')),
            (2024,  9, Decimal('0.4400')),
            (2024, 10, Decimal('0.5600')),
            (2024, 11, Decimal('0.3900')),
            (2024, 12, Decimal('0.5200')),
            (2025,  1, Decimal('0.1600')),
            (2025,  2, Decimal('1.3100')),
            (2025,  3, Decimal('0.5600')),
            # Abr-2025 a Mar-2026
            (2025,  4, Decimal('0.4300')),
            (2025,  5, Decimal('0.2600')),
            (2025,  6, Decimal('0.2400')),
            (2025,  7, Decimal('0.2600')),
            (2025,  8, Decimal('-0.1100')),
            (2025,  9, Decimal('0.4800')),
            (2025, 10, Decimal('0.0900')),
            (2025, 11, Decimal('0.1800')),
            (2025, 12, Decimal('0.3300')),
            (2026,  1, Decimal('0.3300')),
            (2026,  2, Decimal('0.7000')),
            (2026,  3, Decimal('0.8800')),
        ]
        criados = 0
        for ano, mes, valor in ipca_data:
            _, created = IndiceReajuste.objects.get_or_create(
                tipo_indice='IPCA',
                ano=ano,
                mes=mes,
                defaults=dict(valor=valor, fonte='calculoexato.com.br (contrato Uanda L16-QD)'),
            )
            if created:
                criados += 1
        self.stdout.write(
            self.style.SUCCESS(f'  IndiceReajuste IPCA: {criados} novos / {len(ipca_data)} total')
            if criados else f'  IndiceReajuste IPCA: todos {len(ipca_data)} já existiam'
        )

    # ==================================================================
    # Contrato 1 — Henry Magno de Oliveira Silva, Lote 13 Quadra C
    # Minuta: 22/07/2020 | IGPM | PRICE | 120 parcelas | R$ 86.334,81
    # ==================================================================
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
        conta = ContaBancaria.objects.filter(imobiliaria=imobiliaria, banco='104').first()
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
        Juros escalantes por ciclo (cláusula 2 da minuta L13-QC):
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

    # ==================================================================
    # Contrato 2 — Uanda Silva Carvalho, Lote 16 Quadra D
    # Minuta: 24/03/2021 | IPCA | PRICE | 120 mensais + 10 anuais
    # Financiado mensal: R$ 162.126,24 → PMT R$ 1.351,05
    # Financiado intermediárias: R$ 50.000,00 → 10 × R$ 5.000,00 (anuais)
    # ==================================================================
    def _importar_contrato_uanda(self, imobiliaria):
        self.stdout.write('--- Contrato 2: Uanda Silva / L16-QD ---')

        imovel = self._criar_imovel_uanda(imobiliaria)
        comprador = self._criar_comprador_uanda()
        contrato, created = self._criar_contrato_uanda(imovel, comprador, imobiliaria)

        if created:
            self._criar_tabela_juros_uanda(contrato)
            # O valor_financiado (R$212.126,24) inclui intermediárias.
            # Passamos apenas o saldo das parcelas mensais como base_pv:
            contrato.recalcular_amortizacao(base_pv=Decimal('162126.24'))
            self._criar_intermediarias_uanda(contrato)
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Parcelas geradas e amortização calculada '
                    f'({contrato.parcelas.count()} parcelas mensais, '
                    f'PMT ciclo-1 = R$ {contrato.valor_parcela_original})'
                )
            )
        else:
            self.stdout.write(self.style.WARNING('  Contrato já existe — nenhuma alteração.'))

    def _criar_imovel_uanda(self, imobiliaria):
        obj, created = Imovel.objects.get_or_create(
            identificacao='Lote 16, Quadra D',
            loteamento='Residencial Parque das Nogueiras',
            defaults=dict(
                imobiliaria=imobiliaria,
                tipo=TipoImovel.LOTE,
                cep='35703-610',
                logradouro='Alameda Macieiras (antiga Rua C)',
                bairro='Parque das Nogueiras',
                cidade='Sete Lagoas',
                estado='MG',
                area=Decimal('365.26'),
                valor=Decimal('235695.82'),
                matricula='25.757',
                observacoes='Unidade 49 — Livro 2-ARGI, fl 76 — 1º Ofício de Registro de Imóveis de Sete Lagoas',
                disponivel=False,
            ),
        )
        self._log('Imóvel', str(obj), created)
        return obj

    def _criar_comprador_uanda(self):
        obj, created = Comprador.objects.get_or_create(
            nome='Uanda Silva Carvalho',
            defaults=dict(
                tipo_pessoa='PF',
                cpf='000.000.001-00',    # CPF omitido — política de dados
                estado_civil='SOLTEIRO',
                profissao='Empresária',
                logradouro='Rua Cruzeiro',
                numero='196',
                complemento='Apto 101',
                bairro='Braz Filizola',
                cidade='Sete Lagoas',
                estado='MG',
                cep='35701-002',
                telefone='(31) 00000-0000',
                celular='(31) 00000-0000',
                email='uandacarvalho@exemplo.com.br',
            ),
        )
        self._log('Comprador', obj.nome, created)
        return obj

    def _criar_contrato_uanda(self, imovel, comprador, imobiliaria):
        conta = ContaBancaria.objects.filter(imobiliaria=imobiliaria, banco='077').first()
        obj, created = Contrato.objects.get_or_create(
            numero_contrato='L16-QD-24032021',
            defaults=dict(
                imovel=imovel,
                comprador=comprador,
                imobiliaria=imobiliaria,
                data_contrato=date(2021, 3, 24),
                data_primeiro_vencimento=date(2021, 4, 10),
                # Valor total = sinal + financiado mensal + intermediárias
                valor_total=Decimal('235695.82'),
                valor_entrada=Decimal('23569.58'),
                # Parcelas mensais (120) + intermediárias anuais (10)
                numero_parcelas=120,
                quantidade_intermediarias=10,
                dia_vencimento=10,
                tipo_correcao=TipoCorrecao.IPCA,
                prazo_reajuste_meses=12,
                tipo_amortizacao=TipoAmortizacao.PRICE,
                # Intermediárias são obrigações extras (não reduzem PMT mensal)
                intermediarias_reduzem_pmt=False,
                intermediarias_reajustadas=True,
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

    def _criar_tabela_juros_uanda(self, contrato):
        """
        Contrato L16-QD: taxa uniforme desde o início (cláusula 2.2.1).
          Ciclo 1 (Ano 1): 0,00% a.m. → PMT fixo R$ 1.351,05 (= 162.126,24 ÷ 120)
          Ciclos 2+ : 0,85% a.m. (IPCA + juros compostos conforme contrato)
        """
        tabela = [
            (1, 1,    Decimal('0.0000')),
            (2, None, Decimal('0.8500')),   # ciclos 2 em diante
        ]
        for ciclo_inicio, ciclo_fim, juros in tabela:
            TabelaJurosContrato.objects.create(
                contrato=contrato,
                ciclo_inicio=ciclo_inicio,
                ciclo_fim=ciclo_fim,
                juros_mensal=juros,
            )
        self.stdout.write(f'  TabelaJurosContrato: {len(tabela)} faixas criadas.')

    def _criar_intermediarias_uanda(self, contrato):
        """
        10 parcelas intermediárias anuais de R$ 5.000,00 (cláusula 2.2.2).
        Vencimentos: meses 13, 25, 37, 49, 61, 73, 85, 97, 109, 120
        (correspondente a 10/04/2022 … 10/03/2031)
        """
        meses = [13, 25, 37, 49, 61, 73, 85, 97, 109, 120]
        for i, mes in enumerate(meses, start=1):
            PrestacaoIntermediaria.objects.get_or_create(
                contrato=contrato,
                numero_sequencial=i,
                defaults=dict(
                    mes_vencimento=mes,
                    valor=Decimal('5000.00'),
                ),
            )
        self.stdout.write(f'  Intermediárias: {len(meses)} criadas (anuais R$ 5.000,00).')

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
