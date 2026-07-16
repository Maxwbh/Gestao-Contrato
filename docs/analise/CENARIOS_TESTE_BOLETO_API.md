# Cenários de Teste — HUs Boleto-API (BAPI)

> Cenários de teste e de **geração de dados de teste** para as HUs novas da
> integração Boleto-API (`docs/api/BOLETO_API_HUS.md`).
>
> **Premissa central: nenhum cenário chama a API do banco.** Toda a massa de
> dados usa **Boleto Fake** (`financeiro/services/boleto_fake.py`): linha
> digitável e código de barras com dígitos verificadores reais (mod-10/mod-11
> FEBRABAN), Pix copia-e-cola EMV/BR Code com CRC16 válido e PDF de
> demonstração — mas sem registro em banco algum. O ciclo de vida
> (liquidação, baixa, estorno…) é simulado injetando eventos fake no
> **pipeline real do webhook** (`_processar_evento_cobranca`), o que exercita
> o mesmo código de produção do casamento, idempotência e máquina de estados.

---

## 1. Como gerar a massa de dados

```bash
# Passo único (base + boletos fake + ciclo de cobrança registrada)
python manage.py gerar_dados_teste --limpar

# Ou por etapas:
python manage.py gerar_dados_teste --limpar --sem-boletos   # base
python manage.py gerar_dados_teste --so-boletos             # boletos (fake p/ Sicoob/C6)
python manage.py gerar_dados_teste --so-cobranca-api        # ciclo de vida BAPI
```

O que cada etapa produz para as HUs BAPI:

| Etapa | Resultado |
|---|---|
| base | 2 imobiliárias × 4 contas: BB/Bradesco (`brcobranca`) e **Sicoob/C6** (`sicoob`/`c6`, com `tenant_id` e `account_config` de demonstração) |
| `--so-boletos` | Parcelas das contas Sicoob/C6 recebem **boleto fake completo**: `cobranca_id`, linha digitável, código de barras, `valor_boleto`, PDF, `provider`, `metodo_cobranca`, `status_cobranca=registrada`, `pix_txid`; contratos C6 alternam **boleto** e **bolepix** (com `ext_ref` + `pix_copia_cola`) |
| `--so-cobranca-api` | Eventos fake via pipeline do webhook distribuem os estados do ciclo (tabela abaixo) |

### 1.1 Distribuição do ciclo de vida (determinística, por índice da parcela)

| Papel (i % 10) | Cenário | Estado final | HU |
|---|---|---|---|
| 0–2 | Evento `liquidado` casado por `cobranca_id` | `LIQUIDADA` + parcela paga | BAPI-18, 22 |
| 3 | Evento `liquidado` casado por `ext_ref` (bolepix) ou `txid` | `LIQUIDADA` | BAPI-13 |
| 4 | Evento `pix.recebido` casado por `txid` | `LIQUIDADA` | BAPI-16 |
| 5 | Evento `baixado` (cancelada no banco) | `BAIXADA` | BAPI-20, 26 |
| 6 | Evento `expirado` (vencida no banco) | `EXPIRADA` | BAPI-20 |
| 7 | `liquidado` + estorno pela gestão (transição LIQUIDADA→ESTORNADA) | `ESTORNADA` | BAPI-28 |
| 8–9 | Sem evento | `REGISTRADA` (em aberto) | BAPI-08..10 |

Cenários de borda gerados ao final de cada execução:

| Cenário | Resultado no log `EventoCobrancaApi` | HU |
|---|---|---|
| Reenvio de `liquidado` para parcela já baixada | `duplicado` | BAPI-19 |
| `liquidado` tardio em parcela `BAIXADA` (transição ilegal) | `ignorado` | BAPI-24 |
| Evento com `cobranca_id` inexistente | `sem_parcela` | BAPI-22 |
| 4 parcelas marcadas `AGUARDANDO_CIP` (409 na emissão, sem `cobranca_id`) | — | BAPI-25, 33 |

> Obs.: em parcela já `LIQUIDADA`, o reenvio nem chega à máquina de estados —
> a idempotência por `cobranca_id`+baixado responde `duplicado` antes
> (comportamento real do webhook).

### 1.2 Invariantes esperadas após a geração (checklist de verificação)

- Toda parcela com `provider` ∈ {`sicoob`, `c6`} tem `cobranca_id` único,
  linha digitável de 47 dígitos, código de barras de 44 dígitos e PDF em
  `boleto_pdf_db`.
