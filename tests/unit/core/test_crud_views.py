"""
Section 7.2 P2 — Unit tests for core CRUD views.

Tests: Imobiliaria, Imovel, Comprador list/create/update/delete views.
Authenticated users get 200; unauthenticated users are redirected.
"""

import pytest
from django.test import Client
from django.urls import reverse

from tests.fixtures.factories import (
    UserFactory,
    ImobiliariaFactory,
    ImovelFactory,
    CompradorFactory,
)

pytestmark = pytest.mark.django_db


def make_client(user=None):
    """Return a test client, optionally authenticated."""
    c = Client(enforce_csrf_checks=False)
    if user:
        c.force_login(user)
    return c


def sget(client, url):
    """GET over HTTPS to bypass SECURE_SSL_REDIRECT=True."""
    return client.get(url, secure=True)


def anon_get(url):
    """Anonymous GET over HTTPS, returns redirect status code."""
    return Client().get(url, secure=True)


# =============================================================================
# IMOBILIARIA CRUD
# =============================================================================

class TestImobiliariaListView:
    def test_unauthenticated_redirects(self):
        response = anon_get(reverse('core:listar_imobiliarias'))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:listar_imobiliarias'))
        assert response.status_code == 200

    def test_shows_imobiliarias(self):
        user = UserFactory.create()
        ImobiliariaFactory.create()
        response = sget(make_client(user), reverse('core:listar_imobiliarias'))
        assert response.status_code == 200


class TestImobiliariaCreateView:
    def test_unauthenticated_redirects(self):
        response = anon_get(reverse('core:criar_imobiliaria'))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:criar_imobiliaria'))
        assert response.status_code == 200


class TestImobiliariaUpdateView:
    def test_unauthenticated_redirects(self):
        imob = ImobiliariaFactory.create()
        response = anon_get(reverse('core:editar_imobiliaria', args=[imob.pk]))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        imob = ImobiliariaFactory.create()
        response = sget(make_client(user), reverse('core:editar_imobiliaria', args=[imob.pk]))
        assert response.status_code == 200

    def test_404_for_nonexistent(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:editar_imobiliaria', args=[99999]))
        assert response.status_code == 404


class TestImobiliariaDeleteView:
    def test_unauthenticated_redirects(self):
        imob = ImobiliariaFactory.create()
        response = anon_get(reverse('core:excluir_imobiliaria', args=[imob.pk]))
        assert response.status_code == 302

    def test_post_authenticated_redirects(self):
        user = UserFactory.create()
        imob = ImobiliariaFactory.create()
        client = make_client(user)
        response = client.post(reverse('core:excluir_imobiliaria', args=[imob.pk]))
        assert response.status_code == 302


# =============================================================================
# IMOVEL CRUD
# =============================================================================

class TestImovelListView:
    def test_unauthenticated_redirects(self):
        response = anon_get(reverse('core:listar_imoveis'))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:listar_imoveis'))
        assert response.status_code == 200


class TestImovelCreateView:
    def test_unauthenticated_redirects(self):
        response = anon_get(reverse('core:criar_imovel'))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:criar_imovel'))
        assert response.status_code == 200


class TestImovelUpdateView:
    def test_unauthenticated_redirects(self):
        imovel = ImovelFactory.create()
        response = anon_get(reverse('core:editar_imovel', args=[imovel.pk]))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        imovel = ImovelFactory.create()
        response = sget(make_client(user), reverse('core:editar_imovel', args=[imovel.pk]))
        assert response.status_code == 200


class TestImovelDeleteView:
    def test_unauthenticated_redirects(self):
        imovel = ImovelFactory.create()
        response = anon_get(reverse('core:excluir_imovel', args=[imovel.pk]))
        assert response.status_code == 302

    def test_post_authenticated_soft_deletes(self):
        user = UserFactory.create()
        imovel = ImovelFactory.create()
        client = make_client(user)
        response = client.post(reverse('core:excluir_imovel', args=[imovel.pk]))
        assert response.status_code == 302
        imovel.refresh_from_db()
        assert imovel.ativo is False


# =============================================================================
# COMPRADOR CRUD
# =============================================================================

class TestCompradorListView:
    def test_unauthenticated_redirects(self):
        response = anon_get(reverse('core:listar_compradores'))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:listar_compradores'))
        assert response.status_code == 200


class TestCompradorCreateView:
    def test_unauthenticated_redirects(self):
        response = anon_get(reverse('core:criar_comprador'))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        response = sget(make_client(user), reverse('core:criar_comprador'))
        assert response.status_code == 200


class TestCompradorUpdateView:
    def test_unauthenticated_redirects(self):
        comprador = CompradorFactory.create()
        response = anon_get(reverse('core:editar_comprador', args=[comprador.pk]))
        assert response.status_code == 302

    def test_authenticated_returns_200(self):
        user = UserFactory.create()
        comprador = CompradorFactory.create()
        response = sget(make_client(user), reverse('core:editar_comprador', args=[comprador.pk]))
        assert response.status_code == 200


class TestCompradorDeleteView:
    def test_unauthenticated_redirects(self):
        comprador = CompradorFactory.create()
        response = anon_get(reverse('core:excluir_comprador', args=[comprador.pk]))
        assert response.status_code == 302

    def test_post_authenticated_soft_deletes(self):
        user = UserFactory.create()
        comprador = CompradorFactory.create()
        client = make_client(user)
        response = client.post(reverse('core:excluir_comprador', args=[comprador.pk]))
        assert response.status_code == 302
        comprador.refresh_from_db()
        assert comprador.ativo is False
