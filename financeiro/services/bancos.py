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
# Fonte: github.com/Maxwbh/brcobranca (v12.8.0+) — registry Brcobranca::Bancos
# e boleto_cnab_api v1.3.0 (C6 336 com CNAB 400, PIX híbrido em 8 bancos)
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
    '336': {'brcobranca_id': 'banco_c6',    'nome': 'C6 Bank',                'layouts_cnab': ('CNAB_400',)},
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


# ── Validação de campos da conta por banco (BRCobrança) ───────────────────────
# Fonte: docs/api/BRCOBRANCA_CAMPOS_REFERENCIA.md (brcobrança v12.8.1).
# Comprimentos referem-se ao NÚMERO (sem o dígito verificador), em semântica
# 'max' (compatível com a validação anterior do formulário). 'valores' restringe
# a carteira a um conjunto que o próprio BRCobrança valida na inclusão.
CAMPOS_BANCO_VALIDACAO: dict[str, dict] = {
    '001': {'agencia': {'max': 4}, 'conta': {'max': 8}, 'carteira': {'max': 2}},
    '033': {'agencia': {'max': 4}, 'conta': {'max': 9}},
    '041': {'agencia': {'max': 4}, 'conta': {'max': 9}, 'carteira': {'max': 1}},
    '104': {'agencia': {'max': 4}, 'carteira': {'max': 1}},
    '136': {'carteira': {'max': 2}},
    '237': {'agencia': {'max': 4}, 'conta': {'max': 7}, 'carteira': {'max': 2}},
    '336': {'agencia': {'max': 4}, 'conta': {'max': 8}, 'carteira': {'valores': ('10', '20')}},
    '341': {'agencia': {'max': 4}, 'conta': {'max': 5}},
    '748': {'agencia': {'max': 4}, 'conta': {'max': 5}, 'carteira': {'max': 1}},
    '756': {'agencia': {'max': 4}, 'conta': {'max': 8}, 'carteira': {'valores': ('1', '3', '9')}},
}

_ROTULO_CAMPO = {'agencia': 'a agência', 'conta': 'a conta', 'carteira': 'a carteira'}


def _digitos_numero(valor: str) -> str:
    """Parte numérica (sem DV) de um campo '1234-5' / '1234 5' / '1234/5' → '1234'."""
    if not valor:
        return ''
    s = valor.strip()
    for sep in ('-', ' ', '/'):
        if sep in s:
            s = s.split(sep, 1)[0]
            break
    return ''.join(ch for ch in s if ch.isdigit())


def _erro_tamanho(qtd_digitos: int, regra: dict, rotulo: str, banco_nome: str) -> str | None:
    if 'exato' in regra and qtd_digitos != regra['exato']:
        return f"Para {banco_nome}, {rotulo} deve ter exatamente {regra['exato']} dígitos (tem {qtd_digitos})."
    if 'max' in regra and qtd_digitos > regra['max']:
        return f"Para {banco_nome}, {rotulo} deve ter no máximo {regra['max']} dígitos (tem {qtd_digitos})."
    if 'min' in regra and qtd_digitos < regra['min']:
        return f"Para {banco_nome}, {rotulo} deve ter no mínimo {regra['min']} dígitos (tem {qtd_digitos})."
    return None


def validar_campos_conta(codigo: str, *, agencia: str = '', conta: str = '',
                         carteira: str = '') -> dict[str, str]:
    """
    Valida agência, conta e carteira conforme as regras do banco na BRCobrança.

    Comprimentos consideram só o número (DV é descartado). Banco fora da tabela
    não impõe restrições.

    Returns:
        dict {campo: mensagem} — vazio quando tudo válido. Chaves possíveis:
        'agencia', 'conta', 'carteira'.
    """
    regras = CAMPOS_BANCO_VALIDACAO.get(codigo)
    if not regras:
        return {}

    banco_nome = nome(codigo)
    erros: dict[str, str] = {}

    for campo, valor in (('agencia', agencia), ('conta', conta)):
        regra = regras.get(campo)
        if not regra:
            continue
        digitos = _digitos_numero(valor)
        if not digitos:
            continue  # presença/obrigatoriedade é tratada à parte
        msg = _erro_tamanho(len(digitos), regra, _ROTULO_CAMPO[campo], banco_nome)
        if msg:
            erros[campo] = msg

    regra_cart = regras.get('carteira')
    cart = (carteira or '').strip()
    if regra_cart and cart:
        if 'valores' in regra_cart:
            if cart not in regra_cart['valores']:
                permitidos = ', '.join(regra_cart['valores'])
                erros['carteira'] = (
                    f"Para {banco_nome}, a carteira deve ser uma de: {permitidos}."
                )
        else:
            digitos = ''.join(ch for ch in cart if ch.isdigit())
            msg = _erro_tamanho(len(digitos), regra_cart, _ROTULO_CAMPO['carteira'], banco_nome)
            if msg:
                erros['carteira'] = msg

    return erros


