# ROADMAP — Novas Implementações

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Última atualização:** 2026-05-04 (rev 16)

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
| 2.11 | WhatsApp/SMS — testes end-to-end com Twilio | 🏦 Débito Técnico (pós-2050) |

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
| 3.33 | Aba Documentos (upload contrato assinado) | 🏦 Débito Técnico (pós-2050) |
| 3.34 | Upload de logo da imobiliária | ✅ `ImageField logo` em `Imobiliaria`; migration `0005_add_logo_imobiliaria`; card de upload no form; exibição no card da lista |
| 3.35 | Seletor de período reutilizável | ✅ `templates/components/period_selector.html` — campos De/Até com Flatpickr, parâmetros via `with`: `action`, `inicio_name/fim_name`, `inicio_val/fim_val`, `btn_label`, `compact`; limpa filtro se valores presentes |

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

### P3 — Médio ✅ CONCLUÍDO
| Endpoint | Descrição | Status |
|----------|-----------|--------|
| `GET /api/contabilidade/relatorios/vencimentos/` | Relatório semanal/mensal/trimestral | ✅ `api_contabilidade_relatorios_vencimentos` |
| `GET /api/contabilidade/imobiliarias/` | Lista com estatísticas | ✅ já existia como `api_imobiliarias_lista` |
| `GET /api/imobiliaria/<id>/pendencias/` | Parcelas vencidas com encargos | ✅ `api_imobiliaria_pendencias` |
| `POST /portal/api/boletos/segunda-via/` | Gerar segunda via com encargos | ✅ `api_portal_segunda_via` |
| `GET /portal/api/boletos/<id>/linha-digitavel/` | Linha digitável | ✅ `api_portal_linha_digitavel` |

---

## 5. TAREFAS CELERY PENDENTES

### P2 — Alto ✅ CONCLUÍDO (via HTTP tasks — Render Free Tier não suporta Celery)
| Task | Frequência | Descrição | Status |
|------|------------|-----------|--------|
| `alerta_vencimentos_semana` | Segunda-feira | Para Contabilidade | ✅ `enviar_notificacoes_sync()` em `core/tasks.py`; disparado via `POST /api/tasks/run-all/` |
| `alerta_inadimplencia_diario` | Diário | Para Imobiliária | ✅ `enviar_inadimplentes_sync()` em `core/tasks.py`; disparado via `POST /api/tasks/run-all/` |

### P3 — Médio ✅ CONCLUÍDO
| Task | Frequência | Descrição | Status |
|------|------------|-----------|--------|
| `relatorio_semanal_incorporadoras` | Segunda-feira | Resumo semanal | ✅ `relatorio_semanal_incorporadoras_sync()` em `core/tasks.py`; endpoint `POST /api/tasks/relatorio-semanal/`; envia e-mail por imobiliária com recebimentos, inadimplência e a-vencer-7d |
| `relatorio_mensal_consolidado` | 1º dia útil | Consolidado mensal | ✅ `relatorio_mensal_consolidado_sync()` em `core/tasks.py`; endpoint `POST /api/tasks/relatorio-mensal/`; envia e-mail consolidado para cada contabilidade com totais por imobiliária |

---

## 6. SISTEMA DE PERMISSÕES

### P2 — Alto ✅ CONCLUÍDO
| Perfil | Descrição | Status |
|--------|-----------|--------|
| Admin Contabilidade | Acesso total a todas imobiliárias | ✅ `usuario_tem_permissao_total()` verifica `is_superuser ou is_staff`; `get_contabilidades_usuario()` retorna todas para admins |
| Admin Imobiliária | Acesso total à sua imobiliária | ✅ `get_imobiliarias_usuario()` filtra via `AcessoUsuario`; staff tem acesso total |
| Filtro por tenant | Todas as views filtram por imobiliária | ✅ `TenantMixin` em `core/views.py` + `get_imobiliarias_usuario()` / `get_contabilidades_usuario()` usados nos dashboards |
| Audit log | Logs de geração de boletos e reajustes | ✅ `Reajuste.usuario` (FK auth.User) + `Reajuste.ip_address`; `Parcela.data_geracao_boleto` (DateTimeField auto) |

### P3 — Médio ✅ CONCLUÍDO
| Perfil/Item | Descrição | Status |
|-------------|-----------|--------|
| Operador Relatórios | Apenas leitura (pode_editar=False, pode_excluir=False) | ✅ `usuario_eh_apenas_leitura()` em `core/models.py` verifica `AcessoUsuario.pode_editar=False AND pode_excluir=False` |
| Gerente Imobiliária | Editar + excluir (pode_editar=True, pode_excluir=True) | ✅ `usuario_pode_excluir()` em `core/models.py` |
| Operador Imobiliária | Apenas editar (pode_editar=True, pode_excluir=False) | ✅ `usuario_pode_editar()` em `core/models.py` |
| Rate limiting | APIs de tarefa e portal | ✅ `core/permissions.py`: decorator `rate_limit(N)` baseado em cache Django (janela 60s); `task_api_rate_limit` (30/min) em todos endpoints de task; `portal_rate_limit` (10/min) em `api_portal_segunda_via`; `public_api_rate_limit` (60/min) e `boleto_lote_rate_limit` (5/min) disponíveis |
| Decoradores | `requer_permissao_total`, `requer_pode_editar`, `requer_pode_excluir`, `requer_acesso_imobiliaria` | ✅ `core/permissions.py` |

### P4 — Baixo
| Item | Descrição |
|------|-----------|
| Visualizador | Apenas consultas — coberto por `usuario_eh_apenas_leitura()` |
| Confirmação | Antes de operações em massa — `confirm_modal.html` já implementado (3.32) |

---

## 7. TESTES AUTOMATIZADOS

**Meta:** > 80% de cobertura | **Atual:** 1139 testes passando (1122 + 17 novos — W-07 BSP Brasileiro 2026-05-06)

### 7.1 P1 — Apps sem nenhum teste (~104 testes) ✅ CONCLUÍDO
| Arquivo | Escopo | Qtd | Status |
|---------|--------|-----|--------|
| `tests/unit/accounts/test_auth_views.py` | login, logout, registro, perfil, alterar senha | 23 | ✅ |
| `tests/unit/notificacoes/test_models.py` | ConfiguracaoEmail, SMS, WhatsApp, Notificacao | 14 | ✅ |
| `tests/unit/notificacoes/test_views.py` | CRUD configs e templates, preview, webhook Evolution (apikey) | 26 | ✅ |
| `tests/unit/notificacoes/test_tasks.py` | envio email/sms, processar pendentes | 8 | ✅ |
| `tests/unit/portal_comprador/test_models.py` | AcessoComprador, LogAcessoComprador | 5 | ✅ |
| `tests/unit/portal_comprador/test_auth.py` | auto-cadastro, login/logout | 29 | ✅ |
| `tests/unit/portal_comprador/test_views.py` | dashboard, contratos, boletos, dados | 21 | ✅ |
| `tests/unit/portal_comprador/test_api.py` | APIs do portal (P2: vencimentos/boletos · P3: linha digitável) | 16 | ✅ |

### 7.2 P2 — Views e APIs faltantes (~164 testes) ✅ CONCLUÍDO
| Arquivo | Escopo | Qtd | Status |
|---------|--------|-----|--------|
| `tests/unit/core/test_models.py` | Modelos do core | 20 | ✅ (preexistente) |
| `tests/unit/core/test_crud_views.py` | CRUD completo | 30 | ✅ (preexistente) |
| `tests/unit/core/test_api_views.py` | APIs bancos, CEP, CNPJ | 17 | ✅ |
| `tests/unit/core/test_dashboard.py` | index, dashboard, setup | 8 | ✅ |
| `tests/unit/core/test_management_commands.py` | gerar_dados_teste, processar_reajustes | 4 | ✅ |
| `tests/unit/contratos/test_crud_views.py` | CRUD contratos | 24 | ✅ |
| `tests/unit/contratos/test_indices_views.py` | CRUD índices | 12 | ✅ |
| `tests/unit/financeiro/test_parcela_views.py` | listar, detalhe, pagar | 19 | ✅ |
| `tests/unit/financeiro/test_boleto_views.py` | gerar, download, carnê | 20 | ✅ |
| `tests/unit/financeiro/test_reajuste_views.py` | listar, aplicar, calcular, aplicar_informado_lote (J-09) | 20 | ✅ |
| `tests/unit/financeiro/test_cnab_views.py` | remessa e retorno | 21 | ✅ |
| `tests/unit/financeiro/test_dashboard_views.py` | dashboards | 9 | ✅ |
| `tests/unit/financeiro/test_rest_api_views.py` | APIs REST | 26 | ✅ |

### 7.3 P3 — Integração e Forms (~37 testes) ✅ CONCLUÍDO
| Arquivo | Escopo | Qtd | Status |
|---------|--------|-----|--------|
| `tests/unit/core/test_forms.py` | Forms core | 9 | ✅ |
| `tests/unit/contratos/test_forms.py` | Forms contratos | 7 | ✅ |
| `tests/integration/test_fluxo_contrato_completo.py` | E2E contrato | 5 | ✅ |
| `tests/integration/test_fluxo_boleto.py` | E2E boleto | 3 | ✅ |
| `tests/integration/test_portal_comprador.py` | E2E portal | 3 | ✅ |
| `tests/integration/test_notificacoes.py` | E2E notificações | 3 | ✅ |

### 7.4 P4 — Segurança e Edge Cases (~41 testes) ✅ CONCLUÍDO
| Arquivo | Escopo | Qtd | Status |
|---------|--------|-----|--------|
| `tests/functional/test_contrato_workflow.py` | E2E completo | 4 | ✅ |
| `tests/functional/test_financeiro_workflow.py` | E2E financeiro | 3 | ✅ |
| `tests/unit/test_security.py` | Autenticação, 404s, isolamento portal | 14 | ✅ |
| `tests/unit/test_edge_cases.py` | Valores extremos, datas limite, reajuste | 12 | ✅ |
| `tests/unit/notificacoes/test_management_commands.py` | enviar_notificacoes, processar_pendentes | 4 | ✅ |
| `tests/unit/financeiro/test_management_commands.py` | processar_reajustes, audit_nosso_numero | 4 | ✅ |
| `tests/unit/financeiro/test_tasks.py` — **J-08** | `atualizar_indices_sync` (7 índices, tolerância a falhas, endpoint auth) | +3 | ✅ |
| `tests/unit/financeiro/test_parcela_reajuste.py` — **Sec 25.1** | `calcular_ciclo_pendente(antecipacao_meses=1)` — detecção 1 mês antes | +2 | ✅ |

### 7.6 Smoke Tests ✅ CONCLUÍDO (P1)
| Arquivo | Escopo | Qtd | Status |
|---------|--------|-----|--------|
| `tests/test_smoke.py` | Todos os endpoints GET do sistema — core, accounts, contratos, financeiro, notificações, portal comprador | 117 | ✅ |

Detectou e corrigiu 1 bug real: `NoReverseMatch` 500 em `/financeiro/relatorios/posicao-contratos/` — template usava `contratos:detalhe_contrato` (inexistente) em vez de `contratos:detalhe`.

### 7.7 Revisão HU — Auditoria de Cobertura (2026-04-28) ✅

Suite de 947 testes executada integralmente. Todos os cenários HU verificados:

| Seção ROADMAP | Arquivo de Teste | Cenários Cobertos | Resultado |
|---------------|-----------------|-------------------|-----------|
| Sec 10 — R-01..R-19 (Reajuste) | `test_parcela_reajuste.py`, `test_reajuste_service.py`, `test_hu_parcelas_reajuste.py` | Ciclo, acumulado, preview, piso/teto, spread, bloqueio, audit, desfazer | ✅ 81/81 pass |
| Sec 12 — C-01..C-08 (CNAB) | `test_cnab_service.py` | gerar_remessa, parsear_numero_dv, fallback local, processar_retorno CNAB400/240 | ✅ pass |
| Sec 13 — HU-360 Price/SAC | `test_hu_parcelas_reajuste.py` | Cenários A-E: FIXO+Price, FIXO+SAC, IPCA+Simples, IPCA+TabelaPrice, IGPM+intermediárias | ✅ 24 pass |
| Sec 15 — B-01..B-05 (Bloqueio) | `test_parcela_reajuste.py` | pode_gerar_boleto cascata, primeiro ciclo livre, após reajuste libera | ✅ pass |
| Sec 18 — R-01..R-05 (Simulador) | `test_simulador_antecipacao.py` | preview, aplicar, desconto 0/completo, redirect, HistoricoPagamento | ✅ 12 pass |
| Sec 21 — BoletoService | `test_boleto_service.py`, `test_hu_boleto_remessa.py` | HU 1..14: gerar, carne, OFX, CNAB retorno, WhatsApp, SMS | ✅ 81 pass |
| Sec 25 — Grid Reajustes Pendentes | `test_reajuste_views.py`, `test_parcela_reajuste.py`, `test_tasks.py` | J-08 (atualizar_indices), J-09 (informado_lote), antecipacao_meses | ✅ +13 novos |
| Sec 26 — Webhook Evolution | `test_views.py` (notificacoes) | apikey obrigatória, apikey inválida, payload, GET=405 | ✅ 5 pass |

**Gaps confirmados sem cobertura (implementações futuras):**
- Sec 27 — Chatbot WhatsApp (C-01..C-16): funcionalidade não implementada; testes serão adicionados ao implementar.

### 7.8 HU Fluxo Completo — Ciclo de Vida do Contrato (2026-05-04) ✅

Suite de 24 testes cobrindo os 9 marcos de negócio do ciclo de vida completo de um contrato imobiliário:

| Marco | Descrição | Classe de Teste |
|-------|-----------|----------------|
| Passo 1-2 | Criação contrato IPCA+Price+TabelaJuros · 36 parcelas · validação PMT | `TestCriacaoContrato` (5 testes) |
| Passo 3   | Pagamento manual via `pagar_parcela_ajax` · HistoricoPagamento MANUAL | `TestPagamentoManual` (3 testes) |
| Passo 4   | Reajuste ciclo 2 — 5% modo legado · fórmula Price composta `PMT × (1+IPCA) × (1+taxa)^prazo` | `TestReajusteCiclo2` (3 testes) |
| Passo 5   | Carnê 20 meses — ciclos 1 e 2 liberados · mock `gerar_boleto` | `TestGeracaoCarne20Meses` (2 testes) |
| Passo 6   | Bloqueio ciclo 3 em lote (`max_parcela_lote` na view) · `pode_gerar_boleto` True p/ ciclo futuro | `TestBloqueioReajusteCiclo3` (2 testes) |
| Passo 7   | Carnê PDF 6 meses · mock `BoletoService.gerar_carne` · Content-Type PDF | `TestCarnePDF6Meses` (3 testes) |
| Passo 8   | Quitação manual 3 parcelas sequencialmente | `TestQuitacaoManualLote` (1 teste) |
| Passo 9   | Quitação via OFX · mock BRCobrança · `nosso_numero_extraido` · HistoricoPagamento OFX | `TestQuitacaoOFX` (4 testes) |
| E2E       | Teste sequencial único percorrendo todos os 9 passos em uma transação | `TestHUFluxoCompleto` (1 teste) |

**Arquivo:** `tests/unit/financeiro/test_hu_fluxo_completo.py` · **Total:** 24 testes · **Resultado:** ✅ 24/24 pass

