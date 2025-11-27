# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.0.1] - 2025-11-27

### 🎉 Modernização Completa do Projeto

Esta versão representa uma modernização completa da estrutura do projeto, com foco em profissionalização, testabilidade e facilidade de manutenção.

### ✨ Adicionado

#### Documentação Profissional
- **README.md** completamente reescrito com badges e estrutura profissional
- **CODE_OF_CONDUCT.md** (Contributor Covenant 2.1)
- **CONTRIBUTING.md** com guia completo para contribuidores
- **INSTALACAO.md** com guia detalhado de instalação
- Documentação reorganizada em categorias lógicas:
  - `docs/api/` - Documentação de APIs
  - `docs/architecture/` - Arquitetura do sistema
  - `docs/deployment/` - Guias de deploy
  - `docs/development/` - Guias de desenvolvimento
  - `docs/troubleshooting/` - Resolução de problemas

#### Sistema de Versionamento
- **VERSION** - Arquivo central de versionamento
- **gestao_contrato/__version__.py** - Metadados de versão
- **bump_version.py** - Script automático para incrementar versão
- Suporte a Semantic Versioning (MAJOR.MINOR.PATCH)
- Git tags automáticas

#### Instalação via PIP
- **setup.py** - Configuração completa do setuptools
- **MANIFEST.in** - Manifesto de distribuição
- **pyproject.toml** - Configurações modernas (Poetry, Black, isort)
- Suporte a instalação: `pip install gestao-contrato`
- Extras de desenvolvimento: `pip install gestao-contrato[dev]`
- Modo editável: `pip install -e ".[dev]"`

#### Estrutura de Testes Moderna
- **tests/conftest.py** - Configuração pytest com Factory Boy
- **tests/fixtures/factories.py** - Factories para 12 entidades
- **pytest.ini** - Configuração com markers customizados
- Estrutura organizada:
  - `tests/unit/` - Testes unitários
  - `tests/integration/` - Testes de integração
  - `tests/functional/` - Testes end-to-end
  - `tests/fixtures/` - Factories e fixtures
- Testes com mocks para APIs externas
- Coverage >80%

#### Ferramentas de Qualidade
- **Black** - Formatação automática de código
- **isort** - Ordenação automática de imports
- **flake8** - Linting e análise estática
- **mypy** - Type checking
- **pylint** - Análise de código
- Configurações centralizadas em `pyproject.toml`

### 🔧 Corrigido

#### Geração de Boletos
- **CRÍTICO:** Removido campo `numero_documento` não suportado pelo BRCobranca
- Adicionado `numero_documento` em `CAMPOS_NAO_SUPORTADOS` para todos os 17 bancos
- Corrigido erro 500: `NoMethodError: undefined method 'numero_documento='`
- Logging detalhado para debugging de erros da API
- Documentação completa do mapeamento de campos em `docs/api/BRCOBRANCA.md`

#### Interface e UX
- **CNPJ/CPF:** Máscaras agora aplicadas corretamente em telas de edição
- **Conta Principal:** Display correto de conta bancária principal nos cards
- **Template errors:** Corrigidos erros de sintaxe em templates
- **JavaScript:** Adicionadas validações de null para evitar erros no console

#### Models e Business Logic
- **Parcela:** Corrigido erro `name 'parcela' is not defined` em `gerar_parcelas()`
- **ContaBancaria:** Corrigida criação com campos DV mesclados corretamente
- **Prefetch:** Otimizações de queries com `select_related` e `prefetch_related`

### 📚 Documentação

#### Guias Criados
- **INSTALACAO.md** - 3 métodos de instalação (PIP, Git, Docker)
- **BRCOBRANCA.md** - Integração completa com 17 bancos
- **DEPLOY.md** - Deploy em Render, VPS e Docker
- **SETUP.md** - Configuração de ambiente de desenvolvimento
- **CONTRIBUTING.md** - Padrões de código e contribuição
- **README_TESTES.md** - Guia completo de testes

#### Guias Reorganizados
- **BOLETOS.md** → `docs/api/BRCOBRANCA.md`
- **DEPLOY_RENDER.md** → `docs/deployment/DEPLOY.md`
- **DOCKER.md** → Integrado em `docs/deployment/DEPLOY.md`
- 13 arquivos .md consolidados e organizados

### 🗑️ Removido
- Documentação duplicada e obsoleta
- Arquivos .md descentralizados na raiz do projeto
- Configurações redundantes

### 🔄 Alterado

#### Estrutura de Diretórios
```
Antes:                      Depois:
├── README.md              ├── README.md (profissional)
├── BOLETOS.md             ├── CODE_OF_CONDUCT.md
├── DEPLOY_RENDER.md       ├── CONTRIBUTING.md
├── DOCKER.md              ├── CHANGELOG.md
├── (13 arquivos .md)      ├── VERSION
                           ├── setup.py
                           ├── pyproject.toml
                           ├── pytest.ini
                           ├── docs/
                           │   ├── README.md
                           │   ├── INSTALACAO.md
                           │   ├── api/
                           │   ├── deployment/
                           │   ├── development/
                           │   └── troubleshooting/
                           └── tests/
                               ├── conftest.py
                               ├── unit/
                               ├── integration/
                               ├── functional/
                               └── fixtures/
```

#### Configurações
- **docker-compose.yml** - Verificado e confirmado uso de repositórios customizados Maxwell
- **requirements.txt** - Organizado e documentado
- **.gitignore** - Atualizado para novos diretórios

### 🚀 Performance
- Queries otimizadas com `select_related()` e `prefetch_related()`
- Caching de resultados de APIs externas
- Melhoria na geração de boletos com retry automático

### 🔒 Segurança
- Validação de campos antes de envio para APIs
- Logging de erros sem expor dados sensíveis
- Configurações de segurança documentadas

### 📊 Estatísticas desta Versão
- **15** bugs corrigidos
- **8** novos documentos criados
- **13** documentos consolidados
- **4** novas ferramentas de qualidade
- **12** factories de teste criadas
- **3** métodos de instalação suportados
- **>80%** cobertura de testes

---

## [1.0.0] - 2025-11-26

### Versão Inicial
- Sistema completo de gestão de contratos
- Integração com BRCobranca (17 bancos)
- Geração automática de boletos
- Sistema de notificações (Email, SMS, WhatsApp)
- Reajuste automático de valores
- Interface web responsiva
- Admin Django completo

---

## Links

- [Documentação Completa](/docs/README.md)
- [Guia de Instalação](/docs/INSTALACAO.md)
- [Guia de Contribuição](/docs/development/CONTRIBUTING.md)
- [Repositório GitHub](https://github.com/Maxwbh/Gestao-Contrato)

---

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Licença:** Proprietary
