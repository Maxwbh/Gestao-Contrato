"""
Onboarding do Boleto-API (modelo stateless): provisiona as credenciais do banco
(cifradas na ContaBancaria) no gateway via POST /credenciais e guarda o token
bapi_ devolvido (cifrado). Inclui recadastro automático no 401/424.
"""
import logging

from .boleto_api_client import BoletoApiClient

logger = logging.getLogger(__name__)


def onboard_conta(conta, client=None) -> dict:
    """
    Envia as credenciais decifradas da conta para POST /credenciais e grava o
    bapi_token devolvido (cifrado). Retorna {'sucesso': bool, 'erro'?}.
    """
    if not conta.tenant_id:
        return {'sucesso': False, 'erro': 'Conta sem tenant_id.'}
    credenciais = conta.credenciais
    if not credenciais:
        return {'sucesso': False, 'erro': 'Conta sem credenciais do banco cadastradas.'}
    client = client or BoletoApiClient()
    resultado = client.criar_credenciais(conta.tenant_id, conta.provider, credenciais)
    if not resultado.get('sucesso'):
        return resultado
    conta.set_bapi_token(resultado['bapi_token'])
    conta.save(update_fields=['bapi_token_cifrado', 'bapi_token_criado_em'])
    logger.info('[BoletoAPI] onboarding OK conta=%s tenant=%s', conta.pk, conta.tenant_id)
    return {'sucesso': True}


def garantir_bapi_token(conta, client=None) -> dict:
    """
    Garante que a conta tem um bapi_token; se não tiver, faz onboarding.
    Retorna {'sucesso': bool, 'bapi_token'?, 'erro'?}.
    """
    if conta.bapi_token:
        return {'sucesso': True, 'bapi_token': conta.bapi_token}
    resultado = onboard_conta(conta, client=client)
    if not resultado.get('sucesso'):
        return resultado
    return {'sucesso': True, 'bapi_token': conta.bapi_token}


def com_retry_credencial(conta, fn, client=None) -> dict:
    """
    Executa fn(bapi_token) e, se o resultado falhar por credencial (401/424),
    refaz o onboarding e tenta uma vez mais. `fn` recebe o token e devolve o
    dict de resultado do cliente.
    """
    tok = garantir_bapi_token(conta, client=client)
    if not tok.get('sucesso'):
        return tok
    resultado = fn(tok['bapi_token'])
    if isinstance(resultado, dict) and resultado.get('motivo') == 'credencial':
        logger.warning('[BoletoAPI] 401/424 — recadastrando credenciais conta=%s', conta.pk)
        ob = onboard_conta(conta, client=client)
        if not ob.get('sucesso'):
            return ob
        resultado = fn(conta.bapi_token)
    return resultado
