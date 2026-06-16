# Benchmark de Mercado — Rotas e Telas para o Fluxo da Contadora

> Pesquisa de sistemas equivalentes (cobrança, boletos em lote, CNAB remessa/retorno, ERPs de
> imobiliária/loteamento) para identificar as **melhores rotas e telas** que tornem o trabalho da
> **contadora** (HU-23/HU-24) mais **simples e fluido**.
> Data: 2026-06-16. Fontes ao final.

---

## 1. Sistemas pesquisados

| Sistema | Segmento | O que faz bem (aplicável) |
|---------|----------|---------------------------|
| **Superlógica (Imobiliárias/Condomínios)** | Gestão imobiliária | Fluxo linear de cobrança: selecionar títulos → "Marcar para remessa" → "Gerar remessa" → **resumo de conferência** → confirmar → "Baixar arquivo remessa" → processar retorno. Integração (PJBank) que **elimina a rotina diária de CNAB** (registro online + conciliação automática) |
| **SGL — Sistema de Gestão de Loteamentos** | Loteamento (match direto) | Módulo financeiro único: Contas a Receber, **Conciliação Bancária**, **régua de cobrança estruturada**, notificações por e-mail/WhatsApp, exportação/importação remessa/retorno, **reajuste automático de receitas**, **portal do cliente** (2ª via, extrato, quitação/antecipação) |
| **ERPFlex / Sankhya / Lotewin / Nuvem ERP** | ERP genérico/loteamento | Geração de boletos em lote: **marcar títulos do mesmo banco/carteira** → "Exportar Remessa" → importar Retorno → **baixa automática**. Validação de agrupamento por banco/carteira |
| **Asaas** | Cobrança/recebíveis | **Régua de cobrança visual** por etapas (antes: criação, alteração, lembretes 5/10/15/30 dias e no dia; depois: 1/3/7/15/30 dias; após pagamento: confirmação), multicanal (WhatsApp/SMS/e-mail/ligação/correios), configurável no cadastro do cliente |
| **TecnoSpeed / Nexxera / Boleto Cloud / bancos (BB, Bradesco, Sicredi)** | Infra de boleto | **Boleto Híbrido (Bolepix/QR Pix)** com **registro online via API** — elimina remessa/retorno; **conciliação 2-way** informa se o pagamento veio por boleto (COMPE) ou Pix. Regulamentação do Banco Central vigente desde fev/2025 |

---

## 2. Padrões de UX recorrentes (o que torna fluido)

1. **Um fluxo linear, não telas soltas.** Os melhores sistemas tratam o ciclo mensal como um
   **passo a passo** (selecionar → conferir → gerar → baixar → enviar → conciliar), com um
   indicador de progresso. O operador nunca se pergunta "qual a próxima etapa".
2. **Ação combinada de um clique.** "Gerar e Baixar" / "Exportar Remessa" encadeiam geração +
   download sem telas intermediárias. Ação em massa ("Gerar Tudo") como botão de destaque.
3. **Conferência prévia agrupada por banco/carteira.** Toda geração mostra um **resumo** (banco,
   layout, quantidade, valor) antes de confirmar — evita erro e dá confiança.
4. **Seleção inteligente com defaults.** Tudo elegível já vem pré-selecionado; mês atual por
   padrão; "selecionar todos"; itens inelegíveis (vencidos, sem nº, já enviados) **escondidos**.
5. **Régua de cobrança visual.** Linha do tempo configurável (antes/depois do vencimento) por
   canal — o operador desenha a régua, o sistema dispara sozinho.
6. **Conciliação automática / retorno em 1 passo.** Upload do retorno **já dá baixa**; KPIs de
   "% conciliado", pendentes e rejeitados num painel único.
7. **Portal do cliente** para 2ª via, extrato e quitação/antecipação — **reduz a demanda
   operacional** que chega à contadora.
8. **Norte estratégico: registro online + Bolepix.** A maior simplificação do mercado é
   **deixar de manusear arquivos**: o boleto é registrado na criação (via API) e a baixa é
   automática (2-way COMPE/Pix). Onde existe, a remessa/retorno some do dia a dia.

---

## 3. Diagnóstico do nosso sistema (HU-23/HU-24)

