# Referência de Campos BRCobranca por Banco

Documentação completa dos campos aceitos pela biblioteca BRCobranca para geração de boletos bancários e remessas CNAB.

**Fonte:** https://github.com/Maxwbh/brcobranca (v12.8.1)  
**Atualizado em:** 2026-05-29

> ⚠️ **Atenção:** este projeto usa o fork `Maxwbh/brcobranca`, não o `kivanio/brcobranca` original.
> Os campos de PIX (`chave_pix`, `tipo_chave_pix`, `txid`) e o C6 Bank (336) existem APENAS no fork customizado.

---

## Campos Comuns a Todos os Bancos (Classe Base)

### Obrigatórios

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `agencia` | str | Número da agência (sem dígito verificador, exceto quando indicado) |
| `conta_corrente` | str | Número da conta corrente (sem dígito verificador) |
| `moeda` | str | Tipo de moeda. Sempre `'9'` (Real Brasileiro) |
| `especie_documento` | str | Tipo do documento. Padrão: `'DM'` (Duplicata Mercantil) |
| `especie` | str | Símbolo da moeda. Sempre `'R$'` |
| `aceite` | str | Aceite após vencimento: `'S'` ou `'N'` |
| `nosso_numero` | str | Identificador sequencial do boleto (tamanho varia por banco) |
| `sacado` | str | Nome completo do pagador |

### Opcionais (aceitos por todos os bancos)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `convenio` | str | Número do convênio/contrato bancário |
| `carteira` | str | Tipo de carteira/modalidade de cobrança |
| `variacao` | str | Variação da carteira (banco-específico) |
| `valor` | float | Valor do boleto em reais |
| `data_vencimento` | str | Data de vencimento no formato `'YYYY/MM/DD'` |
| `data_documento` | str | Data de emissão do documento (`'YYYY/MM/DD'`) |
| `data_processamento` | str | Data de processamento (`'YYYY/MM/DD'`) |
| `documento_numero` | str | Número do documento/título **— usar APENAS este** |
| `cedente` | str | Nome/Razão social do beneficiário |
| `documento_cedente` | str | CPF/CNPJ do beneficiário (somente dígitos) |
| `cedente_endereco` | str | Endereço do beneficiário |
| `sacado_documento` | str | CPF/CNPJ do pagador (somente dígitos) |
| `sacado_endereco` | str | Endereço completo do pagador |
| `local_pagamento` | str | Texto do local de pagamento |
| `instrucao1`…`instrucao7` | str | Linhas de instruções ao caixa |
| `demonstrativo` | str | Texto demonstrativo no corpo do boleto |
| `quantidade` | str | Quantidade de unidades (banco-específico) |
| `codigo_servico` | bool | Código de serviço (banco-específico) |
| `avalista` | str | Nome do avalista |
| `avalista_documento` | str | CPF/CNPJ do avalista |

### Multa e Juros

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `codigo_multa` | str | `'1'` = valor fixo, `'2'` = percentual |
| `valor_multa` | float | Valor fixo da multa (em R$) |
| `percentual_multa` | float | Percentual da multa (ex: `2.0` = 2%) |
| `data_multa` | str | Data de início da multa (`'YYYY/MM/DD'`) |
| `codigo_mora` | str | `'1'` = valor diário, `'2'` = taxa mensal |
| `valor_mora` | float | Valor diário da mora (em R$) |
| `percentual_mora` | float | Percentual mensal da mora |
| `percentual_juros` | float | Equivalente a `percentual_mora` (alias) |
| `data_mora` | str | Data de início da mora (`'YYYY/MM/DD'`) |
| `desconto` | float | Valor do desconto (em R$) |
| `data_desconto` | str | Data limite para desconto (`'YYYY/MM/DD'`) |

### PIX Híbrido (v12.8.0+) — 8 bancos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `chave_pix` | str | Chave PIX do recebedor (CPF, CNPJ, e-mail, celular ou aleatória) |
| `tipo_chave_pix` | str | Tipo: `'cpf'`, `'cnpj'`, `'email'`, `'celular'`, `'aleatoria'` |
| `txid` | str | ID da transação PIX (alfanumérico, máx. 35 caracteres) |
| `emv` | str | **[resposta]** Código EMV/Pix Copia e Cola gerado pelo brcobrança |

> Bancos com suporte a PIX: 001, 033, 104, 237, **336**, 341, 748 (+ Sicredi 748 em CNAB via mixin Y-03).

---

## Campos Específicos por Banco

### Banco do Brasil (001)

**Validações:**
- `agencia`: máx. 4 dígitos
- `conta_corrente`: máx. 8 dígitos
- `carteira`: máx. 2 dígitos
- `convenio`: **4 a 8 dígitos** — **OBRIGATÓRIO**
- `nosso_numero`: tamanho varia conforme comprimento do convênio:
  - Convênio 8 díg. → máx. 9 díg.
  - Convênio 7 díg. → máx. 10 díg.
  - Convênio 6 díg. + `codigo_servico=false` → máx. 5 díg.
  - Convênio 6 díg. + `codigo_servico=true` → máx. 17 díg.
  - Convênio 4 díg. → máx. 7 díg.

