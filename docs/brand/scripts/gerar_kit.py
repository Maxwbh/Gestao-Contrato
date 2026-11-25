#!/usr/bin/env python3
"""Gera o kit de marca da M&S do Brasil a partir de uma única geometria.

Uso:  python3 scripts/gerar_kit.py            (grava na pasta do kit)
Dependências: fonttools, shapely, pillow e, para os PNG, playwright (chromium).
Fontes: Inter Display SemiBold e Inter SemiBold (SIL OFL). Ajuste os caminhos em
MS_FONTE_NOME e MS_FONTE_SUB se estiverem em outro lugar.
Nenhum SVG do kit é editado à mão: mude aqui e gere de novo.
"""
import json, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from shapely.geometry import LinearRing, LineString, Polygon

VERSAO = "0.7"
FONTE_NOME = os.environ.get("MS_FONTE_NOME", "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf")
FONTE_SUB = os.environ.get("MS_FONTE_SUB", "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf")

COR = {"marinho": "#0D1B4B", "azul": "#1D4ED8", "ciano": "#06B6D4", "ciano-escuro": "#0891B2",
       "tinta": "#0B1533", "texto": "#35425E", "apoio": "#5F6C88", "linha": "#DDE5F2",
       "nevoa": "#F4F7FC", "branco": "#FFFFFF"}
# variante: (losango 1, losango 2, nome, &)
VARIANTES = {
    "fundo-claro": (COR["marinho"], COR["ciano-escuro"], COR["marinho"], COR["ciano-escuro"]),
    "fundo-escuro": (COR["branco"], COR["ciano"], COR["branco"], COR["ciano"]),
    "negativa": (COR["branco"],) * 4,
    "monocromatica": (COR["tinta"],) * 4,
}

# ---------- geometria do símbolo (grade 80 x 64) ----------
MEIA, TRACO, VAO = 22, 4, 2          # meia-diagonal, espessura do traço, vão do cruzamento
C1, C2, CY = 28, 52, 32              # centros dos losangos

def _anel(cx):
    r = LinearRing([(cx - MEIA, CY), (cx, CY - MEIA), (cx + MEIA, CY), (cx, CY + MEIA)])
    return r.buffer(TRACO / 2, quad_segs=8, join_style="round")

def _recorte(y):  # faixa ao longo do traço que passa por cima, no cruzamento (40, y)
    return LineString([(36, y - 4), (44, y + 4)]).buffer(TRACO / 2 + VAO, cap_style="flat")

def _d(geom, casas=2):
    polys = getattr(geom, "geoms", [geom]); out = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)[:-1]
            out.append("M" + " L".join(f"{round(x, casas):g} {round(y, casas):g}" for x, y in pts) + " Z")
    return " ".join(out)

# em cima passa o losango 1; embaixo passa o losango 2. Quem passa por baixo é recortado.
LOSANGO_1 = _d(_anel(C1).difference(_recorte(42)))
LOSANGO_2 = _d(_anel(C2).difference(_recorte(22)))
SIMBOLO_BOX = (C1 - MEIA - TRACO / 2, CY - MEIA - TRACO / 2, 2 * MEIA + (C2 - C1) + TRACO, 2 * MEIA + TRACO)  # x, y, w, h = 4, 8, 72, 48

def simbolo_paths(c1, c2):
    return (f'<path fill-rule="evenodd" d="{LOSANGO_1}" fill="{c1}"/>'
            f'<path fill-rule="evenodd" d="{LOSANGO_2}" fill="{c2}"/>')

# ---------- texto em curvas ----------
_fontes = {}
def _fonte(caminho):
    if caminho not in _fontes: _fontes[caminho] = TTFont(caminho)
    return _fontes[caminho]

