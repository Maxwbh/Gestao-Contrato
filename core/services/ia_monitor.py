"""
Monitor de uso e custo das APIs de IA.

Registra cada chamada com tokens consumidos e custo estimado em USD.
Falha silenciosamente para nunca interromper o fluxo principal.

checar_limite() é a exceção: levanta LimiteUsoIAExcedido quando um
limite mensal configurado é atingido — isso deve bloquear a chamada.
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Preço por milhão de tokens (USD) — (input/MTok, output/MTok)
_PRECOS: dict[str, tuple[float, float]] = {
    'claude-haiku-4-5-20251001': (0.80,   4.00),
    'claude-sonnet-4-6':         (3.00,  15.00),
    'claude-opus-4-7':           (15.00, 75.00),
    'gemini-2.0-flash':          (0.0,    0.0),   # free tier
    'gemini-1.5-flash':          (0.075,  0.30),
    'gemini-1.5-pro':            (1.25,   5.00),
}

PROVIDER_ANTHROPIC = 'ANTHROPIC'
PROVIDER_GOOGLE = 'GOOGLE'

OP_IMPORTACAO_PDF   = 'IMPORTACAO_PDF'
OP_CHATBOT_INTENT   = 'CHATBOT_INTENT'
OP_CHATBOT_HUMANIZE = 'CHATBOT_HUMANIZE'

# Cache em memória para cotação USD/BRL (evita chamada à API a cada requisição)
_cotacao_cache: dict = {}


class LimiteUsoIAExcedido(Exception):
    """Levantada quando um limite mensal de uso de IA é atingido."""


def calcular_custo(modelo: str, tokens_input: int, tokens_output: int) -> Decimal:
    preco_in, preco_out = _PRECOS.get(modelo, (0.0, 0.0))
    custo = (tokens_input * preco_in + tokens_output * preco_out) / 1_000_000
    return Decimal(str(round(custo, 6)))


def get_cotacao_usd_brl() -> float:
    """
    Retorna cotação USD→BRL.
    Ordem: cache em memória → ParametroSistema (cache diário) → AwesomeAPI → fallback 5.80.
    """
    from datetime import date
    hoje = date.today().isoformat()

    if _cotacao_cache.get('data') == hoje:
        return _cotacao_cache['valor']

    # Tenta cache persistido em ParametroSistema
    try:
        from core.parametros import get_param
        salvo = get_param('_COTACAO_USD_BRL_CACHE', '')
        if salvo and '|' in salvo:
            data_salva, val_str = salvo.split('|', 1)
            if data_salva == hoje:
                val = float(val_str)
                _cotacao_cache.update({'data': hoje, 'valor': val})
                return val
    except Exception:
        pass

    # Busca na AwesomeAPI (gratuita, sem autenticação)
    try:
        import urllib.request
        import json as _json
        req = urllib.request.Request(
            'https://economia.awesomeapi.com.br/json/last/USD-BRL',
            headers={'User-Agent': 'gestao-contrato/1.0'},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = _json.loads(resp.read())
        val = float(data['USDBRL']['bid'])
        _salvar_cotacao_cache(hoje, val)
        logger.info('ia_monitor: cotação USD/BRL atualizada: %.4f', val)
        return val
    except Exception as exc:
        logger.debug('ia_monitor: cotação USD/BRL indisponível (%s) — usando 5.80', exc)

    fallback = 5.80
    _cotacao_cache.update({'data': hoje, 'valor': fallback})
    return fallback


def _salvar_cotacao_cache(hoje: str, val: float) -> None:
    _cotacao_cache.update({'data': hoje, 'valor': val})
    try:
        from core.models import ParametroSistema
        ParametroSistema.objects.update_or_create(
            chave='_COTACAO_USD_BRL_CACHE',
            defaults={
                'valor': f'{hoje}|{val}',
                'tipo': 'str',
                'grupo': 'aplicacao',
                'descricao': 'Cache interno — cotação USD/BRL (atualizado diariamente)',
            },
        )
    except Exception:
        pass


def inicio_periodo(periodo: str):
    """Retorna a data de início do período atual para o código de período dado."""
    from datetime import date, timedelta
    hoje = date.today()
    if periodo == 'DIARIO':
        return hoje
    if periodo == 'SEMANAL':
        return hoje - timedelta(days=hoje.weekday())  # segunda-feira da semana atual
    if periodo == 'QUINZENAL':
        return hoje.replace(day=1) if hoje.day <= 15 else hoje.replace(day=16)
    if periodo == 'MENSAL':
        return hoje.replace(day=1)
    if periodo == 'BIMESTRAL':
        mes_inicio = ((hoje.month - 1) // 2) * 2 + 1
        return date(hoje.year, mes_inicio, 1)
    if periodo == 'SEMESTRAL':
        return date(hoje.year, 1, 1) if hoje.month <= 6 else date(hoje.year, 7, 1)
    if periodo == 'ANUAL':
        return date(hoje.year, 1, 1)
    return hoje.replace(day=1)  # fallback → mensal


def consumo_periodo(
    periodo: str = 'MENSAL',
    modelo: str = '',
    operacao: str = '',
    tipo_limite: str = 'TOKENS',
) -> float:
    """Retorna o consumo acumulado no período atual para o escopo dado."""
    from core.models import RegistroUsoIA
    from django.db.models import Sum

    inicio = inicio_periodo(periodo)
    qs = RegistroUsoIA.objects.filter(criado_em__date__gte=inicio)
    if modelo:
        qs = qs.filter(modelo=modelo)
    if operacao:
        qs = qs.filter(operacao=operacao)

    if tipo_limite == 'TOKENS':
        totais = qs.aggregate(ti=Sum('tokens_input'), to=Sum('tokens_output'))
        return float((totais['ti'] or 0) + (totais['to'] or 0))
    else:  # REAIS
        totais = qs.aggregate(custo=Sum('custo_usd'))
        return float(totais['custo'] or 0) * get_cotacao_usd_brl()


def consumo_mes(modelo: str = '', operacao: str = '', tipo_limite: str = 'TOKENS') -> float:
    """Compat: consumo do mês corrente. Use consumo_periodo() para outros períodos."""
    return consumo_periodo('MENSAL', modelo=modelo, operacao=operacao, tipo_limite=tipo_limite)


def checar_limite(modelo: str = '', operacao: str = '') -> None:
    """
    Verifica os limites ativos para o modelo e/ou operação.
    Cada limite usa seu próprio período de reset.
    Múltiplos limites para o mesmo escopo são todos avaliados — o mais
    restritivo bloqueia. Levanta LimiteUsoIAExcedido se algum for atingido.
    Não propaga outras exceções — erros de DB são ignorados silenciosamente.
    """
    try:
        from core.models import LimiteUsoIA
        from django.db.models import Q

        filtros = Q()
        if modelo:
            filtros |= Q(tipo_escopo=LimiteUsoIA.ESCOPO_MODELO, escopo_valor=modelo)
        if operacao:
            filtros |= Q(tipo_escopo=LimiteUsoIA.ESCOPO_OPERACAO, escopo_valor=operacao)
        if not filtros:
            return

        limites = list(LimiteUsoIA.objects.filter(ativo=True).filter(filtros))
    except LimiteUsoIAExcedido:
        raise
    except Exception as exc:
        logger.debug('ia_monitor.checar_limite: erro ao consultar limites (%s) — ignorado', exc)
        return

    for lim in limites:
        if lim.tipo_escopo == LimiteUsoIA.ESCOPO_MODELO:
            atual = consumo_periodo(
                lim.periodo, modelo=lim.escopo_valor, tipo_limite=lim.tipo_limite,
            )
        else:
            atual = consumo_periodo(
                lim.periodo, operacao=lim.escopo_valor, tipo_limite=lim.tipo_limite,
            )

        if atual >= float(lim.valor_limite):
            unidade = 'tokens' if lim.tipo_limite == 'TOKENS' else 'R$'
            raise LimiteUsoIAExcedido(
                f'Limite atingido: {lim.get_tipo_escopo_display()} "{lim.escopo_valor}" '
                f'({lim.get_periodo_display()}) — '
                f'{atual:.2f}/{float(lim.valor_limite):.2f} {unidade}'
            )


def registrar(
    *,
    provider: str,
    modelo: str,
    operacao: str,
    tokens_input: int,
    tokens_output: int,
    usuario=None,
    contrato_importacao=None,
) -> None:
    """Persiste um registro de uso de IA. Falha silenciosamente."""
    try:
        from core.models import RegistroUsoIA
        RegistroUsoIA.objects.create(
            provider=provider,
            modelo=modelo,
            operacao=operacao,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            custo_usd=calcular_custo(modelo, tokens_input, tokens_output),
            usuario=usuario,
            contrato_importacao=contrato_importacao,
        )
    except Exception as exc:
        logger.warning('ia_monitor.registrar falhou: %s', exc)
