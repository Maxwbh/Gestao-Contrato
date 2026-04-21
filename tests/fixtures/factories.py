"""
Factories para geração de dados de teste usando Factory Boy

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from core.models import (
    Contabilidade,
    Imobiliaria,
    ContaBancaria,
    Imovel,
    Comprador,
    AcessoUsuario,
)
from contratos.models import Contrato, TipoCorrecao, TipoAmortizacao, StatusContrato
from financeiro.models import (
    Parcela,
    Reajuste,
    HistoricoPagamento,
    ArquivoRemessa,
    ArquivoRetorno,
    ItemRemessa,
    ItemRetorno,
    StatusArquivoRemessa,
    StatusArquivoRetorno,
)
from notificacoes.models import (
    ConfiguracaoEmail,
    ConfiguracaoSMS,
    ConfiguracaoWhatsApp,
    Notificacao,
    TemplateNotificacao,
    RegraNotificacao,
    TipoNotificacao,
    TipoTemplate,
    TipoGatilho,
)
from portal_comprador.models import AcessoComprador, LogAcessoComprador

fake = Faker('pt_BR')
User = get_user_model()


# =============================================================================
# AUTH & ACCOUNTS
# =============================================================================

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name', locale='pt_BR')
    last_name = factory.Faker('last_name', locale='pt_BR')
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            obj.set_password(extracted)
        else:
            obj.set_password('testpass123')
        obj.save()


class SuperUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


# =============================================================================
# CORE
# =============================================================================

class ContabilidadeFactory(DjangoModelFactory):
    class Meta:
        model = Contabilidade

    nome = factory.Sequence(lambda n: f'Contabilidade {n}')
    razao_social = factory.LazyAttribute(lambda obj: f'{obj.nome} LTDA')
    cnpj = factory.Sequence(lambda n: f'23456781{n:06d}11')
    endereco = factory.Faker('address', locale='pt_BR')
    telefone = factory.Faker('phone_number', locale='pt_BR')
    email = factory.LazyAttribute(
        lambda obj: f"{obj.nome.lower().replace(' ', '')}@contabilidade.com.br"
    )
    responsavel = factory.Faker('name', locale='pt_BR')
    ativo = True


class ImobiliariaFactory(DjangoModelFactory):
    class Meta:
        model = Imobiliaria

    contabilidade = factory.SubFactory(ContabilidadeFactory)
    tipo_pessoa = 'PJ'
    nome = factory.Sequence(lambda n: f'Imobiliária {n}')
    razao_social = factory.LazyAttribute(lambda obj: f'{obj.nome} Negócios Imobiliários LTDA')
    cnpj = factory.Sequence(lambda n: f'12.345.{n:03d}/0001-{(n % 99):02d}')

    # Endereço estruturado
    cep = factory.Faker('postcode', locale='pt_BR')
    logradouro = factory.Faker('street_name', locale='pt_BR')
    numero = factory.Faker('building_number', locale='pt_BR')
    bairro = factory.Faker('bairro', locale='pt_BR')
    cidade = factory.Faker('city', locale='pt_BR')
    estado = 'MG'

    telefone = factory.Faker('phone_number', locale='pt_BR')
    email = factory.LazyAttribute(
        lambda obj: f"{obj.nome.lower().replace(' ', '')}@imobiliaria.com.br"
    )
    responsavel_financeiro = factory.Faker('name', locale='pt_BR')

    # Configurações padrão de boleto
    percentual_multa_padrao = Decimal('2.00')
    percentual_juros_padrao = Decimal('0.033')  # 1% ao mês
    dias_para_encargos_padrao = 1

    ativo = True


class ContaBancariaFactory(DjangoModelFactory):
    class Meta:
        model = ContaBancaria

    imobiliaria = factory.SubFactory(ImobiliariaFactory)
    banco = '001'  # Banco do Brasil
    descricao = 'Conta Principal'
    agencia = factory.Sequence(lambda n: f'{n:04d}')
    conta = factory.Sequence(lambda n: f'{n:08d}')
    convenio = factory.Sequence(lambda n: f'{n:07d}')
    carteira = '18'
    principal = True
    ativo = True


class ImovelFactory(DjangoModelFactory):
    class Meta:
        model = Imovel

    imobiliaria = factory.SubFactory(ImobiliariaFactory)
    tipo = 'LOTE'
    identificacao = factory.Sequence(lambda n: f'Quadra 1, Lote {n}')
    loteamento = factory.Sequence(lambda n: f'Loteamento {n}')

    # Endereço
    cep = factory.Faker('postcode', locale='pt_BR')
    logradouro = factory.Faker('street_name', locale='pt_BR')
    numero = factory.Faker('building_number', locale='pt_BR')
    bairro = factory.Faker('bairro', locale='pt_BR')
    cidade = factory.Faker('city', locale='pt_BR')
    estado = 'MG'

    area = Decimal('360.00')
    valor = Decimal('100000.00')
    matricula = factory.Sequence(lambda n: f'MAT-{n:06d}')
    disponivel = True
    ativo = True


class CompradorFactory(DjangoModelFactory):
    class Meta:
        model = Comprador

    # NOTA: Comprador NÃO tem campo imobiliaria - é associado via Contrato
    tipo_pessoa = 'PF'
    nome = factory.Faker('name', locale='pt_BR')
    cpf = factory.Sequence(lambda n: f'325.513.{n:03d}-{(n % 99):02d}')
    rg = factory.Sequence(lambda n: f'MG{n:08d}')
    data_nascimento = factory.LazyFunction(lambda: date.today() - timedelta(days=365*30))
    profissao = factory.Faker('job', locale='pt_BR')
    estado_civil = 'SOLTEIRO'

    # Endereço
    cep = factory.Faker('postcode', locale='pt_BR')
    logradouro = factory.Faker('street_name', locale='pt_BR')
    numero = factory.Faker('building_number', locale='pt_BR')
    bairro = factory.Faker('bairro', locale='pt_BR')
    cidade = factory.Faker('city', locale='pt_BR')
    estado = 'MG'

    # Contato
    telefone = factory.Faker('phone_number', locale='pt_BR')
    celular = factory.Faker('phone_number', locale='pt_BR')
    email = factory.Faker('email', locale='pt_BR')

    ativo = True


# =============================================================================
# CONTRATOS
# =============================================================================

class ContratoFactory(DjangoModelFactory):
    class Meta:
        model = Contrato

    imovel = factory.SubFactory(ImovelFactory)
    comprador = factory.SubFactory(CompradorFactory)
    imobiliaria = factory.LazyAttribute(lambda obj: obj.imovel.imobiliaria)

    numero_contrato = factory.Sequence(lambda n: f'CTR-2023-{n:04d}')
    data_contrato = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    data_primeiro_vencimento = factory.LazyFunction(lambda: date.today() + timedelta(days=30))

    valor_total = Decimal('100000.00')
    valor_entrada = Decimal('10000.00')
    numero_parcelas = 12
    dia_vencimento = 5

    tipo_amortizacao = TipoAmortizacao.PRICE
    percentual_juros_mora = Decimal('1.00')
    percentual_multa = Decimal('2.00')

    tipo_correcao = TipoCorrecao.IPCA
    prazo_reajuste_meses = 12

    status = StatusContrato.ATIVO


class ParcelaFactory(DjangoModelFactory):
    class Meta:
        model = Parcela

    contrato = factory.SubFactory(ContratoFactory)
    # Use high sequence numbers to avoid UNIQUE constraint failures with auto-generated
    # parcelas (contrato_id, numero_parcela) must be unique; auto-generated start from 1
    numero_parcela = factory.Sequence(lambda n: 1000 + n)
    data_vencimento = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    valor_original = Decimal('7500.00')
    valor_atual = Decimal('7500.00')
    pago = False


class ReajusteFactory(DjangoModelFactory):
    class Meta:
        model = Reajuste

    contrato = factory.SubFactory(ContratoFactory)
    data_reajuste = factory.LazyFunction(date.today)
    indice_tipo = 'IPCA'
    percentual = Decimal('5.79')
    parcela_inicial = 1
    parcela_final = 12
    ciclo = 2
    aplicado = True
    aplicado_manual = False


# =============================================================================
# FINANCEIRO
# =============================================================================

class HistoricoPagamentoFactory(DjangoModelFactory):
    class Meta:
        model = HistoricoPagamento

    parcela = factory.SubFactory(ParcelaFactory)
    data_pagamento = factory.LazyFunction(date.today)
    valor_pago = Decimal('7500.00')
    valor_parcela = Decimal('7500.00')
    valor_juros = Decimal('0.00')
    valor_multa = Decimal('0.00')
    valor_desconto = Decimal('0.00')
    forma_pagamento = 'DINHEIRO'


class ArquivoRetornoFactory(DjangoModelFactory):
    class Meta:
        model = ArquivoRetorno

    conta_bancaria = factory.SubFactory(ContaBancariaFactory)
    nome_arquivo = factory.Sequence(lambda n: f'retorno_{n}.ret')
    layout = 'CNAB_240'
    status = StatusArquivoRetorno.PENDENTE
    arquivo = factory.django.FileField(filename='retorno.ret', data=b'HEADER\nDETALHE\nTRAILER')


class ArquivoRemessaFactory(DjangoModelFactory):
    class Meta:
        model = ArquivoRemessa

    conta_bancaria = factory.SubFactory(ContaBancariaFactory)
    numero_remessa = factory.Sequence(lambda n: n + 1)
    layout = 'CNAB_240'
    nome_arquivo = factory.Sequence(lambda n: f'remessa_{n}.rem')
    status = StatusArquivoRemessa.GERADO
    arquivo = factory.django.FileField(filename='remessa.rem', data=b'HEADER\nDETALHE\nTRAILER')
    quantidade_boletos = 1
    valor_total = Decimal('7500.00')


class ItemRemessaFactory(DjangoModelFactory):
    class Meta:
        model = ItemRemessa

    arquivo_remessa = factory.SubFactory(ArquivoRemessaFactory)
    parcela = factory.SubFactory(ParcelaFactory)
    nosso_numero = factory.Sequence(lambda n: f'00000{n:010d}')
    valor = Decimal('7500.00')
    data_vencimento = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    processado = False


class ItemRetornoFactory(DjangoModelFactory):
    class Meta:
        model = ItemRetorno

    arquivo_retorno = factory.SubFactory(ArquivoRetornoFactory)
    parcela = factory.SubFactory(ParcelaFactory)
    nosso_numero = factory.Sequence(lambda n: f'00000{n:010d}')
    codigo_ocorrencia = '06'
    tipo_ocorrencia = 'LIQUIDACAO'
    valor_titulo = Decimal('7500.00')


# =============================================================================
# NOTIFICAÇÕES
# =============================================================================

class ConfiguracaoEmailFactory(DjangoModelFactory):
    class Meta:
        model = ConfiguracaoEmail

    nome = factory.Sequence(lambda n: f'Config Email {n}')
    host = 'smtp.example.com'
    porta = 587
    usuario = factory.Sequence(lambda n: f'email{n}@example.com')
    senha = 'senha_teste'
    usar_tls = True
    usar_ssl = False
    email_remetente = factory.Sequence(lambda n: f'noreply{n}@example.com')
    nome_remetente = 'Sistema de Gestão'
    ativo = True


class ConfiguracaoSMSFactory(DjangoModelFactory):
    class Meta:
        model = ConfiguracaoSMS

    nome = factory.Sequence(lambda n: f'Config SMS {n}')
    provedor = 'TWILIO'
    account_sid = factory.Sequence(lambda n: f'AC{n:032d}')
    auth_token = factory.Sequence(lambda n: f'token{n:028d}')
    numero_remetente = '+5511999990000'
    ativo = True


class ConfiguracaoWhatsAppFactory(DjangoModelFactory):
    class Meta:
        model = ConfiguracaoWhatsApp

    nome = factory.Sequence(lambda n: f'Config WhatsApp {n}')
    provedor = 'TWILIO'
    account_sid = factory.Sequence(lambda n: f'AC{n:032d}')
    auth_token = factory.Sequence(lambda n: f'token{n:028d}')
    numero_remetente = 'whatsapp:+5511999990000'
    ativo = True


class NotificacaoFactory(DjangoModelFactory):
    class Meta:
        model = Notificacao

    parcela = factory.SubFactory(ParcelaFactory)
    tipo = TipoNotificacao.EMAIL
    destinatario = factory.Faker('email', locale='pt_BR')
    assunto = 'Notificação de Vencimento'
    mensagem = 'Sua parcela vence em breve.'
    status = 'PENDENTE'


class TemplateNotificacaoFactory(DjangoModelFactory):
    class Meta:
        model = TemplateNotificacao

    nome = factory.Sequence(lambda n: f'Template {n}')
    codigo = TipoTemplate.LEMBRETE_PARCELA
    tipo = TipoNotificacao.EMAIL
    assunto = 'Lembrete: parcela %%PARCELA%% vence em %%DATAVENCIMENTO%%'
    corpo = 'Olá %%NOMECOMPRADOR%%, sua parcela %%PARCELA%% vence em %%DATAVENCIMENTO%%.'
    ativo = True


class RegraNotificacaoFactory(DjangoModelFactory):
    class Meta:
        model = RegraNotificacao

    nome = factory.Sequence(lambda n: f'Regra {n}')
    ativo = True
    tipo_gatilho = TipoGatilho.ANTES_VENCIMENTO
    dias_offset = factory.Sequence(lambda n: n + 1)
    tipo_notificacao = TipoNotificacao.EMAIL


# =============================================================================
# PORTAL DO COMPRADOR
# =============================================================================

class AcessoCompradorFactory(DjangoModelFactory):
    class Meta:
        model = AcessoComprador

    comprador = factory.SubFactory(CompradorFactory)
    usuario = factory.SubFactory(UserFactory)
    email_verificado = True
    ativo = True


class LogAcessoCompradorFactory(DjangoModelFactory):
    class Meta:
        model = LogAcessoComprador

    acesso_comprador = factory.SubFactory(AcessoCompradorFactory)
    ip_acesso = '127.0.0.1'
    user_agent = 'Mozilla/5.0 (Test)'
    pagina_acessada = '/portal/'


# =============================================================================
# CORE — ACESSO USUÁRIO
# =============================================================================

class AcessoUsuarioFactory(DjangoModelFactory):
    class Meta:
        model = AcessoUsuario

    usuario = factory.SubFactory(UserFactory)
    contabilidade = factory.SubFactory(ContabilidadeFactory)
    imobiliaria = factory.LazyAttribute(
        lambda obj: ImobiliariaFactory(contabilidade=obj.contabilidade)
    )
    pode_editar = True
    pode_excluir = False
    ativo = True
