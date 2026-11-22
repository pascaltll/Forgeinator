"""Estudio de temas (v2.97, implementación de prueba): las 8 identidades del documento «Visual Design System» resueltas con el motor
nuevo (presets + paleta + layout + material) y traducidas por un ADAPTADOR al dict que dibuja el Hub (el mismo formato que legacy.build).

No toca los 15 temas heredados: estas identidades viven aparte, con ids «v3:<preset>».
Qué traduce el adaptador (y qué no, porque el Hub aún no lo dibuja) está en ADAPTER_NOTES."""
from __future__ import annotations

from .registry import PRESETS, PALETTES, MATERIALS
from .resolver import resolve

PREFIX = "v3:"

# Tabla del documento (secciones 3, 4–11, 15 y 16). `bg` = movimiento ambiental; `label` = nombre que ve el usuario.
IDENTITIES = {
    "minimal":   dict(label="Minimal",  desc="Biblioteca sobria; las portadas mandan", radius=12, spacing="comfortable", font="system", scale=1.00, weight="medium", bg="none",    intensity=0.0,  speed=1.0, audio="soft",  volume=0.35),
    "showcase":  dict(label="Showcase",  desc="Cinematográfico: un juego protagonista", radius=16, spacing="spacious",    font="system", scale=1.10, weight="medium", bg="motes",   intensity=0.15, speed=0.8, audio="glass", volume=0.40),
    "glass":     dict(label="Glass",     desc="Capas translúcidas y profundidad",         radius=18, spacing="comfortable", font="system", scale=1.00, weight="medium", bg="aurora",  intensity=0.20, speed=0.6, audio="glass", volume=0.40),
    "flow":      dict(label="Flow",      desc="Navegación horizontal de consola",         radius=20, spacing="comfortable", font="system", scale=1.00, weight="medium", bg="drift",   intensity=0.12, speed=0.9, audio="silk",  volume=0.35),
    "arcade":    dict(label="Arcade",    desc="Recreativa: casillas numeradas",           radius=4,  spacing="compact",     font="vt323",  scale=1.05, weight="bold",   bg="embers",  intensity=0.25, speed=1.0, audio="chip",  volume=0.45),
    "terminal":  dict(label="Terminal",  desc="Lista monoespaciada, estilo CRT",          radius=2,  spacing="compact",     font="mono",   scale=1.00, weight="normal", bg="scanbar", intensity=0.10, speed=0.6, audio="click", volume=0.25),
    "editorial": dict(label="Editorial", desc="Revista: papel, índice y serifa",          radius=8,  spacing="spacious",    font="serif",  scale=1.05, weight="normal", bg="silk",    intensity=0.08, speed=0.6, audio="wood",  volume=0.25),
    "brutalist": dict(label="Brutalist", desc="Bloques geométricos y números grandes",    radius=2,  spacing="compact",     font="chakra", scale=1.15, weight="bold",   bg="shapes",  intensity=0.12, speed=0.8, audio="click", volume=0.35),
}
ORDER = tuple(IDENTITIES)

# ── v3.09 (tanda 1): parámetros globales declarados por identidad ─────────────────────────────────────────────────────
# Fondo: `intensity` del documento → factor de dibujo (INTENSITY_REF = la intensidad de los 15 temas heredados, factor 1,0).
# `speed` multiplica el reloj de la animación y `density` el número de partículas/figuras. Los temas heredados no traen MOTION: 1, 1, 1.
INTENSITY_REF = 0.20
DENSITY_BG = {"showcase": 0.7, "editorial": 0.8, "terminal": 1.0, "arcade": 1.0, "glass": 1.0, "flow": 1.0, "brutalist": 0.8, "minimal": 1.0}

# Tipografía (sección 8 del documento): 7 niveles. Tamaño en unidades del Hub (las de self.font: se multiplican por la escala de la
# pantalla y por la del tema), peso («regular» | «medium» | «bold») y mayúsculas. DECLARADOS, aún no aplicados a las pantallas existentes:
# los usarán los diseños nuevos con UI.type_font(nivel). VT323 tiene un solo peso: cualquier peso se dibuja con él.
TYPE_LEVELS = ("display", "heading", "title", "body", "secondary", "caption", "numeric")
TYPE_BASE = {"display": (40, "bold"), "heading": (30, "medium"), "title": (24, "medium"), "body": (20, "regular"),
             "secondary": (18, "regular"), "caption": (16, "medium"), "numeric": (24, "medium")}
