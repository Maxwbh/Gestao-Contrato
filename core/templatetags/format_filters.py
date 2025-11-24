"""
Template filters para formatacao de valores monetarios e numeros

Uso nos templates:
    {% load format_filters %}
    {{ valor|moeda }}          -> R$ 1.234,56
    {{ valor|moeda_sem_rs }}   -> 1.234,56
    {{ valor|numero_br }}      -> 1.234,56
"""
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def moeda(valor):
    """
    Formata valor como moeda brasileira: R$ 1.234,56
    """
    if valor is None:
        return 'R$ 0,00'

    try:
        valor = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return 'R$ 0,00'

    # Formatar com separador de milhar e decimal brasileiro
    valor_formatado = '{:,.2f}'.format(valor)
    # Trocar , por X, depois . por , e X por .
    valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')

    return f'R$ {valor_formatado}'


@register.filter
def moeda_sem_rs(valor):
    """
    Formata valor sem o R$: 1.234,56
    """
    if valor is None:
        return '0,00'

    try:
        valor = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return '0,00'

    valor_formatado = '{:,.2f}'.format(valor)
    valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')

    return valor_formatado


@register.filter
def numero_br(valor, casas_decimais=2):
    """
    Formata numero no formato brasileiro: 1.234,56
    """
    if valor is None:
        return '0,00'

    try:
        valor = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return '0,00'

    formato = '{:,.' + str(casas_decimais) + 'f}'
    valor_formatado = formato.format(valor)
    valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')

    return valor_formatado


@register.filter
def percentual(valor):
    """
    Formata percentual: 12,34%
    """
    if valor is None:
        return '0,00%'

    try:
        valor = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return '0,00%'

    valor_formatado = '{:.2f}'.format(valor).replace('.', ',')

    return f'{valor_formatado}%'
