"""
Modelos Financeiros - Parcelas, Reajustes e Pagamentos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from datetime import timedelta
import logging

from core.models import TimeStampedModel, ContaBancaria

logger = logging.getLogger(__name__)


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


class TipoParcela(models.TextChoices):
    """Tipos de parcela"""
    NORMAL = 'NORMAL', 'Normal'
    INTERMEDIARIA = 'INTERMEDIARIA', 'Intermediária'
    ENTRADA = 'ENTRADA', 'Entrada'


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

    # Tipo e ciclo de reajuste
    tipo_parcela = models.CharField(
        max_length=15,
        choices=TipoParcela.choices,
        default=TipoParcela.NORMAL,
        verbose_name='Tipo de Parcela'
    )
    ciclo_reajuste = models.PositiveIntegerField(
        default=1,
        verbose_name='Ciclo de Reajuste',
        help_text='Ciclo de reajuste da parcela (1 = meses 1-12, 2 = meses 13-24, etc.)'
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
    # Breakdown amortização/juros embutidos (Tabela Price e SAC)
    amortizacao = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Amortização',
        help_text='Parcela de amortização do principal embutida nesta prestação'
    )
    juros_embutido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Juros Embutidos',
        help_text='Parcela de juros do financiamento embutida nesta prestação'
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
        help_text='Sequencial bruto do nosso número (sem convênio, sem DV). Usado para conciliação CNAB.'
    )
    nosso_numero_formatado = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Nosso Número Formatado',
        help_text='Nosso número completo conforme impresso no boleto (convênio + sequencial + DV). Usado para conciliação OFX.'
    )
    nosso_numero_dv = models.CharField(
        max_length=2,
        blank=True,
        verbose_name='DV do Nosso Número',
        help_text='Dígito verificador do nosso número (calculado pela API / banco).'
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
    boleto_pdf_db = models.BinaryField(
        null=True,
        blank=True,
        editable=False,
        verbose_name='PDF do boleto (banco de dados)',
        help_text='Cópia do PDF em banco de dados — persiste em storage efêmero (Render)'
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
            # Compound indexes for common dashboard/vencimento queries
            models.Index(fields=['pago', 'data_vencimento'], name='fin_parcela_pago_venc_idx'),
            models.Index(fields=['contrato', 'pago', 'data_vencimento'], name='fin_parcela_ctrt_pago_venc_idx'),
        ]
        constraints = [
            # Nosso número único por conta bancária quando preenchido — evita baixa duplicada
            # Permite reutilização do mesmo nosso_numero em bancos diferentes
            models.UniqueConstraint(
                fields=['conta_bancaria', 'nosso_numero'],
                condition=~Q(nosso_numero=''),
                name='unique_nosso_numero_por_conta',
            ),
        ]

    def __str__(self):
        return f"Parcela {self.numero_parcela}/{self.contrato.numero_parcelas} - Contrato {self.contrato.numero_contrato}"

    def clean(self):
        """Validações de negócio da parcela"""
        super().clean()
        errors = {}

        # Validar que não permite boleto para parcela já paga
        if self.pago and self.status_boleto == StatusBoleto.GERADO:
            # Se a parcela está paga e tentando gerar boleto, é um problema
            pass  # Tratado no método gerar_boleto

        # Validar valores positivos
        if self.valor_original is not None and self.valor_original <= Decimal('0'):
            errors['valor_original'] = 'O valor original deve ser maior que zero.'

        if self.valor_atual is not None and self.valor_atual <= Decimal('0'):
            errors['valor_atual'] = 'O valor atual deve ser maior que zero.'

        # Validar data de pagamento não pode ser futura
        if self.data_pagamento and self.data_pagamento > timezone.localdate():
            errors['data_pagamento'] = 'A data de pagamento não pode ser no futuro.'

        # Validar que valor pago é informado quando pago=True
        if self.pago and not self.valor_pago:
            errors['valor_pago'] = 'Informe o valor pago ao marcar a parcela como paga.'

        # Validar ciclo de reajuste
        if self.ciclo_reajuste is not None and self.ciclo_reajuste < 1:
            errors['ciclo_reajuste'] = 'O ciclo de reajuste deve ser pelo menos 1.'

        if errors:
            raise ValidationError(errors)

    def pode_gerar_boleto(self):
        """
        Verifica se é possível gerar boleto para esta parcela.

        Regra de cascata: se QUALQUER ciclo entre 2 e o ciclo desta parcela
        já venceu (hoje >= data_prevista) e ainda não foi aplicado, todos os
        boletos desse ciclo em diante ficam bloqueados.

        Índice FIXO nunca bloqueia.

        Returns:
            tuple: (pode_gerar: bool, motivo: str)
        """
        if self.pago:
            return False, "Parcela já está paga."

        if self.status_boleto == StatusBoleto.PAGO:
            return False, "Boleto já foi pago."

        # Índice FIXO: sempre pode gerar
        from contratos.models import TipoCorrecao
        if self.contrato.tipo_correcao == TipoCorrecao.FIXO:
            return True, "Índice FIXO — sem necessidade de reajuste."

        prazo = self.contrato.prazo_reajuste_meses or 12
        ciclo_da_parcela = (self.numero_parcela - 1) // prazo + 1

        if ciclo_da_parcela <= 1:
            return True, "Primeiro ciclo — liberado."

        from dateutil.relativedelta import relativedelta
        from django.utils import timezone as tz

        hoje = tz.now().date()

        # Verifica em cascata do ciclo 2 até o ciclo desta parcela
        for ciclo_check in range(2, ciclo_da_parcela + 1):
            data_reajuste = (
                self.contrato.data_contrato
                + relativedelta(months=(ciclo_check - 1) * prazo)
            )
            if hoje < data_reajuste:
                # Ciclo ainda não venceu — os subsequentes também não
                break

            reajuste_aplicado = Reajuste.objects.filter(
                contrato=self.contrato,
                ciclo=ciclo_check,
                aplicado=True
            ).exists()
            if not reajuste_aplicado:
                return False, (
                    f"Reajuste do ciclo {ciclo_check} pendente desde "
                    f"{data_reajuste.strftime('%d/%m/%Y')}. "
                    f"Execute o reajuste antes de gerar boletos."
                )

        return True, "Liberado para geração."

    @property
    def valor_total(self):
        """Calcula o valor total da parcela (valor atual + juros + multa - desconto)"""
        return self.valor_atual + self.valor_juros + self.valor_multa - self.valor_desconto

    @property
    def dias_atraso(self):
        """Calcula quantos dias de atraso a parcela possui"""
        if self.pago:
            return 0

        hoje = timezone.localdate()
        if hoje > self.data_vencimento:
            return (hoje - self.data_vencimento).days
        return 0

    @property
    def esta_vencida(self):
        """Verifica se a parcela está vencida"""
        return not self.pago and timezone.localdate() > self.data_vencimento

    def calcular_juros_multa(self, data_referencia=None):
        """
        Calcula juros e multa com base na data de referência
        Se data_referencia não for fornecida, usa a data atual
        """
        if self.pago:
            return Decimal('0.00'), Decimal('0.00')

        if data_referencia is None:
            data_referencia = timezone.localdate()

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

    def registrar_pagamento(self, valor_pago, data_pagamento=None, observacoes='',
                            valor_minimo=None, validar_minimo=True):
        """
        Registra o pagamento da parcela.

        Args:
            valor_pago: Valor efetivamente pago
            data_pagamento: Data do pagamento (default: hoje)
            observacoes: Observacoes sobre o pagamento
            valor_minimo: Valor minimo permitido (default: R$ 0.01)
            validar_minimo: Se True, valida contra valor minimo

        Raises:
            ValidationError: Se valor_pago for menor que valor_minimo

        Item 2.6 do Roadmap: Nao permitir pagamento menor que valor minimo.
        """
        if data_pagamento is None:
            data_pagamento = timezone.localdate()

        # Item 2.6: Validar valor minimo de pagamento
        if validar_minimo:
            from contratos.validators import validar_valor_minimo_pagamento
            if valor_minimo is None:
                valor_minimo = Decimal('0.01')
            validar_valor_minimo_pagamento(valor_pago, valor_minimo)

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

    def get_nosso_numero_formatado(self):
        """
        Retorna o nosso número formatado com zeros à esquerda conforme o banco.

        Prefere o valor já armazenado em ``nosso_numero_formatado`` (gravado a
        partir da resposta da boleto_cnab_api — fonte da verdade para conciliação
        OFX). Em caso de ausência, reconstrói a partir do sequencial bruto.

        Returns:
            str: Nosso número formatado
        """
        # Valor autoritativo vindo da API (PR#32/#33 do boleto_cnab_api)
        if self.nosso_numero_formatado:
            return self.nosso_numero_formatado

        if not self.nosso_numero:
            return ''

        # Remover caracteres não numéricos
        nosso_numero = ''.join(filter(str.isdigit, str(self.nosso_numero)))

        if not nosso_numero:
            return self.nosso_numero

        # Tamanhos padrão por banco (conforme BRCobranca)
        tamanhos = {
            '001': 17,  # Banco do Brasil
            '033': 13,  # Santander
            '104': 17,  # Caixa
            '237': 11,  # Bradesco
            '341': 8,   # Itau
            '422': 9,   # Safra
            '748': 5,   # Sicredi
            '756': 7,   # Sicoob
            '084': 10,  # Unicred
            '136': 10,  # Unicred
        }

        # Obter código do banco da conta bancária
        if self.conta_bancaria:
            codigo_banco = self.conta_bancaria.banco

            # BB (001): formato = convenio(8) + sequencial(9) = 17 dígitos.
            # boleto_cnab_api PR#32: nosso_numero_formatado vem completo da API.
            # Se o DB armazena só o sequencial (fallback), reconstrói o display.
            if codigo_banco == '001' and self.conta_bancaria.convenio:
                seq = nosso_numero
                if len(seq) <= 10:
                    convenio_str = str(self.conta_bancaria.convenio).zfill(8)
                    return convenio_str + seq.zfill(9)
                # Já inclui o convenio — devolve como está (zfill para 17)
                return seq.zfill(17)

            tamanho = tamanhos.get(codigo_banco, 10)  # Padrão: 10 dígitos
            return nosso_numero.zfill(tamanho)

        # Se não tiver conta bancária, retornar com 10 dígitos (padrão)
        return nosso_numero.zfill(10)

    def calcular_valores_hoje(self):
        """
        Calcula os valores de multa, juros e desconto para pagamento hoje.

        Returns:
            dict: Dicionário com valores calculados e configurações
        """
        from datetime import date

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

            # Configurações do contrato (para exibição — valores efetivamente usados no cálculo)
            'config_multa_percentual': self.contrato.percentual_multa,
            'config_multa_tipo': 'PERCENTUAL',
            'config_juros_percentual': self.contrato.percentual_juros_mora,
            'config_juros_tipo': 'PERCENTUAL',
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
            # Gravar os três campos de nosso_numero para conciliação futura:
            # - nosso_numero: sequencial bruto → conciliação via CNAB (retorno do banco)
            # - nosso_numero_formatado: valor completo impresso no boleto → conciliação via OFX
            # - nosso_numero_dv: dígito verificador (quando o banco/API o retorna isolado)
            self.nosso_numero = resultado.get('nosso_numero', '')
            self.nosso_numero_formatado = resultado.get('nosso_numero_formatado', '')
            self.nosso_numero_dv = resultado.get('nosso_numero_dv', '')
            self.numero_documento = self.gerar_numero_documento()
            self.codigo_barras = resultado.get('codigo_barras', '')
            self.linha_digitavel = resultado.get('linha_digitavel', '')
            self.valor_boleto = resultado.get('valor', self.valor_atual)
            self.status_boleto = StatusBoleto.GERADO
            self.data_geracao_boleto = timezone.now()

            # Salvar PDF se disponível
            if resultado.get('pdf_content'):
                from django.core.files.base import ContentFile
                pdf_content = resultado['pdf_content']
                nome_arquivo = f"boleto_{self.contrato.numero_contrato}_{self.numero_parcela}.pdf"
                self.boleto_pdf.save(nome_arquivo, ContentFile(pdf_content), save=False)
                # Cópia em banco de dados — persiste em deploys com storage efêmero
                self.boleto_pdf_db = pdf_content

            # PIX se disponível
            if resultado.get('pix_copia_cola'):
                self.pix_copia_cola = resultado['pix_copia_cola']
            if resultado.get('pix_qrcode'):
                self.pix_qrcode = resultado['pix_qrcode']

            self.save()

            # Agendar notificação na fila do banco (Option B).
            # Nenhum envio acontece aqui — o cron processar_fila_notificacoes despacha.
            # Isso evita que timeouts de SMTP bloqueiem o request HTTP.
            if enviar_email:
                try:
                    from notificacoes.boleto_notificacao import BoletoNotificacaoService
                    agendado = BoletoNotificacaoService().agendar_notificacao_boleto_criado(self)
                    resultado['email_enviado'] = 'agendado'
                    resultado['notificacoes_agendadas'] = agendado.get('agendadas', [])
                except Exception as exc:
                    logger.exception("Erro ao agendar notificação boleto (parcela pk=%s): %s", self.pk, exc)
                    resultado['email_enviado'] = 'erro_agendamento'

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
                                   banco_pagador='', agencia_pagadora='',
                                   validar_minimo=True):
        """Registra o pagamento do boleto com dados bancários"""
        from datetime import date as date_type, datetime
        if data_pagamento is None:
            data_pagamento = timezone.now()
        elif isinstance(data_pagamento, date_type) and not isinstance(data_pagamento, datetime):
            # Converter date → datetime aware para evitar RuntimeWarning
            data_pagamento = timezone.make_aware(
                datetime.combine(data_pagamento, datetime.min.time())
            )

        self.status_boleto = StatusBoleto.PAGO
        self.data_pagamento_boleto = data_pagamento
        self.valor_pago_boleto = valor_pago
        self.banco_pagador = banco_pagador
        self.agencia_pagadora = agencia_pagadora

        # Também registrar o pagamento da parcela
        self.registrar_pagamento(
            valor_pago=valor_pago,
            data_pagamento=data_pagamento.date() if hasattr(data_pagamento, 'date') else data_pagamento,
            observacoes=f'Pago via boleto. Banco: {banco_pagador} Ag: {agencia_pagadora}',
            validar_minimo=validar_minimo,
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

    # Ciclo de reajuste
    ciclo = models.PositiveIntegerField(
        default=1,
        verbose_name='Ciclo de Reajuste',
        help_text='Número do ciclo de reajuste (2 = reajuste após 12 meses, 3 = após 24 meses, etc.)'
    )
    data_limite_boleto = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data Limite para Boleto',
        help_text='Data até quando boletos podem ser gerados após este reajuste'
    )

    # Período de referência do índice (os 12 meses cujo acumulado foi aplicado)
    periodo_referencia_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Início do Período de Referência',
        help_text='Primeiro mês do período cujo acumulado foi utilizado'
    )
    periodo_referencia_fim = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fim do Período de Referência',
        help_text='Último mês do período cujo acumulado foi utilizado'
    )

    # Percentual bruto (índice calculado) e desconto aplicado
    percentual_bruto = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Percentual Bruto (%)',
        help_text='Percentual calculado do índice antes do desconto'
    )
    desconto_percentual = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Desconto em Pontos Percentuais',
        help_text='Redução em p.p. sobre o índice (ex: IPCA 5,4% - 1 p.p. = 4,4%)'
    )
    desconto_valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Desconto em R$ por Parcela',
        help_text='Desconto fixo em reais subtraído de cada parcela após o percentual'
    )

    # Spread aplicado (snapshot do contrato no momento do reajuste)
    spread_aplicado = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        default=Decimal('0'),
        verbose_name='Spread Aplicado (p.p.)',
        help_text='Pontos percentuais de spread adicionados ao índice bruto'
    )

    # Controle de teto/piso aplicados no momento do reajuste
    piso_aplicado = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Piso Aplicado (%)',
        help_text='Piso de reajuste vigente no contrato no momento da aplicação'
    )
    teto_aplicado = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Teto Aplicado (%)',
        help_text='Teto de reajuste vigente no contrato no momento da aplicação'
    )

    # Audit log
    usuario = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reajustes_aplicados',
        verbose_name='Usuário',
        help_text='Usuário que aplicou o reajuste'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Endereço IP',
        help_text='IP do usuário que aplicou o reajuste'
    )

    aplicado_manual = models.BooleanField(
        default=False,
        verbose_name='Aplicado Manualmente',
        help_text='Indica se o reajuste foi aplicado manualmente pelo usuário'
    )
    aplicado = models.BooleanField(
        default=False,
        verbose_name='Aplicado',
        help_text='Indica se o reajuste já foi efetivamente aplicado nas parcelas'
    )
    data_aplicacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data da Aplicação',
        help_text='Data/hora em que o reajuste foi aplicado'
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
        return f"Reajuste {self.indice_tipo} - {self.percentual}% - Ciclo {self.ciclo} - Contrato {self.contrato.numero_contrato}"

    @property
    def percentual_liquido(self):
        """Percentual efetivamente aplicado após desconto em p.p."""
        perc = self.percentual
        if self.desconto_percentual:
            perc = max(Decimal('0'), perc - self.desconto_percentual)
        return perc

    # ------------------------------------------------------------------
    # Métodos de classe para cálculo automático
    # ------------------------------------------------------------------

    @classmethod
    def calcular_ciclo_pendente(cls, contrato, antecipacao_meses=1):
        """
        Retorna o próximo ciclo que precisa de reajuste, ou None se estiver em dia.

        Regra:
        - Ciclo 1 é sempre isento (sem reajuste).
        - Detecção é baseada em MÊS, não em dia exato: o ciclo aparece como
          pendente quando entramos no mês do aniversário (ou antecipacao_meses
          antes, padrão=1). Isso permite aplicar o reajuste assim que o índice
          de referência estiver disponível — ex.: contrato 15/04/2024 com
          prazo=12 aparece na grid a partir de 01/03/2025 (1 mês antes de 04/2025).
        - Contratos FIXO nunca precisam de reajuste.

        antecipacao_meses: quantos meses antes do aniversário exibir como pendente.
        """
        from django.utils import timezone as tz
        from contratos.models import TipoCorrecao

        if contrato.tipo_correcao == TipoCorrecao.FIXO:
            return None

        prazo = contrato.prazo_reajuste_meses
        hoje = tz.now().date()

        # Comparação mês-a-mês (ignora o dia): soma antecipação para "adiantar"
        hoje_ym = hoje.year * 12 + hoje.month + antecipacao_meses
        inicio_ym = contrato.data_contrato.year * 12 + contrato.data_contrato.month

        meses_efetivos = hoje_ym - inicio_ym
        ciclos_decorridos = meses_efetivos // prazo  # 0 no ciclo 1

        if ciclos_decorridos < 1:
            return None  # ainda no ciclo 1 — nenhum reajuste necessário

        # O próximo ciclo a aplicar é o que vem após o último aplicado
        ultimo_aplicado = contrato.ciclo_reajuste_atual or 1
        proximo = ultimo_aplicado + 1

        # Não ultrapassa o número de ciclos disponíveis
        if proximo > ciclos_decorridos + 1:
            return None

        # Verifica se já existe reajuste aplicado para esse ciclo
        if cls.objects.filter(contrato=contrato, ciclo=proximo, aplicado=True).exists():
            return None

        # Verifica se há parcelas no intervalo desse ciclo
        parcela_inicial = (proximo - 1) * prazo + 1
        if parcela_inicial > contrato.numero_parcelas:
            return None

        return proximo

    @classmethod
    def calcular_periodo_referencia(cls, contrato, ciclo):
        """
        Retorna (data_inicio, data_fim) do período cujo acumulado será aplicado no ciclo N.

        Regra: ciclo N usa os 12 meses de variação do ciclo N-1.
        O mês 1 do ciclo N-1 corresponde ao mês SEGUINTE ao mês do contrato no ano N-2.
        Assim, início = data_contrato + (ciclo-2)*prazo + 1 mês.

        Exemplo — contrato Jan/2023, prazo=12:
          ciclo 2 → referência: Fev/2023 a Jan/2024
          ciclo 3 → referência: Fev/2024 a Jan/2025

        Exemplo — contrato Jul/2020 (Henry), prazo=12:
          ciclo 2 → referência: Ago/2020 a Jul/2021  (IGPM = JUL2021/JUL2020 − 1 ✓)
          ciclo 3 → referência: Ago/2021 a Jul/2022
        """
        from dateutil.relativedelta import relativedelta

        prazo = contrato.prazo_reajuste_meses
        # Primeiro mês de variação do ciclo N-1 (mês seguinte à data do contrato no ano N-2)
        inicio = contrato.data_contrato + relativedelta(months=(ciclo - 2) * prazo + 1)
        # Último mês de variação do ciclo N-1
        fim = contrato.data_contrato + relativedelta(months=(ciclo - 1) * prazo)
        return inicio, fim

    @staticmethod
    def _calcular_pmt(saldo, taxa_mensal_pct, n_parcelas):
        """
        Calcula o valor da prestação pela fórmula da Tabela Price.

        PMT = PV × i / (1 − (1+i)^−n)

        Se taxa = 0, retorna amortização linear (saldo / n), sem juros.
        Se n = 0, retorna 0.
        """
        if n_parcelas <= 0:
            return Decimal('0')
        i = taxa_mensal_pct / Decimal('100')
        if i == 0:
            return (saldo / Decimal(n_parcelas)).quantize(Decimal('0.01'))
        fator = i / (1 - (1 + i) ** (-n_parcelas))
        return (saldo * fator).quantize(Decimal('0.01'))

    @staticmethod
    def _calcular_price_tabela(pv, taxa_mensal_pct, n):
        """
        Gera tabela completa de Tabela Price: lista de (pmt, amort, juros) para n períodos.

        pmt constante, amort crescente, juros decrescentes.
        Se taxa=0, degenera em linear (amort=pmt=PV/n, juros=0).
        """
        if n <= 0:
            return []
        i = taxa_mensal_pct / Decimal('100')
        pmt = Reajuste._calcular_pmt(pv, taxa_mensal_pct, n)
        tabela = []
        saldo = pv
        for k in range(n):
            juros_k = (saldo * i).quantize(Decimal('0.01'))
            if k == n - 1:
                # última parcela: amort = saldo restante (corrige arredondamentos)
                amort_k = saldo
                pmt_k = amort_k + juros_k
            else:
                amort_k = (pmt - juros_k).quantize(Decimal('0.01'))
                pmt_k = pmt
            saldo = (saldo - amort_k).quantize(Decimal('0.01'))
            tabela.append((pmt_k, amort_k, juros_k))
        return tabela

    @staticmethod
    def _calcular_sac_tabela(pv, taxa_mensal_pct, n):
        """
        Gera tabela completa de SAC: lista de (pmt, amort, juros) para n períodos.

        amort constante = PV/n, juros decrescentes, pmt decrescente.
        """
        if n <= 0:
            return []
        i = taxa_mensal_pct / Decimal('100')
        amort = (pv / Decimal(n)).quantize(Decimal('0.01'))
        tabela = []
        saldo = pv
        for k in range(n):
            juros_k = (saldo * i).quantize(Decimal('0.01'))
            if k == n - 1:
                amort_k = saldo  # última parcela: zera o saldo
            else:
                amort_k = amort
            pmt_k = amort_k + juros_k
            saldo = (saldo - amort_k).quantize(Decimal('0.01'))
            tabela.append((pmt_k, amort_k, juros_k))
        return tabela

    @classmethod
    def preview_reajuste(cls, contrato, ciclo,
                         desconto_percentual=None, desconto_valor=None):
        """
        Simula o reajuste sem persistir nada (dry-run).

        Dois modos de cálculo, determinados pela presença de TabelaJurosContrato:

        MODO SIMPLES (padrão):
          novo_valor = valor_atual × (1 + percentual_final/100)
          Afeta apenas as parcelas do ciclo (parcela_inicial..parcela_final).

        MODO TABELA PRICE (quando TabelaJurosContrato está configurada):
          1. Saldo = soma valor_atual de TODAS as parcelas NORMAL não pagas
          2. Saldo atualizado = saldo × (1 + IGPM/100)
          3. Novo PMT = PMT(saldo_atualizado, juros_mensal, n_restantes)
          4. Aplica o mesmo PMT a TODAS as parcelas restantes (todos os ciclos futuros)
          A taxa mensal da tabela é a taxa de financiamento embutida, não um spread no índice.

        Retorna dict com:
          - ciclo, indice_tipo, periodo_referencia_inicio/fim
          - percentual_bruto, spread, percentual_bruto_com_spread, percentual_liquido, percentual_final
          - tipo_calculo ('TABELA_PRICE' | 'SIMPLES')
          - parcela_inicial, parcela_final, parcelas (lista detalhada)
          - total_parcelas, valor_anterior_total, valor_novo_total, diferenca_total
          - boletos_emitidos, erro
        """
        from contratos.models import IndiceReajuste, TabelaJurosContrato
        from django.db.models import Sum

        prazo = contrato.prazo_reajuste_meses
        indice_tipo = contrato.tipo_correcao

        parcela_inicial = (ciclo - 1) * prazo + 1
        parcela_final = min(ciclo * prazo, contrato.numero_parcelas)

        inicio_ref, fim_ref = cls.calcular_periodo_referencia(contrato, ciclo)

        # Buscar acumulado do índice no período de referência
        percentual_bruto = IndiceReajuste.get_acumulado_periodo(
            indice_tipo,
            inicio_ref.year, inicio_ref.month,
            fim_ref.year, fim_ref.month,
        )

        # TabelaJurosContrato tem precedência: taxa de financiamento por ciclo
        # Quando presente → MODO TABELA PRICE; senão → spread fixo / MODO SIMPLES
        taxa_tabela = TabelaJurosContrato.get_juros_para_ciclo(contrato, ciclo)
        usa_tabela_price = taxa_tabela is not None
        spread = taxa_tabela if usa_tabela_price else (contrato.spread_reajuste or Decimal('0'))

        if percentual_bruto is None:
            fallback = contrato.tipo_correcao_fallback
            if fallback:
                percentual_bruto = IndiceReajuste.get_acumulado_periodo(
                    fallback,
                    inicio_ref.year, inicio_ref.month,
                    fim_ref.year, fim_ref.month,
                )
                if percentual_bruto is not None:
                    indice_tipo = fallback
            if percentual_bruto is None:
                return {
                    'erro': f'Índice {indice_tipo} não disponível para {inicio_ref.strftime("%b/%Y")} '
                            f'a {fim_ref.strftime("%b/%Y")}. Importe os dados do índice primeiro.',
                    'periodo_referencia_inicio': inicio_ref,
                    'periodo_referencia_fim': fim_ref,
                    'indice_tipo': indice_tipo,
                    'ciclo': ciclo,
                    'parcela_inicial': parcela_inicial,
                    'parcela_final': parcela_final,
                    'spread': spread,
                }

        desc_perc = Decimal(str(desconto_percentual)) if desconto_percentual else Decimal('0')
        desc_val = Decimal(str(desconto_valor)) if desconto_valor else Decimal('0')

        # Para TABELA PRICE: spread é a taxa de financiamento — NÃO é adicionado ao índice
        # Para MODO SIMPLES: spread é adicionado ao índice como pontos percentuais
        if usa_tabela_price:
            percentual_bruto_com_spread = percentual_bruto  # índice puro; taxa separada
        else:
            percentual_bruto_com_spread = percentual_bruto + spread

        percentual_liquido = percentual_bruto_com_spread - desc_perc

        piso = contrato.reajuste_piso
        teto = contrato.reajuste_teto
        percentual_com_caps = percentual_liquido
        if piso is not None:
            percentual_com_caps = max(piso, percentual_com_caps)
        if teto is not None:
            percentual_com_caps = min(teto, percentual_com_caps)

        detalhes = []
        valor_anterior_total = Decimal('0')
        valor_novo_total = Decimal('0')
        boletos_emitidos = []

        from contratos.models import TipoAmortizacao
        usa_sac = usa_tabela_price and contrato.tipo_amortizacao == TipoAmortizacao.SAC

        if usa_tabela_price and not usa_sac:
            # MODO TABELA PRICE — modelo multiplicativo composto
            # Conforme cláusula contratual:
            #   PMT_novo = PMT_atual × (1 + IPCA) × (1 + taxa_mensal)^prazo
            # onde (1+taxa_mensal)^prazo é o fator de juros compostos anuais.
            todas_restantes = contrato.parcelas.filter(
                pago=False,
                tipo_parcela=TipoParcela.NORMAL,
            ).order_by('numero_parcela')

            primeira = todas_restantes.first()
            pmt_atual = primeira.valor_atual if primeira else Decimal('0')

            prazo = contrato.prazo_reajuste_meses
            taxa_mensal = taxa_tabela / Decimal('100')
            fator_juros_anual = (1 + taxa_mensal) ** prazo  # (1+i)^prazo
            fator_ipca = 1 + percentual_com_caps / Decimal('100')
            novo_pmt = (pmt_atual * fator_ipca * fator_juros_anual).quantize(Decimal('0.01'))
            if desc_val and novo_pmt > desc_val:
                novo_pmt = (novo_pmt - desc_val).quantize(Decimal('0.01'))

            # parcela_final cobrindo todas as restantes (todos os ciclos)
            parcela_final = contrato.numero_parcelas
            parcelas_qs = todas_restantes

            for p in parcelas_qs:
                detalhes.append({
                    'numero_parcela': p.numero_parcela,
                    'data_vencimento': p.data_vencimento,
                    'valor_atual': p.valor_atual,
                    'valor_novo': novo_pmt,
                    'diferenca': novo_pmt - p.valor_atual,
                    'tem_boleto': p.tem_boleto,
                    'amortizacao_nova': None,
                    'juros_novo': None,
                })
                valor_anterior_total += p.valor_atual
                valor_novo_total += novo_pmt
                if p.tem_boleto:
                    boletos_emitidos.append(p.numero_parcela)

        elif usa_sac:
            # MODO SAC — amortização constante recalculada sobre o saldo corrigido
            todas_restantes = contrato.parcelas.filter(
                pago=False,
                tipo_parcela=TipoParcela.NORMAL,
            ).order_by('numero_parcela')

            n_restantes = todas_restantes.count()

            # Saldo SAC = soma das amortizações pendentes (principal real)
            saldo_atual = todas_restantes.aggregate(
                total=Sum('amortizacao')
            )['total']
            if saldo_atual is None:
                # fallback se amortizacao não preenchida
                saldo_atual = todas_restantes.aggregate(
                    total=Sum('valor_atual')
                )['total'] or Decimal('0')

            saldo_atualizado = (saldo_atual * (1 + percentual_com_caps / 100)).quantize(Decimal('0.01'))

            # Recalcula tabela SAC com nova taxa do ciclo
            tabela_sac = cls._calcular_sac_tabela(saldo_atualizado, taxa_tabela, n_restantes)

            parcela_final = contrato.numero_parcelas
            for p, (pmt_k, amort_k, juros_k) in zip(todas_restantes, tabela_sac):
                if desc_val and pmt_k > desc_val:
                    pmt_k = (pmt_k - desc_val).quantize(Decimal('0.01'))
                detalhes.append({
                    'numero_parcela': p.numero_parcela,
                    'data_vencimento': p.data_vencimento,
                    'valor_atual': p.valor_atual,
                    'valor_novo': pmt_k,
                    'diferenca': pmt_k - p.valor_atual,
                    'tem_boleto': p.tem_boleto,
                    'amortizacao_nova': amort_k,
                    'juros_novo': juros_k,
                })
                valor_anterior_total += p.valor_atual
                valor_novo_total += pmt_k
                if p.tem_boleto:
                    boletos_emitidos.append(p.numero_parcela)

        else:
            # MODO SIMPLES: aplica fator a TODAS as parcelas a partir da inicial.
            # Reajuste é permanente e composto — cada ciclo atualiza todas as
            # parcelas restantes, não apenas as do ciclo em questão.
            # Ex.: contrato 360 meses, ciclo 2 IPCA 10% → parcelas 13-360 × 1,10.
            parcela_final = contrato.numero_parcelas  # estende até o final do contrato
            fator = 1 + (percentual_com_caps / 100)
            parcelas_qs = contrato.parcelas.filter(
                numero_parcela__gte=parcela_inicial,
                pago=False,
            ).order_by('numero_parcela')

            for p in parcelas_qs:
                novo_valor = p.valor_atual * fator
                if desc_val:
                    novo_valor = max(p.valor_atual, novo_valor - desc_val)
                novo_valor = novo_valor.quantize(Decimal('0.01'))

                detalhes.append({
                    'numero_parcela': p.numero_parcela,
                    'data_vencimento': p.data_vencimento,
                    'valor_atual': p.valor_atual,
                    'valor_novo': novo_valor,
                    'diferenca': novo_valor - p.valor_atual,
                    'tem_boleto': p.tem_boleto,
                })
                valor_anterior_total += p.valor_atual
                valor_novo_total += novo_valor
                if p.tem_boleto:
                    boletos_emitidos.append(p.numero_parcela)

        # Preview das intermediárias do ciclo (se contrato.intermediarias_reajustadas)
        detalhes_intermediarias = []
        valor_inter_anterior_total = Decimal('0')
        valor_inter_novo_total = Decimal('0')
        if contrato.intermediarias_reajustadas:
            fator_inter = 1 + (percentual_com_caps / 100)
            intermediarias_qs = contrato.intermediarias.filter(
                paga=False,
                mes_vencimento__gte=parcela_inicial,
                mes_vencimento__lte=parcela_final,
            ).order_by('mes_vencimento')
            for inter in intermediarias_qs:
                novo_valor_inter = (inter.valor_atual * fator_inter).quantize(Decimal('0.01'))
                detalhes_intermediarias.append({
                    'numero_sequencial': inter.numero_sequencial,
                    'mes_vencimento': inter.mes_vencimento,
                    'data_vencimento': inter.data_vencimento,
                    'valor_atual': inter.valor_atual,
                    'valor_novo': novo_valor_inter,
                    'diferenca': novo_valor_inter - inter.valor_atual,
                })
                valor_inter_anterior_total += inter.valor_atual
                valor_inter_novo_total += novo_valor_inter

        return {
            'ciclo': ciclo,
            'indice_tipo': indice_tipo,
            'tipo_calculo': 'SAC' if usa_sac else ('TABELA_PRICE' if usa_tabela_price else 'SIMPLES'),
            'periodo_referencia_inicio': inicio_ref,
            'periodo_referencia_fim': fim_ref,
            'percentual_bruto': percentual_bruto,
            'spread': spread,
            'percentual_bruto_com_spread': percentual_bruto_com_spread,
            'desconto_percentual': desc_perc,
            'desconto_valor': desc_val,
            'percentual_liquido': percentual_liquido,
            'percentual_final': percentual_com_caps,
            'piso': piso,
            'teto': teto,
            'piso_ativado': piso is not None and percentual_liquido < piso,
            'teto_ativado': teto is not None and percentual_liquido > teto,
            'parcela_inicial': parcela_inicial,
            'parcela_final': parcela_final,
            'parcelas': detalhes,
            'total_parcelas': len(detalhes),
            'valor_anterior_total': valor_anterior_total,
            'valor_novo_total': valor_novo_total,
            'diferenca_total': valor_novo_total - valor_anterior_total,
            'boletos_emitidos': boletos_emitidos,
            # Intermediárias afetadas pelo reajuste deste ciclo
            'intermediarias': detalhes_intermediarias,
            'total_intermediarias': len(detalhes_intermediarias),
            'valor_inter_anterior_total': valor_inter_anterior_total,
            'valor_inter_novo_total': valor_inter_novo_total,
            'diferenca_inter_total': valor_inter_novo_total - valor_inter_anterior_total,
        }

    def clean(self):
        """Validações de negócio do reajuste"""
        super().clean()
        errors = {}

        # V-08: Contratos FIXO não têm reajuste periódico
        if hasattr(self, 'contrato') and self.contrato:
            from contratos.models import TipoCorrecao
            if self.contrato.tipo_correcao == TipoCorrecao.FIXO:
                errors['contrato'] = (
                    'Contratos com índice FIXO são pré-fixados e não possuem reajuste periódico. '
                    'O valor das parcelas é definido na TabelaJurosContrato no momento da criação.'
                )

        # Validar que o ciclo é sequencial (não pular ciclos)
        if self.ciclo and self.ciclo > 1 and hasattr(self, 'contrato') and self.contrato:
            # Verificar se existe reajuste aplicado para o ciclo anterior
            ciclo_anterior = self.ciclo - 1
            if ciclo_anterior > 1:  # Ciclo 1 não precisa de reajuste anterior
                reajuste_anterior = Reajuste.objects.filter(
                    contrato=self.contrato,
                    ciclo=ciclo_anterior,
                    aplicado=True
                ).exists()
                if not reajuste_anterior:
                    errors['ciclo'] = f'O reajuste do ciclo {ciclo_anterior} deve ser aplicado antes do ciclo {self.ciclo}.'

        # Validar que não pode ter reajuste duplicado para o mesmo ciclo
        if hasattr(self, 'contrato') and self.contrato and self.ciclo:
            reajuste_existente = Reajuste.objects.filter(
                contrato=self.contrato,
                ciclo=self.ciclo
            ).exclude(pk=self.pk if self.pk else None)
            if reajuste_existente.exists():
                errors['ciclo'] = f'Já existe um reajuste cadastrado para o ciclo {self.ciclo} deste contrato.'

        # Validar que reajuste não pode ser aplicado retroativamente
        if self.data_reajuste and hasattr(self, 'contrato') and self.contrato:
            # A data do reajuste não pode ser anterior ao início do ciclo
            from dateutil.relativedelta import relativedelta
            prazo = self.contrato.prazo_reajuste_meses
            data_inicio_ciclo = self.contrato.data_contrato + relativedelta(months=(self.ciclo - 1) * prazo)
            if self.data_reajuste < data_inicio_ciclo:
                errors['data_reajuste'] = f'A data do reajuste não pode ser anterior ao início do ciclo ({data_inicio_ciclo}).'

        # Validar parcela inicial e final
        if self.parcela_inicial and self.parcela_final:
            if self.parcela_inicial > self.parcela_final:
                errors['parcela_final'] = 'A parcela final deve ser maior ou igual à parcela inicial.'

        # Validar percentual razoável
        if self.percentual:
            if self.percentual < Decimal('-50.0000'):
                errors['percentual'] = 'O percentual de reajuste não pode ser menor que -50%.'
            elif self.percentual > Decimal('100.0000'):
                errors['percentual'] = 'O percentual de reajuste não pode ser maior que 100%.'

        if errors:
            raise ValidationError(errors)

    @transaction.atomic
    def aplicar_reajuste(self):
        """
        Aplica o reajuste nas parcelas especificadas.

        Atualiza o valor_atual de todas as parcelas não pagas no intervalo
        e libera a geração de boletos para o próximo ciclo.

        Returns:
            dict: Resumo da aplicação com quantidade de parcelas e valores
        """
        if self.aplicado:
            return {
                'sucesso': False,
                'erro': 'Reajuste já foi aplicado anteriormente'
            }

        from contratos.models import TabelaJurosContrato

        perc_liquido = self.percentual_liquido
        # Aplicar teto/piso registrados no momento da criação do reajuste
        perc_final = perc_liquido
        if self.piso_aplicado is not None:
            perc_final = max(self.piso_aplicado, perc_final)
        if self.teto_aplicado is not None:
            perc_final = min(self.teto_aplicado, perc_final)

        desc_val = self.desconto_valor or Decimal('0')
        parcelas_reajustadas = 0
        valor_anterior_total = Decimal('0.00')
        valor_novo_total = Decimal('0.00')

        # Determina modo de cálculo
        from contratos.models import TipoAmortizacao
        taxa_tabela = TabelaJurosContrato.get_juros_para_ciclo(self.contrato, self.ciclo)
        usa_tabela_price = taxa_tabela is not None
        usa_sac = usa_tabela_price and self.contrato.tipo_amortizacao == TipoAmortizacao.SAC

        if usa_tabela_price and not usa_sac:
            # MODO TABELA PRICE — modelo multiplicativo composto
            # PMT_novo = PMT_atual × (1 + IPCA) × (1 + taxa_mensal)^prazo
            parcelas = self.contrato.parcelas.filter(
                pago=False,
                tipo_parcela=TipoParcela.NORMAL,
            ).order_by('numero_parcela')

            primeira = parcelas.first()
            pmt_atual = primeira.valor_atual if primeira else Decimal('0')

            prazo = self.contrato.prazo_reajuste_meses
            taxa_mensal = taxa_tabela / Decimal('100')
            fator_juros_anual = (1 + taxa_mensal) ** prazo
            fator_ipca = 1 + perc_final / Decimal('100')
            novo_pmt = (pmt_atual * fator_ipca * fator_juros_anual).quantize(Decimal('0.01'))
            if desc_val and novo_pmt > desc_val:
                novo_pmt = (novo_pmt - desc_val).quantize(Decimal('0.01'))

            for parcela in parcelas:
                valor_anterior = parcela.valor_atual
                parcela.valor_atual = novo_pmt
                parcela.save(update_fields=['valor_atual'])
                valor_anterior_total += valor_anterior
                valor_novo_total += novo_pmt
                parcelas_reajustadas += 1

        elif usa_sac:
            # MODO SAC — recalcula amortização constante sobre saldo corrigido
            parcelas = list(self.contrato.parcelas.filter(
                pago=False,
                tipo_parcela=TipoParcela.NORMAL,
            ).order_by('numero_parcela'))

            n_restantes = len(parcelas)
            saldo_atual = sum(
                (p.amortizacao or p.valor_atual) for p in parcelas
            )

            saldo_atualizado = (saldo_atual * (1 + perc_final / 100)).quantize(Decimal('0.01'))
            tabela_sac = self._calcular_sac_tabela(saldo_atualizado, taxa_tabela, n_restantes)

            for parcela, (pmt_k, amort_k, juros_k) in zip(parcelas, tabela_sac):
                if desc_val and pmt_k > desc_val:
                    pmt_k = (pmt_k - desc_val).quantize(Decimal('0.01'))
                valor_anterior = parcela.valor_atual
                parcela.valor_atual = pmt_k
                parcela.amortizacao = amort_k
                parcela.juros_embutido = juros_k
                parcela.save(update_fields=['valor_atual', 'amortizacao', 'juros_embutido'])
                valor_anterior_total += valor_anterior
                valor_novo_total += pmt_k
                parcelas_reajustadas += 1

        else:
            # MODO SIMPLES: aplica fator a TODAS as parcelas a partir da inicial.
            # O reajuste é permanente — afeta o ciclo atual e todos os futuros,
            # pois a prestação base é atualizada para o próximo ciclo calcular
            # sobre o valor já corrigido.
            parcelas = list(self.contrato.parcelas.filter(
                numero_parcela__gte=self.parcela_inicial,
                pago=False,
            ).order_by('numero_parcela'))
            fator_reajuste = 1 + (perc_final / 100)

            for parcela in parcelas:
                valor_anterior = parcela.valor_atual
                novo_valor = parcela.valor_atual * fator_reajuste
                if desc_val:
                    novo_valor = max(parcela.valor_atual, novo_valor - desc_val)
                parcela.valor_atual = novo_valor.quantize(Decimal('0.01'))
                parcela.save(update_fields=['valor_atual'])
                valor_anterior_total += valor_anterior
                valor_novo_total += parcela.valor_atual
                parcelas_reajustadas += 1

            # Atualiza parcela_final para refletir o escopo real aplicado
            if parcelas:
                self.parcela_final = parcelas[-1].numero_parcela

        # Cancelar boletos das parcelas afetadas cujo valor mudou.
        # O PDF/código de barras foi gerado com o valor antigo — deve ser regenerado.
        boletos_cancelados = 0
        parcelas_boleto_qs = self.contrato.parcelas.filter(
            numero_parcela__gte=self.parcela_inicial,
            pago=False,
            status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO],
        )
        for p_boleto in parcelas_boleto_qs:
            p_boleto.status_boleto = StatusBoleto.CANCELADO
            p_boleto.motivo_rejeicao = (
                f"Cancelado — reajuste ciclo {self.ciclo} ({perc_final:+.2f}%) "
                f"alterou o valor da parcela. Regenere o boleto."
            )
            p_boleto.save(update_fields=['status_boleto', 'motivo_rejeicao'])
            boletos_cancelados += 1

        # Reajustar intermediárias do ciclo com perc_final (corrigido: era self.percentual)
        intermediarias = self.contrato.intermediarias.filter(
            paga=False,
            mes_vencimento__gte=self.parcela_inicial,
            mes_vencimento__lte=self.parcela_final,
        )
        intermediarias_reajustadas = 0
        valor_intermediarias_anterior = Decimal('0.00')
        valor_intermediarias_novo = Decimal('0.00')

        for inter in intermediarias:
            valor_anterior_inter = inter.valor_atual
            inter.aplicar_reajuste(perc_final)  # era self.percentual — corrigido
            valor_intermediarias_anterior += valor_anterior_inter
            valor_intermediarias_novo += inter.valor_atual
            intermediarias_reajustadas += 1

        # Marcar como aplicado (salva parcela_final atualizado para MODO SIMPLES)
        self.aplicado = True
        self.data_aplicacao = timezone.now()
        self.save(update_fields=['aplicado', 'data_aplicacao', 'parcela_final'])

        # Atualizar dados do contrato
        self.contrato.data_ultimo_reajuste = self.data_reajuste
        self.contrato.ciclo_reajuste_atual = self.ciclo
        self.contrato.bloqueio_boleto_reajuste = False
        self.contrato.save(update_fields=[
            'data_ultimo_reajuste',
            'ciclo_reajuste_atual',
            'bloqueio_boleto_reajuste'
        ])

        return {
            'sucesso': True,
            'parcelas_reajustadas': parcelas_reajustadas,
            'valor_anterior_total': valor_anterior_total,
            'valor_novo_total': valor_novo_total,
            'diferenca': valor_novo_total - valor_anterior_total,
            'percentual_aplicado': self.percentual,
            # Item 2.4: Incluir informacoes das intermediarias reajustadas
            'intermediarias_reajustadas': intermediarias_reajustadas,
            'valor_intermediarias_anterior': valor_intermediarias_anterior,
            'valor_intermediarias_novo': valor_intermediarias_novo,
            'boletos_cancelados': boletos_cancelados,
        }

    @classmethod
    def criar_reajuste_ciclo(cls, contrato, ciclo, indice_tipo=None, percentual=None):
        """
        DEPRECIADO — use preview_reajuste() + Reajuste.objects.create() + aplicar_reajuste().

        Este método não considera spread_reajuste, TabelaJurosContrato, piso/teto,
        desconto, fallback de índice nem modo Tabela Price. Mantido apenas para
        compatibilidade com testes legados.
        """
        import warnings
        warnings.warn(
            'criar_reajuste_ciclo() está depreciado. '
            'Use preview_reajuste() + Reajuste.objects.create() + aplicar_reajuste().',
            DeprecationWarning,
            stacklevel=2,
        )
        from contratos.models import IndiceReajuste
        from dateutil.relativedelta import relativedelta

        # Usar tipo de correção do contrato se não especificado
        if not indice_tipo:
            indice_tipo = contrato.tipo_correcao

        # Calcular período do reajuste
        prazo = contrato.prazo_reajuste_meses
        parcela_inicial = (ciclo - 1) * prazo + 1
        parcela_final = min(ciclo * prazo, contrato.numero_parcelas)

        # Período de referência: os 12 meses do ciclo anterior (N-1)
        # Ex: ciclo 2 → referência = meses 1-12 do contrato (o ano 1)
        #     ciclo 3 → referência = meses 13-24 do contrato (o ano 2)
        inicio_ref, fim_ref = cls.calcular_periodo_referencia(contrato, ciclo)

        # Buscar percentual acumulado se não especificado
        if percentual is None:
            percentual_acumulado = IndiceReajuste.get_acumulado_periodo(
                indice_tipo,
                inicio_ref.year, inicio_ref.month,
                fim_ref.year, fim_ref.month,
            )

            if percentual_acumulado is not None:
                percentual = percentual_acumulado
            else:
                raise ValueError(
                    f"Índice {indice_tipo} não disponível para "
                    f"{inicio_ref.strftime('%b/%Y')} a {fim_ref.strftime('%b/%Y')}"
                )

        data_inicio_ciclo = contrato.data_contrato + relativedelta(months=(ciclo - 1) * prazo)

        # Criar o reajuste
        reajuste = cls.objects.create(
            contrato=contrato,
            data_reajuste=timezone.now().date(),
            indice_tipo=indice_tipo,
            percentual=percentual,
            percentual_bruto=percentual,
            parcela_inicial=parcela_inicial,
            parcela_final=parcela_final,
            ciclo=ciclo,
            periodo_referencia_inicio=inicio_ref,
            periodo_referencia_fim=fim_ref,
            data_limite_boleto=data_inicio_ciclo + relativedelta(months=prazo * 2),
            aplicado_manual=False,
        )

        return reajuste


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
    antecipado = models.BooleanField(
        default=False,
        verbose_name='Antecipado',
        help_text='Pagamento de antecipação de parcelas com desconto'
    )

    # ── Conciliação bancária ──────────────────────────────────────────────────
    ORIGEM_CHOICES = [
        ('MANUAL',      'Manual'),
        ('CNAB',        'Retorno CNAB'),
        ('OFX',         'Extrato OFX'),
        ('ANTECIPACAO', 'Antecipação'),
        ('SISTEMA',     'Sistema'),
    ]
    origem_pagamento = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default='MANUAL',
        verbose_name='Origem',
        help_text='Como o pagamento foi registrado: manual, retorno CNAB, extrato OFX ou antecipação',
    )
    item_retorno = models.ForeignKey(
        'ItemRetorno',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='historico_pagamentos',
        verbose_name='Item Retorno CNAB',
        help_text='Vínculo ao registro do arquivo de retorno CNAB que gerou este pagamento',
    )
    fitid_ofx = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='FITID OFX',
        help_text='ID único da transação no arquivo OFX — usado para deduplicação',
    )

    class Meta:
        verbose_name = 'Histórico de Pagamento'
        verbose_name_plural = 'Histórico de Pagamentos'
        ordering = ['-data_pagamento']
        indexes = [
            models.Index(fields=['parcela', 'data_pagamento']),
            models.Index(fields=['origem_pagamento']),
            models.Index(fields=['fitid_ofx']),
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
                # Guard: não reprocessar parcela já baixada (retorno duplicado do banco)
                if self.parcela.pago:
                    self.erro_processamento = 'Parcela já paga — possível retorno duplicado'
                    self.processado = True
                    self.save()
                    return False

                valor = self.valor_pago or self.valor_titulo
                data_pgto = (
                    self.data_ocorrencia.date()
                    if hasattr(self.data_ocorrencia, 'date')
                    else (self.data_ocorrencia or timezone.localdate())
                )
                banco = getattr(self.arquivo_retorno.conta_bancaria, 'banco', '') if self.arquivo_retorno_id else ''
                obs = (
                    f'Pago via retorno CNAB. '
                    f'Arquivo: {self.arquivo_retorno.nome_arquivo if self.arquivo_retorno_id else "?"} '
                    f'Ocorrência: {self.descricao_ocorrencia or self.codigo_ocorrencia}'
                )

                self.parcela.registrar_pagamento_boleto(
                    valor_pago=valor,
                    data_pagamento=data_pgto,
                    banco_pagador=banco,
                    agencia_pagadora='',
                    validar_minimo=False,
                )

                # Criar HistoricoPagamento vinculado a este ItemRetorno
                HistoricoPagamento.objects.get_or_create(
                    item_retorno=self,
                    defaults=dict(
                        parcela=self.parcela,
                        data_pagamento=data_pgto,
                        valor_pago=valor,
                        valor_parcela=self.parcela.valor_atual,
                        valor_juros=self.valor_juros or Decimal('0'),
                        valor_multa=Decimal('0'),
                        forma_pagamento='BOLETO',
                        observacoes=obs,
                        origem_pagamento='CNAB',
                    ),
                )

            elif self.tipo_ocorrencia == 'ENTRADA':
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
            logger.exception("Erro ao processar registro CNAB pk=%s: %s", self.pk, e)
            self.erro_processamento = str(e)
            self.save()
            return False
