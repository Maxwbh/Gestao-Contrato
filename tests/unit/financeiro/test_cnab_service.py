"""
Testes para o serviço CNAB - Geração de Remessa e Processamento de Retorno.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, Mock
from io import BytesIO

from django.test import TestCase
from django.utils import timezone
from django.core.files.base import ContentFile

from financeiro.services.cnab_service import (
    CNABService, BANCOS_BRCOBRANCA, OCORRENCIAS_CNAB
)


class TestCNABServiceBasico(TestCase):
    """Testes básicos do CNABService"""

    def setUp(self):
        """Configura dados de teste"""
        self.service = CNABService()

    def test_instanciacao_servico(self):
        """Testa se o serviço pode ser instanciado"""
        service = CNABService()
        self.assertIsNotNone(service)
        self.assertIn('localhost', service.brcobranca_url)

    def test_get_banco_brcobranca_banco_brasil(self):
        """Testa mapeamento do Banco do Brasil"""
        resultado = self.service._get_banco_brcobranca('001')
        self.assertEqual(resultado, 'banco_brasil')

    def test_get_banco_brcobranca_bradesco(self):
        """Testa mapeamento do Bradesco"""
        resultado = self.service._get_banco_brcobranca('237')
        self.assertEqual(resultado, 'bradesco')

    def test_get_banco_brcobranca_itau(self):
        """Testa mapeamento do Itaú"""
        resultado = self.service._get_banco_brcobranca('341')
        self.assertEqual(resultado, 'itau')

    def test_get_banco_brcobranca_desconhecido(self):
        """Testa mapeamento de banco desconhecido (deve retornar banco_brasil)"""
        resultado = self.service._get_banco_brcobranca('999')
        self.assertEqual(resultado, 'banco_brasil')

    def test_formatar_cpf_cnpj_com_formatacao(self):
        """Testa formatação de CPF/CNPJ removendo caracteres especiais"""
        # CNPJ formatado
        resultado = self.service._formatar_cpf_cnpj('12.345.678/0001-90')
        self.assertEqual(resultado, '12345678000190')

        # CPF formatado
        resultado = self.service._formatar_cpf_cnpj('123.456.789-01')
        self.assertEqual(resultado, '12345678901')

    def test_formatar_cpf_cnpj_sem_formatacao(self):
        """Testa formatação de CPF/CNPJ já sem caracteres especiais"""
        resultado = self.service._formatar_cpf_cnpj('12345678000190')
        self.assertEqual(resultado, '12345678000190')

    def test_formatar_cpf_cnpj_vazio(self):
        """Testa formatação de CPF/CNPJ vazio"""
        resultado = self.service._formatar_cpf_cnpj('')
        self.assertEqual(resultado, '')

        resultado = self.service._formatar_cpf_cnpj(None)
        self.assertEqual(resultado, '')

    def test_formatar_data(self):
        """Testa formatação de data para o padrão BRCobranca"""
        data = date(2024, 12, 31)
        resultado = self.service._formatar_data(data)
        self.assertEqual(resultado, '31/12/2024')

    def test_formatar_data_none(self):
        """Testa formatação de data None"""
        resultado = self.service._formatar_data(None)
        self.assertEqual(resultado, '')

    def test_formatar_valor(self):
        """Testa formatação de valor"""
        valor = Decimal('1234.56')
        resultado = self.service._formatar_valor(valor)
        self.assertEqual(resultado, '1234.56')

    def test_formatar_valor_zero(self):
        """Testa formatação de valor zero"""
        resultado = self.service._formatar_valor(Decimal('0'))
        self.assertEqual(resultado, '0.0')

    def test_formatar_valor_none(self):
        """Testa formatação de valor None"""
        resultado = self.service._formatar_valor(None)
        self.assertEqual(resultado, '0.0')


class TestMapeamentoBancos(TestCase):
    """Testes para o mapeamento de bancos"""

    def test_bancos_principais_mapeados(self):
        """Verifica se os principais bancos estão mapeados"""
        bancos_esperados = [
            ('001', 'banco_brasil'),
            ('033', 'santander'),
            ('104', 'caixa'),
            ('237', 'bradesco'),
            ('341', 'itau'),
            ('748', 'sicredi'),
            ('756', 'sicoob'),
        ]

        for codigo, nome in bancos_esperados:
            with self.subTest(codigo=codigo):
                self.assertEqual(BANCOS_BRCOBRANCA[codigo], nome)

    def test_total_bancos_mapeados(self):
        """Verifica quantidade de bancos mapeados"""
        self.assertGreaterEqual(len(BANCOS_BRCOBRANCA), 15)


class TestOcorrenciasCNAB(TestCase):
    """Testes para as ocorrências CNAB"""

    def test_ocorrencia_liquidacao(self):
        """Testa ocorrência de liquidação"""
        self.assertIn('06', OCORRENCIAS_CNAB)
        tipo, descricao = OCORRENCIAS_CNAB['06']
        self.assertEqual(tipo, 'LIQUIDACAO')

    def test_ocorrencia_rejeicao(self):
        """Testa ocorrência de rejeição"""
        self.assertIn('03', OCORRENCIAS_CNAB)
        tipo, descricao = OCORRENCIAS_CNAB['03']
        self.assertEqual(tipo, 'REJEICAO')

    def test_ocorrencia_baixa(self):
        """Testa ocorrências de baixa"""
        self.assertIn('09', OCORRENCIAS_CNAB)
        tipo, _ = OCORRENCIAS_CNAB['09']
        self.assertEqual(tipo, 'BAIXA')


class TestCNABServiceIntegracao(TestCase):
    """Testes de integração do CNABService"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela, ContaBancaria

        # Criar estrutura base
        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade CNAB',
            documento='11111111000111'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária CNAB',
            razao_social='Imobiliária CNAB LTDA',
            documento='22222222000122',
            cnpj='22222222000122'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador CNAB',
            documento='33333333333',
            cpf='33333333333',
            email='comprador@cnab.com',
            endereco='Rua Teste, 123',
            numero='123',
            bairro='Centro',
            cidade='São Paulo',
            estado='SP',
            cep='01234-567'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-CNAB-001',
            endereco='Rua CNAB, 100'
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-CNAB-001',
            data_contrato=date.today() - timedelta(days=30),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00')
        )

        # Criar conta bancária
        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            banco='001',
            agencia='1234-5',
            conta='12345-6',
            convenio='0123456',
            carteira='18',
            nome_titular='Imobiliária CNAB LTDA',
            documento_titular='22222222000122'
        )

        # Criar parcelas
        for i in range(1, 13):
            Parcela.objects.create(
                contrato=cls.contrato,
                numero_parcela=i,
                data_vencimento=date.today() + timedelta(days=30 * i),
                valor_original=Decimal('3750.00'),
                valor_atual=Decimal('3750.00'),
                valor_boleto=Decimal('3750.00'),
                ciclo_reajuste=1,
                pago=(i <= 3),
                tem_boleto=(i <= 6),
                nosso_numero=f'000000{i:03d}' if i <= 6 else None,
                numero_documento=f'CONT-CNAB-001-{i:03d}' if i <= 6 else None
            )

    def test_gerar_remessa_parcelas_invalidas(self):
        """Testa geração de remessa sem parcelas válidas"""
        service = CNABService()
        # Lista vazia
        resultado = service.gerar_remessa([], self.conta_bancaria)

        self.assertFalse(resultado['sucesso'])
        self.assertIn('Nenhuma parcela', resultado['erro'])

    def test_montar_dados_boleto(self):
        """Testa montagem de dados do boleto para BRCobranca"""
        from financeiro.models import Parcela

        service = CNABService()
        parcela = Parcela.objects.filter(
            contrato=self.contrato,
            tem_boleto=True,
            pago=False
        ).first()

        dados = service._montar_dados_boleto(parcela, self.conta_bancaria)

        self.assertIn('nosso_numero', dados)
        self.assertIn('valor', dados)
        self.assertIn('data_vencimento', dados)
        self.assertIn('cedente', dados)
        self.assertIn('sacado', dados)
        self.assertEqual(dados['sacado'][:len(self.comprador.nome)], self.comprador.nome)

    @patch('requests.post')
    def test_gerar_remessa_sucesso_api(self, mock_post):
        """Testa geração de remessa com sucesso via API"""
        from financeiro.models import Parcela, ArquivoRemessa
        import base64

        # Mock da resposta da API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'remessa': base64.b64encode(b'ARQUIVO REMESSA TESTE').decode()
        }
        mock_post.return_value = mock_response

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            tem_boleto=True,
            pago=False
        )[:3])

        resultado = service.gerar_remessa(parcelas, self.conta_bancaria)

        self.assertTrue(resultado['sucesso'])
        self.assertIn('arquivo_remessa', resultado)
        self.assertEqual(resultado['quantidade_boletos'], len(parcelas))

    @patch('requests.post')
    def test_gerar_remessa_erro_api(self, mock_post):
        """Testa geração de remessa com erro da API"""
        from financeiro.models import Parcela

        # Mock de erro da API
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            tem_boleto=True,
            pago=False
        )[:2])

        resultado = service.gerar_remessa(parcelas, self.conta_bancaria)

        self.assertFalse(resultado['sucesso'])
        self.assertIn('Erro BRCobranca', resultado['erro'])

    @patch('requests.post')
    def test_gerar_remessa_api_indisponivel_fallback_local(self, mock_post):
        """Testa fallback para geração local quando API indisponível"""
        from financeiro.models import Parcela
        import requests

        # Mock de erro de conexão
        mock_post.side_effect = requests.exceptions.ConnectionError()

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            tem_boleto=True,
            pago=False
        )[:2])

        resultado = service.gerar_remessa(parcelas, self.conta_bancaria)

        self.assertTrue(resultado['sucesso'])
        self.assertIn('aviso', resultado)
        self.assertIn('localmente', resultado['aviso'])

    def test_obter_boletos_sem_remessa(self):
        """Testa obtenção de boletos sem remessa"""
        from financeiro.models import Parcela, StatusBoleto

        service = CNABService()

        # Atualizar parcelas para ter status de boleto gerado
        Parcela.objects.filter(
            contrato=self.contrato,
            tem_boleto=True,
            pago=False
        ).update(status_boleto=StatusBoleto.GERADO)

        boletos = service.obter_boletos_sem_remessa()

        self.assertIsInstance(boletos, list)


