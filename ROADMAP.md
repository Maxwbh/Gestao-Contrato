# ROADMAP — Novas Implementações

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Última atualização:** 2026-03-31

> Pendentes organizados por prioridade.
> Para documentação do sistema atual, consulte **[SISTEMA.md](SISTEMA.md)**.

---

## Legenda

- **P1** Crítico — bloqueia uso em produção
- **P2** Alto — funcionalidade importante
- **P3** Médio — melhoria significativa
- **P4** Baixo — nice to have

---

## 1. INFRAESTRUTURA (P1 — Correções Críticas) ✅ CONCLUÍDO

| # | Item | Status |
|---|------|--------|
| 1.1 | App `accounts` incompleto | ✅ Criado `models.py`, `admin.py` e `migrations/` |
| 1.2 | `makemigrations` comentado | ✅ Documentado no `build.sh` — comportamento intencional |
| 1.3 | `admin.py` faltando | ✅ Criado `accounts/admin.py` |

---

## 2. BACKEND — REGRAS DE NEGÓCIO

### P2 — Alto ✅ CONCLUÍDO
| # | Item | Status |
|---|------|--------|
| 2.1 | Validar que soma das intermediárias não excede valor financiado | ✅ |
| 2.2 | Validar dia de vencimento recomendado (1–28) | ✅ |
| 2.3 | Ajuste de vencimento para meses com menos dias + feriados | ✅ |
| 2.4 | Aplicar reajuste automaticamente nas prestações intermediárias | ✅ |
| 2.5 | Histórico: valores originais vs reajustados nas intermediárias | ✅ |
| 2.6 | Não permitir pagamento menor que valor mínimo | ✅ |
| 2.7 | Integração IBGE API — IPCA, INPC | ✅ |
| 2.8 | Integração FGV API — IGP-M, INCC | ✅ |

### P3 — Médio
| # | Item |
|---|------|
| 2.9 | Validar sequência de ciclos de reajuste (não pular) |
| 2.10 | Segunda via de boleto com juros/multa calculados |
| 2.11 | WhatsApp/SMS — testes end-to-end com Twilio |

### P4 — Baixo
| # | Item |
|---|------|
| 2.12 | PIX — linha digitável e QR Code no boleto | ⚠️ Prioridade **extremamente baixa** / Alta complexidade — TO_DO 2050 |

---

## 3. FRONTEND — TEMPLATES E INTERFACES

### P2 — Alto
| # | Tela/Componente |
|---|-----------------|
| 3.1 | Aba Histórico de Reajustes (contrato) |
| 3.2 | Aba Boletos gerados (lista com status e download) |
| 3.3 | Wizard de criação de contrato (7 etapas) |
| 3.4 | Dashboard Contabilidade: gráfico recebimentos mensais |
| 3.5 | Dashboard Contabilidade: gráfico inadimplência por imobiliária |
| 3.6 | Dashboard Contabilidade: tabela vencimentos consolidados |
| 3.7 | Dashboard Imobiliária: filtros na lista de contratos |
| 3.8 | Dashboard Imobiliária: busca rápida por contrato/comprador |
| 3.9 | Dashboard Imobiliária: ações em lote (gerar boletos) |
| 3.10 | Dashboard Imobiliária: fluxo de caixa previsto vs realizado |
| 3.11 | Gestão de Boletos: interface geração em lote com progresso |
| 3.12 | Gestão de Boletos: download ZIP de vários boletos |
| 3.13 | Gestão de Parcelas: seleção múltipla para ações em lote |
| 3.14 | Gestão de Parcelas: juros/multa/total nas vencidas |
| 3.15 | Sidebar recolhível com indicadores de pendências |
| 3.16 | Toast de sucesso/erro padronizado |
| 3.17 | Centro de notificações com badge |

### P3 — Médio
| # | Tela/Componente |
|---|-----------------|
| 3.18 | Aba Relatórios do Contrato |
| 3.19 | Aba Histórico de Pagamentos (comprovantes) |
| 3.20 | Configurações Contabilidade (dados, usuários, imobiliárias) |
| 3.21 | Exportar relatório consolidado (PDF, Excel) |
| 3.22 | Tela de reajuste pendente (índice, prévia, aplicar lote) |
| 3.23 | Histórico de reajustes aplicados |
| 3.24 | Upload de comprovante de pagamento |
| 3.25 | Notificar comprador inadimplente |
| 3.26 | Configurações de boleto por imobiliária |
| 3.27 | Configurações de notificação (dias, canais) |
| 3.28 | Gerenciamento de usuários por imobiliária |
| 3.29 | Card de resumo reutilizável |
| 3.30 | Tabela paginada com filtros (componente genérico) |
| 3.31 | Gráficos barras/pizza/linha (componente genérico) |
| 3.32 | Modal de confirmação reutilizável |