def texto(caminho, s, corpo, entreletra=0.0):
    """Devolve (d, largura). Origem na linha de base; entreletra em milésimos do corpo."""
    f = _fonte(caminho); gs = f.getGlyphSet(); cmap = f.getBestCmap(); k = corpo / f["head"].unitsPerEm
    pen = SVGPathPen(gs, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip(".")); x = 0.0
    for ch in s:
        g = cmap[ord(ch)]; gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x, 0)))
        x += gs[g].width * k + entreletra * corpo / 1000
    return pen.getCommands(), x - entreletra * corpo / 1000

def _alt_maiuscula(caminho):
    f = _fonte(caminho); return f["OS/2"].sCapHeight / f["head"].unitsPerEm

def nome(cor_nome, cor_e, corpo, corpo_sub):
    """Bloco “M&S / DO BRASIL”. Devolve (svg, largura, altura); origem no canto superior esquerdo."""
    dm, wm = texto(FONTE_NOME, "M", corpo); de, we = texto(FONTE_NOME, "&", corpo); ds, ws = texto(FONTE_NOME, "S", corpo)
    larg = wm + we + ws; cap = corpo * _alt_maiuscula(FONTE_NOME); resp = corpo * 0.24
    d0, w0 = texto(FONTE_SUB, "DO BRASIL", corpo_sub)
    el = (larg - 1.5 * corpo / 34 - w0) / 8 / corpo_sub * 1000      # espaça até a largura do “M&S”
    dsub, _ = texto(FONTE_SUB, "DO BRASIL", corpo_sub, el)
    alt = cap + resp + corpo_sub * _alt_maiuscula(FONTE_SUB)
    svg = (f'<g transform="translate(0,{cap:.2f})"><path d="{dm}" fill="{cor_nome}"/>'
           f'<path transform="translate({wm:.2f})" d="{de}" fill="{cor_e}"/>'
           f'<path transform="translate({wm + we:.2f})" d="{ds}" fill="{cor_nome}"/></g>'
           f'<path transform="translate({0.8 * corpo / 34:.2f},{alt:.2f})" d="{dsub}" fill="{cor_nome}"/>')
    return svg, larg, alt

# ---------- montagem das versões (todas recortadas rente à arte) ----------
def _svg(w, h, altura, corpo, rotulo, vb_x=0, vb_y=0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x:g} {vb_y:g} {w:.2f} {h:.2f}" width="{altura * w / h:.0f}" height="{altura:g}" '
            f'role="img" aria-label="{rotulo}">{corpo}</svg>')

def svg_simbolo(variante="fundo-claro", altura=512):
    c1, c2, _, _ = VARIANTES[variante]; x, y, w, h = SIMBOLO_BOX
    return _svg(w, h, altura, simbolo_paths(c1, c2), "Símbolo M&amp;S do Brasil", x, y)

HORIZONTAL_VAO = 10   # distância entre símbolo e nome, na unidade da assinatura
def svg_horizontal(variante="fundo-claro", altura=256):
    c1, c2, cn, ce = VARIANTES[variante]; n, wn, hn = nome(cn, ce, 34, 10.5)
    x, y, w, h = SIMBOLO_BOX; k = hn / h                         # símbolo com a mesma altura do bloco do nome
    corpo = (f'<g transform="scale({k:.4f}) translate({-x:g},{-y:g})">{simbolo_paths(c1, c2)}</g>'
             f'<g transform="translate({w * k + HORIZONTAL_VAO:.2f},0)">{n}</g>')
    return _svg(w * k + HORIZONTAL_VAO + wn, hn, altura, corpo, "M&amp;S do Brasil")

VERTICAL_VAO = 8
def svg_vertical(variante="fundo-claro", altura=512):
    c1, c2, cn, ce = VARIANTES[variante]; n, wn, hn = nome(cn, ce, 28, 8.6)
    x, y, w, h = SIMBOLO_BOX
    corpo = (f'<g transform="translate({-x:g},{-y:g})">{simbolo_paths(c1, c2)}</g>'
             f'<g transform="translate({(w - wn) / 2:.2f},{h + VERTICAL_VAO:.2f})">{n}</g>')
    return _svg(w, h + VERTICAL_VAO + hn, altura, corpo, "M&amp;S do Brasil")