**Insights de comportamento documentados:**
- Modo Tabela Price: reajuste aplica `PMT × (1 + IPCA) × (1 + taxa_mensal)^prazo` (não simples × IPCA)
- `pode_gerar_boleto()` retorna `True` para ciclos futuros (bloqueio de lote é feito por `max_parcela_lote` em `gerar_carne`)
- `pagar_parcela_ajax` lê `request.POST` (form data), `gerar_carne` e `download_carne_pdf` leem corpo JSON
- OFX reconciliação prioriza `nosso_numero_extraido` para identificar a parcela correta

### 7.9 HU Ciclos Completos Pendentes de Teste E2E — Planejamento (2026-05-04)

Auditoria identificou 4 histórias de usuário totalmente implementadas no sistema mas **sem cobertura de ciclo completo ponta a ponta**. Cada uma exercita caminhos de código radicalmente diferentes do `test_hu_fluxo_completo.py` (básico 36p + 1 TabelaJuros + sem intermediárias).

#### 7.9.1 — HU-360: Juros Escalantes + Intermediárias (PRIORIDADE P1) ✅ IMPLEMENTADO

> **Referência:** Seções 13 e 14 do ROADMAP. Implementação 100% concluída — falta cobertura E2E.

**Contexto:** `TestCenarioA-E` em `test_hu_parcelas_reajuste.py` testam cenários isolados de amortização, mas nenhum percorre os 4 ciclos com taxa escalante + intermediárias + pagamento + reajuste + bloqueio.

**Arquivo proposto:** `tests/unit/contratos/test_hu_360_juros_escalantes.py`

**Cenário do contrato:**
- Imóvel R$ 350.000 · Entrada R$ 100.000 · Financiado R$ 250.000
- 120 parcelas (10 anos) · Dia vencimento: 10 · IPCA · prazo_reajuste: 12 meses
- `intermediarias_reduzem_pmt = True`
- `TabelaJurosContrato`: ciclo 1 = 0,00%, ciclo 2 = 0,60%, ciclo 3 = 0,65%, ciclo 4+ = 0,70%
- Intermediárias: R$ 5.000 a cada 6 meses (semestral), 20 registros
- Contrato criado há 26 meses → ciclos 1, 2 já vencidos; ciclo 3 vencido há 2 meses

**Passos do fluxo E2E (teste sequencial único):**

| Passo | Marco | Cenários de Teste |
|-------|-------|-------------------|
| P1 | Criação do contrato e validação financeira | PMT ciclo 1 = `(PV − Σinter) / n`; 120 parcelas NORMAL criadas; 20 intermediárias criadas; saldo devedor correto |
| P2 | Ciclo 1 — parcela linear sem juros | Todas as 12 parcelas do ciclo 1 com valor `PV_liquido/n`; amortizacao=None (sem TabelaJuros ciclo 1 taxa=0); boleto ciclo 1 liberado |
| P3 | Pagamento da 1ª intermediária (mês 6) | POST `gerar_boleto_intermediaria` → Parcela INTERMEDIARIA criada; pagar via `pagar_parcela_ajax`; `PrestacaoIntermediaria.paga=True` |
| P4 | Reajuste ciclo 2 — IPCA 5% + taxa 0,60% | `preview_reajuste()` com `MODO TABELA PRICE`; PMT_novo = `saldo_atualizado × 0,006 / (1 − (1,006)^-108)`; parcelas 13-120 atualizadas; intermediárias reajustadas em 5% se `intermediarias_reajustadas=True` |
| P5 | Bloqueio e liberação ciclo 2 | Antes do reajuste ciclo 2: `pode_gerar_boleto(13)` = False; após reajuste: = True; gerar carnê parcelas 13-24 liberado |
| P6 | Pagamento 2ª intermediária reajustada | Valor da intermediária reflete +5%; pagar → `PrestacaoIntermediaria.paga=True`; `valor_reajustado` preenchido |
| P7 | Reajuste ciclo 3 — IPCA 4% + taxa 0,65% | PMT recalculado sobre saldo residual com nova taxa 0,65%; parcelas 25-120 atualizadas; ciclo 2 parcelas permanecem no valor do ciclo 2 |
| P8 | Bloqueio cascata ciclo 2 pendente | Zerar reajuste ciclo 2 → `pode_gerar_boleto(25)` = False por cascata (ciclo 2 pendente bloqueia ciclo 3+) |

**Classes de teste focadas (além do E2E):**

| Classe | Testes | Foco |
|--------|--------|------|
| `TestCriacaoHU360` | 5 | PMT com PV_liquido; count parcelas; count intermediárias; saldo devedor; `intermediarias_reduzem_pmt` |
| `TestTabelaJurosEscalantes` | 4 | `get_juros_para_ciclo(1)` = 0; `(2)` = 0.6; `(3)` = 0.65; `(4+)` = 0.70 |
| `TestPagamentoIntermediaria` | 4 | Gerar boleto intermediária; pagar; `PrestacaoIntermediaria.paga`; vencida sem boleto → alert |
| `TestReajusteHU360Ciclo2` | 5 | PMT recalculado corretamente; saldo devedor reflete IPCA; intermediárias reajustadas; ciclo 1 parcelas intactas; `ciclo_reajuste_atual=2` |
| `TestReajusteHU360Ciclo3` | 4 | PMT ciclo 3 com taxa 0,65%; parcelas 25-120 atualizadas; parcelas 13-24 com valor ciclo 2 preservado; saldo devedor diminui progressivamente |
| `TestBloqueioHU360Cascata` | 3 | Cascata bloqueia desde ciclo 2; desfazer reajuste ciclo 2 re-bloqueia ciclo 3; `gerar_carne` limita ao ciclo 2 |

**Total estimado:** ~25 testes

---

#### 7.9.2 — HU Rescisão e Cessão Contratual (PRIORIDADE P2) ✅ IMPLEMENTADO

> **Referência:** Seção 11 gaps G-03, G-04, G-05, G-11, G-12, G-16. 34 testes implementados em `tests/unit/contratos/test_hu_rescisao_cessao.py` (2026-05-04).

**Arquivo:** `tests/unit/contratos/test_hu_rescisao_cessao.py`

**Cenário do contrato:**
- Imóvel R$ 200.000 · Entrada R$ 30.000 · Financiado R$ 170.000 · 48 parcelas · IPCA
- `percentual_fruicao = 0.5%/mês` · `percentual_multa_rescisao_penal = 10%` · `percentual_multa_rescisao_adm = 12%` · `percentual_cessao = 3%`
- Contrato criado há 6 meses; 4 parcelas pagas; saldo devedor = 44 parcelas restantes

**Passos do fluxo E2E:**

| Passo | Marco | Cenários de Teste |
|-------|-------|-------------------|
| P1 | Setup contrato + pagamento parcial | 4 parcelas pagas; saldo devedor correto |
| P2 | Calcular rescisão pelo comprador | `calcular_rescisao()` retorna dict com: valor_pago (R$ devolvido), fruicao, multa_penal, multa_adm, mora_pro_rata; valor_a_devolver = pago − fruição − multa_penal − multa_adm |
| P3 | Validação fórmula fruição | fruicao = `saldo_devedor × percentual_fruicao/100 × meses_ocupacao` |
| P4 | Validação fórmula mora pro rata | mora = `valor_atraso × taxa_diaria × dias_atraso`; taxa_diaria = `percentual_juros_mora / 30` |
| P5 | Calcular cessão de direitos | `calcular_cessao()` retorna `taxa_cessao = saldo_devedor × 3%`; view renderiza com dados do contrato |
| P6 | Rescisão por inadimplência (vendedor) | Múltiplas parcelas em atraso → cálculo inclui mora acumulada; valor_a_devolver menor |

**Classes de teste focadas:**

| Classe | Testes | Foco |
|--------|--------|------|
| `TestCalcularRescisao` | 6 | Fórmula fruição; multa penal; multa adm; mora pro rata; total a devolver; view GET retorna valores corretos |
| `TestCalcularCessao` | 3 | Taxa de cessão = saldo × 3%; view GET renderiza; valor mínimo |
| `TestRescisaoPorInadimplencia` | 4 | Múltiplas parcelas em atraso; mora pro rata acumulada; valor_a_devolver diminui; histórico de parcelas considerado |
| `TestRescisaoVendedorIniciativa` | 2 | Rescisão por inadimplência do comprador; retenção máxima; cálculo diferenciado |

**Total estimado:** ~15 testes

---

#### 7.9.3 — HU CNAB Remessa→Retorno E2E (PRIORIDADE P2) ✅ IMPLEMENTADO

> **Referência:** Seções 12 e 21. 13 testes implementados em `tests/unit/financeiro/test_hu_cnab_e2e.py` (2026-05-04).

**Arquivo:** `tests/unit/financeiro/test_hu_cnab_e2e.py`

**Cenário:**
- Contrato com 3 parcelas não pagas; `ContaBancaria` Banco do Brasil (001)
- Mock do BRCobrança para `/api/remessa` (CNAB 240) e `/api/retorno`

**Passos do fluxo E2E:**

| Passo | Marco | Cenários de Teste |
|-------|-------|-------------------|
| P1 | Gerar boletos individuais (mock BRCobrança) | 3 boletos com `nosso_numero`; `tem_boleto=True`; `conta_bancaria` vinculada |
| P2 | Gerar remessa CNAB 240 | POST `gerar_arquivo_remessa` → `ArquivoRemessa` criado; `ItemRemessa` para cada parcela; status `GERADO`; mock `/api/remessa` |
| P3 | Controle de duplicata | Segunda tentativa de incluir mesma parcela → filtro `itens_remessa__isnull=True` exclui; aviso UI de "já em remessa pendente" |
| P4 | Processar retorno CNAB 400 — PAGO | Mock arquivo retorno CNAB 400 com ocorrência 06 (pago); `processar_retorno()` → `Parcela.pago=True`; `HistoricoPagamento` com `origem_pagamento='CNAB'` |
| P5 | Processar retorno CNAB 400 — INADIMPLENTE | Ocorrência 02 (entrada confirmada); parcela continua pendente; `ArquivoRetorno` criado |
| P6 | Gerar 2ª via após retorno inadimplente | Parcela não baixada → `gerar_segunda_via()`; juros/multa calculados sobre novo valor; novo `nosso_numero` via BRCobrança |

**Classes de teste focadas:**

| Classe | Testes | Foco |
|--------|--------|------|
| `TestCNABGerarRemessa` | 4 | ArquivoRemessa criado; ItemRemessa × 3; controle duplicata; fallback local sem BRCobrança |
| `TestCNABRetornoPago` | 4 | Ocorrência 06 → pago=True; HistoricoPagamento CNAB; ArquivoRetorno; status PROCESSADO |
| `TestCNABRetornoInadimplente` | 3 | Ocorrência 02 → parcela pendente; ArquivoRetorno; dados de retorno registrados |
| `TestCNAB2aVia` | 3 | Após retorno inadimplente; novo valor com juros; novo boleto via mock BRCobrança |

**Total estimado:** ~14 testes

---

#### 7.9.4 — HU Portal do Comprador — Ciclo Completo (PRIORIDADE P3) ✅ IMPLEMENTADO

> **Referência:** Seção U-05 portal mobile-first. 23 testes implementados em `tests/unit/portal/test_hu_portal_e2e.py` (2026-05-04).

**Arquivo:** `tests/unit/portal/test_hu_portal_e2e.py`

**Cenário:**
- Comprador com acesso ativo; contrato com 6 parcelas (1 paga, 1 com boleto, 4 pendentes)
- `AcessoComprador` válido

**Passos do fluxo E2E:**

| Passo | Marco | Cenários de Teste |
|-------|-------|-------------------|
| P1 | Auto-cadastro e login | `AcessoComprador` criado via `auto_cadastro`; login com CPF+email; `LogAcessoComprador` criado |
| P2 | Dashboard do comprador | KPIs: saldo devedor, próxima parcela, parcelas em atraso; lista de contratos ativos |
| P3 | Consultar parcelas do contrato | Lista de parcelas com status visual (paga/vencida/futura); dados corretos |
| P4 | Baixar boleto disponível | GET `baixar_boleto_portal`; parcela com `nosso_numero` → redirect BRCobrança; sem `nosso_numero` → 404 |
| P5 | Consultar linha digitável | API `api_linha_digitavel`; parcela paga → 404; parcela com boleto → retorna linha |
| P6 | Verificar próximo vencimento | `api_proximos_vencimentos` retorna lista ordenada com status; parcela paga excluída |

**Classes de teste focadas:**

| Classe | Testes | Foco |
|--------|--------|------|
| `TestPortalAutenticacao` | 3 | Auto-cadastro; login CPF+email; logout; `LogAcessoComprador` |
| `TestPortalDashboard` | 4 | KPIs saldo; próxima parcela; atraso; link para contratos |
| `TestPortalParcelas` | 4 | Lista parcelas do contrato; status visual; acesso apenas ao próprio contrato |
| `TestPortalBoleto` | 4 | Download boleto com nosso_numero; sem nosso_numero → 404; linha digitável; parcela paga → indisponível |

**Total estimado:** ~15 testes

---

#### 7.9.5 — Resumo dos Gaps E2E e Priorização

| # | HU | Arquivo Proposto | Prioridade | Testes Est. | Código Crítico não Coberto |
|---|----|-----------------|------------|-------------|---------------------------|
| 1 | HU-360 Juros Escalantes + Intermediárias | `test_hu_360_juros_escalantes.py` | **P1** | 33 | ✅ `get_juros_para_ciclo()`, PMT escalante, `PrestacaoIntermediaria`, `intermediarias_reduzem_pmt`, `intermediarias_reajustadas` |
| 2 | HU Rescisão e Cessão | `test_hu_rescisao_cessao.py` | **P2** | ~15 | `calcular_rescisao()`, `calcular_cessao()`, `calcular_mora_pro_rata()`, fruição, multa penal/adm |
| 3 | HU CNAB Remessa→Retorno | `test_hu_cnab_e2e.py` | **P2** | ~14 | Ciclo completo remessa→retorno→baixa; `processar_retorno()` integrado com `Parcela.pago`; 2ª via pós-retorno |
| 4 | HU Portal Comprador | `test_hu_portal_e2e.py` | **P3** | ~15 | Ciclo uso comprador: auto-cadastro → dashboard → boleto → linha digitável |

**Obs. — HU SAC com múltiplos ciclos:** `TestCenarioB` já cobre amortização constante e `test_hu_fluxo_completo.py` cobre reajuste Price. Um E2E SAC + IPCA + 3 ciclos seria P4 — não prioritário.

### 7.5 Infraestrutura de Testes ✅ CONCLUÍDO (P2)
| Prioridade | Item | Status |
|------------|------|--------|
| P2 | 13 factories faltantes (notificacoes, portal, CNAB) | ✅ ConfiguracaoEmailFactory, ConfiguracaoSMSFactory, ConfiguracaoWhatsAppFactory, NotificacaoFactory, TemplateNotificacaoFactory, RegraNotificacaoFactory, AcessoCompradorFactory, LogAcessoCompradorFactory, ArquivoRemessaFactory, ItemRemessaFactory, ItemRetornoFactory, AcessoUsuarioFactory + registradas no conftest.py |
| P2 | Mocks: Twilio SMS/WhatsApp, IBGE, SMTP | ✅ `mock_twilio_sms`, `mock_twilio_whatsapp`, `mock_twilio_error`, `mock_ibge_ipca`, `mock_ibge_inpc`, `mock_ibge_error`, `mock_smtp` fixtures no conftest.py |
| P3 | CI/CD GitHub Actions | ✅ `.github/workflows/ci.yml` |
| P4 | Badge de cobertura no README | — |

---

## 8. CI/CD E PERFORMANCE

