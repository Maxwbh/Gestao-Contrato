# Parâmetros de Configuração

O sistema usa dois mecanismos distintos de configuração:

| Mecanismo | Onde editar | Quando muda |
|-----------|-------------|-------------|
| **`.env`** — Infraestrutura | Arquivo no servidor / variáveis do Render | Só na implantação (requer restart) |
| **`ParametroSistema`** — Operacional | Admin → Gestão Principal → Parâmetros do Sistema | A qualquer momento (restart para aplicar) |

---

## `.env` — Parâmetros de Infraestrutura

Apenas o que não pode estar no banco de dados (precede a conexão com o DB).

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `SECRET_KEY` | `django-insecure-...` | `str` | **Sim** (produção) | Chave secreta Django. Gere com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | `bool` | Não | Modo debug. **Nunca `True` em produção.** |
| `ALLOWED_HOSTS` | `""` | CSV | **Sim** (produção) | Hosts permitidos. Ex.: `meusite.com,www.meusite.com` |
| `DATABASE_URL` | — | `str` | **Sim** | URL PostgreSQL. Ex.: `postgresql://user:pass@host:5432/db` |
| `SUPABASE_URL` | `""` | `str` | Não | URL do projeto Supabase para acesso via cliente Python |
| `SUPABASE_KEY` | `""` | `str` | Não | Chave anônima (`anon key`) do Supabase |
| `REDIS_URL` | `redis://localhost:6379/0` | `str` | Não | URL do Redis para Celery |
| `SENTRY_DSN` | `None` | `str` | Não | DSN do Sentry. Omitir ou deixar vazio para desativar |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | CSV | Não | Origens CSRF confiáveis. Necessário atrás de proxy HTTPS |

> **Geração de `SECRET_KEY`:**
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## `ParametroSistema` — Parâmetros Operacionais

Gerenciados via **Admin → Gestão Principal → Parâmetros do Sistema**.  
Populados automaticamente na primeira execução de `migrate` com os valores do `.env` ou defaults.

A tabela abaixo documenta todos os parâmetros com seus grupos, tipos e defaults.

### Grupo: E-mail SMTP (`email`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `EMAIL_BACKEND` | str | `django.core.mail.backends.console.EmailBackend` | Backend Django. Em produção: `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | str | `localhost` | Servidor SMTP. Ex.: `smtp.zoho.com`, `smtp.gmail.com` |
| `EMAIL_PORT` | int | `587` | Porta SMTP. 587 para TLS, 465 para SSL |
| `EMAIL_USE_TLS` | bool | `True` | Ativar STARTTLS (porta 587) |
| `EMAIL_USE_SSL` | bool | `False` | Ativar SSL nativo (porta 465). Mutuamente exclusivo com TLS |
| `EMAIL_HOST_USER` | str | `""` | Usuário SMTP |
| `EMAIL_HOST_PASSWORD` | secret | `""` | Senha SMTP ou senha de aplicativo |
| `DEFAULT_FROM_EMAIL` | str | `noreply@gestaocontrato.com.br` | Endereço remetente padrão |
| `EMAIL_TIMEOUT` | int | `10` | Timeout TCP com servidor SMTP (segundos) |

> **Zoho:** `HOST=smtp.zoho.com PORT=465 USE_SSL=True USE_TLS=False`  
> **Gmail:** `HOST=smtp.gmail.com PORT=587 USE_TLS=True USE_SSL=False`

### Grupo: Twilio SMS/WhatsApp (`twilio`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `TWILIO_ACCOUNT_SID` | str | `""` | Account SID da conta Twilio |
| `TWILIO_AUTH_TOKEN` | secret | `""` | Auth Token da conta Twilio |
| `TWILIO_PHONE_NUMBER` | str | `""` | Número para SMS (E.164, ex.: `+15551234567`) |
| `TWILIO_WHATSAPP_NUMBER` | str | `""` | Número para WhatsApp (ex.: `whatsapp:+15551234567`) |
| `TWILIO_STATUS_CALLBACK_URL` | str | `""` | Webhook de status de mensagem |