**O que já está alinhado ao melhor do mercado:**
- Conferência prévia agrupada por (banco, layout) — ✅ (HU-23).
- "Gerar e Baixar" (1 clique) e "Gerar Todos" tolerante a falha — ✅ (HU-23).
- Retorno em 1 passo (upload + auto-processo) com KPIs e rejeição que devolve boleto a elegível — ✅ (HU-23).
- Defaults inteligentes, exclusão silenciosa de inelegíveis, anti-duplicidade — ✅ (HU-23).
- Régua de cobrança configurável e multicanal — ✅ (HU-20).
- Portal do comprador (2ª via, extrato, quitação) — ✅ (HU-21).

**Lacunas frente ao mercado (oportunidades):**
- As etapas vivem em **rotas separadas** (`/financeiro/boletos/`, `/financeiro/remessa/`,
  `/financeiro/retorno/`) — falta um **fio condutor** que conduza a contadora de ponta a ponta.
- Não há **encadeamento de um clique** entre **gerar boletos (HU-24) → gerar remessa (HU-23)**.
- A régua de cobrança (HU-20) é configurável, mas **sem editor visual em linha do tempo**.
- Conciliação ainda depende de **upload manual** do retorno (sem agendamento/automação).
- Registro continua por **arquivo CNAB**; não há **registro online/Bolepix** (norte estratégico).

---

## 4. Recomendações de rotas e telas (priorizadas)

### P1 — Hub "Cobrança do Mês" com passo a passo (maior ganho de fluidez)

Criar **uma rota guia** que una as três etapas num *stepper* horizontal, reaproveitando as telas
existentes como passos (sem reescrevê-las):

```
/financeiro/cobranca/                → Hub do ciclo mensal (stepper 1·2·3)
   Passo 1 — Gerar Boletos   → embute /financeiro/boletos/   (HU-24)
   Passo 2 — Gerar Remessa   → embute /financeiro/remessa/   (HU-23 tela 1)
   Passo 3 — Receber Retorno → embute /financeiro/retorno/   (HU-23 tela 2)
```

- Cabeçalho com indicador de progresso e KPIs do mês (a gerar · a enviar · a conciliar).
- Cada passo "conclui" e habilita o próximo; a contadora nunca procura "o que fazer agora".
- Menu principal passa a ter **1 entrada** ("Cobrança do Mês") em vez de 3 itens dispersos.

### P1 — Encadeamento "Gerar boletos e já preparar a remessa"

No fim da HU-24 já existe o atalho "Gerar Remessa destes boletos →". Evoluir para uma **ação
combinada opcional** ("Gerar boletos do mês **e** abrir a remessa") que leva direto ao Passo 2 com
os grupos já montados — espelha o "Gerar e Baixar" que o mercado usa para reduzir cliques.

### P2 — Editor visual da régua de cobrança

Tela `/notificacoes/regua/` com **linha do tempo** (marcos antes/depois do vencimento) e, em cada
marco, os canais ativos (e-mail/WhatsApp/SMS). Hoje a régua é configurável (HU-20), mas um editor
visual (padrão Asaas) deixa o desenho da cobrança óbvio e reduz erro de configuração.

### P2 — Painel de conciliação com indicadores de saúde

Consolidar no painel de retorno/conciliação os KPIs que o mercado destaca: **% conciliado no mês**,
valor pendente, **boletos rejeitados** (com 1 clique para reincluir na próxima remessa) e
**aging** de inadimplência. Já temos a base (dashboard de conciliação) — falta o recorte por
"saúde do mês".

### P3 — Automação do retorno (reduzir o upload manual)

Oferecer **agendamento de importação** do `.ret` (tarefa periódica via cron-job.org) ou recepção
por integração, espelhando a automação "fim da rotina diária de CNAB" do mercado. Mantém o upload
manual como alternativa.

### Estratégico (norte) — Registro online + Bolepix (Pix no boleto)

A maior simplificação possível para a contadora é **não manusear arquivos**:
- **Boleto Híbrido (Bolepix/QR Pix)**: um único título pago por linha digitável **ou** Pix —
  aumenta conversão e antecipa a baixa.
