"""
D-04: Testes automatizados de isolamento de tenant (imobiliária).

Verifica que um usuário da imobiliária X não consegue acessar
recursos da imobiliária Y, recebendo 403.
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User

from core.hashids_utils import encode_id
from tests.fixtures.factories import (
    ContabilidadeFactory,
    ImobiliariaFactory,
    ContratoFactory,
    ParcelaFactory,
)


def _make_user_com_acesso(username, imobiliaria):
    """Cria usuário vinculado a uma imobiliária via AcessoUsuario."""
    from core.models import AcessoUsuario
    user = User.objects.create_user(username=username, password='pass123')
    AcessoUsuario.objects.create(
        usuario=user,
        imobiliaria=imobiliaria,
        contabilidade=imobiliaria.contabilidade,
    )
    return user


@pytest.mark.django_db
class TestTenantIsolacaoContrato:
    """Usuário A não pode ver contrato de imobiliária B."""

    def test_acesso_negado_contrato_outra_imobiliaria(self):
        contabilidade = ContabilidadeFactory()
        imob_a = ImobiliariaFactory(contabilidade=contabilidade)
        imob_b = ImobiliariaFactory(contabilidade=contabilidade)

        user_a = _make_user_com_acesso('user_a_iso', imob_a)

        # Contrato pertencente à imobiliária B
        contrato_b = ContratoFactory(imobiliaria=imob_b, imovel__imobiliaria=imob_b)

        client = Client()
        client.login(username='user_a_iso', password='pass123')

        hid = encode_id(contrato_b.pk)
        response = client.get(f'/contratos/{hid}/')
        assert response.status_code == 403, (
            f'user_a deveria receber 403 ao acessar contrato de imob_b, '
            f'mas recebeu {response.status_code}'
        )

    def test_acesso_permitido_proprio_contrato(self):
        imob_a = ImobiliariaFactory()
        user_a = _make_user_com_acesso('user_a_iso2', imob_a)

        # Contrato pertencente à própria imobiliária A
        contrato_a = ContratoFactory(imobiliaria=imob_a, imovel__imobiliaria=imob_a)

        client = Client()
        client.login(username='user_a_iso2', password='pass123')

        hid = encode_id(contrato_a.pk)
        response = client.get(f'/contratos/{hid}/')
        assert response.status_code == 200, (
            f'user_a deveria poder acessar próprio contrato, '
            f'mas recebeu {response.status_code}'
        )


@pytest.mark.django_db
class TestTenantIsolacaoParcela:
    """Usuário A não pode ver parcela de contrato da imobiliária B."""

    def test_acesso_negado_parcela_outra_imobiliaria(self):
        contabilidade = ContabilidadeFactory()
        imob_a = ImobiliariaFactory(contabilidade=contabilidade)
        imob_b = ImobiliariaFactory(contabilidade=contabilidade)

        user_a = _make_user_com_acesso('user_pa_iso', imob_a)

        contrato_b = ContratoFactory(imobiliaria=imob_b, imovel__imobiliaria=imob_b)
        parcela_b = ParcelaFactory(contrato=contrato_b)

        client = Client()
        client.login(username='user_pa_iso', password='pass123')

        hid = encode_id(parcela_b.pk)
        response = client.get(f'/financeiro/parcelas/{hid}/')
        assert response.status_code == 403, (
            f'user_pa deveria receber 403 ao acessar parcela de imob_b, '
            f'mas recebeu {response.status_code}'
        )

    def test_acesso_permitido_propria_parcela(self):
        imob_a = ImobiliariaFactory()
        user_a = _make_user_com_acesso('user_pa_iso2', imob_a)

        contrato_a = ContratoFactory(imobiliaria=imob_a, imovel__imobiliaria=imob_a)
        parcela_a = ParcelaFactory(contrato=contrato_a)

        client = Client()
        client.login(username='user_pa_iso2', password='pass123')

        hid = encode_id(parcela_a.pk)
        response = client.get(f'/financeiro/parcelas/{hid}/')
        assert response.status_code == 200, (
            f'user_pa deveria poder acessar própria parcela, '
            f'mas recebeu {response.status_code}'
        )
