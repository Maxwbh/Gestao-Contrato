"""
Testes para APIs REST do módulo financeiro.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import pytest
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
from contratos.models import Contrato, TipoCorrecao, StatusContrato
from financeiro.models import Parcela, Reajuste


class TestAPIBaseSetup(TestCase):
    """Base para testes de API com dados comuns"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        # Criar usuário
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@test.com'
        )

        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade API',
            documento='77777777000177'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária API',
            razao_social='Imobiliária API LTDA',
            documento='88888888000188',
            cnpj='88888888000188'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador API',
            documento='99999999999',
            cpf='99999999999',
            email='comprador@api.com'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-API-001',
            endereco='Rua API, 500'
        )

        # Criar contrato
        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-API-001',
            data_contrato=date.today() - timedelta(days=30),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO
        )

        # Criar algumas parcelas
        for i in range(1, 25):
            vencimento = date.today() + timedelta(days=30 * i)
            Parcela.objects.create(
                contrato=cls.contrato,
                numero_parcela=i,
                data_vencimento=vencimento,
                valor_original=Decimal('3750.00'),
                valor_atual=Decimal('3750.00'),
                ciclo_reajuste=1 if i <= 12 else 2,
                pago=(i <= 3)  # Primeiras 3 pagas
            )

    def setUp(self):
        """Login antes de cada teste"""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')


