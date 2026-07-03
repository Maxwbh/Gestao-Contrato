# Integração com BRCobranca API

Documentação da integração com a API customizada de geração de boletos bancários.

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)

---

## 🔗 Repositórios Customizados

Este projeto utiliza versões customizadas do BRCobranca mantidas pelo desenvolvedor:

| Componente | Repositório | Versão atual |
|-----------|------------|--------------|
| **API REST** | https://github.com/Maxwbh/boleto_cnab_api | v1.3.0 (PR #45: brcobrança 12.8.1) |
| **Biblioteca Ruby** | https://github.com/Maxwbh/brcobranca | v12.8.1 |

> ⚠️ **IMPORTANTE:** Use APENAS estes repositórios customizados. Não use os forks originais (`akretion/boleto_cnab_api` ou `kivanio/brcobranca`).

---

## 🏦 Bancos Suportados (18)

| Código | Banco | Boleto | Remessa | Retorno | PIX | Observações |
|--------|-------|--------|---------|---------|-----|-------------|
| 001 | Banco do Brasil | ✅ | 240 + 400 | 400 | ✅ | Convênio obrigatório (4–8 dígitos) |
| 004 | Banco do Nordeste | ✅ | 400 | — | — | — |
| 021 | Banestes | ✅ | — | — | — | — |
| 033 | Santander | ✅ | 240 + 400 | 240 + 400 | ✅ | Convênio obrigatório (7 dígitos) |
| 041 | Banrisul | ✅ | 400 | 400 | — | — |
| 070 | BRB – Banco de Brasília | ✅ | 400 | — | — | — |
| 085 | Ailos (Cecred) | ✅ | 240 | — | — | — |
| 097 | Credisis | ✅ | 400 | — | — | — |
| 104 | Caixa Econômica Federal | ✅ | 240 | 240 | ✅ | `codigo_beneficiario` obrigatório |
| 136 | Unicred | ✅ | 240 + 400 | 400 | — | — |
| 237 | Bradesco | ✅ | 400 | 400 | ✅ | Apenas CNAB 400 |
| 336 | **C6 Bank** | ✅ | 400 | 400 | ✅ | Carteiras 10/20; convênio (12 díg.) obrigatório |
| 341 | Itaú | ✅ | 400 + 444 | 400 | ✅ | — |
| 389 | Banco Mercantil | ✅ | — | — | — | — |
| 422 | Safra | ✅ | — | — | — | — |
| 748 | Sicredi | ✅ | 240 | 240 | ✅ | `posto` e `byte_idt` obrigatórios |
| 756 | Sicoob | ✅ | 240 + 400 | 240 | — | Carteira 9 usa `numero_contrato`; layout 810 disponível |
| 745 | Citibank | ✅ | 400 | — | — | — |

> Consulte `GET /api/bancos` para a matriz completa e atualizada em tempo real.

---

## 📡 Endpoints da API (15)

| Endpoint | Método | Função |
|----------|--------|--------|
| `/api/health` | GET | Health check do serviço |
| `/api/info` | GET | Versão e configuração |
| `/api/metadata` | GET | Metadados da API e da gem |
| `/api/bancos` | GET | Capacidades por banco (boleto, CNAB, PIX, carteiras) |
| `/api/boleto/validate` | GET | Validar dados de boleto sem gerar |
| `/api/boleto/data` | GET | Campos calculados: nosso_número, código de barras, linha digitável |
| `/api/boleto/nosso_numero` | GET | Apenas o nosso número calculado |
| `/api/boleto` | GET | Gerar boleto (PDF/JPG/PNG/TIF); `include_data=true` retorna JSON + base64 |
| `/api/boleto/multi` | POST | Múltiplos boletos em um arquivo |
| `/api/remessa` | POST | Arquivo CNAB 240/400; `pix=true` inclui segmento PIX |
| `/api/retorno` | POST | Processar arquivo de retorno CNAB → JSON |
| `/api/ofx/parse` | POST | Parsear extrato OFX → JSON com `nosso_numero_extraido` |
| `/api/docs` | GET | Swagger UI interativo |
| `/api/openapi.json` | GET | Spec OpenAPI 3.0 (JSON) |
| `/api/openapi.yaml` | GET | Spec OpenAPI 3.0 (YAML) |