def validar_layout_cnab(codigo: str, layout: str) -> str | None:
    """
    Valida que o banco suporta o layout de remessa escolhido (CNAB 240/400).

    Banco sem remessa CNAB (registro online — HU-23 RN-16) não restringe o
    layout (a conta simplesmente não entra em remessa). Retorna mensagem de
    erro ou None.
    """
    layouts = layouts_cnab(codigo)
    if not layouts:
        return None  # registro online; layout é irrelevante para este banco
    if layout and layout not in layouts:
        disponiveis = ', '.join(l.replace('_', ' ') for l in layouts)
        return (
            f"{nome(codigo)} não suporta {layout.replace('_', ' ')} na BRCobrança. "
            f"Layouts disponíveis: {disponiveis}."
        )
    return None


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
    Descobre bancos e layouts suportados via GET /api/bancos (endpoint dedicado).
    Fallback: probe individual por banco via /api/boleto/data e /api/remessa.

    Resultado é cacheado por _CACHE_TTL segundos.

    Returns:
        Lista de dicts: [{codigo, nome, brcobranca_id, suporta_boleto,
                          layouts_cnab: ['CNAB_240', ...]}, ...]
    """
    global _cache

    agora = time.monotonic()
    if usar_cache and _cache and (agora - _cache.get('ts', 0)) < _CACHE_TTL:
        return _cache['bancos']

    # Tenta endpoint dedicado /api/bancos (documentado no OpenAPI)
    try:
        resp = requests.get(
            f"{brcobranca_url}/api/bancos",
            headers={"Accept": "application/vnd.BoletoApi-v1+json"},
            timeout=10,
        )
        if resp.status_code == 200:
            resultado = []
            for item in resp.json():
                brc_id = item.get('banco', '')
                codigo = item.get('codigo', '')
                # Normaliza layouts CNAB a partir dos campos remessa/retorno da API
                remessa = item.get('remessa') or {}
                formatos = remessa.get('formatos') or []
                layouts: list[str] = []
                if 'cnab240' in formatos:
                    layouts.append('CNAB_240')
                if 'cnab400' in formatos:
                    layouts.append('CNAB_400')
                resultado.append({
                    'codigo': codigo,
                    'nome': item.get('nome', brc_id),
                    'brcobranca_id': brc_id,
                    'suporta_boleto': bool((item.get('boleto') or {}).get('suportado', True)),
                    'layouts_cnab': layouts,
                })
            _cache = {'bancos': resultado, 'ts': agora}
            logger.info("BRCobrança discovery via /api/bancos: %d bancos", len(resultado))
            return resultado
    except Exception as e:
        logger.debug("BRCobrança /api/bancos indisponível, usando probe: %s", e)

    # Fallback: probe individual por banco (API sem /api/bancos)
    resultado = []
    for codigo, spec in BANCOS_SUPORTADOS.items():
        brc_id = spec['brcobranca_id']

        suporta_boleto = _probe_boleto(brcobranca_url, brc_id)

        layouts = []
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
        logger.debug("probe banco=%s boleto=%s layouts=%s", codigo, suporta_boleto, layouts)

    _cache = {'bancos': resultado, 'ts': agora}
    logger.info("BRCobrança discovery por probe: %d bancos", len(resultado))
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
