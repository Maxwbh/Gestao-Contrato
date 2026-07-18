"""
Utilitário de versão do sistema.

VERSION file: MAJOR.MINOR (o número da linha de release; ex.: 4.0)
PATCH: nº de commits (auto-incrementa a cada commit)
Versão completa: MAJOR.MINOR.PATCH

O PATCH e os metadados (commit/data) são resolvidos assim:
  1) do arquivo `.build_info` (JSON), gravado pelo build.sh no deploy — garante
     que a versão atualize em produção mesmo sem `git` disponível no runtime;
  2) fallback para `git` em tempo de execução (ambiente de desenvolvimento).
"""
import json
import subprocess
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_VERSION_FILE = _BASE_DIR / 'VERSION'
_BUILD_INFO_FILE = _BASE_DIR / '.build_info'

_cached_version: str | None = None
_cached_info: dict | None = None


def _read_base_version() -> str:
    try:
        return _VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        return '1.0'


def _read_build_info() -> dict:
    """Metadados de build gravados no deploy (build.sh). Vazio em dev."""
    try:
        return json.loads(_BUILD_INFO_FILE.read_text())
    except Exception:
        return {}


# Caminhos que NÃO contam para a versão (docs/infra — espelha o NONCODE do
# ci.yml e a política de release: commit que só toca estes caminhos não
# altera o PATCH; versão só avança com mudança de FONTE).
# Manter em sincronia com a lista equivalente no build.sh.
_EXCLUIR_NAO_FONTE = (
    'docs', '*.md', 'LICENSE', 'VERSION', '.gitignore', '.dockerignore',
    '.editorconfig', '.gitattributes', '.env.example', '.githooks', '.github',
    'static', 'staticfiles', 'media', 'render.yaml', 'Dockerfile*',
    'docker-compose.yml', 'docker-entrypoint.sh', 'build.sh',
    '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.ico', '*.webp', '*.pdf',
    '*.woff', '*.woff2', '*.ttf', '*.eot',
)


def _contar_commits_fonte(cwd=None):
    """
    PATCH = nº de commits que alteram código-FONTE. Commits só de
    documentação/infra (lista acima) não mexem na versão.
    Retorna None se o git não estiver disponível.
    """
    args = ['git', 'rev-list', '--count', 'HEAD', '--', '.']
    args += [f':(exclude){p}' for p in _EXCLUIR_NAO_FONTE]
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           cwd=cwd or _BASE_DIR, timeout=5)
        if r.returncode == 0:
            return int(r.stdout.strip())
    except Exception:
        pass
    return None


def _read_patch() -> int:
    # 1) bakeado no build (produção)
    baked = _read_build_info().get('patch')
    if baked is not None:
        try:
            return int(baked)
        except (ValueError, TypeError):
            pass
    # 2) git em runtime (desenvolvimento) — conta só commits de fonte
    contagem = _contar_commits_fonte()
    return contagem if contagem is not None else 0


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
        # Versão oficial só na main: builds de outras branches (ex.: hml)
        # recebem sufixo do canal gravado pelo build.sh (ex.: 3.2.90-hml).
        canal = _read_build_info().get('canal', '')
        sufixo = f'-{canal}' if canal and canal != 'oficial' else ''
        _cached_version = f'{base}.{patch}{sufixo}'
    return _cached_version


def get_version_info() -> dict:
    """Retorna dict com versão completa, commit hash, data do último commit e ambiente."""
    global _cached_info
    if _cached_info is None:
        from django.conf import settings
        baked = _read_build_info()
        commit_hash = baked.get('commit') or _git_run('rev-parse', '--short', 'HEAD') or 'unknown'
        commit_date = baked.get('date') or _git_run('log', '-1', '--format=%ci') or ''
        if commit_date:
            commit_date = commit_date[:19]  # YYYY-MM-DD HH:MM:SS
        canal = baked.get('canal', '')
        if canal and canal != 'oficial':
            env_label = canal.upper()  # ex.: HML
        else:
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
