# Prompts de Design para claude.ai/design — HU-25 e HU-26

> **Por que este arquivo existe:** os mockups de referência são os HTML em
> `docs/analise/mockups/HU-25-cobranca-hub-layout.html` e `HU-26-conciliacao-saude-layout.html`.
> Este documento traz **prompts prontos para colar em https://claude.ai/design** (a ferramenta de
> design da Claude na web), caso você queira gerar/iterar as telas por lá. Cada prompt já embute o
> sistema de design (ContractHub), o layout, os componentes, os dados de exemplo e os estados.
>
> Cole o bloco "PROMPT" correspondente no claude.ai/design. Ajuste números/textos à vontade.

---

## Sistema de Design (ContractHub) — colar no início de qualquer prompt

```
Estilo "ContractHub", aplicação web financeira (desktop-first, 1280px), tom corporativo e denso de dados.
Tipografia: Inter (400/600/700). Ícones: Material Symbols Outlined.
Paleta:
- primary (navy) #091426
- secondary (azul ação) #0058be
- success #22c55e · warning #f59e0b · danger #ef4444 · error #ba1a1a
- background #f8f9ff · branco dos cards #ffffff
- borda dos cards (surface-border) #e2e8f0
- realces suaves: surface-container-low #eff4ff, surface-container-high #dce9ff
- texto secundário (on-surface-variant) #45474c
Cards: cantos arredondados (xl ~8px / full ~12px), sombra sutil, borda surface-border.
Badges de status: pílula arredondada com cor semântica (cinza=pendente, azul=registrado/secondary,
verde=concluído/success, âmbar=aviso/warning, vermelho=erro/danger).
Layout base: sidebar fixa à esquerda (256px) com itens [Dashboard, Contratos, Cobrança do Mês,
Conciliação, Relatórios] e avatar "Maria Contadora / Cobrança"; top bar fixa com busca e ícones
(notificações, configurações, ajuda); conteúdo com breadcrumb + título + subtítulo.
Idioma: português do Brasil. Valores em R$ (pt-BR).
```

---

## HU-25 — Hub "Cobrança do Mês" (assistente de ciclo mensal)

**PROMPT (colar no claude.ai/design, após o bloco de Sistema de Design):**

```
Crie a tela "Cobrança do Mês" — um HUB que conduz a contadora pelo ciclo mensal em PASSO A PASSO.

Cabeçalho:
- Breadcrumb: Financeiro / Cobrança do Mês
- Título "Cobrança do Mês" + subtítulo "Gere os boletos, envie a remessa e concilie o retorno — tudo em um fluxo guiado."
- Botão primário de destaque (navy): "Gerar boletos do mês e preparar remessa →" (ícone bolt + arrow_forward)

Filtros compartilhados (uma linha, card branco): seletor "Imobiliária" (default Todas) e
"Competência" (default Junho 2026), com a nota à direita "Filtros aplicados aos 3 passos".

Resumo do Ciclo — 4 KPI cards:
1. A Gerar = 142 (boletos elegíveis)
2. A Enviar = 3 (arquivos / contas)
3. A Conciliar = 58 (boletos enviados)
4. Ciclo Concluído = 38% (card azul com barra de progresso)

STEPPER horizontal com 3 passos conectados por linha:
- Passo 1 "Gerar Boletos": círculo azul preenchido (ícone bolt), badge "EM ANDAMENTO" (âmbar),
  legenda "142 a gerar" — este é o passo RECOMENDADO (destaque com anel/ring azul).
- Passo 2 "Gerar Remessa": círculo cinza (ícone send), badge "PENDENTE" (cinza), legenda "3 contas".
- Passo 3 "Receber Retorno": círculo cinza (ícone account_balance), badge "PENDENTE", legenda "58 a conciliar".

Painel do passo ATIVO (Passo 1) — card com cabeçalho "Passo 1 — Gerar Boletos" e dois botões
("Gerar Boletos" outline + "Concluir e ir para Remessa →" navy). Abaixo, tabela com colunas:
Imobiliária/Contrato | Elegíveis | Bloqueados | Já gerados | Valor | Ação.
Linhas de exemplo:
- Lagoa Real · CTR-2026-018 | 3 | 0 | 1 | R$ 5.400,00 | "Gerar deste"
- Lagoa Real · CTR-2026-022 | 2 | 1 | 0 | R$ 3.600,00 | "ver reajuste →"  (linha com fundo âmbar suave, pois há bloqueio por reajuste)
- Lagoa Real · CTR-2026-031 | 6 | 0 | 0 | R$ 10.800,00 | "Gerar deste"

Comportamento a comunicar visualmente: o stepper mostra onde a contadora está; o passo recomendado
é o primeiro pendente; navegação livre entre passos; a ação encadeada do topo gera os boletos e leva
ao Passo 2 já montado. Linhas bloqueadas por reajuste NÃO geram (destaque âmbar + link para resolver).
```