### P2 — Alto
| Item | Descrição |
|------|-----------|
| PDF boleto persistido no banco | ✅ Campo `BinaryField boleto_pdf_db` em `Parcela` (migration `financeiro/0006`); `BoletoService` salva o PDF gerado no campo ao criar/baixar — resolve perda de arquivos no Render.com free tier (storage efêmero); `download_boleto` tenta DB primeiro, regenera via BRCobrança se ausente |
| Bootstrap local | ✅ Materialize, FontAwesome, AG Grid e Flatpickr servidos localmente via `static/vendor/`; templates base.html, portal_base.html, login, registro, setup atualizados; único CDN restante é Google Fonts (Material Icons) |
| Logging | ✅ Loggers por app (financeiro, contratos, core, notificacoes); django.request/security com AdminEmailHandler em produção; formato verbose com PID e thread |

### P3 — Médio
| Item | Descrição |
|------|-----------|
| GitHub Actions | ✅ `.github/workflows/ci.yml`: pytest unit em push/PR, cobertura ≥25% (cresce conforme testes), sintaxe Python, flake8 (non-blocking); usa SQLite em memória (sem serviço PostgreSQL) |
| Índices DB | ✅ Migration `0008_add_vencimento_compound_indexes`: índices compostos `(pago, data_vencimento)` e `(contrato, pago, data_vencimento)` em `Parcela` para queries de dashboard |

### P4 — Baixo
| Item | Descrição |
|------|-----------|
| Deploy automático | Render após merge em main |

---

## 9. DOCUMENTAÇÃO

### P3 — Médio ✅ CONCLUÍDO
| Item | Descrição | Status |
|------|-----------|--------|
| Swagger/OpenAPI | `drf-spectacular` | ✅ `drf-spectacular==0.29.0` + `djangorestframework==3.17.1` em `requirements.txt`; `drf_spectacular` em `INSTALLED_APPS`; `SPECTACULAR_SETTINGS` configurado; endpoints `/api/schema/` (YAML), `/api/docs/` (Swagger UI), `/api/docs/redoc/` (ReDoc) em `gestao_contrato/urls.py` |

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
| **10** | Testes P2 (views e APIs) | 7.2 | ✅ |
| **11** | Permissões e segurança | 6 | ✅ |
| **12** | Cálculos contratuais avançados (rescisão, cessão, mora pro rata) | 11 (G-10, G-11, G-15) | ✅ |
| **13** | ⭐ **Contrato Tabela Price + Intermediárias (HU-360)** | 13 | ✅ |
| **14** | ⭐ **Sistema de Amortização: Tabela Price e SAC** | 14 | ✅ |
| **15** | ⭐ **Regras de Bloqueio de Boleto — Cascata + Lote** | 15 | ✅ |
| **16** | ⭐ **Conciliação Bancária — CNAB Retorno + OFX + Baixa Manual** | 23 | ✅ |
| **17** | Testes P3/P4 + CI/CD | 7.3, 7.4, 8 | 🏦 Débito Técnico (pós-2050) |
| **18** | Frontend P3/P4 | 3 (P3, P4) | 🏦 Débito Técnico (pós-2050) |
| **19** | Documentação | 9 | ✅ `docs/deployment/CRONJOB.md`, `DEPLOY.md`, `ENV_PARAMETROS.md`, `RENDER.md`, `RENDER_NO_SHELL.md` |
| **20** | ⭐ **Agendamento e Operações — cron-job.org + endpoints HTTP** | 24 | ✅ Endpoints E-01..E-02 implementados; J-01..J-09 documentados em CRONJOB.md (config externa pendente de ativação no cron-job.org) |
| **21** | ⭐ **Grid de Reajustes Pendentes — cálculo inline + Aprovar/Editar** | 25 | ✅ |
| **22** | ⭐ **WhatsApp — Evolução: Cloud API mode + Whapi.cloud sandbox + Templates interativos** | 26 | ✅ W-01..W-08 concluídos |
| **23** | ⭐ **Chatbot WhatsApp — 2ª via, boletos em atraso, comprovante de pagamento** | 27 | ✅ |
| **24** | ⭐ **Segurança — Proteção das URLs Públicas de Boleto** | 28 | — |
| **25** | ⭐ **Portabilidade de Banco de Dados (PostgreSQL → MySQL / Oracle)** | 29 | — |
| **26** | ⭐ **Chatbot WhatsApp — Humanização com IA (Claude API)** | 30 | — |

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

## 16. MAPA INTERATIVO DE LOTES ✅ CONCLUÍDO

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

### 16.2 Página Dedicada por Loteamento ✅ CONCLUÍDO

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| M-11 | Página `/imoveis/loteamento/{slug}/` — mapa dedicado do empreendimento | P2 | ✅ `loteamento_detalhe` em `core/views.py` + URL `imoveis/loteamento/<str:nome>/` + template `loteamento_detalhe.html` com mapa Leaflet + lista filtrável por status |
| M-12 | Estatísticas do loteamento: total, disponíveis %, valor médio por lote | P2 | ✅ KPI cards (total, disponíveis, vendidos, valor médio/min/max) + barra de progresso proporcional na página do loteamento |
| M-13 | Polígonos de lote (boundaries) com `lat/lng` de cada vértice — modelo `LotePoligono` | P3 | ✅ `VerticePoligono` model + migration `0006` + `api_poligono_imovel` (GET/POST) + editor interativo no mapa com toolbar Leaflet (clicar = adicionar vértice, Salvar/Cancelar); `poligonos_json` passado ao template; polígonos renderizados em layer separado |
| M-14 | Upload de planta baixa (imagem) como overlay no mapa | P3 | ✅ `LoteamentoOverlay` model + migration `0010` + admin com preview de imagem + `api_overlay_loteamento` (GET/POST) + `L.imageOverlay` em `loteamento_detalhe.html` (com controle de camadas) e `imovel_list.html` (ao filtrar por loteamento); `overlays_json` passado via contexto |
| M-15 | Link direto "Ver no Google Maps / Waze" no popup do marcador | P3 | ✅ Links Maps e Waze exibidos no popup quando lat/lng disponíveis |
| M-16 | Geolocalização do usuário para mostrar lotes próximos | P4 | ✅ Botão "Perto de mim" na toolbar do mapa; `navigator.geolocation` → centraliza mapa na posição do usuário + marcador azul "Você está aqui" + conta lotes num raio de 50 km |

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
| N-04 | Integração WhatsApp (4 provedores) | P3 | ✅ `ConfiguracaoWhatsApp` suporta: Twilio, Meta Cloud API, Evolution API v2, Z-API. Webhooks de entrega (Evolution + Twilio). Teste de conexão por provedor. Análise custo/benefício e roadmap de evolução: **ver Seção 26**. |
| N-05 | Push notification portal comprador | P4 | 🏦 Débito Técnico (pós-2050) |
| N-08 | **TEST_MODE safeguard** — `_destinatario_email_teste()` e `_destinatario_telefone_teste()` em `BoletoNotificacaoService`: em ambiente não-produção, redireciona todos os envios para endereços de teste configurados em `settings.EMAIL_TESTE` e `settings.TELEFONE_TESTE`; evita notificações acidentais para compradores reais durante desenvolvimento | P2 | ✅ `notificacoes/boleto_notificacao.py` |
| N-09 | **Normalização E.164 para Twilio** — telefones no formato `(31) 99999-8888` são convertidos para `+5531999998888` antes do envio via Twilio SMS/WhatsApp; `_normalizar_telefone_e164()` strip de caracteres não-numéricos + prefixo `+55` | P2 | ✅ `notificacoes/boleto_notificacao.py` |
| N-06 | **Template unificado** — 1 registro por `(codigo, imobiliaria)` com 3 canais: `corpo_html` (Email HTML via TinyMCE 5), `corpo` (SMS ≤255 chars), `corpo_whatsapp`; campo `tipo` removido do form; badges de canal baseados nos campos preenchidos; `renderizar()` retorna 4-tuple `(assunto, corpo, corpo_html, corpo_whatsapp)` | P2 | ✅ Migration `0005_template_unificado` + forms + views + template_form/list atualizados |
| N-07 | **SMS máximo 255 caracteres** — validação no `clean_corpo()` do form + contador em tempo real no template com substituição de `%%TAGS%%` por valores de exemplo (31 tags mapeadas) para exibir comprimento real estimado; aviso laranja >90%, vermelho >255 | P2 | ✅ `TemplateNotificacaoForm.clean_corpo()` + JS no `template_form.html` |

---

## 20. MELHORIAS DE UX / INTERFACE ✅ CONCLUÍDO

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
| U-10 | **Forma de pagamento nos 3 modais** — campo `forma_pagamento` (Dinheiro/Boleto/PIX/Transferência/Cartão) adicionado nos modais: pagamento individual (`detalhe_parcela.html`), pagamento em massa (`listar_parcelas.html`) e registro via contrato (`contrato_detail.html`); salvo em `HistoricoPagamento.forma_pagamento` | P2 | ✅ |
| U-11 | **Máscaras numéricas de entrada e exibição** — `static/js/numeric-masks.js`: máscaras dinâmicas enquanto digita (`moeda` R$ 1.234,56, `pct2`, `pct4`, `decimal`, `inteiro`); todos os `NumberInput` em `contratos/forms.py`, `core/forms.py`, `notificacoes/forms.py` trocados por `TextInput` com `data-mask`; switch dinâmico por `data-mask-switch` para campos R$/% ambíguos; limpeza automática antes do submit; exibição com `numero_br`/`moeda` nos templates | P3 | ✅ |
| U-08 | **AG Grid — duplo cabeçalho corrigido** — removido `floatingFilter: true` e `floatingFiltersHeight: 36` de todas as 12 grids do sistema; busca rápida mantida via `quickFilterText` (input no card-header) | P2 | ✅ 12 templates atualizados: `listar_parcelas`, `contrato_list`, `indice_list`, `listar_reajustes`, `parcelas_mes`, `listar_remessas`, `listar_retornos`, `comprador_list`, `acesso_list`, `listar`, `template_list`, `config_email_list` |
| U-09 | **CSS 95% formulários** — regra global em `custom.css` para `col-xl-*` e `col-lg-*` dentro de `.row.justify-content-center` usa `max-width: 95%`; todos os formulários do sistema aproveitam sem alterar templates individuais | P3 | ✅ `static/css/custom.css` |

---

## Resumo Quantitativo

| Categoria | P1 | P2 | P3 | P4 | Total | Concluído |
|-----------|----|----|----|----|-------|-----------|
| Infraestrutura | 3 | 2 | 1 | — | 6 | ✅ 3/3 P1 |
| Backend — Regras | — | 8 | 3 | — | 11 | ✅ 8/8 P2 |
| Reajuste | 4 | 4 | 7 | — | 15+4=19 | ✅ 19/19 |
| Contrato Real (gaps) | — | — | 9 | — | 12 | ✅ 12/12 |
| CNAB Remessa | — | 8 | — | — | 8 | ✅ 8/8 |
| HU-360 Tabela Price | 2 | 9 | 2 | — | 13 | ✅ 13/13 |
| SAC / Tabela Price | 1 | 4 | — | — | 5 | ✅ 5/5 |
| Bloqueio Boleto (Cascata) | 2 | 3 | — | — | 5 | ✅ 5/5 |
| Mapa Interativo (Seção 16) | — | 5 | 6 | 1 | 12 | ✅ 12/12 M-01..M-16 |
| Dashboard KPIs (Seção 17) | 1 | 5 | 2 | — | 8 | ✅ 8/8 (K-01..K-06, G-01..G-05, D-01..D-04) |
| Simulador Antecipação (Seção 18) | — | 3 | 2 | — | 5 | ✅ 5/5 (R-01..R-05) |
| Notificações (Seção 19) | — | 6 | 2 | 1 | 9 | ✅ 8/9 P2+P3 (N-01..N-04, N-06..N-09) · 🏦 N-05 Débito Técnico |
| UX / Interface (Seção 20) | — | 6 | 5 | — | 11 | ✅ 11/11 (U-01..U-11) |
| Frontend | — | 17 | 15 | 3 | 35 | ✅ 17/17 P2 · ✅ 15/15 P3 · ⏳ 3.33 P4 |
| APIs | — | 6 | 5 | — | 11 | ✅ 11/11 |
| Celery (HTTP tasks) | — | 2 | 2 | — | 4 | ✅ 4/4 |
| Permissões | — | 4 | 4 | 2 | 10 | ✅ 10/10 |
| HU Boleto/Carnê/Remessa (Seção 21) | — | 10 | — | — | 10 | ✅ 10/10 |
| OFX Extrato Bancário (Seção 22) | — | 5 | — | — | 5 | ✅ 5/5 |
| Conciliação Bancária (Seção 23) | — | 8 | — | — | 8 | ✅ 8/8 |
| WhatsApp — Evolução (Seção 26) | — | 5 | 3 | — | 8 | ✅ 8/8 — W-01..W-08 concluídos |
| Chatbot WhatsApp (Seção 27) | 2 | 8 | 6 | — | 16 | ✅ 16/16 — C-01..C-16 |
| Testes | 104 | ~164 | ~37 | ~41+117 | ~463 | ✅ 942 testes passando |
| CI/CD | — | 2 | 4 | 2 | 8 | — |
| Documentação | — | — | 1 | 3 | 4 | — |
| **Total** | **~117** | **~254** | **~112** | **~61** | **~544** | |

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

**Seção 19 (N-06, N-07) — Template Notificação Unificado + SMS:**
- `TemplateNotificacao` refatorado: 1 registro por `(codigo, imobiliaria)` com campos `corpo_html`, `corpo`, `corpo_whatsapp` — elimina duplicidade de 3 registros por tipo
- Migration `0005_template_unificado`: merge de dados existentes, novo `unique_together`
- `renderizar()` retorna 4-tuple; `tem_email/tem_sms/tem_whatsapp` como properties
- TinyMCE 5 (self-hosted, sem API key) no campo `corpo_html`
- SMS máximo 255 chars: `clean_corpo()` valida + contador JS com substituição de `%%TAGS%%` por valores de exemplo
- `criar_templates_padrao()` e `gerar_dados_teste.py` atualizados

**Seção 20 (U-08, U-09) — AG Grid + CSS:**
- Duplo cabeçalho corrigido: removido `floatingFilter: true` das 12 grids — busca via `quickFilterText` mantida
- CSS 95% formulários: regra global em `custom.css` cobre todos os forms sem editar templates individuais

**Seção 22 — OFX: Quitação via Extrato Bancário:**
- `financeiro/services/ofx_service.py` — parser SGML puro sem dependências externas; suporte a SGML e XML-like; auto-detecção de encoding
- `parse_ofx(content)` — extrai lista de `OFXTransaction` (fitid, data, valor, memo)
- `OFXService.processar()` — reconcilia créditos com parcelas não pagas em 4 prioridades: P1 nosso_número no MEMO (ALTA), P2 número do contrato no MEMO (ALTA), P3 valor ±R$0,10 + mesmo mês (MEDIA), P4 valor ±R$0,10 sem data (BAIXA); débitos ignorados automaticamente
- `processar_ofx_upload()` — ponto de entrada para views; suporta `dry_run=True` (reconcilia sem quitar)
- `upload_ofx()` — GET página de upload / POST processa .ofx (limite 5 MB, filtro por imobiliária, dry_run)
- URL: `/cnab/ofx/upload/` → `financeiro:upload_ofx`
- 17 testes: `TestOFXParser` (6), `TestOFXReconciliacao` (6), `TestOFXView` (5)

