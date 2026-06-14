# Análise do Sistema — Hub Central

> **Diretório central de análise de produto** do Sistema de Gestão de Contratos.
> Reúne **Histórias de Usuário (HUs)**, **mockups/protótipos** e a análise de
> negócio em um único lugar. Toda nova HU, wireframe ou estudo de funcionalidade
> deve ser criado aqui.
>
> Desenvolvido por **Maxwell da Silva Oliveira** (maxwbh@gmail.com) — M&S do Brasil LTDA
> Última atualização: 2026-06-14

---

## Estrutura

```
docs/analise/
├── README.md              ← você está aqui (hub central)
├── historias-usuario/     ← Histórias de Usuário (HU-01 … HU-23) + INDICE
│   ├── INDICE.md          ← índice mestre: matriz de rastreabilidade + fluxo macro
│   ├── HU-01.md … HU-23.md
└── mockups/               ← protótipos visuais / wireframes (HTML, imagens)
    └── HU-23-remessa-layout.html
```

---

## Histórias de Usuário

📑 **[Índice Mestre das HUs →](historias-usuario/INDICE.md)** — matriz de rastreabilidade
(HU → modelos → services → views), personas, fluxo macro e regras de negócio globais.

| ID | Nome | Módulo | Status |
|----|------|--------|--------|
| [HU-01](historias-usuario/HU-01.md) | Criação de Contrato (Wizard) | `contratos` | ✅ |
| [HU-02](historias-usuario/HU-02.md) | Geração de Parcelas | `financeiro` | ✅ |
| [HU-03](historias-usuario/HU-03.md) | Gerar Boleto Individual | `financeiro` | ✅ |
| [HU-04](historias-usuario/HU-04.md) | Pagamento de Parcela | `financeiro` | ✅ |
| [HU-05](historias-usuario/HU-05.md) | Reajuste de Parcelas | `financeiro` | ✅ |
| [HU-06](historias-usuario/HU-06.md) | Bloqueio de Boleto por Reajuste | `contratos`/`financeiro` | ✅ |
| [HU-07](historias-usuario/HU-07.md) | Gerar Carnê (Lote de Boletos) | `financeiro` | ✅ |
| [HU-08](historias-usuario/HU-08.md) | Segunda Via de Boleto | `financeiro` | ✅ |
| [HU-09](historias-usuario/HU-09.md) | Quitação Manual / Antecipação | `financeiro` | ✅ |
| [HU-10](historias-usuario/HU-10.md) | Quitação via OFX (Extrato Bancário) | `financeiro` | ✅ |
| [HU-11](historias-usuario/HU-11.md) | Calcular Rescisão Contratual | `contratos` | ✅ |
| [HU-12](historias-usuario/HU-12.md) | Calcular Cessão de Direitos | `contratos` | ✅ |
| [HU-13](historias-usuario/HU-13.md) | Link Público de Boleto | `financeiro` | ✅ |
| [HU-14](historias-usuario/HU-14.md) | Gestão de Prestações Intermediárias | `contratos` | ✅ |
| [HU-15](historias-usuario/HU-15.md) | Importação de Índices Econômicos | `contratos` | ✅ |
| [HU-16](historias-usuario/HU-16.md) | CNAB — Remessa e Retorno Bancário | `financeiro` | ✅ |
| [HU-17](historias-usuario/HU-17.md) | Renegociação de Parcelas | `financeiro` | ✅ |
| [HU-18](historias-usuario/HU-18.md) | Relatórios Financeiros e Dashboard | `financeiro` | ✅ |
| [HU-19](historias-usuario/HU-19.md) | Chatbot WhatsApp — Atendimento Automático | `notificacoes` | ✅ (parcial) |
| [HU-20](historias-usuario/HU-20.md) | Notificações e Cobrança Automática | `notificacoes` | ✅ |
| [HU-21](historias-usuario/HU-21.md) | Portal do Comprador — Autoatendimento | `portal_comprador` | ✅ |
| [HU-22](historias-usuario/HU-22.md) | Mapa Interativo de Lotes | `core` | ✅ (parcial) |
| [HU-23](historias-usuario/HU-23.md) | Envio Mensal de Remessa CNAB (Contadora) | `financeiro` | ✅ |

---

## Mockups / Protótipos

Wireframes e protótipos de alta fidelidade que acompanham as HUs.

| Mockup | HU | Descrição |
|--------|----|-----------|
| [HU-23-remessa-layout.html](mockups/HU-23-remessa-layout.html) | HU-23 | Tela de Gestão de Arquivos Remessa (Tailwind + Material Symbols) |

> Para abrir um mockup HTML, faça o download e abra no navegador (usam CDN do Tailwind).

---

## Convenções

- **Numeração de HU**: sequencial a partir de `HU-01`. A próxima HU livre é **HU-24**.
- **⚠️ Numeração distinta no ROADMAP**: o [`ROADMAP.md`](../../ROADMAP.md) usa uma numeração
  *interna* `HU-360` (e sub-tarefas `HU-01..HU-13` da seção 13) que é **independente**
  deste índice. Ao referenciar, use o prefixo `HU-360/HU-xx` para evitar ambiguidade.
- **Mockups**: nomear como `HU-XX-<tela>.html` (ou `.png`), sempre vinculados a uma HU.
- **Status**: ✅ implementado · 📋 especificado (aguardando implementação) · 🚧 em andamento.

---

## Documentação relacionada (fora deste hub)

- [Documentação geral](../README.md) — manuais, deploy, APIs, arquitetura
- [SISTEMA.md](../../SISTEMA.md) — o que está implementado (técnico)
- [ROADMAP.md](../../ROADMAP.md) — pendentes e prioridades
