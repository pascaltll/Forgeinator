#!/usr/bin/env python3
"""Forgeinator 3000 · identidad gráfica. Genera los SVG fuente y sus PNG (icono, arte de Steam/QAM, GitHub, README).
Diseño original: cartucho pixel art con un martillo golpeando el yunque y la placa «3000» (tools/brand/pixel_logo.py → cartucho.svg).
Requiere (solo para generar, no para usar Forgeinator): `pip install cairosvg` y la fuente Chakra Petch (OFL) en ~/.fonts o en data/fonts.
Uso: python3 tools/brand/make_brand.py [carpeta de salida]   (por defecto assets/brand)"""
import math
import random
import re
import sys
from pathlib import Path

import cairosvg
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "brand"
FONT_DIRS = [Path.home() / ".fonts", ROOT / "data" / "fonts" / "chakrapetch", ROOT / "data" / "fonts"]
FONT = "Chakra Petch"
INK, EMBER, HOT, GOLD, STEEL_D, STEEL_L, BG0, BG1 = "#f6efe6", "#ff7138", "#ffd166", "#ffd166", "#262b33", "#8c97a5", "#080613", "#100d20"

DEFS = f"""
<linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a9b3bf"/><stop offset=".18" stop-color="#6c7682"/>
  <stop offset=".6" stop-color="#3a414b"/><stop offset="1" stop-color="{STEEL_D}"/></linearGradient>
<linearGradient id="steelface" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7d8794"/><stop offset=".5" stop-color="#c9d1da"/>
  <stop offset="1" stop-color="#7d8794"/></linearGradient>
<linearGradient id="hot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset=".25" stop-color="{GOLD}"/>
  <stop offset=".65" stop-color="{EMBER}"/><stop offset="1" stop-color="#c2310b"/></linearGradient>
<radialGradient id="glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{HOT}" stop-opacity=".75"/>
  <stop offset=".45" stop-color="{EMBER}" stop-opacity=".28"/><stop offset="1" stop-color="{EMBER}" stop-opacity="0"/></radialGradient>
<radialGradient id="bg" cx=".5" cy=".62" r=".75"><stop offset="0" stop-color="#2c2048"/><stop offset=".55" stop-color="{BG1}"/>
  <stop offset="1" stop-color="{BG0}"/></radialGradient>
<linearGradient id="plate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe27a"/><stop offset="1" stop-color="#f0a51c"/></linearGradient>
<linearGradient id="word" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff7ec"/><stop offset=".62" stop-color="#f3e3cf"/>
  <stop offset="1" stop-color="#ffb45a"/></linearGradient>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
"""


CART = (Path(__file__).resolve().parent / "cartucho.svg").read_text(encoding="utf-8")
CART_BODY = re.sub(r'<rect width="128" height="128" fill="#100D20"/>', "", CART[CART.index(">", CART.index("<svg")) + 1:CART.rindex("</svg>")], count=1)


def emblem(s=1.0, sparks=True):
    """El logo pixel art (cartucho con yunque y martillo, tools/brand/cartucho.svg) en un cuadro de 512 (origen arriba a la izquierda).
    Se dibuja a escala 4×s con bordes nítidos; sin el fondo del cartucho, para que se vea el fondo de cada imagen."""
    return f'<g transform="scale({4 * s:g})" shape-rendering="crispEdges">{CART_BODY}</g>'


def plate(x, y, h, rot=-8, txt="3000"):
    """Placa «3000» (pegatina retro). (x, y) = centro; h = alto."""
    w = h * 2.45
    fs = h * 0.74
    return f"""<g transform="translate({x} {y}) rotate({rot})">
      <rect x="{-w / 2 + h * .05}" y="{-h / 2 + h * .09}" width="{w}" height="{h}" rx="{h * .22}" fill="#000" fill-opacity=".45"/>
      <rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="{h * .22}" fill="url(#plate)" stroke="#3a1606" stroke-width="{h * .07}"/>
      <text x="0" y="{h * .27}" text-anchor="middle" font-family="{FONT}" font-weight="700" font-size="{fs:.1f}" fill="#2a1206"
            letter-spacing="{h * .03:.1f}">{txt}</text></g>"""


def text_w(txt, size, spacing=0.0, weight="Bold"):
    """Ancho real del texto con Chakra Petch (para colocar la placa y no salirse del lienzo)."""
    path = next((d / f"ChakraPetch-{weight}.ttf" for d in FONT_DIRS if (d / f"ChakraPetch-{weight}.ttf").is_file()), None)
    if path is None:
        raise SystemExit("falta ChakraPetch-Bold.ttf (https://github.com/google/fonts/tree/main/ofl/chakrapetch) en ~/.fonts")
    f = ImageFont.truetype(str(path), int(round(size)))
    return f.getlength(txt) + spacing * (len(txt) - 1)


def wordmark(x, y, size, anchor="start", plate_after=True):
    """«FORGEINATOR» + placa «3000». (x, y) = línea base del texto."""
    est_w = text_w("FORGEINATOR", size, size * .05)
    x0 = x - est_w / 2 if anchor == "middle" else x
    t = (f'<text x="{x0:.1f}" y="{y:.1f}" font-family="{FONT}" font-weight="700" font-size="{size}" letter-spacing="{size * .05:.1f}" '
         f'fill="url(#word)" stroke="#120806" stroke-width="{size * .025:.1f}" paint-order="stroke">FORGEINATOR</text>')
    if plate_after:
        t += plate(x0 + est_w + size * .92, y - size * .66, size * .5, -8)
    return t, est_w


