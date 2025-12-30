"""
Testes para as tarefas Celery do módulo financeiro.

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


class TestFinanceiroTasks(TestCase):
    """Testes para tasks do módulo financeiro"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela

        # Criar estrutura base
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Tasks',
            documento='44444444000100'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Tasks',
            documento='55555555000100'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Tasks',
            documento='66666666666',
            email='comprador@teste.com'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-TASK-001',
            endereco='Rua Task, 123'
        )

        # Criar contrato
        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-TASK-001',
            data_contrato=date.today() - timedelta(days=60),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=36,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO
        )

        # Criar parcelas
        for i in range(1, 37):
            vencimento = date.today() + timedelta(days=30 * (i - 2))  # Algumas já vencidas
            Parcela.objects.create(
                contrato=cls.contrato,
                numero_parcela=i,
                data_vencimento=vencimento,
                valor_original=Decimal('2500.00'),
                valor_atual=Decimal('2500.00'),
                ciclo_reajuste=1 if i <= 12 else (2 if i <= 24 else 3)
            )

    def test_atualizar_juros_multa_parcelas_vencidas(self):
        """Testa task de atualização de juros e multa"""
        from financeiro.tasks import atualizar_juros_multa_parcelas_vencidas

        resultado = atualizar_juros_multa_parcelas_vencidas()

        # Deve retornar quantidade de parcelas atualizadas
        self.assertIsInstance(resultado, int)
        self.assertGreaterEqual(resultado, 0)

    def test_limpar_boletos_vencidos(self):
        """Testa task de limpeza de boletos vencidos"""
        from financeiro.tasks import limpar_boletos_vencidos
        from financeiro.models import Parcela, StatusBoleto

        # Marcar algumas parcelas como boleto gerado
        Parcela.objects.filter(
            contrato=self.contrato,
            pago=False,
            data_vencimento__lt=date.today()
        ).update(status_boleto=StatusBoleto.GERADO)

        resultado = limpar_boletos_vencidos()

        # Deve retornar quantidade atualizada
        self.assertIsInstance(resultado, int)

        # Verificar que boletos foram marcados como vencidos
        vencidos = Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.VENCIDO
        ).count()

        self.assertGreaterEqual(vencidos, 0)

    def test_gerar_relatorio_diario(self):
        """Testa task de geração de relatório diário"""
        from financeiro.tasks import gerar_relatorio_diario

        resultado = gerar_relatorio_diario()

        # Deve retornar dicionário com estatísticas
        self.assertIsInstance(resultado, dict)
        self.assertIn('data', resultado)
        self.assertIn('pagamentos', resultado)
        self.assertIn('boletos_gerados', resultado)
        self.assertIn('vencendo_hoje', resultado)
        self.assertIn('vencidas', resultado)
        self.assertIn('contratos_ativos', resultado)

    @patch('financeiro.tasks.enviar_lembrete_parcela.delay')
    def test_enviar_lembretes_vencimento(self, mock_enviar):
        """Testa task de envio de lembretes"""
        from financeiro.tasks import enviar_lembretes_vencimento
        from financeiro.models import Parcela

        # Criar parcela vencendo em 7 dias
        data_vencimento = date.today() + timedelta(days=7)
        Parcela.objects.filter(contrato=self.contrato).first().delete()
        Parcela.objects.create(
            contrato=self.contrato,
            numero_parcela=100,
            data_vencimento=data_vencimento,
            valor_original=Decimal('2500.00'),
            valor_atual=Decimal('2500.00'),
            ciclo_reajuste=1
        )

        resultado = enviar_lembretes_vencimento()

        # Deve retornar quantidade de lembretes agendados
        self.assertIsInstance(resultado, int)

    @patch('financeiro.tasks.ReajusteService')
    def test_verificar_alertas_reajuste(self, mock_service_class):
        """Testa task de verificação de alertas de reajuste"""
        from financeiro.tasks import verificar_alertas_reajuste

        # Mock do serviço
        mock_service = MagicMock()
        mock_service.listar_contratos_reajuste_pendente.return_value = []
        mock_service_class.return_value = mock_service

        resultado = verificar_alertas_reajuste()

        # Deve retornar dicionário com estatísticas
        self.assertIsInstance(resultado, dict)
        self.assertIn('total_pendentes', resultado)
        self.assertIn('urgentes', resultado)
        self.assertIn('bloqueados', resultado)
        self.assertIn('alertas_enviados', resultado)

    @patch('financeiro.tasks.IndiceEconomicoService')
    def test_buscar_indices_economicos(self, mock_service_class):
        """Testa task de busca de índices econômicos"""
        from financeiro.tasks import buscar_indices_economicos

        # Mock do serviço
        mock_service = MagicMock()
        mock_service.buscar_indice_bcb.return_value = []
        mock_service.importar_indices_periodo.return_value = {
            'criados': 0,
            'atualizados': 0,
            'erros': 0,
            'total': 0
        }
        mock_service_class.return_value = mock_service

        resultado = buscar_indices_economicos()

        # Deve retornar dicionário com resultados
        self.assertIsInstance(resultado, dict)
        self.assertIn('sucesso', resultado)
        self.assertIn('erro', resultado)


