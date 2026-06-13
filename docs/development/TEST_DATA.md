# Geração de Dados de Teste

Sistema para gerar massa de dados de teste no sistema de Gestão de Contratos.

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com

---

## 📊 Dados Gerados

O sistema gera automaticamente:

- ✅ **1 Contabilidade** - Contabilidade Sete Lagoas
- ✅ **2 Imobiliárias** - Lagoa Real e Sete Colinas
- ✅ **8 Contas Bancárias** - BB, Sicoob, Bradesco e C6 Bank (4 contas × 2 imobiliárias)
- ✅ **60 Lotes** - 2 loteamentos com 30 lotes cada em Sete Lagoas
- ✅ **5 Terrenos** - Em bairros de Sete Lagoas
- ✅ **60 Compradores** - Com dados realistas (CPF, endereço, etc.)
- ✅ **65 Contratos** - De 180 a 300 meses
- ✅ **Compras dos últimos 24 meses**
- ✅ **90% das parcelas pagas automaticamente**

---

## 🚀 Como Usar

### Opção 1: Via Django Management Command

```bash
# Gerar dados (boletos distribuídos entre os 4 bancos, round-robin)
python manage.py gerar_dados_teste

# Limpar dados antigos e gerar novos
python manage.py gerar_dados_teste --limpar

# Concentrar 100% dos boletos em um banco (vira a conta principal)
# 001=Banco do Brasil | 756=Sicoob | 237=Bradesco | 336=C6 Bank
python manage.py gerar_dados_teste --limpar --banco 756
```

### Opção 2: Via Endpoint HTTP (assíncrono)

> A geração roda em **segundo plano**: o POST responde imediatamente com
> `202 {"status": "started"}` e o progresso é acompanhado via GET (campo
> `geracao`). Isso evita o timeout de request do Render (~100s) — a geração
> completa leva alguns minutos.

#### **GET** - Ver status atual (e progresso da geração)
```bash
curl https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/
```

Resposta:
```json
{
  "status": "ok",
  "geracao": {
    "status": "running",
    "etapa": "Criando Contratos...",
    "iniciado": "2026-06-12T10:00:00+00:00"
  },
  "dados_existentes": {
    "contabilidades": 1,
    "imobiliarias": 2,
    "imoveis": 65,
    "compradores": 60
  }
}
```

`geracao.status`: `running` (em andamento, com `etapa` atual), `done`
(concluído, com `output` e `dados_gerados`) ou `error` (com `erro`).

#### **POST** - Iniciar geração
```bash
curl -X POST https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/ \
  -H "Content-Type: application/json" \
  -d '{"limpar": true, "banco": "756"}'
```

Resposta imediata (`202 Accepted`):
```json
{
  "status": "started",
  "message": "Geração iniciada em segundo plano. Faça GET neste endpoint para acompanhar."
}
```

POST com geração em andamento retorna `409 {"status": "running"}`.

### Opção 3: Via Browser (recomendado)

Acesse **`/setup/`** no sistema: a tela "Geração de Dados de Teste" tem
seletor de banco dos boletos, opção de limpeza, barra de progresso com a
etapa em andamento e histórico de execuções.

---

## 📋 Detalhes dos Dados Gerados

### Contabilidade
- Nome: Contabilidade Sete Lagoas
- CNPJ: 12.345.678/0001-90
- Responsável: Maxwell da Silva Oliveira
- Localização: Sete Lagoas/MG

### Imobiliárias e Contas Bancárias

Cada imobiliária possui **4 contas bancárias** (uma por banco):

| Banco | Código | Layout CNAB | Carteira | Convênio |
|-------|--------|-------------|----------|----------|
| Banco do Brasil | 001 | CNAB 240 | 18 | 12345678 |
| Sicoob | 756 | CNAB 240 | 1 | 1234567 |
| Bradesco | 237 | CNAB 400 | 06 | — |
| C6 Bank | 336 | CNAB 400 | 10 | 123456789012 |

1. **Imobiliária Lagoa Real** — CNPJ: 23.456.780/0001-10
2. **Imobiliária Sete Colinas** — CNPJ: 23.456.781/0001-11

### Loteamentos

**1. Residencial Lagoa Dourada** (30 lotes)
- Quadras: 1 a 3
- Lotes por quadra: 10
- Área dos lotes: 250m² a 500m²
- Matrícula: 20001 a 20030

**2. Condomínio Parque das Águas** (30 lotes)
- Quadras: 1 a 3
- Lotes por quadra: 10
- Área dos lotes: 250m² a 500m²
- Matrícula: 21001 a 21030

