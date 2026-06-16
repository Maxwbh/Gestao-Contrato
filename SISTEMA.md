# Sistema de Gestão de Contratos — Documentação Técnica

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Última atualização:** 2026-06-16

> Documentação completa do que está implementado no sistema.
> Para novas funcionalidades, consulte **[ROADMAP.md](ROADMAP.md)**.

---

## 1. VISÃO GERAL

Sistema para contabilidades que gerenciam múltiplos loteamentos/imobiliárias:

| Entidade | Descrição |
|----------|-----------|
| **Contabilidade** | Gerencia múltiplas imobiliárias |
| **Imobiliária** | Beneficiário financeiro dos contratos |
| **Imóvel** | Lote, terreno, casa, apartamento, comercial |
| **Comprador** | Cliente (PF ou PJ) que adquire o imóvel |
| **Contrato** | Até 360 meses, até 30 intermediárias, reajuste configurável |

---

## 2. APPS DJANGO

```
gestao_contrato/          # Configuração do projeto
├── accounts/             # Autenticação (login, logout, registro, perfil)
├── core/                 # Entidades base (Contabilidade, Imobiliária, Imóvel, Comprador)
│   └── services/
│       └── ia_monitor.py         # Monitoramento de uso e custo de IA
├── contratos/            # Gestão de contratos e prestações intermediárias
│   └── services/
│       └── importacao_ia.py      # Cadeia de importação PDF via IA (4 níveis)
├── financeiro/           # Parcelas, boletos, reajustes, CNAB
├── notificacoes/         # Email, SMS, WhatsApp (configurações e templates)
│   └── ai_chatbot.py             # Chatbot WhatsApp com IA (Claude)
└── portal_comprador/     # Portal de autoatendimento do comprador
```

---

## 3. MODELOS IMPLEMENTADOS

### 3.1 Core (`core/models.py`)
| Modelo | Descrição |
|--------|-----------|
| `TimeStampedModel` | Base abstrata com `created_at`, `updated_at` |
| `Contabilidade` | Escritório contábil |
| `Imobiliaria` | Vinculada à contabilidade |
| `ContaBancaria` | Dados bancários para boletos |
| `TipoImovel` | Choices: LOTE, TERRENO, CASA, APARTAMENTO, COMERCIAL |
| `Imovel` | Imóvel disponível para venda |
| `Comprador` | PF ou PJ |
| `AcessoUsuario` | Controle de acesso por contabilidade/imobiliária |

### 3.2 Contratos (`contratos/models.py`)
| Modelo | Descrição |
|--------|-----------|
| `TipoCorrecao` | Choices: IPCA, IGPM, SELIC, FIXO |
| `TipoAmortizacao` | Choices: PRICE, SAC |
| `IndiceReajuste` | Histórico de índices econômicos |
| `StatusContrato` | Choices: ATIVO, QUITADO, CANCELADO, SUSPENSO |
| `TipoPrestacao` | Choices: NORMAL, INTERMEDIARIA, ENTRADA |
| `Contrato` | Contrato de venda com configurações de reajuste |
| `TabelaJurosContrato` | Tabela de juros escalantes por ciclo (HU-360) |
| `PrestacaoIntermediaria` | Parcelas intermediárias (máx. 30) |
| `HistoricoReajusteIntermediaria` | Log de reajustes aplicados às intermediárias |
| `MinutaContrato` | Versões de minuta com controle de minuta ativa (única por contrato) |
| `StatusImportacao` | Choices: PENDENTE, EXTRAINDO, REVISAO, CONCLUIDO, ERRO |
| `ContratoImportacao` | Lifecycle de importação via IA: arquivo, dados extraídos (JSON), contrato criado |

### 3.3 Financeiro (`financeiro/models.py`)
| Modelo | Descrição |
|--------|-----------|
| `StatusBoleto` | Choices: PENDENTE, GERADO, REGISTRADO, PAGO, VENCIDO, CANCELADO |
| `TipoParcela` | Choices: NORMAL, INTERMEDIARIA, ENTRADA |
| `Parcela` | Parcela mensal com ciclo de reajuste |
| `Reajuste` | Registro de reajuste aplicado |
| `HistoricoPagamento` | Log de pagamentos |
| `StatusArquivoRemessa` | Choices: PENDENTE, ENVIADO, PROCESSADO |
| `ArquivoRemessa` | CNAB remessa |
| `ItemRemessa` | Itens da remessa |
| `StatusArquivoRetorno` | Choices: PENDENTE, PROCESSADO, ERRO |
| `ArquivoRetorno` | CNAB retorno |
| `ItemRetorno` | Itens do retorno |
| `AcessoBoletoPublico` | Token de acesso público a boleto (link sem autenticação) |
| `EventoPIX` | Log de eventos recebidos via webhook PIX (dedup por `EndToEndId`) |

