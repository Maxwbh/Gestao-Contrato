# ROADMAP — Novas Implementações

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Última atualização:** 2026-04-01

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
> porém sem cálculo automático do acumulado, sem preview e sem interface dedicada.

---

### 10.0 Modelo de Reajuste — Como Funciona

> **Regra do negócio (imutável):**
> - Um único índice por contrato (ex: IPCA)
> - Ciclos anuais de 12 parcelas — o primeiro ciclo é sempre isento
> - O percentual aplicado em cada ciclo é o **acumulado do índice nos 12 meses anteriores**
>
> **Exemplo — Contrato Jan/2023 · 36 parcelas · Índice IPCA:**
>
> ```
> Ciclo 1 → Parcelas  1–12  (ano 2023) → Sem reajuste
> Ciclo 2 → Parcelas 13–24  (ano 2024) → IPCA acumulado de 2023 (jan–dez/2023)
> Ciclo 3 → Parcelas 25–36  (ano 2025) → IPCA acumulado de 2024 (jan–dez/2024)
> ```
>
> O período de referência é sempre os **12 meses do ano anterior ao ciclo**.
> O sistema busca o índice na base (IBGE/FGV) e calcula o acumulado automaticamente.

---

### 10.1 Cálculo Automático

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-01 | **Determinar automaticamente o ciclo atual** — `Reajuste.calcular_ciclo_pendente(contrato)` | P1 | ✅ P1 |
| R-02 | **Calcular acumulado do índice para o período de referência** — `IndiceReajuste.get_acumulado_periodo(...)` com período do ciclo anterior | P1 | ✅ P1 |
| R-03 | **Determinar as parcelas afetadas automaticamente** — ciclo N → parcelas `(N-1)*prazo+1` até `N*prazo` | P1 | ✅ P1 |
| R-04 | **Preview/Simulação dry-run antes de aplicar** — `Reajuste.preview_reajuste(contrato, ciclo, ...)` | P1 | ✅ P1 |
| R-05 | **Desconto sobre o reajuste** — `desconto_percentual` (p.p.) e `desconto_valor` (R$/parcela) | P1 | ✅ P1 |
| R-06 | **Teto e piso configuráveis por contrato** — `Contrato.reajuste_piso/teto`; aplicados após desconto | P2 | ✅ P2 |
| R-07 | **Índice composto** — `Contrato.spread_reajuste` (p.p. adicionados ao índice bruto); snapshot em `Reajuste.spread_aplicado` | P3 | ✅ P3 |
| R-08 | **Reajuste automático via Celery** — `aplicar_reajuste_automatico` reescrita com ciclos corretos; `processar_reajustes_pendentes` para todos os contratos | P3 | ✅ P3 |

---

### 10.2 Interface de Aplicação

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-09 | **Formulário de reajuste simplificado** — modal pré-preenchido com ciclo/índice/período/% ao abrir | P1 | ✅ P1 |
| R-10 | **Tabela de prévia por parcela** — parcela / vencimento / valor atual / % / valor novo / diferença | P1 | ✅ P1 |
| R-11 | **Tela de Reajustes Pendentes** — lista agrupada por imobiliária com botão Aplicar | P1 | ✅ P1 |
| R-12 | **Alerta de boletos já emitidos** — aviso no modal com lista das parcelas afetadas | P1 | ✅ P1 |
| R-13 | **Confirmação dupla para deflação** — alert especial + segunda confirmação quando % final < 0 | P2 | ✅ P2 |
| R-14 | **Histórico de reajustes na tela do contrato** — ciclo / ref. / % bruto / desconto / % aplicado / data / operador / desfazer | P2 | ✅ P2 |
| R-15 | **Aplicação em lote** — checkboxes na tela de pendentes; modal com desconto global; endpoint `POST /reajustes/aplicar-lote/`; relatório por contrato | P3 | ✅ P3 |

---

### 10.3 Validações e Regras de Negócio

| # | Item | Prioridade | Status |
|---|------|------------|--------|
| R-16 | **Validar sequência de ciclos na UI** — `clean()` no model valida sequência; erro surfaçado via JSON na view | P1 | ✅ P1 |
| R-17 | **Bloquear geração de boleto enquanto ciclo pendente** — `pode_gerar_boleto` implementado | P1 | ✅ P1 |
| R-18 | **Audit log** — `Reajuste.usuario` (FK auth.User) + `Reajuste.ip_address`; capturados em todas as views de aplicação | P2 | ✅ P2 |
| R-19 | **Desfazer reajuste automático** — `excluir_reajuste` estendida para todos os reajustes (não só manuais); reverte parcelas + intermediárias + `ciclo_reajuste_atual` | P3 | ✅ P3 |

---

