# Referência de Campos BRCobranca por Banco

Documentação completa dos campos aceitos pela biblioteca BRCobranca para geração de boletos bancários.

**Fonte:** Análise do código-fonte oficial https://github.com/kivanio/brcobranca

**Data:** 2025-11-25

---

## Campos Comuns a Todos os Bancos (Classe Base)

### Campos Obrigatórios (validates presence)
- `agencia` - Número da agência sem dígito verificador
- `conta_corrente` - Número da conta corrente sem dígito verificador
- `moeda` - Tipo de moeda (padrão: '9' para Real)
- `especie_documento` - Tipo do documento (padrão: 'DM')
- `especie` - Símbolo da moeda (padrão: 'R$')
- `aceite` - Aceite após vencimento (padrão: 'S')
- `nosso_numero` - Identificador sequencial do boleto
- `sacado` - Nome do pagador

### Campos Opcionais Aceitos
- `convenio` - Número do convênio/contrato (validado como numérico)
- `carteira` - Tipo de carteira/modalidade de cobrança
- `variacao` - Variação da carteira (banco específico)
- `data_processamento` - Data de processamento do boleto
- `quantidade` - Quantidade de unidades (banco específico)
- `valor` - Valor do boleto em reais
- `data_documento` - Data de emissão do documento
- `data_vencimento` - Data de vencimento do boleto
- `documento_numero` - Número do documento/título (**ENVIAR PARA TODOS OS BANCOS**)
- `numero_documento` - Alias de documento_numero (**ENVIAR PARA TODOS OS BANCOS**)
- `codigo_servico` - Código de serviço (banco específico)

#### Dados do Beneficiário (Cedente)
- `cedente` - Nome/Razão social do beneficiário
- `documento_cedente` - CPF/CNPJ do beneficiário
- `cedente_endereco` - Endereço do beneficiário

#### Dados do Pagador (Sacado)
- `sacado_documento` - CPF/CNPJ do pagador
- `sacado_endereco` - Endereço completo do pagador

#### Dados do Avalista
- `avalista` - Nome do avalista
- `avalista_documento` - CPF/CNPJ do avalista

#### Instruções e Informações Adicionais
- `demonstrativo` - Texto demonstrativo no boleto
- `instrucao1` até `instrucao7` - Linhas de instruções
- `instrucoes` - Array de instruções (alternativa)
- `local_pagamento` - Texto do local de pagamento
- `emv` - Código EMV (se aplicável)
- `descontos_e_abatimentos` - Informações de descontos

#### Multa e Juros
- `codigo_multa` - Tipo de multa: '1' = valor fixo, '2' = percentual
- `valor_multa` - Valor fixo da multa
- `percentual_multa` - Percentual da multa
- `data_multa` - Data de início da multa

- `codigo_mora` - Tipo de mora: '1' = valor diário, '2' = taxa mensal
- `valor_mora` - Valor diário da mora
- `percentual_mora` - Percentual mensal da mora
- `data_mora` - Data de início da mora

#### Desconto
- `desconto` - Valor do desconto
- `data_desconto` - Data limite para desconto

---

## Campos Específicos por Banco

### Banco do Brasil (001)

**Validações de Tamanho:**
- `agencia`: máximo 4 dígitos
- `conta_corrente`: máximo 8 dígitos
- `carteira`: máximo 2 dígitos
- `convenio`: **4 a 8 dígitos (obrigatório)**

**Nosso Número (tamanho varia conforme convênio):**
- Convênio 8 dígitos: máximo 9 dígitos
- Convênio 7 dígitos: máximo 10 dígitos
- Convênio 4 dígitos: máximo 7 dígitos
- Convênio 6 dígitos (sem código_servico): máximo 5 dígitos
- Convênio 6 dígitos (com código_servico): máximo 17 dígitos

**Campos Específicos:**
- `codigo_servico` - Código de serviço (opcional, boolean)

**Valores Padrão:**
- `carteira`: '18'
- `local_pagamento`: 'PAGÁVEL EM QUALQUER BANCO.'

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`

---

### Sicoob (756)

**Validações de Tamanho:**
- `agencia`: máximo 4 dígitos
- `conta_corrente`: máximo 8 dígitos
- `nosso_numero`: máximo 7 dígitos
- `convenio`: máximo 7 dígitos
- `variacao`: máximo 2 dígitos
- `quantidade`: máximo 3 dígitos

**Campos Específicos (Obrigatórios):**
- `variacao` - Variação da modalidade (padrão: '01')
- `quantidade` - Quantidade (padrão: '001')

**Valores Padrão:**
- `carteira`: '1'
- `variacao`: '01'
- `quantidade`: '001'

**Campos Opcionais:**
- `codigo_beneficiario` - Código do beneficiário (se aplicável)

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`

---

### Sicredi (748)

**Validações de Tamanho:**
- `agencia`: máximo 4 dígitos
- `conta_corrente`: máximo 5 dígitos
- `nosso_numero`: máximo 5 dígitos
- `carteira`: máximo 1 dígito
- `convenio`: máximo 5 dígitos
- `posto`: máximo 2 dígitos
- `byte_idt`: exatamente 1 caractere

