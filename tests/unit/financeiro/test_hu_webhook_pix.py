"""
HU Webhook PIX — Roadmap 34.3 P2
=================================

Cobre o endpoint POST /financeiro/webhook/pix/ e a lógica de:
  - Deduplicação por EndToEndId
  - Baixa automática da parcela via registrar_pagamento
  - Identificação da parcela pelo pix_txid
  - Autenticação por Bearer token
  - Parcela não encontrada (SEM_PARCELA)
  - Formato BCB padrão (array "pix")
"""

import json
import pytest
from decimal import Decimal
from datetime import date

from django.test import Client
from django.urls import reverse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio_pix(db):
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    imob = ImobiliariaFactory(nome='Imob PIX Test')
    ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador PIX')
    return imob, imovel, comprador


@pytest.fixture
def parcela_pix(db, dominio_pix):
    """Parcela com pix_txid definido, não paga, valor R$ 1000."""
    from contratos.models import Contrato, TipoAmortizacao, TipoCorrecao, StatusContrato
    imob, imovel, comprador = dominio_pix
    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='CTR-PIX-001',
        data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('12000.00'),
        valor_entrada=Decimal('2000.00'),
        numero_parcelas=10,
        dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA,
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
    )
    parcela = contrato.parcelas.order_by('numero_parcela').first()
    parcela.pix_txid = 'TXID-TESTE-001'
    parcela.save(update_fields=['pix_txid'])
    return parcela


@pytest.fixture
def client_pix():
    return Client()


def _payload(end_to_end_id='E12345678202501011200000000001',
             txid='TXID-TESTE-001',
             valor='1000.00',
             horario='2025-02-01T12:00:00-03:00'):
    return {
        'pix': [{
            'endToEndId': end_to_end_id,
            'txid': txid,
            'valor': valor,
            'horario': horario,
            'pagador': {'cpf': '12345678901', 'nome': 'João Testador'},
            'infoPagador': 'Pagamento parcela 1',
        }]
    }


def _post(client, data, token=None):
    headers = {'content_type': 'application/json'}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client.post(
        reverse('financeiro:webhook_pix'),
        data=json.dumps(data),
        **headers,
    )


