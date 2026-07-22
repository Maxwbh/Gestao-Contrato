"""
Catálogo curado da API para o Swagger/Redoc.

A API do sistema é composta por *views* Django tradicionais (retornam
``JsonResponse``), não por *viewsets* do DRF — por isso o drf-spectacular não
consegue introspectá-las automaticamente e o schema nasceria vazio. Este módulo
descreve **manualmente** um subconjunto representativo e estável de endpoints e
os injeta no schema via *postprocessing hook* (``POSTPROCESSING_HOOKS``), para
que a documentação seja navegável sem converter toda a base para DRF.

Cada entrada segue o OpenAPI 3.0. Ao criar/alterar um endpoint relevante,
acrescente-o aqui — mantendo o catálogo enxuto e fiel ao comportamento real.
"""

# Autenticação por sessão Django (cookie). Referenciada por cada operação.
_SECURITY = [{'cookieAuth': []}]

_JSON_OK = {
    'description': 'Sucesso — objeto JSON.',
    'content': {'application/json': {'schema': {'type': 'object'}}},
}
_JSON_LIST = {
    'description': 'Sucesso — lista/coleção em JSON.',
    'content': {'application/json': {'schema': {'type': 'object'}}},
}
_UNAUTH = {'description': 'Não autenticado — redireciona para o login.'}
_NOT_FOUND = {'description': 'Recurso não encontrado.'}


def _slug(text):
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != '_':
            out.append('_')
    return ''.join(out).strip('_')


def _op(tag, summary, description, *, method='get', params=None,
        request=None, responses=None):
    """Monta uma operação OpenAPI com os campos comuns já preenchidos."""
    op = {
        'operationId': f'{method}_{_slug(tag)}_{_slug(summary)}',
        'tags': [tag],
        'summary': summary,
        'description': description,
        'security': _SECURITY,
        'responses': responses or {'200': _JSON_OK, '401': _UNAUTH},
    }
    if params:
        op['parameters'] = params
    if request is not None:
        op['requestBody'] = request
    return {method: op}


def _path_param(name, description, example=None):
    p = {
        'name': name, 'in': 'path', 'required': True,
        'description': description,
        'schema': {'type': 'string'},
    }
    if example is not None:
        p['example'] = example
    return p


def _json_body(description):
    return {
        'required': True,
        'content': {'application/json': {'schema': {'type': 'object'}}},
        'description': description,
    }


# Tag → descrição (ordem e textos exibidos no topo dos grupos).
CURATED_TAGS = [
    {'name': 'Utilidades', 'description': 'Consultas auxiliares de endereço e cadastro (CEP, CNPJ).'},
    {'name': 'Contas Bancárias', 'description': 'CRUD das contas bancárias da imobiliária (credenciais são cifradas e nunca retornadas).'},
    {'name': 'Conciliação', 'description': 'Indicadores de saúde da conciliação da cobrança registrada.'},
]