### Terrenos (5 unidades)
- Bairros: Centro, Progresso, Santa Luzia, Várzea, Canaan
- Área: 400m² a 1000m²
- Matrícula: 30001 a 30005

### Compradores (60)
- Nomes brasileiros realistas (Faker)
- CPF válido gerado automaticamente
- Idade: 25 a 65 anos
- Profissões diversas
- Endereços em Sete Lagoas
- E-mail: nome.sobrenome@email.com
- Telefones e celulares

### Contratos (65)
- **Prazo:** 180 a 300 meses
- **Data:** Últimos 24 meses
- **Entrada:** 10% a 30% do valor
- **Valor do m²:** R$ 150,00 a R$ 350,00
- **Vencimento:** Dias 5, 10, 15, 20 ou 25
- **Correção:** IPCA, IGP-M ou SELIC
- **Reajuste:** A cada 12 meses
- **Juros:** 1% ao mês
- **Multa:** 2%

### Parcelas
- **90% pagas** automaticamente
- Pagamentos entre vencimento e 10 dias após
- Juros e multa calculados para atrasos
- Status realista

---

## 🎯 Casos de Uso

### 1. Testar Sistema Localmente
```bash
python manage.py gerar_dados_teste
python manage.py runserver
```
Acesse: http://localhost:8000/admin/

### 2. Popular Banco no Render
```bash
# Via Render Shell
python manage.py gerar_dados_teste
```

Ou via endpoint:
```bash
curl -X POST https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/
```

### 3. Demonstração para Cliente
1. Acesse o admin
2. Mostre contratos reais
3. Parcelas pagas e pendentes
4. Relatórios de vencimento

### 4. Testar Funcionalidades
- Reajustes de contratos
- Notificações de vencimento
- Cálculo de juros e multa
- Relatórios financeiros

---

## ⚠️ Importante

### Dados Fictícios
- Todos os dados são **fictícios** e gerados automaticamente
- CPFs são válidos mas **não reais**
- Nomes, endereços e telefones são **aleatórios**
- **NÃO usar em produção com dados reais**

### Limpeza de Dados
Para limpar todos os dados de teste:
```bash
# Via comando
python manage.py gerar_dados_teste --limpar

# Via endpoint
curl -X POST https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/ \
  -d "limpar=true"
```

**ATENÇÃO:** Isso apaga TODOS os dados do sistema!

### Segurança
- O endpoint está **público** por padrão
- Para produção, adicione autenticação:
  - Exigir login
  - API Key
  - Desabilitar em produção

---

## 🔧 Personalização

Para modificar os dados gerados, edite:
```
core/management/commands/gerar_dados_teste.py
```

### Exemplos de Customização

**Alterar quantidade de lotes:**
```python
lotes = self.criar_loteamentos(imobiliarias, 3, 50)  # 3 loteamentos, 50 lotes cada
```

**Alterar percentual de parcelas pagas:**
```python
self.marcar_parcelas_pagas(contratos, 0.75)  # 75% pagas
```

**Alterar prazo dos contratos:**
```python
numero_parcelas = random.randint(120, 240)  # 120 a 240 meses
```

---

## 📊 Exemplo de Output

```
Iniciando geração de dados de teste...
Criando Contabilidade...
Criando Imobiliárias...
Criando Contas Bancárias...
Criando Loteamentos...
Criando Terrenos...
Criando Compradores...
Criando Contratos...
Marcando parcelas como pagas...
Simulando boletos gerados (para demo de remessa)...
   → 001 - Banco do Brasil (001): N boletos simulados
   → 756 - Sicoob (756): N boletos simulados
   → 237 - Bradesco (237): N boletos simulados
   → 336 - C6 Bank (336): N boletos simulados

✅ Dados gerados com sucesso!
   • 1 Contabilidade
   • 2 Imobiliárias
   • 8 Contas Bancárias
   • 60 Lotes
   • 5 Terrenos
   • 60 Compradores
   • 65+ Contratos
```

---

## 🐛 Troubleshooting

### Erro: "relation does not exist"
**Solução:** Execute migrations primeiro
```bash
python manage.py migrate
```

### Erro: "UNIQUE constraint failed"
**Solução:** Limpe dados antes de gerar novos
```bash
python manage.py gerar_dados_teste --limpar
```

### Endpoint retorna 500
**Causa:** Banco de dados não configurado
**Solução:**
1. Verifique `DATABASE_URL`
2. Execute migrations
3. Teste novamente

---

## 📞 Suporte

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**LinkedIn:** [linkedin.com/in/maxwbh](https://www.linkedin.com/in/maxwbh/)

---

**Desenvolvido com ❤️ por Maxwell da Silva Oliveira**
