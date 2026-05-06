"""
U-02: Utilitários para ofuscação de PKs com Hashids.

encode_id(pk) → str   (ex: 1 → 'Ab3kR1')
decode_id(h)  → int | None
"""
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _get_hashids():
    from hashids import Hashids
    salt = getattr(settings, 'HASHIDS_SALT', settings.SECRET_KEY[:20])
    min_length = getattr(settings, 'HASHIDS_MIN_LENGTH', 6)
    return Hashids(salt=salt, min_length=min_length)


def encode_id(pk: int) -> str:
    if pk is None:
        return ''
    return _get_hashids().encode(pk)


def decode_id(h: str) -> int | None:
    try:
        result = _get_hashids().decode(h)
        return result[0] if result else None
    except Exception:
        return None
