# Histórias de Usuário — Índice Geral

> Gestão de Contratos Imobiliários — Todas as HUs organizadas por módulo e fluxo.
> Última atualização: 2026-06-14

---

## Personas

| Persona | Descrição |
|---------|-----------|
| **Operador** | Cadastra contratos, registra pagamentos, aplica reajustes e gera carnês |
| **Gestor** | Supervisiona múltiplas imobiliárias, valida bloqueios e fluxo financeiro |
| **Comprador** | Recebe boletos e acessa o link público sem login |
| **Contadora** | Executa o ciclo mensal de cobrança: gera boletos dos contratos vigentes e envia arquivos de remessa para um ou mais bancos via tela simplificada (HU-23) |

---

## Índice de Histórias

| ID | Arquivo | Nome | Módulo | Status |
|----|---------|------|--------|--------|
| [HU-01](HU-01.md) | `HU-01.md` | Criação de Contrato (Wizard) | `contratos` | ✅ |
| [HU-02](HU-02.md) | `HU-02.md` | Geração de Parcelas | `financeiro` | ✅ |
| [HU-03](HU-03.md) | `HU-03.md` | Gerar Boleto Individual | `financeiro` | ✅ |
| [HU-04](HU-04.md) | `HU-04.md` | Pagamento de Parcela | `financeiro` | ✅ |
| [HU-05](HU-05.md) | `HU-05.md` | Reajuste de Parcelas | `financeiro` | ✅ |
| [HU-06](HU-06.md) | `HU-06.md` | Bloqueio de Boleto por Reajuste | `contratos`/`financeiro` | ✅ |
| [HU-07](HU-07.md) | `HU-07.md` | Gerar Carnê (Lote de Boletos) | `financeiro` | ✅ |
| [HU-08](HU-08.md) | `HU-08.md` | Segunda Via de Boleto | `financeiro` | ✅ |
| [HU-09](HU-09.md) | `HU-09.md` | Quitação Manual / Antecipação | `financeiro` | ✅ |
| [HU-10](HU-10.md) | `HU-10.md` | Quitação via OFX (Extrato Bancário) | `financeiro` | ✅ |
| [HU-11](HU-11.md) | `HU-11.md` | Calcular Rescisão Contratual | `contratos` | ✅ |
| [HU-12](HU-12.md) | `HU-12.md` | Calcular Cessão de Direitos | `contratos` | ✅ |
| [HU-13](HU-13.md) | `HU-13.md` | Link Público de Boleto | `financeiro` | ✅ |
| [HU-14](HU-14.md) | `HU-14.md` | Gestão de Prestações Intermediárias | `contratos` | ✅ |
| [HU-15](HU-15.md) | `HU-15.md` | Importação de Índices Econômicos | `contratos` | ✅ |
| [HU-16](HU-16.md) | `HU-16.md` | CNAB — Remessa e Retorno Bancário | `financeiro` | ✅ |
| [HU-17](HU-17.md) | `HU-17.md` | Renegociação de Parcelas | `financeiro` | ✅ |
| [HU-18](HU-18.md) | `HU-18.md` | Relatórios Financeiros e Dashboard | `financeiro` | ✅ |
| [HU-19](HU-19.md) | `HU-19.md` | Chatbot WhatsApp — Atendimento Automático | `notificacoes` | ✅ (parcial) |
| [HU-20](HU-20.md) | `HU-20.md` | Notificações e Cobrança Automática | `notificacoes` | ✅ |
| [HU-21](HU-21.md) | `HU-21.md` | Portal do Comprador — Acesso e Autoatendimento Digital | `portal_comprador` | ✅ |
| [HU-22](HU-22.md) | `HU-22.md` | Mapa Interativo de Lotes | `core` | ✅ (parcial — M-13/M-14 pendentes) |
| [HU-23](HU-23.md) | `HU-23.md` | Ciclo Mensal de Cobrança CNAB — Remessa + Retorno (Fluxo da Contadora) | `financeiro` | ✅ |
| [HU-24](HU-24.md) | `HU-24.md` | Geração Mensal de Boletos — tela dedicada por escopo (Fluxo da Contadora) | `financeiro` | ✅ |
| [HU-25](HU-25.md) | `HU-25.md` | Hub "Cobrança do Mês" — assistente de ciclo mensal (passo a passo) | `financeiro` | ✅ |
| [HU-26](HU-26.md) | `HU-26.md` | Painel de Conciliação & Saúde da Cobrança | `financeiro` | ✅ |

