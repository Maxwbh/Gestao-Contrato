# Validação Completa - API Customizada Maxwell

**Data:** 2025-11-25
**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA

---

## ✅ Repositórios Oficiais Validados

**USAR EXCLUSIVAMENTE:**
- **API Server:** https://github.com/Maxwbh/boleto_cnab_api
- **Gem BRCobrança:** https://github.com/Maxwbh/brcobranca

**IGNORAR forks originais:**
- ~~https://github.com/akretion/boleto_cnab_api~~
- ~~https://github.com/kivanio/brcobranca~~

---

## 📋 Endpoints da API Customizada

### 1. **Gerar Boleto (PDF)** ✅ VALIDADO

```
GET /api/boleto
```

**Parâmetros:**
- `bank` (String): Nome do banco (ex: 'sicoob', 'banco_brasil')
- `type` (String): Formato de saída (pdf|jpg|png|tif)
- `data` (String): JSON stringificado com TODOS os dados do boleto

**Retorno:** Arquivo binário (PDF/imagem)

**Implementação no código:**
```python
url = f"{self.brcobranca_url}/api/boleto"
params = {
    'bank': banco_nome,
    'type': 'pdf',
    'data': json.dumps(boleto_data)
}
response = requests.get(url, params=params, timeout=self.timeout)
```

**Status:** ✅ CORRETO
**Arquivo:** `financeiro/services/boleto_service.py:812`
**Commit:** `af8ec84`

---

### 2. **Obter Dados do Boleto (JSON)** ✅ VALIDADO

```
GET /api/boleto/data
```

**Parâmetros:**
- `bank` (String): Nome do banco
- `data` (String): JSON stringificado

**Retorno (JSON):**
- `codigo_barras` - Código de barras do boleto
- `linha_digitavel` - Linha digitável formatada
- `nosso_numero` - Nosso número com DV calculado
- `agencia_conta_boleto` - Agência/conta formatada
- Todos os demais dados do boleto

**Implementação no código:**
```python
url = f"{self.brcobranca_url}/api/boleto/data"
params = {
    'bank': banco_nome,
    'data': json.dumps(dados_boleto)
}
response = requests.get(url, params=params, timeout=10)
```

**Status:** ✅ CORRETO
**Arquivo:** `financeiro/services/boleto_service.py:1093`
**Commit:** `af8ec84`

---

### 3. **Obter Nosso Número**

```
GET /api/boleto/nosso_numero
```

**Status:** Endpoint disponível mas não utilizado (usando /api/boleto/data)

---

### 4. **Validar Dados**

```
GET /api/boleto/validate
```

**Status:** Endpoint disponível mas não utilizado

---

### 5. **Health Check**

```
GET /api/health
```

**Retorno:** `{"status":"OK"}`

**Status:** Disponível para monitoramento

---

## 🏦 Bancos Suportados (16 bancos)

| Banco | Código | Nome API | Status |
|-------|--------|----------|--------|
| Banco do Brasil | 001 | banco_brasil | ✅ |
| Banco do Nordeste | 004 | banco_nordeste | ✅ |
| Banestes | 021 | banestes | ✅ |
| Santander | 033 | santander | ✅ |
| Banrisul | 041 | banrisul | ✅ |
| Banco de Brasília | 070 | brb | ✅ |
| AILOS | 085 | ailos | ✅ |
| CREDISIS | 097 | credisis | ✅ |
| Caixa | 104 | caixa | ✅ |
| Unicred | 136 | unicred | ✅ |
| Bradesco | 237 | bradesco | ✅ |
| Itaú | 341 | itau | ✅ |
| Banco Mercantil | 389 | banco_mercantil | ✅ |
| HSBC | 399 | hsbc | ✅ |
| Citibank | 745 | citibank | ✅ |
| Sicredi | 748 | sicredi | ✅ |
| **Sicoob** | **756** | **sicoob** | ✅ **TESTADO** |

---

## 📦 Estrutura de Dados Enviada

### Campos Obrigatórios da Classe Base (SEMPRE enviados)