**Campos específicos:**
- `codigo_servico` — bool, opcional

**Padrões:** `carteira: '18'`, `local_pagamento: 'PAGÁVEL EM QUALQUER BANCO.'`

**Remessa:** `variacao` (CNAB 240) ou `variacao_carteira` (CNAB 400) = carteira zero-padded 3 dígitos.

---

### Santander (033)

**Validações:**
- `agencia`: máx. 4 dígitos
- `conta_corrente`: máx. 9 dígitos
- `convenio`: máx. 7 dígitos — **OBRIGATÓRIO**
- `nosso_numero`: máx. 7 dígitos

---

### Caixa Econômica Federal (104)

**Validações:**
- `emissao`: exatamente 1 dígito — **OBRIGATÓRIO**
- `carteira`: exatamente 1 dígito
- `convenio`: exatamente 6 dígitos (código do cedente)
- `nosso_numero`: exatamente 15 dígitos

**Campos específicos:**
- `emissao` — `'4'` (beneficiário emite) — **OBRIGATÓRIO**
- `codigo_beneficiario` — geralmente igual ao convênio

**Padrões:** `carteira: '1'` (Registrada), `emissao: '4'`

---

### Bradesco (237)

**Validações:**
- `agencia`: máx. 4 dígitos
- `conta_corrente`: máx. 7 dígitos
- `nosso_numero`: máx. 11 dígitos
- `carteira`: máx. 2 dígitos

**Padrões:** `carteira: '06'`

**Suporte:** apenas CNAB **400** (sem CNAB 240).  
**Remessa:** usa `codigo_empresa` (= convênio da conta) — não é o campo `convenio` padrão.

---

### C6 Bank (336) — adicionado em v12.8.0

**Validações:**
- `carteira`: obrigatoriamente `'10'` ou `'20'` (inclusão validada)
  - `'10'` = Cobrança Simples Emissão Banco (padrão)
  - `'20'` = Cobrança Simples Emissão Cliente
- `nosso_numero`: exatamente **10 dígitos** (DV módulo 11 calculado internamente)
- `convenio`: até 12 dígitos — **OBRIGATÓRIO** (código do beneficiário atribuído pelo C6)
- `agencia`: máx. 4 dígitos
- `conta_corrente`: máx. 8 dígitos

**Padrões:** `carteira: '10'`, `banco_dv: '7'`, `especie_documento: 'DM'`

**Remessa CNAB 400:**  
A classe `Cnab400::BancoC6` exige o campo `codigo_beneficiario` (não `convenio`).  
O `CNABService` realiza o mapeamento automaticamente:
```python
dados_empresa['codigo_beneficiario'] = conta.convenio.zfill(12)[:12]
```

**PIX:** suportado em CNAB 400 via `Cnab400::BancoC6Pix` (segmento tipo 8).

---

### Itaú (341)

**Validações:**
- `agencia`: máx. 4 dígitos
- `conta_corrente`: máx. 5 dígitos
- `convenio`: máx. 5 dígitos
- `nosso_numero`: máx. 8 dígitos
- `seu_numero`: máx. 7 dígitos

**Campos específicos:**
- `seu_numero` — obrigatório para carteiras: `198, 106, 107, 122, 142, 143, 195, 196`

**Padrões:** `carteira: '175'`

**Suporte:** CNAB 400 e **444** (formato Itaú-específico).

---

### Sicoob (756)

**Validações:**
- `agencia`: exatamente 4 dígitos
- `conta_corrente`: exatamente 8 dígitos
- `digito_conta`: exatamente 1 dígito
- `convenio`: exatamente **9 dígitos** (com DV) — nas remessas; boleto aceita até 7
- `nosso_numero`: máx. 7 dígitos
- `variacao`: máx. 2 dígitos
- `sequencial_remessa`: exatamente **7 dígitos** (deve ser enviado como string)

**Carteiras disponíveis:** `'1'`, `'3'`, `'9'`  
- **Carteira 9:** usa `numero_contrato` no campo de código cedente do código de barras.  
  Exige `numero_contrato` na remessa.

**Layout 810 (CNAB 240):**  
Versão alternativa onde o cliente calcula os dígitos verificadores.  
Enviar `layout: '810'` nos dados de remessa para ativar.

**Campos específicos:**
- `variacao` — 2 dígitos (padrão: `'01'`)
- `numero_contrato` — obrigatório para carteira 9
- `modalidade_carteira` — 1 dígito (para remessa)
- `distribuicao_boleto` — padrão `'2'` (para remessa)
- `tipo_formulario` — padrão `'4'` (A4 sem envelopamento)
- `nome_banco` — padrão `'BANCOOBCED'` (configurável na remessa CNAB 400)

