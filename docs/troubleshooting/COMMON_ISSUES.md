# Troubleshooting - Erro 500 no Render

Guia para resolver problemas de deploy no Render.

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com

---

## 🔍 Como Verificar os Logs no Render

### 1. Acessar Logs
1. Vá para o Dashboard do Render: https://dashboard.render.com
2. Clique no serviço **gestao-contrato-web**
3. Clique na aba **"Logs"** no menu lateral

### 2. O que Procurar nos Logs

#### Erros Comuns:

**Erro de ALLOWED_HOSTS:**
```
CommandError: You're accessing the development server over HTTPS, but it only supports HTTP.
DisallowedHost at /
Invalid HTTP_HOST header: 'gestao-contrato-web.onrender.com'
```
**Solução:** Já corrigido no último commit. Aguarde o redeploy.

**Erro de Migrations:**
```
django.db.utils.OperationalError: no such table
```
**Solução:** Migrations não foram executadas. Veja seção abaixo.

**Erro de Static Files:**
```
ValueError: Missing staticfiles manifest entry for 'xxx'
```
**Solução:** Execute collectstatic. Veja seção abaixo.

---

## 🔧 Correções Aplicadas

As seguintes correções foram aplicadas no último commit:

✅ **ALLOWED_HOSTS automático**
- Sistema detecta automaticamente `.onrender.com`
- Não precisa configurar manualmente
- DEBUG=False por padrão

✅ **Static Files**
- Criado diretório `static/`
- Verificação automática de diretórios
- Previne erros de arquivos faltantes

✅ **Logging aprimorado**
- Logs detalhados no console
- Facilita identificação de problemas

---

## 🚀 Forçar Redeploy

Se o erro persistir após o último commit:

### Opção 1: Via Dashboard
1. Acesse o serviço **gestao-contrato-web**
2. Clique em **"Manual Deploy"**
3. Selecione o branch: `claude/update-developer-docs-01TGF4Y9D8H9JukuLRBxgQct`
4. Clique em **"Deploy"**

### Opção 2: Via Shell (se o serviço subir)
1. Acesse **Shell** no menu lateral
2. Execute:
```bash
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser --noinput --username admin --email admin@admin.com || true
```

---

## 🗄️ Verificar Banco de Dados

### 1. Confirmar DATABASE_URL
1. Vá para **Environment** no menu lateral
2. Verifique se `DATABASE_URL` existe e aponta para o PostgreSQL

### 2. Executar Migrations via Render Shell

Se o serviço estiver UP mas com erro 500:
```bash
# Conecte ao Shell
python manage.py showmigrations  # Ver status
python manage.py migrate         # Aplicar migrations
```

---

## 📊 Variáveis de Ambiente Necessárias

### Mínimas (obrigatórias):
```env
SECRET_KEY=(gerado automaticamente pelo Render)
DATABASE_URL=(gerado automaticamente pelo PostgreSQL)
DEBUG=False
```

### Opcionais (mas recomendadas):
```env
REDIS_URL=(gerado automaticamente pelo Redis)
```

### Para notificações (opcional):
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app

TWILIO_ACCOUNT_SID=seu-sid
TWILIO_AUTH_TOKEN=seu-token
TWILIO_PHONE_NUMBER=+5511999999999
```

**Nota:** ALLOWED_HOSTS não precisa ser configurado (detectado automaticamente).

---

## 🔍 Debug Avançado

### 1. Habilitar DEBUG Temporariamente

**⚠️ APENAS PARA DEBUG - DESABILITE DEPOIS!**

1. Vá para **Environment**
2. Adicione: `DEBUG=True`
3. Faça um redeploy
4. Acesse a URL - verá o erro detalhado
5. **IMPORTANTE:** Volte `DEBUG=False` depois!

### 2. Verificar Build.sh

O script `build.sh` deve executar:
```bash
pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py createsuperuser (se não existir)
```

### 3. Verificar Logs de Build

Na aba **Logs**, procure por:
```
==> Build succeeded
==> Starting service
```

Se não aparecer "Build succeeded", há erro na instalação.

---

## 🆘 Se Nada Funcionar

### 1. Limpar Cache do Render
1. Vá para **Settings**
2. Role até **Danger Zone**
3. Clique em **Clear Build Cache**
4. Faça um novo deploy

### 2. Recriar Serviço
Se persistir, recrie do zero:
1. Delete o serviço atual
2. Crie novo Blueprint
3. Use o mesmo `render.yaml`

### 3. Testar Localmente

Clone o repositório e teste local:
```bash
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato
git checkout claude/update-developer-docs-01TGF4Y9D8H9JukuLRBxgQct

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Acesse: http://localhost:8000

Se funcionar local, o problema é específico do Render.

---

## 📞 Próximos Passos

1. **Verifique os logs** no Render Dashboard
2. **Aguarde o redeploy** do último commit
3. **Teste novamente** a URL
4. **Se erro persistir**, envie os logs para análise

---

## 📝 Comandos Úteis (via Render Shell)

```bash
# Ver status do Django
python manage.py check

# Ver migrations
python manage.py showmigrations

# Aplicar migrations
python manage.py migrate

# Coletar static files
python manage.py collectstatic --no-input

# Criar superuser
python manage.py createsuperuser

# Ver configurações
python manage.py diffsettings

# Testar banco de dados
python manage.py dbshell
```

---

## 🔗 Links Úteis

- Render Status: https://status.render.com
- Render Docs: https://render.com/docs
- Django Debug: https://docs.djangoproject.com/en/4.2/howto/error-reporting/

---

**Desenvolvido com ❤️ por Maxwell da Silva Oliveira**