# ---------------------------------------------------------------------------
# TestAutenticacaoWebhookPIX
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutenticacaoWebhookPIX:
    def test_sem_token_em_producao_responde_503(self, client_pix, settings, parcela_pix):
        """Fail-closed: token vazio + DEBUG=False ⇒ 503 (não aceita POST anônimo)."""
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        settings.DEBUG = False
        resp = _post(client_pix, _payload())
        assert resp.status_code == 503

    def test_sem_token_em_debug_aceita(self, client_pix, settings, parcela_pix):
        """Em DEBUG (dev/staging) a validação continua sendo pulada."""
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        settings.DEBUG = True
        resp = _post(client_pix, _payload())
        assert resp.status_code == 200

    def test_com_token_correto_aceita(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = 'segredo123'
        resp = _post(client_pix, _payload(), token='segredo123')
        assert resp.status_code == 200

    def test_com_token_errado_rejeita_401(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = 'segredo123'
        resp = _post(client_pix, _payload(), token='errado')
        assert resp.status_code == 401

    def test_sem_token_header_rejeita_401(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = 'segredo123'
        resp = _post(client_pix, _payload())  # no token
        assert resp.status_code == 401

    def test_x_api_key_header_aceito(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = 'segredo123'
        resp = client_pix.post(
            reverse('financeiro:webhook_pix'),
            data=json.dumps(_payload()),
            content_type='application/json',
            HTTP_X_API_KEY='segredo123',
        )
        assert resp.status_code == 200

    def test_get_nao_permitido(self, client_pix, settings):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = client_pix.get(reverse('financeiro:webhook_pix'))
        assert resp.status_code == 405


# ---------------------------------------------------------------------------
# TestBaixaAutomaticaPIX
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBaixaAutomaticaPIX:
    def test_parcela_e_baixada_apos_webhook(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        _post(client_pix, _payload(txid=parcela_pix.pix_txid))
        parcela_pix.refresh_from_db()
        assert parcela_pix.pago is True

    def test_status_retornado_e_baixado(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = _post(client_pix, _payload(txid=parcela_pix.pix_txid))
        data = resp.json()
        assert data['processados'][0]['status'] == 'BAIXADO'

    def test_evento_pix_criado_no_banco(self, client_pix, settings, parcela_pix):
        from financeiro.models import EventoPIX
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        eid = 'E99999999202501011200000000001'
        _post(client_pix, _payload(end_to_end_id=eid, txid=parcela_pix.pix_txid))
        assert EventoPIX.objects.filter(end_to_end_id=eid, status='BAIXADO').exists()

    def test_valor_pago_reflete_webhook(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        _post(client_pix, _payload(txid=parcela_pix.pix_txid, valor='950.00'))
        parcela_pix.refresh_from_db()
        assert parcela_pix.valor_pago == Decimal('950.00')

    def test_observacao_menciona_end_to_end_id(self, client_pix, settings, parcela_pix):
        from financeiro.models import HistoricoPagamento
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        eid = 'E11111111202501011200000000001'
        _post(client_pix, _payload(end_to_end_id=eid, txid=parcela_pix.pix_txid))
        hp = HistoricoPagamento.objects.filter(parcela=parcela_pix).last()
        assert hp is not None
        assert eid in hp.observacoes


# ---------------------------------------------------------------------------
# TestDeduplicacaoPIX
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeduplicacaoPIX:
    def test_segundo_envio_mesmo_end_to_end_id_retorna_duplicado(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        eid = 'E22222222202501011200000000001'
        _post(client_pix, _payload(end_to_end_id=eid, txid=parcela_pix.pix_txid))
        # segundo envio
        resp2 = _post(client_pix, _payload(end_to_end_id=eid, txid=parcela_pix.pix_txid))
        data = resp2.json()
        assert data['processados'][0]['status'] == 'DUPLICADO'

    def test_deduplicacao_nao_paga_duas_vezes(self, client_pix, settings, parcela_pix):
        from financeiro.models import HistoricoPagamento
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        eid = 'E33333333202501011200000000001'
        _post(client_pix, _payload(end_to_end_id=eid, txid=parcela_pix.pix_txid))
        _post(client_pix, _payload(end_to_end_id=eid, txid=parcela_pix.pix_txid))
        count = HistoricoPagamento.objects.filter(parcela=parcela_pix).count()
        assert count == 1


# ---------------------------------------------------------------------------
# TestSemParcelaPIX
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSemParcelaPIX:
    def test_txid_nao_encontrado_retorna_sem_parcela(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = _post(client_pix, _payload(txid='TXID-INEXISTENTE'))
        data = resp.json()
        assert data['processados'][0]['status'] == 'SEM_PARCELA'

    def test_evento_criado_mesmo_sem_parcela(self, client_pix, settings, parcela_pix):
        from financeiro.models import EventoPIX
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        eid = 'E44444444202501011200000000001'
        _post(client_pix, _payload(end_to_end_id=eid, txid='TXID-INEXISTENTE'))
        assert EventoPIX.objects.filter(end_to_end_id=eid, status='SEM_PARCELA').exists()

    def test_txid_parcela_ja_paga_retorna_sem_parcela(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        # Pagar a parcela manualmente primeiro
        parcela_pix.pago = True
        parcela_pix.valor_pago = Decimal('1000.00')
        parcela_pix.data_pagamento = date(2025, 2, 1)
        parcela_pix.save(update_fields=['pago', 'valor_pago', 'data_pagamento'])

        eid = 'E55555555202501011200000000001'
        resp = _post(client_pix, _payload(
            end_to_end_id=eid,
            txid=parcela_pix.pix_txid,
        ))
        data = resp.json()
        assert data['processados'][0]['status'] == 'SEM_PARCELA'


# ---------------------------------------------------------------------------
# TestFormatoPayloadPIX
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFormatoPayloadPIX:
    def test_payload_invalido_retorna_400(self, client_pix, settings):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        resp = client_pix.post(
            reverse('financeiro:webhook_pix'),
            data='nao-e-json',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_evento_sem_end_to_end_id_e_ignorado(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        payload = {'pix': [{'txid': 'x', 'valor': '100.00'}]}
        resp = _post(client_pix, payload)
        assert resp.status_code == 200
        data = resp.json()
        assert 'erro' in data['processados'][0]

    def test_evento_unico_sem_wrapper_pix_e_aceito(self, client_pix, settings, parcela_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        payload = {
            'endToEndId': 'E66666666202501011200000000001',
            'txid': parcela_pix.pix_txid,
            'valor': '1000.00',
            'horario': '2025-02-01T12:00:00-03:00',
            'pagador': {'cpf': '12345678901', 'nome': 'Test'},
        }
        resp = _post(client_pix, payload)
        assert resp.status_code == 200
        parcela_pix.refresh_from_db()
        assert parcela_pix.pago is True

    def test_multiplos_eventos_processados_juntos(self, client_pix, settings, dominio_pix):
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        from contratos.models import Contrato, TipoAmortizacao, TipoCorrecao, StatusContrato
        imob, imovel, comprador = dominio_pix
        contrato = Contrato.objects.create(
            imobiliaria=imob, imovel=imovel, comprador=comprador,
            numero_contrato='CTR-PIX-MULTI',
            data_contrato=date(2025, 1, 1),
            data_primeiro_vencimento=date(2025, 2, 1),
            valor_total=Decimal('24000.00'), valor_entrada=Decimal('4000.00'),
            numero_parcelas=20, dia_vencimento=1,
            tipo_amortizacao=TipoAmortizacao.PRICE,
            tipo_correcao=TipoCorrecao.IPCA, prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO,
        )
        parcelas = list(contrato.parcelas.order_by('numero_parcela')[:2])
        parcelas[0].pix_txid = 'TXID-MULTI-P1'
        parcelas[1].pix_txid = 'TXID-MULTI-P2'
        for p in parcelas:
            p.save(update_fields=['pix_txid'])

        payload = {
            'pix': [
                {
                    'endToEndId': 'E77777777202501011200000000001',
                    'txid': 'TXID-MULTI-P1',
                    'valor': '1000.00',
                    'horario': '2025-02-01T12:00:00-03:00',
                    'pagador': {'cpf': '11111111111', 'nome': 'A'},
                },
                {
                    'endToEndId': 'E77777777202501011200000000002',
                    'txid': 'TXID-MULTI-P2',
                    'valor': '1000.00',
                    'horario': '2025-03-01T12:00:00-03:00',
                    'pagador': {'cpf': '22222222222', 'nome': 'B'},
                },
            ]
        }
        resp = _post(client_pix, payload)
        assert resp.status_code == 200
        data = resp.json()
        statuses = [p['status'] for p in data['processados']]
        assert all(s == 'BAIXADO' for s in statuses)


# ---------------------------------------------------------------------------
# Code-review fix: dedup atômico + comparação constant-time
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWebhookPixDedupAtomico:
    """O check existência + create devem estar no mesmo transaction.atomic.
    IntegrityError do constraint unique deve virar STATUS_DUPLICADO."""

    def test_evento_unique_constraint_existe(self):
        from financeiro.models import EventoPIX
        end_to_end_field = EventoPIX._meta.get_field('end_to_end_id')
        assert end_to_end_field.unique, 'end_to_end_id deve ser unique no DB'

    def test_dedup_via_integrity_error_retorna_duplicado(self, parcela_pix, client_pix, settings):
        """Simula race criando manualmente o EventoPIX antes do segundo POST."""
        from financeiro.models import EventoPIX
        settings.PIX_WEBHOOK_TOKEN = ''
        settings.DEBUG = True  # fail-closed só em produção (DEBUG=False)
        EventoPIX.objects.create(
            end_to_end_id='E_RACE_001',
            txid='TXID-TESTE-001',
            valor=Decimal('1000.00'),
            horario_pix='2025-02-01T12:00:00-03:00',
            status=EventoPIX.STATUS_RECEBIDO,
        )
        payload = {
            'pix': [{
                'endToEndId': 'E_RACE_001',
                'txid': 'TXID-TESTE-001',
                'valor': '1000.00',
                'horario': '2025-02-01T12:00:00-03:00',
            }]
        }
        resp = _post(client_pix, payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data['processados'][0]['status'] == EventoPIX.STATUS_DUPLICADO
        # Apenas 1 evento persistido (constraint absorveu o segundo)
        assert EventoPIX.objects.filter(end_to_end_id='E_RACE_001').count() == 1


@pytest.mark.django_db
class TestWebhookPixConstantTimeCompare:
    """Auth deve usar hmac.compare_digest (não vulnerável a timing-attack)."""

    @pytest.fixture(autouse=True)
    def _settings(self, settings):
        settings.PIX_WEBHOOK_TOKEN = 'token-secreto-longo-12345'

    def test_token_correto_passa(self, parcela_pix, client_pix):
        payload = {'pix': [{'endToEndId': 'E_AUTH_OK', 'txid': 'TXID-TESTE-001',
                            'valor': '1000.00', 'horario': '2025-02-01T12:00:00-03:00'}]}
        resp = client_pix.post(
            reverse('financeiro:webhook_pix'),
            data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION='Bearer token-secreto-longo-12345',
        )
        assert resp.status_code == 200

    def test_token_errado_rejeita_401(self, parcela_pix, client_pix):
        payload = {'pix': [{'endToEndId': 'E_AUTH_BAD', 'txid': 'TXID-TESTE-001',
                            'valor': '1000.00', 'horario': '2025-02-01T12:00:00-03:00'}]}
        resp = client_pix.post(
            reverse('financeiro:webhook_pix'),
            data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION='Bearer token-errado',
        )
        assert resp.status_code == 401
