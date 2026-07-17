"""
Serviço de importação de contratos via IA.

Fluxo: arquivo (PDF ou imagens) → IA extrai JSON → match/create entities → Contrato

Cadeia de modelos (custo crescente, acionados apenas se necessário):
  Tier 0 — Gemini 2.0 Flash  (gratuito, 1.500 req/dia) — requer GEMINI_API_KEY
  Tier 1 — Claude Haiku 4.5  (~$0,01–0,02/contrato)
  Tier 2 — Claude Sonnet 4.6 (~$0,05–0,08/contrato)
  Tier 3 — Claude Opus 4.8   (~$0,15–0,25/contrato)  — último recurso

A cascade escala para o próximo tier quando a confiança extraída não é ALTO
OU quando um tier falha (limite mensal, erro de API, JSON inválido). Só falha
de fato se nenhum tier produzir um resultado utilizável.
"""
import base64
import json
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Defaults dos modelos — os valores efetivos são configuráveis sem deploy via
# ParametroSistema (IA_GEMINI_MODELO, IA_TIERS_CLAUDE) e, para a cascade
# Claude, também via WorkflowIA/WorkflowIATier no Admin.
_GEMINI_MODEL_DEFAULT = 'gemini-2.0-flash'
_TIERS_CLAUDE = (
    'claude-haiku-4-5-20251001',  # Tier 1 — barato: contratos legíveis e padronizados
    'claude-sonnet-5',            # Tier 2 — intermediário: maioria dos casos difíceis
    'claude-opus-4-8',            # Tier 3 — caro: último recurso para documentos muito difíceis
)


def _gemini_model() -> str:
    """Modelo do Tier 0 (Gemini), configurável via parâmetro IA_GEMINI_MODELO."""
    try:
        from core.parametros import get_param
        return (get_param('IA_GEMINI_MODELO', _GEMINI_MODEL_DEFAULT)
                or _GEMINI_MODEL_DEFAULT)
    except Exception:
        return _GEMINI_MODEL_DEFAULT


def _carregar_tiers_workflow() -> tuple:
    """
    Retorna tuple de modelos para a cascade Claude, em ordem de precedência:
    WorkflowIA ativo no Admin → parâmetro IA_TIERS_CLAUDE (CSV barato→caro)
    → default hardcoded. Falha silenciosamente para nunca quebrar importações
    em produção.
    """
    try:
        from core.models import WorkflowIA
        wf = WorkflowIA.objects.filter(ativo=True).prefetch_related('tiers').first()
        if wf is not None:
            tiers = tuple(
                wf.tiers.filter(habilitado=True).order_by('ordem').values_list('modelo', flat=True)
            )
            if tiers:
                return tiers
        from core.parametros import get_param
        csv = get_param('IA_TIERS_CLAUDE', '') or ''
        tiers = tuple(m.strip() for m in csv.split(',') if m.strip())
        return tiers if tiers else _TIERS_CLAUDE
    except Exception:
        return _TIERS_CLAUDE


# ─────────────────────────────────────────────────────────────────────────────
# Prompt de extração
# ─────────────────────────────────────────────────────────────────────────────