---

## Cobertura por Funcionalidade

| Funcionalidade do Sistema | HU |
|--------------------------|-----|
| Wizard de criação de contrato | HU-01 |
| Tabela de juros escalante (Price) | HU-01 |
| Geração automática de parcelas | HU-02 |
| Completar parcelas faltantes | HU-02 |
| Gerar boleto por parcela | HU-03 |
| Cancelar / visualizar / status boleto | HU-03 |
| Pagamento manual + AJAX | HU-04 |
| Cálculo de encargos pro rata die | HU-04 |
| Quitação automática do contrato | HU-04 |
| Preview e aplicação de reajuste | HU-05 |
| Índices IPCA/IGPM/INCC/SELIC/TR/INPC/IGPDI | HU-05, HU-15 |
| Reajuste modo Price com tabela de juros | HU-05 |
| Reajuste em lote | HU-05 |
| Bloqueio de boleto por reajuste | HU-03, HU-06 |
| Painel de reajustes pendentes | HU-06 |
| Carnê 20 meses (PDF + ZIP) | HU-07 |
| Carnê 6 meses | HU-07 |
| Geração de boletos em lote | HU-07 |
| Segunda via com juros atualizados | HU-08 |
| Simulador de antecipação | HU-09 |
| Recibo PDF de quitação | HU-09 |
| Upload OFX e conciliação automática | HU-10 |
| Fallback parser OFX interno | HU-10 |
| Deduplicação por fitid_ofx | HU-10 |
| Cálculo de rescisão | HU-11 |
| Cálculo de cessão de direitos | HU-12 |
| Link público UUID sem login | HU-13 |
| Download PDF público | HU-13 |
| CRUD de prestações intermediárias | HU-14 |
| Pagamento e boleto de intermediárias | HU-14 |
| Importação índices IBGE/BCB/FGV | HU-15 |
| Cálculo acumulado por número-índice | HU-15 |
| Geração de arquivo CNAB de remessa | HU-16, HU-23 |
| Processamento de retorno CNAB | HU-16 |
| Painel mensal de remessa por banco | HU-23 |
| Envio de remessa (fluxo simplificado para contadora) | HU-23 |
| Renegociação de parcelas | HU-17 |
| Relatórios a pagar / pagas / posição | HU-18 |
| Dashboard fluxo de caixa por imobiliária | HU-18 |
| Exportação CSV / PDF / Excel | HU-18 |
| Chatbot WhatsApp — fluxos A-F | HU-19 |
| 2ª via de boleto via WhatsApp | HU-19 |
| Recebimento de comprovante via WhatsApp | HU-19 |
| Resumo financeiro via WhatsApp | HU-19 |
| `SessaoConversaWhatsApp` com timeout | HU-19 |
| Notificações de vencimento (D-5) | HU-20 |
| Notificações de inadimplência (D+3) | HU-20 |
| Régua de cobrança configurável (`RegraNotificacao`) | HU-20 |
| Templates multi-canal (`TemplateNotificacao`) | HU-20 |
| TEST_MODE safeguard para não-produção | HU-20 |
| Normalização E.164 de telefones | HU-20 |
| Portal do Comprador — auto-cadastro e login | HU-21 |
| Dashboard KPIs consolidados (N contratos) | HU-21 |
| Download e visualização de boleto | HU-21 |
| APIs JSON: parcelas, resumo, vencimentos, 2ª via | HU-21 |
| `AcessoComprador` — controle de acesso e auditoria | HU-21 |
| Mapa Leaflet com marcadores disponível/vendido | HU-22 |
| Clustering de marcadores por proximidade | HU-22 |
| Filtros de loteamento e status (client-side) | HU-22 |
| Página dedicada por loteamento com KPIs | HU-22 |

---

## Fluxo Macro

