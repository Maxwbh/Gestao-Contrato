# ROADMAP — Novas Implementações

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Última atualização:** 2026-04-01 (rev 6)

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
| 2.9 | Validar sequência de ciclos de reajuste (não pular) | ✅ V-09: validação em `aplicar_reajuste_pagina` e `aplicar_reajuste_contrato`: verifica `calcular_ciclo_pendente` antes de aceitar POST, retorna erro claro se ciclo fora de ordem; modelo `Reajuste.clean()` já tinha validação de cadeia (ciclo N exige ciclo N-1 aplicado) |
| 2.10 | Segunda via de boleto com juros/multa calculados | ✅ `BoletoService.gerar_segunda_via()` reutiliza nosso_número existente, sobrepõe valor com juros/multa do dia; view `segunda_via_boleto` GET=preview com totais atualizados, GET?download=1=PDF fresco via BRCobrança; botão "Segunda Via" em `detalhe_parcela.html` |
| 2.11 | WhatsApp/SMS — testes end-to-end com Twilio |

### P4 — Baixo
| # | Item |
|---|------|
| 2.12 | PIX — linha digitável e QR Code no boleto | ⚠️ Prioridade **extremamente baixa** / Alta complexidade — TO_DO 2050 |

---

## 3. FRONTEND — TEMPLATES E INTERFACES

### P2 — Alto
| # | Tela/Componente | Status |
|---|-----------------|--------|
| 3.1 | Aba Histórico de Reajustes (contrato) | ✅ Implementado como R-14 |
| 3.2 | Aba Boletos gerados (lista com status e download) | ✅ Card "Boletos Gerados" em `contrato_detail.html` |
| 3.3 | Wizard de criação de contrato (4 etapas) | ✅ step1 a step4 |
| 3.4 | Dashboard Contabilidade: gráfico recebimentos mensais | ✅ Chart.js barras em `dashboard.html` |
| 3.5 | Dashboard Contabilidade: gráfico inadimplência por imobiliária | ✅ Chart.js linha em `dashboard.html` |
| 3.6 | Dashboard Contabilidade: tabela vencimentos consolidados | ✅ Tabela próximos 3 meses em `dashboard.html` |
| 3.7 | Dashboard Imobiliária: filtros na lista de contratos | ✅ Status + imobiliária em `contrato_list.html` |
| 3.8 | Dashboard Imobiliária: busca rápida por contrato/comprador | ✅ Busca textual em `contrato_list.html` |
| 3.9 | Dashboard Imobiliária: ações em lote (gerar boletos) | ✅ `abrirModalGerarLote()` em `contrato_list.html` |
| 3.10 | Dashboard Imobiliária: fluxo de caixa previsto vs realizado | ✅ Chart.js bar chart em `dashboard_imobiliaria.html` consome `api_imobiliaria_fluxo_caixa` — 3 séries: Previsto/Realizado/Pendente, 12 meses (-5 a +6), tooltip em R$, mês corrente destacado |
| 3.11 | Gestão de Boletos: interface geração em lote com progresso | ✅ `gerar_carne` + templates |
| 3.12 | Gestão de Boletos: download ZIP de vários boletos | ✅ `download_zip_boletos` em `financeiro/views.py` + URL `contrato/<id>/boletos/zip/` + botão ZIP na aba Parcelas de `contrato_detail.html` |
| 3.13 | Gestão de Parcelas: seleção múltipla para ações em lote | ✅ Seleção múltipla implementada |
| 3.14 | Gestão de Parcelas: juros/multa/total nas vencidas | ✅ Cálculo dinâmico em `listar_parcelas` view |
| 3.15 | Sidebar recolhível com indicadores de pendências | ✅ `desktop-sidebar` em `base.html`: 240px↔60px toggle (localStorage), badges de parcelas vencidas/reajustes/boletos/CNAB via `api_sidebar_pendencias`; tooltip CSS em modo colapsado; oculto em mobile (usa sidenav Materialize) |
| 3.16 | Toast de sucesso/erro padronizado | ✅ `window.showToast()` global em `base.html` |
| 3.17 | Centro de notificações com badge | ✅ Badge navbar + endpoint `api_reajustes_pendentes_count` |

### P3 — Médio
| # | Tela/Componente |
|---|-----------------|
| 3.18 | Aba Relatórios do Contrato | ✅ Seção colapsável "Relatórios & Exportações" em `contrato_detail.html`: KPIs financeiros (valor total, pago, saldo, progresso); botões CSV (parcelas a pagar, pagas, posição); botão Imprimir; usa `exportar_relatorio` existente filtrado por contrato |
| 3.19 | Aba Histórico de Pagamentos (comprovantes) | ✅ Card "Histórico de Pagamentos" em `contrato_detail.html` — tabela com data, valor, juros, multa, forma de pagamento, link para comprovante; `ContratoDetailView.get_context_data` passa `historico_pagamentos` via queryset |
| 3.20 | Configurações Contabilidade (dados, usuários, imobiliárias) | ✅ View `contabilidade_configuracoes` exibe dados cadastrais (form inline), imobiliárias vinculadas e usuários com acesso em uma única página; URL `/core/contabilidades/<pk>/configuracoes/`; botão "Configurações" (⚙️) na lista de contabilidades |
| 3.21 | Exportar relatório consolidado (PDF, Excel) | ✅ View `exportar_relatorio_consolidado` gera Excel multi-aba (A Pagar 90d / Pagas 90d / Posição Contratos) ou PDF multi-seção; botão "Consolidado" na tela de prestações a pagar; URL `/financeiro/relatorios/exportar-consolidado/` |
| 3.22 | Tela de reajuste pendente (índice, prévia, aplicar lote) | ✅ `reajustes_pendentes` view + template: lista agrupada por imobiliária, paginada; seleção em lote com checkbox; botão "Aplicar Selecionados" abre modal com preview; bulk apply via `aplicar_reajuste_lote` |
| 3.23 | Histórico de reajustes aplicados | ✅ View `listar_reajustes` lista todos os reajustes globalmente; card "Reajustes" em `contrato_detail.html` exibe histórico por contrato com ciclo, índice, período, % bruto/aplicado, parcelas e usuário |
| 3.24 | Upload de comprovante de pagamento | ✅ `registrar_pagamento` aceita `multipart/form-data`; cria `HistoricoPagamento` com `forma_pagamento` e `comprovante` (FileField já existia no model); template atualizado com campos forma_pagamento e comprovante |
| 3.25 | Notificar comprador inadimplente | ✅ View `notificar_inadimplente` (POST) envia e-mail + WhatsApp para comprador de parcela vencida; botão "Notificar Comprador" em `detalhe_parcela.html` (visível apenas para parcelas vencidas não pagas); registra `Notificacao` com status ENVIADO; URL `parcelas/<pk>/notificar/` |
| 3.26 | Configurações de boleto por imobiliária | ✅ Já implementado: campos `percentual_multa_padrao`, `percentual_juros_padrao`, `instrucao_padrao`, etc. no model `Imobiliaria`; `ImobiliariaForm` inclui todos os campos; `Contrato.get_config_boleto()` usa configuração da imobiliária quando `usar_config_boleto_imobiliaria=True` |
| 3.27 | Configurações de notificação (dias, canais) | ✅ CRUD completo para `RegraNotificacao`: view `listar_regras_notificacao`, `criar_regra_notificacao`, `editar_regra_notificacao`, `excluir_regra_notificacao`, `toggle_regra_notificacao`; template com tabela + modais; link no dropdown "Notificações" da navbar; URLs sob `/notificacoes/regras/` |
| 3.28 | Gerenciamento de usuários por imobiliária | ✅ Model `AcessoUsuario` + CRUD completo (`AcessoUsuarioListView`, `AcessoUsuarioCreateView`, etc.) em `core/views.py`; `AcessoUsuarioForm` em `core/forms.py`; URL `/core/acessos/`; acessível via menu Admin |
| 3.29 | Card de resumo reutilizável | ✅ `templates/components/summary_card.html` — suporta icon, variant (Bootstrap), value, subtitle, href, badge; uso: `{% include 'components/summary_card.html' with icon="..." title="..." value="..." %}` |
| 3.30 | Tabela paginada com filtros (componente genérico) | ✅ `templates/components/paginated_table.html` — cabeçalho com busca, tabela responsiva, paginação Bootstrap automática com elipses |
| 3.31 | Gráficos barras/pizza/linha (componente genérico) | ✅ `templates/components/chart_card.html` — Chart.js bar/line/pie/doughnut; suporta api_url (fetch) ou chart_var (inline); paleta Bootstrap; tooltip R$ automático |
| 3.32 | Modal de confirmação reutilizável | ✅ `templates/components/confirm_modal.html` — modal Bootstrap + fallback confirm() para Materialize; API JS: `confirmarAcao({...})` e `confirmarExclusao(nome, url)` |

