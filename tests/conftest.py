"""
Configuração global de testes para o projeto Gestão de Contratos.

Este arquivo contém fixtures compartilhadas entre todos os testes.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    """Cria um usuário comum para testes."""
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Cria um superusuário para testes."""
    User = get_user_model()
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def contabilidade(db):
    """Cria uma contabilidade para testes."""
    from core.models import Contabilidade
    return Contabilidade.objects.create(
        nome='Contabilidade Teste',
        cnpj='12.345.678/0001-90',
        email='contato@contabilidade.com',
        telefone='(11) 99999-9999',
        logradouro='Rua Teste',
        numero='100',
        bairro='Centro',
        cidade='São Paulo',
        estado='SP',
        cep='01000-000'
    )


@pytest.fixture
def imobiliaria(db, contabilidade):
    """Cria uma imobiliária para testes."""
    from core.models import Imobiliaria
    return Imobiliaria.objects.create(
        contabilidade=contabilidade,
        nome='Imobiliária Teste',
        cnpj='98.765.432/0001-10',
        email='contato@imobiliaria.com',
        telefone='(11) 88888-8888',
        logradouro='Av. Principal',
        numero='500',
        bairro='Centro',
        cidade='São Paulo',
        estado='SP',
        cep='01001-000'
    )


@pytest.fixture
def comprador_pf(db, contabilidade):
    """Cria um comprador pessoa física para testes."""
    from core.models import Comprador
    return Comprador.objects.create(
        contabilidade=contabilidade,
        nome='João da Silva',
        tipo='PF',
        cpf_cnpj='123.456.789-09',
        email='joao@example.com',
        telefone='(11) 97777-7777',
        logradouro='Rua do Comprador',
        numero='200',
        bairro='Vila Nova',
        cidade='São Paulo',
        estado='SP',
        cep='02000-000'
    )


@pytest.fixture
def comprador_pj(db, contabilidade):
    """Cria um comprador pessoa jurídica para testes."""
    from core.models import Comprador
    return Comprador.objects.create(
        contabilidade=contabilidade,
        nome='Empresa ABC Ltda',
        tipo='PJ',
        cpf_cnpj='11.222.333/0001-44',
        email='contato@empresaabc.com',
        telefone='(11) 3333-3333',
        logradouro='Av. Empresarial',
        numero='1000',
        bairro='Centro Empresarial',
        cidade='São Paulo',
        estado='SP',
        cep='03000-000'
    )


@pytest.fixture
def imovel(db, imobiliaria):
    """Cria um imóvel para testes."""
    from core.models import Imovel
    return Imovel.objects.create(
        imobiliaria=imobiliaria,
        tipo='LOTE',
        identificacao='Lote 001',
        quadra='A',
        lote='01',
        area_total=Decimal('300.00'),
        logradouro='Rua do Loteamento',
        numero='S/N',
        bairro='Novo Horizonte',
        cidade='São Paulo',
        estado='SP',
        cep='04000-000',
        valor_venda=Decimal('150000.00')
    )


@pytest.fixture
def contrato(db, imovel, comprador_pf):
    """Cria um contrato para testes."""
    from contratos.models import Contrato
    return Contrato.objects.create(
        imovel=imovel,
        comprador=comprador_pf,
        numero='CT-001',
        data_contrato=date.today(),
        valor_total=Decimal('150000.00'),
        valor_entrada=Decimal('30000.00'),
        numero_parcelas=120,
        dia_vencimento=10,
        tipo_reajuste='IPCA',
        periodicidade_reajuste=12,
        taxa_juros_atraso=Decimal('1.00'),
        multa_atraso=Decimal('2.00')
    )


@pytest.fixture
def parcela(db, contrato):
    """Cria uma parcela para testes."""
    from financeiro.models import Parcela
    return Parcela.objects.create(
        contrato=contrato,
        numero_parcela=1,
        valor_original=Decimal('1000.00'),
        valor_atual=Decimal('1000.00'),
        data_vencimento=date.today() + timedelta(days=30),
        status='PENDENTE'
    )


@pytest.fixture
def client_logged_in(client, user):
    """Cliente HTTP autenticado como usuário comum."""
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def client_admin(client, admin_user):
    """Cliente HTTP autenticado como administrador."""
    client.login(username='admin', password='adminpass123')
    return client
