"""
Modelos principais do sistema de Gestão de Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Modelo abstrato para adicionar timestamps a outros modelos"""
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        abstract = True


class Contabilidade(TimeStampedModel):
    """Modelo para representar a Contabilidade que gerencia os loteamentos"""
    nome = models.CharField(max_length=200, verbose_name='Nome da Contabilidade')
    razao_social = models.CharField(max_length=200, verbose_name='Razão Social')
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
            message='CNPJ deve estar no formato XX.XXX.XXX/XXXX-XX'
        )],
        verbose_name='CNPJ'
    )
    endereco = models.TextField(verbose_name='Endereço')
    telefone = models.CharField(max_length=20, verbose_name='Telefone')
    email = models.EmailField(validators=[EmailValidator()], verbose_name='E-mail')
    responsavel = models.CharField(max_length=200, verbose_name='Responsável')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Contabilidade'
        verbose_name_plural = 'Contabilidades'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Imobiliaria(TimeStampedModel):
    """Modelo para representar a Imobiliária/Beneficiário do contrato"""
    contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.PROTECT,
        related_name='imobiliarias',
        verbose_name='Contabilidade'
    )
    nome = models.CharField(max_length=200, verbose_name='Nome da Imobiliária')
    razao_social = models.CharField(max_length=200, verbose_name='Razão Social')
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
            message='CNPJ deve estar no formato XX.XXX.XXX/XXXX-XX'
        )],
        verbose_name='CNPJ'
    )
    endereco = models.TextField(verbose_name='Endereço')
    telefone = models.CharField(max_length=20, verbose_name='Telefone')
    email = models.EmailField(validators=[EmailValidator()], verbose_name='E-mail')
    responsavel_financeiro = models.CharField(
        max_length=200,
        verbose_name='Responsável Financeiro'
    )
    banco = models.CharField(max_length=100, blank=True, verbose_name='Banco')
    agencia = models.CharField(max_length=20, blank=True, verbose_name='Agência')
    conta = models.CharField(max_length=20, blank=True, verbose_name='Conta')
    pix = models.CharField(max_length=100, blank=True, verbose_name='Chave PIX')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Imobiliária'
        verbose_name_plural = 'Imobiliárias'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class TipoImovel(models.TextChoices):
    """Tipos de imóveis disponíveis"""
    LOTE = 'LOTE', 'Lote'
    TERRENO = 'TERRENO', 'Terreno'
    CASA = 'CASA', 'Casa'
    APARTAMENTO = 'APARTAMENTO', 'Apartamento'
    COMERCIAL = 'COMERCIAL', 'Comercial'


class Imovel(TimeStampedModel):
    """Modelo para representar o Imóvel (Lote, Terreno, Casa, etc)"""
    imobiliaria = models.ForeignKey(
        Imobiliaria,
        on_delete=models.PROTECT,
        related_name='imoveis',
        verbose_name='Imobiliária'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoImovel.choices,
        default=TipoImovel.LOTE,
        verbose_name='Tipo de Imóvel'
    )
    identificacao = models.CharField(
        max_length=100,
        verbose_name='Identificação',
        help_text='Ex: Quadra 1, Lote 15'
    )
    loteamento = models.CharField(
        max_length=200,
        verbose_name='Loteamento/Empreendimento'
    )
    endereco = models.TextField(verbose_name='Endereço Completo')
    area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Área (m²)',
        help_text='Área em metros quadrados'
    )
    matricula = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Matrícula',
        help_text='Número da matrícula do imóvel'
    )
    inscricao_municipal = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Inscrição Municipal'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    disponivel = models.BooleanField(default=True, verbose_name='Disponível para Venda')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Imóvel'
        verbose_name_plural = 'Imóveis'
        ordering = ['loteamento', 'identificacao']
        unique_together = [['imobiliaria', 'identificacao', 'loteamento']]

    def __str__(self):
        return f"{self.loteamento} - {self.identificacao}"


class Comprador(TimeStampedModel):
    """Modelo para representar o Comprador do imóvel"""
    nome = models.CharField(max_length=200, verbose_name='Nome Completo')
    cpf = models.CharField(
        max_length=14,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
            message='CPF deve estar no formato XXX.XXX.XXX-XX'
        )],
        verbose_name='CPF'
    )
    rg = models.CharField(max_length=20, blank=True, verbose_name='RG')
    data_nascimento = models.DateField(verbose_name='Data de Nascimento')
    estado_civil = models.CharField(
        max_length=50,
        choices=[
            ('SOLTEIRO', 'Solteiro(a)'),
            ('CASADO', 'Casado(a)'),
            ('DIVORCIADO', 'Divorciado(a)'),
            ('VIUVO', 'Viúvo(a)'),
            ('UNIAO_ESTAVEL', 'União Estável'),
        ],
        verbose_name='Estado Civil'
    )
    profissao = models.CharField(max_length=100, verbose_name='Profissão')

    # Dados de Contato
    endereco = models.TextField(verbose_name='Endereço')
    telefone = models.CharField(max_length=20, verbose_name='Telefone')
    celular = models.CharField(max_length=20, verbose_name='Celular')
    email = models.EmailField(
        validators=[EmailValidator()],
        verbose_name='E-mail',
        help_text='E-mail para envio de notificações'
    )

    # Preferências de Notificação
    notificar_email = models.BooleanField(
        default=True,
        verbose_name='Notificar por E-mail'
    )
    notificar_sms = models.BooleanField(
        default=False,
        verbose_name='Notificar por SMS'
    )
    notificar_whatsapp = models.BooleanField(
        default=False,
        verbose_name='Notificar por WhatsApp'
    )

    # Cônjuge (se casado ou união estável)
    conjuge_nome = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nome do Cônjuge'
    )
    conjuge_cpf = models.CharField(
        max_length=14,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
            message='CPF deve estar no formato XXX.XXX.XXX-XX'
        )],
        verbose_name='CPF do Cônjuge'
    )
    conjuge_rg = models.CharField(max_length=20, blank=True, verbose_name='RG do Cônjuge')

    observacoes = models.TextField(blank=True, verbose_name='Observações')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Comprador'
        verbose_name_plural = 'Compradores'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.cpf}"
