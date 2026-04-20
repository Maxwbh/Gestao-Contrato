"""
Tabela canônica de bancos suportados pela integração BRCobrança.

Fonte única de verdade — qualquer banco fora desta tabela NÃO pode
gerar boleto nem arquivo de remessa CNAB no sistema. Para adicionar
suporte a um novo banco, basta incluir aqui.
"""

BANCOS_SUPORTADOS: dict[str, dict[str, str]] = {
    '001': {'brcobranca_id': 'banco_brasil',   'nome': 'Banco do Brasil'},
    '004': {'brcobranca_id': 'banco_nordeste', 'nome': 'Banco do Nordeste - BNB'},
    '021': {'brcobranca_id': 'banestes',       'nome': 'Banestes'},
    '033': {'brcobranca_id': 'santander',      'nome': 'Santander'},
    '041': {'brcobranca_id': 'banrisul',       'nome': 'Banrisul'},
    '070': {'brcobranca_id': 'brb',            'nome': 'BRB - Banco de Brasília'},
    '077': {'brcobranca_id': 'banco_inter',    'nome': 'Banco Inter'},
    '085': {'brcobranca_id': 'ailos',          'nome': 'Cecred / Ailos'},
    '097': {'brcobranca_id': 'credisis',       'nome': 'Credisis'},
    '104': {'brcobranca_id': 'caixa',          'nome': 'Caixa Econômica Federal'},
    '133': {'brcobranca_id': 'cresol',         'nome': 'Cresol'},
    '136': {'brcobranca_id': 'unicred',        'nome': 'Unicred'},
    '212': {'brcobranca_id': 'banco_original', 'nome': 'Banco Original'},
    '237': {'brcobranca_id': 'bradesco',       'nome': 'Bradesco'},
    '260': {'brcobranca_id': 'nubank',         'nome': 'Nubank'},
    '341': {'brcobranca_id': 'itau',           'nome': 'Itaú'},
    '389': {'brcobranca_id': 'banco_mercantil','nome': 'Mercantil do Brasil'},
    '399': {'brcobranca_id': 'hsbc',           'nome': 'HSBC'},
    '422': {'brcobranca_id': 'safra',          'nome': 'Safra'},
    '655': {'brcobranca_id': 'votorantim',     'nome': 'Votorantim'},
    '748': {'brcobranca_id': 'sicredi',        'nome': 'Sicredi'},
    '756': {'brcobranca_id': 'sicoob',         'nome': 'Sicoob'},
}


def nome(codigo: str) -> str:
    """Nome legível do banco pelo código. Retorna o código se não suportado."""
    spec = BANCOS_SUPORTADOS.get(codigo)
    return spec['nome'] if spec else (codigo or '—')


def brcobranca_id(codigo: str) -> str | None:
    """Identificador do banco no BRCobrança, ou None se não suportado."""
    spec = BANCOS_SUPORTADOS.get(codigo)
    return spec['brcobranca_id'] if spec else None


def suportado(codigo: str) -> bool:
    """True se o banco pode gerar boleto/remessa via BRCobrança."""
    return codigo in BANCOS_SUPORTADOS
