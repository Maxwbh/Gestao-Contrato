"""
Testes dos modelos do app portal_comprador

Testa os modelos:
- AcessoComprador
- LogAcessoComprador
"""
import pytest
from django.utils import timezone

from portal_comprador.models import AcessoComprador, LogAcessoComprador
from tests.fixtures.factories import UserFactory, CompradorFactory


@pytest.mark.django_db
class TestAcessoComprador:
    """Testes do modelo AcessoComprador"""

    def test_criar_acesso_comprador(self):
        """Testa criação básica de acesso do comprador"""
        comprador = CompradorFactory()
        usuario = UserFactory()

        acesso = AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        assert acesso.pk is not None
        assert acesso.comprador == comprador
        assert acesso.usuario == usuario
        assert acesso.ativo is True
        assert acesso.email_verificado is False
        assert acesso.ultimo_acesso is None
        assert acesso.data_criacao is not None

    def test_str_acesso_comprador(self):
        """Testa representação string do acesso"""
        comprador = CompradorFactory(nome='João Silva')
        usuario = UserFactory(username='joao.silva')

        acesso = AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        assert str(acesso) == 'João Silva (joao.silva)'

    def test_registrar_acesso(self):
        """Testa método registrar_acesso que atualiza ultimo_acesso"""
        comprador = CompradorFactory()
        usuario = UserFactory()

        acesso = AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        assert acesso.ultimo_acesso is None

        acesso.registrar_acesso()

        acesso.refresh_from_db()
        assert acesso.ultimo_acesso is not None
        assert acesso.ultimo_acesso <= timezone.now()


@pytest.mark.django_db
class TestLogAcessoComprador:
    """Testes do modelo LogAcessoComprador"""

    def test_criar_log_acesso(self):
        """Testa criação de log de acesso"""
        comprador = CompradorFactory()
        usuario = UserFactory()
        acesso = AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        log = LogAcessoComprador.objects.create(
            acesso_comprador=acesso,
            ip_acesso='192.168.1.100',
            user_agent='Mozilla/5.0',
            pagina_acessada='/portal/dashboard/'
        )

        assert log.pk is not None
        assert log.acesso_comprador == acesso
        assert log.ip_acesso == '192.168.1.100'
        assert log.user_agent == 'Mozilla/5.0'
        assert log.pagina_acessada == '/portal/dashboard/'
        assert log.data_acesso is not None

    def test_str_log_acesso(self):
        """Testa representação string do log de acesso"""
        comprador = CompradorFactory(nome='Maria Santos')
        usuario = UserFactory()
        acesso = AcessoComprador.objects.create(
            comprador=comprador,
            usuario=usuario
        )

        log = LogAcessoComprador.objects.create(
            acesso_comprador=acesso
        )

        resultado = str(log)
        assert 'Maria Santos' in resultado
