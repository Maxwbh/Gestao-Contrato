"""
Testes para os validadores de CPF e CNPJ.
"""
import pytest
from django.core.exceptions import ValidationError
from core.validators import (
    validar_cpf, validar_cnpj, validar_cpf_cnpj,
    formatar_cpf, formatar_cnpj,
    gerar_cpf_valido, gerar_cnpj_valido
)


class TestValidarCPF:
    """Testes para validação de CPF."""

    def test_cpf_valido(self):
        """CPF válido não deve levantar exceção."""
        # CPF válido de teste (gerado com algoritmo correto)
        validar_cpf('52998224725')  # Sem formatação

    def test_cpf_valido_formatado(self):
        """CPF válido formatado não deve levantar exceção."""
        validar_cpf('529.982.247-25')  # Com formatação

    def test_cpf_invalido_digito_verificador(self):
        """CPF com dígito verificador errado deve falhar."""
        with pytest.raises(ValidationError, match='CPF inválido'):
            validar_cpf('52998224726')  # Último dígito errado

    def test_cpf_todos_digitos_iguais(self):
        """CPF com todos os dígitos iguais deve falhar."""
        with pytest.raises(ValidationError, match='CPF inválido'):
            validar_cpf('11111111111')

    def test_cpf_tamanho_incorreto(self):
        """CPF com tamanho incorreto deve falhar."""
        with pytest.raises(ValidationError, match='11 dígitos'):
            validar_cpf('1234567890')  # 10 dígitos

        with pytest.raises(ValidationError, match='11 dígitos'):
            validar_cpf('123456789012')  # 12 dígitos


class TestValidarCNPJ:
    """Testes para validação de CNPJ."""

    def test_cnpj_valido(self):
        """CNPJ válido não deve levantar exceção."""
        validar_cnpj('11222333000181')  # Sem formatação

    def test_cnpj_valido_formatado(self):
        """CNPJ válido formatado não deve levantar exceção."""
        validar_cnpj('11.222.333/0001-81')  # Com formatação

    def test_cnpj_invalido_digito_verificador(self):
        """CNPJ com dígito verificador errado deve falhar."""
        with pytest.raises(ValidationError, match='CNPJ inválido'):
            validar_cnpj('11222333000182')  # Último dígito errado

    def test_cnpj_todos_digitos_iguais(self):
        """CNPJ com todos os dígitos iguais deve falhar."""
        with pytest.raises(ValidationError, match='CNPJ inválido'):
            validar_cnpj('11111111111111')

    def test_cnpj_tamanho_incorreto(self):
        """CNPJ com tamanho incorreto deve falhar."""
        with pytest.raises(ValidationError, match='14 dígitos'):
            validar_cnpj('1122233300018')  # 13 dígitos

        with pytest.raises(ValidationError, match='14 dígitos'):
            validar_cnpj('112223330001810')  # 15 dígitos


class TestValidarCpfCnpj:
    """Testes para validação automática de CPF/CNPJ."""

    def test_detecta_cpf_automaticamente(self):
        """Deve detectar CPF pelo tamanho."""
        validar_cpf_cnpj('52998224725')  # 11 dígitos = CPF

    def test_detecta_cnpj_automaticamente(self):
        """Deve detectar CNPJ pelo tamanho."""
        validar_cpf_cnpj('11222333000181')  # 14 dígitos = CNPJ

    def test_valida_cpf_com_tipo(self):
        """Deve validar CPF quando tipo='PF'."""
        validar_cpf_cnpj('52998224725', tipo='PF')

    def test_valida_cnpj_com_tipo(self):
        """Deve validar CNPJ quando tipo='PJ'."""
        validar_cpf_cnpj('11222333000181', tipo='PJ')

    def test_tamanho_invalido(self):
        """Deve falhar com tamanho que não é CPF nem CNPJ."""
        with pytest.raises(ValidationError, match='CPF.*ou CNPJ'):
            validar_cpf_cnpj('12345678901234567')  # 17 dígitos


class TestFormatacao:
    """Testes para formatação de CPF e CNPJ."""

    def test_formatar_cpf(self):
        """Deve formatar CPF corretamente."""
        assert formatar_cpf('52998224725') == '529.982.247-25'

    def test_formatar_cnpj(self):
        """Deve formatar CNPJ corretamente."""
        assert formatar_cnpj('11222333000181') == '11.222.333/0001-81'

    def test_formatar_cpf_tamanho_errado(self):
        """Retorna sem formatação se tamanho incorreto."""
        assert formatar_cpf('1234') == '1234'

    def test_formatar_cnpj_tamanho_errado(self):
        """Retorna sem formatação se tamanho incorreto."""
        assert formatar_cnpj('1234') == '1234'


class TestGeracao:
    """Testes para geração de CPF e CNPJ válidos."""

    def test_gerar_cpf_valido(self):
        """CPF gerado deve ser válido."""
        cpf = gerar_cpf_valido()
        # Não deve levantar exceção
        validar_cpf(cpf)

    def test_gerar_cnpj_valido(self):
        """CNPJ gerado deve ser válido."""
        cnpj = gerar_cnpj_valido()
        # Não deve levantar exceção
        validar_cnpj(cnpj)

    def test_cpfs_gerados_sao_diferentes(self):
        """CPFs gerados devem ser diferentes entre si."""
        cpfs = {gerar_cpf_valido() for _ in range(10)}
        # Deve ter 10 CPFs únicos (ou quase)
        assert len(cpfs) >= 8

    def test_cnpjs_gerados_sao_diferentes(self):
        """CNPJs gerados devem ser diferentes entre si."""
        cnpjs = {gerar_cnpj_valido() for _ in range(10)}
        # Deve ter 10 CNPJs únicos (ou quase)
        assert len(cnpjs) >= 8