**Seção 23 — Conciliação Bancária (Hub Unificado):**
- `HistoricoPagamento` estendido: `origem_pagamento` (MANUAL/CNAB/OFX/ANTECIPACAO/SISTEMA), `item_retorno` (FK), `fitid_ofx` (deduplicação OFX) — migration 0010
- `Parcela.Meta.constraints`: `UniqueConstraint(conta_bancaria + nosso_numero, nosso_numero≠'')` — único por banco, não global — migration 0011
- `CNABService._buscar_parcela_por_nosso_numero()`: lookup 4 etapas (exact+conta → endswith(strip)+conta → exact global → endswith global) — resolve CNAB zero-padded vs DB curto; elimina código duplicado nos 2 parsers (CNAB400/240)
- `ItemRetorno.processar_baixa()`: guard contra retorno duplicado — `if self.parcela.pago: aborta com mensagem`
- `registrar_pagamento_boleto()`: aceita `validar_minimo=False` para retornos CNAB liquidarem sem rejeição por valor mínimo
- `HistoricoPagamento.objects.get_or_create(item_retorno=self, ...)` — idempotência no CNAB retorno
- `OFXService._quitar()`: deduplicação por `fitid_ofx` antes de processar; cria `HistoricoPagamento` com `origem_pagamento='OFX'` + `fitid_ofx`
- `dashboard_conciliacao()` view: KPIs (pendentes/CNAB/OFX/MANUAL por período), lista de boletos pendentes, histórico recente, arquivos CNAB recentes, erros de processamento
- Template `financeiro/conciliacao/dashboard.html`: hub unificado com 3 métodos explicados
- `management/commands/audit_nosso_numero.py`: audita duplicatas por conta, duplicatas globais e boletos sem nosso_numero; `--fix-duplicates` limpa mantendo o mais antigo
- Admin: `HistoricoPagamentoAdmin` com campos de conciliação em `list_display`, `list_filter`, `search_fields` e fieldset dedicado

---

## 24. AGENDAMENTO E OPERAÇÕES — cron-job.org + Endpoints HTTP

> **Contexto:** O plano gratuito do Render não suporta Background Workers (sem Celery).
> Todas as tarefas periódicas são acionadas via HTTP por um agendador externo (cron-job.org, gratuito).
> Esta seção lista os jobs que devem ser configurados e os endpoints HTTP que ainda precisam ser criados.
> Documentação completa: `docs/deployment/CRONJOB.md`

---

### 24.1 Jobs a Configurar no cron-job.org (P1 — Imediatos)

> Sem estes jobs o serviço "adormece" após 15 min e notificações diárias não são enviadas.

| # | Job | URL | Método | Agenda (BRT) | Auth | Status |
|---|-----|-----|--------|--------------|------|--------|
| J-01 | Keep-alive app Django | `GET /health/` | GET | A cada 10 min | — | — |
| J-02 | Keep-alive BRCobrança | `GET /api/health` (BRCobrança) | GET | A cada 10 min | — | — |
| J-03 | Tarefas diárias (status, reajustes, notificações) | `POST /api/tasks/run-all/` | POST | Diário 08:00 | `X-Task-Token` | — |

**Configuração do header de autenticação:**
```
X-Task-Token: <valor de TASK_TOKEN no painel Render>
```

---

### 24.2 Jobs Recomendados (P2)

| # | Job | URL | Método | Agenda (BRT) | Auth | Status |
|---|-----|-----|--------|--------------|------|--------|
| J-04 | Relatório semanal para imobiliárias | `POST /api/tasks/relatorio-semanal/` | POST | Segunda 08:30 | `X-Task-Token` | — |
| J-05 | Relatório mensal consolidado | `POST /api/tasks/relatorio-mensal/` | POST | 1º dia 07:30 | `X-Task-Token` | — |
| J-06 | Monitoramento de bounces de e-mail | `POST /api/tasks/processar-bounces/` | POST | A cada 30 min | `X-Task-Token` | ✅ Implementado |
| J-07 | Limpeza de sessões Django expiradas | `POST /api/tasks/limpar-sessoes/` | POST | Domingo 03:00 | `X-Task-Token` | ✅ Implementado |
| J-08 | Baixar índices econômicos (IBGE + BCB) | `POST /api/tasks/atualizar-indices/` | POST | Toda segunda 07:00 | `X-Task-Token` | ✅ Implementado |
| J-09 | Notificações dedicado (fila + venc. + inad.) | `POST /api/tasks/processar-notificacoes/` | POST | A cada 6 horas | `X-Task-Token` | ✅ Implementado |

---

### 24.3 Endpoints HTTP Pendentes de Implementação (P2)

> Os endpoints J-06 e J-07 precisam ser criados em `core/views.py` (ou `notificacoes/views.py`)
> como wrappers HTTP dos management commands existentes.

| # | Endpoint | Management Command | Arquivo | Status |
|---|----------|--------------------|---------|--------|
| E-01 | `POST /api/tasks/processar-bounces/` | `processar_bounces` | `core/tasks.py` → `task_processar_bounces` | ✅ |
| E-02 | `POST /api/tasks/limpar-sessoes/` | `clearsessions` (Django built-in) | `core/tasks.py` → `task_limpar_sessoes` | ✅ |

---

### 24.4 Configurações Manuais Pendentes no Render (P1)

> Estas variáveis têm `sync: false` no `render.yaml` — devem ser inseridas manualmente
> no painel do Render em **Environment → Secret Files / Environment Variables**.

| Variável | Valor | Onde configurar |
|----------|-------|-----------------|
| `BOUNCE_IMAP_PASSWORD` | Senha da caixa `bounces@msbrasil.inf.br` | Render → gestao-contrato-web → Environment |
| `EMAIL_HOST_PASSWORD` | Senha SMTP Zoho (`teste@msbrasil.inf.br`) | Render → gestao-contrato-web → Environment |
| `TWILIO_ACCOUNT_SID` | SID da conta Twilio | Render → gestao-contrato-web → Environment |
| `TWILIO_AUTH_TOKEN` | Auth token Twilio | Render → gestao-contrato-web → Environment |

---

### 24.5 Pré-requisitos Externos (P1)

| # | Item | Serviço | Status |
|---|------|---------|--------|
| X-01 | Criar caixa `bounces@msbrasil.inf.br` no painel Zoho | Zoho Mail | — |
| X-02 | Habilitar IMAP na caixa de bounces (Zoho → Settings → Mail Accounts → IMAP) | Zoho Mail | — |
| X-03 | Criar conta gratuita em cron-job.org e configurar os 7 jobs | cron-job.org | — |
| X-04 | Verificar URL do callback Twilio: `TWILIO_STATUS_CALLBACK_URL` deve apontar para a URL real do app em produção | Render / Twilio | ✅ Configurado em `render.yaml` |

---

### 24.6 Checklist de Ativação

```
[ ] J-01 keep-alive Django criado no cron-job.org
[ ] J-02 keep-alive BRCobrança criado no cron-job.org
[ ] J-03 tarefas diárias criado no cron-job.org (com X-Task-Token)
[ ] J-04 relatório semanal criado no cron-job.org
[ ] J-05 relatório mensal criado no cron-job.org
[ ] BOUNCE_IMAP_PASSWORD configurado no Render (manual)
[ ] EMAIL_HOST_PASSWORD configurado no Render (manual)
[ ] TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN configurados no Render (manual)
[ ] Caixa bounces@msbrasil.inf.br criada e IMAP habilitado no Zoho
[x] E-01 endpoint /api/tasks/processar-bounces/ implementado
[ ] J-06 bounce monitoring criado no cron-job.org
[x] E-02 endpoint /api/tasks/limpar-sessoes/ implementado
[ ] J-07 limpeza de sessões criado no cron-job.org
[ ] J-08 atualizar-indices criado no cron-job.org (toda segunda 07:00)
[ ] J-09 processar-notificacoes criado no cron-job.org (a cada 6h, opcional)
```

---

## 25. HU — GRID DE REAJUSTES PENDENTES (Aprovar / Editar) ✅ CONCLUÍDO

> **História de Usuário:**
> Como administrador, quero visualizar todos os contratos com reajuste no período em uma
> grade com os valores calculados já visíveis, podendo aprovar individualmente, editar
> (informar %) individualmente ou selecionar N contratos e aplicar em lote (calculado ou informado).

---

### 25.1 Detecção Mês-a-Mês (não por dia)

| Item | Implementação | Status |
|------|--------------|--------|
| `calcular_ciclo_pendente(antecipacao_meses=1)` | Novo parâmetro: usa `hoje_ym + antecipacao` vs `aniversario_ym`; padrão = 1 mês antes | ✅ |
| Exibe contrato 1 mês antes do aniversário | Contrato 15/04/2024 → aparece na grid em 01/03/2025 | ✅ |
| Independente do dia do mês | Aparece em 01/04/2025 e em 30/04/2025 igualmente | ✅ |

### 25.2 Colunas da Grid

| Coluna | Fonte | Comportamento |
|--------|-------|---------------|
| Contrato / Data | `Contrato` | Link para detalhe |
| Comprador / Imóvel | `Contrato.comprador`, `Contrato.imovel` | — |
| Ciclo / Parcelas | calculado por `prazo_reajuste_meses` | Badge ciclo + range parcelas |
| Índice / Período de Ref. | `contrato.tipo_correcao` + `calcular_periodo_referencia()` | Badge índice + fallback automático |
| Prestação Atual | `Parcela.valor_atual` da parcela inicial do ciclo | R$ formatado |
| Correção % | `IndiceReajuste.get_acumulado_periodo()` | Badge verde com %; "Aguardando" se sem dados |
| Prestação Nova | `prestacao_atual × (1 + %/100)` — mode SIMPLES | `*Price recalcula PMT` para contratos Price |
| Ações | Botão Aprovar + botão Editar | Aprovar desabilitado se sem dados |

### 25.3 Ações

| Ação | Endpoint | Comportamento |
|------|----------|---------------|
| **Aprovar** (individual) | `POST /financeiro/reajustes/aplicar-lote/` | Aplica índice calculado; confirm() antes |
| **Editar** (individual) | `POST /financeiro/reajustes/aplicar-informado-lote/` | Modal com campo % + observações |
| **Aplicar Calculado** (lote) | `POST /financeiro/reajustes/aplicar-lote/` | N contratos, índice calculado, desconto opcional |
| **Aplicar Informado** (lote) | `POST /financeiro/reajustes/aplicar-informado-lote/` | N contratos, % único informado, desconto opcional |

### 25.4 Novo Endpoint

| Endpoint | View | URL | Status |
|----------|------|-----|--------|
| `POST /financeiro/reajustes/aplicar-informado-lote/` | `aplicar_reajuste_informado_lote` | `financeiro/urls.py` | ✅ |

### 25.5 Download de Índices (J-08)

| Item | Implementação | Status |
|------|--------------|--------|
| `atualizar_indices_sync()` | `core/tasks.py` — chama `IndicesEconomicosService.importar_indices()` para 7 índices, últimos 13 meses | ✅ |
| `POST /api/tasks/atualizar-indices/` | `task_atualizar_indices` em `core/tasks.py` + URL em `core/urls.py` | ✅ |
| Agenda cron-job.org | J-08: toda segunda 07:00 BRT | — (configurar no cron-job.org) |
| Sucesso parcial | Sucesso se ao menos 1 de 7 índices importado (tolerante a falhas de API) | ✅ |

---

## 26. WHATSAPP — ANÁLISE DE PROVEDORES E ROADMAP DE INTEGRAÇÃO

> **Contexto:** A Meta alterou seu modelo de cobrança em julho 2025 (por conversa → por mensagem/template).
> Esta seção documenta os provedores disponíveis, análise custo/benefício e o roteiro de evolução
> da integração WhatsApp no sistema.
> **Referência de pesquisa:** https://comunidade.zdg.com.br/geral/api-oficial-whatsapp/

---

### 26.1 Estado Atual da Implementação

Os 4 provedores abaixo já estão implementados em `notificacoes/models.py` (ConfiguracaoWhatsApp) e despachados pelo ServicoWhatsApp em `notificacoes/boleto_notificacao.py`:

| Provedor | Campo `provedor` | Autenticação | Endpoint | Status |
|----------|------------------|--------------|----------|--------|
| **Twilio** | `TWILIO` | `account_sid` + `auth_token` | Twilio API REST | ✅ Implementado |
| **Meta (Cloud API)** | `META` | `account_sid` (token) + `auth_token` | Graph API v18+ | ✅ Implementado |
| **Evolution API v2** | `EVOLUTION` | `api_url` + `api_key` + `instancia` | `POST /message/sendText/{instancia}` | ✅ Implementado |
| **Z-API** | `ZAPI` | `api_url` + `api_key` + `instancia` + `client_token` | `POST /send-text` | ✅ Implementado |

**Funcionalidades transversais já implementadas:**
- Webhook de entrega (Evolution + Twilio) → atualiza `Notificacao.status_entrega`
- Teste de conexão por provedor (`testar_conexao_whatsapp` view)
- TEST_MODE safeguard (redireciona envios em dev para `settings.TELEFONE_TESTE`)
- Normalização E.164: `(31) 99999-8888` → `+5531999998888`
- CRUD completo de configuração via `/notificacoes/config/whatsapp/`

---

### 26.2 Mudança de Modelo de Cobrança Meta (Julho 2025)

A partir de 01/07/2025, a Meta abandonou a cobrança por janela de conversa (24h) e passou a cobrar **por mensagem de template entregue**:

| Categoria de Template | Custo (USD/msg) | Custo aprox. (BRL) | Janela de Serviço |
|-----------------------|-----------------|---------------------|-------------------|
| **Utility** (vencimentos, boletos) | $0,0068 | ~R$ 0,04 | Cobrado só fora da janela 24h |
| **Marketing** (campanhas) | $0,0625 | ~R$ 0,35 | Sempre cobrado |
| **Authentication** | $0,0068 | ~R$ 0,04 | Sempre cobrado |
| **Service** (cliente iniciou) | Grátis | R$ 0,00 | Sempre grátis |

> Para um sistema de gestão de contratos as mensagens de vencimento/boleto se enquadram em **Utility** — o custo unitário mais baixo da API oficial.

---

### 26.3 Tabela Comparativa — Custo/Benefício (2026)

| Provedor | Custo/msg | Mensalidade (BRL) | Aprovação Meta | Self-hosted | Risco de Banimento | LGPD (BR) | Python | Recomendado para |
|----------|-----------|--------------------|-----------------|-------------|---------------------|-----------|--------|-----------------|
| **Meta Cloud API** (via BSP BR) | R$ 0,04 (Utility) | R$ 200–600 (BSP fee) | ✅ Obrigatória | ❌ Não | ✅ Zero | ✅ Sim | ✅ SDK `pywa` | Conformidade total, número verificado |
| **Twilio WhatsApp** | R$ 0,04 + R$ 0,028/msg | R$ 0 (paga por uso) | ✅ Via Twilio | ❌ Não | ✅ Zero | ⚠️ EUA | ✅ SDK maduro | Quem já usa Twilio; equipe enterprise |
| **Z-API** | R$ 0/msg (flat) | R$ 55–100/instância | ❌ Não | ❌ SaaS BR | ⚠️ Existe | ✅ Brasil | ✅ REST JSON | PMEs brasileiras, custo previsível, prioridade suporte PT-BR |
| **Evolution API** (Baileys) | R$ 0/msg | R$ 30–150 (só VPS) | ❌ Não | ✅ Sim | ⚠️ Existe | ✅ Brasil | ✅ REST | Devs com DevOps, custo mínimo, controle total |
| **Evolution API** (Cloud API mode) | R$ 0,04 (Utility) + VPS | R$ 30–150 (VPS) | ✅ Via Meta | ✅ Sim | ✅ Zero | ✅ Brasil | ✅ REST | **Melhor custo/benefício: self-hosted + compliance** |
| **Whapi.cloud** | R$ 0/msg | R$ 165/instância ($29) | ❌ Não | ❌ SaaS EU | ⚠️ Existe | ⚠️ Europa | ✅ Exemplos prontos | Protótipo/sandbox gratuito para testes |
| **WPPConnect** | R$ 0/msg | R$ 30–150 (só VPS) | ❌ Não | ✅ Sim | ⚠️ Existe | ✅ Brasil | ✅ REST (Node) | Alternativa ao Evolution, mais Node.js |
| **Chat-API** | — | — | — | — | — | — | — | ❌ Descontinuado em 2026 |