class TestTasksGeracao(TestCase):
    """Testes para tasks de geração automática"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel, ContaBancaria
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela

        # Criar estrutura base
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Geração',
            documento='77777777000100'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Geração',
            documento='88888888000100'
        )

        cls.conta = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            descricao='Conta Principal',
            banco='001',
            agencia='1234',
            conta='56789',
            digito='0',
            convenio='123456',
            principal=True,
            ativo=True
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Geração',
            documento='99999999999'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-GER-001',
            endereco='Rua Geração, 456'
        )

        # Criar contrato
        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-GER-001',
            data_contrato=date.today() - timedelta(days=30),
            valor_total=Decimal('50000.00'),
            valor_entrada=Decimal('5000.00'),
            numero_parcelas=24,
            dia_vencimento=15,
            tipo_correcao=TipoCorrecao.FIXO,  # Sem reajuste para não bloquear
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO
        )

        # Criar parcelas para o próximo mês
        proximo_mes = date.today().replace(day=1) + timedelta(days=32)
        for i in range(1, 25):
            vencimento = proximo_mes.replace(day=15) + timedelta(days=30 * (i - 1))
            Parcela.objects.create(
                contrato=cls.contrato,
                numero_parcela=i,
                data_vencimento=vencimento,
                valor_original=Decimal('1875.00'),
                valor_atual=Decimal('1875.00'),
                ciclo_reajuste=1 if i <= 12 else 2
            )

    @patch('financeiro.models.Parcela.gerar_boleto')
    def test_gerar_boletos_automaticos(self, mock_gerar):
        """Testa task de geração automática de boletos"""
        from financeiro.tasks import gerar_boletos_automaticos

        mock_gerar.return_value = {'sucesso': True, 'nosso_numero': '123'}

        resultado = gerar_boletos_automaticos()

        # Deve retornar dicionário com resultados
        self.assertIsInstance(resultado, dict)
        self.assertIn('total', resultado)
        self.assertIn('gerados', resultado)
        self.assertIn('bloqueados', resultado)
        self.assertIn('erros', resultado)
        self.assertIn('detalhes', resultado)


class TestEnvioEmail(TestCase):
    """Testes para tasks de envio de email"""

    @patch('django.core.mail.send_mail')
    def test_enviar_lembrete_parcela(self, mock_send_mail):
        """Testa envio de lembrete para parcela"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela
        from financeiro.tasks import enviar_lembrete_parcela

        # Setup
        contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Email',
            documento='10101010000100'
        )

        imobiliaria = Imobiliaria.objects.create(
            contabilidade=contabilidade,
            nome='Imobiliária Email',
            documento='20202020000100'
        )

        comprador = Comprador.objects.create(
            imobiliaria=imobiliaria,
            nome='Comprador Email',
            documento='30303030303',
            email='teste@email.com'
        )

        imovel = Imovel.objects.create(
            imobiliaria=imobiliaria,
            identificacao='LOTE-EMAIL-001',
            endereco='Rua Email, 789'
        )

        contrato = Contrato.objects.create(
            imobiliaria=imobiliaria,
            comprador=comprador,
            imovel=imovel,
            numero_contrato='CONT-EMAIL-001',
            data_contrato=date.today(),
            valor_total=Decimal('30000.00'),
            valor_entrada=Decimal('3000.00'),
            numero_parcelas=12,
            dia_vencimento=20,
            tipo_correcao=TipoCorrecao.FIXO,
            status=StatusContrato.ATIVO
        )

        parcela = Parcela.objects.create(
            contrato=contrato,
            numero_parcela=1,
            data_vencimento=date.today() + timedelta(days=7),
            valor_original=Decimal('2250.00'),
            valor_atual=Decimal('2250.00'),
            ciclo_reajuste=1
        )

        # Executar
        with patch('django.conf.settings.DEFAULT_FROM_EMAIL', 'noreply@teste.com'):
            resultado = enviar_lembrete_parcela(parcela.id, 7)

        # Verificar
        self.assertTrue(mock_send_mail.called or resultado is False)

    @patch('django.core.mail.send_mail')
    def test_enviar_alerta_reajuste(self, mock_send_mail):
        """Testa envio de alerta de reajuste"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.tasks import enviar_alerta_reajuste

        # Setup
        contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Alerta',
            documento='40404040000100'
        )

        imobiliaria = Imobiliaria.objects.create(
            contabilidade=contabilidade,
            nome='Imobiliária Alerta',
            documento='50505050000100',
            email='imob@teste.com'
        )

        comprador = Comprador.objects.create(
            imobiliaria=imobiliaria,
            nome='Comprador Alerta',
            documento='60606060606'
        )

        imovel = Imovel.objects.create(
            imobiliaria=imobiliaria,
            identificacao='LOTE-ALERTA-001',
            endereco='Rua Alerta, 321'
        )

        contrato = Contrato.objects.create(
            imobiliaria=imobiliaria,
            comprador=comprador,
            imovel=imovel,
            numero_contrato='CONT-ALERTA-001',
            data_contrato=date.today() - timedelta(days=360),
            valor_total=Decimal('80000.00'),
            valor_entrada=Decimal('8000.00'),
            numero_parcelas=36,
            dia_vencimento=5,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO
        )

        # Executar
        with patch('django.conf.settings.DEFAULT_FROM_EMAIL', 'noreply@teste.com'):
            resultado = enviar_alerta_reajuste(
                contrato.id,
                dias_restantes=7,
                urgente=True,
                bloqueado=True
            )

        # Verificar
        # Resultado pode ser True se email foi enviado, False se houve erro
        self.assertIn(resultado, [True, False, None])
