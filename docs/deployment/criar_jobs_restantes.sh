#!/usr/bin/env bash
# =============================================================================
# criar_jobs_restantes.sh — Cria os 4 jobs que falharam com 429
# J-06 gestao-notificacoes
# J-07 gestao-atualizar-indices
# J-08 gestao-processar-bounces  (desativado)
# J-09 gestao-limpar-sessoes
#
# Execute: bash docs/deployment/criar_jobs_restantes.sh
# =============================================================================

set -euo pipefail

CRONJOB_API_KEY="DOkj9FGmkpqhjKNsOBc1SzQnaA3io5b/lnbT5wzIMLs="
TASK_TOKEN="eef+VjTogp1VTPk7Vwb7JnXBg7MErQmZkvpRRLeRISw="
APP="https://gestao-contrato-web-mt6j.onrender.com"
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
    jid=$(printf '%s' "$body" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('jobId','?'))" 2>/dev/null || echo "?")
    printf "${GREEN}  ✓ jobId: %s${NC}\n" "$jid"
    RESULTS+=("$name → jobId=$jid")
  else
    printf "${RED}  ✗ HTTP %s: %s${NC}\n" "$code" "$body"
    RESULTS+=("$name → ERRO HTTP $code")
  fi
  sleep 8   # evitar rate limit (429)
}

# ---------------------------------------------------------------------------
# J-06 — Notificações dedicado (cada 6h: 00:00 06:00 12:00 18:00 UTC)
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
# J-07 — Atualizar índices IBGE+BCB (segunda 07:00 BRT = 10:00 UTC)
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
# J-08 — Processar bounces IMAP (cada 30 min — DESATIVADO até configurar Zoho)
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
# J-09 — Limpar sessões Django (domingo 03:00 BRT = 06:00 UTC)
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
printf "\n${YELLOW}Jobs criados anteriormente:${NC}\n"
printf "  keep-alive-gestao      → jobId=7500620\n"
printf "  keep-alive-brcobranca  → jobId=7500621\n"
printf "  gestao-run-all-tasks   → jobId=7500622\n"
printf "  gestao-relatorio-semanal → jobId=7500623\n"
printf "  gestao-relatorio-mensal  → jobId=7500624\n"
printf "\nPainel: https://console.cron-job.org\n\n"
