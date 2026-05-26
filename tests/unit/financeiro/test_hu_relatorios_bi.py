"""
34.5 P3 — Relatórios Agendados e Exportação para BI

Testa:
  34.5.1 — enviar_relatorio_inadimplencia (task Celery)
  34.5.2 — enviar_relatorio_posicao_contratos (task Celery)
  34.5.3 — GET /financeiro/api/relatorios/posicao/ (API BI)
  34.5.4 — GET /financeiro/api/dashboard-executivo/ (dados do dashboard executivo)
"""
import json
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures compartilhadas (pytest)
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio_bi(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ImovelFactory, CompradorFactory, ContaBancariaFactory,
    )
    imob = ImobiliariaFactory(nome='Imob BI Test')
    ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador BI')
    return imob, imovel, comprador


@pytest.fixture
def contrato_com_parcelas(db, dominio_bi):
    from contratos.models import Contrato, TipoAmortizacao, TipoCorrecao, StatusContrato
    from financeiro.models import Parcela

    imob, imovel, comprador = dominio_bi
    hoje = timezone.now().date()

    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='BI-001',
        data_contrato=date(2024, 1, 1),
        data_primeiro_vencimento=date(2024, 2, 1),
        valor_total=Decimal('60000.00'),
        valor_entrada=Decimal('6000.00'),
        numero_parcelas=6,
        dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA,
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
    )
    # Ajusta parcelas: 2 vencidas, 1 paga, 3 futuras
    parcelas = list(contrato.parcelas.order_by('numero_parcela'))
    for i, p in enumerate(parcelas):
        if i == 0:
            p.pago = True
            p.valor_pago = p.valor_atual
            p.data_pagamento = hoje - timedelta(days=60)
            p.data_vencimento = hoje - timedelta(days=60)
        elif i in (1, 2):
            p.pago = False
            p.data_vencimento = hoje - timedelta(days=35 + i * 30)
        else:
            p.pago = False
            p.data_vencimento = hoje + timedelta(days=15 + i * 30)
        p.save()
    return contrato, parcelas


@pytest.fixture
def staff_user(db):
    return User.objects.create_user('staff_bi', password='pass', is_staff=True)