### P4 — Baixo
| # | Tela/Componente |
|---|-----------------|
| 3.33 | Aba Documentos (upload contrato assinado) |
| 3.34 | Upload de logo da imobiliária |
| 3.35 | Seletor de período reutilizável |

---

## 4. APIs — ENDPOINTS PENDENTES

### P2 — Alto ✅ CONCLUÍDO (Fase 9)
| Endpoint | Descrição | Status |
|----------|-----------|--------|
| `GET /financeiro/api/contabilidade/vencimentos/` | Tabela com filtros (período, imobiliária, status) | ✅ `api_contabilidade_vencimentos` |
| `POST /financeiro/api/contabilidade/boletos/gerar/massa/` | Geração em massa | ✅ alias de `api_gerar_boletos_lote` |
| `GET /financeiro/api/imobiliaria/<id>/vencimentos/` | Filtros por período e comprador | ✅ `api_imobiliaria_vencimentos` |
| `GET /financeiro/api/imobiliaria/<id>/fluxo-caixa/` | Previsão mensal vs realizado | ✅ `api_imobiliaria_fluxo_caixa` |
| `GET /portal/api/vencimentos/` | Filtros por período e status | ✅ `api_portal_vencimentos` |
| `GET /portal/api/boletos/` | Lista com filtros | ✅ `api_portal_boletos` |

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

### P2 — Alto ✅ CONCLUÍDO (via HTTP tasks — Render Free Tier não suporta Celery)
| Task | Frequência | Descrição | Status |
|------|------------|-----------|--------|
| `alerta_vencimentos_semana` | Segunda-feira | Para Contabilidade | ✅ `enviar_notificacoes_sync()` em `core/tasks.py`; disparado via `POST /api/tasks/run-all/` |
| `alerta_inadimplencia_diario` | Diário | Para Imobiliária | ✅ `enviar_inadimplentes_sync()` em `core/tasks.py`; disparado via `POST /api/tasks/run-all/` |

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
| Bootstrap local | ✅ Materialize, FontAwesome, AG Grid e Flatpickr servidos localmente via `static/vendor/`; templates base.html, portal_base.html, login, registro, setup atualizados; único CDN restante é Google Fonts (Material Icons) |
| Logging | ✅ Loggers por app (financeiro, contratos, core, notificacoes); django.request/security com AdminEmailHandler em produção; formato verbose com PID e thread |

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

## 10. REAJUSTE DE PARCELAS ✅ CONCLUÍDO

> **Objetivo:** tornar o fluxo de reajuste claro, seguro e auditável — do cálculo à confirmação.
> Implementação completa: cálculo automático do acumulado, preview por parcela, interface dedicada,
> histórico, auditoria, desfazer e aplicação em lote — todos os itens R-01 a R-19 concluídos.

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
| G-07 | **Juros compostos escalantes por ano** — ano 1 fixo, ano 2: 0,60% a.m., ano 3: 0,65%… ano 7+: 0,85% a.m. | `TabelaJurosContrato` + cálculo Tabela Price correto: `preview_reajuste()` e `aplicar_reajuste()` distinguem **MODO TABELA PRICE** (PMT recalculado sobre saldo atualizado, todas as parcelas restantes) de **MODO SIMPLES** (multiplicação por fator, apenas ciclo atual). `_calcular_pmt()` implementa `PMT = PV × i / (1−(1+i)^−n)` | ✅ |
| G-08 | **`calcular_saldo_devedor()` incorreto** para contratos com tabela price / juros compostos embutidos | Reescrito: soma `valor_atual` das parcelas NORMAL não pagas (correto para qualquer estrutura de parcelas, inclusive price) | ✅ |
| G-09 | **`Imovel.identificacao` como texto livre** — genérico o suficiente para lote, apto, sala, endereço DF, quarto de hotel | Mantido genérico; help_text atualizado com exemplos variados. Campos específicos `quadra`/`lote` propostos e revertidos por decisão de design | ✅ |

---

### 11.2 Gaps — Status Atualizado

| # | Gap | Complexidade | Prioridade | Status |
|---|-----|--------------|------------|--------|
| G-10 | **`Imobiliaria` PF/PJ** — `tipo_pessoa` (PF/PJ), `cpf` adicionados; `cnpj` e `razao_social` tornados opcionais; `clean()` valida documento conforme tipo; `documento` property; `core migration 0003` idempotente; admin e build.sh atualizados | Média | P2 | ✅ |
| G-11 | **Cálculo de rescisão** — `Contrato.calcular_rescisao()` (fruição × meses + multa penal + desp. adm.); view `calcular_rescisao_view`; template `calcular_rescisao.html`; URL `<pk>/rescisao/`; botão na tela do contrato | Alta | P3 | ✅ |
| G-12 | **Cálculo de cessão** — `Contrato.calcular_cessao()`; view `calcular_cessao_view`; template `calcular_cessao.html`; URL `<pk>/cessao/`; botão na tela do contrato | Média | P3 | ✅ |
| G-13 | **Taxa condominial (APMRPN)** — fora do escopo do sistema | Alta | — | 🚫 Fora do escopo |
| G-14 | **Testemunhas do contrato** — fora do escopo do sistema | Baixa | — | 🚫 Fora do escopo |
| G-15 | **Prazo para escritura** — fora do escopo do sistema | Média | — | 🚫 Fora do escopo |
| G-16 | **Juros de mora pro rata die** — `Contrato.calcular_mora_pro_rata()`: `taxa_diaria = percentual_juros_mora / 30`; usado em `calcular_rescisao()` para base de cálculo correto | Média | P3 | ✅ |

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

## 12. CNAB — REMESSA E RETORNO ✅ CONCLUÍDO

> **Objetivo:** geração de arquivos de remessa CNAB 240/400 por escopo (Conta, Imobiliária, Contrato, Individual) com controle de duplicatas e integração com BRCobrança.

---

### 12.1 Serviço CNABService (`financeiro/services/cnab_service.py`)

| # | Item | Status |
|---|------|--------|
| C-01 | **`gerar_remessa()`** — gera 1 arquivo por `ContaBancaria`; chama `POST /api/remessa` no BRCobrança; fallback local em CNAB 400 simplificado se container indisponível | ✅ |
| C-02 | **`_gerar_remessa_local()`** — gera CNAB 400 localmente (fallback sem BRCobrança); campos corretos (header, detalhe, trailer) | ✅ |
| C-03 | **`obter_boletos_sem_remessa()`** — filtros por `conta_bancaria`, `imobiliaria_id`, `contrato_id`; usa `itens_remessa__isnull=True` para controle de duplicata | ✅ |
| C-04 | **`obter_boletos_em_remessa_pendente()`** — retorna boletos já em remessa com status `GERADO` (não enviada), para exibir aviso na UI | ✅ |
| C-05 | **`gerar_remessas_por_escopo()`** — recebe lista de `parcela_ids`, agrupa por `conta_bancaria`, chama `gerar_remessa()` para cada grupo; retorna lista de remessas geradas + erros | ✅ |
| C-06 | **`_parsear_numero_dv()`** — helper para separar número e dígito verificador de agência/conta (`"3073-0"` → `("3073", "0")`); corrige bug anterior que mesclava número+DV | ✅ |
| C-07 | **Campo `imobiliaria` correto** — `_montar_dados_boleto()` usa `contrato.imobiliaria` (FK direto no Contrato) em vez de `contrato.imovel.imobiliaria` | ✅ |
| C-08 | **Campos BRCobrança alinhados** — `agencia`, `agencia_dv`, `conta_corrente`, `digito_conta` separados; `dados_empresa` e boleto usam mesma nomenclatura | ✅ |