### 1. Gerar Boleto (`GET /api/boleto`)

```python
import json, requests

boleto_data = {
    # Beneficiário (Cedente)
    'cedente': 'Imobiliária Sete Colinas Negócios Imobiliários LTDA',
    'documento_cedente': '23456781000111',
    'cedente_endereco': 'Rua Monsenhor Messias, 250',

    # Pagador (Sacado)
    'sacado': 'João da Silva',
    'sacado_documento': '12345678901',
    'sacado_endereco': 'Rua das Flores, 123, Centro, São Paulo, SP, 01000-000',

    # Dados Bancários
    'agencia': '1234',
    'conta_corrente': '56789',
    'convenio': '0123456',
    'carteira': '18',

    # Identificação
    'nosso_numero': '1',
    'documento_numero': 'CTR-2023-001-001/012',  # USAR APENAS documento_numero

    # Valores e Datas
    'valor': 1000.00,
    'data_vencimento': '2025/12/31',
    'data_documento': '2025/11/26',

    # Campos obrigatórios da classe Base
    'moeda': '9',
    'especie': 'R$',
    'especie_documento': 'DM',
    'aceite': 'N',

    # Instruções
    'local_pagamento': 'Pagável em qualquer banco até o vencimento',
    'instrucao1': 'Não receber após o vencimento',
    'instrucao2': 'Multa de 2% após o vencimento',

    # Juros e Multa (opcional)
    'percentual_multa': 2.0,
    'percentual_juros': 0.033,  # 1% ao mês = 0.033% ao dia

    # PIX híbrido (opcional — ver seção PIX)
    # 'chave_pix': 'pix@imobiliaria.com.br',
    # 'tipo_chave_pix': 'email',
    # 'txid': 'ABC123XYZ456',
}

response = requests.get(
    'http://localhost:9292/api/boleto',
    params={'bank': 'banco_brasil', 'type': 'pdf', 'data': json.dumps(boleto_data)}
)

if response.status_code == 200:
    pdf_content = response.content  # Conteúdo binário do PDF
else:
    print(f"Erro {response.status_code}: {response.json()}")
```

### 2. Campos Calculados (`GET /api/boleto/data`)

Retorna `nosso_numero`, `codigo_barras`, `linha_digitavel` e `dados_pix` (quando PIX habilitado) sem gerar o PDF. Útil para salvar metadados antes de emitir o PDF.

### 3. Listar Capacidades dos Bancos (`GET /api/bancos`)

```python
resp = requests.get('http://localhost:9292/api/bancos')
bancos = resp.json()['bancos']
# Retorna: [{ codigo, nome, boleto, cnab, pix, carteiras }, ...]
```

### 4. Remessa CNAB (`POST /api/remessa`)

```python
payload = {
    'empresa_mae': 'Imobiliária Lagoa Real LTDA',
    'documento_cedente': '23456780000110',
    'agencia': '3073',
    'conta_corrente': '12345678',
    'digito_conta': '9',
    'convenio': '12345678',
    'carteira': '18',
    'sequencial_remessa': 1,
    'pagamentos': [{ ... }],
}

resp = requests.post(
    'http://localhost:9292/api/remessa',
    params={'bank': 'banco_brasil', 'type': 'cnab240'},
    files={'data': ('remessa.json', json.dumps(payload).encode('utf-8'), 'application/json')},
    headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
)
# resp.content → arquivo CNAB bruto (text/plain, latin-1)
```

> **PIX na remessa:** adicione `pix=true` nos query params para incluir segmento PIX. Requer `chave_pix` nos dados da empresa.

### 5. Parsear OFX (`POST /api/ofx/parse`)

```python
with open('extrato.ofx', 'rb') as f:
    resp = requests.post(
        'http://localhost:9292/api/ofx/parse',
        files={'file': ('extrato.ofx', f, 'application/octet-stream')},
        data={'somente_creditos': 'false'},
    )

transacoes = resp.json()['transacoes']
# Cada transação: { fitid, tipo, data, valor, memo,
#                   nosso_numero_extraido (bank-specific) }
```

---