# ---------------------------------------------------------------------------
# 34.5.1 — Task: enviar_relatorio_inadimplencia
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnviarRelatorioInadimplencia:

    @patch('django.core.mail.EmailMultiAlternatives.send', return_value=1)
    @patch('django.conf.settings.RELATORIO_INADIMPLENCIA_EMAILS', ['gestor@test.com'])
    def test_envia_email_quando_ha_destinatarios(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_inadimplencia
        resultado = enviar_relatorio_inadimplencia(frequencia='diario')
        assert resultado['enviado'] is True
        assert resultado['destinatarios'] == 1
        mock_send.assert_called_once()

    @patch('django.conf.settings.RELATORIO_INADIMPLENCIA_EMAILS', [])
    def test_nao_envia_sem_destinatarios(self):
        from financeiro.tasks import enviar_relatorio_inadimplencia
        resultado = enviar_relatorio_inadimplencia()
        assert resultado['enviado'] is False
        assert resultado['motivo'] == 'sem_destinatarios'

    @patch('django.core.mail.EmailMultiAlternatives.send', return_value=1)
    @patch('django.conf.settings.RELATORIO_INADIMPLENCIA_EMAILS', ['a@b.com'])
    def test_resultado_inclui_total_vencidas(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_inadimplencia
        resultado = enviar_relatorio_inadimplencia()
        assert 'total_vencidas' in resultado
        assert resultado['total_vencidas'] >= 2

    @patch('django.core.mail.EmailMultiAlternatives.send', return_value=1)
    @patch('django.conf.settings.RELATORIO_INADIMPLENCIA_EMAILS', ['a@b.com'])
    def test_frequencia_semanal_aceita(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_inadimplencia
        resultado = enviar_relatorio_inadimplencia(frequencia='semanal')
        assert resultado['enviado'] is True

    @patch('django.core.mail.EmailMultiAlternatives.send', side_effect=Exception('SMTP error'))
    @patch('django.conf.settings.RELATORIO_INADIMPLENCIA_EMAILS', ['x@y.com'])
    def test_captura_erro_smtp(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_inadimplencia
        resultado = enviar_relatorio_inadimplencia()
        assert resultado['enviado'] is False
        assert 'erro' in resultado


# ---------------------------------------------------------------------------
# 34.5.2 — Task: enviar_relatorio_posicao_contratos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnviarRelatorioPosicaoContratos:

    @patch('django.core.mail.EmailMessage.send', return_value=1)
    @patch('django.conf.settings.RELATORIO_POSICAO_EMAILS', ['conta@test.com'])
    def test_envia_excel_quando_ha_destinatarios(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_posicao_contratos
        resultado = enviar_relatorio_posicao_contratos(formato='excel')
        assert resultado['enviado'] is True
        assert resultado['destinatarios'] == 1
        mock_send.assert_called_once()

    @patch('django.conf.settings.RELATORIO_POSICAO_EMAILS', [])
    def test_nao_envia_sem_destinatarios(self):
        from financeiro.tasks import enviar_relatorio_posicao_contratos
        resultado = enviar_relatorio_posicao_contratos()
        assert resultado['enviado'] is False
        assert resultado['motivo'] == 'sem_destinatarios'

    @patch('django.core.mail.EmailMessage.send', return_value=1)
    @patch('django.conf.settings.RELATORIO_POSICAO_EMAILS', ['a@b.com'])
    def test_resultado_inclui_total_contratos(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_posicao_contratos
        resultado = enviar_relatorio_posicao_contratos()
        assert 'total_contratos' in resultado
        assert resultado['total_contratos'] >= 1

    @patch('django.core.mail.EmailMessage.send', side_effect=Exception('timeout'))
    @patch('django.conf.settings.RELATORIO_POSICAO_EMAILS', ['z@w.com'])
    def test_captura_erro_envio(self, mock_send, contrato_com_parcelas):
        from financeiro.tasks import enviar_relatorio_posicao_contratos
        resultado = enviar_relatorio_posicao_contratos()
        assert resultado['enviado'] is False
        assert 'erro' in resultado


# ---------------------------------------------------------------------------
# 34.5.3 — API BI: GET /financeiro/api/relatorios/posicao/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiRelatorioPosicaoBI:

    @pytest.fixture(autouse=True)
    def setup(self, contrato_com_parcelas):
        self.client = Client()
        self.url = reverse('financeiro:api_relatorio_posicao_bi')

    @patch('django.conf.settings.DEBUG', True)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_retorna_json_sem_token_apenas_em_debug(self):
        # Em DEBUG, token vazio é tolerado (dev/staging)
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert 'itens' in data
        assert 'totalizadores' in data

    @patch('django.conf.settings.DEBUG', False)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_fail_closed_em_producao_sem_token(self):
        # Fail-closed: em produção sem token configurado, retorna 503
        resp = self.client.get(self.url)
        assert resp.status_code == 503

    @patch('django.conf.settings.BI_API_TOKEN', 'secret123')
    def test_rejeita_sem_token(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 401

    @patch('django.conf.settings.BI_API_TOKEN', 'secret123')
    def test_aceita_bearer_token(self):
        resp = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer secret123')
        assert resp.status_code == 200

    @patch('django.conf.settings.BI_API_TOKEN', 'secret123')
    def test_aceita_api_key_header(self):
        resp = self.client.get(self.url, HTTP_X_API_KEY='secret123')
        assert resp.status_code == 200

    @patch('django.conf.settings.DEBUG', True)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_formato_json_tem_campos_obrigatorios(self):
        resp = self.client.get(self.url + '?formato=json')
        assert resp.status_code == 200
        data = resp.json()
        assert 'gerado_em' in data
        assert 'totalizadores' in data
        assert 'itens' in data
        totais = data['totalizadores']
        assert 'total_contratos' in totais
        assert 'total_saldo_devedor' in totais

    @patch('django.conf.settings.DEBUG', True)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_itens_tem_campos_do_contrato(self):
        resp = self.client.get(self.url)
        data = resp.json()
        assert len(data['itens']) >= 1
        item = data['itens'][0]
        for campo in ['contrato_numero', 'comprador_nome', 'saldo_devedor', 'progresso_percentual']:
            assert campo in item, f'Campo ausente: {campo}'

    @patch('django.conf.settings.DEBUG', True)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_formato_csv_retorna_content_type_correto(self):
        resp = self.client.get(self.url + '?formato=csv')
        assert resp.status_code == 200
        assert 'text/csv' in resp['Content-Type']
        assert 'posicao_contratos.csv' in resp.get('Content-Disposition', '')

    @patch('django.conf.settings.DEBUG', True)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_formato_csv_tem_cabecalho(self):
        resp = self.client.get(self.url + '?formato=csv')
        content = resp.content.decode('utf-8')
        assert 'contrato_numero' in content
        assert 'saldo_devedor' in content

    @patch('django.conf.settings.DEBUG', True)
    @patch('django.conf.settings.BI_API_TOKEN', '')
    def test_imobiliaria_id_invalido_retorna_400(self):
        resp = self.client.get(self.url + '?imobiliaria_id=abc')
        assert resp.status_code == 400

    def test_recusa_post(self):
        resp = self.client.post(self.url, {})
        assert resp.status_code == 405


# ---------------------------------------------------------------------------
# 34.5.4 — Dashboard executivo: GET /financeiro/api/dashboard-executivo/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiDashboardExecutivo:

    @pytest.fixture(autouse=True)
    def setup(self, contrato_com_parcelas, staff_user):
        self.client = Client()
        self.client.force_login(staff_user)
        self.url = reverse('financeiro:api_dashboard_executivo')

    def test_requer_autenticacao(self):
        c = Client()
        resp = c.get(self.url)
        assert resp.status_code != 200

    def test_retorna_200_autenticado(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_estrutura_resposta(self):
        resp = self.client.get(self.url)
        data = resp.json()
        for campo in ['labels', 'receita_prevista', 'receita_realizada', 'inadimplencia', 'kpis']:
            assert campo in data, f'Campo ausente: {campo}'

    def test_labels_tem_12_meses(self):
        resp = self.client.get(self.url)
        data = resp.json()
        assert len(data['labels']) == 12
        assert len(data['receita_prevista']) == 12
        assert len(data['receita_realizada']) == 12
        assert len(data['inadimplencia']) == 12

    def test_kpis_tem_campos_esperados(self):
        resp = self.client.get(self.url)
        data = resp.json()
        kpis = data['kpis']
        for campo in ['contratos_ativos', 'total_previsto', 'total_recebido', 'total_vencido', 'count_vencido']:
            assert campo in kpis, f'KPI ausente: {campo}'

    def test_kpis_sao_numericos(self):
        resp = self.client.get(self.url)
        data = resp.json()
        kpis = data['kpis']
        assert isinstance(kpis['contratos_ativos'], int)
        assert isinstance(kpis['total_vencido'], float)

    def test_inadimplencia_nao_negativa(self):
        resp = self.client.get(self.url)
        data = resp.json()
        for v in data['inadimplencia']:
            assert v >= 0

    def test_imobiliaria_id_invalido_retorna_400(self):
        resp = self.client.get(self.url + '?imobiliaria_id=abc')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestApiDashboardExecutivoTenantIsolation:
    """Code-review fix: usuário não-staff só vê suas imobiliárias."""

    def test_usuario_sem_permissao_total_ve_zero_se_nao_pertence_a_imobiliaria(self, contrato_com_parcelas):
        # Usuário comum (não staff, sem AcessoUsuario) → get_imobiliarias_usuario retorna vazio
        from tests.fixtures.factories import UserFactory
        user = UserFactory(is_staff=False, is_superuser=False)
        client = Client()
        client.force_login(user)
        url = reverse('financeiro:api_dashboard_executivo')
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        # Sem acesso a nenhuma imobiliária, KPIs devem ser zero
        assert data['kpis']['contratos_ativos'] == 0
        assert data['kpis']['total_recebido'] == 0
        assert data['kpis']['total_previsto'] == 0
