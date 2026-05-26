# Manual do Usuário — Contador (Administrador)

**Sistema:** Gestão de Contratos Imobiliários  
**Perfil:** Contador / Administrador do Site  
**Acesso:** Completo — todas as funções do sistema

---

## Sumário

1. [Acesso ao Sistema](#1-acesso-ao-sistema)
2. [Visão Geral do Menu](#2-visão-geral-do-menu)
3. [Dashboard Principal](#3-dashboard-principal)
4. [Cadastros](#4-cadastros)
5. [Contratos](#5-contratos)
6. [Financeiro](#6-financeiro)
7. [Notificações](#7-notificações)
8. [Administração](#8-administração)
9. [Fluxos Comuns](#9-fluxos-comuns)

---

## 1. Acesso ao Sistema

Acesse pelo navegador o endereço do sistema e clique em **Entrar**:

```
┌─────────────────────────────────────────────┐
│          GESTÃO DE CONTRATOS                │
│                                             │
│  E-mail  [__________________________]       │
│  Senha   [__________________________]       │
│                                             │
│             [ ENTRAR ]                      │
│                                             │
│  ⚠ Esqueceu a senha? Contate o suporte.    │
└─────────────────────────────────────────────┘
```

> O Contador usa a mesma tela de login do sistema principal (não o portal do comprador).

---

## 2. Visão Geral do Menu

Após entrar, a barra superior exibe todos os menus disponíveis:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🏠 GC  │ Dashboard │ Financeiro ▾ │ Contratos ▾ │ Cadastros ▾ │ Notif. ▾ │ Admin ▾ │ 👤 │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Menu Financeiro ▾
| Item | O que faz |
|---|---|
| Dashboard Financeiro | Visão geral de receitas, parcelas e inadimplência |
| Todas as Parcelas | Lista completa de parcelas de todos os contratos |
| Parcelas do Mês | Parcelas com vencimento no mês atual |
| Reajustes Pendentes | Contratos aguardando aplicação de índice |
| Histórico de Reajustes | Reajustes já aplicados |
| Arquivos de Remessa | Envio de boletos ao banco (CNAB) |
| Arquivos de Retorno | Confirmação de pagamentos do banco (CNAB) |
| Conciliação Bancária | Conciliar extrato OFX com parcelas do sistema |

### Menu Contratos ▾
| Item | O que faz |
|---|---|
| Todos os Contratos | Lista e pesquisa de contratos |
| Novo Contrato | Cadastrar contrato manualmente (wizard) |
| Importar via IA | Criar contrato a partir de PDF com extração automática |
| Índices de Reajuste | Gerenciar tabelas IPCA, IGPM, INCC etc. |

### Menu Cadastros ▾
| Item | O que faz |
|---|---|
| Contabilidades | Empresas contábeis cadastradas |
| Imobiliárias / Vendedores | Vendedores (PJ ou PF) ligados aos contratos |
| Imóveis | Propriedades vinculadas a contratos |
| Compradores | Clientes / adquirentes |

### Menu Notificações ▾
| Item | O que faz |
|---|---|
| Histórico de Envios | Todas as notificações enviadas |
| Régua de Cobrança | Regras automáticas de aviso por vencimento |
| Templates de Mensagens | Modelos de e-mail e WhatsApp |
| Servidores de E-mail | Configuração SMTP |
| WhatsApp | Configuração Evolution/BSP |

### Menu Admin ▾ *(exclusivo do Contador)*
| Item | O que faz |
|---|---|
| Configurações do Sistema | Parâmetros globais, percentuais padrão |
| Acessos de Usuários | Criar e gerenciar logins de Imobiliárias |
| Dados de Teste | Gerar / limpar dados fictícios para homologação |
| Django Admin | Painel técnico avançado |

---

## 3. Dashboard Principal

```
┌────────────────────────────────────────────────────────────┐
│  DASHBOARD                             🌙 Modo Escuro  🔍  │
├──────────────┬──────────────┬──────────────┬───────────────┤
│  📋 Contratos│ 💰 Parcelas  │ ⚠ Inadimp.  │  📈 Reajustes │
│     47       │  Mês: 312    │  23 (7,4%)   │  Pendentes: 5 │
└──────────────┴──────────────┴──────────────┴───────────────┘
│                                                            │
│  Vencimentos da Semana         Inadimplência por Imob.    │
│  ┌──────────────────┐          ┌────────────────────┐     │
│  │ Seg 12/05  R$4.2k│          │ Dizaty Imob  3 prc │     │
│  │ Ter 13/05  R$1.8k│          │ J. Silva PF  1 prc │     │
│  │ Qua 14/05  R$6.1k│          └────────────────────┘     │
│  └──────────────────┘                                      │
└────────────────────────────────────────────────────────────┘
```

**Atalhos de teclado:**
- `Ctrl + K` ou `/` → Abre busca global (pesquisa contratos, compradores, imóveis)
- `Ctrl + S` → Salva o formulário aberto

---

## 4. Cadastros

### 4.1 Contabilidades

Cada Contabilidade agrupa um conjunto de Imobiliárias. É o nível mais alto da hierarquia.

```
[Cadastros] → [Contabilidades]

┌──────────────────────────────────────────────────────┐
│ Contabilidades                          [+ Nova]     │
├──────────────────────────────────────────────────────┤
│ Nome              CNPJ               Ações           │
│ M&S Contabilidade 12.345.678/0001-90  ✏ 🗑 ⚙        │
│ Alfa Assessoria   98.765.432/0001-11  ✏ 🗑 ⚙        │
└──────────────────────────────────────────────────────┘
```

O ícone **⚙ Configurações** permite definir dados bancários, parâmetros de juros e multa padrão para a contabilidade.

### 4.2 Imobiliárias / Vendedores

```
[Cadastros] → [Imobiliárias]

┌────────────────────────────────────────────────────────────┐
│ Imobiliárias                                  [+ Nova]     │
├────────────────────────────────────────────────────────────┤
│ Nome               Tipo  Documento           Ações         │
│ Dizaty Imob. Ltda  PJ    12.345.678/0001-90  ✏ 🗑         │
│ João Silva         PF    123.456.789-09      ✏ 🗑         │
└────────────────────────────────────────────────────────────┘
```

> Imobiliária aceita **Pessoa Física (PF)** ou **Pessoa Jurídica (PJ)**.  
> Ao cadastrar PJ informe CNPJ; ao cadastrar PF informe CPF.

**Formulário de Imobiliária:**
```
┌───────────────────────────────────────────────────┐
│ Nova Imobiliária / Vendedor                        │
├───────────────────────────────────────────────────┤
│ Tipo de Pessoa:  ● Pessoa Jurídica  ○ Pessoa Física│
│ Nome Fantasia:   [_____________________]          │
│ Razão Social:    [_____________________]          │
│ CNPJ:            [AA.BBB.000/0001-00]             │  ← aceita letras (formato 2026)
│ E-mail:          [_____________________]          │
│ Telefone:        [(00) 0000-0000]                 │
│ CEP:             [00000-000]  🔍 (preenche auto)  │
│                                                   │
│              [ Salvar ]  [ Cancelar ]             │
└───────────────────────────────────────────────────┘
```

### 4.3 Compradores

```
[Cadastros] → [Compradores]

┌──────────────────────────────────────────────────────────┐
│ Compradores                                   [+ Novo]   │
├──────────────────────────────────────────────────────────┤
│ Nome                CPF/CNPJ          Contratos  Ações   │
│ Maria Aparecida     123.456.789-09    2          ✏ 🗑    │
│ Construtora XYZ Ltda 12.345.678/0001  1          ✏ 🗑   │
└──────────────────────────────────────────────────────────┘
```

### 4.4 Imóveis

```
[Cadastros] → [Imóveis]

┌──────────────────────────────────────────────────────────┐
│ Imóveis                                       [+ Novo]   │
├──────────────────────────────────────────────────────────┤
│ Identificação   Tipo    Loteamento      Cidade   Ações    │
│ Lote 12 Qd 5   LOTE    Res. das Flores Anápolis ✏ 🗑    │
│ Apto 304 Bl B  APART.  —               Goiânia  ✏ 🗑    │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Contratos

### 5.1 Lista de Contratos

```
[Contratos] → [Todos os Contratos]

┌──────────────────────────────────────────────────────────────────┐
│ Contratos  🔍[_____________]  Imob.[_____] Status[_____] [Filtrar]│
├──────────────────────────────────────────────────────────────────┤
│ Nº     Comprador         Imóvel          Valor       Status      │
│ 0042   Maria Aparecida   Lote 12 Qd 5   R$120.000   Ativo ✅    │
│ 0043   José Ferreira     Apto 304 Bl B  R$280.000   Ativo ✅    │
│ 0044   Const. XYZ Ltda   Lote 01 Qd 1   R$90.000   Rescindido ❌│
└──────────────────────────────────────────────────────────────────┘
                                           [← Anterior] [Próximo →]
```

### 5.2 Detalhe do Contrato

```
[Contratos] → [0042 — Maria Aparecida]

┌──────────────────────────────────────────────────────────────────┐
│ Contrato 0042                           [Editar] [Excluir]       │
├─────────────────────────┬────────────────────────────────────────┤
│ DADOS GERAIS            │ FINANCEIRO                             │
│ Data: 15/03/2021        │ Valor Total: R$ 120.000,00             │
│ Comprador: Maria Apare. │ Entrada: R$ 12.000,00                  │
│ Imóvel: Lote 12 Qd 5   │ Saldo: R$ 108.000,00                   │
│ Imobiliária: Dizaty     │ Parcelas: 240 x R$ 450,00             │
│ Correção: IPCA          │ 1º Venc.: 15/04/2021                  │
│ Juros mora: 1% a.m.     │ Dia venc.: 15                         │
│ Multa: 2%               │                                        │
├─────────────────────────┴────────────────────────────────────────┤
│ AÇÕES RÁPIDAS                                                     │
│ [📊 Parcelas] [💰 Gerar Carnê] [📋 Quadro Resumo] [📄 Minutas]  │
│ [📈 Reajuste] [✂ Rescisão] [↔ Cessão] [📥 Importar via IA]     │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 Novo Contrato — Wizard (4 etapas)

```
Etapa 1/4 — Dados Básicos
┌──────────────────────────────────────────────────────────────────┐
│ ① Básico  ─── ② Juros ─── ③ Intermediárias ─── ④ Revisão       │
├──────────────────────────────────────────────────────────────────┤
│ Imobiliária:  [Dizaty Imobiliária Ltda         ▾]               │
│ Comprador:    [Maria Aparecida da Silva         ▾] [+ Novo]      │
│ Imóvel:       [Lote 12, Quadra 5               ▾] [+ Novo]      │
│ Nº Contrato:  [0042]                                             │
│ Data:         [15/03/2021]                                       │
│ Valor Total:  [120.000,00]                                       │
│ Entrada:      [ 12.000,00]                                       │
│ Nº Parcelas:  [240]     Dia vencimento: [15]                    │
│ 1º Vencimento:[15/04/2021]                                       │
│                                         [Próximo →]             │
└──────────────────────────────────────────────────────────────────┘
```

### 5.4 Importar Contrato via IA

```
[Contratos] → [Importar via IA]

┌──────────────────────────────────────────────────────────────────┐
│ 📥 Importar Contrato via Inteligência Artificial                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Arraste o arquivo PDF aqui                                      │
│   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐             │
│   │       📄  ou  clique para selecionar          │             │
│   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘             │
│                                                                    │
│   Formatos aceitos: PDF, JPG, PNG  |  Máx. 10MB                  │
│                                                                    │
│                    [ Enviar para Análise ]                        │
└──────────────────────────────────────────────────────────────────┘
```

Após o envio, a IA extrai os dados e exibe a tela de **Revisão**:

```
┌──────────────────────────────────────────────────────────────────┐
│ ✅ Revisão dos Dados Extraídos pela IA                            │
│ Confiança: ALTO  |  Campos incertos destacados em amarelo        │
├──────────────────────────┬───────────────────────────────────────┤
│ Dados do Contrato        │ Imobiliária / Vendedor                 │
│ Data: [15/03/2021]       │ Tipo: ● PJ  ○ PF                     │
│ Valor Total: [120.000,00]│ Nome: [Dizaty Imobiliária Ltda]       │
│ Parcelas: [240]          │ CNPJ: [12.345.678/0001-90]            │
│ 1º Venc.: [15/04/2021]  │                                        │
├──────────────────────────┴───────────────────────────────────────┤
│ Dados do Comprador                                                 │
│ Nome: [Maria Aparecida da Silva]  CPF: [123.456.789-09]          │
│ E-mail: [_____________] (opcional)                                │
├──────────────────────────────────────────────────────────────────┤
│ Campo com baixa confiança ⚠ = borda amarela → verifique          │
│                                                                    │
│              [ ✅ Confirmar e Cadastrar ]                         │
└──────────────────────────────────────────────────────────────────┘
```

### 5.5 Quadro-Resumo (Lei 6.766 / Art. 26)

Documento legal com todas as condições do contrato, acessível em **[Quadro Resumo]** dentro do detalhe do contrato.

### 5.6 Minutas

Modelos de texto jurídico vinculados ao contrato. Acesse em **[Minutas]** dentro do detalhe.

---

## 6. Financeiro

### 6.1 Dashboard Financeiro

```
[Financeiro] → [Dashboard Financeiro]

┌──────────────────────────────────────────────────────────────────┐
│ Dashboard Financeiro                  Filtro: [Todas Imob. ▾]   │
├──────────────┬───────────────┬──────────────────────────────────┤
│ A Receber/Mês│ Recebido/Mês  │ Inadimplência                    │
│ R$ 48.000    │ R$ 42.300     │ R$ 5.700 (11,9%)                 │
├──────────────┴───────────────┴──────────────────────────────────┤
│ Parcelas Próximas 30 dias             Reajustes Pendentes        │
│  ┌────────────────────────────┐       ┌───────────────────────┐  │
│  │ 15/05  Maria A.  R$ 450   │       │ Contrato 0042 — IPCA  │  │
│  │ 17/05  José F.   R$ 960   │       │ Contrato 0055 — IGPM  │  │
│  └────────────────────────────┘       └───────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Parcelas

```
[Financeiro] → [Todas as Parcelas]

┌───────────────────────────────────────────────────────────────────┐
│ Parcelas  🔍  Período[__/__/____] a [__/__/____]  Status[____▾]   │
├────┬──────────────┬──────────┬──────────┬──────────┬─────────────┤
│ Nº │ Contrato     │ Vecto    │ Valor    │ Status   │ Ações       │
│ 01 │ 0042-Maria A.│ 15/04/21 │ R$450,00 │ ✅ Pago  │ 👁         │
│ 02 │ 0042-Maria A.│ 15/05/21 │ R$450,00 │ ⏳ Aberto│ 💳 📄 📱  │
│ 03 │ 0043-José F. │ 20/05/21 │ R$960,00 │ 🔴 Atras.│ 💳 📄 📱  │
└────┴──────────────┴──────────┴──────────┴──────────┴─────────────┘
```

Ícones de ação:
- 👁 Ver detalhe
- 💳 Registrar pagamento
- 📄 Gerar / visualizar boleto
- 📱 Enviar por WhatsApp

### 6.3 Registrar Pagamento

```
[Parcela] → [Registrar Pagamento]

┌──────────────────────────────────────────────────────┐
│ Registrar Pagamento — Parcela 02/240 (Contrato 0042)  │
├──────────────────────────────────────────────────────┤
│ Valor original:    R$ 450,00                         │
│ Juros calculados:  R$   9,00                         │
│ Multa calculada:   R$   9,00                         │
│ Total a pagar:     R$ 468,00                         │
├──────────────────────────────────────────────────────┤
│ Data pagamento:  [15/05/2021]                        │
│ Valor recebido:  [468,00]                            │
│ Forma:           [PIX ▾]                             │
│ Observação:      [___________________________]       │
│                                                      │
│             [ ✅ Confirmar Pagamento ]               │
└──────────────────────────────────────────────────────┘
```

### 6.4 Boletos

**Gerar boleto individual:**
- Na lista de parcelas, clique em **📄 Gerar Boleto**
- O boleto é gerado e exibido em PDF

**Gerar carnê (todos os boletos do contrato):**
- No detalhe do contrato → **[💰 Gerar Carnê]**
- Baixa um PDF com todos os boletos em sequência

**Enviar por WhatsApp:**
- Na parcela → **📱 WhatsApp** → abre link pré-formatado

### 6.5 Reajustes

```
[Financeiro] → [Reajustes Pendentes]

┌─────────────────────────────────────────────────────────────────┐
│ Reajustes Pendentes (5)                     [Aplicar em Lote]   │
├──────────────────────┬────────────────┬────────────────────────┤
│ Contrato             │ Índice         │ Ações                   │
│ 0042 — Maria Apare.  │ IPCA (2,43%)   │ [Preview] [Aplicar]   │
│ 0043 — José Ferreira │ IGPM (3,12%)   │ [Preview] [Aplicar]   │
└──────────────────────┴────────────────┴────────────────────────┘
```

**Preview de Reajuste:**
```
┌──────────────────────────────────────────────────────┐
│ Preview — Reajuste Contrato 0042                      │
├──────────────────────────────────────────────────────┤
│ Índice aplicado: IPCA — 2,43%                        │
│ Valor atual das parcelas:    R$   450,00             │
│ Valor após reajuste:         R$   460,94             │
│ Variação:                    + R$   10,94            │
│ Parcelas afetadas:           226 restantes           │
│                                                      │
│          [ ✅ Confirmar Reajuste ] [ Cancelar ]      │
└──────────────────────────────────────────────────────┘
```

### 6.6 CNAB (Remessa e Retorno Bancário)

**Gerar arquivo de remessa:**
```
[Financeiro] → [Arquivos de Remessa] → [Gerar Remessa]

Selecione os boletos → [Gerar arquivo CNAB 240]
→ Baixar arquivo .rem para enviar ao banco
```

**Processar retorno do banco:**
```
[Financeiro] → [Arquivos de Retorno] → [Upload Retorno]

Selecione o arquivo .ret do banco → [Processar]
→ Sistema marca automaticamente as parcelas como pagas
```

### 6.7 Relatórios

| Relatório | Descrição |
|---|---|
| Prestações a Pagar | Parcelas em aberto por período |
| Prestações Pagas | Histórico de recebimentos |
| Posição de Contratos | Status geral de todos os contratos |
| Previsão de Reajustes | Contratos com reajuste previsto |

Todos os relatórios podem ser **exportados em Excel ou PDF**.

### 6.8 Simulador de Antecipação

Acesse dentro do detalhe do contrato → **[Simulador]**

```
┌──────────────────────────────────────────────────────┐
│ Simulador de Antecipação — Contrato 0042             │
├──────────────────────────────────────────────────────┤
│ Antecipar até a parcela: [60 ▾]                     │
│ Data de referência:      [01/06/2021]                │
│                                                      │
│ Parcelas antecipadas: 58                             │
│ Valor sem desconto:   R$ 26.700,00                   │
│ Desconto (juros):     R$  4.200,00                   │
│ Total a pagar:        R$ 22.500,00                   │
│                                                      │
│    [ 📄 Gerar Recibo de Antecipação ]               │
└──────────────────────────────────────────────────────┘
```

---

## 7. Notificações

### 7.1 Régua de Cobrança

Define envios automáticos de e-mail e WhatsApp conforme a proximidade do vencimento:

```
[Notificações] → [Régua de Cobrança]

┌──────────────────────────────────────────────────────────────────┐
│ Régua de Cobrança                                  [+ Nova Regra]│
├──────────────────────────────────────────────────────────────────┤
│ Descrição              Canal       Quando          Ativo         │
│ Aviso 5 dias antes     E-mail      -5 dias         ✅ ON        │
│ Lembrete dia vecto     WhatsApp    Dia 0           ✅ ON        │
│ Cobrança 3 dias atrás  E-mail+WA   +3 dias         ✅ ON        │
│ Inadimplência grave    E-mail      +15 dias        ⬜ OFF       │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Templates de Mensagens

Modelos reutilizáveis com variáveis dinâmicas:

```
Olá {{comprador_nome}},

Sua parcela de R$ {{valor}} vence em {{data_vencimento}}.
Acesse seu boleto: {{link_boleto}}

Atenciosamente,
{{imobiliaria_nome}}
```

---

## 8. Administração

### 8.1 Configurações do Sistema

```
[Admin] → [Configurações do Sistema]

┌──────────────────────────────────────────────────────────────────┐
│ ⚙ Configurações do Sistema                                        │
├──────────────────────────────────────────────────────────────────┤
│ Parâmetros Gerais                                                  │
│  Percentual multa padrão:  [2,00] %                              │
│  Percentual juros padrão:  [1,00] % ao mês                       │
│  Prazo reajuste padrão:    [12] meses                            │
├──────────────────────────────────────────────────────────────────┤
│ [Exportar Parâmetros]                         [Salvar]           │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Gestão de Acessos de Usuários

Cria login para funcionários de Imobiliárias:

```
[Admin] → [Acessos de Usuários] → [+ Novo Acesso]

┌──────────────────────────────────────────────────────────────────┐
│ Novo Acesso de Usuário                                            │
├──────────────────────────────────────────────────────────────────┤
│ Usuário:       [funcionario@imobiliaria.com.br ▾]               │
│ Contabilidade: [M&S Contabilidade ▾]                            │
│ Imobiliária:   [Dizaty Imobiliária Ltda ▾]                      │
│ Pode editar:   ✅                                                │
│ Pode excluir:  ⬜                                                │
│ Ativo:         ✅                                                │
│                                                                   │
│                          [ Salvar ]                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9. Fluxos Comuns

### Fluxo 1 — Cadastrar um novo contrato manualmente
1. **Cadastros → Compradores → + Novo** (se o comprador não existe)
2. **Cadastros → Imóveis → + Novo** (se o imóvel não existe)
3. **Contratos → Novo Contrato** → preencher 4 etapas do wizard → **Concluir**

### Fluxo 2 — Importar contrato via PDF
1. **Contratos → Importar via IA** → enviar PDF
2. Aguardar extração (segundos)
3. Revisar os dados destacados → corrigir campos em amarelo
4. Clicar em **Confirmar e Cadastrar**

### Fluxo 3 — Registrar pagamento de parcela
1. **Financeiro → Parcelas do Mês**
2. Localizar a parcela → clicar em **💳 Pagar**
3. Informar data e valor → **Confirmar**

### Fluxo 4 — Aplicar reajuste anual
1. **Financeiro → Reajustes Pendentes**
2. Clicar em **Preview** para conferir o novo valor
3. Clicar em **Aplicar** → confirmar
4. Ou usar **Aplicar em Lote** para todos de uma vez

### Fluxo 5 — Processar retorno bancário (CNAB)
1. Baixar o arquivo `.ret` do internet banking
2. **Financeiro → Arquivos de Retorno → Upload Retorno**
3. Selecionar o arquivo → **Processar**
4. O sistema marca automaticamente as parcelas como pagas

### Fluxo 6 — Criar login para funcionário de Imobiliária
1. O funcionário deve ter uma conta criada em **Accounts → Registro** (ou pelo Admin Django)
2. **Admin → Acessos de Usuários → + Novo Acesso**
3. Selecionar usuário, contabilidade e imobiliária → **Salvar**

---

*Manual gerado em 2026-05-25 — Gestão de Contratos v3.1*
