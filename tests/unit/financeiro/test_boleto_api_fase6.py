"""
Fase 6 Boleto-API — gestão que propaga ao gateway: cancelamento (DELETE),
estorno (devolução Pix) e alteração (PUT). Tudo com mocks.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest

from financeiro.models import Parcela, StatusBoleto, StatusCobranca as S

CLIENT = 'financeiro.services.boleto_api_client.BoletoApiClient'


def _parcela_c6(**kw):
    from tests.fixtures.factories import ParcelaFactory, ContaBancariaApiFactory
    conta = ContaBancariaApiFactory(banco='336', provider='c6', tenant_id='ten-c6')
    conta.set_bapi_token('bapi_x')
    conta.save()
    defaults = dict(provider='c6', cobranca_id='C1', conta_bancaria=conta,
                    status_boleto=StatusBoleto.REGISTRADO, pago=False)
    defaults.update(kw)
    return ParcelaFactory(**defaults)


@pytest.mark.django_db
class TestCancelamentoPropaga:
    def test_c6_cancela_no_gateway(self):
        p = _parcela_c6(status_cobranca=S.REGISTRADA)
        with patch(f'{CLIENT}.baixar_cobranca', return_value={'sucesso': True}) as m:
            ok = p.cancelar_boleto('motivo x')
        assert ok is True
        m.assert_called_once()
        assert m.call_args.kwargs.get('bapi_token') == 'bapi_x'
        p.refresh_from_db()
        assert p.status_boleto == StatusBoleto.CANCELADO
        assert p.status_cobranca == S.BAIXADA

    def test_gateway_recusa_nao_cancela_local(self):
        p = _parcela_c6()
        with patch(f'{CLIENT}.baixar_cobranca',
                   return_value={'sucesso': False, 'motivo': 'validacao', 'erro': 'x'}):
            ok = p.cancelar_boleto()
        assert ok is False
        p.refresh_from_db()
        assert p.status_boleto == StatusBoleto.REGISTRADO  # inalterado

    def test_brcobranca_nao_chama_gateway(self):
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(provider='', status_boleto=StatusBoleto.GERADO, pago=False)
        with patch(f'{CLIENT}.baixar_cobranca') as m:
            ok = p.cancelar_boleto()
        assert ok is True
        m.assert_not_called()
        p.refresh_from_db()
        assert p.status_boleto == StatusBoleto.CANCELADO


@pytest.mark.django_db
class TestEstorno:
    def test_estorna_pix_e_marca_estornada(self):
        p = _parcela_c6(status_cobranca=S.LIQUIDADA)
        with patch(f'{CLIENT}.devolver_pix',
                   return_value={'sucesso': True, 'devolucao_id': 'D1'}) as m:
            r = p.estornar_cobranca(valor=Decimal('100'), e2eid='E2E1')
        assert r['sucesso'] is True
        m.assert_called_once()
        assert m.call_args.kwargs.get('bapi_token') == 'bapi_x'
        p.refresh_from_db()
        assert p.status_cobranca == S.ESTORNADA

    def test_estorno_exige_e2eid(self):
        p = _parcela_c6(status_cobranca=S.LIQUIDADA)
        assert p.estornar_cobranca(valor=Decimal('100'))['sucesso'] is False

    def test_estorno_so_boleto_api(self):
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(provider='')
        assert p.estornar_cobranca(e2eid='X')['sucesso'] is False


@pytest.mark.django_db
class TestAlteracao:
    def test_altera_cobranca_registrada(self):
        p = _parcela_c6()
        with patch(f'{CLIENT}.alterar_cobranca',
                   return_value={'sucesso': True, 'cobranca_id': 'C1'}) as m:
            r = p.alterar_cobranca({'vencimento': '2026-03-01'})
        assert r['sucesso'] is True
        m.assert_called_once()

    def test_altera_exige_cobranca_registrada(self):
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(provider='', cobranca_id='')
        assert p.alterar_cobranca({'valor': 1})['sucesso'] is False
