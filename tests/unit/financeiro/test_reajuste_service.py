"""
Testes para o serviço de reajuste de contratos.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from financeiro.services.reajuste_service import ReajusteService, IndiceEconomicoService


class TestReajusteService(TestCase):
    """Testes para ReajusteService"""

    def setUp(self):
        """Configura dados de teste"""
        self.service = ReajusteService()

    def test_instanciacao_servico(self):
        """Testa se o serviço pode ser instanciado"""
        service = ReajusteService()
        self.assertIsNotNone(service)
        self.assertEqual(service.erros, [])
        self.assertEqual(service.avisos, [])

    def test_fontes_indices_definidas(self):
        """Testa se as fontes de índices estão definidas"""
        self.assertIn('IPCA', ReajusteService.FONTES_INDICES)
        self.assertIn('IGPM', ReajusteService.FONTES_INDICES)
        self.assertIn('SELIC', ReajusteService.FONTES_INDICES)
        self.assertIn('TR', ReajusteService.FONTES_INDICES)
        self.assertIn('INPC', ReajusteService.FONTES_INDICES)
        self.assertIn('INCC', ReajusteService.FONTES_INDICES)

    def test_buscar_indice_inexistente(self):
        """Testa busca de índice que não existe"""
        resultado = self.service.buscar_indice('IPCA', 1990, 1)
        self.assertIsNone(resultado)

    def test_verificar_indices_disponiveis_periodo_vazio(self):
        """Testa verificação de índices para período sem dados"""
        hoje = date.today()
        futuro = hoje + timedelta(days=365)

        disponiveis, faltantes = self.service.verificar_indices_disponiveis(
            'IPCA', futuro, futuro + timedelta(days=30)
        )

        self.assertFalse(disponiveis)
        self.assertGreater(len(faltantes), 0)


class TestIndiceEconomicoService(TestCase):
    """Testes para IndiceEconomicoService"""

    def setUp(self):
        """Configura dados de teste"""
        self.service = IndiceEconomicoService()

    def test_instanciacao_servico(self):
        """Testa se o serviço pode ser instanciado"""
        service = IndiceEconomicoService()
        self.assertIsNotNone(service)
        self.assertEqual(service.erros, [])

    @patch('requests.get')
    def test_buscar_indice_bcb_sucesso(self, mock_get):
        """Testa busca de índice no BCB com sucesso"""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'data': '01/01/2024', 'valor': '0.5'},
            {'data': '01/02/2024', 'valor': '0.6'},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        dados = self.service.buscar_indice_bcb(
            226,  # TR
            date(2024, 1, 1),
            date(2024, 2, 28)
        )

        self.assertEqual(len(dados), 2)
        self.assertEqual(dados[0]['valor'], Decimal('0.5'))
        self.assertEqual(dados[1]['valor'], Decimal('0.6'))

    @patch('requests.get')
    def test_buscar_indice_bcb_erro(self, mock_get):
        """Testa tratamento de erro na busca do BCB"""
        mock_get.side_effect = Exception("Erro de conexão")

        dados = self.service.buscar_indice_bcb(
            226,
            date(2024, 1, 1),
            date(2024, 2, 28)
        )

        self.assertEqual(dados, [])
        self.assertGreater(len(self.service.erros), 0)


class TestReajusteServiceIntegracao(TestCase):
    """Testes de integração para ReajusteService"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato

        # Criar estrutura base
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Teste',
            documento='12345678000100'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Teste',
            documento='98765432000100'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Teste',
            documento='12345678901'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-001',
            endereco='Rua Teste, 123'
        )

        # Contrato de 24 meses
        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-001',
            data_contrato=date.today() - timedelta(days=400),  # 13 meses atrás
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO
        )

    def test_verificar_contrato_precisa_reajuste(self):
        """Testa verificação de contrato que precisa de reajuste"""
        service = ReajusteService()
        resultado = service.verificar_contrato_precisa_reajuste(self.contrato)

        self.assertIn('precisa_reajuste', resultado)

    def test_simular_reajuste(self):
        """Testa simulação de reajuste"""
        from financeiro.models import Parcela

        # Criar algumas parcelas
        for i in range(1, 13):
            Parcela.objects.create(
                contrato=self.contrato,
                numero_parcela=i,
                data_vencimento=date.today() + timedelta(days=30 * i),
                valor_original=Decimal('3750.00'),
                valor_atual=Decimal('3750.00'),
                ciclo_reajuste=1
            )

        service = ReajusteService()
        resultado = service.simular_reajuste(
            self.contrato,
            percentual=Decimal('5.0'),
            ciclo=1
        )

        self.assertTrue(resultado['sucesso'])
        self.assertEqual(resultado['percentual'], Decimal('5.0'))
        self.assertGreater(resultado['valor_novo_total'], resultado['valor_anterior_total'])

    def test_listar_contratos_reajuste_pendente(self):
        """Testa listagem de contratos com reajuste pendente"""
        service = ReajusteService()
        contratos = service.listar_contratos_reajuste_pendente(
            imobiliaria=self.imobiliaria,
            dias_antecedencia=60
        )

        # A lista pode estar vazia ou ter o contrato dependendo da data
        self.assertIsInstance(contratos, list)

    def test_listar_reajustes_contrato(self):
        """Testa listagem de histórico de reajustes"""
        service = ReajusteService()
        reajustes = service.listar_reajustes_contrato(self.contrato)

        self.assertIsInstance(reajustes, list)


