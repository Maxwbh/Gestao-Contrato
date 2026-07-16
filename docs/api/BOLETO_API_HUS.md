# Histórias de Usuário — Integração Boleto-API (Cobrança Registrada Multi-método)

> **Épico novo.** Integração do Gestão-Contrato com o **Boleto-API gateway**
> (v0.6.0) no modelo **stateless / zero-knowledge**: o produto guarda as
> credenciais do banco (cifradas) e o token `bapi_`, envia como `Bearer`, emite
> cobranças por múltiplos métodos (boleto, BoletoPix, Pix) e concilia por
> webhook. O fluxo **BRCobrança/CNAB** permanece como padrão seguro para bancos
> sem REST.
>
> **Todas as HUs deste documento são NOVAS** (🆕), criadas para este épico —
> não substituem as HUs existentes do ROADMAP. Numeração dedicada: **BAPI-NN**.

## Personas

| Persona | Descrição |
|---|---|
| **Gestor** | Configura contas bancárias, credenciais e métodos de cobrança |
| **Operador** | Emite cobranças, acompanha conciliação e trata pendências |
| **Pagador** | Comprador que recebe e paga (boleto, BoletoPix, Pix) |
| **Sistema** | Webhook e jobs: concilia, reprocessa e agenda automaticamente |

## Legenda

Status: ✅ Entregue · 🟡 Parcial · ⬜ Planejado — Todas são 🆕 **NOVA**.

---

## Índice

| # | História | Persona | Fase | Status |
|---|---|---|---|---|
| **Configuração & Onboarding** ||||
| BAPI-01 | Cadastrar credenciais do banco cifradas | Gestor | 1 | ✅ |
| BAPI-02 | Validar compatibilidade banco ↔ provedor | Gestor | 1 | ✅ |
| BAPI-03 | Provisionar credenciais no gateway (onboarding) | Gestor | 3 | ✅ |
| BAPI-04 | Recadastrar credenciais automaticamente no 401 | Sistema | 3 | ✅ |
| BAPI-05 | Apontar campos de `account_config` faltando | Gestor | 2 | ✅ |
| **Métodos disponíveis** ||||
| BAPI-06 | Definir métodos de cobrança na imobiliária | Gestor | 1 | ✅ |
| BAPI-07 | Escolher o método de cobrança no contrato | Operador | 1 | ✅ |
| **Boleto registrado** ||||
| BAPI-08 | Emitir boleto registrado | Operador | 3 | ✅ |
| BAPI-09 | Persistir linha digitável / código de barras / PDF | Operador | 3 | ✅ |
| BAPI-10 | Rastrear provedor/método/status na parcela | Operador | 2 | ✅ |
| **BoletoPix** ||||
| BAPI-11 | Emitir BoletoPix (boleto + QR Pix) | Operador | 3 | ✅ |
| BAPI-12 | Disponibilizar copia-e-cola / QR ao pagador | Pagador | 3 | ✅ |
| BAPI-13 | Conciliar BoletoPix por `ext_ref` | Sistema | 4 | ✅ |
| **Pix** ||||
| BAPI-14 | Emitir Pix com vencimento (cobv) | Operador | 3 | ✅ |
| BAPI-15 | Emitir Pix imediato (2ª via / quitação) | Operador | 3 | ✅ |
| BAPI-16 | Conciliar Pix por `txid` | Sistema | 4 | ✅ |
| **Conciliação por webhook** ||||
| BAPI-17 | Receber webhook autenticado (HMAC) | Sistema | 4 | ✅ |
| BAPI-18 | Dar baixa automática na liquidação | Sistema | 4 | ✅ |
| BAPI-19 | Idempotência de eventos (reenvio do banco) | Sistema | 4 | ✅ |
| BAPI-20 | Atualizar status normalizado por evento | Sistema | 4 | ✅ |
| BAPI-21 | Registrar log de eventos para auditoria | Operador | 4 | ✅ |
| BAPI-22 | Casar a parcela por múltiplas chaves | Sistema | 4 | ✅ |
| **Máquina de estados** ||||
| BAPI-23 | Aceitar apenas transições válidas | Sistema | 5 | ✅ |
| BAPI-24 | Rejeitar evento fora de ordem | Sistema | 5 | ✅ |
| BAPI-25 | Marcar AGUARDANDO_CIP no 409 | Sistema | 5 | ✅ |
| **Gestão da cobrança** ||||
| BAPI-26 | Cancelar propagando ao banco | Operador | 6 | ✅ |
| BAPI-27 | Não cancelar local se o gateway recusar | Operador | 6 | ✅ |
| BAPI-28 | Estornar (devolver) Pix | Operador | 6 | ✅ |
| BAPI-29 | Alterar valor/vencimento da cobrança | Operador | 6 | ✅ |
| **Agendadores (Fase 7)** ||||
| BAPI-30 | Polling de boleto Sicoob (sem webhook) | Sistema | 7 | ✅ |
| BAPI-31 | Conciliação Pix (rede de segurança) | Sistema | 7 | ✅ |
| BAPI-32 | Conciliação financeira (extrato/recebíveis) | Gestor | 7 | ⬜ |
| BAPI-33 | Fila de reprocessamento 409/CIP | Sistema | 7 | ✅ |
| **Planejadas** ||||
| BAPI-34 | Aderir contrato ao Pix Automático | Operador | 8 | ⬜ |
| BAPI-35 | Agendar cobrança do Pix Automático (D-2) | Sistema | 8 | ⬜ |
| BAPI-36 | Retentativa do Pix Automático | Sistema | 8 | ⬜ |
| BAPI-37 | Gerar carnê via gateway (`/carne`) | Operador | 6+ | ⬜ |
| BAPI-38 | Painel de conciliação (recebíveis/extrato) | Gestor | 9 | ⬜ |