def svg_icone(fundo="escuro", lado=512, redondo=False):
    bg = COR["marinho"] if fundo == "escuro" else COR["branco"]
    c1, c2, _, _ = VARIANTES["fundo-escuro" if fundo == "escuro" else "fundo-claro"]
    forma = f'<circle cx="32" cy="32" r="32" fill="{bg}"/>' if redondo else f'<rect width="64" height="64" rx="14" fill="{bg}"/>'
    k = 0.6 if redondo else 0.7
    corpo = f'{forma}<g transform="translate({32 - 40 * k:.2f},{32 - 32 * k:.2f}) scale({k})">{simbolo_paths(c1, c2)}</g>'
    return _svg(64, 64, lado, corpo, "Ícone M&amp;S do Brasil")

def _losango(cx, cy, m): return Polygon([(cx - m, cy), (cx, cy - m), (cx + m, cy), (cx, cy + m)])
FAV_1 = _d(_losango(6, 8, 4.5).difference(_losango(10, 8, 4.5).buffer(0.5, quad_segs=6)), 3)
FAV_2 = _d(_losango(10, 8, 4.5), 3)
def svg_favicon(lado=64, fundo="escuro"):
    bg = COR["marinho"] if fundo == "escuro" else COR["branco"]
    c1, c2, _, _ = VARIANTES["fundo-escuro" if fundo == "escuro" else "fundo-claro"]
    corpo = f'<rect width="16" height="16" rx="3" fill="{bg}"/><path d="{FAV_1}" fill="{c1}"/><path d="{FAV_2}" fill="{c2}"/>'
    return _svg(16, 16, lado, corpo, "Favicon M&amp;S do Brasil")

# ---------- tokens ----------
def _cmyk(hx):
    r, g, b = [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]; k = 1 - max(r, g, b)
    return [0, 0, 0, 100] if k == 1 else [round(100 * v) for v in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k)]

def tokens():
    ident = {k: COR[k] for k in ("marinho", "azul", "ciano", "ciano-escuro")}
    return {
        "version": VERSAO, "status": "proposta em validação",
        "identidade": ident,
        "cmyk_calculado": {k: _cmyk(v) for k, v in ident.items()},
        "cmyk_nota": "Conversão matemática do RGB, sem perfil ICC nem prova gráfica. Validar antes de imprimir.",
        "neutros": {k: COR[k] for k in ("tinta", "texto", "apoio", "linha", "nevoa", "branco")},
        "funcionais": {"acao": "#1D4ED8", "acao-hover": "#1E40AF", "acao-pressionado": "#1E3A8A", "foco": "#1D4ED8",
                       "informacao": "#0369A1", "sucesso": "#047857", "alerta": "#B54708", "erro": "#B42318",
                       "desabilitado": "#5F6C88"},
        "foco_nota": "Anel de foco: 2 px na cor foco, com 2 px de afastamento.",
        "tipografia": {
            "display": {"familia": "Inter Display", "pesos": [600, 700, 800], "alternativas": ["Inter", "Arial", "sans-serif"]},
            "texto": {"familia": "Inter", "pesos": [400, 500, 600, 700], "alternativas": ["Calibri", "Arial", "sans-serif"]},
            "codigo": {"familia": "JetBrains Mono", "pesos": [400, 500], "alternativas": ["Consolas", "monospace"]}},
    }

def tokens_css(t):
    L = [f"/* M&S do Brasil — tokens v{t['version']} ({t['status']}). Gerado por scripts/gerar_kit.py. */", ":root {", "  /* Identidade */"]
    L += [f"  --ms-{k}: {v};" for k, v in t["identidade"].items()] + ["", "  /* Neutros */"]
    L += [f"  --ms-{k}: {v};" for k, v in t["neutros"].items()] + ["", "  /* Funcionais: interface, nunca no logotipo */"]
    L += [f"  --ms-{k}: {v};" for k, v in t["funcionais"].items()] + ["", "  /* Tipografia */"]
    for k, f in t["tipografia"].items():
        pilha = ", ".join([f'"{f["familia"]}"'] + [a if a in ("sans-serif", "monospace") else f'"{a}"' for a in f["alternativas"]])
        L.append(f"  --ms-font-{k}: {pilha};")
    return "\n".join(L + ["}", ""])

