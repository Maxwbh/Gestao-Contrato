# Guia de Configuração do Ambiente de Desenvolvimento

Guia completo para configurar o ambiente de desenvolvimento local.

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)

## 📋 Pré-requisitos

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Git
- Docker e Docker Compose (opcional)

## 🚀 Setup Rápido com Docker

A forma mais rápida de começar a desenvolver:

```bash
# 1. Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# 2. Copie o arquivo de ambiente
cp .env.example .env

# 3. Inicie os serviços com Docker
docker-compose up -d

# 4. Instale as dependências Python
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

pip install -r requirements.txt

# 5. Aplique as migrações
python manage.py migrate

# 6. Crie um superusuário
python manage.py createsuperuser

# 7. Gere dados de teste (opcional)
python manage.py gerar_dados_teste

# 8. Inicie o servidor
python manage.py runserver
```

Acesse: http://localhost:8000

## 🐍 Setup Manual (sem Docker)

### 1. Instalar PostgreSQL

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Windows
Baixe o instalador em: https://www.postgresql.org/download/windows/

### 2. Criar Banco de Dados

```bash
sudo -u postgres psql

CREATE DATABASE gestao_contrato;
CREATE USER gestao_contrato_user WITH PASSWORD 'sua_senha';
ALTER ROLE gestao_contrato_user SET client_encoding TO 'utf8';
ALTER ROLE gestao_contrato_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE gestao_contrato_user SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE gestao_contrato TO gestao_contrato_user;
\q
```

### 3. Instalar Redis

#### Ubuntu/Debian
```bash
sudo apt install redis-server
sudo systemctl start redis
```

#### macOS
```bash
brew install redis
brew services start redis
```

#### Windows
Baixe em: https://github.com/microsoftarchive/redis/releases

### 4. Configurar Ambiente Python

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# Instalar dependências de desenvolvimento
pip install pytest pytest-django factory-boy black flake8 isort
```

### 5. Configurar Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste:

```bash
cp .env.example .env
nano .env  # ou seu editor preferido
```

Configurações mínimas:
```
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
DATABASE_URL=postgres://gestao_contrato_user:sua_senha@localhost:5432/gestao_contrato
REDIS_URL=redis://localhost:6379/0
BRCOBRANCA_URL=http://localhost:9292
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 6. Aplicar Migrações

```bash
python manage.py migrate
```

### 7. Criar Superusuário

```bash
python manage.py createsuperuser
```

### 8. Coletar Arquivos Estáticos

```bash
python manage.py collectstatic --noinput
```

## 🔧 Configurações Adicionais

### Celery (Tarefas Assíncronas)

Terminal 1 - Worker:
```bash
celery -A gestao_contrato worker -l info
```

Terminal 2 - Beat (agendador):
```bash
celery -A gestao_contrato beat -l info
```

### BRCobranca API (Boletos)

#### Opção 1: Docker (Recomendado)
```bash
docker-compose up brcobranca
```

#### Opção 2: Manual
```bash
git clone https://github.com/Maxwbh/boleto_cnab_api.git
cd boleto_cnab_api

# Criar Gemfile.local
echo "gem 'brcobranca', git: 'https://github.com/maxwbh/brcobranca.git', branch: 'master'" > Gemfile.local

bundle install
bundle exec puma -p 9292
```

## 🧪 Executar Testes

```bash
# Todos os testes
pytest

# Apenas unitários
pytest tests/unit/

# Com cobertura
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## 📝 Gerar Dados de Teste

```bash
# Gera dados completos para desenvolvimento
python manage.py gerar_dados_teste

# Isso cria:
# - 1 Contabilidade
# - 5 Imobiliárias
# - 20 Imóveis
# - 15 Compradores
# - 10 Contratos com parcelas
```

## 🔍 Ferramentas Úteis

### Django Debug Toolbar
```bash
pip install django-debug-toolbar
```

Já configurado no projeto quando `DEBUG=True`

### Django Extensions
```bash
pip install django-extensions
```

Comandos úteis:
```bash
python manage.py shell_plus  # Shell com models pré-carregados
python manage.py show_urls   # Lista todas as URLs
python manage.py graph_models -a -o models.png  # Diagrama ER
```

### Formatação de Código

```bash
# Black (formatador)
black .

# isort (ordenar imports)
isort .

# flake8 (linting)
flake8 .
```

## 🐛 Troubleshooting

### Problema: "psycopg2 não instala"
```bash
# Ubuntu/Debian
sudo apt install libpq-dev python3-dev

# macOS
brew install postgresql

# Depois reinstale
pip install psycopg2-binary
```

### Problema: "Redis não conecta"
```bash
# Verificar se está rodando
redis-cli ping
# Deve retornar: PONG

# Verificar porta
netstat -an | grep 6379
```

### Problema: "Migrations não aplicam"
```bash
# Limpar migrations e recriar
python manage.py migrate --fake
python manage.py migrate
```

## 📚 Próximos Passos

1. Leia a [documentação de testes](/tests/README.md)
2. Explore a [API do BRCobranca](/docs/api/BRCOBRANCA.md)
3. Veja exemplos de [uso do sistema](/docs/development/EXAMPLES.md)
4. Contribua seguindo o [guia de contribuição](/docs/development/CONTRIBUTING.md)

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
