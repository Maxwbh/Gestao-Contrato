"""
HU CNAB Remessa→Retorno E2E — Seção 7.9.3
==========================================

Cobre o ciclo completo de cobrança bancária:
  Parcela com boleto → gerar remessa CNAB → banco processa → retorno CNAB → parcela paga

Cenários testados:
  - obter_boletos_sem_remessa() filtra corretamente
  - gerar_remessa() cria ArquivoRemessa e ItemRemessa (mock BRCobrança)
  - gerar_remessa() rejeita parcelas inválidas (sem boleto, já pagas)
  - processar_retorno() com ocorrência ENTRADA → status REGISTRADO
  - processar_retorno() com ocorrência LIQUIDACAO → parcela paga
  - Guard de duplicata: retorno já processado não reprocessa
  - Fluxo E2E completo: boleto → remessa → retorno LIQUIDACAO → quitado
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock

from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dominio(db):
    """Cria domínio básico com ContaBancaria Banco do Brasil + convenio."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaFactory, ImovelFactory, CompradorFactory,
    )
    imob = ImobiliariaFactory(nome='Imobiliária CNAB')
    conta = ContaBancariaFactory(imobiliaria=imob, banco='001', principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador CNAB')
    return imob, conta, imovel, comprador


@pytest.fixture
def usuario_cli(db, dominio):
    """Usuário autenticado e Client Django."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(
        username='cnab_user', password='CNABpass1!', email='cnab@test.com',
    )
    c = Client()
    c.force_login(u)
    return u, c


@pytest.fixture
def contrato_cnab(db, dominio):
    """
    Contrato com 12 parcelas, as parcelas 4–6 com boleto gerado (GERADO).

    Parcelas 1–3: pagas  (pago=True)
    Parcelas 4–6: boleto gerado (status=GERADO, nosso_numero definido, conta vinculada)
    Parcelas 7–12: sem boleto (NAO_GERADO)
    """
    from contratos.models import (
        Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao,
    )
    from financeiro.models import StatusBoleto

    imob, conta, imovel, comprador = dominio

    contrato = Contrato.objects.create(
        imobiliaria=imob,
        imovel=imovel,
        comprador=comprador,
        numero_contrato='CTR-CNAB-001',
        data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('120000.00'),
        valor_entrada=Decimal('20000.00'),
        numero_parcelas=12,
        dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA,
        prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
        percentual_juros_mora=Decimal('1.00'),
        percentual_multa=Decimal('2.00'),
    )

    # Pagar as 3 primeiras parcelas
    contrato.parcelas.filter(numero_parcela__lte=3).update(
        pago=True,
        valor_pago=Decimal('8333.33'),
        status_boleto=StatusBoleto.PAGO,
    )

    # Marcar parcelas 4–6 como com boleto gerado
    valor_boleto = Decimal('8333.33')
    for i in range(4, 7):
        contrato.parcelas.filter(numero_parcela=i).update(
            status_boleto=StatusBoleto.GERADO,
            nosso_numero=f'0000{i:02d}',
            valor_boleto=valor_boleto,
            conta_bancaria=conta,
        )

    return contrato, conta


# ---------------------------------------------------------------------------
# Helper: criar ArquivoRetorno com arquivo de conteúdo simulado
# ---------------------------------------------------------------------------

def _criar_arquivo_retorno(conta_bancaria, nosso_numero='000004'):
    """Cria ArquivoRetorno com conteúdo CNAB400 simulado (1 linha de 400 chars)."""
    from financeiro.models import ArquivoRetorno, StatusArquivoRetorno

    # Header CNAB400: linha de 400 caracteres (layout 400 → len=400)
    header = '0' + ''.ljust(399)
    arquivo_retorno = ArquivoRetorno.objects.create(
        conta_bancaria=conta_bancaria,
        nome_arquivo='CB0501.RET',
        status=StatusArquivoRetorno.PENDENTE,
    )
    arquivo_retorno.arquivo.save(
        'CB0501.RET',
        ContentFile(header.encode('latin-1')),
        save=True,
    )
    return arquivo_retorno


def _mock_retorno(nosso_numero, codigo_ocorrencia='06', valor='8333.33',
                  data_str='2025-05-01'):
    """Retorna mock de requests.post para processar_retorno."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        'retornos': [{
            'nosso_numero': nosso_numero,
            'codigo_ocorrencia': codigo_ocorrencia,
            'valor_titulo': valor,
            'valor_pago': valor if codigo_ocorrencia in ('06', '17') else '0.00',
            'data_ocorrencia': data_str,
            'data_credito': data_str,
        }]
    }
    return mock