**Padrões:** `carteira: '1'`, `variacao: '01'`

**Suporte:** CNAB 240 (remessa + **retorno**) e CNAB 400 (apenas remessa).

---

### Sicredi (748)

**Validações:**
- `agencia`: máx. 4 dígitos
- `conta_corrente`: máx. 5 dígitos
- `nosso_numero`: máx. 5 dígitos
- `carteira`: máx. 1 dígito
- `posto`: máx. 2 dígitos — **OBRIGATÓRIO**
- `byte_idt`: exatamente 1 caractere — **OBRIGATÓRIO**

**Campos específicos:**
- `posto` — código do posto do beneficiário — **OBRIGATÓRIO**
- `byte_idt` — `'2'` para emissão pelo beneficiário — **OBRIGATÓRIO**

**Padrões:** `carteira: '3'` (sem registro), `especie_documento: 'A'`

---

### Banrisul (041)

**Validações:**
- `agencia`: 4 dígitos
- `conta_corrente`: 9 dígitos
- `carteira`: 1 dígito (`'1'` ou `'2'`)
- `nosso_numero`: 8 dígitos

---

### Unicred (136)

**Suporte:** CNAB 240 + CNAB 400 (remessa e retorno).  
**Carteiras:** `'21'`

---

## Campos de Remessa por Banco (CNAB)

Campos adicionais para `POST /api/remessa` (nível de `dados_empresa`):

| Banco | Campo extra | Valor esperado |
|-------|------------|----------------|
| BB (001) CNAB 240 | `variacao` | carteira zero-padded 3 dígitos (ex: `'018'`) |
| BB (001) CNAB 400 | `variacao_carteira` | carteira zero-padded 3 dígitos |
| Bradesco (237) | `codigo_empresa` | convênio da conta (string) |
| C6 (336) | `codigo_beneficiario` | convênio da conta, até 12 dígitos |
| Sicoob (756) | `sequencial_remessa` | string de exatamente 7 dígitos (ex: `'0000001'`) |

> O `CNABService` (`financeiro/services/cnab_service.py`) aplica esses mapeamentos automaticamente para cada banco.

---

## Campos de Pagamento (por item da remessa)

Mapeados pelo `FieldMapper` do `boleto_cnab_api` antes de instanciar `Brcobranca::Remessa::Pagamento`:

| Campo enviado | Campo do gem | Notas |
|--------------|-------------|-------|
| `sacado` | `nome_sacado` | mapeado automaticamente |
| `sacado_documento` | `documento_sacado` | mapeado automaticamente |
| `sacado_endereco` | `endereco_sacado` | mapeado automaticamente |
| `sacado_cidade` | `cidade_sacado` | mapeado automaticamente |
| `sacado_uf` | `uf_sacado` | mapeado automaticamente |
| `sacado_cep` | `cep_sacado` | mapeado automaticamente |
| `sacado_bairro` | `bairro_sacado` | mapeado automaticamente |
| `numero_documento` | `numero` | mapeado automaticamente |
| `documento_numero` | `numero` | mapeado automaticamente |
| `nosso_numero` | `nosso_numero` | direto |
| `valor` | `valor` | direto |
| `data_vencimento` | `data_vencimento` | formato `'YYYY/MM/DD'` |
| `data_emissao` | `data_emissao` | formato `'YYYY/MM/DD'` |

---

## Observações Críticas

### `numero_documento` vs `documento_numero`

O `FieldMapper` da API mapeia `numero_documento` → `numero` (campo do gem). Porém, **alguns bancos rejeitam `numero_documento`** com `NoMethodError`.

- ✅ Enviar sempre **`documento_numero`** (nome correto do gem)
- ✅ O `BoletoService` filtra `numero_documento` automaticamente para BB, Sicoob, C6 e Itaú

### Formato de datas

Todas as datas devem ser enviadas como string `'YYYY/MM/DD'` (ex: `'2026/12/31'`).

### Formato de valores monetários

`valor`, `percentual_multa`, `percentual_juros` devem ser `float` ou `Decimal` em reais.  
A API converte internamente para centavos quando necessário.

---

## Fontes e Referências

- **Gem customizada:** https://github.com/Maxwbh/brcobranca
- **API customizada:** https://github.com/Maxwbh/boleto_cnab_api
- **Classe Base:** `lib/brcobranca/boleto/base.rb`
- **C6 Bank:** `lib/brcobranca/boleto/banco_c6.rb` e `lib/brcobranca/remessa/cnab400/banco_c6.rb`
- **Sicoob:** `lib/brcobranca/boleto/sicoob.rb` e `lib/brcobranca/remessa/cnab400/sicoob.rb`
- **Registry de bancos:** `lib/brcobranca/bancos.rb` (v12.7.0+)
- **Swagger UI:** `GET /api/docs` (quando serviço está rodando)

---

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)  
**Empresa:** M&S do Brasil LTDA  
**Atualizado em:** 2026-05-29 (brcobrança 12.8.1 / PR #45)
