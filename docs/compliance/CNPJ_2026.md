# CNPJ Alfanumérico - Mudança 2026

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

## 📋 Sobre a Mudança

A **Receita Federal do Brasil** anunciou que a partir de **julho de 2026**, o formato do CNPJ será alterado para incluir **caracteres alfanuméricos**, permitindo uma combinação de números e letras.

### Motivação da Mudança

1. **Esgotamento de CNPJs numéricos**
   - Formato atual: 14 dígitos numéricos
   - Capacidade: ~100 bilhões de CNPJs
   - Projeção: Esgotamento em 2026

2. **Aumento da capacidade**
   - Formato novo: 14 caracteres alfanuméricos
   - Letras permitidas: A-Z (26 letras)
   - Números permitidos: 0-9 (10 dígitos)
   - Capacidade total: 36^14 = 6,14 × 10²¹ CNPJs possíveis

3. **Benefícios**
   - Sustentabilidade a longo prazo
   - Alinhamento com padrões internacionais
   - Maior flexibilidade para categorização

## 🔄 Formatos Comparados

### Formato Atual (até 2026)
```
Padrão: 99.999.999/9999-99
Exemplo: 12.345.678/0001-95

Estrutura:
- Posições 1-8: Número base da empresa
- Posição 9: 0 (sempre zero)
- Posições 10-12: Número de ordem da matriz/filial
- Posições 13-14: Dígitos verificadores
```

### Formato Novo (a partir de julho/2026)
```
Padrão: XX.XXX.XXX/XXXX-XX (X = letra ou número)
Exemplo: 12.ABC.345/0001-67

Estrutura:
- Posições 1-8: Identificador alfanumérico da empresa
- Posição 9: Caractere de controle
- Posições 10-12: Ordem matriz/filial (alfanumérico)
- Posições 13-14: Dígitos verificadores (novo algoritmo)
```

## ✅ O Que Foi Implementado

### 1. Modelos Django Atualizados

**Antes:**
```python
cnpj = models.CharField(
    max_length=18,
    validators=[RegexValidator(
        regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$'
    )]
)
```

**Depois:**
```python
cnpj = models.CharField(
    max_length=20,
    verbose_name='CNPJ',
    help_text='Suporta formato numérico atual e alfanumérico (preparado para 2026)'
)
```

**Modelos atualizados:**
- ✅ `Contabilidade`
- ✅ `Imobiliaria`
- ✅ `Comprador` (novo campo CNPJ para PJ)

### 2. Máscara JavaScript Alfanumérica

```javascript
function mascaraCNPJ(value) {
    // Remove caracteres especiais mas mantém letras e números
    value = value.toUpperCase().replace(/[^A-Z0-9]/g, '');

    // Aplica máscara: XX.XXX.XXX/XXXX-XX
    // Suporta tanto números quanto letras
}
```

**Recursos:**
- ✅ Aceita números: 0-9
- ✅ Aceita letras: A-Z (convertidas para maiúsculas)
- ✅ Aplica formatação automática
- ✅ Máximo 14 caracteres (antes da formatação)

### 3. Validação Híbrida

```javascript
function validarCNPJ(cnpj) {
    // Detecta se é numérico ou alfanumérico
    const isNumerico = /^\d{14}$/.test(cnpjLimpo);

    if (isNumerico) {
        // Valida com algoritmo atual (dígitos verificadores)
        return validarCNPJNumerico(cnpj);
    } else {
        // Valida formato alfanumérico
        // (algoritmo completo será divulgado pela Receita em 2026)
        return formatoAlfanumerico.test(cnpjLimpo);
    }
}
```

**Validação atual:**
- ✅ CNPJ numérico: Validação completa com dígitos verificadores
- ✅ CNPJ alfanumérico: Validação de formato (aguardando algoritmo oficial)

## 📅 Cronograma da Receita Federal

### Fase 1: Janeiro - Junho 2026
- Testes internos do novo formato
- Divulgação do algoritmo de validação
- Capacitação de desenvolvedores

### Fase 2: Julho 2026
- **Início da emissão de CNPJs alfanuméricos**
- CNPJs antigos continuam válidos
- Sistemas devem aceitar ambos os formatos

### Fase 3: 2027 em diante
- Migração gradual
- CNPJs antigos permanecem válidos indefinidamente
- Novos cadastros receberão formato alfanumérico

## ⚙️ Como Usar no Sistema

### Cadastro de Comprador (Pessoa Jurídica)

1. Acesse **Cadastros → Compradores → Novo Comprador**
2. Selecione **Tipo de Pessoa: Pessoa Jurídica**
3. No campo CNPJ, digite:
   - **Formato antigo:** `12345678000195` → Formatado: `12.345.678/0001-95`
   - **Formato novo:** `12ABC345000167` → Formatado: `12.ABC.345/0001-67`

