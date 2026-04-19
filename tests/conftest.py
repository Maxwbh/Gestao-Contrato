"""
Configuração global do pytest para testes

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from pytest_factoryboy import register
from django.test import Client

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
    # CNAB
    ArquivoRemessaFactory,
    ItemRemessaFactory,
    ItemRetornoFactory,
    # Notificações
    ConfiguracaoEmailFactory,
    ConfiguracaoSMSFactory,
    ConfiguracaoWhatsAppFactory,
    NotificacaoFactory,
    TemplateNotificacaoFactory,
    RegraNotificacaoFactory,
    # Portal do Comprador
    AcessoCompradorFactory,
    LogAcessoCompradorFactory,
    # Core
    AcessoUsuarioFactory,
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
# CNAB
register(ArquivoRemessaFactory)
register(ItemRemessaFactory)
register(ItemRetornoFactory)
# Notificações
register(ConfiguracaoEmailFactory)
register(ConfiguracaoSMSFactory)
register(ConfiguracaoWhatsAppFactory)
register(NotificacaoFactory)
register(TemplateNotificacaoFactory)
register(RegraNotificacaoFactory)
# Portal do Comprador
register(AcessoCompradorFactory)
register(LogAcessoCompradorFactory)
# Core
register(AcessoUsuarioFactory)


# =============================================================================
# FIXTURES GLOBAIS
# =============================================================================

@pytest.fixture
def api_client():
    """Cliente HTTP do Django (sem DRF)"""
    return Client()


@pytest.fixture
def client():
    """Cliente HTTP do Django"""
    return Client()


@pytest.fixture
def requests_mock():
    """Mock para requisições HTTP usando requests-mock"""
    import requests_mock as rm
    with rm.Mocker() as m:
        yield m


@pytest.fixture
def authenticated_client(db, user_factory):
    """Cliente HTTP autenticado"""
    client = Client()
    user = user_factory(password='testpass123')
    client.login(username=user.username, password='testpass123')
    return client


@pytest.fixture
def authenticated_api_client(db, user_factory):
    """Cliente HTTP autenticado (alias)"""
    client = Client()
    user = user_factory(password='testpass123')
    client.force_login(user)
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
    """Cliente HTTP autenticado como admin (alias)"""
    client = Client()
    admin = superuser_factory(password='admin123')
    client.force_login(admin)
    return client


@pytest.fixture
def client_logged_in(db, user_factory):
    """Cliente HTTP autenticado como usuário comum (alias)"""
    client = Client()
    user = user_factory(password='testpass123')
    client.force_login(user)
    return client


@pytest.fixture
def client_admin(db, super_user_factory):
    """Cliente HTTP autenticado como admin"""
    client = Client()
    admin = super_user_factory(password='admin123')
    client.force_login(admin)
    return client


# =============================================================================
# FIXTURES ESPECÍFICAS DE COMPRADOR
# =============================================================================

@pytest.fixture
def comprador_pf(db):
    """Comprador Pessoa Física para testes"""
    from core.models import Comprador
    return Comprador.objects.create(
        tipo_pessoa='PF',
        nome='João da Silva',
        cpf='123.456.789-01',
        email='joao@teste.com',
        telefone='(31) 3333-4444',
        celular='(31) 99999-8888',
    )


@pytest.fixture
def comprador_pj(db):
    """Comprador Pessoa Jurídica para testes"""
    from core.models import Comprador
    return Comprador.objects.create(
        tipo_pessoa='PJ',
        nome='Empresa Teste LTDA',
        cnpj='12.345.678/0001-90',
        email='empresa@teste.com',
        telefone='(31) 3333-5555',
        celular='(31) 88888-7777',
    )


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
    # Service uses BRCOBRANCA_URL setting (defaults to http://localhost:9292)
    requests_mock.get(
        'http://localhost:9292/api/boleto',
        content=b'%PDF-1.4 Mock PDF Content',
        status_code=200
    )
    # Also register legacy URL in case settings override
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
        'http://localhost:9292/api/boleto',
        json={'erro': 'Erro interno do servidor'},
        status_code=500
    )
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


@pytest.fixture
def mock_twilio_sms(mocker):
    """Mock do cliente Twilio SMS"""
    mock_client = mocker.MagicMock()
    mock_message = mocker.MagicMock()
    mock_message.sid = 'SM00000000000000000000000000000000'
    mock_client.messages.create.return_value = mock_message
    mocker.patch('notificacoes.services.Client', return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_twilio_whatsapp(mocker):
    """Mock do cliente Twilio WhatsApp"""
    mock_client = mocker.MagicMock()
    mock_message = mocker.MagicMock()
    mock_message.sid = 'MM00000000000000000000000000000000'
    mock_client.messages.create.return_value = mock_message
    mocker.patch('notificacoes.services.Client', return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_twilio_error(mocker):
    """Mock do cliente Twilio retornando erro"""
    from twilio.base.exceptions import TwilioRestException
    mock_client = mocker.MagicMock()
    mock_client.messages.create.side_effect = TwilioRestException(
        status=400, uri='/Messages', msg='Invalid phone number'
    )
    mocker.patch('notificacoes.services.Client', return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_ibge_ipca(requests_mock):
    """Mock da API IBGE retornando série IPCA (código 433)"""
    requests_mock.get(
        'https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/202301|202302|202303|202304|202305|202306|202307|202308|202309|202310|202311|202312/variaveis/2266?localidades=N1[all]',
        json=[{
            'id': '2266',
            'resultados': [{
                'series': [{
                    'serie': {
                        '202301': '0.53', '202302': '0.84', '202303': '0.71',
                        '202304': '0.61', '202305': '0.23', '202306': '-0.08',
                        '202307': '0.12', '202308': '0.23', '202309': '0.26',
                        '202310': '0.24', '202311': '0.28', '202312': '0.62',
                    }
                }]
            }]
        }],
        status_code=200
    )
    # Also mock the BCB fallback URL (SGS série 433)
    requests_mock.get(
        'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados',
        json=[{'data': '01/12/2023', 'valor': '4.62'}],
        status_code=200
    )
    return requests_mock


@pytest.fixture
def mock_ibge_inpc(requests_mock):
    """Mock da API IBGE retornando série INPC (código 188)"""
    requests_mock.get(
        'https://api.bcb.gov.br/dados/serie/bcdata.sgs.188/dados',
        json=[{'data': '01/12/2023', 'valor': '3.74'}],
        status_code=200
    )
    return requests_mock


@pytest.fixture
def mock_smtp(settings, mailoutbox):
    """Mock do SMTP — usa o backend locmem do Django"""
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    return mailoutbox


@pytest.fixture
def mock_ibge_error(requests_mock):
    """Mock da API IBGE retornando erro"""
    requests_mock.get(
        'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados',
        status_code=503
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
    # Use simpler static files storage to avoid collectstatic requirement
    settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    # Disable HTTPS redirect for tests
    settings.SECURE_SSL_REDIRECT = False
    # Add humanize for template tag support
    if 'django.contrib.humanize' not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ['django.contrib.humanize']
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
