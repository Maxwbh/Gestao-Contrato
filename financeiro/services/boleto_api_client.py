"""
Boleto-API Client — gateway de cobrança registrada (C6 Bank / Sicoob via OAuth+mTLS).

Responsabilidade: comunicação HTTP com o Boleto-API (Python/FastAPI).  O Django NÃO
armazena credenciais bancárias; elas ficam no cofre do Boleto-API, resolvidas por
tenant_id.  Este módulo só conhece account_config (parâmetros sem segredo) e
tenant_id.

Endpoints consumidos:
  POST   /cobranca              → registrar_cobranca()
  GET    /cobranca/{id}         → consultar_cobranca()
  DELETE /cobranca/{id}         → baixar_cobranca()
  POST   /carne                 → gerar_carne()

Desenvolvedor: Maxwell da Silva Oliveira
"""
import base64
import json
import logging
import time
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_data(valor) -> str:
    """date / datetime / str → 'YYYY-MM-DD'."""
    if not valor:
        return ''
    if hasattr(valor, 'strftime'):
        return valor.strftime('%Y-%m-%d')
    return str(valor)[:10]


def _fmt_valor(valor) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _redact(d: dict, campos=('client_secret', 'password', 'pfx', 'key')) -> dict:
    """Remove campos sensíveis antes de logar."""
    return {k: '***' if k in campos else v for k, v in d.items()}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class BoletoApiClient:
    """
    HTTP client para o Boleto-API gateway.

    Retorna sempre um dict normalizado:
      sucesso=True  → campos do boleto + cobranca_id
      sucesso=False → erro (str)
    """

    def __init__(self):
        self.base_url = getattr(settings, 'BOLETO_API_URL', 'http://localhost:8001').rstrip('/')
        self.timeout = getattr(settings, 'BOLETO_API_TIMEOUT', 30)
        self.max_tentativas = getattr(settings, 'BOLETO_API_MAX_TENTATIVAS', 3)
        self.delay_inicial = getattr(settings, 'BOLETO_API_DELAY_INICIAL', 2)

    # ------------------------------------------------------------------ #
    # Chamada genérica com retry + logging
    # ------------------------------------------------------------------ #

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f'{self.base_url}{path}'
        delay = self.delay_inicial
        last_exc: Exception | None = None
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                resp = requests.request(method, url, timeout=self.timeout, **kwargs)
                if resp.status_code < 500:
                    return resp
                logger.warning(
                    '[BoletoAPI] HTTP %d em %s %s (tentativa %d/%d)',
                    resp.status_code, method, path, tentativa, self.max_tentativas,
                )
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    '[BoletoAPI] Falha de conexão em %s %s (tentativa %d/%d): %s',
                    method, path, tentativa, self.max_tentativas, exc,
                )
            if tentativa < self.max_tentativas:
                time.sleep(delay)
                delay = min(delay * 2, 30)
        if last_exc:
            raise last_exc
        return resp  # type: ignore[return-value]  # última resposta 5xx

    # ------------------------------------------------------------------ #
    # Normalização da resposta CobrancaOut
    # ------------------------------------------------------------------ #

    def _normalizar_cobranca(self, data: dict) -> dict:
        """Converte CobrancaOut do Boleto-API para o dict padrão do Django."""
        pdf_b64 = data.get('pdf_base64') or ''
        pdf_bytes = base64.b64decode(pdf_b64) if pdf_b64 else b''
        return {
            'sucesso': True,
            'cobranca_id': str(data.get('id', '')),
            'status': str(data.get('status', '')),
            'nosso_numero': str(data.get('nosso_numero') or ''),
            'nosso_numero_formatado': str(data.get('nosso_numero') or ''),
            'nosso_numero_dv': '',
            'linha_digitavel': str(data.get('linha_digitavel') or ''),
            'codigo_barras': str(data.get('codigo_barras') or ''),
            'pix_copia_cola': str(data.get('pix_copia_cola') or ''),
            'pix_qrcode': '',
            'valor': Decimal(str(_fmt_valor(data.get('valor')))),
            'pdf_content': pdf_bytes or None,
            'raw': data.get('raw'),
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def registrar_cobranca(
        self,
        tenant_id: str,
        provider: str,
        account_config: dict,
        cobranca: dict,
    ) -> dict:
        """
        POST /cobranca — registra cobrança no banco e retorna boleto.

        cobranca = {
            valor, vencimento, nosso_numero?, seu_numero?,
            pagador: {nome, documento, endereco?},
            multa?, juros?, desconto?
        }
        """
        payload: dict[str, Any] = {
            'tenant_id': tenant_id,
            'provider': provider,
            'account_config': account_config or {},
            'cobranca': cobranca,
        }
        logger.info(
            '[BoletoAPI] registrar_cobranca tenant=%s provider=%s vencimento=%s valor=%s',
            tenant_id, provider, cobranca.get('vencimento'), cobranca.get('valor'),
        )
        try:
            resp = self._request('POST', '/cobranca', json=payload)
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}

        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON do Boleto-API'}
            if data.get('status') == 'erro':
                return {'sucesso': False, 'erro': data.get('detail', 'Erro no Boleto-API')}
            return self._normalizar_cobranca(data)

        # Erros esperados (4xx)
        try:
            err = resp.json()
            detalhe = err.get('detail') or err.get('erro') or resp.text[:300]
        except ValueError:
            detalhe = resp.text[:300]
        logger.error('[BoletoAPI] registrar_cobranca HTTP %d: %s', resp.status_code, detalhe)
        return {'sucesso': False, 'erro': f'Boleto-API retornou {resp.status_code}: {detalhe}'}

    def consultar_cobranca(
        self,
        cobranca_id: str,
        tenant_id: str,
        provider: str,
    ) -> dict:
        """GET /cobranca/{id}"""
        params = {'tenant_id': tenant_id, 'provider': provider}
        try:
            resp = self._request('GET', f'/cobranca/{cobranca_id}', params=params)
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code == 200:
            return self._normalizar_cobranca(resp.json())
        return {'sucesso': False, 'erro': f'HTTP {resp.status_code}'}

    def baixar_cobranca(
        self,
        cobranca_id: str,
        tenant_id: str,
        provider: str,
    ) -> dict:
        """DELETE /cobranca/{id} — solicita baixa/cancelamento no banco."""
        params = {'tenant_id': tenant_id, 'provider': provider}
        logger.info('[BoletoAPI] baixar_cobranca id=%s tenant=%s', cobranca_id, tenant_id)
        try:
            resp = self._request('DELETE', f'/cobranca/{cobranca_id}', params=params)
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code in (200, 204):
            data = resp.json() if resp.content else {}
            if data:
                return {'sucesso': True, **self._normalizar_cobranca(data)}
            return {'sucesso': True}
        return {'sucesso': False, 'erro': f'HTTP {resp.status_code}'}

    def gerar_carne(
        self,
        tenant_id: str,
        provider: str,
        account_config: dict,
        bank: str,
        parcelas: list[dict],
    ) -> dict:
        """
        POST /carne — registra N cobranças e devolve PDF de carnê + lista de CobrancaOut.

        parcelas: lista de dicts no mesmo formato de cobranca.cobranca em registrar_cobranca.
        Retorna: {'sucesso': bool, 'carne_pdf_content': bytes, 'cobrancas': [dict normalized]}
        """
        payload = {
            'tenant_id': tenant_id,
            'provider': provider,
            'account_config': account_config or {},
            'bank': bank,
            'parcelas': parcelas,
        }
        logger.info(
            '[BoletoAPI] gerar_carne tenant=%s provider=%s parcelas=%d',
            tenant_id, provider, len(parcelas),
        )
        try:
            resp = self._request('POST', '/carne', json=payload)
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}

        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON'}
            pdf_b64 = data.get('carne_pdf_base64') or ''
            pdf_bytes = base64.b64decode(pdf_b64) if pdf_b64 else b''
            cobrancas = [self._normalizar_cobranca(c) for c in (data.get('cobrancas') or [])]
            return {'sucesso': True, 'carne_pdf_content': pdf_bytes, 'cobrancas': cobrancas}

        try:
            err = resp.json()
            detalhe = err.get('detail') or err.get('erro') or resp.text[:300]
        except ValueError:
            detalhe = resp.text[:300]
        return {'sucesso': False, 'erro': f'Boleto-API {resp.status_code}: {detalhe}'}