### 3.4 Notificações (`notificacoes/models.py`)
| Modelo | Descrição |
|--------|-----------|
| `ConfiguracaoEmail` | SMTP settings |
| `ConfiguracaoSMS` | Twilio settings |
| `ConfiguracaoWhatsApp` | Twilio WhatsApp settings |
| `Notificacao` | Notificação enviada/pendente |
| `TemplateNotificacao` | Templates personalizáveis |

### 3.5 Portal do Comprador (`portal_comprador/models.py`)
| Modelo | Descrição |
|--------|-----------|
| `AcessoComprador` | Vincula `Comprador` ao `User` Django |
| `LogAcessoComprador` | Registro de acessos com IP e data |
| `ComprovantePagamentoUpload` | Upload de comprovante com aprovação/rejeição e bloqueio anti-duplo-pagamento |
| `PushSubscriptionPortal` | Assinatura Web Push por comprador (VAPID); unique por `(acesso_comprador, endpoint)` |

---

## 4. SERVIÇOS IMPLEMENTADOS

### 4.1 BoletoService (`financeiro/services/boleto_service.py`)
- Geração de boletos via BRCobrança API
- Suporte a múltiplos bancos (BB, Bradesco, Itaú, Sicoob, etc.)
- Validação de dados antes do envio
- Tratamento de erros e retry

### 4.2 CNABService (`financeiro/services/cnab_service.py`)
- Geração de arquivo remessa CNAB 240/400
- Processamento de arquivo retorno CNAB 240/400
- Mapeamento de bancos e ocorrências
- Fallback local quando API indisponível

### 4.3 ReajusteService (`financeiro/services/reajuste_service.py`)
- Busca de índices do Banco Central (TR, SELIC, IPCA, IGP-M)
- Simulação de reajuste
- Aplicação de reajuste em lote
- Listagem de contratos com reajuste pendente

### 4.4 RelatorioService (`financeiro/services/relatorio_service.py`)
- Relatório de Prestações a Pagar
- Relatório de Prestações Pagas
- Relatório de Posição de Contratos (`gerar_relatorio_posicao_contratos(FiltroRelatorio)`)
- Relatório de Previsão de Reajustes
- Exportação: CSV, JSON, PDF, Excel (`exportar_para_excel`, `exportar_para_pdf`)

### 4.5 CarneService (`financeiro/services/carne_service.py`)
- Geração de carnê PDF multi-página (seleção de parcelas)
- Download via `download_carne_pdf`

### 4.6 IndicesEconomicosService (`financeiro/services/indices_economicos_service.py`)
- Busca de índices IPCA (série 433), IGP-M (série 189) e SELIC (série 432) na API BCB
- Cache e fallback para último índice conhecido

### 4.7 OFXService (`financeiro/services/ofx_service.py`)
- Importação de extrato bancário no formato OFX
- Conciliação com parcelas e histórico de pagamentos

### 4.8 ReciboService (`financeiro/services/recibo_service.py`)
- Geração de recibo PDF de pagamento de parcela

### 4.9 bancos.py (`financeiro/services/bancos.py`)
- Catálogo de bancos suportados com código, nome e configurações de boleto

### 4.10 ImportacaoIA (`contratos/services/importacao_ia.py`)
- `ImportacaoIA.extrair_de_pdf(bytes)` — envia PDF nativo via Claude Documents API
- `ImportacaoIA.extrair_de_imagens(pares)` — múltiplas imagens via Claude Vision API
- `ProcessadorImportacao.processar(dados, user)` — match de entidades existentes por CNPJ/CPF/matrícula
- `confirmar_importacao(importacao, post, user)` — criação atômica em `transaction.atomic()`

---

## 5. VIEWS E ROTAS PRINCIPAIS

### 5.1 Accounts (`/accounts/`)
| Rota | View | Descrição |
|------|------|-----------|
| `login/` | `login_view` | Login de usuário |
| `logout/` | `logout_view` | Logout |
| `registro/` | `registro_view` | Cadastro de novo usuário |
| `perfil/` | `perfil_view` | Visualizar/editar perfil |
| `alterar-senha/` | `alterar_senha_view` | Alterar senha |

