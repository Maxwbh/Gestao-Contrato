# Integração com BRCobranca API

Documentação da integração com a API customizada de geração de boletos bancários.

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)

## 🔗 Repositórios Customizados

Este projeto utiliza versões customizadas do BRCobranca mantidas pelo desenvolvedor:

- **API REST:** https://github.com/Maxwbh/boleto_cnab_api
- **Biblioteca Ruby:** https://github.com/Maxwbh/brcobranca

> ⚠️ **IMPORTANTE:** Use APENAS estes repositórios customizados. Não use os forks originais (akretion/kivanio).

## 🏦 Bancos Suportados

A API suporta 17 bancos brasileiros:

| Código | Banco | Observações |
|--------|-------|-------------|
| 001 | Banco do Brasil | Convênio obrigatório (4-8 dígitos) |
| 004 | Banco do Nordeste | - |
| 021 | Banestes | - |
| 033 | Santander | Convênio obrigatório (7 dígitos) |
| 041 | Banrisul | - |
| 070 | BRB | - |
| 077 | Banco Inter | - |
| 084 | Unicred | - |
| 085 | Ailos | - |
| 104 | Caixa Econômica Federal | Código beneficiário obrigatório |
| 133 | Cresol | - |
| 136 | Unicred | - |
| 237 | Bradesco | - |
| 341 | Itaú | - |
| 389 | Banco Mercantil | - |
| 422 | Safra | - |
| 748 | Sicredi | Posto e byte_idt obrigatórios |
| 756 | Sicoob | - |

## 📡 Endpoints da API

### 1. Gerar Boleto (PDF/PNG/JPG/TIF)

```http
GET /api/boleto?bank={nome_banco}&type={formato}&data={json_stringified}
```

**Parâmetros:**
- `bank`: Nome do banco (ex: 'banco_brasil', 'sicoob', 'santander')
- `type`: Formato de saída ('pdf', 'png', 'jpg', 'tif')
- `data`: JSON stringificado com dados do boleto

**Exemplo de chamada:**

```python
import json
import requests

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
}

params = {
    'bank': 'banco_brasil',
    'type': 'pdf',
    'data': json.dumps(boleto_data)
}

response = requests.get('https://brcobranca-api.onrender.com/api/boleto', params=params)

if response.status_code == 200:
    pdf_content = response.content  # Conteúdo binário do PDF
else:
    error = response.json()
    print(f"Erro: {error}")
```

### 2. Obter Dados Opcionais do Boleto

```http
GET /api/boleto/data?bank={nome_banco}&data={json_stringified}
```

Retorna informações adicionais como `nosso_numero` gerado pela API (útil para alguns bancos que geram automaticamente).

## ⚠️ Campo numero_documento vs documento_numero

**CRÍTICO:** O BRCobranca gem aceita **APENAS `documento_numero`**.

❌ **ERRO - NÃO USAR:**
```python
{
    'numero_documento': 'CTR-2023-001',  # Causa erro 500!
    'documento_numero': 'CTR-2023-001'
}
```

✅ **CORRETO - USAR:**
```python
{
    'documento_numero': 'CTR-2023-001'  # Apenas este campo
}
```

### Correção Implementada

O sistema filtra automaticamente o campo `numero_documento` antes de enviar para a API. Veja em:
- `financeiro/services/boleto_service.py` linha 115-205 (`CAMPOS_NAO_SUPORTADOS`)

## 📋 Campos Obrigatórios

Todos os boletos devem ter no mínimo:

```python
{
    # Beneficiário
    'cedente': str,
    'documento_cedente': str,  # CNPJ/CPF

    # Pagador
    'sacado': str,
    'sacado_documento': str,  # CPF/CNPJ

    # Bancários
    'agencia': str,
    'conta_corrente': str,
    'carteira': str,

    # Valores
    'valor': float,
    'data_vencimento': str,  # formato YYYY/MM/DD

    # Base (sempre enviar)
    'moeda': '9',
    'especie': 'R$',
    'especie_documento': 'DM',
    'aceite': 'S' ou 'N',
}
```

## 🔍 Campos Específicos por Banco

### Banco do Brasil (001)
```python
{
    'convenio': str,  # 4-8 dígitos - OBRIGATÓRIO
    'codigo_servico': bool,  # opcional
}
```

### Santander (033)
```python
{
    'convenio': str,  # 7 dígitos - OBRIGATÓRIO
}
```

### Caixa (104)
```python
{
    'codigo_beneficiario': str,  # OBRIGATÓRIO
    'emissao': '1',  # 1 dígito - OBRIGATÓRIO
}
```

### Sicredi (748)
```python
{
    'posto': str,  # 2 dígitos - OBRIGATÓRIO
    'byte_idt': str,  # 1 dígito - OBRIGATÓRIO
}
```

### Sicoob (756)
```python
{
    'variacao': str,  # 2 dígitos - opcional
}
```

## 📖 Referências Completas

Para detalhes completos de todos os campos por banco, consulte:
- `BRCOBRANCA_CAMPOS_REFERENCIA.md` - Lista completa de campos
- `VALIDACAO_API_CUSTOMIZADA.md` - Validações da API customizada

## 🐛 Troubleshooting

### Erro 500 - NoMethodError

**Problema:** `undefined method 'numero_documento='`

**Solução:** Remove o campo `numero_documento` dos dados. Use apenas `documento_numero`.

### Erro 400 - Campos obrigatórios ausentes

**Solução:** Verifique se todos os campos obrigatórios do banco estão presentes.

### Timeout

**Solução:** A API no Render free tier pode demorar ~10s na primeira requisição (cold start).

## 🔗 Links Úteis

- **Exemplos de uso:** https://github.com/Maxwbh/boleto_cnab_api/blob/master/EXEMPLOS_MAXIMO_CAMPOS.md
- **Código da API:** https://github.com/Maxwbh/boleto_cnab_api
- **Gem BRCobranca:** https://github.com/Maxwbh/brcobranca

## 📝 Notas de Implementação

O serviço `BoletoService` em `financeiro/services/boleto_service.py` implementa:
- ✅ Retry automático com backoff exponencial (3 tentativas)
- ✅ Filtragem automática de campos não suportados por banco
- ✅ Validação de campos obrigatórios
- ✅ Logging detalhado de erros
- ✅ Cache de configurações

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
