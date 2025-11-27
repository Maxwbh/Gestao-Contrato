#!/usr/bin/env python
"""
Setup para instalação do Sistema de Gestão de Contratos

Instalação:
    pip install -e .                    # Desenvolvimento (editable)
    pip install .                       # Instalação normal
    pip install gestao-contrato         # Do PyPI (quando publicado)

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import os
from pathlib import Path
from setuptools import setup, find_packages

# Ler versão
version_file = Path(__file__).parent / 'VERSION'
version = version_file.read_text().strip() if version_file.exists() else '1.0.0'

# Ler README
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ''

# Ler requirements
requirements_file = Path(__file__).parent / 'requirements.txt'
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

# Requirements para desenvolvimento
dev_requirements = [
    'pytest>=7.4.3',
    'pytest-django>=4.7.0',
    'pytest-cov>=4.1.0',
    'pytest-mock>=3.12.0',
    'pytest-factoryboy>=2.6.0',
    'factory-boy>=3.3.0',
    'faker>=20.1.0',
    'black>=23.12.0',
    'flake8>=7.0.0',
    'isort>=5.13.0',
    'pylint>=3.0.0',
    'mypy>=1.8.0',
    'django-debug-toolbar>=4.2.0',
    'ipython>=8.19.0',
    'django-extensions>=3.2.0',
]

setup(
    name='gestao-contrato',
    version=version,
    description='Sistema completo de gestão de contratos de venda de imóveis',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Maxwell da Silva Oliveira',
    author_email='maxwbh@gmail.com',
    url='https://github.com/Maxwbh/Gestao-Contrato',
    project_urls={
        'Documentation': 'https://github.com/Maxwbh/Gestao-Contrato/tree/main/docs',
        'Source': 'https://github.com/Maxwbh/Gestao-Contrato',
        'Tracker': 'https://github.com/Maxwbh/Gestao-Contrato/issues',
        'Homepage': 'https://msbrasil.inf.br',
    },
    license='Proprietary',
    packages=find_packages(exclude=['tests', 'tests.*', 'docs', 'docs.*']),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements,
        'test': dev_requirements,
    },
    python_requires='>=3.11',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: Other/Proprietary License',
        'Natural Language :: Portuguese (Brazilian)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Office/Business :: Financial',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords=[
        'django',
        'contratos',
        'imobiliaria',
        'gestao',
        'boletos',
        'financeiro',
        'parcelas',
        'reajuste',
        'ipca',
        'igpm',
    ],
    entry_points={
        'console_scripts': [
            'gestao-contrato=manage:main',
        ],
    },
    zip_safe=False,
)