**Telas/variações úteis para pedir no claude.ai/design:**
- Estado "Passo 2 ativo" (conferência de remessa agrupada por banco/layout, botões "Gerar e Baixar").
- Estado "Passo 3 ativo" (cards de upload de retorno por banco).
- Estado "Ciclo concluído" (banner verde "Ciclo de Junho/2026 concluído").

---

## HU-26 — Painel de Conciliação & Saúde da Cobrança

**PROMPT (colar no claude.ai/design, após o bloco de Sistema de Design):**

```
Crie a tela "Conciliação & Saúde da Cobrança" — visão de fechamento do mês: o que entrou, o que falta,
o que venceu e o que foi rejeitado.

Cabeçalho:
- Breadcrumb: Financeiro / Cobrança / Conciliação & Saúde
- Título "Conciliação & Saúde da Cobrança" + subtítulo "O que entrou, o que falta e o que está vencido — por período e imobiliária."
- À direita: seletor Imobiliária, seletor Competência (Junho 2026) e botão "Exportar" (outline, ícone download).

KPI cards (5):
1. % Conciliado = 80% (card azul com barra de progresso) — indicador-mestre
2. Recebido = R$ 80.000 (verde) · "112 baixas"
3. Pendente = R$ 20.000 · "30 boletos"
4. Vencido = R$ 8.400 (card vermelho suave) · "11 parcelas"
5. Rejeitados = 4 (card âmbar) · link "reincluir →"

Duas colunas:
A) "Recebido por origem" — barras horizontais com legenda colorida:
   CNAB (azul) R$ 50.000 (62%) · PIX (verde) R$ 20.000 (25%) · OFX (âmbar) R$ 8.000 (10%) · Manual (navy) R$ 2.000 (3%).
B) "Aging de inadimplência (clique para filtrar)" — 4 botões/células:
   A vencer R$ 11.600 (19) · 1–30 R$ 4.200 (6, âmbar) · 31–60 R$ 2.800 (3) · 60+ R$ 1.400 (2, vermelho).

Tabela "Pendências do período" (30 boletos não pagos), colunas:
Contrato/Comprador | Vencimento | Atraso | Valor atualizado | Estado | Ações.
Linhas:
- CTR-2026-018 · João Souza | 10/06/2026 | 6 d (âmbar) | R$ 1.832,40 | badge VENCIDO (âmbar) | ações: Baixa · 2ª via · Notificar
- CTR-2026-031 · Ana Lima | 20/06/2026 | — | R$ 1.800,00 | badge REGISTRADO (azul) | ações: Baixa · Notificar

Duas seções finais lado a lado:
- "Boletos rejeitados (4)" (card borda âmbar): cada item com motivo (ex.: "CEP do sacado inválido (cód. 03)")
  e botão navy "Reincluir na remessa".
- "Recém-conciliados": mini-tabela data · contrato · valor · badge de origem (PIX verde / CNAB azul / OFX âmbar).

Comunicar: % Conciliado é em VALOR (recebido / recebido+pendente); origem do recebido vem de
4 fontes (CNAB/PIX/OFX/Manual); buckets de aging são clicáveis e filtram a tabela; reincluir devolve
o boleto rejeitado para a próxima remessa.
```

---

## Observação sobre o ambiente

O assistente que gerou estes artefatos (Claude Code, via terminal) **não opera o claude.ai/design**
diretamente — por isso a entrega aqui são (1) os **mockups HTML** de referência e (2) estes
**prompts prontos** para você gerar/iterar as telas no claude.ai/design. Os HTML podem ainda ser
abertos direto no navegador ou colados no claude.ai como ponto de partida.