---

### 12.2 Views (`financeiro/views.py`)

| # | Item | Status |
|---|------|--------|
| V-01 | **`gerar_arquivo_remessa()` GET** — filtros por escopo (tudo / imobiliária / contrato / conta); boletos agrupados por `conta_bancaria` em `grupos_conta`; `today` para destaque de vencidos | ✅ |
| V-02 | **`gerar_arquivo_remessa()` POST** — chama `gerar_remessas_por_escopo()`; redireciona para detalhe se 1 remessa, para lista se múltiplas | ✅ |
| V-03 | **`listar_arquivos_remessa()`** — filtro adicional por imobiliária via `conta_bancaria__imobiliaria_id` | ✅ |
| V-04 | **`api_cnab_boletos_disponiveis()`** — parâmetros `conta_bancaria_id` (opcional), `imobiliaria_id` (opcional), `contrato_id` (opcional) | ✅ |

---

### 12.3 Templates

| # | Item | Status |
|---|------|--------|
| T-01 | **`gerar_remessa.html`** — seletor de escopo com dropdowns contextuais; boletos agrupados por conta; checkbox "todos desta conta" + checkbox global; contador de selecionados; botão gerar habilitado dinamicamente; aviso de boletos em remessa pendente com link | ✅ |
| T-02 | **`listar_remessas.html`** — filtro por imobiliária adicionado ao lado do filtro de conta e status | ✅ |

---

### 12.4 Script de Dados de Teste (`gerar_dados_teste.py`)

| # | Item | Status |
|---|------|--------|
| D-01 | **`limpar_dados()`** — inclui `ArquivoRemessa.objects.all().delete()` e `ArquivoRetorno.objects.all().delete()` antes de limpar Parcela | ✅ |
| D-02 | **`simular_boletos_gerados()`** — simula até 3 boletos por contrato com status `GERADO`, `nosso_numero`, `conta_bancaria` vinculada; sem chamar BRCobrança — dados suficientes para demonstrar geração de remessa | ✅ |
| D-03 | **Output do `handle()`** — inclui contagem de `TabelaJurosContrato` e boletos simulados | ✅ |

---

### 12.5 Controle de Duplicatas

| Mecanismo | Descrição |
|-----------|-----------|
| `itens_remessa__isnull=True` | Filtra parcelas sem nenhum ItemRemessa — exclui automaticamente da lista de disponíveis |
| `obter_boletos_em_remessa_pendente()` | Retorna as que *já têm* remessa GERADO — exibidas como aviso na UI |
| `gerar_remessas_por_escopo()` + `Parcela.filter(itens_remessa__isnull=True)` | Validação dupla na geração: mesmo se o usuário enviar IDs de parcelas já em remessa, o service as filtra novamente |

---

### 12.6 BRCobrança Integration

| Item | Detalhe |
|------|---------|
| **API endpoint** | `POST /api/remessa` · `POST /api/retorno` |
| **Container** | `docker run -p 9292:9292 maxwbh/boleto_cnab_api` |
| **URL configurável** | `settings.BRCOBRANCA_URL` (default `http://localhost:9292`) |
| **Fallback** | `ConnectionError` → `_gerar_remessa_local()` — CNAB 400 gerado em Python |
| **Payload** | `{"bank": "banco_brasil", "type": "cnab240", "data": [...]}` |
| **Bancos suportados** | BB (001), Santander (033), Caixa (104), Bradesco (237), Itaú (341), Sicredi (748), Sicoob (756) e outros |

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
| **7** | ⭐ **CNAB Remessa — por escopo, BRCobrança, anti-duplicata** | 12 | ✅ |
| **8** | Frontend P2 (telas principais) | 3 (P2) | ✅ |
| **9** | APIs P2 | 4 (P2) | ✅ |
| **10** | Testes P2 (views e APIs) | 7.2 | — |
| **11** | Permissões e segurança | 6 | — |
| **12** | Cálculos contratuais avançados (rescisão, cessão, mora pro rata) | 11 (G-10, G-11, G-15) | — |
| **13** | ⭐ **Contrato Tabela Price + Intermediárias (HU-360)** | 13 | ✅ |
| **14** | ⭐ **Sistema de Amortização: Tabela Price e SAC** | 14 | ✅ |
| **15** | ⭐ **Regras de Bloqueio de Boleto — Cascata + Lote** | 15 | ✅ |
| **16** | Testes P3/P4 + CI/CD | 7.3, 7.4, 8 | — |
| **17** | Frontend P3/P4 | 3 (P3, P4) | — |
| **18** | Documentação | 9 | — |

---

## 13. HU-360 — CONTRATO TABELA PRICE COM JUROS ESCALANTES E INTERMEDIÁRIAS

> **História de Usuário (HU-360):**
> Como usuário quero criar um contrato de 360 parcelas com:
> - Imóvel R$350.000 · Entrada R$100.000 · Financiado R$250.000
> - Intermediárias de R$5.000 a cada 6 meses
> - Correção anual pelo IPCA (a cada 12 meses)
> - Juros compostos escalantes (Tabela Price):
>   - Ciclo 1 (parc. 1–12): 0% a.m. — parcelas lineares (isenção)
>   - Ciclo 2 (parc. 13–24): 0,60% a.m. → PMT recalculado na 13ª
>   - Ciclo 3 (parc. 25–36): 0,65% a.m. → PMT recalculado na 25ª
>   - Ciclo 4+ (parc. 37–360): 0,70% a.m. → PMT recalculado na 37ª
> - **Bloqueio de boleto:** se hoje ≥ data prevista do reajuste do ciclo e o reajuste ainda não foi aplicado, nenhum boleto do ciclo pode ser gerado

---

### 13.0 Análise do Sistema Atual

#### O que já funciona ✅

| Item | Localização | Descrição |
|------|-------------|-----------|
| `TabelaJurosContrato` | `contratos/models.py` | Juros por ciclo (ciclo_inicio/ciclo_fim/juros_mensal) |
| `TabelaJurosContrato.get_juros_para_ciclo()` | `contratos/models.py` | Retorna taxa para o ciclo N |
| `preview_reajuste()` MODO TABELA PRICE | `financeiro/models.py` | PMT recalculado sobre saldo atualizado pelo IPCA |
| `aplicar_reajuste()` MODO TABELA PRICE | `financeiro/models.py` | Aplica PMT a todas as parcelas restantes |
| `_calcular_pmt()` | `financeiro/models.py` | `PMT = PV × i / (1−(1+i)^−n)` |
| `calcular_saldo_devedor()` | `contratos/models.py` | Soma `valor_atual` de NORMAL não pagas (correto para price) |
| `calcular_ciclo_pendente()` | `financeiro/models.py` | Detecta reajuste pendente com verificação de data |
| `PrestacaoIntermediaria` model | `contratos/models.py` | FK→Contrato; O2O→Parcela; valor, mes_vencimento, paga |
| `Contrato.pode_gerar_boleto(numero_parcela)` | `contratos/models.py` | Verifica ciclo via `calcular_ciclo_parcela()` (dinâmico) |
| `TabelaJurosInline` | `contratos/admin.py` | Edição de TabelaJurosContrato dentro do Contrato (Admin) |
| `gerar_parcelas()` linear ciclo 1 | `contratos/models.py` | Parcelas 1–12 geradas com `valor_financiado / n` (correto: ciclo 1 sem juros) |

#### Bugs Identificados ❌

| # | Bug | Arquivo | Linha | Impacto |
|---|-----|---------|-------|---------|
| **BUG-01** | ~~`Parcela.pode_gerar_boleto()` usa `self.ciclo_reajuste` (campo atualizado só após reajuste) — para parcelas recém-criadas `ciclo_reajuste` = 1 → bloco nunca dispara para parcelas do ciclo 2+~~ | `financeiro/models.py` | — | ✅ **Corrigido (Seção 15)** — cascata completa do ciclo 2 ao ciclo da parcela |
| **BUG-02** | ~~`Contrato.pode_gerar_boleto()` bloqueia para ciclo > 1 sem verificar data — bloqueia mesmo antes do reajuste ser devido~~ | `contratos/models.py` | — | ✅ **Corrigido (Seção 15)** — cascata + data + helper `get_primeiro_ciclo_bloqueado()` |

