"""Puente con el Hub v2.88 (fase A): los 14 temas × 58 paletas como datos puros, sin pygame.
`build()` devuelve EXACTAMENTE el dict que daba themes_fam.build (lo comprueba tests_pro/test_v290.py), así que el Hub puede
leer del motor sin que cambie nada de lo que se ve. `appearance()` lo ordena por secciones para que otros programas lo lean."""
from __future__ import annotations
import copy
from .catalog_data import FAMILIES, ORDER, LEGACY, ANIM_LABEL

COLOR_KEYS = ("BG", "PANEL", "PANEL2", "LINE", "TXT", "DIM", "ACC", "OK", "WARN", "ERR", "SEG", "ON_ACC", "FOCUS", "GRAD", "ORBS")


def normalize(name, pal=None):
    """Nombre guardado (antiguo o nuevo) → (familia, paleta válida)."""
    if name in FAMILIES:
        f, dp = name, FAMILIES[name]["palettes"][0]["id"]
    elif name in LEGACY:
        f, dp = LEGACY[name]
    else:
        f, dp = "limpio", "oscuro"
    ids = [p["id"] for p in FAMILIES[f]["palettes"]]
    return f, (pal if pal in ids else dp)


def build(name, pal=None, bg=None):
    f, pal = normalize(name, pal)
    fam = FAMILIES[f]
    row = next(p for p in fam["palettes"] if p["id"] == pal)
    out = copy.deepcopy(fam["structure"])
    out.update(copy.deepcopy(row["extra"]))
    out.update(copy.deepcopy(row["colors"]))
    if bg in fam["bgs"]:
        out["ANIM"] = None if bg == "none" else bg
    else:
        anim = row["anim"] if not bg else row["anim_invalid_bg"]
        out["ANIM"] = anim
    out["FAMILY"], out["PAL"] = f, pal
    return out


def appearance(name, pal=None, bg=None):
    """Apariencia ordenada por secciones (lo que publica `appearance.json`)."""
    d = build(name, pal, bg)
    f, p = d["FAMILY"], d["PAL"]
    return {
        "schema_version": 2,
        "family": f, "palette": p,
        "label": FAMILIES[f]["label"], "palette_label": next(x["label"] for x in FAMILIES[f]["palettes"] if x["id"] == p),
        "colors": {k: d[k] for k in COLOR_KEYS if k in d},
        "layout": {"home": d.get("HOME"), "home_variant": d.get("HOMEV"), "nav": d.get("LAYOUT")},
        "typography": {"font": d.get("FONT"), "scale": d.get("FONTK", 1.0)},
        "audio": {"profile": d.get("SND", "soft")},
        "motion": {"background": d.get("ANIM"), "pattern": d.get("PATTERN"), "options": list(FAMILIES[f]["bgs"])},
        "geometry": {"radius_scale": d.get("RADK", 1.0), "outline": bool(d.get("OUTLINE")), "glass": bool(d.get("GLASS"))},
    }


def catalog():
    """Lista completa para una pantalla de personalización: temas, paletas con sus colores y fondos disponibles."""
    return [{"id": f, "label": v["label"], "desc": v["desc"], "backgrounds": [{"id": b, "label": ANIM_LABEL.get(b, b)} for b in v["bgs"]],
             "palettes": [{"id": p["id"], "label": p["label"], "colors": {k: p["colors"][k] for k in ("BG", "PANEL", "ACC", "TXT") if k in p["colors"]}}
                          for p in v["palettes"]]} for f, v in FAMILIES.items()]


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# mismas exigencias que tests_pro/test_v238.py: cualquier paleta (también las del usuario) debe cumplirlas
CONTRAST_RULES = (("TXT", "BG", 6.0), ("TXT", "PANEL", 6.0), ("DIM", "BG", 3.8), ("DIM", "PANEL", 3.4), ("ACC", "BG", 3.0), ("ACC", "PANEL", 3.0),
                  ("ON_ACC", "ACC", 3.5), ("LINE", "BG", 1.15))


def check_contrast(colors):
    """→ lista de (a, b, ratio, mínimo) que NO cumplen. Vacía = la paleta se puede usar."""
    c = dict(colors)
    c.setdefault("ON_ACC", (255, 255, 255))
    bad = []
    for a, b, mn in CONTRAST_RULES:
        if a in c and b in c:
            r = contrast(c[a], c[b])
            if r < mn:
                bad.append((a, b, round(r, 2), mn))
    return bad
