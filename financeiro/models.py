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
from core.models import TimeStampedModel, ContaBancaria


class StatusBoleto(models.TextChoices):
    """Status do boleto bancário"""
    NAO_GERADO = 'NAO_GERADO', 'Não Gerado'
    GERADO = 'GERADO', 'Gerado'
    REGISTRADO = 'REGISTRADO', 'Registrado no Banco'
    PAGO = 'PAGO', 'Pago'
    VENCIDO = 'VENCIDO', 'Vencido'
    CANCELADO = 'CANCELADO', 'Cancelado'
    PROTESTADO = 'PROTESTADO', 'Protestado'
    BAIXADO = 'BAIXADO', 'Baixado'


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

    # =========================================================================
    # DADOS DO BOLETO BANCÁRIO
    # =========================================================================

    conta_bancaria = models.ForeignKey(
        ContaBancaria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parcelas',
        verbose_name='Conta Bancária',
        help_text='Conta bancária usada para gerar o boleto'
    )

    # Identificação do Boleto
    nosso_numero = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Nosso Número',
        help_text='Número de identificação do boleto no banco'
    )
    numero_documento = models.CharField(
        max_length=25,
        blank=True,
        verbose_name='Número do Documento',
        help_text='Número do documento para o cliente'
    )

    # Código de Barras e Linha Digitável
    codigo_barras = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Código de Barras',
        help_text='Código de barras numérico do boleto'
    )
    linha_digitavel = models.CharField(
        max_length=60,
        blank=True,
        verbose_name='Linha Digitável',
        help_text='Linha digitável para pagamento'
    )

    # Arquivo PDF do Boleto
    boleto_pdf = models.FileField(
        upload_to='boletos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Boleto PDF',
        help_text='Arquivo PDF do boleto gerado'
    )
    boleto_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='URL do Boleto',
        help_text='URL externa do boleto (se houver)'
    )

    # Status e Controle do Boleto
    status_boleto = models.CharField(
        max_length=15,
        choices=StatusBoleto.choices,
        default=StatusBoleto.NAO_GERADO,
        verbose_name='Status do Boleto'
    )
    data_geracao_boleto = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Geração',
        help_text='Data/hora em que o boleto foi gerado'
    )
    data_registro_boleto = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Registro',
        help_text='Data/hora em que o boleto foi registrado no banco'
    )
    data_pagamento_boleto = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data Pagamento Boleto',
        help_text='Data/hora do pagamento confirmado pelo banco'
    )

    # Valores do Boleto (podem diferir do valor da parcela)
    valor_boleto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor do Boleto',
        help_text='Valor nominal do boleto gerado'
    )
    valor_pago_boleto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Pago via Boleto',
        help_text='Valor efetivamente pago via boleto'
    )

    # Dados de Retorno Bancário
    banco_pagador = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Banco Pagador',
        help_text='Código do banco onde foi pago'
    )
    agencia_pagadora = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Agência Pagadora'
    )
    motivo_rejeicao = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Motivo Rejeição/Baixa',
        help_text='Motivo de rejeição ou baixa do boleto'
    )

    # PIX do Boleto (Boleto Híbrido)
    pix_copia_cola = models.TextField(
        blank=True,
        verbose_name='PIX Copia e Cola',
        help_text='Código PIX para pagamento alternativo'
    )
    pix_qrcode = models.TextField(
        blank=True,
        verbose_name='PIX QR Code',
        help_text='Dados do QR Code PIX em base64'
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
            models.Index(fields=['status_boleto']),
            models.Index(fields=['nosso_numero']),
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
        multa = self.valor_atual * (self.contrato.percentual_multa / Decimal('100'))

        # Calcular juros (proporcional aos dias de atraso)
        # Juros = valor * (taxa_mensal / 30) * dias_atraso
        juros = self.valor_atual * (self.contrato.percentual_juros_mora / Decimal('100')) * (Decimal(dias_atraso) / Decimal('30'))

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

    # =========================================================================
    # MÉTODOS RELACIONADOS AO BOLETO
    # =========================================================================

    @property
    def tem_boleto(self):
        """Verifica se a parcela tem boleto gerado"""
        return self.status_boleto != StatusBoleto.NAO_GERADO and bool(self.nosso_numero)

    @property
    def boleto_pode_ser_pago(self):
        """Verifica se o boleto ainda pode ser pago"""
        return self.status_boleto in [
            StatusBoleto.GERADO,
            StatusBoleto.REGISTRADO,
            StatusBoleto.VENCIDO
        ]

    def gerar_numero_documento(self):
        """Gera o número do documento para o boleto"""
        # Formato: CONTRATO-PARCELA/TOTAL (ex: 001-005/012)
        return f"{self.contrato.numero_contrato}-{self.numero_parcela:03d}/{self.contrato.numero_parcelas:03d}"

    def calcular_valores_hoje(self):
        """
        Calcula os valores de multa, juros e desconto para pagamento hoje.

        Returns:
            dict: Dicionário com valores calculados e configurações
        """
        from datetime import date, timedelta

        hoje = date.today()
        config = self.contrato.get_config_boleto()

        # Calcular juros e multa para hoje
        juros_hoje, multa_hoje = self.calcular_juros_multa(data_referencia=hoje)

        # Calcular desconto (se aplicável - antes do vencimento)
        desconto_hoje = Decimal('0.00')
        desconto_disponivel = False

        if hoje <= self.data_vencimento:
            valor_desconto_config = config.get('valor_desconto', 0) or 0
            if valor_desconto_config > 0:
                dias_desconto = config.get('dias_desconto', 0) or 0
                # Verificar se hoje está dentro do período de desconto
                data_limite_desconto = self.data_vencimento - timedelta(days=dias_desconto)

                if hoje >= data_limite_desconto:
                    desconto_disponivel = True
                    if config.get('tipo_valor_desconto') == 'PERCENTUAL':
                        desconto_hoje = self.valor_atual * (Decimal(str(valor_desconto_config)) / Decimal('100'))
                    else:
                        desconto_hoje = Decimal(str(valor_desconto_config))

        # Valor total para pagamento hoje
        valor_total_hoje = self.valor_atual + juros_hoje + multa_hoje - desconto_hoje

        # Dias de atraso
        dias_atraso = 0
        if hoje > self.data_vencimento:
            dias_atraso = (hoje - self.data_vencimento).days

        # Configurações do contrato
        return {
            # Valores calculados para hoje
            'valor_original': self.valor_atual,
            'multa_hoje': multa_hoje,
            'juros_hoje': juros_hoje,
            'desconto_hoje': desconto_hoje,
            'desconto_disponivel': desconto_disponivel,
            'valor_total_hoje': valor_total_hoje,
            'dias_atraso': dias_atraso,
            'vencido': hoje > self.data_vencimento,

            # Configurações do contrato (para exibição)
            'config_multa_percentual': config.get('valor_multa', 0) or 0,
            'config_multa_tipo': config.get('tipo_valor_multa', 'PERCENTUAL'),
            'config_juros_percentual': config.get('valor_juros', 0) or 0,
            'config_juros_tipo': config.get('tipo_valor_juros', 'PERCENTUAL'),
            'config_desconto_valor': config.get('valor_desconto', 0) or 0,
            'config_desconto_tipo': config.get('tipo_valor_desconto', 'PERCENTUAL'),
            'config_desconto_dias': config.get('dias_desconto', 0) or 0,
            'config_dias_carencia': config.get('dias_carencia', 0) or 0,
        }

    def obter_proximos_nosso_numero(self, conta_bancaria):
        """
        Obtém o próximo nosso número disponível para a conta bancária.
        Incrementa o contador na conta bancária.
        """
        conta_bancaria.nosso_numero_atual += 1
        conta_bancaria.save(update_fields=['nosso_numero_atual'])
        return conta_bancaria.nosso_numero_atual

    def gerar_boleto(self, conta_bancaria=None, force=False, enviar_email=True):
        """
        Gera o boleto para esta parcela.

        Args:
            conta_bancaria: Conta bancária a ser usada (opcional, usa a principal)
            force: Se True, regenera mesmo que já exista boleto
            enviar_email: Se True, envia email para o comprador com o boleto

        Returns:
            dict: Dados do boleto gerado ou None se falhar
        """
        from financeiro.services.boleto_service import BoletoService

        # Não gerar boleto para parcelas já pagas
        if self.pago:
            return None

        # Verificar se já tem boleto e não é para forçar
        if self.tem_boleto and not force:
            return {
                'sucesso': True,
                'nosso_numero': self.nosso_numero,
                'linha_digitavel': self.linha_digitavel,
                'codigo_barras': self.codigo_barras,
            }

        # Obter conta bancária
        if not conta_bancaria:
            conta_bancaria = self.conta_bancaria
            if not conta_bancaria:
                # Buscar conta principal da imobiliária
                imobiliaria = self.contrato.imovel.imobiliaria
                conta_bancaria = imobiliaria.contas_bancarias.filter(
                    principal=True, ativo=True
                ).first()

        if not conta_bancaria:
            raise ValueError("Nenhuma conta bancária disponível para gerar boleto")

        # Usar o serviço de boleto
        service = BoletoService()
        resultado = service.gerar_boleto(self, conta_bancaria)

        if resultado.get('sucesso'):
            self.conta_bancaria = conta_bancaria
            self.nosso_numero = resultado.get('nosso_numero', '')
            self.numero_documento = self.gerar_numero_documento()
            self.codigo_barras = resultado.get('codigo_barras', '')
            self.linha_digitavel = resultado.get('linha_digitavel', '')
            self.valor_boleto = resultado.get('valor', self.valor_atual)
            self.status_boleto = StatusBoleto.GERADO
            self.data_geracao_boleto = timezone.now()

            # Salvar PDF se disponível
            if resultado.get('pdf_content'):
                from django.core.files.base import ContentFile
                nome_arquivo = f"boleto_{self.contrato.numero_contrato}_{self.numero_parcela}.pdf"
                self.boleto_pdf.save(nome_arquivo, ContentFile(resultado['pdf_content']), save=False)

            # PIX se disponível
            if resultado.get('pix_copia_cola'):
                self.pix_copia_cola = resultado['pix_copia_cola']
            if resultado.get('pix_qrcode'):
                self.pix_qrcode = resultado['pix_qrcode']

            self.save()

            # Enviar email para o comprador
            if enviar_email:
                try:
                    from notificacoes.boleto_notificacao import BoletoNotificacaoService
                    notificacao_service = BoletoNotificacaoService()
                    email_result = notificacao_service.notificar_boleto_criado(self)
                    resultado['email_enviado'] = email_result.get('sucesso', False)
                    resultado['email_erro'] = email_result.get('erro', '')
                except Exception as e:
                    # Não falhar a geração do boleto por erro de email
                    resultado['email_enviado'] = False
                    resultado['email_erro'] = str(e)

        return resultado

    def cancelar_boleto(self, motivo=''):
        """Cancela o boleto da parcela"""
        if self.status_boleto in [StatusBoleto.NAO_GERADO, StatusBoleto.CANCELADO]:
            return False

        self.status_boleto = StatusBoleto.CANCELADO
        self.motivo_rejeicao = motivo
        self.save()
        return True

    def registrar_pagamento_boleto(self, valor_pago, data_pagamento=None,
                                    banco_pagador='', agencia_pagadora=''):
        """Registra o pagamento do boleto com dados bancários"""
        if data_pagamento is None:
            data_pagamento = timezone.now()

        self.status_boleto = StatusBoleto.PAGO
        self.data_pagamento_boleto = data_pagamento
        self.valor_pago_boleto = valor_pago
        self.banco_pagador = banco_pagador
        self.agencia_pagadora = agencia_pagadora

        # Também registrar o pagamento da parcela
        self.registrar_pagamento(
            valor_pago=valor_pago,
            data_pagamento=data_pagamento.date() if hasattr(data_pagamento, 'date') else data_pagamento,
            observacoes=f'Pago via boleto. Banco: {banco_pagador} Ag: {agencia_pagadora}'
        )


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


# =============================================================================
# MODELOS CNAB - ARQUIVOS REMESSA E RETORNO
# =============================================================================

class StatusArquivoRemessa(models.TextChoices):
    """Status do arquivo de remessa"""
    GERADO = 'GERADO', 'Gerado'
    ENVIADO = 'ENVIADO', 'Enviado ao Banco'
    PROCESSADO = 'PROCESSADO', 'Processado'
    ERRO = 'ERRO', 'Erro'


class ArquivoRemessa(TimeStampedModel):
    """
    Modelo para gerenciar arquivos de remessa CNAB.
    Cada arquivo contém uma lista de boletos a serem registrados no banco.
    """

    conta_bancaria = models.ForeignKey(
        ContaBancaria,
        on_delete=models.PROTECT,
        related_name='arquivos_remessa',
        verbose_name='Conta Bancária'
    )
    numero_remessa = models.PositiveIntegerField(
        verbose_name='Número da Remessa',
        help_text='Número sequencial da remessa para esta conta'
    )
    layout = models.CharField(
        max_length=10,
        choices=[
            ('CNAB_240', 'CNAB 240'),
            ('CNAB_400', 'CNAB 400'),
        ],
        default='CNAB_240',
        verbose_name='Layout'
    )

    # Arquivo
    arquivo = models.FileField(
        upload_to='cnab/remessa/%Y/%m/',
        verbose_name='Arquivo',
        help_text='Arquivo CNAB gerado'
    )
    nome_arquivo = models.CharField(
        max_length=100,
        verbose_name='Nome do Arquivo'
    )

    # Status e controle
    status = models.CharField(
        max_length=15,
        choices=StatusArquivoRemessa.choices,
        default=StatusArquivoRemessa.GERADO,
        verbose_name='Status'
    )
    data_geracao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Geração'
    )
    data_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Envio ao Banco'
    )

    # Estatísticas
    quantidade_boletos = models.PositiveIntegerField(
        default=0,
        verbose_name='Quantidade de Boletos'
    )
    valor_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor Total'
    )

    # Observações e erros
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )
    erro_mensagem = models.TextField(
        blank=True,
        verbose_name='Mensagem de Erro'
    )

    class Meta:
        verbose_name = 'Arquivo de Remessa'
        verbose_name_plural = 'Arquivos de Remessa'
        ordering = ['-data_geracao']
        unique_together = [['conta_bancaria', 'numero_remessa']]
        indexes = [
            models.Index(fields=['conta_bancaria', 'numero_remessa']),
            models.Index(fields=['status']),
            models.Index(fields=['data_geracao']),
        ]

    def __str__(self):
        return f"Remessa {self.numero_remessa} - {self.conta_bancaria.descricao} ({self.get_status_display()})"

    @property
    def pode_reenviar(self):
        """Verifica se a remessa pode ser reenviada"""
        return self.status in [StatusArquivoRemessa.GERADO, StatusArquivoRemessa.ERRO]

    def marcar_enviado(self):
        """Marca a remessa como enviada"""
        self.status = StatusArquivoRemessa.ENVIADO
        self.data_envio = timezone.now()
        self.save()

    def marcar_processado(self):
        """Marca a remessa como processada"""
        self.status = StatusArquivoRemessa.PROCESSADO
        self.save()
        # Atualizar status dos boletos
        self.itens.update(processado=True)

    def marcar_erro(self, mensagem):
        """Marca a remessa com erro"""
        self.status = StatusArquivoRemessa.ERRO
        self.erro_mensagem = mensagem
        self.save()