#### Funcionalidades Ausentes — ✅ Todas Resolvidas

| # | Lacuna | Solução | Status |
|---|--------|---------|--------|
| **L-01** | Formulário web de criação de contrato não suporta `TabelaJurosContrato` inline (só Django Admin) | Wizard step2 implementa `TabelaJurosContrato` inline | ✅ |
| **L-02** | Não há criação em lote de intermediárias (padrão: "R$X a cada Y meses") | Wizard step3: criação em lote com padrão (R$X a cada Y meses) e manual | ✅ |
| **L-03** | Regra de negócio não definida: PMT considera PV das intermediárias ou não? | Parametrizado via `intermediarias_reduzem_pmt`; decisão em 13.1 | ✅ |
| **L-04** | Geração de boleto para intermediária não está disponível na web UI | `gerar_boleto_intermediaria()` + `intermediaria_list.html` | ✅ |
| **L-05** | Sem preview de parcelas com projeção de reajustes futuros na criação | step4 + `api_preview_parcelas` projeta primeiras 24 parcelas | ✅ |
| **L-06** | Sem validação de consistência financeira na criação | Validação financeira implementada no wizard (`_calcular_resumo`) | ✅ |

---

### 13.1 Definição de Regra de Negócio — L-03 — Decisão Tomada ✅

> **Questão:** no cálculo da parcela mensal, as intermediárias são deduzidas do PV?
>
> **Decisão:** Opção A — Parametrizado via `intermediarias_reduzem_pmt`. Implementado no Wizard step1 e `_salvar_contrato()`.

| Opção | Fórmula parcela inicial | Comportamento |
|-------|------------------------|---------------|
| **A — Independente** (recomendado para loteamentos) | `PMT = valor_financiado / n` (ciclo 1 sem juros) | Intermediárias reduzem saldo devedor no reajuste seguinte — PMT diminui a cada ciclo |
| **B — Dedução de PV** | `PV_liquido = valor_financiado − PV(intermediárias, taxa, n)` → PMT sobre PV_liquido | PMT inicial menor; intermediárias não afetam recalculate |

**Recomendação:** Opção A. É como o contrato Parque das Nogueiras funciona (minuta analisada na seção 11): as intermediárias são parcelas extras de amortização e reduzem o saldo devedor calculado na próxima recalculação de PMT.

---

### 13.2 BUG-01 — Fix `Parcela.pode_gerar_boleto()` ✅ CORRIGIDO (ver Seção 15)

> **Nota:** O fix implementado supera esta especificação — ver **Seção 15** para o algoritmo de cascata completo (ciclo 2 até ciclo da parcela).

**Problema:** usa `self.ciclo_reajuste` (campo pós-reajuste) em vez de calcular o ciclo dinamicamente.

**Comportamento atual:**
```
Parcela 15 criada → ciclo_reajuste = 1 (padrão)
pode_gerar_boleto() → self.ciclo_reajuste (1) > 1? NÃO → retorna True ❌
```

**Comportamento correto:**
```
Parcela 15, prazo=12 → ciclo = (15-1)//12 + 1 = 2
data_reajuste_ciclo2 = data_contrato + 12 meses
hoje >= data_reajuste? SIM → reajuste aplicado? NÃO → retorna False ✓
```

**Fix a implementar:**
```python
# financeiro/models.py — Parcela.pode_gerar_boleto()
prazo = self.contrato.prazo_reajuste_meses
ciclo_da_parcela = (self.numero_parcela - 1) // prazo + 1

if ciclo_da_parcela > 1:
    from dateutil.relativedelta import relativedelta
    from django.utils import timezone as tz
    data_reajuste_prevista = (
        self.contrato.data_contrato
        + relativedelta(months=(ciclo_da_parcela - 1) * prazo)
    )
    if tz.now().date() >= data_reajuste_prevista:
        reajuste_aplicado = Reajuste.objects.filter(
            contrato=self.contrato,
            ciclo=ciclo_da_parcela,
            aplicado=True
        ).exists()
        if not reajuste_aplicado:
            return False, (
                f"Reajuste do ciclo {ciclo_da_parcela} pendente "
                f"desde {data_reajuste_prevista.strftime('%d/%m/%Y')}. "
                f"Execute o reajuste antes de gerar boletos."
            )
```

---

### 13.3 BUG-02 — Fix `Contrato.pode_gerar_boleto()` ✅ CORRIGIDO (ver Seção 15)

> **Nota:** O fix implementado supera esta especificação — ver **Seção 15** para o algoritmo de cascata completo (ciclo 2 até ciclo da parcela).

**Problema:** bloqueia imediatamente ao entrar no ciclo 2, mesmo antes da data do reajuste.

**Fix:** replicar a lógica de data acima:
```python
# contratos/models.py — Contrato.pode_gerar_boleto()
ciclo_parcela = self.calcular_ciclo_parcela(numero_parcela)
if ciclo_parcela == 1:
    return True, "Primeiro ciclo - liberado"

from dateutil.relativedelta import relativedelta
from django.utils import timezone as tz
data_reajuste_prevista = (
    self.data_contrato + relativedelta(months=(ciclo_parcela - 1) * self.prazo_reajuste_meses)
)
if tz.now().date() < data_reajuste_prevista:
    return True, f"Reajuste do ciclo {ciclo_parcela} ainda não vencido (previsto {data_reajuste_prevista.strftime('%d/%m/%Y')})"

from financeiro.models import Reajuste
reajuste_aplicado = Reajuste.objects.filter(
    contrato=self, ciclo=ciclo_parcela, aplicado=True
).exists()
if reajuste_aplicado:
    return True, f"Reajuste do ciclo {ciclo_parcela} aplicado"

return False, (
    f"Reajuste do ciclo {ciclo_parcela} pendente "
    f"desde {data_reajuste_prevista.strftime('%d/%m/%Y')}. "
    f"Execute o reajuste antes de gerar boletos."
)
```

---

### 13.4 Plano de Implementação

#### Fase 1 — Bugs Críticos (P1) 🔴

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| HU-01 | Fix `Parcela.pode_gerar_boleto()` — cálculo dinâmico de ciclo + verificação de data | `financeiro/models.py` | ✅ |
| HU-02 | Fix `Contrato.pode_gerar_boleto()` — adicionar verificação de data | `contratos/models.py` | ✅ |
| HU-03 | Campos `intermediarias_reduzem_pmt` + `intermediarias_reajustadas` no Contrato; migration 0007 | `contratos/models.py` | ✅ |

#### Fase 2 — Formulário de Criação Completo (P1) 🔴

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| HU-04 | `ContratoWizardView` — wizard 4 etapas com sessão Django | `contratos/views.py` | ✅ |
| HU-05 | `TabelaJurosForm` — linhas dinâmicas de faixas de juros | `contratos/forms.py` | ✅ |
| HU-06 | `IntermediariaPadraoForm` + `IntermediariaManualForm` — padrão (intervalo+n) ou manual | `contratos/forms.py` | ✅ |
| HU-07 | Templates wizard — step1 a step4 com progress bar e Bootstrap 5 | `templates/contratos/wizard/` | ✅ |

#### Fase 3 — Preview e Validações (P2) 🟡

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| HU-08 | `api_preview_parcelas` — endpoint GET/POST que retorna projeção das primeiras 24 parcelas (ciclo, juros, intermediárias) | `contratos/views.py` | ✅ |
| HU-09 | Validação financeira na preview: PMT base = `valor_financiado - soma_inter` se `reduzem_pmt=True` | `contratos/views.py` | ✅ |
| HU-10 | Preview de parcelas no step4: tabela JS via `api_preview_parcelas` com marcação de início de ciclo e intermediárias | `templates/contratos/wizard/step4_preview.html` | ✅ |

