# Histórias de Usuário — Gestão de Contratos

> **Organização**: cada HU tem seu próprio arquivo detalhado em [`historias-usuario/`](historias-usuario/).  
> Índice completo, matriz de rastreabilidade e fluxo macro: [`historias-usuario/INDICE.md`](historias-usuario/INDICE.md).

---

## HUs Disponíveis (22 histórias)

| ID | Arquivo | Nome | Módulo |
|----|---------|------|--------|
| HU-01 | [HU-01.md](historias-usuario/HU-01.md) | Criação de Contrato (Wizard) | `contratos` |
| HU-02 | [HU-02.md](historias-usuario/HU-02.md) | Geração de Parcelas | `financeiro` |
| HU-03 | [HU-03.md](historias-usuario/HU-03.md) | Gerar Boleto Individual | `financeiro` |
| HU-04 | [HU-04.md](historias-usuario/HU-04.md) | Pagamento de Parcela | `financeiro` |
| HU-05 | [HU-05.md](historias-usuario/HU-05.md) | Reajuste de Parcelas | `financeiro` |
| HU-06 | [HU-06.md](historias-usuario/HU-06.md) | Bloqueio de Boleto por Reajuste | `contratos`/`financeiro` |
| HU-07 | [HU-07.md](historias-usuario/HU-07.md) | Gerar Carnê (Lote de Boletos) | `financeiro` |
| HU-08 | [HU-08.md](historias-usuario/HU-08.md) | Segunda Via de Boleto | `financeiro` |
| HU-09 | [HU-09.md](historias-usuario/HU-09.md) | Quitação Manual / Antecipação | `financeiro` |
| HU-10 | [HU-10.md](historias-usuario/HU-10.md) | Quitação via OFX (Extrato Bancário) | `financeiro` |
| HU-11 | [HU-11.md](historias-usuario/HU-11.md) | Calcular Rescisão Contratual | `contratos` |
| HU-12 | [HU-12.md](historias-usuario/HU-12.md) | Calcular Cessão de Direitos | `contratos` |
| HU-13 | [HU-13.md](historias-usuario/HU-13.md) | Link Público de Boleto | `financeiro` |
| HU-14 | [HU-14.md](historias-usuario/HU-14.md) | Gestão de Prestações Intermediárias | `contratos` |
| HU-15 | [HU-15.md](historias-usuario/HU-15.md) | Importação de Índices Econômicos | `contratos` |
| HU-16 | [HU-16.md](historias-usuario/HU-16.md) | CNAB — Remessa e Retorno Bancário | `financeiro` |
| HU-17 | [HU-17.md](historias-usuario/HU-17.md) | Renegociação de Parcelas | `financeiro` |
| HU-18 | [HU-18.md](historias-usuario/HU-18.md) | Relatórios Financeiros e Dashboard | `financeiro` |
| HU-19 | [HU-19.md](historias-usuario/HU-19.md) | Chatbot WhatsApp — Atendimento Automático | `notificacoes` |
| HU-20 | [HU-20.md](historias-usuario/HU-20.md) | Notificações e Cobrança Automática | `notificacoes` |
| HU-21 | [HU-21.md](historias-usuario/HU-21.md) | Portal do Comprador — Acesso e Autoatendimento Digital | `portal_comprador` |
| HU-22 | [HU-22.md](historias-usuario/HU-22.md) | Mapa Interativo de Lotes | `core` |

---

## Estrutura de Cada HU

```
# HU-XX — Nome

## História do Usuário
**Como** / **Quero** / **Para**

## Pré-condições
## Critérios de Aceitação
## Regras de Negócio (RN-01, RN-02, ...)
## Definição de Pronto (checklist)
## Cenários de Teste (CT-01, CT-02, ...)
## Fluxo do Processo (diagrama ASCII)
```

---

## Cobertura Verificada

| Funcionalidade | HU | Status |
|---------------|-----|--------|
| Wizard criação de contrato | HU-01 | ✅ |
| Tabela de juros escalante | HU-01 | ✅ |
| Geração automática de parcelas | HU-02 | ✅ |
| Gerar boleto individual | HU-03 | ✅ |
| Pagamento manual + AJAX | HU-04 | ✅ |
| Reajuste (preview + aplicação) | HU-05 | ✅ |
| Bloqueio de boleto por reajuste | HU-06 | ✅ |
| Carnê PDF + ZIP | HU-07 | ✅ |
| Segunda via com encargos | HU-08 | ✅ |
| Simulador de antecipação | HU-09 | ✅ |
| Quitação via OFX | HU-10 | ✅ |
| Cálculo de rescisão | HU-11 | ✅ |
| Cálculo de cessão | HU-12 | ✅ |
| Link público de boleto | HU-13 | ✅ |
| CRUD de intermediárias pós-wizard | HU-14 | ✅ |
| Importação IBGE/BCB/FGV | HU-15 | ✅ |
| CNAB remessa e retorno | HU-16 | ✅ |
| Renegociação de parcelas | HU-17 | ✅ |
| Relatórios e dashboard fluxo de caixa | HU-18 | ✅ |
| Chatbot WhatsApp (fluxos A-F, 2ª via, comprovante) | HU-19 | ✅ (parcial) |
| Notificações automáticas (e-mail, SMS, WhatsApp) | HU-20 | ✅ |
| Régua de cobrança configurável | HU-20 | ✅ |
| Portal do Comprador — auto-cadastro, login, dashboard | HU-21 | ✅ |
| Download de boleto pelo comprador | HU-21 | ✅ |
| Mapa interativo de lotes (Leaflet + clustering) | HU-22 | ✅ |
| Página dedicada por loteamento com KPIs | HU-22 | ✅ |

→ [Índice completo com matriz de rastreabilidade](historias-usuario/INDICE.md)