- Parcelas `bolepix` (só C6) têm `ext_ref` e `pix_copia_cola` (EMV com CRC
  válido); o `Contrato.metodo_cobranca` correspondente é `bolepix` e a
  imobiliária tem `bolepix` habilitado em `metodos_cobranca` (BAPI-06/07).
- Parcelas `LIQUIDADA` estão `pago=True` com `EventoCobrancaApi` `baixado`.
- Parcelas `AGUARDANDO_CIP` não têm `cobranca_id` (emissão não completou) e
  têm `conta_bancaria` atribuída — insumo da fila de reprocessamento.
- Nenhuma parcela Sicoob/C6 entra em remessa/retorno CNAB (conciliação é por
  webhook); remessa CNAB segue exclusiva de BB/Bradesco (`brcobranca`).

---

## 2. Cenários de teste por grupo de HU

Formato: **Dado / Quando / Então**. A coluna “Automação” aponta o teste
existente ou o incluído neste pacote.

### 2.1 Configuração & Onboarding (BAPI-01..05)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-01 | Credenciais cifradas | conta Sicoob/C6 com `client_id/secret` | salvar | valores em `credenciais` cifrados (Fernet), nunca em texto claro | `test_boleto_api_fase1.py` |
| CT-02 | Banco ↔ provider incompatível | conta banco 001 | escolher provider `c6` | `ValidationError` em `ContaBancaria.clean()` | `test_boleto_api_fase1.py` |
| CT-03 | Onboarding devolve token | conta sem `bapi_token` | `garantir_bapi_token()` (gateway mockado) | `POST /credenciais` chamado 1×; token gravado cifrado | `test_boleto_api_fase3.py` |
| CT-04 | Recadastro no 401 | token revogado (mock devolve 401) | operação `com_retry_credencial()` | recadastra e repete a operação 1× | `test_boleto_api_fase3.py` |
| CT-05 | `account_config` incompleto | conta C6 sem `billing_scheme` | `account_config_faltando()` | lista aponta o campo faltante (validação branda) | `test_account_config_fase2.py` |

### 2.2 Métodos de cobrança (BAPI-06..07)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-06 | Método não habilitado | imobiliária só com `boleto` | contrato com `metodo_cobranca=bolepix` | `ValidationError` no `Contrato.clean()` | `test_boleto_api_fase1.py` |
| CT-07 | Massa coerente | dados de teste gerados | inspecionar contratos `bolepix` | imobiliária correspondente tem `bolepix` habilitado | `test_cenarios_dados_teste_bapi.py` |

### 2.3 Emissão — boleto / bolepix / pix (BAPI-08..16)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-08 | Emissão registra rastreio | parcela pendente, conta Sicoob (gateway mockado ou **fake**) | emitir | `provider/metodo_cobranca/status_cobranca=REGISTRADA` + `cobranca_id` persistidos (BAPI-10) | `test_boleto_api_fase2/3.py`, fake: `test_cenarios_dados_teste_bapi.py` |
| CT-09 | Persistência p/ 2ª via | emissão ok | reabrir parcela | linha digitável (47 díg.), código de barras (44 díg.), PDF disponíveis | `test_boleto_fake.py` + dados gerados |
| CT-10 | BoletoPix expõe Pix | contrato C6 `bolepix` | emitir | `ext_ref` e `pix_copia_cola` (CRC EMV válido) preenchidos p/ portal (BAPI-12) | `test_cenarios_dados_teste_bapi.py` |
| CT-11 | Pix com txid | qualquer emissão fake | inspecionar | `pix_txid = GC<contrato:07d>P<parcela:04d>` (mesmo formato da emissão real) | `test_cenarios_dados_teste_bapi.py` |

### 2.4 Conciliação por webhook (BAPI-17..22)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-12 | HMAC inválido | webhook com `X-Signature` errada | POST | 401, nada processado | `test_boleto_api_fase4.py` |
| CT-13 | Baixa automática | parcela `REGISTRADA` | evento `liquidado` por `cobranca_id` | parcela paga, `LIQUIDADA`, evento `baixado` | fase4 + ciclo fake |
| CT-14 | Casamento por `ext_ref` | bolepix sem `cobranca_id` no evento | evento com `ext_ref` | mesma baixa (ordem cobranca_id→ext_ref→txid) | fase4 + ciclo fake |
| CT-15 | Casamento por `txid` | evento `pix.recebido` | POST | baixa por `pix_txid` | fase4 + ciclo fake |
| CT-16 | Idempotência por `event_id` | evento já processado reenviado | POST | `duplicado`, sem 2ª baixa | fase4 + ciclo fake |
| CT-17 | Evento órfão | `cobranca_id` desconhecido | POST | `sem_parcela` registrado p/ auditoria | fase4 + ciclo fake |
| CT-18 | Auditoria imutável | qualquer evento | POST | `EventoCobrancaApi` guarda payload/status/resultado | fase4 |