### 5.2 Core (`/`)
| Rota | View | Descrição |
|------|------|-----------|
| `health/` | `health_check` | Health check para monitoramento |
| `dashboard/` | `dashboard` | Dashboard principal |
| `setup/` | `setup` | Configuração inicial |
| `dados-teste/` | `pagina_dados_teste` | Gerar/limpar dados de teste |
| `contabilidades/` | `ContabilidadeListView` | CRUD Contabilidades |
| `compradores/` | `CompradorListView` | CRUD Compradores |
| `imoveis/` | `ImovelListView` | CRUD Imóveis |
| `imobiliarias/` | `ImobiliariaListView` | CRUD Imobiliárias |
| `acessos/` | `AcessoUsuarioListView` | CRUD Acessos de Usuários |
| `api/bancos/` | `api_listar_bancos` | Lista de bancos |
| `api/cep/<cep>/` | `api_buscar_cep` | Busca CEP via ViaCEP |
| `api/cnpj/<cnpj>/` | `api_buscar_cnpj` | Busca CNPJ via BrasilAPI |

### 5.3 Contratos (`/contratos/`)
| Rota | View | Descrição |
|------|------|-----------|
| `/` | `ContratoListView` | Lista de contratos |
| `novo/` | `ContratoCreateView` | Criar contrato |
| `<id>/` | `ContratoDetailView` | Detalhe do contrato |
| `<id>/editar/` | `ContratoUpdateView` | Editar contrato |
| `<id>/parcelas/` | `parcelas_contrato` | Parcelas do contrato |
| `indices/` | `IndiceReajusteListView` | CRUD Índices |
| `<id>/intermediarias/` | `IntermediariasListView` | CRUD Intermediárias |

### 5.4 Financeiro (`/financeiro/`)
| Rota | View | Descrição |
|------|------|-----------|
| `dashboard/` | `DashboardFinanceiroView` | Dashboard financeiro |
| `contabilidade/dashboard/` | `DashboardContabilidadeView` | Dashboard contabilidade |
| `imobiliaria/<id>/dashboard/` | `dashboard_imobiliaria` | Dashboard por imobiliária |
| `parcelas/` | `listar_parcelas` | Lista de parcelas |
| `parcelas/<id>/` | `detalhe_parcela` | Detalhe da parcela |
| `parcelas/<id>/pagar/` | `registrar_pagamento` | Registrar pagamento |
| `parcelas/<id>/boleto/gerar/` | `gerar_boleto_parcela` | Gerar boleto |
| `contrato/<id>/gerar-carne/` | `gerar_carne` | Gerar carnê |
| `reajustes/` | `listar_reajustes` | Lista de reajustes |
| `contrato/<id>/reajuste/aplicar/` | `aplicar_reajuste_contrato` | Aplicar reajuste |
| `cnab/remessa/` | `listar_arquivos_remessa` | Remessas CNAB (lista técnica) |
| `cnab/retorno/` | `listar_arquivos_retorno` | Retornos CNAB (lista técnica) |
| `boletos/` | `boletos_painel` | **HU-24** Geração Mensal de Boletos (wizard da contadora) |
| `boletos/gerar/` | `boletos_painel_gerar` | **HU-24** Geração dirigida por escopo (todos/imobiliaria/contratos/parcela/intermediaria) |
| `remessa/` | `remessa_painel` | **HU-23** Tela 1 — Gerar Arquivo Remessa (wizard da contadora) |
| `remessa/gerar/` | `remessa_painel_gerar` | **HU-23** Geração dirigida por escopo (todos/imobiliaria/conta/boleto) |
| `retorno/` | `retorno_painel` | **HU-23** Tela 2 — Receber Arquivo de Retorno (baixa) |
| `retorno/upload/` | `remessa_painel_retorno_upload` | **HU-23** Upload + auto-processo do `.ret` |
| `relatorios/prestacoes-a-pagar/` | `RelatorioPrestacoesAPagarView` | Relatório |
| `relatorios/prestacoes-pagas/` | `RelatorioPrestacoesPageasView` | Relatório |
| `relatorios/posicao-contratos/` | `RelatorioPosicaoContratosView` | Relatório |
| `relatorios/previsao-reajustes/` | `RelatorioPrevisaoReajustesView` | Relatório |
| `api/relatorios/posicao/` | `api_relatorio_posicao_bi` | **API BI** — JSON/CSV autenticado por Bearer token |
| `api/dashboard-executivo/` | `api_dashboard_executivo` | **Dashboard executivo** — série 12 meses, KPIs, tenant isolation |
| `api/webhook/pix/` | `webhook_pix` | Webhook PIX com dedup atômico e timing-safe auth |