```
HU-01 Criar Contrato ──► HU-14 Intermediárias (CRUD pós-criação)
        │
        ▼
HU-02 Gerar Parcelas ─────────────────────────────────────────────┐
        │                                                          │
        ├──► HU-03 Gerar Boleto ──► HU-13 Link Público            │
        │          │                                               │
        │          ├──► HU-08 Segunda Via                          │
        │          │                                               │
        │          └──► HU-07 Carnê ──► HU-16 CNAB Remessa        │
        │                                     │                    │
        │                                HU-23 Envio              │
        │                                Mensal Remessa            │
        │                                (Contadora)               │
        │                                     │                    │
        │                                     ▼                    │
        │                               CNAB Retorno ─────────────┤
        │                                                          │
        ├──► HU-04 Registrar Pagamento ────────────────────────────┤
        │                                                          │
        ├──► HU-05 Reajuste ──► HU-06 Bloqueio                    │
        │          │                                               │
        │          └──► HU-15 Importar Índices                     │
        │                                                          │
        ├──► HU-09 Quitação Manual (antecipação)                   │
        │                                                          │
        ├──► HU-10 Quitação via OFX ───────────────────────────────┘
        │                 │
        │                 ▼
        │         Contrato QUITADO
        │
        ├──► HU-11 Calcular Rescisão ──► Contrato CANCELADO
        │
        ├──► HU-12 Calcular Cessão de Direitos
        │
        ├──► HU-17 Renegociar Parcelas
        │
        ├──► HU-18 Relatórios e Dashboard
        │
        └──► HU-20 Notificações e Cobrança
                    │
                    └──► HU-19 Chatbot WhatsApp (2ª via, comprovante, resumo)

HU-21 Portal do Comprador ──► auto-cadastro → dashboard → boletos → dados
    (acesso direto pelo comprador, independente do chatbot)
```

> **Nota sobre numeração interna do ROADMAP**: O ROADMAP usa uma numeração interna de HU-01..HU-13 como sub-tarefas da HU-360 (seção 13 — Contrato Tabela Price com Juros Escalantes e Intermediárias). Essa numeração é **independente e diferente** do índice HU-01..HU-20 desta documentação. Ao referenciar HUs do ROADMAP, utilizar o prefixo `HU-360/HU-xx` para evitar ambiguidade.

---

## Matriz de Rastreabilidade

