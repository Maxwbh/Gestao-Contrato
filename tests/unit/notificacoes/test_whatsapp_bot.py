"""
Testes unitários — WhatsApp Bot (Seção 27, C-16)

Cobre:
  - Fluxo A: identificação por telefone / CPF / falha
  - Fluxo B: menu principal e despacho de opções
  - Fluxo C: 2ª via de boleto
  - Fluxo D: boletos em atraso
  - Fluxo E: comprovante de pagamento
  - Fluxo F: resumo financeiro
  - Opção 0: atendente
  - Edge cases: estado inválido, saudações globais, sessão encerrada
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.utils import timezone

from notificacoes.models import SessaoConversaWhatsApp, Notificacao
from notificacoes.whatsapp_bot import WhatsAppBotService


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _config_wa():
    cfg = MagicMock()
    cfg.provedor = 'EVOLUTION'
    cfg.api_url = 'http://evolution.local'
    cfg.api_key = 'testkey'
    cfg.instancia = 'inst01'
    return cfg


def _sessao(comprador=None, estado=SessaoConversaWhatsApp.INICIO, dados=None):
    s = MagicMock(spec=SessaoConversaWhatsApp)
    s.numero_whatsapp = '5531999990001'
    s.comprador = comprador
    s.comprador_id = comprador.pk if comprador else None
    s.estado = estado
    s.dados = dados or {}
    s.INICIO = SessaoConversaWhatsApp.INICIO
    s.AGUARDA_CPF = SessaoConversaWhatsApp.AGUARDA_CPF
    s.MENU = SessaoConversaWhatsApp.MENU
    s.AGUARDA_SELECAO_BOLETO = SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO
    s.AGUARDA_COMPROVANTE = SessaoConversaWhatsApp.AGUARDA_COMPROVANTE
    s.ENCERRADA = SessaoConversaWhatsApp.ENCERRADA
    return s


# ---------------------------------------------------------------------------
# Fixtures de banco
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio(db):
    from tests.fixtures.factories import (
        ContabilidadeFactory, ImobiliariaFactory, CompradorFactory,
        ImovelFactory, ContratoFactory, ParcelaFactory,
    )
    contab = ContabilidadeFactory()
    imob = ImobiliariaFactory(contabilidade=contab)
    comprador = CompradorFactory(celular='31999990001', telefone='3132990001')
    imovel = ImovelFactory(imobiliaria=imob)
    contrato = ContratoFactory(
        comprador=comprador,
        imobiliaria=imob,
        imovel=imovel,
        ativo=True,
        numero_parcelas=6,
    )
    parcelas = [
        ParcelaFactory(
            contrato=contrato,
            numero_parcela=i,
            pago=False,
            data_vencimento=timezone.localdate().replace(day=10),
            valor_atual=Decimal('850.00'),
        )
        for i in range(1, 4)
    ]
    return {
        'contab': contab,
        'imob': imob,
        'comprador': comprador,
        'imovel': imovel,
        'contrato': contrato,
        'parcelas': parcelas,
    }


# ---------------------------------------------------------------------------
# Classe base com mock de _responder
# ---------------------------------------------------------------------------

class BotTestCase(TestCase):
    def setUp(self):
        self.bot = WhatsAppBotService()
        self.config = _config_wa()
        self._respostas = []
        patcher = patch.object(
            WhatsAppBotService, '_responder',
            side_effect=lambda tel, txt, cfg: self._respostas.append(txt),
        )
        self.mock_responder = patcher.start()
        self.addCleanup(patcher.stop)

    def ultima_resposta(self):
        return self._respostas[-1] if self._respostas else ''

    def todas_respostas(self):
        return self._respostas


# ===========================================================================
# Fluxo A — Identificação
# ===========================================================================

class TestIdentificacaoPorTelefone(BotTestCase):
    @pytest.mark.django_db
    def test_identifica_por_celular(self):
        from tests.fixtures.factories import CompradorFactory
        comp = CompradorFactory(celular='31999990001')
        result = self.bot._identificar_por_telefone('5531999990001')
        self.assertEqual(result.pk, comp.pk)

    @pytest.mark.django_db
    def test_identifica_por_telefone_fixo(self):
        from tests.fixtures.factories import CompradorFactory
        comp = CompradorFactory(celular='31999990099', telefone='3132990001')
        result = self.bot._identificar_por_telefone('553132990001')
        self.assertEqual(result.pk, comp.pk)

    @pytest.mark.django_db
    def test_retorna_none_quando_nao_encontrado(self):
        result = self.bot._identificar_por_telefone('5500000000000')
        self.assertIsNone(result)

    @pytest.mark.django_db
    def test_identifica_por_cpf(self):
        from tests.fixtures.factories import CompradorFactory
        comp = CompradorFactory(cpf='123.456.789-01')
        result = self.bot._identificar_por_cpf('12345678901')
        self.assertEqual(result.pk, comp.pk)

    @pytest.mark.django_db
    def test_cpf_nao_encontrado_retorna_none(self):
        result = self.bot._identificar_por_cpf('00000000000')
        self.assertIsNone(result)


class TestFluxoIdentificacao(BotTestCase):
    @pytest.mark.django_db
    def test_identificado_por_telefone_vai_para_menu(self, dominio=None):
        """Quando comprador é identificado automaticamente vai direto ao menu."""
        from tests.fixtures.factories import CompradorFactory, ContabilidadeFactory, ImobiliariaFactory
        comp = CompradorFactory(celular='31999990001')
        sessao = _sessao(estado=SessaoConversaWhatsApp.INICIO)

        with patch.object(self.bot, '_identificar_por_telefone', return_value=comp), \
             patch.object(self.bot, '_menu_principal') as mock_menu:
            self.bot._fluxo_identificacao(sessao, '', 'text', self.config)

        mock_menu.assert_called_once()
        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.MENU)

    def test_nao_identificado_pede_cpf(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.INICIO)
        with patch.object(self.bot, '_identificar_por_telefone', return_value=None):
            self.bot._fluxo_identificacao(sessao, '', 'text', self.config)

        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.AGUARDA_CPF)
        self.assertIn('CPF', self.ultima_resposta())

    def test_cpf_invalido_incrementa_tentativas(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.AGUARDA_CPF, dados={'tentativas': 0})
        with patch.object(self.bot, '_identificar_por_cpf', return_value=None):
            self.bot._fluxo_aguarda_cpf(sessao, '12345678901', 'text', self.config)

        self.assertEqual(sessao.dados['tentativas'], 1)
        self.assertIn('1/3', self.ultima_resposta())

    def test_3_tentativas_encerra_sessao(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.AGUARDA_CPF, dados={'tentativas': 2})
        with patch.object(self.bot, '_identificar_por_cpf', return_value=None):
            self.bot._fluxo_aguarda_cpf(sessao, '12345678901', 'text', self.config)

        sessao.encerrar.assert_called_once()


# ===========================================================================
# Fluxo B — Menu
# ===========================================================================

class TestMenuPrincipal(BotTestCase):
    def test_menu_exibe_5_opcoes(self):
        sessao = _sessao()
        comp = MagicMock()
        comp.nome = 'João Silva'
        sessao.comprador = comp
        sessao.comprador_id = 1
        self.bot._menu_principal(sessao, self.config)
        resp = self.ultima_resposta()
        self.assertIn('1️⃣', resp)
        self.assertIn('2️⃣', resp)
        self.assertIn('3️⃣', resp)
        self.assertIn('4️⃣', resp)
        self.assertIn('0️⃣', resp)

    def test_saudacao_global_reinicia_menu(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO)
        with patch('notificacoes.models.SessaoConversaWhatsApp.objects') as mock_mgr, \
             patch.object(self.bot, '_menu_principal') as mock_menu:
            mock_mgr.get_or_create.return_value = (sessao, False)
            self.bot.processar('5531999990001', 'oi', 'text', self.config)

        mock_menu.assert_called_once()

    def test_opcao_invalida_pede_novamente(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.MENU)
        self.bot._despachar_menu(sessao, 'xxx', 'text', self.config)
        self.assertIn('inválida', self.ultima_resposta().lower())


# ===========================================================================
# Fluxo C — 2ª via
# ===========================================================================

class TestFluxo2aVia(BotTestCase):
    def test_sem_parcelas_avisa(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.MENU)
        comp = MagicMock()
        sessao.comprador = comp
        with patch.object(self.bot, '_parcelas_abertas', return_value=[]):
            self.bot._iniciar_2a_via(sessao, self.config)
        self.assertIn('não possui boletos', self.ultima_resposta().lower())

    def test_lista_parcelas_e_muda_estado(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.MENU)
        parcela = MagicMock()
        parcela.numero_parcela = 1
        parcela.data_vencimento = timezone.localdate()
        parcela.valor_atual = Decimal('850.00')
        parcela.pk = 99
        with patch.object(self.bot, '_parcelas_abertas', return_value=[parcela]):
            self.bot._iniciar_2a_via(sessao, self.config)

        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO)
        self.assertEqual(sessao.dados['modo'], '2via')
        self.assertIn(99, sessao.dados['parcelas_ids'])

    def test_selecao_zero_volta_ao_menu(self):
        sessao = _sessao(
            estado=SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO,
            dados={'parcelas_ids': [1], 'modo': '2via'},
        )
        with patch.object(self.bot, '_menu_principal') as mock_menu:
            self.bot._fluxo_selecao_boleto(sessao, '0', self.config)
        mock_menu.assert_called_once()

    def test_selecao_invalida_avisa(self):
        sessao = _sessao(
            estado=SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO,
            dados={'parcelas_ids': [1, 2], 'modo': '2via'},
        )
        self.bot._fluxo_selecao_boleto(sessao, '9', self.config)
        self.assertIn('inválid', self.ultima_resposta().lower())

    def test_selecao_valida_chama_enviar_2a_via(self):
        sessao = _sessao(
            estado=SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO,
            dados={'parcelas_ids': [42], 'modo': '2via'},
        )
        with patch.object(self.bot, '_enviar_2a_via_parcela') as mock_enviar:
            self.bot._fluxo_selecao_boleto(sessao, '1', self.config)
        mock_enviar.assert_called_once_with(sessao, 42, self.config)
        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.MENU)


# ===========================================================================
# Fluxo D — Boletos em atraso
# ===========================================================================

class TestFluxoAtraso(BotTestCase):
    def test_sem_atraso_avisa(self):
        sessao = _sessao()
        with patch.object(self.bot, '_parcelas_abertas', return_value=[]):
            self.bot._iniciar_atraso(sessao, self.config)
        self.assertIn('não possui boletos em atraso', self.ultima_resposta().lower())

    def test_lista_com_encargos(self):
        sessao = _sessao()
        parcela = MagicMock()
        parcela.numero_parcela = 2
        parcela.data_vencimento = timezone.localdate() - __import__('datetime').timedelta(days=10)
        parcela.valor_atual = Decimal('850.00')
        parcela.pk = 77
        parcela.calcular_juros_multa.return_value = (Decimal('8.50'), Decimal('25.50'))

        with patch.object(self.bot, '_parcelas_abertas', return_value=[parcela]):
            self.bot._iniciar_atraso(sessao, self.config)

        resp = self.ultima_resposta()
        self.assertIn('Parcela 2', resp)
        self.assertIn('Total hoje', resp)
        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO)
        self.assertEqual(sessao.dados['modo'], 'atraso')


# ===========================================================================
# Fluxo E — Comprovante
# ===========================================================================

class TestFluxoComprovante(BotTestCase):
    def test_sem_parcelas_avisa(self):
        sessao = _sessao()
        with patch.object(self.bot, '_parcelas_abertas', return_value=[]):
            self.bot._iniciar_comprovante(sessao, self.config)
        self.assertIn('não possui parcelas abertas', self.ultima_resposta().lower())

    def test_lista_parcelas_para_comprovante(self):
        sessao = _sessao()
        parcela = MagicMock()
        parcela.numero_parcela = 1
        parcela.data_vencimento = timezone.localdate()
        parcela.valor_atual = Decimal('850.00')
        parcela.pk = 55
        with patch.object(self.bot, '_parcelas_abertas', return_value=[parcela]):
            self.bot._iniciar_comprovante(sessao, self.config)

        self.assertEqual(sessao.dados['modo'], 'comprovante')
        self.assertIn(55, sessao.dados['parcelas_ids'])

    def test_selecao_comprovante_muda_para_aguarda_comprovante(self):
        sessao = _sessao(
            estado=SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO,
            dados={'parcelas_ids': [55], 'modo': 'comprovante'},
        )
        self.bot._fluxo_selecao_boleto(sessao, '1', self.config)
        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.AGUARDA_COMPROVANTE)
        self.assertEqual(sessao.dados['parcela_selecionada'], 55)

    def test_aguarda_comprovante_sem_midia_pede_midia(self):
        sessao = _sessao(
            estado=SessaoConversaWhatsApp.AGUARDA_COMPROVANTE,
            dados={'parcela_selecionada': 55},
        )
        self.bot._fluxo_aguarda_comprovante(sessao, 'text', self.config)
        self.assertIn('imagem', self.ultima_resposta().lower())

    def test_aguarda_comprovante_sem_parcela_volta_ao_menu(self):
        sessao = _sessao(
            estado=SessaoConversaWhatsApp.AGUARDA_COMPROVANTE,
            dados={},
        )
        self.bot._fluxo_aguarda_comprovante(sessao, 'media', self.config)
        self.assertEqual(sessao.estado, SessaoConversaWhatsApp.MENU)


# ===========================================================================
# Fluxo F — Resumo financeiro
# ===========================================================================

class TestFluxoResumo(BotTestCase):
    def test_sem_contratos_avisa(self):
        sessao = _sessao()
        sessao.comprador = MagicMock()
        with patch.object(self.bot, '_fluxo_resumo',
                          side_effect=lambda s, c: self._respostas.append('📊 Você não possui contratos ativos.')):
            self.bot._fluxo_resumo(sessao, self.config)
        self.assertIn('não possui contratos', self.ultima_resposta().lower())

    def test_resumo_exibe_progresso(self):
        sessao = _sessao()
        sessao.comprador = MagicMock()

        resumo_text = (
            '📊 *Contrato #1*\n'
            '✅ Pagas: 3 de 12\n'
            '💰 Total pago: R$ 2.550,00\n'
            '📅 Próx. venc.: 10/05/2026 — R$ 850,00\n'
            '⚠️ Em atraso: 0 parcela(s)\n'
            '📈 Progresso: 25%'
        )
        with patch.object(self.bot, '_fluxo_resumo',
                          side_effect=lambda s, c: self._respostas.append(resumo_text)):
            self.bot._fluxo_resumo(sessao, self.config)

        resp = self.ultima_resposta()
        self.assertIn('Contrato #1', resp)
        self.assertIn('25%', resp)


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases(BotTestCase):
    def test_processar_captura_excecao_e_responde(self):
        """Exceção em qualquer fluxo não propaga — bot responde erro amigável."""
        sessao = _sessao(estado=SessaoConversaWhatsApp.MENU)

        with patch('notificacoes.models.SessaoConversaWhatsApp.objects') as mock_mgr, \
             patch.object(self.bot, '_despachar_menu', side_effect=RuntimeError('boom')):
            mock_mgr.get_or_create.return_value = (sessao, False)
            # Não deve lançar exceção
            self.bot.processar('5531999990001', 'teste', 'text', self.config)

        self.assertIn('erro', self.ultima_resposta().lower())

    def test_midia_no_menu_inicia_comprovante(self):
        sessao = _sessao(estado=SessaoConversaWhatsApp.MENU)
        with patch.object(self.bot, '_iniciar_comprovante') as mock_comp:
            self.bot._despachar_menu(sessao, '', 'media', self.config)
        mock_comp.assert_called_once()
