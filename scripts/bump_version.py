#!/usr/bin/env python3
"""
Script para atualizar a linha de release (MAJOR.MINOR) do projeto.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: /maxwbh
Empresa: M&S do Brasil LTDA - www.msbrasil.inf.br

O arquivo VERSION guarda apenas MAJOR.MINOR (ex.: 4.0). O PATCH é automático
(nº de commits) e resolvido em core/version.py — não é gravado aqui.

Uso:
    python scripts/bump_version.py [minor|major]

Exemplos:
    python scripts/bump_version.py minor  # 4.0 -> 4.1
    python scripts/bump_version.py major  # 4.0 -> 5.0
"""
import sys
from pathlib import Path


def get_project_root():
    """Retorna o diretorio raiz do projeto"""
    return Path(__file__).resolve().parent.parent


def read_version():
    """Le a versao atual (MAJOR.MINOR) do arquivo VERSION"""
    version_file = get_project_root() / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return '0.0'


def write_version(version):
    """Escreve a nova versao (MAJOR.MINOR) no arquivo VERSION"""
    version_file = get_project_root() / 'VERSION'
    version_file.write_text(f'{version}\n')


def parse_version(version_str):
    """Converte 'MAJOR.MINOR' para (major, minor). Ignora patch legado, se houver."""
    parts = version_str.split('.')
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return (major, minor)


def bump_version(bump_type='minor'):
    """
    Incrementa a linha de release.

    Args:
        bump_type: 'minor' (padrao) ou 'major'

    Returns:
        Nova versao MAJOR.MINOR como string
    """
    major, minor = parse_version(read_version())

    if bump_type == 'major':
        major += 1
        minor = 0
    else:  # minor
        minor += 1

    new_version = f'{major}.{minor}'
    write_version(new_version)

    return new_version


def main():
    """Funcao principal"""
    bump_type = 'minor'

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('minor', 'major'):
            bump_type = arg
        elif arg == 'patch':
            print('PATCH e automatico (no. de commits) — nada a gravar no VERSION.')
            print('A versao completa MAJOR.MINOR.PATCH e resolvida em core/version.py.')
            sys.exit(0)
        elif arg in ('-h', '--help'):
            print(__doc__)
            sys.exit(0)
        else:
            print(f'Tipo invalido: {arg}')
            print('Use: minor ou major (patch e automatico)')
            sys.exit(1)

    old_version = read_version()
    new_version = bump_version(bump_type)

    print(f'Linha de release atualizada: {old_version} -> {new_version}')
    return new_version


if __name__ == '__main__':
    main()
