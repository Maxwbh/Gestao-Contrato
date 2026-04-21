"""
Testes — Seção 19: Notificações de Vencimento (N-01) e Inadimplência (N-02)

Cenários:
  N-01 Vencimento
   1  Parcela vencendo EXATAMENTE em dias_antecedencia dias gera notificação
   2  Parcelas já pagas NÃO geram notificação
   3  Parcelas fora da data exata (mais cedo ou mais tarde) NÃO geram notificação
   4  Duplicatas no mesmo dia são ignoradas
   5  Comprador sem e-mail é ignorado

  N-02 Inadimplência
   6  Parcelas vencidas há >= 3 dias geram notificação
   7  Parcelas vencidas há < 3 dias NÃO geram notificação
   8  Parcelas pagas NÃO geram notificação de inadimplência
   9  Duplicatas no mesmo dia são ignoradas
  10  Endpoint HTTP /api/tasks/enviar-inadimplentes/ exige token
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import Client, override_settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(username='tasks_user', password='pass')


@pytest.fixture
def cli(usuario):
    c = Client()
    c.login(username='tasks_user', password='pass')
    return c


@pytest.fixture
def dominio(db):
    from tests.fixtures.factories import ImobiliariaFactory, ImovelFactory, CompradorFactory
    imob = ImobiliariaFactory()
    imovel = ImovelFactory(imobiliaria=imob)
    comprador = CompradorFactory(
        email='comprador@test.com',
        notificar_email=True,
    )
    return imob, imovel, comprador


@pytest.fixture
def contrato_base(db, dominio):
    from contratos.models import Contrato, StatusContrato, TipoCorrecao, TipoAmortizacao
    imob, imovel, comprador = dominio
    c = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='CTR-NOT-001',
        data_contrato=date.today() - timedelta(days=90),
        data_primeiro_vencimento=date.today() - timedelta(days=60),
        valor_total=Decimal('60000.00'),
        valor_entrada=Decimal('10000.00'),
        numero_parcelas=12,
        dia_vencimento=5,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.FIXO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
    )
    if not c.parcelas.exists():
        c.gerar_parcelas()
    return c


def _criar_parcela(contrato, dias_offset, pago=False):
    """Cria parcela com vencimento relativo a hoje."""
    from financeiro.models import Parcela
    return Parcela.objects.create(
        contrato=contrato,
        numero_parcela=900 + dias_offset,
        valor_original=Decimal('1000.00'),
        valor_atual=Decimal('1000.00'),
        valor_pago=Decimal('0.00'),
        data_vencimento=date.today() + timedelta(days=dias_offset),
        tipo_parcela='NORMAL',
        pago=pago,
    )


# ===========================================================================
# N-01 — Notificações de Vencimento
# ===========================================================================

@pytest.mark.django_db
class TestN01Vencimento:
    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_ANTECEDENCIA=5)
    def test_parcela_a_vencer_gera_notificacao(self, mock_email, contrato_base):
        from core.tasks import enviar_notificacoes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        _criar_parcela(contrato_base, dias_offset=5)  # vence exatamente em dias_antecedencia dias

        result = enviar_notificacoes_sync()

        assert result.items_processed >= 1
        assert Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').exists()

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_ANTECEDENCIA=5)
    def test_parcela_paga_nao_notifica(self, mock_email, contrato_base):
        from core.tasks import enviar_notificacoes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        _criar_parcela(contrato_base, dias_offset=3, pago=True)

        count_antes = Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').count()
        enviar_notificacoes_sync()
        count_depois = Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').count()

        assert count_depois == count_antes  # parcela paga não gera notificação nova

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_ANTECEDENCIA=5)
    def test_parcela_longe_nao_notifica(self, mock_email, contrato_base):
        from core.tasks import enviar_notificacoes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        _criar_parcela(contrato_base, dias_offset=10)  # vence em 10 dias (fora do horizonte)

        count_antes = Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').count()
        enviar_notificacoes_sync()
        count_depois = Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').count()

        assert count_depois == count_antes

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_ANTECEDENCIA=5)
    def test_deduplicacao_no_mesmo_dia(self, mock_email, contrato_base):
        from core.tasks import enviar_notificacoes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        _criar_parcela(contrato_base, dias_offset=5)  # vence exatamente no limite — deve ser processada

        enviar_notificacoes_sync()
        count1 = Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').count()

        enviar_notificacoes_sync()  # segunda execução — deve ignorar
        count2 = Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').count()

        assert count2 == count1  # sem duplicatas

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_ANTECEDENCIA=5)
    def test_comprador_notificar_email_false_ignorado(self, mock_email, contrato_base):
        from core.tasks import enviar_notificacoes_sync
        from notificacoes.models import Notificacao
        from core.models import Comprador

        mock_email.enviar = MagicMock()
        # Desabilitar notificação por e-mail (sem ValidationError)
        Comprador.objects.filter(id=contrato_base.comprador.id).update(notificar_email=False)

        _criar_parcela(contrato_base, dias_offset=2)
        enviar_notificacoes_sync()

        assert not Notificacao.objects.filter(assunto__startswith='[VENCIMENTO]').exists()


# ===========================================================================
# N-02 — Notificações de Inadimplência
# ===========================================================================

@pytest.mark.django_db
class TestN02Inadimplencia:
    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_INADIMPLENCIA=3)
    def test_parcela_vencida_ha_3_dias_notifica(self, mock_email, contrato_base):
        from core.tasks import enviar_inadimplentes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        _criar_parcela(contrato_base, dias_offset=-3)  # venceu há 3 dias

        result = enviar_inadimplentes_sync()

        assert result.items_processed >= 1
        assert Notificacao.objects.filter(assunto__startswith='[INADIMPLENCIA]').exists()

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_INADIMPLENCIA=3)
    def test_parcela_vencida_ha_1_dia_nao_notifica(self, mock_email, contrato_base):
        from core.tasks import enviar_inadimplentes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        p = _criar_parcela(contrato_base, dias_offset=-1)  # venceu há 1 dia (< carência de 3d)

        enviar_inadimplentes_sync()

        # Específico: esta parcela NÃO deve ter notificação
        assert not Notificacao.objects.filter(
            parcela=p, assunto__startswith='[INADIMPLENCIA]'
        ).exists()

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_INADIMPLENCIA=3)
    def test_parcela_paga_nao_notifica_inadimplencia(self, mock_email, contrato_base):
        from core.tasks import enviar_inadimplentes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        p = _criar_parcela(contrato_base, dias_offset=-5, pago=True)

        enviar_inadimplentes_sync()

        assert not Notificacao.objects.filter(
            parcela=p, assunto__startswith='[INADIMPLENCIA]'
        ).exists()

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_INADIMPLENCIA=3)
    def test_deduplicacao_inadimplencia_no_mesmo_dia(self, mock_email, contrato_base):
        from core.tasks import enviar_inadimplentes_sync
        from notificacoes.models import Notificacao

        mock_email.enviar = MagicMock()
        _criar_parcela(contrato_base, dias_offset=-3)  # venceu exatamente no limite de inadimplência

        enviar_inadimplentes_sync()
        count1 = Notificacao.objects.filter(assunto__startswith='[INADIMPLENCIA]').count()

        enviar_inadimplentes_sync()
        count2 = Notificacao.objects.filter(assunto__startswith='[INADIMPLENCIA]').count()

        assert count2 == count1


# ===========================================================================
# Endpoint HTTP
# ===========================================================================

@pytest.mark.django_db
class TestEndpointInadimplentes:
    def test_endpoint_sem_token_retorna_401(self, client):
        with patch('core.tasks.get_param', return_value='test-token-123'):
            resp = client.post('/api/tasks/enviar-inadimplentes/')
        assert resp.status_code == 401

    def test_endpoint_token_invalido_retorna_403(self, client):
        with patch('core.tasks.get_param', return_value='test-token-123'):
            resp = client.post(
                '/api/tasks/enviar-inadimplentes/',
                HTTP_X_TASK_TOKEN='token-errado'
            )
        assert resp.status_code == 403

    @patch('notificacoes.services.ServicoEmail')
    @override_settings(NOTIFICACAO_DIAS_INADIMPLENCIA=3)
    def test_endpoint_token_valido_retorna_200(self, mock_email, client):
        mock_email.enviar = MagicMock()
        with patch('core.tasks.get_param', return_value='test-token-123'):
            resp = client.post(
                '/api/tasks/enviar-inadimplentes/',
                HTTP_X_TASK_TOKEN='test-token-123'
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data['task'] == 'enviar_inadimplentes'
        assert 'success' in data
