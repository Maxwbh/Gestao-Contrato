# Guia de Instalação do Sistema de Gestão de Contratos

**Versão:** 1.0.1
**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)

## 📦 Instalação

### Método 1: Instalação via PIP (Recomendado)

#### Instalação Simples
```bash
pip install gestao-contrato
```

#### Instalação com Dependências de Desenvolvimento
```bash
pip install gestao-contrato[dev]
```

Isso instala todas as ferramentas de desenvolvimento:
- pytest e plugins (testes)
- black (formatação)
- flake8 (linting)
- isort (ordenação de imports)
- mypy (type checking)
- django-debug-toolbar
- ipython
- e mais...

#### Instalação em Modo Editável (para Desenvolvimento)
```bash
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato
pip install -e ".[dev]"
```

O modo `-e` (editável) permite que você modifique o código e as mudanças sejam refletidas imediatamente sem precisar reinstalar.

### Método 2: Instalação Manual

```bash
# 1. Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# 2. Crie ambiente virtual
python3 -m venv venv

# 3. Ative o ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Configure variáveis de ambiente
cp .env.example .env
nano .env  # Edite com suas configurações
```

### Método 3: Docker Compose (Mais Rápido)

```bash
# 1. Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# 2. Inicie todos os serviços
docker-compose up -d

# 3. Aplique migrações
docker-compose exec web python manage.py migrate

# 4. Crie superusuário
docker-compose exec web python manage.py createsuperuser

# 5. Acesse o sistema
# http://localhost:8000
```

---

## ⚙️ Configuração Inicial

### 1. Configurar Banco de Dados

#### PostgreSQL (Recomendado)

```bash
# Criar banco de dados
sudo -u postgres psql

CREATE DATABASE gestao_contrato;
CREATE USER gestao_contrato_user WITH PASSWORD 'sua_senha_segura';
GRANT ALL PRIVILEGES ON DATABASE gestao_contrato TO gestao_contrato_user;
\q
```

Configure no `.env`:
```bash
DATABASE_URL=postgres://gestao_contrato_user:sua_senha_segura@localhost:5432/gestao_contrato
```

#### SQLite (Desenvolvimento)

```bash
# Já configurado por padrão
# Arquivo: db.sqlite3
```

### 2. Aplicar Migrações

```bash
python manage.py migrate
```

### 3. Criar Superusuário

```bash
python manage.py createsuperuser
```

### 4. Coletar Arquivos Estáticos

```bash
python manage.py collectstatic --noinput
```

### 5. Gerar Dados de Teste (Opcional)

```bash
python manage.py gerar_dados_teste
```

Isso cria:
- 1 Contabilidade
- 5 Imobiliárias
- 20 Imóveis
- 15 Compradores
- 10 Contratos com parcelas

---

## 🚀 Executando o Sistema

### Desenvolvimento

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

### Produção com Gunicorn

```bash
gunicorn gestao_contrato.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120
```

---

## 🧪 Verificação da Instalação

### 1. Verificar Versão

```bash
python -c "from gestao_contrato.__version__ import get_version; print(f'Versão: {get_version()}')"
```

### 2. Executar Testes

```bash
pytest
```

### 3. Verificar Dependências

```bash
pip list | grep -E "(Django|postgres|redis|celery)"
```

### 4. Acessar Admin

Navegue para: http://localhost:8000/admin

---

## 📚 Próximos Passos

Após a instalação:

1. **Configure a BRCobranca API** para geração de boletos
   - Ver: [docs/api/BRCOBRANCA.md](/docs/api/BRCOBRANCA.md)

2. **Configure Redis e Celery** para tarefas assíncronas
   - Ver: [docs/development/SETUP.md](/docs/development/SETUP.md#celery)

3. **Configure notificações** (Email, SMS, WhatsApp)
   - Edite `.env` com credenciais do Twilio

4. **Explore a documentação**
   - [Documentação Completa](/docs/README.md)

---

## ❓ Solução de Problemas

### Erro: "No module named 'gestao_contrato'"

**Solução:**
```bash
# Reinstale em modo editável
pip install -e .
```

### Erro: "psycopg2 não instala"

**Solução Ubuntu/Debian:**
```bash
sudo apt install libpq-dev python3-dev
pip install psycopg2-binary
```

**Solução macOS:**
```bash
brew install postgresql
pip install psycopg2-binary
```

### Erro: "Redis não conecta"

**Solução:**
```bash
# Verificar se Redis está rodando
redis-cli ping
# Deve retornar: PONG

# Iniciar Redis
sudo systemctl start redis  # Linux
brew services start redis   # macOS
```

### Erro: "SECRET_KEY não definida"

**Solução:**
```bash
cp .env.example .env
# Edite .env e adicione uma SECRET_KEY
```

Gerar SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🔄 Atualizações

### Atualizar para Nova Versão

```bash
# Se instalou via pip
pip install --upgrade gestao-contrato

# Se clonou o repositório
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### Verificar Versão Atual

```bash
cat VERSION
# ou
python -c "from gestao_contrato.__version__ import __version__; print(__version__)"
```

---

## 📞 Suporte

Se encontrar problemas:

1. **Consulte a documentação:** [docs/README.md](/docs/README.md)
2. **Veja problemas comuns:** [docs/troubleshooting/COMMON_ISSUES.md](/docs/troubleshooting/COMMON_ISSUES.md)
3. **Abra uma issue:** https://github.com/Maxwbh/Gestao-Contrato/issues
4. **Contate o desenvolvedor:** maxwbh@gmail.com

---

## 📋 Requisitos do Sistema

### Mínimos

- **Python:** 3.11+
- **RAM:** 512 MB
- **Disco:** 500 MB

### Recomendados

- **Python:** 3.11 ou 3.12
- **RAM:** 2 GB
- **Disco:** 2 GB
- **PostgreSQL:** 12+
- **Redis:** 6+

### Sistemas Operacionais Suportados

- ✅ Ubuntu 20.04+
- ✅ Debian 11+
- ✅ macOS 11+
- ✅ Windows 10/11
- ✅ Docker (qualquer plataforma)

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Versão:** 1.0.1
