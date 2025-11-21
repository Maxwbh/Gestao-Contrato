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


# ============================================================
# Choices para Configurações de Boleto
# ============================================================

class TipoValor(models.TextChoices):
    """Tipos de valor para multa, juros e desconto"""
    PERCENTUAL = 'PERCENTUAL', 'Percentual (%)'
    REAL = 'REAL', 'Valor em Reais (R$)'


class TipoTitulo(models.TextChoices):
    """Tipos de título para boleto bancário"""
    AP = 'AP', 'AP - Apólice de Seguro'
    BDP = 'BDP', 'BDP - Boleto de Proposta'
    CC = 'CC', 'CC - Cartão de Crédito'
    CH = 'CH', 'CH - Cheque'
    CPR = 'CPR', 'CPR - Cédula de Produto Rural'
    DAE = 'DAE', 'DAE - Dívida Ativa de Estado'
    DAM = 'DAM', 'DAM - Dívida Ativa de Município'
    DAU = 'DAU', 'DAU - Dívida Ativa da União'
    DD = 'DD', 'DD - Documento de Dívida'
    DM = 'DM', 'DM - Duplicata Mercantil'
    DMI = 'DMI', 'DMI - Duplicata Mercantil para Indicação'
    DR = 'DR', 'DR - Duplicata Rural'
    DS = 'DS', 'DS - Duplicata de Serviço'
    DSI = 'DSI', 'DSI - Duplicata de Serviço para Indicação'
    EC = 'EC', 'EC - Encargos Condominiais'
    FAT = 'FAT', 'FAT - Fatura'
    LC = 'LC', 'LC - Letra de Câmbio'
    ME = 'ME', 'ME - Mensalidade Escolar'
    NCC = 'NCC', 'NCC - Nota de Crédito Comercial'
    NCE = 'NCE', 'NCE - Nota de Crédito à Exportação'
    NCI = 'NCI', 'NCI - Nota de Crédito Industrial'
    NCR = 'NCR', 'NCR - Nota de Crédito Rural'
    ND = 'ND', 'ND - Nota de Débito'
    NF = 'NF', 'NF - Nota Fiscal'
    NP = 'NP', 'NP - Nota Promissória'
    NPR = 'NPR', 'NPR - Nota Promissória Rural'
    NS = 'NS', 'NS - Nota de Seguro'
    OUTROS = 'O', 'O - Outros'
    PC = 'PC', 'PC - Parcela de Consórcio'
    RC = 'RC', 'RC - Recibo'
    TM = 'TM', 'TM - Triplicata Mercantil'
    TS = 'TS', 'TS - Triplicata de Serviço'
    W = 'W', 'W - Warrant'