### 5.5 Notificações (`/notificacoes/`)
| Rota | View | Descrição |
|------|------|-----------|
| `/` | `listar_notificacoes` | Lista de notificações |
| `email/` | `ConfiguracaoEmailListView` | CRUD Config Email |
| `templates/` | `TemplateNotificacaoListView` | CRUD Templates |
| `templates/<id>/preview/` | `preview_template` | Preview do template |

### 5.6 Portal do Comprador (`/portal/`)
| Rota | View | Descrição |
|------|------|-----------|
| `cadastro/` | `auto_cadastro` | Auto-cadastro via CPF/CNPJ |
| `login/` | `login_comprador` | Login do comprador |
| `logout/` | `logout_comprador` | Logout |
| `dashboard/` | `dashboard` | Dashboard do comprador |
| `contratos/` | `meus_contratos` | Meus contratos |
| `contratos/<id>/` | `detalhe_contrato` | Detalhe do contrato |
| `boletos/` | `meus_boletos` | Meus boletos |
| `boletos/<id>/download/` | `download_boleto` | Download PDF |
| `meus-dados/` | `meus_dados` | Editar dados pessoais |
| `alterar-senha/` | `alterar_senha` | Alterar senha |
| `api/contratos/<id>/parcelas/` | `api_parcelas_contrato` | API parcelas |
| `api/resumo-financeiro/` | `api_resumo_financeiro` | API resumo |
| `manifest.json` | `portal_manifest` | **PWA** manifest JSON |
| `sw.js` | `portal_service_worker` | **PWA** service worker (scope `/portal/`) |
| `api/push/subscribe/` | `api_push_subscribe` | **Web Push** — cadastrar assinatura VAPID |
| `api/push/unsubscribe/` | `api_push_unsubscribe` | **Web Push** — remover assinatura |

---

## 6. TAREFAS AGENDADAS (CELERY + CRON-JOB.ORG)

> **Como roda em produção:** as tarefas são **definidas** como tarefas Celery
> (`gestao_contrato/celery.py` + `financeiro/tasks.py`, com agenda `celery-beat`). Porém, no
> ambiente de produção (Render Free Tier) **não há workers Celery**; por isso as mesmas rotinas
> também são expostas como **endpoints HTTP** em `core/tasks.py` (`POST /api/tasks/...`) e
> **agendadas externamente pelo cron-job.org**. Em ambientes com worker, o Celery+beat executa
> diretamente; no free tier, o cron-job.org chama os endpoints HTTP (protegidos por `TASK_TOKEN`).

| Task | Módulo | Frequência | Descrição |
|------|--------|------------|-----------|
| `buscar_indices_economicos` | `financeiro` | Diário | Busca índices do BCB |
| `verificar_alertas_reajuste` | `financeiro` | Diário | Alertas de reajuste pendente |
| `gerar_boletos_automaticos` | `financeiro` | Mensal | Gera boletos do próximo mês |
| `enviar_lembretes_vencimento` | `financeiro` | Diário | Lembretes 7, 3 e 1 dia antes |
| `atualizar_juros_multa_parcelas_vencidas` | `financeiro` | Diário | Atualiza encargos |
| `limpar_boletos_vencidos` | `financeiro` | Diário | Atualiza status de boletos |
| `gerar_relatorio_diario` | `financeiro` | Diário | Estatísticas consolidadas |
| `processar_arquivos_retorno_pendentes` | `financeiro` | Diário | Processa retornos CNAB |
| `enviar_relatorio_inadimplencia` | `financeiro` | Diário/Semanal | E-mail com tabela de parcelas vencidas (34.5) |
| `enviar_relatorio_posicao_contratos` | `financeiro` | Configurável | E-mail com anexo Excel/PDF de posição (34.5) |
| `enviar_push_comprador` | `portal_comprador` | On-demand | Envia notificação push via VAPID (34.6) |
| `notificar_push_vencimento_amanha` | `portal_comprador` | Diário | Push para parcelas com vencimento amanhã (34.6) |

