#!/usr/bin/env python3
"""
Configura os jobs do cron-job.org conforme estratégia de keepalive otimizada.

Alterações realizadas:
  - keep-alive-gestao     → Seg-Sex 08h-18h, a cada 14 min (~220h/mês)
  - keep-alive-brcobranca → DESATIVADO (warm-up automático substitui)

Uso:
  export CRONJOB_API_KEY=<sua_chave>
  python configurar_cronjob.py

  # Só visualiza — não altera nada:
  python configurar_cronjob.py --dry-run

Obter chave:
  cron-job.org → Settings → API → Generate API Key
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error

API_BASE = "https://api.cron-job.org"

# URLs dos serviços (conforme render.yaml / CRONJOB.md)
URL_DJANGO     = "https://gestao-contrato-web-mt6j.onrender.com/health/"
URL_BRCOBRANCA = "https://brcobranca-api-m4q9.onrender.com"

# Schedule: Seg-Sex (wdays 1-5), horas 8-18, a cada 14 min
SCHEDULE_COMERCIAL = {
    "timezone": "America/Sao_Paulo",
    "hours":    [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "minutes":  [0, 14, 28, 42, 56],
    "mdays":    [-1],
    "months":   [-1],
    "wdays":    [1, 2, 3, 4, 5],   # 0=Dom … 6=Sáb
}


# ─────────────────────────────────────────────────────────────────────────────

def _req(method: str, path: str, api_key: str, body=None):
    url = API_BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body_text}") from e


def listar_jobs(api_key: str) -> list:
    data = _req("GET", "/jobs", api_key)
    return data.get("jobs", [])


def atualizar_job(job_id: int, payload: dict, api_key: str, dry_run: bool):
    if dry_run:
        print(f"    [dry-run] PATCH /jobs/{job_id} -> {json.dumps(payload, ensure_ascii=False)}")
        return
    _req("PATCH", f"/jobs/{job_id}", api_key, payload)


def classificar_job(job: dict) -> str:
    """Retorna 'django', 'brcobranca' ou None."""
    url   = (job.get("url")   or "").lower()
    title = (job.get("title") or "").lower()
    if URL_DJANGO.split("/")[2] in url or "keep-alive-gestao" in title:
        return "django"
    if (URL_BRCOBRANCA.split("/")[2] in url
            or "keep-alive-brcobranca" in title
            or "brcobranca" in title):
        return "brcobranca"
    return None


def formatar_schedule(s: dict) -> str:
    horas = s.get("hours", [-1])
    h_str = "todas as horas" if horas == [-1] else f"{horas[0]}h-{horas[-1]}h"
    mins  = s.get("minutes", [-1])
    m_str = "todo minuto" if mins == [-1] else f"a cada ~{mins[1]-mins[0]}min"
    wdays = s.get("wdays", [-1])
    dias  = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    d_str = "todos os dias" if wdays == [-1] else "/".join(dias.get(d, str(d)) for d in wdays)
    tz    = s.get("timezone", "UTC")
    return f"{d_str}, {h_str}, {m_str} ({tz})"


# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("CRONJOB_API_KEY"),
        help="Chave da API do cron-job.org (ou variavel CRONJOB_API_KEY)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exibe as alteracoes sem executar",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("ERRO: forneca a chave via --api-key ou CRONJOB_API_KEY=...")
        print("  cron-job.org -> Settings -> API -> Generate API Key")
        sys.exit(1)

    print("=" * 60)
    print("  Configuracao de cron-job.org -- Gestao de Contratos")
    print("=" * 60)
    if args.dry_run:
        print("  MODO DRY-RUN -- nenhuma alteracao sera feita\n")

    # ── 1. Listar jobs ────────────────────────────────────────────────────────
    print("Buscando jobs...")
    try:
        jobs = listar_jobs(args.api_key)
    except RuntimeError as e:
        print(f"ERRO ao buscar jobs: {e}")
        sys.exit(1)

    print(f"  {len(jobs)} job(s) encontrado(s)\n")

    django_jobs     = [(j["jobId"], j) for j in jobs if classificar_job(j) == "django"]
    brcobranca_jobs = [(j["jobId"], j) for j in jobs if classificar_job(j) == "brcobranca"]
    outros          = [j for j in jobs if classificar_job(j) is None]

    # ── 2. Resumo atual ───────────────────────────────────────────────────────
    print("-- Estado atual " + "-" * 43)
    for jid, j in django_jobs:
        status = "ativo" if j.get("enabled") else "pausado"
        print(f"  Django   [{jid}] {j.get('title','?')}  [{status}]")
        print(f"           {j.get('url','?')}")
        print(f"           schedule: {formatar_schedule(j.get('schedule') or {})}")
    for jid, j in brcobranca_jobs:
        status = "ativo" if j.get("enabled") else "pausado"
        print(f"  BRCob    [{jid}] {j.get('title','?')}  [{status}]")
        print(f"           {j.get('url','?')}")
    for j in outros:
        print(f"  Outro    [{j['jobId']}] {j.get('title','?')}")
    print()

    alteracoes = 0

    # ── 3. Atualizar / criar keep-alive-gestao ────────────────────────────────
    if not django_jobs:
        print("Nenhum job Django encontrado -- criando keep-alive-gestao...")
        payload_criar = {
            "job": {
                "url":           URL_DJANGO,
                "title":         "keep-alive-gestao",
                "enabled":       True,
                "requestMethod": 0,       # GET
                "schedule":      SCHEDULE_COMERCIAL,
            }
        }
        if not args.dry_run:
            try:
                _req("PUT", "/jobs", args.api_key, payload_criar)
                print("  OK  Job criado.")
                alteracoes += 1
            except RuntimeError as e:
                print(f"  ERRO ao criar job: {e}")
        else:
            print(f"  [dry-run] PUT /jobs -> criar keep-alive-gestao")
            alteracoes += 1
    else:
        for jid, j in django_jobs:
            sch = j.get("schedule") or {}
            ja_ok = (
                sorted(sch.get("hours",   [])) == sorted(SCHEDULE_COMERCIAL["hours"])   and
                sorted(sch.get("wdays",   [])) == sorted(SCHEDULE_COMERCIAL["wdays"])   and
                sorted(sch.get("minutes", [])) == sorted(SCHEDULE_COMERCIAL["minutes"])
            )
            if ja_ok and j.get("enabled"):
                print(f"  OK  keep-alive-gestao [{jid}] ja esta com horario comercial -- sem alteracao.")
            else:
                print(f"Atualizando keep-alive-gestao [{jid}]...")
                print(f"  Antes : {formatar_schedule(sch)}")
                print(f"  Depois: {formatar_schedule(SCHEDULE_COMERCIAL)}")
                atualizar_job(jid, {"job": {"enabled": True, "schedule": SCHEDULE_COMERCIAL}},
                              args.api_key, args.dry_run)
                if not args.dry_run:
                    print("  OK  Atualizado.")
                alteracoes += 1

    # ── 4. Desativar keep-alive-brcobranca ────────────────────────────────────
    print()
    if not brcobranca_jobs:
        print("  INFO  Nenhum job brcobranca encontrado -- nada a desativar.")
    else:
        for jid, j in brcobranca_jobs:
            if not j.get("enabled"):
                print(f"  OK  keep-alive-brcobranca [{jid}] ja esta desativado -- sem alteracao.")
            else:
                print(f"Desativando keep-alive-brcobranca [{jid}]...")
                print(f"  URL   : {j.get('url','?')}")
                print("  Motivo: warm-up automatico no Django substitui o keepalive continuo.")
                atualizar_job(jid, {"job": {"enabled": False}},
                              args.api_key, args.dry_run)
                if not args.dry_run:
                    print("  OK  Desativado.")
                alteracoes += 1

    # ── 5. Resumo ─────────────────────────────────────────────────────────────
    print()
    print("-- Resultado " + "-" * 46)
    if alteracoes == 0:
        print("  Nenhuma alteracao necessaria. Tudo ja esta configurado.")
    elif args.dry_run:
        print(f"  {alteracoes} alteracao(oes) seriam aplicadas (dry-run).")
    else:
        print(f"  {alteracoes} alteracao(oes) aplicadas com sucesso.")

    print()
    print("-- Consumo estimado apos configuracao " + "-" * 21)
    print("  keep-alive-gestao    Seg-Sex 08h-18h/14min  ~220 h/mes")
    print("  keep-alive-brcobranca  desativado           ~  0 h/mes")
    print("  brcobranca warm-up (sob demanda)            ~  5 h/mes")
    print("  " + "-" * 50)
    print("  Total estimado                              ~225 h/mes")
    print("  Limite Free Tier                             750 h/mes")
    print("  Margem disponivel                           ~525 h/mes")
    print()


if __name__ == "__main__":
    main()
