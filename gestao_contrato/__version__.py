"""
Versão do Sistema de Gestão de Contratos

Este arquivo é gerado automaticamente pelo sistema de versionamento.
Não edite manualmente.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""

__version__ = '1.0.1'
__author__ = 'Maxwell da Silva Oliveira'
__email__ = 'maxwbh@gmail.com'
__license__ = 'Proprietary'
__copyright__ = 'Copyright 2024-2025 M&S do Brasil LTDA'
__url__ = 'https://github.com/Maxwbh/Gestao-Contrato'
__description__ = 'Sistema completo de gestão de contratos de venda de imóveis'

VERSION_INFO = {
    'major': 1,
    'minor': 0,
    'patch': 1,
    'release': 'stable',
    'build': None
}


def get_version():
    """Retorna a versão atual do sistema"""
    return __version__


def get_version_info():
    """Retorna informações detalhadas da versão"""
    return VERSION_INFO


def get_full_version():
    """Retorna versão completa com metadados"""
    version = __version__
    if VERSION_INFO.get('build'):
        version += f"+{VERSION_INFO['build']}"
    return version
