"""
Utilitário de versão do sistema.

VERSION file: MAJOR.MINOR (editado manualmente a cada release)
PATCH: git rev-list --count HEAD (auto-incrementa a cada commit)
Versão completa: MAJOR.MINOR.PATCH
"""
import subprocess
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_VERSION_FILE = _BASE_DIR / 'VERSION'

_cached_version: str | None = None


def _read_base_version() -> str:
    try:
        return _VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        return '1.0'


def _read_patch() -> int:
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True, text=True, cwd=_BASE_DIR, timeout=3
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return 0


def get_version() -> str:
    global _cached_version
    if _cached_version is None:
        base = _read_base_version()
        patch = _read_patch()
        _cached_version = f'{base}.{patch}'
    return _cached_version


def reset_cache() -> None:
    global _cached_version
    _cached_version = None
