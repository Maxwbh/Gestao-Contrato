"""
Testes das APIs JSON do app portal_comprador

Testa:
- api_parcelas_contrato
- api_resumo_financeiro
"""
import pytest
import json
from decimal import Decimal
from datetime import date, timedelta

from portal_comprador.models import AcessoComprador
from contratos.models import Contrato
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
            status='ATIVO',
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
