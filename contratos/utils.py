"""
Utilitarios para o app contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from datetime import date, timedelta
from calendar import monthrange
from typing import Optional, List, Tuple


# Feriados nacionais fixos (dia, mes)
FERIADOS_FIXOS = [
    (1, 1),    # Ano Novo
    (21, 4),   # Tiradentes
    (1, 5),    # Dia do Trabalhador
    (7, 9),    # Independencia
    (12, 10),  # Nossa Senhora Aparecida
    (2, 11),   # Finados
    (15, 11),  # Proclamacao da Republica
    (25, 12),  # Natal
]


def calcular_pascoa(ano: int) -> date:
    """
    Calcula a data da Pascoa para um determinado ano.
    Algoritmo de Gauss.

    Args:
        ano: Ano para calcular

    Returns:
        Data da Pascoa
    """
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    mes = (h + L - 7 * m + 114) // 31
    dia = ((h + L - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def obter_feriados_ano(ano: int) -> List[date]:
    """
    Retorna lista de feriados nacionais de um ano.

    Args:
        ano: Ano para obter feriados

    Returns:
        Lista de datas de feriados
    """
    feriados = []

    # Feriados fixos
    for dia, mes in FERIADOS_FIXOS:
        feriados.append(date(ano, mes, dia))

    # Feriados moveis (baseados na Pascoa)
    pascoa = calcular_pascoa(ano)

    # Carnaval (47 dias antes da Pascoa - segunda e terca)
    carnaval_terca = pascoa - timedelta(days=47)
    carnaval_segunda = pascoa - timedelta(days=48)
    feriados.extend([carnaval_segunda, carnaval_terca])

    # Sexta-feira Santa (2 dias antes da Pascoa)
    sexta_santa = pascoa - timedelta(days=2)
    feriados.append(sexta_santa)

    # Corpus Christi (60 dias apos a Pascoa)
    corpus_christi = pascoa + timedelta(days=60)
    feriados.append(corpus_christi)

    return sorted(feriados)


def eh_dia_util(data: date, feriados: Optional[List[date]] = None) -> bool:
    """
    Verifica se uma data e dia util (nao e fim de semana nem feriado).

    Args:
        data: Data a verificar
        feriados: Lista de feriados (opcional, calcula se nao informado)

    Returns:
        True se for dia util
    """
    # Fim de semana (sabado=5, domingo=6)
    if data.weekday() >= 5:
        return False

    # Feriados
    if feriados is None:
        feriados = obter_feriados_ano(data.year)

    return data not in feriados


def ajustar_data_vencimento(
    dia_desejado: int,
    mes: int,
    ano: int,
    ajustar_feriado: bool = True,
    ajustar_fim_semana: bool = True
) -> Tuple[date, str]:
    """
    Ajusta a data de vencimento considerando:
    - Meses com menos dias que o dia desejado
    - Feriados nacionais
    - Fins de semana

    Item 2.3 do Roadmap: Ajuste de vencimento para meses com menos dias + feriados.

    Args:
        dia_desejado: Dia desejado para vencimento (1-31)
        mes: Mes
        ano: Ano
        ajustar_feriado: Se True, ajusta para proximo dia util se cair em feriado
        ajustar_fim_semana: Se True, ajusta para proximo dia util se cair em fim de semana

    Returns:
        Tuple (data_ajustada, motivo_ajuste ou None)
    """
    # Obter ultimo dia do mes
    ultimo_dia_mes = monthrange(ano, mes)[1]

    # Ajustar se o dia desejado nao existe no mes
    dia_real = min(dia_desejado, ultimo_dia_mes)
    motivo = None

    if dia_real < dia_desejado:
        motivo = f'Dia {dia_desejado} ajustado para {dia_real} (ultimo dia do mes)'

    data_vencimento = date(ano, mes, dia_real)

    # Obter feriados do ano
    feriados = obter_feriados_ano(ano)

    # Ajustar para proximo dia util se necessario
    ajustes = []
    while True:
        ajustado = False

        # Verificar fim de semana
        if ajustar_fim_semana and data_vencimento.weekday() >= 5:
            dia_semana = 'sabado' if data_vencimento.weekday() == 5 else 'domingo'
            ajustes.append(f'cai em {dia_semana}')
            data_vencimento += timedelta(days=1)
            ajustado = True
            continue

        # Verificar feriado
        if ajustar_feriado and data_vencimento in feriados:
            ajustes.append('cai em feriado')
            data_vencimento += timedelta(days=1)
            ajustado = True
            # Atualizar feriados se mudou de ano
            if data_vencimento.year != ano:
                feriados = obter_feriados_ano(data_vencimento.year)
            continue

        if not ajustado:
            break

    if ajustes:
        motivo_ajuste = ', '.join(ajustes)
        if motivo:
            motivo = f'{motivo}; {motivo_ajuste}'
        else:
            motivo = f'Data ajustada: {motivo_ajuste}'

    return data_vencimento, motivo


def proximo_dia_util(data: date) -> date:
    """
    Retorna o proximo dia util a partir de uma data.

    Args:
        data: Data inicial

    Returns:
        Proximo dia util
    """
    feriados = obter_feriados_ano(data.year)
    while not eh_dia_util(data, feriados):
        data += timedelta(days=1)
        if data.year != data.year:
            feriados = obter_feriados_ano(data.year)
    return data


def dias_uteis_entre(data_inicio: date, data_fim: date) -> int:
    """
    Conta os dias uteis entre duas datas.

    Args:
        data_inicio: Data inicial
        data_fim: Data final

    Returns:
        Numero de dias uteis
    """
    if data_inicio > data_fim:
        return 0

    feriados = set()
    for ano in range(data_inicio.year, data_fim.year + 1):
        feriados.update(obter_feriados_ano(ano))

    dias = 0
    data = data_inicio
    while data <= data_fim:
        if eh_dia_util(data, list(feriados)):
            dias += 1
        data += timedelta(days=1)

    return dias
