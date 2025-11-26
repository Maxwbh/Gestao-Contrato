# Setup do Render FREE sem Acesso ao Shell

Guia completo para configurar o sistema no Render FREE (sem acesso ao Shell).

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com

---

## ⚠️ Limitação do Plano Gratuito

O plano **FREE do Render NÃO tem acesso ao Shell**.

Portanto, criamos uma **página de setup via browser** que substitui o Shell!

---

## 🚀 Configuração em 3 Passos Simples

### 1️⃣ Aguarde o Deploy Finalizar

Após fazer push do código, aguarde o deploy no Render (5-10 minutos).

Verifique nos logs:
```
==> Build succeeded
==> Starting service
```

### 2️⃣ Acesse a Página de Setup

Abra no navegador:
```
https://gestao-contrato-web.onrender.com/setup/
```

**IMPORTANTE:** Use `/setup/` no final!

### 3️⃣ Execute o Setup Completo

Na página, clique no botão:

```
🎯 Setup Completo
```

Isso executará automaticamente:
1. ✅ Migrations (cria tabelas no banco)
2. ✅ Cria superuser (admin / admin123)
3. ✅ Gera dados de teste (65 contratos, 60 lotes, etc.)

Aguarde a mensagem: **"✅ Setup completo! Recarregando página..."**

---

## 🎯 Pronto! Sistema Configurado

Após o setup, acesse:

```
Admin: https://gestao-contrato-web.onrender.com/admin/
Login: admin
Senha: admin123
```

**⚠️ IMPORTANTE:** Altere a senha imediatamente após o primeiro login!

---

## 📊 Página de Setup - Funcionalidades

A página `/setup/` mostra:

### **Status do Sistema**
- ✅ Banco de Dados (conectado ou não)
- ✅ Tabelas (criadas ou não)
- ✅ Superusuário (existe ou não)
- ✅ Dados de Teste (quantidade)

### **Ações Disponíveis**

#### **Setup Completo** (Recomendado)
Executa tudo de uma vez:
- Migrations
- Criar admin
- Gerar dados de teste

#### **Ações Individuais**
Se preferir, execute separadamente:
- **📊 Executar Migrations** - Cria tabelas
- **👤 Criar Admin** - Cria superuser
- **📋 Gerar Dados** - Gera massa de dados

---

## 🔧 Como Funciona

### **Por Trás dos Panos**

A página `/setup/` executa comandos Django via HTTP:

```python
# Migrations
python manage.py makemigrations
python manage.py migrate

# Superuser
python manage.py createsuperuser

# Dados
python manage.py gerar_dados_teste
```

Tudo via interface web, sem precisar de Shell!

---

## 📋 Dados Gerados Automaticamente

Ao clicar em "Setup Completo" ou "Gerar Dados", o sistema cria:

- ✅ 1 Contabilidade (Sete Lagoas)
- ✅ 2 Imobiliárias (Lagoa Real, Sete Colinas)
- ✅ 60 Lotes (2 loteamentos × 30 lotes)
- ✅ 5 Terrenos (Centro, Progresso, etc.)
- ✅ 60 Compradores (dados realistas)
- ✅ 65 Contratos (180-300 meses)
- ✅ 90% das parcelas pagas

**Dados prontos para testar!**

---

## 🔄 Reconfigurar o Sistema

Se quiser limpar e começar de novo:

1. Acesse: `/setup/`
2. Clique em **"📋 Gerar Dados"**
3. Na popup, marque "Limpar dados antes"
4. Confirme

Isso apagará todos os dados e gerará novos.

---

## 🐛 Troubleshooting

### Erro 500 ao acessar `/setup/`

**Causa:** Banco não configurado ou variáveis faltando

**Solução:**
1. Verifique `DATABASE_URL` no painel do Render
2. Aguarde o deploy completar
3. Tente novamente

### Setup Completo não funciona

**Solução:** Execute as ações separadamente:
1. Clique em "📊 Executar Migrations"
2. Aguarde finalizar
3. Clique em "👤 Criar Admin"
4. Aguarde finalizar
5. Clique em "📋 Gerar Dados"