---

## Configuração & Onboarding

### BAPI-01 — Cadastrar credenciais do banco cifradas 🆕 ✅
**Como** gestor **quero** cadastrar as credenciais de API do banco (C6/Sicoob)
**para que** o sistema emita cobrança registrada.
**Aceite:** credenciais (`client_id`/`client_secret`/`.pfx`/`access_token`) e o
token `bapi_` guardados **cifrados** (Fernet), nunca em texto claro; chave
dedicada `CREDENTIALS_ENCRYPTION_KEY` (deriva do `SECRET_KEY` em dev).
**Ref.:** `core/crypto.py`, `ContaBancaria.credenciais`/`bapi_token`.

### BAPI-02 — Validar compatibilidade banco ↔ provedor 🆕 ✅
**Como** gestor **quero** ser impedido de escolher provedor incompatível
**para que** eu não crie contas inválidas.
**Aceite:** 336→`c6`/`brcobranca`; 756→`sicoob`/`brcobranca`; demais→`brcobranca`;
validado em `ContaBancaria.clean()`.

### BAPI-03 — Provisionar credenciais no gateway (onboarding) 🆕 ✅
**Como** gestor **quero** enviar as credenciais ao gateway **para que** ele
devolva o token `bapi_` de uso diário.
**Aceite:** `POST /credenciais` grava o `bapi_token` cifrado; `garantir_bapi_token()`
faz o onboarding quando não há token.
**Ref.:** `financeiro/services/boleto_api_onboarding.py`.

### BAPI-04 — Recadastrar credenciais automaticamente no 401 🆕 ✅
**Como** sistema **quero** refazer o cadastro quando o token expira/é revogado
**para que** a operação não pare após um redeploy.
**Aceite:** `com_retry_credencial()` recadastra em 401/424 e tenta a operação uma
vez mais.

### BAPI-05 — Apontar campos de `account_config` faltando 🆕 ✅
**Como** gestor **quero** saber quais parâmetros faltam por provedor **para que** o
cadastro fique completo.
**Aceite:** `ACCOUNT_CONFIG_SCHEMA` + `account_config_faltando()` (validação branda).

---

## Métodos disponíveis

### BAPI-06 — Definir métodos de cobrança na imobiliária 🆕 ✅
**Como** gestor **quero** marcar os métodos oferecidos (Boleto, Carnê, BoletoPix,
Pix Automático) **para que** os contratos só usem o habilitado.
**Aceite:** `Imobiliaria.metodos_cobranca` (lista multi-seleção; default
`["boleto"]`); checkboxes no form e no admin.

### BAPI-07 — Escolher o método de cobrança no contrato 🆕 ✅
**Como** operador **quero** escolher o método do contrato **para que** ele seja
cobrado da forma combinada.
**Aceite:** `Contrato.metodo_cobranca` (default `boleto`); validação de que está
habilitado na imobiliária.

