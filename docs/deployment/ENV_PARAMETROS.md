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
| `CREDENTIALS_ENCRYPTION_KEY` | `""` (deriva do `SECRET_KEY`) | `str` | Recomendado (produção) | Chave Fernet que cifra credenciais bancárias e o token `bapi_` do Boleto-API. Gere com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `BOLETO_API_URL` | `http://localhost:8001` | `str` | Sim (cobrança registrada) | URL do gateway Boleto-API (C6/Sicoob) |
| `BOLETO_API_TIMEOUT` | `30` | `int` | Não | Timeout das chamadas ao gateway (s) |
| `BOLETO_API_MAX_TENTATIVAS` | `3` | `int` | Não | Máximo de tentativas por chamada |
| `BOLETO_API_DELAY_INICIAL` | `2` | `int` | Não | Delay inicial de retry (s, dobra a cada tentativa) |
| `EVENT_WEBHOOK_SECRET` | `""` | `str` | **Sim (produção)** | Segredo HMAC do webhook do Boleto-API (`X-Signature`). **Fail-closed:** vazio com `DEBUG=False` ⇒ webhook responde 503 |
| `PIX_WEBHOOK_TOKEN` | `""` | `str` | **Sim (produção)** | Token Bearer do webhook PIX do PSP. **Fail-closed:** vazio com `DEBUG=False` ⇒ webhook responde 503 |
| `BI_API_TOKEN` | `""` | `str` | Não | Token Bearer da API de BI (`/financeiro/api/relatorios/posicao/`). Fail-closed: vazio em produção ⇒ 503 |
| `RELATORIO_INADIMPLENCIA_EMAILS` | `""` | CSV | Não | Destinatários do relatório agendado de inadimplência |
| `RELATORIO_POSICAO_EMAILS` | `""` | CSV | Não | Destinatários do relatório agendado de posição |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | `""` | `str` | Não | Par de chaves Web Push (portal do comprador) |
| `VAPID_CLAIMS_EMAIL` | `admin@example.com` | `str` | Não | E-mail de contato dos claims VAPID |
| `BRCOBRANCA_DELAY_MAX_429` | `8` | `int` | Não | Teto do backoff quando o BRCobrança responde 429 (s) |
| `BRCOBRANCA_HEALTH_TIMEOUT` | `90` | `int` | Não | Timeout do health-check do BRCobrança (s) |
| `BRCOBRANCA_INTER_BOLETO_DELAY_MS` | `100` | `int` | Não | Pausa entre boletos em geração em lote (ms) |
| `BRCOBRANCA_REMESSA_COOLDOWN_S` | `5` | `int` | Não | Intervalo mínimo entre gerações de remessa (s) |
| `BRCOBRANCA_TEMPO_API_BOLETO_S` | `1.8` | `float` | Não | Estimativa por boleto para a barra de progresso (s) |
| `BRCOBRANCA_TEMPLATE` | `prawn` | `str` | Não | Template de PDF do BRCobrança |
| `ANTHROPIC_API_KEY` | `""` | `str` | Não | Chave de API Anthropic para Claude. Obrigatória para importação PDF via IA, chatbot inteligente e workflows. **Env-only: não é sincronizada para o banco** (ver seção IA). Gere em [console.anthropic.com](https://console.anthropic.com) |
| `GEMINI_API_KEY` | `""` | `str` | Não | Chave de API Google Gemini (tier gratuito). Opcional — quando ausente o sistema usa diretamente a cadeia Claude. **Env-only.** Gere em [aistudio.google.com](https://aistudio.google.com) |

> **Geração de `SECRET_KEY`:**
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

> **Segurança — fail-closed:** os webhooks de cobrança (`EVENT_WEBHOOK_SECRET`,
> `PIX_WEBHOOK_TOKEN`) e a API de BI (`BI_API_TOKEN`) **dão baixa/expõem dados
> financeiros**. Com `DEBUG=False` e a chave vazia, os endpoints respondem
> **503** em vez de aceitar requisições sem autenticação. Em `DEBUG=True`
> (dev/staging) a validação é pulada.

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

### Grupo: IA e Modelos de Linguagem (`ia`)

> **Chaves de API são env-only.** `ANTHROPIC_API_KEY` e `GEMINI_API_KEY` vivem
> apenas como variáveis de ambiente e **não são sincronizadas** para
> `ParametroSistema` (o valor ficaria em texto claro no banco, visível no
> Admin). Precedência de leitura unificada (chatbot e importação de PDF):
> **env (settings) → parâmetro legado no banco → erro**. Linhas antigas de
> `ANTHROPIC_API_KEY` no banco seguem funcionando como fallback, mas o
> recomendado é migrar o valor para a env e remover a linha do Admin.

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `CHATBOT_IA_ATIVO` | bool | `True` | Liga/desliga o chatbot com IA. Quando `False`, o sistema usa apenas o despachante de regras sem nenhuma chamada de API |
| `CHATBOT_MODELO` | str | `claude-haiku-4-5-20251001` | Modelo Claude utilizado em ambos os estágios do chatbot (classificador de intent e humanizador de resposta) |
| `CHATBOT_MAX_TOKENS_POR_RESPOSTA` | int | `300` | Limite de tokens gerados por resposta do chatbot. Controla custo e comprimento das mensagens enviadas ao comprador |
| `CHATBOT_SYSTEM_PROMPT_CLASSIFIER` | str | *(prompt interno)* | System prompt completo do classificador de intent (estágio `tool_use`). O valor padrão é gerenciado pelo código; só altere para customizar o comportamento de classificação |
| `CHATBOT_SYSTEM_PROMPT` | str | *(prompt interno)* | System prompt completo do humanizador de resposta. O valor padrão é gerenciado pelo código; só altere para ajustar tom ou formato das respostas |
| `_COTACAO_USD_BRL_CACHE` | str | `""` | Cache interno da cotação USD/BRL usado para converter custos de IA. Atualizado automaticamente via AwesomeAPI ao acessar `/core/ia/cotacao/`. **Não editar manualmente** |

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
