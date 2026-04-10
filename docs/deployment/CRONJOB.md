# Configuração de Tarefas Agendadas — cron-job.org

**Sistema:** Gestão de Contratos — M&S do Brasil LTDA  
**Desenvolvedor:** Maxwell da Silva Oliveira  
**Última atualização:** 2026-04-10

> O Render Free Tier não oferece Background Workers (Celery). Todas as tarefas
> agendadas são executadas via HTTP POST por cron externo.
> Serviço recomendado: **[cron-job.org](https://cron-job.org)** (gratuito, sem limite de jobs).

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Como obter o TASK_TOKEN](#2-como-obter-o-task_token)
3. [Jobs obrigatórios](#3-jobs-obrigatórios)
4. [Jobs complementares](#4-jobs-complementares)
5. [Jobs de rastreamento de mensagens](#5-jobs-de-rastreamento-de-mensagens)
6. [Configuração passo a passo no cron-job.org](#6-configuração-passo-a-passo-no-cron-joborg)
7. [Referência de todos os endpoints](#7-referência-de-todos-os-endpoints)
8. [Monitoramento e alertas](#8-monitoramento-e-alertas)
9. [Variáveis de ambiente relacionadas](#9-variáveis-de-ambiente-relacionadas)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Pré-requisitos

| Item | Descrição |
|------|-----------|
| Conta cron-job.org | Gratuita — [cron-job.org/en/signup](https://cron-job.org/en/signup) |
| App no Render | Deploy realizado com sucesso |
| TASK_TOKEN | Copiado do painel do Render após o deploy |
| BOUNCE_IMAP_PASSWORD | Definido manualmente no Render (para bounce monitoring) |

**URL base do app:**
```
https://gestao-contrato-web-mt6j.onrender.com
```

---

## 2. Como obter o TASK_TOKEN

1. Acesse o [Dashboard do Render](https://dashboard.render.com)
2. Selecione o serviço **gestao-contrato-web**
3. Vá em **Environment → Environment Variables**
4. Copie o valor de **`TASK_TOKEN`** (gerado automaticamente no deploy)

> ⚠️ Nunca exponha o `TASK_TOKEN` publicamente. Trate como senha.

Para verificar se o token está funcionando:
```bash
curl -s -X POST \
  https://gestao-contrato-web-mt6j.onrender.com/api/tasks/status/ \
  -H "X-Task-Token: SEU_TOKEN_AQUI"
```

---

## 3. Jobs Obrigatórios

### Job 1 — Keep-Alive (prevenir hibernação)

O Render Free Tier hiberna serviços após **15 minutos** sem requisições.

| Campo | Valor |
|-------|-------|
| **Nome** | `keep-alive-gestao` |
| **URL** | `https://gestao-contrato-web-mt6j.onrender.com/health/` |
| **Método** | `GET` |
| **Intervalo** | A cada **10 minutos** |
| **Autenticação** | Nenhuma |
| **Timeout** | 30 segundos |

**Resposta esperada (HTTP 200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-10T08:00:00Z",
  "checks": {
    "database": {"status": "healthy", "latency_ms": 2.5},
    "cache":    {"status": "healthy", "latency_ms": 1.3}
  }
}
```

---

### Job 2 — Keep-Alive BRCobrança

| Campo | Valor |
|-------|-------|
| **Nome** | `keep-alive-brcobranca` |
| **URL** | `https://brcobranca-api-m4q9.onrender.com/api/health` |
| **Método** | `GET` |
| **Intervalo** | A cada **10 minutos** |
| **Autenticação** | Nenhuma |
| **Timeout** | 30 segundos |

---

### Job 3 — Tarefas Diárias (Orquestrador Principal)

Executa **todas** as tarefas em sequência: atualiza status de parcelas,
processa reajustes, envia notificações de vencimento e inadimplência.

| Campo | Valor |
|-------|-------|
| **Nome** | `gestao-run-all-tasks` |
| **URL** | `https://gestao-contrato-web-mt6j.onrender.com/api/tasks/run-all/` |
| **Método** | `POST` |
| **Horário** | Todo dia às **08:00** (fuso America/Sao_Paulo) |
| **Header** | `X-Task-Token: <SEU_TOKEN>` |
| **Timeout** | 120 segundos |

**Resposta esperada (HTTP 200 ou 207):**
```json
{
  "status": "success",
  "executed_at": "2026-04-10T11:00:00Z",
  "tasks": [
    {"task": "atualizar_status_parcelas", "success": true, "duration_seconds": 1.2},
    {"task": "processar_reajustes",       "success": true, "duration_seconds": 0.8},
    {"task": "processar_fila_notificacoes","success": true,"duration_seconds": 3.1},
    {"task": "enviar_notificacoes",        "success": true, "duration_seconds": 2.4},
    {"task": "enviar_inadimplentes",       "success": true, "duration_seconds": 1.9}
  ]
}
```

> **Nota:** HTTP 207 (Multi-Status) indica sucesso parcial — alguma tarefa falhou,
> mas as demais foram executadas. Verificar o log de cada `task`.

---

## 4. Jobs Complementares

### Job 4 — Relatório Semanal (Imobiliárias)

Envia e-mail de resumo semanal para cada imobiliária: recebimentos da semana,
inadimplência atual e parcelas vencendo em 7 dias.

| Campo | Valor |
|-------|-------|
| **Nome** | `gestao-relatorio-semanal` |
| **URL** | `https://gestao-contrato-web-mt6j.onrender.com/api/tasks/relatorio-semanal/` |
| **Método** | `POST` |
| **Horário** | Toda **segunda-feira às 07:00** |
| **Header** | `X-Task-Token: <SEU_TOKEN>` |
| **Timeout** | 60 segundos |

---

### Job 5 — Relatório Mensal (Consolidado)

Envia e-mail consolidado para cada contabilidade com totais por imobiliária.
Executa automaticamente no 1º dia útil do mês.

| Campo | Valor |
|-------|-------|
| **Nome** | `gestao-relatorio-mensal` |
| **URL** | `https://gestao-contrato-web-mt6j.onrender.com/api/tasks/relatorio-mensal/` |
| **Método** | `POST` |
| **Horário** | Todo **dia 1 do mês às 06:00** |
| **Header** | `X-Task-Token: <SEU_TOKEN>` |
| **Timeout** | 60 segundos |

---

### Job 6 — Somente Notificações (backup opcional)

Útil para reenviar notificações que falharam fora do ciclo diário principal.

| Campo | Valor |
|-------|-------|
| **Nome** | `gestao-fila-notificacoes` |
| **URL** | `https://gestao-contrato-web-mt6j.onrender.com/api/tasks/processar-fila/` |
| **Método** | `POST` |
| **Horário** | A cada **4 horas** (06:00, 10:00, 14:00, 18:00, 22:00) |
| **Header** | `X-Task-Token: <SEU_TOKEN>` |
| **Timeout** | 90 segundos |

> **Opcional** — se o Job 3 (run-all) estiver funcionando corretamente,
> este job não é necessário.

---

## 5. Jobs de Rastreamento de Mensagens

### Job 7 — Processamento de Bounces IMAP

Lê a caixa de e-mail `bounces@msbrasil.inf.br` via IMAP, detecta NDR/DSN
(e-mails não entregues) e atualiza `status_entrega = 'bounced'` no banco.

> **Pré-requisito:** Criar a caixa `bounces@msbrasil.inf.br` no Zoho Mail
> e definir `BOUNCE_IMAP_PASSWORD` no Render antes de ativar este job.

| Campo | Valor |
|-------|-------|
| **Nome** | `gestao-processar-bounces` |
| **URL** | `https://gestao-contrato-web-mt6j.onrender.com/api/tasks/processar-bounces/` |
| **Método** | `POST` |
| **Horário** | A cada **30 minutos** |
| **Header** | `X-Task-Token: <SEU_TOKEN>` |
| **Timeout** | 60 segundos |

> **Status:** Este endpoint ainda precisa ser implementado (ver [ROADMAP — Item 17.3](#)).
> Alternativa temporária: chamar manualmente via
> `python manage.py processar_bounces` no shell do Render.

---

## 6. Configuração Passo a Passo no cron-job.org

### 6.1 Criar conta e acessar o dashboard

1. Acesse [cron-job.org/en/signup](https://cron-job.org/en/signup)
2. Confirme o e-mail
3. Faça login e acesse **"Cron jobs"** no menu principal

### 6.2 Criar um novo job (exemplo: Keep-Alive)

1. Clique em **"Create cronjob"**
2. Preencha:

```
Title:     keep-alive-gestao
URL:       https://gestao-contrato-web-mt6j.onrender.com/health/
Schedule:  Every 10 minutes (selecione Minutes → Every: 10)
```

3. Em **"Advanced"** → **"Headers"** (para jobs com autenticação):
   - Clique em **"Add header"**
   - Key: `X-Task-Token`
   - Value: `<cole seu token aqui>`

4. Clique em **"Create"**

### 6.3 Configurar o fuso horário

No cron-job.org, o horário padrão é UTC. Para usar horário de Brasília (UTC-3):

- Nas configurações do job: **"Timezone"** → selecione `America/Sao_Paulo`
- Ou ajuste manualmente: Job 3 às 08:00 BRT = **11:00 UTC**

### 6.4 Tabela de horários (horário de Brasília / UTC)

| Job | BRT (Brasília) | UTC |
|-----|----------------|-----|
| Keep-Alive app | Cada 10 min | Cada 10 min |
| Keep-Alive BRCobrança | Cada 10 min | Cada 10 min |
| Run-all diário | 08:00 | 11:00 |
| Relatório semanal | Segunda 07:00 | Segunda 10:00 |
| Relatório mensal | Dia 1 às 06:00 | Dia 1 às 09:00 |
| Processar bounces | Cada 30 min | Cada 30 min |

---

## 7. Referência de Todos os Endpoints

### Endpoints de Tarefas

Todos requerem header `X-Task-Token` e método `POST`.

| Endpoint | Descrição | Frequência sugerida |
|----------|-----------|---------------------|
| `/api/tasks/run-all/` | Executa todas as tarefas em sequência | Diário 08:00 |
| `/api/tasks/atualizar-parcelas/` | Atualiza status de parcelas vencidas | — (incluso no run-all) |
| `/api/tasks/processar-reajustes/` | Processa reajustes IPCA/IGP-M/SELIC pendentes | — (incluso no run-all) |
| `/api/tasks/enviar-notificacoes/` | Envia notificações de vencimento | — (incluso no run-all) |
| `/api/tasks/enviar-inadimplentes/` | Envia notificações de inadimplência | — (incluso no run-all) |
| `/api/tasks/processar-fila/` | Processa fila PENDENTE de notificações | A cada 4h (opcional) |
| `/api/tasks/relatorio-semanal/` | Relatório semanal por imobiliária | Segunda 07:00 |
| `/api/tasks/relatorio-mensal/` | Relatório mensal consolidado | Dia 1 às 06:00 |
| `/api/tasks/testar-notificacoes/` | Diagnóstico de notificações (dev) | Sob demanda |
| `/api/tasks/processar-bounces/` | Bounce monitoring IMAP *(pendente)* | A cada 30 min |

### Endpoint de Saúde

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/health/` | GET | Nenhuma | Health check + keep-alive |

### Endpoints de Webhook (recebem dados externos)

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/notificacoes/webhook/twilio/` | POST | Assinatura Twilio | Confirmação de entrega SMS/WhatsApp |
| `/notificacoes/track/<uuid>/click/` | GET | Nenhuma | Rastreamento de clique em e-mail |

### Endpoint de Status (diagnóstico)

```bash
# Listar todas as tarefas disponíveis (sem autenticação)
curl https://gestao-contrato-web-mt6j.onrender.com/api/tasks/status/
```

---

## 8. Monitoramento e Alertas

### 8.1 Alertas no cron-job.org

Em cada job, acesse **"Notifications"** e configure:

- ✅ **Alert on failure** — e-mail quando o job retornar erro (non-2xx)
- ✅ **Alert on timeout** — e-mail quando o job demorar mais que o timeout configurado
- Destinatário: `receber@msbrasil.inf.br` (ou `maxwbh@gmail.com`)

### 8.2 Verificar execuções

No cron-job.org, cada job exibe:

- **Last execution** — timestamp da última execução
- **Last status** — HTTP status da resposta
- **History** — log das últimas 25 execuções
- **Response body** — JSON retornado pelo servidor

### 8.3 Interpretar respostas

| HTTP Status | Significado | Ação |
|-------------|-------------|------|
| `200 OK` | Todas as tarefas concluíram com sucesso | Nenhuma |
| `207 Multi-Status` | Sucesso parcial — alguma tarefa falhou | Verificar JSON `tasks[].errors` |
| `401 Unauthorized` | Token inválido ou expirado | Verificar `TASK_TOKEN` no Render |
| `429 Too Many Requests` | Rate limit atingido (30 req/min) | Aumentar intervalo entre jobs |
| `503 Service Unavailable` | App hibernado ou em deploy | Aguardar e verificar keep-alive |

### 8.4 Painel interno

Acesse o painel de mensagens do sistema:
```
https://gestao-contrato-web-mt6j.onrender.com/notificacoes/painel/
```

Mostra histórico completo de envios com status de entrega (Twilio) e
rastreamento de cliques (e-mail).

---

## 9. Variáveis de Ambiente Relacionadas

Configurar no painel **Render → Environment Variables**:

### Já configuradas (render.yaml)

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `TASK_TOKEN` | *(gerado automaticamente)* | Token de autenticação das tasks |
| `SITE_URL` | `https://gestao-contrato-web-mt6j.onrender.com` | URL base para links de e-mail |
| `BRCOBRANCA_URL` | `https://brcobranca-api-m4q9.onrender.com` | URL da API de boletos |
| `BOUNCE_EMAIL_ADDRESS` | `bounces@msbrasil.inf.br` | Return-Path dos e-mails enviados |
| `BOUNCE_IMAP_HOST` | `imap.zoho.com` | Servidor IMAP para bounce monitoring |
| `BOUNCE_IMAP_PORT` | `993` | Porta IMAP SSL |
| `BOUNCE_IMAP_USER` | `bounces@msbrasil.inf.br` | Usuário IMAP |
| `BOUNCE_IMAP_FOLDER` | `INBOX` | Pasta monitorada |
| `TWILIO_STATUS_CALLBACK_URL` | `https://...onrender.com/notificacoes/webhook/twilio/` | Callback Twilio para status SMS/WhatsApp |

### Definir manualmente no Render (secrets)

| Variável | Onde obter | Descrição |
|----------|-----------|-----------|
| `EMAIL_HOST_PASSWORD` | Painel Zoho Mail | Senha SMTP Zoho |
| `BOUNCE_IMAP_PASSWORD` | Painel Zoho Mail | Senha IMAP da caixa de bounces |
| `TWILIO_ACCOUNT_SID` | Console Twilio | Account SID |
| `TWILIO_AUTH_TOKEN` | Console Twilio | Auth Token |

---

## 10. Troubleshooting

### Serviço não responde (timeout)

O Render Free Tier pode demorar até **30 segundos** para "acordar" após
hibernação. Se o keep-alive estiver configurado corretamente (Job 1 e 2),
isso não deveria acontecer no horário de uso.

**Verificar:**
1. Job 1 (keep-alive) está ativo e executando a cada 10 min?
2. Acessar manualmente: `https://gestao-contrato-web-mt6j.onrender.com/health/`

### HTTP 401 — Token inválido

```bash
# Verificar se o token está correto
curl -v -X POST \
  https://gestao-contrato-web-mt6j.onrender.com/api/tasks/status/ \
  -H "X-Task-Token: SEU_TOKEN"
```

Se retornar 401, copie o `TASK_TOKEN` novamente do painel do Render
(pode ter sido re-gerado num redeploy).

### HTTP 429 — Rate limit

Os endpoints de tarefa aceitam **30 requisições por minuto** por IP.
O cron-job.org usa IPs fixos — se múltiplos jobs executarem ao mesmo tempo,
pode atingir o limite.

**Solução:** Distribuir os horários dos jobs (ex: run-all às 08:00, relatorio-semanal às 07:50).

### Notificações não são enviadas

1. Verificar `TEST_MODE=True` — em modo de teste, e-mails vão para `TEST_RECIPIENT_EMAIL`
2. Verificar se há notificações `PENDENTE` no painel: `/notificacoes/painel/`
3. Executar manualmente: `POST /api/tasks/processar-fila/`
4. Verificar logs do Render: **Dashboard → gestao-contrato-web → Logs**

### Bounces não são detectados

1. Confirmar que `BOUNCE_IMAP_PASSWORD` está definido no Render
2. Confirmar que a caixa `bounces@msbrasil.inf.br` existe no Zoho
3. Testar manualmente via Render Shell (se disponível):
   ```bash
   python manage.py processar_bounces --dry-run
   ```
4. Verificar se o Zoho está enviando NDRs para `bounces@` (Return-Path configurado)

### Job 3 (run-all) retorna 207 parcialmente

Inspecionar a resposta JSON para identificar qual tarefa falhou:

```json
{
  "status": "partial_failure",
  "tasks": [
    {"task": "enviar_notificacoes", "success": false, "errors": ["Twilio: Account not configured"]}
  ]
}
```

Ação: verificar as credenciais Twilio no Render (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`).

---

## Resumo — Checklist de Configuração

### Imediato (obrigatório)

- [ ] Criar conta em cron-job.org
- [ ] Copiar `TASK_TOKEN` do painel do Render
- [ ] **Job 1:** Keep-alive app (a cada 10 min, GET `/health/`)
- [ ] **Job 2:** Keep-alive BRCobrança (a cada 10 min, GET `/api/health`)
- [ ] **Job 3:** Run-all diário (08:00 BRT, POST `/api/tasks/run-all/`)

### Complementar (recomendado)

- [ ] **Job 4:** Relatório semanal (segunda 07:00, POST `/api/tasks/relatorio-semanal/`)
- [ ] **Job 5:** Relatório mensal (dia 1 às 06:00, POST `/api/tasks/relatorio-mensal/`)
- [ ] Configurar alertas de falha por e-mail no cron-job.org

### Rastreamento de Mensagens (após criar caixa de bounces)

- [ ] Criar caixa `bounces@msbrasil.inf.br` no Zoho Mail
- [ ] Definir `BOUNCE_IMAP_PASSWORD` no Render
- [ ] Aguardar implementação do endpoint `/api/tasks/processar-bounces/`
- [ ] **Job 7:** Processar bounces (a cada 30 min, POST `/api/tasks/processar-bounces/`)

### Twilio Delivery Callbacks (SMS/WhatsApp)

- [ ] Confirmar que `TWILIO_STATUS_CALLBACK_URL` está definido no Render
- [ ] No Console Twilio → Messaging → Settings → definir Status Callback URL
- [ ] Verificar recebimento de callbacks no painel: `/notificacoes/painel/`
