"""
Backlog Boleto-API — BAPI-14/15 (Pix avulso), BAPI-32 (conciliação
financeira), BAPI-36 (retentativa do Pix Automático) e BAPI-37 (carnê via
gateway). Tudo com o gateway mockado (sem rede).
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from core.models import MetodoCobranca
from financeiro.models import (StatusCobranca as S, RecorrenciaPix, RecStatusPA)

CLIENT = 'financeiro.services.boleto_api_client.BoletoApiClient'


@pytest.fixture
def imob_api(db):
    from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaApiFactory
    imob = ImobiliariaFactory()
    conta = ContaBancariaApiFactory(imobiliaria=imob, principal=True)
    return imob, conta


def _parcela(imob, **kw):
    from tests.fixtures.factories import ParcelaFactory
    return ParcelaFactory(contrato__imovel__imobiliaria=imob, **kw)


# ---------------------------------------------------------------------------
# BAPI-14/15 — Pix avulso (2ª via / quitação)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEmitirPixAvulso:
    def test_emite_e_persiste_txid_e_copia_cola(self, imob_api):
        imob, conta = imob_api
        p = _parcela(imob)
        with patch(f'{CLIENT}.emitir_pix', return_value={
                'sucesso': True, 'txid': 'TXAV1', 'pix_copia_cola': '000201BR...'}) as m:
            r = p.emitir_pix_avulso()
        assert r['sucesso'] and r['txid'] == 'TXAV1'
        p.refresh_from_db()
        assert p.pix_txid == 'TXAV1'
        assert p.pix_copia_cola == '000201BR...'
        assert p.status_cobranca == S.REGISTRADA
        assert p.provider == conta.provider
        assert m.call_args.args[3]['modalidade'] == 'cobv'

    def test_modalidade_imediata(self, imob_api):
        imob, _ = imob_api
        p = _parcela(imob)
        with patch(f'{CLIENT}.emitir_pix', return_value={
                'sucesso': True, 'txid': 'T', 'pix_copia_cola': 'E'}) as m:
            p.emitir_pix_avulso(modalidade='cob')
        assert m.call_args.args[3]['modalidade'] == 'cob'

    def test_parcela_paga_recusa(self, imob_api):
        imob, _ = imob_api
        p = _parcela(imob, pago=True)
        r = p.emitir_pix_avulso()
        assert not r['sucesso'] and 'paga' in r['erro']

    def test_sem_conta_api_recusa(self, db):
        from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaFactory
        imob = ImobiliariaFactory()
        ContaBancariaFactory(imobiliaria=imob)  # brcobranca
        p = _parcela(imob)
        r = p.emitir_pix_avulso()
        assert not r['sucesso'] and 'C6/Sicoob' in r['erro']

    def test_view_emite_pix(self, client, imob_api):
        from tests.fixtures.factories import SuperUserFactory
        imob, _ = imob_api
        p = _parcela(imob)
        client.force_login(SuperUserFactory())
        with patch(f'{CLIENT}.emitir_pix', return_value={
                'sucesso': True, 'txid': 'TXV', 'pix_copia_cola': 'EMV'}):
            resp = client.post(reverse('financeiro:emitir_pix_parcela', args=[p.pk]))
        assert resp.status_code == 200
        assert resp.json()['txid'] == 'TXV'

    def test_view_modalidade_invalida_400(self, client, imob_api):
        from tests.fixtures.factories import SuperUserFactory
        imob, _ = imob_api
        p = _parcela(imob)
        client.force_login(SuperUserFactory())
        resp = client.post(reverse('financeiro:emitir_pix_parcela', args=[p.pk]),
                           {'modalidade': 'xxx'})
        assert resp.status_code == 400

    def test_view_tenant_alheio_404(self, client, imob_api):
        from tests.fixtures.factories import (UserFactory, ImobiliariaFactory,
                                              AcessoUsuarioFactory)
        imob, _ = imob_api
        p = _parcela(imob)
        outra = ImobiliariaFactory()
        user = UserFactory()
        AcessoUsuarioFactory(usuario=user, imobiliaria=outra,
                             contabilidade=outra.contabilidade)
        client.force_login(user)
        resp = client.post(reverse('financeiro:emitir_pix_parcela', args=[p.pk]))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# BAPI-36 — Retentativa do Pix Automático
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestRetentativaPixAutomatico:
    def _setup(self, imob, vencida_ha=1, rec_status=RecStatusPA.APROVADA, pago=False):
        p = _parcela(imob, metodo_cobranca=MetodoCobranca.PIX_AUTOMATICO,
                     status_cobranca=S.REGISTRADA, pago=pago, provider='c6',
                     data_vencimento=timezone.localdate() - timedelta(days=vencida_ha))
        p.pix_txid = f'CT{p.contrato_id:07d}202607'
        p.save(update_fields=['pix_txid'])
        RecorrenciaPix.objects.create(contrato=p.contrato, id_rec=f'R{p.pk}',
                                      provider='c6', status=rec_status)
        return p

    def test_retenta_vencida_nao_paga(self, imob_api):
        from financeiro.tasks import retentar_cobrancas_pix_automatico
        imob, _ = imob_api
        p = self._setup(imob)
        with patch(f'{CLIENT}.retentar_cobranca_pa',
                   return_value={'sucesso': True}) as m:
            r = retentar_cobrancas_pix_automatico()
        assert r['retentadas'] == 1
        assert m.call_args.args[0] == p.pix_txid

    def test_nao_retenta_paga_nem_rejeitada(self, imob_api):
        from financeiro.tasks import retentar_cobrancas_pix_automatico
        imob, _ = imob_api
        self._setup(imob, pago=True)
        self._setup(imob, rec_status=RecStatusPA.CANCELADA)
        with patch(f'{CLIENT}.retentar_cobranca_pa') as m:
            r = retentar_cobrancas_pix_automatico()
        assert r['retentadas'] == 0 and not m.called

    def test_fora_da_janela_nao_retenta(self, imob_api):
        from financeiro.tasks import retentar_cobrancas_pix_automatico
        imob, _ = imob_api
        self._setup(imob, vencida_ha=30)
        with patch(f'{CLIENT}.retentar_cobranca_pa') as m:
            retentar_cobrancas_pix_automatico(janela_dias=7)
        assert not m.called

    def test_agendada_no_beat(self):
        from gestao_contrato.celery import app
        tasks = {e['task'] for e in app.conf.beat_schedule.values()}
        assert 'financeiro.tasks.retentar_cobrancas_pix_automatico' in tasks


# ---------------------------------------------------------------------------
# BAPI-32 — Conciliação financeira (recebíveis × sistema)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestConciliacaoFinanceira:
    def test_classificacao(self, imob_api):
        from financeiro.services.boleto_api_conciliacao import conciliacao_financeira
        imob, _ = imob_api
        hoje = timezone.localdate()

        def liquidada(cobranca_id='', txid='', valor='100.00'):
            p = _parcela(imob, status_cobranca=S.LIQUIDADA, pago=True, provider='sicoob')
            p.cobranca_id = cobranca_id
            p.pix_txid = txid
            p.data_pagamento = hoje
            p.valor_pago = Decimal(valor)
            p.save()
            return p

        p_ok = liquidada(cobranca_id='C1')
        p_div = liquidada(txid='TX2', valor='90.00')
        p_so_sys = liquidada(cobranca_id='C3')

        itens = [
            {'cobranca_id': 'C1', 'valor': '100.00'},
            {'txid': 'TX2', 'valor': '95.00'},
            {'cobranca_id': 'C-ORFAO', 'valor': '50.00'},
        ]
        with patch(f'{CLIENT}.consultar_conciliacao',
                   return_value={'sucesso': True, 'itens': itens}):
            r = conciliacao_financeira(imob, hoje - timedelta(days=7), hoje)

        assert [c['parcela'].pk for c in r['conferidos']] == [p_ok.pk]
        assert [d['parcela'].pk for d in r['divergentes']] == [p_div.pk]
        assert r['apenas_gateway'][0]['cobranca_id'] == 'C-ORFAO'
        assert [p.pk for p in r['apenas_sistema']] == [p_so_sys.pk]
        assert not r['erros']

    def test_erro_no_gateway_reportado(self, imob_api):
        from financeiro.services.boleto_api_conciliacao import conciliacao_financeira
        imob, _ = imob_api
        hoje = timezone.localdate()
        with patch(f'{CLIENT}.consultar_conciliacao',
                   return_value={'sucesso': False, 'erro': 'offline'}):
            r = conciliacao_financeira(imob, hoje, hoje)
        assert r['erros'] and r['erros'][0]['erro'] == 'offline'

    def test_view_relatorio(self, client, imob_api):
        from tests.fixtures.factories import SuperUserFactory
        imob, _ = imob_api
        client.force_login(SuperUserFactory())
        with patch(f'{CLIENT}.consultar_conciliacao',
                   return_value={'sucesso': True, 'itens': []}):
            r = client.get(reverse('financeiro:relatorio_conciliacao_financeira'),
                           {'imobiliaria': imob.id})
        assert r.status_code == 200
        assert r.context['resultado'] is not None

    def test_client_consultar_conciliacao_e_extrato(self):
        from financeiro.services.boleto_api_client import BoletoApiClient
        client_api = BoletoApiClient()

        class FakeResp:
            status_code = 200
            def json(self):
                return {'itens': [{'cobranca_id': 'C1'}], 'lancamentos': [{'tipo': 'credito'}]}

        with patch.object(BoletoApiClient, '_request', return_value=FakeResp()):
            r1 = client_api.consultar_conciliacao('2026-07-01', '2026-07-31', 't1', 'c6')
            r2 = client_api.consultar_extrato('2026-07-01', '2026-07-31', 't1', 'c6')
        assert r1['sucesso'] and r1['itens'][0]['cobranca_id'] == 'C1'
        assert r2['sucesso'] and r2['lancamentos'][0]['tipo'] == 'credito'


# ---------------------------------------------------------------------------
# BAPI-37 — Carnê via gateway
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCarneViaGateway:
    def test_conta_api_usa_gateway_e_persiste_rastreio(self, imob_api):
        from financeiro.services.carne_service import gerar_carne_pdf
        imob, conta = imob_api
        p1 = _parcela(imob)
        p2 = _parcela(imob, contrato=p1.contrato)
        cobrancas = [
            {'cobranca_id': 'K1', 'linha_digitavel': 'L1', 'codigo_barras': 'B1',
             'nosso_numero': 'N1', 'ext_ref': 'E1'},
            {'cobranca_id': 'K2', 'linha_digitavel': 'L2', 'codigo_barras': 'B2',
             'nosso_numero': 'N2', 'ext_ref': 'E2'},
        ]
        with patch(f'{CLIENT}.gerar_carne', return_value={
                'sucesso': True, 'carne_pdf_content': b'%PDF-carne',
                'cobrancas': cobrancas}) as m:
            pdf = gerar_carne_pdf([p1, p2], p1.contrato)
        assert pdf == b'%PDF-carne'
        assert m.call_args.args[1] == conta.provider
        p1.refresh_from_db(); p2.refresh_from_db()
        assert p1.cobranca_id == 'K1' and p2.cobranca_id == 'K2'
        assert p1.status_cobranca == S.REGISTRADA
        assert p1.metodo_cobranca == MetodoCobranca.CARNE
        assert p1.ext_ref == 'E1'

    def test_gateway_recusa_levanta_erro(self, imob_api):
        from financeiro.services.carne_service import gerar_carne_pdf
        imob, _ = imob_api
        p = _parcela(imob)
        with patch(f'{CLIENT}.gerar_carne',
                   return_value={'sucesso': False, 'erro': 'account_config incompleto'}):
            with pytest.raises(RuntimeError, match='account_config incompleto'):
                gerar_carne_pdf([p], p.contrato)

    def test_conta_brcobranca_mantem_fluxo_legado(self, db):
        from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaFactory
        from financeiro.services.carne_service import gerar_carne_pdf
        imob = ImobiliariaFactory()
        ContaBancariaFactory(imobiliaria=imob, principal=True)  # brcobranca
        p = _parcela(imob)
        with patch('financeiro.services.boleto_service.BoletoService.gerar_carne',
                   return_value={'sucesso': True, 'pdf_content': b'%PDF-br'}) as m:
            pdf = gerar_carne_pdf([p], p.contrato)
        assert pdf == b'%PDF-br' and m.called