### Grupo: Bounce / IMAP (`imap`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `BOUNCE_EMAIL_ADDRESS` | str | `""` | Endereço que recebe os bounces |
| `BOUNCE_IMAP_HOST` | str | `imap.zoho.com` | Servidor IMAP |
| `BOUNCE_IMAP_PORT` | int | `993` | Porta IMAP (993 = SSL) |
| `BOUNCE_IMAP_USER` | str | `""` | Usuário IMAP |
| `BOUNCE_IMAP_PASSWORD` | secret | `""` | Senha IMAP |
| `BOUNCE_IMAP_FOLDER` | str | `INBOX` | Pasta monitorada |

### Grupo: Modo de Teste (`teste`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `TEST_MODE` | bool | `False` | Redireciona todos os envios para os destinatários abaixo. **Nunca `True` em produção** |
| `TEST_RECIPIENT_EMAIL` | str | `receber@msbrasil.inf.br` | E-mail de destino em modo de teste |
| `TEST_RECIPIENT_PHONE` | str | `+5531993257479` | Telefone de destino em modo de teste (E.164) |

### Grupo: Notificações (`notificacao`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `NOTIFICACAO_DIAS_ANTECEDENCIA` | int | `5` | Dias de antecedência para notificar vencimento próximo |
| `NOTIFICACAO_DIAS_INADIMPLENCIA` | int | `3` | Dias após vencimento para alertar inadimplência |

### Grupo: Tarefas Agendadas (`tarefa`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `TASK_TOKEN` | secret | `""` | Token Bearer para `/api/tasks/run-all/`. Gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

### Grupo: BRCobrança (`brcobranca`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `BRCOBRANCA_URL` | str | `http://localhost:9292` | URL da API BRCobrança (`docker run -p 9292:9292 kivanio/brcobranca`) |
| `BRCOBRANCA_TIMEOUT` | int | `30` | Timeout para chamadas à API (segundos) |
| `BRCOBRANCA_MAX_TENTATIVAS` | int | `3` | Máximo de tentativas em caso de falha |
| `BRCOBRANCA_DELAY_INICIAL` | int | `2` | Delay inicial de retry em segundos (dobra a cada tentativa) |

### Grupo: Portal do Comprador (`portal`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `PORTAL_EMAIL_VERIFICACAO` | bool | `False` | `True` = exige confirmação de e-mail após cadastro |

### Grupo: Aplicação (`aplicacao`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `SITE_URL` | str | `http://localhost:8000` | URL pública sem barra final. Usada em links de e-mails |

### Grupo: APIs BCB (`bcb`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `BCBAPI_URL` | str | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados` | URL template da API de séries temporais do BCB |
| `IPCA_SERIE_ID` | str | `433` | Código da série IPCA |
| `IGPM_SERIE_ID` | str | `189` | Código da série IGP-M |
| `SELIC_SERIE_ID` | str | `432` | Código da série SELIC |

---

## Como funciona em produção

```
Startup:
  settings.py       → define defaults (hardcoded)
  CoreConfig.ready() → lê ParametroSistema → sobrescreve settings.*
  Cache (5 min)     → evita queries repetidas

Request:
  get_param('CHAVE')  → DB (cache) → settings.* → default
  settings.EMAIL_HOST → já foi sobrescrito pelo ready()

Mudança de config:
  1. Admin → Parâmetros do Sistema → editar valor
  2. Reiniciar a aplicação (Render: Manual Deploy ou restart)
```

---

## Migração inicial

Na primeira execução de `python manage.py migrate`, a migration
`0008_data_parametro_sistema` lê os valores atuais do `.env` (via
`decouple.config()`) e os insere na tabela `ParametroSistema`.

Após a migração, os valores do `.env` para parâmetros operacionais
podem ser removidos — eles serão lidos do banco de dados.
