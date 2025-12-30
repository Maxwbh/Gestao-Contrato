"""
Testes unitários para os modelos de Contrato

Testa:
- Modelo Contrato (campos, validações, métodos)
- Modelo PrestacaoIntermediaria
- Lógica de ciclos de reajuste
- Bloqueio de boleto por reajuste
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone


@pytest.mark.django_db
class TestContratoModel:
    """Testes para o modelo Contrato"""

    def test_contrato_criacao_basica(self, contrato_factory):
        """Testa criação básica de contrato"""
        contrato = contrato_factory()
        assert contrato.pk is not None
        assert contrato.numero_contrato is not None
        assert contrato.status == 'ATIVO'

    def test_contrato_valor_financiado_calculado(self, contrato_factory):
        """Testa cálculo automático do valor financiado"""
        contrato = contrato_factory(
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('20000.00')
        )
        assert contrato.valor_financiado == Decimal('80000.00')

    def test_contrato_valor_parcela_original_calculado(self, contrato_factory):
        """Testa cálculo do valor original da parcela"""
        contrato = contrato_factory(
            valor_total=Decimal('120000.00'),
            valor_entrada=Decimal('0.00'),
            numero_parcelas=120
        )
        assert contrato.valor_parcela_original == Decimal('1000.00')

    def test_contrato_maximo_360_parcelas(self, contrato_factory):
        """Testa que o contrato aceita até 360 parcelas"""
        contrato = contrato_factory(numero_parcelas=360)
        assert contrato.numero_parcelas == 360

    def test_contrato_maximo_30_intermediarias(self, contrato_factory):
        """Testa que o contrato aceita até 30 intermediárias"""
        contrato = contrato_factory(quantidade_intermediarias=30)
        assert contrato.quantidade_intermediarias == 30

    def test_contrato_calcular_ciclo_parcela(self, contrato_factory):
        """Testa cálculo do ciclo de reajuste de uma parcela"""
        contrato = contrato_factory(prazo_reajuste_meses=12)

        # Parcelas 1-12 = Ciclo 1
        assert contrato.calcular_ciclo_parcela(1) == 1
        assert contrato.calcular_ciclo_parcela(12) == 1

        # Parcelas 13-24 = Ciclo 2
        assert contrato.calcular_ciclo_parcela(13) == 2
        assert contrato.calcular_ciclo_parcela(24) == 2

        # Parcelas 25-36 = Ciclo 3
        assert contrato.calcular_ciclo_parcela(25) == 3
        assert contrato.calcular_ciclo_parcela(36) == 3

    def test_contrato_pode_gerar_boleto_primeiro_ciclo(self, contrato_factory):
        """Testa que boletos podem ser gerados no primeiro ciclo"""
        contrato = contrato_factory()

        pode, motivo = contrato.pode_gerar_boleto(1)
        assert pode is True
        assert "liberado" in motivo.lower()

        pode, motivo = contrato.pode_gerar_boleto(12)
        assert pode is True

    def test_contrato_bloqueio_boleto_sem_reajuste(self, contrato_factory):
        """Testa bloqueio de boleto quando reajuste não foi aplicado"""
        contrato = contrato_factory(prazo_reajuste_meses=12)

        # Parcela 13 (segundo ciclo) deve estar bloqueada
        pode, motivo = contrato.pode_gerar_boleto(13)
        assert pode is False
        assert "reajuste pendente" in motivo.lower()

    def test_contrato_get_parcelas_a_pagar(self, contrato_com_parcelas):
        """Testa busca de parcelas a pagar"""
        contrato = contrato_com_parcelas

        parcelas = contrato.get_parcelas_a_pagar()
        assert parcelas.count() > 0
        assert all(not p.pago for p in parcelas)

    def test_contrato_get_parcelas_pagas(self, contrato_com_parcelas):
        """Testa busca de parcelas pagas"""
        contrato = contrato_com_parcelas

        # Pagar uma parcela
        parcela = contrato.parcelas.first()
        parcela.registrar_pagamento(valor_pago=parcela.valor_atual)

        parcelas = contrato.get_parcelas_pagas()
        assert parcelas.count() == 1
        assert all(p.pago for p in parcelas)

    def test_contrato_get_resumo_financeiro(self, contrato_com_parcelas):
        """Testa geração de resumo financeiro"""
        contrato = contrato_com_parcelas
        resumo = contrato.get_resumo_financeiro()

        assert 'valor_contrato' in resumo
        assert 'total_parcelas' in resumo
        assert 'parcelas_pagas' in resumo
        assert 'parcelas_a_pagar' in resumo
        assert 'saldo_devedor' in resumo
        assert 'progresso_percentual' in resumo

    def test_contrato_verificar_reajuste_necessario(self, contrato_factory):
        """Testa verificação de reajuste necessário"""
        # Contrato novo, não precisa de reajuste
        contrato = contrato_factory(
            data_contrato=date.today(),
            prazo_reajuste_meses=12
        )
        assert contrato.verificar_reajuste_necessario() is False

        # Contrato antigo, precisa de reajuste
        contrato_antigo = contrato_factory(
            data_contrato=date.today() - timedelta(days=400),
            prazo_reajuste_meses=12
        )
        assert contrato_antigo.verificar_reajuste_necessario() is True

    def test_contrato_data_proximo_reajuste(self, contrato_factory):
        """Testa cálculo da data do próximo reajuste"""
        data_contrato = date(2024, 1, 15)
        contrato = contrato_factory(
            data_contrato=data_contrato,
            prazo_reajuste_meses=12,
            tipo_correcao='IPCA'
        )

        # Próximo reajuste deve ser 12 meses após a data do contrato
        assert contrato.data_proximo_reajuste == date(2025, 1, 15)

    def test_contrato_sem_reajuste_valor_fixo(self, contrato_factory):
        """Testa que contrato com valor fixo não precisa de reajuste"""
        contrato = contrato_factory(tipo_correcao='FIXO')

        assert contrato.verificar_reajuste_necessario() is False
        assert contrato.data_proximo_reajuste is None


@pytest.mark.django_db
class TestPrestacaoIntermediariaModel:
    """Testes para o modelo PrestacaoIntermediaria"""

    def test_intermediaria_criacao(self, contrato_factory, intermediaria_factory):
        """Testa criação de prestação intermediária"""
        contrato = contrato_factory()
        intermediaria = intermediaria_factory(
            contrato=contrato,
            numero_sequencial=1,
            mes_vencimento=6,
            valor=Decimal('5000.00')
        )

        assert intermediaria.pk is not None
        assert intermediaria.numero_sequencial == 1
        assert intermediaria.mes_vencimento == 6
        assert intermediaria.valor == Decimal('5000.00')
        assert intermediaria.paga is False

    def test_intermediaria_valor_atual(self, intermediaria_factory):
        """Testa propriedade valor_atual"""
        intermediaria = intermediaria_factory(
            valor=Decimal('5000.00'),
            valor_reajustado=None
        )
        assert intermediaria.valor_atual == Decimal('5000.00')

        intermediaria.valor_reajustado = Decimal('5250.00')
        intermediaria.save()
        assert intermediaria.valor_atual == Decimal('5250.00')

    def test_intermediaria_data_vencimento(self, contrato_factory, intermediaria_factory):
        """Testa cálculo da data de vencimento"""
        contrato = contrato_factory(
            data_primeiro_vencimento=date(2024, 1, 15)
        )
        intermediaria = intermediaria_factory(
            contrato=contrato,
            mes_vencimento=6
        )

        # Mês 6 = 5 meses após o primeiro vencimento
        assert intermediaria.data_vencimento == date(2024, 6, 15)

    def test_intermediaria_ciclo_reajuste(self, contrato_factory, intermediaria_factory):
        """Testa cálculo do ciclo de reajuste"""
        contrato = contrato_factory(prazo_reajuste_meses=12)

        inter_ciclo1 = intermediaria_factory(contrato=contrato, mes_vencimento=6)
        assert inter_ciclo1.ciclo_reajuste == 1

        inter_ciclo2 = intermediaria_factory(contrato=contrato, mes_vencimento=18)
        assert inter_ciclo2.ciclo_reajuste == 2

    def test_intermediaria_aplicar_reajuste(self, intermediaria_factory):
        """Testa aplicação de reajuste na intermediária"""
        intermediaria = intermediaria_factory(valor=Decimal('10000.00'))

        intermediaria.aplicar_reajuste(5.0)  # 5% de reajuste

        assert intermediaria.valor_reajustado == Decimal('10500.00')

    def test_intermediaria_nao_reajusta_se_paga(self, intermediaria_factory):
        """Testa que intermediária paga não é reajustada"""
        intermediaria = intermediaria_factory(
            valor=Decimal('10000.00'),
            paga=True
        )

        intermediaria.aplicar_reajuste(5.0)

        assert intermediaria.valor_reajustado is None


@pytest.mark.django_db
class TestIndiceReajusteModel:
    """Testes para o modelo IndiceReajuste"""

    def test_indice_criacao(self, indice_factory):
        """Testa criação de índice de reajuste"""
        indice = indice_factory(
            tipo_indice='IPCA',
            ano=2024,
            mes=1,
            valor=Decimal('0.42')
        )

        assert indice.pk is not None
        assert indice.tipo_indice == 'IPCA'
        assert indice.valor == Decimal('0.42')

    def test_indice_get_indice(self, indice_factory):
        """Testa busca de índice específico"""
        from contratos.models import IndiceReajuste

        indice = indice_factory(tipo_indice='IPCA', ano=2024, mes=1)

        resultado = IndiceReajuste.get_indice('IPCA', 2024, 1)
        assert resultado == indice

        resultado_inexistente = IndiceReajuste.get_indice('IPCA', 2024, 12)
        assert resultado_inexistente is None

    def test_indice_acumulado_periodo(self, indice_factory):
        """Testa cálculo de índice acumulado no período"""
        from contratos.models import IndiceReajuste

        # Criar índices para 3 meses
        indice_factory(tipo_indice='IPCA', ano=2024, mes=1, valor=Decimal('0.50'))
        indice_factory(tipo_indice='IPCA', ano=2024, mes=2, valor=Decimal('0.40'))
        indice_factory(tipo_indice='IPCA', ano=2024, mes=3, valor=Decimal('0.30'))

        acumulado = IndiceReajuste.get_acumulado_periodo('IPCA', 2024, 1, 2024, 3)

        # Cálculo: (1.005) * (1.004) * (1.003) - 1 ≈ 1.203%
        assert acumulado is not None
        assert acumulado > Decimal('1.0')


# Fixtures específicas para os testes
@pytest.fixture
def contrato_factory(db, imobiliaria_factory, comprador_factory, imovel_factory):
    """Factory para criar contratos de teste"""
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
            'numero_parcelas': kwargs.pop('numero_parcelas', 120),
            'dia_vencimento': kwargs.pop('dia_vencimento', 15),
            'tipo_correcao': kwargs.pop('tipo_correcao', 'IPCA'),
            'prazo_reajuste_meses': kwargs.pop('prazo_reajuste_meses', 12),
        }
        defaults.update(kwargs)
        return Contrato.objects.create(**defaults)

    return create


@pytest.fixture
def contrato_com_parcelas(contrato_factory):
    """Cria um contrato com parcelas geradas"""
    contrato = contrato_factory(numero_parcelas=24)
    # As parcelas são geradas automaticamente no save
    return contrato


@pytest.fixture
def intermediaria_factory(db, contrato_factory):
    """Factory para criar prestações intermediárias"""
    def create(**kwargs):
        from contratos.models import PrestacaoIntermediaria

        contrato = kwargs.pop('contrato', None) or contrato_factory()

        defaults = {
            'contrato': contrato,
            'numero_sequencial': kwargs.pop('numero_sequencial', 1),
            'mes_vencimento': kwargs.pop('mes_vencimento', 6),
            'valor': kwargs.pop('valor', Decimal('5000.00')),
        }
        defaults.update(kwargs)
        return PrestacaoIntermediaria.objects.create(**defaults)

    return create


@pytest.fixture
def indice_factory(db):
    """Factory para criar índices de reajuste"""
    def create(**kwargs):
        from contratos.models import IndiceReajuste

        defaults = {
            'tipo_indice': kwargs.pop('tipo_indice', 'IPCA'),
            'ano': kwargs.pop('ano', 2024),
            'mes': kwargs.pop('mes', 1),
            'valor': kwargs.pop('valor', Decimal('0.50')),
        }
        defaults.update(kwargs)
        return IndiceReajuste.objects.create(**defaults)

    return create


@pytest.fixture
def imobiliaria_factory(db, contabilidade_factory):
    """Factory para criar imobiliárias"""
    def create(**kwargs):
        from core.models import Imobiliaria

        defaults = {
            'contabilidade': kwargs.pop('contabilidade', None) or contabilidade_factory(),
            'razao_social': 'Imobiliária Teste LTDA',
            'nome_fantasia': 'Imobiliária Teste',
            'cnpj': '12345678000190',
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
            'cnpj': '98765432000110',
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
            'cpf': '12345678901',
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
