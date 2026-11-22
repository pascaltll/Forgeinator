"""Arte propio para Steam y para el launcher a partir de un fondo (wallpaper) que tú elijas. Solo pygame, sin dependencias.
Genera en <carpeta del juego>/art/: icon.png (512²), cover.png (sin texto, para Hub), portrait.png (600×900), banner.png (920×430), hero.png (1920×620), logo.png (transparente, solo título)."""
from pathlib import Path

import pygame

SIZES = {"icon": (512, 512), "portrait": (600, 900), "banner": (920, 430), "hero": (1920, 620)}


def _cover(img, size):
    w, h = img.get_size()
    k = max(size[0] / w, size[1] / h)
    sc = pygame.transform.smoothscale(img, (max(1, int(w * k + 0.5)), max(1, int(h * k + 0.5))))
    out = pygame.Surface(size).convert()
    out.blit(sc, ((size[0] - sc.get_width()) // 2, (size[1] - sc.get_height()) // 2))
    return out


def _wrap(font, text, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def _font(size):
    p = pygame.font.match_font("notosans,dejavusans,liberationsans,arial", bold=True)
    return pygame.font.Font(p, size)


def _title(surf, text, area, color=(255, 255, 255), max_size=120, min_size=24, align="left"):
    x, y, w, h = area
    for size in range(max_size, min_size - 1, -4):
        f = _font(size)
        lines = _wrap(f, text, w)
        if len(lines) * f.get_linesize() <= h and all(f.size(l)[0] <= w for l in lines):
            break
    ty = y + (h - len(lines) * f.get_linesize()) // 2
    for ln in lines:
        s = f.render(ln, True, color)
        sh = f.render(ln, True, (0, 0, 0))
        tx = x if align == "left" else x + (w - s.get_width()) // 2
        for dx, dy in ((3, 3), (2, 2)):
            sh.set_alpha(110)
            surf.blit(sh, (tx + dx, ty + dy))
        surf.blit(s, (tx, ty))
        ty += f.get_linesize()


def _shade(surf, top_a=0, bottom_a=215, from_frac=0.35):
    w, h = surf.get_size()
    g = pygame.Surface((w, h), pygame.SRCALPHA)
    y0 = int(h * from_frac)
    for y in range(y0, h):
        a = int(top_a + (bottom_a - top_a) * ((y - y0) / max(1, h - y0)) ** 1.4)
        pygame.draw.line(g, (0, 0, 0, a), (0, y), (w, y))
    surf.blit(g, (0, 0))


def _round(surf, r):
    m = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), border_radius=r)
    out = surf.convert_alpha()
    out.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return out


def initials(title):
    ws = [w for w in "".join(c if c.isalnum() else " " for c in title).split() if w]
    return ("".join(w[0] for w in ws[:2]) or "?").upper()


def generate(wallpaper, title, outdir, short=None):
    """Devuelve {'icon': Path, ...}. Lanza OSError/pygame.error si el fondo no se puede leer."""
    img = pygame.image.load(str(wallpaper))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    for kind, size in SIZES.items():
        s = _cover(img, size)
        if kind == "icon":
            _shade(s, 0, 150, 0.45)
            _title(s, short or initials(title), (30, 30, size[0] - 60, size[1] - 60), max_size=260, align="center")
            s = _round(s, 96)
        else:
            _shade(s, 0, 215 if kind != "hero" else 190, 0.4 if kind != "hero" else 0.2)
            pad = int(size[0] * 0.05)
            area = (pad, int(size[1] * 0.55), size[0] - 2 * pad if kind != "hero" else int(size[0] * 0.6), int(size[1] * 0.38))
            _title(s, title, area, max_size=130 if kind != "banner" else 90)
        p = out / f"{kind}.png"
        pygame.image.save(s, str(p))
        res[kind] = p
    cv = _cover(img, (920, 430))     # portada SIN texto: la usa Hub en sus tarjetas (ya dibujan el título)
    _shade(cv, 0, 120, 0.3)
    pygame.image.save(cv, str(out / "cover.png"))
    logo = pygame.Surface((1280, 480), pygame.SRCALPHA)
    _title(logo, title, (40, 40, 1200, 400), max_size=170, align="center")
    pygame.image.save(logo, str(out / "logo.png"))
    res["logo"] = out / "logo.png"
    return res
