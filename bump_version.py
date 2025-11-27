#!/usr/bin/env python
"""
Script para incrementar versão automaticamente

Uso:
    python bump_version.py patch  # 1.0.0 -> 1.0.1
    python bump_version.py minor  # 1.0.0 -> 1.1.0
    python bump_version.py major  # 1.0.0 -> 2.0.0

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import sys
import re
from pathlib import Path


def read_version():
    """Lê a versão atual do arquivo VERSION"""
    version_file = Path('VERSION')
    if not version_file.exists():
        return '1.0.0'
    return version_file.read_text().strip()


def parse_version(version):
    """Parse da versão no formato semver"""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        raise ValueError(f'Versão inválida: {version}')
    return tuple(map(int, match.groups()))


def bump_version(version, bump_type='patch'):
    """Incrementa a versão"""
    major, minor, patch = parse_version(version)

    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f'Tipo de bump inválido: {bump_type}. Use: major, minor, patch')

    return f'{major}.{minor}.{patch}'


def update_version_file(new_version):
    """Atualiza o arquivo VERSION"""
    version_file = Path('VERSION')
    version_file.write_text(new_version + '\n')
    print(f'✓ VERSION atualizado: {new_version}')


def update_version_py(new_version):
    """Atualiza o arquivo __version__.py"""
    version_py = Path('gestao_contrato/__version__.py')

    if not version_py.exists():
        print('⚠ Arquivo __version__.py não encontrado')
        return

    content = version_py.read_text()

    # Atualizar __version__
    content = re.sub(
        r"__version__ = '[^']*'",
        f"__version__ = '{new_version}'",
        content
    )

    # Atualizar VERSION_INFO
    major, minor, patch = parse_version(new_version)
    content = re.sub(
        r"'major': \d+",
        f"'major': {major}",
        content
    )
    content = re.sub(
        r"'minor': \d+",
        f"'minor': {minor}",
        content
    )
    content = re.sub(
        r"'patch': \d+",
        f"'patch': {patch}",
        content
    )

    version_py.write_text(content)
    print(f'✓ __version__.py atualizado')


def update_pyproject_toml(new_version):
    """Atualiza versão no pyproject.toml"""
    pyproject = Path('pyproject.toml')

    if not pyproject.exists():
        print('⚠ Arquivo pyproject.toml não encontrado')
        return

    content = pyproject.read_text()
    content = re.sub(
        r'version = "[^"]*"',
        f'version = "{new_version}"',
        content
    )

    pyproject.write_text(content)
    print(f'✓ pyproject.toml atualizado')


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print('Uso: python bump_version.py [patch|minor|major]')
        sys.exit(1)

    bump_type = sys.argv[1].lower()

    try:
        current_version = read_version()
        print(f'Versão atual: {current_version}')

        new_version = bump_version(current_version, bump_type)
        print(f'Nova versão: {new_version}')

        # Atualizar arquivos
        update_version_file(new_version)
        update_version_py(new_version)
        update_pyproject_toml(new_version)

        print(f'\n✅ Versão incrementada com sucesso: {current_version} → {new_version}')
        print(f'\nPróximos passos:')
        print(f'  git add VERSION gestao_contrato/__version__.py pyproject.toml')
        print(f'  git commit -m "Bump version to {new_version}"')
        print(f'  git tag v{new_version}')
        print(f'  git push origin v{new_version}')

    except Exception as e:
        print(f'❌ Erro: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
