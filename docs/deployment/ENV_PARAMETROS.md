# Parâmetros de Ambiente (.env)

Referência completa de todas as variáveis de ambiente utilizadas pelo projeto.
Copie `.env.example` para `.env` e ajuste os valores conforme o ambiente.

---

## Django — Core

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `SECRET_KEY` | `django-insecure-dev-key-change-in-production` | `str` | **Sim** (produção) | Chave secreta do Django. Gere com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | `bool` | Não | Ativa modo debug. **Nunca `True` em produção.** |
| `ALLOWED_HOSTS` | `""` | `str` (CSV) | **Sim** (produção) | Hosts permitidos, separados por vírgula. Ex.: `meusite.com,www.meusite.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | `str` (CSV) | Não | Origens confiáveis para CSRF (HTTPS). Necessário atrás de proxy reverso. Só aplicado quando `DEBUG=False`. |

---

## Banco de Dados

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `DATABASE_URL` | — | `str` | **Sim** | URL de conexão PostgreSQL. Ex.: `postgresql://user:pass@host:5432/dbname`. Sem esta variável, usa SQLite local. |
| `SUPABASE_URL` | `""` | `str` | Não | URL do projeto Supabase. Ex.: `https://xyz.supabase.co`. Usado para funcionalidades adicionais via cliente Supabase. |
| `SUPABASE_KEY` | `""` | `str` | Não | Chave anônima (`anon key`) do Supabase. |

---

## Redis / Celery

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `REDIS_URL` | `redis://localhost:6379/0` | `str` | Não | URL do Redis. Usado como broker e backend do Celery. |

---

## E-mail (SMTP)

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | `str` | Não | Backend de e-mail. Em produção use `django.core.mail.backends.smtp.EmailBackend`. |
| `EMAIL_HOST` | `localhost` | `str` | Não | Servidor SMTP. Ex.: `smtp.zoho.com`, `smtp.gmail.com` |
| `EMAIL_PORT` | `587` | `int` | Não | Porta SMTP. Use `465` para SSL, `587` para TLS. |
| `EMAIL_USE_TLS` | `True` | `bool` | Não | Ativa STARTTLS. Use `True` para porta 587. |
| `EMAIL_USE_SSL` | `False` | `bool` | Não | Ativa SSL nativo. Use `True` para porta 465. **Mutuamente exclusivo com `EMAIL_USE_TLS`.** |
| `EMAIL_HOST_USER` | `""` | `str` | Não | Usuário SMTP (geralmente o e-mail remetente). |
| `EMAIL_HOST_PASSWORD` | `""` | `str` | Não | Senha do SMTP ou senha de aplicativo. |
| `DEFAULT_FROM_EMAIL` | `noreply@gestaocontrato.com.br` | `str` | Não | Endereço remetente padrão para todos os e-mails do sistema. |
| `EMAIL_TIMEOUT` | `10` | `int` | Não | Timeout de conexão TCP com o servidor SMTP (segundos). Evita bloquear requisições. |

> **Zoho**: `HOST=smtp.zoho.com PORT=465 USE_SSL=True USE_TLS=False`  
> **Gmail**: `HOST=smtp.gmail.com PORT=587 USE_TLS=True USE_SSL=False`

---

## Twilio — SMS e WhatsApp

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `TWILIO_ACCOUNT_SID` | `""` | `str` | Não | Account SID da conta Twilio. |
| `TWILIO_AUTH_TOKEN` | `""` | `str` | Não | Auth Token da conta Twilio. |
| `TWILIO_PHONE_NUMBER` | `""` | `str` | Não | Número Twilio para SMS. Formato E.164: `+15551234567` |
| `TWILIO_WHATSAPP_NUMBER` | `""` | `str` | Não | Número Twilio para WhatsApp. Formato: `whatsapp:+15551234567` |
| `TWILIO_STATUS_CALLBACK_URL` | `""` | `str` | Não | URL de webhook para callbacks de status de mensagem Twilio. |

---

## Bounce / IMAP

