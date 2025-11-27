# Sistema de Gestão de Contratos de Venda de Imóveis

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Django Version](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-%3E80%25-brightgreen.svg)](https://github.com/Maxwbh/Gestao-Contrato)

Sistema completo desenvolvido em Python/Django para gerenciamento de contratos de venda de imóveis (lotes, terrenos, casas) com funcionalidades avançadas de gestão financeira, geração de boletos, reajustes automáticos e notificações.

## 👨‍💻 Desenvolvedor

**Maxwell da Silva Oliveira**
- **E-mail:** maxwbh@gmail.com
- **LinkedIn:** [linkedin.com/in/maxwbh](https://www.linkedin.com/in/maxwbh/)
- **GitHub:** [github.com/Maxwbh](https://github.com/Maxwbh/)
- **Empresa:** M&S do Brasil LTDA
- **Website:** [msbrasil.inf.br](https://msbrasil.inf.br)

## 📋 Sobre o Sistema

Sistema desenvolvido para contabilidades que gerenciam múltiplos loteamentos, permitindo o controle completo de:

- **Contabilidades** → Gerenciam múltiplas imobiliárias
- **Imobiliárias** → Responsáveis financeiros/beneficiários dos contratos
- **Imóveis** → Lotes, terrenos, casas, apartamentos e imóveis comerciais
- **Compradores** → Clientes que adquirem os imóveis
- **Contratos** → Gestão completa com parcelas, reajustes e notificações
- **Boletos** → Geração automática via BRCobranca (17 bancos suportados)

## ✨ Funcionalidades Principais

### 💼 Gestão de Entidades
- ✅ Cadastro de Contabilidades
- ✅ Cadastro de Imobiliárias/Beneficiários
- ✅ Múltiplas contas bancárias por imobiliária
- ✅ Cadastro de Imóveis (5 tipos)
- ✅ Cadastro de Compradores (PF/PJ)

### 📝 Sistema de Contratos
- ✅ Criação de contratos de venda
- ✅ Configuração de número de parcelas
- ✅ Definição de dia de vencimento
- ✅ Cálculo de juros e multa
- ✅ Correção monetária: IPCA, IGP-M, SELIC ou Fixo
- ✅ Reajuste automático configurável

### 💰 Gestão Financeira
- ✅ Geração automática de parcelas
- ✅ Cálculo automático de encargos
- ✅ Registro de pagamentos
- ✅ Controle de saldo devedor
- ✅ Histórico completo de pagamentos
- ✅ Geração de carnês

### 🧾 Boletos Bancários
- ✅ Integração com **17 bancos** via BRCobranca
- ✅ Geração automática de boletos
- ✅ Linha digitável e código de barras
- ✅ Configuração de juros, multa e descontos
- ✅ API customizada para boletos

### 📊 Reajuste Automático
- ✅ Integração com API do Banco Central
- ✅ Busca automática de índices
- ✅ Aplicação automática de reajustes
- ✅ Histórico de reajustes

### 📧 Notificações
- ✅ E-mail, SMS e WhatsApp
- ✅ Templates personalizáveis
- ✅ Envio automático antes do vencimento
- ✅ Configuração individual por comprador

### 🎨 Interface e UX
- ✅ Dashboard com estatísticas
- ✅ Design responsivo (Bootstrap 5)
- ✅ Busca e filtros avançados
- ✅ Admin Django completo
- ✅ Máscaras de entrada (CPF, CNPJ, CEP)
- ✅ Integração com ViaCEP

## 🚀 Instalação

### Via PIP (Recomendado)

```bash
# Instalação simples
pip install gestao-contrato

# Com dependências de desenvolvimento
pip install gestao-contrato[dev]

# Editable mode (para desenvolvimento)
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato
pip install -e ".[dev]"
```

### Via Git

```bash
# Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# Crie ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure o ambiente
cp .env.example .env
# Edite o .env com suas configurações

# Aplique as migrações
python manage.py migrate

# Crie um superusuário
python manage.py createsuperuser

# Inicie o servidor
python manage.py runserver
```

Acesse: http://localhost:8000

### Via Docker Compose (Mais Rápido)

```bash
# Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# Inicie todos os serviços
docker-compose up -d

# Aplique migrações
python manage.py migrate

# Crie superusuário
python manage.py createsuperuser

# Acesse
# http://localhost:8000
```

O Docker Compose inicia:
- PostgreSQL
- Redis
- BRCobranca API (já configurada com repositórios customizados)

## 🛠️ Tecnologias

### Backend
- **Python 3.11+**
- **Django 4.2** - Framework web
- **PostgreSQL** - Banco de dados
- **Redis** - Cache e Celery broker
- **Celery** - Tarefas assíncronas
- **Gunicorn** - Servidor WSGI

### Frontend
- **Bootstrap 5**
- **Font Awesome**
- **JavaScript ES6+**

### APIs e Integrações
- **BRCobranca** - Boletos (17 bancos)
- **Banco Central** - Índices econômicos
- **ViaCEP** - Busca de endereços
- **Twilio** - SMS e WhatsApp

## 📚 Documentação

A documentação completa está organizada em `/docs`:

### Principais Guias

- **[Documentação Completa](/docs/README.md)** - Índice geral
- **[Instalação e Setup](/docs/development/SETUP.md)** - Guia de configuração
- **[Deploy no Render](/docs/deployment/DEPLOY.md)** - Deploy em produção
- **[Testes](/tests/README.md)** - Estrutura de testes
- **[API BRCobranca](/docs/api/BRCOBRANCA.md)** - Integração com boletos
- **[Contribuindo](/docs/development/CONTRIBUTING.md)** - Guia para contribuidores

### Estrutura do Projeto

```
Gestao-Contrato/
├── core/                    # App principal
├── contratos/               # Gestão de contratos
├── financeiro/              # Gestão financeira e boletos
├── notificacoes/            # Sistema de notificações
├── accounts/                # Autenticação
├── docs/                    # 📚 Documentação
│   ├── api/                 # Documentação de APIs
│   ├── deployment/          # Guias de deploy
│   ├── development/         # Guias de desenvolvimento
│   └── troubleshooting/     # Resolução de problemas
├── tests/                   # 🧪 Testes
│   ├── unit/                # Testes unitários
│   ├── integration/         # Testes de integração
│   ├── functional/          # Testes end-to-end
│   └── fixtures/            # Factories de teste
├── templates/               # Templates Django
├── static/                  # Arquivos estáticos
├── docker-compose.yml       # 🐳 Docker
├── setup.py                 # 📦 Instalação via PIP
├── pyproject.toml           # ⚙️ Configurações modernas
└── pytest.ini               # 🧪 Configuração de testes
```

## 🧪 Testes

O projeto possui uma estrutura moderna de testes com >80% de cobertura:

```bash
# Executar todos os testes
pytest

# Apenas testes unitários (rápido ~5s)
pytest tests/unit/

# Com cobertura
pytest --cov=. --cov-report=html

# Verbose
pytest -v

# Ver relatório de cobertura
open htmlcov/index.html
```

**Recursos de testes:**
- ✅ Pytest com fixtures modernas
- ✅ Factory Boy para dados de teste
- ✅ Mocks para APIs externas
- ✅ Testes unitários, integração e E2E
- ✅ Coverage >80%

Ver: [Documentação de Testes](/tests/README.md)

## 🔧 Desenvolvimento

### Ferramentas de Qualidade

O projeto inclui ferramentas modernas configuradas via `pyproject.toml`:

```bash
# Formatação automática
black .

# Ordenar imports
isort .

# Linting
flake8 .

# Type checking
mypy .

# Tudo de uma vez
black . && isort . && flake8 .
```

### Versionamento

O projeto usa **Semantic Versioning** (MAJOR.MINOR.PATCH):

```bash
# Incrementar versão
python bump_version.py patch  # 1.0.0 -> 1.0.1
python bump_version.py minor  # 1.0.0 -> 1.1.0
python bump_version.py major  # 1.0.0 -> 2.0.0

# Versão atual
cat VERSION
```

Cada tipo de mudança incrementa automaticamente:
- **MAJOR:** Mudanças incompatíveis na API
- **MINOR:** Nova funcionalidade compatível
- **PATCH:** Correções de bugs

### Dados de Teste

```bash
# Gerar dados completos para desenvolvimento
python manage.py gerar_dados_teste

# Isso cria:
# - 1 Contabilidade
# - 5 Imobiliárias
# - 20 Imóveis
# - 15 Compradores
# - 10 Contratos com parcelas
```

## 🐳 Docker e APIs Customizadas

Este projeto utiliza versões **customizadas** do BRCobranca:

### Repositórios Oficiais
- **API REST:** https://github.com/Maxwbh/boleto_cnab_api
- **Biblioteca Ruby:** https://github.com/Maxwbh/brcobranca

⚠️ **IMPORTANTE:** Use APENAS estes repositórios customizados!

O `docker-compose.yml` já está configurado corretamente.

## 🚀 Deploy

### Render.com (Recomendado)

Deploy gratuito com PostgreSQL, Redis e BRCobranca:

1. Fork este repositório
2. Crie conta no [Render](https://render.com)
3. Siga o guia: [Deploy no Render](/docs/deployment/DEPLOY.md)

### Outras Plataformas

- **VPS/Cloud:** Ver [Deploy Manual](/docs/deployment/DEPLOY.md#deploy-em-vpscloud)
- **Docker:** Ver [Deploy com Docker](/docs/deployment/DEPLOY.md#deploy-com-docker)

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia nosso [Guia de Contribuição](/docs/development/CONTRIBUTING.md) e [Código de Conduta](/CODE_OF_CONDUCT.md).

### Quick Start para Contribuir

```bash
# 1. Fork e clone
git clone https://github.com/SEU_USER/Gestao-Contrato.git

# 2. Instale dependências de dev
pip install -e ".[dev]"

# 3. Crie uma branch
git checkout -b feature/minha-feature

# 4. Faça suas mudanças e teste
pytest

# 5. Commit (incrementa versão automaticamente)
python bump_version.py patch
git add .
git commit -m "feat: minha nova feature"

# 6. Push e PR
git push origin feature/minha-feature
```

## 📝 Licença

**Proprietary** - Copyright © 2024-2025 M&S do Brasil LTDA

Este é um software proprietário. Todos os direitos reservados.

## 📞 Contato e Suporte

- **Email:** maxwbh@gmail.com
- **LinkedIn:** [linkedin.com/in/maxwbh](https://www.linkedin.com/in/maxwbh/)
- **Issues:** [github.com/Maxwbh/Gestao-Contrato/issues](https://github.com/Maxwbh/Gestao-Contrato/issues)
- **Website:** [msbrasil.inf.br](https://msbrasil.inf.br)

## 🏆 Créditos

**Desenvolvido por:** Maxwell da Silva Oliveira
**Empresa:** M&S do Brasil LTDA
**Versão:** 1.0.0
**Última atualização:** 2025-11-26

## ⭐ Mostre seu Apoio

Se este projeto foi útil para você, considere dar uma ⭐ no GitHub!

---

**Made with ❤️ in Brazil 🇧🇷**
