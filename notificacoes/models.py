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


class StatusEntrega(models.TextChoices):
    """Status de entrega retornado pelo provedor ou detectado localmente."""
    # Twilio SMS/WhatsApp
    ACEITO = 'accepted', 'Aceito'
    ENFILEIRADO = 'queued', 'Enfileirado'
    ENVIANDO = 'sending', 'Enviando'
    ENVIADO = 'sent', 'Enviado'
    ENTREGUE = 'delivered', 'Entregue'
    NAO_ENTREGUE = 'undelivered', 'Não entregue'
    FALHOU = 'failed', 'Falhou'
    LIDO = 'read', 'Lido'
    # E-mail — rastreamento local
    CLICADO = 'clicked', 'Clicado (link)'
    BOUNCED = 'bounced', 'Bounce (NDR)'
    ABERTO = 'opened', 'Aberto (pixel)'


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
            ('EVOLUTION', 'Evolution API (self-hosted)'),
            ('ZAPI', 'Z-API'),
        ],
        default='TWILIO',
        verbose_name='Provedor'
    )
    # Twilio / Meta fields
    account_sid = models.CharField(max_length=255, blank=True, verbose_name='Account SID')
    auth_token = models.CharField(max_length=255, blank=True, verbose_name='Auth Token')
    numero_remetente = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Número WhatsApp Remetente',
        help_text='Twilio/Meta: whatsapp:+5511999999999 | Z-API: número sem prefixo'
    )
    # Evolution API / Z-API fields
    api_url = models.URLField(
        blank=True,
        verbose_name='URL da API',
        help_text='Evolution: http://seu-servidor:8080 | Z-API: https://api.z-api.io'
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='API Key / Token',
        help_text='Evolution: apikey do cabeçalho | Z-API: token da instância'
    )
    instancia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Instância / Instance',
        help_text='Evolution: nome da instância | Z-API: instance ID'
    )
    # Z-API additional field
    client_token = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Client-Token (Z-API)',
        help_text='Cabeçalho Client-Token exigido pela Z-API'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Configuração de WhatsApp'
        verbose_name_plural = 'Configurações de WhatsApp'

    def __str__(self):
        return f"{self.nome} ({self.get_provedor_display()})"


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

    # Rastreamento de entrega
    external_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID Externo',
        help_text='Twilio MessageSid ou Message-ID do e-mail para rastreamento'
    )
    status_entrega = models.CharField(
        max_length=20,
        blank=True,
        choices=StatusEntrega.choices,
        verbose_name='Status de Entrega',
        help_text='Status confirmado pelo provedor: queued, sending, sent, delivered, undelivered, failed, read'
    )
    data_confirmacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Confirmação',
        help_text='Quando o provedor confirmou a entrega ou falha via webhook'
    )

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-data_agendamento']
        indexes = [
            models.Index(fields=['status', 'data_agendamento']),
            models.Index(fields=['parcela']),
            models.Index(fields=['external_id'], name='notif_external_id_idx'),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.destinatario} - {self.get_status_display()}"

    def marcar_como_enviada(self, external_id=''):
        """Marca a notificação como enviada, armazenando o ID externo se fornecido."""
        self.status = StatusNotificacao.ENVIADA
        self.data_envio = timezone.now()
        if external_id:
            self.external_id = external_id
        self.save()

    def marcar_erro(self, mensagem_erro):
        """Marca a notificação com erro"""
        self.status = StatusNotificacao.ERRO
        self.erro_mensagem = mensagem_erro
        self.tentativas += 1
        self.save()