#### Fase 4 — Geração de Boleto para Intermediárias (P2) 🟡

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| HU-11 | `gerar_boleto_intermediaria()` — cria Parcela tipo INTERMEDIARIA e vincula via `parcela_vinculada` | `contratos/views.py` | ✅ (já existia) |
| HU-12 | Template `intermediaria_list.html` com tabela, estatísticas e botão gerar boleto | `templates/contratos/intermediaria_list.html` | ✅ |
| HU-13 | Alert na tela do contrato: intermediárias vencidas sem boleto + seção resumo | `templates/contratos/contrato_detail.html` | ✅ |

---

### 13.5 Fluxo Completo da História de Usuário

```
CRIAÇÃO DO CONTRATO (HU-04 a HU-10)
┌─────────────────────────────────────────────────────────┐
│ 1. Dados básicos                                         │
│    Imovel R$350k · Entrada R$100k · 360 parcelas        │
│    Dia vencimento: 10 · IPCA · prazo_reajuste: 12 meses │
├─────────────────────────────────────────────────────────┤
│ 2. Juros Escalantes (TabelaJurosContrato)               │
│    Ciclo 1 (1–12):   0,0000% a.m.                       │
│    Ciclo 2 (13–24):  0,6000% a.m.                       │
│    Ciclo 3 (25–36):  0,6500% a.m.                       │
│    Ciclo 4 (37–∞):   0,7000% a.m.                       │
├─────────────────────────────────────────────────────────┤
│ 3. Intermediárias (padrão ou manual)                    │
│    Padrão: R$5.000 a cada 6 meses → 60 registros       │
│    Meses: 6, 12, 18, 24, 30 ... 360                     │
├─────────────────────────────────────────────────────────┤
│ 4. Preview                                              │
│    Parc. 1–12:  R$ 694,44/mês  (250.000/360)           │
│    Parc. 13+:  PMT recalc. com IPCA + 0,6% a.m.        │
│    Parc. 25+:  PMT recalc. com IPCA + 0,65% a.m.       │
└─────────────────────────────────────────────────────────┘
          ↓ SALVAR
PARCELAS GERADAS: 360 × R$694,44 (ajuste no último para fechar)

FLUXO MENSAL
┌─────────────────────────────────────────────────────────┐
│ Meses 1–12: gerar boleto → OK (ciclo 1)                 │
├─────────────────────────────────────────────────────────┤
│ Mês 6: Intermediária vence                              │
│   → Alert na tela do contrato                           │
│   → Gerar boleto da intermediária (HU-11)               │
├─────────────────────────────────────────────────────────┤
│ Mês 12: último do ciclo 1                               │
│   → Reajuste IPCA pendente surge no dashboard           │
├─────────────────────────────────────────────────────────┤
│ Mês 13: hoje >= data_reajuste E reajuste NÃO aplicado  │
│   → pode_gerar_boleto() → False ← BUG-01 fix           │
│   → Sistema exige reajuste antes de gerar boleto        │
├─────────────────────────────────────────────────────────┤
│ Usuário aplica reajuste (IPCA acumulado do ano)         │
│   → MODO TABELA PRICE:                                  │
│      saldo_devedor atualizado pelo IPCA                 │
│      PMT = saldo × 0,006 / (1-(1,006)^-348)            │
│      Parcelas 13–360 atualizadas                        │
│   → Intermediárias reajustadas pelo IPCA               │
├─────────────────────────────────────────────────────────┤
│ Mês 13+: pode_gerar_boleto() → True                    │
└─────────────────────────────────────────────────────────┘
```

---

### 13.6 Decisões Confirmadas pelo Usuário (2026-04-01)

| # | Questão | Decisão |
|---|---------|---------|
| Q-01 | **Intermediárias afetam PMT inicial?** | **Parametrizável** — campo `intermediarias_reduzem_pmt` (bool) no Contrato. Se `True`, PMT = `(valor_financiado - soma_intermediarias) / n`. |
| Q-02 | **Intermediárias são reajustadas pelo IPCA?** | **Parametrizável** — campo `intermediarias_reajustadas` (bool) no Contrato. Se `True`, valor é atualizado pelo mesmo índice a cada ciclo. |
| Q-03 | **Intermediária vence junto com parcela normal?** | **Boleto separado** — `PrestacaoIntermediaria` gera Parcela tipo `INTERMEDIARIA` independente. |
| Q-04 | **Ciclo 1 com taxa 0,0000%** — constar na `TabelaJurosContrato`? | **Explícito** — ciclo 1 sempre registrado na tabela com `juros_mensal=0`. |
| Q-05 | **Wizard em múltiplas etapas ou formulário único?** | **Wizard 4 etapas** — sessão Django; step1 dados básicos, step2 juros, step3 intermediárias, step4 preview + salvar. |

---

## 15. REGRAS DE BLOQUEIO DE BOLETO — CASCATA E LOTE ✅ CONCLUÍDO

> **Contexto:** a implementação anterior de `pode_gerar_boleto()` só verificava o ciclo próprio da
> parcela. Se o ciclo 2 estava pendente mas a parcela pertencia ao ciclo 3 (data ainda não vencida),
> o bloqueio não era aplicado. Além disso, geração em lote (carnê) não respeitava o limite do ciclo atual.
> O usuário especificou as regras corretas na sessão de 2026-04-01.

---

### 15.1 Regras de Negócio (Especificação)

| # | Regra |
|---|-------|
| R-B01 | **Se hoje ≥ data de qualquer reajuste pendente (ciclo N)**, todos os boletos do ciclo N em diante ficam bloqueados — não apenas os do ciclo N |
| R-B02 | **Geração em lote (carnê)** só é permitida até o último boleto do ciclo atual (último ciclo totalmente reajustado) |
| R-B03 | **Boletos de ciclos futuros** (data ainda não chegou) só podem ser gerados individualmente |
| R-B04 | **Intermediárias sem reajuste** (`intermediarias_reajustadas=False`) podem ser geradas a qualquer momento, independente de bloqueio |
| R-B05 | **Intermediárias com reajuste** seguem a mesma regra das parcelas normais |
| R-B06 | **Índice FIXO** — sem reajuste, sem bloqueio; todos os boletos sempre liberados |

---

### 15.2 Implementação

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| B-01 | `Parcela.pode_gerar_boleto()` — loop cascata ciclo 2..ciclo_da_parcela; break se data futura; bloqueia ao encontrar primeiro ciclo pendente | `financeiro/models.py` | ✅ |
| B-02 | `Contrato.pode_gerar_boleto()` — mesma lógica de cascata | `contratos/models.py` | ✅ |
| B-03 | `Contrato.get_primeiro_ciclo_bloqueado()` — helper; retorna número do primeiro ciclo pendente (ou None) | `contratos/models.py` | ✅ |
| B-04 | `gerar_boleto_intermediaria()` — pula verificação se `contrato.intermediarias_reajustadas=False` | `contratos/views.py` | ✅ |
| B-05 | `gerar_carne()` — calcula `max_parcela_lote` antes do loop; ciclos futuros/pendentes bloqueados em lote com mensagem orientativa | `financeiro/views.py` | ✅ |

---

### 15.3 Algoritmo de Cascata

```
para ciclo_check = 2 até ciclo_da_parcela:
    data_reajuste = data_contrato + (ciclo_check - 1) * prazo_meses
    se hoje < data_reajuste:
        break  ← ciclo futuro, não bloqueia
    se Reajuste.aplicado(ciclo_check) == False:
        return False, "Reajuste ciclo {ciclo_check} pendente desde {data}"
return True, "Liberado"
```

**Exemplo — contrato Jan/2024, prazo 12, ciclo 2 pendente (hoje >= Jan/2025, reajuste não aplicado):**
```
Parcela 12 (ciclo 1) → loop vazio (ciclo 1, não verifica) → Liberada ✓
Parcela 13 (ciclo 2) → ciclo 2: hoje >= Jan/2025, não aplicado → Bloqueada ✗
Parcela 14 (ciclo 2) → ciclo 2: hoje >= Jan/2025, não aplicado → Bloqueada ✗
...
Parcela 25 (ciclo 3) → ciclo 2: hoje >= Jan/2025, não aplicado → Bloqueada ✗ (cascata)
...
Parcela 360 (ciclo 30) → ciclo 2: hoje >= Jan/2025, não aplicado → Bloqueada ✗ (cascata)

→ Nenhum boleto pode ser gerado da parcela 13 à 360 até o reajuste do ciclo 2 ser aplicado.
```

