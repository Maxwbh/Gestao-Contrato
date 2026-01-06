"""
Testes unitários para Parcela e Reajuste

Testa:
- Modelo Parcela (tipo, ciclo, cálculos)
- Modelo Reajuste (criação, aplicação, ciclos)
- Bloqueio de boleto por reajuste
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


@pytest.mark.django_db
class TestParcelaModel:
    """Testes para o modelo Parcela"""

    def test_parcela_tipo_padrao_normal(self, parcela_factory):
        """Testa que parcela tem tipo NORMAL por padrão"""
        parcela = parcela_factory()
        assert parcela.tipo_parcela == 'NORMAL'

    def test_parcela_ciclo_reajuste_padrao(self, parcela_factory):
        """Testa que parcela tem ciclo 1 por padrão"""
        parcela = parcela_factory()
        assert parcela.ciclo_reajuste == 1

    def test_parcela_valor_total(self, parcela_factory):
        """Testa cálculo do valor total da parcela"""
        parcela = parcela_factory(
            valor_atual=Decimal('1000.00'),
            valor_juros=Decimal('50.00'),
            valor_multa=Decimal('20.00'),
            valor_desconto=Decimal('10.00')
        )

        # valor_total = valor_atual + juros + multa - desconto
        assert parcela.valor_total == Decimal('1060.00')

    def test_parcela_dias_atraso_nao_vencida(self, parcela_factory):
        """Testa dias de atraso de parcela não vencida"""
        parcela = parcela_factory(
            data_vencimento=date.today() + timedelta(days=10)
        )
        assert parcela.dias_atraso == 0

    def test_parcela_dias_atraso_vencida(self, parcela_factory):
        """Testa dias de atraso de parcela vencida"""
        parcela = parcela_factory(
            data_vencimento=date.today() - timedelta(days=5)
        )
        assert parcela.dias_atraso == 5

    def test_parcela_esta_vencida(self, parcela_factory):
        """Testa propriedade esta_vencida"""
        parcela_futura = parcela_factory(
            data_vencimento=date.today() + timedelta(days=1)
        )
        assert parcela_futura.esta_vencida is False

        parcela_passada = parcela_factory(
            data_vencimento=date.today() - timedelta(days=1)
        )
        assert parcela_passada.esta_vencida is True

    def test_parcela_calcular_juros_multa(self, parcela_factory, contrato_factory):
        """Testa cálculo de juros e multa"""
        contrato = contrato_factory(
            percentual_juros_mora=Decimal('1.00'),  # 1% ao mês
            percentual_multa=Decimal('2.00')  # 2%
        )
        parcela = parcela_factory(
            contrato=contrato,
            valor_atual=Decimal('1000.00'),
            data_vencimento=date.today() - timedelta(days=30)
        )

        juros, multa = parcela.calcular_juros_multa()

        # Multa: 1000 * 2% = 20
        assert multa == Decimal('20.00')

        # Juros: 1000 * 1% * (30/30) = 10
        assert juros == Decimal('10.00')

    def test_parcela_registrar_pagamento(self, parcela_factory):
        """Testa registro de pagamento"""
        parcela = parcela_factory(valor_atual=Decimal('1000.00'))

        parcela.registrar_pagamento(
            valor_pago=Decimal('1000.00'),
            data_pagamento=date.today()
        )

        assert parcela.pago is True
        assert parcela.valor_pago == Decimal('1000.00')
        assert parcela.data_pagamento == date.today()

    def test_parcela_cancelar_pagamento(self, parcela_factory):
        """Testa cancelamento de pagamento"""
        parcela = parcela_factory()
        parcela.registrar_pagamento(valor_pago=Decimal('1000.00'))

        parcela.cancelar_pagamento()

        assert parcela.pago is False
        assert parcela.valor_pago is None
        assert parcela.data_pagamento is None


@pytest.mark.django_db
class TestReajusteModel:
    """Testes para o modelo Reajuste"""

    def test_reajuste_criacao(self, reajuste_factory):
        """Testa criação de reajuste"""
        reajuste = reajuste_factory(
            indice_tipo='IPCA',
            percentual=Decimal('5.50'),
            ciclo=2
        )

        assert reajuste.pk is not None
        assert reajuste.indice_tipo == 'IPCA'
        assert reajuste.percentual == Decimal('5.50')
        assert reajuste.ciclo == 2
        assert reajuste.aplicado is False

    def test_reajuste_aplicar(self, contrato_com_parcelas, reajuste_factory):
        """Testa aplicação de reajuste nas parcelas"""
        contrato = contrato_com_parcelas

        # Valor original da primeira parcela
        parcela = contrato.parcelas.first()
        valor_original = parcela.valor_atual

        # Criar e aplicar reajuste de 5%
        reajuste = reajuste_factory(
            contrato=contrato,
            percentual=Decimal('5.00'),
            parcela_inicial=1,
            parcela_final=24,
            ciclo=2
        )

        resultado = reajuste.aplicar_reajuste()

        # Verificar resultado
        assert resultado['sucesso'] is True
        assert resultado['parcelas_reajustadas'] > 0
        assert resultado['percentual_aplicado'] == Decimal('5.00')

        # Verificar que o reajuste foi marcado como aplicado
        reajuste.refresh_from_db()
        assert reajuste.aplicado is True
        assert reajuste.data_aplicacao is not None

        # Verificar que a parcela foi reajustada
        parcela.refresh_from_db()
        valor_esperado = valor_original * Decimal('1.05')
        assert parcela.valor_atual == valor_esperado

    def test_reajuste_nao_aplica_parcelas_pagas(self, contrato_com_parcelas, reajuste_factory):
        """Testa que parcelas pagas não são reajustadas"""
        contrato = contrato_com_parcelas

        # Pagar primeira parcela
        parcela = contrato.parcelas.first()
        parcela.registrar_pagamento(valor_pago=parcela.valor_atual)
        valor_antes = parcela.valor_atual

        # Aplicar reajuste
        reajuste = reajuste_factory(
            contrato=contrato,
            percentual=Decimal('5.00'),
            parcela_inicial=1,
            parcela_final=24,
            ciclo=2
        )
        reajuste.aplicar_reajuste()

        # Verificar que parcela paga não foi alterada
        parcela.refresh_from_db()
        assert parcela.valor_atual == valor_antes

    def test_reajuste_nao_aplica_duas_vezes(self, contrato_com_parcelas, reajuste_factory):
        """Testa que reajuste não pode ser aplicado duas vezes"""
        contrato = contrato_com_parcelas

        reajuste = reajuste_factory(
            contrato=contrato,
            percentual=Decimal('5.00'),
            parcela_inicial=1,
            parcela_final=24,
            ciclo=2
        )

        # Primeira aplicação
        resultado1 = reajuste.aplicar_reajuste()
        assert resultado1['sucesso'] is True

        # Segunda aplicação (deve falhar)
        resultado2 = reajuste.aplicar_reajuste()
        assert resultado2['sucesso'] is False
        assert 'já foi aplicado' in resultado2['erro']

    def test_reajuste_atualiza_contrato(self, contrato_com_parcelas, reajuste_factory):
        """Testa que reajuste atualiza dados do contrato"""
        contrato = contrato_com_parcelas
        contrato.bloqueio_boleto_reajuste = True
        contrato.save()

        reajuste = reajuste_factory(
            contrato=contrato,
            percentual=Decimal('5.00'),
            parcela_inicial=1,
            parcela_final=24,
            ciclo=2
        )
        reajuste.aplicar_reajuste()

        contrato.refresh_from_db()
        assert contrato.data_ultimo_reajuste == reajuste.data_reajuste
        assert contrato.ciclo_reajuste_atual == 2
        assert contrato.bloqueio_boleto_reajuste is False

    def test_reajuste_criar_reajuste_ciclo(self, contrato_com_parcelas, indice_factory):
        """Testa criação automática de reajuste para ciclo"""
        from financeiro.models import Reajuste

        contrato = contrato_com_parcelas

        # Criar índices para o período
        for mes in range(1, 13):
            indice_factory(
                tipo_indice='IPCA',
                ano=2024,
                mes=mes,
                valor=Decimal('0.50')
            )

        # Criar reajuste para ciclo 2
        reajuste = Reajuste.criar_reajuste_ciclo(
            contrato=contrato,
            ciclo=2,
            percentual=Decimal('6.17')  # Passando percentual manualmente para o teste
        )

        assert reajuste is not None
        assert reajuste.ciclo == 2
        assert reajuste.contrato == contrato


@pytest.mark.django_db
class TestBloqueioBoletoPorReajuste:
    """Testes para a lógica de bloqueio de boleto por reajuste"""

    def test_boleto_liberado_primeiro_ciclo(self, contrato_factory):
        """Testa que boletos são liberados no primeiro ciclo"""
        contrato = contrato_factory()

        pode, motivo = contrato.pode_gerar_boleto(1)
        assert pode is True

        pode, motivo = contrato.pode_gerar_boleto(12)
        assert pode is True

    def test_boleto_bloqueado_segundo_ciclo_sem_reajuste(self, contrato_factory):
        """Testa que boletos são bloqueados no segundo ciclo sem reajuste"""
        contrato = contrato_factory(prazo_reajuste_meses=12)

        pode, motivo = contrato.pode_gerar_boleto(13)
        assert pode is False
        assert "reajuste pendente" in motivo.lower()

    def test_boleto_liberado_apos_reajuste(self, contrato_com_parcelas, reajuste_factory):
        """Testa que boletos são liberados após aplicar reajuste"""
        contrato = contrato_com_parcelas

        # Verificar bloqueio inicial
        pode, _ = contrato.pode_gerar_boleto(13)
        assert pode is False

        # Aplicar reajuste do ciclo 2
        reajuste = reajuste_factory(
            contrato=contrato,
            percentual=Decimal('5.00'),
            parcela_inicial=13,
            parcela_final=24,
            ciclo=2
        )
        reajuste.aplicar_reajuste()

        # Verificar que agora está liberado
        pode, _ = contrato.pode_gerar_boleto(13)
        assert pode is True

    def test_verificar_bloqueio_reajuste(self, contrato_factory):
        """Testa verificação e atualização de bloqueio"""
        contrato = contrato_factory(prazo_reajuste_meses=12)
        contrato.ultimo_mes_boleto_gerado = 12  # Último mês do primeiro ciclo

        bloqueado = contrato.verificar_bloqueio_reajuste()

        assert bloqueado is True
        contrato.refresh_from_db()
        assert contrato.bloqueio_boleto_reajuste is True


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
    return contrato_factory(numero_parcelas=24)


@pytest.fixture
def parcela_factory(db, contrato_factory):
    """Factory para criar parcelas"""
    def create(**kwargs):
        from financeiro.models import Parcela

        contrato = kwargs.pop('contrato', None) or contrato_factory()

        defaults = {
            'contrato': contrato,
            'numero_parcela': kwargs.pop('numero_parcela', 1),
            'data_vencimento': kwargs.pop('data_vencimento', date.today() + timedelta(days=30)),
            'valor_original': kwargs.pop('valor_original', Decimal('1000.00')),
            'valor_atual': kwargs.pop('valor_atual', Decimal('1000.00')),
        }
        defaults.update(kwargs)
        return Parcela.objects.create(**defaults)

    return create


@pytest.fixture
def reajuste_factory(db, contrato_factory):
    """Factory para criar reajustes"""
    def create(**kwargs):
        from financeiro.models import Reajuste

        contrato = kwargs.pop('contrato', None) or contrato_factory()

        defaults = {
            'contrato': contrato,
            'data_reajuste': kwargs.pop('data_reajuste', date.today()),
            'indice_tipo': kwargs.pop('indice_tipo', 'IPCA'),
            'percentual': kwargs.pop('percentual', Decimal('5.00')),
            'parcela_inicial': kwargs.pop('parcela_inicial', 1),
            'parcela_final': kwargs.pop('parcela_final', 12),
            'ciclo': kwargs.pop('ciclo', 2),
        }
        defaults.update(kwargs)
        return Reajuste.objects.create(**defaults)

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
