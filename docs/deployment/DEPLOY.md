# Guia Completo de Deploy

Sistema de Gestão de Contratos - Desenvolvido por Maxwell da Silva Oliveira

## 📋 Índice

1. [Deploy no Render.com](#deploy-no-rendercom)
2. [Deploy com Docker](#deploy-com-docker)
3. [Deploy em VPS/Cloud](#deploy-em-vpscloud)
4. [Variáveis de Ambiente](#variáveis-de-ambiente)

---

## 🚀 Deploy no Render.com

### Pré-requisitos
- Conta no [Render.com](https://render.com)
- Conta no GitHub com repositório do projeto
- PostgreSQL database (criar no Render)

### Passo 1: Criar Banco de Dados PostgreSQL

1. Acesse o Dashboard do Render
2. Clique em **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name:** gestao-contrato-db
   - **Database:** gestao_contrato
   - **User:** gestao_contrato_user
   - **Region:** Ohio (US East) - melhor custo-benefício
   - **Plan:** Free
4. Clique em **"Create Database"**
5. **Copie a DATABASE_URL** (Internal Database URL)

### Passo 2: Criar Web Service (Django)

1. Clique em **"New +"** → **"Web Service"**
2. Conecte seu repositório GitHub
3. Configure:
   - **Name:** gestao-contrato-web
   - **Region:** Ohio (US East)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command:**
     ```bash
     gunicorn gestao_contrato.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --max-requests 1000 --max-requests-jitter 50
     ```
   - **Plan:** Free

4. **Variáveis de Ambiente:**
   ```
   DATABASE_URL=<copiar do PostgreSQL criado>
   SECRET_KEY=<gerar uma chave segura>
   DEBUG=False
   ALLOWED_HOSTS=gestao-contrato-web.onrender.com
   BRCOBRANCA_URL=https://brcobranca-api.onrender.com
   REDIS_URL=<opcional - adicionar se usar Redis>
   ```

### Passo 3: Criar Web Service (BRCobranca API)

1. Clique em **"New +"** → **"Web Service"**
2. Conecte o repositório https://github.com/Maxwbh/boleto_cnab_api
3. Configure:
   - **Name:** brcobranca-api
   - **Region:** Ohio (US East)
   - **Branch:** master
   - **Runtime:** Docker
   - **Dockerfile Path:** Dockerfile (ou use Dockerfile.brcobranca do projeto)
   - **Plan:** Free

4. **Variáveis de Ambiente:**
   ```
   RACK_ENV=production
   PORT=9292
   MALLOC_ARENA_MAX=2
   ```

### Passo 4: Configurar Domínio (Opcional)

1. Acesse o Web Service
2. Vá em **"Settings"** → **"Custom Domain"**
3. Adicione seu domínio personalizado
4. Configure DNS conforme instruções do Render

### ⚠️ Limitações do Render Free Tier

- **Sleep automático:** Serviços ficam inativos após 15min sem uso
- **Cold start:** Primeira requisição pode levar 10-30s
- **750h/mês:** Uso gratuito compartilhado entre serviços
- **Sem shell interativo:** Não é possível acessar terminal

**Soluções:**
- Use serviços de ping para manter ativo (UptimeRobot, cron-job.org)
- Configure health checks
- Considere upgrade para plano pago ($7/mês por serviço)

---

## 🐳 Deploy com Docker

### Docker Compose (Desenvolvimento)

```bash
# 1. Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# 2. Configure variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações

# 3. Inicie os serviços
docker-compose up -d

# 4. Aplique migrações
docker-compose exec web python manage.py migrate

# 5. Crie superusuário
docker-compose exec web python manage.py createsuperuser

# 6. Acesse o sistema
# http://localhost:8000
```

### Docker Compose (Produção)

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_DB: gestao_contrato
      POSTGRES_USER: gestao_contrato_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: always

  brcobranca:
    build:
      context: .
      dockerfile: Dockerfile.brcobranca
    restart: always
    environment:
      RACK_ENV: production

  web:
    build: .
    restart: always
    command: gunicorn gestao_contrato.wsgi:application --bind 0.0.0.0:8000
    environment:
      DATABASE_URL: postgres://gestao_contrato_user:${DB_PASSWORD}@db:5432/gestao_contrato
      REDIS_URL: redis://redis:6379/0
      BRCOBRANCA_URL: http://brcobranca:9292
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
      - brcobranca

volumes:
  postgres_data:
```

---

## ☁️ Deploy em VPS/Cloud

### AWS EC2 / Google Cloud / DigitalOcean

#### 1. Provisionamento do Servidor

```bash
# Ubuntu 22.04 LTS
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3-pip python3-venv postgresql redis-server nginx git

# Criar usuário para a aplicação
sudo useradd -m -s /bin/bash gestao
sudo su - gestao
```

#### 2. Configurar PostgreSQL

```bash
sudo -u postgres psql

CREATE DATABASE gestao_contrato;
CREATE USER gestao_contrato_user WITH PASSWORD 'sua_senha_segura';
ALTER ROLE gestao_contrato_user SET client_encoding TO 'utf8';
ALTER ROLE gestao_contrato_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE gestao_contrato_user SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE gestao_contrato TO gestao_contrato_user;
\q
```

#### 3. Deploy da Aplicação

```bash
# Clone o projeto
git clone https://github.com/Maxwbh/Gestao-Contrato.git /home/gestao/app
cd /home/gestao/app

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
pip install gunicorn

# Configurar variáveis de ambiente
cp .env.example .env
nano .env  # Edite com suas configurações

# Aplicar migrações
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

#### 4. Configurar Gunicorn com Systemd

```bash
sudo nano /etc/systemd/system/gestao-contrato.service
```

```ini
[Unit]
Description=Gestao Contrato gunicorn daemon
After=network.target

[Service]
User=gestao
Group=www-data
WorkingDirectory=/home/gestao/app
Environment="PATH=/home/gestao/app/venv/bin"
EnvironmentFile=/home/gestao/app/.env
ExecStart=/home/gestao/app/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/home/gestao/app/gestao_contrato.sock \
          gestao_contrato.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl start gestao-contrato
sudo systemctl enable gestao-contrato
```

#### 5. Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/gestao-contrato
```

```nginx
server {
    listen 80;
    server_name seu-dominio.com.br;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /home/gestao/app;
    }

    location /media/ {
        root /home/gestao/app;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/gestao/app/gestao_contrato.sock;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/gestao-contrato /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 6. SSL com Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com.br
```

---

## 🔐 Variáveis de Ambiente

Ver arquivo completo: [ENVIRONMENT.md](ENVIRONMENT.md)

### Mínimas Necessárias

```bash
# Django
SECRET_KEY=seu-secret-key-super-seguro
DEBUG=False
ALLOWED_HOSTS=seu-dominio.com,*.render.com

# Database
DATABASE_URL=postgres://user:pass@host:5432/dbname

# BRCobranca API
BRCOBRANCA_URL=https://brcobranca-api.onrender.com

# Redis (opcional)
REDIS_URL=redis://localhost:6379/0
```

### Gerando SECRET_KEY

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📊 Monitoramento

### Logs no Render
```bash
# Acessar pelo Dashboard → Logs
# Ou via CLI
render logs --service gestao-contrato-web --tail
```

### Health Checks

Configure no Render:
- **Path:** `/health/`
- **Interval:** 60 segundos

---

## 🔄 Atualizações

### Render (Auto Deploy)
- Push para branch `main` → Deploy automático
- Configurável em Settings → Auto-Deploy

### Manual via SSH
```bash
cd /home/gestao/app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gestao-contrato
```

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
