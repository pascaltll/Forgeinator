"""Familias de temas (v2.38). Un TEMA es una temática (estructura, tipografía, sonido, forma del Inicio); cada tema ofrece varias PALETAS
(las que antes eran temas casi iguales: oscuro/claro, cristal/aurora, píxel/16 bits…) y varios FONDOS animados de su temática.
Datos puros, sin pygame: `build()` junta estructura + paleta + fondo en el mismo dict que usa apply_theme."""

COLOR_KEYS = ("BG", "PANEL", "PANEL2", "LINE", "TXT", "DIM", "ACC", "OK", "WARN", "ERR", "SEG", "ON_ACC", "FOCUS", "GRAD", "ORBS")
OPT_KEYS = ("ON_ACC", "FOCUS", "GRAD", "ORBS")          # si la paleta no los define, vuelven a su valor por defecto
SOFT_KEYS = ("FONT", "FONTK", "GLASS", "SND", "PATTERN", "ANIM", "RADK", "OUTLINE", "HOME", "HOMEV")   # la paleta de origen solo pisa los que traiga

ANIM_LABEL = {"none": "Liso", "motes": "Motas", "drift": "Luces", "aurora": "Aurora", "stars": "Estrellas", "embers": "Ascuas", "gridrun": "Rejilla",
              "scanbar": "Barrido", "shapes": "Figuras", "silk": "Seda", "cubes": "Cubos", "spincube": "Cubo giratorio", "diag": "Bandas"}


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def derive(bg, panel, acc, txt, dark=True, glow=0):
    """Paleta completa a partir de cuatro colores. glow>0 añade degradado de fondo y un resplandor del acento."""
    d = {"BG": bg, "PANEL": panel, "ACC": acc, "TXT": txt,
         "PANEL2": mix(panel, txt, 0.10 if dark else 0.08), "LINE": mix(panel, txt, 0.26 if dark else 0.22),
         "DIM": mix(bg, txt, 0.64), "SEG": mix(panel, txt, 0.20 if dark else 0.14),
         "OK": (72, 214, 120) if dark else (26, 140, 58), "WARN": (255, 184, 64) if dark else (184, 108, 0), "ERR": (255, 100, 92) if dark else (207, 36, 28),
         "ON_ACC": (255, 255, 255) if _lum(acc) <= 0.30 else mix(bg, (0, 0, 0), 0.7), "FOCUS": mix(acc, (255, 255, 255), 0.55) if dark else txt}
    if glow:
        d["GRAD"] = (mix(bg, acc, 0.14), mix(bg, (0, 0, 0), 0.55))
        d["ORBS"] = ((0.5, 1.05, 0.6, acc, int(40 + 14 * glow)), (0.1, 0.1, 0.5, mix(acc, (120, 120, 255), 0.5), int(24 + 10 * glow)))
    return d


def P(pid, label, *c, dark=True, glow=0, **extra):
    spec = dict(derive(*c, dark=dark, glow=glow))
    spec.update(extra)
    return (pid, label, spec)


def L(pid, label, src, **extra):
    """Paleta tomada de uno de los temas antiguos (sus colores, y su tipografía/sonido/fondo si los trae)."""
    return (pid, label, dict(src=src, **extra))


def _fam(label, desc, base, pals, bgs, **over):
    return {"label": label, "desc": desc, "base": base, "pals": pals, "bgs": bgs, **over}


