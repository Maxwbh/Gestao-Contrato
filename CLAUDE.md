# Gestão de Contratos — Instruções para Claude

## Fluxo Git (obrigatório)

```
claude/fix-boleto-generation-error-tuqwA  →  PR  →  V3.1  →  merge  →  main
          (desenvolvimento Claude)            (review)   (staging)          (produção)
```

### Regras de Branch

| Branch | Função | Quem commita |
|--------|--------|--------------|
| `claude/fix-boleto-generation-error-tuqwA` | Desenvolvimento / testes | Claude |
| `V3.1` | Integração / staging | Merge via PR revisado por @maxwbh |
| `main` | Produção | Merge de V3.1 por @maxwbh — commits verificados |

### Workflow por Fase

1. **Durante o desenvolvimento**: Claude commita e pusha **sempre** em `claude/fix-boleto-generation-error-tuqwA`
2. **Fase concluída**: Claude abre **PR** de `claude/fix-boleto-generation-error-tuqwA` → `V3.1`
3. **Revisão**: @maxwbh valida e faz merge do PR em `V3.1`
4. **Produção**: @maxwbh faz merge de `V3.1` → `main` com commits atribuídos a @maxwbh (verificados)

### Comandos Claude (resumo)

```bash
# Desenvolvimento normal
git checkout claude/fix-boleto-generation-error-tuqwA
git add <arquivos>
git commit -m "Fase X: descrição"
git push -u origin claude/fix-boleto-generation-error-tuqwA

# Quando fase concluída → abrir PR via GitHub MCP
# mcp__github__create_pull_request (base: V3.1, head: claude/fix-boleto-generation-error-tuqwA)
```

### NÃO fazer
- ❌ Não commitar diretamente em `V3.1`
- ❌ Não commitar diretamente em `main`
- ❌ Não criar PR sem a fase estar completa
- ❌ Não fazer merge sem aprovação de @maxwbh

---

## Stack Técnica

- **Backend**: Django 4.x + PostgreSQL (Supabase)
- **Frontend**: Materialize CSS 1.0.0 + Bootstrap bridge classes (sem Bootstrap JS)
- **Grids**: AG Grid Community 31.3.4 (`agGrid.createGrid`, `ag-theme-material`)
- **Date picker**: Flatpickr 4.6.13 (locale pt-BR)
- **Deploy**: Render.com free tier + Whitenoise + Gunicorn
- **Boletos**: BRCobranca API (Docker separado)

## Branches de Produção

- `main` — produção final (@maxwbh)
- `V3.1` — staging / integração
- `claude/fix-boleto-generation-error-tuqwA` — desenvolvimento Claude