## ⚠️ Campo `numero_documento` vs `documento_numero`

**CRÍTICO:** O BRCobranca gem aceita **APENAS `documento_numero`** em vários bancos.

❌ **ERRO:**
```python
{ 'numero_documento': 'CTR-2023-001' }   # NoMethodError → HTTP 400
```

✅ **CORRETO:**
```python
{ 'documento_numero': 'CTR-2023-001' }
```

O `BoletoService` filtra automaticamente `numero_documento` para os bancos que o rejeitam. Veja `financeiro/services/boleto_service.py` → `CAMPOS_NAO_SUPORTADOS`.

---

## 💡 PIX Híbrido (Boleto + PIX)

Campos opcionais adicionados ao `Brcobranca::Boleto::Base` na v12.8.0:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `chave_pix` | str | Chave PIX do recebedor (CPF, CNPJ, e-mail, celular, aleatória) |
| `tipo_chave_pix` | str | Tipo da chave: `'cpf'`, `'cnpj'`, `'email'`, `'celular'`, `'aleatoria'` |
| `txid` | str | ID da transação PIX (máx. 35 caracteres alfanuméricos) |

O boleto retorna adicionalmente:

| Campo (resposta) | Descrição |
|-----------------|-----------|
| `emv` | Código EMV/Pix Copia e Cola gerado pelo brcobrança |
| `qrcode_disponivel` | `true` quando EMV está populado |

**Bancos com suporte a PIX (8):** BB (001), Santander (033), Caixa (104), Bradesco (237), C6 (336), Itaú (341), Sicredi (748).

**Exemplo:**
```python
boleto_data = {
    ...
    'chave_pix': 'pix@imobiliaria.com.br',
    'tipo_chave_pix': 'email',
    'txid': 'CTRPAY20261231001001',
}
```

---

## 🔍 Campos Específicos por Banco

### Banco do Brasil (001)
```python
{
    'convenio': str,  # 4–8 dígitos — OBRIGATÓRIO
    # codigo_servico: bool  (opcional)
}
# Remessa: variacao_carteira = carteira zero-padded 3 dígitos
```

### Santander (033)
```python
{
    'convenio': str,  # 7 dígitos — OBRIGATÓRIO
}
```

### Caixa Econômica Federal (104)
```python
{
    'codigo_beneficiario': str,  # OBRIGATÓRIO
    'emissao': '4',              # 1 dígito — OBRIGATÓRIO (4 = pelo beneficiário)
    'convenio': str,             # 6 dígitos (igual ao codigo_beneficiario)
}
```

### Bradesco (237)
```python
{
    # Apenas CNAB 400
    # Remessa usa 'codigo_empresa' (= convenio da conta)
    'nosso_numero': str,  # máx. 11 dígitos
    'carteira': '06',     # padrão
}
```

### C6 Bank (336) — *novo em v12.8.0*
```python
{
    'convenio': str,   # código do beneficiário, até 12 dígitos — OBRIGATÓRIO
    'carteira': str,   # '10' (emissão banco) ou '20' (emissão cliente) — OBRIGATÓRIO
    'nosso_numero': str,  # exatamente 10 dígitos (DV módulo 11 calculado internamente)
}
# Remessa CNAB 400: campo enviado como 'codigo_beneficiario' (não 'convenio')
# O CNABService faz o mapeamento automaticamente.
```

### Sicoob (756)
```python
{
    'convenio': str,    # máx. 7 dígitos
    'carteira': str,    # '1', '3' ou '9'
    'variacao': '01',   # 2 dígitos (padrão: '01')

    # Carteira 9 — usa número do contrato no lugar do código cedente:
    'numero_contrato': str,  # obrigatório quando carteira == '9'

    # CNAB 240 Layout 810 (opcional):
    # Enviar 'layout': '810' nos dados de remessa
}
```

### Sicredi (748)
```python
{
    'posto': str,     # 2 dígitos — OBRIGATÓRIO
    'byte_idt': '2',  # 1 dígito — OBRIGATÓRIO
    'nosso_numero': str,  # máx. 5 dígitos
}
```

### Itaú (341)
```python
{
    'seu_numero': str,  # máx. 7 dígitos — obrigatório para carteiras 198, 106, 107, 122, 142, 143, 195, 196
    'nosso_numero': str,  # máx. 8 dígitos
}
```

