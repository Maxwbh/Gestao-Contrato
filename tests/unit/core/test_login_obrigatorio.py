"""
Auditoria de autenticação — telas/endpoints que devem exigir login.

Foco nas falhas encontradas: ferramentas de dados de teste (populam/expõem o
banco) e a API de contas bancárias (dados sensíveis).
"""
import pytest
from django.urls import reverse

from tests.fixtures.factories import SuperUserFactory


@pytest.mark.django_db
class TestDadosTesteProtegidos:
    URLS = ('core:gerar_dados_teste', 'core:gerar_boletos_teste')

    @pytest.mark.parametrize('url', URLS)
    def test_anonimo_em_producao_bloqueado(self, client, settings, url):
        settings.DEBUG = False
        r = client.get(reverse(url))
        assert r.status_code == 403

    @pytest.mark.parametrize('url', URLS)
    def test_anonimo_em_debug_liberado(self, client, settings, url):
        settings.DEBUG = True
        r = client.get(reverse(url))
        assert r.status_code == 200  # GET só devolve status, não popula

    @pytest.mark.parametrize('url', URLS)
    def test_superuser_liberado_em_producao(self, client, settings, url):
        settings.DEBUG = False
        client.force_login(SuperUserFactory())
        r = client.get(reverse(url))
        assert r.status_code == 200

    def test_comum_em_producao_bloqueado(self, client, settings):
        from django.contrib.auth import get_user_model
        settings.DEBUG = False
        client.force_login(get_user_model().objects.create_user('c', 'c@x.com', 'x'))
        assert client.get(reverse('core:gerar_dados_teste')).status_code == 403


@pytest.mark.django_db
class TestApiContasBancarias:
    def test_anonimo_redireciona_login(self, client):
        r = client.get(reverse('financeiro:api_contas_bancarias'))
        assert r.status_code in (301, 302) and 'login' in r.url

    def test_logado_ve_so_seu_tenant(self, client):
        from tests.fixtures.factories import (ImobiliariaFactory, ContaBancariaFactory,
                                              UserFactory, AcessoUsuarioFactory)
        im_a = ImobiliariaFactory()
        im_b = ImobiliariaFactory()
        ContaBancariaFactory(imobiliaria=im_a, descricao='Conta A')
        ContaBancariaFactory(imobiliaria=im_b, descricao='Conta B')
        user = UserFactory()
        AcessoUsuarioFactory(usuario=user, contabilidade=im_a.contabilidade, imobiliaria=im_a)
        client.force_login(user)
        r = client.get(reverse('financeiro:api_contas_bancarias'))
        assert r.status_code == 200
        nomes = {c['imobiliaria']['nome'] for c in r.json()['contas']}
        assert im_a.nome in nomes and im_b.nome not in nomes
