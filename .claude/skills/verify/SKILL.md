---
name: verify
description: Receita de verificação visual deste repo — sobe o Django, semeia dados por estágio do ciclo de cobrança e dirige as telas com Playwright.
---

# Verificação visual — Gestao-Contrato

## Subir o app
```bash
DEBUG=True nohup python manage.py runserver 127.0.0.1:8777 --noreload > /tmp/server.log 2>&1 &
until curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8777/accounts/login/ | grep -q 200; do sleep 1; done
```
- SQLite `db.sqlite3` já no repo; `python manage.py migrate` se necessário.
- Usuário de verificação: crie superuser via shell (`verificador`/`verifica123`).
- **Sempre reinicie o servidor após editar .py E templates** (não confie no reload).

## Semear estados do ciclo de cobrança
```bash
python manage.py gerar_dados_teste --limpar        # base (contratos, parcelas, índices)
python manage.py gerar_dados_teste --so-boletos    # boletos GERADO (simulados se API BRCobrança off)
python manage.py gerar_dados_teste --so-remessa    # ArquivoRemessa ENVIADO (libera tela de retorno)
python manage.py gerar_dados_teste --so-retorno    # baixas simuladas (alimenta conciliação)
```
- Cenário de bloqueio HU-06: contrato IPCA com `data_contrato` 14 meses atrás,
  `prazo_reajuste_meses=12`, sem `Reajuste` aplicado → parcela 13+ bloqueada.
- Boletos "gerados" de teste precisam de `conta_bancaria` preenchida para
  aparecer nas telas de remessa.

## Dirigir com Playwright
- Chromium pré-instalado (`playwright.chromium.launch()` já resolve).
- Login: POST form em `/accounts/login/` (username/password/submit).
- Telas do ciclo: `/financeiro/cobranca/` (hub) → `/financeiro/boletos/` →
  `/financeiro/remessa/` → `/financeiro/retorno/` → `/financeiro/cobranca/conciliacao/`.
- Grid de parcelas: `window.parcelasGridApi` (AG Grid) — esperar ~2,5s pós-load.
- Modais: `getMModal('id').open()` (Materialize) ou `bootstrap.Modal` (shim no base.html).

## Pegadinhas conhecidas
- `page.inner_text()` devolve texto RENDERIZADO — labels `.kpi-label` são
  uppercase via CSS; compare case-insensitive.
- Floats em JS de template: `{{ v }}` renderiza vírgula (pt-br) → SyntaxError.
  Use `{% load l10n %}` + `|unlocalize`. `page.on('pageerror')` pega isso.
- API BRCobrança (localhost:9292) fica OFF — botões "Gerar" aguardam cold-start
  (~105s) antes de falhar; dê timeout generoso ou verifique o caminho bloqueado.
