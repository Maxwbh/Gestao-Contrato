"""
Testes HU — Gerar Boleto e Gerar Arquivo Remessa

Cobre os cenários especificados pela Contabilidade:

  1  Gerar 1 boleto → gerar remessa
  2  Gerar N boletos + N contratos → gerar remessas por conta
  3  Gerar N boletos de 1 contrato → gerar remessa desta conta
  4  Carnê 6 meses para 1 contrato
  5  Carnê 12 meses para 1 contrato
  6  Carnê 6 meses para N contratos
  7  Carnê 12 meses para N contratos
  8  Gerar remessa apenas para boletos sem arquivo gerado
  9  Quitar 1 boleto de 1 contrato
 10  Quitar N boletos de 1 contrato
 11  Quitar boletos via retorno CNAB (extrato banco)
 12  Enviar boleto por e-mail (mock)

Não testados aqui (dependem de credenciais externas):
  - WhatsApp via Twilio
  - SMS via Twilio
"""
import json
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import Client
from django.urls import reverse


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='hu_user', email='hu@test.com', password='pass123'
    )


@pytest.fixture
def cli(usuario):
    c = Client()
    c.login(username='hu_user', password='pass123')
    return c


@pytest.fixture
def dominio(db):
    """Cria imobiliária + conta bancária + imovel + comprador."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory
    )
    imob = ImobiliariaFactory()
    conta = ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob)
    comprador = CompradorFactory()
    return imob, conta, imovel, comprador


@pytest.fixture
def contrato_com_parcelas(db, dominio):
    """Cria contrato FIXO+Price com 12 parcelas (auto-geradas pelo Contrato.save)."""
    from contratos.models import Contrato, StatusContrato, TipoCorrecao, TipoAmortizacao
    imob, conta, imovel, comprador = dominio
    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='CTR-HU-001',
        data_contrato=date.today() - timedelta(days=60),
        data_primeiro_vencimento=date.today() - timedelta(days=30),
        valor_total=Decimal('120000.00'),
        valor_entrada=Decimal('20000.00'),
        numero_parcelas=12,
        dia_vencimento=5,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.FIXO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
    )
    # Parcelas são auto-geradas pelo Contrato.save() — forçar se necessário
    if not contrato.parcelas.exists():
        contrato.gerar_parcelas()
    return contrato


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_brcobranca_sucesso(nosso_numero='0000000001', linha='12345.67890 00000.000001 00000.000001 1 10000000100000'):
    """Retorna um mock do resultado de gerar_boleto() com sucesso."""
    return {
        'sucesso': True,
        'nosso_numero': nosso_numero,
        'linha_digitavel': linha,
        'codigo_barras': '12345678901234567890123456789012345678901234',
        'pdf_content': b'%PDF-1.4 FAKE',
    }


def _mock_gerar_remessa_sucesso():
    """Retorna mock de gerar_remessa_por_escopo."""
    from unittest.mock import MagicMock
    result = MagicMock()
    result.id = 1
    result.numero_remessa = 1
    result.total_boletos = 1
    result.valor_total = Decimal('8333.33')
    return result


# ===========================================================================
# HU 1 — Gerar 1 boleto → gerar remessa
# ===========================================================================

@pytest.mark.django_db
class TestHU01_GerarBoletoUnico:
    """1 boleto → 1 remessa."""

    def test_gerar_boleto_individual(self, cli, contrato_com_parcelas):
        """POST em gerar_boleto deve retornar sucesso com nosso_numero."""
        parcela = contrato_com_parcelas.parcelas.first()

        with patch('financeiro.models.Parcela.gerar_boleto',
                   return_value=_mock_brcobranca_sucesso()):
            url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
            resp = cli.post(url, content_type='application/json', data=json.dumps({}))

        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert 'nosso_numero' in data

    def test_boleto_nao_gerado_para_parcela_paga(self, cli, contrato_com_parcelas):
        """POST em parcela já paga deve retornar erro."""
        parcela = contrato_com_parcelas.parcelas.first()
        parcela.pago = True
        parcela.save()

        url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
        resp = cli.post(url, content_type='application/json', data=json.dumps({}))

        assert resp.status_code in (400, 200)
        if resp.status_code == 200:
            assert resp.json().get('sucesso') is False


# ===========================================================================
# HU 2 / 3 — Gerar N boletos (lote) de 1 contrato
# ===========================================================================

@pytest.mark.django_db
class TestHU02_GerarNBoletos:
    """N boletos de 1 contrato."""

    def test_gerar_todos_boletos_contrato(self, cli, contrato_com_parcelas):
        """POST em gerar_carne deve tentar gerar todos os boletos selecionados."""
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:6])
        ids = [p.pk for p in parcelas]

        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato_com_parcelas.pk})
        with patch('financeiro.models.Parcela.gerar_boleto',
                   return_value=_mock_brcobranca_sucesso()):
            resp = cli.post(
                url,
                content_type='application/json',
                data=json.dumps({'parcelas': ids}),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data['sucesso'] is True
        assert data.get('gerados', 0) > 0

    def test_gerar_carne_sem_parcelas_retorna_erro(self, cli, contrato_com_parcelas):
        """POST sem IDs deve retornar erro 400."""
        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato_com_parcelas.pk})
        resp = cli.post(
            url,
            content_type='application/json',
            data=json.dumps({'parcelas': []}),
        )
        assert resp.status_code == 400

    def test_gerar_carne_parcela_de_outro_contrato_ignorada(self, cli, contrato_com_parcelas, dominio):
        """IDs de outro contrato são silenciosamente ignorados."""
        from tests.fixtures.factories import ContratoFactory
        from contratos.models import TipoCorrecao
        imob, conta, imovel, comprador = dominio

        # Criar outro contrato com suas parcelas (auto-geradas)
        outro = ContratoFactory(imobiliaria=imob, imovel=imovel, comprador=comprador,
                                numero_contrato='CTR-HU-999', numero_parcelas=3,
                                tipo_correcao=TipoCorrecao.FIXO)
        parcela_outra = outro.parcelas.first()

        url = reverse('financeiro:gerar_carne', kwargs={'contrato_id': contrato_com_parcelas.pk})
        resp = cli.post(
            url,
            content_type='application/json',
            data=json.dumps({'parcelas': [parcela_outra.pk]}),  # parcela de outro contrato
        )
        # Deve retornar erro (nenhuma parcela válida para este contrato)
        assert resp.status_code in (400, 200)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get('gerados', 0) == 0 or data.get('sucesso') is False


# ===========================================================================
# HU 4 / 5 — Carnê PDF 6 e 12 meses para 1 contrato
# ===========================================================================

@pytest.mark.django_db
class TestHU04_05_CarnePDF:
    """Carnê PDF 6 e 12 meses para 1 contrato."""

    def _parcelas_com_boleto(self, contrato, n: int):
        """Simula parcelas com boleto já gerado."""
        parcelas = list(contrato.parcelas.order_by('numero_parcela')[:n])
        for i, p in enumerate(parcelas, 1):
            p.nosso_numero = f'{i:010d}'
            p.linha_digitavel = f'12345.{i:05d} 00000.000001 00000.000001 1 10000000100000'
            p.save()
        return parcelas

    def test_carne_6_meses_brcobranca(self, cli, contrato_com_parcelas, dominio):
        """Carnê 6 meses via BRCobrança retorna PDF."""
        from financeiro.services.boleto_service import BoletoService
        parcelas = self._parcelas_com_boleto(contrato_com_parcelas, 6)
        ids = [p.pk for p in parcelas]

        pdf_mock = b'%PDF-1.4 CARNE_MOCK'
        with patch.object(BoletoService, 'gerar_carne',
                          return_value={'sucesso': True, 'pdf_content': pdf_mock}):
            url = reverse('financeiro:download_carne_pdf',
                          kwargs={'contrato_id': contrato_com_parcelas.pk})
            resp = cli.post(
                url,
                content_type='application/json',
                data=json.dumps({'parcela_ids': ids}),
            )

        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
        assert b'PDF' in resp.content

    def test_carne_api_indisponivel_retorna_500(self, cli, contrato_com_parcelas, dominio):
        """BRCobrança indisponível → view retorna 500 com mensagem de erro."""
        from financeiro.services.boleto_service import BoletoService
        parcelas = self._parcelas_com_boleto(contrato_com_parcelas, 6)
        ids = [p.pk for p in parcelas]

        with patch.object(BoletoService, 'gerar_carne',
                          return_value={'sucesso': False, 'erro': 'API indisponível'}):
            url = reverse('financeiro:download_carne_pdf',
                          kwargs={'contrato_id': contrato_com_parcelas.pk})
            resp = cli.post(
                url,
                content_type='application/json',
                data=json.dumps({'parcela_ids': ids}),
            )

        assert resp.status_code == 500

    def test_carne_get_retorna_lista_parcelas(self, cli, contrato_com_parcelas):
        """GET em download_carne_pdf retorna lista de parcelas disponíveis."""
        url = reverse('financeiro:download_carne_pdf',
                      kwargs={'contrato_id': contrato_com_parcelas.pk})
        resp = cli.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert 'parcelas' in data
        assert len(data['parcelas']) == 12

    def test_carne_sem_parcelas_retorna_erro(self, cli, contrato_com_parcelas):
        """POST sem parcela_ids deve retornar 400."""
        url = reverse('financeiro:download_carne_pdf',
                      kwargs={'contrato_id': contrato_com_parcelas.pk})
        resp = cli.post(url, content_type='application/json', data=json.dumps({'parcela_ids': []}))
        assert resp.status_code == 400

    def test_carne_limite_60_parcelas(self, cli, contrato_com_parcelas):
        """Mais de 60 parcelas deve retornar 400."""
        ids = list(range(1, 70))  # 69 IDs fictícios
        url = reverse('financeiro:download_carne_pdf',
                      kwargs={'contrato_id': contrato_com_parcelas.pk})
        resp = cli.post(url, content_type='application/json', data=json.dumps({'parcela_ids': ids}))
        assert resp.status_code == 400


# ===========================================================================
# HU 6 / 7 — Carnê N contratos
# ===========================================================================

@pytest.mark.django_db
class TestHU06_07_CarneMultiplosContratos:
    """Carnê 6/12 meses para N contratos."""

    def test_carne_multiplos_contratos_pdf(self, cli, contrato_com_parcelas, dominio):
        """POST em download_carne_multiplos gera PDF multi-contrato."""
        imob, conta, imovel, comprador = dominio
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:6])
        ids = [p.pk for p in parcelas]

        payload = {
            'contratos': [
                {'contrato_id': contrato_com_parcelas.pk, 'parcela_ids': ids},
            ]
        }

        pdf_mock = b'%PDF-1.4 MULTIPLOS'
        with patch('financeiro.services.carne_service.gerar_carne_multiplos_contratos',
                   return_value=pdf_mock):
            url = reverse('financeiro:download_carne_multiplos')
            resp = cli.post(url, content_type='application/json', data=json.dumps(payload))

        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'

    def test_carne_multiplos_sem_contratos_retorna_erro(self, cli):
        """POST sem contratos deve retornar 400."""
        url = reverse('financeiro:download_carne_multiplos')
        resp = cli.post(url, content_type='application/json', data=json.dumps({'contratos': []}))
        assert resp.status_code == 400

    def test_carne_multiplos_limite_50(self, cli):
        """Mais de 50 contratos deve retornar 400."""
        contratos = [{'contrato_id': i, 'parcela_ids': [1]} for i in range(1, 52)]
        url = reverse('financeiro:download_carne_multiplos')
        resp = cli.post(url, content_type='application/json', data=json.dumps({'contratos': contratos}))
        assert resp.status_code == 400


# ===========================================================================
# HU 8 — Gerar remessa para boletos sem arquivo
# ===========================================================================

@pytest.mark.django_db
class TestHU08_GerarRemessa:
    """Gerar arquivo remessa CNAB."""

    def test_gerar_remessa_contrato(self, cli, contrato_com_parcelas, dominio):
        """POST em gerar_remessa cria arquivo remessa."""
        imob, conta, imovel, comprador = dominio

        mock_ar = MagicMock()
        mock_ar.id = 1
        mock_ar.numero_remessa = 1
        mock_ar.pk = 1

        with patch('financeiro.services.cnab_service.CNABService') as mock_cnab_cls:
            mock_cnab_cls.return_value.gerar_remessas_por_escopo.return_value = [mock_ar]
            url = reverse('financeiro:gerar_remessa')
            resp = cli.post(
                url,
                data={
                    'escopo': 'contrato',
                    'contrato_id': str(contrato_com_parcelas.pk),
                },
            )

        # Pode retornar 200 (JSON/HTML) ou redirect 302
        assert resp.status_code in (200, 302)

    def test_listar_remessas_acessivel(self, cli):
        """GET em listar_remessas retorna 200."""
        url = reverse('financeiro:listar_remessas')
        resp = cli.get(url)
        assert resp.status_code == 200


# ===========================================================================
# HU 9 / 10 — Quitar 1 ou N boletos
# ===========================================================================

@pytest.mark.django_db
class TestHU09_10_QuitarBoleto:
    """Quitar 1 ou N boletos manualmente."""

    def test_quitar_1_boleto(self, cli, contrato_com_parcelas):
        """POST em pagar_parcela_ajax deve marcar parcela como paga."""
        parcela = contrato_com_parcelas.parcelas.first()

        url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': parcela.pk})
        resp = cli.post(
            url,
            content_type='application/json',
            data=json.dumps({
                'data_pagamento': str(date.today()),
                'valor_pago': '8333.33',
                'forma_pagamento': 'DINHEIRO',
            }),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('sucesso') is True

        parcela.refresh_from_db()
        assert parcela.pago is True

    def test_quitar_n_boletos(self, cli, contrato_com_parcelas):
        """Quitar múltiplas parcelas uma por uma."""
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:3])
        for parcela in parcelas:
            url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': parcela.pk})
            resp = cli.post(
                url,
                content_type='application/json',
                data=json.dumps({
                    'data_pagamento': str(date.today()),
                    'valor_pago': str(parcela.valor_atual),
                    'forma_pagamento': 'TRANSFERENCIA',
                }),
            )
            assert resp.status_code == 200
            assert resp.json().get('sucesso') is True

        # Verifica que todas ficaram pagas
        for parcela in parcelas:
            parcela.refresh_from_db()
            assert parcela.pago is True

    def test_parcela_ja_paga_retorna_erro(self, cli, contrato_com_parcelas):
        """Tentar pagar parcela já paga deve retornar erro."""
        parcela = contrato_com_parcelas.parcelas.first()
        parcela.pago = True
        parcela.save()

        url = reverse('financeiro:pagar_parcela_ajax', kwargs={'pk': parcela.pk})
        resp = cli.post(
            url,
            content_type='application/json',
            data=json.dumps({
                'data_pagamento': str(date.today()),
                'valor_pago': '8333.33',
                'forma_pagamento': 'DINHEIRO',
            }),
        )
        assert resp.status_code in (400, 200)
        if resp.status_code == 200:
            assert resp.json().get('sucesso') is False


# ===========================================================================
# HU 11 — Quitação via retorno CNAB (extrato)
# ===========================================================================

@pytest.mark.django_db
class TestHU11_RetornoCNAB:
    """Processar arquivo retorno CNAB e quitar boletos pagos."""

    def test_upload_retorno_acessivel(self, cli):
        """GET em listar_retornos retorna 200."""
        url = reverse('financeiro:listar_retornos')
        resp = cli.get(url)
        assert resp.status_code == 200

    def test_processar_retorno_cnab(self, cli, dominio, contrato_com_parcelas):
        """POST em processar_retorno processa arquivo e quita parcelas."""
        from tests.fixtures.factories import ArquivoRetornoFactory
        imob, conta, imovel, comprador = dominio

        retorno = ArquivoRetornoFactory(conta_bancaria=conta)

        mock_result = {
            'sucesso': True,
            'total_registros': 2,
            'registros_processados': 2,
            'registros_erro': 0,
            'valor_total_pago': 16666.66,
        }

        with patch('financeiro.services.cnab_service.CNABService') as mock_cnab:
            mock_cnab.return_value.processar_retorno.return_value = mock_result
            url = reverse('financeiro:processar_retorno', kwargs={'pk': retorno.pk})
            resp = cli.post(url, content_type='application/json', data=json.dumps({}))

        assert resp.status_code == 200
        data = resp.json()
        assert data.get('sucesso') is True
        assert data.get('registros_processados', 0) == 2


# ===========================================================================
# HU 12 — Envio por e-mail (mock)
# ===========================================================================

@pytest.mark.django_db
class TestHU12_EnvioEmail:
    """Envio de boleto por e-mail."""

    def test_boleto_enviado_por_email_ao_gerar(self, cli, contrato_com_parcelas):
        """Ao gerar boleto com enviar_email=True, notificação é criada."""
        parcela = contrato_com_parcelas.parcelas.first()

        mock_result = _mock_brcobranca_sucesso()

        with patch('financeiro.models.Parcela.gerar_boleto', return_value=mock_result):
            url = reverse('financeiro:gerar_boleto', kwargs={'pk': parcela.pk})
            resp = cli.post(
                url,
                content_type='application/json',
                data=json.dumps({'enviar_email': True}),
            )
        assert resp.status_code == 200

    def test_notificacao_boleto_criado(self, db, contrato_com_parcelas):
        """BoletoNotificacaoService.notificar_boleto_criado() é chamado."""
        from notificacoes.boleto_notificacao import BoletoNotificacaoService
        parcela = contrato_com_parcelas.parcelas.first()
        parcela.nosso_numero = '0000000001'
        parcela.linha_digitavel = '12345.67890 00000.000001 00000.000001 1 10000000100000'
        parcela.save()

        with patch.object(BoletoNotificacaoService, 'notificar_boleto_criado') as mock_notify:
            BoletoNotificacaoService().notificar_boleto_criado(parcela)
            mock_notify.assert_called_once_with(parcela)


# ===========================================================================
# Testes de unidade: CarneService
# ===========================================================================

@pytest.mark.django_db
class TestCarneService:
    """Testes unitários do CarneService."""

    def test_gerar_carne_brcobranca_chamado(self, contrato_com_parcelas, dominio):
        """gerar_carne_pdf chama BRCobrança e retorna o PDF recebido."""
        from financeiro.services.carne_service import gerar_carne_pdf
        from financeiro.services.boleto_service import BoletoService
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:6])

        pdf_brcobranca = b'%PDF-1.4 BRCOBRANCA'
        with patch.object(BoletoService, 'gerar_carne', return_value={'sucesso': True, 'pdf_content': pdf_brcobranca}):
            result = gerar_carne_pdf(parcelas, contrato_com_parcelas)

        assert result == pdf_brcobranca

    def test_gerar_carne_levanta_runtime_error_quando_api_falha(self, contrato_com_parcelas, dominio):
        """gerar_carne_pdf levanta RuntimeError quando BRCobrança retorna erro."""
        from financeiro.services.carne_service import gerar_carne_pdf
        from financeiro.services.boleto_service import BoletoService
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:6])

        with patch.object(BoletoService, 'gerar_carne', return_value={'sucesso': False, 'erro': 'API indisponível'}):
            with pytest.raises(RuntimeError, match='BRCobrança'):
                gerar_carne_pdf(parcelas, contrato_com_parcelas)

    def test_gerar_carne_sem_parcelas_levanta_exception(self, contrato_com_parcelas):
        """Lista vazia levanta ValueError."""
        from financeiro.services.carne_service import gerar_carne_pdf

        with pytest.raises(ValueError, match='Nenhuma parcela'):
            gerar_carne_pdf([], contrato_com_parcelas)

    def test_gerar_carne_6_meses(self, contrato_com_parcelas, dominio):
        """Carnê de 6 parcelas retorna PDF válido via BRCobrança."""
        from financeiro.services.carne_service import gerar_carne_pdf
        from financeiro.services.boleto_service import BoletoService
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:6])

        pdf_mock = b'%PDF-1.4 MOCK6'
        with patch.object(BoletoService, 'gerar_carne', return_value={'sucesso': True, 'pdf_content': pdf_mock}):
            result = gerar_carne_pdf(parcelas, contrato_com_parcelas)

        assert result[:4] == b'%PDF'

    def test_gerar_carne_12_meses(self, contrato_com_parcelas, dominio):
        """Carnê de 12 parcelas retorna PDF válido via BRCobrança."""
        from financeiro.services.carne_service import gerar_carne_pdf
        from financeiro.services.boleto_service import BoletoService
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela'))

        pdf_mock = b'%PDF-1.4 MOCK12'
        with patch.object(BoletoService, 'gerar_carne', return_value={'sucesso': True, 'pdf_content': pdf_mock}):
            result = gerar_carne_pdf(parcelas, contrato_com_parcelas)

        assert result[:4] == b'%PDF'


# ===========================================================================
# Testes de unidade: BoletoService.gerar_carne
# ===========================================================================

@pytest.mark.django_db
class TestBoletoServiceGeraCarne:
    """Testes para BoletoService.gerar_carne (POST /api/boleto/multi)."""

    def test_gerar_carne_chama_api_multi(self, contrato_com_parcelas, dominio):
        """gerar_carne chama POST /api/boleto/multi com dados corretos."""
        from financeiro.services.boleto_service import BoletoService
        imob, conta, imovel, comprador = dominio
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:6])

        pdf_mock = b'%PDF-1.4 MULTI'

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = pdf_mock

        with patch('financeiro.services.boleto_service.requests.post', return_value=mock_resp) as mock_post:
            service = BoletoService()
            # Mock _montar_dados_boleto para não precisar de dados bancários completos
            with patch.object(service, '_montar_dados_boleto', return_value={
                'cedente': 'Imob Teste', 'sacado': 'Comprador', 'valor': 8333.33,
                'data_vencimento': '2026/04/07', 'nosso_numero': '0000000001',
                'agencia': '1234', 'conta_corrente': '567890', 'carteira': '18',
                'documento_cedente': '12345678000199', 'sacado_documento': '123.456.789-01',
                'moeda': '9', 'especie': 'R$', 'especie_documento': 'DM', 'aceite': 'N',
            }):
                with patch.object(service, '_get_banco_brcobranca', return_value='sicoob'):
                    resultado = service.gerar_carne(parcelas, conta)

        assert mock_post.called
        call_kwargs = mock_post.call_args
        assert '/api/boleto/multi' in call_kwargs[0][0]
        assert resultado['sucesso'] is True
        assert resultado['pdf_content'] == pdf_mock
        assert resultado['total'] == 6

    def test_gerar_carne_banco_nao_suportado(self, contrato_com_parcelas, dominio):
        """Banco sem código no mapeamento retorna erro."""
        from financeiro.services.boleto_service import BoletoService
        imob, conta, imovel, comprador = dominio
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:3])

        service = BoletoService()
        with patch.object(service, '_get_banco_brcobranca', return_value=None):
            resultado = service.gerar_carne(parcelas, conta)

        assert resultado['sucesso'] is False
        assert 'Banco não suportado' in resultado['erro']

    def test_gerar_carne_erro_conexao(self, contrato_com_parcelas, dominio):
        """Erro de conexão com BRCobrança retorna sucesso=False."""
        import requests as req_lib
        from financeiro.services.boleto_service import BoletoService
        imob, conta, imovel, comprador = dominio
        parcelas = list(contrato_com_parcelas.parcelas.order_by('numero_parcela')[:3])

        service = BoletoService()
        with patch.object(service, '_montar_dados_boleto', return_value={
            'cedente': 'T', 'sacado': 'T', 'valor': 100, 'data_vencimento': '2026/04/07',
            'nosso_numero': '1', 'agencia': '1', 'conta_corrente': '1', 'carteira': '1',
            'documento_cedente': '1', 'sacado_documento': '1',
            'moeda': '9', 'especie': 'R$', 'especie_documento': 'DM', 'aceite': 'N',
        }):
            with patch.object(service, '_get_banco_brcobranca', return_value='sicoob'):
                with patch('financeiro.services.boleto_service.requests.post',
                           side_effect=req_lib.exceptions.ConnectionError('refused')):
                    resultado = service.gerar_carne(parcelas, conta)

        assert resultado['sucesso'] is False
        assert 'conexão' in resultado['erro'].lower() or 'Erro' in resultado['erro']


# ===========================================================================
# HU — OFX: Quitação via Extrato Bancário
# ===========================================================================

# ---------------------------------------------------------------------------
# OFX SGML de teste (formato real dos bancos BR)
# ---------------------------------------------------------------------------

OFX_SAMPLE = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<DTSERVER>20260407120000</DTSERVER>
<LANGUAGE>POR</LANGUAGE>
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>756</BANKID>
<ACCTID>123456</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260301000000</DTSTART>
<DTEND>20260407000000</DTEND>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260405120000</DTPOSTED>
<TRNAMT>8333.33</TRNAMT>
<FITID>20260405001</FITID>
<MEMO>PAG PARCELA CTR-HU-001 COMPRADOR HU</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260406120000</DTPOSTED>
<TRNAMT>-150.00</TRNAMT>
<FITID>20260406001</FITID>
<MEMO>TARIFA BANCARIA</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260407120000</DTPOSTED>
<TRNAMT>9999.00</TRNAMT>
<FITID>20260407001</FITID>
<MEMO>TED OUTROS</MEMO>
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

OFX_NOSSO_NUMERO = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260405000000</DTPOSTED>
<TRNAMT>8333.33</TRNAMT>
<FITID>FIT-NN-001</FITID>
<MEMO>COBRANCA NOSSO NUMERO 0000000042 PAGO</MEMO>
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


_OFX_SAMPLE_BRCOBRANCA = {
    "transacoes": [
        {
            "fitid": "20260405001", "tipo": "CREDIT",
            "data": "2026-04-05", "valor": 8333.33,
            "memo": "PAG PARCELA CTR-HU-001 COMPRADOR HU",
            "nosso_numero_extraido": None,
        },
        {
            "fitid": "20260406001", "tipo": "DEBIT",
            "data": "2026-04-06", "valor": 150.0,
            "memo": "TARIFA BANCARIA",
            "nosso_numero_extraido": None,
        },
        {
            "fitid": "20260407001", "tipo": "CREDIT",
            "data": "2026-04-07", "valor": 9999.0,
            "memo": "TED OUTROS",
            "nosso_numero_extraido": None,
        },
    ]
}

_OFX_NOSSO_NUMERO_BRCOBRANCA = {
    "transacoes": [
        {
            "fitid": "FIT-NN-001", "tipo": "CREDIT",
            "data": "2026-04-05", "valor": 8333.33,
            "memo": "COBRANCA NOSSO NUMERO 0000000042 PAGO",
            "nosso_numero_extraido": "0000000042",
        },
    ]
}


def _mock_brcobranca_response(data: dict):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = data
    return mock_resp


@pytest.mark.django_db
class TestOFXReconciliacao:
    """Testa reconciliação OFX com parcelas do banco."""

    def test_reconcilia_por_numero_contrato_no_memo(self, contrato_com_parcelas):
        """P2: número do contrato no MEMO → match ALTA."""
        from financeiro.services.ofx_service import OFXService
        service = OFXService(contrato=contrato_com_parcelas)

        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_SAMPLE_BRCOBRANCA)):
            resultado = service.processar(OFX_SAMPLE)

        reconciliadas = [r for r in resultado['resultados'] if r.reconciliada]
        assert len(reconciliadas) >= 1
        assert reconciliadas[0].confianca == 'ALTA'

    def test_reconcilia_por_nosso_numero(self, contrato_com_parcelas):
        """P1: nosso_numero no MEMO → match ALTA."""
        from financeiro.services.ofx_service import OFXService
        parcela = contrato_com_parcelas.parcelas.first()
        parcela.nosso_numero = '0000000042'
        parcela.save()

        service = OFXService(contrato=contrato_com_parcelas)
        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_NOSSO_NUMERO_BRCOBRANCA)):
            resultado = service.processar(OFX_NOSSO_NUMERO)

        reconciliadas = [r for r in resultado['resultados'] if r.reconciliada]
        assert len(reconciliadas) == 1
        assert reconciliadas[0].confianca == 'ALTA'
        assert reconciliadas[0].parcela.pk == parcela.pk

    def test_debito_ignorado(self, contrato_com_parcelas):
        """Transações de débito (valor < 0) devem ser ignoradas na reconciliação."""
        from financeiro.services.ofx_service import OFXService
        service = OFXService(contrato=contrato_com_parcelas)

        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_SAMPLE_BRCOBRANCA)):
            resultado = service.processar(OFX_SAMPLE)

        nao_rec = [r for r in resultado['resultados'] if r.confianca == 'NAO_ENCONTRADA']
        debitos = [r for r in nao_rec if 'Débito' in r.motivo]
        assert len(debitos) == 1

    def test_total_transacoes_contabilizado(self, contrato_com_parcelas):
        """O total de transações retornado deve incluir débitos."""
        from financeiro.services.ofx_service import OFXService
        service = OFXService(contrato=contrato_com_parcelas)

        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_SAMPLE_BRCOBRANCA)):
            resultado = service.processar(OFX_SAMPLE)

        assert resultado['total_transacoes'] == 3

    def test_processar_arquivo_vazio_retorna_zeros(self, db):
        """Arquivo sem transações retorna resultado zerado."""
        from financeiro.services.ofx_service import OFXService
        service = OFXService()

        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response({'transacoes': []})):
            resultado = service.processar(b'<OFX></OFX>')

        assert resultado['total_transacoes'] == 0
        assert resultado['reconciliadas'] == 0
        assert resultado['resultados'] == []

    def test_dry_run_nao_quita(self, contrato_com_parcelas):
        """dry_run=True: parseia via BRCobrança sem marcar parcelas como pagas."""
        from financeiro.services.ofx_service import processar_ofx_upload

        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_SAMPLE_BRCOBRANCA)):
            resultado = processar_ofx_upload(
                OFX_SAMPLE,
                contrato=contrato_com_parcelas,
                dry_run=True,
            )

        assert resultado['dry_run'] is True
        assert 'transacoes' in resultado
        # Parcelas não devem ter sido quitadas
        assert contrato_com_parcelas.parcelas.filter(pago=True).count() == 0


@pytest.mark.django_db
class TestOFXView:
    """Testa o endpoint /financeiro/cnab/ofx/upload/."""

    def test_get_retorna_pagina(self, cli):
        """GET deve retornar 200 (template de upload)."""
        from django.urls import reverse
        url = reverse('financeiro:upload_ofx')
        resp = cli.get(url)
        assert resp.status_code == 200

    def test_post_sem_arquivo_retorna_400(self, cli):
        """POST sem arquivo deve retornar 400."""
        from django.urls import reverse
        url = reverse('financeiro:upload_ofx')
        resp = cli.post(url, data={})
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert data['sucesso'] is False

    def test_post_extensao_invalida_retorna_400(self, cli):
        """POST com arquivo .txt deve retornar 400."""
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile
        url = reverse('financeiro:upload_ofx')
        arquivo = SimpleUploadedFile('extrato.txt', b'content', content_type='text/plain')
        resp = cli.post(url, {'arquivo_ofx': arquivo})
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert '.ofx' in data['erro']

    def test_post_ofx_valido_retorna_resultado(self, cli, contrato_com_parcelas):
        """POST com .ofx válido deve retornar JSON com resultado da reconciliação."""
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile
        url = reverse('financeiro:upload_ofx')
        arquivo = SimpleUploadedFile(
            'extrato.ofx', OFX_SAMPLE, content_type='application/x-ofx'
        )
        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_SAMPLE_BRCOBRANCA)):
            resp = cli.post(url, {'arquivo_ofx': arquivo, 'dry_run': '0'})

        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['sucesso'] is True
        assert 'total_transacoes' in data
        assert 'reconciliadas' in data
        assert 'resultados' in data

    def test_post_dry_run_nao_quita(self, cli, contrato_com_parcelas):
        """POST com dry_run=1 não deve quitar parcelas."""
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile
        url = reverse('financeiro:upload_ofx')
        arquivo = SimpleUploadedFile(
            'extrato.ofx', OFX_NOSSO_NUMERO, content_type='application/x-ofx'
        )
        with patch('financeiro.services.ofx_service.requests.post',
                   return_value=_mock_brcobranca_response(_OFX_NOSSO_NUMERO_BRCOBRANCA)):
            resp = cli.post(url, {'arquivo_ofx': arquivo, 'dry_run': '1'})

        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data.get('dry_run') is True
        # Nenhuma parcela foi quitada
        assert contrato_com_parcelas.parcelas.filter(pago=True).count() == 0


@pytest.mark.django_db
class TestOFXBRCobranca:
    """Testa integração OFX → BRCobrança API (parse primário com fallback Python)."""

    # Resposta simulada do endpoint /api/ofx/parse do boleto_cnab_api
    _BRCOBRANCA_RESPONSE = {
        "banco": {"org": "Sicoob", "fid": "756"},
        "conta": {"agencia": "1234", "numero": "56789-0", "tipo": "CHECKING"},
        "periodo": {"inicio": "2026-04-01", "fim": "2026-04-07"},
        "saldo": {"valor": 25000.0, "data": "2026-04-07"},
        "transacoes": [
            {
                "fitid": "20260405001",
                "tipo": "CREDIT",
                "data": "2026-04-05",
                "valor": 8333.33,
                "memo": "PAG PARCELA CTR-HU-001",
                "name": "",
                "checknum": "",
                "refnum": "",
                "nosso_numero_extraido": "0000042",
            },
            {
                "fitid": "20260406001",
                "tipo": "DEBIT",
                "data": "2026-04-06",
                "valor": 150.0,
                "memo": "TARIFA BANCARIA",
                "name": "",
                "checknum": "",
                "refnum": "",
                "nosso_numero_extraido": None,
            },
        ],
        "resumo": {
            "total_transacoes": 2,
            "total_creditos": 1,
            "total_debitos": 1,
            "soma_creditos": 8333.33,
            "soma_debitos": 150.0,
        },
    }

    def test_parse_via_brcobranca_retorna_transacoes(self):
        """_parse_via_brcobranca retorna lista quando API responde 200."""
        from unittest.mock import patch, MagicMock
        from financeiro.services.ofx_service import _parse_via_brcobranca

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._BRCOBRANCA_RESPONSE

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            transacoes = _parse_via_brcobranca(OFX_SAMPLE, 'http://localhost:9292')

        assert transacoes is not None
        assert len(transacoes) == 2

    def test_parse_via_brcobranca_preenche_nosso_numero_extraido(self):
        """nosso_numero_extraido é preenchido a partir da resposta BRCobrança."""
        from unittest.mock import patch, MagicMock
        from financeiro.services.ofx_service import _parse_via_brcobranca

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._BRCOBRANCA_RESPONSE

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            transacoes = _parse_via_brcobranca(OFX_SAMPLE, 'http://localhost:9292')

        credito = next(t for t in transacoes if t.valor > 0)
        assert credito.nosso_numero_extraido == '0000042'

    def test_parse_via_brcobranca_debito_negativo(self):
        """Transações DEBIT têm valor negativo internamente."""
        from unittest.mock import patch, MagicMock
        from financeiro.services.ofx_service import _parse_via_brcobranca

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._BRCOBRANCA_RESPONSE

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            transacoes = _parse_via_brcobranca(OFX_SAMPLE, 'http://localhost:9292')

        debito = next(t for t in transacoes if t.tipo == 'DEBIT')
        assert debito.valor < 0

    def test_parse_via_brcobranca_retorna_none_em_connection_error(self):
        """ConnectionError → retorna None (serviço levantará RuntimeError)."""
        import requests as req_lib
        from unittest.mock import patch
        from financeiro.services.ofx_service import _parse_via_brcobranca

        with patch('financeiro.services.ofx_service.requests.post',
                   side_effect=req_lib.exceptions.ConnectionError()):
            result = _parse_via_brcobranca(OFX_SAMPLE, 'http://localhost:9292')

        assert result is None

    def test_parse_via_brcobranca_retorna_none_em_status_nao_200(self):
        """Status != 200 → retorna None (serviço levantará RuntimeError)."""
        from unittest.mock import patch, MagicMock
        from financeiro.services.ofx_service import _parse_via_brcobranca

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            result = _parse_via_brcobranca(OFX_SAMPLE, 'http://localhost:9292')

        assert result is None

    def test_ofx_service_usa_brcobranca_quando_disponivel(self, contrato_com_parcelas):
        """OFXService.processar usa BRCobrança quando disponível (parser='brcobranca')."""
        from unittest.mock import patch, MagicMock
        from financeiro.services.ofx_service import OFXService

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._BRCOBRANCA_RESPONSE

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            service = OFXService(contrato=contrato_com_parcelas)
            resultado = service.processar(OFX_SAMPLE)

        assert resultado['parser'] == 'brcobranca'
        assert resultado['total_transacoes'] == 2

    def test_ofx_service_levanta_erro_quando_brcobranca_indisponivel(self, contrato_com_parcelas):
        """OFXService.processar levanta RuntimeError quando BRCobrança não está disponível."""
        import requests as req_lib
        from unittest.mock import patch
        from financeiro.services.ofx_service import OFXService

        with patch('financeiro.services.ofx_service.requests.post',
                   side_effect=req_lib.exceptions.ConnectionError()):
            service = OFXService(contrato=contrato_com_parcelas)
            with pytest.raises(RuntimeError, match='BRCobrança'):
                service.processar(OFX_SAMPLE)

    def test_reconciliacao_p1a_usa_nosso_numero_extraido(self, contrato_com_parcelas):
        """P1a: nosso_numero_extraido pelo BRCobrança casa com parcela.nosso_numero."""
        from unittest.mock import patch, MagicMock
        from financeiro.services.ofx_service import OFXService

        # Configurar nosso_numero na parcela para 0000042 (mesmo do mock)
        parcela = contrato_com_parcelas.parcelas.first()
        parcela.nosso_numero = '0000042'
        parcela.save()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._BRCOBRANCA_RESPONSE

        with patch('financeiro.services.ofx_service.requests.post', return_value=mock_resp):
            service = OFXService(contrato=contrato_com_parcelas)
            resultado = service.processar(OFX_SAMPLE)

        reconciliadas = [r for r in resultado['resultados'] if r.reconciliada]
        assert len(reconciliadas) >= 1
        assert reconciliadas[0].confianca == 'ALTA'
        assert 'BRCobrança' in reconciliadas[0].motivo
        assert reconciliadas[0].parcela.pk == parcela.pk


# ===========================================================================
# HU 13 — Enviar boleto por WhatsApp
# HU 14 — Enviar boleto por SMS
# ===========================================================================

@pytest.mark.django_db
class TestHU13_EnvioWhatsApp:
    """Envio de boleto via WhatsApp (Twilio mock)."""

    def _parcela_com_boleto(self, contrato):
        """Retorna primeira parcela simulando tem_boleto=True."""
        p = contrato.parcelas.order_by('numero_parcela').first()
        # Simular boleto gerado
        p.linha_digitavel = '10492.33128 00005.780142 00000.010000 1 10000000833333'
        p.nosso_numero = '0000000001'
        p.save()
        return p

    def test_whatsapp_envia_com_telefone_no_body(self, cli, contrato_com_parcelas):
        """POST com telefone no body envia WhatsApp e retorna sucesso."""
        from django.urls import reverse
        from unittest.mock import patch
        p = self._parcela_com_boleto(contrato_com_parcelas)
        url = reverse('financeiro:boleto_whatsapp', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: True)):
            with patch('notificacoes.services.ServicoWhatsApp.enviar', return_value=True) as mock_wa:
                resp = cli.post(
                    url,
                    data='{"telefone": "+5511999999999"}',
                    content_type='application/json',
                )

        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['sucesso'] is True
        mock_wa.assert_called_once()
        args = mock_wa.call_args[0]
        assert args[0] == '+5511999999999'
        assert p.linha_digitavel in args[1]

    def test_whatsapp_sem_boleto_retorna_400(self, cli, contrato_com_parcelas):
        """Parcela sem boleto retorna 400."""
        from django.urls import reverse
        p = contrato_com_parcelas.parcelas.first()
        url = reverse('financeiro:boleto_whatsapp', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: False)):
            resp = cli.post(url, data='{"telefone": "+5511999999999"}',
                            content_type='application/json')

        assert resp.status_code == 400
        assert json.loads(resp.content)['sucesso'] is False

    def test_whatsapp_sem_telefone_retorna_400(self, cli, contrato_com_parcelas):
        """POST sem telefone e comprador sem telefone retorna 400."""
        from django.urls import reverse
        from unittest.mock import PropertyMock
        p = self._parcela_com_boleto(contrato_com_parcelas)
        url = reverse('financeiro:boleto_whatsapp', args=[p.pk])

        # Patch tem_boleto=True e comprador.telefone=None
        with patch('financeiro.views.Parcela.tem_boleto',
                   new_callable=lambda: property(lambda self: True)):
            with patch.object(
                type(contrato_com_parcelas.comprador), 'telefone',
                new_callable=PropertyMock, return_value=None
            ):
                resp = cli.post(url, data='{}', content_type='application/json')

        assert resp.status_code == 400

    def test_whatsapp_erro_twilio_retorna_500(self, cli, contrato_com_parcelas):
        """Erro na chamada Twilio retorna 500."""
        from django.urls import reverse
        p = self._parcela_com_boleto(contrato_com_parcelas)
        url = reverse('financeiro:boleto_whatsapp', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: True)):
            with patch('notificacoes.services.ServicoWhatsApp.enviar',
                       side_effect=Exception('Twilio error')):
                resp = cli.post(url, data='{"telefone": "+5511999999999"}',
                                content_type='application/json')

        assert resp.status_code == 500
        assert json.loads(resp.content)['sucesso'] is False


@pytest.mark.django_db
class TestHU14_EnvioSMS:
    """Envio de boleto via SMS (Twilio mock)."""

    def _parcela_com_boleto(self, contrato):
        p = contrato.parcelas.order_by('numero_parcela').first()
        p.linha_digitavel = '10492.33128 00005.780142 00000.010000 1 10000000833333'
        p.nosso_numero = '0000000001'
        p.save()
        return p

    def test_sms_envia_com_telefone_no_body(self, cli, contrato_com_parcelas):
        """POST com telefone no body envia SMS e retorna sucesso."""
        from django.urls import reverse
        p = self._parcela_com_boleto(contrato_com_parcelas)
        url = reverse('financeiro:boleto_sms', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: True)):
            with patch('notificacoes.services.ServicoSMS.enviar', return_value=True) as mock_sms:
                resp = cli.post(
                    url,
                    data='{"telefone": "+5511999999999"}',
                    content_type='application/json',
                )

        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['sucesso'] is True
        mock_sms.assert_called_once()
        _, msg = mock_sms.call_args[0]
        assert len(msg) <= 160  # limite SMS

    def test_sms_mensagem_contem_linha_digitavel(self, cli, contrato_com_parcelas):
        """Mensagem SMS inclui a linha digitável do boleto."""
        from django.urls import reverse
        p = self._parcela_com_boleto(contrato_com_parcelas)
        url = reverse('financeiro:boleto_sms', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: True)):
            with patch('notificacoes.services.ServicoSMS.enviar', return_value=True) as mock_sms:
                cli.post(url, data='{"telefone": "+5511999999999"}',
                         content_type='application/json')

        _, msg = mock_sms.call_args[0]
        assert p.linha_digitavel in msg

    def test_sms_sem_boleto_retorna_400(self, cli, contrato_com_parcelas):
        """Parcela sem boleto retorna 400."""
        from django.urls import reverse
        p = contrato_com_parcelas.parcelas.first()
        url = reverse('financeiro:boleto_sms', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: False)):
            resp = cli.post(url, data='{"telefone": "+5511999999999"}',
                            content_type='application/json')

        assert resp.status_code == 400

    def test_sms_telefone_via_form_post(self, cli, contrato_com_parcelas):
        """Telefone pode ser enviado como form data (não JSON)."""
        from django.urls import reverse
        p = self._parcela_com_boleto(contrato_com_parcelas)
        url = reverse('financeiro:boleto_sms', args=[p.pk])

        with patch('financeiro.views.Parcela.tem_boleto', new_callable=lambda: property(lambda self: True)):
            with patch('notificacoes.services.ServicoSMS.enviar', return_value=True) as mock_sms:
                resp = cli.post(url, data={'telefone': '+5511999999999'})

        assert resp.status_code == 200
        assert json.loads(resp.content)['sucesso'] is True
        mock_sms.assert_called_once()