---

## Boleto registrado

### BAPI-08 — Emitir boleto registrado 🆕 ✅
**Como** operador **quero** emitir boleto registrado (C6/Sicoob) **para que** a
cobrança fique registrada no banco com conciliação por evento.
**Aceite:** `POST /cobranca` com `Bearer`; erros tipados (401/409/422).

### BAPI-09 — Persistir linha digitável / código de barras / PDF 🆕 ✅
**Como** operador **quero** os dados do boleto persistidos **para que** eu envie e
reimprima a 2ª via.
**Aceite:** `cobranca_id`, `linha_digitavel`, `codigo_barras`, PDF salvos na parcela.

### BAPI-10 — Rastrear provedor/método/status na parcela 🆕 ✅
**Como** operador **quero** ver por parcela como/onde foi cobrada **para que** eu
concilie e atenda o pagador.
**Aceite:** `provider`, `metodo_cobranca`, `ext_ref`, `status_cobranca` gravados na
emissão via `registrar_emissao()`.

---

## BoletoPix

### BAPI-11 — Emitir BoletoPix (boleto + QR Pix) 🆕 ✅
**Como** operador **quero** emitir um boleto com QR Pix (C6) **para que** o pagador
pague por boleto **ou** Pix.
**Aceite:** `POST /bolepix` quando `Contrato.metodo_cobranca = bolepix`; persiste
`ext_ref` e `pix_copia_cola`.

### BAPI-12 — Disponibilizar copia-e-cola / QR ao pagador 🆕 ✅
**Como** pagador **quero** o Pix copia-e-cola do boleto **para que** eu pague na
hora pelo app do banco.
**Aceite:** `pix_copia_cola` disponível na parcela para exibição no portal.

### BAPI-13 — Conciliar BoletoPix por `ext_ref` 🆕 ✅
**Como** sistema **quero** casar o evento de pagamento pelo `ext_ref` **para que**
o BoletoPix baixe corretamente.
**Aceite:** webhook casa por `ext_ref` quando não há `cobranca_id`.

---

## Pix

### BAPI-14 — Emitir Pix com vencimento (cobv) 🆕 ✅
**Como** operador **quero** emitir uma cobrança Pix com vencimento **para que** o
pagador quite via Pix respeitando a data.
**Aceite:** `POST /pix`; retorna `txid` + EMV.

### BAPI-15 — Emitir Pix imediato (2ª via / quitação) 🆕 ✅
**Como** operador **quero** gerar um Pix imediato **para que** o pagador faça uma
quitação/2ª via na hora.
**Aceite:** `POST /pix` (cob); retorna `txid` + copia-e-cola.

### BAPI-16 — Conciliar Pix por `txid` 🆕 ✅
**Como** sistema **quero** casar o Pix recebido pelo `txid` **para que** a parcela
baixe automaticamente.
**Aceite:** evento `pix.recebido` casa por `pix_txid` e marca `LIQUIDADA`.

---

## Conciliação por webhook

### BAPI-17 — Receber webhook autenticado (HMAC) 🆕 ✅
**Como** sistema **quero** validar a origem do push **para que** só o gateway
consiga baixar parcelas.
**Aceite:** `POST /financeiro/webhooks/boleto-api/` valida `X-Signature`
(**HMAC-SHA256 timing-safe**); rejeita inválido com 401.

### BAPI-18 — Dar baixa automática na liquidação 🆕 ✅
**Como** operador **quero** que a parcela baixe sozinha quando o banco confirma
**para que** eu não concilie manualmente.
**Aceite:** `liquidado`/`pago`/`pix.recebido` → registra pagamento + `LIQUIDADA`.

### BAPI-19 — Idempotência de eventos 🆕 ✅
**Como** sistema **quero** ignorar eventos repetidos **para que** o reenvio do
banco não duplique baixas.
**Aceite:** dedup por `event_id` e por `cobranca_id` já baixado → `duplicado`.

### BAPI-20 — Atualizar status normalizado por evento 🆕 ✅
**Como** operador **quero** o status normalizado atualizado a cada evento **para
que** eu veja o estado real da cobrança.
**Aceite:** mapa status do gateway → `StatusCobranca`
(registrado→REGISTRADA, baixado→BAIXADA, expirado→EXPIRADA, estornado→ESTORNADA).

