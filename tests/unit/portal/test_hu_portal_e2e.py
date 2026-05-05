"""
HU Portal do Comprador — Seção 7.9.4
======================================

Cobre o ciclo completo de uso do Portal do Comprador:
  login → dashboard → contratos → detalhe do contrato → vencimentos → boletos

Cenários testados:
  - Acesso sem autenticação redireciona para login do portal
  - Login page acessível sem auth
  - Dashboard retorna 200 com dados do comprador autenticado
  - Meus Contratos lista apenas contratos do próprio comprador
  - Detalhe Contrato retorna 200 para contrato próprio, 404 para de outro comprador
  - Meus Boletos retorna 200
  - API vencimentos retorna JSON
  - API boletos retorna JSON
  - Dados do comprador retorna 200
  - Fluxo E2E completo: auth → dashboard → contratos → detalhe → APIs
"""

import pytest
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio(db):
    """Domínio básico com imobiliária, imovel e comprador."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    imob = ImobiliariaFactory(nome='Imobiliária Portal')
    ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador Portal')
    return imob, imovel, comprador


@pytest.fixture
def comprador_com_acesso(db, dominio):
    """
    Comprador com AcessoComprador vinculado a um User Django.
    Retorna (comprador, user, client_logado).
    """
    from portal_comprador.models import AcessoComprador

    imob, imovel, comprador = dominio
    user = User.objects.create_user(
        username=f'portal_{comprador.cpf or comprador.pk}',
        password='PortalPass1!',
        email=comprador.email or 'portal@test.com',
    )
    AcessoComprador.objects.create(
        comprador=comprador,
        usuario=user,
        ativo=True,
        email_verificado=True,
    )
    cli = Client()
    cli.force_login(user)
    return comprador, user, cli


@pytest.fixture
def contrato_portal(db, dominio, comprador_com_acesso):
    """Contrato ATIVO para o comprador do portal."""
    from contratos.models import (
        Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
    )
    imob, imovel, _ = dominio
    comprador, _, _ = comprador_com_acesso

    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='CTR-PORTAL-001',
        data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('120000.00'),
        valor_entrada=Decimal('20000.00'),
        numero_parcelas=12,
        dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA,
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
    )
    return contrato


@pytest.fixture
def outro_comprador_com_contrato(db, dominio):
    """Comprador diferente com seu próprio contrato (para testes de isolamento)."""
    from tests.fixtures.factories import CompradorFactory, ImovelFactory
    from contratos.models import (
        Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
    )
    imob, _, _ = dominio
    outro_imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    outro_comprador = CompradorFactory(nome='Outro Comprador')

    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=outro_imovel,
        comprador=outro_comprador,
        numero_contrato='CTR-PORTAL-OUTRO',
        data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('80000.00'),
        valor_entrada=Decimal('10000.00'),
        numero_parcelas=12,
        dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA,
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
    )
    return outro_comprador, contrato


# ---------------------------------------------------------------------------
# TestPortalAuth — acesso sem autenticação
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPortalAuth:
    """Testes de autenticação do portal."""

    def test_login_page_acessivel_sem_auth(self, client):
        resp = client.get(reverse('portal_comprador:login'))
        assert resp.status_code == 200

    def test_dashboard_redireciona_sem_auth(self, client):
        resp = client.get(reverse('portal_comprador:dashboard'))
        assert resp.status_code in (302, 403)

    def test_contratos_redireciona_sem_auth(self, client):
        resp = client.get(reverse('portal_comprador:meus_contratos'))
        assert resp.status_code in (302, 403)

    def test_boletos_redireciona_sem_auth(self, client):
        resp = client.get(reverse('portal_comprador:meus_boletos'))
        assert resp.status_code in (302, 403)

    def test_api_vencimentos_redireciona_sem_auth(self, client):
        resp = client.get(reverse('portal_comprador:api_portal_vencimentos'))
        assert resp.status_code in (302, 403)


# ---------------------------------------------------------------------------
# TestPortalDashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPortalDashboard:
    """Testes do dashboard do comprador autenticado."""

    def test_dashboard_retorna_200_logado(self, comprador_com_acesso):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:dashboard'))
        assert resp.status_code == 200

    def test_dashboard_contem_dados_do_comprador(self, comprador_com_acesso, contrato_portal):
        comprador, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:dashboard'))
        assert resp.status_code == 200
        assert 'comprador' in resp.context

    def test_dashboard_nao_vaza_dados_de_outro_comprador(
        self, comprador_com_acesso, outro_comprador_com_contrato
    ):
        """Dashboard não deve mostrar contratos de outro comprador."""
        _, _, cli = comprador_com_acesso
        _, contrato_outro = outro_comprador_com_contrato
        resp = cli.get(reverse('portal_comprador:dashboard'))
        assert resp.status_code == 200
        # Contratos no contexto pertencem apenas ao comprador logado
        if 'contratos' in resp.context:
            for c in resp.context['contratos']:
                assert c.numero_contrato != contrato_outro.numero_contrato


# ---------------------------------------------------------------------------
# TestPortalContratos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPortalContratos:
    """Testes da listagem e detalhe de contratos no portal."""

    def test_meus_contratos_retorna_200(self, comprador_com_acesso):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:meus_contratos'))
        assert resp.status_code == 200

    def test_meus_contratos_lista_apenas_proprios(self, comprador_com_acesso, contrato_portal,
                                                   outro_comprador_com_contrato):
        comprador, _, cli = comprador_com_acesso
        _, contrato_outro = outro_comprador_com_contrato
        resp = cli.get(reverse('portal_comprador:meus_contratos'))
        assert resp.status_code == 200
        if 'contratos' in resp.context:
            nums = [c.numero_contrato for c in resp.context['contratos']]
            assert 'CTR-PORTAL-001' in nums
            assert 'CTR-PORTAL-OUTRO' not in nums

    def test_detalhe_contrato_proprio_retorna_200(self, comprador_com_acesso, contrato_portal):
        _, _, cli = comprador_com_acesso
        url = reverse('portal_comprador:detalhe_contrato',
                      kwargs={'contrato_id': contrato_portal.pk})
        resp = cli.get(url)
        assert resp.status_code == 200

    def test_detalhe_contrato_outro_comprador_retorna_404(
        self, comprador_com_acesso, outro_comprador_com_contrato
    ):
        """Comprador não pode ver contrato de outra pessoa."""
        _, _, cli = comprador_com_acesso
        _, contrato_outro = outro_comprador_com_contrato
        url = reverse('portal_comprador:detalhe_contrato',
                      kwargs={'contrato_id': contrato_outro.pk})
        resp = cli.get(url)
        assert resp.status_code == 404

    def test_detalhe_contrato_inexistente_retorna_404(self, comprador_com_acesso):
        _, _, cli = comprador_com_acesso
        url = reverse('portal_comprador:detalhe_contrato', kwargs={'contrato_id': 999999})
        resp = cli.get(url)
        assert resp.status_code == 404

    def test_detalhe_contrato_contem_parcelas_no_contexto(self,
                                                           comprador_com_acesso,
                                                           contrato_portal):
        _, _, cli = comprador_com_acesso
        url = reverse('portal_comprador:detalhe_contrato',
                      kwargs={'contrato_id': contrato_portal.pk})
        resp = cli.get(url)
        assert resp.status_code == 200
        assert 'parcelas' in resp.context
        assert 'stats_parcelas' in resp.context


# ---------------------------------------------------------------------------
# TestPortalBoletos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPortalBoletos:
    """Testes da área de boletos do portal."""

    def test_meus_boletos_retorna_200(self, comprador_com_acesso):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:meus_boletos'))
        assert resp.status_code == 200

    def test_meus_dados_retorna_200(self, comprador_com_acesso):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:meus_dados'))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestPortalAPIs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPortalAPIs:
    """Testes das APIs JSON do portal."""

    def test_api_vencimentos_retorna_json(self, comprador_com_acesso, contrato_portal):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:api_portal_vencimentos'))
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('application/json')

    def test_api_boletos_retorna_json(self, comprador_com_acesso, contrato_portal):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:api_portal_boletos'))
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('application/json')

    def test_api_parcelas_contrato_retorna_json(self, comprador_com_acesso, contrato_portal):
        _, _, cli = comprador_com_acesso
        url = reverse('portal_comprador:api_parcelas_contrato',
                      kwargs={'contrato_id': contrato_portal.pk})
        resp = cli.get(url)
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('application/json')

    def test_api_resumo_financeiro_retorna_json(self, comprador_com_acesso, contrato_portal):
        _, _, cli = comprador_com_acesso
        resp = cli.get(reverse('portal_comprador:api_resumo_financeiro'))
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('application/json')

    def test_api_vencimentos_sem_auth_nega_acesso(self, client):
        resp = client.get(reverse('portal_comprador:api_portal_vencimentos'))
        assert resp.status_code in (302, 403)

    def test_api_parcelas_contrato_outro_comprador_nega_acesso(
        self, comprador_com_acesso, outro_comprador_com_contrato
    ):
        """API de parcelas não deve expor contratos de outro comprador."""
        _, _, cli = comprador_com_acesso
        _, contrato_outro = outro_comprador_com_contrato
        url = reverse('portal_comprador:api_parcelas_contrato',
                      kwargs={'contrato_id': contrato_outro.pk})
        resp = cli.get(url)
        # Deve retornar 403/404, não 200 com dados do outro comprador
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# TestFluxoCompletoPortal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFluxoCompletoPortal:
    """
    E2E: Ciclo completo de uso do portal pelo comprador.

    Passos:
      1. Login page acessível sem auth
      2. Dashboard retorna 302 sem auth
      3. Comprador autentica (force_login)
      4. Dashboard retorna 200
      5. Lista de contratos retorna 200 e inclui o contrato do comprador
      6. Detalhe do contrato retorna 200 com stats de parcelas
      7. API vencimentos retorna JSON com lista
      8. Tentativa de ver contrato de outro comprador → 404 (isolamento)
    """

    def test_fluxo_completo_portal_comprador(
        self, db, dominio, comprador_com_acesso, outro_comprador_com_contrato
    ):
        imob, imovel, _ = dominio
        comprador, user, cli = comprador_com_acesso
        _, contrato_outro = outro_comprador_com_contrato

        from contratos.models import (
            Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
        )

        # Criar contrato para o comprador principal
        contrato = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel,
            comprador=comprador,
            numero_contrato='CTR-PORTAL-E2E',
            data_contrato=date(2025, 1, 1),
            data_primeiro_vencimento=date(2025, 2, 1),
            valor_total=Decimal('120000.00'),
            valor_entrada=Decimal('20000.00'),
            numero_parcelas=12,
            dia_vencimento=1,
            tipo_amortizacao=TipoAmortizacao.PRICE,
            tipo_correcao=TipoCorrecao.IPCA,
            prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
        )

        # ── Passo 1: Login page acessível sem auth ────────────────────────
        anon = Client()
        resp = anon.get(reverse('portal_comprador:login'))
        assert resp.status_code == 200, 'Login page deve retornar 200'

        # ── Passo 2: Dashboard sem auth → redirecionamento ────────────────
        resp = anon.get(reverse('portal_comprador:dashboard'))
        assert resp.status_code in (302, 403), 'Dashboard requer auth'

        # ── Passo 3–4: Comprador autenticado → dashboard 200 ─────────────
        resp = cli.get(reverse('portal_comprador:dashboard'))
        assert resp.status_code == 200, 'Dashboard deve retornar 200'

        # ── Passo 5: Lista de contratos ───────────────────────────────────
        resp = cli.get(reverse('portal_comprador:meus_contratos'))
        assert resp.status_code == 200
        if 'contratos' in resp.context:
            nums = [c.numero_contrato for c in resp.context['contratos']]
            assert 'CTR-PORTAL-E2E' in nums
            assert 'CTR-PORTAL-OUTRO' not in nums

        # ── Passo 6: Detalhe com stats de parcelas ────────────────────────
        url = reverse('portal_comprador:detalhe_contrato',
                      kwargs={'contrato_id': contrato.pk})
        resp = cli.get(url)
        assert resp.status_code == 200
        assert 'stats_parcelas' in resp.context
        stats = resp.context['stats_parcelas']
        assert stats['total'] == 12  # 12 parcelas geradas

        # ── Passo 7: API vencimentos retorna JSON ─────────────────────────
        resp = cli.get(reverse('portal_comprador:api_portal_vencimentos'))
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert isinstance(data, (dict, list))

        # ── Passo 8: Isolamento — contrato de outro comprador → 404 ──────
        url_outro = reverse('portal_comprador:detalhe_contrato',
                            kwargs={'contrato_id': contrato_outro.pk})
        resp = cli.get(url_outro)
        assert resp.status_code == 404, (
            'Comprador não deve ver contrato de outro comprador'
        )