### P4 — Baixo
| # | Tela/Componente |
|---|-----------------|
| 3.33 | Aba Documentos (upload contrato assinado) |
| 3.34 | Upload de logo da imobiliária |
| 3.35 | Seletor de período reutilizável |

---

## 4. APIs — ENDPOINTS PENDENTES

### P2 — Alto
| Endpoint | Descrição |
|----------|-----------|
| `GET /api/contabilidade/vencimentos/` | Tabela com filtros (período, imobiliária, status) |
| `POST /api/contabilidade/boletos/gerar/massa/` | Geração em massa |
| `GET /api/imobiliaria/<id>/vencimentos/` | Filtros por período e comprador |
| `GET /api/imobiliaria/<id>/fluxo-caixa/` | Previsão mensal vs realizado |
| `GET /portal/api/vencimentos/` | Filtros por período e status |
| `GET /portal/api/boletos/` | Lista com filtros |

### P3 — Médio
| Endpoint | Descrição |
|----------|-----------|
| `GET /api/contabilidade/relatorios/vencimentos/` | Relatório semanal/mensal/trimestral |
| `GET /api/contabilidade/imobiliarias/` | Lista com estatísticas |
| `GET /api/imobiliaria/<id>/pendencias/` | Parcelas vencidas com encargos |
| `POST /portal/api/boletos/segunda-via/` | Gerar segunda via com encargos |
| `GET /portal/api/boletos/<id>/linha-digitavel/` | Linha digitável |

---

## 5. TAREFAS CELERY PENDENTES

### P2 — Alto
| Task | Frequência | Descrição |
|------|------------|-----------|
| `alerta_vencimentos_semana` | Segunda-feira | Para Contabilidade |
| `alerta_inadimplencia_diario` | Diário | Para Imobiliária |

### P3 — Médio
| Task | Frequência | Descrição |
|------|------------|-----------|
| `relatorio_semanal_incorporadoras` | Segunda-feira | Resumo semanal |
| `relatorio_mensal_consolidado` | 1º dia útil | Consolidado mensal |

### P4 — Baixo
| Task | Frequência | Descrição |
|------|------------|-----------|
| `gerar_boletos_mes_seguinte` | Dia 25 | Automação completa |

---

## 6. SISTEMA DE PERMISSÕES

### P2 — Alto
| Perfil | Descrição |
|--------|-----------|
| Admin Contabilidade | Acesso total a todas imobiliárias |
| Admin Imobiliária | Acesso total à sua imobiliária |
| Filtro por tenant | Todas as views filtram por imobiliária |
| Audit log | Logs de geração de boletos e reajustes |

### P3 — Médio
| Perfil | Descrição |
|--------|-----------|
| Operador Contabilidade | Apenas relatórios |
| Gerente Imobiliária | Contratos e relatórios |
| Operador Imobiliária | Pagamentos e boletos |
| Rate limiting | Nas APIs públicas |

### P4 — Baixo
| Item | Descrição |
|------|-----------|
| Visualizador | Apenas consultas |
| Confirmação | Antes de operações em massa |

---

## 7. TESTES AUTOMATIZADOS

**Meta:** > 80% de cobertura | **Atual:** ~25%

### 7.1 P1 — Apps sem nenhum teste (~104 testes) ✅ CONCLUÍDO
| Arquivo | Escopo | Qtd | Status |
|---------|--------|-----|--------|
| `tests/unit/accounts/test_auth_views.py` | login, logout, registro, perfil, alterar senha | 22 | ✅ |
| `tests/unit/notificacoes/test_models.py` | ConfiguracaoEmail, SMS, WhatsApp, Notificacao | 10 | ✅ |
| `tests/unit/notificacoes/test_views.py` | CRUD configs e templates, preview | 22 | ✅ |
| `tests/unit/notificacoes/test_tasks.py` | envio email/sms, processar pendentes | 8 | ✅ |
| `tests/unit/portal_comprador/test_models.py` | AcessoComprador, LogAcessoComprador | 5 | ✅ |
| `tests/unit/portal_comprador/test_auth.py` | auto-cadastro, login/logout | 11 | ✅ |
| `tests/unit/portal_comprador/test_views.py` | dashboard, contratos, boletos, dados | 21 | ✅ |
| `tests/unit/portal_comprador/test_api.py` | APIs do portal | 5 | ✅ |

