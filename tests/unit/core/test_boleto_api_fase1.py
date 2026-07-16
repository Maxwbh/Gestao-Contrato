"""
Fase 1 Boleto-API — cifra de credenciais, validação banco↔provider e métodos
de cobrança da imobiliária. Testes de unidade (sem DB onde possível).
"""
import pytest
from django.core.exceptions import ValidationError

from core.crypto import encrypt_str, decrypt_str, encrypt_dict, decrypt_dict
from core.models import ContaBancaria, Imobiliaria, MetodoCobranca


class TestCrypto:
    def test_str_roundtrip(self):
        tok = encrypt_str('s3cr3t')
        assert tok and tok != 's3cr3t'
        assert decrypt_str(tok) == 's3cr3t'

    def test_dict_roundtrip_nao_vaza_em_claro(self):
        d = {'client_id': 'a', 'client_secret': 'super-segredo'}
        tok = encrypt_dict(d)
        assert tok and 'super-segredo' not in tok
        assert decrypt_dict(tok) == d

    def test_vazios(self):
        assert encrypt_str('') == '' and decrypt_str('') == ''
        assert encrypt_dict({}) == '' and decrypt_dict('') == {}

    def test_decifra_lixo_retorna_vazio(self):
        assert decrypt_str('nao-eh-token') == ''
        assert decrypt_dict('nao-eh-token') == {}


class TestContaBancariaCredenciais:
    def test_credenciais_property_roundtrip(self):
        cb = ContaBancaria(banco='336', provider='c6')
        cb.credenciais = {'client_id': 'x', 'client_secret': 'y'}
        assert cb.credenciais_cifradas
        assert 'client_secret' not in cb.credenciais_cifradas
        assert cb.credenciais == {'client_id': 'x', 'client_secret': 'y'}

    def test_bapi_token_set_get_e_timestamp(self):
        cb = ContaBancaria(banco='756', provider='sicoob')
        assert cb.bapi_token == '' and cb.bapi_token_criado_em is None
        cb.set_bapi_token('bapi_abc')
        assert cb.bapi_token == 'bapi_abc'
        assert cb.bapi_token_criado_em is not None
        cb.set_bapi_token('')
        assert cb.bapi_token == '' and cb.bapi_token_criado_em is None


class TestBancoProvider:
    @pytest.mark.parametrize('banco,provider', [
        ('336', 'c6'), ('336', 'brcobranca'),
        ('756', 'sicoob'), ('756', 'brcobranca'),
        ('001', 'brcobranca'),
    ])
    def test_compativel_nao_levanta(self, banco, provider):
        ContaBancaria(banco=banco, provider=provider).clean()

    @pytest.mark.parametrize('banco,provider', [
        ('336', 'sicoob'), ('756', 'c6'), ('001', 'c6'), ('001', 'sicoob'),
    ])
    def test_incompativel_levanta(self, banco, provider):
        with pytest.raises(ValidationError):
            ContaBancaria(banco=banco, provider=provider).clean()


class TestImobiliariaMetodos:
    def test_default_boleto(self):
        assert Imobiliaria().metodos_cobranca == [MetodoCobranca.BOLETO]

    def test_metodo_habilitado(self):
        im = Imobiliaria(metodos_cobranca=['boleto', 'carne'])
        assert im.metodo_habilitado('boleto')
        assert im.metodo_habilitado('carne')
        assert not im.metodo_habilitado('pix_automatico')