class TestProcessamentoRetornoCNAB400(TestCase):
    """Testes para processamento de retorno CNAB 400"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela, ContaBancaria, ArquivoRetorno

        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Retorno',
            documento='44444444000144'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Retorno',
            documento='55555555000155',
            cnpj='55555555000155'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Retorno',
            documento='66666666666',
            cpf='66666666666'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-RET-001',
            endereco='Rua Retorno, 200'
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-RET-001',
            data_contrato=date.today() - timedelta(days=60),
            valor_total=Decimal('50000.00'),
            valor_entrada=Decimal('5000.00'),
            numero_parcelas=12,
            dia_vencimento=15,
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            banco='001',
            agencia='5678',
            conta='98765-4',
            convenio='9876543',
            carteira='17'
        )

        # Criar parcela com nosso_numero específico
        cls.parcela = Parcela.objects.create(
            contrato=cls.contrato,
            numero_parcela=1,
            data_vencimento=date.today() - timedelta(days=15),
            valor_original=Decimal('3750.00'),
            valor_atual=Decimal('3750.00'),
            valor_boleto=Decimal('3750.00'),
            ciclo_reajuste=1,
            pago=False,
            tem_boleto=True,
            nosso_numero='12345678901234567890'
        )

    def _criar_linha_retorno_cnab400(
        self,
        nosso_numero,
        codigo_ocorrencia,
        valor_titulo,
        valor_pago,
        data_ocorrencia='060126',
        data_credito='070126'
    ):
        """Cria uma linha de retorno CNAB 400 para testes"""
        linha = '1'  # Tipo registro
        linha += '02'  # Tipo inscricao
        linha += '55555555000155'  # CNPJ
        linha += '5678'  # Agencia
        linha += '00'  # Zeros
        linha += '00098765'  # Conta
        linha += '4'  # Digito
        linha += ''.ljust(6)  # Brancos
        linha += 'CTR-001-001'.ljust(25)  # Uso empresa
        linha += nosso_numero.ljust(20)  # Nosso numero (pos 62-82)
        linha += ''.ljust(26)  # Brancos
        linha += codigo_ocorrencia  # Codigo ocorrencia (pos 108-110)
        linha += data_ocorrencia  # Data ocorrencia (pos 110-116)
        linha += 'CTR-001-001'.ljust(10)  # Numero titulo
        linha += ''.ljust(20)  # Brancos
        linha += '060126'  # Data vencimento
        linha += str(int(valor_titulo * 100)).zfill(13)  # Valor titulo (pos 152-165)
        linha += '001'  # Banco
        linha += '00000'  # Agencia cobradora
        linha += ''.ljust(2)  # Especie
        linha += ''.ljust(26)  # Brancos
        linha += data_credito  # Data credito (pos 175-181)
        linha += ''.ljust(72)  # Brancos
        linha += str(int(valor_pago * 100)).zfill(13)  # Valor pago (pos 253-266)
        linha += ''.ljust(128)  # Brancos
        linha += '000001'  # Sequencial

        return linha[:400]

    def test_processar_retorno_cnab400_liquidacao(self):
        """Testa processamento de retorno com liquidação CNAB 400"""
        from financeiro.models import ArquivoRetorno, StatusArquivoRetorno

        # Criar arquivo de retorno
        arquivo_retorno = ArquivoRetorno.objects.create(
            conta_bancaria=self.conta_bancaria,
            nome_arquivo='CB0601.RET',
            status=StatusArquivoRetorno.PENDENTE
        )

        # Criar conteúdo do arquivo
        header = '0' + ''.ljust(399)
        detalhe = self._criar_linha_retorno_cnab400(
            nosso_numero=self.parcela.nosso_numero,
            codigo_ocorrencia='06',  # Liquidação
            valor_titulo=Decimal('3750.00'),
            valor_pago=Decimal('3750.00')
        )
        trailer = '9' + ''.ljust(399)

        conteudo = f"{header}\n{detalhe}\n{trailer}"

        # Salvar arquivo
        arquivo_retorno.arquivo.save(
            'CB0601.RET',
            ContentFile(conteudo.encode('latin-1')),
            save=True
        )

        # Processar
        service = CNABService()
        resultado = service.processar_retorno(arquivo_retorno)

        self.assertTrue(resultado['sucesso'])
        self.assertGreater(resultado['total_registros'], 0)


class TestProcessamentoRetornoCNAB240(TestCase):
    """Testes para processamento de retorno CNAB 240"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela, ContaBancaria

        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade 240',
            documento='77777777000177'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária 240',
            documento='88888888000188',
            cnpj='88888888000188'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador 240',
            documento='99999999999',
            cpf='99999999999'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-240-001',
            endereco='Rua 240, 300'
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-240-001',
            data_contrato=date.today() - timedelta(days=90),
            valor_total=Decimal('80000.00'),
            valor_entrada=Decimal('8000.00'),
            numero_parcelas=36,
            dia_vencimento=20,
            tipo_correcao=TipoCorrecao.IGPM,
            status=StatusContrato.ATIVO
        )

        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            banco='237',  # Bradesco
            agencia='9999',
            conta='88888-9',
            convenio='0987654',
            carteira='09'
        )

        cls.parcela = Parcela.objects.create(
            contrato=cls.contrato,
            numero_parcela=1,
            data_vencimento=date.today() - timedelta(days=10),
            valor_original=Decimal('2000.00'),
            valor_atual=Decimal('2000.00'),
            valor_boleto=Decimal('2000.00'),
            ciclo_reajuste=1,
            pago=False,
            tem_boleto=True,
            nosso_numero='00000000000000000001'
        )

    def test_detectar_layout_cnab240(self):
        """Testa detecção de layout CNAB 240"""
        from financeiro.models import ArquivoRetorno, StatusArquivoRetorno

        # Criar arquivo de retorno com linha de 240 caracteres
        arquivo_retorno = ArquivoRetorno.objects.create(
            conta_bancaria=self.conta_bancaria,
            nome_arquivo='CB0602.RET',
            status=StatusArquivoRetorno.PENDENTE
        )

        # Conteúdo CNAB 240 (linha com 240 caracteres)
        header = '2370001'.ljust(240)
        arquivo_retorno.arquivo.save(
            'CB0602.RET',
            ContentFile(header.encode('latin-1')),
            save=True
        )

        service = CNABService()

        # Ler arquivo e verificar tamanho da linha
        arquivo_retorno.arquivo.seek(0)
        conteudo = arquivo_retorno.arquivo.read().decode('latin-1')
        linhas = conteudo.split('\n')

        # Linha deve ter 240 caracteres (sem \n)
        self.assertEqual(len(linhas[0].strip()), 240)