### 7.2 P2 — Views e APIs faltantes (~164 testes)
| Arquivo | Escopo | Qtd |
|---------|--------|-----|
| `tests/unit/core/test_models.py` | Modelos do core | 12 |
| `tests/unit/core/test_crud_views.py` | CRUD completo | 30 |
| `tests/unit/core/test_api_views.py` | APIs bancos, CEP, CNPJ | 15 |
| `tests/unit/core/test_dashboard.py` | index, dashboard, setup | 7 |
| `tests/unit/core/test_management_commands.py` | gerar_dados_teste | 8 |
| `tests/unit/contratos/test_crud_views.py` | CRUD contratos | 14 |
| `tests/unit/contratos/test_indices_views.py` | CRUD índices | 9 |
| `tests/unit/financeiro/test_parcela_views.py` | listar, detalhe, pagar | 14 |
| `tests/unit/financeiro/test_boleto_views.py` | gerar, download, carnê | 17 |
| `tests/unit/financeiro/test_reajuste_views.py` | listar, aplicar, calcular | 9 |
| `tests/unit/financeiro/test_cnab_views.py` | remessa e retorno | 15 |
| `tests/unit/financeiro/test_dashboard_views.py` | dashboards | 9 |
| `tests/unit/financeiro/test_rest_api_views.py` | APIs REST | 24 |

### 7.3 P3 — Integração e Forms (~37 testes)
| Arquivo | Escopo | Qtd |
|---------|--------|-----|
| `tests/unit/core/test_forms.py` | Forms core | 10 |
| `tests/unit/contratos/test_forms.py` | Forms contratos | 8 |
| `tests/integration/test_fluxo_contrato_completo.py` | E2E contrato | 5 |
| `tests/integration/test_fluxo_boleto.py` | E2E boleto | 3 |
| `tests/integration/test_portal_comprador.py` | E2E portal | 3 |
| `tests/integration/test_notificacoes.py` | E2E notificações | 3 |

### 7.4 P4 — Segurança e Edge Cases (~41 testes)
| Arquivo | Escopo | Qtd |
|---------|--------|-----|
| `tests/functional/test_contrato_workflow.py` | E2E completo | 4 |
| `tests/functional/test_financeiro_workflow.py` | E2E financeiro | 3 |
| `tests/unit/test_security.py` | CSRF, SQL injection, XSS | 7 |
| `tests/unit/test_edge_cases.py` | Casos extremos | 10 |
| `tests/unit/notificacoes/test_management_commands.py` | Commands | 3 |
| `tests/unit/financeiro/test_management_commands.py` | Commands | 2 |

### 7.5 Infraestrutura de Testes
| Prioridade | Item |
|------------|------|
| P2 | 13 factories faltantes (notificacoes, portal, CNAB) |
| P2 | Mocks: Twilio SMS/WhatsApp, IBGE, SMTP |
| P3 | CI/CD GitHub Actions |
| P4 | Badge de cobertura no README |

---

## 8. CI/CD E PERFORMANCE

### P2 — Alto
| Item | Descrição |
|------|-----------|
| Bootstrap local | Servir Bootstrap 5 localmente (não CDN) |
| Logging | Configurar logging de erros além do Sentry |

### P3 — Médio
| Item | Descrição |
|------|-----------|
| GitHub Actions | Rodar pytest em cada PR |
| GitHub Actions | Verificar cobertura > 80% |
| Cache Redis | Para dashboards |
| Índices DB | Para queries de vencimento |

### P4 — Baixo
| Item | Descrição |
|------|-----------|
| Deploy automático | Render após merge em main |
| Async boletos | Processamento assíncrono em massa |

---

## 9. DOCUMENTAÇÃO

### P3 — Médio
| Item | Descrição |
|------|-----------|
| Swagger/OpenAPI | `drf-spectacular` ou `drf-yasg` |

### P4 — Baixo
| Item | Descrição |
|------|-----------|
| `docs/development/EXAMPLES.md` | Exemplos de uso das factories |
| Diagramas | ER, fluxo de boleto, fluxo de reajuste |
| `CONTRIBUTING.md` | Guia de contribuição |

---

---

## 10. REAJUSTE DE PARCELAS — FOCO ATUAL

> **Objetivo:** tornar o fluxo de reajuste claro, seguro e auditável — do cálculo à confirmação.
> Estado atual: lógica de backend implementada (ciclos, bloqueio de boleto, índices IBGE/FGV),
> porém sem interface dedicada, sem preview e sem simulação.

---