---

## 📋 Campos Base (Comuns a Todos os Bancos)

```python
{
    # Obrigatórios
    'cedente': str,
    'documento_cedente': str,       # CNPJ/CPF sem formatação
    'sacado': str,
    'sacado_documento': str,        # CPF/CNPJ sem formatação
    'agencia': str,
    'conta_corrente': str,
    'carteira': str,
    'nosso_numero': str,
    'valor': float,
    'data_vencimento': str,         # formato 'YYYY/MM/DD'
    'moeda': '9',                   # sempre '9' para Real
    'especie': 'R$',
    'especie_documento': 'DM',
    'aceite': 'N',                  # ou 'S'

    # Opcionais frequentes
    'documento_numero': str,        # USAR APENAS ESTE (não numero_documento)
    'data_documento': str,          # 'YYYY/MM/DD'
    'cedente_endereco': str,
    'sacado_endereco': str,
    'local_pagamento': str,
    'instrucao1': str,
    'instrucao2': str,
    'percentual_multa': float,      # ex: 2.0 (= 2%)
    'percentual_juros': float,      # ex: 0.033 (= 1% a.m. / 30)

    # PIX (opcional — ver seção PIX)
    'chave_pix': str,
    'tipo_chave_pix': str,
    'txid': str,
}
```

---

## 🐛 Troubleshooting

### Erro HTTP 400 — NoMethodError (a partir da v1.3.0 / PR #45)

**Antes:** campo inválido causava `NoMethodError` → HTTP 500.  
**Agora:** `RemessaService` captura `NoMethodError` e retorna HTTP **400** com mensagem descritiva.

**Causa comum:** campo específico do banco enviado para banco errado (ex: `codigo_beneficiario` enviado para BB).

### Erro HTTP 400 — Campos obrigatórios ausentes

Verifique se todos os campos obrigatórios do banco estão presentes. Use `GET /api/boleto/validate` para diagnóstico sem gerar o arquivo.

### Erro HTTP 422 — Validação do brcobrança

O brcobrança valida tamanhos e formatos. Exemplos comuns:
- `nosso_numero` do C6 com ≠ 10 dígitos
- `carteira` do C6 fora de `['10', '20']`
- `sequencial_remessa` do Sicoob com ≠ 7 dígitos (deve ser string)
- `convenio` do Santander com ≠ 7 dígitos

### Timeout / Cold Start

A API no Render Free Tier pode demorar ~10–15s na primeira requisição. O `BoletoService` implementa retry automático com backoff exponencial (3 tentativas).

---

## 🔗 Links Úteis

- **Swagger UI:** `GET /api/docs` (quando o serviço está rodando)
- **Spec OpenAPI:** `GET /api/openapi.yaml`
- **Campos por banco (referência):** `docs/api/BRCOBRANCA_CAMPOS_REFERENCIA.md`
- **Validações customizadas:** `docs/api/VALIDACAO_API_CUSTOMIZADA.md`
- **Repositório API:** https://github.com/Maxwbh/boleto_cnab_api
- **Gem brcobrança:** https://github.com/Maxwbh/brcobranca

---

## 📝 Notas de Implementação

O serviço `BoletoService` (`financeiro/services/boleto_service.py`) implementa:

- ✅ Retry automático com backoff exponencial (3 tentativas, delay inicial 2s)
- ✅ Filtragem automática de campos não suportados por banco (`CAMPOS_NAO_SUPORTADOS`)
- ✅ Validação de campos obrigatórios antes de chamar a API
- ✅ Normalização de campos numéricos por banco (nosso número, convênio, etc.)
- ✅ Mapeamento `convenio` → `codigo_beneficiario` para C6 em remessa
- ✅ Logging detalhado (INFO para remessa, WARNING para erros de conectividade)
- ✅ Suporte a PIX híbrido (`chave_pix`, `tipo_chave_pix`, `txid`) — passados direto ao brcobrança

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)  
**Empresa:** M&S do Brasil LTDA  
**Atualizado em:** 2026-05-29 (brcobrança 12.8.1 / boleto_cnab_api PR #45)