class TestAPIImobiliarias(TestAPIBaseSetup):
    """Testes para API de imobiliárias"""

    def test_listar_imobiliarias(self):
        """Testa listagem de imobiliárias"""
        url = reverse('financeiro:api_imobiliarias')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertIn('imobiliarias', data)
        self.assertGreater(len(data['imobiliarias']), 0)

    def test_listar_imobiliarias_filtro_contabilidade(self):
        """Testa listagem de imobiliárias filtrada por contabilidade"""
        url = reverse('financeiro:api_imobiliarias')
        response = self.client.get(url, {'contabilidade': self.contabilidade.id})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        for imob in data['imobiliarias']:
            self.assertEqual(imob['contabilidade']['id'], self.contabilidade.id)

    def test_dashboard_imobiliaria(self):
        """Testa dashboard de imobiliária específica"""
        url = reverse('financeiro:api_imobiliaria_dashboard', args=[self.imobiliaria.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertIn('contratos', data)
        self.assertIn('parcelas', data)
        self.assertIn('proximas_parcelas', data)


class TestAPIContratos(TestAPIBaseSetup):
    """Testes para API de contratos"""

    def test_listar_contratos(self):
        """Testa listagem de contratos"""
        url = reverse('financeiro:api_contratos')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertIn('contratos', data)
        self.assertIn('total', data)
        self.assertIn('page', data)

    def test_listar_contratos_paginacao(self):
        """Testa paginação da listagem de contratos"""
        url = reverse('financeiro:api_contratos')
        response = self.client.get(url, {'page': 1, 'per_page': 10})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['page'], 1)
        self.assertEqual(data['per_page'], 10)
        self.assertIn('total_pages', data)

    def test_listar_contratos_filtro_imobiliaria(self):
        """Testa filtro por imobiliária"""
        url = reverse('financeiro:api_contratos')
        response = self.client.get(url, {'imobiliaria': self.imobiliaria.id})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        for contrato in data['contratos']:
            self.assertEqual(contrato['imobiliaria']['id'], self.imobiliaria.id)

    def test_detalhe_contrato(self):
        """Testa detalhes de um contrato"""
        url = reverse('financeiro:api_contrato_detalhe', args=[self.contrato.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertEqual(data['contrato']['id'], self.contrato.id)
        self.assertIn('valores', data['contrato'])
        self.assertIn('resumo_financeiro', data['contrato'])

    def test_detalhe_contrato_inexistente(self):
        """Testa detalhe de contrato inexistente"""
        url = reverse('financeiro:api_contrato_detalhe', args=[99999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_parcelas_contrato(self):
        """Testa listagem de parcelas de um contrato"""
        url = reverse('financeiro:api_contrato_parcelas', args=[self.contrato.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertEqual(data['contrato_id'], self.contrato.id)
        self.assertIn('parcelas', data)
        self.assertEqual(len(data['parcelas']), 24)

    def test_parcelas_contrato_filtro_status(self):
        """Testa filtro de parcelas por status"""
        url = reverse('financeiro:api_contrato_parcelas', args=[self.contrato.id])
        response = self.client.get(url, {'status': 'pago'})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        for parcela in data['parcelas']:
            self.assertTrue(parcela['pago'])

    def test_reajustes_contrato(self):
        """Testa listagem de reajustes de um contrato"""
        url = reverse('financeiro:api_contrato_reajustes', args=[self.contrato.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertEqual(data['contrato_id'], self.contrato.id)
        self.assertIn('reajustes', data)


class TestAPIParcelas(TestAPIBaseSetup):
    """Testes para API de parcelas"""

    def test_listar_parcelas(self):
        """Testa listagem de parcelas"""
        url = reverse('financeiro:api_parcelas')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertIn('parcelas', data)
        self.assertIn('totais', data)

    def test_listar_parcelas_filtro_contrato(self):
        """Testa filtro de parcelas por contrato"""
        url = reverse('financeiro:api_parcelas')
        response = self.client.get(url, {'contrato': self.contrato.id})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        for parcela in data['parcelas']:
            self.assertEqual(parcela['contrato']['id'], self.contrato.id)

    def test_listar_parcelas_filtro_periodo(self):
        """Testa filtro de parcelas por período"""
        hoje = date.today()
        data_inicio = hoje.strftime('%Y-%m-%d')
        data_fim = (hoje + timedelta(days=90)).strftime('%Y-%m-%d')

        url = reverse('financeiro:api_parcelas')
        response = self.client.get(url, {
            'data_inicio': data_inicio,
            'data_fim': data_fim
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])

    def test_registrar_pagamento_parcela(self):
        """Testa registro de pagamento de parcela"""
        # Obter uma parcela não paga
        parcela = Parcela.objects.filter(contrato=self.contrato, pago=False).first()

        url = reverse('financeiro:api_parcela_pagamento', args=[parcela.id])
        response = self.client.post(
            url,
            data=json.dumps({
                'valor_pago': float(parcela.valor_atual),
                'data_pagamento': date.today().strftime('%Y-%m-%d'),
                'forma_pagamento': 'PIX',
                'observacoes': 'Pagamento via API'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data['sucesso'])
        self.assertTrue(data['parcela']['pago'])

        # Verificar no banco
        parcela.refresh_from_db()
        self.assertTrue(parcela.pago)

    def test_registrar_pagamento_parcela_ja_paga(self):
        """Testa registro de pagamento em parcela já paga"""
        # Obter uma parcela paga
        parcela = Parcela.objects.filter(contrato=self.contrato, pago=True).first()

        url = reverse('financeiro:api_parcela_pagamento', args=[parcela.id])
        response = self.client.post(
            url,
            data=json.dumps({
                'valor_pago': 1000.00,
                'data_pagamento': date.today().strftime('%Y-%m-%d')
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)

        self.assertFalse(data['sucesso'])
        self.assertIn('já está paga', data['erro'])

    def test_registrar_pagamento_valor_invalido(self):
        """Testa registro de pagamento com valor inválido"""
        parcela = Parcela.objects.filter(contrato=self.contrato, pago=False).first()

        url = reverse('financeiro:api_parcela_pagamento', args=[parcela.id])
        response = self.client.post(
            url,
            data=json.dumps({
                'valor_pago': 0,  # Valor inválido
                'data_pagamento': date.today().strftime('%Y-%m-%d')
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)

        self.assertFalse(data['sucesso'])


class TestAPIAutenticacao(TestCase):
    """Testes para verificar autenticação das APIs"""

    def test_api_requer_login(self):
        """Testa que APIs requerem login"""
        client = Client()  # Cliente não autenticado

        urls = [
            reverse('financeiro:api_imobiliarias'),
            reverse('financeiro:api_contratos'),
            reverse('financeiro:api_parcelas'),
        ]

        for url in urls:
            response = client.get(url)
            # Deve redirecionar para login
            self.assertEqual(response.status_code, 302)
            self.assertIn('login', response.url)