```python
boleto_data = {
    # Beneficiário (Cedente)
    'cedente': 'Nome da Empresa',
    'documento_cedente': '12345678000190',

    # Pagador (Sacado)
    'sacado': 'Nome do Cliente',
    'sacado_documento': '12345678901',
    'sacado_endereco': 'Rua, Nro, Bairro, Cidade, UF, CEP',

    # Dados Bancários
    'agencia': '4327',
    'conta_corrente': '417270',
    'convenio': '229385',
    'carteira': '1',

    # Identificação do Boleto
    'nosso_numero': '0000001',
    'numero_documento': 'CONTRATO-1/10',
    'documento_numero': 'CONTRATO-1/10',  # Alias

    # Valores e Datas (formato YYYY/MM/DD)
    'valor': 1500.50,
    'data_vencimento': '2025/12/24',

    # Campos Padrão da Base (OBRIGATÓRIOS)
    'moeda': '9',           # Real
    'especie': 'R$',        # Símbolo da moeda
    'aceite': 'S',          # Aceite (S/N)
    'especie_documento': 'DM',  # Duplicata Mercantil

    # Informações e Instruções
    'local_pagamento': 'Pagavel em qualquer banco',
    'instrucao1': 'Não receber após vencimento',
    'instrucao2': 'Juros de 2% ao mês',
    'instrucao3': 'Multa de 2% após vencimento',
    'instrucao4': 'Contrato: XXX',
}
```

### Campos Opcionais Sicoob (756)

```python
# Campos específicos Sicoob
'variacao': '01',       # Variação da modalidade (2 dígitos)
'quantidade': '001',    # Quantidade (3 dígitos)
'codigo_beneficiario': None,  # Opcional

# Campos adicionais aceitos
'data_documento': '2025/11/24',
'data_processamento': '2025/11/24',
'cedente_endereco': 'Endereço da empresa',

# Multa
'codigo_multa': '2',        # 1=valor fixo, 2=percentual
'percentual_multa': 2.0,    # 2%
'data_multa': '2025/12/25',

# Juros/Mora
'codigo_mora': '2',         # 1=valor diário, 2=taxa mensal
'percentual_mora': 2.0,     # 2% ao mês
'data_mora': '2025/12/25',

# Desconto
'desconto': 10.00,          # Valor do desconto
'data_desconto': '2025/12/20',

# Instruções adicionais
'instrucao5': '',
'instrucao6': '',
'instrucao7': '',

# Avalista
'avalista': 'Nome do Avalista',
'avalista_documento': '12345678901',
```

---

## ✅ Validação dos Campos Enviados

### Campos da Classe Base (TODOS aceitos por TODOS os bancos)

| Campo | Status | Tipo | Observação |
|-------|--------|------|------------|
| cedente | ✅ ENVIADO | String | Nome do beneficiário |
| documento_cedente | ✅ ENVIADO | String | CPF/CNPJ sem formatação |
| sacado | ✅ ENVIADO | String | Nome do pagador |
| sacado_documento | ✅ ENVIADO | String | CPF/CNPJ sem formatação |
| sacado_endereco | ✅ ENVIADO | String | Endereço completo (máx 80 chars) |
| agencia | ✅ ENVIADO | String | Sem DV, zerofill conforme banco |
| conta_corrente | ✅ ENVIADO | String | Sem DV, zerofill conforme banco |
| convenio | ✅ ENVIADO | String | Código do convênio |
| carteira | ✅ ENVIADO | String | Tipo de carteira |
| nosso_numero | ✅ ENVIADO | String | Zerofill 7 dígitos (Sicoob) |
| numero_documento | ✅ ENVIADO | String | CONTRATO-PARCELA/TOTAL |
| documento_numero | ✅ ENVIADO | String | Alias de numero_documento |
| valor | ✅ ENVIADO | Float | Valor do boleto |
| data_vencimento | ✅ ENVIADO | String | Formato YYYY/MM/DD |
| **moeda** | ✅ ENVIADO | String | **Padrão '9' (Real)** |
| **especie** | ✅ ENVIADO | String | **Padrão 'R$'** |
| **aceite** | ✅ ENVIADO | String | **Padrão 'S'** |
| **especie_documento** | ✅ ENVIADO | String | **Padrão 'DM'** |
| local_pagamento | ✅ ENVIADO | String | Texto do local de pagamento |
| instrucao1-4 | ✅ ENVIADO | String | Instruções no boleto |

