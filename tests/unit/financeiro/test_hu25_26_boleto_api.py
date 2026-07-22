"""
Revisão das HUs 25/26 com os providers de cobrança registrada (C6/Sicoob).

- HU-26: toda baixa via Boleto-API (webhook / polling / conciliação Pix) deve
  gravar HistoricoPagamento com origem BOLETO_API — sem isso o valor recebido
  não entra no painel de Conciliação & Saúde (que agrega por HistoricoPagamento).
- HU-25: boletos de contas C6/Sicoob (REGISTRADO) conciliam por webhook, não por
  retorno CNAB — saem do contador do Passo 3 e viram o contador a_conciliar_api.
"""
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse


def _contrato_api(provider='sicoob', cobranca_id='cob-hu26', banco='756'):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaApiFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import StatusBoleto, TipoParcela

    imob = ImobiliariaFactory()
    conta = ContaBancariaApiFactory(imobiliaria=imob, banco=banco, provider=provider,
                                    principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=CompradorFactory(),
        numero_contrato=f'CTR-HU26-{cobranca_id}', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('12000.00'), valor_entrada=Decimal('2000.00'),
        numero_parcelas=2, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
    )
    parcela = contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).first()
    parcela.cobranca_id = cobranca_id
    parcela.status_boleto = StatusBoleto.REGISTRADO
    parcela.conta_bancaria = conta
    parcela.save(update_fields=['cobranca_id', 'status_boleto', 'conta_bancaria'])
    return imob, conta, parcela


@pytest.mark.django_db
class TestHu26OrigemBoletoApi:
    def test_baixa_por_conciliacao_grava_historico(self):
        from financeiro.models import HistoricoPagamento
        from financeiro.services.boleto_api_conciliacao import baixar_por_conciliacao
        _, _, parcela = _contrato_api(cobranca_id='cob-conc')
        r = baixar_por_conciliacao(parcela, valor=Decimal('500.00'), origem='polling-sicoob')
        assert r['status'] == 'baixado'
        h = HistoricoPagamento.objects.get(parcela=parcela)
        assert h.origem_pagamento == 'BOLETO_API'
        assert h.valor_pago == Decimal('500.00')

    def test_webhook_liquidado_grava_historico(self, settings):
        from financeiro.models import HistoricoPagamento
        settings.EVENT_WEBHOOK_SECRET = ''
        settings.DEBUG = True
        _, _, parcela = _contrato_api(cobranca_id='cob-wh26')
        resp = Client().post(
            '/financeiro/webhooks/boleto-api/',
            data=json.dumps({'id': 'cob-wh26', 'status': 'liquidado', 'valor': '321.00'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        h = HistoricoPagamento.objects.get(parcela=parcela)
        assert h.origem_pagamento == 'BOLETO_API'

    def test_painel_saude_conta_recebido_boleto_api(self, settings):
        """O valor baixado via Boleto-API entra em 'recebido' e na origem BOLETO_API."""
        from django.contrib.auth import get_user_model
        from financeiro.services.boleto_api_conciliacao import baixar_por_conciliacao
        from django.utils import timezone
        _, _, parcela = _contrato_api(cobranca_id='cob-kpi')
        baixar_por_conciliacao(parcela, valor=Decimal('700.00'), origem='pix')

        cli = Client()
        cli.force_login(get_user_model().objects.create_superuser('adm26', 'a@x.com', 'x'))
        hoje = timezone.localdate()
        r = cli.get(reverse('financeiro:api_conciliacao_saude'),
                    {'mes': hoje.month, 'ano': hoje.year})
        data = r.json()
        assert data['sucesso'] is True
        assert data['origem']['BOLETO_API'] == 700.0
        assert data['recebido'] >= 700.0
        # A soma por origem fecha com o total recebido (RN-03).
        assert round(sum(data['origem'].values()), 2) == round(data['recebido'], 2)


@pytest.mark.django_db
class TestHu25ContadorApi:
    def test_hub_separa_conciliacao_api_do_cnab(self):
        """Parcela REGISTRADO de conta C6/Sicoob não infla o contador CNAB do
        Passo 3; aparece em a_conciliar_api."""
        from django.contrib.auth import get_user_model
        _contrato_api(cobranca_id='cob-hub')

        cli = Client()
        cli.force_login(get_user_model().objects.create_superuser('adm25', 'a@x.com', 'x'))
        r = cli.get(reverse('financeiro:api_cobranca_estado'))
        estado = r.json()['estado']
        assert estado['a_conciliar_api'] == 1
        assert estado['a_conciliar_boletos'] == 0