class ItemRemessa(TimeStampedModel):
    """
    Itens (boletos) incluídos em um arquivo de remessa.
    Relaciona parcelas com arquivos de remessa.
    """

    arquivo_remessa = models.ForeignKey(
        ArquivoRemessa,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Arquivo de Remessa'
    )
    parcela = models.ForeignKey(
        'Parcela',
        on_delete=models.PROTECT,
        related_name='itens_remessa',
        verbose_name='Parcela'
    )

    # Dados do momento da inclusão
    nosso_numero = models.CharField(
        max_length=30,
        verbose_name='Nosso Número'
    )
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor'
    )
    data_vencimento = models.DateField(
        verbose_name='Data de Vencimento'
    )

    # Status de processamento
    processado = models.BooleanField(
        default=False,
        verbose_name='Processado',
        help_text='Indica se o retorno já foi processado'
    )
    codigo_ocorrencia = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Código de Ocorrência',
        help_text='Código retornado pelo banco'
    )
    descricao_ocorrencia = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Descrição da Ocorrência'
    )

    class Meta:
        verbose_name = 'Item de Remessa'
        verbose_name_plural = 'Itens de Remessa'
        ordering = ['arquivo_remessa', 'id']
        unique_together = [['arquivo_remessa', 'parcela']]

    def __str__(self):
        return f"Item {self.nosso_numero} - Remessa {self.arquivo_remessa.numero_remessa}"


