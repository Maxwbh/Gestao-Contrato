"""
Paridade por banco no BRCobrança (HU-03 / HU-23).

Trava de consistência entre as três tabelas que precisam andar juntas:

1. core.models.BancoBrasil          — bancos selecionáveis na ContaBancaria
2. financeiro.services.bancos.BANCOS_SUPORTADOS
                                     — bancos que o BRCobrança GERA boleto (HU-03)
3. layouts_cnab por banco (na mesma tabela)
                                     — bancos que o BRCobrança monta REMESSA (HU-23)

Qualquer drift entre elas quebra estes testes, forçando uma decisão consciente
(ex.: adicionar um banco ao seletor sem suporte de geração, ou um banco com
boleto mas sem layout de remessa — ver HU-23 RN-16).
"""
from core.models import BancoBrasil, LayoutCNAB
from financeiro.services import bancos
from financeiro.services.boleto_service import BoletoService

# Códigos do seletor de ContaBancaria que o BRCobrança NÃO gera boleto.
# Selecionáveis na UI mas sem integração — geração falharia em runtime.
# Documentado como Item de Atenção em REVISAO_TECNICA_HUS.md (parity gap).
SELECIONAVEIS_SEM_SUPORTE_BRCOBRANCA = frozenset({
    '084', '089', '208', '213', '246', '274', '637', '707',
    '290', '323', '197', '461', '000',
})

# Bancos com integração de boleto mas que NÃO constam no seletor de ContaBancaria.
SUPORTADOS_NAO_SELECIONAVEIS = frozenset({'097', '212', '655'})

# Bancos que GERAM boleto mas NÃO têm layout de remessa CNAB (layouts_cnab vazio).
# Registro só via API/online → não entram em remessa (HU-23 RN-16).
BOLETO_SEM_REMESSA_CNAB = frozenset({
    '021', '077', '133', '212', '260', '389', '399', '422', '655',
})

_LAYOUTS_VALIDOS = {LayoutCNAB.CNAB_240, LayoutCNAB.CNAB_400, LayoutCNAB.CNAB_444}


def _codigos_choices(choices_cls):
    return {valor for valor, _ in choices_cls.choices}


def test_layouts_cnab_sao_valores_validos():
    """Todo layout declarado por banco é um LayoutCNAB válido."""
    for codigo, spec in bancos.BANCOS_SUPORTADOS.items():
        for layout in spec['layouts_cnab']:
            assert layout in _LAYOUTS_VALIDOS, (
                f"banco {codigo} declara layout inválido: {layout}"
            )


def test_brcobranca_id_e_nome_preenchidos():
    """Toda entrada suportada tem brcobranca_id e nome não-vazios."""
    for codigo, spec in bancos.BANCOS_SUPORTADOS.items():
        assert spec['brcobranca_id'], f"banco {codigo} sem brcobranca_id"
        assert spec['nome'], f"banco {codigo} sem nome"


def test_boleto_service_deriva_da_tabela_unica():
    """BoletoService.BANCOS_BRCOBRANCA é derivado de BANCOS_SUPORTADOS (fonte única).

    Garante que HU-03 (geração) usa exatamente o mesmo mapa banco→brcobranca_id
    que o módulo de paridade — sem segunda tabela divergente.
    """
    esperado = {cod: spec['brcobranca_id']
                for cod, spec in bancos.BANCOS_SUPORTADOS.items()}
    assert BoletoService.BANCOS_BRCOBRANCA == esperado


def test_paridade_seletor_vs_geracao_boleto():
    """Trava da divergência entre o seletor (BancoBrasil) e a geração (HU-03).

    Qualquer banco novo no seletor precisa de suporte no BRCobrança (ou ser
    adicionado conscientemente ao conjunto documentado), e vice-versa.
    """
    codigos_choices = _codigos_choices(BancoBrasil)
    suportados = set(bancos.BANCOS_SUPORTADOS)

    assert (codigos_choices - suportados) == set(SELECIONAVEIS_SEM_SUPORTE_BRCOBRANCA), (
        "seletor ContaBancaria divergiu dos bancos suportados pelo BRCobrança — "
        "atualize SELECIONAVEIS_SEM_SUPORTE_BRCOBRANCA e a doc (HU-03/HU-23)"
    )
    assert (suportados - codigos_choices) == set(SUPORTADOS_NAO_SELECIONAVEIS), (
        "há banco suportado pelo BRCobrança fora do seletor — "
        "atualize SUPORTADOS_NAO_SELECIONAVEIS e o seletor BancoBrasil"
    )


def test_paridade_boleto_vs_remessa_cnab():
    """Trava da divergência HU-03 (boleto) × HU-23 (remessa CNAB).

    Bancos com boleto mas sem layout de remessa CNAB são exatamente o conjunto
    'registro online / sem remessa' (HU-23 RN-16). Mudou? Decisão consciente.
    """
    sem_remessa = {
        cod for cod, spec in bancos.BANCOS_SUPORTADOS.items()
        if not spec['layouts_cnab']
    }
    assert sem_remessa == set(BOLETO_SEM_REMESSA_CNAB), (
        "conjunto de bancos 'boleto sem remessa CNAB' mudou — "
        "reavalie HU-23 RN-16 e atualize BOLETO_SEM_REMESSA_CNAB"
    )


