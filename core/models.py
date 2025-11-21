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
        max_length=20,
        unique=True,
        verbose_name='CNPJ',
        help_text='Suporta formato numérico atual e alfanumérico (preparado para 2026)'
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
        max_length=20,
        unique=True,
        verbose_name='CNPJ',
        help_text='Suporta formato numérico atual e alfanumérico (preparado para 2026)'
    )

    # Dados de Endereço (estruturado)
    cep = models.CharField(
        max_length=9,
        blank=True,
        verbose_name='CEP',
        help_text='Formato: 99999-999'
    )
    logradouro = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Logradouro'
    )
    numero = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Número'
    )
    complemento = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Complemento'
    )
    bairro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Bairro'
    )
    cidade = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Cidade'
    )
    estado = models.CharField(
        max_length=2,
        blank=True,
        verbose_name='UF',
        choices=[
            ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
            ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
            ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
            ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
            ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
            ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
            ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
        ]
    )

    # Dados de Contato (mantido para compatibilidade)
    endereco = models.TextField(
        blank=True,
        verbose_name='Endereço Completo (legacy)',
        help_text='Campo legado - use os campos separados acima'
    )
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
    """Modelo para representar o Comprador do imóvel (Pessoa Física ou Jurídica)"""

    # Tipo de Pessoa
    TIPO_PESSOA_CHOICES = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]
    tipo_pessoa = models.CharField(
        max_length=2,
        choices=TIPO_PESSOA_CHOICES,
        default='PF',
        verbose_name='Tipo de Pessoa',
        help_text='Pessoa Física ou Pessoa Jurídica'
    )

    # Dados Gerais (para ambos PF e PJ)
    nome = models.CharField(
        max_length=200,
        verbose_name='Nome Completo / Razão Social',
        help_text='Nome completo para PF ou Razão Social para PJ'
    )

    # Dados Pessoa Física
    cpf = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
            message='CPF deve estar no formato XXX.XXX.XXX-XX'
        )],
        verbose_name='CPF',
        help_text='Obrigatório para Pessoa Física'
    )
    rg = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='RG',
        help_text='Apenas para Pessoa Física'
    )
    data_nascimento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Data de Nascimento',
        help_text='Apenas para Pessoa Física'
    )
    estado_civil = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('SOLTEIRO', 'Solteiro(a)'),
            ('CASADO', 'Casado(a)'),
            ('DIVORCIADO', 'Divorciado(a)'),
            ('VIUVO', 'Viúvo(a)'),
            ('UNIAO_ESTAVEL', 'União Estável'),
        ],
        verbose_name='Estado Civil',
        help_text='Apenas para Pessoa Física'
    )
    profissao = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Profissão',
        help_text='Apenas para Pessoa Física'
    )

    # Dados Pessoa Jurídica
    cnpj = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='CNPJ',
        help_text='Obrigatório para PJ. Suporta formato alfanumérico (preparado para 2026)'
    )
    nome_fantasia = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nome Fantasia',
        help_text='Apenas para Pessoa Jurídica'
    )
    inscricao_estadual = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Inscrição Estadual',
        help_text='Apenas para Pessoa Jurídica'
    )
    inscricao_municipal = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Inscrição Municipal',
        help_text='Apenas para Pessoa Jurídica'
    )
    responsavel_legal = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Responsável Legal',
        help_text='Nome do representante legal da empresa (apenas PJ)'
    )
    responsavel_cpf = models.CharField(
        max_length=14,
        blank=True,
        verbose_name='CPF do Responsável',
        help_text='CPF do representante legal (apenas PJ)'
    )

    # Dados de Endereço (estruturado)
    cep = models.CharField(
        max_length=9,
        blank=True,
        verbose_name='CEP',
        help_text='Formato: 99999-999'
    )
    logradouro = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Logradouro'
    )
    numero = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Número'
    )
    complemento = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Complemento'
    )
    bairro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Bairro'
    )
    cidade = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Cidade'
    )
    estado = models.CharField(
        max_length=2,
        blank=True,
        verbose_name='UF',
        choices=[
            ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
            ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
            ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
            ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
            ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
            ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
            ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
        ]
    )

    # Dados de Contato (mantido para compatibilidade)
    endereco = models.TextField(
        blank=True,
        verbose_name='Endereço Completo (legacy)',
        help_text='Campo legado - use os campos separados acima'
    )
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
        indexes = [
            models.Index(fields=['tipo_pessoa']),
            models.Index(fields=['cpf']),
            models.Index(fields=['cnpj']),
        ]

    def __str__(self):
        if self.tipo_pessoa == 'PF':
            return f"{self.nome} - CPF: {self.cpf}" if self.cpf else self.nome
        else:
            return f"{self.nome} - CNPJ: {self.cnpj}" if self.cnpj else self.nome

    def clean(self):
        """Validação customizada para garantir dados obrigatórios por tipo"""
        from django.core.exceptions import ValidationError

        if self.tipo_pessoa == 'PF':
            # Para Pessoa Física, CPF é obrigatório
            if not self.cpf:
                raise ValidationError({'cpf': 'CPF é obrigatório para Pessoa Física'})
        elif self.tipo_pessoa == 'PJ':
            # Para Pessoa Jurídica, CNPJ é obrigatório
            if not self.cnpj:
                raise ValidationError({'cnpj': 'CNPJ é obrigatório para Pessoa Jurídica'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def documento(self):
        """Retorna o documento principal (CPF ou CNPJ)"""
        return self.cpf if self.tipo_pessoa == 'PF' else self.cnpj

    @property
    def nome_exibicao(self):
        """Retorna o nome de exibição apropriado"""
        if self.tipo_pessoa == 'PF':
            return self.nome
        else:
            return self.nome_fantasia if self.nome_fantasia else self.nome