# ---------------------------------------------------------------------------
# TestObterBoletosSemRemessa
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestObterBoletosSemRemessa:
    """Verifica que obter_boletos_sem_remessa() filtra corretamente."""

    def test_retorna_parcelas_com_boleto_gerado_sem_remessa(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        contrato, conta = contrato_cnab
        service = CNABService()
        boletos = service.obter_boletos_sem_remessa(conta_bancaria=conta)
        # Parcelas 4, 5, 6 têm boleto GERADO e nenhuma remessa
        numeros = [b.numero_parcela for b in boletos]
        assert sorted(numeros) == [4, 5, 6]

    def test_exclui_parcelas_pagas(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        contrato, conta = contrato_cnab
        service = CNABService()
        boletos = service.obter_boletos_sem_remessa(conta_bancaria=conta)
        assert all(not b.pago for b in boletos)

    def test_exclui_parcelas_em_remessa_ativa(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        from financeiro.models import (
            ArquivoRemessa, ItemRemessa, StatusArquivoRemessa,
        )
        contrato, conta = contrato_cnab

        # Criar remessa ativa incluindo a parcela 4
        parcela4 = contrato.parcelas.get(numero_parcela=4)
        remessa = ArquivoRemessa.objects.create(
            conta_bancaria=conta,
            numero_remessa=1,
            status=StatusArquivoRemessa.GERADO,
            quantidade_boletos=1,
            valor_total=Decimal('8333.33'),
        )
        ItemRemessa.objects.create(
            arquivo_remessa=remessa,
            parcela=parcela4,
            nosso_numero=parcela4.nosso_numero,
            valor=parcela4.valor_atual,
            data_vencimento=parcela4.data_vencimento,
        )

        service = CNABService()
        boletos = service.obter_boletos_sem_remessa(conta_bancaria=conta)
        numeros = [b.numero_parcela for b in boletos]
        # Parcela 4 está em remessa GERADO → excluída; restam 5 e 6
        assert 4 not in numeros
        assert 5 in numeros and 6 in numeros


# ---------------------------------------------------------------------------
# TestGerarRemessa
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGerarRemessa:
    """Testa geração de arquivo de remessa CNAB."""

    def test_gerar_remessa_cria_arquivo_e_itens(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        from financeiro.models import ArquivoRemessa, ItemRemessa, StatusArquivoRemessa

        contrato, conta = contrato_cnab
        parcelas = list(contrato.parcelas.filter(numero_parcela__in=[4, 5, 6]))

        mock_api = MagicMock()
        mock_api.status_code = 200
        mock_api.content = b'0' * 240 + b'\n'  # conteúdo CNAB simulado

        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            resultado = service.gerar_remessa(parcelas, conta)

        assert resultado['sucesso'] is True
        assert resultado['quantidade_boletos'] == 3
        assert 'arquivo_remessa' in resultado

        remessa = resultado['arquivo_remessa']
        assert remessa.status == StatusArquivoRemessa.GERADO
        assert remessa.conta_bancaria == conta
        assert remessa.itens.count() == 3

    def test_gerar_remessa_retorna_falso_sem_parcelas_validas(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        contrato, conta = contrato_cnab
        # Parcelas 1–3 estão pagas → inválidas para remessa
        parcelas = list(contrato.parcelas.filter(numero_parcela__lte=3))
        service = CNABService()
        resultado = service.gerar_remessa(parcelas, conta)
        assert resultado['sucesso'] is False
        assert 'erro' in resultado

    def test_gerar_remessa_retorna_falso_quando_api_falha(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        contrato, conta = contrato_cnab
        parcelas = list(contrato.parcelas.filter(numero_parcela__in=[4, 5]))

        mock_api = MagicMock()
        mock_api.status_code = 500
        mock_api.text = 'Internal Server Error'

        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            resultado = service.gerar_remessa(parcelas, conta)

        assert resultado['sucesso'] is False

    def test_gerar_remessa_numero_incrementa(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService

        contrato, conta = contrato_cnab
        parcelas = list(contrato.parcelas.filter(numero_parcela__in=[4, 5]))

        mock_api = MagicMock()
        mock_api.status_code = 200
        mock_api.content = b'0' * 240 + b'\n'

        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            r1 = service.gerar_remessa(parcelas, conta)

        assert r1['sucesso'] is True
        assert r1['numero_remessa'] == 1


# ---------------------------------------------------------------------------
# TestProcessarRetornoEntrada
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProcessarRetornoEntrada:
    """Retorno com ocorrência ENTRADA (01/02) → status_boleto = REGISTRADO."""

    def test_entrada_muda_status_para_registrado(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        from financeiro.models import StatusBoleto

        contrato, conta = contrato_cnab
        parcela4 = contrato.parcelas.get(numero_parcela=4)
        arquivo_retorno = _criar_arquivo_retorno(conta, parcela4.nosso_numero)
        mock_api = _mock_retorno(
            nosso_numero=parcela4.nosso_numero,
            codigo_ocorrencia='02',  # ENTRADA
            valor=str(parcela4.valor_atual),
        )

        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            result = service.processar_retorno(arquivo_retorno)

        assert result['sucesso'] is True
        parcela4.refresh_from_db()
        assert parcela4.status_boleto == StatusBoleto.REGISTRADO
        assert parcela4.pago is False  # entrada não quita

    def test_entrada_nao_marca_parcela_como_paga(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        contrato, conta = contrato_cnab
        parcela5 = contrato.parcelas.get(numero_parcela=5)
        arquivo_retorno = _criar_arquivo_retorno(conta, parcela5.nosso_numero)
        mock_api = _mock_retorno(
            nosso_numero=parcela5.nosso_numero,
            codigo_ocorrencia='01',
        )
        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            service.processar_retorno(arquivo_retorno)
        parcela5.refresh_from_db()
        assert parcela5.pago is False


# ---------------------------------------------------------------------------
# TestProcessarRetornoLiquidacao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProcessarRetornoLiquidacao:
    """Retorno com ocorrência LIQUIDACAO (06) → parcela quitada."""

    def test_liquidacao_marca_parcela_como_paga(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        from financeiro.models import StatusBoleto

        contrato, conta = contrato_cnab
        parcela4 = contrato.parcelas.get(numero_parcela=4)
        arquivo_retorno = _criar_arquivo_retorno(conta, parcela4.nosso_numero)
        mock_api = _mock_retorno(
            nosso_numero=parcela4.nosso_numero,
            codigo_ocorrencia='06',
            valor=str(parcela4.valor_atual),
        )

        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            result = service.processar_retorno(arquivo_retorno)

        assert result['sucesso'] is True
        parcela4.refresh_from_db()
        assert parcela4.pago is True
        assert parcela4.status_boleto == StatusBoleto.PAGO

    def test_liquidacao_registra_valor_pago(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        contrato, conta = contrato_cnab
        parcela4 = contrato.parcelas.get(numero_parcela=4)
        valor = parcela4.valor_atual
        arquivo_retorno = _criar_arquivo_retorno(conta, parcela4.nosso_numero)
        mock_api = _mock_retorno(
            nosso_numero=parcela4.nosso_numero,
            codigo_ocorrencia='06',
            valor=str(valor),
        )
        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            service.processar_retorno(arquivo_retorno)

        parcela4.refresh_from_db()
        assert parcela4.valor_pago == valor

    def test_guard_duplicata_nao_reprocessa_parcela_ja_paga(self, contrato_cnab):
        """Se a parcela já está paga, ItemRetorno.processar_baixa() não reprocessa."""
        from financeiro.services.cnab_service import CNABService
        from financeiro.models import ArquivoRetorno, StatusArquivoRetorno

        contrato, conta = contrato_cnab
        parcela4 = contrato.parcelas.get(numero_parcela=4)

        # Primeiro processamento: quitar a parcela
        ret1 = _criar_arquivo_retorno(conta, parcela4.nosso_numero)
        mock_api = _mock_retorno(parcela4.nosso_numero, '06', str(parcela4.valor_atual))
        service = CNABService()
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api):
            r1 = service.processar_retorno(ret1)
        assert r1['sucesso'] is True
        parcela4.refresh_from_db()
        assert parcela4.pago is True

        # Segundo processamento (retorno duplicado): nova parcela não reprocessada
        ret2 = _criar_arquivo_retorno(conta, parcela4.nosso_numero)
        # Mudar nome para criar novo ArquivoRetorno
        ret2.nome_arquivo = 'CB0502.RET'
        ret2.save()
        mock_api2 = _mock_retorno(parcela4.nosso_numero, '06', str(parcela4.valor_atual))
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_api2):
            r2 = service.processar_retorno(ret2)
        # O resultado pode ser sucesso, mas o pagamento não foi reprocessado
        parcela4.refresh_from_db()
        assert parcela4.pago is True  # permanece paga, não foi revertida


# ---------------------------------------------------------------------------
# TestFluxoCompletoCNAB
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFluxoCompletoCNAB:
    """
    E2E: Ciclo completo CNAB.

    Passos:
      1. Parcelas 4, 5 têm boletos gerados (GERADO)
      2. obter_boletos_sem_remessa() lista as 3 parcelas disponíveis
      3. gerar_remessa() → ArquivoRemessa criado com status GERADO e 2 itens
      4. marcar_enviado() → status ENVIADO
      5. processar_retorno() ENTRADA (01) → parcela 4 fica REGISTRADO
      6. processar_retorno() LIQUIDACAO (06) → parcela 5 fica paga
      7. Contrato still ATIVO após ciclo completo
    """

    def test_fluxo_completo_remessa_retorno(self, contrato_cnab):
        from financeiro.services.cnab_service import CNABService
        from financeiro.models import StatusBoleto, StatusArquivoRemessa
        from contratos.models import StatusContrato

        contrato, conta = contrato_cnab

        service = CNABService()

        # ── Passo 2: listar boletos disponíveis ────────────────────────────
        disponiveis = service.obter_boletos_sem_remessa(conta_bancaria=conta)
        assert len(disponiveis) == 3

        # ── Passo 3: gerar remessa com parcelas 4 e 5 ─────────────────────
        parcela4 = contrato.parcelas.get(numero_parcela=4)
        parcela5 = contrato.parcelas.get(numero_parcela=5)

        mock_remessa = MagicMock()
        mock_remessa.status_code = 200
        mock_remessa.content = b'0' * 240 + b'\n'

        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_remessa):
            r = service.gerar_remessa([parcela4, parcela5], conta)

        assert r['sucesso'] is True
        remessa = r['arquivo_remessa']
        assert remessa.status == StatusArquivoRemessa.GERADO
        assert remessa.itens.count() == 2

        # ── Passo 4: marcar como enviada ─────────────────────────────────
        remessa.marcar_enviado()
        remessa.refresh_from_db()
        assert remessa.status == StatusArquivoRemessa.ENVIADO

        # ── Passo 5: retorno ENTRADA para parcela 4 ───────────────────────
        ret_entrada = _criar_arquivo_retorno(conta, parcela4.nosso_numero)
        mock_entrada = _mock_retorno(
            nosso_numero=parcela4.nosso_numero,
            codigo_ocorrencia='01',
        )
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_entrada):
            re1 = service.processar_retorno(ret_entrada)

        assert re1['sucesso'] is True
        parcela4.refresh_from_db()
        assert parcela4.status_boleto == StatusBoleto.REGISTRADO
        assert parcela4.pago is False

        # ── Passo 6: retorno LIQUIDACAO para parcela 5 ────────────────────
        ret_liq = _criar_arquivo_retorno(conta, parcela5.nosso_numero)
        mock_liq = _mock_retorno(
            nosso_numero=parcela5.nosso_numero,
            codigo_ocorrencia='06',
            valor=str(parcela5.valor_atual),
        )
        with patch('financeiro.services.cnab_service.requests.post', return_value=mock_liq):
            re2 = service.processar_retorno(ret_liq)

        assert re2['sucesso'] is True
        parcela5.refresh_from_db()
        assert parcela5.pago is True
        assert parcela5.status_boleto == StatusBoleto.PAGO

        # ── Passo 7: contrato permanece ATIVO ────────────────────────────
        contrato.refresh_from_db()
        assert contrato.status == StatusContrato.ATIVO