class TipoGatilho(models.TextChoices):
    """Momento de disparo em relação ao vencimento da parcela"""
    ANTES_VENCIMENTO = 'ANTES', 'Dias antes do vencimento'
    APOS_VENCIMENTO = 'APOS', 'Dias após o vencimento (inadimplência)'


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
    RELATORIO_MENSAL = 'RELATORIO_MENSAL', 'Relatório Mensal'
    RELATORIO_SEMANAL = 'RELATORIO_SEMANAL', 'Relatório Semanal'
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

    RELATÓRIO SEMANAL (RELATORIO_SEMANAL):
    %%NOMEIMOBILIARIA%% - Nome da imobiliária
    %%PERIODORELATORIO%% - Período (ex: 14/04/2025 a 20/04/2025)
    %%QTDRECEBIMENTOS%% - Quantidade de pagamentos recebidos na semana
    %%VALORRECEBIMENTOS%% - Valor total recebido na semana (R$)
    %%QTDINADIMPLENTES%% - Quantidade de parcelas vencidas em aberto
    %%VALORINADIMPLENTES%% - Valor total inadimplente (R$)
    %%QTDAVENCER%% - Quantidade de parcelas a vencer nos próximos 7 dias
    %%VALORAVENCER%% - Valor a vencer nos próximos 7 dias (R$)
    %%DATAATUAL%% - Data de geração do relatório

    RELATÓRIO MENSAL (RELATORIO_MENSAL):
    %%NOMECONTABILIDADE%% - Nome da contabilidade destinatária
    %%MESREFERENCIA%% - Mês de referência (ex: março/2025)
    %%PERIODORELATORIO%% - Período completo (ex: 01/03/2025 a 31/03/2025)
    %%QTDCONTRATOSATIVOS%% - Total de contratos ativos (todas as imobiliárias)
    %%QTDRECEBIMENTOS%% - Total de recebimentos no mês
    %%VALORRECEBIMENTOS%% - Valor total recebido no mês (R$)
    %%QTDINADIMPLENTES%% - Total de parcelas vencidas em aberto
    %%VALORINADIMPLENTES%% - Valor total inadimplente (R$)
    %%QTDREAJUSTES%% - Reajustes aplicados no mês
    %%TABELAIMOBILIARIAS%% - Tabela HTML com resumo por imobiliária
    %%DATAATUAL%% - Data de geração do relatório
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
        null=True,
        blank=True,
        verbose_name='Canal de Envio',
        help_text='Legado — canal determinado automaticamente pelos campos preenchidos'
    )
    assunto = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Assunto (E-mail)',
        help_text='Assunto do e-mail. Suporta TAGs como %%NOMECOMPRADOR%%'
    )
    corpo = models.TextField(
        blank=True,
        verbose_name='Corpo SMS',
        help_text='Texto para SMS (máx. 255 caracteres). Use TAGs como %%NOMECOMPRADOR%%.'
    )
    corpo_html = models.TextField(
        blank=True,
        verbose_name='Corpo E-mail (HTML)',
        help_text='Conteúdo HTML do e-mail. Suporta TAGs %%TAG%%.'
    )
    corpo_whatsapp = models.TextField(
        blank=True,
        verbose_name='Corpo WhatsApp',
        help_text='Texto para mensagem WhatsApp. Suporta TAGs %%TAG%%.'
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
        unique_together = [['codigo', 'imobiliaria']]

    def __str__(self):
        canais = []
        if self.tem_email:
            canais.append('Email')
        if self.tem_sms:
            canais.append('SMS')
        if self.tem_whatsapp:
            canais.append('WA')
        canal_str = '+'.join(canais) if canais else 'sem canal'
        return f"{self.nome} ({canal_str})"

    @property
    def tem_email(self):
        return bool(self.corpo_html or self.assunto)

    @property
    def tem_sms(self):
        return bool(self.corpo)

    @property
    def tem_whatsapp(self):
        return bool(self.corpo_whatsapp)

    def renderizar(self, contexto):
        """
        Renderiza o template substituindo TAGs pelo contexto.

        Returns:
            tuple: (assunto, corpo_sms, corpo_html, corpo_whatsapp) — todos renderizados
        """
        assunto_r = self.assunto or ''
        corpo_r = self.corpo or ''
        corpo_html_r = self.corpo_html or ''
        corpo_whatsapp_r = self.corpo_whatsapp or ''

        for tag, valor in contexto.items():
            placeholder = f"%%{tag}%%"
            valor_str = str(valor) if valor is not None else ''
            assunto_r = assunto_r.replace(placeholder, valor_str)
            corpo_r = corpo_r.replace(placeholder, valor_str)
            if corpo_html_r:
                corpo_html_r = corpo_html_r.replace(placeholder, valor_str)
            if corpo_whatsapp_r:
                corpo_whatsapp_r = corpo_whatsapp_r.replace(placeholder, valor_str)

        return assunto_r, corpo_r, corpo_html_r, corpo_whatsapp_r

    @classmethod
    def get_template(cls, codigo, imobiliaria=None, tipo=None):
        """
        Busca o template mais específico disponível.
        Prioriza template da imobiliária, depois template global.
        O parâmetro `tipo` é mantido apenas para compatibilidade — é ignorado.
        """
        # Primeiro tenta template específico da imobiliária
        if imobiliaria:
            template = cls.objects.filter(
                codigo=codigo,
                imobiliaria=imobiliaria,
                ativo=True
            ).first()
            if template:
                return template

        # Senão, busca template global
        return cls.objects.filter(
            codigo=codigo,
            imobiliaria__isnull=True,
            ativo=True
        ).first()


class RegraNotificacao(TimeStampedModel):
    """
    N-03: Régua de cobrança configurável.

    Cada regra define um gatilho (X dias antes/após o vencimento), o canal
    (e-mail, SMS ou WhatsApp) e, opcionalmente, um template customizado.
    Quando existem regras ativas, as tarefas de notificação usam a régua
    em vez dos valores padrão de settings.
    """
    nome = models.CharField(max_length=100, verbose_name='Nome da Regra')
    ativo = models.BooleanField(default=True, verbose_name='Ativa')
    tipo_gatilho = models.CharField(
        max_length=5,
        choices=TipoGatilho.choices,
        verbose_name='Gatilho',
        help_text='Momento de envio em relação ao vencimento da parcela',
    )
    dias_offset = models.PositiveIntegerField(
        verbose_name='Dias',
        help_text='Número de dias antes/após o vencimento para disparar',
    )
    tipo_notificacao = models.CharField(
        max_length=10,
        choices=TipoNotificacao.choices,
        default=TipoNotificacao.EMAIL,
        verbose_name='Canal',
    )
    template = models.ForeignKey(
        TemplateNotificacao,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='regras',
        verbose_name='Template',
        help_text='Deixe vazio para usar a mensagem padrão do sistema',
    )

    class Meta:
        verbose_name = 'Regra de Notificação'
        verbose_name_plural = 'Régua de Notificação'
        ordering = ['tipo_gatilho', 'dias_offset']
        unique_together = [['tipo_gatilho', 'dias_offset', 'tipo_notificacao']]

    def __str__(self):
        sinal = '−' if self.tipo_gatilho == TipoGatilho.ANTES_VENCIMENTO else '+'
        return f"{self.nome} (D{sinal}{self.dias_offset} · {self.get_tipo_notificacao_display()})"
