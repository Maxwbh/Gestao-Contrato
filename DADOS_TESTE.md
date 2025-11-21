# Geração de Dados de Teste

Sistema para gerar massa de dados de teste no sistema de Gestão de Contratos.

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com

---

## 📊 Dados Gerados

O sistema gera automaticamente:

- ✅ **1 Contabilidade** - Contabilidade Sete Lagoas
- ✅ **2 Imobiliárias** - Lagoa Real e Sete Colinas
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
# Gerar dados
python manage.py gerar_dados_teste

# Limpar dados antigos e gerar novos
python manage.py gerar_dados_teste --limpar
```

### Opção 2: Via Endpoint HTTP

#### **GET** - Ver status atual
```bash
curl https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/
```

Resposta:
```json
{
  "status": "ok",
  "dados_existentes": {
    "contabilidades": 1,
    "imobiliarias": 2,
    "imoveis": 65,
    "compradores": 60
  }
}
```

#### **POST** - Gerar dados
```bash
curl -X POST https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/
```

#### **POST** - Limpar e gerar novos dados
```bash
curl -X POST https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/ \
  -d "limpar=true"
```

Resposta:
```json
{
  "status": "success",
  "message": "Dados gerados com sucesso!",
  "output": "...",
  "dados_gerados": {
    "contabilidades": 1,
    "imobiliarias": 2,
    "imoveis": 65,
    "compradores": 60
  }
}
```

### Opção 3: Via Browser

Acesse diretamente no navegador:
```
GET: https://gestao-contrato-web.onrender.com/api/gerar-dados-teste/
```

Para gerar via POST, use uma ferramenta como Postman ou Thunder Client.

---

## 📋 Detalhes dos Dados Gerados

### Contabilidade
- Nome: Contabilidade Sete Lagoas
- CNPJ: 12.345.678/0001-90
- Responsável: Maxwell da Silva Oliveira
- Localização: Sete Lagoas/MG

### Imobiliárias
1. **Imobiliária Lagoa Real**
   - CNPJ: 23.456.780/0001-10
   - Banco: Banco do Brasil

2. **Imobiliária Sete Colinas**
   - CNPJ: 23.456.781/0001-11
   - Banco: Banco do Brasil

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
Criando Loteamentos...
Criando Terrenos...
Criando Compradores...
Criando Contratos...
Marcando parcelas como pagas...

✅ Dados gerados com sucesso!
   • 1 Contabilidade
   • 2 Imobiliárias
   • 60 Lotes
   • 5 Terrenos
   • 60 Compradores
   • 65 Contratos
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