_PROMPT = """
Você é um especialista em contratos imobiliários brasileiros.
Analise este documento e extraia TODOS os dados em formato JSON estruturado.
Retorne APENAS o JSON, sem texto adicional, markdown ou explicações.

{
  "numero_contrato": "string ou null",
  "data_contrato": "YYYY-MM-DD ou null",
  "data_primeiro_vencimento": "YYYY-MM-DD ou null",
  "valor_total": decimal ou null,
  "valor_entrada": decimal ou null,
  "numero_parcelas": inteiro ou null,
  "dia_vencimento": inteiro 1-31 ou null,
  "tipo_correcao": "IPCA|IGPM|INCC|IGPDI|INPC|TR|SELIC|FIXO ou null",
  "prazo_reajuste_meses": inteiro ou null,
  "percentual_juros_mora": decimal ou null,
  "percentual_multa": decimal ou null,
  "imobiliaria": {
    "nome": "string",
    "razao_social": "string ou null",
    "cnpj": "XX.XXX.XXX/XXXX-XX ou null",
    "cpf": "XXX.XXX.XXX-XX ou null",
    "tipo_pessoa": "PJ|PF"
  },
  "comprador": {
    "nome": "string",
    "tipo_pessoa": "PF|PJ",
    "cpf": "XXX.XXX.XXX-XX ou null",
    "cnpj": "XX.XXX.XXX/XXXX-XX ou null",
    "rg": "string ou null",
    "email": "string ou null",
    "telefone": "string ou null",
    "celular": "string ou null",
    "logradouro": "string ou null",
    "numero": "string ou null",
    "complemento": "string ou null",
    "bairro": "string ou null",
    "cidade": "string ou null",
    "estado": "UF 2 letras ou null",
    "cep": "XXXXX-XXX ou null"
  },
  "imovel": {
    "tipo": "LOTE|TERRENO|CASA|APARTAMENTO|COMERCIAL",
    "identificacao": "string",
    "loteamento": "string ou null",
    "logradouro": "string ou null",
    "numero": "string ou null",
    "complemento": "string ou null",
    "bairro": "string ou null",
    "cidade": "string ou null",
    "estado": "UF 2 letras ou null",
    "cep": "XXXXX-XXX ou null",
    "area": decimal ou null,
    "matricula": "string ou null"
  },
  "prestacoes_intermediarias": [
    {"descricao": "string", "mes_vencimento": inteiro, "valor": decimal}
  ],
  "observacoes": "string ou null",
  "confianca": {
    "nivel": "ALTO|MEDIO|BAIXO",
    "campos_incertos": ["nomes dos campos com dados incertos ou ilegíveis"]
  }
}

Regras:
- Valores monetários: "R$ 150.000,00" → 150000.00 (decimal sem vírgula)
- Datas: "10 de março de 2024" → "2024-03-10"
- CPF/CNPJ: manter formatação com pontos e traços. CNPJ pode ter letras (A-Z) nas posições 1-12 (formato alfanumérico 2026); preserve exatamente como aparece no documento.
- Estado: 2 letras maiúsculas (SP, MG, GO, etc.)
- tipo_correcao: IGPM para IGP-M/FGV, IPCA para IBGE, SELIC para taxa básica, FIXO para sem índice
- percentual_juros_mora: valor mensal em % (ex: 1.00 para 1% ao mês)
- Campo ausente no documento → null
- IMPORTANTE — campo "imobiliaria": deve ser preenchido com os dados do VENDEDOR
  (quem está vendendo o imóvel), seja ele PJ (imobiliária/construtora/loteadora) ou
  PF (pessoa física vendendo diretamente). NÃO use dados de intermediadora/corretor/
  imobiliária que recebeu comissão — esses são apenas facilitadores do negócio.
  Exemplo: se o contrato tem VENDEDOR: João Silva CPF 123... e INTERMEDIADORA: XYZ Ltda,
  preencha imobiliaria com João Silva (tipo_pessoa: PF, cpf: 123...).
- prestacoes_intermediarias: parcelas com vencimentos em datas específicas (anuais,
  semestrais etc.) distintas das parcelas mensais do financiamento principal.
  Informe o mês relativo ao início do contrato (ex: parcela anual do ano 1 = mês 12).
"""


# ─────────────────────────────────────────────────────────────────────────────
# Cliente IA
# ─────────────────────────────────────────────────────────────────────────────