---

### 26.4 Simulação de Custo Mensal (Sistema Imobiliário)

**Cenário:** 500–5.000 msgs/mês — vencimentos (Utility) + inadimplência + lembretes

| Volume | Meta Cloud API (BSP) | Z-API | Evolution API + VPS R$80 |
|--------|----------------------|-------|--------------------------|
| 500 msgs | R$ 220–620 | R$ 55–100 | R$ 80 |
| 1.000 msgs | R$ 240–640 | R$ 55–100 | R$ 80 |
| 3.000 msgs | R$ 320–720 | R$ 55–100 | R$ 80–150 |
| 5.000 msgs | R$ 400–800 | R$ 55–100 | R$ 80–150 |

> **Nota:** BSP Fee é a mensalidade cobrada pelo parceiro BSP (Hablla, Poli Digital, Digisac) além das taxas Meta. Para volume < 5.000 msgs/mês, Evolution API no modo Cloud API próprio é o mais econômico com compliance.

---


### 26.5 Quadro Comparativo — 4 Provedores × 4 Ambientes

> **Premissa:** VPS própria disponível (custo já pago). Evolution API pode rodar na VPS sem custo adicional de infraestrutura.

---

#### Ambiente 1 — Desenvolvimento / Homologação

| Critério | Twilio | Meta Cloud API | Evolution API (Baileys) | Z-API |
|----------|--------|----------------|------------------------|-------|
| **Custo/mês** | R$ 0 (trial) | R$ 0 (sandbox) | **R$ 0** (VPS já paga) | R$ 0 (2 dias trial) |
| **Setup (horas)** | 2h | 4h | **1h** (Docker na VPS) | 1h (QR Code) |
| **Número real necessário** | Não (sandbox) | Não (sandbox) | **Não** (pode usar número pessoal) | Sim |
| **Reinicialização** | Sem estado | Sem estado | Persiste na VPS | Reconectar QR |
| **Logs/Debug** | Dashboard Twilio | Meta Developers | **Logs diretos na VPS** | Dashboard web |
| **Isolamento de dev/prod** | Fácil (2 projetos) | Médio | **Fácil** (2 instâncias Docker) | 2 planos |
| **Recomendação** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Veredicto** | Funciona | Funciona | **Melhor: grátis + na VPS** | Funciona |

---

#### Ambiente 2 — Produção Pequena (até 2.000 msgs/mês)

| Critério | Twilio | Meta Cloud API | Evolution API (Baileys) | Z-API |
|----------|--------|----------------|------------------------|-------|
| **Custo/mês** | ~R$ 85 (2.000 msgs × R$ 0,04 Meta + markup) | ~R$ 80 (BSP mínimo) | **R$ 0** (VPS já paga) | R$ 55–100 |
| **Custo/mensagem** | ~R$ 0,07 | ~R$ 0,04 (Utility) | **R$ 0** | R$ 0 (flat) |
| **Aprovação prévia** | Sim (semanas) | Sim (dias-semanas) | **Não** | **Não** |
| **Risco de banimento** | ✅ Zero | ✅ Zero | ⚠️ Baixo-médio | ⚠️ Baixo-médio |
| **Número verificado** | ✅ Sim | ✅ Sim | ❌ Não | ❌ Não |
| **Botões interativos** | ✅ Sim | ✅ Sim (templates) | Parcial | Parcial |
| **Suporte PT-BR** | ❌ Inglês | ❌ Inglês | Comunidade | **✅ BR** |
| **Manutenção** | Zero | Zero | **Baixa** (VPS + Docker) | Zero |
| **LGPD** | ⚠️ EUA | ⚠️ EUA/EU | **✅ Brasil (VPS)** | **✅ Brasil** |
| **Recomendação** | ⭐⭐⭐ | ⭐⭐⭐ | **⭐⭐⭐⭐⭐** | ⭐⭐⭐⭐ |
| **Veredicto** | Caro para volume baixo | Setup burocrático | **Melhor: custo zero na VPS** | Boa alternativa sem DevOps |

---

#### Ambiente 3 — Produção Média (2.000–10.000 msgs/mês)

| Critério | Twilio | Meta Cloud API | Evolution API (Baileys) | Z-API |
|----------|--------|----------------|------------------------|-------|
| **Custo/mês (5.000 msgs)** | ~R$ 350 | ~R$ 400 (BSP + msgs) | **R$ 0** (VPS já paga) | R$ 55–100 |
| **Custo/mês (10.000 msgs)** | ~R$ 700 | ~R$ 600 | **R$ 0** | R$ 55–100 |
| **Escalabilidade** | Ilimitada | Ilimitada | ✅ Multi-instância VPS | Paga por instância |
| **Múltiplos números** | Paga por número | Paga por número | **✅ N instâncias grátis** | R$ 55-100/número |
| **Webhook entrega** | ✅ Robusto | ✅ Robusto | ✅ Implementado | ✅ Implementado |
| **Uptime** | 99,99% (SLA) | 99,99% | Depende da VPS | 99,9% declarado |
| **Risco de banimento** | ✅ Zero | ✅ Zero | ⚠️ Médio (volume alto) | ⚠️ Médio |
| **Recomendação** | ⭐⭐ | ⭐⭐⭐ | **⭐⭐⭐⭐** | ⭐⭐⭐ |
| **Veredicto** | Muito caro | Custo cresce com volume | **Melhor: sem custo por msg** | Custo fixo previsível |

---

#### Ambiente 4 — Produção Compliance / Escala (>10.000 msgs/mês ou número verificado)

| Critério | Twilio | Meta Cloud API (BSP BR) | Evolution API (Cloud API mode) | Z-API |
|----------|--------|--------------------------|-------------------------------|-------|
| **Custo/mês (10.000 msgs)** | ~R$ 700 | ~R$ 600 (BSP + R$0,04/Utility) | **~R$ 400** (VPS já paga + Meta R$0,04/msg) | ❌ Alto risco neste volume |
| **Conformidade TOS Meta** | ✅ Total | ✅ Total | ✅ Total (sem Baileys) | ❌ Não conforme |
| **Número verificado** | ✅ Sim | ✅ Sim | ✅ Sim (via Meta direto) | ❌ Não |
| **Selo de empresa verificada** | ✅ Sim | ✅ Sim | ✅ Sim | ❌ Não |
| **Risco de banimento** | ✅ Zero | ✅ Zero | ✅ Zero | ⚠️ Alto em escala |
| **Templates aprovados pela Meta** | ✅ Sim | ✅ Sim | ✅ Sim | ❌ Não suporta |
| **Botões / Listas / Carousel** | ✅ Completo | ✅ Completo | ✅ Completo | Parcial |
| **LGPD** | ⚠️ EUA | ⚠️ Depende do BSP | **✅ Brasil (VPS)** | ✅ Brasil |
| **Suporte enterprise** | ✅ Twilio | ✅ BSP BR (Hablla, Digisac) | Comunidade | Suporte BR |
| **Setup** | Semanas | Semanas | **1 semana** | ❌ Não indicado |
| **Recomendação** | ⭐⭐⭐ | ⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐** | ❌ |
| **Veredicto** | Caro + dados nos EUA | Boa opção com BSP BR | **Melhor: VPS própria + Meta oficial** | Não indicado para este volume |

---

### 26.6 Decisão Recomendada (com VPS própria disponível)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  VPS JÁ DISPONÍVEL → Evolution API é a âncora em todos os ambientes    │
└─────────────────────────────────────────────────────────────────────────┘

DEV/HOMOLOGAÇÃO
  └─► Evolution API (Baileys) na VPS
      • Instância Docker separada: evolution-dev
      • Custo: R$ 0 (VPS já paga)
      • Setup: 1h

PRODUÇÃO — FASE 1 (até 5.000 msgs/mês, início rápido)
  └─► Evolution API (Baileys) na VPS
      • Instância Docker: evolution-prod
      • Custo: R$ 0 adicional
      • Risco de banimento: baixo-médio (monitorar)
      • Setup: 1-2h

PRODUÇÃO — FASE 2 (quando quiser número verificado OU > 5.000 msgs/mês)
  └─► Evolution API no modo Cloud API oficial na VPS
      • Mesma VPS, mesmo endpoint, campo extra no config
      • Custo: R$ 0 (VPS) + R$ 0,04/msg Meta (Utility)
      • Risco de banimento: ZERO
      • Setup: 3-5 dias (verificação Meta Business)

FALLBACK (se VPS ficar fora)
  └─► Z-API (R$ 55-100/mês) — SaaS BR, sem infraestrutura
```

---

### 26.7 Comparativo Consolidado — Scorecard Final (com VPS disponível)

| Critério (peso) | Twilio | Meta via BSP | Evolution Baileys | Evolution Cloud API | Z-API |
|-----------------|--------|-------------|-------------------|---------------------|-------|
| **Custo total (30%)** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Conformidade TOS (20%)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Facilidade setup (15%)** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **LGPD / dados BR (15%)** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Recursos (templates, botões) (10%)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Escalabilidade (10%)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Score ponderado** | 3,1 | 3,4 | **4,3** | **4,7** | 3,7 |
| **Indicado para** | Infra Twilio existente | Empresa com CNPJ verificado | Início rápido + VPS | **Produção ideal** | Sem DevOps |

> **Vencedor com VPS disponível: Evolution API no modo Cloud API oficial** — custo mínimo, compliance total, dados no Brasil, escala ilimitada.

---

### 26.8 Itens Pendentes de Implementação

| # | Item | Prioridade | Provedor | Status |
|---|------|------------|----------|--------|
| W-01 | Adicionar `modo_evolution` (`BAILEYS`/`CLOUD_API`) ao model `ConfiguracaoWhatsApp` + migration | P1 | Evolution | ✅ migration 0013 |
| W-02 | Campos `phone_number_id` + `meta_access_token` no model para modo Cloud API | P1 | Evolution | ✅ migration 0013 |
| W-03 | `ServicoWhatsApp._enviar_evolution()` — branch por `modo_evolution` (endpoint e payload diferentes) | P1 | Evolution | ✅ `_enviar_evolution_cloud_api()` |
| W-04 | **Webhook Evolution modo Cloud API** — payload diferente do Baileys; atualizar `webhook_evolution()` | P2 | Evolution | ✅ `_EVOLUTION_STATUS_MAP` + `_webhook_evolution_meta_format()` |
| W-05 | **Teste de conexão** para modo Cloud API (`GET /<instancia>/instance/connectionState`) | P2 | Evolution | ✅ `testar_conexao_whatsapp()` verifica Meta Graph API quando `modo_evolution=CLOUD_API` |
| W-06 | **Templates interativos** — `corpo_whatsapp_interativo` (JSON) com botões para Evolution Cloud API e Meta | P3 | Evolution / Meta | ✅ JSONField em `TemplateNotificacao`; `renderizar_interativo()`; `ServicoWhatsApp.enviar_interativo()` + `_enviar_evolution_interativo()` → `/message/sendButtons/{instancia}`; fallback automático para texto em Cloud API/Meta/Twilio |
| W-07 | **BSP brasileiro** — suporte a Hablla / Poli Digital / Digisac como provedor `BSP` | P3 | Meta via BSP | ✅ `_enviar_bsp()` (Meta Cloud API compatível); `webhook_bsp()` (hub verification + X-Hub-Signature-256 + inbound chatbot); fieldset no admin; 17 testes |
| W-08 | **Status de entrega unificado** — normalizar `DELIVERED/READ` entre provedores | P3 | Todos | ✅ `_TWILIO_STATUS_MAP` + `webhook_twilio` normaliza para conjunto canônico `queued/sent/delivered/read/failed`; `_STATUS_ENTREGA_LABELS` e `_STATUS_ENTREGA_CHOICES` unificados |

---

### 26.9 Configuração Docker — Evolution API na VPS

```yaml
# docker-compose.evolution.yml (na VPS)
services:
  evolution-dev:
    image: atendai/evolution-api:latest
    ports: ["8080:8080"]
    environment:
      - SERVER_URL=http://sua-vps:8080
      - AUTHENTICATION_API_KEY=sua-chave-dev
      - DATABASE_ENABLED=true
    volumes: ["./evolution-dev-data:/evolution/store"]

  evolution-prod:
    image: atendai/evolution-api:latest
    ports: ["8081:8080"]
    environment:
      - SERVER_URL=http://sua-vps:8081
      - AUTHENTICATION_API_KEY=sua-chave-prod
      - DATABASE_ENABLED=true
      # Modo Cloud API oficial (W-01):
      # - CLOUD_API_ENABLED=true
      # - CLOUD_API_PHONE_NUMBER_ID=seu-phone-number-id
      # - CLOUD_API_ACCESS_TOKEN=seu-access-token-meta
    volumes: ["./evolution-prod-data:/evolution/store"]
```

**Custo total na VPS:** R$ 0 adicional (VPS já contratada).

---

### 26.10 Comparativo com Concorrentes

| Sistema | Provedor WhatsApp | Custo estimado |
|---------|-------------------|----------------|
| LoteWin | Meta Cloud API via BSP | R$ 400–800/mês |
| GELOT | Z-API ou Evolution | R$ 80–150/mês |
| SGL | Twilio | R$ 300–700/mês |
| SmartIPTU | Meta Cloud API direto | R$ 300–600/mês |
| **Este Sistema (com VPS)** | **Evolution API (VPS própria)** | **R$ 0–120/mês** |

### 25.6 Endpoint Dedicado de Notificações (J-09)

| Item | Implementação | Status |
|------|--------------|--------|
| `POST /api/tasks/processar-notificacoes/` | Fila + vencimentos + inadimplentes em sequência | ✅ |
| `task_processar_notificacoes` | `core/tasks.py` + URL em `core/urls.py` | ✅ |
| Quando usar | Quando quiser notificações mais frequentes que o `run-all` (ex.: a cada 6h) | ✅ |

---

## 27. CHATBOT WHATSAPP — 2ª VIA, COMPROVANTE E ATENDIMENTO AUTOMÁTICO

> **Contexto:** cliente envia mensagem para o número WhatsApp da imobiliária e recebe
> automaticamente: 2ª via de boleto, linha digitável, envio de comprovante de pagamento,
> situação de boletos em atraso e resumo financeiro — sem intervenção humana.
>
> **Base técnica:** Evolution API (já implementado). O webhook atual já recebe
> `messages.upsert` mas ignora `fromMe=False` (linha 478 de `notificacoes/views.py`).
> Esta seção especifica o que adicionar a partir desse ponto de entrada.

---

### 27.1 Fluxos Implementados

#### Fluxo A — Identificação do Cliente

```
Cliente envia qualquer mensagem
        │
        ▼
webhook_evolution() ── fromMe=False? ──► WhatsAppBotService.processar()
        │
        ▼
Busca Comprador por telefone E.164
        │
    Encontrou? ──Não──► "Olá! Informe seu CPF para acessar seus boletos:"
        │                      │
       Sim                     ▼ (cliente responde com CPF)
        │               Busca por CPF → encontrou → salva sessão → continua
        ▼
Exibe menu principal (ver 27.1B)
```

#### Fluxo B — Menu Principal

```
🏠 *Gestão de Contratos*
Olá, [Nome]! Como posso ajudar?

