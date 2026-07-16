"""
Fase 7 Boleto-API — agendadores: polling de boleto Sicoob, conciliação de Pix
recebidos (rede de segurança) e fila de reprocessamento 409/CIP. Tudo com mocks.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from financeiro.models import StatusBoleto, StatusCobranca as S
from financeiro import tasks

CLIENT = 'financeiro.services.boleto_api_client.BoletoApiClient'


@pytest.fixture
def contrato_sicoob(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import TipoParcela

    imob = ImobiliariaFactory()
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='756', principal=True, ativo=True,
        convenio='000000001', provider='sicoob', tenant_id='ten-s',
        account_config={'numeroCliente': '1', 'codigoModalidade': '1', 'numeroContaCorrente': '9'},
    )
    conta.set_bapi_token('bapi_s')
    conta.save()
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=CompradorFactory(),
        numero_contrato='CTR-F7', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000'), valor_entrada=Decimal('10000'),
        numero_parcelas=6, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
    )
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
        valor_boleto=Decimal('8333.33'))
    return conta, contrato


@pytest.mark.django_db
class TestPollingSicoob:
    def test_baixa_quando_liquidado(self, contrato_sicoob):
        _, contrato = contrato_sicoob
        p = contrato.parcelas.first()
        p.provider = 'sicoob'; p.cobranca_id = 'C1'; p.status_cobranca = S.REGISTRADA; p.save()
        with patch(f'{CLIENT}.consultar_cobranca',
                   return_value={'sucesso': True, 'status': 'liquidado', 'valor': Decimal('8333.33')}) as m:
            r = tasks.polling_boletos_sicoob()
        assert r['baixadas'] == 1
        assert m.call_args.kwargs.get('bapi_token') == 'bapi_s'
        p.refresh_from_db()
        assert p.pago and p.status_cobranca == S.LIQUIDADA

    def test_nao_liquidado_nao_baixa(self, contrato_sicoob):
        _, contrato = contrato_sicoob
        p = contrato.parcelas.first()
        p.provider = 'sicoob'; p.cobranca_id = 'C2'; p.save()
        with patch(f'{CLIENT}.consultar_cobranca',
                   return_value={'sucesso': True, 'status': 'registrado'}):
            r = tasks.polling_boletos_sicoob()
        assert r['baixadas'] == 0
        p.refresh_from_db()
        assert p.pago is False


@pytest.mark.django_db
class TestConciliacaoPix:
    def test_baixa_por_txid(self):
        from tests.fixtures.factories import ContaBancariaApiFactory, ParcelaFactory
        conta = ContaBancariaApiFactory(banco='336', provider='c6', tenant_id='t', ativo=True)
        conta.set_bapi_token('b'); conta.save()
        p = ParcelaFactory(pix_txid='TX9', pago=False, valor_boleto=Decimal('50'))
        with patch(f'{CLIENT}.listar_pix_recebidos',
                   return_value={'sucesso': True, 'itens': [{'txid': 'TX9', 'valor': 50}]}):
            r = tasks.conciliar_pix_recebidos(dias=1)
        assert r['baixadas'] == 1
        p.refresh_from_db()
        assert p.pago and p.status_cobranca == S.LIQUIDADA

    def test_txid_sem_parcela_nao_quebra(self):
        from tests.fixtures.factories import ContaBancariaApiFactory
        conta = ContaBancariaApiFactory(banco='336', provider='c6', tenant_id='t', ativo=True)
        conta.set_bapi_token('b'); conta.save()
        with patch(f'{CLIENT}.listar_pix_recebidos',
                   return_value={'sucesso': True, 'itens': [{'txid': 'INEXISTENTE', 'valor': 1}]}):
            r = tasks.conciliar_pix_recebidos()
        assert r['baixadas'] == 0


@pytest.mark.django_db
class TestReprocessarCip:
    def test_reprocessa_aguardando_cip(self, contrato_sicoob):
        _, contrato = contrato_sicoob
        p = contrato.parcelas.first()
        p.provider = 'sicoob'; p.status_cobranca = S.AGUARDANDO_CIP; p.save()
        ok = {'sucesso': True, 'cobranca_id': 'CX', 'valor': Decimal('8333.33'),
              'linha_digitavel': '1', 'codigo_barras': '2', 'nosso_numero': '1',
              'nosso_numero_formatado': '1', 'nosso_numero_dv': '', 'pix_copia_cola': '',
              'pix_qrcode': ''}
        with patch(f'{CLIENT}.registrar_cobranca', return_value=ok):
            r = tasks.reprocessar_fila_cip()
        assert r['reprocessadas'] == 1
        p.refresh_from_db()
        assert p.status_cobranca == S.REGISTRADA


@pytest.mark.django_db
class TestServicoConciliacao:
    def test_idempotente_ja_pago(self):
        from tests.fixtures.factories import ParcelaFactory
        from financeiro.services.boleto_api_conciliacao import baixar_por_conciliacao
        p = ParcelaFactory(pago=True)
        assert baixar_por_conciliacao(p)['status'] == 'duplicado'
