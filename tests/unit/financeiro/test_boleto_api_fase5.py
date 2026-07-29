"""
Fase 5 Boleto-API — máquina de estados de status_cobranca: guardas de transição,
webhook rejeita eventos fora de ordem, e 409 (CIP) marca AGUARDANDO_CIP.
"""
import hashlib
import hmac
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from financeiro.models import Parcela, StatusBoleto, StatusCobranca as S

SECRET = 'test-webhook-secret'


def _post(client, payload, secret=SECRET):
    body = json.dumps(payload).encode()
    sig = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(reverse('financeiro:webhook_boleto_api'), data=body,
                       content_type='application/json', HTTP_X_SIGNATURE=sig)


class TestMaquinaEstados:
    def test_fluxo_feliz(self):
        p = Parcela()  # ''
        assert p.transicionar_cobranca(S.REGISTRADA)
        assert p.transicionar_cobranca(S.LIQUIDADA)
        assert p.transicionar_cobranca(S.ESTORNADA)

    def test_inicial_permissivo(self):
        # '' (desconhecido) aceita qualquer status, inclusive liquidação direta.
        assert Parcela().pode_transicionar_cobranca(S.LIQUIDADA)

    def test_registrada_nao_regride_para_pendente(self):
        assert not Parcela(status_cobranca=S.REGISTRADA).pode_transicionar_cobranca(S.PENDENTE)

    def test_transicao_ilegal_nao_altera(self):
        p = Parcela(status_cobranca=S.LIQUIDADA)
        assert p.transicionar_cobranca(S.REGISTRADA) is False
        assert p.status_cobranca == S.LIQUIDADA

    def test_terminal_estornada(self):
        p = Parcela(status_cobranca=S.ESTORNADA)
        assert not p.transicionar_cobranca(S.LIQUIDADA)
        assert p.transicionar_cobranca(S.ESTORNADA)  # idempotente

    def test_reemissao_apos_baixada_ou_expirada(self):
        assert Parcela(status_cobranca=S.BAIXADA).transicionar_cobranca(S.REGISTRADA)
        assert Parcela(status_cobranca=S.EXPIRADA).transicionar_cobranca(S.REGISTRADA)

    def test_aguardando_cip_a_partir_do_inicial(self):
        assert Parcela().pode_transicionar_cobranca(S.AGUARDANDO_CIP)


@pytest.mark.django_db
class TestWebhookForaDeOrdem:
    def test_evento_ilegal_e_ignorado(self, client, settings):
        settings.EVENT_WEBHOOK_SECRET = SECRET
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(pago=False, status_boleto=StatusBoleto.REGISTRADO,
                           cobranca_id='CX', status_cobranca=S.LIQUIDADA)
        r = _post(client, {'id': 'CX', 'status': 'registrado', 'event': 'cobranca.atualizada'})
        assert r.json()['status'] == 'ignorado'
        p.refresh_from_db()
        assert p.status_cobranca == S.LIQUIDADA  # inalterado


@pytest.fixture
def base_c6(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import TipoParcela

    imob = ImobiliariaFactory()
    conta = ContaBancariaFactory(
        imobiliaria=imob, banco='336', principal=True, ativo=True,
        convenio='000000000001', provider='c6', tenant_id='tenant-abc',
        account_config={'billing_scheme': 'padrao'},
    )
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory()
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-F5-1', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000.00'), valor_entrada=Decimal('10000.00'),
        numero_parcelas=6, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
    )
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
        valor_boleto=Decimal('8333.33'),
    )
    return conta, contrato


@pytest.mark.django_db
class TestAguardandoCip:
    def test_409_cip_marca_aguardando_cip(self, base_c6):
        conta, contrato = base_c6
        parcela = contrato.parcelas.first()
        with patch('financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca',
                   return_value={'sucesso': False, 'motivo': 'cip', 'codigo': 409, 'erro': 'CIP'}):
            resultado = parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        assert resultado['sucesso'] is False and resultado['motivo'] == 'cip'
        parcela.refresh_from_db()
        assert parcela.status_cobranca == S.AGUARDANDO_CIP
