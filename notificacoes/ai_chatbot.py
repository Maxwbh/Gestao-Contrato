"""
Seção 30 — Chatbot WhatsApp com IA (Claude API).

H-02: AIIntentClassifier — usa claude-haiku para classificar intent com tool_use.
H-03: AIResponseHumanizer — gera resposta em linguagem natural com dados reais do DB.
H-04: últimas 6 mensagens de contexto passadas ao Claude.
H-05: pergunta_livre respondida com dados do comprador.
H-06: delay de digitação simulado.
H-07: fallback silencioso para despachante de regras se API falhar.
H-08: system prompt configurável via ParametroSistema.
H-09: limite de tokens por resposta e modelo configurável.
H-10: flag CHATBOT_IA_ATIVO para ligar/desligar sem deploy.
H-11: métricas gravadas na sessão.
"""
import logging
import time

logger = logging.getLogger(__name__)

# ─── Intents disponíveis ────────────────────────────────────────────────────

INTENTS = ['segunda_via', 'atraso', 'comprovante', 'resumo', 'atendente', 'pergunta_livre']

# ─── Definição das tools para o classificador ───────────────────────────────

_TOOLS = [
    {
        'name': 'classificar_intent',
        'description': (
            'Classifica o intent da mensagem do usuário. '
            'Use sempre esta ferramenta para retornar o intent identificado.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'intent': {
                    'type': 'string',
                    'enum': INTENTS,
                    'description': (
                        'segunda_via: quer gerar/receber boleto | '
                        'atraso: parcela em atraso/dívida | '
                        'comprovante: enviar comprovante de pagamento | '
                        'resumo: saldo, histórico, situação financeira | '
                        'atendente: quer falar com humano | '
                        'pergunta_livre: qualquer outra pergunta sobre o contrato'
                    ),
                },
                'confianca': {
                    'type': 'number',
                    'description': 'Confiança de 0.0 a 1.0',
                },
            },
            'required': ['intent', 'confianca'],
        },
    }
]

_DEFAULT_SYSTEM_PROMPT = """\
Você é um assistente virtual de cobrança. Sua única função é identificar o que o cliente deseja.
Classifique SEMPRE usando a ferramenta classificar_intent.
Não responda em texto — use apenas a ferramenta.
"""

_DEFAULT_HUMANIZER_PROMPT = """\
Você é o assistente virtual da imobiliária {nome_imobiliaria}.

PERSONALIDADE:
- Prestativo e cordial, sem excessiva formalidade
- Direto ao ponto — o cliente quer resolver, não ler parágrafos
- Use 1-2 emojis por mensagem quando natural
- Português brasileiro informal mas profissional

ESCOPO:
- Responda APENAS sobre: boletos, parcelas, contratos, pagamentos, situação financeira
- Para outros assuntos: "Para outros assuntos, fale com um atendente humano 👋"
- Nunca invente dados — use apenas as informações fornecidas

FORMATO WHATSAPP:
- Máximo 3 parágrafos curtos
- Valores: R$ 1.234,56 (com pontuação brasileira)
- Datas: 15/06/2025
- Não use markdown (# ** etc.) — WhatsApp formata diferente
"""


def _get_client():
    """Retorna cliente Anthropic ou None se não configurado."""
    try:
        import anthropic
        from django.conf import settings as _s
        api_key = getattr(_s, 'ANTHROPIC_API_KEY', None)
        if not api_key:
            from core.parametros import get_param
            api_key = get_param('ANTHROPIC_API_KEY', '')
        if not api_key:
            return None
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.debug('[AI Chatbot] anthropic não instalado — usando despachante de regras')
        return None


def _get_modelo() -> str:
    from core.parametros import get_param
    return get_param('CHATBOT_MODELO', 'claude-haiku-4-5-20251001')


def _get_max_tokens() -> int:
    from core.parametros import get_param
    return int(get_param('CHATBOT_MAX_TOKENS_POR_RESPOSTA', 300))


def _extrair_historico(sessao, limite: int = 6) -> list[dict]:
    """Extrai as últimas `limite` mensagens do campo dados da sessão."""
    dados = getattr(sessao, 'dados', {}) or {}
    historico = dados.get('historico_ia', [])
    return historico[-limite:]


def _salvar_historico(sessao, role: str, content: str) -> None:
    """Adiciona mensagem ao histórico da sessão (máx. 12 entradas)."""
    dados = sessao.dados or {}
    historico = dados.get('historico_ia', [])
    historico.append({'role': role, 'content': content})
    dados['historico_ia'] = historico[-12:]
    sessao.dados = dados
    sessao.save(update_fields=['dados'])


