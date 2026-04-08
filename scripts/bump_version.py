#!/usr/bin/env python3
"""
Script para incrementar a versao do projeto automaticamente.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: /maxwbh
Empresa: M&S do Brasil LTDA - www.msbrasil.inf.br

Uso:
    python scripts/bump_version.py [patch|minor|major]

Exemplos:
    python scripts/bump_version.py patch  # 1.0.0 -> 1.0.1
    python scripts/bump_version.py minor  # 1.0.0 -> 1.1.0
    python scripts/bump_version.py major  # 1.0.0 -> 2.0.0
"""
import sys
import os
from pathlib import Path


def get_project_root():
    """Retorna o diretorio raiz do projeto"""
    return Path(__file__).resolve().parent.parent


def read_version():
    """Le a versao atual do arquivo VERSION"""
    version_file = get_project_root() / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return '0.0.0'


def write_version(version):
    """Escreve a nova versao no arquivo VERSION"""
    version_file = get_project_root() / 'VERSION'
    version_file.write_text(f'{version}\n')


def parse_version(version_str):
    """Converte string de versao para tupla (major, minor, patch)"""
    parts = version_str.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


def bump_version(bump_type='patch'):
    """
    Incrementa a versao baseado no tipo.

    Args:
        bump_type: 'patch' (padrao), 'minor' ou 'major'

    Returns:
        Nova versao como string
    """
    current = read_version()
    major, minor, patch = parse_version(current)

    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f'{major}.{minor}.{patch}'
    write_version(new_version)

    return new_version


def main():
    """Funcao principal"""
    bump_type = 'patch'

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('patch', 'minor', 'major'):
            bump_type = arg
        elif arg in ('-h', '--help'):
            print(__doc__)
            sys.exit(0)
        else:
            print(f'Tipo invalido: {arg}')
            print('Use: patch, minor ou major')
            sys.exit(1)

    old_version = read_version()
    new_version = bump_version(bump_type)

    print(f'Versao atualizada: {old_version} -> {new_version}')
    return new_version


if __name__ == '__main__':
    main()
