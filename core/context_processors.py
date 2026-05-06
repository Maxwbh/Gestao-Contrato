"""
Context processors globais do sistema Gestão de Contratos.

Injeta em todos os templates:
  - system_version: versão completa (ex: "1.0.294")
  - page_id: código de 4 dígitos da página atual (ex: "1001")
"""
from .version import get_version

# Mapa de view_name → page_id de 4 dígitos
# Formato: 'app:view_name' ou 'view_name' para views sem namespace
PAGE_ID_MAP: dict[str, str] = {
    # ── Core / Imóveis ─────────────────────────────────────────────────────
    'core:imovel_list':             '0101',
    'core:loteamento_detalhe':      '0102',
    'core:imovel_detalhe':          '0103',
    'core:imovel_create':           '0104',
    'core:imovel_update':           '0105',

    # ── Contratos ──────────────────────────────────────────────────────────
    'contratos:listar':             '1001',
    'contratos:criar':              '1002',
    'contratos:editar':             '1003',
    'contratos:detalhe':            '1004',
    'contratos:excluir':            '1005',
    'contratos:parcelas':           '1006',
    'contratos:wizard':             '1007',
    'contratos:intermediarias_listar': '1010',
    'contratos:intermediarias_detalhe': '1011',
    'contratos:intermediarias_criar': '1012',
    'contratos:indices_listar':     '1020',
    'contratos:indices_criar':      '1021',
    'contratos:indices_editar':     '1022',

    # ── Financeiro — Dashboard ─────────────────────────────────────────────
    'financeiro:dashboard':         '2001',
    'financeiro:dashboard_imobiliaria': '2002',
    'financeiro:dashboard_contabilidade': '2003',

    # ── Financeiro — Parcelas ─────────────────────────────────────────────
    'financeiro:listar_parcelas':   '2101',
    'financeiro:detalhe_parcela':   '2102',
    'financeiro:registrar_pagamento': '2103',
    'financeiro:parcelas_mes':      '2104',

    # ── Financeiro — Boletos ──────────────────────────────────────────────
    'financeiro:visualizar_boleto': '2201',
    'financeiro:download_boleto':   '2202',
    'financeiro:segunda_via':       '2203',
    'financeiro:boleto_publico:visualizar': '2204',

    # ── Financeiro — CNAB / Remessa ────────────────────────────────────────
    'financeiro:listar_remessas':   '2301',
    'financeiro:detalhe_remessa':   '2302',
    'financeiro:gerar_remessa':     '2303',
    'financeiro:download_remessa':  '2304',

    # ── Financeiro — CNAB / Retorno ───────────────────────────────────────
    'financeiro:listar_retornos':   '2401',
    'financeiro:detalhe_retorno':   '2402',
    'financeiro:upload_retorno':    '2403',
    'financeiro:download_retorno':  '2404',

    # ── Financeiro — Relatórios ────────────────────────────────────────────
    'financeiro:relatorio_prestacoes': '2501',
    'financeiro:conciliacao':       '2502',

    # ── Notificações ──────────────────────────────────────────────────────
    'notificacoes:listar_notificacoes': '3001',
    'notificacoes:listar_templates': '3002',
    'notificacoes:criar_template':  '3003',
    'notificacoes:editar_template': '3004',
    'notificacoes:listar_regras':   '3005',
    'notificacoes:config_email':    '3010',
    'notificacoes:config_whatsapp': '3011',

    # ── Portal do Comprador ────────────────────────────────────────────────
    'portal_comprador:dashboard':   '4001',
    'portal_comprador:parcelas':    '4002',
    'portal_comprador:boleto':      '4003',

    # ── Admin Django ──────────────────────────────────────────────────────
    'admin:index':                  '9001',
}


def system_info(request) -> dict:
    """Injeta versão do sistema e ID da página em todos os templates."""
    view_name = ''
    try:
        if request.resolver_match:
            namespace = request.resolver_match.namespace
            url_name = request.resolver_match.url_name
            view_name = f'{namespace}:{url_name}' if namespace else url_name
    except Exception:
        pass

    return {
        'system_version': get_version(),
        'page_id': PAGE_ID_MAP.get(view_name, '0000'),
        'page_view_name': view_name,
    }
