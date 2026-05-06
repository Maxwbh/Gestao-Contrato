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
_cached_info: dict | None = None


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


def _git_run(*args) -> str:
    try:
        r = subprocess.run(
            ['git'] + list(args),
            capture_output=True, text=True, cwd=_BASE_DIR, timeout=3
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ''


def get_version() -> str:
    global _cached_version
    if _cached_version is None:
        base = _read_base_version()
        patch = _read_patch()
        _cached_version = f'{base}.{patch}'
    return _cached_version


def get_version_info() -> dict:
    """Retorna dict com versão completa, commit hash, data do último commit e ambiente."""
    global _cached_info
    if _cached_info is None:
        from django.conf import settings
        commit_hash = _git_run('rev-parse', '--short', 'HEAD') or 'unknown'
        commit_date = _git_run('log', '-1', '--format=%ci') or ''
        if commit_date:
            commit_date = commit_date[:19]  # YYYY-MM-DD HH:MM:SS
        env_label = 'PROD' if not getattr(settings, 'DEBUG', True) else 'DEV'
        _cached_info = {
            'version': get_version(),
            'commit': commit_hash,
            'date': commit_date,
            'env': env_label,
        }
    return _cached_info


def reset_cache() -> None:
    global _cached_version, _cached_info
    _cached_version = None
    _cached_info = None
