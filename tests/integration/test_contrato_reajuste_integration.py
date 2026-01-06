"""
Testes de integração para Contratos e Reajustes

Testa o fluxo completo de:
- Criação de contrato com 360 meses
- Geração de parcelas
- Prestações intermediárias
- Ciclos de reajuste
- Bloqueio de boleto por reajuste
- Relatórios financeiros
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


@pytest.mark.django_db
class TestFluxoContratoCompleto:
    """Testes de integração para o fluxo completo de contrato"""

    def test_contrato_360_meses_com_intermediarias(
        self,
        imobiliaria_factory,
        comprador_factory,
        imovel_factory
    ):
        """
        Testa criação de contrato de 360 meses com intermediárias.

        Cenário:
        - Contrato de R$ 360.000,00
        - 360 parcelas de R$ 1.000,00
        - 30 intermediárias de R$ 5.000,00 cada (a cada 12 meses)
        - Reajuste anual por IPCA
        """
        from contratos.models import Contrato, PrestacaoIntermediaria

        imobiliaria = imobiliaria_factory()
        comprador = comprador_factory()
        imovel = imovel_factory(imobiliaria=imobiliaria)

        # Criar contrato de 30 anos
        contrato = Contrato.objects.create(
            imobiliaria=imobiliaria,
            comprador=comprador,
            imovel=imovel,
            numero_contrato='CTR-360M-001',
            data_contrato=date.today(),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('360000.00'),
            valor_entrada=Decimal('0.00'),
            numero_parcelas=360,
            dia_vencimento=15,
            tipo_correcao='IPCA',
            prazo_reajuste_meses=12,
            quantidade_intermediarias=30,
        )

        # Verificar contrato criado
        assert contrato.numero_parcelas == 360
        assert contrato.quantidade_intermediarias == 30
        assert contrato.valor_parcela_original == Decimal('1000.00')

        # Criar 30 intermediárias (uma a cada 12 meses)
        for i in range(1, 31):
            PrestacaoIntermediaria.objects.create(
                contrato=contrato,
                numero_sequencial=i,
                mes_vencimento=i * 12,  # Mês 12, 24, 36, ...
                valor=Decimal('5000.00')
            )

        # Verificar intermediárias
        assert contrato.intermediarias.count() == 30

        # Verificar parcelas geradas
        assert contrato.parcelas.count() == 360

    def test_fluxo_reajuste_completo(
        self,
        contrato_factory,
        indice_factory
    ):
        """
        Testa o fluxo completo de reajuste.

        Cenário:
        1. Contrato de 24 parcelas
        2. Gerar boletos do ciclo 1 (1-12)
        3. Tentar gerar boleto do ciclo 2 (bloqueado)
        4. Aplicar reajuste
        5. Gerar boleto do ciclo 2 (liberado)
        """
        from financeiro.models import Reajuste

        # Criar contrato
        contrato = contrato_factory(
            numero_parcelas=24,
            prazo_reajuste_meses=12
        )

        # Verificar que ciclo 1 está liberado
        for i in range(1, 13):
            pode, motivo = contrato.pode_gerar_boleto(i)
            assert pode is True, f"Parcela {i} deveria estar liberada"

        # Verificar que ciclo 2 está bloqueado
        pode, motivo = contrato.pode_gerar_boleto(13)
        assert pode is False
        assert "reajuste pendente" in motivo.lower()

        # Criar índices para o período
        for mes in range(1, 13):
            indice_factory(tipo_indice='IPCA', ano=2024, mes=mes, valor=Decimal('0.50'))

        # Aplicar reajuste do ciclo 2
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=Decimal('6.17'),  # ~6.17% acumulado de 12x 0.5%
            parcela_inicial=13,
            parcela_final=24,
            ciclo=2,
        )
        resultado = reajuste.aplicar_reajuste()

        assert resultado['sucesso'] is True
        assert resultado['parcelas_reajustadas'] == 12

        # Verificar que ciclo 2 agora está liberado
        pode, motivo = contrato.pode_gerar_boleto(13)
        assert pode is True

        # Verificar valores reajustados
        parcela_13 = contrato.parcelas.get(numero_parcela=13)
        valor_esperado = contrato.valor_parcela_original * Decimal('1.0617')
        assert abs(parcela_13.valor_atual - valor_esperado) < Decimal('0.01')

    def test_intermediarias_reajustadas_junto_com_parcelas(
        self,
        contrato_factory,
        indice_factory
    ):
        """
        Testa que intermediárias são reajustadas junto com as parcelas.
        """
        from contratos.models import PrestacaoIntermediaria
        from financeiro.models import Reajuste

        contrato = contrato_factory(
            numero_parcelas=24,
            prazo_reajuste_meses=12,
            quantidade_intermediarias=2
        )

        # Criar intermediárias
        inter1 = PrestacaoIntermediaria.objects.create(
            contrato=contrato,
            numero_sequencial=1,
            mes_vencimento=12,
            valor=Decimal('5000.00')
        )
        inter2 = PrestacaoIntermediaria.objects.create(
            contrato=contrato,
            numero_sequencial=2,
            mes_vencimento=18,
            valor=Decimal('5000.00')
        )

        # Aplicar reajuste de 5%
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=Decimal('5.00'),
            parcela_inicial=13,
            parcela_final=24,
            ciclo=2,
        )
        reajuste.aplicar_reajuste()

        # Verificar intermediárias
        inter1.refresh_from_db()
        inter2.refresh_from_db()

        # Inter1 (mês 12) não é reajustada (está no ciclo anterior)
        assert inter1.valor_reajustado is None

        # Inter2 (mês 18) deve ser reajustada
        assert inter2.valor_reajustado == Decimal('5250.00')  # 5000 * 1.05

    def test_relatorio_integrado_com_reajuste(
        self,
        contrato_factory
    ):
        """
        Testa relatórios após aplicação de reajuste.
        """
        from financeiro.models import Reajuste
        from financeiro.services import RelatorioService, FiltroRelatorio

        contrato = contrato_factory(numero_parcelas=24)

        # Pagar primeiras 6 parcelas
        for parcela in contrato.parcelas.filter(numero_parcela__lte=6):
            parcela.registrar_pagamento(valor_pago=parcela.valor_atual)

        # Aplicar reajuste
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=Decimal('5.00'),
            parcela_inicial=7,
            parcela_final=24,
            ciclo=2,
        )
        reajuste.aplicar_reajuste()

        # Gerar relatórios
        service = RelatorioService()
        filtro = FiltroRelatorio(contrato_id=contrato.id)

        # Relatório a pagar
        rel_pagar = service.gerar_relatorio_prestacoes_a_pagar(filtro)
        assert rel_pagar['totalizador'].total_parcelas == 18  # 24 - 6 pagas

        # Relatório pagas
        rel_pagas = service.gerar_relatorio_prestacoes_pagas(filtro)
        assert rel_pagas['totalizador'].total_parcelas == 6

        # Posição do contrato
        rel_posicao = service.gerar_relatorio_posicao_contratos(filtro)
        assert len(rel_posicao['itens']) == 1
        assert rel_posicao['itens'][0]['parcelas_pagas'] == 6

    def test_multiplos_ciclos_reajuste(
        self,
        contrato_factory
    ):
        """
        Testa múltiplos ciclos de reajuste consecutivos.
        """
        from financeiro.models import Reajuste

        contrato = contrato_factory(
            numero_parcelas=48,  # 4 anos
            prazo_reajuste_meses=12
        )

        valor_parcela_original = contrato.valor_parcela_original

        # Aplicar reajuste ciclo 2 (5%)
        reajuste2 = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=Decimal('5.00'),
            parcela_inicial=13,
            parcela_final=48,
            ciclo=2,
        )
        reajuste2.aplicar_reajuste()

        # Verificar bloqueio ciclo 3
        pode, _ = contrato.pode_gerar_boleto(25)
        assert pode is False

        # Aplicar reajuste ciclo 3 (4%)
        reajuste3 = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=Decimal('4.00'),
            parcela_inicial=25,
            parcela_final=48,
            ciclo=3,
        )
        reajuste3.aplicar_reajuste()

        # Verificar que ciclo 3 está liberado
        pode, _ = contrato.pode_gerar_boleto(25)
        assert pode is True

        # Verificar valor acumulado (5% + 4% = ~9.2%)
        parcela_25 = contrato.parcelas.get(numero_parcela=25)
        valor_esperado = valor_parcela_original * Decimal('1.05') * Decimal('1.04')
        assert abs(parcela_25.valor_atual - valor_esperado) < Decimal('0.01')


@pytest.mark.django_db
class TestCenariosEspeciais:
    """Testes para cenários especiais e edge cases"""

    def test_contrato_valor_fixo_sem_bloqueio(self, contrato_factory):
        """
        Testa que contrato com valor fixo não tem bloqueio de reajuste.
        """
        contrato = contrato_factory(
            tipo_correcao='FIXO',
            prazo_reajuste_meses=12
        )

        # Todas as parcelas devem estar liberadas
        for i in range(1, 25):
            pode, _ = contrato.pode_gerar_boleto(i)
            assert pode is True

        # Verificar bloqueio
        bloqueado = contrato.verificar_bloqueio_reajuste()
        assert bloqueado is False

    def test_parcela_paga_nao_reajustada(self, contrato_factory):
        """
        Testa que parcelas pagas não são reajustadas.
        """
        from financeiro.models import Reajuste

        contrato = contrato_factory(numero_parcelas=24)

        # Pagar parcela 15
        parcela_15 = contrato.parcelas.get(numero_parcela=15)
        valor_original = parcela_15.valor_atual
        parcela_15.registrar_pagamento(valor_pago=valor_original)

        # Aplicar reajuste
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=date.today(),
            indice_tipo='IPCA',
            percentual=Decimal('5.00'),
            parcela_inicial=13,
            parcela_final=24,
            ciclo=2,
        )
        reajuste.aplicar_reajuste()

        # Verificar que parcela 15 não foi alterada
        parcela_15.refresh_from_db()
        assert parcela_15.valor_atual == valor_original

    def test_resumo_financeiro_completo(self, contrato_factory):
        """
        Testa resumo financeiro com pagamentos parciais.
        """
        contrato = contrato_factory(
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=100
        )

        # Pagar 10 parcelas
        for parcela in contrato.parcelas.filter(numero_parcela__lte=10):
            parcela.registrar_pagamento(valor_pago=parcela.valor_atual)

        resumo = contrato.get_resumo_financeiro()

        assert resumo['valor_contrato'] == Decimal('100000.00')
        assert resumo['valor_entrada'] == Decimal('10000.00')
        assert resumo['valor_financiado'] == Decimal('90000.00')
        assert resumo['total_parcelas'] == 100
        assert resumo['parcelas_pagas'] == 10
        assert resumo['parcelas_a_pagar'] == 90
        assert resumo['progresso_percentual'] == 10.0


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
def indice_factory(db):
    """Factory para criar índices"""
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

        imob = kwargs.pop('imobiliaria', None) or imobiliaria_factory()

        defaults = {
            'imobiliaria': imob,
            'tipo': 'LOTE',
            'identificacao': f'LOTE-{timezone.now().timestamp()}',
            'quadra': 'A',
            'lote': '1',
        }
        defaults.update(kwargs)
        return Imovel.objects.create(**defaults)

    return create