class ImportacaoIA:
    """Extrai dados estruturados de contratos usando cadeia de modelos Gemini → Claude."""

    def __init__(self, usuario=None, contrato_importacao=None):
        self._client = None
        self._usuario = usuario
        self._contrato_importacao = contrato_importacao

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise RuntimeError('Pacote anthropic não instalado. Execute: pip install anthropic')
            # Precedência unificada com o chatbot: env (settings) primeiro,
            # ParametroSistema como fallback legado.
            api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
            if not api_key:
                from core.parametros import get_param
                api_key = get_param('ANTHROPIC_API_KEY', '')
            if not api_key:
                raise RuntimeError('ANTHROPIC_API_KEY não configurada nas variáveis de ambiente.')
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def extrair_de_pdf(self, pdf_bytes: bytes) -> dict:
        # Tier 0 — Gemini (gratuito)
        dados = self._tentar_gemini([{'mime_type': 'application/pdf', 'data': pdf_bytes}])
        if dados is not None:
            return dados
        # Tiers 1-3 — Claude
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')
        return self._call([
            {
                'type': 'document',
                'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': pdf_b64},
            },
            {'type': 'text', 'text': _PROMPT},
        ])

    def extrair_de_imagens(self, pares: list) -> dict:
        """pares = [(bytes, 'image/jpeg'), ...]"""
        # Tier 0 — Gemini (gratuito)
        dados = self._tentar_gemini([{'mime_type': mime, 'data': img} for img, mime in pares])
        if dados is not None:
            return dados
        # Tiers 1-3 — Claude
        content = []
        for img_bytes, mime in pares:
            content.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': mime,
                    'data': base64.standard_b64encode(img_bytes).decode('utf-8'),
                },
            })
        content.append({'type': 'text', 'text': _PROMPT})
        return self._call(content)

    def _tentar_gemini(self, partes: list) -> dict | None:
        """
        Tier 0: Gemini 2.0 Flash gratuito (1.500 req/dia).
        Retorna dados se confiança ALTO; None se quota esgotada, erro ou confiança < ALTO.
        partes = [{'mime_type': str, 'data': bytes}, ...]
        """
        api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()
        if not api_key:
            return None
        gemini_model = _gemini_model()
        try:
            from core.services.ia_monitor import checar_limite, LimiteUsoIAExcedido
            checar_limite(modelo=gemini_model, operacao='IMPORTACAO_PDF')
        except LimiteUsoIAExcedido as e:
            logger.info('Gemini bloqueado por limite mensal (%s) — escalando para cadeia Claude', e)
            return None
        try:
            import google.generativeai as genai
        except ImportError:
            logger.debug('google-generativeai não instalado — pulando Tier 0 Gemini')
            return None
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(gemini_model)
            content = [{'mime_type': p['mime_type'], 'data': p['data']} for p in partes]
            content.append(_PROMPT)
            resposta = model.generate_content(content)
            dados = _parse_json(resposta.text)
            # Registra uso (tokens via usage_metadata quando disponível)
            meta = getattr(resposta, 'usage_metadata', None)
            tok_in  = getattr(meta, 'prompt_token_count', 0) or 0
            tok_out = getattr(meta, 'candidates_token_count', 0) or 0
            from core.services.ia_monitor import registrar, PROVIDER_GOOGLE, OP_IMPORTACAO_PDF
            registrar(
                provider=PROVIDER_GOOGLE,
                modelo=gemini_model,
                operacao=OP_IMPORTACAO_PDF,
                tokens_input=tok_in,
                tokens_output=tok_out,
                usuario=self._usuario,
                contrato_importacao=self._contrato_importacao,
            )
            nivel = dados.get('confianca', {}).get('nivel')
            if nivel == 'ALTO':
                return dados
            logger.info(
                'Gemini confiança=%s campos_incertos=%s — escalando para cadeia Claude',
                nivel,
                dados.get('confianca', {}).get('campos_incertos', []),
            )
            return None
        except Exception as exc:
            logger.warning('Gemini falhou (%s) — usando cadeia Claude', type(exc).__name__)
            return None

    def _call(self, content: list) -> dict:
        """
        Percorre a cascade Claude. Um tier que retorna confiança ALTO encerra
        a cadeia. Falhas (limite mensal, erro de API, JSON inválido) NÃO abortam
        a importação: escalam para o próximo tier. Só propaga erro se nenhum
        tier produzir resultado algum.
        """
        from core.services.ia_monitor import LimiteUsoIAExcedido

        melhor: dict = {}
        ultimo_erro: Exception | None = None

        tiers = _carregar_tiers_workflow()
        for idx, modelo in enumerate(tiers):
            final = idx == len(tiers) - 1
            try:
                dados = self._invocar(modelo, content)
            except LimiteUsoIAExcedido as exc:
                ultimo_erro = exc
                logger.info('%s bloqueado por limite mensal — escalando para o próximo tier', modelo)
                continue
            except Exception as exc:
                ultimo_erro = exc
                logger.warning('%s falhou (%s) — escalando para o próximo tier', modelo, type(exc).__name__)
                continue

            melhor = dados  # guarda o último resultado utilizável obtido
            nivel = (dados.get('confianca') or {}).get('nivel')
            if nivel == 'ALTO' or final:
                return dados
            logger.info(
                '%s confiança=%s campos_incertos=%s — escalando para o próximo tier',
                modelo, nivel, (dados.get('confianca') or {}).get('campos_incertos', []),
            )

        # Nenhum tier retornou ALTO ou o tier final falhou. Usa o melhor
        # resultado parcial disponível; se nenhum tier respondeu, propaga o erro.
        if melhor:
            return melhor
        if ultimo_erro:
            raise ultimo_erro
        raise RuntimeError('Cadeia de IA não retornou nenhum resultado.')

    def _invocar(self, model: str, content: list) -> dict:
        from core.services.ia_monitor import checar_limite, LimiteUsoIAExcedido
        checar_limite(modelo=model, operacao='IMPORTACAO_PDF')
        resposta = self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{'role': 'user', 'content': content}],
        )
        from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_IMPORTACAO_PDF
        registrar(
            provider=PROVIDER_ANTHROPIC,
            modelo=model,
            operacao=OP_IMPORTACAO_PDF,
            tokens_input=resposta.usage.input_tokens,
            tokens_output=resposta.usage.output_tokens,
            usuario=self._usuario,
            contrato_importacao=self._contrato_importacao,
        )
        return _parse_json(resposta.content[0].text)


