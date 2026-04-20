"""
Tabela de bancos suportados pela integração BRCobrança.

Fonte primária: discovery via API do boleto_cnab_api (probe dinâmico).
Fallback estático: tabela abaixo (sincronizada com kivanio/brcobrança).

Uso:
    from financeiro.services import bancos
    lista = await bancos.obter_bancos(brcobranca_url)  # via API
    print(bancos.nome('104'))   # Caixa Econômica Federal
    print(bancos.layouts_cnab('001'))  # ('CNAB_240', 'CNAB_400')
"""

import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

# ── Tabela estática (fallback quando BRCobrança indisponível) ─────────────────
# Fonte: github.com/kivanio/brcobrança — pastas remessa/cnab240 e remessa/cnab400
BANCOS_SUPORTADOS: dict[str, dict] = {
    '001': {'brcobranca_id': 'banco_brasil',   'nome': 'Banco do Brasil',        'layouts_cnab': ('CNAB_240', 'CNAB_400')},
    '004': {'brcobranca_id': 'banco_nordeste', 'nome': 'Banco do Nordeste - BNB','layouts_cnab': ('CNAB_400',)},
    '021': {'brcobranca_id': 'banestes',       'nome': 'Banestes',               'layouts_cnab': ()},
    '033': {'brcobranca_id': 'santander',      'nome': 'Santander',              'layouts_cnab': ('CNAB_240', 'CNAB_400')},
    '041': {'brcobranca_id': 'banrisul',       'nome': 'Banrisul',               'layouts_cnab': ('CNAB_400',)},
    '070': {'brcobranca_id': 'brb',            'nome': 'BRB - Banco de Brasília','layouts_cnab': ('CNAB_400',)},
    '077': {'brcobranca_id': 'banco_inter',    'nome': 'Banco Inter',            'layouts_cnab': ()},
    '085': {'brcobranca_id': 'ailos',          'nome': 'Cecred / Ailos',         'layouts_cnab': ('CNAB_240',)},
    '097': {'brcobranca_id': 'credisis',       'nome': 'Credisis',               'layouts_cnab': ('CNAB_400',)},
    '104': {'brcobranca_id': 'caixa',          'nome': 'Caixa Econômica Federal','layouts_cnab': ('CNAB_240',)},
    '133': {'brcobranca_id': 'cresol',         'nome': 'Cresol',                 'layouts_cnab': ()},
    '136': {'brcobranca_id': 'unicred',        'nome': 'Unicred',                'layouts_cnab': ('CNAB_240', 'CNAB_400')},
    '212': {'brcobranca_id': 'banco_original', 'nome': 'Banco Original',         'layouts_cnab': ()},
    '237': {'brcobranca_id': 'bradesco',       'nome': 'Bradesco',               'layouts_cnab': ('CNAB_400',)},
    '260': {'brcobranca_id': 'nubank',         'nome': 'Nubank',                 'layouts_cnab': ()},
    '341': {'brcobranca_id': 'itau',           'nome': 'Itaú',                   'layouts_cnab': ('CNAB_400',)},
    '389': {'brcobranca_id': 'banco_mercantil','nome': 'Mercantil do Brasil',     'layouts_cnab': ()},
    '399': {'brcobranca_id': 'hsbc',           'nome': 'HSBC',                   'layouts_cnab': ()},
    '422': {'brcobranca_id': 'safra',          'nome': 'Safra',                  'layouts_cnab': ()},
    '655': {'brcobranca_id': 'votorantim',     'nome': 'Votorantim',             'layouts_cnab': ()},
    '748': {'brcobranca_id': 'sicredi',        'nome': 'Sicredi',                'layouts_cnab': ('CNAB_240',)},
    '756': {'brcobranca_id': 'sicoob',         'nome': 'Sicoob',                 'layouts_cnab': ('CNAB_240', 'CNAB_400')},
}

# ── Cache em memória do resultado do probe (ttl 60 min) ───────────────────────
_cache: dict = {}           # {'bancos': [...], 'ts': float}
_CACHE_TTL = 3600           # segundos


# ── Helpers (operam sobre a tabela estática) ──────────────────────────────────

def nome(codigo: str) -> str:
    """Nome legível do banco pelo código. Retorna o código se não suportado."""
    spec = BANCOS_SUPORTADOS.get(codigo)
    return spec['nome'] if spec else (codigo or '—')


def brcobranca_id(codigo: str) -> str | None:
    """Identificador do banco no BRCobrança, ou None se não suportado."""
    spec = BANCOS_SUPORTADOS.get(codigo)
    return spec['brcobranca_id'] if spec else None


def layouts_cnab(codigo: str) -> tuple:
    """Layouts de remessa CNAB suportados pelo banco na BRCobrança."""
    spec = BANCOS_SUPORTADOS.get(codigo)
    return spec['layouts_cnab'] if spec else ()


def suporta_cnab(codigo: str, layout: str) -> bool:
    """True se o banco suporta o layout de remessa específico."""
    return layout in layouts_cnab(codigo)


def suportado(codigo: str) -> bool:
    """True se o banco está na integração BRCobrança."""
    return codigo in BANCOS_SUPORTADOS


# ── Discovery via API ─────────────────────────────────────────────────────────