1️⃣ 2ª via de boleto
2️⃣ Boletos em atraso
3️⃣ Enviar comprovante de pagamento
4️⃣ Meu resumo financeiro
0️⃣ Falar com atendente

Responda com o número da opção.
```

#### Fluxo C — 2ª Via de Boleto

```
Cliente escolhe "1" ou digita "segunda via" / "boleto"
        │
        ▼
Lista parcelas PENDENTES + VENCIDAS (até 5):
  📄 Parc. 3 — Venc. 10/05/2026 — R$ 850,00
  📄 Parc. 4 — Venc. 10/06/2026 — R$ 850,00
  ...
"Qual parcela deseja? Responda com o número."
        │
        ▼
Cliente responde "1" → seleciona parcela
        │
        ▼
BoletoService.gerar_segunda_via() ── sem boleto? ──► gerar novo boleto
        │
        ▼
Envia texto:
  ✅ *2ª Via — Parcela 3*
  📋 Linha digitável: 00190.00009 02625...
  📅 Vencimento: 10/05/2026
  💰 Valor: R$ 850,00

Envia PDF do boleto via sendMedia (Evolution)
```

#### Fluxo D — Boletos em Atraso

```
Cliente escolhe "2" ou digita "atraso" / "vencido" / "atrasado"
        │
        ▼
Lista parcelas VENCIDAS com encargos calculados:
  ⚠️ *Boletos em Atraso*
  📄 Parc. 1 — Venc. 10/03/2026
     Principal: R$ 850,00
     Juros + Multa: R$ 42,50
     *Total hoje: R$ 892,50*

  📄 Parc. 2 — Venc. 10/04/2026
     ...

"Deseja a 2ª via de alguma dessas parcelas? (número ou 0 para voltar)"
        │
        ▼
Segue Fluxo C com a parcela selecionada
```

#### Fluxo E — Comprovante de Pagamento

```
Cliente escolhe "3" OU envia imagem/PDF diretamente
        │
        ▼
"Qual parcela este comprovante se refere?"
Lista parcelas aguardando pagamento
        │
        ▼ (cliente seleciona)
Baixa o arquivo do Evolution API (base64 → arquivo)
        │
        ▼
Salva em HistoricoPagamento.comprovante (FileField)
Cria Notificacao interna para admin revisar
        │
        ▼
"✅ Comprovante recebido! Nossa equipe confirmará em até 1 dia útil."
Notificação push para admin (email + painel)
```

#### Fluxo F — Resumo Financeiro

```
Cliente escolhe "4"
        │
        ▼
Contrato.get_resumo_financeiro()
        │
        ▼
📊 *Seu Resumo — Contrato #001*
✅ Parcelas pagas: 12 de 60
💰 Total pago: R$ 10.200,00
📅 Próximo vencimento: 10/05/2026 — R$ 850,00
⚠️ Em atraso: 0 parcelas
📈 Progresso: 20%
```

---

### 27.2 Modelo de Sessão de Conversa

```python
# notificacoes/models.py — novo modelo
class SessaoConversaWhatsApp(models.Model):
    """
    Estado da conversa por número de telefone.
    Armazenado no banco; Redis seria mais rápido mas requer infra extra.
    TTL: limpar sessões com updated_at > 30 minutos (management command).
    """
    class Estado(models.TextChoices):
        IDLE                    = 'IDLE',                    'Aguardando'
        AGUARDANDO_CPF          = 'AGUARDANDO_CPF',          'Aguardando CPF'
        MENU_PRINCIPAL          = 'MENU_PRINCIPAL',          'Menu principal'
        AGUARDANDO_PARCELA_2VIA = 'AGUARDANDO_PARCELA_2VIA', 'Seleção 2ª via'
        AGUARDANDO_PARCELA_COMP = 'AGUARDANDO_PARCELA_COMP', 'Seleção comprovante'
        AGUARDANDO_COMPROVANTE  = 'AGUARDANDO_COMPROVANTE',  'Enviando comprovante'

    telefone    = models.CharField(max_length=20, unique=True, db_index=True)
    comprador   = models.ForeignKey('financeiro.Comprador', null=True, blank=True,
                                    on_delete=models.SET_NULL)
    estado      = models.CharField(max_length=30, choices=Estado.choices,
                                    default=Estado.IDLE)
    contexto    = models.JSONField(default=dict)   # parcelas_ids, contrato_id etc.
    config_wa   = models.ForeignKey('ConfiguracaoWhatsApp', null=True,
                                    on_delete=models.SET_NULL)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sessão WhatsApp'
```

---

### 27.3 Serviço do Chatbot

```python
# notificacoes/whatsapp_bot.py — novo arquivo
class WhatsAppBotService:

    def processar(self, telefone, mensagem, tipo_msg, media_b64, config_wa): ...
    # Despacha para o estado correto da sessão

    def _identificar_comprador(self, telefone): ...
    # Busca por Comprador.telefone normalizado E.164

    def _menu_principal(self, sessao): ...
    def _fluxo_2a_via(self, sessao, mensagem): ...
    def _fluxo_atraso(self, sessao, mensagem): ...
    def _fluxo_comprovante(self, sessao, mensagem, media_b64): ...
    def _fluxo_resumo(self, sessao): ...

    def _responder(self, telefone, texto, config_wa): ...
    # ServicoWhatsApp._enviar_evolution() já existente

    def _enviar_pdf(self, telefone, pdf_bytes, filename, config_wa): ...
    # POST /message/sendMedia/{instancia} (base64)

    def _baixar_media(self, message_id, config_wa): ...
    # GET /message/download-media/{instancia}/{messageId}
```

---

### 27.4 Mudanças no Webhook Existente

```python
# notificacoes/views.py — webhook_evolution() — adicionar após linha 478:

# fromMe=False → mensagem recebida do cliente → chatbot
if not from_me and is_upsert:
    _processar_mensagem_inbound(item, config, request)
    continue
```

```python
def _processar_mensagem_inbound(item, config, request):
    """Extrai texto/mídia e despacha para WhatsAppBotService."""
    remote_jid = item.get('key', {}).get('remoteJid', '')
    telefone = remote_jid.replace('@s.whatsapp.net', '')

    msg_content = item.get('message', {})
    texto = (
        msg_content.get('conversation')
        or msg_content.get('extendedTextMessage', {}).get('text', '')
        or ''
    ).strip()

    # Mídia (imagem/documento = comprovante)
    tipo_msg = 'text'
    media_b64 = None
    if 'imageMessage' in msg_content or 'documentMessage' in msg_content:
        tipo_msg = 'media'
        # Download lazy — feito dentro do bot se necessário

    WhatsAppBotService().processar(
        telefone=telefone,
        mensagem=texto,
        tipo_msg=tipo_msg,
        media_b64=media_b64,
        config_wa=config,
    )
```

---

### 27.5 Plano de Implementação

#### Fase 1 — Infraestrutura (P1)

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| C-01 | Model `SessaoConversaWhatsApp` + migration | `notificacoes/models.py` | ✅ |
| C-02 | Webhook: rotear `fromMe=False` para `_processar_mensagem_inbound()` | `notificacoes/views.py` | ✅ |
| C-03 | `WhatsAppBotService.processar()` — dispatcher por estado | `notificacoes/whatsapp_bot.py` | ✅ |
| C-04 | Identificação por telefone + fallback CPF (Fluxo A) | `notificacoes/whatsapp_bot.py` | ✅ |
| C-05 | Menu principal (Fluxo B) | `notificacoes/whatsapp_bot.py` | ✅ |

#### Fase 2 — 2ª Via e Atraso (P1)

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| C-06 | Fluxo C — 2ª via: lista parcelas + `gerar_segunda_via()` + envio PDF | `notificacoes/whatsapp_bot.py` | ✅ |
| C-07 | Fluxo D — boletos em atraso: encargos calculados + linha digitável | `notificacoes/whatsapp_bot.py` | ✅ |
| C-08 | `_enviar_pdf()` — `POST /message/sendMedia/{instancia}` (base64) | `notificacoes/whatsapp_bot.py` | ✅ |

#### Fase 3 — Comprovante (P2)

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| C-09 | Fluxo E — receber mídia + seleção de parcela + notificação admin | `notificacoes/whatsapp_bot.py` | ✅ |
| C-10 | Criar `Notificacao` para admin revisar + envio de e-mail para imobiliária | `notificacoes/whatsapp_bot.py` | ✅ |
| C-11 | Admin: fila de comprovantes pendentes de revisão | `notificacoes/admin.py` | ✅ `ComprovantePendenteAdmin` proxy com fila filtrada, ações confirmar/cancelar, link para parcela |

#### Fase 4 — UX e Robustez (P2)

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| C-12 | Fluxo F — resumo financeiro | `notificacoes/whatsapp_bot.py` | ✅ |
| C-13 | Management command `limpar_sessoes_whatsapp` — remove sessões > 30 min | `notificacoes/management/` | ✅ `limpar_sessoes_whatsapp.py` + endpoint `POST /api/tasks/limpar-sessoes/` |
| C-14 | Timeout de sessão: mensagem de aviso após 20 min sem resposta | `notificacoes/whatsapp_bot.py` | ✅ Verifica `atualizado_em` no início de `processar()` — envia aviso e reinicia sessão para INICIO |
| C-15 | Opção "0 — Falar com atendente": pausa bot + notifica staff por email | `notificacoes/whatsapp_bot.py` | ✅ |
| C-16 | Testes unitários: 20 casos (identificação, fluxos A–F, estados, edge cases) | `tests/unit/notificacoes/test_whatsapp_bot.py` | ✅ 417 linhas — identificação, fluxos A–F, timeout, estados |

---

### 27.6 Dependências e Integrações Existentes

| Recurso existente | Reutilizado em |
|-------------------|----------------|
| `BoletoService.gerar_segunda_via()` | Fluxo C (2ª via) |
| `ServicoWhatsApp._enviar_evolution()` | Todos os fluxos (resposta texto) |
| `ServicoWhatsApp._normalizar_numero()` | Identificação por telefone |
| `Parcela.calcular_encargos()` | Fluxo D (boletos em atraso) |
| `Contrato.get_resumo_financeiro()` | Fluxo F |
| `HistoricoPagamento.comprovante` (FileField) | Fluxo E |
| `AcessoComprador` (Portal do Comprador) | Identificação alternativa |
| Redis (já disponível) | Cache de sessão opcional (fase futura) |

---

### 27.7 Palavras-chave Reconhecidas (Intents)

| Intenção | Palavras-chave |
|----------|---------------|
| 2ª via | `segunda via`, `2a via`, `boleto`, `2ª via`, `1` |
| Atraso | `atraso`, `atrasado`, `vencido`, `em atraso`, `2` |
| Comprovante | `comprovante`, `paguei`, `pagamento`, `enviar comprovante`, `3` |
| Resumo | `saldo`, `resumo`, `situação`, `meu contrato`, `4` |
| Atendente | `atendente`, `humano`, `pessoa`, `falar com`, `0` |
| Cancelar/Voltar | `cancelar`, `voltar`, `sair`, `menu` |

---

### 27.8 Adição ao Execution Order

| Fase | Escopo | Status |
|------|--------|--------|
| **23** | ⭐ **Chatbot WhatsApp — 2ª via, atraso, comprovante** | ✅ C-01..C-16 concluídos |
| **24** | ⭐ **Segurança — Proteção das URLs Públicas de Boleto** | 28 | — |
| **25** | ⭐ **Portabilidade de Banco de Dados (PostgreSQL → MySQL / Oracle)** | 29 | — |
| **26** | ⭐ **Chatbot WhatsApp — Humanização com IA (Claude API)** | 30 | — |
| **27** | Versão do Sistema no Rodapé + ID de Página | 31 | — |

---

## 28. SEGURANÇA — PROTEÇÃO DAS URLs PÚBLICAS DE BOLETO

> **Contexto:** As URLs `/b/<uuid>/` permitem acesso sem autenticação ao boleto do comprador.
> Atualmente não há limite de requisições, expiração de token ou bloqueio de abuso.
> O UUID é gerado uma única vez e nunca rotacionado — um token vazado concede acesso permanente.

---

### 28.1 Inventário de Risco Atual

| Risco | Vetor | Severidade |
|-------|-------|-----------|
| Token nunca expira | Token vazado em WhatsApp/e-mail arquivado dá acesso por anos | Alta |
| Sem rate limiting | Enumeração de UUIDs (improvável, mas possível) / scraping em massa | Média |
| Sem logging de acesso | Impossível auditar quem acessou o boleto e quando | Média |
| Token não rotacionado | Nova segunda via mantém o mesmo token antigo | Baixa |

---

### 28.2 Proteções a Implementar

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| S-01 | **Expiração de token** — `token_expira_em` (DateTimeField, nullable) em `Parcela`; `token_esta_expirado()` + `renovar_token(dias)`; view retorna 410 + `boleto_expirado.html` | P1 | ✅ |
| S-02 | **Rate limiting** — 20 req/hora por IP via cache Django (sem dependência externa); retorna 429; limite configurável via `BOLETO_RATE_LIMIT_POR_HORA` | P1 | ✅ |
| S-03 | **Log de acesso público** — model `AcessoBoletoPublico` (parcela FK, ip, user_agent, acessado_em); index em parcela+data e ip+data; gravado em cada GET bem-sucedido | P2 | ✅ |
| S-04 | **Rotação de token na geração** — `gerar_boleto_parcela()` chama `parcela.renovar_token()` após sucesso; gera novo UUID + nova expiração a cada boleto gerado | P2 | ✅ |
| S-05 | **Expiração configurável** — `BOLETO_TOKEN_DIAS_VALIDADE` (padrão 90) e `BOLETO_RATE_LIMIT_POR_HORA` (padrão 20) adicionados a `sync_params_from_env` | P2 | ✅ |
| S-06 | **Headers de segurança** — `X-Robots-Tag: noindex, nofollow` e `Cache-Control: private, no-store` em `boleto_publico` e `download_boleto_publico` | P2 | ✅ |
| S-07 | **Admin de monitoramento** — `AcessoBoletoPublicoAdmin` com `list_display`, `list_filter`, `search_fields`, `date_hierarchy`; somente leitura | P3 | ✅ |

---

### 28.3 Implementação S-01 — Expiração de Token

```python
# financeiro/models.py — Parcela
token_expira_em = models.DateTimeField(null=True, blank=True, verbose_name='Token expira em')

def get_link_publico(self):
    """Retorna path público /b/<uuid>/. Levanta ValueError se expirado."""
    if self.token_expira_em and timezone.now() > self.token_expira_em:
        raise TokenExpiradoError('Link público expirado. Gere uma nova segunda via.')
    return reverse('boleto_publico:visualizar', kwargs={'token': self.token_publico})
```

```python
# financeiro/views.py — boleto_publico
@ratelimit(key='ip', rate='20/h', block=True)
def boleto_publico(request, token):
    parcela = get_object_or_404(Parcela, token_publico=token)
    if parcela.token_expira_em and timezone.now() > parcela.token_expira_em:
        return render(request, 'financeiro/boleto_expirado.html', status=410)
    # ... resto da view
```

---

### 28.4 Implementação S-02 — Rate Limiting

```bash
pip install django-ratelimit==4.1.0
```

```python
# settings.py
RATELIMIT_USE_CACHE = 'default'  # Redis já configurado
RATELIMIT_FAIL_OPEN = False       # Bloqueia se Redis indisponível