class StatusArquivoRetorno(models.TextChoices):
    """Status do arquivo de retorno"""
    PENDENTE = 'PENDENTE', 'Pendente de Processamento'
    PROCESSADO = 'PROCESSADO', 'Processado'
    PROCESSADO_PARCIAL = 'PROCESSADO_PARCIAL', 'Processado Parcialmente'
    ERRO = 'ERRO', 'Erro'


class ArquivoRetorno(TimeStampedModel):
    """
    Modelo para gerenciar arquivos de retorno CNAB.
    Arquivos enviados pelo banco com informações de pagamentos e ocorrências.
    """

    conta_bancaria = models.ForeignKey(
        ContaBancaria,
        on_delete=models.PROTECT,
        related_name='arquivos_retorno',
        verbose_name='Conta Bancária'
    )

    # Arquivo
    arquivo = models.FileField(
        upload_to='cnab/retorno/%Y/%m/',
        verbose_name='Arquivo',
        help_text='Arquivo CNAB de retorno'
    )
    nome_arquivo = models.CharField(
        max_length=100,
        verbose_name='Nome do Arquivo'
    )
    layout = models.CharField(
        max_length=10,
        choices=[
            ('CNAB_240', 'CNAB 240'),
            ('CNAB_400', 'CNAB 400'),
        ],
        default='CNAB_240',
        verbose_name='Layout'
    )

    # Status e controle
    status = models.CharField(
        max_length=20,
        choices=StatusArquivoRetorno.choices,
        default=StatusArquivoRetorno.PENDENTE,
        verbose_name='Status'
    )
    data_upload = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Upload'
    )
    data_processamento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Processamento'
    )
    processado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Processado por'
    )

    # Estatísticas
    total_registros = models.PositiveIntegerField(
        default=0,
        verbose_name='Total de Registros'
    )
    registros_processados = models.PositiveIntegerField(
        default=0,
        verbose_name='Registros Processados'
    )
    registros_erro = models.PositiveIntegerField(
        default=0,
        verbose_name='Registros com Erro'
    )
    valor_total_pago = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor Total Pago'
    )

    # Observações e erros
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )
    erro_mensagem = models.TextField(
        blank=True,
        verbose_name='Mensagem de Erro'
    )

    class Meta:
        verbose_name = 'Arquivo de Retorno'
        verbose_name_plural = 'Arquivos de Retorno'
        ordering = ['-data_upload']
        indexes = [
            models.Index(fields=['conta_bancaria']),
            models.Index(fields=['status']),
            models.Index(fields=['data_upload']),
        ]

    def __str__(self):
        return f"Retorno {self.nome_arquivo} - {self.conta_bancaria.descricao} ({self.get_status_display()})"

    @property
    def pode_reprocessar(self):
        """Verifica se o arquivo pode ser reprocessado"""
        return self.status in [StatusArquivoRetorno.PENDENTE, StatusArquivoRetorno.ERRO]