class TestReajusteAplicacao(TestCase):
    """Testes para aplicação de reajustes"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato, IndiceReajuste
        from financeiro.models import Parcela

        # Criar estrutura base
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Reajuste',
            documento='11111111000100'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Reajuste',
            documento='22222222000100'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Reajuste',
            documento='33333333333'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-REA-001',
            endereco='Rua Reajuste, 100'
        )

        # Criar índices para teste
        hoje = date.today()
        for i in range(12):
            mes = (hoje.month - i - 1) % 12 + 1
            ano = hoje.year if hoje.month > i else hoje.year - 1
            IndiceReajuste.objects.create(
                tipo_indice='IPCA',
                ano=ano,
                mes=mes,
                valor=Decimal('0.50'),
                fonte='TESTE'
            )

    def test_aplicar_reajuste_manual(self):
        """Testa aplicação de reajuste manual"""
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela

        # Criar contrato para este teste
        contrato = Contrato.objects.create(
            imobiliaria=self.imobiliaria,
            comprador=self.comprador,
            imovel=self.imovel,
            numero_contrato='CONT-REA-001',
            data_contrato=date.today() - timedelta(days=365),
            valor_total=Decimal('50000.00'),
            valor_entrada=Decimal('5000.00'),
            numero_parcelas=24,
            dia_vencimento=15,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO
        )

        # Criar parcelas
        for i in range(1, 25):
            ciclo = 1 if i <= 12 else 2
            Parcela.objects.create(
                contrato=contrato,
                numero_parcela=i,
                data_vencimento=date.today() + timedelta(days=30 * i),
                valor_original=Decimal('1875.00'),
                valor_atual=Decimal('1875.00'),
                ciclo_reajuste=ciclo,
                pago=(i <= 6)  # Primeiras 6 pagas
            )

        service = ReajusteService()
        resultado = service.aplicar_reajuste(
            contrato=contrato,
            percentual=Decimal('5.0'),
            ciclo=1,
            manual=True,
            observacoes='Teste de reajuste manual'
        )

        self.assertTrue(resultado['sucesso'])
        self.assertEqual(resultado['percentual'], Decimal('5.0'))

        # Verificar que parcelas foram reajustadas
        parcela_reajustada = Parcela.objects.filter(
            contrato=contrato,
            numero_parcela=7  # Primeira não paga
        ).first()

        self.assertIsNotNone(parcela_reajustada)
        # Valor deve ter aumentado 5%
        expected = Decimal('1875.00') * Decimal('1.05')
        self.assertAlmostEqual(
            float(parcela_reajustada.valor_atual),
            float(expected),
            places=2
        )
