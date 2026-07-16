"""
Fase 9 Boleto-API — painel de conciliação da cobrança registrada: agrega
% conciliado, distribuição por status, recebido por origem e recorrências.
"""
import pytest
from django.urls import reverse

from financeiro.models import StatusCobranca as S, RecorrenciaPix, RecStatusPA

URL = 'financeiro:painel_conciliacao_boleto_api'


@pytest.mark.django_db
class TestPainelConciliacao:
    def _login(self, client):
        from tests.fixtures.factories import SuperUserFactory
        user = SuperUserFactory()
        client.force_login(user)
        return user

    def test_painel_200_e_pct_conciliado(self, client):
        from tests.fixtures.factories import ParcelaFactory
        self._login(client)
        ParcelaFactory(status_cobranca=S.LIQUIDADA, provider='c6')
        ParcelaFactory(status_cobranca=S.REGISTRADA, provider='c6')
        r = client.get(reverse(URL))
        assert r.status_code == 200
        assert r.context['total'] == 2
        assert r.context['pct_conciliado'] == 50.0
        assert ('Liquidada', 1) in r.context['status_rows']

    def test_painel_sem_dados(self, client):
        self._login(client)
        r = client.get(reverse(URL))
        assert r.status_code == 200
        assert r.context['total'] == 0 and r.context['pct_conciliado'] == 0.0

    def test_recorrencias_no_contexto(self, client):
        from tests.fixtures.factories import ContratoFactory
        self._login(client)
        RecorrenciaPix.objects.create(contrato=ContratoFactory(), id_rec='R', provider='c6',
                                      status=RecStatusPA.APROVADA)
        r = client.get(reverse(URL))
        assert ('Aprovada', 1) in r.context['recorrencia_rows']

    def test_exige_login(self, client):
        r = client.get(reverse(URL))
        assert r.status_code in (302, 301)  # redireciona para login