| HU | Modelos Django | Services | Views / URLs |
|----|---------------|----------|--------------|
| HU-01 | `Contrato`, `TabelaJurosContrato`, `PrestacaoIntermediaria` | `gerar_parcelas()`, `recalcular_amortizacao()` | `ContratoWizardView /contratos/wizard/` |
| HU-02 | `Parcela` | `gerar_parcelas()`, `completar_parcelas_faltantes()` | `/contratos/wizard/api/preview-parcelas/` |
| HU-03 | `Parcela`, `StatusBoleto` | `BoletoService.gerar_boleto()` | `POST /financeiro/parcelas/<id>/boleto/gerar/` |
| HU-04 | `Parcela`, `HistoricoPagamento` | — | `registrar_pagamento`, `pagar_parcela_ajax` |
| HU-05 | `Reajuste`, `IndiceReajuste` | `ReajusteService` | `/financeiro/contrato/<id>/reajuste/preview/`, `/api/` |
| HU-06 | `Contrato.bloqueio_boleto_reajuste` | `Parcela.pode_gerar_boleto()` | `/financeiro/reajustes/pendentes/` |
| HU-07 | `Parcela`, `StatusBoleto` | `BoletoService.gerar_carne()` | `gerar_carne`, `download_carne_pdf`, `download_zip_boletos` |
| HU-08 | `Parcela` | `BoletoService.gerar_segunda_via()` | `GET /financeiro/parcelas/<id>/boleto/segunda-via/` |
| HU-09 | `HistoricoPagamento (antecipado)` | `recibo_service` | `/financeiro/contrato/<id>/simulador/` |
| HU-10 | `HistoricoPagamento (fitid_ofx)` | `OFXService` | `POST /financeiro/cnab/ofx/upload/` |
| HU-11 | `Contrato` | `Contrato.calcular_rescisao()` | `/contratos/<id>/rescisao/` |
| HU-12 | `Contrato` | `Contrato.calcular_cessao()` | `/contratos/<id>/cessao/` |
| HU-13 | `Parcela.token_publico` | `BoletoService` | `/b/<uuid>/`, `/b/<uuid>/download/` |
| HU-14 | `PrestacaoIntermediaria` | `BoletoService` | `/contratos/<id>/intermediarias/criar/`, `/pagar/`, `/gerar-boleto/` |
| HU-15 | `IndiceReajuste` | `IndicesEconomicosService` | `POST /contratos/indices/importar/`, `/financeiro/api/indice-reajuste/` |
| HU-16 | `ArquivoRemessa`, `ArquivoRetorno`, `ItemRetorno` | `CNABService` | `/financeiro/cnab/remessa/gerar/`, `/cnab/retorno/upload/` |
| HU-17 | `Parcela`, auditoria | — | `/financeiro/contrato/<id>/renegociar/` |
| HU-18 | `Parcela`, `HistoricoPagamento` | `RelatorioService` | `/financeiro/relatorios/`, `/imobiliaria/<id>/dashboard/` |
| HU-19 | `SessaoConversaWhatsApp`, `HistoricoPagamento` | `WhatsAppBotService`, `BoletoService` | `POST /notificacoes/webhook/evolution/` |
| HU-20 | `RegraNotificacao`, `TemplateNotificacao`, `Notificacao`, `ConfiguracaoWhatsApp` | `enviar_notificacoes_sync()`, `enviar_inadimplentes_sync()` | `POST /api/tasks/enviar-notificacoes/`, `/api/tasks/enviar-inadimplentes/`, `POST /financeiro/parcelas/<pk>/notificar/` |
| HU-21 | `AcessoComprador`, `LogAcessoComprador` | — | `/portal/cadastro/`, `/portal/login/`, `/portal/`, `/portal/contratos/`, `/portal/boletos/`, `/portal/meus-dados/`, `/portal/api/*` |
| HU-22 | `Imovel` | — | `/imoveis/` (mapa com marcadores Leaflet + markercluster), `/imoveis/loteamento/<nome>/` |
| HU-23 | `ArquivoRemessa`, `ItemRemessa`, `ArquivoRetorno`, `ItemRetorno`, `ContaBancaria` | `CNABService` | **Tela 1 (Remessa):** `/financeiro/remessa/` (wizard), `/remessa/gerar/` (escopo: todos/imobiliaria/conta/boleto), `download-lote/`, `cancelar-envio/`. **Tela 2 (Retorno):** `/financeiro/retorno/` (KPIs + upload por banco), `/retorno/upload/` (upload + baixa em 1 passo) |
| HU-24 | `Parcela`, `PrestacaoIntermediaria`, `ContaBancaria` | `BoletoService` (`gerar_boletos_lote`) | **Tela dedicada:** `/financeiro/boletos/` (wizard), `/boletos/gerar/` (escopo: todos/imobiliaria/contratos/parcela/intermediaria, quantidade 1/X), `api/boletos/elegiveis/`. Etapa anterior à HU-23 |
| HU-25 | *(orquestra HU-24/HU-23 — sem modelos novos)* | reutiliza `boletos_painel_gerar`, `remessa_painel_gerar`, `remessa_retorno_upload` | **Hub:** `/financeiro/cobranca/` (stepper 1·2·3), `api/cobranca/estado/`. Costura geração→remessa→retorno num fluxo guiado (📋 especificada) |
| HU-26 | `HistoricoPagamento`, `EventoPIX`, `ItemRemessa` | reutiliza serviços de baixa/relatório (HU-04/16/18) | **Painel:** `/financeiro/cobranca/conciliacao/`, `api/conciliacao/saude/`. KPIs de saúde, recebido por origem, aging, rejeitados (📋 especificada) |

---

## Regras de Negócio Globais

| Código | Regra | HU(s) |
|--------|-------|-------|
| RN-G01 | `tipo_correcao=FIXO` nunca bloqueia boleto nem consulta índices | HU-03, HU-06, HU-15 |
| RN-G02 | Ciclo 1 nunca requer reajuste — boletos sempre liberados | HU-06 |
| RN-G03 | Quitação manual e OFX ignoram bloqueio de reajuste | HU-09, HU-10 |
| RN-G04 | `devolucao = max(0, total_pago − total_retencoes)` | HU-11 |
| RN-G05 | CPF do comprador nunca aparece em páginas públicas | HU-13 |
| RN-G06 | `fitid_ofx` é único — mesma transação nunca gera pagamento duplo | HU-10 |
| RN-G07 | `valor_original` nunca é alterado; apenas `valor_atual` muda | HU-05, HU-17 |
| RN-G08 | CNAB retorno é idempotente — segundo processamento não duplica | HU-16 |
| RN-G09 | `nosso_numero` obrigatório para incluir boleto na remessa CNAB | HU-16 |
| RN-G10 | Remessa inclui apenas parcelas com `data_vencimento >= date.today()` — vencimentos passados não entram | HU-23 |
| RN-G11 | Boleto em remessa `ENVIADA` ou `PROCESSADA` não pode entrar em nova remessa — evita registro duplicado no banco | HU-23 |
