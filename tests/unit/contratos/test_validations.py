"""
Testes para validações de negócio dos modelos de contratos.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
from contratos.models import Contrato, TipoCorrecao, StatusContrato, PrestacaoIntermediaria


class TestContratoValidations(TestCase):
    """Testes para validações do modelo Contrato"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Validação',
            documento='11111111000111'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Validação',
            documento='22222222000122'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Validação',
            documento='33333333333'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-VAL-001',
            endereco='Rua Validação, 100'
        )

    def test_validar_numero_parcelas_maximo(self):
        """Testa que número de parcelas não pode exceder 360"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-001',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=361,  # Excede o limite
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('numero_parcelas', context.exception.message_dict)

    def test_validar_numero_parcelas_minimo(self):
        """Testa que número de parcelas deve ser pelo menos 1"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-002',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=0,  # Menor que o mínimo
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('numero_parcelas', context.exception.message_dict)

    def test_validar_intermediarias_maximo(self):
        """Testa que quantidade de intermediárias não pode exceder 30"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-003',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            quantidade_intermediarias=31,  # Excede o limite
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('quantidade_intermediarias', context.exception.message_dict)

    def test_validar_prazo_reajuste_minimo(self):
        """Testa que prazo de reajuste mínimo é 1 mês"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-004',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            prazo_reajuste_meses=0,  # Menor que o mínimo
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('prazo_reajuste_meses', context.exception.message_dict)

    def test_validar_prazo_reajuste_maximo(self):
        """Testa que prazo de reajuste máximo é 24 meses"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-005',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            prazo_reajuste_meses=25,  # Excede o máximo
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('prazo_reajuste_meses', context.exception.message_dict)

    def test_validar_entrada_maior_que_total(self):
        """Testa que valor de entrada não pode exceder valor total"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-006',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('100000.00'),  # Igual ao total
            numero_parcelas=120,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('valor_entrada', context.exception.message_dict)

    def test_validar_juros_mora_limite_legal(self):
        """Testa que juros de mora não pode exceder 2% (limite legal)"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-007',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            percentual_juros_mora=Decimal('3.00'),  # Excede limite legal
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('percentual_juros_mora', context.exception.message_dict)

    def test_validar_multa_limite_legal(self):
        """Testa que multa não pode exceder 2% (limite legal)"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-008',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            percentual_multa=Decimal('5.00'),  # Excede limite legal
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('percentual_multa', context.exception.message_dict)

    def test_validar_primeiro_vencimento_anterior_contrato(self):
        """Testa que primeiro vencimento não pode ser anterior à data do contrato"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-009',
            data_contrato=date.today(),
            data_primeiro_vencimento=date.today() - timedelta(days=30),  # Anterior ao contrato
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        with self.assertRaises(ValidationError) as context:
            contrato.clean()

        self.assertIn('data_primeiro_vencimento', context.exception.message_dict)

    def test_contrato_valido_passa_validacao(self):
        """Testa que contrato válido passa na validação"""
        contrato = Contrato(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-VAL-010',
            data_contrato=date.today(),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=120,
            dia_vencimento=10,
            prazo_reajuste_meses=12,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        # Não deve levantar exceção
        try:
            contrato.clean()
        except ValidationError:
            self.fail("Contrato válido não deveria levantar ValidationError")


class TestPrestacaoIntermediariaValidations(TestCase):
    """Testes para validações do modelo PrestacaoIntermediaria"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade PI',
            documento='44444444000144'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária PI',
            documento='55555555000155'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador PI',
            documento='66666666666'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-PI-001',
            endereco='Rua PI, 200'
        )

        # Criar contrato com 24 parcelas e 5 intermediárias
        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-PI-001',
            data_contrato=date.today(),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=10,
            quantidade_intermediarias=5,
            tipo_correcao=TipoCorrecao.FIXO,
            status=StatusContrato.ATIVO
        )

    def test_validar_numero_sequencial_maximo(self):
        """Testa que número sequencial não pode exceder 30"""
        intermediaria = PrestacaoIntermediaria(
            contrato=self.contrato,
            numero_sequencial=31,  # Excede o máximo
            mes_vencimento=12,
            valor=Decimal('5000.00')
        )

        with self.assertRaises(ValidationError) as context:
            intermediaria.clean()

        self.assertIn('numero_sequencial', context.exception.message_dict)

    def test_validar_mes_vencimento_excede_contrato(self):
        """Testa que mês de vencimento não pode exceder prazo do contrato"""
        intermediaria = PrestacaoIntermediaria(
            contrato=self.contrato,
            numero_sequencial=1,
            mes_vencimento=30,  # Contrato tem 24 parcelas
            valor=Decimal('5000.00')
        )

        with self.assertRaises(ValidationError) as context:
            intermediaria.clean()

        self.assertIn('mes_vencimento', context.exception.message_dict)

    def test_validar_sequencial_excede_limite_contrato(self):
        """Testa que número sequencial não pode exceder limite do contrato"""
        intermediaria = PrestacaoIntermediaria(
            contrato=self.contrato,
            numero_sequencial=6,  # Contrato permite apenas 5
            mes_vencimento=12,
            valor=Decimal('5000.00')
        )

        with self.assertRaises(ValidationError) as context:
            intermediaria.clean()

        self.assertIn('numero_sequencial', context.exception.message_dict)

    def test_validar_valor_maior_que_zero(self):
        """Testa que valor da intermediária deve ser maior que zero"""
        intermediaria = PrestacaoIntermediaria(
            contrato=self.contrato,
            numero_sequencial=1,
            mes_vencimento=12,
            valor=Decimal('0.00')  # Valor zero
        )

        with self.assertRaises(ValidationError) as context:
            intermediaria.clean()

        self.assertIn('valor', context.exception.message_dict)

    def test_intermediaria_valida_passa_validacao(self):
        """Testa que intermediária válida passa na validação"""
        intermediaria = PrestacaoIntermediaria(
            contrato=self.contrato,
            numero_sequencial=1,
            mes_vencimento=12,
            valor=Decimal('5000.00')
        )

        # Não deve levantar exceção
        try:
            intermediaria.clean()
        except ValidationError:
            self.fail("Intermediária válida não deveria levantar ValidationError")