def svg(w, h, body, bg=True):
    back = f'<rect width="{w}" height="{h}" fill="url(#bg)"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{DEFS}</defs>{back}{body}</svg>'


def icon(size=512, rounded=True, small=False):
    """El cartucho tal cual, a escala exacta (512 = 4×, 256 = 2×, 128 = 1×). rounded=True: sin fondo (la silueta del cartucho hace de
    icono, para el QAM, la ventana y GitHub); rounded=False: con su fondo oscuro, para Steam (que recorta en cuadrado)."""
    body = ("" if rounded else '<rect width="512" height="512" fill="#100D20"/>') + emblem(1)
    return svg(512, 512, body, bg=False)


def embers(w, h, n, seed=7, y0=0.35, avoid=None):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(h * y0, h)
        if avoid and avoid[0] <= x <= avoid[2] and avoid[1] <= y <= avoid[3]:
            continue
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(1.2, 3.6):.1f}" fill="{rnd.choice([HOT, GOLD, EMBER])}" '
                   f'fill-opacity="{rnd.uniform(.35, .95):.2f}"/>')
    return "".join(out)


def put(name, s, w, h):
    (OUT / "src").mkdir(parents=True, exist_ok=True)
    (OUT / "src" / f"{name}.svg").write_text(s, encoding="utf-8")
    cairosvg.svg2png(bytestring=s.encode(), write_to=str(OUT / f"{name}.png"), output_width=w, output_height=h)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ic, ics = icon(), icon(small=True)
    for px in (512, 256, 128):
        put(f"icon-{px}", ic, px, px)
    for px in (64, 32):                                          # reducido: el marco, el yunque y los pines siguen leyéndose
        put(f"icon-{px}", ics, px, px)
    put("icon-square", icon(rounded=False), 512, 512)            # icono de Steam (Steam ya redondea)
    # Steam: cápsula vertical 600×900
    wm, ww = wordmark(300, 700, 64, "middle", plate_after=False)
    put("steam-capsule", svg(600, 900, embers(600, 900, 70, 1, .55, avoid=(0, 640, 600, 880)) + f'<g transform="translate(36 80)">{emblem(1.03)}</g>' + wm
                          + plate(300, 790, 74, -6) +
                          f'<text x="300" y="860" text-anchor="middle" font-family="{FONT}" font-weight="600" font-size="22" fill="{HOT}" '
                          f'fill-opacity=".85" letter-spacing="2">FORGES PORTS INTO GAMES</text>'), 600, 900)
    # Steam: cabecera 920×430 (y 460×215)
    wm, ww = wordmark(350, 232, 56)
    hdr = svg(920, 430, embers(920, 430, 60, 2, avoid=(340, 150, 920, 310)) + f'<g transform="translate(0 40)">{emblem(.68)}</g>' + wm +
              f'<text x="352" y="286" font-family="{FONT}" font-weight="600" font-size="19" fill="{HOT}" letter-spacing="1">'
              'FORGES SCATTERED PORTS INTO PLAYABLE GAMES</text>')
    put("steam-header", hdr, 920, 430)
    put("steam-header-small", hdr, 460, 215)
    # Steam: fondo grande 1920×620 (sin texto: Steam pone el logo encima)
    hero = svg(1920, 620, embers(1920, 620, 260, 3, .2) +
               f'<ellipse cx="1500" cy="330" rx="560" ry="300" fill="url(#glow)"/><g transform="translate(1270 60) scale(.92)">{emblem(1, True)}</g>')
    put("steam-hero", hero, 1920, 620)
    # Steam / QAM: logo transparente 1280×720
    wm, ww = wordmark(400, 420, 92)
    put("steam-logo", svg(1280, 720, f'<g transform="translate(20 150) scale(.8)">{emblem(1)}</g>' + wm, bg=False), 1280, 720)
    # GitHub: vista previa social 1280×640 y banner del README 1280×320
    wm, ww = wordmark(560, 318, 76)
    put("github-social", svg(1280, 640, embers(1280, 640, 120, 4, avoid=(540, 200, 1280, 580)) + f'<g transform="translate(40 80)">{emblem(.92)}</g>' + wm +
                         f'<text x="562" y="392" font-family="{FONT}" font-weight="600" font-size="30" fill="{INK}" fill-opacity=".92">'
                         'Behold, the Forgeinator 3000!</text>'
                         f'<text x="562" y="436" font-family="{FONT}" font-weight="600" font-size="26" fill="{HOT}">'
                         'It forges scattered ports into playable games.</text>'
                         f'<text x="562" y="560" font-family="{FONT}" font-weight="600" font-size="20" fill="{INK}" fill-opacity=".55">'
                         'github.com/pascaltll/Forgeinator · GPL-3.0</text>'), 1280, 640)
    wm, ww = wordmark(330, 178, 70)
    put("readme-banner", svg(1280, 320, embers(1280, 320, 90, 5, avoid=(320, 100, 1280, 260)) + f'<g transform="translate(40 18) scale(.56)">{emblem(1)}</g>' + wm +
                         f'<text x="332" y="236" font-family="{FONT}" font-weight="600" font-size="24" fill="{HOT}">'
                         'Behold, the Forgeinator 3000! It forges scattered ports into playable games.</text>'), 1280, 320)
    print("ok", OUT)


if __name__ == "__main__":
    main()