class AIIntentClassifier:
    """H-02: Classifica o intent da mensagem com claude-haiku via tool_use."""

    @staticmethod
    def classificar(texto: str, sessao=None) -> str | None:
        """
        Retorna o intent identificado ou None se falhar (H-07: fallback).

        Args:
            texto: mensagem do usuário
            sessao: SessaoConversaWhatsApp (para contexto das últimas mensagens)

        Returns:
            str (um de INTENTS) ou None
        """
        client = _get_client()
        if client is None:
            return None

        from core.parametros import get_param
        system_prompt = get_param('CHATBOT_SYSTEM_PROMPT_CLASSIFIER', _DEFAULT_SYSTEM_PROMPT)

        messages = []
        if sessao:
            messages.extend(_extrair_historico(sessao))
        messages.append({'role': 'user', 'content': texto})

        t0 = time.monotonic()
        try:
            resposta = client.messages.create(
                model=_get_modelo(),
                max_tokens=64,
                system=system_prompt,
                tools=_TOOLS,
                tool_choice={'type': 'any'},
                messages=messages,
                timeout=3.0,  # H-07: 3s timeout para fallback imediato
            )

            latencia_ms = int((time.monotonic() - t0) * 1000)

            # Extrai o resultado do tool_use
            for bloco in resposta.content:
                if bloco.type == 'tool_use' and bloco.name == 'classificar_intent':
                    intent = bloco.input.get('intent')
                    confianca = bloco.input.get('confianca', 0.0)

                    # Monitor de custo
                    from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_CHATBOT_INTENT
                    registrar(
                        provider=PROVIDER_ANTHROPIC,
                        modelo=_get_modelo(),
                        operacao=OP_CHATBOT_INTENT,
                        tokens_input=resposta.usage.input_tokens,
                        tokens_output=resposta.usage.output_tokens,
                    )
                    # H-11: gravar métricas
                    if sessao:
                        _salvar_metricas(sessao, {
                            'intent': intent,
                            'confianca': confianca,
                            'modelo': _get_modelo(),
                            'tokens_input': resposta.usage.input_tokens,
                            'tokens_output': resposta.usage.output_tokens,
                            'latencia_ms': latencia_ms,
                            'etapa': 'classificacao',
                        })

                    logger.info(
                        '[AI Chatbot] intent=%s confiança=%.2f latência=%dms',
                        intent, confianca, latencia_ms
                    )
                    return intent

        except Exception as exc:
            logger.warning('[AI Chatbot] classificação falhou (%s) — fallback para regras', exc)

        return None  # H-07: fallback


class AIResponseHumanizer:
    """H-03: Humaniza a resposta do bot com dados reais do DB."""

    @staticmethod
    def humanizar(
        dados_db: str | dict,
        intent: str,
        sessao=None,
        nome_imobiliaria: str = 'Imobiliária',
        nome_comprador: str = '',
    ) -> str | None:
        """
        Gera resposta humanizada em linguagem natural.

        Args:
            dados_db: texto ou dict com dados estruturados vindos do despachante
            intent: intent classificado
            sessao: SessaoConversaWhatsApp para contexto
            nome_imobiliaria: personaliza o assistente
            nome_comprador: personaliza a saudação

        Returns:
            str com a resposta humanizada ou None (H-07: fallback para dados_db)
        """
        client = _get_client()
        if client is None:
            return None

        from core.parametros import get_param
        system_template = get_param('CHATBOT_SYSTEM_PROMPT', _DEFAULT_HUMANIZER_PROMPT)
        system_prompt = system_template.format(nome_imobiliaria=nome_imobiliaria)

        # Contexto para o Claude: intent + dados + nome do comprador
        dados_str = dados_db if isinstance(dados_db, str) else str(dados_db)
        contexto = (
            f"Intent do cliente: {intent}\n"
            f"Nome do comprador: {nome_comprador or 'Cliente'}\n\n"
            f"Dados do sistema:\n{dados_str}"
        )

        messages = []
        if sessao:
            messages.extend(_extrair_historico(sessao))
        messages.append({'role': 'user', 'content': contexto})

        t0 = time.monotonic()
        try:
            resposta = client.messages.create(
                model=_get_modelo(),
                max_tokens=_get_max_tokens(),
                system=system_prompt,
                messages=messages,
                timeout=4.0,
            )

            latencia_ms = int((time.monotonic() - t0) * 1000)
            texto = resposta.content[0].text if resposta.content else None

            if texto:
                # Monitor de custo
                from core.services.ia_monitor import registrar, PROVIDER_ANTHROPIC, OP_CHATBOT_HUMANIZE
                registrar(
                    provider=PROVIDER_ANTHROPIC,
                    modelo=_get_modelo(),
                    operacao=OP_CHATBOT_HUMANIZE,
                    tokens_input=resposta.usage.input_tokens,
                    tokens_output=resposta.usage.output_tokens,
                )
            if texto and sessao:
                # H-11: métricas + H-04: salvar no histórico
                _salvar_metricas(sessao, {
                    'intent': intent,
                    'modelo': _get_modelo(),
                    'tokens_input': resposta.usage.input_tokens,
                    'tokens_output': resposta.usage.output_tokens,
                    'latencia_ms': latencia_ms,
                    'etapa': 'humanizacao',
                })
                _salvar_historico(sessao, 'assistant', texto)

            return texto

        except Exception as exc:
            logger.warning('[AI Chatbot] humanização falhou (%s) — retornando resposta original', exc)

        return None  # H-07: fallback


def _salvar_metricas(sessao, metricas: dict) -> None:
    """H-11: Grava métricas de IA no campo dados da sessão."""
    try:
        dados = sessao.dados or {}
        historico_metricas = dados.get('metricas_ia', [])
        historico_metricas.append(metricas)
        dados['metricas_ia'] = historico_metricas[-20:]
        sessao.dados = dados
        sessao.save(update_fields=['dados'])
    except Exception:
        pass


def delay_digitacao(segundos_min: float = 0.8, segundos_max: float = 2.0) -> None:
    """H-06: Simula delay de digitação humana."""
    import random
    time.sleep(random.uniform(segundos_min, segundos_max))
