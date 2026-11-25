# M&S do Brasil — kit de marca v0.7

**Situação:** conceito visual congelado; proposta ainda não homologada. Faltam a busca de anterioridade no INPI e a prova de impressão.

## O que há no kit

| Pasta | Conteúdo |
|---|---|
| `manual/` | Manual de identidade visual em PDF (15 páginas) |
| `master/` | Geometria mestre do símbolo |
| `svg/` | Assinatura horizontal, assinatura vertical e símbolo, cada um em 4 variantes; ícone em 2 |
| `png/` | As mesmas peças em duas resoluções, com fundo transparente |
| `favicon/` | `favicon.svg`, `favicon.ico` (16, 32 e 48 px) e PNG de 16 a 512 px |
| `tokens/` | `paleta.json` e `tokens.css` |
| `scripts/` | `gerar_kit.py`, que gera todos os arquivos acima a partir de uma única geometria |

Ainda não há pasta `impressao/` (depende da prova gráfica) nem `templates/` (proposta, relatório, apresentação e e-mail ficam para a implantação).

## Variantes

O sufixo diz onde a peça é aplicada ou como ela é:

| Sufixo | Uso |
|---|---|
| `fundo-claro` | Marinho e ciano escuro, para fundo branco ou claro |
| `fundo-escuro` | Branco e ciano, para fundo marinho ou escuro |
| `negativa` | Toda branca, para fundo azul ou colorido |
| `monocromatica` | Toda em uma cor (#0B1533), para impressão em uma tinta |

Os cruzamentos dos losangos são recortes reais: a área é transparente e a mesma peça serve para qualquer fundo do seu grupo.
As variantes `fundo-escuro` e `negativa` em PNG são brancas sobre transparente; abra sobre um fundo escuro para ver.

## Tamanho mínimo em tela

Alturas medidas na arte, sem margem (todos os arquivos são recortados rente à marca).

| Versão | Altura mínima |
|---|---|
| Assinatura horizontal | 28 px (101 px de largura) |
| Assinatura vertical | 72 px |
| Símbolo isolado | 24 px |
| Ícone quadrado | 32 px |
| Favicon | 16 px; de 32 px em diante use o ícone |

Impressão (proposta, a validar em prova): horizontal 8 mm, vertical 22 mm, símbolo 6 mm.

## Área de proteção

X = um terço da altura visível da assinatura, em todos os lados. Numa assinatura horizontal de 42 px de altura, X = 14 px.

## Fontes

O nome está convertido em curvas (Inter Display SemiBold e Inter SemiBold, SIL Open Font License). Nenhuma fonte precisa estar instalada para exibir a marca.

## Gerar de novo

```
pip install fonttools shapely pillow playwright && playwright install chromium
python3 scripts/gerar_kit.py
```

Nenhum SVG é editado à mão. Mude a geometria ou as cores em `scripts/gerar_kit.py`, gere de novo e registre no `CHANGELOG.md`.

## Uso da marca

Veja `TERMOS-DE-USO.md`. A licença dos projetos de código aberto da M&S não autoriza o uso da marca da empresa.
