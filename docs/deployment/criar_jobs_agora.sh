#!/usr/bin/env bash
# =============================================================================
# criar_jobs_agora.sh — Cria todos os 9 jobs no cron-job.org (tokens reais)
#
# EXECUTE NO SEU TERMINAL LOCAL (não no servidor):
#   bash docs/deployment/criar_jobs_agora.sh
#
# Requer: curl + python3 (para formatar JSON na saída)
# =============================================================================

set -euo pipefail

CRONJOB_API_KEY="DOkj9FGmkpqhjKNsOBc1SzQnaA3io5b/lnbT5wzIMLs="
TASK_TOKEN="eef+VjTogp1VTPk7Vwb7JnXBg7MErQmZkvpRRLeRISw="
APP="https://gestao-contrato-web-mt6j.onrender.com"
BRC="https://brcobranca-api-m4q9.onrender.com"
API="https://api.cron-job.org/jobs"
AUTH="Authorization: Bearer ${CRONJOB_API_KEY}"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"; NC="\033[0m"
declare -a RESULTS=()

put_job() {
  local name="$1"; local payload="$2"
  printf "${YELLOW}→ %s${NC}\n" "$name"
  resp=$(curl -s -w "\n%{http_code}" -X PUT "$API" \
    -H "$AUTH" -H "Content-Type: application/json" -d "$payload")
  code=$(printf '%s' "$resp" | tail -1)
  body=$(printf '%s' "$resp" | sed '$d')
  if [[ "$code" == "200" || "$code" == "201" ]]; then
    jid=$(printf '%s' "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('jobId','?'))" 2>/dev/null || echo "?")
    printf "${GREEN}  ✓ jobId: %s${NC}\n" "$jid"
    RESULTS+=("$name → jobId=$jid")
  else
    printf "${RED}  ✗ HTTP %s: %s${NC}\n" "$code" "$body"
    RESULTS+=("$name → ERRO HTTP $code")
  fi
}

# ---------------------------------------------------------------------------
# J-01 — Keep-Alive app (GET, cada 10 min, sem auth)
# ---------------------------------------------------------------------------
put_job "keep-alive-gestao" '{
  "job": {
    "url": "'"$APP"'/health/",
    "title": "keep-alive-gestao",
    "enabled": true,
    "saveResponses": false,
    "schedule": {
      "timezone": "UTC",
      "hours": [-1], "mdays": [-1],
      "minutes": [0,10,20,30,40,50],
      "months": [-1], "wdays": [-1]
    },
    "requestTimeout": 30,
    "requestMethod": 0
  }
}'

# ---------------------------------------------------------------------------
# J-02 — Keep-Alive BRCobrança (GET, cada 10 min, sem auth)
# ---------------------------------------------------------------------------
put_job "keep-alive-brcobranca" '{
  "job": {
    "url": "'"$BRC"'/api/health",
    "title": "keep-alive-brcobranca",
    "enabled": true,
    "saveResponses": false,
    "schedule": {
      "timezone": "UTC",
      "hours": [-1], "mdays": [-1],
      "minutes": [0,10,20,30,40,50],
      "months": [-1], "wdays": [-1]
    },
    "requestTimeout": 30,
    "requestMethod": 0
  }
}'

# ---------------------------------------------------------------------------
# J-03 — Run-all diário (POST, 08:00 BRT = 11:00 UTC)
# ---------------------------------------------------------------------------
put_job "gestao-run-all-tasks" '{
  "job": {
    "url": "'"$APP"'/api/tasks/run-all/",
    "title": "gestao-run-all-tasks",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [11], "mdays": [-1],
      "minutes": [0],
      "months": [-1], "wdays": [-1]
    },
    "requestTimeout": 120,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# J-04 — Relatório semanal (POST, segunda 07:30 BRT = 10:30 UTC)
# ---------------------------------------------------------------------------
put_job "gestao-relatorio-semanal" '{
  "job": {
    "url": "'"$APP"'/api/tasks/relatorio-semanal/",
    "title": "gestao-relatorio-semanal",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [10], "mdays": [-1],
      "minutes": [30],
      "months": [-1], "wdays": [1]
    },
    "requestTimeout": 60,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# J-05 — Relatório mensal (POST, dia 1 às 06:00 BRT = 09:00 UTC)
# ---------------------------------------------------------------------------
put_job "gestao-relatorio-mensal" '{
  "job": {
    "url": "'"$APP"'/api/tasks/relatorio-mensal/",
    "title": "gestao-relatorio-mensal",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [9], "mdays": [1],
      "minutes": [0],
      "months": [-1], "wdays": [-1]
    },
    "requestTimeout": 60,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# J-06 — Notificações dedicado (POST, cada 6h: 00:00 06:00 12:00 18:00 UTC)
# ---------------------------------------------------------------------------
put_job "gestao-notificacoes" '{
  "job": {
    "url": "'"$APP"'/api/tasks/processar-notificacoes/",
    "title": "gestao-notificacoes",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [0,6,12,18], "mdays": [-1],
      "minutes": [0],
      "months": [-1], "wdays": [-1]
    },
    "requestTimeout": 90,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# J-07 — Atualizar índices IBGE+BCB (POST, segunda 07:00 BRT = 10:00 UTC)
# ---------------------------------------------------------------------------
put_job "gestao-atualizar-indices" '{
  "job": {
    "url": "'"$APP"'/api/tasks/atualizar-indices/",
    "title": "gestao-atualizar-indices",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [10], "mdays": [-1],
      "minutes": [0],
      "months": [-1], "wdays": [1]
    },
    "requestTimeout": 120,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# J-08 — Processar bounces IMAP (POST, cada 30 min — DESATIVADO)
# Ativar após criar bounces@msbrasil.inf.br no Zoho e definir
# BOUNCE_IMAP_PASSWORD no Render.
# ---------------------------------------------------------------------------
put_job "gestao-processar-bounces" '{
  "job": {
    "url": "'"$APP"'/api/tasks/processar-bounces/",
    "title": "gestao-processar-bounces",
    "enabled": false,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [-1], "mdays": [-1],
      "minutes": [0,30],
      "months": [-1], "wdays": [-1]
    },
    "requestTimeout": 60,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# J-09 — Limpar sessões Django (POST, domingo 03:00 BRT = 06:00 UTC)
# ---------------------------------------------------------------------------
put_job "gestao-limpar-sessoes" '{
  "job": {
    "url": "'"$APP"'/api/tasks/limpar-sessoes/",
    "title": "gestao-limpar-sessoes",
    "enabled": true,
    "saveResponses": false,
    "schedule": {
      "timezone": "UTC",
      "hours": [6], "mdays": [-1],
      "minutes": [0],
      "months": [-1], "wdays": [0]
    },
    "requestTimeout": 30,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "'"$TASK_TOKEN"'"},
      {"name": "Content-Type",  "value": "application/json"}
    ]
  }
}'

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
printf "\n${GREEN}=== Resumo ===${NC}\n"
for r in "${RESULTS[@]}"; do printf "  %s\n" "$r"; done
printf "\n${YELLOW}⚠  J-08 (bounces) criado como DESATIVADO — ativar após configurar Zoho.${NC}\n"
printf "Painel: https://console.cron-job.org\n\n"
