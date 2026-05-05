# Histórias de Usuário — Índice Geral

> Gestão de Contratos Imobiliários — Todas as HUs organizadas por módulo e fluxo.
> Última atualização: 2026-05-05

---

## Personas

| Persona | Descrição |
|---------|-----------|
| **Operador** | Cadastra contratos, registra pagamentos, aplica reajustes e gera carnês |
| **Gestor** | Supervisiona múltiplas imobiliárias, valida bloqueios e fluxo financeiro |
| **Comprador** | Recebe boletos e acessa o link público sem login |

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

---

## Cobertura por Funcionalidade

| Funcionalidade do Sistema | HU Cobrindo |
|--------------------------|-------------|
| Wizard de criação de contrato | HU-01 |
| Tabela de juros escalante (Price) | HU-01 |
| Intermediárias | HU-01 |
| Geração automática de parcelas | HU-02 |
| Completar parcelas faltantes | HU-02 |
| Gerar boleto por parcela | HU-03 |
| Bloqueio por reajuste | HU-03, HU-06 |
| Cancelar boleto | HU-03 |
| Registrar pagamento (manual/AJAX) | HU-04 |
| Quitação automática do contrato | HU-04 |
| Preview de reajuste | HU-05 |
| Aplicar reajuste (modo simples e Price) | HU-05 |
| Reajuste em lote | HU-05 |
| Painel de reajustes pendentes | HU-06 |
| Gerar carnê PDF (20 ou 6 meses) | HU-07 |
| Download ZIP de boletos | HU-07 |
| Segunda via com juros atualizados | HU-08 |
| Simulador de antecipação | HU-09 |
| Recibo PDF de quitação | HU-09 |
| Upload OFX | HU-10 |
| Conciliação automática | HU-10 |
| Cálculo de rescisão | HU-11 |
| Cálculo de cessão de direitos | HU-12 |
| Link público UUID sem login | HU-13 |
| Download PDF público | HU-13 |

---

## Fluxo Macro

```
HU-01 Criar Contrato
        │
        ▼
HU-02 Gerar Parcelas ────────────────────────────────────────────┐
        │                                                         │
        ├──► HU-03 Gerar Boleto ──► HU-13 Link Público Boleto    │
        │          │                                              │
        │          ├──► HU-08 Segunda Via (boleto vencido)        │
        │          │                                              │
        │          └──► HU-07 Carnê (lote de boletos)            │
        │                                                         │
        ├──► HU-04 Registrar Pagamento ───────────────────────────┤
        │                                                         │
        ├──► HU-05 Reajuste ──► HU-06 Bloqueio de Boleto         │
        │                                                         │
        ├──► HU-09 Quitação Manual (antecipação)                  │
        │                                                         │
        ├──► HU-10 Quitação via OFX ──────────────────────────────┘
        │                 │
        │                 ▼
        │         Contrato QUITADO
        │
        ├──► HU-11 Calcular Rescisão ──► Contrato CANCELADO
        │
        └──► HU-12 Calcular Cessão de Direitos
```

---

## Matriz de Rastreabilidade

| HU | Modelos Django | Services | Views / URLs |
|----|---------------|----------|--------------|
| HU-01 | `Contrato`, `TabelaJurosContrato`, `PrestacaoIntermediaria` | `Contrato.gerar_parcelas()` | `ContratoWizardView /contratos/wizard/` |
| HU-02 | `Parcela` | `Contrato.gerar_parcelas()`, `completar_parcelas_faltantes()` | `/contratos/wizard/api/preview-parcelas/` |
| HU-03 | `Parcela`, `StatusBoleto` | `BoletoService.gerar_boleto()` | `POST /financeiro/parcelas/<id>/boleto/gerar/` |
| HU-04 | `Parcela`, `HistoricoPagamento` | — | `registrar_pagamento`, `pagar_parcela_ajax` |
| HU-05 | `Reajuste`, `IndiceReajuste` | `ReajusteService` | `/financeiro/contrato/<id>/reajuste/preview/`, `/api/` |
| HU-06 | `Contrato.bloqueio_boleto_reajuste` | `Parcela.pode_gerar_boleto()` | `/financeiro/reajustes/pendentes/` |
| HU-07 | `Parcela`, `StatusBoleto` | `BoletoService.gerar_carne()` | `gerar_carne`, `download_carne_pdf` |
| HU-08 | `Parcela` | `BoletoService.gerar_segunda_via()` | `GET /financeiro/parcelas/<id>/boleto/segunda-via/` |
| HU-09 | `HistoricoPagamento (antecipado)` | `recibo_service` | `simulador_antecipacao` |
| HU-10 | `HistoricoPagamento (fitid_ofx)` | `OFXService` | `upload_ofx` |
| HU-11 | `Contrato` | `Contrato.calcular_rescisao()` | `/contratos/<id>/rescisao/` |
| HU-12 | `Contrato` | `Contrato.calcular_cessao()` | `/contratos/<id>/cessao/` |
| HU-13 | `Parcela.token_publico` | `BoletoService` | `/b/<uuid>/`, `/b/<uuid>/download/` |

---

## Regras de Negócio Globais

| Código | Regra | HU(s) |
|--------|-------|-------|
| RN-G01 | Contrato com `tipo_correcao=FIXO` nunca bloqueia boleto | HU-03, HU-06 |
| RN-G02 | Ciclo 1 nunca requer reajuste — boletos sempre liberados | HU-06 |
| RN-G03 | Quitação manual e OFX ignoram bloqueio de reajuste | HU-09, HU-10 |
| RN-G04 | `devolucao = max(0, total_pago − total_retencoes)` | HU-11 |
| RN-G05 | CPF do comprador não aparece em páginas públicas | HU-13 |
| RN-G06 | `fitid_ofx` é único — mesma transação não gera pagamento duplo | HU-10 |
