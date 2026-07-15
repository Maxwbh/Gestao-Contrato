"""
Cifra simétrica (Fernet) para segredos em repouso — credenciais de API dos
bancos (C6/Sicoob) e o token `bapi_` do Boleto-API.

Chave: ``CREDENTIALS_ENCRYPTION_KEY`` (env; base64 urlsafe de 32 bytes, gerada
com ``Fernet.generate_key()``). Em desenvolvimento/teste, se ausente, deriva
uma chave determinística do ``SECRET_KEY`` (com aviso) para não travar o
ambiente local. **Em produção, defina a chave explicitamente** — rotacionar o
``SECRET_KEY`` sem essa variável tornaria os segredos indecifráveis.
"""
import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


def _derive_key_from_secret() -> bytes:
    """Chave Fernet determinística derivada do SECRET_KEY (fallback de dev)."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    key = getattr(settings, 'CREDENTIALS_ENCRYPTION_KEY', '') or ''
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    logger.warning(
        'CREDENTIALS_ENCRYPTION_KEY não definida — derivando do SECRET_KEY. '
        'Aceitável em dev/teste; defina a chave explicitamente em produção.'
    )
    return Fernet(_derive_key_from_secret())


def encrypt_str(plaintext: str) -> str:
    """Cifra uma string; devolve token Fernet (str) ou '' para entrada vazia."""
    if not plaintext:
        return ''
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_str(token: str) -> str:
    """Decifra um token Fernet; '' se vazio ou indecifrável (chave trocada)."""
    if not token:
        return ''
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.error('Falha ao decifrar segredo (token inválido ou chave trocada).')
        return ''


def encrypt_dict(data: dict) -> str:
    """Cifra um dict como JSON; '' para dict vazio/None."""
    if not data:
        return ''
    return encrypt_str(json.dumps(data, ensure_ascii=False, sort_keys=True))


def decrypt_dict(token: str) -> dict:
    """Decifra um token para dict; {} se vazio/indecifrável/inválido."""
    raw = decrypt_str(token)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}
