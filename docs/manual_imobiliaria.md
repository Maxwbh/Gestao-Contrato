# Manual do Usuário — Imobiliária / Vendedor

**Sistema:** Gestão de Contratos Imobiliários  
**Perfil:** Funcionário de Imobiliária ou Vendedor cadastrado  
**Acesso:** Restrito à(s) imobiliária(s) vinculadas ao seu login

---

## Sumário

1. [Acesso ao Sistema](#1-acesso-ao-sistema)
2. [Visão Geral do Menu](#2-visão-geral-do-menu)
3. [Dashboard](#3-dashboard)
4. [Contratos](#4-contratos)
5. [Financeiro — Parcelas e Boletos](#5-financeiro--parcelas-e-boletos)
6. [Reajustes](#6-reajustes)
7. [Cadastros](#7-cadastros)
8. [Notificações](#8-notificações)
9. [Fluxos Comuns](#9-fluxos-comuns)

---

## 1. Acesso ao Sistema

Acesse pelo navegador o endereço do sistema (fornecido pelo contador) e faça login com o e-mail e senha cadastrados:

```
┌─────────────────────────────────────────────┐
│          GESTÃO DE CONTRATOS                │
│                                             │
│  E-mail  [__________________________]       │
│  Senha   [__________________________]       │
│                                             │
│             [ ENTRAR ]                      │
└─────────────────────────────────────────────┘
```

> Caso não tenha login, solicite ao **Contador** (administrador) que crie um acesso para você.

---

## 2. Visão Geral do Menu

Após entrar, você verá a barra de menus:

```
┌──────────────────────────────────────────────────────────────────────┐
│ 🏠 GC  │ Dashboard │ Financeiro ▾ │ Contratos ▾ │ Cadastros ▾ │ 👤 │
└──────────────────────────────────────────────────────────────────────┘
```

> O menu **Admin** não aparece para o perfil de Imobiliária — é exclusivo do Contador.  
> Todos os dados exibidos são filtrados automaticamente para a sua imobiliária.

### Menu Financeiro ▾
| Item | O que faz |
|---|---|
| Dashboard Financeiro | Resumo financeiro da sua imobiliária |
| Todas as Parcelas | Parcelas dos contratos da sua imobiliária |
| Parcelas do Mês | Vencimentos do mês atual |
| Reajustes Pendentes | Contratos da sua imobiliária aguardando reajuste |
| Histórico de Reajustes | Reajustes já aplicados |
| Arquivos de Remessa | Envio de boletos ao banco (CNAB) |
| Arquivos de Retorno | Confirmação de pagamentos do banco |

### Menu Contratos ▾
| Item | O que faz |
|---|---|
| Todos os Contratos | Lista de contratos da sua imobiliária |
| Novo Contrato | Cadastrar contrato pelo wizard (4 etapas) |
| Importar via IA | Criar contrato a partir de um PDF |
| Índices de Reajuste | Visualizar tabelas de correção disponíveis |

### Menu Cadastros ▾
| Item | O que faz |
|---|---|
| Imóveis | Imóveis vinculados à sua imobiliária |
| Compradores | Compradores vinculados à sua imobiliária |

> Imobiliárias e Contabilidades são gerenciadas apenas pelo Contador.

---

## 3. Dashboard

Ao entrar no sistema, você vai direto ao Dashboard com um resumo da sua carteira:

```
┌────────────────────────────────────────────────────────────────────┐
│  DASHBOARD — Dizaty Imobiliária Ltda           🔍 Buscar (Ctrl+K) │
├──────────────┬──────────────┬─────────────────┬────────────────────┤
│ 📋 Contratos │ 💰 A Receber │ ⚠ Inadimplentes │ 📈 Reaj. Pendentes │
│     23       │  R$ 24.300   │   4 (17,4%)     │         3          │
└──────────────┴──────────────┴─────────────────┴────────────────────┘
│                                                                      │
│  Próximos Vencimentos (7 dias)    Inadimplentes                     │
│  ┌────────────────────────────┐   ┌──────────────────────────────┐  │
│  │ 15/05  Maria A.  R$ 450   │   │ José F.  45 dias  R$ 1.920  │  │
│  │ 17/05  Pedro S.  R$ 620   │   │ Ana B.    3 dias  R$   450  │  │
│  │ 20/05  Ana B.    R$ 450   │   └──────────────────────────────┘  │
│  └────────────────────────────┘                                      │
└────────────────────────────────────────────────────────────────────┘
```

**Dica:** Use a **busca rápida** (`Ctrl+K` ou tecla `/`) para encontrar qualquer contrato, comprador ou imóvel pelo nome ou número.

---

## 4. Contratos

### 4.1 Lista de Contratos

```
[Contratos] → [Todos os Contratos]

┌──────────────────────────────────────────────────────────────────┐
│ Contratos  🔍[_____________]  Status[_____▾]          [Filtrar]  │
├──────────────────────────────────────────────────────────────────┤
│ Nº     Comprador          Imóvel           Valor      Status     │
│ 0042   Maria Aparecida    Lote 12 Qd 5    R$120.000  Ativo ✅   │
│ 0043   José Ferreira      Apto 304 Bl B   R$280.000  Ativo ✅   │
│ 0044   Pedro Santos       Lote 01 Qd 1    R$ 90.000  Ativo ✅   │
└──────────────────────────────────────────────────────────────────┘
```

Clique no número do contrato ou no nome do comprador para ver os detalhes.

### 4.2 Detalhe do Contrato

```
[Contrato 0042 — Maria Aparecida]

┌──────────────────────────────────────────────────────────────────┐
│ Contrato 0042                              [Editar] [Excluir]    │
├─────────────────────────┬────────────────────────────────────────┤
│ DADOS GERAIS            │ FINANCEIRO                             │
│ Data: 15/03/2021        │ Valor Total:    R$ 120.000,00          │
│ Comprador: Maria Apare. │ Entrada:        R$  12.000,00          │
│ Imóvel: Lote 12 Qd 5   │ Saldo Devedor:  R$  96.450,00          │
│ Correção: IPCA          │ Parcelas:       240 x R$ 450,00        │
│ Juros mora: 1% ao mês   │ 1º Vencimento:  15/04/2021            │
│ Multa: 2%               │ Próx. Reajuste: 15/03/2022            │
├─────────────────────────┴────────────────────────────────────────┤
│ [ 📊 Parcelas ] [ 💰 Carnê ] [ 📋 Quadro Resumo ] [ 📄 Minutas ]│
│ [ 📈 Aplicar Reajuste ] [ ✂ Rescisão ] [ ↔ Cessão ]            │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Cadastrar Novo Contrato (Wizard)

O assistente guia você em **4 etapas**:

**Etapa 1 — Dados Básicos**
```
┌──────────────────────────────────────────────────────────────────┐
│ ① Básico ── ② Juros ── ③ Intermediárias ── ④ Revisão            │
├──────────────────────────────────────────────────────────────────┤
│ Comprador:    [Maria Aparecida da Silva ▾]      [+ Cadastrar]    │
│ Imóvel:       [Lote 12, Quadra 5        ▾]      [+ Cadastrar]    │
│ Nº Contrato:  [0042]                                              │
│ Data:         [15/03/2021]                                        │
│ Valor Total:  [120.000,00]                                        │
│ Entrada:      [ 12.000,00]                                        │
│ Nº Parcelas:  [240]    Dia vencimento: [15]                      │
│ 1º Vencimento:[15/04/2021]  (preenchido automaticamente)         │
│                                            [Próximo →]           │
└──────────────────────────────────────────────────────────────────┘
```

**Etapa 2 — Juros e Correção**
```
│ Índice de correção: [IPCA ▾]   Prazo reajuste: [12] meses       │
│ Juros mora:  [1,00] % ao mês                                      │
│ Multa:       [2,00] %                                             │
│                           [← Anterior]  [Próximo →]              │
```

**Etapa 3 — Parcelas Intermediárias** (opcional)
```
│ Parcelas com vencimentos específicos (semestrais, anuais):       │
│ [+ Adicionar Parcela Intermediária]                               │
│                           [← Anterior]  [Próximo →]              │
```

**Etapa 4 — Revisão e Confirmação**
```
│ Resumo completo do contrato para conferência                      │
│ Tabela de parcelas geradas automaticamente                        │
│                       [← Anterior]  [✅ Concluir]               │
```

### 4.4 Importar Contrato via IA (PDF)

```
[Contratos] → [Importar via IA]

1. Arraste o PDF do contrato ou clique para selecionar
2. Clique em [Enviar para Análise]
3. Aguarde a extração (normalmente 10-30 segundos)
4. Revise os dados na tela de revisão
   ⚠ Campos com borda amarela = IA não tinha certeza → confira!
5. Clique em [Confirmar e Cadastrar]
```

### 4.5 Rescisão de Contrato

```
[Contrato] → [✂ Rescisão]

┌──────────────────────────────────────────────────────────────────┐
│ Cálculo de Rescisão — Contrato 0042                              │
├──────────────────────────────────────────────────────────────────┤
│ Data de rescisão:  [01/06/2021]                                  │
│ Meses de fruição: 2                                              │
├──────────────────────────────────────────────────────────────────┤
│ Valor pago pelo comprador:    R$ 12.900,00                       │
│ Fruição (2 meses):            R$  2.000,00                       │
│ Multa penal (10%):            R$  1.200,00                       │
│ Despesas administrativas:     R$    500,00                       │
│ Valor a devolver:             R$  9.200,00                       │
└──────────────────────────────────────────────────────────────────┘
```

### 4.6 Cessão de Contrato

Transferência do contrato para outro comprador. Acesse em **[↔ Cessão]** dentro do detalhe do contrato.

---

## 5. Financeiro — Parcelas e Boletos

### 5.1 Parcelas do Mês

```
[Financeiro] → [Parcelas do Mês]

Maio/2021
┌────┬───────────────────┬──────────┬──────────┬──────────────────┐
│ Nº │ Comprador         │ Vecto    │ Valor    │ Ações            │
│ 14 │ Maria Aparecida   │ 15/05/21 │ R$450,00 │ 💳 📄 📱 📧     │
│ 08 │ José Ferreira     │ 17/05/21 │ R$960,00 │ 💳 📄 📱 📧     │
│ 22 │ Pedro Santos      │ 20/05/21 │ R$620,00 │ 💳 📄 📱 📧     │
└────┴───────────────────┴──────────┴──────────┴──────────────────┘
Legenda: 💳 Pagar  📄 Boleto  📱 WhatsApp  📧 E-mail
```

### 5.2 Registrar Pagamento

```
[Parcela] → [💳 Pagar]

┌──────────────────────────────────────────────────────────────┐
│ Registrar Pagamento                                           │
│ Comprador: Maria Aparecida | Parcela 14/240                  │
├──────────────────────────────────────────────────────────────┤
│ Valor original:    R$ 450,00                                 │
│ Juros (2 dias):    R$   0,30                                 │
│ Total calculado:   R$ 450,30                                 │
├──────────────────────────────────────────────────────────────┤
│ Data do pagamento: [15/05/2021]                              │
│ Valor recebido:    [450,30]                                   │
│ Forma de pagamento:[PIX ▾]                                   │
│                                                               │
│               [ ✅ Confirmar Pagamento ]                     │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Gerar e Enviar Boleto

**Gerar boleto de uma parcela:**
1. Na lista de parcelas → clique em **📄 Boleto**
2. Escolha: **Visualizar** | **Baixar PDF** | **Enviar por WhatsApp** | **Enviar por SMS**

**Gerar carnê completo:**
1. No detalhe do contrato → **[💰 Gerar Carnê]**
2. Sistema gera PDF com todos os boletos em sequência
3. Entregue ao comprador no primeiro encontro

**Enviar link do boleto por WhatsApp:**
1. Na parcela → **📱 WhatsApp**
2. Abre o WhatsApp Web com mensagem e link pré-formatados
3. Basta clicar em Enviar

### 5.4 Boleto Público (sem login)

Cada boleto gerado possui um **link único** que o comprador pode acessar sem fazer login:

```
https://seusite.com/b/[código-único]/

┌──────────────────────────────────────────┐
│ 🏠 Gestão de Contratos                   │
│                                          │
│ Parcela: 14/240 — Maio 2021             │
│ Comprador: Maria Aparecida da Silva      │
│ Vencimento: 15/05/2021                   │
│ Valor: R$ 450,00                         │
│                                          │
│  Linha digitável:                        │
│  23793.38128 60007.727244...             │
│                                          │
│       [ 📥 Baixar Boleto PDF ]          │
└──────────────────────────────────────────┘
```

### 5.5 Detalhe da Parcela

```
[Financeiro] → [Parcelas] → [Clique em uma parcela]

┌──────────────────────────────────────────────────────────────┐
│ Parcela 14/240 — Contrato 0042                               │
├──────────────────────────────────────────────────────────────┤
│ Status: ⏳ Em aberto                                         │
│ Vencimento: 15/05/2021                                       │
│ Valor Original: R$ 450,00                                    │
│ Competência: Maio/2021                                       │
├──────────────────────────────────────────────────────────────┤
│ Histórico de boletos                                         │
│  📄 Boleto gerado em 01/05/2021 — Vigente até 15/06/2021    │
├──────────────────────────────────────────────────────────────┤
│ [💳 Registrar Pagamento] [📄 Nova Via] [📱 WhatsApp]        │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Reajustes

### 6.1 Ver Reajustes Pendentes

```
[Financeiro] → [Reajustes Pendentes]

┌─────────────────────────────────────────────────────────────────┐
│ Reajustes Pendentes (3)                    [Aplicar em Lote]   │
├──────────────────────────────┬────────────┬────────────────────┤
│ Contrato / Comprador         │ Índice     │ Ações              │
│ 0042 — Maria Aparecida       │ IPCA 2,43% │ [Preview] [Aplicar]│
│ 0043 — José Ferreira         │ IPCA 2,43% │ [Preview] [Aplicar]│
│ 0044 — Pedro Santos          │ IGPM 3,12% │ [Preview] [Aplicar]│
└──────────────────────────────┴────────────┴────────────────────┘
```

### 6.2 Conferir Antes de Aplicar (Preview)

```
[Reajuste 0042] → [Preview]

┌──────────────────────────────────────────────────────────────────┐
│ Preview do Reajuste — Contrato 0042 — Maria Aparecida            │
├──────────────────────────────────────────────────────────────────┤
│ Índice:              IPCA — Março/2022 — 2,43%                  │
│ Valor atual:         R$ 450,00                                   │
│ Valor após reajuste: R$ 460,94                                   │
│ Aumento por parcela: R$  10,94                                   │
│ Parcelas restantes:  226                                         │
├──────────────────────────────────────────────────────────────────┤
│   [ ✅ Confirmar Reajuste ]             [ Cancelar ]            │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 Aplicar Reajuste em Lote

Aplica o reajuste em todos os contratos pendentes de uma só vez:

1. **Financeiro → Reajustes Pendentes**
2. Clique em **[Aplicar em Lote]**
3. Confirme a operação

---

## 7. Cadastros

### 7.1 Compradores

```
[Cadastros] → [Compradores] → [+ Novo Comprador]

┌──────────────────────────────────────────────────────────────────┐
│ Novo Comprador                                                     │
├──────────────────────────────────────────────────────────────────┤
│ Tipo de Pessoa: ● Pessoa Física  ○ Pessoa Jurídica               │
│ Nome Completo: [_______________________________]                  │
│ CPF:           [000.000.000-00]                                   │
│ RG:            [_______________________________]                  │
│ E-mail:        [_______________] (opcional)                       │
│ Telefone:      [(00) 0000-0000] (opcional)                       │
│ Celular:       [(00) 00000-0000] (opcional)                      │
│ CEP:           [00000-000] 🔍  → preenche endereço auto          │
│ Endereço:      [_______________________________]                  │
│ Número:        [____]  Complemento: [___________]                │
│ Bairro:        [_______________________________]                  │
│ Cidade:        [_______________________________] Estado: [MG▾]   │
│                                                                    │
│                          [ Salvar ]  [ Cancelar ]                │
└──────────────────────────────────────────────────────────────────┘
```

> **E-mail, Telefone e Celular são opcionais.** Podem ser deixados em branco.

### 7.2 Imóveis

```
[Cadastros] → [Imóveis] → [+ Novo Imóvel]

┌──────────────────────────────────────────────────────────────────┐
│ Novo Imóvel                                                       │
├──────────────────────────────────────────────────────────────────┤
│ Imobiliária:   [Dizaty Imobiliária Ltda ▾]                       │
│ Tipo:          [LOTE ▾]  (Lote / Terreno / Casa / Apto / Comerc.)│
│ Identificação: [Lote 12, Quadra 5]                               │
│ Loteamento:    [Residencial das Flores]                           │
│ Área (m²):     [300,00]                                           │
│ Matrícula:     [12345]                                            │
│ CEP:           [00000-000] 🔍                                    │
│ Logradouro:    [_______________________________]                  │
│ Cidade:        [_______________________________] Estado: [GO▾]   │
│                                                                    │
│                          [ Salvar ]  [ Cancelar ]                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Notificações

### 8.1 Ver Histórico de Notificações

```
[Notificações] → [Histórico de Envios]

┌──────────────────────────────────────────────────────────────────┐
│ Histórico de Notificações          🔍                            │
├──────────────────┬──────────────┬───────────┬───────────────────┤
│ Comprador        │ Canal        │ Data       │ Status            │
│ Maria Aparecida  │ 📧 E-mail    │ 10/05/2021 │ ✅ Enviado       │
│ José Ferreira    │ 📱 WhatsApp  │ 10/05/2021 │ ✅ Enviado       │
│ Pedro Santos     │ 📧 E-mail    │ 08/05/2021 │ ❌ Falhou        │
└──────────────────┴──────────────┴───────────┴───────────────────┘
```

Clique em **❌ Falhou** para ver o motivo e reenviar manualmente.

---

## 9. Fluxos Comuns

### Fluxo 1 — Cadastrar um novo contrato
1. **Cadastros → Compradores → + Novo** (se necessário)
2. **Cadastros → Imóveis → + Novo** (se necessário)
3. **Contratos → Novo Contrato** → preencha as 4 etapas → **Concluir**
4. Na tela do contrato recém-criado → **[💰 Gerar Carnê]** para imprimir os boletos

### Fluxo 2 — Importar contrato de um PDF
1. **Contratos → Importar via IA** → envie o PDF
2. Aguarde a extração
3. Revise os dados (campos amarelos = confirme manualmente)
4. **Confirmar e Cadastrar**

### Fluxo 3 — Dia a dia: verificar e cobrar parcelas vencidas
1. **Financeiro → Parcelas do Mês**
2. Identifique parcelas com status 🔴 Atrasado
3. Envie o boleto por **📱 WhatsApp** ou **📧 E-mail**
4. Ao receber o pagamento, registre em **💳 Pagar**

### Fluxo 4 — Gerar boleto avulso (segunda via)
1. **Financeiro → Todas as Parcelas** → localize a parcela
2. Clique em **📄 Boleto** → **Segunda Via**
3. O novo boleto é gerado com data de validade atualizada

### Fluxo 5 — Aplicar reajuste anual
1. **Financeiro → Reajustes Pendentes**
2. Clique em **Preview** para confirmar o novo valor
3. **Aplicar** (individualmente) ou **Aplicar em Lote** (todos de uma vez)

### Fluxo 6 — Calcular rescisão de contrato
1. Abra o contrato → **[✂ Rescisão]**
2. Informe a data de rescisão
3. O sistema calcula automaticamente: fruição, multa, valor a devolver
4. Imprima o cálculo para formalizar com o comprador

---

## Perguntas Frequentes

**P: Não consigo ver contratos de outras imobiliárias. Por quê?**  
R: Seu acesso é limitado à imobiliária vinculada ao seu login. Contate o Contador para ajustar.

**P: Preciso cadastrar uma nova imobiliária. O que faço?**  
R: Apenas o Contador pode cadastrar imobiliárias. Solicite ao administrador.

**P: O boleto gerado está com dados errados. Como corrigir?**  
R: Cancele o boleto atual → corrija os dados do comprador ou contrato → gere um novo boleto.

**P: O comprador não recebeu o e-mail com o boleto. O que fazer?**  
R: Verifique em **Notificações → Histórico** se o envio foi processado. Se constar falha, clique em **Reenviar**. Se o problema persistir, contate o Contador para verificar o servidor de e-mail.

**P: Como alterar a data de vencimento das parcelas?**  
R: A data de vencimento é definida no contrato e não pode ser alterada individualmente. Para renegociar, use **Financeiro → Renegociar Parcelas** dentro do contrato.

---

*Manual gerado em 2026-05-25 — Gestão de Contratos v3.1*