---

### 15.4 Lógica de Limite de Lote (`gerar_carne`)

```
max_parcela_lote = None  # sem limite por padrão
para ciclo = 2..total_ciclos+1:
    data_reajuste = data_contrato + (ciclo-1) * prazo
    se hoje < data_reajuste:
        max_parcela_lote = (ciclo-1) * prazo  ← limita ao ciclo anterior
        break
    se não aplicado(ciclo):
        max_parcela_lote = (ciclo-1) * prazo  ← limita ao ciclo anterior
        break
```

---

## 16. MAPA INTERATIVO DE LOTES ⚙️ EM ANDAMENTO

> **Contexto:** pesquisa de mercado (2026-04-02) identificou mapa interativo como feature central em
> todos os principais concorrentes (LoteWin, Terravista, LotNet, SmartIPTU). A implementação inicial
> usa Leaflet + OSM. Esta seção documenta a evolução para um mapa de nível profissional.

---

### 16.1 Mapa da Lista de Imóveis ⚙️ MELHORADO (2026-04-02)

| # | Item | Status |
|---|------|--------|
| M-01 | Tiles Carto Voyager (visual igual ao Google Maps, gratuito, sem API key) | ✅ |
| M-02 | Tiles Esri Satellite + Dark (switcher de camadas) | ✅ |
| M-03 | Leaflet.markercluster — agrupamento de marcadores | ✅ |
| M-04 | DivIcon customizado: círculo verde (disponível) / vermelho (vendido) | ✅ |
| M-05 | Filtro por loteamento no mapa (dropdown JS, sem reload) | ✅ |
| M-06 | Filtro por status no mapa (disponível / vendido) | ✅ |
| M-07 | Legenda inline no canto inferior direito | ✅ |
| M-08 | Popup com hover — abre ao passar o mouse sobre o marcador | ✅ |
| M-09 | Contador dinâmico de marcadores visíveis | ✅ |
| M-10 | Todos os imóveis com coord. passados ao mapa (não paginado) | ✅ |

### 16.2 Página Dedicada por Loteamento — TODO

| # | Item | Prioridade |
|---|------|-----------|
| M-11 | Página `/imoveis/loteamento/{slug}/` — mapa dedicado do empreendimento | P2 | ✅ `loteamento_detalhe` em `core/views.py` + URL `imoveis/loteamento/<str:nome>/` + template `loteamento_detalhe.html` com mapa Leaflet + lista filtrável por status |
| M-12 | Estatísticas do loteamento: total, disponíveis %, valor médio por lote | P2 | ✅ KPI cards (total, disponíveis, vendidos, valor médio/min/max) + barra de progresso proporcional na página do loteamento |
| M-13 | Polígonos de lote (boundaries) com `lat/lng` de cada vértice — modelo `LotePoligono` | P3 |
| M-14 | Upload de planta baixa (imagem) como overlay no mapa | P3 |
| M-15 | Link direto "Ver no Google Maps / Waze" no popup do marcador | P3 |
| M-16 | Geolocalização do usuário para mostrar lotes próximos | P4 |

---

## 17. DASHBOARD KPIs E GRÁFICOS ✅ CONCLUÍDO

> **Contexto:** todos os concorrentes têm dashboard com KPIs visuais. O sistema atual tem um
> dashboard básico. Esta seção especifica o redesign completo.

### 17.1 KPIs Principais (cards topo)

| # | Métrica | Cálculo | Status |
|---|---------|---------|--------|
| K-01 | Total de lotes / Vendidos / Disponíveis | count() por Imovel.disponivel | ✅ `context['total_lotes']`, `lotes_vendidos`, `lotes_disponiveis` |
| K-02 | Arrecadação do mês atual | sum(valor_pago) de Parcelas pagas no mês | ✅ `parcelas_mes_atual.valor_recebido` em `dashboard.html` |
| K-03 | Inadimplência ativa | count(Parcelas vencidas não pagas) | ✅ `parcelas_vencidas` + `valor_em_atraso` em `dashboard.html` |
| K-04 | Contratos ativos | count(Contrato status=ATIVO) | ✅ `context['contratos_ativos']` em `DashboardFinanceiroView` |
| K-05 | Saldo total da carteira | sum(valor_atual) de Parcelas não pagas | ✅ `valor_a_receber` em `dashboard.html` |
| K-06 | Reajustes pendentes | count(contratos com ciclo pendente) | ✅ `context['reajustes_pendentes']` via `Reajuste.calcular_ciclo_pendente()` |

### 17.2 Gráficos

| # | Gráfico | Biblioteca | Prioridade | Status |
|---|---------|-----------|-----------|--------|
| G-01 | Arrecadação mensal (barras) — 12 meses | Chart.js | P2 | ✅ `chartRecebimentos` — barras Recebido vs Esperado 12 meses |
| G-02 | Inadimplência por faixa de atraso (pizza) — 1–30d, 31–60d, 61–90d, 90d+ | Chart.js | P2 | ✅ `inadimplencia_faixas` em `api_dashboard_dados()` |
| G-03 | Fluxo de caixa previsto vs. realizado (linha) | Chart.js | P2 | ✅ `chartFluxoCaixa` — linha 6 meses passados + 6 futuros em `api_dashboard_dados()` |
| G-04 | Parcelas vencendo esta semana (tabela destacada) | Template | P1 | ✅ `context['parcelas_semana']` (D-04) |
| G-05 | Top 5 contratos com maior saldo devedor | Template | P3 | ✅ `context['top5_saldo_devedor']` com anotação Sum |

### 17.3 Implementação

| # | Item | Arquivo | Prioridade | Status |
|---|------|---------|-----------|--------|
| D-01 | `DashboardFinanceiroView` — enriquecer com KPIs reais | `financeiro/views.py` | P2 | ✅ K-01..K-06, D-04, G-05 |
| D-02 | API `api_kpis_dashboard` — endpoint JSON para gráficos | `financeiro/views.py` | P2 | ✅ G-01, G-02, G-03 em `api_dashboard_dados()` |
| D-03 | Template redesign com Chart.js | `templates/financeiro/dashboard.html` | P2 | ✅ Cards KPI + Chart.js + tabelas D-04 + G-05 |
| D-04 | Widget "Parcelas da semana" no dashboard principal | template | P1 | ✅ `parcelas_semana` context var |

---

## 18. SIMULADOR DE RENEGOCIAÇÃO / ANTECIPAÇÃO ✅ PARCIALMENTE CONCLUÍDO

> **Referência:** LoteWin, SGL e SIVI oferecem simulação de antecipação de parcelas com desconto.

| # | Item | Descrição | Prioridade | Status |
|---|------|-----------|-----------|--------|
| R-01 | Tela simulador: quantas parcelas antecipar + % desconto | GET view, sem persistir | P2 | ✅ `simulador_antecipacao` GET — `/financeiro/contrato/<id>/simulador/` |
| R-02 | Preview: valor original vs. valor antecipado (economia total) | render server-side | P2 | ✅ POST `action=preview` — tabela com economia sem persistir |
| R-03 | Aplicar antecipação: cria HistoricoPagamento com flag `antecipado=True` | POST view | P2 | ✅ POST `action=aplicar` — quita + `HistoricoPagamento(antecipado=True)` + migration 0007 |
| R-04 | Renegociação: alterar prazo/valor de parcelas em atraso | — | P3 | ✅ `renegociar_parcelas` view em `financeiro/views.py` + template `renegociar_parcelas.html` — seleção múltipla, nova data/valor por parcela, data global para lote, zera juros/multa; botão em `contrato_detail.html` |
| R-05 | Recibo de quitação antecipada (PDF) | — | P3 | ✅ `financeiro/services/recibo_service.py` ReportLab + `download_recibo_antecipacao` view + URL `recibo_antecipacao` + botões em `contrato_detail.html` |

---

