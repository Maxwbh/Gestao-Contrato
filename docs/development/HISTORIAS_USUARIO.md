# Histórias de Usuário (HU) — Sistema de Gestão de Contratos

> Documento consolidado das HUs do fluxo de contrato → parcelas → pagamento → reajuste → carnê → quitação.
> Atualizado em: 2026-04-29
> Branch: `claude/contract-payment-system-MG9ih`

## Índice

| ID | História | Módulo |
|----|----------|--------|
| [HU-01](#hu-01--criação-de-contrato) | Criação de Contrato | `contratos` |
| [HU-02](#hu-02--geração-de-parcelas) | Geração de Parcelas | `financeiro` |
| [HU-03](#hu-03--pagamento-de-parcela) | Pagamento de Parcela | `financeiro` |
| [HU-04](#hu-04--gerar-reajuste) | Gerar Reajuste | `financeiro` |
| [HU-05](#hu-05--gerar-carnê-para-os-próximos-20-meses) | Gerar Carnê 20 meses | `financeiro` |
| [HU-06](#hu-06--validar-bloqueio-de-reajuste) | Validar Bloqueio de Reajuste | `contratos` / `financeiro` |
| [HU-07](#hu-07--gerar-carnê-6-meses) | Gerar Carnê 6 meses | `financeiro` |
| [HU-08](#hu-08--gerar-quitação-via-manual) | Quitação Manual (Antecipação) | `financeiro` |
| [HU-09](#hu-09--gerar-quitação-via-ofx) | Quitação via OFX | `financeiro` |

---

## Personas

- **Operador da Imobiliária**: cadastra contratos, registra pagamentos, aplica reajustes e gera carnês.
- **Gestor da Contabilidade**: supervisiona contratos de múltiplas imobiliárias, valida bloqueios e fluxo financeiro.
- **Comprador**: visualiza parcelas via Portal do Comprador (consumidor das saídas).

---

## HU-01 — Criação de Contrato

**Como** operador da imobiliária
**Quero** cadastrar um novo contrato de venda de imóvel
**Para** formalizar a relação comercial e iniciar o fluxo financeiro de cobrança.

### Pré-condições
- Imobiliária, imóvel disponível e comprador previamente cadastrados em `core`.
- Conta bancária ativa configurada (`core.ContaBancaria`) caso haja emissão de boleto.

### Critérios de Aceitação
1. O sistema permite criar contrato via fluxo direto (`ContratoCreateView` em `/contratos/novo/`) ou via wizard passo a passo (`ContratoWizardView` em `/contratos/wizard/`).
2. Os campos obrigatórios são: `numero_contrato`, `data_contrato`, `data_primeiro_vencimento`, `valor_total`, `numero_parcelas`, `dia_vencimento`, `tipo_amortizacao` (PRICE/SAC) e `tipo_correcao` (IPCA/IGPM/INCC/IGPDI/INPC/TR/SELIC/FIXO).
3. O `valor_entrada` deve ser estritamente menor que o `valor_total` (validado em `ContratoWizardBasicoForm`).
4. O `numero_parcelas` aceita até 360 meses; intermediárias até 30 (`PrestacaoIntermediaria`).
5. Após salvo, o contrato é criado com `status = ATIVO` e os campos `numero_parcelas`, `valor_total` e `valor_entrada` tornam-se imutáveis.
6. Ao confirmar a criação, o sistema dispara automaticamente a geração de parcelas (HU-02).

### Regras de Negócio
- RN-01: Número do contrato é único por imobiliária.
- RN-02: O ciclo de reajuste padrão é 12 meses, configurável no campo `ciclo_reajuste`.
- RN-03: Quando `tipo_correcao = FIXO`, o sistema não exige `IndiceReajuste` cadastrado.
- RN-04: `bloqueio_boleto_reajuste` inicia como `False`.

### Cenário de exceção
- Se o usuário informar `valor_entrada >= valor_total`, o formulário rejeita com mensagem "Entrada não pode ser maior ou igual ao valor total".

### Definição de Pronto
- [ ] Contrato persistido com auditoria (`created_at`, `updated_at`).
- [ ] Parcelas geradas (HU-02 OK).
- [ ] Wizard exibe preview antes do commit.

---

## HU-02 — Geração de Parcelas

**Como** operador da imobiliária
**Quero** que as parcelas mensais sejam geradas automaticamente a partir das condições do contrato
**Para** ter o cronograma financeiro completo, com vencimentos, valores e ciclos de reajuste.

### Pré-condições
- Contrato criado e em status `ATIVO`.

### Critérios de Aceitação
1. O método `Contrato.gerar_parcelas()` (`contratos/models.py:720`) cria todas as parcelas conforme o `tipo_amortizacao`:
   - **PRICE**: parcelas de valor constante.
   - **SAC**: amortização constante com parcelas decrescentes.
2. Cada `Parcela` (`financeiro/models.py:41`) é criada com:
   - `numero_parcela` sequencial.
   - `data_vencimento` calculada a partir de `data_primeiro_vencimento` e `dia_vencimento`.
   - `valor_original` (= valor inicial calculado) e `valor_atual` (= valor com reajustes aplicados).
   - `tipo_parcela` em `NORMAL`, `INTERMEDIARIA` ou `ENTRADA`.
   - `ciclo` correspondente ao período de reajuste.
3. Parcelas intermediárias (`PrestacaoIntermediaria`) são criadas com `tipo_parcela = INTERMEDIARIA` nas datas configuradas.
4. Endpoint de preview (`/contratos/wizard/api/preview-parcelas/`) retorna a tabela calculada **sem persistir**, antes da criação.
5. Em caso de divergência (parcelas faltantes por interrupção), o método `completar_parcelas_faltantes()` regenera apenas as ausentes, preservando histórico.

### Regras de Negócio
- RN-05: Toda parcela inicia com `pago = False` e `status_boleto = PENDENTE`.
- RN-06: Soma de `valor_original` das parcelas + `valor_entrada` = `valor_total` (tolerância R$ 0,01).
- RN-07: O `ciclo` de cada parcela define quando o reajuste será aplicado.

### Definição de Pronto
- [ ] Total de parcelas criadas = `numero_parcelas` + intermediárias.
- [ ] Soma confere com o valor do contrato.
- [ ] Preview no wizard reflete o que será criado.

---

## HU-03 — Pagamento de Parcela

**Como** operador da imobiliária
**Quero** registrar o pagamento de uma parcela
**Para** atualizar a posição financeira do contrato e dar baixa no boleto correspondente.

### Pré-condições
- Parcela existente com `pago = False`.

### Critérios de Aceitação
1. A view `registrar_pagamento` (`financeiro/views.py:692`) e o endpoint `pagar_parcela_ajax` recebem:
   - `valor_pago`, `data_pagamento`, `forma_pagamento` (PIX, BOLETO, CHEQUE, DINHEIRO, TRANSFERÊNCIA, …), opcional `desconto`, `juros`, `multa`.
2. Cria-se um `HistoricoPagamento` (`financeiro/models.py:1719`) com `origem_pagamento` em {`MANUAL`, `CNAB`, `OFX`, `SISTEMA`}.
3. A parcela é marcada `pago = True` e `status_boleto = PAGO`.
4. Se houver `ItemRetorno` CNAB associado, o vínculo é registrado para rastreabilidade.
5. Pagamento parcial: se `valor_pago < valor_atual`, o sistema mantém `pago = False` e registra o histórico parcial (regra opcional, conforme configuração da imobiliária).
6. Após o último pagamento, se todas as parcelas (NORMAL + INTERMEDIARIA) estão pagas, o contrato muda para `status = QUITADO`.

### Regras de Negócio
- RN-08: Valor com encargos = `valor_atual - desconto + juros + multa`.
- RN-09: `data_pagamento` não pode ser futura.
- RN-10: Pagamento via OFX exige `fitid_ofx` único (deduplicação — ver HU-09).
- RN-11: Reversão de pagamento exige permissão e gera novo `HistoricoPagamento` com sinal contrário.

### Definição de Pronto
- [ ] Histórico persistido com `origem_pagamento` correta.
- [ ] Status do boleto e da parcela atualizados.
- [ ] Quitação automática do contrato se aplicável.

---

## HU-04 — Gerar Reajuste

**Como** operador da imobiliária
**Quero** aplicar o reajuste econômico sobre as parcelas do próximo ciclo
**Para** manter o equilíbrio financeiro do contrato conforme o índice contratado.

### Pré-condições
- Contrato com `tipo_correcao` diferente de `FIXO`.
- Índice (`IndiceReajuste`) cadastrado para o período do ciclo.
- Existem parcelas em ciclo posterior ao último reajuste aplicado.

### Critérios de Aceitação
1. O `ReajusteService` (`financeiro/services/reajuste_service.py`) calcula o percentual a partir do `IndiceReajuste` do tipo do contrato.
2. A view `aplicar_reajuste_contrato` (`financeiro/views.py:3046`) e o endpoint `/contrato/<id>/reajuste/api/` aplicam:
   - Atualização de `Parcela.valor_atual` para todas as parcelas do ciclo alvo.
   - Criação de um registro `Reajuste` (`financeiro/models.py:806`) com: `percentual`, `indice_tipo`, `ciclo`, `piso_aplicado`, `teto_aplicado`, `spread_aplicado`, `data_limite_boleto`.
3. O reajuste respeita os limitadores configurados no contrato:
   - **Piso** (mínimo) e **teto** (máximo) percentuais.
   - **Spread** (acréscimo fixo sobre o índice).
4. Há aplicação em lote via `/reajustes/aplicar-lote/` para múltiplos contratos no mesmo ciclo.
5. Após aplicação bem-sucedida, o `bloqueio_boleto_reajuste` é desfeito automaticamente para o ciclo (HU-06).

### Regras de Negócio
- RN-12: Não se aplica reajuste em parcelas do **ciclo 1** (período inicial sem reajuste).
- RN-13: Não se aplica reajuste em parcelas já pagas.
- RN-14: Quando o índice resulta em valor negativo (deflação), o sistema aplica `0%` se o contrato tiver `piso = 0`.
- RN-15: O registro `Reajuste` é imutável após persistência (auditoria).

### Definição de Pronto
- [ ] `valor_atual` das parcelas do ciclo atualizado.
- [ ] Registro `Reajuste` persistido com piso/teto/spread auditados.
- [ ] `data_limite_boleto` definida.
- [ ] Bloqueio do ciclo levantado.

---

## HU-05 — Gerar Carnê para os Próximos 20 Meses

**Como** operador da imobiliária
**Quero** emitir um carnê em PDF com os boletos dos próximos 20 meses
**Para** entregar ao comprador o conjunto de cobranças de longo prazo em um único documento.

### Pré-condições
- Contrato `ATIVO`, com conta bancária configurada e parcelas pendentes nos próximos 20 meses.
- Reajustes aplicados quando exigido (HU-06).

### Critérios de Aceitação
1. A view `gerar_carne` (`financeiro/views.py:2306`) recebe `quantidade = 20` ou lista explícita de parcelas.
2. O `carne_service.gerar_carne_pdf()` (`financeiro/services/carne_service.py`) executa:
   - Seleção das próximas 20 parcelas com `pago = False`, ordenadas por `data_vencimento`.
   - Validação do bloqueio de reajuste (HU-06) — interrompe se violado.
   - Chamada à BRCobrança via `POST /api/boleto/multi` com payload de N boletos.
   - Persistência de `Boleto` por parcela com `status_boleto = GERADO`.
3. O PDF resultante é disponibilizado em `download_carne_pdf` (`/contrato/<id>/carne/pdf/`).
4. Falha em uma parcela individual não aborta o lote inteiro: o erro é registrado e as demais seguem.

### Regras de Negócio
- RN-16: Pular parcelas já pagas e canceladas.
- RN-17: Se restar menos de 20 parcelas, gera o que houver.
- RN-18: Boletos com vencimento posterior à `data_limite_boleto` do reajuste só são gerados após reaplicar reajuste.

### Definição de Pronto
- [ ] PDF entregue com os boletos numerados.
- [ ] Cada parcela com `status_boleto = GERADO` e `nosso_numero` atribuído.
- [ ] Erros parciais reportados ao usuário.

---

## HU-06 — Validar Bloqueio de Reajuste

**Como** sistema
**Quero** impedir a emissão de boletos quando o ciclo de reajuste estiver pendente
**Para** evitar cobranças com valores desatualizados e garantir conformidade contratual.

### Pré-condições
- Contrato `ATIVO`.

### Critérios de Aceitação
1. `Contrato.bloqueio_boleto_reajuste` (campo Boolean em `contratos/models.py:299`) é controlado automaticamente pelo método `verificar_bloqueio_reajuste()` (`contratos/models.py:1113`).
2. O método retorna `True` quando:
   - O próximo ciclo a vencer ainda não tem `Reajuste` aplicado.
   - O ciclo NÃO é o de número 1.
   - `tipo_correcao` NÃO é `FIXO`.
3. Em `gerar_boleto_parcela` (`financeiro/views.py:1196`) e em `gerar_carne_pdf`, ao detectar bloqueio:
   - Aborta a operação.
   - Retorna mensagem clara: "Reajuste do ciclo X pendente. Aplique antes de gerar boletos."
4. O painel `/reajustes/pendentes/` lista todos os contratos com bloqueio ativo, agrupados por imobiliária.
5. Ao concluir HU-04 (aplicar reajuste), o bloqueio é levantado para aquele ciclo.

### Regras de Negócio
- RN-19: Ciclo 1 nunca bloqueia.
- RN-20: Contratos `FIXO` nunca bloqueiam.
- RN-21: Bloqueio é por ciclo, não por contrato — após aplicar o reajuste do ciclo N, o ciclo N+1 só bloqueará quando vencer seu período.
- RN-22: Quitação manual e via OFX (HU-08, HU-09) ignoram o bloqueio (apenas a emissão de boletos é impedida).

### Definição de Pronto
- [ ] Bloqueio impede emissão de boletos.
- [ ] Mensagens claras retornadas em cada ponto de barreira.
- [ ] Painel de pendências reflete a lista correta.

---

## HU-07 — Gerar Carnê 6 Meses

**Como** operador da imobiliária
**Quero** emitir um carnê em PDF com os boletos dos próximos 6 meses
**Para** atender o ciclo curto de cobrança (semestral) sem ultrapassar a `data_limite_boleto` do ciclo de reajuste.

### Pré-condições
- Idênticas à HU-05, mas com janela curta — geralmente NÃO atinge fronteira de reajuste.

### Critérios de Aceitação
1. Mesma view `gerar_carne` (`financeiro/views.py:2306`) com parâmetro `quantidade = 6`.
2. Comportamento idêntico ao HU-05, exceto pelo número de parcelas selecionadas.
3. Operação típica para imobiliárias que reemitem carnê a cada semestre.
4. Quando o ciclo de reajuste está próximo (ex.: faltam 3 meses), o sistema **avisa** que após o ciclo será necessário novo carnê — informativo, não bloqueante.

### Regras de Negócio
- RN-23: Reaproveita todas as regras da HU-05 (RN-16 a RN-18).
- RN-24: Janela de 6 meses é o **default recomendado** para contratos com reajuste anual.

### Definição de Pronto
- [ ] PDF gerado com até 6 boletos.
- [ ] Aviso amigável quando o ciclo de reajuste se aproxima.

---

## HU-08 — Gerar Quitação via Manual

**Como** operador da imobiliária
**Quero** quitar parcelas em aberto manualmente, com simulação de antecipação e desconto
**Para** atender solicitações de quitação total ou parcial do contrato negociadas presencialmente.

### Pré-condições
- Contrato `ATIVO`.
- Existe pelo menos uma parcela `NORMAL` não paga.

### Critérios de Aceitação
1. A view `simulador_antecipacao` (`financeiro/views.py:6870`) atende `/contrato/<id>/simulador/` em três modos:
   - **GET**: exibe formulário com parcelas selecionáveis e campo de desconto (% ou fixo).
   - **POST action=preview**: retorna prévia do desconto/valor final **sem persistir**.
   - **POST action=aplicar**: persiste os pagamentos.
2. Ao aplicar, para cada parcela selecionada:
   - Cria `HistoricoPagamento` com `origem_pagamento = MANUAL` e `antecipado = True`.
   - Aplica o desconto sobre `valor_atual`.
   - Marca `Parcela.pago = True` e `status_boleto = PAGO`.
3. O serviço `recibo_service` gera um PDF de quitação acessível em `/contrato/<id>/recibo-antecipacao.pdf`.
4. Se todas as parcelas forem quitadas, o contrato passa para `status = QUITADO` automaticamente.

### Regras de Negócio
- RN-25: Desconto pode ser percentual ou valor fixo, mas nunca superior ao `valor_atual`.
- RN-26: Apenas parcelas `NORMAL` (não pagas) entram na simulação; intermediárias são tratadas separadamente.
- RN-27: Recibo PDF deve conter: identificação das partes, parcelas quitadas, desconto aplicado, valor pago, data e assinaturas.
- RN-28: A quitação manual ignora o bloqueio de reajuste (HU-06 RN-22).

### Cenário de exceção
- Desconto inválido (negativo ou > valor): formulário recusa com erro de validação.
- Sem parcelas elegíveis: simulador exibe mensagem "Não há parcelas em aberto para antecipação".

### Definição de Pronto
- [ ] Histórico de pagamento criado com `antecipado = True`.
- [ ] Recibo PDF disponível para download.
- [ ] Contrato quitado quando aplicável.

---

## HU-09 — Gerar Quitação via OFX

**Como** operador da imobiliária
**Quero** importar o extrato bancário em formato OFX e conciliar automaticamente os pagamentos
**Para** dar baixa em massa nas parcelas pagas via PIX/TED/depósito sem digitação manual.

### Pré-condições
- Arquivo OFX (v1 ou v2) exportado do internet banking da imobiliária.
- Parcelas em aberto compatíveis com as transações do OFX.

### Critérios de Aceitação
1. A view `upload_ofx` (`financeiro/views.py:6666`) recebe upload em `/cnab/ofx/upload/`.
2. O `OFXService` (`financeiro/services/ofx_service.py`) faz parse via BRCobrança em `POST /api/ofx/parse`, com fallback para parse manual em caso de indisponibilidade da API.
3. Cada `OFXTransaction` é reconciliada por **prioridade**:
   1. **Nosso número** (campo `MEMO` do OFX) → match direto com `Boleto.nosso_numero`.
   2. **Número do contrato** detectado no `MEMO`.
   3. **Valor exato ± R$ 0,10** + janela de data → match com parcela aberta.
   4. **Valor genérico** → exibe sugestões para conciliação manual.
4. Para cada match positivo, cria `HistoricoPagamento` com:
   - `origem_pagamento = OFX`.
   - `fitid_ofx` = ID único da transação (deduplicação).
   - `forma_pagamento` derivada do tipo de transação OFX.
5. O sistema **rejeita** transações com `fitid_ofx` já existente (evita pagamento duplicado).
6. Tela de resultado lista: matches automáticos, conflitos (múltiplos candidatos), não conciliadas.

### Regras de Negócio
- RN-29: `fitid_ofx` é único globalmente — segunda importação do mesmo arquivo não duplica baixas.
- RN-30: Transações de débito (saída) são ignoradas — apenas créditos viram pagamentos.
- RN-31: Em caso de empate de match (duas parcelas com mesmo valor), o sistema NÃO concilia automaticamente; pendência fica para revisão manual.
- RN-32: A baixa via OFX ignora o bloqueio de reajuste (HU-06 RN-22).
- RN-33: Quitação total do contrato é detectada após cada lote — `status = QUITADO` se todas as parcelas estiverem pagas.

### Cenário de exceção
- OFX corrompido ou em formato não suportado: erro "Arquivo OFX inválido".
- BRCobrança indisponível: aviso de uso do parser fallback.

### Definição de Pronto
- [ ] Transações importadas, conciliadas e auditadas.
- [ ] `HistoricoPagamento` com `fitid_ofx` único persistido.
- [ ] Relatório final exibido (matches, conflitos, pendências).
- [ ] Contratos quitados marcados automaticamente.

---

## Matriz de Rastreabilidade

| HU | Modelos | Services | Views/URLs principais |
|----|---------|----------|------------------------|
| HU-01 | `Contrato`, `PrestacaoIntermediaria` | — | `ContratoCreateView`, `ContratoWizardView` |
| HU-02 | `Parcela` | `Contrato.gerar_parcelas()`, `completar_parcelas_faltantes()` | `/wizard/api/preview-parcelas/` |
| HU-03 | `HistoricoPagamento`, `Parcela` | — | `registrar_pagamento`, `pagar_parcela_ajax` |
| HU-04 | `Reajuste`, `IndiceReajuste`, `Parcela` | `ReajusteService` | `aplicar_reajuste_contrato`, `/reajustes/aplicar-lote/` |
| HU-05 | `Boleto`, `Parcela` | `carne_service.gerar_carne_pdf` | `gerar_carne`, `download_carne_pdf` |
| HU-06 | `Contrato.bloqueio_boleto_reajuste` | `Contrato.verificar_bloqueio_reajuste` | `/reajustes/pendentes/`, `gerar_boleto_parcela` |
| HU-07 | `Boleto`, `Parcela` | `carne_service.gerar_carne_pdf` (qty=6) | `gerar_carne` |
| HU-08 | `HistoricoPagamento (antecipado)` | `recibo_service` | `simulador_antecipacao`, `/recibo-antecipacao.pdf` |
| HU-09 | `HistoricoPagamento (fitid_ofx)` | `OFXService` | `upload_ofx` |

---

## Fluxo Macro

```
HU-01 Criação Contrato
        │
        ▼
HU-02 Geração Parcelas
        │
        ├──────────────► HU-04 Reajuste ────► HU-06 Validar Bloqueio
        │                                              │
        │                                              ▼
        ├──────────────► HU-05 Carnê 20m / HU-07 Carnê 6m
        │
        ├──► HU-03 Pagamento (manual/sistema)
        │
        ├──► HU-08 Quitação Manual (antecipação)
        │
        └──► HU-09 Quitação via OFX (em lote)
                  │
                  ▼
            Contrato QUITADO
```
