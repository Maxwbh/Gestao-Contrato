#!/usr/bin/env python3
"""
Configura os jobs do cron-job.org conforme estratégia de keepalive.

Ações realizadas:
  keep-alive-gestao            → Seg-Sex 08h-18h, a cada 14 min  (atualizado)
  keep-alive-brcobranca        → DESATIVADO  (warm-up automático no Django)
  keep-alive-brcobranca_cnab_api → DESATIVADO  (serviço antigo, substituído)
  jobs de tarefas              → mantidos como estão (voltarão a funcionar
                                 quando o Render for reativado)

Uso:
  python configurar_cronjob.py --api-key SUA_CHAVE [--dry-run]
  ou
  CRONJOB_API_KEY=SUA_CHAVE python configurar_cronjob.py

Obtenha sua chave em: https://cron-job.org/en/members/api/
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = "https://api.cron-job.org"

# Fragmentos de URL que identificam cada categoria de job
URL_DJANGO_HEALTH  = "/health/"
URL_DJANGO_TASKS   = "gestao-contrato-web-mt6j.onrender.com/api/tasks/"
URL_BRCOBRANCA     = "brcobranca-api-m4q9.onrender.com"
URL_BOLETO_ANTIGO  = "boleto-cnab-api.onrender.com"

# Schedule novo para o Django: Seg-Sex 08h-18h, a cada 14 min
SCHEDULE_COMERCIAL = {
    "timezone": "America/Sao_Paulo",
    "hours":    [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "minutes":  [0, 14, 28, 42, 56],
    "mdays":    [-1],
    "months":   [-1],
    "wdays":    [1, 2, 3, 4, 5],   # 1=Seg … 5=Sex
}


# ──────────────────────────────────────────────────────────────────────────────

class CronJobClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _req(self, method: str, path: str, body=None):
        url  = f"{API_BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f"    ✗ HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
            raise

    def listar_jobs(self):
        return self._req("GET", "/jobs").get("jobs", [])

    def atualizar(self, job_id: int, payload: dict):
        return self._req("PATCH", f"/jobs/{job_id}", {"job": payload})

    def desativar(self, job_id: int):
        return self.atualizar(job_id, {"enabled": False})


# ──────────────────────────────────────────────────────────────────────────────

def _sched_str(s: dict) -> str:
    if not s:
        return "(sem schedule)"
    h  = s.get("hours",   [-1])
    m  = s.get("minutes", [-1])
    wd = s.get("wdays",   [-1])
    tz = s.get("timezone", "?")
    wd_nomes = {0:"Dom",1:"Seg",2:"Ter",3:"Qua",4:"Qui",5:"Sex",6:"Sáb"}
    dias = [wd_nomes.get(d, str(d)) for d in wd] if wd != [-1] else ["todos"]
    horas = f"{min(h)}h-{max(h)}h" if h != [-1] else "todas"
    return f"{dias}  {horas}  min={m}  tz={tz}"


def _job_label(j: dict) -> str:
    return f"#{j['jobId']} «{j.get('title','?')}» {'✓ ativo' if j.get('enabled') else '✗ inativo'}"


def _url_contem(job: dict, fragmento: str) -> bool:
    return fragmento in (job.get("url") or "")


# ──────────────────────────────────────────────────────────────────────────────

def run(api_key: str, dry_run: bool):
    client = CronJobClient(api_key)

    print("Buscando jobs em cron-job.org...")
    try:
        todos = client.listar_jobs()
    except Exception:
        print("Falha ao listar jobs. Verifique sua API key.")
        sys.exit(1)

    print(f"  → {len(todos)} job(s) encontrado(s)\n")

    # Classificar jobs
    keepalive_django    = [j for j in todos if _url_contem(j, "gestao-contrato-web") and _url_contem(j, URL_DJANGO_HEALTH)]
    keepalive_brc       = [j for j in todos if _url_contem(j, URL_BRCOBRANCA)]
    keepalive_brc_antigo= [j for j in todos if _url_contem(j, URL_BOLETO_ANTIGO)]
    tarefas             = [j for j in todos if _url_contem(j, URL_DJANGO_TASKS)]
    outros              = [j for j in todos
                           if j not in keepalive_django
                           and j not in keepalive_brc
                           and j not in keepalive_brc_antigo
                           and j not in tarefas]

    # ── 1. Jobs de tarefas — apenas informativo ────────────────────────────────
    print("─" * 60)
    print("TAREFAS AGENDADAS  (não alteradas)")
    print("─" * 60)
    for j in tarefas:
        print(f"  {_job_label(j)}")
        print(f"    {j.get('url','')}")
        print(f"    última: {j.get('lastExecutionTime','—')}  status: {j.get('lastStatus','?')}")
    if not tarefas:
        print("  (nenhum job de tarefas encontrado)")
    print("  ℹ  Estes jobs voltarão a funcionar quando o Render for reativado.\n")

    # ── 2. Keep-alive brcobranca atual → DESATIVAR ────────────────────────────
    print("─" * 60)
    print("KEEP-ALIVE brcobranca-api  → DESATIVAR")
    print("─" * 60)
    _processar_desativar(client, keepalive_brc, "brcobranca-api", dry_run)

    # ── 3. Keep-alive boleto-cnab-api antigo → DESATIVAR ─────────────────────
    print("─" * 60)
    print("KEEP-ALIVE boleto-cnab-api (antigo)  → DESATIVAR")
    print("─" * 60)
    _processar_desativar(client, keepalive_brc_antigo, "boleto-cnab-api", dry_run)

    # ── 4. Keep-alive Django → HORÁRIO COMERCIAL ──────────────────────────────
    print("─" * 60)
    print("KEEP-ALIVE gestao-contrato-web  → Seg-Sex 08h-18h / 14 min")
    print("─" * 60)
    if not keepalive_django:
        print("  (job não encontrado — crie manualmente em cron-job.org)")
        print(f"  URL:     https://gestao-contrato-web-mt6j.onrender.com/health/")
        print(f"  Método:  GET")
        print(f"  Schedule: {_sched_str(SCHEDULE_COMERCIAL)}")
    else:
        for j in keepalive_django:
            print(f"  {_job_label(j)}")
            print(f"    URL: {j.get('url','')}")
            print(f"    Schedule atual: {_sched_str(j.get('schedule') or {})}")
            print(f"    Schedule novo:  {_sched_str(SCHEDULE_COMERCIAL)}")
            if dry_run:
                print("    [dry-run] Atualizaria schedule e reativaria.")
            else:
                try:
                    client.atualizar(j["jobId"], {
                        "enabled":  True,
                        "schedule": SCHEDULE_COMERCIAL,
                    })
                    print("    ✓ Atualizado e reativado.")
                except Exception:
                    print("    ✗ Falha ao atualizar.")
    print()

    # ── 5. Outros jobs ────────────────────────────────────────────────────────
    if outros:
        print("─" * 60)
        print("OUTROS JOBS  (não alterados)")
        print("─" * 60)
        for j in outros:
            print(f"  {_job_label(j)}  {j.get('url','')}")
        print()

    # ── Resumo ────────────────────────────────────────────────────────────────
    print("=" * 60)
    if dry_run:
        print("DRY-RUN — nenhuma alteração aplicada.")
        print("Execute sem --dry-run para aplicar as mudanças.")
    else:
        print("Configuração concluída.")
    print()
    print("Consumo estimado após as mudanças:")
    print("  gestao-contrato-web:  10h/dia × 22 dias úteis = ~220h/mês")
    print("  brcobranca-api:       warm-up sob demanda      =   ~5h/mês")
    print("  Total:                                         = ~225h/mês")
    print("  Limite free:                                     750h/mês  ✓")


def _processar_desativar(client, jobs, nome, dry_run):
    if not jobs:
        print(f"  (nenhum job de keepalive para {nome} encontrado — ok)\n")
        return
    for j in jobs:
        print(f"  {_job_label(j)}")
        print(f"    URL: {j.get('url','')}")
        if not j.get("enabled"):
            print("    → Já está inativo.\n")
            continue
        if dry_run:
            print("    [dry-run] Desativaria este job.\n")
        else:
            try:
                client.desativar(j["jobId"])
                print("    ✓ Desativado.\n")
            except Exception:
                print("    ✗ Falha ao desativar.\n")


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("CRONJOB_API_KEY"),
        help="API key do cron-job.org (ou env CRONJOB_API_KEY)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria feito sem aplicar nenhuma mudança",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("Erro: informe --api-key ou defina a variável CRONJOB_API_KEY.")
        print("Obtenha sua chave em: https://cron-job.org/en/members/api/")
        sys.exit(1)

    run(args.api_key, args.dry_run)
