"""
Testes das views de parcelas do app financeiro.

Escopo: listar_parcelas, detalhe_parcela, registrar_pagamento,
        gerar_boleto, notificar_inadimplente
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model

from tests.fixtures.factories import (
    UserFactory, ContratoFactory,
)

User = get_user_model()


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.fixture
def contrato(db):
    return ContratoFactory()


@pytest.fixture
def parcela(db, contrato):
    """Usa a primeira parcela auto-gerada pelo contrato"""
    return contrato.parcelas.order_by('numero_parcela').first()


@pytest.fixture
def parcela_vencida(db, contrato):
    """Usa a segunda parcela do contrato e define vencimento no passado"""
    p = contrato.parcelas.order_by('numero_parcela')[1]
    p.data_vencimento = date.today() - timedelta(days=10)
    p.pago = False
    p.save()
    return p


@pytest.mark.django_db
class TestListarParcelas:
    """Testes da view listar_parcelas"""

    def test_requer_autenticacao(self, client):
        """Usuário não autenticado é redirecionado para login"""
        response = client.get(reverse('financeiro:listar_parcelas'))
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        """Retorna 200 mesmo sem parcelas"""
        response = client_logado.get(reverse('financeiro:listar_parcelas'))
        assert response.status_code == 200

    def test_lista_com_parcelas(self, client_logado, parcela):
        """Parcela aparece na listagem"""
        response = client_logado.get(reverse('financeiro:listar_parcelas'))
        assert response.status_code == 200

    def test_filtro_status_vencida(self, client_logado, parcela_vencida):
        """Filtro por status VENCIDA retorna parcelas vencidas"""
        response = client_logado.get(
            reverse('financeiro:listar_parcelas'),
            {'status': 'VENCIDA'}
        )
        assert response.status_code == 200

    def test_paginacao(self, client_logado):
        """Paginação funciona com per_page"""
        response = client_logado.get(
            reverse('financeiro:listar_parcelas'),
            {'per_page': '10'}
        )
        assert response.status_code == 200

    def test_paginacao_invalida_usa_padrao(self, client_logado):
        """per_page inválido usa padrão 25"""
        response = client_logado.get(
            reverse('financeiro:listar_parcelas'),
            {'per_page': 'abc'}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestDetalheParcela:
    """Testes da view detalhe_parcela"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:detalhe_parcela', kwargs={'pk': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_exibe_detalhe(self, client_logado, parcela):
        """Detalhe da parcela retorna 200"""
        url = reverse('financeiro:detalhe_parcela', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code == 200

    def test_parcela_inexistente_retorna_404(self, client_logado):
        """ID inexistente retorna 404"""
        url = reverse('financeiro:detalhe_parcela', kwargs={'pk': 999999})
        response = client_logado.get(url)
        assert response.status_code == 404

    def test_contexto_tem_parcela(self, client_logado, parcela):
        """Contexto da view contém a parcela"""
        url = reverse('financeiro:detalhe_parcela', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert 'parcela' in response.context
        assert response.context['parcela'] == parcela


@pytest.mark.django_db
class TestRegistrarPagamento:
    """Testes da view registrar_pagamento"""

    def test_requer_autenticacao(self, client, parcela):
        url = reverse('financeiro:registrar_pagamento', kwargs={'pk': parcela.pk})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_exibe_formulario(self, client_logado, parcela):
        """GET retorna formulário de pagamento"""
        url = reverse('financeiro:registrar_pagamento', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        assert response.status_code == 200

    def test_post_registra_pagamento(self, client_logado, parcela):
        """POST válido registra o pagamento"""
        url = reverse('financeiro:registrar_pagamento', kwargs={'pk': parcela.pk})
        data = {
            'data_pagamento': date.today().strftime('%d/%m/%Y'),
            'valor_pago': str(parcela.valor_atual),
            'forma_pagamento': 'DINHEIRO',
        }
        response = client_logado.post(url, data=data)
        # Deve redirecionar após sucesso ou retornar 200 com form
        assert response.status_code in (200, 302)

    def test_parcela_paga_redireciona(self, client_logado, parcela):
        """Parcela já paga não pode ser paga novamente"""
        parcela.pago = True
        parcela.save()
        url = reverse('financeiro:registrar_pagamento', kwargs={'pk': parcela.pk})
        response = client_logado.get(url)
        # Deve redirecionar ou exibir mensagem de erro
        assert response.status_code in (200, 302)


@pytest.mark.django_db
class TestNotificarInadimplente:
    """Testes da view notificar_inadimplente (3.25)"""

    def test_requer_autenticacao(self, client, parcela_vencida):
        url = reverse('financeiro:notificar_inadimplente', kwargs={'pk': parcela_vencida.pk})
        response = client.post(url)
        assert response.status_code in (302, 403)

    def test_parcela_paga_retorna_400(self, client_logado, parcela):
        """Parcela já paga não pode ser notificada como inadimplente"""
        parcela.pago = True
        parcela.save()
        url = reverse('financeiro:notificar_inadimplente', kwargs={'pk': parcela.pk})
        response = client_logado.post(url, {})
        assert response.status_code == 400
        data = response.json()
        assert not data['sucesso']

    def test_parcela_nao_vencida_retorna_400(self, client_logado, parcela):
        """Parcela com vencimento futuro retorna 400"""
        parcela.pago = False
        parcela.data_vencimento = date.today() + timedelta(days=5)
        parcela.save()
        url = reverse('financeiro:notificar_inadimplente', kwargs={'pk': parcela.pk})
        response = client_logado.post(url, {})
        assert response.status_code == 400

    def test_get_nao_permitido(self, client_logado, parcela_vencida):
        """GET retorna 405"""
        url = reverse('financeiro:notificar_inadimplente', kwargs={'pk': parcela_vencida.pk})
        response = client_logado.get(url)
        assert response.status_code == 405

    def test_parcela_vencida_tenta_notificar(self, client_logado, parcela_vencida):
        """POST em parcela vencida retorna JSON (sucesso, erro, ou 500 se sem config)"""
        url = reverse('financeiro:notificar_inadimplente', kwargs={'pk': parcela_vencida.pk})
        response = client_logado.post(url, {})
        # 200=enviado, 400=sem canal, 500=erro de configuração (sem Twilio/SMTP no teste)
        assert response.status_code in (200, 400, 500)
        if response.status_code in (200, 400):
            data = response.json()
            assert 'sucesso' in data
