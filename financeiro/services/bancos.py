"""
Tabela canônica de bancos suportados pela integração BRCobrança.

Fonte única de verdade — qualquer banco fora desta tabela NÃO pode
gerar boleto nem arquivo de remessa CNAB no sistema. Para adicionar
suporte a um novo banco, basta incluir aqui.

Coluna layouts_cnab: layouts de REMESSA suportados pelo BRCobrança para
cada banco (fonte: github.com/kivanio/brcobranca — pastas remessa/cnab240
e remessa/cnab400). Bancos com tuple vazia não possuem implementação de
remessa, apenas boleto avulso.
"""

BANCOS_SUPORTADOS: dict[str, dict] = {
    # cod:  brcobranca_id          nome                          layouts_cnab remessa
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
