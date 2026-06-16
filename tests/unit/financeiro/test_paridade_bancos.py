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
