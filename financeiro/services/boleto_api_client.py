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

    @staticmethod
    def _headers(bapi_token=None) -> dict:
        """Header de autenticação (stateless): Bearer bapi_ quando houver token."""
        return {'Authorization': f'Bearer {bapi_token}'} if bapi_token else {}

    @staticmethod
    def _classificar_erro(resp, op: str) -> dict:
        """
        Mapeia erros HTTP do gateway para um resultado tipado:
          401/424 → motivo='credencial' (recadastrar via onboarding)
          409     → motivo='cip'        (registro em processamento na CIP; re-agendar)
          422     → motivo='validacao'  (dado inválido; mostrar ao usuário)
          outros  → motivo='http'
        """
        try:
            err = resp.json()
            detalhe = err.get('detail') or err.get('erro') or resp.text[:300]
        except ValueError:
            detalhe = resp.text[:300]
        motivo = {401: 'credencial', 424: 'credencial', 409: 'cip', 422: 'validacao'}.get(
            resp.status_code, 'http'
        )
        logger.error('[BoletoAPI] %s HTTP %d (%s): %s', op, resp.status_code, motivo, detalhe)
        return {
            'sucesso': False,
            'codigo': resp.status_code,
            'motivo': motivo,
            'erro': f'Boleto-API retornou {resp.status_code}: {detalhe}',
        }

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
        bapi_token=None,
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
            resp = self._request('POST', '/cobranca', json=payload, headers=self._headers(bapi_token))
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

        return self._classificar_erro(resp, 'registrar_cobranca')

    def criar_credenciais(self, tenant_id: str, provider: str, credenciais: dict) -> dict:
        """
        POST /credenciais — provisiona as credenciais do banco no gateway e
        recebe o token bapi_ de uso diário. Onboarding: uma vez por conta ou
        no recadastro após 401.
        """
        payload = {'tenant_id': tenant_id, 'provider': provider, 'credenciais': credenciais or {}}
        logger.info('[BoletoAPI] criar_credenciais tenant=%s provider=%s', tenant_id, provider)
        try:
            resp = self._request('POST', '/credenciais', json=payload)
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON do Boleto-API'}
            token = data.get('bapi_token') or data.get('token') or ''
            if not token:
                return {'sucesso': False, 'erro': 'Boleto-API não retornou bapi_token'}
            return {'sucesso': True, 'bapi_token': token}
        return self._classificar_erro(resp, 'criar_credenciais')

    def emitir_bolepix(self, tenant_id, provider, account_config, cobranca, bapi_token=None) -> dict:
        """POST /bolepix — boleto com QR Pix (C6). Retorna ext_ref + linha + pix_copia_cola."""
        payload = {'tenant_id': tenant_id, 'provider': provider,
                   'account_config': account_config or {}, 'cobranca': cobranca}
        try:
            resp = self._request('POST', '/bolepix', json=payload, headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON do Boleto-API'}
            norm = self._normalizar_cobranca(data)
            norm['ext_ref'] = str(data.get('ext_ref') or data.get('id') or '')
            return norm
        return self._classificar_erro(resp, 'emitir_bolepix')

    def emitir_pix(self, tenant_id, provider, account_config, cobranca, bapi_token=None) -> dict:
        """POST /pix — Pix com vencimento (cobv) ou imediato (cob). Retorna txid + EMV."""
        payload = {'tenant_id': tenant_id, 'provider': provider,
                   'account_config': account_config or {}, 'cobranca': cobranca}
        try:
            resp = self._request('POST', '/pix', json=payload, headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON do Boleto-API'}
            return {
                'sucesso': True,
                'txid': str(data.get('txid') or ''),
                'pix_copia_cola': str(data.get('pix_copia_cola') or data.get('emv') or ''),
                'pix_qrcode': str(data.get('pix_qrcode') or ''),
                'valor': Decimal(str(_fmt_valor(data.get('valor')))),
                'status': str(data.get('status') or ''),
                'raw': data.get('raw'),
            }
        return self._classificar_erro(resp, 'emitir_pix')

    # ------------------------------------------------------------------ #
    # Pix Automático (débito recorrente)
    # ------------------------------------------------------------------ #

    def criar_recorrencia(self, tenant_id, provider, dados, bapi_token=None) -> dict:
        """POST /pix-automatico/recorrencias — cria a recorrência; retorna idRec."""
        payload = {'tenant_id': tenant_id, 'provider': provider, **(dados or {})}
        try:
            resp = self._request('POST', '/pix-automatico/recorrencias', json=payload,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON'}
            id_rec = str(data.get('idRec') or data.get('id_rec') or data.get('id') or '')
            if not id_rec:
                return {'sucesso': False, 'erro': 'Gateway não retornou idRec'}
            return {'sucesso': True, 'id_rec': id_rec, 'status': str(data.get('status', 'CRIADA'))}
        return self._classificar_erro(resp, 'criar_recorrencia')

    def cancelar_recorrencia(self, id_rec, tenant_id, provider, bapi_token=None) -> dict:
        """PATCH /pix-automatico/recorrencias/{idRec} {status: CANCELADA}."""
        payload = {'tenant_id': tenant_id, 'provider': provider, 'status': 'CANCELADA'}
        try:
            resp = self._request('PATCH', f'/pix-automatico/recorrencias/{id_rec}',
                                 json=payload, headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 204):
            return {'sucesso': True}
        return self._classificar_erro(resp, 'cancelar_recorrencia')

    def agendar_cobranca_pa(self, txid, tenant_id, provider, cobranca, bapi_token=None) -> dict:
        """PUT /pix-automatico/cobrancas/{txid} — agenda uma cobrança do ciclo."""
        payload = {'tenant_id': tenant_id, 'provider': provider, 'cobranca': cobranca or {}}
        try:
            resp = self._request('PUT', f'/pix-automatico/cobrancas/{txid}',
                                 json=payload, headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                data = {}
            return {'sucesso': True, 'txid': str(data.get('txid', txid)),
                    'status': str(data.get('status', ''))}
        return self._classificar_erro(resp, 'agendar_cobranca_pa')

    def retentar_cobranca_pa(self, txid, data_retentativa, tenant_id, provider, bapi_token=None) -> dict:
        """POST /pix-automatico/cobrancas/{txid}/retentativa/{data} — retentativa."""
        payload = {'tenant_id': tenant_id, 'provider': provider}
        try:
            resp = self._request(
                'POST', f'/pix-automatico/cobrancas/{txid}/retentativa/{data_retentativa}',
                json=payload, headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            return {'sucesso': True}
        return self._classificar_erro(resp, 'retentar_cobranca_pa')

    def consultar_cobranca(
        self,
        cobranca_id: str,
        tenant_id: str,
        provider: str,
        bapi_token=None,
    ) -> dict:
        """GET /cobranca/{id} — usado no polling (Sicoob não tem webhook de boleto)."""
        params = {'tenant_id': tenant_id, 'provider': provider}
        try:
            resp = self._request('GET', f'/cobranca/{cobranca_id}', params=params,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code == 200:
            return self._normalizar_cobranca(resp.json())
        return self._classificar_erro(resp, 'consultar_cobranca')

    def listar_pix_recebidos(
        self,
        inicio: str,
        fim: str,
        tenant_id: str,
        provider: str,
        bapi_token=None,
    ) -> dict:
        """
        GET /pix/recebidos?inicio&fim — Pix recebidos no período (rede de
        segurança do webhook). Retorna {'sucesso', 'itens': [{txid, valor, ...}]}.
        """
        params = {'tenant_id': tenant_id, 'provider': provider, 'inicio': inicio, 'fim': fim}
        try:
            resp = self._request('GET', '/pix/recebidos', params=params,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON'}
            itens = data if isinstance(data, list) else data.get('itens') or data.get('pix') or []
            return {'sucesso': True, 'itens': itens}
        return self._classificar_erro(resp, 'listar_pix_recebidos')

    def baixar_cobranca(
        self,
        cobranca_id: str,
        tenant_id: str,
        provider: str,
        bapi_token=None,
    ) -> dict:
        """DELETE /cobranca/{id} — solicita baixa/cancelamento no banco."""
        params = {'tenant_id': tenant_id, 'provider': provider}
        logger.info('[BoletoAPI] baixar_cobranca id=%s tenant=%s', cobranca_id, tenant_id)
        try:
            resp = self._request('DELETE', f'/cobranca/{cobranca_id}', params=params,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code in (200, 204):
            data = resp.json() if resp.content else {}
            if data:
                return {'sucesso': True, **self._normalizar_cobranca(data)}
            return {'sucesso': True}
        return self._classificar_erro(resp, 'baixar_cobranca')

    def alterar_cobranca(
        self,
        cobranca_id: str,
        tenant_id: str,
        provider: str,
        alteracao: dict,
        bapi_token=None,
    ) -> dict:
        """PUT /cobranca/{id} — altera valor/vencimento da cobrança (C6)."""
        payload = {'tenant_id': tenant_id, 'provider': provider, 'cobranca': alteracao or {}}
        logger.info('[BoletoAPI] alterar_cobranca id=%s tenant=%s', cobranca_id, tenant_id)
        try:
            resp = self._request('PUT', f'/cobranca/{cobranca_id}', json=payload,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                return self._normalizar_cobranca(resp.json())
            except ValueError:
                return {'sucesso': True}
        return self._classificar_erro(resp, 'alterar_cobranca')

    def devolver_pix(
        self,
        e2eid: str,
        devolucao_id: str,
        valor,
        tenant_id: str,
        provider: str,
        bapi_token=None,
    ) -> dict:
        """PUT /pix/recebidos/{e2eid}/devolucao/{id} — estorno (devolução) de Pix."""
        payload = {'tenant_id': tenant_id, 'provider': provider, 'valor': _fmt_valor(valor)}
        logger.info('[BoletoAPI] devolver_pix e2eid=%s id=%s valor=%s', e2eid, devolucao_id, valor)
        try:
            resp = self._request('PUT', f'/pix/recebidos/{e2eid}/devolucao/{devolucao_id}',
                                 json=payload, headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': f'Falha de conexão com Boleto-API: {exc}'}
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except ValueError:
                data = {}
            return {'sucesso': True, 'devolucao_id': str(data.get('id', devolucao_id)),
                    'status': str(data.get('status', ''))}
        return self._classificar_erro(resp, 'devolver_pix')

    def consultar_conciliacao(self, inicio: str, fim: str, tenant_id: str,
                              provider: str, bapi_token=None) -> dict:
        """
        GET /conciliacao — recebíveis liquidados no período segundo o banco
        (BAPI-32). Retorna itens com cobranca_id/txid/valor/pago_em.
        """
        params = {'inicio': inicio, 'fim': fim,
                  'tenant_id': tenant_id, 'provider': provider}
        try:
            resp = self._request('GET', '/conciliacao', params=params,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON do Boleto-API'}
            itens = data if isinstance(data, list) else (data.get('itens') or [])
            return {'sucesso': True, 'itens': itens}
        return self._classificar_erro(resp, 'consultar_conciliacao')

    def consultar_extrato(self, inicio: str, fim: str, tenant_id: str,
                          provider: str, bapi_token=None) -> dict:
        """GET /extrato — lançamentos da conta no período (BAPI-32)."""
        params = {'inicio': inicio, 'fim': fim,
                  'tenant_id': tenant_id, 'provider': provider}
        try:
            resp = self._request('GET', '/extrato', params=params,
                                 headers=self._headers(bapi_token))
        except requests.RequestException as exc:
            return {'sucesso': False, 'erro': str(exc)}
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                return {'sucesso': False, 'erro': 'Resposta não-JSON do Boleto-API'}
            lancamentos = data if isinstance(data, list) else (data.get('lancamentos') or [])
            return {'sucesso': True, 'lancamentos': lancamentos}
        return self._classificar_erro(resp, 'consultar_extrato')

    def gerar_carne(
        self,
        tenant_id: str,
        provider: str,
        account_config: dict,
        bank: str,
        parcelas: list[dict],
        bapi_token=None,
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
            resp = self._request('POST', '/carne', json=payload,
                                 headers=self._headers(bapi_token))
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
