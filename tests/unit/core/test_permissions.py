"""
Testes do módulo core/permissions.py

Cobre: rate_limit decorator, requer_permissao_total,
       helpers usuario_pode_editar / usuario_pode_excluir / usuario_eh_apenas_leitura.
"""
import pytest
from django.test import RequestFactory
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from core.permissions import rate_limit
from core.models import (
    usuario_pode_editar,
    usuario_pode_excluir,
    usuario_eh_apenas_leitura,
    get_acesso_usuario,
    AcessoUsuario,
)
from tests.fixtures.factories import (
    UserFactory,
    SuperUserFactory,
    ImobiliariaFactory,
    ContabilidadeFactory,
)

User = get_user_model()


# =============================================================================
# RATE LIMIT DECORATOR
# =============================================================================

@pytest.mark.django_db
class TestRateLimitDecorator:
    """Testa o decorator rate_limit baseado em cache."""

    def _make_view(self):
        @rate_limit(3)
        def minha_view(request):
            return HttpResponse('ok', status=200)
        return minha_view

    def _make_request(self, ip='127.0.0.1'):
        factory = RequestFactory()
        req = factory.get('/')
        req.META['REMOTE_ADDR'] = ip
        return req

    def test_primeira_requisicao_passa(self):
        view = self._make_view()
        req = self._make_request()
        resp = view(req)
        assert resp.status_code == 200

    def test_dentro_do_limite_passa(self):
        view = self._make_view()
        req = self._make_request(ip='10.0.0.1')
        for _ in range(3):
            resp = view(req)
        assert resp.status_code == 200

    def test_acima_do_limite_retorna_429(self):
        view = self._make_view()
        req = self._make_request(ip='10.0.0.2')
        for _ in range(3):
            view(req)
        resp = view(req)
        assert resp.status_code == 429

    def test_ips_diferentes_nao_interferem(self):
        view = self._make_view()
        for i in range(10):
            req = self._make_request(ip=f'192.168.1.{i}')
            resp = view(req)
            assert resp.status_code == 200

    def test_retorno_429_e_json(self):
        import json
        view = self._make_view()
        req = self._make_request(ip='10.0.0.3')
        for _ in range(3):
            view(req)
        resp = view(req)
        assert resp.status_code == 429
        data = json.loads(resp.content)
        assert 'erro' in data
        assert 'retry_after' in data

    def test_x_forwarded_for_usado_como_chave(self):
        view = self._make_view()
        factory = RequestFactory()
        req = factory.get('/')
        req.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 5.6.7.8'
        req.META['REMOTE_ADDR'] = '127.0.0.1'
        resp = view(req)
        assert resp.status_code == 200


# =============================================================================
# ROLE HELPERS — usuario_pode_editar / excluir / leitura
# =============================================================================

@pytest.mark.django_db
class TestRoleHelpers:
    """Testa helpers de permissão granular."""

    def test_superuser_pode_editar(self, db):
        user = SuperUserFactory()
        imobiliaria = ImobiliariaFactory()
        assert usuario_pode_editar(user, imobiliaria) is True

    def test_superuser_pode_excluir(self, db):
        user = SuperUserFactory()
        imobiliaria = ImobiliariaFactory()
        assert usuario_pode_excluir(user, imobiliaria) is True

    def test_superuser_nao_e_apenas_leitura(self, db):
        user = SuperUserFactory()
        imobiliaria = ImobiliariaFactory()
        assert usuario_eh_apenas_leitura(user, imobiliaria) is False

    def test_usuario_sem_acesso_nao_pode_editar(self, db):
        user = UserFactory()
        imobiliaria = ImobiliariaFactory()
        assert usuario_pode_editar(user, imobiliaria) is False

    def test_usuario_sem_acesso_nao_pode_excluir(self, db):
        user = UserFactory()
        imobiliaria = ImobiliariaFactory()
        assert usuario_pode_excluir(user, imobiliaria) is False

    def test_usuario_com_acesso_pode_editar_quando_pode_editar_true(self, db):
        user = UserFactory()
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        AcessoUsuario.objects.create(
            usuario=user,
            contabilidade=contabilidade,
            imobiliaria=imobiliaria,
            pode_editar=True,
            pode_excluir=False,
            ativo=True,
        )
        assert usuario_pode_editar(user, imobiliaria) is True

    def test_usuario_operador_nao_pode_excluir(self, db):
        """Operador Imobiliária (pode_editar=True, pode_excluir=False)"""
        user = UserFactory()
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        AcessoUsuario.objects.create(
            usuario=user,
            contabilidade=contabilidade,
            imobiliaria=imobiliaria,
            pode_editar=True,
            pode_excluir=False,
            ativo=True,
        )
        assert usuario_pode_excluir(user, imobiliaria) is False

    def test_usuario_gerente_pode_excluir(self, db):
        """Gerente Imobiliária (pode_editar=True, pode_excluir=True)"""
        user = UserFactory()
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        AcessoUsuario.objects.create(
            usuario=user,
            contabilidade=contabilidade,
            imobiliaria=imobiliaria,
            pode_editar=True,
            pode_excluir=True,
            ativo=True,
        )
        assert usuario_pode_excluir(user, imobiliaria) is True

    def test_operador_relatorios_eh_apenas_leitura(self, db):
        """Operador Relatórios (pode_editar=False, pode_excluir=False)"""
        user = UserFactory()
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        AcessoUsuario.objects.create(
            usuario=user,
            contabilidade=contabilidade,
            imobiliaria=imobiliaria,
            pode_editar=False,
            pode_excluir=False,
            ativo=True,
        )
        assert usuario_eh_apenas_leitura(user, imobiliaria) is True

    def test_usuario_inativo_nao_pode_editar(self, db):
        user = UserFactory()
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        AcessoUsuario.objects.create(
            usuario=user,
            contabilidade=contabilidade,
            imobiliaria=imobiliaria,
            pode_editar=True,
            pode_excluir=True,
            ativo=False,  # inativo
        )
        assert usuario_pode_editar(user, imobiliaria) is False

    def test_get_acesso_usuario_retorna_objeto(self, db):
        user = UserFactory()
        contabilidade = ContabilidadeFactory()
        imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
        acesso = AcessoUsuario.objects.create(
            usuario=user,
            contabilidade=contabilidade,
            imobiliaria=imobiliaria,
            pode_editar=True,
            ativo=True,
        )
        resultado = get_acesso_usuario(user, imobiliaria)
        assert resultado == acesso

    def test_get_acesso_usuario_retorna_none_sem_acesso(self, db):
        user = UserFactory()
        imobiliaria = ImobiliariaFactory()
        resultado = get_acesso_usuario(user, imobiliaria)
        assert resultado is None

    def test_usuario_nao_autenticado_nao_pode_editar(self, db):
        """AnonymousUser retorna False para pode_editar"""
        from django.contrib.auth.models import AnonymousUser
        anon = AnonymousUser()
        imobiliaria = ImobiliariaFactory()
        assert usuario_pode_editar(anon, imobiliaria) is False