def test_suporta_cnab_coerente_com_layouts_cnab():
    """suporta_cnab(banco, layout) concorda com a tabela layouts_cnab."""
    for codigo, spec in bancos.BANCOS_SUPORTADOS.items():
        for layout in (LayoutCNAB.CNAB_240, LayoutCNAB.CNAB_400):
            esperado = layout in spec['layouts_cnab']
            assert bancos.suporta_cnab(codigo, layout) == esperado, (
                f"suporta_cnab({codigo}, {layout}) diverge de layouts_cnab"
            )


def test_banco_nao_suportado_para_remessa_nao_suporta_nenhum_layout():
    """Coerência: banco fora da tabela não suporta CNAB algum."""
    assert not bancos.suporta_cnab('999', LayoutCNAB.CNAB_240)
    assert bancos.layouts_cnab('999') == ()
    assert not bancos.suportado('999')


# ── Validação de campos da conta por banco ────────────────────────────────────

def test_campos_validacao_so_para_bancos_suportados():
    """Toda entrada de CAMPOS_BANCO_VALIDACAO é um banco suportado."""
    assert set(bancos.CAMPOS_BANCO_VALIDACAO).issubset(set(bancos.BANCOS_SUPORTADOS))


def test_validar_campos_conta_agencia_excedida():
    """BB: agência além de 4 dígitos é rejeitada."""
    erros = bancos.validar_campos_conta('001', agencia='12345', conta='123')
    assert 'agencia' in erros and '4' in erros['agencia']


def test_validar_campos_conta_descarta_dv():
    """O dígito verificador (após '-') não conta no tamanho."""
    # BB conta máx 8 → '12345678-9' tem número de 8 dígitos (válido)
    erros = bancos.validar_campos_conta('001', agencia='1234-5', conta='12345678-9')
    assert erros == {}


def test_validar_campos_conta_conta_excedida():
    """Itaú: conta máx 5 dígitos."""
    erros = bancos.validar_campos_conta('341', conta='123456')
    assert 'conta' in erros


def test_validar_campos_conta_carteira_valores_c6():
    """C6: carteira só pode ser 10 ou 20."""
    assert bancos.validar_campos_conta('336', carteira='10') == {}
    assert bancos.validar_campos_conta('336', carteira='20') == {}
    erros = bancos.validar_campos_conta('336', carteira='99')
    assert 'carteira' in erros and '10' in erros['carteira']


def test_validar_campos_conta_carteira_valores_sicoob():
    """Sicoob: carteira ∈ {1, 3, 9}."""
    assert bancos.validar_campos_conta('756', carteira='1') == {}
    assert 'carteira' in bancos.validar_campos_conta('756', carteira='2')


def test_validar_campos_conta_carteira_tamanho():
    """BB: carteira máx 2 dígitos."""
    assert bancos.validar_campos_conta('001', carteira='18') == {}
    assert 'carteira' in bancos.validar_campos_conta('001', carteira='123')


def test_validar_campos_conta_banco_sem_regra_nao_restringe():
    """Banco fora da tabela de validação não impõe restrição."""
    assert bancos.validar_campos_conta('077', agencia='999999', conta='9'*30) == {}


def test_validar_campos_conta_vazio_nao_erra():
    """Campos vazios não disparam erro de tamanho (obrigatoriedade é à parte)."""
    assert bancos.validar_campos_conta('001', agencia='', conta='', carteira='') == {}


# ── Validação de layout CNAB por banco ────────────────────────────────────────

def test_validar_layout_cnab_incompativel():
    """Caixa (104) só suporta CNAB 240 → CNAB 400 é rejeitado."""
    erro = bancos.validar_layout_cnab('104', LayoutCNAB.CNAB_400)
    assert erro and 'CNAB 400' in erro
    assert bancos.validar_layout_cnab('104', LayoutCNAB.CNAB_240) is None


def test_validar_layout_cnab_bradesco_so_400():
    """Bradesco (237) só suporta CNAB 400 → CNAB 240 é rejeitado."""
    assert bancos.validar_layout_cnab('237', LayoutCNAB.CNAB_240) is not None
    assert bancos.validar_layout_cnab('237', LayoutCNAB.CNAB_400) is None


def test_validar_layout_cnab_banco_sem_remessa_nao_restringe():
    """Banco sem remessa CNAB (Inter 077) não restringe layout (registro online)."""
    assert bancos.validar_layout_cnab('077', LayoutCNAB.CNAB_240) is None
    assert bancos.validar_layout_cnab('077', LayoutCNAB.CNAB_400) is None


def test_validar_layout_cnab_concorda_com_layouts_cnab():
    """validar_layout_cnab concorda com a tabela layouts_cnab para todo banco."""
    for codigo, spec in bancos.BANCOS_SUPORTADOS.items():
        layouts = spec['layouts_cnab']
        for layout in (LayoutCNAB.CNAB_240, LayoutCNAB.CNAB_400):
            erro = bancos.validar_layout_cnab(codigo, layout)
            if not layouts:
                assert erro is None  # sem remessa → nunca bloqueia
            elif layout in layouts:
                assert erro is None
            else:
                assert erro is not None