FAMILIES = {
    "limpio": _fam("Limpio", "Portadas verticales en cuadrícula, sin adornos", "light", [
        L("claro", "Claro", "light"), L("oscuro", "Oscuro", "dark"),
        P("oceano", "Océano", (8, 18, 32), (18, 36, 58), (56, 189, 248), (232, 244, 252)),
        P("menta", "Menta", (240, 247, 244), (255, 255, 255), (0, 138, 100), (20, 36, 30), dark=False),
        P("rosa", "Rosa", (28, 14, 24), (48, 26, 42), (255, 110, 170), (252, 236, 244)),
        P("grafito", "Grafito", (18, 18, 18), (32, 32, 32), (196, 196, 206), (240, 240, 244))],
        ["motes", "drift", "none"], HOME="posters", HOMEV=None),
    "quiver": _fam("Quiver", "Plano con contorno, lista con iconos", "quiver", [
        L("azul", "Azul", "quiver"),
        P("esmeralda", "Esmeralda", (12, 18, 16), (18, 28, 24), (40, 190, 130), (232, 244, 238)),
        P("violeta", "Violeta", (16, 13, 24), (24, 20, 38), (150, 110, 255), (240, 236, 252)),
        P("ambar", "Ámbar", (20, 16, 12), (30, 24, 18), (255, 170, 40), (250, 242, 230))],
        ["motes", "drift", "none"]),
    "prototipo": _fam("Prototipo", "Barra lateral y héroe «Continuar»", "prototipo", [
        L("naranja", "Naranja", "prototipo"),
        P("verde", "Verde", (12, 18, 16), (24, 34, 32), (60, 200, 120), (236, 246, 240), glow=1),
        P("rosa", "Rosa", (20, 13, 18), (38, 24, 34), (255, 92, 160), (250, 236, 244), glow=1),
        P("celeste", "Celeste", (11, 16, 22), (22, 34, 46), (70, 190, 255), (234, 244, 252), glow=1)],
        ["drift", "embers", "motes", "none"]),
    "cristal": _fam("Cristal", "Paneles translúcidos y mosaico de tarjetas", "cristal", [
        L("celeste", "Celeste", "cristal"), L("aurora", "Aurora", "aurora"),
        P("atardecer", "Atardecer", (30, 10, 30), (72, 34, 84), (255, 140, 120), (255, 240, 244), glow=2),
        P("esmeralda", "Esmeralda", (6, 24, 24), (18, 66, 62), (80, 240, 190), (232, 252, 248), glow=2)],
        ["drift", "aurora", "silk", "none"], HOME="mosaic", HOMEV=None),
    "onda": _fam("Onda", "Cintas de seda y fila de portadas que se desplaza", "onda", [
        L("azul", "Azul", "onda"),
        P("esmeralda", "Esmeralda", (4, 28, 30), (10, 68, 66), (110, 240, 200), (232, 252, 248), glow=2),
        P("violeta", "Violeta", (24, 8, 50), (52, 24, 104), (190, 150, 255), (246, 240, 255), glow=2),
        P("atardecer", "Atardecer", (40, 10, 16), (100, 26, 40), (255, 150, 120), (255, 240, 236), glow=2),
        P("dorado", "Dorado", (26, 18, 6), (70, 48, 14), (255, 200, 80), (255, 246, 226), glow=2)],
        ["silk", "aurora", "drift", "none"]),
    "tarjeta": _fam("Tarjeta", "Casillas numeradas sobre el vacío", "tarjeta", [
        L("azul", "Azul", "tarjeta"),
        P("rojo", "Rojo", (14, 2, 4), (40, 10, 16), (255, 110, 110), (255, 236, 236)),
        P("verde", "Verde", (2, 12, 6), (10, 40, 22), (100, 240, 140), (232, 255, 240)),
        P("violeta", "Violeta", (8, 2, 18), (28, 12, 56), (190, 140, 255), (244, 236, 255))],
        ["cubes", "stars", "none"]),
    "cubo": _fam("Cubo", "Galería de portadas que se abre en abanico", "cubo", [
        L("violeta", "Violeta", "cubo"),
        P("azul", "Azul", (6, 14, 40), (18, 42, 96), (100, 170, 255), (236, 244, 255), glow=2),
        P("naranja", "Naranja", (36, 14, 6), (84, 38, 16), (255, 150, 70), (255, 240, 228), glow=2),
        P("verde", "Verde", (6, 28, 20), (16, 76, 56), (110, 240, 170), (234, 255, 244), glow=2)],
        ["spincube", "cubes", "drift", "none"]),
    "interruptor": _fam("Interruptor", "Claro, redondeado, portadas altas con elevación", "interruptor", [
        L("rojoazul", "Rojo y azul", "interruptor"),
        P("noche", "Noche", (30, 30, 34), (44, 44, 50), (0, 195, 227), (240, 240, 244), FOCUS=(255, 70, 50)),
        P("menta", "Menta", (230, 244, 238), (255, 255, 255), (0, 150, 110), (20, 40, 32), dark=False, FOCUS=(0, 170, 230))],
        ["drift", "shapes", "none"]),
    "brasa": _fam("Brasa", "Fragua: estantes con portadas", "brasa", [
        L("brasa", "Brasa", "brasa"),
        P("hielo", "Hielo", (6, 10, 16), (16, 28, 40), (90, 190, 255), (234, 246, 255), glow=2),
        P("bosque", "Bosque", (6, 14, 8), (18, 36, 22), (130, 220, 90), (238, 252, 232), glow=2),
        P("oro", "Oro", (16, 12, 4), (40, 32, 10), (255, 205, 70), (255, 248, 226), glow=2)],
        ["embers", "motes", "drift", "none"]),
    "pixel": _fam("Píxel", "Cartuchos y niveles con portadas altas", "pixel", [
        L("8bits", "8 bits", "pixel", HOME="slots", HOMEV="level"),
        L("16bits", "16 bits", "retro16", HOME="slots", HOMEV="cart"),
        P("gameboy", "Verde LCD", (15, 56, 15), (34, 78, 34), (155, 188, 15), (226, 242, 188), OUTLINE=True, HOME="slots", HOMEV="level"),
        P("ambar", "Ámbar", (16, 8, 0), (46, 26, 0), (255, 176, 0), (255, 214, 130), OUTLINE=True, HOME="slots", HOMEV="cart")],
        ["stars", "diag", "none"], HOME="slots", HOMEV="level"),
    "neon": _fam("Neón", "Recreativa: juegos agrupados por plataforma", "neon", [
        L("rosa", "Rosa y cian", "neon"),
        P("lima", "Lima", (4, 16, 18), (10, 44, 48), (40, 240, 200), (226, 252, 250), FOCUS=(255, 90, 200)),
        P("hielo", "Hielo", (6, 10, 28), (16, 26, 70), (90, 150, 255), (232, 240, 255), FOCUS=(255, 255, 255)),
        P("sol", "Sol", (24, 8, 10), (56, 20, 26), (255, 150, 40), (255, 238, 224), FOCUS=(255, 70, 120))],
        ["gridrun", "stars", "diag", "none"]),
    "fosforo": _fam("Fósforo", "Terminal con nombres de juego", "fosforo", [
        L("verde", "Verde", "fosforo"),
        P("ambar", "Ámbar", (10, 6, 0), (44, 28, 4), (255, 176, 40), (255, 214, 140), OUTLINE=True),
        P("azul", "Azul", (2, 8, 16), (8, 36, 64), (90, 200, 255), (190, 230, 255), OUTLINE=True),
        P("mono", "Monocromo", (8, 8, 8), (28, 28, 28), (230, 230, 230), (230, 230, 230), OUTLINE=True)],
        ["scanbar", "motes", "none"]),
    "tinta": _fam("Tinta", "Papel, índice con títulos originales", "tinta", [
        L("crema", "Crema", "tinta"),
        P("sepia", "Sepia", (232, 216, 186), (244, 232, 206), (140, 76, 28), (46, 32, 20), dark=False, LINE=(70, 52, 36), FOCUS=(46, 32, 20)),
        P("azulpapel", "Azul papel", (234, 238, 244), (248, 250, 253), (28, 76, 160), (20, 28, 44), dark=False, LINE=(40, 52, 80), FOCUS=(20, 28, 44)),
        P("nocturno", "Nocturno", (22, 20, 18), (34, 31, 28), (214, 74, 54), (236, 228, 214), LINE=(150, 140, 126), FOCUS=(236, 228, 214))],
        ["motes", "drift", "none"]),
    "bloque": _fam("Bloque", "Brutalista: bloques con número gigante", "bloque", [
        L("amarillo", "Amarillo", "bloque"),
        P("rosa", "Rosa", (255, 140, 200), (255, 255, 255), (0, 64, 255), (0, 0, 0), dark=False, LINE=(0, 0, 0), FOCUS=(0, 0, 0)),
        P("cian", "Cian", (80, 220, 230), (255, 255, 255), (196, 0, 36), (0, 0, 0), dark=False, LINE=(0, 0, 0), FOCUS=(0, 0, 0)),
        P("lima", "Lima", (170, 240, 60), (255, 255, 255), (200, 0, 100), (0, 0, 0), dark=False, LINE=(0, 0, 0), FOCUS=(0, 0, 0))],
        ["shapes", "diag", "none"]),
    "obsidian": _fam("Obsidian", "Oscuro uniforme, portadas verticales, sin transparencias ni animación", "dark", [
        ("obsidian", "Obsidian", dict(BG=(16, 17, 20), PANEL=(31, 33, 39), PANEL2=(43, 46, 54), LINE=(72, 76, 86), TXT=(239, 241, 246), DIM=(164, 170, 181),
                                      ACC=(196, 196, 206), OK=(72, 214, 120), WARN=(255, 184, 64), ERR=(255, 100, 92), SEG=(58, 60, 66), ON_ACC=(16, 17, 20),
                                      FOCUS=(225, 226, 230), ANIM=None, GLASS=False, FONT=None, SND="soft"))],
        ["none"], HOME="posters", HOMEV=None),
}
ORDER = tuple(FAMILIES)
# temas antiguos → (familia, paleta): lo que ya tenían guardado en ajustes sigue viéndose igual
LEGACY = {"dark": ("limpio", "oscuro"), "light": ("limpio", "claro"), "aurora": ("cristal", "aurora"), "pixel": ("pixel", "8bits"), "retro16": ("pixel", "16bits")}
LEGACY.update({k: (k, FAMILIES[k]["pals"][0][0]) for k in FAMILIES})


