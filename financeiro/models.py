"""
Modelos Financeiros - Parcelas, Reajustes e Pagamentos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from core.models import TimeStampedModel


class Parcela(TimeStampedModel):
    """Modelo para representar uma parcela do contrato"""

    contrato = models.ForeignKey(
        'contratos.Contrato',
        on_delete=models.CASCADE,
        related_name='parcelas',
        verbose_name='Contrato'
    )
    numero_parcela = models.PositiveIntegerField(
        verbose_name='Número da Parcela'
    )
    data_vencimento = models.DateField(
        verbose_name='Data de Vencimento'
    )

    # Valores
    valor_original = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor Original',
        help_text='Valor inicial da parcela sem reajustes'
    )
    valor_atual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor Atual',
        help_text='Valor atual da parcela após reajustes'
    )
    valor_juros = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor de Juros',
        help_text='Juros calculados por atraso'
    )
    valor_multa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor de Multa',
        help_text='Multa calculada por atraso'
    )
    valor_desconto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor de Desconto',
        help_text='Desconto concedido na parcela'
    )

    # Status de Pagamento
    pago = models.BooleanField(
        default=False,
        verbose_name='Pago'
    )
    data_pagamento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data do Pagamento'
    )
    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Pago'
    )

    # Observações
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )

    class Meta:
        verbose_name = 'Parcela'
        verbose_name_plural = 'Parcelas'
        ordering = ['contrato', 'numero_parcela']
        unique_together = [['contrato', 'numero_parcela']]
        indexes = [
            models.Index(fields=['contrato', 'numero_parcela']),
            models.Index(fields=['data_vencimento']),
            models.Index(fields=['pago']),
        ]

    def __str__(self):
        return f"Parcela {self.numero_parcela}/{self.contrato.numero_parcelas} - Contrato {self.contrato.numero_contrato}"

    @property
    def valor_total(self):
        """Calcula o valor total da parcela (valor atual + juros + multa - desconto)"""
        return self.valor_atual + self.valor_juros + self.valor_multa - self.valor_desconto

    @property
    def dias_atraso(self):
        """Calcula quantos dias de atraso a parcela possui"""
        if self.pago:
            return 0

        hoje = timezone.now().date()
        if hoje > self.data_vencimento:
            return (hoje - self.data_vencimento).days
        return 0

    @property
    def esta_vencida(self):
        """Verifica se a parcela está vencida"""
        return not self.pago and timezone.now().date() > self.data_vencimento

    def calcular_juros_multa(self, data_referencia=None):
        """
        Calcula juros e multa com base na data de referência
        Se data_referencia não for fornecida, usa a data atual
        """
        if self.pago:
            return Decimal('0.00'), Decimal('0.00')

        if data_referencia is None:
            data_referencia = timezone.now().date()

        if data_referencia <= self.data_vencimento:
            return Decimal('0.00'), Decimal('0.00')

        dias_atraso = (data_referencia - self.data_vencimento).days

        # Calcular multa (aplicada uma vez)
        multa = self.valor_atual * (self.contrato.percentual_multa / 100)

        # Calcular juros (proporcional aos dias de atraso)
        # Juros = valor * (taxa_mensal / 30) * dias_atraso
        juros = self.valor_atual * (self.contrato.percentual_juros_mora / 100) * (dias_atraso / 30)

        return juros, multa

    def atualizar_juros_multa(self):
        """Atualiza os valores de juros e multa da parcela"""
        if not self.pago:
            juros, multa = self.calcular_juros_multa()
            self.valor_juros = juros
            self.valor_multa = multa
            self.save()

    def registrar_pagamento(self, valor_pago, data_pagamento=None, observacoes=''):
        """Registra o pagamento da parcela"""
        if data_pagamento is None:
            data_pagamento = timezone.now().date()

        # Atualizar juros e multa antes de registrar o pagamento
        if data_pagamento > self.data_vencimento:
            juros, multa = self.calcular_juros_multa(data_pagamento)
            self.valor_juros = juros
            self.valor_multa = multa

        self.pago = True
        self.data_pagamento = data_pagamento
        self.valor_pago = valor_pago
        if observacoes:
            self.observacoes = observacoes
        self.save()

    def cancelar_pagamento(self):
        """Cancela o pagamento da parcela"""
        self.pago = False
        self.data_pagamento = None
        self.valor_pago = None
        self.valor_juros = Decimal('0.00')
        self.valor_multa = Decimal('0.00')
        self.save()


class Reajuste(TimeStampedModel):
    """Modelo para registrar os reajustes aplicados nas parcelas"""

    contrato = models.ForeignKey(
        'contratos.Contrato',
        on_delete=models.CASCADE,
        related_name='reajustes',
        verbose_name='Contrato'
    )
    data_reajuste = models.DateField(
        default=timezone.now,
        verbose_name='Data do Reajuste'
    )
    indice_tipo = models.CharField(
        max_length=10,
        verbose_name='Tipo de Índice',
        help_text='IPCA, IGPM, SELIC, etc.'
    )
    percentual = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('-100.0000'))],
        verbose_name='Percentual (%)',
        help_text='Percentual do índice aplicado'
    )
    parcela_inicial = models.PositiveIntegerField(
        verbose_name='Parcela Inicial',
        help_text='Primeira parcela afetada pelo reajuste'
    )
    parcela_final = models.PositiveIntegerField(
        verbose_name='Parcela Final',
        help_text='Última parcela afetada pelo reajuste'
    )
    aplicado_manual = models.BooleanField(
        default=False,
        verbose_name='Aplicado Manualmente',
        help_text='Indica se o reajuste foi aplicado manualmente pelo usuário'
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )

    class Meta:
        verbose_name = 'Reajuste'
        verbose_name_plural = 'Reajustes'
        ordering = ['-data_reajuste']
        indexes = [
            models.Index(fields=['contrato', 'data_reajuste']),
        ]

    def __str__(self):
        return f"Reajuste {self.indice_tipo} - {self.percentual}% - Contrato {self.contrato.numero_contrato}"

    def aplicar_reajuste(self):
        """Aplica o reajuste nas parcelas especificadas"""
        parcelas = self.contrato.parcelas.filter(
            numero_parcela__gte=self.parcela_inicial,
            numero_parcela__lte=self.parcela_final,
            pago=False  # Só reajusta parcelas não pagas
        )

        fator_reajuste = 1 + (self.percentual / 100)

        for parcela in parcelas:
            parcela.valor_atual = parcela.valor_atual * fator_reajuste
            parcela.save()

        # Atualizar data do último reajuste no contrato
        self.contrato.data_ultimo_reajuste = self.data_reajuste
        self.contrato.save()


class HistoricoPagamento(TimeStampedModel):
    """Modelo para manter histórico de pagamentos"""

    parcela = models.ForeignKey(
        Parcela,
        on_delete=models.CASCADE,
        related_name='historico_pagamentos',
        verbose_name='Parcela'
    )
    data_pagamento = models.DateField(
        verbose_name='Data do Pagamento'
    )
    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor Pago'
    )
    valor_parcela = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor da Parcela'
    )
    valor_juros = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor de Juros'
    )
    valor_multa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor de Multa'
    )
    valor_desconto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor de Desconto'
    )
    forma_pagamento = models.CharField(
        max_length=50,
        choices=[
            ('DINHEIRO', 'Dinheiro'),
            ('PIX', 'PIX'),
            ('TRANSFERENCIA', 'Transferência Bancária'),
            ('BOLETO', 'Boleto'),
            ('CARTAO_CREDITO', 'Cartão de Crédito'),
            ('CARTAO_DEBITO', 'Cartão de Débito'),
            ('CHEQUE', 'Cheque'),
        ],
        default='DINHEIRO',
        verbose_name='Forma de Pagamento'
    )
    comprovante = models.FileField(
        upload_to='comprovantes/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Comprovante',
        help_text='Upload do comprovante de pagamento'
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )

    class Meta:
        verbose_name = 'Histórico de Pagamento'
        verbose_name_plural = 'Histórico de Pagamentos'
        ordering = ['-data_pagamento']
        indexes = [
            models.Index(fields=['parcela', 'data_pagamento']),
        ]

    def __str__(self):
        return f"Pagamento - {self.parcela} - {self.data_pagamento}"