TYPE_OVERRIDES = {
    "showcase":  {"display": (48, "bold"), "heading": (32, "medium"), "title": (26, "medium")},
    "glass":     {"display": (42, "medium"), "heading": (30, "medium")},
    "flow":      {"display": (42, "bold"), "title": (24, "medium")},
    "arcade":    {"display": (44, "bold", "upper"), "heading": (30, "bold", "upper"), "caption": (16, "regular", "upper"), "numeric": (30, "bold")},
    "terminal":  {"display": (34, "bold"), "heading": (26, "bold"), "title": (22, "regular"), "caption": (16, "regular"), "numeric": (22, "regular")},
    "editorial": {"display": (46, "bold"), "heading": (30, "regular"), "title": (24, "regular"), "caption": (15, "regular", "upper"), "numeric": (22, "regular")},
    "brutalist": {"display": (54, "bold", "upper"), "heading": (34, "bold", "upper"), "title": (24, "bold"), "caption": (16, "medium", "upper"), "numeric": (42, "bold")},
}
# Densidad (spacing del documento): huecos, márgenes internos y alto mínimo de fila. 72 es el mínimo táctil (7 mm en el Ally) en las tres.
DENSITY = {"compact": {"gap": 8, "pad": 14, "row": 72}, "comfortable": {"gap": 12, "pad": 20, "row": 80}, "spacious": {"gap": 18, "pad": 28, "row": 92}}


def type_scale(name) -> dict:
    """Niveles tipográficos de la identidad: {nivel: {"size", "weight", "case"}} (declarados; ver TYPE_BASE)."""
    p = preset_of(name)
    ov = TYPE_OVERRIDES.get(p, {})
    out = {}
    for lv in TYPE_LEVELS:
        v = ov.get(lv, TYPE_BASE[lv])
        out[lv] = {"size": v[0], "weight": v[1], "case": v[2] if len(v) > 2 else None}
    return out


def density(name) -> dict:
    sp = IDENTITIES[preset_of(name)]["spacing"]
    return {"name": sp, **DENSITY[sp]}


def motion_factors(name) -> dict:
    """Factores del fondo animado: velocidad, intensidad y densidad (1, 1, 1 = como los temas heredados)."""
    i = IDENTITIES[preset_of(name)]
    return {"speed": float(i["speed"]), "intensity": round(max(0.3, min(1.5, i["intensity"] / INTENSITY_REF)), 3),
            "density": float(DENSITY_BG.get(preset_of(name), 1.0))}
PALETTE_LABEL = {"obsidian": "Obsidian", "ocean": "Océano", "emerald": "Esmeralda", "violet": "Violeta", "sunset": "Atardecer",
                 "paper": "Papel", "neon": "Neón", "lcd": "LCD", "cloud": "Nube"}
LAYOUT_LABEL = {"grid": "Cuadrícula", "posters": "Portadas", "list": "Lista", "hero": "Destacado", "coverflow": "Coverflow", "xmb": "Horizontal (XMB)",
                "slots": "Casillas", "shelf": "Estantes", "mosaic": "Mosaico", "blocks": "Bloques"}
# layout del motor → (HOME, HOMEV) que entiende el despachador de Inicio (ui_homes._home_custom / ui_home)
LAYOUT_TO_HOME = {"grid": ("grid", None), "posters": ("posters", None), "list": ("list", None), "hero": ("hero", None),
                  "coverflow": ("coverflow", None), "xmb": ("xmb", None), "slots": ("slots", "card"), "shelf": ("posters", "shelf"),
                  "mosaic": ("mosaic", None), "blocks": ("blocks", None)}
# fuentes del motor → FONT del Hub (None = la del sistema). «notosans» no la trae el Hub: cae a la del sistema.
FONT_TO_HUB = {"system": None, "serif": "serif", "mono": "mono", "poppins": "poppins", "chakra": "chakra", "vt323": "vt323", "notosans": None}
FONT_OPTICAL = {"vt323": 1.18}      # VT323 tiene glifos pequeños: a la misma escala se lee peor (los temas heredados la usan a 1,24)
PATTERN = {"terminal": "scan"}
# v3.05: cómo organiza cada identidad las otras pantallas (solo las que ya tienen variante dibujada; el resto, la organización de siempre)
SCREENS = {"minimal": {"explore": "posters", "downloads": "rows"},
           "showcase": {"explore": "shelf_big", "downloads": "featured"},     # v3.06: estantes por consola con portadas grandes
           "flow": {"explore": "shelf", "downloads": "wide"},
           "glass": {"explore": "mosaic"},
           "arcade": {"explore": "numbered", "downloads": "segments"},       # v3.07
           "terminal": {"explore": "text", "downloads": "proc"},
           "editorial": {"explore": "index", "downloads": "table"},          # v3.08
           "brutalist": {"explore": "blocks", "downloads": "blocks"}}      # trama de líneas de los temas CRT heredados