**Campos Específicos (Obrigatórios):**
- `posto` - Código do posto (obrigatório)
- `byte_idt` - Byte de identificação (obrigatório, geralmente '2' para geração pelo beneficiário)

**Valores Padrão:**
- `carteira`: '3' (sem registro)
- `especie_documento`: 'A'

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`

---

### Itaú (341)

**Validações de Tamanho:**
- `agencia`: máximo 4 dígitos
- `conta_corrente`: máximo 5 dígitos
- `convenio`: máximo 5 dígitos
- `nosso_numero`: máximo 8 dígitos
- `seu_numero`: máximo 7 dígitos (condicional)

**Campos Específicos:**
- `seu_numero` - Obrigatório para carteiras: 198, 106, 107, 122, 142, 143, 195, 196

**Valores Padrão:**
- `carteira`: '175'

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`
- ✅ `seu_numero` (para carteiras específicas)

---

### Bradesco (237)

**Validações de Tamanho:**
- `agencia`: máximo 4 dígitos
- `conta_corrente`: máximo 7 dígitos
- `nosso_numero`: máximo 11 dígitos
- `carteira`: máximo 2 dígitos

**Valores Padrão:**
- `carteira`: '06'
- `local_pagamento`: 'Pagável preferencialmente na Rede Bradesco ou Bradesco Expresso'

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`

---

### Caixa Econômica Federal (104)

**Validações de Tamanho:**
- `emissao`: exatamente 1 dígito
- `carteira`: exatamente 1 dígito
- `convenio`: exatamente 6 dígitos (código do cedente)
- `nosso_numero`: exatamente 15 dígitos

**Campos Específicos (Obrigatórios):**
- `emissao` - Tipo de emissão (padrão: '4' para Beneficiário)
- `codigo_beneficiario` - Código do beneficiário (geralmente igual ao convênio)

**Valores Padrão:**
- `carteira`: '1' (Registrada)
- `carteira_label`: 'RG'
- `emissao`: '4'
- `local_pagamento`: 'PREFERENCIALMENTE NAS CASAS LOTÉRICAS ATÉ O VALOR LIMITE'

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`

---

### Santander (033)

**Validações de Tamanho:**
- `agencia`: máximo 4 dígitos
- `convenio`: máximo 7 dígitos (obrigatório)
- `nosso_numero`: máximo 7 dígitos
- `conta_corrente`: máximo 9 dígitos

**Campos Específicos:**
- `convenio` - Obrigatório, 7 dígitos

**Campos que DEVEM ser enviados:**
- ✅ `documento_numero` / `numero_documento`
- ✅ `aceite`
- ✅ `especie_documento`

---

## Campos que NÃO Causam Erro

Baseado na análise do código-fonte oficial do BRCobranca, **NENHUM** campo da classe Base causa erro quando enviado. Todos os bancos herdam da classe Base e aceitam todos os seus campos.

Os únicos campos que podem causar problemas são:
1. Campos com tamanho EXCEDIDO (ex: nosso_numero > 11 para Bradesco)
2. Campos obrigatórios AUSENTES (ex: posto e byte_idt para Sicredi)
3. Campos específicos com formato INVÁLIDO (ex: emissao != 1 dígito na Caixa)

**IMPORTANTE:** Os campos `documento_numero`, `numero_documento`, `aceite`, e `especie_documento` **DEVEM** ser enviados para TODOS os bancos, pois fazem parte da classe Base.

---

## Recomendações de Implementação

### 1. Enviar Máximo de Campos Possível

**Campos que SEMPRE devem ser enviados quando disponíveis:**
- Todos os campos obrigatórios da classe Base
- `documento_numero` e `numero_documento` (ambos)
- `aceite` (padrão 'S')
- `especie_documento` (padrão 'DM')
- `especie` (padrão 'R$')
- `moeda` (padrão '9')
- Todos os campos de multa, mora e desconto quando configurados
- Todos os campos de instrução quando disponíveis
- Todos os campos específicos do banco quando obrigatórios

### 2. Filtrar Apenas Campos Problemáticos

**Filtrar somente quando:**
- Tamanho excede o máximo permitido pelo banco
- Campo obrigatório está vazio/nulo
- Formato é incompatível com o banco

**NÃO filtrar:**
- Campos opcionais válidos
- Campos da classe Base
- Campos de multa/mora/desconto válidos
- Instruções válidas

### 3. Validações por Banco

Implementar validações específicas para:
- Tamanho máximo de campos numéricos
- Campos obrigatórios específicos do banco
- Formatos especiais (ex: byte_idt do Sicredi)

---

## Fontes e Referências

- **Código-fonte oficial:** https://github.com/kivanio/brcobranca
- **Classe Base:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/base.rb
- **Sicoob:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/sicoob.rb
- **Sicredi:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/sicredi.rb
- **Banco do Brasil:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/banco_brasil.rb
- **Itaú:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/itau.rb
- **Bradesco:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/bradesco.rb
- **Caixa:** https://github.com/kivanio/brcobranca/blob/master/lib/brcobranca/boleto/caixa.rb
- **API boleto_cnab_api:** https://github.com/akretion/boleto_cnab_api

---

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Data:** 2025-11-25
