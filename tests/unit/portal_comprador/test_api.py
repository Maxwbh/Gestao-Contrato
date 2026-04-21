"""
Testes das APIs JSON do app portal_comprador

Testa:
- api_parcelas_contrato
- api_resumo_financeiro
- api_portal_vencimentos (P2)
- api_portal_boletos (P2)
- api_portal_linha_digitavel (P3)
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from portal_comprador.models import AcessoComprador
from contratos.models import Contrato, StatusContrato
from tests.fixtures.factories import (
    UserFactory,
    CompradorFactory,
    ContratoFactory,
    ParcelaFactory,
    ImovelFactory,
)


@pytest.fixture
def comprador_logado(client):
    """Fixture que retorna um comprador logado e seus objetos relacionados"""
    comprador = CompradorFactory()
    usuario = UserFactory()
    acesso = AcessoComprador.objects.create(
        comprador=comprador,
        usuario=usuario
    )
    client.force_login(usuario)
    return {
        'comprador': comprador,
        'usuario': usuario,
        'acesso': acesso,
        'client': client,
    }


@pytest.mark.django_db
class TestApiParcelasContrato:
    """Testes da API de parcelas por contrato"""

    def test_api_parcelas_requer_login(self, client):
        """Testa que API requer autenticacao"""
        response = client.get('/portal/api/contratos/1/parcelas/')

        assert response.status_code == 302

    def test_api_parcelas_contrato_de_outro_comprador(self, comprador_logado):
        """Testa acesso a parcelas de contrato de outro comprador"""
        client = comprador_logado['client']

        # Criar contrato de outro comprador
        outro_comprador = CompradorFactory()
        contrato = ContratoFactory(comprador=outro_comprador)

        response = client.get(f'/portal/api/contratos/{contrato.id}/parcelas/')

        assert response.status_code == 404

    def test_api_parcelas_retorna_json(self, comprador_logado):
        """Testa que API retorna JSON com parcelas"""
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']

        # Criar contrato com parcelas
        imovel = ImovelFactory()
        contrato = Contrato.objects.create(
            imovel=imovel,
            comprador=comprador,
            imobiliaria=imovel.imobiliaria,
            numero_contrato='CTR-API-001',
            data_contrato=date.today() - timedelta(days=30),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=12,
            dia_vencimento=5,
            status=StatusContrato.ATIVO,
        )
        response = client.get(f'/portal/api/contratos/{contrato.id}/parcelas/')

        assert response.status_code == 200
        data = response.json()
        assert data['sucesso'] is True
        assert 'parcelas' in data
        assert data['total'] >= 1  # At least auto-generated parcelas exist


@pytest.mark.django_db
class TestApiResumoFinanceiro:
    """Testes da API de resumo financeiro"""

    def test_api_resumo_requer_login(self, client):
        """Testa que API requer autenticacao"""
        response = client.get('/portal/api/resumo-financeiro/')

        assert response.status_code == 302

    def test_api_resumo_retorna_json(self, comprador_logado):
        """Testa que API retorna JSON com resumo"""
        client = comprador_logado['client']

        response = client.get('/portal/api/resumo-financeiro/')

        assert response.status_code == 200
        data = response.json()
        assert data['sucesso'] is True
        assert 'resumo' in data


# =============================================================================
# FASE 9 P2 — api_portal_vencimentos
# =============================================================================

@pytest.mark.django_db
class TestApiPortalVencimentos:
    """Testes da API de vencimentos (P2)"""

    def test_vencimentos_requer_login(self, client):
        response = client.get('/portal/api/vencimentos/')
        assert response.status_code == 302

    def test_vencimentos_retorna_apenas_do_comprador(self, comprador_logado):
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']

        # Parcela do comprador logado
        contrato_proprio = ContratoFactory(comprador=comprador)
        ParcelaFactory(contrato=contrato_proprio, pago=False,
                       data_vencimento=date.today() + timedelta(days=10))

        # Parcela de outro comprador — não deve aparecer
        outro = CompradorFactory()
        contrato_alheio = ContratoFactory(comprador=outro)
        ParcelaFactory(contrato=contrato_alheio, pago=False,
                       data_vencimento=date.today() + timedelta(days=10))

        response = client.get('/portal/api/vencimentos/')
        assert response.status_code == 200
        data = response.json()
        assert data['sucesso'] is True
        ids_contratos = {p['contrato']['id'] for p in data['parcelas']}
        assert contrato_alheio.id not in ids_contratos

    def test_vencimentos_filtro_status_pago(self, comprador_logado):
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']
        contrato = ContratoFactory(comprador=comprador)
        ParcelaFactory(contrato=contrato, pago=True,
                       data_vencimento=date.today() - timedelta(days=5))

        response = client.get('/portal/api/vencimentos/?status=pago')
        assert response.status_code == 200
        data = response.json()
        assert all(p['pago'] for p in data['parcelas'])

    def test_vencimentos_paginacao(self, comprador_logado):
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']
        contrato = ContratoFactory(comprador=comprador)
        for i in range(5):
            ParcelaFactory(contrato=contrato, pago=False,
                           data_vencimento=date.today() + timedelta(days=i + 1))

        response = client.get('/portal/api/vencimentos/?per_page=2&page=1')
        assert response.status_code == 200
        data = response.json()
        assert len(data['parcelas']) <= 2
        assert data['per_page'] == 2
        assert data['page'] == 1


# =============================================================================
# FASE 9 P2 — api_portal_boletos
# =============================================================================

@pytest.mark.django_db
class TestApiPortalBoletos:
    """Testes da API de boletos (P2)"""

    def test_boletos_requer_login(self, client):
        response = client.get('/portal/api/boletos/')
        assert response.status_code == 302

    def test_boletos_exclui_nao_gerados(self, comprador_logado):
        """NAO_GERADO não aparece na listagem de boletos"""
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']
        contrato = ContratoFactory(comprador=comprador)
        # parcela sem boleto
        ParcelaFactory(contrato=contrato, status_boleto='NAO_GERADO')

        response = client.get('/portal/api/boletos/')
        assert response.status_code == 200
        data = response.json()
        assert data['sucesso'] is True
        # nenhum boleto com status NAO_GERADO deve aparecer
        for b in data['boletos']:
            assert b['status_boleto'] != 'NAO_GERADO'

    def test_boletos_filtro_status(self, comprador_logado):
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']
        contrato = ContratoFactory(comprador=comprador)
        ParcelaFactory(contrato=contrato, status_boleto='GERADO',
                       nosso_numero='0001234')

        response = client.get('/portal/api/boletos/?status_boleto=GERADO')
        assert response.status_code == 200
        data = response.json()
        for b in data['boletos']:
            assert b['status_boleto'] == 'GERADO'


# =============================================================================
# FASE 9 P3 — api_portal_linha_digitavel
# =============================================================================

@pytest.mark.django_db
class TestApiPortalLinhaDigitavel:
    """Testes da API de linha digitável (P3)"""

    def test_linha_digitavel_requer_login(self, client):
        parcela = ParcelaFactory()
        response = client.get(f'/portal/api/boletos/{parcela.id}/linha-digitavel/')
        assert response.status_code == 302

    def test_linha_digitavel_sem_nosso_numero_retorna_404(self, comprador_logado):
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']
        contrato = ContratoFactory(comprador=comprador)
        parcela = ParcelaFactory(contrato=contrato, nosso_numero='')

        response = client.get(f'/portal/api/boletos/{parcela.id}/linha-digitavel/')
        assert response.status_code == 404

    def test_linha_digitavel_de_outro_comprador_retorna_404(self, comprador_logado):
        client = comprador_logado['client']
        outro = CompradorFactory()
        contrato = ContratoFactory(comprador=outro)
        parcela = ParcelaFactory(contrato=contrato, nosso_numero='9999')

        response = client.get(f'/portal/api/boletos/{parcela.id}/linha-digitavel/')
        assert response.status_code == 404

    def test_linha_digitavel_retorna_dados_corretos(self, comprador_logado):
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']
        contrato = ContratoFactory(comprador=comprador)
        parcela = ParcelaFactory(
            contrato=contrato,
            nosso_numero='0001',
            linha_digitavel='12345.67890 12345.678901 12345.678901 1 12340000100000',
            status_boleto='GERADO',
        )

        response = client.get(f'/portal/api/boletos/{parcela.id}/linha-digitavel/')
        assert response.status_code == 200
        data = response.json()
        assert data['sucesso'] is True
        assert data['nosso_numero'] == '0001'
        assert 'linha_digitavel' in data
        assert 'valor' in data
