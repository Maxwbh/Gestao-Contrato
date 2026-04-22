"""
Testes para o serviço CNAB - Geração de Remessa e Processamento de Retorno.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.files.base import ContentFile

from financeiro.services.cnab_service import (
    CNABService, BANCOS_BRCOBRANCA, OCORRENCIAS_CNAB
)
from financeiro.models import StatusArquivoRemessa


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
        self.assertEqual(resultado, '2024/12/31')

    def test_formatar_data_none(self):
        """Testa formatação de data None"""
        resultado = self.service._formatar_data(None)
        self.assertEqual(resultado, '')

    def test_formatar_valor(self):
        """Testa formatação de valor"""
        valor = Decimal('1234.56')
        resultado = self.service._formatar_valor(valor)
        self.assertEqual(resultado, 1234.56)

    def test_formatar_valor_zero(self):
        """Testa formatação de valor zero"""
        resultado = self.service._formatar_valor(Decimal('0'))
        self.assertEqual(resultado, 0.0)

    def test_formatar_valor_none(self):
        """Testa formatação de valor None"""
        resultado = self.service._formatar_valor(None)
        self.assertEqual(resultado, 0.0)


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
            razao_social='Contabilidade CNAB LTDA',
            cnpj='11111111000111',
            endereco='Rua CNAB, 100',
            telefone='(31) 3333-0080',
            email='cnab@contabilidade.com',
            responsavel='Responsável CNAB',
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária CNAB',
            razao_social='Imobiliária CNAB LTDA',
            cnpj='22222222000122',
            telefone='(31) 3333-0081',
            email='cnab@imobiliaria.com',
            responsavel_financeiro='Responsável Financeiro CNAB',
        )

        cls.comprador = Comprador.objects.create(
            nome='Comprador CNAB',
            tipo_pessoa='PF',
            cpf='333.333.333-35',
            telefone='(31) 3333-0082',
            celular='(31) 99999-0082',
            email='comprador@cnab.com',
            logradouro='Rua Teste',
            numero='123',
            bairro='Centro',
            cidade='São Paulo',
            estado='SP',
            cep='01234-567',
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-CNAB-001',
            area='360.00',
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-CNAB-001',
            data_contrato=date.today() - timedelta(days=30),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
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
            descricao='Conta Principal CNAB',
            banco='001',
            agencia='1234-5',
            conta='12345-6',
            convenio='0123456',
            carteira='18',
        )

        # Criar parcelas (only if not auto-generated by contrato.save())
        existing = set(cls.contrato.parcelas.values_list('numero_parcela', flat=True))
        for i in range(1, 13):
            if i not in existing:
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
        # Update auto-generated parcelas with needed attributes
        from financeiro.models import StatusBoleto
        cls.contrato.parcelas.filter(numero_parcela__lte=3).update(pago=True)
        cls.contrato.parcelas.filter(numero_parcela__lte=6).update(
            status_boleto=StatusBoleto.GERADO,
            valor_boleto=Decimal('3750.00'),
        )
        for i in range(1, 7):
            cls.contrato.parcelas.filter(numero_parcela=i).update(
                nosso_numero=f'000000{i:03d}',
                numero_documento=f'CONT-CNAB-001-{i:03d}'
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
        from financeiro.models import Parcela, StatusBoleto

        service = CNABService()
        parcela = Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
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
        from financeiro.models import Parcela, StatusBoleto

        # API retorna conteúdo CNAB bruto (text/plain), não JSON+base64
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'ARQUIVO REMESSA TESTE CNAB240\n'
        mock_post.return_value = mock_response

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
            pago=False
        )[:3])

        resultado = service.gerar_remessa(parcelas, self.conta_bancaria)

        self.assertTrue(resultado['sucesso'])
        self.assertIn('arquivo_remessa', resultado)
        self.assertEqual(resultado['quantidade_boletos'], len(parcelas))

    @patch('requests.post')
    def test_gerar_remessa_erro_api_retorna_falha(self, mock_post):
        """Testa geração de remessa com erro HTTP da API — deve retornar sucesso=False"""
        from financeiro.models import Parcela, StatusBoleto

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
            pago=False
        )[:2])

        resultado = service.gerar_remessa(parcelas, self.conta_bancaria)

        self.assertFalse(resultado['sucesso'])
        self.assertIn('erro', resultado)

    @patch('requests.post')
    def test_gerar_remessa_api_indisponivel_retorna_falha(self, mock_post):
        """Testa que ConnectionError com API retorna sucesso=False com mensagem de erro"""
        from financeiro.models import Parcela, StatusBoleto
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError()

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
            pago=False
        )[:2])

        resultado = service.gerar_remessa(parcelas, self.conta_bancaria)

        self.assertFalse(resultado['sucesso'])
        self.assertIn('erro', resultado)

    @patch('requests.post')
    def test_gerar_remessa_usa_multipart_form_data(self, mock_post):
        """Regressão: API /api/remessa exige multipart (files+data), não JSON body.

        Antes do fix a chamada usava json={...} e a API retornava
        HTTP 400 "data is invalid". Este teste garante que as chamadas
        usam files={'data': ...} + data={'bank':..., 'type':...}.
        """
        from financeiro.models import Parcela, StatusBoleto

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'ARQUIVO REMESSA\n'
        mock_post.return_value = mock_response

        service = CNABService()
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
            pago=False
        )[:1])

        service.gerar_remessa(parcelas, self.conta_bancaria, layout='CNAB_240')

        self.assertTrue(mock_post.called)
        _, kwargs = mock_post.call_args

        # Deve usar multipart/form-data, não JSON body
        self.assertNotIn('json', kwargs, 'gerar_remessa não deve usar json={...}')
        self.assertIn('files', kwargs, 'gerar_remessa deve usar files={...}')
        self.assertIn('data', kwargs, 'gerar_remessa deve usar data={...}')

        # files deve conter 'data' como arquivo JSON
        self.assertIn('data', kwargs['files'])
        filename, content, content_type = kwargs['files']['data']
        self.assertEqual(content_type, 'application/json')

        # data deve conter bank e type
        self.assertIn('bank', kwargs['data'])
        self.assertIn('type', kwargs['data'])
        self.assertEqual(kwargs['data']['bank'], 'banco_brasil')
        self.assertEqual(kwargs['data']['type'], 'cnab240')

    @patch('requests.post')
    def test_regenerar_remessa_preserva_itens_em_falha(self, mock_post):
        """Regressão: regenerar_remessa NÃO deve deletar ItemRemessa se API falhar.

        Antes do fix, itens.delete() era chamado ANTES da API. Se a API
        falhasse, o ArquivoRemessa ficava sem nenhum ItemRemessa.
        """
        from financeiro.models import (
            Parcela, StatusBoleto, ArquivoRemessa, ItemRemessa,
            StatusArquivoRemessa,
        )
        from decimal import Decimal

        # Criar ArquivoRemessa existente (simula remessa anterior com sucesso)
        parcelas = list(Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
            pago=False
        )[:2])
        arquivo = ArquivoRemessa.objects.create(
            conta_bancaria=self.conta_bancaria,
            numero_remessa=1,
            layout='CNAB_240',
            nome_arquivo='remessa_teste.REM',
            quantidade_boletos=len(parcelas),
            valor_total=Decimal('1000.00'),
        )
        for p in parcelas:
            ItemRemessa.objects.create(
                arquivo_remessa=arquivo,
                parcela=p,
                nosso_numero=p.nosso_numero,
                valor=p.valor_boleto or p.valor_atual or Decimal('500.00'),
                data_vencimento=p.data_vencimento,
            )
        itens_count_antes = arquivo.itens.count()
        self.assertEqual(itens_count_antes, len(parcelas))

        # API falha com 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        service = CNABService()
        resultado = service.regenerar_remessa(arquivo)

        self.assertFalse(resultado['sucesso'])

        # Itens devem estar PRESERVADOS, arquivo deve estar em ERRO
        arquivo.refresh_from_db()
        self.assertEqual(arquivo.status, StatusArquivoRemessa.ERRO)
        self.assertEqual(arquivo.itens.count(), itens_count_antes,
                         'ItemRemessa não deve ser deletado quando API falha')

    def test_obter_boletos_sem_remessa(self):
        """Testa obtenção de boletos sem remessa"""
        from financeiro.models import Parcela, StatusBoleto

        service = CNABService()

        # Atualizar parcelas para ter status de boleto gerado
        Parcela.objects.filter(
            contrato=self.contrato,
            status_boleto=StatusBoleto.GERADO,
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
        from financeiro.models import Parcela, ContaBancaria

        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Retorno',
            razao_social='Contabilidade Retorno LTDA',
            cnpj='44444444000144',
            endereco='Rua Retorno, 100',
            telefone='(31) 3333-0044',
            email='retorno@contabilidade.com',
            responsavel='Responsável Retorno',
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Retorno',
            cnpj='55555555000155',
            telefone='(31) 3333-0055',
            email='retorno@imobiliaria.com',
            responsavel_financeiro='Responsável Financeiro Retorno',
        )

        cls.comprador = Comprador.objects.create(
            nome='Comprador Retorno',
            tipo_pessoa='PF',
            cpf='666.666.666-68',
            telefone='(31) 3333-0066',
            celular='(31) 99999-0066',
            email='retorno@comprador.com',
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-RET-001',
            area='360.00',
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-RET-001',
            data_contrato=date.today() - timedelta(days=60),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('50000.00'),
            valor_entrada=Decimal('5000.00'),
            numero_parcelas=12,
            dia_vencimento=15,
            tipo_correcao=TipoCorrecao.IPCA,
            status=StatusContrato.ATIVO
        )

        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            descricao='Conta Retorno',
            banco='001',
            agencia='5678',
            conta='98765-4',
            convenio='9876543',
            carteira='17'
        )

        # Criar parcela com nosso_numero específico (high number to avoid UNIQUE conflicts)
        from financeiro.models import StatusBoleto
        cls.parcela = Parcela.objects.create(
            contrato=cls.contrato,
            numero_parcela=100,
            data_vencimento=date.today() - timedelta(days=15),
            valor_original=Decimal('3750.00'),
            valor_atual=Decimal('3750.00'),
            valor_boleto=Decimal('3750.00'),
            ciclo_reajuste=1,
            pago=False,
            status_boleto=StatusBoleto.GERADO,
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
        """Testa processamento de retorno com liquidação CNAB 400 via API BRCobrança"""
        from financeiro.models import ArquivoRetorno, StatusArquivoRetorno

        arquivo_retorno = ArquivoRetorno.objects.create(
            conta_bancaria=self.conta_bancaria,
            nome_arquivo='CB0601.RET',
            status=StatusArquivoRetorno.PENDENTE
        )

        header = '0' + ''.ljust(399)
        detalhe = self._criar_linha_retorno_cnab400(
            nosso_numero=self.parcela.nosso_numero,
            codigo_ocorrencia='06',
            valor_titulo=Decimal('3750.00'),
            valor_pago=Decimal('3750.00')
        )
        trailer = '9' + ''.ljust(399)
        conteudo = f"{header}\n{detalhe}\n{trailer}"

        arquivo_retorno.arquivo.save(
            'CB0601.RET',
            ContentFile(conteudo.encode('latin-1')),
            save=True
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'retornos': [
                {
                    'nosso_numero': self.parcela.nosso_numero,
                    'codigo_ocorrencia': '06',
                    'valor_titulo': '3750.00',
                    'valor_pago': '3750.00',
                    'data_ocorrencia': '2026-06-01',
                    'data_credito': '2026-06-01',
                }
            ]
        }

        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_response):
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
            razao_social='Contabilidade 240 LTDA',
            cnpj='77777777000177',
            endereco='Rua 240, 100',
            telefone='(31) 3333-0077',
            email='cnab240@contabilidade.com',
            responsavel='Responsável 240',
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária 240',
            cnpj='88888888000188',
            telefone='(31) 3333-0088',
            email='cnab240@imobiliaria.com',
            responsavel_financeiro='Responsável Financeiro 240',
        )

        cls.comprador = Comprador.objects.create(
            nome='Comprador 240',
            tipo_pessoa='PF',
            cpf='999.999.999-97',
            telefone='(31) 3333-0099',
            celular='(31) 99999-0099',
            email='cnab240@comprador.com',
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-240-001',
            area='360.00',
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-240-001',
            data_contrato=date.today() - timedelta(days=90),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('80000.00'),
            valor_entrada=Decimal('8000.00'),
            numero_parcelas=36,
            dia_vencimento=20,
            tipo_correcao=TipoCorrecao.IGPM,
            status=StatusContrato.ATIVO
        )

        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            descricao='Conta 240',
            banco='237',  # Bradesco
            agencia='9999',
            conta='88888-9',
            convenio='0987654',
            carteira='09'
        )

        from financeiro.models import StatusBoleto
        cls.parcela = Parcela.objects.create(
            contrato=cls.contrato,
            numero_parcela=100,
            data_vencimento=date.today() - timedelta(days=10),
            valor_original=Decimal('2000.00'),
            valor_atual=Decimal('2000.00'),
            valor_boleto=Decimal('2000.00'),
            ciclo_reajuste=1,
            pago=False,
            status_boleto=StatusBoleto.GERADO,
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

        CNABService()

        # Ler arquivo e verificar tamanho da linha
        arquivo_retorno.arquivo.seek(0)
        conteudo = arquivo_retorno.arquivo.read().decode('latin-1')
        linhas = conteudo.split('\n')

        # Linha deve ter 240 caracteres (sem \n, com padding de espaços)
        self.assertEqual(len(linhas[0]), 240)


class TestRegenerarRemessa(TestCase):
    """Testes para regeneração de remessa"""

    @classmethod
    def setUpTestData(cls):
        """Configura dados para todos os testes"""
        from core.models import Contabilidade, Imobiliaria, Comprador, Imovel
        from contratos.models import Contrato, TipoCorrecao, StatusContrato
        from financeiro.models import ContaBancaria

        cls.contabilidade = Contabilidade.objects.create(
            nome='Contabilidade Regen',
            razao_social='Contabilidade Regen LTDA',
            cnpj='10101010000110',
            endereco='Rua Regen, 100',
            telefone='(31) 3333-0101',
            email='regen@contabilidade.com',
            responsavel='Responsável Regen',
        )

        cls.imobiliaria = Imobiliaria.objects.create(
            contabilidade=cls.contabilidade,
            nome='Imobiliária Regen',
            cnpj='20202020000120',
            telefone='(31) 3333-0202',
            email='regen@imobiliaria.com',
            responsavel_financeiro='Responsável Financeiro Regen',
        )

        cls.comprador = Comprador.objects.create(
            nome='Comprador Regen',
            tipo_pessoa='PF',
            cpf='303.030.303-03',
            telefone='(31) 3333-0303',
            celular='(31) 99999-0303',
            email='regen@comprador.com',
        )

        cls.imovel = Imovel.objects.create(
            imobiliaria=cls.imobiliaria,
            identificacao='LOTE-REG-001',
            area='360.00',
        )

        cls.contrato = Contrato.objects.create(
            imobiliaria=cls.imobiliaria,
            comprador=cls.comprador,
            imovel=cls.imovel,
            numero_contrato='CONT-REG-001',
            data_contrato=date.today() - timedelta(days=45),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('60000.00'),
            valor_entrada=Decimal('6000.00'),
            numero_parcelas=18,
            dia_vencimento=5,
            tipo_correcao=TipoCorrecao.FIXO,
            status=StatusContrato.ATIVO
        )

        cls.conta_bancaria = ContaBancaria.objects.create(
            imobiliaria=cls.imobiliaria,
            descricao='Conta Regen',
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
            status=StatusArquivoRemessa.ENVIADO
        )

        service = CNABService()
        resultado = service.regenerar_remessa(arquivo_remessa)

        self.assertFalse(resultado['sucesso'])
        self.assertIn('status', resultado['erro'].lower())