### Dados não aparecem no Admin

**Causa:** Migrations não executadas

**Solução:**
1. Acesse `/setup/`
2. Verifique se "Tabelas" está ✅
3. Se não, clique em "📊 Executar Migrations"
4. Depois clique em "📋 Gerar Dados"

### Não consigo fazer login no Admin

**Causa:** Superuser não criado

**Solução:**
1. Acesse `/setup/`
2. Clique em "👤 Criar Admin"
3. Aguarde mensagem de sucesso
4. Tente login novamente com admin/admin123

---

## 🔒 Segurança

### Página `/setup/` é Pública?

**Sim**, mas segura porque:
- Não expõe dados sensíveis
- Não permite deletar dados (exceto via opção específica)
- Apenas cria/configura o sistema

### Devo Desabilitar `/setup/` em Produção?

**Recomendado**, mas não obrigatório.

Para desabilitar, adicione no `settings.py`:
```python
SETUP_ENABLED = config('SETUP_ENABLED', default=True, cast=bool)
```

E na view `setup`:
```python
if not settings.SETUP_ENABLED:
    return HttpResponse("Setup desabilitado", status=403)
```

No Render, configure:
```
SETUP_ENABLED=False
```

---

## 📱 Acessando via Mobile

A página `/setup/` é **responsiva** e funciona em qualquer dispositivo:

- 📱 Smartphone
- 💻 Notebook
- 🖥️ Desktop

Basta acessar a URL no navegador!

---

## 🎯 Fluxo Completo Recomendado

```
1. Deploy no Render ✅
   ↓
2. Aguardar Build ⏳
   ↓
3. Acessar /setup/ 🌐
   ↓
4. Clicar "Setup Completo" 🎯
   ↓
5. Aguardar processamento ⏳
   ↓
6. Sistema pronto! 🎉
   ↓
7. Acessar /admin/ 🔐
   ↓
8. Fazer login (admin/admin123) 👤
   ↓
9. Alterar senha ⚠️
   ↓
10. Usar o sistema! 🚀
```

---

## 📞 Suporte

Se encontrar problemas, envie:

1. URL do seu Render
2. Screenshot da página `/setup/`
3. Mensagem de erro (se houver)

**Contato:**
- Email: maxwbh@gmail.com
- LinkedIn: https://www.linkedin.com/in/maxwbh/

---

## ✅ Vantagens da Página de Setup

Comparado com Shell:

| Recurso | Shell | Página /setup/ |
|---------|-------|----------------|
| Disponível no FREE | ❌ Não | ✅ Sim |
| Interface gráfica | ❌ Não | ✅ Sim |
| Execução via browser | ❌ Não | ✅ Sim |
| Status visual | ❌ Não | ✅ Sim |
| Fácil de usar | ⚠️ Técnico | ✅ Simples |
| Funciona em mobile | ❌ Não | ✅ Sim |

---

## 🎁 Bônus: Endpoints Alternativos

Se preferir usar **cURL** ou **Postman**:

### Ver Status
```bash
curl https://gestao-contrato-web.onrender.com/setup/
```

### Executar Setup Completo
```bash
curl -X POST https://gestao-contrato-web.onrender.com/setup/ \
  -d "action=setup_completo&gerar_dados=true"
```

### Apenas Migrations
```bash
curl -X POST https://gestao-contrato-web.onrender.com/setup/ \
  -d "action=migrations"
```

### Apenas Superuser
```bash
curl -X POST https://gestao-contrato-web.onrender.com/setup/ \
  -d "action=superuser"
```

### Apenas Dados
```bash
curl -X POST https://gestao-contrato-web.onrender.com/setup/ \
  -d "action=dados"
```

---

## 📚 Links Úteis

- Render Dashboard: https://dashboard.render.com
- Admin do Sistema: https://gestao-contrato-web.onrender.com/admin/
- Página de Setup: https://gestao-contrato-web.onrender.com/setup/
- Gerar Dados (API): https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/

---

**Desenvolvido com ❤️ por Maxwell da Silva Oliveira**

**M&S do Brasil LTDA**
Site: https://msbrasil.inf.br