# ─────────────────────────────────────────────────────────────────────────────
# Matching de entidades
# ─────────────────────────────────────────────────────────────────────────────

class ProcessadorImportacao:
    """Tenta casar entidades extraídas com registros existentes no banco."""

    def processar(self, dados: dict, user) -> dict:
        from core.models import get_imobiliarias_usuario

        imobiliarias_qs = get_imobiliarias_usuario(user)
        imob_match = None
        if dados.get('imobiliaria'):
            imob_match = _match_imobiliaria(dados['imobiliaria'], imobiliarias_qs)

        comp_match = None
        if dados.get('comprador'):
            comp_match = _match_comprador(dados['comprador'])

        imov_match = None
        if dados.get('imovel'):
            imov_match = _match_imovel(dados['imovel'], imob_match)

        return {
            'imobiliaria_match': imob_match,
            'comprador_match': comp_match,
            'imovel_match': imov_match,
        }


def _match_imobiliaria(dados, qs):
    cnpj = (dados.get('cnpj') or '').strip()
    if cnpj:
        m = qs.filter(cnpj=cnpj).first()
        if m:
            return m
    nome = (dados.get('nome') or '').strip()
    if nome:
        return qs.filter(nome__icontains=nome).first()
    return None


def _match_comprador(dados):
    from core.models import Comprador
    cpf = (dados.get('cpf') or '').strip()
    if cpf:
        m = Comprador.objects.filter(cpf=cpf).first()
        if m:
            return m
    cnpj = (dados.get('cnpj') or '').strip()
    if cnpj:
        return Comprador.objects.filter(cnpj=cnpj).first()
    return None


