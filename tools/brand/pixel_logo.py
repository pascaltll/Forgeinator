"""Forgeinator 3000 · logo pixel art (cartucho). Parte de cartucho-base.svg (diseño de Carlos: cartucho, marco, pines, placa «3000»)
y genera el yunque, el martillo y las chispas píxel a píxel con la paleta del cartucho. Salida: cartucho.svg (lo usa make_brand.py).
Uso: python3 tools/brand/pixel_logo.py"""
import math, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
SRC = (HERE / "cartucho-base.svg").read_text(encoding="utf-8")
OUTL, DARK, SH, MID, LT, HI = "#080613", "#211832", "#211832", "#6B638B", "#AAA0C7", "#F3EDFF"
W1, W2, W3, GOLD, OR = "#FF7138", "#FF8A00", "#FFD166", "#FFD166", "#FF7138"

def inside(px, py, poly):
    c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            c = not c
    return c

def raster(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return {(x, y) for x in range(int(min(xs)) - 1, int(max(xs)) + 2) for y in range(int(min(ys)) - 1, int(max(ys)) + 2) if inside(x + .5, y + .5, poly)}

def rot(cx, cy, pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]

def shade_metal(px, light=(-1, -1)):
    out = {}
    for (x, y) in px:
        up = (x, y - 1) not in px; lf = (x - 1, y) not in px
        dn = (x, y + 1) not in px; rt = (x + 1, y) not in px
        up2 = (x, y - 2) not in px
        if up: out[(x, y)] = HI
        elif dn or rt: out[(x, y)] = DARK
        elif lf or up2: out[(x, y)] = LT
        else: out[(x, y)] = MID
    return out

def outline(px):
    o = set()
    for (x, y) in px:
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q = (x + dx, y + dy)
            if q not in px: o.add(q)
    return o

def emit(cmap):
    rows = {}
    for (x, y), c in cmap.items(): rows.setdefault(y, {})[x] = c
    out = []
    for y in sorted(rows):
        xs = sorted(rows[y]); i = 0
        while i < len(xs):
            x0 = xs[i]; c = rows[y][x0]; j = i
            while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1 and rows[y][xs[j + 1]] == c: j += 1
            out.append(f'<rect x="{x0}" y="{y}" width="{xs[j]-x0+1}" height="1" fill="{c}"/>')
            i = j + 1
    return "\n    ".join(out)

def build(name, anvil_poly, hammer_head, handle, sparks, extra=None):
    canvas = {}
    # anvil
    A = set().union(*[raster(p) for p in anvil_poly])
    for q in outline(A): canvas[q] = OUTL
    canvas.update(shade_metal(A))
    if extra: extra(canvas, A)
    # handle (wood)
    Hd = raster(handle[0])
    Hh = raster(hammer_head)
    for q in outline(Hd | Hh):
        canvas[q] = OUTL
    ax, ay = handle[1]
    for (x, y) in Hd:
        # wood: light on one side, dark on the other (perp. to axis)
        d = (x + .5 - handle[2][0]) * ay - (y + .5 - handle[2][1]) * ax
        canvas[(x, y)] = W3 if d < -0.8 else (W1 if d > 0.8 else W2)
    canvas.update(shade_metal(Hh))
    for (x, y, c) in sparks:
        cur = canvas.get((x, y))
        if cur is None or (cur == OUTL and y >= FACE_Y - 1 and (x, y) not in outline(Hd | Hh)):
            canvas[(x, y)] = c
    body = emit(canvas)
    svg = re.sub(r"<!-- ================= YUNQUE.*?<!-- ================= TEXTO", "<!-- ================= YUNQUE Y MARTILLO (generado) ================= -->\n  <g>\n    " + body + "\n  </g>\n\n  <!-- ================= TEXTO", SRC, flags=re.S)
    (HERE / f"{name}.svg").write_text(svg, encoding="utf-8")

# ---------- anvil (classic: horn left, face, heel right, waist, feet) ----------
FACE_Y = 66
anvil = [
    # face + heel block
    [(40, FACE_Y), (94, FACE_Y), (94, FACE_Y + 6), (40, FACE_Y + 6)],
    # horn: tapered cone to a point on the left, underside curving back
    [(40, FACE_Y), (33, FACE_Y - 0.2), (27, FACE_Y + 1.2), (22, FACE_Y + 3.2), (27, FACE_Y + 4.4), (33, FACE_Y + 5.8), (40, FACE_Y + 7.5)],
    # shoulders narrowing into waist
    [(46, FACE_Y + 6), (90, FACE_Y + 6), (82, FACE_Y + 10), (78, FACE_Y + 13), (56, FACE_Y + 13), (52, FACE_Y + 10)],
    [(56, FACE_Y + 12), (78, FACE_Y + 12), (78, FACE_Y + 18), (56, FACE_Y + 18)],
    # feet flaring out
    [(56, FACE_Y + 17), (78, FACE_Y + 17), (84, FACE_Y + 20), (88, FACE_Y + 23), (88, FACE_Y + 25), (46, FACE_Y + 25), (46, FACE_Y + 23), (50, FACE_Y + 20)],
]

def hardy(canvas, A):
    for (x, y) in ((86, FACE_Y + 2), (87, FACE_Y + 2), (86, FACE_Y + 3), (87, FACE_Y + 3)):
        canvas[(x, y)] = OUTL
    # foot notch shadow (gap between feet)
    for x in range(64, 71):
        canvas[(x, FACE_Y + 24)] = OUTL if (x, FACE_Y + 24) in A else canvas.get((x, FACE_Y + 24))
        canvas[(x, FACE_Y + 23)] = DARK


def hammer(theta_deg, cx, length=26, hw=12, hh=7, w=2.2, band=True):
    t = math.radians(theta_deg)
    hx, hy = math.sin(t), -math.cos(t)               # handle direction (up, leaning right)
    ax_, ay_ = -hy, hx                               # head long axis (perpendicular)
    # head corners in local frame (u along axis, v along handle)
    def P(u, v, c): return (c[0] + ax_ * u + hx * v, c[1] + ay_ * u + hy * v)
    c0 = (cx, 0)
    low = max(P(u, v, c0)[1] for u in (-hw, hw) for v in (-hh, hh))
    c = (cx, FACE_Y - 1.2 - low)
    head = [P(-hw, -hh, c), P(hw, -hh, c), P(hw, hh, c), P(-hw, hh, c)]
    p0 = P(0, hh - 1, c); p1 = P(0, hh + length, c)
    px_, py_ = ax_, ay_
    hp = [(p0[0] + px_ * w, p0[1] + py_ * w), (p1[0] + px_ * w, p1[1] + py_ * w), (p1[0] - px_ * w, p1[1] - py_ * w), (p0[0] - px_ * w, p0[1] - py_ * w)]
    bandpx = raster([P(-hw + 3, -1.2, c), P(hw - 3, -1.2, c), P(hw - 3, 1.2, c), P(-hw + 3, 1.2, c)]) if band else set()
    lowpt = max(head, key=lambda p: p[1])
    return head, (hp, (hx, hy), c), bandpx, lowpt

def sparks_at(sx, sy):
    sp = [(sx + dx, sy + dy, HI) for dx in (-2,-1,0,1,2) for dy in (0,) ] + [(sx + dx, sy - 1, HI) for dx in (-1,0,1)]
    def blk(dx, dy, col): return [(dx, dy, col), (dx + 1, dy, col), (dx, dy + 1, col), (dx + 1, dy + 1, col)]
    burst = (blk(-8, -4, W3) + blk(8, -4, W3) + blk(-14, -8, W2) + blk(14, -9, W2) + blk(-20, -3, W1) + blk(20, -4, W1)
             + blk(-11, -13, W3) + blk(11, -14, W3)
             + [(-4, -3, HI), (4, -3, HI), (-5, -7, W3), (5, -7, W3), (-17, -12, HI), (17, -13, HI), (-24, -8, W1), (24, -9, W1),
                (-3, -2, W3), (3, -2, W3), (-6, -1, W2), (6, -1, W2)])
    return sp + [(sx + dx, sy + dy, c) for dx, dy, c in burst]

def swing(theta_deg, head, handle, arcs=((0.0, LT), (-4.5, MID)), span=22, gap=0):
    hp, (hx, hy), c = handle
    pivot = ((hp[1][0] + hp[2][0]) / 2, (hp[1][1] + hp[2][1]) / 2)
    far = max(head, key=lambda p: (p[0] - pivot[0]) ** 2 + (p[1] - pivot[1]) ** 2)
    R = math.dist(far, pivot)
    a0 = math.atan2(far[1] - pivot[1], far[0] - pivot[0])
    pts = []
    for dr, col in arcs:
        r = R + 2 + dr
        for k in range(4, span):
            if gap and (k // gap) % 2: continue
            a = a0 + math.radians(k)
            pts.append((int(round(pivot[0] + r * math.cos(a))), int(round(pivot[1] + r * math.sin(a))), col))
    return pts

def build3(name, theta, cx, hw=13, hh=7.5, length=24, w=2.5, trail=True):
    head, handle, bandpx, low = hammer(theta, cx, hw=hw, hh=hh, length=length, w=w)
    sx = int(round(low[0]))
    sp = sparks_at(sx, FACE_Y - 1)
    if trail:
        sp = swing(theta, head, handle) + sp
    build(name, anvil, head, handle, sp, hardy)
    svg = (HERE / f"{name}.svg").read_text(encoding="utf-8")
    add = "\n    ".join(f'<rect x="{x}" y="{y}" width="1" height="1" fill="{DARK}"/>' for x, y in sorted(bandpx))
    svg = svg.replace("  </g>\n\n  <!-- ================= TEXTO", "    " + add + "\n  </g>\n\n  <!-- ================= TEXTO", 1)
    (HERE / f"{name}.svg").write_text(svg, encoding="utf-8")

if __name__ == "__main__":
    build3("cartucho", 45, 62, trail=False)     # diseño aprobado (23-11-2026): un martillo a 45° golpeando el yunque
    print("ok", HERE / "cartucho.svg")
