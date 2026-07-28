"""
Rename do modo offline: `brcobranca` → `pycobranca`.

O motor offline do gateway deixou de ser o BRCobrança (Ruby) e passou a ser o
pyCobrança (Python). O valor canônico agora é `pycobranca`; o legado continua
sendo ACEITO na entrada (APIs, forms, integrações antigas) e convertido — os
dados já gravados foram migrados em core.0027 / financeiro.0027.
"""
import json

import pytest
from django.urls import reverse

from core.models import (ContaBancaria, ProviderBoleto, normalizar_provider,
                         PROVIDER_OFFLINE_LEGADO)


class TestNormalizacao:
    def test_valor_canonico(self):
        assert ProviderBoleto.PYCOBRANCA == 'pycobranca'

    def test_legado_vira_pycobranca(self):
        assert normalizar_provider(PROVIDER_OFFLINE_LEGADO) == 'pycobranca'
        assert normalizar_provider('BRCobranca') == 'pycobranca'

    def test_vazio_vira_pycobranca(self):
        assert normalizar_provider('') == 'pycobranca'
        assert normalizar_provider(None) == 'pycobranca'

    def test_registrados_preservados(self):
        assert normalizar_provider('c6') == 'c6'
        assert normalizar_provider('sicoob') == 'sicoob'


@pytest.mark.django_db
class TestApiAceitaLegado:
    """Integrações que ainda mandam 'brcobranca' continuam funcionando."""

    @pytest.fixture
    def admin_client(self, client):
        from tests.fixtures.factories import SuperUserFactory
        client.force_login(SuperUserFactory())
        return client

    @pytest.fixture
    def imob(self, db):
        from tests.fixtures.factories import ImobiliariaFactory
        return ImobiliariaFactory()

    def test_criar_com_valor_legado_grava_canonico(self, admin_client, imob):
        r = admin_client.post(
            reverse('core:api_criar_conta'),
            data=json.dumps({
                'imobiliaria_id': imob.id, 'banco': '001', 'descricao': 'BB',
                'agencia': '1234', 'conta': '5678', 'provider': 'brcobranca',
            }),
            content_type='application/json')
        assert r.status_code == 200
        conta = ContaBancaria.objects.get(pk=r.json()['conta_id'])
        assert conta.provider == ProviderBoleto.PYCOBRANCA
        assert conta.tenant_id == ''   # offline não usa tenant

    def test_atualizar_com_valor_legado_grava_canonico(self, admin_client, imob):
        from tests.fixtures.factories import ContaBancariaApiFactory
        conta = ContaBancariaApiFactory(imobiliaria=imob, provider='sicoob')
        admin_client.post(
            reverse('core:api_atualizar_conta', args=[conta.pk]),
            data=json.dumps({'banco': '756', 'descricao': 'x',
                             'provider': 'brcobranca'}),
            content_type='application/json')
        conta.refresh_from_db()
        assert conta.provider == ProviderBoleto.PYCOBRANCA


@pytest.mark.django_db
class TestCortesUsamValorNovo:
    """Os cortes de fluxo (offline × registrado) seguem o valor canônico."""

    def test_conta_pycobranca_nao_e_boleto_api(self, db):
        from tests.fixtures.factories import ContaBancariaFactory
        from financeiro.services.cnab_service import PROVIDERS_BOLETO_API
        conta = ContaBancariaFactory(provider=ProviderBoleto.PYCOBRANCA)
        assert conta.provider not in PROVIDERS_BOLETO_API

    def test_parcela_pycobranca_nao_e_boleto_api(self, db):
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(provider=ProviderBoleto.PYCOBRANCA)
        assert p._e_boleto_api() is False
