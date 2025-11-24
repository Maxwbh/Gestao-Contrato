"""
Validadores customizados para o sistema de Gestão de Contratos

Inclui validação completa de CPF e CNPJ com dígitos verificadores.
"""
from django.core.exceptions import ValidationError
import re


def validar_cpf(cpf: str) -> None:
    """
    Valida CPF brasileiro com verificação de dígitos verificadores.

    Args:
        cpf: CPF a ser validado (pode conter formatação)

    Raises:
        ValidationError: Se o CPF for inválido
    """
    # Remove formatação
    cpf = re.sub(r'[^0-9]', '', cpf)

    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        raise ValidationError('CPF deve conter 11 dígitos.')

    # Verifica se todos os dígitos são iguais (CPFs inválidos conhecidos)
    if cpf == cpf[0] * 11:
        raise ValidationError('CPF inválido.')

    # Calcula primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cpf[9]) != digito1:
        raise ValidationError('CPF inválido.')

    # Calcula segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    if int(cpf[10]) != digito2:
        raise ValidationError('CPF inválido.')


def validar_cnpj(cnpj: str) -> None:
    """
    Valida CNPJ brasileiro com verificação de dígitos verificadores.

    Args:
        cnpj: CNPJ a ser validado (pode conter formatação)

    Raises:
        ValidationError: Se o CNPJ for inválido
    """
    # Remove formatação
    cnpj = re.sub(r'[^0-9]', '', cnpj)

    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        raise ValidationError('CNPJ deve conter 14 dígitos.')

    # Verifica se todos os dígitos são iguais (CNPJs inválidos conhecidos)
    if cnpj == cnpj[0] * 14:
        raise ValidationError('CNPJ inválido.')

    # Pesos para cálculo dos dígitos verificadores
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    # Calcula primeiro dígito verificador
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cnpj[12]) != digito1:
        raise ValidationError('CNPJ inválido.')

    # Calcula segundo dígito verificador
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    if int(cnpj[13]) != digito2:
        raise ValidationError('CNPJ inválido.')


def validar_cpf_cnpj(valor: str, tipo: str = None) -> None:
    """
    Valida CPF ou CNPJ baseado no tipo ou tamanho.

    Args:
        valor: CPF ou CNPJ a ser validado
        tipo: 'PF' para CPF, 'PJ' para CNPJ, None para detectar automaticamente

    Raises:
        ValidationError: Se o documento for inválido
    """
    # Remove formatação
    valor_limpo = re.sub(r'[^0-9]', '', valor)

    if tipo == 'PF' or (tipo is None and len(valor_limpo) == 11):
        validar_cpf(valor)
    elif tipo == 'PJ' or (tipo is None and len(valor_limpo) == 14):
        validar_cnpj(valor)
    else:
        raise ValidationError('Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos).')


def formatar_cpf(cpf: str) -> str:
    """
    Formata CPF no padrão XXX.XXX.XXX-XX

    Args:
        cpf: CPF apenas com dígitos

    Returns:
        CPF formatado
    """
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11:
        return cpf
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def formatar_cnpj(cnpj: str) -> str:
    """
    Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX

    Args:
        cnpj: CNPJ apenas com dígitos

    Returns:
        CNPJ formatado
    """
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'


def gerar_cpf_valido() -> str:
    """
    Gera um CPF válido aleatório (para testes).

    Returns:
        CPF válido formatado
    """
    import random

    # Gera 9 primeiros dígitos
    cpf = [random.randint(0, 9) for _ in range(9)]

    # Calcula primeiro dígito verificador
    soma = sum(cpf[i] * (10 - i) for i in range(9))
    resto = soma % 11
    cpf.append(0 if resto < 2 else 11 - resto)

    # Calcula segundo dígito verificador
    soma = sum(cpf[i] * (11 - i) for i in range(10))
    resto = soma % 11
    cpf.append(0 if resto < 2 else 11 - resto)

    return formatar_cpf(''.join(map(str, cpf)))


def gerar_cnpj_valido() -> str:
    """
    Gera um CNPJ válido aleatório (para testes).

    Returns:
        CNPJ válido formatado
    """
    import random

    # Gera 12 primeiros dígitos
    cnpj = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]

    # Pesos para cálculo
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    # Calcula primeiro dígito verificador
    soma = sum(cnpj[i] * pesos1[i] for i in range(12))
    resto = soma % 11
    cnpj.append(0 if resto < 2 else 11 - resto)

    # Calcula segundo dígito verificador
    soma = sum(cnpj[i] * pesos2[i] for i in range(13))
    resto = soma % 11
    cnpj.append(0 if resto < 2 else 11 - resto)

    return formatar_cnpj(''.join(map(str, cnpj)))