def _match_imovel(dados, imobiliaria=None):
    from core.models import Imovel
    matricula = (dados.get('matricula') or '').strip()
    if matricula:
        qs = Imovel.objects.filter(matricula=matricula)
        if imobiliaria:
            qs = qs.filter(imobiliaria=imobiliaria)
        m = qs.first()
        if m:
            return m
    identificacao = (dados.get('identificacao') or '').strip()
    if identificacao and imobiliaria:
        return Imovel.objects.filter(
            identificacao__iexact=identificacao,
            imobiliaria=imobiliaria,
        ).first()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Criação do contrato (pós-revisão)
# ─────────────────────────────────────────────────────────────────────────────

def confirmar_importacao(importacao, post, user):
    """
    Cria/reutiliza todas as entidades com base nos dados revisados pelo usuário.
    Retorna o Contrato criado.
    """
    from core.models import (
        Imobiliaria, Comprador, Imovel, TipoImovel,
        get_contabilidades_usuario, get_imobiliarias_usuario,
    )
    from contratos.models import Contrato, PrestacaoIntermediaria, TipoCorrecao

    with transaction.atomic():
        # ── Imobiliária ───────────────────────────────────────────────────────
        imob_id = post.get('imobiliaria_match_id')
        if imob_id:
            # Tenant check: only allow imobiliarias the user can access
            try:
                imobiliaria = get_imobiliarias_usuario(user).get(pk=_int(imob_id))
            except Imobiliaria.DoesNotExist:
                raise ValueError(f'Imobiliária #{imob_id} não encontrada ou sem permissão de acesso.')
        else:
            contabilidade = get_contabilidades_usuario(user).first()
            if contabilidade is None:
                raise ValueError(
                    'Usuário não tem acesso a nenhuma contabilidade. '
                    'Contate o administrador para configurar o acesso.'
                )
            imob_tipo   = post.get('imob_tipo_pessoa', 'PJ')
            imob_cpf    = post.get('imob_cpf', '').strip() or None
            imob_cnpj   = post.get('imob_cnpj', '').strip() or None
            if imob_tipo == 'PF' and not imob_cpf:
                raise ValueError('CPF é obrigatório para vendedor/imobiliária Pessoa Física.')
            if imob_tipo == 'PJ' and not imob_cnpj:
                raise ValueError('CNPJ é obrigatório para vendedor/imobiliária Pessoa Jurídica.')
            imobiliaria = Imobiliaria.objects.create(
                contabilidade=contabilidade,
                tipo_pessoa=imob_tipo,
                nome=post.get('imob_nome', '').strip(),
                razao_social=post.get('imob_razao_social', '').strip(),
                cnpj=imob_cnpj,
                cpf=imob_cpf,
            )

        # ── Comprador ─────────────────────────────────────────────────────────
        comp_id = post.get('comprador_match_id')
        if comp_id:
            try:
                comprador = Comprador.objects.get(pk=_int(comp_id))
            except Comprador.DoesNotExist:
                raise ValueError(f'Comprador #{comp_id} não encontrado.')
        else:
            comprador = Comprador.objects.create(
                tipo_pessoa=post.get('comp_tipo_pessoa', 'PF'),
                nome=post.get('comp_nome', '').strip(),
                cpf=post.get('comp_cpf', '').strip() or None,
                cnpj=post.get('comp_cnpj', '').strip() or None,
                rg=post.get('comp_rg', '').strip(),
                email=post.get('comp_email', '').strip(),
                telefone=post.get('comp_telefone', '').strip(),
                celular=post.get('comp_celular', '').strip(),
                logradouro=post.get('comp_logradouro', '').strip(),
                numero=post.get('comp_numero', '').strip(),
                complemento=post.get('comp_complemento', '').strip(),
                bairro=post.get('comp_bairro', '').strip(),
                cidade=post.get('comp_cidade', '').strip(),
                estado=post.get('comp_estado', '').strip(),
                cep=post.get('comp_cep', '').strip(),
            )

        # ── Imóvel ────────────────────────────────────────────────────────────
        imov_id = post.get('imovel_match_id')
        if imov_id:
            # Tenant check: only allow imoveis linked to accessible imobiliarias
            accessible_imobs = get_imobiliarias_usuario(user).values_list('pk', flat=True)
            try:
                imovel = Imovel.objects.get(pk=_int(imov_id), imobiliaria__in=accessible_imobs)
            except Imovel.DoesNotExist:
                raise ValueError(f'Imóvel #{imov_id} não encontrado ou sem permissão de acesso.')
        else:
            imovel = Imovel.objects.create(
                imobiliaria=imobiliaria,
                tipo=post.get('imov_tipo', TipoImovel.LOTE),
                identificacao=post.get('imov_identificacao', '').strip(),
                loteamento=post.get('imov_loteamento', '').strip(),
                logradouro=post.get('imov_logradouro', '').strip(),
                numero=post.get('imov_numero', '').strip(),
                complemento=post.get('imov_complemento', '').strip(),
                bairro=post.get('imov_bairro', '').strip(),
                cidade=post.get('imov_cidade', '').strip(),
                estado=post.get('imov_estado', '').strip(),
                cep=post.get('imov_cep', '').strip(),
                area=_dec(post.get('imov_area')) or Decimal('0'),
                matricula=post.get('imov_matricula', '').strip(),
            )

        # ── Contrato ──────────────────────────────────────────────────────────
        data_pv = _date(post.get('data_primeiro_vencimento'))
        if data_pv is None:
            # Auto-calcular: 30 dias após data_contrato ou hoje
            from datetime import timedelta
            base = _date(post.get('data_contrato')) or date.today()
            data_pv = base + timedelta(days=30)

        contrato = Contrato.objects.create(
            imobiliaria=imobiliaria,
            comprador=comprador,
            imovel=imovel,
            numero_contrato=post.get('numero_contrato', '').strip(),
            data_contrato=_date(post.get('data_contrato')),
            data_primeiro_vencimento=data_pv,
            valor_total=_dec(post.get('valor_total')) or Decimal('0'),
            valor_entrada=_dec(post.get('valor_entrada')) or Decimal('0'),
            numero_parcelas=_int(post.get('numero_parcelas'), default=1),
            dia_vencimento=_int(post.get('dia_vencimento'), default=1),
            tipo_correcao=post.get('tipo_correcao', TipoCorrecao.IPCA),
            prazo_reajuste_meses=_int(post.get('prazo_reajuste_meses'), default=12),
            percentual_juros_mora=_dec(post.get('percentual_juros_mora')) or Decimal('1.00'),
            percentual_multa=_dec(post.get('percentual_multa')) or Decimal('2.00'),
        )

        # ── Prestações Intermediárias ──────────────────────────────────────────
        count = _int(post.get('interm_count'), default=0)
        for i in range(count):
            mes = post.get(f'interm_{i}_mes_vencimento')
            valor = _dec(post.get(f'interm_{i}_valor'))
            if mes and valor:
                PrestacaoIntermediaria.objects.create(
                    contrato=contrato,
                    numero_sequencial=i + 1,
                    mes_vencimento=_int(mes),
                    valor=valor,
                )

        importacao.contrato_criado = contrato
        importacao.status = 'CONCLUIDO'
        importacao.save(update_fields=['contrato_criado', 'status'])

        return contrato


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(texto: str) -> dict:
    texto = re.sub(r'^```(?:json)?\s*', '', texto.strip())
    texto = re.sub(r'\s*```$', '', texto.strip())
    try:
        return json.loads(texto.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f'Resposta da IA não é JSON válido: {exc}') from exc


def _dec(val) -> Decimal | None:
    if val is None or str(val).strip() == '':
        return None
    try:
        return Decimal(str(val).replace(',', '.').replace(' ', ''))
    except InvalidOperation:
        return None


def _date(val) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _int(val, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default
