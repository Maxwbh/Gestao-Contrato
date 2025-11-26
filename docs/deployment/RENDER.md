# Deploy no Render (Plano Gratuito)

Guia completo para deploy do Sistema de Gestão de Contratos no Render Free Tier.

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

---

## 📋 Limitações do Plano Gratuito

O plano gratuito do Render tem as seguintes limitações:

- ✅ **Web Service**: Disponível (com sleep após inatividade)
- ✅ **PostgreSQL**: Disponível (até 1GB)
- ✅ **Redis**: Disponível (até 25MB)
- ❌ **Background Workers**: NÃO disponível (Celery)
- ❌ **Cron Jobs**: NÃO disponível

### Funcionalidades Afetadas

Sem Background Workers, as seguintes funcionalidades automáticas não funcionarão:
- ❌ Reajuste automático de parcelas (IPCA/IGPM/SELIC)
- ❌ Envio automático de notificações

### Soluções Alternativas

As tarefas podem ser executadas **manualmente** de 3 formas:

#### 1. Via Django Admin (Mais Fácil)
- Acesse `/admin/financeiro/reajuste/`
- Crie e aplique reajustes manualmente
- Acesse `/admin/notificacoes/notificacao/`
- Crie e envie notificações manualmente

#### 2. Via Render Shell
```bash
# Conecte ao shell do serviço no Render Dashboard
python manage.py processar_reajustes
python manage.py enviar_notificacoes
python manage.py processar_notificacoes_pendentes
```

#### 3. Via API REST (Futuro)
- Crie endpoints para executar as tarefas
- Use um serviço externo de cron (cron-job.org, UptimeRobot, etc.)

---

## 🚀 Passo a Passo do Deploy

### 1. Preparar Repositório

Certifique-se de que o código está no GitHub:
```bash
git push origin claude/update-developer-docs-01TGF4Y9D8H9JukuLRBxgQct
```

### 2. Criar Conta no Render

1. Acesse: https://render.com
2. Crie uma conta (pode usar GitHub)
3. Conecte seu repositório GitHub

### 3. Deploy via Blueprint

1. No Dashboard do Render, clique em **"New +"**
2. Selecione **"Blueprint"**
3. Conecte o repositório: `Maxwbh/Gestao-Contrato`
4. Selecione o branch: `claude/update-developer-docs-01TGF4Y9D8H9JukuLRBxgQct`
5. Nome do Blueprint: `Gestao-Contrato`
6. Clique em **"Apply"**

O Render criará automaticamente:
- ✅ PostgreSQL Database (`gestao-contrato-db`)
- ✅ Redis Instance (`gestao-contrato-redis`)
- ✅ Web Service (`gestao-contrato-web`)

### 4. Configurar Variáveis de Ambiente

No painel do **Web Service** (`gestao-contrato-web`), configure as seguintes variáveis:

#### Variáveis Obrigatórias

```env
ALLOWED_HOSTS=seu-app.onrender.com
```

**⚠️ IMPORTANTE:** Substitua `seu-app` pelo nome real do seu serviço no Render.

#### Variáveis Opcionais (mas recomendadas)

##### E-mail (Gmail)
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app
DEFAULT_FROM_EMAIL=noreply@gestaocontrato.com.br
```

**Como obter a senha de app do Gmail:**
1. Ative a verificação em 2 etapas: https://myaccount.google.com/security
2. Gere uma senha de app: https://myaccount.google.com/apppasswords
3. Use essa senha em `EMAIL_HOST_PASSWORD`

##### Twilio (SMS e WhatsApp)
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=seu-token-aqui
TWILIO_PHONE_NUMBER=+5511999999999
TWILIO_WHATSAPP_NUMBER=whatsapp:+5511999999999
```

**Como obter credenciais Twilio:**
1. Crie uma conta: https://www.twilio.com/try-twilio
2. Obtenha Account SID e Auth Token no Console
3. Compre ou configure um número de telefone

**Alternativas mais baratas:**
- Zenvia: https://www.zenvia.com (SMS/WhatsApp)
- TotalVoice: https://www.totalvoice.com.br (SMS)
- SMS Dev: https://smsdev.com.br (SMS barato)

##### Notificações
```env
NOTIFICACAO_DIAS_ANTECEDENCIA=5
```

### 5. Aguardar Deploy

O deploy pode levar de 5 a 10 minutos. Você pode acompanhar os logs em tempo real.

### 6. Acessar o Sistema

Após o deploy bem-sucedido:

```
URL: https://seu-app.onrender.com
Admin: https://seu-app.onrender.com/admin/
```

**Credenciais padrão:**
- Usuário: `admin`
- Senha: `admin123`

**⚠️ IMPORTANTE:** Altere a senha imediatamente após o primeiro login!