## 19. NOTIFICAÇÕES E COBRANÇA AUTOMÁTICA ✅ PARCIALMENTE CONCLUÍDO

> **Referência:** GELOT, SGL e LoteWin enviam alertas por WhatsApp/e-mail automaticamente.

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| N-01 | E-mail automático D-5 antes do vencimento da parcela | P2 | ✅ `enviar_notificacoes_sync()` em `core/tasks.py` + deduplicação via `Notificacao` model + POST `/api/tasks/enviar-notificacoes/` |
| N-02 | E-mail de inadimplência após D+3 | P2 | ✅ `enviar_inadimplentes_sync()` em `core/tasks.py` + `task_run_all` inclui N-02 + POST `/api/tasks/enviar-inadimplentes/` + `NOTIFICACAO_DIAS_INADIMPLENCIA=3` |
| N-03 | Régua de cobrança configurável (D-5, D+3, D+10, D+30) | P3 | ✅ `RegraNotificacao` model em `notificacoes/models.py` + `TipoGatilho` (ANTES/APOS) + admin com `list_editable` + `_processar_regra()` em `core/tasks.py` — fallback automático para N-01/N-02 quando nenhuma regra configurada |
| N-04 | Integração WhatsApp (Evolution API / Z-API) | P3 | ✅ `ConfiguracaoWhatsApp` agora suporta 4 provedores: Twilio, Meta (Cloud API), Evolution API v2 (`/message/sendText/{instancia}`), Z-API (`/send-text`). `ServicoWhatsApp` despacha pelo `provedor` do config ativo. Migration `0004_add_whatsapp_providers` adiciona `api_url`, `api_key`, `instancia`, `client_token`. Admin com fieldsets colapsáveis por provedor. |
| N-05 | Push notification portal comprador | P4 | ⏳ |

---

## 20. MELHORIAS DE UX / INTERFACE ✅ PARCIALMENTE CONCLUÍDO

> **Referência:** pesquisa de concorrentes e inspeção de sistemas líderes (2026-04-02).

| # | Item | Descrição | Prioridade | Status |
|---|------|-----------|-----------|--------|
| U-01 | Dark mode toggle (persistido em localStorage) | Carto dark já disponível no mapa | P3 | ✅ Botão lua/sol na navbar desktop e mobile; `body.dark-mode` CSS em `custom.css` cobre cards, tabelas, forms, modals, dropdowns, sidenav; persistido em `localStorage['gc_dark_mode']` |
| U-02 | Timeline visual de ciclos na tela de parcelas | Linha do tempo horizontal com ciclos | P2 | ✅ JS inline em `contrato_detail.html` — ciclos coloridos por estado (concluído/ativo/atraso/bloqueado) + % reajuste aplicado |
| U-03 | Simulador inline de parcelas no cadastro de contrato | Preview em tempo real enquanto preenche | P2 | ✅ Painel "Simulação Rápida" em `step1_basico.html` — PMT Price/SAC em tempo real + taxa editável |
| U-04 | Exportar relatórios em Excel (openpyxl) | Complementar ao PDF | P3 | ✅ `openpyxl==3.1.2` adicionado em `requirements.txt`; 4 templates de relatório reconstruídos com filtros, totalizadores, botões CSV/Excel/PDF; `exportar_relatorio` view já suportava Excel via `RelatorioService.exportar_para_excel()` |
| U-05 | Portal do comprador — redesign mobile-first | Compradores acessam via celular | P2 | ✅ `portal_base.html` + todos os templates — nav bottom, stat chips, cards mobile |
| U-06 | Busca global (Ctrl+K) — busca rápida por contrato, comprador, lote | P3 | ✅ `api_busca_global` em `core/views.py` + modal overlay em `base.html` — debounce, nav teclado ↑↓/Enter/Esc, highlight `<mark>` |
| U-07 | Impressão de carnê de pagamento (PDF multi-página) | P3 | ✅ Já implementado — `download_carne_pdf` + `gerar_carne_pdf` em `financeiro/services/carne_service.py` + modal de seleção de parcelas em `contrato_detail.html` |

---

## Resumo Quantitativo

| Categoria | P1 | P2 | P3 | P4 | Total | Concluído |
|-----------|----|----|----|----|-------|-----------|
| Infraestrutura | 3 | 2 | 1 | — | 6 | ✅ 3/3 P1 |
| Backend — Regras | — | 8 | 3 | 1 | 12 | ✅ 8/8 P2 |
| Reajuste | 4 | 4 | 7 | — | 15+4=19 | ✅ 19/19 |
| Contrato Real (gaps) | — | — | 9 | 6 | 15 | ✅ 9/9 implementados · 6 pendentes |
| CNAB Remessa | — | 8 | — | — | 8 | ✅ 8/8 |
| HU-360 Tabela Price | 2 | 9 | 2 | — | 13 | ✅ 13/13 |
| SAC / Tabela Price | 1 | 4 | — | — | 5 | ✅ 5/5 |
| Bloqueio Boleto (Cascata) | 2 | 3 | — | — | 5 | ✅ 5/5 |
| Mapa Interativo (Seção 16) | — | 5 | 6 | 1 | 12 | ✅ 10/10 M-01..M-10 |
| Dashboard KPIs (Seção 17) | 1 | 5 | 2 | — | 8 | ✅ 8/8 (K-01..K-06, G-01..G-05, D-01..D-04) |
| Simulador Antecipação (Seção 18) | — | 3 | 2 | — | 5 | ✅ 3/3 P2 (R-01..R-03) · ⏳ 2 P3 |
| Notificações (Seção 19) | — | 2 | 2 | 1 | 5 | ✅ 2/2 P2 (N-01, N-02) · ⏳ 3 P3/P4 |
| UX / Interface (Seção 20) | — | 3 | 4 | — | 7 | ✅ 3/3 P2 (U-02, U-03, U-05) · ⏳ 4 P3 |
| Frontend | — | 17 | 15 | 3 | 35 | ⚠️ ~4/17 P2 |
| APIs | — | 6 | 5 | — | 11 | — |
| Celery | — | 2 | 2 | 1 | 5 | — |
| Permissões | — | 4 | 4 | 2 | 10 | — |
| HU Boleto/Carnê/Remessa (Seção 21) | — | 10 | — | — | 10 | ✅ 10/10 |
| OFX Extrato Bancário (Seção 22) | — | 5 | — | — | 5 | ✅ 5/5 |
| Testes | 104 | ~164 | ~37 | ~41 | ~346 | ✅ 104/104 P1 · ✅ 508 passando (12 Simulador + 12 Notificações) |
| CI/CD | — | 2 | 4 | 2 | 8 | — |
| Documentação | — | — | 1 | 3 | 4 | — |
| **Total** | **~117** | **~251** | **~107** | **~61** | **~536** | |

### ✅ Fases concluídas (2026-04-01)

**Seção 11 — Adequação ao Contrato Real:**
- `TabelaJurosContrato` — juros escalantes por ciclo (0,60% → 0,85% a.m.)
- `calcular_saldo_devedor()` — corrigido para tabela price e juros compostos
- Fallback de índice automático em `preview_reajuste()`
- Cláusulas contratuais no `Contrato` (fruição, rescisão, cessão)
- `preview_reajuste()` e `aplicar_reajuste()` com **MODO TABELA PRICE** e `_calcular_pmt()`
- Bug corrigido: intermediárias usavam percentual bruto → agora `perc_final` (com piso/teto)
- `criar_reajuste_ciclo()` depreciado com `DeprecationWarning`
- Admin, navegação e dados de teste atualizados

**Seção 12 — CNAB Remessa:**
- Geração por escopo: Todos / Por Imobiliária / Por Contrato / Por Conta Bancária
- Auto-split por `conta_bancaria` → 1 arquivo de remessa por conta
- `gerar_remessas_por_escopo()` agrupa parcelas e chama `gerar_remessa()` para cada grupo
- Controle de duplicatas: `itens_remessa__isnull=True` + aviso UI de pendentes
- `_parsear_numero_dv()`: corrige bug de agência/conta (separar número e DV)
- `imobiliaria` corrigido: `contrato.imobiliaria` em vez de `contrato.imovel.imobiliaria`
- Campos BRCobrança alinhados: `agencia`, `agencia_dv`, `conta_corrente`, `digito_conta`
- Filtro por imobiliária na lista de remessas
- Script de dados de teste: `simular_boletos_gerados()` + limpeza de `ArquivoRemessa/Retorno`

