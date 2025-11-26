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
)
from contratos.models import Contrato, Parcela, Reajuste
from financeiro.models import HistoricoPagamento, ArquivoRetorno

fake = Faker('pt_BR')
User = get_user_model()


# =============================================================================
# AUTH & ACCOUNTS
# =============================================================================

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

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
    nome = factory.Sequence(lambda n: f'Imobiliária {n}')
    razao_social = factory.LazyAttribute(lambda obj: f'{obj.nome} Negócios Imobiliários LTDA')
    cnpj = factory.Sequence(lambda n: f'34567892{n:06d}22')

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
    descricao = factory.LazyAttribute(lambda obj: f'Loteamento Premium - {obj.identificacao}')

    # Endereço
    cep = factory.Faker('postcode', locale='pt_BR')
    logradouro = factory.Faker('street_name', locale='pt_BR')
    numero = factory.Faker('building_number', locale='pt_BR')
    bairro = factory.Faker('bairro', locale='pt_BR')
    cidade = factory.Faker('city', locale='pt_BR')
    estado = 'MG'

    # Dimensões
    area_total = Decimal('360.00')
    area_construida = Decimal('0.00')
    testada = Decimal('12.00')

    matricula = factory.Sequence(lambda n: f'MAT-{n:06d}')
    status = 'disponivel'
    valor_venda = Decimal('100000.00')
    ativo = True


class CompradorFactory(DjangoModelFactory):
    class Meta:
        model = Comprador

    imobiliaria = factory.SubFactory(ImobiliariaFactory)
    tipo_pessoa = 'PF'
    nome = factory.Faker('name', locale='pt_BR')
    cpf = factory.Sequence(lambda n: f'325513065{n:02d}')
    rg = factory.Sequence(lambda n: f'MG{n:08d}')
    data_nascimento = factory.LazyFunction(lambda: date.today() - timedelta(days=365*30))
    profissao = factory.Faker('job', locale='pt_BR')
    estado_civil = 'solteiro'

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

    percentual_juros_mora = Decimal('0.033')
    percentual_multa = Decimal('2.00')

    tipo_correcao = 'IPCA'
    prazo_reajuste_meses = 12

    status = 'ativo'


class ParcelaFactory(DjangoModelFactory):
    class Meta:
        model = Parcela

    contrato = factory.SubFactory(ContratoFactory)
    numero_parcela = factory.Sequence(lambda n: n + 1)
    data_vencimento = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    valor_original = Decimal('7500.00')
    valor_atual = Decimal('7500.00')
    status = 'pendente'


class ReajusteFactory(DjangoModelFactory):
    class Meta:
        model = Reajuste

    contrato = factory.SubFactory(ContratoFactory)
    data_reajuste = factory.LazyFunction(date.today)
    indice_tipo = 'IPCA'
    percentual = Decimal('5.79')
    parcela_inicial = 1
    parcela_final = 12
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
    forma_pagamento = 'dinheiro'


class ArquivoRetornoFactory(DjangoModelFactory):
    class Meta:
        model = ArquivoRetorno

    conta_bancaria = factory.SubFactory(ContaBancariaFactory)
    nome_arquivo = factory.Sequence(lambda n: f'retorno_{n}.ret')
    data_upload = factory.LazyFunction(date.today)
    processado = False