### Cadastro de Imobiliária

1. Acesse **Cadastros → Imobiliárias → Nova Imobiliária**
2. No campo CNPJ, digite qualquer combinação de 14 caracteres (números e letras)
3. Sistema aplicará máscara automaticamente

### Validação Automática

```
✅ CNPJ Numérico Válido:
   Input: 11222333000181
   Saída: 11.222.333/0001-81 ✓

✅ CNPJ Alfanumérico Válido:
   Input: 11ABC333000181
   Saída: 11.ABC.333/0001-81 ✓ (formato validado)

❌ CNPJ Inválido (tamanho):
   Input: 123
   Erro: "CNPJ deve ter 14 caracteres"

❌ CNPJ Numérico Inválido (dígitos):
   Input: 11222333000182
   Erro: "CNPJ inválido"
```

## 🔐 Segurança e Validação

### Validação no Frontend (JavaScript)

```javascript
// Exemplo de uso
const cnpj1 = '12.345.678/0001-95'; // Numérico
const cnpj2 = '12.ABC.345/0001-67'; // Alfanumérico

console.log(validarCNPJ(cnpj1)); // true (validação completa)
console.log(validarCNPJ(cnpj2)); // true (validação de formato)
```

### Validação no Backend (Django)

```python
from core.models import Comprador

# CNPJ numérico
comprador_pf = Comprador.objects.create(
    tipo_pessoa='PJ',
    nome='Empresa Exemplo LTDA',
    cnpj='12.345.678/0001-95'
)

# CNPJ alfanumérico (após 2026)
comprador_pj = Comprador.objects.create(
    tipo_pessoa='PJ',
    nome='Nova Empresa LTDA',
    cnpj='12.ABC.345/0001-67'
)
```

## 🚀 Preparação para 2026

### Checklist de Compatibilidade

- [x] **Models:** Campos CNPJ com `max_length=20`
- [x] **Forms:** Aceita entrada alfanumérica
- [x] **JavaScript:** Máscara alfanumérica implementada
- [x] **Validação:** Suporte híbrido (numérico/alfanumérico)
- [x] **Database:** VARCHAR(20) para armazenar formato completo
- [x] **Templates:** Exibição formatada de CNPJ
- [ ] **API Externa:** Aguardando integração com Receita Federal (2026)
- [ ] **Algoritmo Validação:** Aguardando divulgação oficial (2026)

### O Que Falta

1. **Algoritmo de Dígitos Verificadores**
   - Receita Federal divulgará em 2026
   - Sistema está preparado para receber atualização

2. **Integração com APIs**
   - Serasa, SPC e outros bureaus atualizarão seus sistemas
   - Receita Federal disponibilizará consulta oficial

3. **Documentos Oficiais**
   - Portaria/Instrução Normativa detalhada
   - Exemplos oficiais de CNPJs alfanuméricos

## 📚 Referências

### Documentação Oficial

- [Receita Federal - Comunicado CNPJ Alfanumérico](https://www.gov.br/receitafederal/)
- [Portaria RFB (a ser publicada)](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cnpj)

### Artigos e Notícias

- [Portal da Receita - FAQ CNPJ](https://www.gov.br/receitafederal/pt-br/canais_atendimento/faq)
- [Migração CNPJ Alfanumérico - Guia Técnico](https://www.gov.br/receitafederal/)

### Normas Relacionadas

- Instrução Normativa RFB nº XXXX/2025 (a ser publicada)
- Ato Declaratório Executivo nº YY/2025 (a ser publicado)

## ⚠️ Observações Importantes

1. **Compatibilidade Retroativa**
   - CNPJs antigos (apenas numéricos) continuarão válidos
   - Sistemas devem aceitar AMBOS os formatos
   - Migração automática NÃO ocorrerá (opcional)

2. **Validação Temporária**
   - Atualmente: CNPJs alfanuméricos validam apenas FORMATO
   - Após 2026: Validação incluirá dígitos verificadores
   - Não haverá quebra de compatibilidade

3. **Banco de Dados**
   - Garantir campo CNPJ com tamanho ≥ 20 caracteres
   - Índices devem suportar VARCHAR alfanumérico
   - Queries case-insensitive podem ser necessárias

4. **Integração com Terceiros**
   - Verificar se parceiros (Serasa, SPC, etc.) estão prontos
   - Testar integração antes de julho/2026
   - Manter fallback para formato antigo

## 🔧 Suporte e Manutenção

Para dúvidas ou problemas relacionados ao CNPJ alfanumérico:

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

---

**Última atualização:** Novembro 2025
**Próxima revisão:** Maio 2026 (pré-lançamento)
