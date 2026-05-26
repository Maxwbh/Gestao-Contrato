"""
HU — Importação de Contratos via IA

Testa:
  - Parser JSON da resposta da IA (incluindo markdown code blocks)
  - ProcessadorImportacao: match de entidades existentes
  - Estratégia híbrida: Haiku → Opus (escala apenas quando confiança < ALTO)
  - View de upload: validações de tipo e tamanho
  - View de revisão: renderiza dados extraídos e matches
  - confirmar_importacao: criação atômica de todas as entidades
  - Idempotência: importação já CONCLUIDA redireciona sem criar duplicatas
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from decimal import Decimal

from django.test import Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_logado(db):
    from tests.fixtures.factories import UserFactory, ImobiliariaFactory, ContabilidadeFactory
    from core.models import AcessoUsuario
    contabilidade = ContabilidadeFactory()
    imobiliaria = ImobiliariaFactory(contabilidade=contabilidade)
    user = UserFactory()
    AcessoUsuario.objects.create(
        usuario=user,
        contabilidade=contabilidade,
        imobiliaria=imobiliaria,
        ativo=True,
    )
    client = Client()
    client.force_login(user)
    return user, client, imobiliaria, contabilidade


@pytest.fixture
def dados_extraidos_exemplo():
    return {
        'numero_contrato': 'CTR-2024-001',
        'data_contrato': '2024-03-10',
        'data_primeiro_vencimento': '2024-04-10',
        'valor_total': 150000.00,
        'valor_entrada': 15000.00,
        'numero_parcelas': 120,
        'dia_vencimento': 10,
        'tipo_correcao': 'IPCA',
        'prazo_reajuste_meses': 12,
        'percentual_juros_mora': 1.00,
        'percentual_multa': 2.00,
        'imobiliaria': {
            'nome': 'Imobiliária Teste LTDA',
            'razao_social': 'Imobiliária Teste LTDA',
            'cnpj': '23.456.781/0001-11',
            'tipo_pessoa': 'PJ',
        },
        'comprador': {
            'nome': 'João da Silva',
            'tipo_pessoa': 'PF',
            'cpf': '123.456.789-09',
            'email': 'joao@example.com',
            'telefone': '(31) 3333-4444',
            'logradouro': 'Rua das Flores',
            'numero': '123',
            'cidade': 'Belo Horizonte',
            'estado': 'MG',
            'cep': '30100-000',
        },
        'imovel': {
            'tipo': 'LOTE',
            'identificacao': 'Quadra A Lote 5',
            'loteamento': 'Parque das Árvores',
            'cidade': 'Contagem',
            'estado': 'MG',
            'area': 300.0,
            'matricula': '12345',
        },
        'prestacoes_intermediarias': [],
        'observacoes': None,
        'confianca': {'nivel': 'ALTO', 'campos_incertos': []},
    }


# ─── Testes de parser JSON ────────────────────────────────────────────────────

class TestParseJson:
    def test_json_puro(self):
        from contratos.services.importacao_ia import _parse_json
        assert _parse_json('{"chave": "valor"}') == {'chave': 'valor'}

    def test_json_em_markdown(self):
        from contratos.services.importacao_ia import _parse_json
        assert _parse_json('```json\n{"chave": "valor"}\n```') == {'chave': 'valor'}

    def test_json_em_markdown_sem_tipo(self):
        from contratos.services.importacao_ia import _parse_json
        assert _parse_json('```\n{"chave": "valor"}\n```') == {'chave': 'valor'}

    def test_json_invalido_lanca_valueerror(self):
        from contratos.services.importacao_ia import _parse_json
        with pytest.raises(ValueError, match='não é JSON válido'):
            _parse_json('isso não é json')


# ─── Helpers de conversão ─────────────────────────────────────────────────────

class TestHelpers:
    def test_dec_valor_normal(self):
        from contratos.services.importacao_ia import _dec
        assert _dec('150000.00') == Decimal('150000.00')

    def test_dec_valor_com_virgula(self):
        from contratos.services.importacao_ia import _dec
        assert _dec('150000,00') == Decimal('150000.00')

    def test_dec_none(self):
        from contratos.services.importacao_ia import _dec
        assert _dec(None) is None

    def test_dec_vazio(self):
        from contratos.services.importacao_ia import _dec
        assert _dec('') is None

    def test_date_iso(self):
        from contratos.services.importacao_ia import _date
        from datetime import date
        assert _date('2024-03-10') == date(2024, 3, 10)

    def test_date_none(self):
        from contratos.services.importacao_ia import _date
        assert _date(None) is None

    def test_date_invalido(self):
        from contratos.services.importacao_ia import _date
        assert _date('nao-e-data') is None


# ─── Estratégia híbrida Haiku → Sonnet → Opus ────────────────────────────────

class TestEstrategiaHibrida:
    """
    Verifica o roteamento de modelos em 3 camadas:
      Haiku (barato) → Sonnet (intermediário) → Opus (último recurso)
    Cada camada só é acionada se a anterior retornar confiança < ALTO.
    """

    def _api_resp(self, data: dict):
        resp = MagicMock()
        resp.content = [MagicMock(text=json.dumps(data))]
        return resp

    def _ia_com_mock_client(self):
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        ia._client = MagicMock()
        return ia

    # ── Tier 0: Gemini ───────────────────────────────────────────────────────

    def _mock_gemini(self, dados: dict):
        """
        Retorna (mock_genai, mock_model, sys_modules_patch) prontos para uso em
        patch.dict(sys.modules, ...). Garante que google.generativeai e
        google.generativeai (acessado via google.generativeai) apontem para o
        mesmo objeto.
        """
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text=json.dumps(dados))
        mock_genai = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        # google namespace package deve expor .generativeai = mock_genai
        mock_google = MagicMock()
        mock_google.generativeai = mock_genai
        sys_patch = {'google': mock_google, 'google.generativeai': mock_genai}
        return mock_genai, mock_model, sys_patch

    def test_gemini_alto_retorna_sem_chamar_claude(self):
        """Gemini ALTO → retorna imediatamente; nenhum modelo Claude é chamado."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        dados = {'numero_contrato': 'X', 'confianca': {'nivel': 'ALTO', 'campos_incertos': []}}
        mock_genai, mock_model, sys_patch = self._mock_gemini(dados)

        with patch.dict('sys.modules', sys_patch):
            with override_settings(GEMINI_API_KEY='fake-key'):
                resultado = ia._tentar_gemini([{'mime_type': 'application/pdf', 'data': b'%PDF'}])

        assert resultado == dados
        mock_model.generate_content.assert_called_once()

    def test_gemini_medio_retorna_none_e_escala_para_claude(self):
        """Gemini MEDIO → _tentar_gemini retorna None → cadeia Claude é acionada."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        mock_genai, _, sys_patch = self._mock_gemini({'confianca': {'nivel': 'MEDIO', 'campos_incertos': ['valor_total']}})

        with patch.dict('sys.modules', sys_patch):
            with override_settings(GEMINI_API_KEY='fake-key'):
                resultado = ia._tentar_gemini([{'mime_type': 'application/pdf', 'data': b'%PDF'}])

        assert resultado is None

    def test_gemini_erro_retorna_none(self):
        """Quota esgotada ou qualquer exceção → retorna None sem lançar."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception('quota exceeded')
        mock_genai = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_google = MagicMock()
        mock_google.generativeai = mock_genai

        with patch.dict('sys.modules', {'google': mock_google, 'google.generativeai': mock_genai}):
            with override_settings(GEMINI_API_KEY='fake-key'):
                resultado = ia._tentar_gemini([{'mime_type': 'application/pdf', 'data': b'%PDF'}])

        assert resultado is None

    def test_gemini_sem_api_key_retorna_none(self):
        """Sem GEMINI_API_KEY configurada → pula Tier 0 silenciosamente."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()

        with override_settings(GEMINI_API_KEY=''):
            resultado = ia._tentar_gemini([{'mime_type': 'application/pdf', 'data': b'%PDF'}])

        assert resultado is None

    def test_gemini_sem_pacote_retorna_none(self):
        """google-generativeai não instalado → pula Tier 0 sem erro."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        mock_google = MagicMock()
        mock_google.generativeai = None

        with patch.dict('sys.modules', {'google': mock_google, 'google.generativeai': None}):
            with override_settings(GEMINI_API_KEY='fake-key'):
                resultado = ia._tentar_gemini([{'mime_type': 'application/pdf', 'data': b'%PDF'}])

        assert resultado is None

    def test_extrair_de_pdf_usa_gemini_quando_alto(self):
        """extrair_de_pdf retorna resultado Gemini sem acionar nenhum modelo Claude."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        ia._client = MagicMock()  # garante que Claude não seja chamado
        dados_gemini = {'numero_contrato': 'GEM-01', 'confianca': {'nivel': 'ALTO', 'campos_incertos': []}}

        with patch.object(ia, '_tentar_gemini', return_value=dados_gemini):
            resultado = ia.extrair_de_pdf(b'%PDF-fake')

        assert resultado == dados_gemini
        ia._client.messages.create.assert_not_called()

    def test_extrair_de_pdf_cai_para_claude_quando_gemini_none(self):
        """Quando _tentar_gemini retorna None, a cadeia Claude é acionada normalmente."""
        from contratos.services.importacao_ia import ImportacaoIA
        ia = ImportacaoIA()
        dados_haiku = {'numero_contrato': 'HAI-01', 'confianca': {'nivel': 'ALTO', 'campos_incertos': []}}
        ia._client = MagicMock()
        ia._client.messages.create.return_value = self._api_resp(dados_haiku)

        with patch.object(ia, '_tentar_gemini', return_value=None):
            resultado = ia.extrair_de_pdf(b'%PDF-fake')

        assert resultado == dados_haiku
        assert ia._client.messages.create.call_count == 1

    # ── Tier 1: Haiku ────────────────────────────────────────────────────────

    def test_haiku_alto_retorna_sem_escalar(self):
        """Contrato legível → Haiku basta, Sonnet e Opus não são chamados."""
        ia = self._ia_com_mock_client()
        dados = {'confianca': {'nivel': 'ALTO', 'campos_incertos': []}}
        ia._client.messages.create.return_value = self._api_resp(dados)

        resultado = ia._call([])

        assert resultado == dados
        assert ia._client.messages.create.call_count == 1
        assert ia._client.messages.create.call_args.kwargs['model'] == 'claude-haiku-4-5-20251001'

    def test_haiku_medio_escala_para_sonnet(self):
        """Haiku MEDIO → Sonnet retorna ALTO → Opus não chamado."""
        ia = self._ia_com_mock_client()
        dados_haiku  = {'confianca': {'nivel': 'MEDIO', 'campos_incertos': ['valor_total']}}
        dados_sonnet = {'confianca': {'nivel': 'ALTO',  'campos_incertos': []}, 'valor_total': 150000}
        ia._client.messages.create.side_effect = [
            self._api_resp(dados_haiku),
            self._api_resp(dados_sonnet),
        ]

        resultado = ia._call([])

        assert resultado == dados_sonnet
        assert ia._client.messages.create.call_count == 2
        modelos = [c.kwargs['model'] for c in ia._client.messages.create.call_args_list]
        assert modelos == ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6']

    def test_haiku_baixo_escala_para_sonnet(self):
        """Haiku BAIXO → Sonnet resolve → Opus não chamado."""
        ia = self._ia_com_mock_client()
        dados_haiku  = {'confianca': {'nivel': 'BAIXO', 'campos_incertos': ['cpf', 'data_contrato']}}
        dados_sonnet = {'confianca': {'nivel': 'ALTO',  'campos_incertos': []}}
        ia._client.messages.create.side_effect = [
            self._api_resp(dados_haiku),
            self._api_resp(dados_sonnet),
        ]

        resultado = ia._call([])

        assert resultado == dados_sonnet
        assert ia._client.messages.create.call_count == 2
        assert ia._client.messages.create.call_args.kwargs['model'] == 'claude-sonnet-4-6'

    def test_haiku_sem_campo_confianca_escala_para_sonnet(self):
        """JSON sem 'confianca' é não-ALTO → escala preventiva para Sonnet."""
        ia = self._ia_com_mock_client()
        dados_haiku  = {'valor_total': 100000}
        dados_sonnet = {'valor_total': 100000, 'confianca': {'nivel': 'ALTO', 'campos_incertos': []}}
        ia._client.messages.create.side_effect = [
            self._api_resp(dados_haiku),
            self._api_resp(dados_sonnet),
        ]

        ia._call([])

        modelos = [c.kwargs['model'] for c in ia._client.messages.create.call_args_list]
        assert modelos[1] == 'claude-sonnet-4-6'

    # ── Tier 2: Sonnet ───────────────────────────────────────────────────────

    def test_sonnet_alto_nao_chama_opus(self):
        """Haiku MEDIO → Sonnet ALTO → Opus poupado."""
        ia = self._ia_com_mock_client()
        dados_haiku  = {'confianca': {'nivel': 'MEDIO', 'campos_incertos': ['valor_total']}}
        dados_sonnet = {'confianca': {'nivel': 'ALTO',  'campos_incertos': []}}
        ia._client.messages.create.side_effect = [
            self._api_resp(dados_haiku),
            self._api_resp(dados_sonnet),
        ]

        ia._call([])

        assert ia._client.messages.create.call_count == 2
        modelos = [c.kwargs['model'] for c in ia._client.messages.create.call_args_list]
        assert 'claude-opus-4-7' not in modelos

    def test_sonnet_medio_escala_para_opus(self):
        """Haiku BAIXO → Sonnet MEDIO → Opus chamado como último recurso."""
        ia = self._ia_com_mock_client()
        dados_haiku  = {'confianca': {'nivel': 'BAIXO', 'campos_incertos': ['cpf']}}
        dados_sonnet = {'confianca': {'nivel': 'MEDIO', 'campos_incertos': ['cpf']}}
        dados_opus   = {'confianca': {'nivel': 'ALTO',  'campos_incertos': []}}
        ia._client.messages.create.side_effect = [
            self._api_resp(dados_haiku),
            self._api_resp(dados_sonnet),
            self._api_resp(dados_opus),
        ]

        resultado = ia._call([])

        assert resultado == dados_opus
        assert ia._client.messages.create.call_count == 3
        modelos = [c.kwargs['model'] for c in ia._client.messages.create.call_args_list]
        assert modelos == ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6', 'claude-opus-4-7']

    # ── Tier 3: Opus ─────────────────────────────────────────────────────────

    def test_opus_resultado_aceito_independente_de_confianca(self):
        """Opus é última instância — retorna o resultado sem nova tentativa."""
        ia = self._ia_com_mock_client()
        dados_haiku  = {'confianca': {'nivel': 'BAIXO', 'campos_incertos': ['cpf']}}
        dados_sonnet = {'confianca': {'nivel': 'BAIXO', 'campos_incertos': ['cpf']}}
        dados_opus   = {'confianca': {'nivel': 'MEDIO', 'campos_incertos': ['cpf']}}
        ia._client.messages.create.side_effect = [
            self._api_resp(dados_haiku),
            self._api_resp(dados_sonnet),
            self._api_resp(dados_opus),
        ]

        resultado = ia._call([])

        assert resultado == dados_opus
        assert ia._client.messages.create.call_count == 3


# ─── Matching de entidades ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProcessadorImportacao:

    def test_match_imobiliaria_por_cnpj(self, usuario_logado):
        from contratos.services.importacao_ia import ProcessadorImportacao
        user, _, imobiliaria, _ = usuario_logado
        dados = {'imobiliaria': {'cnpj': imobiliaria.cnpj, 'nome': imobiliaria.nome, 'tipo_pessoa': 'PJ'}}
        resultado = ProcessadorImportacao().processar(dados, user)
        assert resultado['imobiliaria_match'] == imobiliaria

    def test_sem_match_imobiliaria_cnpj_diferente(self, usuario_logado):
        from contratos.services.importacao_ia import ProcessadorImportacao
        user, _, _, _ = usuario_logado
        dados = {'imobiliaria': {'cnpj': '00.000.000/0000-00', 'nome': 'Inexistente', 'tipo_pessoa': 'PJ'}}
        resultado = ProcessadorImportacao().processar(dados, user)
        assert resultado['imobiliaria_match'] is None

    def test_match_comprador_por_cpf(self, db, usuario_logado):
        from contratos.services.importacao_ia import ProcessadorImportacao
        from tests.fixtures.factories import CompradorFactory
        user, _, _, _ = usuario_logado
        comprador = CompradorFactory(cpf='123.456.789-09')
        dados = {'comprador': {'cpf': '123.456.789-09', 'nome': comprador.nome, 'tipo_pessoa': 'PF'}}
        resultado = ProcessadorImportacao().processar(dados, user)
        assert resultado['comprador_match'] == comprador

    def test_sem_match_comprador_cpf_ausente(self, db, usuario_logado):
        from contratos.services.importacao_ia import ProcessadorImportacao
        user, _, _, _ = usuario_logado
        dados = {'comprador': {'cpf': '999.999.999-99', 'nome': 'Ninguém', 'tipo_pessoa': 'PF'}}
        resultado = ProcessadorImportacao().processar(dados, user)
        assert resultado['comprador_match'] is None

    def test_match_imovel_por_matricula(self, db, usuario_logado):
        from contratos.services.importacao_ia import ProcessadorImportacao
        from tests.fixtures.factories import ImovelFactory
        user, _, imobiliaria, _ = usuario_logado
        imovel = ImovelFactory(imobiliaria=imobiliaria, matricula='MAT-999')
        dados = {
            'imobiliaria': {'cnpj': imobiliaria.cnpj, 'nome': imobiliaria.nome, 'tipo_pessoa': 'PJ'},
            'imovel': {'matricula': 'MAT-999', 'identificacao': imovel.identificacao, 'tipo': 'LOTE'},
        }
        resultado = ProcessadorImportacao().processar(dados, user)
        assert resultado['imovel_match'] == imovel


# ─── Views: upload ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUploadImportacao:

    def test_get_retorna_200(self, usuario_logado):
        _, client, _, _ = usuario_logado
        resp = client.get(reverse('contratos:upload_importacao'))
        assert resp.status_code == 200
        assert b'Importar Contrato' in resp.content

    def test_sem_arquivo_retorna_erro(self, usuario_logado):
        _, client, _, _ = usuario_logado
        resp = client.post(reverse('contratos:upload_importacao'), {})
        assert resp.status_code == 200
        assert 'Nenhum arquivo' in resp.content.decode()

    def test_arquivo_muito_grande_retorna_erro(self, usuario_logado):
        _, client, _, _ = usuario_logado
        big = BytesIO(b'%PDF-' + b'x' * (21 * 1024 * 1024))
        big.name = 'contrato.pdf'
        resp = client.post(reverse('contratos:upload_importacao'), {'arquivo': big})
        assert resp.status_code == 200
        assert 'grande' in resp.content.decode().lower()

    def test_pdf_valido_chama_ia_e_redireciona(self, usuario_logado):
        from contratos.services.importacao_ia import ImportacaoIA
        _, client, _, _ = usuario_logado
        dados_mock = {
            'numero_contrato': 'CTR-001', 'data_contrato': '2024-01-01',
            'valor_total': 100000, 'numero_parcelas': 120, 'dia_vencimento': 10,
            'tipo_correcao': 'IPCA', 'prazo_reajuste_meses': 12,
            'percentual_juros_mora': 1.0, 'percentual_multa': 2.0,
            'imobiliaria': None, 'comprador': None, 'imovel': None,
            'prestacoes_intermediarias': [], 'observacoes': None,
            'confianca': {'nivel': 'ALTO', 'campos_incertos': []},
        }
        with patch.object(ImportacaoIA, 'extrair_de_pdf', return_value=dados_mock):
            pdf = BytesIO(b'%PDF-1.4 fake content')
            pdf.name = 'contrato.pdf'
            resp = client.post(reverse('contratos:upload_importacao'), {'arquivo': pdf})
        assert resp.status_code == 302
        assert 'revisao' in resp['Location']

    def test_erro_ia_redireciona_com_mensagem(self, usuario_logado):
        from contratos.services.importacao_ia import ImportacaoIA
        _, client, _, _ = usuario_logado
        with patch.object(ImportacaoIA, 'extrair_de_pdf', side_effect=ValueError('API indisponível')):
            pdf = BytesIO(b'%PDF-1.4')
            pdf.name = 'contrato.pdf'
            resp = client.post(reverse('contratos:upload_importacao'), {'arquivo': pdf})
        assert resp.status_code == 302
        assert resp['Location'] == reverse('contratos:upload_importacao')

    def test_requer_login(self, db):
        resp = Client().get(reverse('contratos:upload_importacao'))
        assert resp.status_code in (302, 403)


# ─── Views: revisão ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRevisaoImportacao:

    def _criar_importacao(self, usuario_logado, dados_extraidos_exemplo):
        from contratos.models import ContratoImportacao
        user, _, _, _ = usuario_logado
        return ContratoImportacao.objects.create(
            arquivo_nome='fake.pdf',
            status='REVISAO',
            dados_extraidos=dados_extraidos_exemplo,
            criado_por=user,
        )

    def test_retorna_200_com_dados(self, usuario_logado, dados_extraidos_exemplo):
        _, client, _, _ = usuario_logado
        imp = self._criar_importacao(usuario_logado, dados_extraidos_exemplo)
        resp = client.get(reverse('contratos:revisao_importacao', kwargs={'pk': imp.pk}))
        assert resp.status_code == 200
        assert b'CTR-2024-001' in resp.content

    def test_importacao_concluida_redireciona(self, usuario_logado, dados_extraidos_exemplo):
        from contratos.models import ContratoImportacao
        from tests.fixtures.factories import ContratoFactory
        user, client, _, _ = usuario_logado
        contrato = ContratoFactory()
        imp = ContratoImportacao.objects.create(
            arquivo_nome='fake.pdf',
            status='CONCLUIDO',
            dados_extraidos=dados_extraidos_exemplo,
            contrato_criado=contrato,
            criado_por=user,
        )
        resp = client.get(reverse('contratos:revisao_importacao', kwargs={'pk': imp.pk}))
        assert resp.status_code == 302

    def test_outro_usuario_nao_acessa(self, db, usuario_logado, dados_extraidos_exemplo):
        from contratos.models import ContratoImportacao
        from tests.fixtures.factories import UserFactory
        user, _, _, _ = usuario_logado
        outro_user = UserFactory()
        imp = ContratoImportacao.objects.create(
            arquivo_nome='fake.pdf',
            status='REVISAO',
            dados_extraidos=dados_extraidos_exemplo,
            criado_por=user,
        )
        outro_client = Client()
        outro_client.force_login(outro_user)
        resp = outro_client.get(reverse('contratos:revisao_importacao', kwargs={'pk': imp.pk}))
        assert resp.status_code == 404


# ─── confirmar_importacao: criação atômica ────────────────────────────────────

@pytest.mark.django_db
class TestConfirmarImportacao:

    def _importacao_em_revisao(self, user, dados):
        from contratos.models import ContratoImportacao
        return ContratoImportacao.objects.create(
            arquivo_nome='fake.pdf',
            status='REVISAO',
            dados_extraidos=dados,
            criado_por=user,
        )

    def _post_revisao(self, imob_id, comp_id, imov_id):
        return {
            'imobiliaria_match_id': str(imob_id),
            'comprador_match_id': str(comp_id),
            'imovel_match_id': str(imov_id),
            'numero_contrato': 'CTR-IMPORT-001',
            'data_contrato': '2024-03-01',
            'data_primeiro_vencimento': '2024-04-01',
            'valor_total': '150000',
            'valor_entrada': '15000',
            'numero_parcelas': '120',
            'dia_vencimento': '10',
            'tipo_correcao': 'IPCA',
            'prazo_reajuste_meses': '12',
            'percentual_juros_mora': '1.00',
            'percentual_multa': '2.00',
            'interm_count': '0',
        }

    def test_criacao_completa_com_entidades_existentes(self, usuario_logado, dados_extraidos_exemplo):
        from contratos.models import Contrato
        from tests.fixtures.factories import CompradorFactory, ImovelFactory
        user, client, imobiliaria, _ = usuario_logado
        comprador = CompradorFactory()
        imovel = ImovelFactory(imobiliaria=imobiliaria)

        imp = self._importacao_em_revisao(user, dados_extraidos_exemplo)
        post = self._post_revisao(imobiliaria.pk, comprador.pk, imovel.pk)

        resp = client.post(reverse('contratos:confirmar_importacao', kwargs={'pk': imp.pk}), post)
        assert resp.status_code == 302

        imp.refresh_from_db()
        assert imp.status == 'CONCLUIDO'
        assert imp.contrato_criado is not None
        contrato = Contrato.objects.get(pk=imp.contrato_criado_id)
        assert contrato.numero_contrato == 'CTR-IMPORT-001'
        assert contrato.imobiliaria == imobiliaria
        assert contrato.comprador == comprador

    def test_confirmacao_dupla_nao_cria_duplicata(self, usuario_logado, dados_extraidos_exemplo):
        from contratos.models import Contrato
        from tests.fixtures.factories import CompradorFactory, ImovelFactory
        user, client, imobiliaria, _ = usuario_logado
        comprador = CompradorFactory()
        imovel = ImovelFactory(imobiliaria=imobiliaria)

        imp = self._importacao_em_revisao(user, dados_extraidos_exemplo)
        post = self._post_revisao(imobiliaria.pk, comprador.pk, imovel.pk)

        client.post(reverse('contratos:confirmar_importacao', kwargs={'pk': imp.pk}), post)
        count_antes = Contrato.objects.count()
        resp = client.post(reverse('contratos:confirmar_importacao', kwargs={'pk': imp.pk}), post)
        assert resp.status_code == 302
        assert Contrato.objects.count() == count_antes

    def test_criacao_cria_novas_entidades_quando_sem_match(self, usuario_logado, dados_extraidos_exemplo):
        from core.models import Comprador, Imobiliaria
        user, client, _, _ = usuario_logado

        imp = self._importacao_em_revisao(user, dados_extraidos_exemplo)
        post = {
            'imobiliaria_match_id': '',
            'comprador_match_id': '',
            'imovel_match_id': '',
            'imob_nome': 'Nova Imobiliária LTDA',
            'imob_tipo_pessoa': 'PJ',
            'imob_cnpj': '00.111.222/0001-33',
            'comp_nome': 'Maria Nova',
            'comp_tipo_pessoa': 'PF',
            'comp_cpf': '987.654.321-00',
            'comp_email': 'maria@example.com',
            'comp_telefone': '(31) 3333-4444',
            'comp_celular': '(31) 99999-8888',
            'imov_tipo': 'LOTE',
            'imov_identificacao': 'Quadra B Lote 9',
            'numero_contrato': 'CTR-NOVO-001',
            'data_contrato': '2024-03-01',
            'data_primeiro_vencimento': '2024-04-01',
            'valor_total': '200000',
            'valor_entrada': '0',
            'numero_parcelas': '60',
            'dia_vencimento': '5',
            'tipo_correcao': 'IGPM',
            'prazo_reajuste_meses': '12',
            'percentual_juros_mora': '1.00',
            'percentual_multa': '2.00',
            'interm_count': '0',
        }
        resp = client.post(reverse('contratos:confirmar_importacao', kwargs={'pk': imp.pk}), post)
        assert resp.status_code == 302
        assert Comprador.objects.filter(nome='Maria Nova').exists()
        assert Imobiliaria.objects.filter(nome='Nova Imobiliária LTDA').exists()

    def test_data_primeiro_vencimento_calculada_automaticamente(self, usuario_logado, dados_extraidos_exemplo):
        """Quando data_primeiro_vencimento não é informada, calcula data_contrato + 30 dias."""
        from contratos.models import Contrato
        from datetime import date, timedelta
        from tests.fixtures.factories import CompradorFactory, ImovelFactory
        user, client, imobiliaria, _ = usuario_logado
        comprador = CompradorFactory()
        imovel = ImovelFactory(imobiliaria=imobiliaria)

        imp = self._importacao_em_revisao(user, dados_extraidos_exemplo)
        post = self._post_revisao(imobiliaria.pk, comprador.pk, imovel.pk)
        post['data_primeiro_vencimento'] = ''
        post['data_contrato'] = '2024-03-01'

        client.post(reverse('contratos:confirmar_importacao', kwargs={'pk': imp.pk}), post)
        imp.refresh_from_db()
        contrato = Contrato.objects.get(pk=imp.contrato_criado_id)
        esperado = date(2024, 3, 1) + timedelta(days=30)
        assert contrato.data_primeiro_vencimento == esperado

    def test_intermediarias_criadas(self, usuario_logado, dados_extraidos_exemplo):
        from contratos.models import PrestacaoIntermediaria
        from tests.fixtures.factories import CompradorFactory, ImovelFactory
        user, client, imobiliaria, _ = usuario_logado
        comprador = CompradorFactory()
        imovel = ImovelFactory(imobiliaria=imobiliaria)

        dados_com_interm = {**dados_extraidos_exemplo, 'prestacoes_intermediarias': [
            {'descricao': 'Chaves', 'mes_vencimento': 24, 'valor': 5000.0},
        ]}
        imp = self._importacao_em_revisao(user, dados_com_interm)
        post = self._post_revisao(imobiliaria.pk, comprador.pk, imovel.pk)
        post.update({
            'interm_count': '1',
            'interm_0_descricao': 'Chaves',
            'interm_0_mes_vencimento': '24',
            'interm_0_valor': '5000',
        })
        client.post(reverse('contratos:confirmar_importacao', kwargs={'pk': imp.pk}), post)
        imp.refresh_from_db()
        assert PrestacaoIntermediaria.objects.filter(contrato=imp.contrato_criado).count() == 1