### 10.4 Ordem de Execução — Concluída

| Fase | Itens | Status |
|------|-------|--------|
| **1 (P1)** | R-01, R-02, R-03, R-04 | ✅ Concluído |
| **2 (P1)** | R-09, R-10, R-05 | ✅ Concluído |
| **3 (P1)** | R-11, R-12, R-16, R-17 | ✅ Concluído |
| **4 (P2)** | R-06, R-14, R-18, R-13 | ✅ Concluído |
| **5 (P3)** | R-07, R-08, R-15, R-19 | ✅ Concluído |

---

## 11. ADEQUAÇÃO AO CONTRATO REAL — Minuta Parque das Nogueiras ✅ CONCLUÍDO

> **Contexto:** Análise comparativa do contrato real "MINUTA L 13 Q C 22072020.pdf"
> (promessa de compra e venda de lote, Sete Lagoas/MG) contra a estrutura de dados do sistema.
> Gaps identificados e implementados.

---

### 11.1 Gaps de Estrutura de Dados

| # | Gap identificado | Solução implementada | Status |
|---|-----------------|----------------------|--------|
| G-01 | ~~**Vendedor pessoa física**~~ — `Contrato.imobiliaria` (FK `Imobiliária/Beneficiário`) já é o vendedor; campos `vendedor_nome`/`vendedor_cpf_cnpj` eram redundantes | Campos removidos (`migration 0006`). Ver G-10 para suporte a vendedor PF | ❌ Removido |
| G-02 | **Índice de fallback** — INPC substitui IGPM se extinto (cláusula contratual) | `Contrato.tipo_correcao_fallback`; usado automaticamente em `preview_reajuste()` quando índice principal sem dados | ✅ |
| G-03 | **Taxa de fruição** — 0,5%/mês sobre valor atualizado em rescisão pelo comprador | `Contrato.percentual_fruicao` (default 0,5000%) | ✅ |
| G-04 | **Multa penal de rescisão** — 10% do valor atualizado retido pelo vendedor | `Contrato.percentual_multa_rescisao_penal` (default 10,0000%) | ✅ |
| G-05 | **Despesas administrativas de rescisão** — 12% retido | `Contrato.percentual_multa_rescisao_adm` (default 12,0000%) | ✅ |
| G-06 | **Taxa de cessão de direitos** — 3% sobre valor atualizado | `Contrato.percentual_cessao` (default 3,0000%) | ✅ |
| G-07 | **Juros compostos escalantes por ano** — ano 1 fixo, ano 2: 0,60% a.m., ano 3: 0,65%… ano 7+: 0,85% a.m. | Novo model `TabelaJurosContrato` (ciclo_inicio, ciclo_fim, juros_mensal); `get_juros_para_ciclo()` usado no `preview_reajuste()` com precedência sobre `spread_reajuste` fixo | ✅ |
| G-08 | **`calcular_saldo_devedor()` incorreto** para contratos com tabela price / juros compostos embutidos | Reescrito: soma `valor_atual` das parcelas NORMAL não pagas (correto para qualquer estrutura de parcelas, inclusive price) | ✅ |
| G-09 | **`Imovel.identificacao` como texto livre** — genérico o suficiente para lote, apto, sala, endereço DF, quarto de hotel | Mantido genérico; help_text atualizado com exemplos variados. Campos específicos `quadra`/`lote` propostos e revertidos por decisão de design | ✅ |

---

### 11.2 Gaps Pendentes (Fora do Escopo Atual)

> Estes gaps existem no contrato real mas requerem features completas, não apenas campos.

| # | Gap | Complexidade | Prioridade |
|---|-----|--------------|------------|
| G-10 | **`Imobiliaria` suporta apenas PJ (CNPJ obrigatório)** — para contratos onde o vendedor é pessoa física (CPF), o model `Imobiliaria` não é adequado. Solução: adicionar `tipo_pessoa` (PF/PJ) e tornar `cnpj` opcional quando PF, com campo `cpf` para pessoa física | Média | P2 |
| G-11 | **Cálculo de rescisão** — tela/endpoint que aplica fruição + multa penal + adm e gera valor de devolução | Alta | P3 |
| G-12 | **Cálculo de cessão** — tela para calcular taxa de cessão e registrar transferência de comprador | Média | P3 |
| G-13 | **Taxa condominial (APMRPN)** — 1,32% de fração ideal mensal, cobrada separado do contrato | Alta | P4 |
| G-14 | **Testemunhas do contrato** — campos testemunha_1_nome, testemunha_1_cpf etc. para impressão do contrato | Baixa | P4 |
| G-15 | **Prazo para escritura** — prazo de 60+30 dias após quitação para lavratura de escritura | Média | P4 |
| G-16 | **Juros de mora pro rata die** — 0,033%/dia (contrato usa esta fórmula, não 1%/mês simples) | Média | P3 |

