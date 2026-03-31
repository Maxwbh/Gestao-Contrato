# Correção Necessária na API boleto_cnab_api

**Data:** 2025-11-25
**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA

---

## 🔴 PROBLEMA IDENTIFICADO

### Erro Atual:
```ruby
NoMethodError: undefined method `numero_documento='
for #<Brcobranca::Boleto::BancoBrasil:0x0000784f93e323e8>
```

### Análise:
A API **boleto_cnab_api** está recebendo o campo `numero_documento` no JSON, mas a gem **BRCobranca** aceita apenas `documento_numero`.

### Request enviado pelo Django:
```json
{
  "numero_documento": "CTR-2023-0012-017/017",
  "documento_numero": "CTR-2023-0012-017/017"
}
```

### O que acontece:
1. ✅ Django envia ambos os campos (`numero_documento` e `documento_numero`)
2. ❌ API tenta passar `numero_documento` para a gem BRCobranca
3. ❌ Gem BRCobranca rejeita com `NoMethodError`

---

## 🛠️ CORREÇÃO NECESSÁRIA

### Repositório: https://github.com/Maxwbh/boleto_cnab_api

### Arquivo a corrigir: `lib/api.rb` (ou similar)

### Localização do código:

Procurar onde os dados JSON são processados e passados para a gem BRCobranca:

```ruby
# CÓDIGO ATUAL (PROBLEMA):
# O código está tentando passar numero_documento diretamente
boleto_data.each do |key, value|
  boleto.send("#{key}=", value)  # ERRO aqui quando key = 'numero_documento'
end
```

### Solução 1: Mapeamento de campos

```ruby
# ANTES de passar para a gem BRCobranca, mapear os campos:
FIELD_MAPPING = {
  'numero_documento' => 'documento_numero',  # Mapear para o nome correto
  # Adicionar outros mapeamentos se necessário
}

boleto_data.each do |key, value|
  mapped_key = FIELD_MAPPING[key] || key
  boleto.send("#{mapped_key}=", value) if boleto.respond_to?("#{mapped_key}=")
end
```

### Solução 2: Normalizar entrada

```ruby
# Normalizar os dados de entrada antes de processar
def normalize_boleto_data(data)
  normalized = data.dup

  # Se receber numero_documento, copiar para documento_numero
  if normalized['numero_documento'] && !normalized['documento_numero']
    normalized['documento_numero'] = normalized['numero_documento']
  end

  # Remover campo não suportado
  normalized.delete('numero_documento')

  normalized
end

# Usar na API:
data = normalize_boleto_data(params[:data])
```

### Solução 3: Filtro de campos aceitos

```ruby
# Definir campos aceitos por cada banco
CAMPOS_ACEITOS = {
  'banco_brasil' => [
    'cedente', 'documento_cedente', 'sacado', 'sacado_documento',
    'agencia', 'conta_corrente', 'convenio', 'carteira',
    'nosso_numero', 'documento_numero',  # USAR documento_numero
    'valor', 'data_vencimento', 'moeda', 'especie',
    'especie_documento', 'aceite', 'local_pagamento',
    'instrucao1', 'instrucao2', 'instrucao3', 'instrucao4',
    # ... outros campos aceitos
  ],
  # ... outros bancos
}

def filter_boleto_fields(bank, data)
  accepted_fields = CAMPOS_ACEITOS[bank] || []
  filtered = {}

  data.each do |key, value|
    # Mapear numero_documento -> documento_numero
    mapped_key = (key == 'numero_documento' ? 'documento_numero' : key)
    filtered[mapped_key] = value if accepted_fields.include?(mapped_key)
  end

  filtered
end
```

---

## 📋 CAMPOS AFETADOS

### Campos que precisam de mapeamento:

| Campo Enviado | Campo BRCobranca | Status |
|---------------|------------------|--------|
| `numero_documento` | `documento_numero` | ❌ PRECISA MAPEAR |
| `documento_numero` | `documento_numero` | ✅ OK |

### Outros campos que podem ter aliases:

Verificar se existem outros campos com nomes diferentes que precisam de mapeamento.

---

## 🎯 RECOMENDAÇÃO FINAL

### Implementar Solução 2 (Normalização)

**Vantagens:**
- ✅ Simples e direto
- ✅ Mantém compatibilidade com ambos os nomes
- ✅ Remove campos não suportados
- ✅ Fácil de testar e manter

**Implementação:**

```ruby
# Em lib/api.rb ou lib/boleto_api.rb

