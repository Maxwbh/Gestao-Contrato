<picture>
  <source media="(prefers-color-scheme: dark)" srcset="svg/ms-assinatura-horizontal-fundo-escuro.svg">
  <img src="svg/ms-assinatura-horizontal-fundo-claro.svg" alt="M&S do Brasil" height="56">
</picture>

# Marca M&S do Brasil neste repositório

Esta pasta guarda o **kit de marca v0.7** como foi entregue e explica onde ele
é usado no Gestão de Contratos. Nenhum arquivo do kit é editado aqui.

> **Situação (do kit):** conceito visual congelado; proposta ainda não
> homologada. Faltam a busca de anterioridade no INPI e a prova de impressão.

## Documentos do kit

| Arquivo | Conteúdo |
|---------|----------|
| [LEIAME.md](LEIAME.md) | Variantes, tamanhos mínimos, área de proteção, fontes |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões da marca |
| [TERMOS-DE-USO.md](TERMOS-DE-USO.md) | Minuta dos termos de uso (pendente de revisão jurídica) |
| [manual/](manual/) | Manual de identidade visual em PDF |
| `svg/` · `favicon/` · `tokens/` · `master/` · `scripts/` | Peças, tokens, geometria mestre e gerador |

A pasta `png/` do kit (3 MB) não foi versionada; os SVG cobrem os usos do
repositório e os PNG podem ser gerados por `scripts/gerar_kit.py`.

## Onde a marca entra

| Lugar | Peça |
|-------|------|
| README, CONTRIBUTING, SECURITY, `docs/README.md` | Assinatura horizontal `fundo-claro` / `fundo-escuro`, com troca automática pelo tema |
| Barra do sistema, menu lateral, rodapé e login | Símbolo `fundo-escuro` (`static/img/ms-simbolo-claro.svg`), 24 px ou mais |
| Aba do navegador | `static/img/favicon.svg` e `favicon.ico` |
| Ícone do portal do comprador (PWA) | `static/img/icon-180.png`, `icon-192.png`, `icon-512.png` |
| Cores e fontes da interface | `static/css/ms-tokens.css` (cópia de `tokens/tokens.css`) |

Ao atualizar o kit, substitua esta pasta e recopie os arquivos de `static/img/`
e `static/css/ms-tokens.css`.

### No README

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/svg/ms-assinatura-horizontal-fundo-escuro.svg">
  <img src="docs/brand/svg/ms-assinatura-horizontal-fundo-claro.svg" alt="M&S do Brasil" height="64">
</picture>
```

## Cores na interface

| Token | HEX | Uso no sistema |
|-------|-----|----------------|
| `--ms-marinho` | `#0D1B4B` | Barra superior, cabeçalho de cartão e de tabela |
| `--ms-acao` / `--ms-azul` | `#1D4ED8` | Botões, links, foco de campo |
| `--ms-acao-hover` | `#1E40AF` | Botão sob o cursor |
| `--ms-ciano` | `#06B6D4` | Destaque sobre fundo escuro |
| `--ms-ciano-escuro` | `#0891B2` | Gráficos e destaque sobre fundo claro |
| `--ms-sucesso` | `#047857` | Pago, concluído |
| `--ms-alerta` | `#B54708` | Pendente, atenção |
| `--ms-erro` | `#B42318` | Vencido, falha |
| `--ms-informacao` | `#0369A1` | Avisos informativos |
| `--ms-tinta` · `--ms-texto` · `--ms-apoio` | `#0B1533` · `#35425E` · `#5F6C88` | Títulos, corpo, legendas |
| `--ms-linha` · `--ms-nevoa` | `#DDE5F2` · `#F4F7FC` | Bordas, fundo de página |

As cores funcionais são da interface e nunca entram no logotipo. Vermelho só
aparece como erro.

## Tipografia

Inter Display nos títulos, Inter no texto, JetBrains Mono em código. Sem a fonte
instalada: Arial ou Calibri, e Consolas para código. O nome na assinatura já
está em curvas.

## Tom de voz

Técnico, direto e verificável: diga o que o sistema faz e mostre o comando ou o
arquivo. Títulos sem emoji; marcas de status em tabela (✅ / ⬜) são dado.

Projetos mantidos pela empresa assinam **"um projeto M&S do Brasil"**; forks de
terceiros, "com apoio da M&S do Brasil".

## Contatos

- **Empresa:** contato@msbrasil.inf.br · [msbrasil.inf.br](https://msbrasil.inf.br)
- **Maxwell da Silva Oliveira:** maxwbh@gmail.com