### 2.5 Máquina de estados (BAPI-23..25)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-19 | Transição legal | `REGISTRADA` | `liquidado` | `LIQUIDADA` | `test_boleto_api_fase5.py` |
| CT-20 | Fora de ordem | `BAIXADA` | `liquidado` tardio | evento `ignorado`, estado preservado | fase5 + ciclo fake |
| CT-21 | Estado terminal | `ESTORNADA` | qualquer evento | rejeitado (terminal) | fase5 |
| CT-22 | 409/CIP | emissão devolve 409 `motivo=cip` | emitir | `AGUARDANDO_CIP`, sem `cobranca_id` | fase5 + `_simular_aguardando_cip` |

### 2.6 Gestão da cobrança (BAPI-26..29)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-23 | Cancelar propaga | parcela `REGISTRADA` (gateway mock aceita) | cancelar | `DELETE /cobranca/{id}`; local `BAIXADA` | `test_boleto_api_fase6.py` |
| CT-24 | Gateway recusa | mock recusa | cancelar | retorna `False`, status local intacto | fase6 |
| CT-25 | Estorno Pix | parcela `LIQUIDADA` com `e2eid` | estornar | `PUT /pix/recebidos/...`; `ESTORNADA` (terminal) | fase6 + ciclo fake |
| CT-26 | Alterar cobrança | parcela `REGISTRADA` C6 | alterar valor/vencimento | `PUT /cobranca/{id}` | fase6 |

### 2.7 Agendadores — Fase 7 (BAPI-30, 31, 33)

| # | Cenário | Dado | Quando | Então | Automação |
|---|---|---|---|---|---|
| CT-27 | Polling Sicoob baixa | parcela Sicoob aberta; consulta (mock) devolve `liquidado` | `polling_boletos_sicoob` | baixa idempotente + evento `conciliacao.polling-sicoob` | `test_boleto_api_fase7.py` |
| CT-28 | Polling não liquidado | consulta devolve `registrado` | idem | nada muda | fase7 |
| CT-29 | Conciliação Pix | `GET /pix/recebidos` (mock) devolve txid casável | `conciliar_pix_recebidos` | baixa por txid; já paga → `duplicado` | fase7 |
| CT-30 | Fila CIP | parcelas `AGUARDANDO_CIP` da massa fake | `reprocessar_fila_cip` (emissão mockada) | reemite e completa | fase7 + massa fake |

### 2.8 Telas alimentadas pela massa fake (verificação visual)

Com a massa gerada, as telas do ciclo devem exibir todos os estados sem
nenhuma chamada externa (roteiro da skill `verify`):

1. `/financeiro/cobranca/` — hub com REGISTRADA / LIQUIDADA / BAIXADA /
   EXPIRADA / ESTORNADA / AGUARDANDO_CIP.
2. `/financeiro/boletos/` — 2ª via com linha digitável e PDF fake.
3. Portal do comprador — parcela bolepix exibe Pix copia-e-cola.
4. `/financeiro/cobranca/conciliacao/` — log de eventos com `baixado`,
   `duplicado`, `ignorado` e `sem_parcela`.

---

## 3. Boleto Fake — contrato do gerador

`financeiro/services/boleto_fake.py` (sem dependências externas, sem rede):

| Função | Garantia testável |
|---|---|
| `gerar_codigo_barras_fake()` | 44 dígitos; DV geral mod-11 na posição 5; fator de vencimento com o reinício FEBRABAN de 22/02/2025 |
| `gerar_linha_digitavel()` | 47 dígitos; DVs mod-10 dos 3 campos; espelha o código de barras |
| `gerar_pix_copia_cola_fake()` | payload EMV/BR Code com CRC16-CCITT válido e txid no campo 62-05 |
| `gerar_pdf_boleto_fake()` | PDF 1.4 válido e legível (2ª via/anexo) |
| `montar_boleto_fake()` | dict no MESMO formato de `BoletoApiClient._normalizar_cobranca` — os simuladores persistem pelo caminho real (`registrar_emissao`) |

Testes: `tests/unit/financeiro/test_boleto_fake.py` e
`tests/unit/financeiro/test_cenarios_dados_teste_bapi.py`.