module BoletoAPI
  class API < Grape::API
    helpers do
      def normalize_boleto_data(data)
        normalized = data.is_a?(String) ? JSON.parse(data) : data.dup

        # Mapeamento numero_documento -> documento_numero
        if normalized['numero_documento']
          normalized['documento_numero'] ||= normalized['numero_documento']
          normalized.delete('numero_documento')
        end

        # Adicionar outros mapeamentos conforme necessário

        normalized
      end
    end

    resource :boleto do
      desc 'Gerar boleto em PDF/imagem'
      params do
        requires :bank, type: String, desc: 'Nome do banco'
        requires :type, type: String, desc: 'Formato: pdf|jpg|png|tif'
        requires :data, type: String, desc: 'JSON stringificado'
      end
      get do
        begin
          bank_name = params[:bank]
          format = params[:type]

          # NORMALIZAR DADOS ANTES DE PROCESSAR
          raw_data = JSON.parse(params[:data])
          boleto_data = normalize_boleto_data(raw_data)

          # Criar boleto com dados normalizados
          boleto = create_boleto(bank_name, boleto_data)

          # Gerar PDF/imagem
          content_type format == 'pdf' ? 'application/pdf' : 'image/jpeg'
          env['api.format'] = :binary
          boleto.to(format)
        rescue => e
          error!({ error: e.message }, 400)
        end
      end
    end
  end
end
```

---

## ✅ TESTES

### Depois de implementar, testar:

1. **Enviar apenas `documento_numero`:**
```json
{"documento_numero": "123456"}
```
Resultado esperado: ✅ Deve funcionar

2. **Enviar apenas `numero_documento`:**
```json
{"numero_documento": "123456"}
```
Resultado esperado: ✅ Deve ser mapeado para `documento_numero`

3. **Enviar ambos:**
```json
{
  "numero_documento": "123456",
  "documento_numero": "789012"
}
```
Resultado esperado: ✅ Usar `documento_numero` (prioridade)

---

## 📝 COMMITS SUGERIDOS

```bash
git commit -m "Adiciona mapeamento de numero_documento para documento_numero

PROBLEMA:
- Gem BRCobranca aceita apenas 'documento_numero'
- Aplicacoes podem enviar 'numero_documento'
- Causava NoMethodError

SOLUCAO:
- Adiciona normalize_boleto_data() helper
- Mapeia numero_documento -> documento_numero
- Remove campo nao suportado apos mapeamento
- Mantem compatibilidade com ambos os nomes

TESTE:
- Aceita numero_documento e mapeia corretamente
- Aceita documento_numero diretamente
- Prioriza documento_numero quando ambos presentes
"
```

---

## 🚀 DEPLOY

### Após correção:

1. ✅ Testar localmente com Docker:
```bash
docker build -t boleto_cnab_api .
docker run -p 9292:9292 boleto_cnab_api
curl "http://localhost:9292/api/boleto?bank=banco_brasil&type=pdf&data={...}"
```

2. ✅ Fazer push para GitHub:
```bash
git push origin master
```

3. ✅ Deployar no Render:
   - Render detectará mudanças automaticamente
   - Aguardar build e deploy (~2-3 minutos)
   - Verificar logs para confirmar sucesso

4. ✅ Testar na produção:
   - URL: https://brcobranca-api.onrender.com
   - Verificar health: `GET /api/health`
   - Testar geração de boleto

---

## 📚 REFERÊNCIAS

- **API GitHub:** https://github.com/Maxwbh/boleto_cnab_api
- **Gem BRCobranca:** https://github.com/Maxwbh/brcobranca
- **Documentação Grape API:** https://github.com/ruby-grape/grape
- **Erro Original:** NoMethodError undefined method 'numero_documento='

---

## 📧 CONTATO

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

---

**Status:** ⚠️ CORREÇÃO PENDENTE NA API
**Prioridade:** 🔴 ALTA
**Impacto:** Impede geração de boletos para Banco do Brasil
