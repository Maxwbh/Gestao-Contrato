"""
Testes para 35.1 (Auditoria Reduzida) e 35.2 (Bloqueio de Crédito).
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.test import Client
from django.utils import timezone

from tests.fixtures.factories import (
    UserFactory,
    SuperUserFactory,
    CompradorFactory,
    ContratoFactory,
    ParcelaFactory,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# 35.1 — LogAuditoria / registrar_auditoria
# =============================================================================

class TestLogAuditoriaModel:
    def test_create_direto(self):
        from core.models import LogAuditoria
        log = LogAuditoria.objects.create(acao='PAGAMENTO', entidade='Parcela', entidade_pk=1)
        assert log.pk is not None
        assert log.acao == 'PAGAMENTO'

    def test_ordering_mais_recente_primeiro(self):
        from core.models import LogAuditoria
        LogAuditoria.objects.create(acao='EXPORTACAO')
        LogAuditoria.objects.create(acao='PAGAMENTO')
        logs = list(LogAuditoria.objects.all())
        assert logs[0].acao == 'PAGAMENTO'

    def test_registrar_auditoria_helper_cria_registro(self):
        from core.models import registrar_auditoria, LogAuditoria
        user = UserFactory()
        registrar_auditoria(user, 'BOLETO_GERADO', 'Parcela', 42, 'teste')
        assert LogAuditoria.objects.filter(acao='BOLETO_GERADO', entidade_pk=42).exists()

    def test_registrar_auditoria_helper_falha_silenciosa(self):
        from core.models import registrar_auditoria
        # Deve suprimir qualquer exceção
        registrar_auditoria(None, 'ACAO_INVALIDA_XYZ_99')

    def test_registrar_auditoria_extrai_ip_do_request(self):
        from core.models import registrar_auditoria, LogAuditoria
        from django.test import RequestFactory
        rf = RequestFactory()
        req = rf.get('/')
        req.META['REMOTE_ADDR'] = '10.0.0.1'
        user = UserFactory()
        req.user = user
        registrar_auditoria(req, 'EXPORTACAO', 'Contrato', 99)
        log = LogAuditoria.objects.filter(acao='EXPORTACAO').first()
        assert log is not None
        assert log.ip_address == '10.0.0.1'


class TestAuditoriaLogView:
    def _client(self, user):
        c = Client()
        c.force_login(user)
        return c

    def test_requer_autenticacao(self):
        resp = Client().get(reverse('core:auditoria_log'), secure=True)
        assert resp.status_code == 302

    def test_staff_ve_200(self):
        user = UserFactory(is_staff=True)
        resp = self._client(user).get(reverse('core:auditoria_log'), secure=True)
        assert resp.status_code == 200

    def test_superuser_ve_200(self):
        user = SuperUserFactory()
        resp = self._client(user).get(reverse('core:auditoria_log'), secure=True)
        assert resp.status_code == 200

    def test_usuario_comum_recebe_403(self):
        user = UserFactory()
        resp = self._client(user).get(reverse('core:auditoria_log'), secure=True)
        assert resp.status_code == 403

    def test_filtro_por_acao(self):
        from core.models import LogAuditoria
        LogAuditoria.objects.create(acao='PAGAMENTO')
        LogAuditoria.objects.create(acao='EXPORTACAO')
        user = UserFactory(is_staff=True)
        resp = self._client(user).get(
            reverse('core:auditoria_log') + '?acao=PAGAMENTO', secure=True
        )
        assert resp.status_code == 200
        assert b'PAGAMENTO' in resp.content or b'Pagamento' in resp.content

    def test_contexto_contem_logs_e_acoes(self):
        user = UserFactory(is_staff=True)
        resp = self._client(user).get(reverse('core:auditoria_log'), secure=True)
        assert 'logs' in resp.context
        assert 'acoes' in resp.context


# =============================================================================
# 35.2 — Bloqueio de Crédito
# =============================================================================

class TestBloqueioCredito:
    def _parcela_vencida(self, comprador, dias=100):
        contrato = ContratoFactory(comprador=comprador)
        return ParcelaFactory(
            contrato=contrato,
            pago=False,
            data_vencimento=date.today() - timedelta(days=dias),
        )

    def test_ativacao_automatica_90_dias(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        comprador = CompradorFactory(bloqueio_credito=False)
        self._parcela_vencida(comprador, dias=95)
        result = atualizar_bloqueio_credito_sync()
        comprador.refresh_from_db()
        assert comprador.bloqueio_credito is True
        assert result.success is True
        assert result.data['ativados'] >= 1

    def test_nao_ativa_com_menos_de_90_dias(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        comprador = CompradorFactory(bloqueio_credito=False)
        self._parcela_vencida(comprador, dias=30)
        atualizar_bloqueio_credito_sync()
        comprador.refresh_from_db()
        assert comprador.bloqueio_credito is False

    def test_desativacao_apos_quitacao(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        comprador = CompradorFactory(
            bloqueio_credito=True,
            bloqueio_credito_motivo='teste',
            bloqueio_credito_em=timezone.now(),
        )
        # Comprador sem parcelas vencidas → deve desbloquear
        result = atualizar_bloqueio_credito_sync()
        comprador.refresh_from_db()
        assert comprador.bloqueio_credito is False
        assert result.data['desativados'] >= 1

    def test_registra_log_auditoria_ao_ativar(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        from core.models import LogAuditoria
        comprador = CompradorFactory(bloqueio_credito=False)
        self._parcela_vencida(comprador, dias=100)
        atualizar_bloqueio_credito_sync()
        assert LogAuditoria.objects.filter(
            acao='BLOQUEIO_CREDITO', entidade='Comprador', entidade_pk=comprador.pk
        ).exists()

    def test_registra_log_auditoria_ao_desativar(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        from core.models import LogAuditoria
        comprador = CompradorFactory(
            bloqueio_credito=True,
            bloqueio_credito_em=timezone.now(),
        )
        atualizar_bloqueio_credito_sync()
        assert LogAuditoria.objects.filter(
            acao='DESBLOQUEIO_CREDITO', entidade='Comprador', entidade_pk=comprador.pk
        ).exists()

    def test_campos_preenchidos_ao_bloquear(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        comprador = CompradorFactory(bloqueio_credito=False)
        self._parcela_vencida(comprador, dias=100)
        atualizar_bloqueio_credito_sync()
        comprador.refresh_from_db()
        assert comprador.bloqueio_credito_em is not None
        assert '90' in comprador.bloqueio_credito_motivo

    def test_campos_limpos_ao_desbloquear(self):
        from core.tasks import atualizar_bloqueio_credito_sync
        comprador = CompradorFactory(
            bloqueio_credito=True,
            bloqueio_credito_motivo='motivo antigo',
            bloqueio_credito_em=timezone.now(),
        )
        atualizar_bloqueio_credito_sync()
        comprador.refresh_from_db()
        assert comprador.bloqueio_credito_motivo == ''
        assert comprador.bloqueio_credito_em is None


class TestDesbloqueioManualView:
    def test_superuser_pode_desbloquear(self):
        superuser = SuperUserFactory()
        comprador = CompradorFactory(
            bloqueio_credito=True,
            bloqueio_credito_motivo='teste',
            bloqueio_credito_em=timezone.now(),
        )
        c = Client()
        c.force_login(superuser)
        resp = c.post(
            reverse('core:comprador_desbloquear', kwargs={'pk': comprador.pk}),
            secure=True,
        )
        assert resp.status_code in (302, 200)
        comprador.refresh_from_db()
        assert comprador.bloqueio_credito is False

    def test_usuario_comum_recebe_403(self):
        user = UserFactory()
        comprador = CompradorFactory(bloqueio_credito=True)
        c = Client()
        c.force_login(user)
        resp = c.post(
            reverse('core:comprador_desbloquear', kwargs={'pk': comprador.pk}),
            secure=True,
        )
        assert resp.status_code == 403

    def test_desbloqueio_manual_gera_log(self):
        from core.models import LogAuditoria
        superuser = SuperUserFactory()
        comprador = CompradorFactory(
            bloqueio_credito=True,
            bloqueio_credito_em=timezone.now(),
        )
        c = Client()
        c.force_login(superuser)
        c.post(
            reverse('core:comprador_desbloquear', kwargs={'pk': comprador.pk}),
            secure=True,
        )
        assert LogAuditoria.objects.filter(
            acao='DESBLOQUEIO_CREDITO', entidade='Comprador', entidade_pk=comprador.pk
        ).exists()


class TestWizardBloqueioStep1:
    def _client(self, user):
        c = Client()
        c.force_login(user)
        return c

    def _payload_basico(self, comprador, imovel):
        from datetime import date
        return {
            'imobiliaria': imovel.imobiliaria.pk,
            'comprador': comprador.pk,
            'imovel': imovel.pk,
            'numero_contrato': 'CTR-2026-0001',
            'data_contrato': date.today().isoformat(),
            'data_primeiro_vencimento': (date.today() + timedelta(days=30)).isoformat(),
            'valor_total': '100000',
            'valor_entrada': '10000',
            'numero_parcelas': '60',
            'dia_vencimento': '10',
            'tipo_amortizacao': 'PRICE',
            'tipo_correcao': 'IPCA',
            'prazo_reajuste_meses': '12',
            'tipo_correcao_fallback': 'IGPM',
            'spread_reajuste': '0',
            'reajuste_piso': '0',
            'reajuste_teto': '20',
            'percentual_juros_mora': '1',
            'percentual_multa': '2',
        }

    def test_usuario_comum_bloqueado_nao_passa(self):
        from tests.fixtures.factories import ImovelFactory
        user = UserFactory()
        comprador = CompradorFactory(bloqueio_credito=True)
        imovel = ImovelFactory()
        resp = self._client(user).post(
            reverse('contratos:wizard', kwargs={'step': 'basico'}),
            data=self._payload_basico(comprador, imovel),
            secure=True,
        )
        assert resp.status_code == 200
        assert b'bloqueio' in resp.content.lower() or b'inadimpl' in resp.content.lower() or b'administrador' in resp.content.lower()

    def test_superuser_sem_confirmar_ve_banner(self):
        from tests.fixtures.factories import ImovelFactory
        superuser = SuperUserFactory()
        comprador = CompradorFactory(bloqueio_credito=True)
        imovel = ImovelFactory()
        resp = self._client(superuser).post(
            reverse('contratos:wizard', kwargs={'step': 'basico'}),
            data=self._payload_basico(comprador, imovel),
            secure=True,
        )
        assert resp.status_code == 200
        assert b'confirmar_bloqueio' in resp.content

    def test_superuser_com_confirmacao_avanca(self):
        from tests.fixtures.factories import ImovelFactory
        superuser = SuperUserFactory()
        comprador = CompradorFactory(bloqueio_credito=True)
        imovel = ImovelFactory()
        payload = self._payload_basico(comprador, imovel)
        payload['confirmar_bloqueio'] = '1'
        resp = self._client(superuser).post(
            reverse('contratos:wizard', kwargs={'step': 'basico'}),
            data=payload,
            secure=True,
        )
        assert resp.status_code == 302
        assert 'juros' in resp['Location']

    def test_comprador_sem_bloqueio_avanca_normalmente(self):
        from tests.fixtures.factories import ImovelFactory
        user = UserFactory()
        comprador = CompradorFactory(bloqueio_credito=False)
        imovel = ImovelFactory()
        resp = self._client(user).post(
            reverse('contratos:wizard', kwargs={'step': 'basico'}),
            data=self._payload_basico(comprador, imovel),
            secure=True,
        )
        assert resp.status_code == 302
        assert 'juros' in resp['Location']