---

### 11.3 Admin e Ferramentas

| # | Item | Status |
|---|------|--------|
| A-01 | `TabelaJurosContrato` registrado no Django Admin (`TabelaJurosContratoAdmin` + `TabelaJurosInline` no Contrato) | ✅ |
| A-02 | `ContratoAdmin` fieldsets atualizados com novos campos (Cláusulas Contratuais, fallback, spread, piso/teto). Fieldset Vendedor removido — coberto pelo FK `imobiliaria` | ✅ |
| A-03 | Link **"Dados de Teste"** adicionado no menu Admin do `base.html` (visível para staff/superuser) | ✅ |
| A-04 | Página de Dados de Teste inclui counter de `TabelaJurosContrato` + atualiza via JS pós-geração | ✅ |

---

### 11.4 Migration

| Migration | App | Conteúdo |
|-----------|-----|----------|
| `contratos/0005_contrato_clausulas_vendedor_tabela_juros` | contratos | Cria `TabelaJurosContrato`; adiciona ao `Contrato`: `tipo_correcao_fallback`, `percentual_fruicao`, `percentual_multa_rescisao_penal`, `percentual_multa_rescisao_adm`, `percentual_cessao`, `vendedor_nome`, `vendedor_cpf_cnpj` (estes dois removidos na 0006) |
| `contratos/0006_remove_vendedor_campos_redundantes` | contratos | Remove `vendedor_nome` e `vendedor_cpf_cnpj` do `Contrato` — redundantes com `imobiliaria` FK |

---

## Ordem de Execução Recomendada

| Fase | Escopo | Seções | Status |
|------|--------|--------|--------|
| **1** | Correções críticas de infraestrutura | 1 | ✅ |
| **2** | ⭐ **Reajuste — Formulário + Preview + Pendentes** | 10 (Fase 1–2) | ✅ |
| **3** | Testes P1 (apps sem cobertura) | 7.1 | ✅ |
| **4** | ⭐ **Reajuste — Acumulado + Histórico + Auditoria** | 10 (Fase 3–4) | ✅ |
| **5** | ⭐ **Reajuste — Índice composto + Lote + Celery** | 10 (Fase 5) | ✅ |
| **6** | ⭐ **Adequação ao contrato real — estrutura de dados** | 11 | ✅ |
| **7** | Frontend P2 (telas principais) | 3 (P2) | — |
| **8** | APIs P2 | 4 (P2) | — |
| **9** | Testes P2 (views e APIs) | 7.2 | — |
| **10** | Permissões e segurança | 6 | — |
| **11** | Cálculos contratuais avançados (rescisão, cessão, mora pro rata) | 11 (G-10, G-11, G-15) | — |
| **12** | Testes P3/P4 + CI/CD | 7.3, 7.4, 8 | — |
| **13** | Frontend P3/P4 | 3 (P3, P4) | — |
| **14** | Documentação | 9 | — |

---

## Resumo Quantitativo

| Categoria | P1 | P2 | P3 | P4 | Total | Concluído |
|-----------|----|----|----|----|-------|-----------|
| Infraestrutura | 3 | 2 | 1 | — | 6 | ✅ 3/3 P1 |
| Backend — Regras | — | 8 | 3 | 1 | 12 | ✅ 8/8 P2 |
| Reajuste | 4 | 4 | 7 | — | 15+4=19 | ✅ 19/19 |
| Contrato Real (gaps) | — | — | 9 | 6 | 15 | ✅ 9/9 (P3) · 6 pendentes P4 |
| Frontend | — | 17 | 15 | 3 | 35 | — |
| APIs | — | 6 | 5 | — | 11 | — |
| Celery | — | 2 | 2 | 1 | 5 | — |
| Permissões | — | 4 | 4 | 2 | 10 | — |
| Testes | 104 | ~164 | ~37 | ~41 | ~346 | ✅ 104/104 P1 |
| CI/CD | — | 2 | 4 | 2 | 8 | — |
| Documentação | — | — | 1 | 3 | 4 | — |
| **Total** | **~111** | **~209** | **~88** | **~59** | **~467** | |

### ✅ Fases concluídas nesta sessão (2026-04-01)
- **Seção 11 completa:** Análise do contrato real + 9 gaps estruturais implementados
- `TabelaJurosContrato` — juros escalantes por ciclo (0,60% → 0,85% a.m.)
- `calcular_saldo_devedor()` — corrigido para tabela price e juros compostos
- Fallback de índice automático em `preview_reajuste()`
- 6 novos campos no `Contrato` (vendedor, cláusulas contratuais)
- Admin, navegação e dados de teste atualizados