# Limites por ambiente
BOLETO_RATE_LIMIT = '5/h' if not DEBUG else '1000/h'
```

---

### 28.5 Implementação S-03 — Log de Acesso

```python
# financeiro/models.py
class AcessoBoletoPublico(models.Model):
    parcela    = models.ForeignKey(Parcela, on_delete=models.CASCADE, related_name='acessos_publicos')
    ip         = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=300, blank=True)
    acessado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-acessado_em']
        indexes = [models.Index(fields=['parcela', 'acessado_em'])]
```

---

### 28.6 Dependências

| Pacote | Versão | Uso |
|--------|--------|-----|
| `django-ratelimit` | 4.1.0 | Rate limiting por IP/chave |

---

## 29. PORTABILIDADE DE BANCO DE DADOS (PostgreSQL → MySQL / Oracle)

> **Contexto:** O sistema usa exclusivamente PostgreSQL (Supabase/Render). Para clientes
> corporativos com Oracle ou MySQL já existentes, é necessário remover dependências
> PostgreSQL-específicas e criar uma camada de compatibilidade.
>
> **Estratégia:** Isolar em 2 fases — fase A (remover blockers) e fase B (drivers e testes).

---

### 29.1 Inventário de Incompatibilidades

| Item | Localização | PostgreSQL-específico | Alternativa portável |
|------|-------------|----------------------|---------------------|
| `search_path = gestao_contrato` | `settings.py` connection signal | Sim — schema isolation PG | Prefixo de tabela ou banco dedicado por cliente |
| `JSONField` (nativo PG) | `notificacoes/models.py` (4 campos) | Parcialmente — Django emula em MySQL 5.7+ / Oracle via `TextField` | `django-jsonfield-backport` ou `TextField + json` |
| `CONN_MAX_AGE=0` + `DISABLE_SERVER_SIDE_CURSORS` | `settings.py` | pgBouncer-specific | Remover para MySQL/Oracle |
| `psycopg2-binary` | `requirements.txt` | Driver exclusivo PG | Condicional por `DATABASE_ENGINE` |

---

### 29.2 Fases de Implementação

#### Fase A — Remover Blockers (P1)

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| DB-01 | **Isolar `search_path`** — envolver signal `connection_created` em `if 'postgresql' in settings.DATABASES['default']['ENGINE']`; remover para MySQL/Oracle | P1 | — |
| DB-02 | **`JSONField` portável** — criar `core/db_fields.py` com `PortableJSONField`: usa `JSONField` para PG/MySQL 5.7+, `TextField` com `from_db_value`/`get_prep_value` para Oracle | P1 | — |
| DB-03 | **Settings por driver** — `DATABASE_ENGINE` env var; `settings.py` detecta e ajusta `CONN_MAX_AGE`, `DISABLE_SERVER_SIDE_CURSORS`, `OPTIONS` automaticamente | P1 | — |
| DB-04 | **Remover `pg_catalog` direto** — verificar e substituir qualquer `RawSQL`/`.raw()` que use sintaxe PG | P2 | — |

#### Fase B — Drivers e Testes (P2)

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| DB-05 | **Driver MySQL** — adicionar `mysqlclient==2.2.*` e `PyMySQL==1.1.*` em `requirements.txt`; configurar `DATABASES` para MySQL com charset `utf8mb4` | P2 | — |
| DB-06 | **Driver Oracle** — adicionar `cx_Oracle==8.*` (ou `python-oracledb==2.*`); configurar `NLS_LANG`, `BLOB` para campos `FileField` em Oracle | P2 | — |
| DB-07 | **Migration portável** — revisar todas as migrations; substituir `default=uuid.uuid4` por `default=uuid.uuid4` (já portável); garantir que `TextField` mínimo seja `VARCHAR(max)` compatível com Oracle | P2 | — |
| DB-08 | **Test suite multi-banco** — CI GitHub Actions com matrix: `[postgresql, mysql, sqlite]`; Oracle em pipeline separado (licença) | P3 | — |
| DB-09 | **Documentação de setup** — `docs/deployment/DATABASES.md`: instruções de string de conexão, drivers e variáveis de ambiente para cada banco | P3 | — |

---

### 29.3 Arquitetura `PortableJSONField`

```python
# core/db_fields.py
import json
from django.db import models

class PortableJSONField(models.JSONField):
    """JSONField portável: usa nativo no PG/MySQL ≥5.7, emula via TextField no Oracle."""

    def db_type(self, connection):
        vendor = connection.vendor
        if vendor == 'postgresql':
            return 'jsonb'
        if vendor == 'mysql':
            return 'json'
        # Oracle, SQLite, outros: TEXT
        return 'NCLOB' if vendor == 'oracle' else 'text'

    def from_db_value(self, value, expression, connection):
        if isinstance(value, str):
            return json.loads(value)
        return value

    def get_prep_value(self, value):
        if value is None:
            return value
        return json.dumps(value, ensure_ascii=False)
```

---

### 29.4 Configuração Dinâmica de `settings.py`

```python
# settings.py — detecção automática de engine
_DB_ENGINE = env('DATABASE_ENGINE', default='postgresql')

DATABASES = {
    'default': {
        'ENGINE': f'django.db.backends.{_DB_ENGINE}',
        'NAME': env('DB_NAME', default='gestao_contrato'),
        ...
    }
}

# Opções específicas por driver
if _DB_ENGINE == 'postgresql':
    DATABASES['default']['OPTIONS'] = {'options': '-c search_path=gestao_contrato'}
    DATABASES['default']['CONN_MAX_AGE'] = 0
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
elif _DB_ENGINE == 'mysql':
    DATABASES['default']['OPTIONS'] = {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}
elif _DB_ENGINE == 'oracle':
    DATABASES['default']['OPTIONS'] = {'threaded': True}
```

---

### 29.5 Variáveis de Ambiente Adicionais

| Variável | Valores | Padrão |
|----------|---------|--------|
| `DATABASE_ENGINE` | `postgresql` / `mysql` / `oracle` / `sqlite3` | `postgresql` |
| `DB_NAME` | Nome do banco / serviço Oracle | `gestao_contrato` |
| `DB_HOST` | Host do servidor | via `DATABASE_URL` |
| `DB_PORT` | Porta do servidor | padrão do driver |

---

## 30. CHATBOT WHATSAPP — HUMANIZAÇÃO COM IA (Claude API)

> **Contexto:** O chatbot atual (Seção 27) usa um despachante de regras fixas com 5 intents.
> Funciona bem para fluxos estruturados, mas respostas são mecânicas e não compreendem
> perguntas livres ("Quando vence minha próxima?", "Tenho desconto se pagar hoje?").
>
> **Estratégia:** Manter os fluxos estruturados existentes como ferramentas (tools) e
> adicionar uma camada de IA (Claude API) para: entendimento de linguagem natural,
> respostas humanizadas, contexto de conversa e tratamento de perguntas não mapeadas.

---

### 30.1 Arquitetura Proposta

```
Mensagem do Cliente
        │
        ▼
 ┌─────────────────────────────┐
 │   Camada IA (Claude API)    │
 │   claude-haiku-4-5          │  ← rápido, barato, < 1s
 │   + system prompt + tools   │
 └──────────┬──────────────────┘
            │  tool_use → intent identificado
            ▼
 ┌─────────────────────────────┐
 │   Despachante Existente     │  ← _iniciar_2a_via(),
 │   (whatsapp_bot.py)         │     _iniciar_atraso(), etc.
 └──────────┬──────────────────┘
            │  dados estruturados do DB
            ▼
 ┌─────────────────────────────┐
 │   Claude gera resposta      │  ← humaniza o texto final
 │   com dados reais do DB     │     com nome, tom, emojis
 └──────────┬──────────────────┘
            │
            ▼
     Mensagem WhatsApp
```

---

### 30.2 Items de Implementação

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| H-01 | **Dependência** — `anthropic>=0.34` em `requirements.txt`; `ANTHROPIC_API_KEY` no Render | P1 | — |
| H-02 | **Classificador de intent** — `AIIntentClassifier.classificar(texto, contexto_sessao)`: chama `claude-haiku-4-5` com tool_use; tools = `["segunda_via", "atraso", "comprovante", "resumo", "atendente", "pergunta_livre"]`; fallback para despachante atual se API indisponível | P1 | — |
| H-03 | **Humanizador de resposta** — `AIResponseHumanizer.humanizar(dados_db, intent, nome_comprador)`: recebe dados estruturados (parcela, valores, datas) e gera texto natural; tom: prestativo, direto, sem formalidade excessiva | P1 | — |
| H-04 | **Contexto de sessão** — salvar últimas 6 mensagens em `SessaoConversaWhatsApp.dados` (JSON); passadas ao Claude como `messages` para manter contexto | P2 | — |
| H-05 | **Pergunta livre** — quando intent = `pergunta_livre`, Claude responde com base nos dados do comprador (contratos, parcelas) sem acionar fluxo estruturado; limita resposta a tópicos financeiros/contratuais | P2 | — |
| H-06 | **Delay de digitação** — `asyncio.sleep(random.uniform(0.8, 2.0))` antes de enviar resposta; simula tempo de leitura/digitação humana via Evolution API `typing indicator` | P2 | — |
| H-07 | **Fallback gracioso** — se Claude API retornar erro/timeout (>3s), cair silenciosamente para despachante de regras atual; usuário não percebe a troca | P2 | — |
| H-08 | **Prompt de sistema** — `SYSTEM_PROMPT` configurável em `ParametroSistema` com chave `CHATBOT_SYSTEM_PROMPT`; padrão define tom, limites (só assuntos do contrato), idioma (pt-BR) e persona | P2 | — |
| H-09 | **Limite de custo** — `CHATBOT_MAX_TOKENS_POR_RESPOSTA = 300`; `CHATBOT_MODELO = 'claude-haiku-4-5'` (≈ R$0,002/conversa); alertar admin se > R$50/mês via log | P3 | — |
| H-10 | **A/B testing** — flag `CHATBOT_IA_ATIVO` em `ParametroSistema`; permite ligar/desligar IA sem deploy | P3 | — |
| H-11 | **Métricas de qualidade** — gravar `intent_detectado`, `confianca`, `modelo_usado`, `tokens_usados`, `latencia_ms` em `SessaoConversaWhatsApp.dados`; dashboard admin com médias mensais | P3 | — |

---

### 30.3 System Prompt Padrão

```
Você é o assistente virtual de cobrança da {NOMEIMOBILIARIA}.
Seu nome é "Assistente {NOMEIMOBILIARIA}".

PERSONALIDADE:
- Prestativo e cordial, sem ser excessivamente formal
- Direto ao ponto — o comprador quer resolver, não ler parágrafos
- Use emojis com moderação (1-2 por mensagem, apenas quando naturais)
- Idioma: português brasileiro, informal mas profissional

ESCOPO:
- Responda APENAS sobre: boletos, parcelas, contratos, pagamentos, situação financeira
- Para assuntos fora do escopo: "Para outros assuntos, fale com um atendente humano"
- Nunca invente dados — use apenas as informações fornecidas no contexto