class ItemRetorno(TimeStampedModel):
    """
    Itens processados de um arquivo de retorno CNAB.
    Cada item representa uma ocorrência (pagamento, rejeição, etc.)
    """

    arquivo_retorno = models.ForeignKey(
        ArquivoRetorno,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Arquivo de Retorno'
    )
    parcela = models.ForeignKey(
        'Parcela',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_retorno',
        verbose_name='Parcela',
        help_text='Parcela identificada (pode ser nulo se não encontrada)'
    )

    # Dados do registro
    nosso_numero = models.CharField(
        max_length=30,
        verbose_name='Nosso Número'
    )
    numero_documento = models.CharField(
        max_length=25,
        blank=True,
        verbose_name='Número do Documento'
    )

    # Ocorrência
    codigo_ocorrencia = models.CharField(
        max_length=10,
        verbose_name='Código de Ocorrência'
    )
    descricao_ocorrencia = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Descrição da Ocorrência'
    )
    tipo_ocorrencia = models.CharField(
        max_length=20,
        choices=[
            ('ENTRADA', 'Entrada Confirmada'),
            ('LIQUIDACAO', 'Liquidação/Pagamento'),
            ('BAIXA', 'Baixa'),
            ('REJEICAO', 'Rejeição'),
            ('PROTESTO', 'Protesto'),
            ('TARIFA', 'Tarifa/Taxa'),
            ('OUTROS', 'Outros'),
        ],
        default='OUTROS',
        verbose_name='Tipo de Ocorrência'
    )

    # Valores
    valor_titulo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor do Título'
    )
    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Pago'
    )
    valor_juros = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor de Juros'
    )
    valor_multa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor de Multa'
    )
    valor_desconto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor de Desconto'
    )
    valor_tarifa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor de Tarifa'
    )

    # Datas
    data_ocorrencia = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data da Ocorrência'
    )
    data_credito = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de Crédito'
    )

    # Controle
    processado = models.BooleanField(
        default=False,
        verbose_name='Processado',
        help_text='Indica se a baixa foi realizada no sistema'
    )
    erro_processamento = models.TextField(
        blank=True,
        verbose_name='Erro de Processamento'
    )

    class Meta:
        verbose_name = 'Item de Retorno'
        verbose_name_plural = 'Itens de Retorno'
        ordering = ['arquivo_retorno', 'id']
        indexes = [
            models.Index(fields=['nosso_numero']),
            models.Index(fields=['codigo_ocorrencia']),
            models.Index(fields=['tipo_ocorrencia']),
        ]

    def __str__(self):
        return f"Retorno {self.nosso_numero} - {self.get_tipo_ocorrencia_display()}"

    def processar_baixa(self):
        """
        Processa a baixa do item no sistema.
        Atualiza o status do boleto e registra o pagamento se for liquidação.
        """
        if self.processado:
            return False

        if not self.parcela:
            self.erro_processamento = "Parcela não encontrada"
            self.save()
            return False

        try:
            if self.tipo_ocorrencia == 'LIQUIDACAO':
                # Registrar pagamento
                self.parcela.registrar_pagamento_boleto(
                    valor_pago=self.valor_pago or self.valor_titulo,
                    data_pagamento=self.data_ocorrencia or timezone.now(),
                    banco_pagador='',
                    agencia_pagadora=''
                )
            elif self.tipo_ocorrencia == 'ENTRADA':
                # Confirmar registro no banco
                self.parcela.status_boleto = StatusBoleto.REGISTRADO
                self.parcela.data_registro_boleto = timezone.now()
                self.parcela.save()
            elif self.tipo_ocorrencia == 'BAIXA':
                self.parcela.status_boleto = StatusBoleto.BAIXADO
                self.parcela.motivo_rejeicao = self.descricao_ocorrencia
                self.parcela.save()
            elif self.tipo_ocorrencia == 'REJEICAO':
                self.parcela.status_boleto = StatusBoleto.CANCELADO
                self.parcela.motivo_rejeicao = self.descricao_ocorrencia
                self.parcela.save()
            elif self.tipo_ocorrencia == 'PROTESTO':
                self.parcela.status_boleto = StatusBoleto.PROTESTADO
                self.parcela.save()

            self.processado = True
            self.save()
            return True

        except Exception as e:
            self.erro_processamento = str(e)
            self.save()
            return False