# path → { método: operação }
CURATED_PATHS = {
    # ---- Utilidades ----
    '/api/cep/{cep}/': _op(
        'Utilidades', 'Buscar endereço por CEP',
        'Retorna logradouro, bairro, cidade e UF a partir do CEP informado.',
        params=[_path_param('cep', 'CEP com 8 dígitos (com ou sem hífen).', '30140071')],
        responses={'200': _JSON_OK, '401': _UNAUTH, '404': _NOT_FOUND},
    ),
    '/api/cnpj/{cnpj}/': _op(
        'Utilidades', 'Buscar dados por CNPJ',
        'Retorna razão social, endereço e situação cadastral a partir do CNPJ.',
        params=[_path_param('cnpj', 'CNPJ com 14 dígitos (com ou sem máscara).', '12345678000199')],
        responses={'200': _JSON_OK, '401': _UNAUTH, '404': _NOT_FOUND},
    ),

    # ---- Contas Bancárias ----
    '/api/imobiliarias/{imobiliaria_id}/contas/': _op(
        'Contas Bancárias', 'Listar contas da imobiliária',
        'Lista as contas bancárias ativas de uma imobiliária (escopo por tenant).',
        params=[_path_param('imobiliaria_id', 'ID da imobiliária.', '1')],
        responses={'200': _JSON_LIST, '401': _UNAUTH},
    ),
    '/api/contas/': _op(
        'Contas Bancárias', 'Criar conta bancária',
        'Cria uma conta bancária. Para provedores C6/Sicoob, as credenciais são '
        'gravadas **cifradas** (Fernet) e o `tenant_id` interno é gerado '
        'automaticamente. Credenciais nunca são retornadas na leitura.',
        method='post',
        request=_json_body('Dados da conta: banco, agência, conta, provider, '
                           'account_config e (C6/Sicoob) credenciais.'),
        responses={'200': _JSON_OK, '401': _UNAUTH},
    ),
    '/api/contas/{conta_id}/': _op(
        'Contas Bancárias', 'Obter conta bancária',
        'Retorna os dados da conta. Segredos não são expostos — apenas as flags '
        '`tem_credenciais` e `tem_bapi_token`.',
        params=[_path_param('conta_id', 'ID da conta bancária.', '10')],
        responses={'200': _JSON_OK, '401': _UNAUTH, '404': _NOT_FOUND},
    ),
    '/api/contas/{conta_id}/atualizar/': _op(
        'Contas Bancárias', 'Atualizar conta bancária',
        'Atualiza a conta. Credenciais em branco preservam as já cadastradas.',
        method='post',
        params=[_path_param('conta_id', 'ID da conta bancária.', '10')],
        request=_json_body('Campos a atualizar (parciais).'),
        responses={'200': _JSON_OK, '401': _UNAUTH, '404': _NOT_FOUND},
    ),
    '/api/contas/{conta_id}/excluir/': _op(
        'Contas Bancárias', 'Excluir conta bancária',
        'Exclusão lógica (soft delete) da conta bancária.',
        method='post',
        params=[_path_param('conta_id', 'ID da conta bancária.', '10')],
        responses={'200': _JSON_OK, '401': _UNAUTH, '404': _NOT_FOUND},
    ),

    # ---- Conciliação ----
    '/financeiro/api/conciliacao/saude/': _op(
        'Conciliação', 'Saúde da conciliação',
        'Indicadores de conciliação da cobrança registrada: % conciliado, '
        'distribuição por status e recebido por origem (webhook, polling '
        'Sicoob, conciliação Pix, baixa manual), com escopo por tenant.',
        responses={'200': _JSON_OK, '401': _UNAUTH},
    ),
    '/financeiro/api/contas-bancarias/': _op(
        'Conciliação', 'Listar contas bancárias (financeiro)',
        'Lista as contas bancárias visíveis ao usuário logado, filtradas pelo '
        'seu escopo de acesso (tenant).',
        responses={'200': _JSON_LIST, '401': _UNAUTH},
    ),
}


def add_curated_paths(result, generator, request, public):
    """Postprocessing hook: injeta o catálogo curado e o esquema de segurança
    por cookie de sessão no schema gerado (que, sozinho, viria vazio)."""
    paths = result.setdefault('paths', {})
    for path, ops in CURATED_PATHS.items():
        # Não sobrescreve rotas que porventura já tenham sido introspectadas.
        paths.setdefault(path, {}).update(ops)

    # Esquema de segurança (sessão Django via cookie).
    components = result.setdefault('components', {})
    schemes = components.setdefault('securitySchemes', {})
    schemes.setdefault('cookieAuth', {
        'type': 'apiKey', 'in': 'cookie', 'name': 'sessionid',
        'description': 'Sessão autenticada do Django (login em `/accounts/login/`).',
    })

    # Tags com descrição, preservando eventuais já existentes.
    existentes = {t.get('name') for t in result.get('tags', [])}
    result.setdefault('tags', [])
    for t in CURATED_TAGS:
        if t['name'] not in existentes:
            result['tags'].append(t)

    return result
