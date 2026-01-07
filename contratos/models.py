"""
Modelos de Contratos de Venda de Imóveis

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
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


class TipoPrestacao(models.TextChoices):
    """Tipos de prestação"""
    NORMAL = 'NORMAL', 'Normal'
    INTERMEDIARIA = 'INTERMEDIARIA', 'Intermediária'
    ENTRADA = 'ENTRADA', 'Entrada'


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
        validators=[MinValueValidator(1), MaxValueValidator(360)],
        verbose_name='Número de Parcelas',
        help_text='Quantidade total de parcelas do contrato (máximo 360 meses = 30 anos)'
    )
    dia_vencimento = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name='Dia de Vencimento',
        help_text='Dia do mês para vencimento das parcelas (1-31)'
    )

    # Prestações Intermediárias
    quantidade_intermediarias = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        verbose_name='Quantidade de Intermediárias',
        help_text='Quantidade de prestações intermediárias (máximo 30)'
    )

    # Controle de Ciclo de Reajuste para Boletos
    ciclo_reajuste_atual = models.PositiveIntegerField(
        default=1,
        verbose_name='Ciclo de Reajuste Atual',
        help_text='Número do ciclo de reajuste atual (1 = meses 1-12, 2 = meses 13-24, etc.)'
    )
    ultimo_mes_boleto_gerado = models.PositiveIntegerField(
        default=0,
        verbose_name='Último Mês com Boleto Gerado',
        help_text='Número do último mês (relativo ao contrato) com boleto gerado'
    )
    bloqueio_boleto_reajuste = models.BooleanField(
        default=False,
        verbose_name='Boleto Bloqueado por Reajuste',
        help_text='Se True, a geração de boletos está bloqueada até aplicar o reajuste'
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

    # ============================================================
    # Configurações de Boleto do Contrato
    # Se usar_config_boleto_imobiliaria=True, usa valores da Imobiliária
    # Caso contrário, usa os valores definidos abaixo
    # ============================================================
    usar_config_boleto_imobiliaria = models.BooleanField(
        default=True,
        verbose_name='Usar Configurações da Imobiliária',
        help_text='Se marcado, usa as configurações de boleto da imobiliária'
    )

    # Conta Bancária padrão para este contrato
    conta_bancaria_padrao = models.ForeignKey(
        'core.ContaBancaria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contratos',
        verbose_name='Conta Bancária Padrão',
        help_text='Conta bancária para geração de boletos deste contrato'
    )

    # Configurações de Multa (personalizadas)
    tipo_valor_multa = models.CharField(
        max_length=10,
        choices=[('PERCENTUAL', 'Percentual'), ('VALOR', 'Valor Fixo')],
        default='PERCENTUAL',
        verbose_name='Tipo de Multa'
    )
    valor_multa_boleto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Multa do Boleto',
        help_text='Valor em percentual ou reais conforme tipo'
    )

    # Configurações de Juros (personalizadas)
    tipo_valor_juros = models.CharField(
        max_length=10,
        choices=[('PERCENTUAL', 'Percentual'), ('VALOR', 'Valor Fixo')],
        default='PERCENTUAL',
        verbose_name='Tipo de Juros'
    )
    valor_juros_boleto = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='Juros ao Dia do Boleto',
        help_text='Valor em percentual (0,0333 = 1% ao mês) ou reais'
    )

    # Dias sem encargos
    dias_carencia_boleto = models.IntegerField(
        default=0,
        verbose_name='Dias sem Encargos',
        help_text='Dias sem cobrar multa/juros após vencimento'
    )

    # Desconto
    tipo_valor_desconto = models.CharField(
        max_length=10,
        choices=[('PERCENTUAL', 'Percentual'), ('VALOR', 'Valor Fixo')],
        default='PERCENTUAL',
        verbose_name='Tipo de Desconto'
    )
    valor_desconto_boleto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Desconto do Boleto',
        help_text='Valor em percentual ou reais conforme tipo'
    )
    dias_desconto_boleto = models.IntegerField(
        default=0,
        verbose_name='Dias para Desconto',
        help_text='Dias antes do vencimento para conceder desconto'
    )

    # Instruções personalizadas
    instrucao_boleto_1 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Instrução 1',
        help_text='Primeira linha de instrução do boleto'
    )
    instrucao_boleto_2 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Instrução 2',
        help_text='Segunda linha de instrução do boleto'
    )
    instrucao_boleto_3 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Instrução 3',
        help_text='Terceira linha de instrução do boleto'
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

    def get_config_boleto(self):
        """
        Retorna as configurações de boleto do contrato.
        Se usar_config_boleto_imobiliaria=True, retorna valores da imobiliária.
        Caso contrário, retorna valores personalizados do contrato.

        Returns:
            dict: Configurações de boleto
        """
        if self.usar_config_boleto_imobiliaria:
            imob = self.imobiliaria
            return {
                'tipo_valor_multa': imob.tipo_valor_multa,
                'valor_multa': imob.percentual_multa_padrao,
                'tipo_valor_juros': imob.tipo_valor_juros,
                'valor_juros': imob.percentual_juros_padrao,
                'dias_carencia': imob.dias_para_encargos_padrao,
                'tipo_valor_desconto': imob.tipo_valor_desconto,
                'valor_desconto': imob.percentual_desconto_padrao,
                'dias_desconto': imob.dias_para_desconto_padrao,
                'instrucao_1': imob.instrucao_padrao,
                'instrucao_2': '',
                'instrucao_3': '',
                'tipo_titulo': imob.tipo_titulo,
                'aceite': imob.aceite,
            }
        else:
            return {
                'tipo_valor_multa': self.tipo_valor_multa,
                'valor_multa': self.valor_multa_boleto,
                'tipo_valor_juros': self.tipo_valor_juros,
                'valor_juros': self.valor_juros_boleto,
                'dias_carencia': self.dias_carencia_boleto,
                'tipo_valor_desconto': self.tipo_valor_desconto,
                'valor_desconto': self.valor_desconto_boleto,
                'dias_desconto': self.dias_desconto_boleto,
                'instrucao_1': self.instrucao_boleto_1,
                'instrucao_2': self.instrucao_boleto_2,
                'instrucao_3': self.instrucao_boleto_3,
                'tipo_titulo': self.imobiliaria.tipo_titulo,
                'aceite': self.imobiliaria.aceite,
            }

    def get_conta_bancaria(self):
        """
        Retorna a conta bancária para geração de boletos.
        Prioridade: 1) Conta do contrato, 2) Conta principal da imobiliária
        """
        if self.conta_bancaria_padrao:
            return self.conta_bancaria_padrao
        return self.imobiliaria.contas_bancarias.filter(
            principal=True, ativo=True
        ).first()

    def clean(self):
        """Validações de negócio do contrato"""
        super().clean()
        errors = {}

        # Validar prazo máximo de 360 meses
        if self.numero_parcelas and self.numero_parcelas > 360:
            errors['numero_parcelas'] = 'O número máximo de parcelas é 360 (30 anos).'

        if self.numero_parcelas and self.numero_parcelas < 1:
            errors['numero_parcelas'] = 'O contrato deve ter pelo menos 1 parcela.'

        # Validar máximo de 30 prestações intermediárias
        if self.quantidade_intermediarias and self.quantidade_intermediarias > 30:
            errors['quantidade_intermediarias'] = 'O máximo de prestações intermediárias é 30.'

        # Validar prazo de reajuste (padrão 12, mínimo 1, máximo 24)
        if self.prazo_reajuste_meses:
            if self.prazo_reajuste_meses < 1:
                errors['prazo_reajuste_meses'] = 'O prazo mínimo de reajuste é 1 mês.'
            elif self.prazo_reajuste_meses > 24:
                errors['prazo_reajuste_meses'] = 'O prazo máximo de reajuste é 24 meses.'

        # Validar valor de entrada não pode exceder valor total
        if self.valor_entrada and self.valor_total:
            if self.valor_entrada >= self.valor_total:
                errors['valor_entrada'] = 'O valor de entrada deve ser menor que o valor total do contrato.'

        # Validar dia de vencimento (1-28 recomendado para evitar problemas com meses curtos)
        if self.dia_vencimento and self.dia_vencimento > 28:
            # Aviso, não erro - aceita mas alerta
            pass  # Considera-se válido mas ajusta automaticamente

        # Validar que a data do primeiro vencimento não é anterior à data do contrato
        if self.data_primeiro_vencimento and self.data_contrato:
            if self.data_primeiro_vencimento < self.data_contrato:
                errors['data_primeiro_vencimento'] = 'A data do primeiro vencimento não pode ser anterior à data do contrato.'

        # Validar juros e multa dentro de limites legais
        if self.percentual_juros_mora and self.percentual_juros_mora > Decimal('2.00'):
            errors['percentual_juros_mora'] = 'O limite legal de juros de mora é 2% ao mês.'

        if self.percentual_multa and self.percentual_multa > Decimal('2.00'):
            errors['percentual_multa'] = 'O limite legal de multa é 2%.'

        # Validar que imóvel pertence à mesma imobiliária do contrato
        if self.imovel_id and self.imobiliaria_id:
            if hasattr(self, 'imovel') and self.imovel.imobiliaria_id != self.imobiliaria_id:
                errors['imovel'] = 'O imóvel deve pertencer à mesma imobiliária do contrato.'
        # NOTA: Comprador NÃO tem campo imobiliaria - um comprador pode
        # comprar imóveis de diferentes imobiliárias através de diferentes contratos

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override do save para calcular campos automáticos"""
        # Executar validações de negócio
        self.full_clean()

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
        parcelas_criadas = []

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

            parcela = Parcela.objects.create(
                contrato=self,
                numero_parcela=numero,
                data_vencimento=data_vencimento,
                valor_original=valor_parcela,
                valor_atual=valor_parcela,
            )
            parcelas_criadas.append(parcela)

            # Avançar para o próximo mês, mantendo o dia de vencimento
            data_vencimento = data_vencimento + relativedelta(months=1)

            # Ajustar dia de vencimento se necessário (ex: 31 em meses com 30 dias)
            if data_vencimento.day != self.dia_vencimento:
                # Usar o último dia do mês se o dia de vencimento não existir naquele mês
                ultimo_dia = (data_vencimento.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)).day
                dia = min(self.dia_vencimento, ultimo_dia)
                data_vencimento = data_vencimento.replace(day=dia)

        return parcelas_criadas

    def gerar_boletos_parcelas(self, parcelas=None, conta_bancaria=None):
        """
        Gera boletos para as parcelas do contrato.

        Args:
            parcelas: Lista de parcelas (opcional, usa todas não pagas se não informado)
            conta_bancaria: Conta bancária para geração (opcional)

        Returns:
            list: Resultados da geração de boletos
        """
        if parcelas is None:
            parcelas = self.parcelas.filter(pago=False)

        # Obter conta bancária se não informada
        if not conta_bancaria:
            imobiliaria = self.imovel.imobiliaria
            conta_bancaria = imobiliaria.contas_bancarias.filter(
                principal=True, ativo=True
            ).first()

        if not conta_bancaria:
            return {'erro': 'Nenhuma conta bancária disponível'}

        resultados = []
        for parcela in parcelas:
            try:
                resultado = parcela.gerar_boleto(conta_bancaria)
                resultados.append({
                    'parcela': parcela.numero_parcela,
                    'sucesso': resultado.get('sucesso', False) if resultado else False,
                    'nosso_numero': resultado.get('nosso_numero', '') if resultado else '',
                })
            except Exception as e:
                resultados.append({
                    'parcela': parcela.numero_parcela,
                    'sucesso': False,
                    'erro': str(e),
                })

        return resultados

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

    @property
    def data_proximo_reajuste(self):
        """
        Calcula a data do proximo reajuste.
        Retorna None se o contrato usa valor fixo (sem reajuste).
        """
        if self.tipo_correcao == TipoCorrecao.FIXO:
            return None

        # Data base para calculo
        if self.data_ultimo_reajuste:
            data_base = self.data_ultimo_reajuste
        else:
            data_base = self.data_contrato

        # Adicionar o prazo de reajuste
        return data_base + relativedelta(months=self.prazo_reajuste_meses)

    def calcular_ciclo_parcela(self, numero_parcela):
        """
        Calcula o ciclo de reajuste de uma parcela.
        Ciclo 1 = meses 1-12, Ciclo 2 = meses 13-24, etc.

        Args:
            numero_parcela: Número da parcela (1-based)

        Returns:
            int: Número do ciclo (1, 2, 3, ...)
        """
        return ((numero_parcela - 1) // self.prazo_reajuste_meses) + 1

    def pode_gerar_boleto(self, numero_parcela):
        """
        Verifica se é possível gerar boleto para uma parcela específica.

        Regra: Só é possível emitir boleto até o 12º mês de cada ciclo.
               No 13º mês (início de novo ciclo), a emissão só é liberada
               APÓS aplicação do reajuste.

        Args:
            numero_parcela: Número da parcela a verificar

        Returns:
            tuple: (pode_gerar: bool, motivo: str)
        """
        ciclo_parcela = self.calcular_ciclo_parcela(numero_parcela)

        # Primeiro ciclo (meses 1-12): sempre pode gerar
        if ciclo_parcela == 1:
            return True, "Primeiro ciclo - liberado"

        # Verificar se o reajuste do ciclo anterior foi aplicado
        from financeiro.models import Reajuste
        reajuste_aplicado = Reajuste.objects.filter(
            contrato=self,
            ciclo=ciclo_parcela
        ).exists()

        if reajuste_aplicado:
            return True, f"Reajuste do ciclo {ciclo_parcela} aplicado"

        return False, f"Reajuste pendente para o ciclo {ciclo_parcela}. Aplique o reajuste antes de gerar boletos."

    def verificar_bloqueio_reajuste(self):
        """
        Verifica e atualiza o status de bloqueio de boleto por reajuste.

        Returns:
            bool: True se está bloqueado, False se liberado
        """
        if self.tipo_correcao == TipoCorrecao.FIXO:
            self.bloqueio_boleto_reajuste = False
            return False

        # Verificar se a próxima parcela a gerar boleto está em um novo ciclo
        proxima_parcela = self.ultimo_mes_boleto_gerado + 1
        if proxima_parcela > self.numero_parcelas:
            self.bloqueio_boleto_reajuste = False
            return False

        ciclo_proxima = self.calcular_ciclo_parcela(proxima_parcela)

        # Se está no primeiro ciclo, não há bloqueio
        if ciclo_proxima == 1:
            self.bloqueio_boleto_reajuste = False
            return False

        # Verificar se reajuste foi aplicado
        pode_gerar, _ = self.pode_gerar_boleto(proxima_parcela)
        self.bloqueio_boleto_reajuste = not pode_gerar
        self.save(update_fields=['bloqueio_boleto_reajuste'])
        return self.bloqueio_boleto_reajuste

    def get_parcelas_ciclo(self, ciclo):
        """
        Retorna as parcelas de um ciclo específico.

        Args:
            ciclo: Número do ciclo (1, 2, 3, ...)

        Returns:
            QuerySet: Parcelas do ciclo
        """
        inicio = (ciclo - 1) * self.prazo_reajuste_meses + 1
        fim = ciclo * self.prazo_reajuste_meses
        return self.parcelas.filter(
            numero_parcela__gte=inicio,
            numero_parcela__lte=fim
        )

    def get_parcelas_a_pagar(self):
        """
        Retorna as parcelas não pagas do contrato.

        Returns:
            QuerySet: Parcelas não pagas ordenadas por vencimento
        """
        return self.parcelas.filter(pago=False).order_by('data_vencimento')

    def get_parcelas_pagas(self):
        """
        Retorna as parcelas pagas do contrato.

        Returns:
            QuerySet: Parcelas pagas ordenadas por data de pagamento
        """
        return self.parcelas.filter(pago=True).order_by('-data_pagamento')

    def get_parcelas_vencidas(self):
        """
        Retorna as parcelas vencidas e não pagas.

        Returns:
            QuerySet: Parcelas vencidas
        """
        return self.parcelas.filter(
            pago=False,
            data_vencimento__lt=timezone.now().date()
        ).order_by('data_vencimento')

    def get_resumo_financeiro(self):
        """
        Retorna um resumo financeiro do contrato.

        Returns:
            dict: Resumo com totais e estatísticas
        """
        from django.db.models import Sum, Count

        parcelas = self.parcelas.all()
        pagas = parcelas.filter(pago=True)
        a_pagar = parcelas.filter(pago=False)
        vencidas = a_pagar.filter(data_vencimento__lt=timezone.now().date())

        total_pago = pagas.aggregate(total=Sum('valor_pago'))['total'] or Decimal('0.00')
        total_a_pagar = a_pagar.aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')
        total_vencido = vencidas.aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')

        # Calcular juros e multa acumulados em parcelas vencidas
        total_juros = vencidas.aggregate(total=Sum('valor_juros'))['total'] or Decimal('0.00')
        total_multa = vencidas.aggregate(total=Sum('valor_multa'))['total'] or Decimal('0.00')

        return {
            'valor_contrato': self.valor_total,
            'valor_entrada': self.valor_entrada,
            'valor_financiado': self.valor_financiado,
            'total_parcelas': parcelas.count(),
            'parcelas_pagas': pagas.count(),
            'parcelas_a_pagar': a_pagar.count(),
            'parcelas_vencidas': vencidas.count(),
            'total_pago': total_pago + self.valor_entrada,
            'total_a_pagar': total_a_pagar,
            'total_vencido': total_vencido,
            'total_juros_acumulado': total_juros,
            'total_multa_acumulada': total_multa,
            'saldo_devedor': self.calcular_saldo_devedor(),
            'progresso_percentual': self.calcular_progresso(),
            'ciclo_atual': self.ciclo_reajuste_atual,
            'bloqueio_reajuste': self.bloqueio_boleto_reajuste,
        }


class PrestacaoIntermediaria(TimeStampedModel):
    """
    Modelo para prestações intermediárias do contrato.

    Prestações intermediárias são parcelas adicionais com valores maiores
    que vencem em meses específicos do contrato (ex: mês 6, 12, 18...).
    Um contrato pode ter até 30 prestações intermediárias.
    """

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='intermediarias',
        verbose_name='Contrato'
    )
    numero_sequencial = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name='Número Sequencial',
        help_text='Número da intermediária (1 a 30)'
    )
    mes_vencimento = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(360)],
        verbose_name='Mês de Vencimento',
        help_text='Mês relativo ao início do contrato (ex: 6 = sexto mês)'
    )
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor',
        help_text='Valor da prestação intermediária'
    )

    # Status de pagamento
    paga = models.BooleanField(
        default=False,
        verbose_name='Paga'
    )
    data_pagamento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de Pagamento'
    )
    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Pago'
    )

    # Vinculação com parcela (quando gerada)
    parcela_vinculada = models.OneToOneField(
        'financeiro.Parcela',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intermediaria_origem',
        verbose_name='Parcela Vinculada',
        help_text='Parcela gerada para esta intermediária'
    )

    # Valor reajustado (após aplicação de índices)
    valor_reajustado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Reajustado',
        help_text='Valor após aplicação de reajustes'
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )

    class Meta:
        verbose_name = 'Prestação Intermediária'
        verbose_name_plural = 'Prestações Intermediárias'
        ordering = ['contrato', 'numero_sequencial']
        unique_together = [['contrato', 'numero_sequencial']]
        indexes = [
            models.Index(fields=['contrato', 'mes_vencimento']),
            models.Index(fields=['paga']),
        ]

    def __str__(self):
        return f"Intermediária {self.numero_sequencial} - Mês {self.mes_vencimento} - Contrato {self.contrato.numero_contrato}"

    def clean(self):
        """Validações de negócio da prestação intermediária"""
        super().clean()
        errors = {}

        # Validar número sequencial (1 a 30)
        if self.numero_sequencial:
            if self.numero_sequencial < 1 or self.numero_sequencial > 30:
                errors['numero_sequencial'] = 'O número sequencial deve estar entre 1 e 30.'

        # Validar mês de vencimento dentro do prazo do contrato
        if self.mes_vencimento and hasattr(self, 'contrato') and self.contrato:
            if self.mes_vencimento > self.contrato.numero_parcelas:
                errors['mes_vencimento'] = f'O mês de vencimento não pode exceder o prazo do contrato ({self.contrato.numero_parcelas} meses).'

        # Validar que não ultrapassa o limite de intermediárias do contrato
        if hasattr(self, 'contrato') and self.contrato:
            limite = self.contrato.quantidade_intermediarias
            if limite and self.numero_sequencial and self.numero_sequencial > limite:
                errors['numero_sequencial'] = f'O contrato permite no máximo {limite} prestações intermediárias.'

        # Validar valor mínimo
        if self.valor and self.valor <= Decimal('0'):
            errors['valor'] = 'O valor da intermediária deve ser maior que zero.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override do save para executar validações"""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def valor_atual(self):
        """Retorna o valor atual (reajustado ou original)"""
        return self.valor_reajustado if self.valor_reajustado else self.valor

    @property
    def data_vencimento(self):
        """Calcula a data de vencimento baseada no mês relativo"""
        from dateutil.relativedelta import relativedelta
        data_base = self.contrato.data_primeiro_vencimento
        return data_base + relativedelta(months=self.mes_vencimento - 1)

    @property
    def ciclo_reajuste(self):
        """Retorna o ciclo de reajuste desta intermediária"""
        return self.contrato.calcular_ciclo_parcela(self.mes_vencimento)

    def gerar_parcela(self):
        """
        Gera uma parcela vinculada a esta intermediária.

        Returns:
            Parcela: A parcela gerada ou None se já existir
        """
        if self.parcela_vinculada:
            return self.parcela_vinculada

        from financeiro.models import Parcela

        parcela = Parcela.objects.create(
            contrato=self.contrato,
            numero_parcela=0,  # Intermediárias usam número 0 ou negativo
            data_vencimento=self.data_vencimento,
            valor_original=self.valor,
            valor_atual=self.valor_atual,
            tipo_parcela=TipoPrestacao.INTERMEDIARIA,
            ciclo_reajuste=self.ciclo_reajuste,
        )

        self.parcela_vinculada = parcela
        self.save(update_fields=['parcela_vinculada'])

        return parcela

    def aplicar_reajuste(self, percentual):
        """
        Aplica reajuste no valor da intermediária.

        Args:
            percentual: Percentual de reajuste (ex: 5.5 para 5,5%)
        """
        if self.paga:
            return

        valor_base = self.valor_reajustado if self.valor_reajustado else self.valor
        fator = 1 + (Decimal(str(percentual)) / 100)
        self.valor_reajustado = valor_base * fator
        self.save(update_fields=['valor_reajustado'])

        # Atualizar parcela vinculada se existir
        if self.parcela_vinculada:
            self.parcela_vinculada.valor_atual = self.valor_reajustado
            self.parcela_vinculada.save(update_fields=['valor_atual'])