ADAPTER_NOTES = {
    "aplicado": ["colores (11 de la paleta + SEG, ON_ACC derivados)", "forma de Inicio (layout)", "material: cristal (GLASS), contorno (OUTLINE), sombra, grosor de borde y opacidad de paneles/tarjetas/botones (MAT)",
                 "radio de esquinas (RADK × radius_scale del material respecto al del preset)", "tipografía y escala", "timbre de sonido", "fondo animado",
                 "velocidad, intensidad y densidad del fondo (MOTION)", "desenfoque del material solo tras los diálogos, una vez al abrirlos (MAT.blur)",
                 "accesibilidad: movimiento reducido, alto contraste y texto grande (para todos los temas, desde Ajustes)",
                 "calidad: alta / equilibrada / rendimiento (cfg fx: glass / balanced / perf)"],
    "declarado, sin aplicar a las pantallas existentes": ["niveles tipográficos (TYPE: display…numeric, con peso medium real en Poppins y Chakra Petch)",
                                                          "densidad compact/comfortable/spacious (DENS)"],
    "no aplicado (el Hub aún no lo dibuja)": ["volumen por tema (el volumen es global y lo elige el usuario)",
                                              "Ajustes con organización propia (ninguna identidad); Glass: Descargas sin variante propia (solo material)"],
}


def is_studio(name) -> bool:
    return isinstance(name, str) and name.startswith(PREFIX) and name[len(PREFIX):] in IDENTITIES


def preset_of(name) -> str:
    return name[len(PREFIX):] if is_studio(name) else "minimal"


def palettes(name) -> list:
    return list(PRESETS[preset_of(name)].supported_palettes)


def layouts(name) -> list:
    return list(PRESETS[preset_of(name)].supported_layouts)


def backgrounds(name) -> list:
    b = IDENTITIES[preset_of(name)]["bg"]
    return [b, "none"] if b != "none" else ["none"]


def normalize(name, pal=None, layout=None):
    """→ (id «v3:…», paleta válida para ese preset, layout compatible). Nunca falla."""
    p = preset_of(name)
    pr = PRESETS[p]
    return PREFIX + p, (pal if pal in pr.supported_palettes else pr.default_palette), (layout if layout in pr.supported_layouts else pr.default_layout)


QUALITY = {"glass": "high", "balanced": "balanced", "perf": "low"}      # cfg «fx» del Hub → render.quality del motor


def config(name, pal=None, bg=None, layout=None, reduce_motion=False, quality=None, a11y=None) -> dict:
    """Configuración del motor (formato que valida resolver/validation) para esta identidad con lo que eligió el usuario."""
    nm, pal, layout = normalize(name, pal, layout)
    p = preset_of(nm)
    i = IDENTITIES[p]
    back = bg if bg in backgrounds(nm) else i["bg"]
    return {"schema_version": 1, "active_preset": p,
            "appearance": {"layout": layout, "palette": {"id": pal}, "material": PRESETS[p].default_material,
                           "geometry": {"radius": i["radius"], "spacing": i["spacing"], "outline": PRESETS[p].default_material in ("outline", "arcade")},
                           "typography": {"family": i["font"], "scale": i["scale"], "weight": i["weight"]},
                           "motion": {"background": back, "intensity": i["intensity"], "speed": i["speed"], "reduce_motion": bool(reduce_motion)},
                           "audio": {"enabled": True, "profile": i["audio"], "volume": i["volume"]},
                           "render": {"quality": QUALITY.get(quality, "auto"), "blur_enabled": True},
                           "accessibility": {k: bool((a11y or {}).get(k) or (k == "reduce_motion" and reduce_motion))
                                             for k in ("high_contrast", "reduce_motion", "large_text")}}}


