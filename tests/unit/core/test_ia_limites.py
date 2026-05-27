"""
Testes de configuração e aplicação de limites de uso de IA.

Cobre: LimiteUsoIA model, inicio_periodo, checar_limite, consumo_periodo,
       get_cotacao_usd_brl, views ia_limites / salvar / excluir / toggle.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model

from tests.fixtures.factories import UserFactory

User = get_user_model()


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.fixture
def limite_tokens(db):
    from core.models import LimiteUsoIA
    return LimiteUsoIA.objects.create(
        tipo_escopo=LimiteUsoIA.ESCOPO_MODELO,
        escopo_valor='claude-haiku-4-5-20251001',
        tipo_limite=LimiteUsoIA.TIPO_TOKENS,
        valor_limite=Decimal('100000'),
        ativo=True,
    )


@pytest.fixture
def limite_reais(db):
    from core.models import LimiteUsoIA
    return LimiteUsoIA.objects.create(
        tipo_escopo=LimiteUsoIA.ESCOPO_OPERACAO,
        escopo_valor='IMPORTACAO_PDF',
        tipo_limite=LimiteUsoIA.TIPO_REAIS,
        valor_limite=Decimal('50.00'),
        ativo=True,
    )


# ─── Model ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLimiteUsoIAModel:
    def test_criacao(self, limite_tokens):
        assert limite_tokens.pk is not None
        assert limite_tokens.ativo is True

    def test_str(self, limite_tokens):
        s = str(limite_tokens)
        assert 'claude-haiku-4-5-20251001' in s
        assert '100000' in s

    def test_periodo_padrao_mensal(self, limite_tokens):
        assert limite_tokens.periodo == 'MENSAL'

    def test_unique_together_inclui_periodo(self, limite_tokens):
        from core.models import LimiteUsoIA
        from django.db import IntegrityError
        # mesmo escopo/tipo/período → viola constraint
        with pytest.raises(IntegrityError):
            LimiteUsoIA.objects.create(
                tipo_escopo=LimiteUsoIA.ESCOPO_MODELO,
                escopo_valor='claude-haiku-4-5-20251001',
                tipo_limite=LimiteUsoIA.TIPO_TOKENS,
                periodo=LimiteUsoIA.PERIODO_MENSAL,
                valor_limite=Decimal('999'),
            )

    def test_mesmo_escopo_periodo_diferente_permitido(self, limite_tokens, db):
        from core.models import LimiteUsoIA
        # mesmo modelo/tipo mas período diferente → permitido (acumuladores)
        lim2 = LimiteUsoIA.objects.create(
            tipo_escopo=LimiteUsoIA.ESCOPO_MODELO,
            escopo_valor='claude-haiku-4-5-20251001',
            tipo_limite=LimiteUsoIA.TIPO_TOKENS,
            periodo=LimiteUsoIA.PERIODO_ANUAL,
            valor_limite=Decimal('1000000'),
        )
        assert lim2.pk != limite_tokens.pk

    def test_mesmo_modelo_tipos_diferentes_permitido(self, limite_tokens, db):
        from core.models import LimiteUsoIA
        lim2 = LimiteUsoIA.objects.create(
            tipo_escopo=LimiteUsoIA.ESCOPO_MODELO,
            escopo_valor='claude-haiku-4-5-20251001',
            tipo_limite=LimiteUsoIA.TIPO_REAIS,
            periodo=LimiteUsoIA.PERIODO_MENSAL,
            valor_limite=Decimal('10.00'),
        )
        assert lim2.pk != limite_tokens.pk


# ─── inicio_periodo ──────────────────────────────────────────────────────────

class TestInicioPeriodo:
    def test_diario_e_hoje(self):
        from core.services.ia_monitor import inicio_periodo
        from datetime import date
        assert inicio_periodo('DIARIO') == date.today()

    def test_mensal_e_dia_1(self):
        from core.services.ia_monitor import inicio_periodo
        from datetime import date
        assert inicio_periodo('MENSAL').day == 1

    def test_anual_e_jan_1(self):
        from core.services.ia_monitor import inicio_periodo
        from datetime import date
        r = inicio_periodo('ANUAL')
        assert r.month == 1 and r.day == 1

    def test_semanal_e_segunda(self):
        from core.services.ia_monitor import inicio_periodo
        assert inicio_periodo('SEMANAL').weekday() == 0  # Monday

    def test_bimestral_retorna_mes_impar(self):
        from core.services.ia_monitor import inicio_periodo
        r = inicio_periodo('BIMESTRAL')
        assert r.month % 2 == 1  # jan(1), mar(3), mai(5), jul(7), set(9), nov(11)

    def test_semestral_retorna_jan_ou_jul(self):
        from core.services.ia_monitor import inicio_periodo
        r = inicio_periodo('SEMESTRAL')
        assert r.month in (1, 7)

    def test_quinzenal_retorna_dia_1_ou_16(self):
        from core.services.ia_monitor import inicio_periodo
        r = inicio_periodo('QUINZENAL')
        assert r.day in (1, 16)


# ─── consumo_periodo ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestConsumoPeriodo:
    def test_sem_registros_retorna_zero(self):
        from core.services.ia_monitor import consumo_periodo
        assert consumo_periodo('MENSAL', modelo='claude-haiku-4-5-20251001') == 0.0

    def test_conta_tokens_do_periodo(self):
        from core.services.ia_monitor import registrar, consumo_periodo, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-haiku-4-5-20251001',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=300, tokens_output=200)
        total = consumo_periodo('MENSAL', modelo='claude-haiku-4-5-20251001', tipo_limite='TOKENS')
        assert total == 500.0

    def test_tokens_por_operacao(self):
        from core.services.ia_monitor import registrar, consumo_periodo, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-haiku-4-5-20251001',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=100, tokens_output=50)
        total = consumo_periodo('MENSAL', operacao=OP_IMPORTACAO_PDF, tipo_limite='TOKENS')
        assert total >= 150.0

    def test_custo_em_reais(self):
        from core.services.ia_monitor import registrar, consumo_periodo, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        with patch('core.services.ia_monitor.get_cotacao_usd_brl', return_value=5.0):
            registrar(provider=PROVIDER_ANTHROPIC, modelo='gemini-2.0-flash',
                      operacao=OP_IMPORTACAO_PDF, tokens_input=0, tokens_output=0)
            total = consumo_periodo('MENSAL', operacao=OP_IMPORTACAO_PDF, tipo_limite='REAIS')
        assert total == 0.0  # gemini free


# ─── checar_limite ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChecarLimite:
    def test_sem_limites_nao_levanta(self):
        from core.services.ia_monitor import checar_limite
        checar_limite(modelo='claude-haiku-4-5-20251001', operacao='IMPORTACAO_PDF')  # sem exceção

    def test_abaixo_do_limite_nao_levanta(self, limite_tokens):
        from core.services.ia_monitor import checar_limite, registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-haiku-4-5-20251001',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=100, tokens_output=50)
        checar_limite(modelo='claude-haiku-4-5-20251001')  # 150 < 100000 — OK

    def test_acima_do_limite_levanta(self, limite_tokens):
        from core.services.ia_monitor import checar_limite, LimiteUsoIAExcedido, registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        # Cria registros acima do limite
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-haiku-4-5-20251001',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=60000, tokens_output=50000)
        with pytest.raises(LimiteUsoIAExcedido):
            checar_limite(modelo='claude-haiku-4-5-20251001')

    def test_limite_inativo_nao_bloqueia(self, limite_tokens):
        from core.services.ia_monitor import checar_limite, registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        limite_tokens.ativo = False
        limite_tokens.save()
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-haiku-4-5-20251001',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=60000, tokens_output=50000)
        checar_limite(modelo='claude-haiku-4-5-20251001')  # não bloqueia

    def test_limite_operacao_bloqueia(self, limite_reais):
        from core.services.ia_monitor import checar_limite, LimiteUsoIAExcedido, registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        with patch('core.services.ia_monitor.get_cotacao_usd_brl', return_value=5.0):
            # Sonnet: $3/MTok in + $15/MTok out → 1M tokens each → $18 USD * 5 = R$90 > R$50
            registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-sonnet-4-6',
                      operacao=OP_IMPORTACAO_PDF,
                      tokens_input=1_000_000, tokens_output=1_000_000)
            with pytest.raises(LimiteUsoIAExcedido):
                checar_limite(operacao='IMPORTACAO_PDF')

    def test_multiplos_limites_acumuladores(self, db):
        """Dois limites para o mesmo escopo — o mensal é atingido, o anual não."""
        from core.models import LimiteUsoIA
        from core.services.ia_monitor import checar_limite, LimiteUsoIAExcedido, registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        # Limite mensal baixo → vai ser excedido
        LimiteUsoIA.objects.create(
            tipo_escopo='MODELO', escopo_valor='claude-haiku-4-5-20251001',
            tipo_limite='TOKENS', periodo='MENSAL', valor_limite=Decimal('100'),
        )
        # Limite anual alto → não excedido
        LimiteUsoIA.objects.create(
            tipo_escopo='MODELO', escopo_valor='claude-haiku-4-5-20251001',
            tipo_limite='TOKENS', periodo='ANUAL', valor_limite=Decimal('999999999'),
        )
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-haiku-4-5-20251001',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=200, tokens_output=0)
        # O mensal (100 tokens) está excedido → bloqueia mesmo com anual OK
        with pytest.raises(LimiteUsoIAExcedido) as exc_info:
            checar_limite(modelo='claude-haiku-4-5-20251001')
        assert 'Mensal' in str(exc_info.value) or 'MENSAL' in str(exc_info.value) or 'mensal' in str(exc_info.value).lower()

    def test_modelo_diferente_nao_bloqueia(self, limite_tokens):
        from core.services.ia_monitor import checar_limite, registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        registrar(provider=PROVIDER_ANTHROPIC, modelo='claude-sonnet-4-6',
                  operacao=OP_IMPORTACAO_PDF, tokens_input=60000, tokens_output=50000)
        checar_limite(modelo='claude-sonnet-4-6')  # sem limite para Sonnet

    def test_sem_args_nao_levanta(self):
        from core.services.ia_monitor import checar_limite
        checar_limite()  # sem modelo nem operação — não faz nada


# ─── get_cotacao_usd_brl ─────────────────────────────────────────────────────

class TestGetCotacao:
    def test_usa_cache_memoria(self):
        import core.services.ia_monitor as mon
        from datetime import date
        mon._cotacao_cache = {'data': date.today().isoformat(), 'valor': 5.75}
        val = mon.get_cotacao_usd_brl()
        assert val == 5.75
        mon._cotacao_cache = {}  # limpa após teste

    def test_usa_awesome_api(self):
        import core.services.ia_monitor as mon
        mon._cotacao_cache = {}
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"USDBRL":{"bid":"5.95"}}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch('urllib.request.urlopen', return_value=mock_resp):
            with patch.object(mon, '_salvar_cotacao_cache'):
                val = mon.get_cotacao_usd_brl()
        assert val == pytest.approx(5.95)
        mon._cotacao_cache = {}

    def test_fallback_se_api_falha(self):
        import core.services.ia_monitor as mon
        mon._cotacao_cache = {}
        with patch('urllib.request.urlopen', side_effect=Exception('timeout')):
            with patch('core.parametros.get_param', side_effect=Exception):
                val = mon.get_cotacao_usd_brl()
        assert val == 5.80
        mon._cotacao_cache = {}


# ─── Views ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIaLimitesView:
    def test_requer_login(self, client):
        resp = client.get(reverse('core:ia_limites'))
        assert resp.status_code == 302

    def test_200_autenticado(self, client_logado):
        resp = client_logado.get(reverse('core:ia_limites'))
        assert resp.status_code == 200

    def test_contexto_tem_chaves(self, client_logado):
        resp = client_logado.get(reverse('core:ia_limites'))
        for k in ('limites_com_consumo', 'modelos', 'operacoes', 'cotacao_usd_brl'):
            assert k in resp.context

    def test_lista_limites(self, client_logado, limite_tokens):
        resp = client_logado.get(reverse('core:ia_limites'))
        assert len(resp.context['limites_com_consumo']) == 1
        assert resp.context['limites_com_consumo'][0]['limite'].pk == limite_tokens.pk


@pytest.mark.django_db
class TestIaLimiteSalvarView:
    def test_cria_novo_limite(self, client_logado):
        from core.models import LimiteUsoIA
        resp = client_logado.post(reverse('core:ia_limite_salvar'), {
            'tipo_escopo': 'MODELO',
            'escopo_valor': 'claude-sonnet-4-6',
            'tipo_limite': 'TOKENS',
            'periodo': 'MENSAL',
            'valor_limite': '500000',
        })
        assert resp.status_code == 302
        assert LimiteUsoIA.objects.filter(escopo_valor='claude-sonnet-4-6').exists()

    def test_multiplos_limites_mesmo_escopo_diferentes_periodos(self, client_logado):
        """O mesmo modelo pode ter limites mensais E anuais (acumuladores)."""
        from core.models import LimiteUsoIA
        for periodo in ('MENSAL', 'SEMESTRAL', 'ANUAL'):
            client_logado.post(reverse('core:ia_limite_salvar'), {
                'tipo_escopo': 'OPERACAO',
                'escopo_valor': 'IMPORTACAO_PDF',
                'tipo_limite': 'REAIS',
                'periodo': periodo,
                'valor_limite': '100',
            })
        assert LimiteUsoIA.objects.filter(escopo_valor='IMPORTACAO_PDF').count() == 3

    def test_valor_virgula_aceito(self, client_logado):
        from core.models import LimiteUsoIA
        client_logado.post(reverse('core:ia_limite_salvar'), {
            'tipo_escopo': 'OPERACAO',
            'escopo_valor': 'CHATBOT_INTENT',
            'tipo_limite': 'REAIS',
            'periodo': 'MENSAL',
            'valor_limite': '25,50',
        })
        lim = LimiteUsoIA.objects.filter(escopo_valor='CHATBOT_INTENT').first()
        assert lim is not None
        assert lim.valor_limite == Decimal('25.50')

    def test_campos_obrigatorios(self, client_logado):
        from core.models import LimiteUsoIA
        client_logado.post(reverse('core:ia_limite_salvar'), {
            'tipo_escopo': 'MODELO',
            'escopo_valor': '',
            'tipo_limite': 'TOKENS',
            'periodo': '',
            'valor_limite': '',
        })
        assert LimiteUsoIA.objects.count() == 0

    def test_atualiza_existente_com_pk(self, client_logado, limite_tokens):
        client_logado.post(reverse('core:ia_limite_salvar'), {
            'pk': str(limite_tokens.pk),
            'tipo_escopo': 'MODELO',
            'escopo_valor': 'claude-haiku-4-5-20251001',
            'tipo_limite': 'TOKENS',
            'periodo': 'MENSAL',
            'valor_limite': '999999',
        })
        limite_tokens.refresh_from_db()
        assert limite_tokens.valor_limite == Decimal('999999')


@pytest.mark.django_db
class TestIaLimiteExcluirView:
    def test_exclui_limite(self, client_logado, limite_tokens):
        from core.models import LimiteUsoIA
        client_logado.post(reverse('core:ia_limite_excluir', args=[limite_tokens.pk]))
        assert not LimiteUsoIA.objects.filter(pk=limite_tokens.pk).exists()

    def test_pk_inexistente_nao_erro(self, client_logado):
        resp = client_logado.post(reverse('core:ia_limite_excluir', args=[99999]))
        assert resp.status_code == 302


@pytest.mark.django_db
class TestIaLimiteToggleView:
    def test_desativa_limite_ativo(self, client_logado, limite_tokens):
        client_logado.post(reverse('core:ia_limite_toggle', args=[limite_tokens.pk]))
        limite_tokens.refresh_from_db()
        assert limite_tokens.ativo is False

    def test_ativa_limite_inativo(self, client_logado, limite_tokens):
        limite_tokens.ativo = False
        limite_tokens.save()
        client_logado.post(reverse('core:ia_limite_toggle', args=[limite_tokens.pk]))
        limite_tokens.refresh_from_db()
        assert limite_tokens.ativo is True


@pytest.mark.django_db
class TestApiCotacaoView:
    def test_requer_login(self, client):
        resp = client.get(reverse('core:api_cotacao_usd_brl'))
        assert resp.status_code == 302

    def test_retorna_json(self, client_logado):
        import core.services.ia_monitor as mon
        from datetime import date
        mon._cotacao_cache = {'data': date.today().isoformat(), 'valor': 5.80}
        resp = client_logado.get(reverse('core:api_cotacao_usd_brl'))
        mon._cotacao_cache = {}
        assert resp.status_code == 200
        import json
        data = json.loads(resp.content)
        assert 'cotacao' in data
        assert data['cotacao'] == 5.80