### BAPI-21 — Registrar log de eventos para auditoria 🆕 ✅
**Como** operador **quero** um histórico imutável dos eventos **para que** eu
audite a conciliação.
**Aceite:** `EventoCobrancaApi` registra cada push (id/status/payload/resultado).

### BAPI-22 — Casar a parcela por múltiplas chaves 🆕 ✅
**Como** sistema **quero** casar por `cobranca_id`, `ext_ref` ou `txid` **para que**
qualquer método seja conciliado.
**Aceite:** ordem de tentativa cobranca_id → ext_ref → txid; sem casamento →
`sem_parcela` (registrado).

---

## Máquina de estados

### BAPI-23 — Aceitar apenas transições válidas 🆕 ✅
**Como** sistema **quero** um conjunto formal de transições **para que** o estado
da cobrança seja consistente.
**Aceite:** `TRANSICOES_COBRANCA`; `LIQUIDADA` não regride para `REGISTRADA`;
`ESTORNADA` é terminal; `BAIXADA`/`EXPIRADA` permitem reemissão.

### BAPI-24 — Rejeitar evento fora de ordem 🆕 ✅
**Como** sistema **quero** ignorar transições ilegais **para que** um evento tardio
não corrompa o estado.
**Aceite:** transição ilegal → evento registrado como `ignorado`, sem baixa.

### BAPI-25 — Marcar AGUARDANDO_CIP no 409 🆕 ✅
**Como** sistema **quero** marcar `AGUARDANDO_CIP` quando o banco responde 409
**para que** a cobrança entre na fila de reprocessamento.
**Aceite:** emissão com `motivo=cip` → `status_cobranca=AGUARDANDO_CIP`.

```
              emitir            webhook/polling
  (vazio) ────────────► REGISTRADA ─────────────► LIQUIDADA ──► ESTORNADA
     │  409 (CIP)          │  cancelar                              (terminal)
     └──► AGUARDANDO_CIP   │────────► BAIXADA ──► (reemissão) ─┐
              │            │  vencimento                       │
              └──────────► └────────► EXPIRADA ──► (reemissão)─┘
```

---

## Gestão da cobrança

### BAPI-26 — Cancelar propagando ao banco 🆕 ✅
**Como** operador **quero** cancelar a cobrança **para que** ela seja baixada **no
banco**, não só no sistema.
**Aceite:** C6/Sicoob → `DELETE /cobranca/{id}`; sucesso → `BAIXADA`;
BRCobrança/CNAB segue local.

### BAPI-27 — Não cancelar local se o gateway recusar 🆕 ✅
**Como** operador **quero** que o cancelamento local só aconteça se o banco aceitar
**para que** não fique status divergente.
**Aceite:** gateway recusa → `cancelar_boleto()` retorna `False` sem alterar local.

### BAPI-28 — Estornar (devolver) Pix 🆕 ✅
**Como** operador **quero** estornar um Pix recebido **para que** o valor volte ao
pagador e a cobrança fique `ESTORNADA`.
**Aceite:** `PUT /pix/recebidos/{e2eid}/devolucao/{id}` (exige `e2eid`) → `ESTORNADA`.

### BAPI-29 — Alterar valor/vencimento da cobrança 🆕 ✅
**Como** operador **quero** alterar valor/vencimento de uma cobrança registrada
(C6) **para que** eu não precise cancelar e reemitir.
**Aceite:** `PUT /cobranca/{id}`.

---

## Agendadores (Fase 7)

### BAPI-30 — Polling de boleto Sicoob 🆕 ✅
**Como** sistema **quero** consultar periodicamente as cobranças Sicoob em aberto
**para que** concilie mesmo sem webhook de boleto.
**Aceite:** job `polling_boletos_sicoob` consulta `GET /cobranca/{id}` das parcelas
Sicoob em aberto e baixa via `baixar_por_conciliacao()` (idempotente).
**Ref.:** `financeiro/tasks.py`, `financeiro/services/boleto_api_conciliacao.py`.

### BAPI-31 — Conciliação Pix (rede de segurança) 🆕 ✅
**Como** sistema **quero** cruzar `GET /pix/recebidos` com as parcelas **para que**
eu tenha um fallback do webhook.
**Aceite:** job `conciliar_pix_recebidos(dias)` casa por `pix_txid` e baixa as não
pagas; parcela já paga → `duplicado` (sem baixa dupla).
**Ref.:** `financeiro/tasks.py`, `financeiro/services/boleto_api_conciliacao.py`.

