"""
Bug do "Editar Conta Bancária": ao escolher C6/Sicoob faltavam os campos de
autenticação. Cobre a API que agora aceita credenciais (cifradas) + account_config
e gera o tenant_id interno; e que os segredos nunca voltam ao cliente.
"""
import json
import pytest
from django.urls import reverse

from core.models import ContaBancaria


@pytest.fixture
def admin_client(client, db):
    from tests.fixtures.factories import SuperUserFactory
    client.force_login(SuperUserFactory())
    return client


@pytest.fixture
def imob(db):
    from tests.fixtures.factories import ImobiliariaFactory
    return ImobiliariaFactory()


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type='application/json')


@pytest.mark.django_db
class TestCriarContaBoletoApi:
    def test_sicoob_grava_credenciais_e_account_config(self, admin_client, imob):
        r = _post(admin_client, reverse('core:api_criar_conta'), {
            'imobiliaria_id': imob.id, 'banco': '756', 'descricao': 'Sicoob',
            'agencia': '3073', 'conta': '12345678', 'provider': 'sicoob',
            'account_config': {'numeroCliente': '999', 'codigoModalidade': '1',
                               'numeroContaCorrente': '12345678'},
            'credenciais': {'client_id': 'CID', 'client_secret': 'SEC'},
        })
        assert r.status_code == 200 and r.json()['status'] == 'success'
        conta = ContaBancaria.objects.get(pk=r.json()['conta_id'])
        # credenciais guardadas cifradas e recuperáveis pela property
        assert conta.credenciais == {'client_id': 'CID', 'client_secret': 'SEC'}
        assert conta.credenciais_cifradas and 'CID' not in conta.credenciais_cifradas
        assert conta.account_config['numeroCliente'] == '999'
        # tenant_id interno gerado automaticamente
        assert conta.tenant_id == f'imob{imob.id}-sicoob'

    def test_sicoob_conta_corrente_vem_do_campo_conta(self, admin_client, imob):
        # numeroContaCorrente não é enviado: deve ser derivado do campo "conta".
        r = _post(admin_client, reverse('core:api_criar_conta'), {
            'imobiliaria_id': imob.id, 'banco': '756', 'descricao': 'Sicoob',
            'agencia': '3073', 'conta': '87654321', 'provider': 'sicoob',
            'account_config': {'numeroCliente': '999', 'codigoModalidade': '1'},
            'credenciais': {'client_id': 'CID', 'client_secret': 'SEC'},
        })
        assert r.status_code == 200 and r.json()['status'] == 'success'
        conta = ContaBancaria.objects.get(pk=r.json()['conta_id'])
        assert conta.account_config['numeroContaCorrente'] == '87654321'

    def test_c6_gera_tenant(self, admin_client, imob):
        r = _post(admin_client, reverse('core:api_criar_conta'), {
            'imobiliaria_id': imob.id, 'banco': '336', 'descricao': 'C6',
            'agencia': '0001', 'conta': '111', 'provider': 'c6',
            'account_config': {'billing_scheme': 'BILL_1'},
            'credenciais': {'client_id': 'X', 'client_secret': 'Y'},
        })
        conta = ContaBancaria.objects.get(pk=r.json()['conta_id'])
        assert conta.tenant_id == f'imob{imob.id}-c6'

    def test_brcobranca_sem_tenant_nem_credenciais(self, admin_client, imob):
        r = _post(admin_client, reverse('core:api_criar_conta'), {
            'imobiliaria_id': imob.id, 'banco': '001', 'descricao': 'BB',
            'agencia': '1234', 'conta': '5678', 'provider': 'brcobranca',
        })
        conta = ContaBancaria.objects.get(pk=r.json()['conta_id'])
        assert conta.tenant_id == '' and conta.credenciais_cifradas == ''


@pytest.mark.django_db
class TestObterEAtualizar:
    def _conta(self, imob):
        from tests.fixtures.factories import ContaBancariaApiFactory
        c = ContaBancariaApiFactory(imobiliaria=imob, banco='756', provider='sicoob')
        c.credenciais = {'client_id': 'OLD', 'client_secret': 'OLDSEC'}
        c.save()
        return c

    def test_obter_nao_vaza_segredo_mas_indica(self, admin_client, imob):
        c = self._conta(imob)
        r = admin_client.get(reverse('core:api_obter_conta', args=[c.pk]))
        data = r.json()['conta']
        assert 'credenciais' not in data and 'credenciais_cifradas' not in data
        assert data['tem_credenciais'] is True
        assert data['account_config']  # account_config volta (sem segredo)

    def test_atualizar_sem_credenciais_preserva(self, admin_client, imob):
        c = self._conta(imob)
        _post(admin_client, reverse('core:api_atualizar_conta', args=[c.pk]), {
            'banco': '756', 'descricao': 'novo', 'provider': 'sicoob',
            'account_config': {'numeroCliente': '1', 'codigoModalidade': '1',
                               'numeroContaCorrente': '2'},
            'credenciais': {'client_id': '', 'client_secret': ''},  # em branco = mantém
        })
        c.refresh_from_db()
        assert c.credenciais == {'client_id': 'OLD', 'client_secret': 'OLDSEC'}

    def test_atualizar_com_credenciais_substitui(self, admin_client, imob):
        c = self._conta(imob)
        _post(admin_client, reverse('core:api_atualizar_conta', args=[c.pk]), {
            'banco': '756', 'descricao': 'x', 'provider': 'sicoob',
            'account_config': {'numeroCliente': '1', 'codigoModalidade': '1',
                               'numeroContaCorrente': '2'},
            'credenciais': {'client_id': 'NEW', 'client_secret': 'NEWSEC'},
        })
        c.refresh_from_db()
        assert c.credenciais == {'client_id': 'NEW', 'client_secret': 'NEWSEC'}
