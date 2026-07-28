# Análise — Lote assíncrono com JOB (`/jobs/boletos`) para a tela "Boletos do Mês"

> Revisão do gateway **cobranca-api** (github.com/Maxwbh/cobranca-api) aplicada à
> geração em massa da HU-24. Este documento analisa a adoção do lote assíncrono;
> a integração em si fica para um épico futuro (ver Recomendação).

## 1. O contrato do gateway

| Rota | Função |
|------|--------|
| `POST /jobs/boletos` | Cria o job (body `{tenant_id, boletos[], template?}`) → **202** + `job_id`. Header opcional `Idempotency-Key`: repetir a mesma chave devolve **200** com o mesmo `job_id` (`idempotent_replay: true`) — nunca duplica. |
| `GET /jobs/boletos/{job_id}` | Estado do job: `received → processing → completed / partially_completed / failed`, com `total/completed/failed` e métricas (`duracao_ms`, `ms_por_item`). |
| `GET /jobs/boletos/{job_id}/items` | Itens paginados (`status?`, `limite ≤ 500`, `offset`); cada item tem `item_id` (= `external_id` enviado), `status`, `errors[]` e `artifact {href, sha256, tamanho}`. |
| `GET /jobs/boletos/{job_id}/artifacts` | Manifesto: PDFs individuais + `consolidado.zip` + `errors.json`, com `sha256` e `expira_em` (**410 Gone** após expirar). |
| `GET /jobs/boletos/{job_id}/artifacts/items/{nome}` | **PDF individual por boleto** (FileResponse). |

- Teto: `JOB_MAX_ITENS` = **200** por job (413 acima) — mesmo padrão do síncrono
  (`LOTE_MAX_ITENS` = 200 no `/api/boleto/multi`).
- Estado persistido (sobrevive a restart); falha de um item **não** cancela o lote.
- O lote entrega **referências** (href/sha256), nunca base64.
- Há também `POST /jobs/cnab/remessas`: sublotes **determinísticos** por
  (banco, layout, convênio, carteira, conta, agência, pix) → 1 arquivo `.rem` por sublote.

## 2. O que temos hoje (após a feature multi boletos)

- Tela Boletos do Mês: contas CNAB geram via **`/api/boleto/multi` síncrono**
  em lotes de até 200 (`BOLETO_MULTI_TAMANHO_LOTE`), com verificação por boleto
  do retorno (só grava o que veio OK) — C6/Sicoob seguem individuais (registro
  no banco via gateway).
- Limitação conhecida do multi síncrono: o PDF gravado por parcela é o
  **combinado do lote** (o multi devolve um arquivo único).

## 3. O que o JOB assíncrono resolveria

1. **PDF individual por parcela** — `artifacts/items/{item_id}.pdf` elimina a
   limitação do PDF combinado (2ª via correta por boleto).
2. **Lotes grandes sem timeout HTTP** — 202 imediato; o worker processa em
   background (importante no Render free, onde o cold start + lote grande
   estoura o request síncrono).
3. **Idempotência de verdade** — `Idempotency-Key` (ex.: `boletos-{imob}-{competência}`)
   torna o reenvio do formulário inofensivo.
4. **Conferência item a item nativa** — `items?status=failed` + `errors.json`
   dá o relatório de falhas pronto (hoje conferimos via metadados do multi).
5. **Remessa em sublotes prontos** — `/jobs/cnab/remessas` replica (e substitui)
   o agrupamento local por conta/layout da HU-23.

## 4. O que a integração exige (custo)

- **Modelo de rastreamento**: gravar `job_id` (+ `idempotency_key`, status) por
  solicitação de geração — novo modelo pequeno (ex.: `LoteGeracaoBoletos`).
- **Polling**: task (Celery beat ou cron-job.org) consultando
  `GET /jobs/boletos/{job_id}` até estado terminal; no Render free (sem worker),
  o polling teria que ser via cron HTTP — latência de minutos.
- **Download dos artifacts**: buscar e gravar o PDF individual por parcela
  **antes** de `expira_em` (senão 410).
- **UX**: a tela passa a ter estado "processando…" com atualização posterior —
  hoje o resultado é imediato na resposta do POST.

## 5. Recomendação

- **Manter o multi síncrono como padrão** para o volume atual (≤ 200 por lote,
  resposta imediata na tela) — já entregue.
- **Adotar o JOB assíncrono num épico próprio (BAPI-42 sugerido)** quando:
  volume por competência ultrapassar ~200 boletos por conta, ou o PDF individual
  por parcela via lote se tornar requisito, ou o deploy tiver worker dedicado.
  - Fase 1: emitir job + persistir `job_id`/`Idempotency-Key`.
  - Fase 2: polling + gravação por item (PDF individual via `artifacts/items/`).
  - Fase 3: migrar a remessa para `/jobs/cnab/remessas` (sublotes determinísticos).