### 10.0 Regras de Reajuste por Faixas de Parcelas (NOVO — PRIORIDADE MÁXIMA)

> **Conceito central:** cada contrato define quais parcelas são reajustadas, por qual índice e em qual período.
> Exemplo real: parcelas 1–12 sem reajuste / 13–24 pelo IPCA / 25–36 pelo IGPM.
> Hoje o sistema trata todas as parcelas com um único índice global — isso precisa mudar.

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-00 | **Modelo de Faixas de Reajuste no Contrato** — substituir campo único `tipo_correcao` por tabela `RegraReajuste(contrato, parcela_inicial, parcela_final, indice_tipo, periodicidade_meses)`; permite múltiplas regras por contrato | P1 | TO_DO |
| R-00a | **Cálculo automático a partir das regras do contrato** — ao aplicar reajuste, o sistema determina automaticamente: quais parcelas afetadas, qual índice usar e o percentual do período, sem entrada manual do operador | P1 | TO_DO |
| R-00b | **UI de cadastro de faixas no contrato** — seção "Regras de Reajuste" na tela do contrato com tabela editável: `De (parcela) / Até / Índice / A cada (meses) / Ação` | P1 | TO_DO |
| R-00c | **Desconto sobre o reajuste** — ao aplicar o reajuste de uma faixa, permitir informar desconto em `%` ou `R$` que reduz o percentual final aplicado (ex: IPCA 5,4% com desconto de 1% → aplica 4,4%; ou desconto fixo de R$ 50,00 por parcela) | P1 | TO_DO |
| R-00d | **Preview automático no momento do reajuste** — ao clicar "Aplicar Reajuste", o sistema carrega as regras do contrato, busca o índice do período, calcula desconto e exibe tabela: parcela / valor atual / % aplicado / desconto / valor final, antes de confirmar | P1 | TO_DO |
| R-00e | **Migração de contratos existentes** — script para converter contratos atuais (campo `tipo_correcao` único) para o novo modelo de faixas, preservando histórico de reajustes já aplicados | P2 | TO_DO |

**Exemplo de configuração de faixas:**

```
Contrato XYZ — Regras de Reajuste:
┌─────────────┬──────────────┬────────┬──────────────┬─────────────────────┐
│ Parcelas De │ Parcelas Até │ Índice │ A cada       │ Observação          │
├─────────────┼──────────────┼────────┼──────────────┼─────────────────────┤
│      1      │      12      │   —    │      —       │ Sem reajuste        │
│     13      │      24      │  IPCA  │  12 meses    │ Aniversário anual   │
│     25      │      36      │  IGPM  │  12 meses    │ Aniversário anual   │
└─────────────┴──────────────┴────────┴──────────────┴─────────────────────┘
```

---

### 10.1 Cálculo — Melhorias

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-01 | **Preview/Simulação antes de aplicar** — endpoint dry-run que retorna a prévia de cada parcela (valor atual → valor reajustado) sem persistir nada | P1 | TO_DO |
| R-02 | **Acumulado de índices** — quando o reajuste não foi feito no mês exato, calcular automaticamente o acumulado dos meses em atraso (ex: 3 meses de IPCA acumulados) | P1 | TO_DO |
| R-03 | **Índice composto** — suporte a `ÍNDICE + spread fixo` (ex: IPCA + 2% a.a.), comum em contratos imobiliários | P2 | TO_DO |
| R-04 | **Teto e piso configuráveis** — limitar reajuste mínimo (0% — sem deflação) e máximo (ex: 15%) por contrato ou por faixa | P2 | TO_DO |
| R-05 | **Reajuste proporcional acessível via UI** — `calcular_reajuste_proporcional` existe no backend mas não está exposto na interface; surfaçar resultado no formulário de reajuste | P2 | TO_DO |
| R-06 | **Desfazer reajuste automático** — atualmente só reajustes manuais podem ser excluídos; permitir reverter reajuste automático com registro de auditoria | P3 | TO_DO |
| R-07 | **Reajuste automático via Celery** — task agendada que aplica índice do mês na data aniversário do contrato conforme regras de faixas, com log e notificação ao gestor | P3 | TO_DO |

---