### BAPI-33 — Fila de reprocessamento 409/CIP 🆕 ✅
**Como** sistema **quero** reprocessar cobranças `AGUARDANDO_CIP` **para que** a
emissão se complete quando a CIP liberar.
**Aceite:** job `reprocessar_fila_cip` reemite (`gerar_boleto(force=True)`) as
parcelas `AGUARDANDO_CIP`; sucesso atualiza o status pela própria emissão.
**Ref.:** `financeiro/tasks.py`.

---

## Planejadas (Fases 7–9)

### BAPI-32 — Conciliação financeira (extrato/recebíveis) 🆕 ⬜
**Como** gestor **quero** cruzar `GET /conciliacao` e `GET /extrato` **para que** eu
tenha relatório financeiro consolidado.

### BAPI-34 — Aderir contrato ao Pix Automático 🆕 ⬜
**Como** operador **quero** aderir o contrato ao débito recorrente **para que** as
parcelas sejam cobradas automaticamente (idRec, recorrência).

### BAPI-35 — Agendar cobrança do Pix Automático (D-2) 🆕 ⬜
**Como** sistema **quero** agendar a cobrança recorrente 2 dias antes do vencimento
**para que** o débito ocorra no prazo.

### BAPI-36 — Retentativa do Pix Automático 🆕 ⬜
**Como** sistema **quero** retentar cobranças não pagas conforme a política **para
que** a inadimplência recorrente seja recuperada.

### BAPI-37 — Gerar carnê via gateway 🆕 ⬜
**Como** operador **quero** gerar o carnê registrado via `POST /carne` **para que** o
carnê use cobrança registrada (hoje usa o PDF local BRCobrança).

### BAPI-38 — Painel de conciliação 🆕 ⬜
**Como** gestor **quero** um painel de recebíveis/extrato **para que** eu acompanhe
% conciliado, recebido por origem e pendências.

---

## Referências técnicas

| Área | Onde |
|---|---|
| Cifra de segredos | `core/crypto.py` |
| Conta/credenciais/métodos | `core/models.py` (`ContaBancaria`, `ProviderBoleto`, `MetodoCobranca`) |
| Cliente HTTP do gateway | `financeiro/services/boleto_api_client.py` |
| Onboarding | `financeiro/services/boleto_api_onboarding.py` |
| Emissão + rastreio + estados | `financeiro/models.py` (`Parcela`, `StatusCobranca`, `TRANSICOES_COBRANCA`) |
| Webhook / conciliação | `financeiro/views.py` (`webhook_boleto_api`, `_processar_evento_cobranca`) |
| Log de eventos | `financeiro/models.py` (`EventoCobrancaApi`) |
| Agendadores (Fase 7) | `financeiro/tasks.py`, `financeiro/services/boleto_api_conciliacao.py` |
| Boleto fake (dados de teste, sem API do banco) | `financeiro/services/boleto_fake.py`, `core/management/commands/gerar_dados_teste.py` |
| Cenários de teste | `docs/analise/CENARIOS_TESTE_BOLETO_API.md` |
| Testes | `tests/unit/financeiro/test_boleto_api_fase{2..7}.py`, `tests/unit/core/*fase1*` |

## Endpoints do gateway consumidos

| Método | Endpoint | HUs |
|---|---|---|
| POST | `/credenciais` | BAPI-03, BAPI-04 |
| POST | `/cobranca` | BAPI-08, BAPI-09 |
| POST | `/bolepix` | BAPI-11 |
| POST | `/pix` | BAPI-14, BAPI-15 |
| PUT | `/cobranca/{id}` | BAPI-29 |
| DELETE | `/cobranca/{id}` | BAPI-26 |
| PUT | `/pix/recebidos/{e2eid}/devolucao/{id}` | BAPI-28 |
| POST | `/carne` | BAPI-37 (planejado) |
| GET | `/cobranca/{id}`, `/pix/recebidos`, `/conciliacao`, `/extrato` | BAPI-30..32 (planejado) |
| (webhook) | `POST /financeiro/webhooks/boleto-api/` | BAPI-17..22 |