**Endpoints HTTP de tarefas** (`core/tasks.py`, acionados pelo cron-job.org, protegidos por `TASK_TOKEN`):
`POST /api/tasks/run-all/`, `enviar-notificacoes/`, `enviar-inadimplentes/`, `processar-reajustes/`,
`atualizar-parcelas/`, `atualizar-indices/`, `processar-fila/`, `processar-notificacoes/`,
`relatorio-semanal/`, `relatorio-mensal/`, `processar-bounces/`, `limpar-sessoes/`,
`limpar-sessoes-whatsapp/`, `atualizar-bloqueio-credito/`, `status/`.

---

## 7. SEGURANÇA IMPLEMENTADA

| Área | Mecanismo | Onde |
|------|-----------|------|
| Timing attack | `hmac.compare_digest` (tempo constante) | Webhook PIX, API BI |
| Race condition — pagamento | `select_for_update()` + `transaction.atomic()` | `ComprovantePagamentoUpload.aprovar()` |
| Race condition — EventoPIX | `create()` dentro de `atomic()` + catch `IntegrityError` | `_processar_evento_pix()` |
| Race condition — minuta ativa | `select_for_update()` dentro de `atomic()` | `MinutaContrato.save()` |
| Upload malicioso | Validação de magic bytes (PDF/JPEG/PNG/WebP) | `ComprovantePagamentoUploadForm.clean_comprovante()` |
| Tenant isolation | `get_imobiliarias_usuario()` em todas as views | `api_dashboard_executivo`, views financeiras |
| API BI fail-closed | Retorna 503 quando `BI_API_TOKEN` vazio em produção | `api_relatorio_posicao_bi` |

---

## 8. REGRAS DE NEGÓCIO IMPLEMENTADAS

### 8.1 Contratos
- Máximo 360 parcelas (30 anos)
- Máximo 30 prestações intermediárias
- Prazo de reajuste: 1–24 meses (padrão 12)
- Entrada não pode exceder valor total
- Juros mora máximo 2%
- Multa máxima 2%
- Primeiro vencimento após data do contrato

### 8.2 Bloqueio de Boleto por Reajuste
```python
def pode_gerar_boleto(parcela):
    if parcela.paga:
        return False
    if parcela.ciclo_reajuste <= 1:
        return True  # Primeiro ciclo sempre liberado
    # Ciclos > 1: precisa do reajuste do ciclo anterior
    return Reajuste.objects.filter(
        contrato=parcela.contrato,
        ciclo=parcela.ciclo_reajuste - 1,
        aplicado=True
    ).exists()
```

### 8.3 Cálculo de Reajuste
```python
valor_reajustado = valor_atual * (1 + indice_percentual / 100)
```

---

## 9. INTEGRAÇÕES ATIVAS

| Serviço | Uso | Status |
|---------|-----|--------|
| **BRCobrança API** | Geração de boletos | ✅ Funcionando |
| **Banco Central do Brasil** | Índices TR, SELIC, IPCA, IGP-M | ✅ Funcionando |
| **ViaCEP** | Busca de endereço por CEP | ✅ Funcionando |
| **BrasilAPI** | Busca de CNPJ | ✅ Funcionando |
| **Twilio** | SMS e WhatsApp | ⚠️ Configurado, pendente testes E2E |
| **cron-job.org** | Agendador HTTP das tarefas (`/api/tasks/*`) — substitui workers Celery no Render Free Tier | ✅ Funcionando |

---

## 10. ESTRUTURA DE TESTES

```
tests/
├── conftest.py              # Fixtures globais e Factory Boy
├── pytest.ini               # Configuração pytest
├── fixtures/
│   └── factories.py         # 12 factories (User, Contrato, Parcela, etc.)
├── unit/
│   ├── contratos/           # test_contrato_models.py, test_validations.py, test_hu_*
│   ├── financeiro/          # test_hu_boleto_remessa.py, test_hu_relatorios_bi.py, test_hu_webhook_pix.py, ...
│   ├── portal_comprador/    # test_hu_portal_expandido.py, test_hu_pwa.py, test_hu_portal_e2e.py, ...
│   └── views/               # test_contrato_views.py, test_financeiro_views.py
├── integration/
│   └── test_contrato_reajuste_integration.py
└── functional/              # test_fluxo_contrato_completo.py, etc.
```