class LayoutCNAB(models.TextChoices):
    """Layouts de arquivo CNAB"""
    CNAB_240 = 'CNAB_240', 'Layout 240'
    CNAB_400 = 'CNAB_400', 'Layout 400'
    CNAB_444 = 'CNAB_444', 'Layout 444 (CNAB 400 + Chave NFE)'


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

    # ============================================================
    # Configurações Padrão para Geração de Boletos
    # ============================================================

    # Multa
    tipo_valor_multa = models.CharField(
        max_length=10,
        choices=TipoValor.choices,
        default=TipoValor.PERCENTUAL,
        verbose_name='Tipo de Multa'
    )
    percentual_multa_padrao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Multa Padrão',
        help_text='Valor em percentual ou reais conforme tipo'
    )

    # Juros
    tipo_valor_juros = models.CharField(
        max_length=10,
        choices=TipoValor.choices,
        default=TipoValor.PERCENTUAL,
        verbose_name='Tipo de Juros'
    )
    percentual_juros_padrao = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='Juros ao Dia Padrão',
        help_text='Valor em percentual (0,0333 = 1% ao mês) ou reais'
    )

    # Dias sem encargos
    dias_para_encargos_padrao = models.IntegerField(
        default=0,
        verbose_name='Dias sem Encargos',
        help_text='Dias sem cobrar multa/juros após vencimento'
    )

    # Opções de Boleto
    boleto_sem_valor = models.BooleanField(
        default=False,
        verbose_name='Permite Boleto sem Valor'
    )
    parcela_no_documento = models.BooleanField(
        default=False,
        verbose_name='Parcela no Documento',
        help_text='Incluir número da parcela no campo Documento'
    )
    campo_desconto_abatimento_pdf = models.BooleanField(
        default=False,
        verbose_name='Desconto no PDF',
        help_text='Mostrar desconto no campo "Desconto/Abatimento" do boleto'
    )

    # Desconto 1
    tipo_valor_desconto = models.CharField(
        max_length=10,
        choices=TipoValor.choices,
        default=TipoValor.PERCENTUAL,
        verbose_name='Tipo de Desconto'
    )
    percentual_desconto_padrao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Desconto Padrão',
        help_text='Valor em percentual ou reais conforme tipo'
    )
    dias_para_desconto_padrao = models.IntegerField(
        default=0,
        verbose_name='Dias para Desconto',
        help_text='Dias para conceder desconto até vencimento'
    )

    # Desconto 2
    tipo_valor_desconto2 = models.CharField(
        max_length=10,
        choices=TipoValor.choices,
        default=TipoValor.PERCENTUAL,
        verbose_name='Tipo de 2º Desconto'
    )
    desconto2_padrao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='2º Desconto Padrão'
    )
    dias_para_desconto2_padrao = models.IntegerField(
        default=0,
        verbose_name='Dias para 2º Desconto'
    )

    # Desconto 3
    tipo_valor_desconto3 = models.CharField(
        max_length=10,
        choices=TipoValor.choices,
        default=TipoValor.PERCENTUAL,
        verbose_name='Tipo de 3º Desconto'
    )
    desconto3_padrao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='3º Desconto Padrão'
    )
    dias_para_desconto3_padrao = models.IntegerField(
        default=0,
        verbose_name='Dias para 3º Desconto'
    )

    # Instrução e Tipo de Título
    instrucao_padrao = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Instrução Padrão',
        help_text='Uma linha no espaço instrução ao caixa'
    )
    tipo_titulo = models.CharField(
        max_length=5,
        choices=TipoTitulo.choices,
        default=TipoTitulo.RC,
        verbose_name='Tipo do Título',
        help_text='Tipo de título para emissão de boletos'
    )
    aceite = models.BooleanField(
        default=False,
        verbose_name='Aceite'
    )

    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Imobiliária'
        verbose_name_plural = 'Imobiliárias'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class BancoBrasil(models.TextChoices):
    """Lista de bancos brasileiros para contas bancárias"""
    BANCO_DO_BRASIL = '001', '001 - Banco do Brasil'
    BANCO_DO_NORDESTE = '004', '004 - Banco do Nordeste - BNB'
    BANESTES = '021', '021 - Banestes'
    SANTANDER = '033', '033 - Santander'
    BANRISUL = '041', '041 - Banrisul'
    BRB = '070', '070 - BRB - Banco de Brasília'
    BANCO_INTER = '077', '077 - Banco Inter'
    SISPRIME = '084', '084 - Sisprime'
    CECRED = '085', '085 - Cecred / Ailos'
    CREDISAN = '089', '089 - Credisan'
    CAIXA = '104', '104 - Caixa Econômica Federal'
    CRESOL = '133', '133 - Cresol'
    UNICRED = '136', '136 - Unicred'
    BTG_PACTUAL = '208', '208 - BTG Pactual'
    BANCO_ARBI = '213', '213 - Banco Arbi'
    BRADESCO = '237', '237 - Bradesco'
    ABC_BRASIL = '246', '246 - ABC Brasil'
    BMP = '274', '274 - BMP'
    C6_BANK = '336', '336 - C6 Bank'
    ITAU = '341', '341 - Itaú'
    MERCANTIL = '389', '389 - Mercantil do Brasil'
    HSBC = '399', '399 - HSBC'
    SAFRA = '422', '422 - Safra'
    BANCOOB = '756', '756 - Sicoob / Bancoob'
    SICREDI = '748', '748 - Sicredi'
    SOFISA = '637', '637 - Sofisa'
    DAYCOVAL = '707', '707 - Daycoval'
    NUBANK = '260', '260 - Nubank'
    PAGBANK = '290', '290 - PagBank / PagSeguro'
    MERCADO_PAGO = '323', '323 - Mercado Pago'
    STONE = '197', '197 - Stone'
    ASAAS = '461', '461 - Asaas'
    OUTROS = '000', '000 - Outros'


