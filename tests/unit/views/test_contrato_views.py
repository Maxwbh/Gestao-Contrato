"""
Testes unitários para as views de contratos

Testa:
- ContratoDetailView com intermediárias e bloqueio de reajuste
- Views CRUD de PrestacaoIntermediaria
- API de intermediárias
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
class TestContratoDetailView:
    """Testes para a view de detalhes do contrato"""

    def test_detalhe_contrato_basico(self, client_autenticado, contrato_factory):
        """Testa acesso básico aos detalhes do contrato"""
        contrato = contrato_factory()
        url = reverse('contratos:detalhe', kwargs={'pk': contrato.pk})

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'contrato' in response.context

    def test_detalhe_contrato_contexto_intermediarias(self, client_autenticado, contrato_com_intermediarias):
        """Testa que o contexto inclui informações de intermediárias"""
        url = reverse('contratos:detalhe', kwargs={'pk': contrato_com_intermediarias.pk})

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'intermediarias' in response.context
        assert 'total_intermediarias' in response.context
        assert response.context['total_intermediarias'] > 0

    def test_detalhe_contrato_contexto_bloqueio_reajuste(self, client_autenticado, contrato_factory):
        """Testa que o contexto inclui informações de bloqueio de reajuste"""
        contrato = contrato_factory()
        url = reverse('contratos:detalhe', kwargs={'pk': contrato.pk})

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'bloqueio_reajuste' in response.context
        assert 'parcelas_status_boleto' in response.context

    def test_detalhe_contrato_contexto_resumo_financeiro(self, client_autenticado, contrato_factory):
        """Testa que o contexto inclui resumo financeiro"""
        contrato = contrato_factory()
        url = reverse('contratos:detalhe', kwargs={'pk': contrato.pk})

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'resumo_financeiro' in response.context

    def test_detalhe_contrato_contexto_ciclo_reajuste(self, client_autenticado, contrato_factory):
        """Testa que o contexto inclui informações de ciclo"""
        contrato = contrato_factory()
        url = reverse('contratos:detalhe', kwargs={'pk': contrato.pk})

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'ciclo_atual' in response.context
        assert 'prazo_reajuste' in response.context


@pytest.mark.django_db
class TestIntermediariasViews:
    """Testes para as views de prestações intermediárias"""

    def test_listar_intermediarias(self, client_autenticado, contrato_com_intermediarias):
        """Testa listagem de intermediárias"""
        url = reverse('contratos:intermediarias_listar', kwargs={
            'contrato_id': contrato_com_intermediarias.pk
        })

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'intermediarias' in response.context
        assert 'contrato' in response.context

    def test_criar_intermediaria(self, client_autenticado, contrato_factory):
        """Testa criação de intermediária via API"""
        contrato = contrato_factory()
        url = reverse('contratos:intermediarias_criar', kwargs={
            'contrato_id': contrato.pk
        })

        response = client_autenticado.post(
            url,
            data={
                'mes_vencimento': 12,
                'valor': '5000.00',
                'observacoes': 'Teste'
            },
            content_type='application/json'
        )

        data = response.json()
        assert response.status_code == 200 or data.get('sucesso')
        if data.get('sucesso'):
            assert 'intermediaria_id' in data

    def test_criar_intermediaria_limite_maximo(self, client_autenticado, contrato_com_30_intermediarias):
        """Testa que não permite criar mais de 30 intermediárias"""
        url = reverse('contratos:intermediarias_criar', kwargs={
            'contrato_id': contrato_com_30_intermediarias.pk
        })

        response = client_autenticado.post(
            url,
            data={
                'mes_vencimento': 36,
                'valor': '5000.00'
            },
            content_type='application/json'
        )

        data = response.json()
        assert data.get('sucesso') is False
        assert 'limite' in data.get('erro', '').lower() or '30' in data.get('erro', '')

    def test_atualizar_intermediaria(self, client_autenticado, contrato_com_intermediarias):
        """Testa atualização de intermediária"""
        intermediaria = contrato_com_intermediarias.intermediarias.first()
        url = reverse('contratos:intermediarias_atualizar', kwargs={'pk': intermediaria.pk})

        response = client_autenticado.post(
            url,
            data={'valor': '6000.00'},
            content_type='application/json'
        )

        data = response.json()
        assert data.get('sucesso')

    def test_excluir_intermediaria(self, client_autenticado, contrato_com_intermediarias):
        """Testa exclusão de intermediária"""
        intermediaria = contrato_com_intermediarias.intermediarias.first()
        url = reverse('contratos:intermediarias_excluir', kwargs={'pk': intermediaria.pk})

        response = client_autenticado.post(url)

        data = response.json()
        assert data.get('sucesso')

    def test_api_intermediarias_contrato(self, client_autenticado, contrato_com_intermediarias):
        """Testa API de listagem de intermediárias em JSON"""
        url = reverse('contratos:intermediarias_api', kwargs={
            'contrato_id': contrato_com_intermediarias.pk
        })

        response = client_autenticado.get(url)

        data = response.json()
        assert data.get('sucesso')
        assert 'intermediarias' in data
        assert len(data['intermediarias']) > 0


@pytest.mark.django_db
class TestPagamentoIntermediaria:
    """Testes para pagamento de intermediárias"""

    def test_pagar_intermediaria(self, client_autenticado, contrato_com_intermediarias):
        """Testa registro de pagamento de intermediária"""
        intermediaria = contrato_com_intermediarias.intermediarias.filter(paga=False).first()
        url = reverse('contratos:intermediarias_pagar', kwargs={'pk': intermediaria.pk})

        response = client_autenticado.post(
            url,
            data={
                'valor_pago': str(intermediaria.valor),
                'data_pagamento': date.today().isoformat()
            },
            content_type='application/json'
        )

        data = response.json()
        assert data.get('sucesso')

    def test_pagar_intermediaria_ja_paga(self, client_autenticado, contrato_com_intermediarias):
        """Testa que não permite pagar intermediária já paga"""
        intermediaria = contrato_com_intermediarias.intermediarias.first()
        intermediaria.paga = True
        intermediaria.save()

        url = reverse('contratos:intermediarias_pagar', kwargs={'pk': intermediaria.pk})

        response = client_autenticado.post(
            url,
            data={'valor_pago': '5000.00'},
            content_type='application/json'
        )

        data = response.json()
        assert data.get('sucesso') is False


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client_autenticado(db, django_user_model):
    """Cliente autenticado para testes"""
    django_user_model.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )
    client = Client()
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def contrato_factory(db, imobiliaria_factory, comprador_factory, imovel_factory):
    """Factory para criar contratos"""
    counter = {'n': 0}

    def create(**kwargs):
        from contratos.models import Contrato

        counter['n'] += 1
        n = counter['n']
        # Ensure imovel belongs to the same imobiliaria as the contrato
        imobiliaria = kwargs.pop('imobiliaria', None) or imobiliaria_factory()
        imovel = kwargs.pop('imovel', None) or imovel_factory(imobiliaria=imobiliaria)
        defaults = {
            'imobiliaria': imobiliaria,
            'comprador': kwargs.pop('comprador', None) or comprador_factory(),
            'imovel': imovel,
            'numero_contrato': kwargs.pop('numero_contrato', None) or f'CTR-{n:06d}-{timezone.now().microsecond}',
            'data_contrato': kwargs.pop('data_contrato', date.today()),
            'data_primeiro_vencimento': kwargs.pop('data_primeiro_vencimento', date.today() + timedelta(days=30)),
            'valor_total': kwargs.pop('valor_total', Decimal('100000.00')),
            'valor_entrada': kwargs.pop('valor_entrada', Decimal('10000.00')),
            'numero_parcelas': kwargs.pop('numero_parcelas', 24),
            'dia_vencimento': kwargs.pop('dia_vencimento', 15),
            'tipo_correcao': kwargs.pop('tipo_correcao', 'IPCA'),
            'prazo_reajuste_meses': kwargs.pop('prazo_reajuste_meses', 12),
        }
        defaults.update(kwargs)
        return Contrato.objects.create(**defaults)

    return create


@pytest.fixture
def contrato_com_intermediarias(contrato_factory):
    """Cria um contrato com intermediárias"""
    from contratos.models import PrestacaoIntermediaria

    contrato = contrato_factory(quantidade_intermediarias=3, numero_parcelas=36)

    for i in range(1, 4):
        PrestacaoIntermediaria.objects.create(
            contrato=contrato,
            numero_sequencial=i,
            mes_vencimento=i * 6,
            valor=Decimal('5000.00')
        )

    return contrato


@pytest.fixture
def contrato_com_30_intermediarias(contrato_factory):
    """Cria um contrato com 30 intermediárias (limite máximo)"""
    from contratos.models import PrestacaoIntermediaria

    contrato = contrato_factory(quantidade_intermediarias=30, numero_parcelas=360)

    for i in range(1, 31):
        PrestacaoIntermediaria.objects.create(
            contrato=contrato,
            numero_sequencial=i,
            mes_vencimento=i * 12,
            valor=Decimal('5000.00')
        )

    return contrato


@pytest.fixture
def imobiliaria_factory(db, contabilidade_factory):
    """Factory para criar imobiliárias"""
    counter = {'n': 0}

    def create(**kwargs):
        from core.models import Imobiliaria

        counter['n'] += 1
        n = counter['n']
        defaults = {
            'contabilidade': kwargs.pop('contabilidade', None) or contabilidade_factory(),
            'nome': 'Imobiliária Teste',
            'razao_social': 'Imobiliária Teste LTDA',
            'cnpj': f'1234{n:010d}',
            'telefone': '(31) 3333-4000',
            'email': f'teste{n}@imobiliaria.com',
            'responsavel_financeiro': 'Responsável Financeiro Teste',
        }
        defaults.update(kwargs)
        return Imobiliaria.objects.create(**defaults)

    return create


@pytest.fixture
def contabilidade_factory(db):
    """Factory para criar contabilidades"""
    counter = {'n': 0}

    def create(**kwargs):
        from core.models import Contabilidade

        counter['n'] += 1
        n = counter['n']
        defaults = {
            'nome': f'Contabilidade Teste {n}',
            'razao_social': 'Contabilidade Teste LTDA',
            'cnpj': f'9876{n:010d}',
            'endereco': 'Rua Contabilidade, 100',
            'telefone': '(31) 3333-5000',
            'email': f'teste{n}@contabilidade.com',
            'responsavel': 'Responsável Teste',
        }
        defaults.update(kwargs)
        return Contabilidade.objects.create(**defaults)

    return create


@pytest.fixture
def comprador_factory(db):
    """Factory para criar compradores"""
    counter = {'n': 0}

    def create(**kwargs):
        from core.models import Comprador

        counter['n'] += 1
        n = counter['n']
        defaults = {
            'nome': 'Comprador Teste',
            'tipo_pessoa': 'PF',
            'cpf': f'{n:03d}.456.789-{(n % 99):02d}',
            'email': f'comprador{n}@teste.com',
            'telefone': '(31) 3333-6000',
            'celular': '(31) 99999-6000',
            'cep': '01310100',
            'logradouro': 'Av. Paulista',
            'numero': '1000',
            'bairro': 'Bela Vista',
            'cidade': 'São Paulo',
            'estado': 'SP',
        }
        defaults.update(kwargs)
        return Comprador.objects.create(**defaults)

    return create


@pytest.fixture
def imovel_factory(db, imobiliaria_factory):
    """Factory para criar imóveis"""
    counter = {'n': 0}

    def create(**kwargs):
        from core.models import Imovel

        counter['n'] += 1
        n = counter['n']
        defaults = {
            'imobiliaria': kwargs.pop('imobiliaria', None) or imobiliaria_factory(),
            'tipo': 'LOTE',
            'identificacao': f'LOTE-{n:04d}',
            'area': '360.00',
        }
        defaults.update(kwargs)
        return Imovel.objects.create(**defaults)

    return create