**Total:** 1335 testes | **Executar:**
```bash
pytest                              # Todos os 1335 testes
pytest tests/unit/                  # Apenas unitários
pytest --cov=. --cov-report=html    # Com cobertura
```

---

## 11. DEPLOY

### 11.1 Render.com (Produção)
- Web Service: Gunicorn + Django
- PostgreSQL: Schema `gestao_contrato`
- Redis: Cache e broker Celery
- BRCobrança: Docker service separado

### 11.2 Docker (Desenvolvimento)
```bash
docker-compose up -d   # PostgreSQL, Redis, BRCobrança
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 11.3 Variáveis de Ambiente
Veja `.env.example` para lista completa.

---

## 12. MÓDULO DE INTELIGÊNCIA ARTIFICIAL

### 12.1 Importação de Contrato via IA

A importação de contratos em PDF utiliza uma cadeia de 4 níveis ordenados por custo crescente. O sistema tenta o nível mais barato primeiro e só escala para o próximo quando há falha ou resultado insuficiente.

| Nível | Modelo | Custo | Condição de escalonamento |
|-------|--------|-------|--------------------------|
| 1 | Gemini 2.0 Flash (Google) | Gratuito (tier free) | Falha na API ou extração incompleta |
| 2 | Claude Haiku (Anthropic) | ~US$ 0,25/MTok input | Extração incompleta ou confiança baixa |
| 3 | Claude Sonnet (Anthropic) | ~US$ 3,00/MTok input | Extração incompleta ou confiança baixa |
| 4 | Claude Opus (Anthropic) | ~US$ 15,00/MTok input | Último recurso; falha gera erro ao usuário |

**Entry point:** `contratos/services/importacao_ia.py`  
**View de upload:** `contratos/views.py → upload_importacao`  
**Modelo de lifecycle:** `ContratoImportacao` — persiste arquivo, dados JSON extraídos e status (`PENDENTE → EXTRAINDO → REVISAO → CONCLUIDO / ERRO`)

**Configuração:**

```env
GEMINI_API_KEY=...        # Tier gratuito do Google AI Studio; opcional — sem essa chave o sistema pula direto para Claude Haiku
ANTHROPIC_API_KEY=...     # Obrigatória para os níveis 2–4
```

O Gemini é chamado via REST puro (sem SDK). Se a chave estiver ausente ou a chamada retornar erro, o sistema avança imediatamente para o nível Claude Haiku sem exibir erro ao usuário. Todos os modelos recebem o PDF como documento nativo (Claude Documents API / Gemini inline_data), portanto não é feita conversão para imagem antes do envio.

Após a extração, `ProcessadorImportacao.processar()` faz match das entidades extraídas (imobiliária, comprador, imóvel) por CNPJ, CPF ou matrícula antes de apresentar a tela de revisão. A confirmação chama `confirmar_importacao()` dentro de `transaction.atomic()`.

---

### 12.2 Chatbot WhatsApp com IA

**Arquivo:** `notificacoes/ai_chatbot.py`

O chatbot recebe mensagens WhatsApp via webhook Twilio e segue dois estágios com Claude:

1. **Classificador de intent** — usa `tool_use` (function calling) para identificar a intent da mensagem entre as opções registradas. Permite que o modelo devolva parâmetros estruturados (ex.: número do contrato consultado).
2. **Humanizador de resposta** — recebe a resposta técnica gerada pelas regras de negócio e a reformula com tom conversacional adequado ao contexto do comprador.

**Fallbacks:**
- Se a chamada à API Claude falhar, o chatbot cai para o despachante de regras puro (sem IA), garantindo continuidade do atendimento.
- Intent não reconhecida pelo classificador desencadeia a resposta H-07 (mensagem padrão de não entendimento).

**Configuração via `ParametroSistema`:**

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `CHATBOT_IA_ATIVO` | `True` | Liga/desliga a camada IA; `False` usa apenas regras |
| `CHATBOT_MODELO` | `claude-haiku-4-5-20251001` | Modelo usado em ambos os estágios |
| `CHATBOT_MAX_TOKENS_POR_RESPOSTA` | `300` | Limite de tokens por resposta |
| `CHATBOT_SYSTEM_PROMPT_CLASSIFIER` | *(interno)* | System prompt do classificador |
| `CHATBOT_SYSTEM_PROMPT` | *(interno)* | System prompt do humanizador |

---

### 12.3 Monitor de Custo (`ia_monitor`)

**Arquivo:** `core/services/ia_monitor.py`  
**Modelo:** `core/models.py → RegistroUsoIA`

Toda chamada a um modelo de IA registra automaticamente um `RegistroUsoIA` com:

| Campo | Descrição |
|-------|-----------|
| `modelo` | Identificador do modelo (ex.: `claude-haiku-4-5-20251001`) |
| `operacao` | Tipo de operação (ex.: `importacao_pdf`, `chatbot_classifier`) |
| `tokens_input` | Tokens enviados ao modelo |
| `tokens_output` | Tokens gerados pelo modelo |
| `custo_usd` | Custo calculado em dólares no momento da chamada |
| `custo_brl` | Custo convertido para BRL usando cotação em cache |
| `imobiliaria` | FK opcional para isolar custos por tenant |
| `created_at` | Timestamp da chamada |

**Cálculo de custo:** a tabela de preços por MTok é mantida em `ia_monitor.py` para cada modelo suportado. O custo em BRL é obtido multiplicando `custo_usd` pela cotação USD/BRL armazenada em `_COTACAO_USD_BRL_CACHE` (parâmetro do sistema), que é atualizada automaticamente via [AwesomeAPI](https://docs.awesomeapi.com.br/api-de-moedas).

**Tabela de preços de referência (por milhão de tokens):**

| Modelo | Input (US$/MTok) | Output (US$/MTok) |
|--------|-----------------|-------------------|
| Gemini 2.0 Flash | 0,00 (free tier) | 0,00 |
| Claude Haiku | 0,25 | 1,25 |
| Claude Sonnet | 3,00 | 15,00 |
| Claude Opus | 15,00 | 75,00 |

**Dashboard:** `/core/ia/custos/` — exibe gasto total, gasto por modelo, gasto por operação e histórico de chamadas com paginação.

---

### 12.4 Limites de Uso (`LimiteUsoIA`)

**Modelo:** `core/models.py → LimiteUsoIA`  
**Função de guarda:** `core/services/ia_monitor.py → checar_limite()`  
**Configuração:** `/core/ia/limites/`

Antes de toda chamada à IA, `checar_limite()` é invocada. Se qualquer limite ativo for excedido, a chamada é bloqueada e um erro descritivo é retornado ao usuário sem consumir tokens.

**Campos do modelo `LimiteUsoIA`:**

| Campo | Descrição |
|-------|-----------|
| `modelo` | Modelo ao qual o limite se aplica (pode ser `*` para todos) |
| `operacao` | Operação ao qual o limite se aplica (pode ser `*` para todas) |
| `periodo` | `diario`, `semanal`, `mensal`, `total` |
| `limite_chamadas` | Número máximo de chamadas no período (opcional) |
| `limite_tokens_input` | Máximo de tokens de entrada no período (opcional) |
| `limite_custo_usd` | Máximo de custo em USD no período (opcional) |
| `ativo` | Liga/desliga o limite sem excluir o registro |

**Comportamento com múltiplos limites:** quando existem vários limites ativos para o mesmo escopo (mesmo modelo + operação), **todos são avaliados simultaneamente**. A chamada é bloqueada se *qualquer* limite for excedido — não há prioridade ou hierarquia entre eles.

---

### 12.5 Rotas da IA

| URL | View | Descrição |
|-----|------|-----------|
| `/core/ia/custos/` | `ia_custos_dashboard` | Dashboard de custos com gráficos e histórico |
| `/core/ia/limites/` | `ia_limites_lista` | CRUD de limites de uso (`LimiteUsoIA`) |
| `/core/ia/tokens/` | `ia_tokens_lista` | Listagem detalhada de registros de uso (`RegistroUsoIA`) |
| `/core/ia/cotacao/` | `ia_atualizar_cotacao` | Atualiza manualmente a cotação USD/BRL via AwesomeAPI |
| `/contratos/importacao/upload/` | `upload_importacao` | Upload de PDF para importação via cadeia IA |

---

## 13. REFERÊNCIAS

- **Documentação completa:** `/docs/README.md`
- **API BRCobrança:** `/docs/api/BRCOBRANCA.md`
- **Deploy Render:** `/docs/deployment/DEPLOY.md`
- **Dados de teste:** `/docs/development/TEST_DATA.md`
- **Testes:** `/tests/README.md`