class ContaBancaria(TimeStampedModel):
    """Modelo para representar Contas Bancárias das Imobiliárias"""
    imobiliaria = models.ForeignKey(
        'Imobiliaria',
        on_delete=models.CASCADE,
        related_name='contas_bancarias',
        verbose_name='Imobiliária'
    )

    # Dados do Banco
    banco = models.CharField(
        max_length=3,
        choices=BancoBrasil.choices,
        verbose_name='Banco'
    )
    descricao = models.CharField(
        max_length=150,
        verbose_name='Descrição',
        help_text='Identificação da conta (ex: Conta Principal, Conta Boletos)'
    )
    principal = models.BooleanField(
        default=False,
        verbose_name='Conta Principal',
        help_text='Marque se esta é a conta principal'
    )

    # Dados da Conta
    agencia = models.CharField(
        max_length=10,
        verbose_name='Agência',
        help_text='Número da agência com dígito'
    )
    conta = models.CharField(
        max_length=20,
        verbose_name='Conta',
        help_text='Número da conta com dígito'
    )

    # Dados para Boleto (opcionais)
    convenio = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Convênio / Código do Cliente',
        help_text='Código do convênio para emissão de boletos'
    )
    carteira = models.CharField(
        max_length=5,
        blank=True,
        verbose_name='Carteira',
        help_text='Número da carteira de cobrança'
    )
    nosso_numero_atual = models.IntegerField(
        default=0,
        verbose_name='Nosso Número Atual',
        help_text='Sequencial atual do nosso número'
    )
    modalidade = models.CharField(
        max_length=5,
        blank=True,
        verbose_name='Modalidade'
    )

    # PIX
    tipo_pix = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('CPF', 'CPF'),
            ('CNPJ', 'CNPJ'),
            ('EMAIL', 'E-mail'),
            ('TELEFONE', 'Telefone'),
            ('ALEATORIA', 'Chave Aleatória'),
        ],
        verbose_name='Tipo de Chave PIX'
    )
    chave_pix = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Chave PIX'
    )

    # Configurações de Cobrança
    cobranca_registrada = models.BooleanField(
        default=True,
        verbose_name='Cobrança Registrada'
    )
    prazo_baixa = models.IntegerField(
        default=0,
        verbose_name='Prazo para Baixa (dias)',
        help_text='Prazo em dias para baixa/devolução do título após vencimento'
    )
    prazo_protesto = models.IntegerField(
        default=0,
        verbose_name='Prazo para Protesto (dias)',
        help_text='Prazo em dias para protesto. 0 = não protestar'
    )

    # Configurações CNAB
    layout_cnab = models.CharField(
        max_length=10,
        choices=LayoutCNAB.choices,
        default=LayoutCNAB.CNAB_240,
        verbose_name='Layout CNAB',
        help_text='Layout dos arquivos CNAB'
    )
    numero_remessa_cnab_atual = models.IntegerField(
        default=0,
        verbose_name='Sequencial Remessa',
        help_text='Número sequencial da remessa CNAB'
    )

    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'
        ordering = ['-principal', 'banco', 'descricao']

    def __str__(self):
        banco_nome = self.get_banco_display() if self.banco else 'Sem banco'
        return f"{banco_nome} - Ag: {self.agencia} Cc: {self.conta}"

    def save(self, *args, **kwargs):
        # Se marcada como principal, desmarcar outras
        if self.principal:
            ContaBancaria.objects.filter(
                imobiliaria=self.imobiliaria,
                principal=True
            ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    @property
    def banco_nome(self):
        """Retorna o nome completo do banco"""
        return self.get_banco_display() if self.banco else ''


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


# =============================================================================
# CONTROLE DE ACESSO
# =============================================================================

class TipoUsuario(models.TextChoices):
    """Tipos de usuário no sistema"""
    ADMIN = 'ADMIN', 'Administrador'
    CONTABILIDADE = 'CONTABILIDADE', 'Contabilidade'
    IMOBILIARIA = 'IMOBILIARIA', 'Imobiliária'
    OPERADOR = 'OPERADOR', 'Operador'


class PerfilUsuario(TimeStampedModel):
    """
    Perfil do usuário com controle de acesso por Contabilidade/Imobiliária.

    - ADMIN: Acesso total ao sistema
    - CONTABILIDADE: Acesso a todas as imobiliárias de uma contabilidade
    - IMOBILIARIA: Acesso apenas à imobiliária específica
    - OPERADOR: Acesso limitado de leitura
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    usuario = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name='Usuário'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoUsuario.choices,
        default=TipoUsuario.OPERADOR,
        verbose_name='Tipo de Usuário'
    )

    # Vínculo com Contabilidade (para CONTABILIDADE e IMOBILIARIA)
    contabilidade = models.ForeignKey(
        'Contabilidade',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='Contabilidade',
        help_text='Obrigatório para usuários do tipo Contabilidade ou Imobiliária'
    )

    # Vínculo com Imobiliária (apenas para IMOBILIARIA)
    imobiliaria = models.ForeignKey(
        'Imobiliaria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='Imobiliária',
        help_text='Obrigatório apenas para usuários do tipo Imobiliária'
    )

    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'
        ordering = ['usuario__username']

    def __str__(self):
        return f"{self.usuario.username} ({self.get_tipo_display()})"

    def clean(self):
        """Validação para garantir vínculos corretos por tipo"""
        from django.core.exceptions import ValidationError

        if self.tipo == TipoUsuario.CONTABILIDADE:
            if not self.contabilidade:
                raise ValidationError({
                    'contabilidade': 'Contabilidade é obrigatória para usuários do tipo Contabilidade'
                })

        if self.tipo == TipoUsuario.IMOBILIARIA:
            if not self.contabilidade:
                raise ValidationError({
                    'contabilidade': 'Contabilidade é obrigatória para usuários do tipo Imobiliária'
                })
            if not self.imobiliaria:
                raise ValidationError({
                    'imobiliaria': 'Imobiliária é obrigatória para usuários do tipo Imobiliária'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        """Verifica se o usuário é administrador"""
        return self.tipo == TipoUsuario.ADMIN

    @property
    def is_contabilidade(self):
        """Verifica se o usuário é do tipo contabilidade"""
        return self.tipo == TipoUsuario.CONTABILIDADE

    @property
    def is_imobiliaria(self):
        """Verifica se o usuário é do tipo imobiliária"""
        return self.tipo == TipoUsuario.IMOBILIARIA

    def get_contabilidades_permitidas(self):
        """Retorna as contabilidades que o usuário pode acessar"""
        if self.is_admin:
            return Contabilidade.objects.filter(ativo=True)
        elif self.contabilidade:
            return Contabilidade.objects.filter(pk=self.contabilidade.pk, ativo=True)
        return Contabilidade.objects.none()

    def get_imobiliarias_permitidas(self):
        """Retorna as imobiliárias que o usuário pode acessar"""
        if self.is_admin:
            return Imobiliaria.objects.filter(ativo=True)
        elif self.is_imobiliaria and self.imobiliaria:
            return Imobiliaria.objects.filter(pk=self.imobiliaria.pk, ativo=True)
        elif self.is_contabilidade and self.contabilidade:
            return Imobiliaria.objects.filter(contabilidade=self.contabilidade, ativo=True)
        return Imobiliaria.objects.none()
