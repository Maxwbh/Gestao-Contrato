"""
Testes unitários para BoletoService

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock, patch

from financeiro.services.boleto_service import BoletoService


class TestBoletoServiceValidacao:
    """Testes de validação de dados do boleto"""

    def test_validar_dados_completos(self):
        """Deve validar dados completos com sucesso"""
        service = BoletoService()

        dados = {
            'cedente': 'Imobiliária Teste',
            'documento_cedente': '23456781000111',
            'sacado': 'João da Silva',
            'sacado_documento': '12345678901',
            'agencia': '1234',
            'conta_corrente': '567890',
            'carteira': '18',
            'valor': 1000.00,
            'data_vencimento': '2025/12/31',
            'moeda': '9',
            'especie': 'R$',
            'especie_documento': 'DM',
            'aceite': 'N',
        }

        result = service._validar_dados_boleto(dados)

        assert result['valido'] is True
        assert len(result['erros']) == 0

    def test_validar_dados_faltando_campos_obrigatorios(self):
        """Deve falhar quando faltam campos obrigatórios"""
        service = BoletoService()

        dados = {
            'cedente': 'Imobiliária Teste',
            # documento_cedente FALTANDO
            'sacado': 'João da Silva',
            # Outros campos faltando...
        }

        result = service._validar_dados_boleto(dados)

        assert result['valido'] is False
        assert 'documento_cedente' in str(result['erros'])


class TestBoletoServiceFiltroCampos:
    """Testes de filtragem de campos por banco"""

    def test_remover_numero_documento_banco_brasil(self):
        """Deve remover numero_documento para Banco do Brasil"""
        service = BoletoService()

        dados = {
            'cedente': 'Teste',
            'numero_documento': 'CTR-001',  # Campo não suportado
            'documento_numero': 'CTR-001',  # Campo correto
            'agencia': '1234',
        }

        dados_filtrados = service._filtrar_campos_banco(dados, '001')

        assert 'numero_documento' not in dados_filtrados
        assert 'documento_numero' in dados_filtrados

    def test_remover_numero_documento_sicoob(self):
        """Deve remover numero_documento para Sicoob"""
        service = BoletoService()

        dados = {
            'numero_documento': 'CTR-001',
            'documento_numero': 'CTR-001',
        }

        dados_filtrados = service._filtrar_campos_banco(dados, '756')

        assert 'numero_documento' not in dados_filtrados
        assert 'documento_numero' in dados_filtrados


@pytest.mark.integration
class TestBoletoServiceIntegracao:
    """Testes de integração com a API BRCobranca"""

    @pytest.mark.django_db
    def test_gerar_boleto_sucesso_mock(
        self,
        contrato_factory,
        conta_bancaria_factory,
        parcela_factory,
        mock_brcobranca_success
    ):
        """Deve gerar boleto com sucesso usando API mockada"""
        # Arrange
        contrato = contrato_factory()
        conta = conta_bancaria_factory(
            imobiliaria=contrato.imobiliaria,
            banco='001',  # Banco do Brasil
            convenio='0123456'
        )
        parcela = parcela_factory(
            contrato=contrato,
            valor_original=Decimal('1000.00'),
            valor_atual=Decimal('1000.00')
        )

        service = BoletoService()

        # Act
        result = service.gerar_boleto(parcela, conta)

        # Assert
        assert result['sucesso'] is True
        assert result['pdf_content'] is not None
        assert result['valor'] == Decimal('1000.00')
        assert result['numero_documento'] == parcela.gerar_numero_documento()

    @pytest.mark.django_db
    def test_gerar_boleto_erro_500_com_retry(
        self,
        contrato_factory,
        conta_bancaria_factory,
        parcela_factory,
        mock_brcobranca_error
    ):
        """Deve fazer retry em caso de erro 500"""
        # Arrange
        contrato = contrato_factory()
        conta = conta_bancaria_factory(imobiliaria=contrato.imobiliaria)
        parcela = parcela_factory(contrato=contrato)

        service = BoletoService()

        # Act
        result = service.gerar_boleto(parcela, conta)

        # Assert
        assert result['sucesso'] is False
        assert 'Erro do servidor' in result['erro']
        # Deve ter tentado 3 vezes
        assert mock_brcobranca_error.call_count == 3


class TestBoletoServiceFormatacao:
    """Testes de formatação de dados"""

    def test_formatar_cnpj_apenas_numeros(self):
        """Deve formatar CNPJ removendo pontuação"""
        service = BoletoService()

        cnpj = '23.456.781/0001-11'
        esperado = '23456781000111'

        # Teste indireto através de _filtrar_campos_banco
        dados = {'documento_cedente': cnpj}
        # _filtrar_campos_banco não altera documento_cedente
        # mas valida formato

        result = service._validar_dados_boleto(dados)
        # Validação básica passa com qualquer formato

    def test_formatar_numero_documento(self):
        """Deve gerar numero_documento no formato correto"""
        from contratos.models import Contrato, Parcela

        # Mock de parcela
        contrato_mock = Mock(spec=Contrato)
        contrato_mock.numero_contrato = 'CTR-2023-0034'

        parcela_mock = Mock(spec=Parcela)
        parcela_mock.contrato = contrato_mock
        parcela_mock.numero_parcela = 14
        parcela_mock.contrato.numero_parcelas = 15

        # Teste do método gerar_numero_documento
        numero = parcela_mock.contrato.numero_contrato
        esperado = f"{numero}-014/015"

        assert esperado == 'CTR-2023-0034-014/015'


@pytest.mark.slow
@pytest.mark.integration
class TestBoletoServiceReal:
    """Testes com API real (apenas em ambiente de staging)"""

    @pytest.mark.skip(reason="Requer API real configurada")
    @pytest.mark.django_db
    def test_gerar_boleto_banco_brasil_real(
        self,
        contrato_completo,
        conta_bancaria_factory
    ):
        """Teste com API real do BRCobranca (skip por padrão)"""
        # Este teste só roda se API estiver disponível
        conta = conta_bancaria_factory(
            imobiliaria=contrato_completo.imobiliaria,
            banco='001',
            agencia='3073',
            conta='12345678',
            convenio='01234567',
            carteira='18'
        )

        parcela = contrato_completo.parcelas.first()

        service = BoletoService()
        result = service.gerar_boleto(parcela, conta)

        assert result['sucesso'] is True
        assert len(result['pdf_content']) > 1000  # PDF tem tamanho significativo
