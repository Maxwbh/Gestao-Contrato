# Histórias de Usuário — Gestão de Contratos

> **Organização**: cada HU tem seu próprio arquivo detalhado em [`historias-usuario/`](historias-usuario/).  
> Este arquivo é o ponto de entrada; o índice completo e a matriz de rastreabilidade estão em [`historias-usuario/INDICE.md`](historias-usuario/INDICE.md).

---

## HUs Disponíveis

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

---

## Estrutura de Cada HU

Cada arquivo segue o template:

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
| Completar parcelas faltantes | HU-02 | ✅ |
| Gerar boleto por parcela | HU-03 | ✅ |
| Cancelar boleto | HU-03 | ✅ |
| Pagamento (manual + AJAX) | HU-04 | ✅ |
| Quitação automática do contrato | HU-04 | ✅ |
| Preview e aplicação de reajuste | HU-05 | ✅ |
| Índices IPCA/IGPM/INCC/SELIC/TR | HU-05 | ✅ |
| Reajuste modo Price com tabela | HU-05 | ✅ |
| Reajuste em lote | HU-05 | ✅ |
| Bloqueio de boleto por reajuste | HU-06 | ✅ |
| Painel de reajustes pendentes | HU-06 | ✅ |
| Carnê 20 meses (PDF + ZIP) | HU-07 | ✅ |
| Carnê 6 meses | HU-07 | ✅ |
| Segunda via com juros atualizados | HU-08 | ✅ |
| Simulador de antecipação | HU-09 | ✅ |
| Recibo PDF de quitação | HU-09 | ✅ |
| Upload OFX e conciliação | HU-10 | ✅ |
| Deduplicação por fitid_ofx | HU-10 | ✅ |
| Cálculo de rescisão | HU-11 | ✅ |
| Cálculo de cessão de direitos | HU-12 | ✅ |
| Link público UUID sem login | HU-13 | ✅ |
| Download PDF público | HU-13 | ✅ |

→ [Índice completo com matriz de rastreabilidade](historias-usuario/INDICE.md)