- **Registro online via API**: o boleto é registrado **na geração** (HU-24), tornando a remessa
  (HU-23 tela 1) **desnecessária** para os bancos que suportam; a baixa vira **automática**
  (conciliação 2-way COMPE/Pix), reduzindo a HU-23 tela 2 a exceções.
- Caminho técnico: evoluir o serviço de geração (**BRCobrança**) ou integrar um provedor de
  registro online; manter o CNAB como *fallback* para bancos sem API. Fora do escopo imediato,
  mas é a direção que o mercado (e o Banco Central, desde fev/2025) já tomou.

---

## 5. Mapa de navegação recomendado (persona Contadora)

```
Menu: "Cobrança do Mês"  →  /financeiro/cobranca/   (hub com stepper)
        │
        ├─ 1. Gerar Boletos      (HU-24)  → defaults: mês atual, todas as imobiliárias acessíveis
        │       └─ [Gerar tudo do mês]  (1 clique, tolerante a falha)
        │       └─ [Gerar e já preparar remessa →]   (encadeia para o passo 2)
        │
        ├─ 2. Gerar Remessa      (HU-23/1) → conferência agrupada por banco/layout
        │       └─ [Gerar e Baixar] por banco  ·  [Gerar Todos] (ZIP)
        │       └─ [Marcar como Enviada]  (após baixar)
        │
        └─ 3. Receber Retorno    (HU-23/2) → upload .ret = baixa automática
                └─ KPIs do mês: % conciliado · pendentes · rejeitados (1 clique p/ reincluir)

Apoio (reduzem demanda à contadora):
   /notificacoes/regua/   → editor visual da régua (HU-20)
   Portal do Comprador    → 2ª via, extrato, quitação/antecipação (HU-21)
```

---

## 6. Resumo executivo

- O nosso fluxo **já cobre o essencial** que os líderes de mercado oferecem (conferência agrupada,
  geração em lote, "gerar e baixar", retorno em 1 passo, régua multicanal, portal).
- O maior ganho de **fluidez** não é uma nova funcionalidade e sim **costurar as 3 telas num único
  hub com passo a passo** e **encadear geração de boletos → remessa** — reduzindo a carga cognitiva
  ("o que faço agora?") e o número de cliques.
- O maior ganho **estratégico** é migrar para **registro online + Bolepix**, que elimina o
  vai-e-vem de arquivos CNAB — a direção que Superlógica (PJBank), Asaas e a infraestrutura de
  boleto (TecnoSpeed/Nexxera/bancos) já seguem desde a regulamentação do Bolepix (fev/2025).

---

## Fontes

- [Superlógica — Funcionalidades para Imobiliárias](https://superlogica.com/recursos/funcionalidades-imobiliarias/)
- [Superlógica — Como gerar arquivos de remessa e retorno bancário](https://imobiliarias.superlogica.com/hc/pt-br/articles/360034169393-Como-gerar-arquivos-de-remessa-e-retorno-banc%C3%A1rio-de-boletos)
- [Superlógica — Automatizar envio e recebimento do arquivo remessa/retorno](https://superlogica.com/como-automatizar-arquivo-remessa-e-retorno/)
- [SGL — Sistema de Gestão de Loteamentos](https://sistemasgl.com.br/)
- [ERPFlex — Boletos e Remessa/Retorno (CNAB)](https://docsnew.erpflex.com.br/boletos-e-remessaretorno-cnab/)
- [Sankhya — Geração de Boletos para Loteamentos](https://ajuda.sankhya.com.br/hc/pt-br/articles/360057139513-Gera%C3%A7%C3%A3o-Boletos-Loteamentos)
- [Asaas — Régua de Cobrança automatizada](https://www.asaas.com/regua-de-cobranca)
- [Omie — CNAB: Remessa e Retorno](https://www.omie.com.br/funcionalidades/cnab/)
- [TecnoSpeed — Boleto Híbrido (Bolepix/QR Pix)](https://blog.tecnospeed.com.br/cluster-boleto-hibrido/)
- [Nexxera — Cobrança Online (Boleto, QR Code Pix e Boleto Híbrido)](https://cobrancaonlinenexxera.docs.apiary.io/)
- [Sicredi — Tipos de cobrança (Internet, aplicativo)](https://www.sicredi.com.br/site/recebimentos-para-empresa/cobranca/)
