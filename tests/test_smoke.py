"""
Smoke tests — verifica que nenhum endpoint retorna HTTP 500.

Cobre todas as URLs GET do sistema (staff + portal do comprador).
Respostas aceitáveis: 200, 302, 400, 404. Qualquer 500 é uma falha.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model

from tests.fixtures.factories import (
    SuperUserFactory, ContabilidadeFactory, ImobiliariaFactory,
    ContaBancariaFactory, ImovelFactory, CompradorFactory,
    ContratoFactory, ParcelaFactory, ArquivoRemessaFactory,
    ArquivoRetornoFactory, ConfiguracaoEmailFactory,
    ConfiguracaoWhatsAppFactory, TemplateNotificacaoFactory,
    RegraNotificacaoFactory, NotificacaoFactory,
)
from portal_comprador.models import AcessoComprador

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixture de dados — classe-scoped para criar objetos uma única vez
# ---------------------------------------------------------------------------

@pytest.fixture(scope='class')
def dados(django_db_setup, django_db_blocker):
    """Cria conjunto mínimo de objetos para os smoke tests."""
    with django_db_blocker.unblock():
        staff = SuperUserFactory(username='_smoke_staff', password='pass')
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        conta = ContaBancariaFactory(imobiliaria=imobiliaria, principal=True)
        imovel = ImovelFactory(imobiliaria=imobiliaria, disponivel=False)
        comprador = CompradorFactory()
        contrato = ContratoFactory(
            imovel=imovel, comprador=comprador, imobiliaria=imobiliaria,
        )
        parcela = ParcelaFactory(contrato=contrato)
        remessa = ArquivoRemessaFactory(conta_bancaria=conta)
        retorno = ArquivoRetornoFactory(conta_bancaria=conta)
        cfg_email = ConfiguracaoEmailFactory()
        cfg_wa = ConfiguracaoWhatsAppFactory()
        template = TemplateNotificacaoFactory()
        regra = RegraNotificacaoFactory()
        notificacao = NotificacaoFactory(parcela=parcela)

        usuario_comprador = User.objects.create_user(
            username='_smoke_comprador', password='pass',
        )
        AcessoComprador.objects.create(
            comprador=comprador, usuario=usuario_comprador,
        )

        yield {
            'staff': staff,
            'contabilidade': contabilidade,
            'imobiliaria': imobiliaria,
            'conta': conta,
            'imovel': imovel,
            'comprador': comprador,
            'contrato': contrato,
            'parcela': parcela,
            'remessa': remessa,
            'retorno': retorno,
            'cfg_email': cfg_email,
            'cfg_wa': cfg_wa,
            'template': template,
            'regra': regra,
            'notificacao': notificacao,
            'usuario_comprador': usuario_comprador,
        }

        # Teardown — delete in reverse dependency order so FKs don't block
        AcessoComprador.objects.filter(usuario=usuario_comprador).delete()
        notificacao.delete()
        regra.delete()
        template.delete()
        cfg_wa.delete()
        cfg_email.delete()
        retorno.delete()
        remessa.delete()
        parcela.delete()
        contrato.delete()
        comprador.delete()
        imovel.delete()
        conta.delete()
        imobiliaria.delete()
        contabilidade.delete()
        User.objects.filter(username__in=['_smoke_staff', '_smoke_comprador']).delete()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def staff(d):
    c = Client()
    c.force_login(d['staff'])
    return c


def portal(d):
    c = Client()
    c.force_login(d['usuario_comprador'])
    return c


OK = (200, 302, 400, 404)  # acceptable — anything but 500


def check(client, url, acceptable=OK):
    resp = client.get(url)
    assert resp.status_code in acceptable, (
        f"HTTP {resp.status_code} em {url}\n"
        f"{resp.content[:600].decode(errors='replace')}"
    )
    return resp.status_code


# ===========================================================================
# CORE
# ===========================================================================

@pytest.mark.django_db
class TestSmokeCore:
    def test_health(self, dados):
        check(Client(), '/health/')

    def test_index(self, dados):
        check(Client(), '/')

    def test_setup(self, dados):
        check(Client(), '/setup/')

    def test_dashboard(self, dados):
        assert check(staff(dados), '/dashboard/') == 200

    def test_dados_teste(self, dados):
        assert check(staff(dados), '/dados-teste/') == 200

    def test_contabilidades(self, dados):
        assert check(staff(dados), '/contabilidades/') == 200

    def test_contabilidade_configuracoes(self, dados):
        pk = dados['contabilidade'].pk
        assert check(staff(dados), f'/contabilidades/{pk}/configuracoes/') == 200

    def test_compradores(self, dados):
        assert check(staff(dados), '/compradores/') == 200

    def test_imoveis(self, dados):
        assert check(staff(dados), '/imoveis/') == 200

    def test_imobiliarias(self, dados):
        assert check(staff(dados), '/imobiliarias/') == 200

    def test_acessos(self, dados):
        assert check(staff(dados), '/acessos/') == 200

    def test_api_bancos(self, dados):
        assert check(staff(dados), '/api/bancos/') == 200

    def test_api_busca_global(self, dados):
        assert check(staff(dados), '/api/search/?q=teste') == 200

    def test_api_cep(self, dados):
        check(staff(dados), '/api/cep/01310100/', acceptable=(200, 400, 404, 500, 502, 503))

    def test_api_imobiliarias_por_contabilidade(self, dados):
        pk = dados['contabilidade'].pk
        assert check(staff(dados), f'/api/contabilidades/{pk}/imobiliarias/') == 200

    def test_loteamento_detalhe(self, dados):
        nome = dados['imobiliaria'].nome
        check(staff(dados), f'/imoveis/loteamento/{nome}/')

    def test_imovel_poligono(self, dados):
        pk = dados['imovel'].pk
        check(staff(dados), f'/imoveis/{pk}/poligono/')


# ===========================================================================
# ACCOUNTS
# ===========================================================================

@pytest.mark.django_db
class TestSmokeAccounts:
    def test_login_page(self, dados):
        assert check(Client(), '/accounts/login/') == 200

    def test_registro_page(self, dados):
        assert check(Client(), '/accounts/registro/') == 200

    def test_perfil(self, dados):
        check(staff(dados), '/accounts/perfil/')

    def test_alterar_senha(self, dados):
        check(staff(dados), '/accounts/alterar-senha/')


# ===========================================================================
# CONTRATOS
# ===========================================================================

@pytest.mark.django_db
class TestSmokeContratos:
    def test_listar(self, dados):
        assert check(staff(dados), '/contratos/') == 200

    def test_wizard(self, dados):
        check(staff(dados), '/contratos/wizard/')

    def test_wizard_step1(self, dados):
        check(staff(dados), '/contratos/wizard/step1/')

    def test_detalhe(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/contratos/{pk}/') == 200

    def test_editar(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/contratos/{pk}/editar/') == 200

    def test_parcelas(self, dados):
        pk = dados['contrato'].pk
        check(staff(dados), f'/contratos/{pk}/parcelas/')

    def test_rescisao(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/contratos/{pk}/rescisao/') == 200

    def test_cessao(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/contratos/{pk}/cessao/') == 200

    def test_intermediarias(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/contratos/{pk}/intermediarias/') == 200

    def test_indices(self, dados):
        assert check(staff(dados), '/contratos/indices/') == 200

    def test_api_tabela_juros(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/contratos/{pk}/tabela-juros/') == 200

    def test_api_wizard_imoveis(self, dados):
        assert check(staff(dados), '/contratos/wizard/api/imoveis/') == 200


# ===========================================================================
# FINANCEIRO — dashboards
# ===========================================================================

@pytest.mark.django_db
class TestSmokeFinanceiroDashboards:
    def test_dashboard_financeiro(self, dados):
        assert check(staff(dados), '/financeiro/dashboard/') == 200

    def test_api_dashboard_dados(self, dados):
        assert check(staff(dados), '/financeiro/api/dashboard-dados/') == 200

    def test_dashboard_contabilidade(self, dados):
        assert check(staff(dados), '/financeiro/contabilidade/dashboard/') == 200

    def test_api_dashboard_contabilidade(self, dados):
        assert check(staff(dados), '/financeiro/api/dashboard-contabilidade/') == 200

    def test_dashboard_imobiliaria(self, dados):
        pk = dados['imobiliaria'].pk
        assert check(staff(dados), f'/financeiro/imobiliaria/{pk}/dashboard/') == 200

    def test_api_imobiliaria_dashboard(self, dados):
        pk = dados['imobiliaria'].pk
        assert check(staff(dados), f'/financeiro/api/imobiliaria/{pk}/dashboard/') == 200


# ===========================================================================
# FINANCEIRO — parcelas
# ===========================================================================

@pytest.mark.django_db
class TestSmokeFinanceiroParcelas:
    def test_listar(self, dados):
        assert check(staff(dados), '/financeiro/parcelas/') == 200

    def test_detalhe(self, dados):
        pk = dados['parcela'].pk
        assert check(staff(dados), f'/financeiro/parcelas/{pk}/') == 200

    def test_parcelas_mes(self, dados):
        assert check(staff(dados), '/financeiro/parcelas/mes/') == 200

    def test_api_parcelas_lista(self, dados):
        assert check(staff(dados), '/financeiro/api/parcelas/') == 200

    def test_api_contrato_parcelas(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/api/contratos/{pk}/parcelas/') == 200

    def test_api_calcular_encargos(self, dados):
        pk = dados['parcela'].pk
        assert check(staff(dados), f'/financeiro/parcelas/{pk}/calcular-encargos/') == 200

    def test_api_parcelas_elegibilidade(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/api/contrato/{pk}/parcelas-elegibilidade/') == 200

    def test_api_status_boleto(self, dados):
        pk = dados['parcela'].pk
        assert check(staff(dados), f'/financeiro/parcelas/{pk}/boleto/status/') == 200

    def test_boleto_visualizar(self, dados):
        pk = dados['parcela'].pk
        check(staff(dados), f'/financeiro/parcelas/{pk}/boleto/visualizar/')

    def test_segunda_via_boleto_get(self, dados):
        pk = dados['parcela'].pk
        check(staff(dados), f'/financeiro/parcelas/{pk}/boleto/segunda-via/')

    def test_simulador_antecipacao(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/contrato/{pk}/simulador/') == 200

    def test_renegociar_parcelas(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/contrato/{pk}/renegociar/') == 200

    def test_gerar_carne_get(self, dados):
        pk = dados['contrato'].pk
        check(staff(dados), f'/financeiro/contrato/{pk}/gerar-carne/', acceptable=(200, 302, 400, 404, 405))

    def test_download_carne_pdf_get(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/contrato/{pk}/carne/pdf/') == 200

    def test_api_boleto_detalhe(self, dados):
        pk = dados['parcela'].pk
        check(staff(dados), f'/financeiro/api/boletos/{pk}/')


# ===========================================================================
# FINANCEIRO — reajustes
# ===========================================================================

@pytest.mark.django_db
class TestSmokeFinanceiroReajustes:
    def test_listar(self, dados):
        assert check(staff(dados), '/financeiro/reajustes/') == 200

    def test_pendentes(self, dados):
        assert check(staff(dados), '/financeiro/reajustes/pendentes/') == 200

    def test_aplicar_pagina(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/contrato/{pk}/reajuste/') == 200

    def test_api_reajustes_count(self, dados):
        assert check(staff(dados), '/financeiro/api/reajustes-pendentes/count/') == 200

    def test_api_sidebar_pendencias(self, dados):
        assert check(staff(dados), '/financeiro/api/sidebar/pendencias/') == 200

    def test_api_indice_reajuste(self, dados):
        check(staff(dados), '/financeiro/api/indice-reajuste/?tipo_correcao=IPCA&data_inicio=2024-01-01&data_fim=2024-12-01')

    def test_api_calcular_acumulado(self, dados):
        check(staff(dados), '/financeiro/api/calcular-indice-acumulado/?tipo=IPCA&data_inicio=2024-01-01&data_fim=2024-12-01')

    def test_api_contrato_reajustes(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/api/contratos/{pk}/reajustes/') == 200


# ===========================================================================
# FINANCEIRO — CNAB / OFX / Conciliação
# ===========================================================================

@pytest.mark.django_db
class TestSmokeFinanceiroCNAB:
    def test_listar_remessas(self, dados):
        assert check(staff(dados), '/financeiro/cnab/remessa/') == 200

    def test_gerar_remessa_get(self, dados):
        assert check(staff(dados), '/financeiro/cnab/remessa/gerar/') == 200

    def test_detalhe_remessa(self, dados):
        pk = dados['remessa'].pk
        assert check(staff(dados), f'/financeiro/cnab/remessa/{pk}/') == 200

    def test_listar_retornos(self, dados):
        assert check(staff(dados), '/financeiro/cnab/retorno/') == 200

    def test_upload_retorno_get(self, dados):
        assert check(staff(dados), '/financeiro/cnab/retorno/upload/') == 200

    def test_detalhe_retorno(self, dados):
        pk = dados['retorno'].pk
        assert check(staff(dados), f'/financeiro/cnab/retorno/{pk}/') == 200

    def test_upload_ofx_get(self, dados):
        assert check(staff(dados), '/financeiro/cnab/ofx/upload/') == 200

    def test_dashboard_conciliacao(self, dados):
        assert check(staff(dados), '/financeiro/conciliacao/') == 200

    def test_api_cnab_boletos_disponiveis(self, dados):
        assert check(staff(dados), '/financeiro/api/cnab/boletos-disponiveis/') == 200

    def test_api_cnab_boletos_pendentes_count(self, dados):
        assert check(staff(dados), '/financeiro/api/cnab/boletos-pendentes/count/') == 200

    def test_api_cnab_remessas(self, dados):
        assert check(staff(dados), '/financeiro/api/cnab/remessas/') == 200

    def test_api_cnab_retornos(self, dados):
        assert check(staff(dados), '/financeiro/api/cnab/retornos/') == 200

    def test_api_contas_bancarias(self, dados):
        assert check(staff(dados), '/financeiro/api/contas-bancarias/') == 200


# ===========================================================================
# FINANCEIRO — relatórios e APIs REST
# ===========================================================================

@pytest.mark.django_db
class TestSmokeFinanceiroRelatorios:
    def test_prestacoes_a_pagar(self, dados):
        assert check(staff(dados), '/financeiro/relatorios/prestacoes-a-pagar/') == 200

    def test_prestacoes_pagas(self, dados):
        assert check(staff(dados), '/financeiro/relatorios/prestacoes-pagas/') == 200

    def test_posicao_contratos(self, dados):
        assert check(staff(dados), '/financeiro/relatorios/posicao-contratos/') == 200

    def test_previsao_reajustes(self, dados):
        assert check(staff(dados), '/financeiro/relatorios/previsao-reajustes/') == 200

    def test_exportar_csv(self, dados):
        check(staff(dados), '/financeiro/relatorios/exportar/prestacoes_a_pagar/?formato=csv')

    def test_api_relatorio_resumo(self, dados):
        assert check(staff(dados), '/financeiro/api/relatorios/resumo/') == 200

    def test_api_contabilidade_vencimentos(self, dados):
        assert check(staff(dados), '/financeiro/api/contabilidade/vencimentos/') == 200

    def test_api_contabilidade_relatorios_vencimentos(self, dados):
        assert check(staff(dados), '/financeiro/api/contabilidade/relatorios/vencimentos/') == 200

    def test_api_imobiliaria_vencimentos(self, dados):
        pk = dados['imobiliaria'].pk
        assert check(staff(dados), f'/financeiro/api/imobiliaria/{pk}/vencimentos/') == 200

    def test_api_imobiliaria_fluxo_caixa(self, dados):
        pk = dados['imobiliaria'].pk
        assert check(staff(dados), f'/financeiro/api/imobiliaria/{pk}/fluxo-caixa/') == 200

    def test_api_imobiliaria_pendencias(self, dados):
        pk = dados['imobiliaria'].pk
        assert check(staff(dados), f'/financeiro/api/imobiliaria/{pk}/pendencias/') == 200

    def test_api_imobiliarias_lista(self, dados):
        assert check(staff(dados), '/financeiro/api/imobiliarias/') == 200

    def test_api_contratos_lista(self, dados):
        assert check(staff(dados), '/financeiro/api/contratos/') == 200

    def test_api_contrato_detalhe(self, dados):
        pk = dados['contrato'].pk
        assert check(staff(dados), f'/financeiro/api/contratos/{pk}/') == 200


# ===========================================================================
# NOTIFICAÇÕES
# ===========================================================================

@pytest.mark.django_db
class TestSmokeNotificacoes:
    def test_listar(self, dados):
        assert check(staff(dados), '/notificacoes/') == 200

    def test_painel_mensagens(self, dados):
        assert check(staff(dados), '/notificacoes/painel/') == 200

    def test_configuracoes(self, dados):
        assert check(staff(dados), '/notificacoes/configuracoes/') == 200

    def test_listar_config_email(self, dados):
        assert check(staff(dados), '/notificacoes/email/') == 200

    def test_criar_config_email(self, dados):
        assert check(staff(dados), '/notificacoes/email/novo/') == 200

    def test_editar_config_email(self, dados):
        pk = dados['cfg_email'].pk
        assert check(staff(dados), f'/notificacoes/email/{pk}/editar/') == 200

    def test_listar_config_whatsapp(self, dados):
        assert check(staff(dados), '/notificacoes/whatsapp/') == 200

    def test_criar_config_whatsapp(self, dados):
        assert check(staff(dados), '/notificacoes/whatsapp/novo/') == 200

    def test_editar_config_whatsapp(self, dados):
        pk = dados['cfg_wa'].pk
        assert check(staff(dados), f'/notificacoes/whatsapp/{pk}/editar/') == 200

    def test_listar_templates(self, dados):
        assert check(staff(dados), '/notificacoes/templates/') == 200

    def test_criar_template(self, dados):
        assert check(staff(dados), '/notificacoes/templates/novo/') == 200

    def test_editar_template(self, dados):
        pk = dados['template'].pk
        assert check(staff(dados), f'/notificacoes/templates/{pk}/editar/') == 200

    def test_preview_template(self, dados):
        pk = dados['template'].pk
        check(staff(dados), f'/notificacoes/templates/{pk}/preview/')

    def test_listar_regras(self, dados):
        assert check(staff(dados), '/notificacoes/regras/') == 200

    def test_criar_regra(self, dados):
        check(staff(dados), '/notificacoes/regras/novo/')

    def test_editar_regra(self, dados):
        pk = dados['regra'].pk
        check(staff(dados), f'/notificacoes/regras/{pk}/editar/')


# ===========================================================================
# PORTAL DO COMPRADOR
# ===========================================================================

@pytest.mark.django_db
class TestSmokePortal:
    def test_login(self, dados):
        assert check(Client(), '/portal/login/') == 200

    def test_cadastro(self, dados):
        assert check(Client(), '/portal/cadastro/') == 200

    def test_dashboard(self, dados):
        assert check(portal(dados), '/portal/') == 200

    def test_meus_contratos(self, dados):
        assert check(portal(dados), '/portal/contratos/') == 200

    def test_detalhe_contrato(self, dados):
        pk = dados['contrato'].pk
        assert check(portal(dados), f'/portal/contratos/{pk}/') == 200

    def test_meus_boletos(self, dados):
        assert check(portal(dados), '/portal/boletos/') == 200

    def test_meus_dados(self, dados):
        assert check(portal(dados), '/portal/meus-dados/') == 200

    def test_api_parcelas(self, dados):
        pk = dados['contrato'].pk
        assert check(portal(dados), f'/portal/api/contratos/{pk}/parcelas/') == 200

    def test_api_resumo_financeiro(self, dados):
        assert check(portal(dados), '/portal/api/resumo-financeiro/') == 200

    def test_api_vencimentos(self, dados):
        assert check(portal(dados), '/portal/api/vencimentos/') == 200

    def test_api_boletos(self, dados):
        assert check(portal(dados), '/portal/api/boletos/') == 200

    def test_api_linha_digitavel(self, dados):
        pk = dados['parcela'].pk
        check(portal(dados), f'/portal/api/boletos/{pk}/linha-digitavel/')