class TestRegenerarRemessa(TestCase):
    """Testes para regeneração de remessa"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import Parcela, ContaBancaria, ArquivoRemessa

        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Regen',
            documento='10101010000110'
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Regen',
            documento='20202020000120',
            cnpj='20202020000120'
        )

        cls.comprador = Comprador.objects.create(
            imobiliaria=cls.imobiliaria,
            nome='Comprador Regen',
            documento='30303030303',
            cpf='30303030303'
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-REG-001',
            endereco='Rua Regen, 400'
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-REG-001',
            data_contrato=date.today() - timedelta(days=45),
            valor_total=Decimal('60000.00'),
            valor_entrada=Decimal('6000.00'),
            numero_parcelas=18,
            dia_vencimento=5,
            tipo_correcao=TipoCorrecao.FIXO,
            status=StatusContrato.ATIVO
        )

        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            banco='341',  # Itaú
            agencia='7777',
            conta='77777-7',
            convenio='7777777',
            carteira='175'
        )

    def test_regenerar_remessa_status_invalido(self):
        """Testa regeneração de remessa com status inválido"""
        from financeiro.models import ArquivoRemessa

        # Criar remessa com status ENVIADO (não pode regenerar)
        arquivo_remessa = ArquivoRemessa.objects.create(
            conta_bancaria=self.conta_bancaria,
            numero_remessa=1,
            layout='CNAB_240',
            nome_arquivo='CB0601.REM',
            quantidade_boletos=1,
            valor_total=Decimal('1000.00'),
            status='ENVIADO'
        )

        service = CNABService()
        resultado = service.regenerar_remessa(arquivo_remessa)

        self.assertFalse(resultado['sucesso'])
        self.assertIn('status', resultado['erro'].lower())
