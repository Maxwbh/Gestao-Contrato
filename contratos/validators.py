"""
Validadores de regras de negocio para contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from decimal import Decimal
from django.core.exceptions import ValidationError


def validar_soma_intermediarias(contrato):
    """
    Valida que a soma das prestacoes intermediarias nao excede o valor financiado.

    Regra de negocio: O valor total das intermediarias nao pode ultrapassar
    o valor financiado (valor_total - valor_entrada), pois isso resultaria
    em parcelas normais com valor zero ou negativo.

    Args:
        contrato: Instancia do modelo Contrato

    Raises:
        ValidationError: Se a soma exceder o valor financiado
    """
    if not hasattr(contrato, 'intermediarias'):
        return

    soma_intermediarias = sum(
        inter.valor for inter in contrato.intermediarias.all()
    )

    valor_financiado = contrato.valor_financiado or (
        contrato.valor_total - contrato.valor_entrada
    )

    # Margem de tolerancia: intermediarias podem representar ate 80% do financiado
    # para garantir que as parcelas normais tenham valor significativo
    limite_intermediarias = valor_financiado * Decimal('0.80')

    if soma_intermediarias > limite_intermediarias:
        raise ValidationError({
            'intermediarias': (
                f'A soma das prestacoes intermediarias (R$ {soma_intermediarias:,.2f}) '
                f'excede 80% do valor financiado (R$ {limite_intermediarias:,.2f}). '
                f'Valor financiado: R$ {valor_financiado:,.2f}.'
            )
        })


def validar_dia_vencimento(dia_vencimento):
    """
    Valida e alerta sobre o dia de vencimento recomendado.

    Regra de negocio: Dias entre 1 e 28 sao recomendados para evitar
    problemas com meses que tem menos de 31 dias (fevereiro, abril, etc.).

    Args:
        dia_vencimento: Dia do mes (1-31)

    Returns:
        tuple: (valido: bool, aviso: str ou None)
    """
    if not dia_vencimento:
        return False, 'Dia de vencimento e obrigatorio'

    if dia_vencimento < 1 or dia_vencimento > 31:
        return False, 'Dia de vencimento deve estar entre 1 e 31'

    if dia_vencimento > 28:
        return True, (
            f'Atencao: O dia {dia_vencimento} pode causar ajustes automaticos '
            f'em meses com menos dias (ex: fevereiro). '
            f'Recomendamos usar dias entre 1 e 28.'
        )

    return True, None


def validar_valor_minimo_pagamento(valor_pagamento, valor_minimo=Decimal('0.01')):
    """
    Valida que o valor do pagamento nao e menor que o minimo permitido.

    Regra de negocio: Nao permite pagamentos com valor menor que o minimo
    estabelecido para evitar pagamentos insignificantes que gerem custos
    administrativos maiores que o valor recebido.

    Args:
        valor_pagamento: Valor do pagamento em Decimal
        valor_minimo: Valor minimo permitido (padrao R$ 0.01)

    Raises:
        ValidationError: Se o valor for menor que o minimo
    """
    if valor_pagamento < valor_minimo:
        raise ValidationError({
            'valor_pago': (
                f'O valor do pagamento (R$ {valor_pagamento:,.2f}) '
                f'nao pode ser menor que R$ {valor_minimo:,.2f}.'
            )
        })


def calcular_percentual_intermediarias(contrato):
    """
    Calcula o percentual do valor financiado representado pelas intermediarias.

    Args:
        contrato: Instancia do modelo Contrato

    Returns:
        dict: Informacoes sobre as intermediarias
    """
    if not hasattr(contrato, 'intermediarias'):
        return {
            'soma_intermediarias': Decimal('0.00'),
            'valor_financiado': contrato.valor_financiado,
            'percentual': Decimal('0.00'),
            'dentro_limite': True
        }

    soma_intermediarias = sum(
        inter.valor for inter in contrato.intermediarias.all()
    ) or Decimal('0.00')

    valor_financiado = contrato.valor_financiado or Decimal('0.01')
    percentual = (soma_intermediarias / valor_financiado) * 100

    return {
        'soma_intermediarias': soma_intermediarias,
        'valor_financiado': valor_financiado,
        'percentual': percentual,
        'dentro_limite': percentual <= Decimal('80.00'),
        'limite_disponivel': (valor_financiado * Decimal('0.80')) - soma_intermediarias
    }
