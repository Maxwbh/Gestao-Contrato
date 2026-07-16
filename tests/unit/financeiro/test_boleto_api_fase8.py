"""
Fase 8 Boleto-API — Pix Automático (recorrência): modelo, adesão/cancelamento,
webhook (pix_automatico.recorrencia/cobranca) e job de agendamento D-2. Mocks.
"""
import hashlib
import hmac
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from financeiro.models import (
    RecorrenciaPix, RecStatusPA, StatusBoleto, StatusCobranca as S, MetodoCobranca,
)
from financeiro import tasks

CLIENT = 'financeiro.services.boleto_api_client.BoletoApiClient'
SECRET = 'test-webhook-secret'


def _post(client, payload):
    body = json.dumps(payload).encode()
    sig = 'sha256=' + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post(reverse('financeiro:webhook_boleto_api'), data=body,
                       content_type='application/json', HTTP_X_SIGNATURE=sig)


@pytest.fixture
def contrato_c6(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import TipoParcela

    imob = ImobiliariaFactory(metodos_cobranca=['boleto', 'pix_automatico'])
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='336', principal=True, ativo=True,
        convenio='000000001', provider='c6', tenant_id='ten-c6',
        account_config={'billing_scheme': 'padrao'})
    conta.set_bapi_token('bapi_c6'); conta.save()
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=CompradorFactory(),
        numero_contrato='CTR-F8', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000'), valor_entrada=Decimal('10000'),
        numero_parcelas=6, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO)
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        pago=False, conta_bancaria=conta, valor_boleto=Decimal('8333.33'))
    return conta, contrato


class TestModeloRecorrencia:
    def test_transicoes(self):
        r = RecorrenciaPix(status=RecStatusPA.CRIADA)
        assert r.transicionar(RecStatusPA.APROVADA)
        assert not r.transicionar(RecStatusPA.CRIADA)   # APROVADA não volta
        assert r.transicionar(RecStatusPA.CANCELADA)    # APROVADA → CANCELADA ok
        assert not r.transicionar(RecStatusPA.APROVADA)  # CANCELADA terminal


@pytest.mark.django_db
class TestAdesaoCancelamento:
    def test_aderir_cria_recorrencia(self, contrato_c6):
        _, contrato = contrato_c6
        with patch(f'{CLIENT}.criar_recorrencia',
                   return_value={'sucesso': True, 'id_rec': 'RN-1', 'status': 'CRIADA'}) as m:
            r = contrato.aderir_pix_automatico()
        assert r['sucesso'] and r['id_rec'] == 'RN-1'
        assert m.call_args.kwargs.get('bapi_token') == 'bapi_c6'
        rec = RecorrenciaPix.objects.get(contrato=contrato)
        assert rec.id_rec == 'RN-1' and rec.status == RecStatusPA.CRIADA

    def test_aderir_bloqueia_duplicado(self, contrato_c6):
        _, contrato = contrato_c6
        RecorrenciaPix.objects.create(contrato=contrato, id_rec='X', provider='c6',
                                      status=RecStatusPA.APROVADA)
        assert contrato.aderir_pix_automatico()['sucesso'] is False

    def test_cancelar(self, contrato_c6):
        _, contrato = contrato_c6
        rec = RecorrenciaPix.objects.create(contrato=contrato, id_rec='RN-9', provider='c6',
                                            status=RecStatusPA.APROVADA)
        with patch(f'{CLIENT}.cancelar_recorrencia', return_value={'sucesso': True}):
            r = contrato.cancelar_pix_automatico()
        assert r['sucesso'] is True
        rec.refresh_from_db()
        assert rec.status == RecStatusPA.CANCELADA


@pytest.mark.django_db
class TestWebhookPixAutomatico:
    def test_recorrencia_atualiza_status(self, client, settings, contrato_c6):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        _, contrato = contrato_c6
        rec = RecorrenciaPix.objects.create(contrato=contrato, id_rec='R1', provider='c6',
                                            status=RecStatusPA.CRIADA)
        r = _post(client, {'event': 'pix_automatico.recorrencia', 'idRec': 'R1', 'status': 'APROVADA'})
        assert r.json()['status'] == 'recorrencia'
        rec.refresh_from_db()
        assert rec.status == RecStatusPA.APROVADA

    def test_cobranca_do_ciclo_baixa_por_txid(self, client, settings, contrato_c6):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        _, contrato = contrato_c6
        p = contrato.parcelas.first()
        p.pix_txid = 'TXPA'; p.status_cobranca = S.REGISTRADA; p.save()
        r = _post(client, {'event': 'pix_automatico.cobranca', 'txid': 'TXPA',
                           'status': 'liquidado', 'valor': '8333.33'})
        assert r.json()['status'] == 'baixado'
        p.refresh_from_db()
        assert p.pago and p.status_cobranca == S.LIQUIDADA


@pytest.mark.django_db
class TestJobAgendamento:
    def test_agenda_d2(self, contrato_c6):
        conta, contrato = contrato_c6
        RecorrenciaPix.objects.create(contrato=contrato, id_rec='R2', provider='c6',
                                      status=RecStatusPA.APROVADA)
        alvo = timezone.now().date() + timedelta(days=2)
        p = contrato.parcelas.filter(pago=False).first()
        p.data_vencimento = alvo; p.valor_atual = Decimal('8333.33'); p.save()
        with patch(f'{CLIENT}.agendar_cobranca_pa',
                   return_value={'sucesso': True, 'txid': 'CTx', 'status': 'AGENDADA'}) as m:
            r = tasks.agendar_cobrancas_pix_automatico(dias_antecedencia=2)
        assert r['agendadas'] == 1
        m.assert_called_once()
        p.refresh_from_db()
        assert p.metodo_cobranca == MetodoCobranca.PIX_AUTOMATICO and p.pix_txid