Processamento automático de e-mails devolvidos (bounces).

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `BOUNCE_EMAIL_ADDRESS` | `""` | `str` | Não | Endereço de e-mail que recebe os bounces. |
| `BOUNCE_IMAP_HOST` | `imap.zoho.com` | `str` | Não | Servidor IMAP para leitura de bounces. |
| `BOUNCE_IMAP_PORT` | `993` | `int` | Não | Porta IMAP (993 = SSL). |
| `BOUNCE_IMAP_USER` | `""` | `str` | Não | Usuário IMAP. |
| `BOUNCE_IMAP_PASSWORD` | `""` | `str` | Não | Senha IMAP. |
| `BOUNCE_IMAP_FOLDER` | `INBOX` | `str` | Não | Pasta IMAP a ser monitorada. |

---

## Modo de Teste

Redireciona **todos** os envios (e-mail e SMS/WhatsApp) para endereços de teste. Útil em homologação para evitar envios reais.

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `TEST_MODE` | `False` | `bool` | Não | Quando `True`, redireciona todos os envios para os destinatários de teste abaixo. **Nunca usar em produção.** |
| `TEST_RECIPIENT_EMAIL` | `receber@msbrasil.inf.br` | `str` | Não | E-mail de destino em modo de teste. |
| `TEST_RECIPIENT_PHONE` | `+5531993257479` | `str` | Não | Telefone de destino em modo de teste (E.164). |

---

## Notificações

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `NOTIFICACAO_DIAS_ANTECEDENCIA` | `5` | `int` | Não | Dias de antecedência para enviar notificação de vencimento próximo. |
| `NOTIFICACAO_DIAS_INADIMPLENCIA` | `3` | `int` | Não | Dias após vencimento para enviar alerta de inadimplência. |

---

## Tarefas Agendadas

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `TASK_TOKEN` | `None` | `str` | Não | Token Bearer para autenticar chamadas à API `/api/tasks/run-all/`. Gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Sem este token, o endpoint é desativado. |

---

## BRCobrança — Boletos

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `BRCOBRANCA_URL` | `http://localhost:9292` | `str` | Não | URL base da API BRCobrança. Execute com Docker: `docker run -p 9292:9292 kivanio/brcobranca` |
| `BRCOBRANCA_TIMEOUT` | `30` | `int` | Não | Timeout para chamadas à API BRCobrança (segundos). |

---

## Portal do Comprador

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `PORTAL_EMAIL_VERIFICACAO` | `False` | `bool` | Não | Quando `True`, exige confirmação de e-mail após cadastro no portal. O comprador recebe um link de verificação e fica com acesso restrito até confirmar. Quando `False` (padrão), o acesso é liberado imediatamente. |

---

## Aplicação

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `SITE_URL` | `http://localhost:8000` | `str` | Não | URL pública do site, sem barra final. Usada para gerar links absolutos em e-mails e notificações. Em produção: `https://meusite.com.br` |

---

## Monitoramento

| Variável | Padrão | Tipo | Obrigatório | Descrição |
|----------|--------|------|-------------|-----------|
| `SENTRY_DSN` | `None` | `str` | Não | DSN do Sentry para rastreamento de erros em produção. Se vazio ou ausente, o Sentry não é inicializado. |

---

## APIs BCB (Banco Central do Brasil)

> Estas constantes são **hardcoded** no `settings.py` e **não são configuráveis via `.env`**. Listadas aqui apenas para referência.

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `BCBAPI_URL` | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados` | URL template da API de séries temporais do BCB. |
| `IPCA_SERIE_ID` | `433` | Código da série IPCA no BCB. |
| `IGPM_SERIE_ID` | `189` | Código da série IGP-M no BCB. |
| `SELIC_SERIE_ID` | `432` | Código da série SELIC no BCB. |

---

## Configuração por Ambiente

| Variável | Desenvolvimento | Homologação | Produção |
|----------|----------------|-------------|----------|
| `DEBUG` | `True` | `False` | `False` |
| `DATABASE_URL` | SQLite (omitir) | Supabase staging | Supabase produção |
| `EMAIL_BACKEND` | `console` | `smtp` | `smtp` |
| `TEST_MODE` | `True` | `True` | `False` |
| `BRCOBRANCA_URL` | `http://localhost:9292` | URL do Docker | URL do Docker |
| `PORTAL_EMAIL_VERIFICACAO` | `False` | `True` | `True` |
| `SENTRY_DSN` | omitir | opcional | recomendado |
| `TASK_TOKEN` | omitir | token seguro | token seguro |

---

## Geração de Valores Seguros

```bash
# SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# TASK_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