**Seção 13 — HU-360 Contrato Tabela Price + Intermediárias (Fases 1 a 4) — lacunas L-01..L-06 todas fechadas:**
- BUG-01 fix: `Parcela.pode_gerar_boleto()` — cálculo dinâmico de ciclo + verificação de data de reajuste
- BUG-02 fix: `Contrato.pode_gerar_boleto()` — só bloqueia se `hoje >= data_reajuste_prevista` E sem reajuste aplicado
- Novos campos: `intermediarias_reduzem_pmt` e `intermediarias_reajustadas` no Contrato (migration 0007)
- Wizard 4 etapas em sessão Django: step1 dados básicos, step2 juros escalantes, step3 intermediárias (padrão/manual/nenhuma), step4 preview + salvar
- 4 forms: `ContratoWizardBasicoForm`, `TabelaJurosForm`, `IntermediariaPadraoForm`, `IntermediariaManualForm`
- `_salvar_contrato()`: cria Contrato + TabelaJurosContrato + PrestacaoIntermediaria em `transaction.atomic()`; recalcula PMT se `intermediarias_reduzem_pmt=True`
- Botão "Novo Contrato (Wizard)" na lista de contratos; admin atualizado com fieldset de intermediárias
- `api_preview_parcelas` — projeção das primeiras 24 parcelas (ciclo, juros, intermediárias marcadas) via GET/POST JSON
- Preview interativo no step4 do wizard: JS carrega tabela via API, marca início de ciclo com badge
- Alert no detalhe do contrato: intermediárias vencidas sem boleto; seção resumo com tabela e botão gerar boleto
- Template `intermediaria_list.html` — lista completa com estatísticas, paginação, ação gerar boleto via AJAX
- URL `/contratos/wizard/api/preview-parcelas/` para o endpoint de preview

**Seção 14 — Sistema de Amortização Tabela Price e SAC:**
- `TipoAmortizacao` (TextChoices: PRICE | SAC) adicionado a `contratos/models.py`
- Campo `tipo_amortizacao` no `Contrato` com default=PRICE (migration 0008)
- Campos `amortizacao` + `juros_embutido` (DecimalField null) na `Parcela` (migration financeiro 0005)
- `Parcela._calcular_price_tabela(pv, taxa, n)` — retorna lista (pmt, amort, juros) para Tabela Price
- `Parcela._calcular_sac_tabela(pv, taxa, n)` — retorna lista (pmt, amort, juros) para SAC
- `Contrato.recalcular_amortizacao(base_pv)` — recalcula todas as parcelas NORMAL com o sistema correto; chamado pelo wizard após criar TabelaJuros
- `Contrato.calcular_saldo_devedor()` — SAC usa soma de `amortizacao` (principal real); Price usa soma de `valor_atual`
- `Parcela.preview_reajuste()` — modo SAC: saldo corrigido → nova amort constante → tabela decrescente
- `Reajuste.aplicar_reajuste()` — modo SAC: recalcula e persiste amortizacao + juros_embutido por parcela
- Wizard step1: campo `tipo_amortizacao` com painel explicativo JS (Price vs SAC)
- Wizard step4: exibe sistema, taxa ciclo 1, PMT inicial e último (SAC); preview de parcelas mostra breakdown amort/juros para SAC
- `api_preview_parcelas`: suporte a `tipo_amortizacao=SAC`; retorna `amortizacao` e `juros_embutido` por parcela
- Admin: `tipo_amortizacao` no fieldset "Configurações de Parcelas"

**Seção 15 — Regras de Bloqueio de Boleto — Cascata + Lote:**
- `Parcela.pode_gerar_boleto()` reescrito: verifica em **cascata** do ciclo 2 até o ciclo da parcela — se qualquer ciclo intermediário venceu sem reajuste aplicado, bloqueia a parcela e todas as subsequentes
- `Contrato.pode_gerar_boleto()` reescrito com mesma lógica de cascata
- `Contrato.get_primeiro_ciclo_bloqueado()` — novo helper; retorna o menor ciclo bloqueado (ou None)
- `gerar_boleto_intermediaria()`: respeita `intermediarias_reajustadas` — se `False`, pula verificação de reajuste; intermediárias fixas sempre liberadas independente do ciclo
- `gerar_carne()`: calcula `max_parcela_lote` antes do loop — determina o último ciclo totalmente reajustado; parcelas de ciclos futuros ou bloqueados são recusadas em lote com mensagem orientativa para geração individual
- **Impactos corrigidos:** `ContratoForm` agora inclui `tipo_amortizacao`; `gerar_dados_teste.py` distribui 25% SAC / 75% Price e chama `recalcular_amortizacao()` após TabelaJuros; `contrato_detail.html` exibe badge do sistema de amortização

**Seção 16 — Mapa Interativo:**
- Leaflet.js com marcadores por lote (disponível/vendido); filtros por imobiliária e status

**Seção 17 — Dashboard KPIs (parcial):**
- K-01: lotes totais / vendidos / disponíveis → `context['total_lotes']`, `lotes_vendidos`, `lotes_disponiveis`
- K-06: reajustes pendentes → `context['reajustes_pendentes']` via `Reajuste.calcular_ciclo_pendente()`
- G-02: inadimplência por faixa (1–30d, 31–60d, 61–90d, 90d+) → `inadimplencia_faixas` em `api_dashboard_dados()`
- D-04/G-04: parcelas da semana → `context['parcelas_semana']` (próximos 7 dias)
- G-05: top 5 saldo devedor → `context['top5_saldo_devedor']` com anotação `Sum`

**Seção 21 — HU Gerar Boleto, Carnê e Arquivo Remessa (48 testes):**
- `BoletoService.gerar_carne()` — POST `/api/boleto/multi` no BRCobrança; gera PDF de carnê com N boletos de 1 contrato
- `CarneService.gerar_carne_pdf()` — BRCobrança primário + fallback ReportLab; suporte a 6/12 meses
- `CarneService.gerar_carne_multiplos_contratos()` — PDF único concatenado com carnês de N contratos (limite 50)
- `download_carne_pdf()` — GET lista parcelas disponíveis / POST retorna PDF (limite 60 parcelas)
- `download_carne_pdf_multiplos()` — POST `{contratos: [{contrato_id, parcela_ids}]}` → PDF único
- URLs: `/contrato/<id>/carne/pdf/` e `/api/carne/multiplos/`
- Bug fixes: `Reajuste._calcular_price_tabela` / `_calcular_sac_tabela` (eram chamados em `Parcela`) em `contratos/models.py`, `contratos/views.py` (×2), `financeiro/models.py`
- 48 testes em `tests/unit/financeiro/test_hu_boleto_remessa.py` (HU01–HU12 + CarneService + BoletoService + OFX)

**Seção 22 — OFX: Quitação via Extrato Bancário:**
- `financeiro/services/ofx_service.py` — parser SGML puro sem dependências externas; suporte a SGML e XML-like; auto-detecção de encoding
- `parse_ofx(content)` — extrai lista de `OFXTransaction` (fitid, data, valor, memo)
- `OFXService.processar()` — reconcilia créditos com parcelas não pagas em 4 prioridades: P1 nosso_número no MEMO (ALTA), P2 número do contrato no MEMO (ALTA), P3 valor ±R$0,10 + mesmo mês (MEDIA), P4 valor ±R$0,10 sem data (BAIXA); débitos ignorados automaticamente
- `processar_ofx_upload()` — ponto de entrada para views; suporta `dry_run=True` (reconcilia sem quitar)
- `upload_ofx()` — GET página de upload / POST processa .ofx (limite 5 MB, filtro por imobiliária, dry_run)
- URL: `/cnab/ofx/upload/` → `financeiro:upload_ofx`
- 17 testes: `TestOFXParser` (6), `TestOFXReconciliacao` (6), `TestOFXView` (5)