FORMATO:
- Respostas curtas (máx. 3 parágrafos para WhatsApp)
- Valores sempre em R$ com centavos: "R$ 1.234,56"
- Datas no formato brasileiro: "15/06/2025"
- Nunca use markdown (asteriscos, #) — WhatsApp usa *negrito* diferente
```

---

### 30.4 Integração com Código Existente

```python
# notificacoes/whatsapp_bot.py — processar()
from notificacoes.ai_chatbot import AIIntentClassifier, AIResponseHumanizer

class WhatsAppBotService:
    def processar(self, telefone, mensagem, **kwargs):
        sessao = self._obter_ou_criar_sessao(telefone)

        # IA: classificar intent (com fallback para regras)
        if settings.get_param('CHATBOT_IA_ATIVO', 'false') == 'true':
            intent = AIIntentClassifier.classificar(mensagem, sessao)
        else:
            intent = self._classificar_regras(mensagem)  # lógica atual

        # Despachar fluxo estruturado (código existente)
        dados_db = self._despachar(intent, sessao)

        # IA: humanizar resposta
        if settings.get_param('CHATBOT_IA_ATIVO', 'false') == 'true':
            return AIResponseHumanizer.humanizar(dados_db, intent, sessao)
        return dados_db  # resposta texto atual
```

---

### 30.5 Modelo e Custo Estimado

| Modelo | Latência | Custo/1k tokens | Custo/mês (500 conv.) |
|--------|----------|-----------------|----------------------|
| `claude-haiku-4-5` | ~400ms | Input: $0.80 / Output: $4.00 | ~R$ 8–15 |
| `claude-sonnet-4-6` | ~1.2s | Input: $3.00 / Output: $15.00 | ~R$ 40–80 |

> **Recomendação:** Usar `claude-haiku-4-5` para classificação de intent (barato, rápido)
> e `claude-haiku-4-5` para humanização de resposta (volume alto). Reservar Sonnet apenas
> para perguntas livres complexas (`pergunta_livre` intent com fallback).

---

### 30.6 Variáveis de Ambiente

| Variável | Descrição | Onde configurar |
|----------|-----------|-----------------|
| `ANTHROPIC_API_KEY` | Chave da API Claude | Render → Secret (sync: false) |
| `CHATBOT_IA_ATIVO` | Liga/desliga IA (`true`/`false`) | `ParametroSistema` ou env var |
| `CHATBOT_MODELO` | Modelo padrão | `ParametroSistema` (padrão: `claude-haiku-4-5`) |
| `CHATBOT_MAX_TOKENS` | Limite de tokens por resposta | `ParametroSistema` (padrão: `300`) |

---

## 31. VERSÃO DO SISTEMA NO RODAPÉ + ID DE PÁGINA

> **Contexto:** O rodapé atual mostra apenas nome e créditos. O usuário precisa saber
> em qual versão do sistema está e qual página está vendo (útil para suporte e rastreamento).
> Cada commit deve incrementar automaticamente o número de versão (patch).

---

### 31.1 Itens de Implementação

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| V-01 | **Arquivo `VERSION`** — arquivo de texto na raiz do projeto com `MAJOR.MINOR` (ex: `3.1`); PATCH = `git rev-list --count HEAD` em runtime | P1 | ✅ |
| V-02 | **Context processor** — `core/context_processors.py`: `system_info(request)` injeta `system_version`, `page_id` (4 dígitos) e `page_view_name` em todos os templates; registrado em `TEMPLATES[0]['OPTIONS']['context_processors']` | P1 | ✅ |
| V-03 | **Mapeamento de IDs de página** — `PAGE_ID_MAP` em `core/context_processors.py`: dicionário `'app:view_name' → '0000'`; fallback `'0000'` para páginas sem ID | P1 | ✅ |
| V-04 | **Rodapé atualizado** — `templates/base.html` e `portal_base.html`: linha `v{{ system_version }} \| Página {{ page_id }}` no footer; estilo discreto (`opacity:0.65`) | P1 | ✅ |
| V-05 | **Build number automático** — `core/version.py` chama `git rev-list --count HEAD` em subprocess; resultado cacheado por processo (não por request); funciona em Render sem nenhuma variável de ambiente | P2 | ✅ |
| V-06 | **Git pre-commit hook** — `.git/hooks/pre-commit`: lê `VERSION`, incrementa PATCH, reescreve o arquivo e faz `git add VERSION`; assim cada commit local incrementa automaticamente o patch | P2 | — |
| V-07 | **Claude Code hook** — `.claude/settings.json` `PostToolUse` em `git commit`: executa `python scripts/bump_version.py patch` que faz o mesmo que V-06, garantindo incremento via Claude Code | P2 | — |
| V-08 | **Tooltip no rodapé** — hover no número de versão mostra: commit hash abreviado (`git rev-parse --short HEAD`), data do build e ambiente (`DEV` / `PROD`) | P3 | — |

---

### 31.2 Estrutura do `VERSION`

```
# Arquivo: VERSION (na raiz do projeto)
3.1.0
```

Leitura em `settings.py`:
```python
import pathlib
_VERSION_FILE = pathlib.Path(BASE_DIR) / 'VERSION'
APP_VERSION = _VERSION_FILE.read_text(encoding='utf-8').strip() if _VERSION_FILE.exists() else '0.0.0'
```

---

### 31.3 Context Processor

```python
# core/context_processors.py
from django.conf import settings

def system_version(request):
    page_id = getattr(request, 'page_id', 0)
    return {
        'SYSTEM_VERSION': getattr(settings, 'APP_VERSION', '—'),
        'PAGE_ID': page_id,
    }
```

Registrar em `settings.py`:
```python
TEMPLATES[0]['OPTIONS']['context_processors'].append(
    'core.context_processors.system_version'
)
```

---

### 31.4 Mapeamento de IDs de Página

```python
# core/page_ids.py — cada URL name recebe um ID de 4 dígitos único
PAGE_ID_MAP = {
    # Core
    'core:index':                 1000,
    'core:dashboard':             1001,
    'core:listar_imoveis':        1010,
    'core:criar_imovel':          1011,
    'core:editar_imovel':         1012,
    'core:listar_imobiliarias':   1020,
    'core:listar_compradores':    1030,
    'core:listar_contabilidades': 1040,
    'core:listar_acessos':        1050,
    'core:busca_global':          1060,
    # Contratos
    'contratos:listar':           2000,
    'contratos:detalhe':          2001,
    'contratos:criar':            2002,
    'contratos:editar':           2003,
    # Financeiro
    'financeiro:listar_parcelas': 3000,
    'financeiro:detalhe_parcela': 3001,
    'financeiro:listar_boletos':  3010,
    'financeiro:listar_reajustes':3020,
    'financeiro:listar_remessas': 3030,
    'financeiro:listar_retornos': 3040,
    'financeiro:upload_ofx':      3050,
    'financeiro:dashboard_conciliacao': 3060,
    'financeiro:simulador_antecipacao': 3070,
    'financeiro:visualizar_boleto':     3080,
    # Notificações
    'notificacoes:listar':        4000,
    'notificacoes:painel_mensagens': 4010,
    'notificacoes:listar_configs_email':    4020,
    'notificacoes:listar_configs_whatsapp': 4030,
    'notificacoes:listar_templates':        4040,
    # Portal Comprador
    'portal_comprador:dashboard': 5000,
    'portal_comprador:contratos': 5001,
    'portal_comprador:boletos':   5002,
    # Admin
    'admin:index':                9000,
    # API / Tasks
    'core:health_check':          8000,
    'core:task_run_all':          8010,
}
```

Middleware para injetar `request.page_id`:
```python
# core/middleware.py
from core.page_ids import PAGE_ID_MAP

class PageIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        url_name = getattr(getattr(request, 'resolver_match', None), 'view_name', '')
        request.page_id = PAGE_ID_MAP.get(url_name, 0)
        return response
```

---

### 31.5 Rodapé (`base.html`)

```html
<footer class="app-footer">
    <div class="container center-align">
        <p class="mb-0">
            <strong>Sistema de Gestão de Contratos de Venda de Imóveis</strong>
        </p>
        <p class="mb-0">
            Desenvolvido por <strong>Maxwell da Silva Oliveira</strong> |
            <a href="https://msbrasil.inf.br" target="_blank" class="white-text">M&S do Brasil LTDA</a>
        </p>
        <p class="mt-1 mb-0 text-muted" style="font-size:0.75rem; opacity:0.7;">
            v{{ SYSTEM_VERSION }}
            {% if PAGE_ID %} · PG-{{ PAGE_ID|stringformat:"04d" }}{% endif %}
        </p>
    </div>
</footer>
```

**Exemplo de exibição:** `v3.1.247 · PG-2001`
- `3.1` = MAJOR.MINOR (manual)
- `247` = número de commits (`git rev-list --count HEAD`) — sempre incrementa
- `2001` = ID da página `contratos:detalhe`

---

### 31.6 Build Number via `build.sh` (Render)

```bash
# build.sh — adicionar antes do collectstatic
echo "==> Calculando build number..."
BUILD_NUMBER=$(git rev-list --count HEAD 2>/dev/null || echo "0")
MAJOR_MINOR=$(cat VERSION 2>/dev/null | cut -d. -f1,2 || echo "3.1")
echo "${MAJOR_MINOR}.${BUILD_NUMBER}" > VERSION_BUILD
echo "Versão do sistema: ${MAJOR_MINOR}.${BUILD_NUMBER}"
```

```python
# settings.py
_VERSION_BUILD = (BASE_DIR / 'VERSION_BUILD')
APP_VERSION = _VERSION_BUILD.read_text().strip() if _VERSION_BUILD.exists() else (
    (BASE_DIR / 'VERSION').read_text().strip() if (BASE_DIR / 'VERSION').exists() else '0.0.0'
)
```

---

### 31.7 Git Hook — Auto-incremento Local

```bash
#!/bin/sh
# .git/hooks/pre-commit
VERSION_FILE="$(git rev-parse --show-toplevel)/VERSION"
if [ -f "$VERSION_FILE" ]; then
    CURRENT=$(cat "$VERSION_FILE")
    MAJOR=$(echo "$CURRENT" | cut -d. -f1)
    MINOR=$(echo "$CURRENT" | cut -d. -f2)
    PATCH=$(echo "$CURRENT" | cut -d. -f3)
    NEW_PATCH=$((PATCH + 1))
    echo "${MAJOR}.${MINOR}.${NEW_PATCH}" > "$VERSION_FILE"
    git add "$VERSION_FILE"
fi
```

```bash
# Ativar o hook
chmod +x .git/hooks/pre-commit
```

> No Render, o build number é calculado por `git rev-list --count HEAD` (mais confiável
> que incremento manual, pois reflete o histórico real de commits).

---

## 32. SEGURANÇA — PROTEÇÃO DE URLs E ISOLAMENTO DE TENANT

> **Contexto:** Auditoria de segurança identificou dois problemas independentes:
>
> **Problema 1 — ID sequencial visível:** `/contratos/1055/` expõe o PK inteiro do banco.
> Um usuário autenticado pode iterar `/contratos/1/`, `/contratos/2/` … até `9999` e
> tentar acessar contratos de outras imobiliárias.
>
> **Problema 2 — Sem isolamento de tenant:** `ContratoDetailView.get_queryset()` e
> `detalhe_parcela()` não filtram por imobiliária do usuário logado — qualquer usuário
> autenticado acessa qualquer objeto do banco. As funções `get_imobiliarias_usuario()` e
> `usuario_tem_acesso_imobiliaria()` já existem em `core/models.py` mas **não são usadas**
> em `contratos/views.py` nem em `financeiro/views.py`.
>
> **Escopo auditado:** 109 URL patterns com `<int:pk>` em 5 apps.

---

### 32.1 Inventário de Risco

| Superfície | URLs | Risco | Auth | Tenant Isolation |
|-----------|------|-------|------|-----------------|
| `contratos/` | 20 | Contrato de outra imobiliária visível | ✅ | ❌ |
| `financeiro/` | 59 | Parcelas, boletos, CNAB de qualquer contrato | ✅ | ❌ |
| `core/` | 20 | Entidades core (usa `get_imobiliarias_usuario`) | ✅ | ✅ parcial |
| `notificacoes/` | 16 | Configurações e templates por imobiliária | ✅ | ❌ |
| `portal_comprador/` | 8 | URLs do comprador | ✅ | ✅ (filtra por comprador) |

---

### 32.2 Fase A — Isolamento de Tenant (P1, crítico)

> Resolver o acesso cruzado **independentemente** da obfuscação de URL.
> O helper `get_imobiliarias_usuario(user)` já retorna o queryset correto de imobiliárias.

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| T-01 | **`ContratoListView`** — `TenantMixin` (get_queryset filtra por imobiliária); contadores e dropdown de imobiliárias limitados ao tenant | `contratos/views.py` | ✅ |
| T-02 | **`ContratoDetailView / UpdateView / DeleteView`** — `TenantMixin` (get_object verifica imobiliária via dotted tenant_field) | `contratos/views.py` | ✅ |
| T-03 | **`detalhe_parcela()`** — `verificar_acesso_tenant(request, parcela.contrato.imobiliaria)`; parcela buscada com `select_related('contrato__imobiliaria')` | `financeiro/views.py` | ✅ |
| T-04 | **Todos os endpoints de parcela/boleto** — 11 views protegidas: `registrar_pagamento`, `gerar_boleto_parcela`, `notificar_inadimplente`, `download_boleto`, `visualizar_boleto`, `cancelar_boleto`, `api_status_boleto`, `segunda_via_boleto`, `gerar_boletos_contrato`, `download_zip_boletos` + mais | `financeiro/views.py` | ✅ |
| T-05 | **Remessa CNAB** — `listar_arquivos_remessa` filtra por `_imobs_para_usuario()`; `detalhe`, `regenerar`, `marcar_enviada`, `excluir`, `download` verificam `conta_bancaria.imobiliaria` | `financeiro/views.py` | ✅ |
| T-06 | **Retorno CNAB** — `listar_arquivos_retorno` filtra por `_imobs_para_usuario()`; `detalhe`, `processar`, `download` verificam `conta_bancaria.imobiliaria` | `financeiro/views.py` | ✅ |
| T-07 | **Notificações** — `reenviar_notificacao` verifica `parcela.contrato.imobiliaria`; `IntermediariasListView/DetailView` com `TenantMixin` | `notificacoes/views.py` | ✅ |
| T-08 | **`TenantMixin` + `verificar_acesso_tenant()`** — em `core/mixins.py`: `get_object()` e `get_queryset()` com atributos `tenant_field`/`tenant_filter` customizáveis; helper FBV levanta `PermissionDenied` | `core/mixins.py` | ✅ |

**Padrão para T-01/T-02 (Class-based Views):**
```python
# core/mixins.py
class TenantMixin:
    """Filtra queryset pelas imobiliárias do usuário logado. Superuser vê tudo."""
    tenant_field = 'imovel__imobiliaria'  # campo de FK para imobiliaria

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        imobs = get_imobiliarias_usuario(self.request.user)
        return qs.filter(**{self.tenant_field + '__in': imobs})
```

```python
# contratos/views.py
class ContratoDetailView(LoginRequiredMixin, TenantMixin, DetailView):
    model = Contrato
    tenant_field = 'imovel__imobiliaria'  # herda proteção automática
```

**Padrão para T-03/T-04 (Function-based Views):**
```python
# core/decorators.py
def tenant_required(get_imobiliaria):
    """Decorador para function-based views — verifica acesso ao objeto."""
    def decorator(func):
        @wraps(func)
        def wrapper(request, pk, *args, **kwargs):
            obj = get_object_or_404(get_imobiliaria.__self__.__class__, pk=pk)
            imob = get_imobiliaria(obj)
            if not request.user.is_superuser and not usuario_tem_acesso_imobiliaria(request.user, imob):
                raise PermissionDenied
            return func(request, pk, *args, **kwargs)
        return wrapper
    return decorator
```

---

### 32.3 Fase B — Obfuscação de URL com Hashids (P2)

> Substituir `/contratos/1055/` por `/contratos/Xk9mP3/` sem mudar modelos.
> Hashids codifica o inteiro usando uma chave secreta — reversível só pelo servidor.
> Não elimina Problema 2 (tenant), mas elimina a legibilidade e o risco de enumeração.

| # | Item | Status |
|---|------|--------|
| U-01 | **Instalar `hashids==1.3.1`** — `pip install hashids`; adicionar `HASHIDS_SALT = SECRET_KEY[:20]` e `HASHIDS_MIN_LENGTH = 6` em `settings.py` | — |
| U-02 | **`core/hashids_utils.py`** — funções `encode_id(pk) → str` e `decode_id(h) → int`; usam salt do settings; retornam `None` se hash inválido | — |
| U-03 | **URL pattern `<str:hid>`** — substituir `<int:pk>` por `<str:hid>` nos apps `contratos/`, `financeiro/`, `core/`; view decodifica antes do `get_object_or_404` | — |
| U-04 | **Template tag `{% hashid obj.pk %}`** — para gerar links nos templates sem expor PK: `{% url 'contratos:detalhe' obj.pk|hashid %}` | — |
| U-05 | **Rota de compatibilidade** — manter redirecionamento `<int:pk>/` → `<str:hid>/` por 30 dias para não quebrar links antigos em e-mails já enviados | — |
| U-06 | **Admin Django** — admin continua usando PK inteiro (acesso restrito a staff) | — |

**Exemplo de implementação:**
```python
# core/hashids_utils.py
from hashids import Hashids
from django.conf import settings

_h = Hashids(salt=settings.HASHIDS_SALT, min_length=settings.HASHIDS_MIN_LENGTH)

def encode_id(pk: int) -> str:
    return _h.encode(pk)

def decode_id(hid: str) -> int | None:
    decoded = _h.decode(hid)
    return decoded[0] if decoded else None
```

```python
# contratos/views.py — URL: contratos/<str:hid>/
def detalhe_contrato(request, hid):
    from core.hashids_utils import decode_id
    pk = decode_id(hid)
    if pk is None:
        raise Http404
    contrato = get_object_or_404(Contrato, pk=pk)
    # + verificação de tenant (T-01)
    ...
```

```html
<!-- template: antes -->
<a href="{% url 'contratos:detalhe' contrato.pk %}">ver</a>

<!-- template: depois -->
{% load hashids_tags %}
<a href="{% url 'contratos:detalhe' contrato.pk|hashid %}">ver</a>
```

---

### 32.4 Fase C — Defesa em Profundidade (P3)

| # | Item | Status |
|---|------|--------|
| D-01 | **Middleware anti-enumeração** — contador Redis por IP: se mesmo IP retornar > 30 respostas 403/404 em 5 min, banir por 1 hora (retornar 429) | — |
| D-02 | **Log de acesso negado** — model `AcessoNegado`: IP, user, URL, timestamp; admin com lista filtrável | — |
| D-03 | **Header `X-Content-Type-Options: nosniff`** + `X-Frame-Options: DENY` — `SecurityMiddleware` já configura; confirmar que está ativo | — |
| D-04 | **Teste automatizado de isolamento** — suite de testes: login como `user_A` (imobiliária X), tentar GET no contrato de `user_B` (imobiliária Y) → deve retornar 403 | — |

---

### 32.5 Ordem de Implementação Recomendada

```
Semana 1: T-01 a T-05 (isolamento tenant — contratos e parcelas principais)
Semana 2: T-06 a T-08 (APIs e notificações) + D-04 (testes automatizados)
Semana 3: U-01 a U-04 (hashids nas URLs principais: contratos, parcelas)
Semana 4: U-05 a U-06 + D-01 a D-03 (compatibilidade + defesa em profundidade)
```

> **Prioridade absoluta: Fase A (T-01..T-08).**
> A obfuscação de URL (Fase B) é uma defesa secundária — sem o isolamento de tenant,
> hashids não impede o acesso cruzado (hash é reversível pelo próprio sistema).

---

### 32.6 Resumo de Risco

| Problema | Impacto | Solução | Fase |
|---------|---------|---------|------|
| Usuário vê contratos de outra imobiliária | **CRÍTICO** | TenantMixin + tenant_required | A |
| IDs sequenciais visíveis na URL | Alto | Hashids `Xk9mP3` | B |
| Sem log de tentativas de enumeração | Médio | Middleware + AcessoNegado | C |
| 109 templates com `obj.pk` exposto | Médio | Template tag `{% hashid %}` | B |
