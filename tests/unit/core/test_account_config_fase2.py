"""Fase 2 Boleto-API — account_config estruturado (get_config, faltando)."""
from core.models import ContaBancaria


class TestGetConfig:
    def test_le_valor(self):
        cb = ContaBancaria(account_config={'numeroCliente': '123'})
        assert cb.get_config('numeroCliente') == '123'

    def test_default(self):
        cb = ContaBancaria(account_config={})
        assert cb.get_config('x') is None
        assert cb.get_config('x', 'd') == 'd'

    def test_config_none(self):
        cb = ContaBancaria(account_config=None)
        assert cb.get_config('x', 'd') == 'd'


class TestAccountConfigFaltando:
    def test_sicoob_faltando(self):
        cb = ContaBancaria(banco='756', provider='sicoob',
                           account_config={'numeroCliente': '1'})
        assert set(cb.account_config_faltando()) == {'codigoModalidade', 'numeroContaCorrente'}

    def test_sicoob_completo(self):
        cb = ContaBancaria(banco='756', provider='sicoob', account_config={
            'numeroCliente': '1', 'codigoModalidade': '1', 'numeroContaCorrente': '9',
        })
        assert cb.account_config_faltando() == []

    def test_c6_faltando_e_completo(self):
        assert ContaBancaria(banco='336', provider='c6',
                             account_config={}).account_config_faltando() == ['billing_scheme']
        assert ContaBancaria(banco='336', provider='c6',
                             account_config={'billing_scheme': 'x'}).account_config_faltando() == []

    def test_brcobranca_nunca_falta(self):
        assert ContaBancaria(banco='001', provider='brcobranca',
                             account_config=None).account_config_faltando() == []