def normalize(name, pal=None):
    """Nombre guardado (antiguo o nuevo) → (familia, paleta válida)."""
    if name in FAMILIES:
        f, dp = name, FAMILIES[name]["pals"][0][0]
    elif name in LEGACY:
        f, dp = LEGACY[name]
    else:
        f, dp = "limpio", "oscuro"
    ids = [p[0] for p in FAMILIES[f]["pals"]]
    return f, (pal if pal in ids else dp)


def build(themes, name, pal=None, bg=None):
    """Dict de tema listo para apply_theme. `themes` = diccionario de temas antiguos (de ahí salen estructura y colores de origen)."""
    f, pal = normalize(name, pal)
    fam = FAMILIES[f]
    out = {k: v for k, v in themes[fam["base"]].items() if k not in COLOR_KEYS}
    spec = next(p[2] for p in fam["pals"] if p[0] == pal)
    spec = dict(spec)
    src = themes.get(spec.pop("src", None) or "", None)
    if src is not None:
        for k in COLOR_KEYS:
            if k in src:
                out[k] = src[k]
            elif k in OPT_KEYS:
                out.pop(k, None)
        for k in SOFT_KEYS:
            if k in src:
                out[k] = src[k]
    else:
        for k in OPT_KEYS:
            out.pop(k, None)
    out.update(spec)
    for k in ("HOME", "HOMEV"):                     # la familia fija el Inicio; la paleta puede afinarlo (píxel)
        if k in fam and k not in spec:
            out[k] = fam[k]
    if bg in fam["bgs"]:
        out["ANIM"] = None if bg == "none" else bg
    elif out.get("ANIM") is None and not bg:
        out["ANIM"] = None if fam["bgs"][0] == "none" else fam["bgs"][0]
    out["FAMILY"], out["PAL"] = f, pal
    return out
