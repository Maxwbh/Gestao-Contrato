"""
Testes das views do app portal_comprador

Testa:
- Dashboard
- Meus Contratos
- Detalhe Contrato
- Meus Boletos
- Download/Visualizar Boleto
- Meus Dados
- Alterar Senha
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from portal_comprador.models import AcessoComprador, LogAcessoComprador
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
class TestDashboardView:
    """Testes da view dashboard"""

    def test_dashboard_requer_login(self, client):
        """Testa que dashboard requer autenticacao"""
        response = client.get('/portal/')

        assert response.status_code == 302
        assert 'login' in response.url

    def test_dashboard_usuario_sem_acesso_comprador(self, client):
        """Testa dashboard com usuario sem acesso de comprador"""
        usuario = UserFactory()
        client.force_login(usuario)

        response = client.get('/portal/')

        assert response.status_code == 302

    def test_dashboard_comprador_logado(self, comprador_logado):
        """Testa dashboard com comprador logado"""
        client = comprador_logado['client']

        response = client.get('/portal/')

        assert response.status_code == 200

    def test_dashboard_registra_log_acesso(self, comprador_logado):
        """Testa que dashboard registra log de acesso"""
        client = comprador_logado['client']
        acesso = comprador_logado['acesso']

        client.get('/portal/')

        log = LogAcessoComprador.objects.filter(
            acesso_comprador=acesso,
            pagina_acessada='dashboard'
        ).first()
        assert log is not None


@pytest.mark.django_db
class TestMeusContratosView:
    """Testes da view meus_contratos"""

    def test_meus_contratos_requer_login(self, client):
        """Testa que meus_contratos requer autenticacao"""
        response = client.get('/portal/contratos/')

        assert response.status_code == 302
        assert 'login' in response.url

    def test_meus_contratos_lista_contratos(self, comprador_logado):
        """Testa listagem de contratos do comprador"""
        client = comprador_logado['client']
        comprador = comprador_logado['comprador']

        # Criar contrato para o comprador
        imovel = ImovelFactory()
        Contrato.objects.create(
            imovel=imovel,
            comprador=comprador,
            imobiliaria=imovel.imobiliaria,
            numero_contrato='CTR-TEST-001',
            data_contrato=date.today() - timedelta(days=30),
            data_primeiro_vencimento=date.today() + timedelta(days=30),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=12,
            dia_vencimento=5,
            status='ATIVO',
        )

        response = client.get('/portal/contratos/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestDetalheContratoView:
    """Testes da view detalhe_contrato"""

    def test_detalhe_contrato_requer_login(self, client):
        """Testa que detalhe_contrato requer autenticacao"""
        response = client.get('/portal/contratos/1/')

        assert response.status_code == 302
        assert 'login' in response.url

    def test_detalhe_contrato_de_outro_comprador(self, comprador_logado):
        """Testa acesso a contrato de outro comprador"""
        client = comprador_logado['client']

        # Criar contrato de outro comprador
        outro_comprador = CompradorFactory()
        contrato = ContratoFactory(comprador=outro_comprador)

        response = client.get(f'/portal/contratos/{contrato.id}/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestMeusBoletosView:
    """Testes da view meus_boletos"""

    def test_meus_boletos_requer_login(self, client):
        """Testa que meus_boletos requer autenticacao"""
        response = client.get('/portal/boletos/')

        assert response.status_code == 302
        assert 'login' in response.url

    def test_meus_boletos_lista_parcelas(self, comprador_logado):
        """Testa listagem de boletos/parcelas"""
        client = comprador_logado['client']

        response = client.get('/portal/boletos/')

        assert response.status_code == 200

    def test_meus_boletos_filtro_a_pagar(self, comprador_logado):
        """Testa filtro de boletos a pagar"""
        client = comprador_logado['client']

        response = client.get('/portal/boletos/?status=a_pagar')

        assert response.status_code == 200

    def test_meus_boletos_filtro_pagos(self, comprador_logado):
        """Testa filtro de boletos pagos"""
        client = comprador_logado['client']

        response = client.get('/portal/boletos/?status=pagos')

        assert response.status_code == 200

    def test_meus_boletos_filtro_vencidos(self, comprador_logado):
        """Testa filtro de boletos vencidos"""
        client = comprador_logado['client']

        response = client.get('/portal/boletos/?status=vencidos')

        assert response.status_code == 200


@pytest.mark.django_db
class TestDownloadBoletoView:
    """Testes da view download_boleto"""

    def test_download_boleto_requer_login(self, client):
        """Testa que download_boleto requer autenticacao"""
        response = client.get('/portal/boletos/1/download/')

        assert response.status_code == 302

    def test_download_boleto_de_outro_comprador(self, comprador_logado):
        """Testa download de boleto de outro comprador"""
        client = comprador_logado['client']

        # Criar parcela de outro comprador
        outro_comprador = CompradorFactory()
        contrato = ContratoFactory(comprador=outro_comprador)
        parcela = ParcelaFactory(contrato=contrato)

        response = client.get(f'/portal/boletos/{parcela.id}/download/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestMeusDadosView:
    """Testes da view meus_dados"""

    def test_meus_dados_requer_login(self, client):
        """Testa que meus_dados requer autenticacao"""
        response = client.get('/portal/meus-dados/')

        assert response.status_code == 302
        assert 'login' in response.url

    def test_meus_dados_get(self, comprador_logado):
        """Testa acesso GET a meus_dados"""
        client = comprador_logado['client']

        response = client.get('/portal/meus-dados/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestAlterarSenhaView:
    """Testes da view alterar_senha"""

    def test_alterar_senha_requer_login(self, client):
        """Testa que alterar_senha requer autenticacao"""
        response = client.get('/portal/alterar-senha/')

        assert response.status_code == 302
        assert 'login' in response.url

    def test_alterar_senha_get(self, comprador_logado):
        """Testa acesso GET a alterar_senha"""
        client = comprador_logado['client']

        response = client.get('/portal/alterar-senha/')

        assert response.status_code == 200

    def test_alterar_senha_post_sucesso(self, comprador_logado):
        """Testa alteracao de senha bem sucedida"""
        client = comprador_logado['client']
        usuario = comprador_logado['usuario']

        # Definir senha inicial
        usuario.set_password('senhaatual123')
        usuario.save()
        client.force_login(usuario)

        response = client.post('/portal/alterar-senha/', {
            'senha_atual': 'senhaatual123',
            'nova_senha': 'novaSenha456',
            'confirmar_senha': 'novaSenha456',
        })

        assert response.status_code == 302

    def test_alterar_senha_senha_incorreta(self, comprador_logado):
        """Testa alteracao com senha atual incorreta"""
        client = comprador_logado['client']

        response = client.post('/portal/alterar-senha/', {
            'senha_atual': 'senhaerrada',
            'nova_senha': 'novaSenha456',
            'confirmar_senha': 'novaSenha456',
        })

        assert response.status_code == 200  # Retorna ao form com erro