def _mix(a, b, t):
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def to_hub(app) -> dict:
    """ADAPTADOR: Appearance resuelta → dict de tema del Hub (mismas claves que legacy.build)."""
    c = dict(app.colors)
    dark = app.palette_mode != "light"
    mat = MATERIALS[app.material]
    c.setdefault("SEG", _mix(c["PANEL"], c["TXT"], 0.20 if dark else 0.14))
    darkon = _mix(c["BG"], (0, 0, 0), 0.7 if dark else 0.2)
    la = _lum(c["ACC"])
    cw, cd = 1.05 / (la + 0.05), (la + 0.05) / (_lum(darkon) + 0.05)
    c["ON_ACC"] = (255, 255, 255) if cw >= cd else darkon        # el que más contraste dé sobre el acento
    glass = app.material == "glass" and app.render.get("blur_enabled", True)
    grad = orbs = None
    if glass:                                    # profundidad atmosférica del material cristal (como los temas heredados con brillo)
        grad = (_mix(c["BG"], c["ACC"], 0.14), _mix(c["BG"], (0, 0, 0), 0.55))
        orbs = ((0.5, 1.05, 0.6, c["ACC"], 54), (0.1, 0.1, 0.5, _mix(c["ACC"], (120, 120, 255), 0.5), 34))
    home, homev = LAYOUT_TO_HOME.get(app.layout, ("grid", None))
    fam = app.typography.get("family", "system")
    motion = app.motion or {}
    anim = motion.get("background", "none")
    if motion.get("reduce_motion") or (app.accessibility or {}).get("reduce_motion") or anim == "none":
        anim = None
    out = {**c, "GRAD": grad, "ORBS": orbs,
           "HOME": home, "HOMEV": homev, "LAYOUT": "top",
           "GLASS": glass, "OUTLINE": bool(app.geometry.get("outline")) or mat.border_width >= 1.5,
           # v3.09: radius_scale del material relativo al del material por defecto del preset (con el de siempre, factor 1: nada cambia)
           "RADK": round(max(0.0, float(app.geometry.get("radius", 12))) / 14.0
                         * mat.radius_scale / MATERIALS[PRESETS[app.preset].default_material].radius_scale, 3),
           "FONT": FONT_TO_HUB.get(fam), "FONTK": round(float(app.typography.get("scale", 1.0)) * FONT_OPTICAL.get(fam, 1.0), 3),
           "SND": (app.audio or {}).get("profile", "soft") if (app.audio or {}).get("profile") != "none" else "soft",
           "ANIM": anim, "PATTERN": PATTERN.get(app.preset), "SCALE": 1.25,
           "FAMILY": PREFIX + app.preset, "PAL": app.palette, "STUDIO_LAYOUT": app.layout,
           # v3.04: el material (registro del motor) llega al dibujo de paneles, tarjetas y botones
           "MAT": {"opacity": mat.opacity, "shadow": mat.shadow, "border": mat.border_width, "blur": mat.blur if glass else 0.0},
           "MOTION": motion_factors(PREFIX + app.preset) if anim else None,
           "TYPE": type_scale(PREFIX + app.preset), "DENS": density(PREFIX + app.preset),
           "SCREENS": dict(SCREENS.get(app.preset) or {}) or None}
    return out


def build(name, pal=None, bg=None, layout=None, reduce_motion=False, quality=None, a11y=None) -> dict:
    return to_hub(resolve(config(name, pal, bg, layout, reduce_motion, quality, a11y)))


def family(name) -> dict:
    """La identidad con la forma de una familia heredada (label, desc, pals, bgs) para reutilizar la pantalla de Ajustes."""
    p = preset_of(name)
    return {"label": IDENTITIES[p]["label"], "desc": IDENTITIES[p]["desc"],
            "pals": [(x, PALETTE_LABEL.get(x, x), None) for x in palettes(name)], "bgs": backgrounds(name), "layouts": layouts(name)}


def appearance(name, pal=None, bg=None, layout=None, quality=None, a11y=None) -> dict:
    """Lo que se publica en appearance.json (mismo formato v2 que legacy.appearance, más el bloque «studio» del motor nuevo)."""
    nm, pal, layout = normalize(name, pal, layout)
    cfg = config(nm, pal, bg, layout, quality=quality, a11y=a11y)
    app = resolve(cfg)
    d = to_hub(app)
    p = preset_of(nm)
    keys = ("BG", "PANEL", "PANEL2", "LINE", "TXT", "DIM", "ACC", "OK", "WARN", "ERR", "SEG", "ON_ACC", "FOCUS", "GRAD", "ORBS")
    return {"schema_version": 2, "family": nm, "palette": pal, "label": IDENTITIES[p]["label"], "palette_label": PALETTE_LABEL.get(pal, pal),
            "colors": {k: d[k] for k in keys if k in d},
            "layout": {"home": d["HOME"], "home_variant": d["HOMEV"], "nav": d["LAYOUT"], "studio": layout, "options": layouts(nm)},
            "typography": {"font": d["FONT"], "scale": d["FONTK"]}, "audio": {"profile": d["SND"]},
            "motion": {"background": d["ANIM"], "pattern": d["PATTERN"], "options": backgrounds(nm), **motion_factors(nm)},
            "geometry": {"radius_scale": d["RADK"], "outline": d["OUTLINE"], "glass": d["GLASS"]},
            "type_levels": d["TYPE"], "density": d["DENS"],
            "studio": {"engine": app.to_dict(), "adapter_notes": ADAPTER_NOTES}}