---

## 🔧 Configuração Pós-Deploy

### 1. Alterar Senha do Admin

```bash
# Via Render Shell
python manage.py changepassword admin
```

### 2. Criar Usuários Adicionais

```bash
# Via Render Shell
python manage.py createsuperuser
```

### 3. Configurar Notificações

1. Acesse `/admin/notificacoes/templatenotificacao/`
2. Crie templates para:
   - E-mail de vencimento
   - SMS de vencimento
   - WhatsApp de vencimento

**Exemplo de template de e-mail:**
```
Assunto: Parcela {numero_parcela}/{total_parcelas} a vencer

Olá {comprador},

Lembramos que a parcela {numero_parcela}/{total_parcelas} do contrato {contrato} vence em {vencimento}.

Valor: {valor}
Imóvel: {imovel}

Atenciosamente,
Equipe de Gestão de Contratos
```

### 4. Testar Notificações

1. Cadastre um comprador de teste
2. Crie um contrato com vencimento próximo
3. Execute via Shell:
```bash
python manage.py enviar_notificacoes
python manage.py processar_notificacoes_pendentes
```

---

## 📅 Executar Tarefas Manualmente

Como o plano gratuito não suporta workers, você deve executar as tarefas periodicamente.

### Via Render Shell

1. No Dashboard do Render, acesse seu Web Service
2. Clique em **"Shell"** no menu lateral
3. Execute os comandos:

```bash
# Processar reajustes (executar mensalmente)
python manage.py processar_reajustes

# Criar notificações de vencimento (executar semanalmente)
python manage.py enviar_notificacoes

# Processar e enviar notificações pendentes (executar diariamente)
python manage.py processar_notificacoes_pendentes
```

### Agendar com Serviço Externo (Opcional)

Use um serviço de cron externo para chamar endpoints do seu sistema:

**Serviços gratuitos:**
- https://cron-job.org (recomendado)
- https://uptimerobot.com
- https://easycron.com

**Passos:**
1. Crie endpoints públicos para executar as tarefas
2. Configure o cron para chamar os endpoints periodicamente

---

## 🔒 Segurança

### Configurações Recomendadas

1. **Alterar senha do admin** imediatamente
2. **Desabilitar DEBUG** em produção (já configurado)
3. **Usar HTTPS** (automático no Render)
4. **Não compartilhar credenciais** de e-mail e Twilio

### Backup

O PostgreSQL no Render Free Tier **não tem backup automático**. Para produção, considere:

1. **Upgrade para plano pago** (backup incluído)
2. **Backup manual** via `pg_dump`
3. **Exportar dados** periodicamente via Django Admin

---

## 💰 Upgrade para Plano Pago

Para ter todas as funcionalidades automáticas, considere upgrade:

### Render Plans

- **Starter ($7/mês)**:
  - Inclui 1 Background Worker
  - Permite Celery Worker + Beat
  - Sem sleep após inatividade

- **Standard ($25/mês)**:
  - Múltiplos workers
  - Backup automático do PostgreSQL
  - Suporte prioritário

### Após Upgrade

1. Acesse o repositório no GitHub
2. Edite `.github/workflows/render-paid.yaml` (criar)
3. Adicione os workers de volta ao `render.yaml`
4. Faça novo deploy

---

## 🐛 Troubleshooting

### Erro: "Application failed to start"

**Solução:**
1. Verifique os logs no Render Dashboard
2. Certifique-se de que `ALLOWED_HOSTS` está configurado corretamente
3. Verifique se o `build.sh` tem permissão de execução

### Erro: "Static files not found"

**Solução:**
```bash
# Via Render Shell
python manage.py collectstatic --no-input
```

### Erro: "Database connection failed"

**Solução:**
1. Verifique se `DATABASE_URL` está configurado
2. Certifique-se de que o PostgreSQL foi criado corretamente
3. Execute as migrations: `python manage.py migrate`

### Redis connection failed

**Solução:**
1. Verifique se `REDIS_URL` está configurado
2. Redis é opcional para o plano gratuito (usado apenas para cache)

---

## 📞 Suporte

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**LinkedIn:** [linkedin.com/in/maxwbh](https://www.linkedin.com/in/maxwbh/)
**GitHub:** [github.com/Maxwbh](https://github.com/Maxwbh/)

**Empresa:** M&S do Brasil LTDA
**Site:** [msbrasil.inf.br](https://msbrasil.inf.br)

---

## 📄 Links Úteis

- Documentação Render: https://render.com/docs
- Django Documentation: https://docs.djangoproject.com
- Twilio Documentation: https://www.twilio.com/docs
- API Banco Central: https://dadosabertos.bcb.gov.br

---

**Desenvolvido com ❤️ por Maxwell da Silva Oliveira**