### 10.2 Entrada de Dados — Melhorias

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-08 | **Tela dedicada de Reajuste Pendente** — lista todos os contratos com reajuste vencido, agrupados por imobiliária, com ação rápida "Aplicar" | P1 | TO_DO |
| R-09 | **Formulário com busca automática do índice** — ao selecionar tipo (IPCA, IGP-M…) e mês/ano de referência, buscar o percentual na base e preencher automaticamente; já existe `obter_indice_reajuste` no backend | P1 | TO_DO |
| R-10 | **Tabela de prévia por parcela no modal** — antes de confirmar, exibir lista parcela / vencimento / valor atual / % reajuste / desconto / valor final | P1 | TO_DO |
| R-11 | **Alerta quando há boletos já emitidos no intervalo** — avisar que os boletos precisam ser regenerados após o reajuste e oferecer botão "Regenerar todos" | P1 | TO_DO |
| R-12 | **Confirmação dupla para reajuste negativo (deflação)** — exibir alerta especial quando percentual < 0% para evitar aplicação acidental | P2 | TO_DO |
| R-13 | **Seleção de intervalo de parcelas visual** — campos `De / Até` preenchidos automaticamente pelas regras do contrato, editáveis para ajuste fino | P2 | TO_DO |
| R-14 | **Histórico detalhado na tela do contrato** — aba "Reajustes" com: ciclo, índice, percentual, desconto aplicado, parcelas afetadas, data, quem aplicou, botão desfazer | P2 | TO_DO |
| R-15 | **Aplicação em lote** — selecionar N contratos da mesma imobiliária e aplicar reajuste de uma vez conforme regras de cada contrato, com relatório de resultado | P3 | TO_DO |

---

### 10.3 Validações e Regras de Negócio

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-16 | **Validar sequência de ciclos** (não pular) — já existe no `clean()` do model, porém sem feedback claro na UI quando o ciclo anterior está faltando | P1 | TO_DO |
| R-17 | **Bloquear reajuste em contrato com parcelas em disputa/negociação** — flag `em_negociacao` no contrato impede reajuste até resolução | P3 | TO_DO |
| R-18 | **Audit log** — registrar usuário, IP e timestamp de cada reajuste aplicado/desfeito | P2 | TO_DO |

---

### 10.4 Ordem de Execução Sugerida para o Módulo de Reajuste

| Fase | Itens | Resultado esperado |
|------|-------|-------------------|
| **1** | R-00, R-00b, R-00c | Modelo de faixas + UI de cadastro + desconto no contrato |
| **2** | R-00a, R-00d, R-01 | Cálculo automático pelas regras + preview dry-run antes de aplicar |
| **3** | R-08, R-09, R-10, R-11, R-16 | Tela de pendentes + busca automática de índice + tabela de prévia + alertas |
| **4** | R-02, R-04, R-05 | Acumulado de índices + teto/piso + proporcional na UI |
| **5** | R-14, R-18, R-12, R-00e | Histórico com auditoria + migração de contratos existentes |
| **6** | R-03, R-13, R-15, R-06, R-07 | Índice composto + lote + Celery automático |

---

## Ordem de Execução Recomendada

| Fase | Escopo | Seções |
|------|--------|--------|
| **1** | Correções críticas de infraestrutura | 1 |
| **2** | ⭐ **Reajuste — Fórmulário + Preview + Pendentes** | 10 (Fase 1–2) |
| **3** | Testes P1 (apps sem cobertura) | 7.1 |
| **4** | Frontend P2 (telas principais) | 3 (P2) |
| **5** | ⭐ **Reajuste — Acumulado + Histórico + Auditoria** | 10 (Fase 3–4) |
| **6** | APIs P2 | 4 (P2) |
| **7** | Testes P2 (views e APIs) | 7.2 |
| **8** | Permissões e segurança | 6 |
| **9** | ⭐ **Reajuste — Índice composto + Lote + Celery** | 10 (Fase 5–6) |
| **10** | Testes P3/P4 + CI/CD | 7.3, 7.4, 8 |
| **11** | Frontend P3/P4 | 3 (P3, P4) |
| **12** | Documentação | 9 |

---

## Resumo Quantitativo

| Categoria | P1 | P2 | P3 | P4 | Total |
|-----------|----|----|----|----|-------|
| Infraestrutura | 3 | 2 | 1 | — | 6 |
| Backend | — | ✅8 | 3 | 1 | 12 |
| Frontend | — | 17 | 15 | 3 | 35 |
| APIs | — | 6 | 5 | — | 11 |
| Celery | — | 2 | 2 | 1 | 5 |
| Permissões | — | 4 | 4 | 2 | 10 |
| Testes | ✅104 | ~164 | ~37 | ~41 | ~346 |
| CI/CD | — | 2 | 4 | 2 | 8 |
| Documentação | — | — | 1 | 3 | 4 |
| **Total** | **~107** | **~205** | **~72** | **~53** | **~437** |
