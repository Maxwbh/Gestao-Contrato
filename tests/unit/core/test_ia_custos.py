"""
Testes do Painel de Custos de IA.

Cobre: ia_monitor.calcular_custo, ia_monitor.registrar,
       views.ia_custos, views.api_ia_custos_dados.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model

from tests.fixtures.factories import UserFactory

User = get_user_model()


# ─── ia_monitor ─────────────────────────────────────────────────────────────

class TestCalcularCusto:
    def test_modelo_conhecido_haiku(self):
        from core.services.ia_monitor import calcular_custo
        # (1000*1.00 + 1000*5.00) / 1_000_000 = 6000/1_000_000 = 0.006
        custo = calcular_custo('claude-haiku-4-5-20251001', 1000, 1000)
        assert custo == Decimal('0.006')
        assert isinstance(custo, Decimal)

    def test_modelo_gemini_flash_gratuito(self):
        from core.services.ia_monitor import calcular_custo
        custo = calcular_custo('gemini-2.0-flash', 99999, 99999)
        assert custo == Decimal('0')

    def test_modelo_desconhecido_retorna_zero(self):
        from core.services.ia_monitor import calcular_custo
        custo = calcular_custo('modelo-inexistente', 500, 500)
        assert custo == Decimal('0')

    def test_zero_tokens(self):
        from core.services.ia_monitor import calcular_custo
        custo = calcular_custo('claude-sonnet-4-6', 0, 0)
        assert custo == Decimal('0')


@pytest.mark.django_db
class TestRegistrar:
    def test_cria_registro_no_banco(self):
        from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        from core.models import RegistroUsoIA
        registrar(
            provider=PROVIDER_ANTHROPIC,
            modelo='claude-haiku-4-5-20251001',
            operacao=OP_IMPORTACAO_PDF,
            tokens_input=100,
            tokens_output=50,
        )
        assert RegistroUsoIA.objects.filter(
            provider=PROVIDER_ANTHROPIC, operacao=OP_IMPORTACAO_PDF
        ).count() == 1

    def test_falha_silenciosa_sem_exception(self):
        from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_CHATBOT_INTENT
        with patch('core.models.RegistroUsoIA.objects') as mock_mgr:
            mock_mgr.create.side_effect = Exception('DB down')
            # deve completar sem levantar
            registrar(
                provider=PROVIDER_ANTHROPIC,
                modelo='claude-haiku-4-5-20251001',
                operacao=OP_CHATBOT_INTENT,
                tokens_input=10,
                tokens_output=5,
            )

    def test_custo_calculado_automaticamente(self):
        from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_CHATBOT_HUMANIZE
        from core.models import RegistroUsoIA
        registrar(
            provider=PROVIDER_ANTHROPIC,
            modelo='gemini-2.0-flash',  # free
            operacao=OP_CHATBOT_HUMANIZE,
            tokens_input=500,
            tokens_output=200,
        )
        reg = RegistroUsoIA.objects.latest('criado_em')
        assert reg.custo_usd == Decimal('0')

    def test_com_usuario(self):
        from core.services.ia_monitor import registrar, PROVIDER_GOOGLE, OP_IMPORTACAO_PDF
        from core.models import RegistroUsoIA
        user = UserFactory()
        registrar(
            provider=PROVIDER_GOOGLE,
            modelo='gemini-2.0-flash',
            operacao=OP_IMPORTACAO_PDF,
            tokens_input=0,
            tokens_output=0,
            usuario=user,
        )
        reg = RegistroUsoIA.objects.filter(usuario=user).first()
        assert reg is not None


# ─── Views ──────────────────────────────────────────────────────────────────

@pytest.fixture
def staff_user(db):
    return UserFactory(is_staff=True)


@pytest.fixture
def client_staff(client, staff_user):
    client.force_login(staff_user)
    return client


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestIaCustosView:
    def test_requer_login(self, client):
        url = reverse('core:ia_custos')
        resp = client.get(url)
        assert resp.status_code == 302
        assert '/login' in resp['Location'] or 'login' in resp['Location']

    def test_200_autenticado(self, client_logado):
        resp = client_logado.get(reverse('core:ia_custos'))
        assert resp.status_code == 200

    def test_contexto_contem_chaves(self, client_logado):
        resp = client_logado.get(reverse('core:ia_custos'))
        for chave in ('total_custo', 'total_chamadas', 'total_tokens', 'por_modelo', 'por_operacao', 'tendencia', 'recentes'):
            assert chave in resp.context

    def test_periodo_padrao_30(self, client_logado):
        resp = client_logado.get(reverse('core:ia_custos'))
        assert resp.context['periodo'] == 30

    def test_periodo_customizado(self, client_logado):
        resp = client_logado.get(reverse('core:ia_custos') + '?periodo=7')
        assert resp.context['periodo'] == 7

    def test_com_dados_no_banco(self, client_logado):
        from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        from core.models import RegistroUsoIA
        registrar(
            provider=PROVIDER_ANTHROPIC,
            modelo='claude-haiku-4-5-20251001',
            operacao=OP_IMPORTACAO_PDF,
            tokens_input=200,
            tokens_output=100,
        )
        resp = client_logado.get(reverse('core:ia_custos'))
        assert resp.context['total_chamadas'] >= 1
        assert resp.context['total_custo'] > 0

    def test_sem_dados_retorna_zeros(self, client_logado):
        resp = client_logado.get(reverse('core:ia_custos'))
        assert resp.context['total_chamadas'] == 0
        assert resp.context['total_custo'] == Decimal('0')


@pytest.mark.django_db
class TestApiIaCustosDados:
    def test_requer_login(self, client):
        resp = client.get(reverse('core:api_ia_custos_dados'))
        assert resp.status_code == 302

    def test_retorna_json(self, client_logado):
        resp = client_logado.get(reverse('core:api_ia_custos_dados'))
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/json'

    def test_estrutura_json(self, client_logado):
        import json
        resp = client_logado.get(reverse('core:api_ia_custos_dados'))
        data = json.loads(resp.content)
        assert 'por_modelo' in data
        assert 'por_operacao' in data
        assert 'tendencia' in data

    def test_json_com_registros(self, client_logado):
        import json
        from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_CHATBOT_INTENT
        registrar(
            provider=PROVIDER_ANTHROPIC,
            modelo='claude-haiku-4-5-20251001',
            operacao=OP_CHATBOT_INTENT,
            tokens_input=50,
            tokens_output=25,
        )
        resp = client_logado.get(reverse('core:api_ia_custos_dados'))
        data = json.loads(resp.content)
        assert len(data['por_modelo']) >= 1
        assert len(data['por_operacao']) >= 1
        assert data['por_modelo'][0]['custo'] >= 0
        assert data['por_modelo'][0]['chamadas'] >= 1

    def test_periodo_filtra_registros(self, client_logado):
        """Registros fora do período não aparecem."""
        import json
        from core.models import RegistroUsoIA
        from datetime import datetime, timedelta, timezone

        # criar registro com 60 dias de idade
        reg = RegistroUsoIA.objects.create(
            provider='ANTHROPIC',
            modelo='claude-haiku-4-5-20251001',
            operacao='IMPORTACAO_PDF',
            tokens_input=100,
            tokens_output=50,
            custo_usd=Decimal('0.000120'),
        )
        RegistroUsoIA.objects.filter(pk=reg.pk).update(
            criado_em=datetime.now(timezone.utc) - timedelta(days=61)
        )

        resp = client_logado.get(reverse('core:api_ia_custos_dados') + '?periodo=30')
        data = json.loads(resp.content)
        # o registro antigo não deve aparecer na tendência
        total_chamadas = sum(d['chamadas'] for d in data['tendencia'])
        assert total_chamadas == 0
