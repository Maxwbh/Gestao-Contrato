#!/usr/bin/env bash
# =============================================================================
# setup_cronjobs.sh — Criação automática de todos os jobs no cron-job.org
#
# Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
# Última atualização: 2026-04-18
#
# USO:
#   export CRONJOB_API_KEY="DOkj9FGmkpqhjKNsOBc1SzQnaA3io5b/lnbT5wzIMLs="
#   export TASK_TOKEN="<copie do painel Render → Environment Variables>"
#   bash setup_cronjobs.sh
#
# Ou passando inline:
#   CRONJOB_API_KEY="..." TASK_TOKEN="..." bash setup_cronjobs.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
API_BASE="https://api.cron-job.org"
APP_URL="https://gestao-contrato-web-mt6j.onrender.com"
BRCOBRANCA_URL="https://brcobranca-api-m4q9.onrender.com"

CRONJOB_API_KEY="${CRONJOB_API_KEY:?Defina a variável CRONJOB_API_KEY}"
TASK_TOKEN="${TASK_TOKEN:?Defina a variável TASK_TOKEN (painel Render)}"

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

created_ids=()

# ---------------------------------------------------------------------------
# Função auxiliar
# ---------------------------------------------------------------------------
create_job() {
  local name="$1"
  local payload="$2"

  echo -e "${YELLOW}Criando job: ${name}...${NC}"

  response=$(curl -s -w "\n%{http_code}" \
    -X PUT "${API_BASE}/jobs" \
    -H "Authorization: Bearer ${CRONJOB_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${payload}")

  http_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | sed '$d')

  if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
    job_id=$(echo "$body" | grep -o '"jobId":[0-9]*' | grep -o '[0-9]*')
    echo -e "${GREEN}  ✓ Criado — jobId: ${job_id}${NC}"
    created_ids+=("${name}: ${job_id}")
  else
    echo -e "${RED}  ✗ Erro HTTP ${http_code}: ${body}${NC}"
  fi
}

# ---------------------------------------------------------------------------
# J-01 — Keep-Alive app principal (GET, cada 10 min, sem auth)
# ---------------------------------------------------------------------------
create_job "keep-alive-gestao" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/health/",
    "title": "keep-alive-gestao",
    "enabled": true,
    "saveResponses": false,
    "schedule": {
      "timezone": "UTC",
      "hours": [-1],
      "mdays": [-1],
      "minutes": [0,10,20,30,40,50],
      "months": [-1],
      "wdays": [-1]
    },
    "requestTimeout": 30,
    "requestMethod": 0
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-02 — Keep-Alive BRCobrança (GET, cada 10 min, sem auth)
# ---------------------------------------------------------------------------
create_job "keep-alive-brcobranca" "$(cat <<EOF
{
  "job": {
    "url": "${BRCOBRANCA_URL}/api/health",
    "title": "keep-alive-brcobranca",
    "enabled": true,
    "saveResponses": false,
    "schedule": {
      "timezone": "UTC",
      "hours": [-1],
      "mdays": [-1],
      "minutes": [0,10,20,30,40,50],
      "months": [-1],
      "wdays": [-1]
    },
    "requestTimeout": 30,
    "requestMethod": 0
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-03 — Run-all diário (POST, 08:00 BRT = 11:00 UTC, todo dia)
# ---------------------------------------------------------------------------
create_job "gestao-run-all-tasks" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/run-all/",
    "title": "gestao-run-all-tasks",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [11],
      "mdays": [-1],
      "minutes": [0],
      "months": [-1],
      "wdays": [-1]
    },
    "requestTimeout": 120,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-04 — Relatório semanal (POST, segunda 07:30 BRT = segunda 10:30 UTC)
# ---------------------------------------------------------------------------
create_job "gestao-relatorio-semanal" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/relatorio-semanal/",
    "title": "gestao-relatorio-semanal",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [10],
      "mdays": [-1],
      "minutes": [30],
      "months": [-1],
      "wdays": [1]
    },
    "requestTimeout": 60,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-05 — Relatório mensal (POST, dia 1 às 06:00 BRT = 09:00 UTC)
# ---------------------------------------------------------------------------
create_job "gestao-relatorio-mensal" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/relatorio-mensal/",
    "title": "gestao-relatorio-mensal",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [9],
      "mdays": [1],
      "minutes": [0],
      "months": [-1],
      "wdays": [-1]
    },
    "requestTimeout": 60,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-06 — Notificações dedicado (POST, cada 6 horas: 00:00, 06:00, 12:00, 18:00 UTC)
# ---------------------------------------------------------------------------
create_job "gestao-notificacoes" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/processar-notificacoes/",
    "title": "gestao-notificacoes",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [0,6,12,18],
      "mdays": [-1],
      "minutes": [0],
      "months": [-1],
      "wdays": [-1]
    },
    "requestTimeout": 90,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-07 — Atualizar índices econômicos (POST, segunda 07:00 BRT = 10:00 UTC)
# ---------------------------------------------------------------------------
create_job "gestao-atualizar-indices" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/atualizar-indices/",
    "title": "gestao-atualizar-indices",
    "enabled": true,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [10],
      "mdays": [-1],
      "minutes": [0],
      "months": [-1],
      "wdays": [1]
    },
    "requestTimeout": 120,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# J-08 — Processar bounces IMAP (POST, cada 30 min)
# ---------------------------------------------------------------------------
create_job "gestao-processar-bounces" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/processar-bounces/",
    "title": "gestao-processar-bounces",
    "enabled": false,
    "saveResponses": true,
    "schedule": {
      "timezone": "UTC",
      "hours": [-1],
      "mdays": [-1],
      "minutes": [0,30],
      "months": [-1],
      "wdays": [-1]
    },
    "requestTimeout": 60,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"
# Nota: enabled=false — ativar após criar caixa bounces@msbrasil.inf.br no Zoho

# ---------------------------------------------------------------------------
# J-09 — Limpar sessões Django (POST, domingo 03:00 BRT = 06:00 UTC)
# ---------------------------------------------------------------------------
create_job "gestao-limpar-sessoes" "$(cat <<EOF
{
  "job": {
    "url": "${APP_URL}/api/tasks/limpar-sessoes/",
    "title": "gestao-limpar-sessoes",
    "enabled": true,
    "saveResponses": false,
    "schedule": {
      "timezone": "UTC",
      "hours": [6],
      "mdays": [-1],
      "minutes": [0],
      "months": [-1],
      "wdays": [0]
    },
    "requestTimeout": 30,
    "requestMethod": 1,
    "body": "",
    "headers": [
      {"name": "X-Task-Token", "value": "${TASK_TOKEN}"},
      {"name": "Content-Type", "value": "application/json"}
    ]
  }
}
EOF
)"

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=== Jobs criados ===${NC}"
for entry in "${created_ids[@]}"; do
  echo "  $entry"
done
echo ""
echo -e "${YELLOW}⚠  J-08 (bounces) criado como DESATIVADO.${NC}"
echo -e "   Ative após configurar a caixa bounces@msbrasil.inf.br no Zoho."
echo ""
echo "Acesse o painel: https://console.cron-job.org"