# ---------- saída ----------
XML = '<?xml version="1.0" encoding="UTF-8"?>\n'
def arquivos_svg():
    arq = {}
    for v in VARIANTES:
        arq[f"svg/ms-assinatura-horizontal-{v}.svg"] = svg_horizontal(v)
        arq[f"svg/ms-assinatura-vertical-{v}.svg"] = svg_vertical(v)
        arq[f"svg/ms-simbolo-{v}.svg"] = svg_simbolo(v)
    arq["svg/ms-icone-fundo-escuro.svg"] = svg_icone("escuro"); arq["svg/ms-icone-fundo-claro.svg"] = svg_icone("claro")
    arq["favicon/favicon.svg"] = svg_favicon(64)
    arq["master/ms-simbolo-mestre.svg"] = svg_simbolo("fundo-claro", 480).replace(
        "<path", "<!-- Geometria mestre: grade 80 x 64, losangos de meia-diagonal 22 com centros em (28,32) e (52,32), traço 4, vão 2. Gerado por scripts/gerar_kit.py. -->\n<path", 1)
    return arq

PNGS = [("svg/ms-assinatura-horizontal-{v}.svg", "png/ms-assinatura-horizontal-{v}-{a}.png", (256, 1024)),
        ("svg/ms-assinatura-vertical-{v}.svg", "png/ms-assinatura-vertical-{v}-{a}.png", (512, 2048)),
        ("svg/ms-simbolo-{v}.svg", "png/ms-simbolo-{v}-{a}.png", (512, 2048))]

def main(raiz):
    for p in ("svg", "png", "favicon", "master", "tokens"): os.makedirs(os.path.join(raiz, p), exist_ok=True)
    arq = arquivos_svg()
    for nome_arq, svg in arq.items(): open(os.path.join(raiz, nome_arq), "w", encoding="utf-8").write(XML + svg + "\n")
    t = tokens()
    json.dump(t, open(os.path.join(raiz, "tokens/paleta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(os.path.join(raiz, "tokens/tokens.css"), "w", encoding="utf-8").write(tokens_css(t))
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright ausente: SVG e tokens gerados, PNG e ICO não."); return
    import re
    from PIL import Image
    tarefas = []
    for origem, destino, alturas in PNGS:
        for v in VARIANTES:
            for a in alturas: tarefas.append((arq[origem.format(v=v)], destino.format(v=v, a=a), a))
    for f in ("escuro", "claro"):
        for a in (512, 1024): tarefas.append((svg_icone(f), f"png/ms-icone-fundo-{f}-{a}.png", a))
    for a in (16, 32, 48, 180, 192, 512):
        tarefas.append((svg_favicon(64) if a < 32 else svg_icone("escuro"), f"favicon/favicon-{a}.png", a))
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        for svg, destino, a in tarefas:
            m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', svg); w = round(a * float(m[1]) / float(m[2]))
            svg = re.sub(r'width="\d+" height="[\d.]+"', f'width="{w}" height="{a}"', svg, count=1)
            pg.set_viewport_size({"width": max(w, 16), "height": max(a, 16)})
            pg.set_content(f'<body style="margin:0;background:transparent">{svg}</body>')
            pg.query_selector("svg").screenshot(path=os.path.join(raiz, destino), omit_background=True)
        b.close()
    ims = [Image.open(os.path.join(raiz, f"favicon/favicon-{a}.png")).convert("RGBA") for a in (16, 32, 48)]
    ims[2].save(os.path.join(raiz, "favicon/favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)], append_images=ims[:2])
    print(f"{len(arq)} SVG e {len(tarefas)} PNG gerados em {raiz}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
