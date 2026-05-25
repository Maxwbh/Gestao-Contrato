"""
Serviço de importação de contratos via IA (Claude API).

Fluxo: arquivo (PDF ou imagens) → Claude extrai JSON → match/create entities → Contrato
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
- CPF/CNPJ: manter formatação com pontos e traços
- Estado: 2 letras maiúsculas (SP, MG, GO, etc.)
- tipo_correcao: IGPM para IGP-M/FGV, IPCA para IBGE, SELIC para taxa básica, FIXO para sem índice
- percentual_juros_mora: valor mensal em % (ex: 1.00 para 1% ao mês)
- Campo ausente no documento → null
"""


# ─────────────────────────────────────────────────────────────────────────────
# Cliente IA
# ─────────────────────────────────────────────────────────────────────────────

class ImportacaoIA:
    """Chama Claude API para extrair dados estruturados de documentos de contrato."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise RuntimeError('Pacote anthropic não instalado. Execute: pip install anthropic')
            api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
            if not api_key:
                raise RuntimeError('ANTHROPIC_API_KEY não configurada nas variáveis de ambiente.')
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def extrair_de_pdf(self, pdf_bytes: bytes) -> dict:
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

    def _call(self, content: list) -> dict:
        resposta = self.client.messages.create(
            model='claude-opus-4-7',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': content}],
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
        get_contabilidades_usuario,
    )
    from contratos.models import Contrato, PrestacaoIntermediaria, TipoCorrecao

    with transaction.atomic():
        # ── Imobiliária ───────────────────────────────────────────────────────
        imob_id = post.get('imobiliaria_match_id')
        if imob_id:
            imobiliaria = Imobiliaria.objects.get(pk=int(imob_id))
        else:
            contabilidade = get_contabilidades_usuario(user).first()
            imobiliaria = Imobiliaria.objects.create(
                contabilidade=contabilidade,
                tipo_pessoa=post.get('imob_tipo_pessoa', 'PJ'),
                nome=post.get('imob_nome', '').strip(),
                razao_social=post.get('imob_razao_social', '').strip(),
                cnpj=post.get('imob_cnpj', '').strip() or None,
                cpf=post.get('imob_cpf', '').strip() or None,
            )

        # ── Comprador ─────────────────────────────────────────────────────────
        comp_id = post.get('comprador_match_id')
        if comp_id:
            comprador = Comprador.objects.get(pk=int(comp_id))
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
            imovel = Imovel.objects.get(pk=int(imov_id))
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
        contrato = Contrato.objects.create(
            imobiliaria=imobiliaria,
            comprador=comprador,
            imovel=imovel,
            numero_contrato=post.get('numero_contrato', '').strip(),
            data_contrato=_date(post.get('data_contrato')),
            data_primeiro_vencimento=_date(post.get('data_primeiro_vencimento')),
            valor_total=_dec(post.get('valor_total')) or Decimal('0'),
            valor_entrada=_dec(post.get('valor_entrada')) or Decimal('0'),
            numero_parcelas=int(post.get('numero_parcelas') or 1),
            dia_vencimento=int(post.get('dia_vencimento') or 1),
            tipo_correcao=post.get('tipo_correcao', TipoCorrecao.IPCA),
            prazo_reajuste_meses=int(post.get('prazo_reajuste_meses') or 12),
            percentual_juros_mora=_dec(post.get('percentual_juros_mora')) or Decimal('1.00'),
            percentual_multa=_dec(post.get('percentual_multa')) or Decimal('2.00'),
        )

        # ── Prestações Intermediárias ──────────────────────────────────────────
        count = int(post.get('interm_count') or 0)
        for i in range(count):
            mes = post.get(f'interm_{i}_mes_vencimento')
            valor = _dec(post.get(f'interm_{i}_valor'))
            if mes and valor:
                PrestacaoIntermediaria.objects.create(
                    contrato=contrato,
                    numero_sequencial=i + 1,
                    mes_vencimento=int(mes),
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