_STUB_BOLETO = {
    "nosso_numero": "1",
    "valor": "1.00",
    "cedente": "Teste",
    "sacado": "Teste",
    "sacado_documento": "00000000000",
    "sacado_endereco": "Rua Teste",
    "cedente_documento": "00000000000000",
    "agencia": "0001",
    "conta_corrente": "00001",
    "carteira": "1",
    "data_vencimento": "2099/12/31",
    "data_documento": "2024/01/01",
}

_STUB_EMPRESA = {
    "empresa_mae": "Teste",
    "documento_cedente": "00000000000000",
    "agencia": "0001",
    "agencia_dv": "0",
    "conta_corrente": "00001",
    "digito_conta": "0",
    "convenio": "000001",
    "carteira": "1",
    "sequencial_remessa": 1,
    "codigo_cedente": "000001",
}

# Frases nas mensagens de erro da BRCobrança que indicam que o banco NÃO é
# reconhecido (vs. erros de validação de dados onde o banco É reconhecido).
_ERROS_BANCO_DESCONHECIDO = (
    "uninitialized constant",
    "undefined method",
    "not supported",
    "bank not found",
    "banco nao suportado",
    "invalid bank",
)


def _banco_reconhecido_por_resposta(resp_text: str) -> bool:
    """
    Distingue erro de 'banco desconhecido' de 'dados inválidos mas banco OK'.
    Retorna True se o banco é reconhecido (mesmo que os dados estejam errados).
    """
    lower = resp_text.lower()
    return not any(p in lower for p in _ERROS_BANCO_DESCONHECIDO)


def _probe_boleto(brcobranca_url: str, brc_id: str, timeout: int = 5) -> bool:
    """
    Testa se o banco é suportado para boleto via GET /api/boleto/data.
    Retorna True se o banco é reconhecido pela BRCobrança.
    """
    try:
        resp = requests.get(
            f"{brcobranca_url}/api/boleto/data",
            params={"bank": brc_id, "data": json.dumps(_STUB_BOLETO)},
            headers={"Accept": "application/vnd.BoletoApi-v1+json"},
            timeout=timeout,
        )
        return _banco_reconhecido_por_resposta(resp.text)
    except Exception:
        return False


def _probe_remessa(brcobranca_url: str, brc_id: str, formato: str, timeout: int = 5) -> bool:
    """
    Testa se o banco/layout é suportado para remessa via POST /api/remessa.
    Retorna True se o banco+formato é reconhecido pela BRCobrança.
    """
    try:
        payload = {"banco": brc_id, "formato": formato, "pagamentos": [], **_STUB_EMPRESA}
        resp = requests.post(
            f"{brcobranca_url}/api/remessa",
            json=payload,
            timeout=timeout,
        )
        return _banco_reconhecido_por_resposta(resp.text)
    except Exception:
        return False


def descobrir_bancos(brcobranca_url: str, usar_cache: bool = True) -> list[dict]:
    """
    Descobre bancos e layouts suportados consultando a API BRCobrança.

    Para cada banco em BANCOS_SUPORTADOS:
      - Proba GET /api/boleto/data para verificar suporte a boleto
      - Proba POST /api/remessa com cnab240 e cnab400 para verificar remessa

    Resultado é cacheado por _CACHE_TTL segundos para evitar probes repetidos.

    Returns:
        Lista de dicts: [{codigo, nome, brcobranca_id, suporta_boleto,
                          layouts_cnab: ['CNAB_240', ...]}, ...]
    """
    global _cache

    agora = time.monotonic()
    if usar_cache and _cache and (agora - _cache.get('ts', 0)) < _CACHE_TTL:
        return _cache['bancos']

    resultado = []
    for codigo, spec in BANCOS_SUPORTADOS.items():
        brc_id = spec['brcobranca_id']

        suporta_boleto = _probe_boleto(brcobranca_url, brc_id)

        layouts: list[str] = []
        for fmt, key in [('cnab240', 'CNAB_240'), ('cnab400', 'CNAB_400')]:
            if _probe_remessa(brcobranca_url, brc_id, fmt):
                layouts.append(key)

        resultado.append({
            'codigo': codigo,
            'nome': spec['nome'],
            'brcobranca_id': brc_id,
            'suporta_boleto': suporta_boleto,
            'layouts_cnab': layouts,
        })
        logger.debug(
            "probe banco=%s boleto=%s layouts=%s", codigo, suporta_boleto, layouts
        )

    _cache = {'bancos': resultado, 'ts': agora}
    logger.info("BRCobrança discovery concluído: %d bancos", len(resultado))
    return resultado


def descobrir_bancos_fallback(brcobranca_url: str | None = None) -> list[dict]:
    """
    Tenta discovery via API; se BRCobrança estiver indisponível usa fallback estático.
    """
    if brcobranca_url:
        try:
            r = requests.get(f"{brcobranca_url}/", timeout=3)
            if r.status_code in (200, 404, 405):
                return descobrir_bancos(brcobranca_url)
        except Exception:
            pass

    logger.warning("BRCobrança indisponível — usando tabela estática de bancos")
    return [
        {
            'codigo': cod,
            'nome': spec['nome'],
            'brcobranca_id': spec['brcobranca_id'],
            'suporta_boleto': True,
            'layouts_cnab': list(spec['layouts_cnab']),
        }
        for cod, spec in BANCOS_SUPORTADOS.items()
    ]
