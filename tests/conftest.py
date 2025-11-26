"""
Configuração global do pytest para testes

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from pytest_factoryboy import register
from django.conf import settings
from django.test import Client
from rest_framework.test import APIClient

# Importar todas as factories
from tests.fixtures.factories import (
    UserFactory,
    SuperUserFactory,
    ContabilidadeFactory,
    ImobiliariaFactory,
    ContaBancariaFactory,
    ImovelFactory,
    CompradorFactory,
    ContratoFactory,
    ParcelaFactory,
    ReajusteFactory,
    HistoricoPagamentoFactory,
    ArquivoRetornoFactory,
)

# Registrar factories para uso automático nos testes
# Isso permite usar fixtures como 'user', 'imobiliaria', etc.
register(UserFactory)
register(SuperUserFactory, 'superuser')
register(ContabilidadeFactory)
register(ImobiliariaFactory)
register(ContaBancariaFactory)
register(ImovelFactory)
register(CompradorFactory)
register(ContratoFactory)
register(ParcelaFactory)
register(ReajusteFactory)
register(HistoricoPagamentoFactory)
register(ArquivoRetornoFactory)


# =============================================================================
# FIXTURES GLOBAIS
# =============================================================================

@pytest.fixture
def api_client():
    """Cliente da API REST Framework"""
    return APIClient()


@pytest.fixture
def client():
    """Cliente HTTP do Django"""
    return Client()


@pytest.fixture
def authenticated_client(db, user_factory):
    """Cliente HTTP autenticado"""
    client = Client()
    user = user_factory(password='testpass123')
    client.login(username=user.username, password='testpass123')
    return client


@pytest.fixture
def authenticated_api_client(db, user_factory):
    """Cliente API autenticado"""
    client = APIClient()
    user = user_factory(password='testpass123')
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(db, superuser_factory):
    """Cliente HTTP autenticado como admin"""
    client = Client()
    admin = superuser_factory(password='admin123')
    client.login(username=admin.username, password='admin123')
    return client


@pytest.fixture
def admin_api_client(db, superuser_factory):
    """Cliente API autenticado como admin"""
    client = APIClient()
    admin = superuser_factory(password='admin123')
    client.force_authenticate(user=admin)
    return client


# =============================================================================
# FIXTURES DE DADOS COMUNS
# =============================================================================

@pytest.fixture
def contrato_completo(db, contrato_factory, conta_bancaria_factory):
    """
    Cria um contrato completo com:
    - Contabilidade
    - Imobiliária com conta bancária
    - Imóvel
    - Comprador
    - Contrato
    - 12 Parcelas
    """
    contrato = contrato_factory(numero_parcelas=12)
    conta_bancaria_factory(imobiliaria=contrato.imobiliaria)

    # Gerar parcelas
    contrato.gerar_parcelas()

    return contrato


@pytest.fixture
def parcela_vencida(db, parcela_factory):
    """Cria uma parcela vencida (30 dias atrás)"""
    from datetime import date, timedelta
    return parcela_factory(
        data_vencimento=date.today() - timedelta(days=30),
        status='vencida'
    )


@pytest.fixture
def parcela_paga(db, parcela_factory, historico_pagamento_factory):
    """Cria uma parcela já paga"""
    parcela = parcela_factory(status='paga')
    historico_pagamento_factory(parcela=parcela)
    return parcela


# =============================================================================
# FIXTURES DE MOCKS
# =============================================================================

@pytest.fixture
def mock_brcobranca_success(requests_mock):
    """Mock da API BRCobranca retornando sucesso"""
    requests_mock.get(
        'https://brcobranca-api.onrender.com/api/boleto',
        content=b'%PDF-1.4 Mock PDF Content',
        status_code=200
    )
    return requests_mock


@pytest.fixture
def mock_brcobranca_error(requests_mock):
    """Mock da API BRCobranca retornando erro 500"""
    requests_mock.get(
        'https://brcobranca-api.onrender.com/api/boleto',
        json={'erro': 'Erro interno do servidor'},
        status_code=500
    )
    return requests_mock


@pytest.fixture
def mock_banco_central_success(requests_mock):
    """Mock da API do Banco Central retornando índices"""
    requests_mock.get(
        'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados',
        json=[
            {
                'data': '01/01/2023',
                'valor': '5.79'
            }
        ],
        status_code=200
    )
    return requests_mock


@pytest.fixture
def mock_viacep_success(requests_mock):
    """Mock da API ViaCEP retornando endereço"""
    requests_mock.get(
        'https://viacep.com.br/ws/35702000/json/',
        json={
            'cep': '35702-000',
            'logradouro': 'Rua Teste',
            'bairro': 'Centro',
            'localidade': 'Sete Lagoas',
            'uf': 'MG'
        },
        status_code=200
    )
    return requests_mock


# =============================================================================
# CONFIGURAÇÕES DE TESTE
# =============================================================================

@pytest.fixture(autouse=True)
def configure_test_settings(settings):
    """Configurações específicas para testes"""
    settings.DEBUG = False
    settings.CELERY_TASK_ALWAYS_EAGER = True  # Executa tasks síncronamente
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    return settings


# =============================================================================
# HELPERS
# =============================================================================

@pytest.fixture
def assert_redirects():
    """Helper para validar redirects"""
    def _assert_redirects(response, expected_url, status_code=302):
        assert response.status_code == status_code
        assert response.url == expected_url
    return _assert_redirects


@pytest.fixture
def assert_contains():
    """Helper para validar conteúdo de resposta"""
    def _assert_contains(response, text, count=None):
        content = response.content.decode('utf-8')
        if count is None:
            assert text in content
        else:
            assert content.count(text) == count
    return _assert_contains
