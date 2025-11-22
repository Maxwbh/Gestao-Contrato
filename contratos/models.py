"""
Modelos de Contratos de Venda de Imóveis

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from core.models import TimeStampedModel, Imovel, Comprador, Imobiliaria


class TipoCorrecao(models.TextChoices):
    """Tipos de correção monetária disponíveis"""
    IPCA = 'IPCA', 'IPCA - Índice de Preços ao Consumidor Amplo'
    IGPM = 'IGPM', 'IGP-M - Índice Geral de Preços do Mercado'
    INCC = 'INCC', 'INCC - Índice Nacional de Custo da Construção'
    IGPDI = 'IGPDI', 'IGP-DI - Índice Geral de Preços - Disponibilidade Interna'
    INPC = 'INPC', 'INPC - Índice Nacional de Preços ao Consumidor'
    TR = 'TR', 'TR - Taxa Referencial'
    SELIC = 'SELIC', 'SELIC - Taxa Básica de Juros'
    FIXO = 'FIXO', 'Valor Fixo (sem correção)'


class IndiceReajuste(TimeStampedModel):
    """Modelo para armazenar os índices de reajuste mensais"""

    tipo_indice = models.CharField(
        max_length=10,
        choices=[
            ('IPCA', 'IPCA - Índice de Preços ao Consumidor Amplo'),
            ('IGPM', 'IGP-M - Índice Geral de Preços do Mercado'),
            ('INCC', 'INCC - Índice Nacional de Custo da Construção'),
            ('IGPDI', 'IGP-DI - Índice Geral de Preços - Disponibilidade Interna'),
            ('INPC', 'INPC - Índice Nacional de Preços ao Consumidor'),
            ('TR', 'TR - Taxa Referencial'),
            ('SELIC', 'SELIC - Taxa Básica de Juros'),
        ],
        verbose_name='Tipo de Índice'
    )
    ano = models.PositiveIntegerField(
        verbose_name='Ano',
        validators=[MinValueValidator(1990), MaxValueValidator(2100)]
    )
    mes = models.PositiveIntegerField(
        verbose_name='Mês',
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    valor = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name='Valor (%)',
        help_text='Valor percentual do índice no mês'
    )
    valor_acumulado_ano = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Acumulado no Ano (%)',
        help_text='Valor acumulado desde janeiro do ano corrente'
    )
    valor_acumulado_12m = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Acumulado 12 meses (%)',
        help_text='Valor acumulado nos últimos 12 meses'
    )
    fonte = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Fonte',
        help_text='Fonte dos dados (ex: IBGE, BCB, FGV)'
    )
    data_importacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Importação',
        help_text='Data em que o dado foi importado automaticamente'
    )

    class Meta:
        verbose_name = 'Índice de Reajuste'
        verbose_name_plural = 'Índices de Reajuste'
        ordering = ['-ano', '-mes', 'tipo_indice']
        unique_together = ['tipo_indice', 'ano', 'mes']
        indexes = [
            models.Index(fields=['tipo_indice', 'ano', 'mes']),
            models.Index(fields=['ano', 'mes']),
        ]

    def __str__(self):
        meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        return f"{self.tipo_indice} - {meses[self.mes]}/{self.ano}: {self.valor}%"

    @property
    def mes_nome(self):
        """Retorna o nome do mês"""
        meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        return meses[self.mes]

    @property
    def periodo(self):
        """Retorna o período formatado (MM/AAAA)"""
        return f"{self.mes:02d}/{self.ano}"

    @classmethod
    def get_indice(cls, tipo_indice, ano, mes):
        """Busca um índice específico"""
        try:
            return cls.objects.get(tipo_indice=tipo_indice, ano=ano, mes=mes)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_acumulado_periodo(cls, tipo_indice, ano_inicio, mes_inicio, ano_fim, mes_fim):
        """Calcula o índice acumulado em um período"""
        indices = cls.objects.filter(
            tipo_indice=tipo_indice
        ).filter(
            models.Q(ano__gt=ano_inicio) |
            models.Q(ano=ano_inicio, mes__gte=mes_inicio)
        ).filter(
            models.Q(ano__lt=ano_fim) |
            models.Q(ano=ano_fim, mes__lte=mes_fim)
        ).order_by('ano', 'mes')

        if not indices.exists():
            return None

        # Calcula acumulado: (1 + i1/100) * (1 + i2/100) * ... - 1
        acumulado = Decimal('1')
        for indice in indices:
            acumulado *= (1 + indice.valor / 100)

        return (acumulado - 1) * 100


class StatusContrato(models.TextChoices):
    """Status possíveis do contrato"""
    ATIVO = 'ATIVO', 'Ativo'
    QUITADO = 'QUITADO', 'Quitado'
    CANCELADO = 'CANCELADO', 'Cancelado'
    SUSPENSO = 'SUSPENSO', 'Suspenso'


class Contrato(TimeStampedModel):
    """Modelo principal de Contrato de Venda de Imóvel"""

    # Relações principais
    imovel = models.ForeignKey(
        Imovel,
        on_delete=models.PROTECT,
        related_name='contratos',
        verbose_name='Imóvel'
    )
    comprador = models.ForeignKey(
        Comprador,
        on_delete=models.PROTECT,
        related_name='contratos',
        verbose_name='Comprador'
    )
    imobiliaria = models.ForeignKey(
        Imobiliaria,
        on_delete=models.PROTECT,
        related_name='contratos',
        verbose_name='Imobiliária/Beneficiário'
    )

    # Dados do Contrato
    numero_contrato = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Número do Contrato',
        help_text='Número único de identificação do contrato'
    )
    data_contrato = models.DateField(
        default=timezone.now,
        verbose_name='Data do Contrato'
    )
    data_primeiro_vencimento = models.DateField(
        verbose_name='Data do Primeiro Vencimento',
        help_text='Data de vencimento da primeira parcela'
    )

    # Valores
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor Total do Contrato'
    )
    valor_entrada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Valor de Entrada',
        help_text='Valor pago como entrada (opcional)'
    )

    # Configurações de Parcelas
    numero_parcelas = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        verbose_name='Número de Parcelas',
        help_text='Quantidade total de parcelas do contrato'
    )
    dia_vencimento = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name='Dia de Vencimento',
        help_text='Dia do mês para vencimento das parcelas (1-31)'
    )

    # Juros e Multa
    percentual_juros_mora = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name='Juros de Mora (%)',
        help_text='Percentual de juros ao mês sobre o valor em atraso'
    )
    percentual_multa = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name='Multa (%)',
        help_text='Percentual de multa sobre o valor em atraso'
    )

    # Correção Monetária
    tipo_correcao = models.CharField(
        max_length=10,
        choices=TipoCorrecao.choices,
        default=TipoCorrecao.IPCA,
        verbose_name='Tipo de Correção'
    )
    prazo_reajuste_meses = models.PositiveIntegerField(
        default=12,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name='Prazo para Reajuste (meses)',
        help_text='Intervalo em meses para aplicação do reajuste'
    )
    data_ultimo_reajuste = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data do Último Reajuste'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=StatusContrato.choices,
        default=StatusContrato.ATIVO,
        verbose_name='Status'
    )

    # Observações
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações',
        help_text='Observações gerais sobre o contrato'
    )

    # Campos calculados
    valor_financiado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
        verbose_name='Valor Financiado',
        help_text='Valor Total - Valor de Entrada'
    )
    valor_parcela_original = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
        verbose_name='Valor Original da Parcela',
        help_text='Valor inicial de cada parcela (sem reajustes)'
    )

    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-data_contrato', 'numero_contrato']
        indexes = [
            models.Index(fields=['numero_contrato']),
            models.Index(fields=['status']),
            models.Index(fields=['data_contrato']),
        ]

    def __str__(self):
        return f"Contrato {self.numero_contrato} - {self.comprador.nome}"

    def save(self, *args, **kwargs):
        """Override do save para calcular campos automáticos"""
        # Calcular valor financiado
        self.valor_financiado = self.valor_total - self.valor_entrada

        # Calcular valor da parcela original
        if self.numero_parcelas > 0:
            self.valor_parcela_original = self.valor_financiado / self.numero_parcelas

        super().save(*args, **kwargs)

        # Gerar parcelas se ainda não foram geradas
        if not self.parcelas.exists():
            self.gerar_parcelas()

    def gerar_parcelas(self, ate_mes_atual=False):
        """
        Gera as parcelas do contrato

        Args:
            ate_mes_atual: Se True, gera parcelas apenas até o mês atual (útil para dados de teste)
        """
        from financeiro.models import Parcela
        from django.utils import timezone

        data_vencimento = self.data_primeiro_vencimento
        valor_parcela = self.valor_parcela_original

        # Data limite: último dia do mês atual
        if ate_mes_atual:
            hoje = timezone.now().date()
            data_limite = hoje.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)
        else:
            data_limite = None

        for numero in range(1, self.numero_parcelas + 1):
            # Se ate_mes_atual=True, parar quando vencimento ultrapassar o mês atual
            if data_limite and data_vencimento > data_limite:
                break

            Parcela.objects.create(
                contrato=self,
                numero_parcela=numero,
                data_vencimento=data_vencimento,
                valor_original=valor_parcela,
                valor_atual=valor_parcela,
            )

            # Avançar para o próximo mês, mantendo o dia de vencimento
            data_vencimento = data_vencimento + relativedelta(months=1)

            # Ajustar dia de vencimento se necessário (ex: 31 em meses com 30 dias)
            if data_vencimento.day != self.dia_vencimento:
                # Usar o último dia do mês se o dia de vencimento não existir naquele mês
                ultimo_dia = (data_vencimento.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)).day
                dia = min(self.dia_vencimento, ultimo_dia)
                data_vencimento = data_vencimento.replace(day=dia)

    def calcular_progresso(self):
        """Calcula o progresso de pagamento do contrato"""
        total_parcelas = self.parcelas.count()
        parcelas_pagas = self.parcelas.filter(pago=True).count()

        if total_parcelas == 0:
            return 0

        return (parcelas_pagas / total_parcelas) * 100

    def calcular_valor_pago(self):
        """Calcula o valor total já pago"""
        from django.db.models import Sum

        valor_pago = self.parcelas.filter(pago=True).aggregate(
            total=Sum('valor_pago')
        )['total'] or Decimal('0.00')

        return valor_pago + self.valor_entrada

    def calcular_saldo_devedor(self):
        """Calcula o saldo devedor atual"""
        valor_pago = self.calcular_valor_pago() - self.valor_entrada
        saldo_devedor = self.valor_financiado - valor_pago
        return max(saldo_devedor, Decimal('0.00'))

    def verificar_reajuste_necessario(self):
        """Verifica se o contrato precisa de reajuste"""
        if self.tipo_correcao == TipoCorrecao.FIXO:
            return False

        if not self.data_ultimo_reajuste:
            # Se nunca foi reajustado, verificar se já passou o prazo desde a data do contrato
            meses_desde_contrato = (timezone.now().date().year - self.data_contrato.year) * 12 + \
                                  (timezone.now().date().month - self.data_contrato.month)
            return meses_desde_contrato >= self.prazo_reajuste_meses

        # Verificar se passou o prazo desde o último reajuste
        meses_desde_reajuste = (timezone.now().date().year - self.data_ultimo_reajuste.year) * 12 + \
                              (timezone.now().date().month - self.data_ultimo_reajuste.month)
        return meses_desde_reajuste >= self.prazo_reajuste_meses
