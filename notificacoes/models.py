"""
Modelos do Sistema de Notificações

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel


class TipoNotificacao(models.TextChoices):
    """Tipos de notificação disponíveis"""
    EMAIL = 'EMAIL', 'E-mail'
    SMS = 'SMS', 'SMS'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'


class StatusNotificacao(models.TextChoices):
    """Status da notificação"""
    PENDENTE = 'PENDENTE', 'Pendente'
    ENVIADA = 'ENVIADA', 'Enviada'
    ERRO = 'ERRO', 'Erro'
    CANCELADA = 'CANCELADA', 'Cancelada'


class ConfiguracaoEmail(TimeStampedModel):
    """Configurações de servidor de e-mail"""
    nome = models.CharField(max_length=100, verbose_name='Nome da Configuração')
    host = models.CharField(max_length=255, verbose_name='Servidor SMTP')
    porta = models.IntegerField(default=587, verbose_name='Porta')
    usuario = models.CharField(max_length=255, verbose_name='Usuário')
    senha = models.CharField(max_length=255, verbose_name='Senha')
    usar_tls = models.BooleanField(default=True, verbose_name='Usar TLS')
    usar_ssl = models.BooleanField(default=False, verbose_name='Usar SSL')
    email_remetente = models.EmailField(verbose_name='E-mail Remetente')
    nome_remetente = models.CharField(
        max_length=100,
        default='Sistema de Gestão de Contratos',
        verbose_name='Nome do Remetente'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Configuração de E-mail'
        verbose_name_plural = 'Configurações de E-mail'

    def __str__(self):
        return self.nome


class ConfiguracaoSMS(TimeStampedModel):
    """Configurações de serviço de SMS"""
    nome = models.CharField(max_length=100, verbose_name='Nome da Configuração')
    provedor = models.CharField(
        max_length=50,
        choices=[
            ('TWILIO', 'Twilio'),
            ('NEXMO', 'Nexmo/Vonage'),
            ('AWS_SNS', 'AWS SNS'),
        ],
        default='TWILIO',
        verbose_name='Provedor'
    )
    account_sid = models.CharField(max_length=255, verbose_name='Account SID')
    auth_token = models.CharField(max_length=255, verbose_name='Auth Token')
    numero_remetente = models.CharField(
        max_length=20,
        verbose_name='Número Remetente',
        help_text='Número de telefone do remetente (formato internacional)'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Configuração de SMS'
        verbose_name_plural = 'Configurações de SMS'

    def __str__(self):
        return self.nome


class ConfiguracaoWhatsApp(TimeStampedModel):
    """Configurações de serviço de WhatsApp"""
    nome = models.CharField(max_length=100, verbose_name='Nome da Configuração')
    provedor = models.CharField(
        max_length=50,
        choices=[
            ('TWILIO', 'Twilio'),
            ('META', 'Meta (WhatsApp Business API)'),
        ],
        default='TWILIO',
        verbose_name='Provedor'
    )
    account_sid = models.CharField(max_length=255, verbose_name='Account SID')
    auth_token = models.CharField(max_length=255, verbose_name='Auth Token')
    numero_remetente = models.CharField(
        max_length=20,
        verbose_name='Número WhatsApp Remetente',
        help_text='Número de WhatsApp do remetente (formato: whatsapp:+5511999999999)'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Configuração de WhatsApp'
        verbose_name_plural = 'Configurações de WhatsApp'

    def __str__(self):
        return self.nome


class Notificacao(TimeStampedModel):
    """Modelo para gerenciar notificações enviadas"""

    parcela = models.ForeignKey(
        'financeiro.Parcela',
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name='Parcela',
        null=True,
        blank=True
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoNotificacao.choices,
        verbose_name='Tipo'
    )
    destinatario = models.CharField(
        max_length=255,
        verbose_name='Destinatário',
        help_text='E-mail, telefone ou número WhatsApp do destinatário'
    )
    assunto = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Assunto',
        help_text='Assunto da mensagem (usado em e-mails)'
    )
    mensagem = models.TextField(verbose_name='Mensagem')

    # Status
    status = models.CharField(
        max_length=20,
        choices=StatusNotificacao.choices,
        default=StatusNotificacao.PENDENTE,
        verbose_name='Status'
    )
    data_agendamento = models.DateTimeField(
        default=timezone.now,
        verbose_name='Data de Agendamento'
    )
    data_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Envio'
    )
    tentativas = models.IntegerField(
        default=0,
        verbose_name='Tentativas de Envio'
    )
    erro_mensagem = models.TextField(
        blank=True,
        verbose_name='Mensagem de Erro'
    )

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-data_agendamento']
        indexes = [
            models.Index(fields=['status', 'data_agendamento']),
            models.Index(fields=['parcela']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.destinatario} - {self.get_status_display()}"

    def marcar_como_enviada(self):
        """Marca a notificação como enviada"""
        self.status = StatusNotificacao.ENVIADA
        self.data_envio = timezone.now()
        self.save()

    def marcar_erro(self, mensagem_erro):
        """Marca a notificação com erro"""
        self.status = StatusNotificacao.ERRO
        self.erro_mensagem = mensagem_erro
        self.tentativas += 1
        self.save()


class TipoTemplate(models.TextChoices):
    """Tipos de templates disponíveis"""
    BOLETO_CRIADO = 'BOLETO_CRIADO', 'Boleto Criado'
    BOLETO_5_DIAS = 'BOLETO_5_DIAS', 'Boleto - 5 dias para vencer'
    BOLETO_VENCE_AMANHA = 'BOLETO_VENCE_AMANHA', 'Boleto - Vence amanhã'
    BOLETO_VENCEU_ONTEM = 'BOLETO_VENCEU_ONTEM', 'Boleto - Venceu ontem'
    BOLETO_VENCIDO = 'BOLETO_VENCIDO', 'Boleto Vencido'
    PAGAMENTO_CONFIRMADO = 'PAGAMENTO_CONFIRMADO', 'Pagamento Confirmado'
    CONTRATO_CRIADO = 'CONTRATO_CRIADO', 'Contrato Criado'
    LEMBRETE_PARCELA = 'LEMBRETE_PARCELA', 'Lembrete de Parcela'
    CUSTOM = 'CUSTOM', 'Personalizado'


class TemplateNotificacao(TimeStampedModel):
    """Templates para notificações com suporte a TAGs %%TAG%%"""

    TAGS_DISPONIVEIS = """
    TAGs disponíveis para uso nos templates:

    DADOS DO COMPRADOR:
    %%NOMECOMPRADOR%% - Nome completo do comprador
    %%CPFCOMPRADOR%% - CPF do comprador
    %%CNPJCOMPRADOR%% - CNPJ do comprador (se PJ)
    %%EMAILCOMPRADOR%% - E-mail do comprador
    %%TELEFONECOMPRADOR%% - Telefone do comprador
    %%CELULARCOMPRADOR%% - Celular do comprador
    %%ENDERECOCOMPRADOR%% - Endereço completo do comprador

    DADOS DA IMOBILIÁRIA:
    %%NOMEIMOBILIARIA%% - Nome da imobiliária
    %%CNPJIMOBILIARIA%% - CNPJ da imobiliária
    %%TELEFONEIMOBILIARIA%% - Telefone da imobiliária
    %%EMAILIMOBILIARIA%% - E-mail da imobiliária

    DADOS DO CONTRATO:
    %%NUMEROCONTRATO%% - Número do contrato
    %%DATACONTRATO%% - Data do contrato
    %%VALORTOTAL%% - Valor total do contrato
    %%TOTALPARCELAS%% - Total de parcelas

    DADOS DO IMÓVEL:
    %%IMOVEL%% - Identificação do imóvel
    %%LOTEAMENTO%% - Nome do loteamento
    %%ENDERECOIMOVEL%% - Endereço do imóvel

    DADOS DA PARCELA:
    %%PARCELA%% - Número da parcela (ex: 5/24)
    %%NUMEROPARCELA%% - Apenas o número da parcela
    %%VALORPARCELA%% - Valor da parcela
    %%DATAVENCIMENTO%% - Data de vencimento
    %%DIASATRASO%% - Dias de atraso (se vencida)
    %%VALORJUROS%% - Valor dos juros
    %%VALORMULTA%% - Valor da multa
    %%VALORTOTALPARCELA%% - Valor total (parcela + juros + multa)

    DADOS DO BOLETO:
    %%NOSSONUMERO%% - Nosso número do boleto
    %%LINHADIGITAVEL%% - Linha digitável do boleto
    %%CODIGOBARRAS%% - Código de barras
    %%STATUSBOLETO%% - Status do boleto
    %%VALORBOLETO%% - Valor do boleto

    DADOS DO SISTEMA:
    %%DATAATUAL%% - Data atual
    %%HORAATUAL%% - Hora atual
    %%LINKBOLETO%% - Link para download do boleto
    """

    nome = models.CharField(max_length=100, verbose_name='Nome do Template')
    codigo = models.CharField(
        max_length=30,
        choices=TipoTemplate.choices,
        default=TipoTemplate.CUSTOM,
        verbose_name='Tipo do Template'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoNotificacao.choices,
        verbose_name='Canal de Envio'
    )
    assunto = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Assunto',
        help_text='Para e-mails. Suporta TAGs como %%NOMECOMPRADOR%%'
    )
    corpo = models.TextField(
        verbose_name='Corpo da Mensagem',
        help_text='Use TAGs como %%NOMECOMPRADOR%%, %%DATAVENCIMENTO%%, etc.'
    )
    corpo_html = models.TextField(
        blank=True,
        verbose_name='Corpo HTML',
        help_text='Versão HTML do e-mail (opcional)'
    )

    # Configurações
    imobiliaria = models.ForeignKey(
        'core.Imobiliaria',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='templates_notificacao',
        verbose_name='Imobiliária',
        help_text='Deixe vazio para template global'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Template de Notificação'
        verbose_name_plural = 'Templates de Notificação'
        ordering = ['codigo', 'nome']
        unique_together = [['codigo', 'imobiliaria', 'tipo']]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    def renderizar(self, contexto):
        """
        Renderiza o template substituindo TAGs pelo contexto

        Args:
            contexto (dict): Dicionário com valores para as TAGs

        Returns:
            tuple: (assunto_renderizado, corpo_renderizado, corpo_html_renderizado)
        """
        assunto_renderizado = self.assunto
        corpo_renderizado = self.corpo
        corpo_html_renderizado = self.corpo_html

        for tag, valor in contexto.items():
            placeholder = f"%%{tag}%%"
            valor_str = str(valor) if valor is not None else ''
            assunto_renderizado = assunto_renderizado.replace(placeholder, valor_str)
            corpo_renderizado = corpo_renderizado.replace(placeholder, valor_str)
            if corpo_html_renderizado:
                corpo_html_renderizado = corpo_html_renderizado.replace(placeholder, valor_str)

        return assunto_renderizado, corpo_renderizado, corpo_html_renderizado

    @classmethod
    def get_template(cls, codigo, imobiliaria=None, tipo=TipoNotificacao.EMAIL):
        """
        Busca o template mais específico disponível.
        Prioriza template da imobiliária, depois template global.
        """
        # Primeiro tenta template específico da imobiliária
        if imobiliaria:
            template = cls.objects.filter(
                codigo=codigo,
                imobiliaria=imobiliaria,
                tipo=tipo,
                ativo=True
            ).first()
            if template:
                return template

        # Senão, busca template global
        return cls.objects.filter(
            codigo=codigo,
            imobiliaria__isnull=True,
            tipo=tipo,
            ativo=True
        ).first()
