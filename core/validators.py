"""
Validadores customizados para o sistema de Gestão de Contratos

Inclui validação completa de CPF e CNPJ com dígitos verificadores.
Suporta o novo formato alfanumérico de CNPJ (IN RFB nº 2229/2024, vigente 2026):
  posições 1-12 → alfanumérico (0-9, A-Z); posições 13-14 → dígitos verificadores numéricos.
  Valores para cálculo: dígitos mantêm valor numérico, letras A=17 … Z=42.
"""
from django.core.exceptions import ValidationError
import re

# Valor numérico de cada caractere válido de CNPJ no cálculo dos dígitos verificadores
_CNPJ_CHAR_VALUES: dict[str, int] = {str(i): i for i in range(10)}
_CNPJ_CHAR_VALUES.update({chr(ord('A') + i): 17 + i for i in range(26)})


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
    Valida CNPJ brasileiro (formato clássico numérico e novo formato alfanumérico 2026).

    Args:
        cnpj: CNPJ a ser validado (pode conter formatação XX.XXX.XXX/XXXX-XX)

    Raises:
        ValidationError: Se o CNPJ for inválido
    """
    cnpj = re.sub(r'[^0-9A-Za-z]', '', cnpj).upper()

    if len(cnpj) != 14:
        raise ValidationError('CNPJ deve conter 14 caracteres.')

    if cnpj == cnpj[0] * 14:
        raise ValidationError('CNPJ inválido.')

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    soma = sum(_CNPJ_CHAR_VALUES.get(cnpj[i], 0) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cnpj[12]) != digito1:
        raise ValidationError('CNPJ inválido.')

    soma = sum(_CNPJ_CHAR_VALUES.get(cnpj[i], 0) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    if int(cnpj[13]) != digito2:
        raise ValidationError('CNPJ inválido.')


def validar_cpf_cnpj(valor: str, tipo: str = None) -> None:
    """
    Valida CPF ou CNPJ baseado no tipo ou tamanho.
    Suporta CNPJ alfanumérico 2026 (posições 1-12 podem ter letras).

    Args:
        valor: CPF ou CNPJ a ser validado
        tipo: 'PF' para CPF, 'PJ' para CNPJ, None para detectar automaticamente

    Raises:
        ValidationError: Se o documento for inválido
    """
    digits_only = re.sub(r'[^0-9]', '', valor)
    alnum_only = re.sub(r'[^0-9A-Za-z]', '', valor)

    # Check CNPJ first: 14 alphanumeric chars covers both classic (all digits) and 2026 (letters+digits)
    if tipo == 'PJ' or (tipo is None and len(alnum_only) == 14):
        validar_cnpj(valor)
    elif tipo == 'PF' or (tipo is None and len(digits_only) == 11):
        validar_cpf(valor)
    else:
        raise ValidationError('Documento deve ser CPF (11 dígitos) ou CNPJ (14 caracteres).')


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
    Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX (suporta alfanumérico 2026).

    Args:
        cnpj: CNPJ com ou sem formatação (dígitos ou alfanumérico)

    Returns:
        CNPJ formatado
    """
    cnpj = re.sub(r'[^0-9A-Za-z]', '', cnpj).upper()
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
