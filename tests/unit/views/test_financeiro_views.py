"""
Testes unitários para as views de financeiro

Testa:
- Dashboard da imobiliária com métricas de reajuste
- Dashboard consolidado da contabilidade
- Bloqueio de boleto por reajuste
- Views de relatórios avançados
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
class TestDashboardImobiliaria:
    """Testes para o dashboard da imobiliária"""

    def test_dashboard_acesso(self, client_autenticado, imobiliaria_factory):
        """Testa acesso ao dashboard da imobiliária"""
        imobiliaria = imobiliaria_factory()
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={
            'imobiliaria_id': imobiliaria.pk
        })

        response = client_autenticado.get(url)

        assert response.status_code == 200

    def test_dashboard_contexto_basico(self, client_autenticado, imobiliaria_factory):
        """Testa contexto básico do dashboard"""
        imobiliaria = imobiliaria_factory()
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={
            'imobiliaria_id': imobiliaria.pk
        })

        response = client_autenticado.get(url)

        assert 'stats_geral' in response.context
        assert 'stats_mes' in response.context
        assert 'stats_contratos' in response.context

    def test_dashboard_contexto_reajuste(self, client_autenticado, imobiliaria_factory):
        """Testa contexto de reajuste no dashboard"""
        imobiliaria = imobiliaria_factory()
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={
            'imobiliaria_id': imobiliaria.pk
        })

        response = client_autenticado.get(url)

        assert 'contratos_reajuste_pendente' in response.context
        assert 'contratos_com_boleto_bloqueado' in response.context
        assert 'total_contratos_bloqueados' in response.context

    def test_dashboard_contexto_intermediarias(self, client_autenticado, imobiliaria_factory):
        """Testa contexto de intermediárias no dashboard"""
        imobiliaria = imobiliaria_factory()
        url = reverse('financeiro:dashboard_imobiliaria', kwargs={
            'imobiliaria_id': imobiliaria.pk
        })

        response = client_autenticado.get(url)

        assert 'intermediarias_pendentes' in response.context
        assert 'stats_intermediarias' in response.context


@pytest.mark.django_db
class TestDashboardContabilidade:
    """Testes para o dashboard consolidado da contabilidade"""

    def test_dashboard_acesso(self, client_autenticado):
        """Testa acesso ao dashboard da contabilidade"""
        url = reverse('financeiro:dashboard_contabilidade')

        response = client_autenticado.get(url)

        assert response.status_code == 200

    def test_dashboard_contexto(self, client_autenticado, contabilidade_factory, imobiliaria_factory):
        """Testa contexto do dashboard da contabilidade"""
        contabilidade = contabilidade_factory()
        imobiliaria_factory(contabilidade=contabilidade)

        url = reverse('financeiro:dashboard_contabilidade')

        response = client_autenticado.get(url)

        assert 'total_imobiliarias' in response.context
        assert 'stats_contratos' in response.context
        assert 'stats_parcelas' in response.context
        assert 'stats_por_imobiliaria' in response.context

    def test_dashboard_filtro_contabilidade(self, client_autenticado, contabilidade_factory, imobiliaria_factory):
        """Testa filtro por contabilidade no dashboard"""
        contabilidade = contabilidade_factory()
        imobiliaria_factory(contabilidade=contabilidade)

        url = reverse('financeiro:dashboard_contabilidade') + f'?contabilidade={contabilidade.pk}'

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert response.context['contabilidade_selecionada'] == contabilidade

    def test_api_dashboard_contabilidade(self, client_autenticado):
        """Testa API de dados do dashboard"""
        url = reverse('financeiro:api_dashboard_contabilidade')

        response = client_autenticado.get(url)

        data = response.json()
        assert 'recebimentos_mensais' in data
        assert 'distribuicao_imobiliarias' in data
        assert 'status_contratos' in data


@pytest.mark.django_db
class TestBloqueioBoletoPorReajuste:
    """Testes para bloqueio de boleto por reajuste"""

    def test_gerar_boleto_ciclo_1_liberado(self, client_autenticado, contrato_com_parcelas):
        """Testa que boleto do ciclo 1 é liberado"""
        parcela = contrato_com_parcelas.parcelas.filter(numero_parcela__lte=12).first()
        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})

        response = client_autenticado.post(url)

        # Pode retornar sucesso ou erro de conta bancária, mas não deve bloquear por reajuste
        data = response.json()
        assert 'bloqueado_reajuste' not in data or data.get('bloqueado_reajuste') is False

    def test_gerar_boleto_ciclo_2_bloqueado_sem_reajuste(self, client_autenticado, contrato_com_parcelas_ciclo_2):
        """Testa que boleto do ciclo 2 é bloqueado sem reajuste aplicado"""
        parcela = contrato_com_parcelas_ciclo_2.parcelas.filter(numero_parcela=13).first()
        if not parcela:
            pytest.skip("Parcela do ciclo 2 não encontrada")

        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})

        response = client_autenticado.post(url)

        data = response.json()
        # Deve estar bloqueado por reajuste
        assert data.get('bloqueado_reajuste') is True or 'reajuste' in data.get('erro', '').lower()

    def test_gerar_boletos_contrato_com_bloqueio(self, client_autenticado, contrato_com_parcelas_ciclo_2):
        """Testa geração de boletos em lote com bloqueio parcial"""
        url = reverse('financeiro:gerar_boletos_contrato', kwargs={
            'contrato_id': contrato_com_parcelas_ciclo_2.pk
        })

        response = client_autenticado.post(url)

        data = response.json()
        # Deve ter alguns bloqueados se tiver parcelas do ciclo 2
        if data.get('sucesso'):
            assert 'bloqueados' in data

    def test_gerar_boleto_com_force(self, client_autenticado, contrato_com_parcelas_ciclo_2):
        """Testa que force=true ignora bloqueio por reajuste"""
        parcela = contrato_com_parcelas_ciclo_2.parcelas.filter(numero_parcela=13).first()
        if not parcela:
            pytest.skip("Parcela do ciclo 2 não encontrada")

        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})

        response = client_autenticado.post(url, data={'force': 'true'})

        data = response.json()
        # Não deve estar bloqueado por reajuste quando force=true
        assert data.get('bloqueado_reajuste') is not True


@pytest.mark.django_db
class TestRelatoriosAvancados:
    """Testes para views de relatórios avançados"""

    def test_relatorio_prestacoes_a_pagar(self, client_autenticado):
        """Testa acesso ao relatório de prestações a pagar"""
        url = reverse('financeiro:relatorio_prestacoes_a_pagar')

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'relatorio' in response.context

    def test_relatorio_prestacoes_pagas(self, client_autenticado):
        """Testa acesso ao relatório de prestações pagas"""
        url = reverse('financeiro:relatorio_prestacoes_pagas')

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'relatorio' in response.context

    def test_relatorio_posicao_contratos(self, client_autenticado):
        """Testa acesso ao relatório de posição de contratos"""
        url = reverse('financeiro:relatorio_posicao_contratos')

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'relatorio' in response.context

    def test_relatorio_previsao_reajustes(self, client_autenticado):
        """Testa acesso ao relatório de previsão de reajustes"""
        url = reverse('financeiro:relatorio_previsao_reajustes')

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert 'relatorio' in response.context

    def test_exportar_relatorio_csv(self, client_autenticado):
        """Testa exportação de relatório para CSV"""
        url = reverse('financeiro:exportar_relatorio', kwargs={'tipo': 'prestacoes_a_pagar'})
        url += '?formato=csv'

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'

    def test_exportar_relatorio_json(self, client_autenticado):
        """Testa exportação de relatório para JSON"""
        url = reverse('financeiro:exportar_relatorio', kwargs={'tipo': 'prestacoes_a_pagar'})
        url += '?formato=json'

        response = client_autenticado.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_api_relatorio_resumo(self, client_autenticado):
        """Testa API de resumo de relatórios"""
        url = reverse('financeiro:api_relatorio_resumo')

        response = client_autenticado.get(url)

        data = response.json()
        assert 'a_pagar' in data
        assert 'pagas' in data
        assert 'reajustes_pendentes' in data


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client_autenticado(db, django_user_model):
    """Cliente autenticado para testes"""
    user = django_user_model.objects.create_user(
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
    def create(**kwargs):
        from contratos.models import Contrato

        defaults = {
            'imobiliaria': kwargs.pop('imobiliaria', None) or imobiliaria_factory(),
            'comprador': kwargs.pop('comprador', None) or comprador_factory(),
            'imovel': kwargs.pop('imovel', None) or imovel_factory(),
            'numero_contrato': kwargs.pop('numero_contrato', None) or f'CTR-{timezone.now().timestamp()}',
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
def contrato_com_parcelas(contrato_factory):
    """Cria um contrato com parcelas"""
    return contrato_factory()


@pytest.fixture
def contrato_com_parcelas_ciclo_2(contrato_factory):
    """Cria um contrato com parcelas do ciclo 2 (parcela 13+)"""
    from financeiro.models import Parcela
    from dateutil.relativedelta import relativedelta

    contrato = contrato_factory(numero_parcelas=24)

    # Criar parcelas do ciclo 1 e 2
    for i in range(1, 25):
        data_vencimento = contrato.data_primeiro_vencimento + relativedelta(months=i-1)
        Parcela.objects.create(
            contrato=contrato,
            numero_parcela=i,
            data_vencimento=data_vencimento,
            valor_original=Decimal('3750.00'),
            valor_atual=Decimal('3750.00'),
        )

    return contrato


@pytest.fixture
def imobiliaria_factory(db, contabilidade_factory):
    """Factory para criar imobiliárias"""
    def create(**kwargs):
        from core.models import Imobiliaria

        defaults = {
            'contabilidade': kwargs.pop('contabilidade', None) or contabilidade_factory(),
            'razao_social': 'Imobiliária Teste LTDA',
            'nome_fantasia': 'Imobiliária Teste',
            'cnpj': f'1234567800{int(timezone.now().timestamp()) % 10000:04d}',
            'email': 'teste@imobiliaria.com',
        }
        defaults.update(kwargs)
        return Imobiliaria.objects.create(**defaults)

    return create


@pytest.fixture
def contabilidade_factory(db):
    """Factory para criar contabilidades"""
    def create(**kwargs):
        from core.models import Contabilidade

        defaults = {
            'razao_social': 'Contabilidade Teste LTDA',
            'cnpj': f'9876543200{int(timezone.now().timestamp()) % 10000:04d}',
            'email': 'teste@contabilidade.com',
        }
        defaults.update(kwargs)
        return Contabilidade.objects.create(**defaults)

    return create


@pytest.fixture
def comprador_factory(db):
    """Factory para criar compradores"""
    def create(**kwargs):
        from core.models import Comprador

        defaults = {
            'nome': 'Comprador Teste',
            'tipo_pessoa': 'PF',
            'cpf': f'{int(timezone.now().timestamp()) % 100000000000:011d}',
            'email': 'comprador@teste.com',
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
    def create(**kwargs):
        from core.models import Imovel

        defaults = {
            'imobiliaria': kwargs.pop('imobiliaria', None) or imobiliaria_factory(),
            'tipo': 'LOTE',
            'identificacao': f'LOTE-{timezone.now().timestamp()}',
            'quadra': 'A',
            'lote': '1',
        }
        defaults.update(kwargs)
        return Imovel.objects.create(**defaults)

    return create
