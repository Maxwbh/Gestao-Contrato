"""
Testes unitários para o serviço de relatórios

Testa:
- Relatório de prestações a pagar
- Relatório de prestações pagas
- Relatório de posição de contratos
- Relatório de previsão de reajustes
- Exportação para CSV e JSON
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


@pytest.mark.django_db
class TestRelatorioPrestacoesAPagar:
    """Testes para relatório de prestações a pagar"""

    def test_relatorio_basico(self, contrato_com_parcelas):
        """Testa geração básica do relatório"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio()

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)

        assert relatorio is not None
        assert 'itens' in relatorio
        assert 'totalizador' in relatorio
        assert relatorio['tipo'] == 'prestacoes_a_pagar'

    def test_relatorio_filtro_contrato(self, contrato_com_parcelas):
        """Testa filtro por contrato específico"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(contrato_id=contrato_com_parcelas.id)

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)

        for item in relatorio['itens']:
            assert item.contrato_numero == contrato_com_parcelas.numero_contrato

    def test_relatorio_filtro_data(self, contrato_com_parcelas):
        """Testa filtro por período de vencimento"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(
            data_inicio=date.today(),
            data_fim=date.today() + timedelta(days=60)
        )

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)

        for item in relatorio['itens']:
            assert item.data_vencimento >= date.today()
            assert item.data_vencimento <= date.today() + timedelta(days=60)

    def test_relatorio_filtro_vencidas(self, contrato_com_parcelas_vencidas):
        """Testa filtro de parcelas vencidas"""
        from financeiro.services import RelatorioService, FiltroRelatorio, StatusParcela

        service = RelatorioService()
        filtro = FiltroRelatorio(status=StatusParcela.VENCIDAS)

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)

        for item in relatorio['itens']:
            assert item.dias_atraso > 0

    def test_relatorio_totalizadores(self, contrato_com_parcelas):
        """Testa cálculo de totalizadores"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(contrato_id=contrato_com_parcelas.id)

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)
        totalizador = relatorio['totalizador']

        assert totalizador.total_parcelas > 0
        assert totalizador.valor_total > Decimal('0.00')
        assert totalizador.parcelas_a_vencer >= 0


@pytest.mark.django_db
class TestRelatorioPrestacoesPages:
    """Testes para relatório de prestações pagas"""

    def test_relatorio_basico(self, contrato_com_pagamentos):
        """Testa geração básica do relatório de pagas"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio()

        relatorio = service.gerar_relatorio_prestacoes_pagas(filtro)

        assert relatorio is not None
        assert 'itens' in relatorio
        assert relatorio['tipo'] == 'prestacoes_pagas'

    def test_relatorio_filtro_periodo_pagamento(self, contrato_com_pagamentos):
        """Testa filtro por período de pagamento"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(
            data_inicio=date.today() - timedelta(days=30),
            data_fim=date.today()
        )

        relatorio = service.gerar_relatorio_prestacoes_pagas(filtro)

        for item in relatorio['itens']:
            assert item.data_pagamento is not None
            assert item.data_pagamento >= date.today() - timedelta(days=30)

    def test_relatorio_totalizadores_pagas(self, contrato_com_pagamentos):
        """Testa totalizadores de parcelas pagas"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio()

        relatorio = service.gerar_relatorio_prestacoes_pagas(filtro)
        totalizador = relatorio['totalizador']

        assert totalizador.total_parcelas >= 0
        assert totalizador.valor_total >= Decimal('0.00')


@pytest.mark.django_db
class TestRelatorioPosicaoContratos:
    """Testes para relatório de posição de contratos"""

    def test_relatorio_basico(self, contrato_com_parcelas):
        """Testa geração do relatório de posição"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio()

        relatorio = service.gerar_relatorio_posicao_contratos(filtro)

        assert relatorio is not None
        assert 'itens' in relatorio
        assert 'totalizadores' in relatorio
        assert relatorio['tipo'] == 'posicao_contratos'

    def test_relatorio_campos_contrato(self, contrato_com_parcelas):
        """Testa campos retornados por contrato"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(contrato_id=contrato_com_parcelas.id)

        relatorio = service.gerar_relatorio_posicao_contratos(filtro)

        assert len(relatorio['itens']) == 1
        item = relatorio['itens'][0]

        assert 'contrato_numero' in item
        assert 'valor_total' in item
        assert 'saldo_devedor' in item
        assert 'progresso_percentual' in item
        assert 'ciclo_atual' in item


@pytest.mark.django_db
class TestRelatorioPrevisaoReajustes:
    """Testes para relatório de previsão de reajustes"""

    def test_relatorio_basico(self, contrato_proximo_reajuste):
        """Testa geração do relatório de previsão"""
        from financeiro.services import RelatorioService

        service = RelatorioService()

        relatorio = service.gerar_relatorio_previsao_reajustes(dias_antecedencia=60)

        assert relatorio is not None
        assert 'itens' in relatorio
        assert relatorio['tipo'] == 'previsao_reajustes'

    def test_relatorio_dias_antecedencia(self, contrato_proximo_reajuste):
        """Testa filtro de dias de antecedência"""
        from financeiro.services import RelatorioService

        service = RelatorioService()

        # Com 60 dias de antecedência
        relatorio_60 = service.gerar_relatorio_previsao_reajustes(dias_antecedencia=60)

        # Com 7 dias de antecedência
        relatorio_7 = service.gerar_relatorio_previsao_reajustes(dias_antecedencia=7)

        # Relatório com mais dias deve ter igual ou mais itens
        assert len(relatorio_60['itens']) >= len(relatorio_7['itens'])


@pytest.mark.django_db
class TestExportacao:
    """Testes para exportação de relatórios"""

    def test_exportar_csv(self, contrato_com_parcelas):
        """Testa exportação para CSV"""
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(contrato_id=contrato_com_parcelas.id)

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)
        csv = service.exportar_para_csv(relatorio)

        assert csv is not None
        assert len(csv) > 0
        assert 'Contrato' in csv  # Cabeçalho
        assert contrato_com_parcelas.numero_contrato in csv

    def test_exportar_json(self, contrato_com_parcelas):
        """Testa exportação para JSON"""
        import json
        from financeiro.services import RelatorioService, FiltroRelatorio

        service = RelatorioService()
        filtro = FiltroRelatorio(contrato_id=contrato_com_parcelas.id)

        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)
        json_str = service.exportar_para_json(relatorio)

        assert json_str is not None
        data = json.loads(json_str)
        assert 'itens' in data
        assert 'totalizador' in data


# Fixtures
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
def contrato_com_parcelas_vencidas(contrato_factory):
    """Cria um contrato com parcelas vencidas"""
    return contrato_factory(
        data_primeiro_vencimento=date.today() - timedelta(days=60)
    )


@pytest.fixture
def contrato_com_pagamentos(contrato_factory):
    """Cria um contrato com algumas parcelas pagas"""
    contrato = contrato_factory()

    # Pagar as 3 primeiras parcelas
    for parcela in contrato.parcelas.all()[:3]:
        parcela.registrar_pagamento(
            valor_pago=parcela.valor_atual,
            data_pagamento=date.today() - timedelta(days=10)
        )

    return contrato


@pytest.fixture
def contrato_proximo_reajuste(contrato_factory):
    """Cria um contrato que precisa de reajuste em breve"""
    return contrato_factory(
        data_contrato=date.today() - timedelta(days=330),  # 11 meses atrás
        prazo_reajuste_meses=12
    )


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