### Campos Específicos Sicoob (756)

| Campo | Status | Obrigatório | Validação | Observação |
|-------|--------|-------------|-----------|------------|
| variacao | ✅ ENVIADO | Sim | 2 dígitos | Padrão '01' |
| quantidade | ✅ ENVIADO | Não | 3 dígitos | Padrão '001' |
| codigo_beneficiario | ✅ ENVIADO | Não | - | Quando aplicável |

### Campos de Multa/Juros/Desconto

| Campo | Status | Condição | Tipo |
|-------|--------|----------|------|
| codigo_multa | ✅ ENVIADO | Se configurado | 1 ou 2 |
| percentual_multa | ✅ ENVIADO | Se tipo=2 | Float |
| valor_multa | ✅ ENVIADO | Se tipo=1 | Float |
| data_multa | ✅ ENVIADO | Se configurado | YYYY/MM/DD |
| codigo_mora | ✅ ENVIADO | Se configurado | 1 ou 2 |
| percentual_mora | ✅ ENVIADO | Se tipo=2 | Float |
| valor_mora | ✅ ENVIADO | Se tipo=1 | Float |
| data_mora | ✅ ENVIADO | Se configurado | YYYY/MM/DD |
| desconto | ✅ ENVIADO | Se configurado | Float |
| data_desconto | ✅ ENVIADO | Se configurado | YYYY/MM/DD |

---

## 🎯 Resumo da Validação

### ✅ CORRETO - Endpoints

1. **Geração de boleto:** `GET /api/boleto` ✅
2. **Obter dados:** `GET /api/boleto/data` ✅
3. **Formato JSON stringificado:** ✅
4. **Parâmetros bank, type, data:** ✅

### ✅ CORRETO - Campos

1. **Campos obrigatórios da Base:** TODOS enviados ✅
2. **Campos específicos Sicoob:** variacao, quantidade ✅
3. **Campos opcionais:** ~45+ campos quando disponíveis ✅
4. **Formato de datas:** YYYY/MM/DD ✅
5. **Valores numéricos:** Float/Integer ✅

### ✅ CORRETO - Documentação

1. **Referências à API customizada:** ✅
2. **Referências ao repositório Maxwell:** ✅
3. **EXEMPLOS_MAXIMO_CAMPOS.md:** Referenciado ✅
4. **Comentários inline atualizados:** ✅

---

## 📝 Commits Finais

1. **af8ec84** - Corrige endpoint de dados opcionais para API customizada ⭐
2. **6ca8410** - Corrige endpoint da API para usar repositório customizado ⭐
3. **74be3ad** - Atualiza endpoint para obter dados opcionais do boleto
4. **f22aff7** - Corrige método HTTP para geração de boleto
5. **6a0b202** - Documenta e valida campos BRCobranca por banco
6. **d29ba75** - Implementa captura do nosso_numero retornado pela API

Todos os commits atribuídos a: **Maxwell da Silva Oliveira** (maxwbh@gmail.com)

---

## 🚀 Status Final

**API Validada:** ✅ 100% conforme repositório customizado Maxwell
**Endpoints Corretos:** ✅ `/api/boleto` e `/api/boleto/data`
**Campos Maximizados:** ✅ 45+ campos enviados quando disponíveis
**Documentação Completa:** ✅ Toda referência aos repos customizados
**Commits Atribuídos:** ✅ Maxwell da Silva Oliveira

---

## 📚 Referências Oficiais (API Customizada Maxwell)

- **API Server:** https://github.com/Maxwbh/boleto_cnab_api
- **Gem BRCobrança:** https://github.com/Maxwbh/brcobranca
- **Exemplos de Uso:** https://github.com/Maxwbh/boleto_cnab_api/blob/master/EXEMPLOS_MAXIMO_CAMPOS.md
- **Documentação Local:** `docs/BRCOBRANCA_CAMPOS_REFERENCIA.md`

---

**Validação completa concluída em:** 2025-11-25
**Sistema pronto para testes de geração de boletos!** ✅
