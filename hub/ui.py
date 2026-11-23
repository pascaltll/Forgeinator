"""Interfaz SDL (pygame-ce) de Forgeinator (antes Recomp Hub): táctil primero + mando completo. Modo inmediato con navegación espacial por foco."""
import collections
import io
import json
import math
import random
import os
import unicodedata
import re
import shutil
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import pygame

import urllib.parse

from . import themes as hubthemes
from . import a11y as a11ymod
from . import directplay
from . import channel as chan
from . import qamlink
from . import selfupdate, gamedict, buildplan, sfx, auth, build, catalog, config, downloads, gamepad, ghapi, github, install, dlwatch, esde, formats, library, port, roms, hubbrowser, received, gamecfg, cmdjob, artgen, steamsetup, sgdb, artsrc, recompsite, gsfocus, catalogservice, catalogjobs, quiversrc, trash, perf, covers, buildlog, doctor, ghcookies, ghstats, platformart, icons, launchlog, osver, steamlib, power, recipes, peek, discid, fonts, launchwatch, themes_fam, ownwine, lcheck, nethttp, history, diag, haptic, logview

BG = (10, 10, 12)            # estilo Apple oscuro: negro casi puro, capas de gris «sistema»
PANEL = (28, 28, 30)
PANEL2 = (44, 44, 48)
LINE = (58, 58, 62)
TXT = (245, 245, 247)
DIM = (152, 152, 160)
ACC = (10, 132, 255)
OK = (48, 209, 88)
WARN = (255, 159, 10)
ERR = (255, 69, 58)
SEG = (84, 84, 90)           # segmento seleccionado
ON_ACC = (255, 255, 255)     # texto sobre botones de color (azul/verde/rojo) y sobre las fichas teñidas: siempre claro
TILE_SUB = (200, 200, 210)
THEMES = {
    "dark": dict(BG=(10, 10, 12), PANEL=(28, 28, 30), PANEL2=(44, 44, 48), LINE=(58, 58, 62), TXT=(245, 245, 247), DIM=(152, 152, 160),
                 ACC=(10, 132, 255), OK=(48, 209, 88), WARN=(255, 159, 10), ERR=(255, 69, 58), SEG=(84, 84, 90)),
    "light": dict(BG=(242, 242, 247), PANEL=(255, 255, 255), PANEL2=(229, 229, 234), LINE=(209, 209, 214), TXT=(28, 28, 30), DIM=(99, 99, 106),
                  ACC=(0, 108, 224), OK=(26, 140, 58), WARN=(184, 108, 0), ERR=(207, 36, 28), SEG=(196, 196, 204)),
}
# «Quiver»: aspecto plano de Quiver Launcher (render que envió Carlos): casi negro azulado, botones SOLO con contorno, esquinas medias,
# títulos de sección en mayúsculas pequeñas y foco en azul claro. No usa blur ni sombras (es el más barato de dibujar).
THEMES["quiver"] = dict(ANIM="motes", SND="soft", BG=(15, 16, 20), PANEL=(22, 23, 29), PANEL2=(30, 31, 38), LINE=(62, 64, 74), TXT=(236, 237, 241), DIM=(160, 162, 172),
                        ACC=(34, 122, 228), OK=(52, 199, 89), WARN=(255, 170, 40), ERR=(255, 90, 80), SEG=(54, 57, 70),
                        OUTLINE=True, RADK=0.62, FOCUS=(88, 176, 255))
# «Prototipo»: el diseño que enviaste como render — barra lateral con iconos, acento naranja, héroe «Continuar», tarjetas verticales con insignia de plataforma.
THEMES["prototipo"] = dict(ANIM="drift", SND="glass", BG=(13, 16, 20), PANEL=(26, 32, 41), PANEL2=(35, 43, 54), LINE=(44, 53, 65), TXT=(238, 242, 246), DIM=(147, 160, 176),
                           ACC=(255, 138, 61), OK=(76, 214, 138), WARN=(255, 194, 71), ERR=(255, 107, 94), SEG=(58, 68, 82),
                           ON_ACC=(26, 14, 3), FOCUS=(255, 255, 255), RADK=1.0, LAYOUT="side", SCALE=1.25,
                           GRAD=((22, 27, 36), (9, 11, 15)), ORBS=((0.92, 0.02, 0.62, (255, 138, 61), 46), (0.06, 1.0, 0.58, (70, 110, 210), 40)))
# «Cristal»: barra lateral del prototipo pero con paneles translúcidos sobre un fondo con profundidad (violeta, azul y turquesa), bordes de luz y acento celeste.
THEMES["cristal"] = dict(ANIM="drift", SND="glass", BG=(10, 12, 28), PANEL=(34, 40, 78), PANEL2=(52, 60, 112), LINE=(96, 108, 170), TXT=(240, 244, 255), DIM=(164, 174, 210),
                         ACC=(78, 190, 255), OK=(80, 226, 168), WARN=(255, 196, 90), ERR=(255, 108, 124), SEG=(74, 86, 150),
                         ON_ACC=(6, 14, 38), FOCUS=(255, 255, 255), RADK=1.2, LAYOUT="side", SCALE=1.25, GLASS=True,
                         GRAD=((18, 16, 46), (8, 10, 26)),
                         ORBS=((0.82, 0.10, 0.62, (60, 120, 255), 74), (0.10, 0.92, 0.58, (150, 70, 230), 70), (0.55, 0.60, 0.50, (30, 190, 200), 36)))
# ── v2.27: temas con carácter propio. Además de la paleta cambian tipografía (FONT), trama del fondo (PATTERN) y forma (RADK/OUTLINE). ──
# «Neón»: sala de recreativas — magenta y cian sobre violeta casi negro, rejilla en perspectiva hacia un sol en el horizonte.
THEMES["neon"] = dict(ANIM="gridrun", SND="arcade", BG=(10, 6, 24), PANEL=(28, 16, 52), PANEL2=(46, 26, 84), LINE=(132, 62, 190), TXT=(246, 238, 255), DIM=(182, 156, 220),
                      ACC=(255, 76, 178), OK=(60, 240, 200), WARN=(255, 210, 70), ERR=(255, 96, 96), SEG=(74, 42, 126),
                      ON_ACC=(34, 4, 24), FOCUS=(70, 235, 255), OUTLINE=True, RADK=0.8, LAYOUT="side", SCALE=1.25,
                      GRAD=((30, 8, 64), (6, 4, 18)), ORBS=((0.5, 0.60, 0.42, (255, 56, 168), 70),), PATTERN="grid")
# «Tinta»: papel y tinta — crema, negro cálido y un solo rojo de imprenta; serif, contornos finos, sin efectos (el más barato de dibujar).
THEMES["tinta"] = dict(ANIM="motes", SND="wood", BG=(243, 237, 222), PANEL=(252, 248, 238), PANEL2=(231, 223, 204), LINE=(64, 56, 46), TXT=(28, 24, 20), DIM=(98, 90, 78),
                       ACC=(176, 44, 30), OK=(34, 104, 56), WARN=(150, 92, 0), ERR=(164, 28, 28), SEG=(212, 202, 180),
                       FOCUS=(28, 24, 20), OUTLINE=True, RADK=0.3, FONT="serif")
# «Fósforo»: terminal CRT — verde fósforo sobre negro, monoespaciada, líneas de barrido y esquinas casi rectas.
THEMES["fosforo"] = dict(ANIM="scanbar", SND="blip", BG=(3, 9, 5), PANEL=(16, 50, 27), PANEL2=(24, 70, 38), LINE=(40, 128, 70), TXT=(160, 255, 186), DIM=(104, 200, 132),
                         ACC=(64, 255, 134), OK=(150, 255, 178), WARN=(255, 204, 64), ERR=(255, 110, 90), SEG=(32, 88, 48),
                         ON_ACC=(2, 18, 7), FOCUS=(214, 255, 224), OUTLINE=True, RADK=0.18, FONT="mono", FONTK=0.86, PATTERN="scan")
# «Bloque»: brutalista — amarillo señal, tarjetas blancas con borde negro grueso, esquinas rectas y azul eléctrico.
THEMES["bloque"] = dict(ANIM="shapes", SND="wood", BG=(255, 214, 10), PANEL=(255, 255, 255), PANEL2=(232, 232, 232), LINE=(0, 0, 0), TXT=(0, 0, 0), DIM=(66, 62, 50),
                        ACC=(0, 64, 255), OK=(0, 104, 48), WARN=(132, 48, 0), ERR=(214, 0, 44), SEG=(206, 206, 206),
                        FOCUS=(0, 0, 0), OUTLINE=True, RADK=0.0, LAYOUT="side", SCALE=1.25)
# ── v2.31: temas con fondo ANIMADO (ANIM) y tipografía propia que se descarga una vez (hub/fonts.py). Con efectos en «rendimiento» no se animan. ──
# «Aurora»: noche polar — cristal translúcido sobre luces verdes y violetas que se mueven despacio. Letra: Poppins.
THEMES["aurora"] = dict(SND="glass", BG=(6, 12, 22), PANEL=(22, 40, 58), PANEL2=(34, 60, 82), LINE=(84, 132, 150), TXT=(236, 248, 250), DIM=(158, 190, 200),
                        ACC=(64, 226, 170), OK=(110, 236, 150), WARN=(255, 204, 96), ERR=(255, 116, 128), SEG=(46, 80, 104),
                        ON_ACC=(4, 26, 20), FOCUS=(255, 255, 255), RADK=1.3, LAYOUT="side", SCALE=1.25, GLASS=True,
                        GRAD=((8, 20, 38), (4, 8, 16)), ORBS=((0.5, 1.1, 0.5, (30, 60, 120), 50),), ANIM="aurora", FONT="poppins", FONTK=0.94)
# «Píxel»: recreativa de 8 bits — cielo estrellado que parpadea, amarillo moneda y esquinas rectas. Letra: VT323.
THEMES["pixel"] = dict(SND="chip", BG=(8, 8, 28), PANEL=(22, 22, 62), PANEL2=(36, 36, 92), LINE=(108, 108, 200), TXT=(244, 244, 255), DIM=(170, 170, 226),
                       ACC=(255, 214, 40), OK=(96, 240, 120), WARN=(255, 160, 60), ERR=(255, 96, 110), SEG=(52, 52, 120),
                       ON_ACC=(30, 20, 0), FOCUS=(255, 255, 255), OUTLINE=True, RADK=0.0, ANIM="stars", FONT="vt323", FONTK=1.24)
# «Brasa»: fragua — negro cálido, naranja incandescente y ascuas que suben. Letra: Chakra Petch.
THEMES["brasa"] = dict(SND="wood", BG=(14, 8, 6), PANEL=(34, 20, 16), PANEL2=(54, 30, 22), LINE=(120, 62, 40), TXT=(255, 240, 228), DIM=(206, 168, 148),
                       ACC=(255, 122, 40), OK=(140, 220, 110), WARN=(255, 200, 80), ERR=(255, 96, 96), SEG=(74, 42, 30),
                       ON_ACC=(36, 12, 0), FOCUS=(255, 226, 190), RADK=0.5, LAYOUT="side", SCALE=1.25,
                       GRAD=((30, 12, 8), (8, 4, 3)), ORBS=((0.5, 1.15, 0.6, (255, 90, 20), 80),), ANIM="embers", FONT="chakra")
# ── v2.36: temas con aire de consolas famosas. Solo imitan el estilo (colores, movimiento); nada de logos, nombres de marca ni imágenes. ──
# «Onda»: menú de sobremesa de 2006 — azul profundo con cintas de seda que ondulan despacio, cristal translúcido y barra superior.
THEMES["onda"] = dict(SND="silk", BG=(6, 16, 48), PANEL=(16, 34, 86), PANEL2=(26, 52, 120), LINE=(90, 130, 220), TXT=(240, 246, 255), DIM=(170, 190, 235),
                      ACC=(120, 190, 255), OK=(110, 240, 190), WARN=(255, 210, 110), ERR=(255, 120, 130), SEG=(40, 70, 150),
                      ON_ACC=(4, 16, 50), FOCUS=(255, 255, 255), RADK=1.6, GLASS=True, ANIM="silk", FONT="poppins", FONTK=0.94,
                      GRAD=((12, 30, 96), (4, 8, 28)), ORBS=((0.5, 0.5, 0.7, (80, 140, 255), 60),))
# «Tarjeta»: arranque de una consola de 2000 — vacío casi negro con cubos azules que flotan y suben, rótulos nítidos.
THEMES["tarjeta"] = dict(SND="glass", BG=(2, 4, 14), PANEL=(10, 16, 40), PANEL2=(18, 28, 70), LINE=(60, 90, 190), TXT=(232, 240, 255), DIM=(150, 170, 220),
                         ACC=(104, 168, 255), OK=(96, 236, 190), WARN=(255, 204, 96), ERR=(255, 110, 124), SEG=(30, 44, 100),
                         ON_ACC=(2, 8, 30), FOCUS=(200, 225, 255), OUTLINE=True, RADK=0.5, ANIM="cubes", FONT="chakra",
                         GRAD=((6, 10, 30), (1, 2, 8)))
# «Interruptor»: consola híbrida — fondo claro, tarjetas blancas muy redondeadas, rojo y azul cielo, luces suaves rojas y azules.
THEMES["interruptor"] = dict(SND="click", BG=(232, 232, 236), PANEL=(255, 255, 255), PANEL2=(222, 222, 228), LINE=(190, 190, 200), TXT=(24, 24, 30), DIM=(92, 92, 104),
                             ACC=(230, 0, 18), OK=(0, 120, 60), WARN=(170, 96, 0), ERR=(200, 20, 30), SEG=(200, 200, 208),
                             FOCUS=(0, 170, 230), RADK=1.4, ANIM="drift", FONT="poppins", FONTK=0.94,
                             GRAD=((240, 240, 244), (222, 222, 230)), ORBS=((0.2, 0.3, 0.6, (0, 160, 230), 46), (0.85, 0.7, 0.6, (230, 0, 18), 38)))
# «Cubo»: caja compacta violeta — un cubo de líneas que gira despacio sobre un degradado ciruela.
THEMES["cubo"] = dict(SND="marimba", BG=(20, 10, 44), PANEL=(42, 26, 86), PANEL2=(62, 40, 120), LINE=(130, 100, 210), TXT=(244, 238, 255), DIM=(180, 164, 226),
                      ACC=(164, 120, 255), OK=(110, 236, 170), WARN=(255, 204, 100), ERR=(255, 112, 140), SEG=(76, 52, 140),
                      ON_ACC=(20, 6, 50), FOCUS=(255, 255, 255), RADK=1.0, LAYOUT="side", SCALE=1.25, ANIM="spincube", FONT="poppins", FONTK=0.94,
                      GRAD=((40, 18, 90), (10, 4, 26)), ORBS=((0.75, 0.5, 0.7, (140, 90, 255), 56),))
# «16 bits»: consola de los 90 — violeta de cartucho, bandas diagonales que desfilan, esquinas rectas y letra de píxel.
THEMES["retro16"] = dict(SND="chip", BG=(40, 36, 84), PANEL=(70, 64, 128), PANEL2=(92, 84, 156), LINE=(196, 188, 240), TXT=(252, 248, 255), DIM=(206, 198, 240),
                         ACC=(255, 196, 0), OK=(120, 240, 120), WARN=(255, 170, 60), ERR=(255, 100, 100), SEG=(84, 78, 150),
                         ON_ACC=(40, 24, 0), FOCUS=(255, 255, 255), OUTLINE=True, RADK=0.0, ANIM="diag", FONT="vt323", FONTK=1.24)
# Orden: primero los que se parecen entre sí (planos, cristal y azules/violetas), después los más singulares.
# Disposición de Inicio por tema (ui_homes.py): cada uno representa «Tus juegos» a su manera.
for _t, _h in {"dark": ("grid", None), "light": ("posters", None), "quiver": ("list", "dock"), "prototipo": ("hero", None), "cristal": ("orbs", None),
               "aurora": ("orbs", "glow"), "onda": ("xmb", None), "tarjeta": ("slots", "card"), "cubo": ("coverflow", None), "interruptor": ("switch", None),
               "brasa": ("posters", "shelf"), "pixel": ("slots", "level"), "retro16": ("slots", "cart"), "neon": ("list", "score"),
               "fosforo": ("list", "term"), "tinta": ("list", "index"), "bloque": ("blocks", None)}.items():
    THEMES[_t].update(HOME=_h[0], HOMEV=_h[1])
SND = "soft"                                              # timbre de los sonidos del tema: soft · glass · chip · wood
THEMES["dark"].update(ANIM="motes")
THEMES["light"].update(ANIM="motes")
# v2.38: los 17 «temas» de antes pasan a ser PALETAS de 14 temas (themes_fam.py). _LEG guarda los antiguos como origen de colores y estructura.
_LEG = dict(THEMES)
THEME_ORDER = themes_fam.ORDER
for _f in themes_fam.FAMILIES:
    THEMES[_f] = themes_fam.build(_LEG, _f)
FAMILY, PAL = "limpio", "oscuro"
def _fsig(p):
    """Firma barata de un archivo (fecha en ns y tamaño) para memo(): si otro proceso lo reescribe, la clave cambia y se relee."""
    try:
        st = os.stat(p)
        return st.st_mtime_ns, st.st_size
    except OSError:
        return None


def _gamescope_running() -> bool:
    try:
        for d in os.listdir("/proc"):
            if d.isdigit():
                try:
                    with open(f"/proc/{d}/comm", encoding="utf-8") as f:
                        if f.read().strip() in ("gamescope", "gamescope-wl", "gamescope-sessio"):
                            return True
                except OSError:
                    continue
    except OSError:
        pass
    return False


TAP_WAIT = 0.25                                        # v3.18: espera de un clic «instantáneo» (posible atajo de Steam)
CHORD_WIN = 0.12                                       # v3.17: ventana para reconocer «guía + botón» (atajos de Steam)
_MOTION_EV = (pygame.MOUSEMOTION, pygame.FINGERMOTION, pygame.MOUSEWHEEL)
ANIM = None                                                # fondo animado del tema: "aurora" · "stars" · "embers"
FONTK = 1.0                                                # la monoespaciada es más ancha: el tema la encoge para que quepa
FONT = PATTERN = None                                      # tipografía ("serif"/"mono") y trama del fondo ("grid"/"scan") del tema
FONT_FAMS = {None: "notosans,dejavusans,liberationsans,arial", "serif": "notoserif,dejavuserif,liberationserif,georgia,timesnewroman",
             "mono": "jetbrainsmono,notosansmono,dejavusansmono,liberationmono,couriernew"}
SCALE = 1.0                                                  # el tema puede agrandar toda la interfaz (Prototipo: 1,25 para la pantalla del Ally)
OUTLINE, RADK, FOCUS, LAYOUT, GLASS = False, 1.0, None, "top", False
SCREENS = None      # v3.05: organización propia de Explorar/Descargas de una identidad del Estudio; None = la de siempre
MAT = None          # v3.04: material de las identidades del Estudio {opacity, shadow, border, blur}; None = temas heredados
MOTION = None       # v3.09: factores del fondo animado {speed, intensity, density}; None = 1, 1, 1 (temas heredados)
TYPE = DENS = None  # v3.09: niveles tipográficos y densidad declarados por la identidad (UI.type_font); None = valores base
GRAD = ORBS = None                                         # fondo con profundidad del tema: degradado (arriba, abajo) y resplandores; None = el de Oscuro     # los redefine apply_theme (FOCUS None = usar TXT; LAYOUT "side" = barra lateral)
THEME_LABEL = {f: f"{v['label'].upper()} ({v['desc'].lower()})" for f, v in themes_fam.FAMILIES.items()}
STUDIO_ORDER = tuple(hubthemes.studio.PREFIX + p for p in hubthemes.studio.ORDER)      # v2.97: Estudio de temas (prueba), aparte de THEME_ORDER
THEME_LABEL.update({n: f"{hubthemes.studio.family(n)['label'].upper()} ({hubthemes.studio.family(n)['desc'].lower()})" for n in STUDIO_ORDER})
THEME_LABEL.update({"dark": "OSCURO", "light": "CLARO", "aurora": "AURORA", "retro16": "16 BITS"})
FX_LABEL = {"glass": "CRISTAL (blur precalculado)", "balanced": "EQUILIBRADO (fondo quieto)", "perf": "RENDIMIENTO (sin blur)"}


def on_color(c, dark=None):
    """Color de texto legible sobre el fondo c: el oscuro del tema si c es claro (p. ej. el naranja), blanco si no."""
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    L = 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
    return (dark or (26, 14, 3)) if L > 0.28 else (255, 255, 255)


def theme_dict(name, pal=None, bg=None, layout=None):
    """Dict del tema: los 15 heredados por legacy.build; las identidades del Estudio («v3:…», v2.97) por el adaptador del motor nuevo."""
    if hubthemes.studio.is_studio(name):
        return hubthemes.studio.build(name, pal, bg, layout)
    return hubthemes.legacy.build(name, pal, bg)


def apply_theme(name, pal=None, bg=None, layout=None, a11y=None):
    """Cambia la paleta global. Hay que invalidar las cachés de dibujo después (UI.set_look lo hace).
    v3.09: `a11y` (movimiento reducido, alto contraste, texto grande) se aplica encima, igual para todos los temas; apagado no toca nada."""
    t = {"OUTLINE": False, "GLASS": False, "GRAD": None, "ORBS": None, "FONT": None, "PATTERN": None, "FONTK": 1.0, "ANIM": None, "SND": "soft", "HOME": "grid", "HOMEV": None, "RADK": 1.0, "FOCUS": None, "LAYOUT": "top", "ON_ACC": (255, 255, 255), "SCALE": 1.25, "STUDIO_LAYOUT": None, "MAT": None, "SCREENS": None, "MOTION": None, "TYPE": None, "DENS": None, **theme_dict(name, pal, bg, layout)}
    t = a11ymod.apply(t, a11y)
    g = globals()
    for k, v in t.items():
        g[k] = v
DIRS = ("UP", "DOWN", "LEFT", "RIGHT")
TABS = (("home", "INICIO"), ("games", "EXPLORAR"), ("downloads", "DESCARGAS"), ("settings", "AJUSTES"))
SUBTAB = {"library": "games", "search": "games", "steam": "settings", "art": "settings"}   # pantallas que cuelgan de EXPLORAR


def fmt_size(n):
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def fmt_eta(s):
    if s is None:
        return "—"
    s = int(s)
    return f"{s // 3600}h {s % 3600 // 60}m" if s >= 3600 else f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


class View:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.off = 0.0
        self.vel = 0.0
        self.target = None      # desplazamiento suave hacia el foco (se acerca en ~0,12 s)
        self.h = 0
        self.nh = 0

    def clamp(self):
        self.off = max(0.0, min(self.off, max(0, self.h - self.rect.h)))


class Wd:
    __slots__ = ("key", "rect", "cb", "focus", "adj", "x", "y", "view")

    def __init__(self, key, rect, cb, focus, adj, x, y, view):
        self.key, self.rect, self.cb, self.focus, self.adj, self.x, self.y, self.view = key, rect, cb, focus, adj, x, y, view


GH_SEARCH = "https://github.com/search?type=repositories"


from . import ui_detail, ui_downloads, ui_explore, ui_files, ui_fx, ui_home, ui_homes, ui_modal, ui_recipes, ui_settings  # noqa: E402


def _adopt(cls):
    """Los métodos de las partes separadas (ui_home.py…) resuelven sus nombres globales en ESTE módulo: el tema cambia ACC/TXT…
    en tiempo de ejecución y las pruebas parchean hub.ui.subprocess; así todo sigue viéndose igual que si estuvieran aquí."""
    g = globals()
    for k, v in list(vars(cls).items()):
        wrap = type(v) if isinstance(v, (staticmethod, classmethod)) else None
        f = v.__func__ if wrap else v
        if isinstance(f, types.FunctionType):
            nf = types.FunctionType(f.__code__, g, f.__name__, f.__defaults__, f.__closure__)
            nf.__kwdefaults__, nf.__doc__, nf.__qualname__ = f.__kwdefaults__, f.__doc__, f.__qualname__
            setattr(cls, k, wrap(nf) if wrap else nf)
    return cls


_PARTS = tuple(_adopt(m) for m in (ui_fx.FxMixin, ui_home.HomeMixin, ui_homes.HomeLayoutsMixin, ui_explore.ExploreMixin, ui_downloads.DownloadsMixin, ui_settings.SettingsMixin,
                                   ui_detail.DetailMixin, ui_modal.ModalMixin, ui_files.FilesMixin, ui_recipes.RecipesMixin))


class UI(*_PARTS):
    active_views = []

    def __init__(self, size=None):
        pygame.display.init()
        pygame.font.init()
        size = size or os.environ.get("HUB_WINDOW")
        if isinstance(size, str):
            size = tuple(int(v) for v in size.lower().split("x"))
        self.screen = pygame.display.set_mode(size) if size else pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Forgeinator 3000")
        self._set_window_icon()
        pygame.mouse.set_visible(bool(size))
        self.W, self.H = self.screen.get_size()
        self.k0 = max(0.7, min(1.6, self.H / 1080.0)) * float(os.environ.get("HUB_FONT_SCALE", "1"))
        self.k = self.k0
        self._fonts, self._tc = {}, {}
        self._glyph_ok, self.glyph_subs, self._sane_c, self._fit_c = {}, {}, {}, {}
        threading.Thread(target=lambda: launchlog.scan_orphans(), daemon=True).start()
        self._font_path = pygame.font.match_font("notosans,dejavusans,liberationsans,arial") or None
        self._font_bold = pygame.font.match_font("notosans,dejavusans,liberationsans,arial", bold=True) or self._font_path
        # estado
        self.running = True
        self.exit_at, self.game_pids = 0, []
        self.play_pr, self.play_t, self.play_id, self.play_wait, self.play_name = None, 0, "", 6.0, ""
        self.art = None
        self.tab, self.detail, self.modal = "home", None, None
        if os.environ.get("HUB_START") == "steam":
            self.tab = "steam"
            steamsetup.clear_autostart()   # el arranque automático es de una sola vez
        self.explore = "cats"   # EXPLORAR: "cats" (consolas) o "list" (juegos de una consola)
        self.focus, self.show_focus, self.reveal = None, False, False
        self.smooth_scroll = os.environ.get("HUB_SMOOTH_SCROLL", "1") == "1"
        self.widgets, self.new, self.views, self.cur = [], [], {}, None
        self._planning = set()
        self.pending_osk = None
        self.stick = {}
        self.queue, self.held, self.last_press, self.pad_q = collections.deque(), {}, {}, collections.deque()
        self.win_focus, self.mute_until, self.dropped, self.lost_at = True, 0.0, 0, 0.0
        self.gs_base, self.gs_now = None, None   # ventana de Gamescope con foco cuando Hub está delante / ahora
        gsfocus.start(self._gs_changed, alive=lambda: self.running)
        self.touch = None
        self.toast_msg, self.toast_t = "", 0
        self.t = 0.0
        self._cov, self._cov_jobs, self._cov_done = {}, set(), []   # portadas: caché, en preparación, terminadas por los hilos
        self.filter, self.query = "Todos", ""
        self.sel_asset, self.rel, self.loading = {}, {}, set()
        self.rel_t = {}   # v2.64: cuándo (time.time) se trajeron los datos de releases de cada repo (disco o GitHub)
        self.rel_sel, self.rel_sum = {}, {}   # release elegida a mano por juego (dict) y resumen de releases recientes (qué trae cada una)
        self.ver_view = {}                                   # método de Linux que se está mirando en la ficha (release | built)
        self.ver_adv = set()                                 # fichas con «Avanzado» desplegado
        self._rcp, self._rcp_q = {}, []        # recetas por juego (caché) y cola de acciones que los hilos piden al hilo principal
        self.sel_win, self.asset_os = {}, {}   # build de Windows elegido y qué lista de builds se muestra (linux|windows) por juego
        self.builds = []
        self.sq, self.ssuf, self.sres, self.sbusy, self.serr = "", "recomp", None, False, ""
        self.clip_repo, self.clip_seen, self.rview = "", "", None
        self.clip_url = ""
        self._hb_ok, self.hb_repo = None, ""
        self.recv, self.recv_busy = [], False
        self.hb_opening = 0
        self.brow_t = 0.0
        self.hb_fatal = False
        self._last_char = ("", 0.0)
        self.last_input, self.t0, self.why, self.fails, self.fps = time.time(), time.time(), "", 0, 0.0
        for _d in (config.path("downloads_dir"), config.BROWSER_DL):
            try:
                Path(_d).mkdir(parents=True, exist_ok=True)
            except OSError as ex:
                print(f"[dl] no pude crear {_d}: {ex}", file=sys.stderr, flush=True)
        self.gh_login, self.device = auth.login(), None
        self.match_res, self.detected, self.progress, self.watch = {}, {}, {}, None
        self.roms_msg, self.rom_index, self.rom_scanned = {}, [], set()
        self.lib_rows, self.lib_busy, self.lib_msg, self.lib_plat, self.lib_mode, self.lib_limit, self.lib_loaded = [], False, "", "", "all", 60, False
        self.cfg = config.settings()
        osver.DEFAULT_PROTON = str(self.cfg.get("proton_default") or "")   # v2.65
        self._look_norm()
        apply_theme(self.cfg["theme"], self._pal(), self._bg(), self._layout(), self._a11y())
        self._publish_look()
        self.k = self.k0 * SCALE
        self.perf = perf.Probe(self.cfg.get('perf_log', False))
        self.sfx = sfx.Sfx(self.cfg.get("sounds", True), self.cfg.get("sound_volume", 0.5), config.DATA / "sounds")
        self.sfx.profile = SND if SND in sfx.PROFILES else "soft"      # timbre del tema con el que se arranca
        self.sfx.warm()
        UI.zoom = float(self.cfg.get("browser_zoom", 1.5))
        self.entries = catalog.load()
        threading.Thread(target=self._cwd_migrate, daemon=True).start()   # v1.96: la carpeta de trabajo vuelve a ser la del juego
        self.mgr = downloads.Manager(max_active=self.cfg["max_active"], connections=self.cfg["connections"])
        self.cjobs = catalogjobs.Jobs(on_done=self._cat_done, on_wait=self._cat_wait, store=config.DATA / "catalog_jobs.json")   # descargas que hace tu servidor de catálogo (JSON-RPC local)
        self.cat_health, self.cat_hb, self.cat_hb_t = {}, False, 0.0
        threading.Thread(target=lambda: print(f"[catalogo] retomadas {self.cjobs.restore()} descarga(s) del servicio de la sesión anterior", file=sys.stderr, flush=True), daemon=True).start()
        if self.cfg.get("catalog_autostart", True):   # el servicio de catálogo arranca con Hub (si está instalado), sin bloquear la ventana
            threading.Thread(target=self._cat_autostart, daemon=True).start()
        self.mgr.on_done = self._on_done
        self.sdlc, self.ctrls = None, {}
        self.libchk, self.libs_ok, self._osv, self._place_done = {}, set(), {}, set()   # bibliotecas que faltan por juego (ldd) y los que quieres lanzar igualmente
        self.no_pad = os.environ.get("HUB_NO_PAD") == "1"   # pruebas: el mando real del Ally no debe pulsar nada
        self._init_controllers()
        if not self.no_pad:
            gamepad.start(lambda b: self.pad_q.append((b, time.time())), alive=lambda: self.running)
        threading.Thread(target=self._watcher, daemon=True).start()
        self.dlw, self.want_front, self.brow_proc, self.dl_done = dlwatch.DLWatch(self.cfg["watch_dirs"], self.cfg.get("dl_detect_direct", False)), False, None, None
        threading.Thread(target=self._dl_loop, daemon=True).start()
        threading.Thread(target=self._clip_watcher, daemon=True).start()
        self.adv_open = bool(self.cfg.get("adv_open", False))
        self.set_page = None          # categoría abierta en Ajustes (None = lista de categorías)
        self.more_tab = {}                                # pestaña abierta en «Más opciones» por juego
        self.fold_state = {}                              # v2.89: secciones plegables de la ficha
        self.more_open = set()                            # fichas con «Más opciones» desplegado
        self._upd_first = threading.Event()
        self.upd_ready, self.upd_busy = None, ""          # versión nueva de Hub ya puesta en ~/Games/actualizaciones (la detecta _upd_loop)
        threading.Thread(target=self._upd_loop, daemon=True).start()
        threading.Thread(target=lambda: setattr(self, "_hb_ok", hubbrowser.ready()), daemon=True).start()
        if auth.token() and not self.gh_login:
            threading.Thread(target=self._whoami, daemon=True).start()
        try:   # una sola vez y en el hilo principal: pygame.scrap.init() repetido desde el hilo del portapapeles acababa cerrando el vídeo de SDL (cada ~5 min)
            pygame.scrap.init()
        except Exception:  # noqa: BLE001
            pass
        self._prewarm()

    # ── recursos / dibujo básico ─────────────────────────────
    def _prewarm(self):
        """Crea de antemano las fuentes habituales y la caché de instalados: antes se hacía dentro del primer fotograma de Inicio (~100 ms en el Ally)."""
        for b in (False, True):
            for s in (14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 28, 30, 32, 34, 40):
                self.font(s, b)
        self._inst_refresh()

    def font(self, size, bold=False, weight=None):
        """weight (v3.09, para los diseños nuevos): «regular» | «medium» | «bold». «medium» usa el archivo Medium real si lo hay (Poppins,
        Chakra Petch descargadas, o la del sistema si trae ese peso instalado); si no, la negrita. VT323: su único peso."""
        if weight == "medium":
            mp = self.__dict__.get("_font_medium")
            if mp:
                px = max(13, int(size * self.k * FONTK))
                key = (px, "medium")
                if key not in self._fonts:
                    self._fonts[key] = pygame.font.Font(mp, px)
                return self._fonts[key]
            bold = FONT != "vt323"
        elif weight is not None:
            bold = weight == "bold"
        px = max(13, int(size * self.k * FONTK))
        key = (px, bold)
        if key not in self._fonts:
            f = self._fonts[key] = pygame.font.Font(self._font_bold if bold else self._font_path, px)
            if bold and getattr(self, "_font_fat", False):          # la fuente no trae negrita: se engorda la normal
                try:
                    f.set_bold(True)
                except (AttributeError, pygame.error):
                    pass
        return self._fonts[key]

    def type_font(self, level):
        """v3.09: fuente de un nivel tipográfico de la identidad (display, heading, title, body, secondary, caption, numeric).
        Solo para pantallas nuevas: las existentes siguen con sus tamaños de siempre. → (pygame.font.Font, «upper» | None)."""
        lv = (TYPE or hubthemes.studio.type_scale("v3:minimal")).get(level) or hubthemes.studio.TYPE_BASE.get(level, (20, "regular"))
        if isinstance(lv, tuple):
            lv = {"size": lv[0], "weight": lv[1], "case": None}
        return self.font(lv["size"], weight=lv["weight"]), lv.get("case")

    def _set_window_icon(self):
        """v3.13: icono de Forgeinator 3000 en la ventana (escritorio y barra de tareas). Sin el archivo, el de siempre."""
        try:
            ic = Path(__file__).resolve().parents[1] / "assets" / "brand" / "icon-64.png"
            if ic.is_file():
                pygame.display.set_icon(pygame.image.load(str(ic)))
        except Exception:  # noqa: BLE001
            pass

    def _sys_medium(self, fam):
        """Archivo del peso medio (fontconfig weight 100) de una familia del sistema, solo si de verdad está instalado; None si no."""
        c = self.__dict__.setdefault("_sysmed_c", {})
        if fam in c:
            return c[fam]
        path = None
        try:
            for name in fam.split(","):
                out = subprocess.run(["fc-match", "-f", "%{file}\t%{weight}\t%{variable}", f"{name}:weight=100"],
                                     capture_output=True, text=True, timeout=2).stdout
                fp, w, var = (out.split("\t") + ["", "", ""])[:3]
                ok_name = name.replace(" ", "").lower() in Path(fp).name.replace("-", "").replace("_", "").lower()
                # una fuente variable (NotoSans[wght].ttf) se dibujaría con su peso por defecto: no cuenta como Medium
                if fp and w.strip() == "100" and ok_name and var.strip() != "True" and "[" not in fp and Path(fp).is_file():
                    path = fp
                    break
        except Exception:  # noqa: BLE001  (sin fontconfig: se usa la negrita)
            path = None
        c[fam] = path
        return path

    # Glifos que la fuente del Ally puede no traer (se veían como cuadrados): se sustituyen por ASCII si faltan.
    GLYPH_FALLBACK = {"✓": "ok", "✔": "ok", "↑": "^", "↓": "v", "←": "<", "→": ">", "▶": ">", "◀": "<", "▲": "^", "▼": "v", "‹": "<", "›": ">",
                      "●": "o", "★": "*", "✕": "x", "×": "x", "↻": "o", "⟳": "o", "•": "*", "—": "-", "–": "-", "·": ".", "≈": "~", "…": "...", "ℹ": "i", "⚙": "*", "⚠": "!", "✗": "x", "✘": "x", "⏸": "||", "⏵": ">", "“": '"', "”": '"', "’": "'",
                      "─": "-", "═": "=", "≠": "!=", "≥": ">=", "≤": "<=", "⇧": "^", "↔": "<>", "◂": "<", "▸": ">"}
    SYMBOL_CATS = ("So", "Sm", "Sk")   # v2.70: flechas, formas y dingbats se sustituyen SIEMPRE: la fuente del Ally dibuja un cuadrado con avance > 0
    INVISIBLE = {0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF, 0x00AD, 0x034F, 0x180E}
    SPACES = {0x00A0, 0x202F, 0x2007, 0x2009, 0x200A, 0x2002, 0x2003, 0x3000}
    _deny = ()          # (solo tests) caracteres que se tratan como ausentes para simular una fuente pobre

    def has_glyph(self, ch):
        _tob = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
        if ch in self._deny:
            return False
        ok = self._glyph_ok.get(ch)
        if ok is None:
            try:
                f = self.font(20)
                m = f.metrics(ch)[0]
                ok = m is not None and m[4] > 0            # sin avance = la fuente no lo dibuja
                if ok:                                     # v2.70: con avance pero idéntico al «cuadrado» de glifo ausente = tampoco existe
                    a = _tob(f.render(ch, True, (255, 255, 255)), "RGBA")
                    ok = all(a != _tob(f.render(b, True, (255, 255, 255)), "RGBA") for b in ("\uffff", "\U0010ffff"))
            except Exception:  # noqa: BLE001
                ok = True
            self._glyph_ok[ch] = ok
        return ok

    def sane(self, s):
        """Cambia por equivalentes ASCII los caracteres que la fuente no tiene (nunca dibuja un cuadrado)."""
        if s.isascii():
            return s
        c = self._sane_c.get(s)
        if c is not None:
            return c
        out = []
        for ch in s:
            o = ord(ch)
            if o in self.INVISIBLE or unicodedata.category(ch) in ("Cf", "Cc", "Co", "Cs") or 0xFE00 <= o <= 0xFE0F or 0x1F3FB <= o <= 0x1F3FF:
                continue                       # invisibles (ZWJ, selector de emoji…): en algunas fuentes salen como rectángulo
            if o in self.SPACES:
                out.append(" ")
                continue
            if o == 0x2011:
                out.append("-")
                continue
            if o < 128 or ch in "áéíóúñüÁÉÍÓÚÑÜ¿¡°€×" or (unicodedata.category(ch) not in self.SYMBOL_CATS and self.has_glyph(ch)):
                out.append(ch)
            else:
                self.glyph_subs[ch] = self.glyph_subs.get(ch, 0) + 1
                out.append(self.GLYPH_FALLBACK.get(ch, "" if unicodedata.category(ch) == "So" else "?"))
        if len(self._sane_c) > 4000:
            self._sane_c.clear()
        self._sane_c[s] = res = "".join(out)
        return res

    def surf(self, s, size, color, bold=False):
        s = self.sane(s)
        key = (s, size, color, bold)
        if key not in self._tc:
            if len(self._tc) > 600:
                self._tc.clear()
            self._tc[key] = self.font(size, bold).render(s, True, color)
        return self._tc[key]

    def fit(self, s, size, maxw, bold=False):
        key = (s, size, int(maxw), bold, self.k, FONTK, self._font_path)     # v3.09: con la letra del tema (texto grande, otra fuente)
        c = self._fit_c.get(key)
        if c is not None:
            return c
        s0 = s
        s = self.sane(s)
        f = self.font(size, bold)
        if f.size(s)[0] > maxw:
            while len(s) > 1 and f.size(s + "…")[0] > maxw:
                s = s[:-1]
            s += "…"
        if len(self._fit_c) > 6000:
            self._fit_c.clear()
        self._fit_c[key] = s
        return s

    def wrap(self, s, size, maxw, bold=False, max_lines=99):
        f, lines = self.font(size, bold), []
        for para in self.sane(str(s)).split("\n"):
            cur = ""
            for w in para.split(" "):
                t = (cur + " " + w).strip()
                if f.size(t)[0] <= maxw or not cur:
                    cur = t
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self.fit(lines[-1] + "…", size, maxw, bold)
        return lines

    def text(self, s, x, y, size=22, color=None, bold=False, maxw=None, anchor="tl"):
        s = str(s)
        color = TXT if color is None else color
        if maxw:
            s = self.fit(s, size, maxw, bold)
        su = self.surf(s, size, color, bold)
        r = su.get_rect()
        setattr(r, {"tl": "topleft", "tr": "topright", "mid": "midtop", "c": "center", "ml": "midleft", "mr": "midright"}[anchor], (x, y))
        self.screen.blit(su, r)
        return r

    def para(self, s, x, y, size, maxw, color=None, bold=False, max_lines=99, gap=1.28):
        color = DIM if color is None else color
        """Dibuja texto con saltos; devuelve la y final (relativa a lo que se le pasó)."""
        for ln in self.wrap(s, size, maxw, bold, max_lines):
            self.text(ln, x, y, size, color, bold)
            y += int(size * self.k * gap)
        return y

    def _mat_hit(self, color):
        """¿Es una superficie del tema (panel, panel claro, segmento, o su versión «con foco»)? Solo esas llevan material."""
        for base in (PANEL, PANEL2, SEG):
            if all(0 <= c - b <= 22 for c, b in zip(color, base)):
                return True
        return False

    def _mat_shadow(self, rc, rad, amount):
        """Sombra suave bajo una superficie (material del tema). Se prepara una vez por tamaño; luego cuesta un blit."""
        spread = int(self.n(4) + self.n(26) * amount)
        key = (rc.w, rc.h, rad, round(amount, 2), spread)
        c = self.__dict__.setdefault("_ms_c", {})
        if len(c) > 400:
            c.clear()
        sf = c.get(key)
        if sf is None:
            sf = pygame.Surface((rc.w + 2 * spread, rc.h + 2 * spread), pygame.SRCALPHA)
            total = min(150, int(255 * amount * 1.4))
            steps = 5
            for i in range(steps):
                f = 1 - i / steps
                r = pygame.Rect(0, 0, rc.w + int(2 * spread * f), rc.h + int(2 * spread * f))
                r.center = sf.get_rect().center
                pygame.draw.rect(sf, (0, 0, 0, max(1, total // steps)), r, border_radius=rad + int(spread * f))
            c[key] = sf
        self.screen.blit(sf, (rc.x - spread, rc.y - spread + spread // 2))

    def _mat_fill(self, rc, color, rad, alpha):
        key = (rc.w, rc.h, rad, tuple(color), alpha)
        c = self.__dict__.setdefault("_mf_c", {})
        if len(c) > 400:
            c.clear()
        sf = c.get(key)
        if sf is None:
            sf = c[key] = pygame.Surface((rc.w, rc.h), pygame.SRCALPHA)
            pygame.draw.rect(sf, (*color, alpha), sf.get_rect(), border_radius=rad)
        self.screen.blit(sf, rc.topleft)

    def rr(self, rect, color, r=14, width=0, a=None):
        # v3.04: material del tema (solo identidades del Estudio; los 15 temas heredados no traen MAT y no pasan por aquí)
        if MAT and not width and len(color) == 3 and self.cfg.get("fx") != "perf" and self._mat_hit(color):
            rc = pygame.Rect(rect)
            if rc.w >= self.n(40) and rc.h >= self.n(36):
                rad = int(r * self.k)
                if MAT["shadow"] > 0:
                    self._mat_shadow(rc, rad, MAT["shadow"])
                if GLASS and a is None:
                    a = self._glass_alpha(color)
                if GLASS and a is not None:
                    self._glass_rect(rc, color, rad, a)
                elif MAT["opacity"] < 0.995:
                    self._mat_fill(rc, color, rad, int(255 * MAT["opacity"]))
                else:
                    self._aa_fill(rc, color, rad) if rc.w >= 2 * rad and rc.h >= 2 * rad and rad >= 6 else \
                        pygame.draw.rect(self.screen, color, rc, border_radius=min(rad, rc.w // 2, rc.h // 2))
                if MAT["border"] > 0 and not GLASS:
                    pygame.draw.rect(self.screen, LINE, rc, max(1, round(MAT["border"] * self.k)), border_radius=rad)
                return
        if GLASS and not width and len(color) == 3 and rect[2] > 3 and rect[3] > 3 and self.cfg.get("fx") != "perf":
            if a is None:
                a = self._glass_alpha(color)
            if a is not None:
                return self._glass_rect(rect, color, int(r * self.k), a)
        rad = int(r * self.k)
        if not width and rad >= 6 and len(color) == 3 and self.cfg.get("fx") != "perf":
            rc = pygame.Rect(rect)
            if rc.w >= 2 * rad and rc.h >= 2 * rad:
                return self._aa_fill(rc, color, rad)
            rad = min(rad, rc.w // 2, rc.h // 2)
        pygame.draw.rect(self.screen, color, rect, width, border_radius=rad)

    def _aa_fill(self, rc, color, rad):
        """Rectángulo redondeado relleno con esquinas suaves, como UNA sola copia ya preparada (una por tamaño, radio y color): cuesta unos
        7 µs por panel; dibujar cuerpo y esquinas por separado en cada fotograma costaba ~55 µs (7× más) y se notaba en el Ally.
        Se arma una vez: cuerpo con rellenos y cuatro esquinas suavizadas (un cuarto de círculo dibujado a 4× y reducido)."""
        key = (rc.w, rc.h, rad, tuple(color))
        c = getattr(self, "_aa_c", None)
        if c is None or self._aa_bytes > 80_000_000 or len(c) > 900:
            c = self._aa_c = {}
            self._aa_bytes = 0
        sf = c.get(key)
        if sf is None:
            ck = (rad, tuple(color))
            cc = getattr(self, "_corner_c", None)
            if cc is None or len(cc) > 300:
                cc = self._corner_c = {}
            cs = cc.get(ck)
            if cs is None:
                S = 4
                big = pygame.Surface((rad * S, rad * S), pygame.SRCALPHA)
                pygame.draw.circle(big, (*color, 255), (rad * S, rad * S), rad * S)
                tl = pygame.transform.smoothscale(big, (rad, rad))
                cs = cc[ck] = (tl, pygame.transform.flip(tl, True, False), pygame.transform.flip(tl, False, True), pygame.transform.flip(tl, True, True))
            w, h = rc.w, rc.h
            sf = pygame.Surface((w, h), pygame.SRCALPHA)
            sf.fill((*color, 255), (rad, 0, w - 2 * rad, h))
            sf.fill((*color, 255), (0, rad, rad, h - 2 * rad))
            sf.fill((*color, 255), (w - rad, rad, rad, h - 2 * rad))
            for img, pos in ((cs[0], (0, 0)), (cs[1], (w - rad, 0)), (cs[2], (0, h - rad)), (cs[3], (w - rad, h - rad))):
                sf.blit(img, pos, special_flags=pygame.BLEND_RGBA_MAX)
            sf = sf.convert_alpha()
            c[key] = sf
            self._aa_bytes = getattr(self, "_aa_bytes", 0) + w * h * 4
        self.screen.blit(sf, rc.topleft)

    @staticmethod
    def _glass_alpha(color):
        """Opacidad de los paneles del tema Cristal (y de su versión «con foco»); None = el color va opaco (acento, avisos, texto)."""
        for base, al in ((PANEL, 118), (PANEL2, 150), (SEG, 178)):
            if all(0 <= c - b <= 22 for c, b in zip(color, base)):
                return al
        return None

    def _glass_rect(self, rect, color, rad, a):
        """Rectángulo redondeado translúcido con filo de luz; cada combinación se prepara una vez."""
        rc = pygame.Rect(rect)
        key = (rc.w, rc.h, rad, tuple(color), a)
        c = getattr(self, "_gr_c", None)
        if c is None or len(c) > 500:
            c = self._gr_c = {}
        sf = c.get(key)
        if sf is None:
            sf = pygame.Surface((rc.w, rc.h), pygame.SRCALPHA)
            pygame.draw.rect(sf, (*color, a), sf.get_rect(), border_radius=rad)
            hi = pygame.Surface((rc.w, rc.h), pygame.SRCALPHA)                  # velo de luz que se apaga hacia abajo (sin línea dura)
            for yy in range(rc.h):
                pygame.draw.line(hi, (255, 255, 255, int(26 * max(0.0, 1 - yy / (rc.h * 0.8)) ** 1.5)), (0, yy), (rc.w, yy))
            mask = pygame.Surface((rc.w, rc.h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=rad)
            hi.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            sf.blit(hi, (0, 0))
            pygame.draw.rect(sf, (255, 255, 255, 46), sf.get_rect(), 1, border_radius=rad)
            c[key] = sf
        self.screen.blit(sf, rc.topleft)

    def n(self, v):
        return int(v * self.k)

    def ring(self, r, foc):
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 24, max(3, self.n(3)))

    def tri(self, cx, cy, size, direction, color):
        """Triángulo dibujado (◀ ▶ ▲ ▼ sin depender de la fuente)."""
        h = size / 2
        pts = {"left": [(cx + h * 0.6, cy - h), (cx + h * 0.6, cy + h), (cx - h * 0.8, cy)], "right": [(cx - h * 0.6, cy - h), (cx - h * 0.6, cy + h), (cx + h * 0.8, cy)],
               "up": [(cx - h, cy + h * 0.6), (cx + h, cy + h * 0.6), (cx, cy - h * 0.8)], "down": [(cx - h, cy - h * 0.6), (cx + h, cy - h * 0.6), (cx, cy + h * 0.8)]}[direction]
        pygame.draw.polygon(self.screen, color, pts)

    def check(self, cx, cy, size, color, width=3):
        h = size / 2
        pygame.draw.lines(self.screen, color, False, [(cx - h, cy), (cx - h * 0.25, cy + h * 0.7), (cx + h, cy - h * 0.7)], max(2, int(width * self.k)))

    def chevron(self, cx, cy, size, color, direction="right", width=3):
        h = size / 2
        pts = {"right": [(cx - h * 0.5, cy - h), (cx + h * 0.5, cy), (cx - h * 0.5, cy + h)], "down": [(cx - h, cy - h * 0.5), (cx, cy + h * 0.5), (cx + h, cy - h * 0.5)],
               "up": [(cx - h, cy + h * 0.5), (cx, cy - h * 0.5), (cx + h, cy + h * 0.5)], "left": [(cx + h * 0.5, cy - h), (cx - h * 0.5, cy), (cx + h * 0.5, cy + h)]}[direction]
        pygame.draw.lines(self.screen, color, False, pts, max(2, int(width * self.k)))

    def work(self, label, fn, done=None):
        """v2.77: ejecuta fn en un hilo y muestra un indicador animado (rueda + segundos) mientras dure; done(resultado, error) se llama al terminar.
        Así una operación larga (reparar, copiar, comprobar un hash…) no parece que la interfaz se haya congelado."""
        w = self.__dict__.setdefault("_work", {})
        wid = object()
        w[wid] = (label, time.time())

        def job():
            res, err = None, None
            try:
                res = fn()
            except Exception as ex:  # noqa: BLE001
                err = ex
                print(f"[trabajo] {label}: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            finally:
                w.pop(wid, None)
            if done:
                done(res, err)
        threading.Thread(target=job, daemon=True).start()

    def _workbar(self):
        w = getattr(self, "_work", None)
        if not w:
            return
        label, t0 = max(w.values(), key=lambda v: v[1])
        el = time.time() - t0
        txt = label + (f"  ·  {int(el)} s" if el >= 3 else "") + (f"  (+{len(w) - 1} más)" if len(w) > 1 else "")
        f = self.font(20, True)
        tw = min(self.W - self.n(120), f.size(self.sane(txt))[0] + self.n(96))
        r = pygame.Rect(0, 0, tw, self.n(58))
        r.midbottom = (self.W // 2, self.H - self.n(self.FH) - self.n(18) - (self.n(90) if time.time() < self.toast_t else 0))
        self.rr(r, PANEL2, 29, a=245 if GLASS else None)
        self.rr(r, ACC, 29, 2)
        cx, cy = r.x + self.n(34), r.centery
        rad = self.n(12)
        ang = (time.time() * 5.0) % (2 * math.pi)
        for k in range(10):                                   # rueda: 10 puntos que se desvanecen detrás del que gira
            a = ang - k * 0.5
            c = tuple(int(ACC[i] * (1 - k / 11) + PANEL2[i] * (k / 11)) for i in range(3))
            pygame.draw.circle(self.screen, c, (cx + int(rad * math.cos(a)), cy + int(rad * math.sin(a))), max(2, self.n(4)))
        self.text(txt, r.x + self.n(62), r.centery, 20, TXT, True, tw - self.n(78), anchor="ml")

    def toast(self, msg):
        self.toast_msg, self.toast_t = msg, time.time() + 3.5

    # ── vistas con scroll ────────────────────────────────────
    def begin(self, name, rect):
        v = self.views.setdefault(name, View())
        v.rect, v.nh, self.cur = pygame.Rect(rect), 0, v
        self.active_views.append(v)
        hh, fh = self.n(self.HH), self.n(self.FH)
        if v.rect.y == hh and v.rect.bottom == self.H - fh and v.rect.x == 0 and v.rect.w == self.W:
            self.screen.set_clip(pygame.Rect(0, 0, self.W, self.H))     # vista principal: el contenido se ve pasar bajo las barras translúcidas
        else:
            self.screen.set_clip(v.rect)
        return v

    def _fade_edge(self, v, top, bg):
        """Degradado en el borde superior/inferior de una lista con flechita: avisa de que hay más en esa dirección."""
        gh = self.n(70)
        key = ("_fe", v.rect.w, gh, bg, top)
        gs = getattr(self, "_fe_c", {}).get(key)
        if gs is None:
            gs = pygame.Surface((v.rect.w, gh), pygame.SRCALPHA)
            for yy in range(gh):
                t = (1 - yy / gh) if top else (yy / gh)
                pygame.draw.line(gs, (bg[0], bg[1], bg[2], int(240 * t ** 1.5)), (0, yy), (v.rect.w, yy))
            if not hasattr(self, "_fe_c"):
                self._fe_c = {}
            self._fe_c[key] = gs
        self.screen.blit(gs, (v.rect.x, v.rect.y if top else v.rect.bottom - gh))
        d = self.n(46)
        pr = pygame.Rect(0, 0, d, d)
        pr.center = (v.rect.right - self.n(50), v.rect.y + self.n(30) if top else v.rect.bottom - self.n(30))
        pygame.draw.ellipse(self.screen, PANEL2, pr)
        pygame.draw.ellipse(self.screen, LINE, pr, max(1, self.n(2)))
        self.chevron(pr.centerx, pr.centery + (-self.n(2) if top else self.n(2)), self.n(16), TXT, "up" if top else "down", 3)

    def end(self, bg=None, arrows=False):
        v = self.cur
        v.h = v.nh
        v.clamp()
        self.screen.set_clip(None)
        if arrows and v.h > v.rect.h:
            tr = v.rect.h * v.rect.h / v.h
            ty = v.rect.y + (v.rect.h - tr) * (v.off / (v.h - v.rect.h))
            self.rr((v.rect.right - self.n(8), ty, self.n(5), tr), LINE, 3)
            if v.off > self.n(10):
                self._fade_edge(v, True, bg or BG)
            if v.off < v.h - v.rect.h - self.n(10):
                self._fade_edge(v, False, bg or BG)
        elif v.h > v.rect.h:
            tr = v.rect.h * v.rect.h / v.h
            ty = v.rect.y + (v.rect.h - tr) * (v.off / (v.h - v.rect.h))
            self.rr((v.rect.right - self.n(8), ty, self.n(5), tr), LINE, 3)
            if v.off < v.h - v.rect.h - self.n(10):   # hay más contenido debajo: degradado + indicador
                gh = self.n(110)
                gs = getattr(self, "_fade", None)
                if gs is None or gs.get_size() != (v.rect.w, gh) or getattr(self, "_fade_bg", None) != BG:
                    self._fade_bg = BG
                    gs = self._fade = pygame.Surface((v.rect.w, gh), pygame.SRCALPHA)
                    for yy in range(gh):
                        pygame.draw.line(gs, (BG[0], BG[1], BG[2], int(235 * (yy / gh) ** 1.6)), (0, yy), (v.rect.w, yy))
                self.screen.blit(gs, (v.rect.x, v.rect.bottom - gh))
                ph = self.n(44)                         # v2.27: solo una flecha en la esquina; la píldora centrada tapaba texto
                pr = pygame.Rect(v.rect.right - ph - self.n(26), v.rect.bottom - ph - self.n(12), ph, ph)
                self.rr(pr, PANEL2, ph // 2)
                self.chevron(pr.centerx, pr.centery + self.n(1), self.n(11), DIM, "down", 2)
        self.cur = None

    def cy(self, y):
        """y relativa al contenido → y de pantalla."""
        return self.cur.rect.y + y - int(self.cur.off) if self.cur else y

    ex_t0 = -9.0
    _ex_seen = None

    def enter(self, i, key):
        """Entrada escalonada (desliza hacia arriba 0,28 s, cada tarjeta un poco después). Solo mueve las primeras 14 y solo al entrar en la pantalla."""
        if self._ex_seen != key:
            self._ex_seen, self.ex_t0 = key, self.t
        if self.power_saving() or self.reduced_motion():
            return 0                 # modo ahorro o movimiento reducido: sin animaciones de entrada
        p = max(0.0, min(1.0, (self.t - self.ex_t0 - min(i, 14) * 0.035) / 0.28))
        return int((1 - p) ** 2 * self.n(28)) if p < 1 else 0

    def thumb(self, e, rect, foc=False):
        """Carátula pequeña del juego (hilo + caché; nunca más de 3 cargas a la vez) o, mientras no hay, un bloque de color con el logo de su consola."""
        rect = pygame.Rect(rect)
        cov = self.cover(e, rect.size, small=True)
        if cov is not None:
            self.screen.blit(cov, rect)
            return
        pygame.draw.rect(self.screen, self.tint(e["name"], 0.30, 0.45), rect, border_radius=self.n(14))
        lg = platformart.logo(e.get("platform") or "", self.n(22), rect.w - self.n(20))
        if lg is not None:
            pl = pygame.Rect(0, 0, lg.get_width() + self.n(12), lg.get_height() + self.n(10))
            pl.center = rect.center
            self.rr(pl, (240, 243, 247), 8)
            self.screen.blit(lg, lg.get_rect(center=pl.center))
        else:
            self.text((e["name"][:1] or "?").upper(), rect.centerx, rect.centery, 34, (255, 255, 255), True, anchor="c")

    def offscreen(self, r):
        """True si el rectángulo (ya registrado) queda fuera de la vista actual: se registra para la navegación pero no se dibuja."""
        v = self.cur
        return bool(v) and (r.bottom < v.rect.y - self.n(30) or r.y > v.rect.bottom + self.n(30))

    def reg(self, key, rect, cb=None, focus=True, adj=None, x=None, y=None):
        r = pygame.Rect(rect)
        v = self.cur
        if v:
            v.nh = max(v.nh, r.bottom + self.n(24))
            if key == self.focus and self.reveal:
                m = self.n(20)
                want = None
                if r.top < self.n(300):
                    want = 0
                elif r.top - m < v.off:
                    want = max(0, r.top - m)
                elif r.bottom + m > v.off + v.rect.h:
                    want = r.bottom + m - v.rect.h
                if want is not None:
                    if abs(want - v.off) > v.rect.h * 1.5 or self.power_saving() or not self.smooth_scroll or self.reduced_motion():
                        v.off, v.target = want, None       # saltos largos (o modo ahorro): directo
                    else:
                        v.target = want
                self.reveal = False
            r = r.move(0, v.rect.y - int(v.off))
        self.new.append(Wd(key, r, cb, focus, adj, x, y, v))
        return r, (key == self.focus and self.show_focus)

    def button(self, key, rect, label, cb, kind="normal", size=22, focus=True, enabled=True, x=None, y=None, sub=None, pill=False, mark=False):
        r, foc = self.reg(key, rect, cb if enabled else None, focus, None, x, y)
        base = {"primary": ACC, "danger": (170, 52, 52), "ok": (38, 128, 78), "seg": SEG, "chipsel": TXT, "ghost": None}.get(kind, PANEL2)
        if not enabled:
            base = PANEL2 if kind != "ghost" else None
        hot = self.touch and self.touch.get("hot") == key and not self.touch["drag"]
        if base is None and hot:
            base = PANEL2
        elif hot:
            base = tuple(min(255, c + 22) for c in base)
        rad = r.h / self.k / 2 if pill else 16 * RADK
        if base is not None:
            if OUTLINE and kind in ("normal", "seg", "ghost") and base in (PANEL2, SEG, PANEL):
                self.rr(r, PANEL, rad)
                self.rr(r, ACC if kind == "seg" else LINE, rad, max(1, self.n(2)))
            else:
                self.rr(r, base, rad)
        if foc:
            self.glow(r, rad)
            self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, rad + 4 if pill else 20 * RADK, max(2, self.n(3)))
        col = BG if (kind == "chipsel" and enabled) else ((on_color(base) if kind in ("primary", "danger", "ok") else TXT) if enabled else DIM)
        if kind == "ghost" and enabled:
            col = DIM
        if sub:
            self.text(label, r.centerx, r.centery - self.n(size * 0.28), size, col, True, r.w - self.n(20), "c")
            self.text(sub, r.centerx, r.centery + self.n(size * 0.62), size - 6, DIM, False, r.w - self.n(20), "c")
        else:
            self.text(label, r.centerx - (self.n(12) if mark else 0), r.centery, size, col, True, r.w - self.n(20) - (self.n(34) if mark else 0), "c")
        if mark:
            self.check(r.right - self.n(26), r.centery, self.n(16), OK if kind != "chipsel" else BG)
        return r

    # ── entrada ──────────────────────────────────────────────
    def _init_controllers(self):
        try:
            if getattr(self, "no_pad", False):
                raise RuntimeError("HUB_NO_PAD")
            from pygame._sdl2 import controller as c
            c.init()
            self.sdlc = c
            for i in range(c.get_count()):
                self._open_ctrl(i)
        except Exception:  # noqa: BLE001
            self.sdlc = None
        names = ("A", "B", "X", "Y", "LEFTSHOULDER", "RIGHTSHOULDER", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "BACK")
        cb = {n: getattr(pygame, "CONTROLLER_BUTTON_" + n, None) for n in names}
        m = {cb["A"]: "A", cb["B"]: "B", cb["X"]: "X", cb["Y"]: "Y", cb["LEFTSHOULDER"]: "LB", cb["RIGHTSHOULDER"]: "RB",
             cb["BACK"]: "SEL", cb["DPAD_UP"]: "UP", cb["DPAD_DOWN"]: "DOWN", cb["DPAD_LEFT"]: "LEFT", cb["DPAD_RIGHT"]: "RIGHT"}
        m.pop(None, None)
        self.cbmap = m
        self.keymap = {pygame.K_RETURN: "A", pygame.K_KP_ENTER: "A", pygame.K_ESCAPE: "B", pygame.K_BACKSPACE: "B", pygame.K_x: "X",
                       pygame.K_y: "Y", pygame.K_q: "LB", pygame.K_w: "RB", pygame.K_PAGEUP: "LB", pygame.K_PAGEDOWN: "RB",
                       pygame.K_UP: "UP", pygame.K_DOWN: "DOWN", pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT", pygame.K_SPACE: "A"}

    def _open_ctrl(self, i):
        try:
            if self.sdlc.is_controller(i):
                self.ctrls[i] = self.sdlc.Controller(i)
        except Exception:  # noqa: BLE001
            pass

    def press(self, act, hold=False, now=None):
        now = now or time.time()
        self._io_gen += 1                              # v3.14: lo que se lea del disco para dibujar se relee tras cada pulsación
        if now - self.last_press.get(act, 0) < 0.08:
            return
        self.last_press[act] = now
        self.queue.append(act)
        if hold and act in DIRS:
            self.held[act] = [now, now]

    def pump(self):
        now = time.time()
        self.poll_appearance_request()
        while self._rcp_q:
            try:
                self._rcp_q.pop(0)()
            except Exception as ex:  # noqa: BLE001
                print(f"[receta] {ex}", file=sys.stderr, flush=True)
        t0 = self.__dict__.setdefault("_t_first_pump", now)
        q = self.__dict__.get("_uiq")
        while q:                                        # v3.17: lo que los hilos dejan para el hilo de la interfaz
            try:
                q.pop(0)()
            except Exception as ex:  # noqa: BLE001
                print(f"[interfaz] tarea pendiente falló: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
        if not self.__dict__.get("_chan_chk") and now - t0 > 1.5:
            self._chan_chk = True
            msg = chan.take_notice() if config.CHANNEL else None
            if msg:
                self.toast(msg)
        if config.CHANNEL == "dev" and not self.__dict__.get("_boot_ok") and now - t0 > chan.BOOT_OK_AFTER:
            self._boot_ok = True                    # v3.15: dev arrancó bien (red de seguridad: ver hub/channel.py)
            chan.boot_ok()
            print(f"[canal] arranque de dev confirmado ({chan.BOOT_OK_AFTER:.0f} s funcionando)", file=sys.stderr, flush=True)
        if not self.__dict__.get("_boot_chk") and now - t0 > 4:
            self._boot_chk = True
            try:
                if not self.cfg.get("launcher_checks", True) and lcheck.apply(self.cfg):
                    config.save_settings(self.cfg)
            except Exception as ex:  # noqa: BLE001
                print(f"[launcher] {ex}", file=sys.stderr, flush=True)
            try:      # v3.10: accesos de Steam sin la pantalla del launcher (o de vuelta a ella). v3.15: solo el canal activo
                n = directplay.apply_all(self.cfg.get("direct_play", True)) if chan.is_active() else 0
                if n:
                    print(f"[arranque directo] {n} acceso(s) de Steam ajustados ({'sin' if self.cfg.get('direct_play', True) else 'con'} pantalla del launcher)",
                          file=sys.stderr, flush=True)
            except Exception as ex:  # noqa: BLE001
                print(f"[arranque directo] {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            if self.cfg.get("check_on_start", False):
                print("[inicio] comprobando versiones nuevas de lo instalado (Ajustes › Comprobar al arrancar)", file=sys.stderr, flush=True)
                self.check_all()
        sw = getattr(self, "steam_wait", None)
        if sw and not self.exit_at:
            age = now - sw["t"]
            if now - sw["chk"] >= 0.25:
                sw["chk"] = now
                up = bool(sw["nd"]) and launchwatch.alive(sw["lid"], sw["nd"])
                if up:
                    print(f"[jugar] {sw['lid']}: el juego apareció a los {age:.1f}s con Hub abierto (Steam sí lo abre con Hub en marcha); Hub se cierra", file=sys.stderr, flush=True)
                    self.steam_wait, self.exit_at = None, now + self.STEAM_COVER
                    self.steam_cover = {"lid": sw["lid"], "nd": sw["nd"], "chk": now, "bad": 0, "t0": now, "w0": sw["t"]}
                elif age >= self.STEAM_WAIT_MAX:
                    print(f"[jugar] {sw['lid']}: no apareció en {age:.0f}s con Hub abierto; Hub se cierra y vuelvo a pedírselo a Steam", file=sys.stderr, flush=True)
                    steamlib.launch_later(sw["appid"], delay=2)
                    self.steam_wait, self.exit_at = None, now + 0.4
        sc = getattr(self, "steam_cover", None)
        if sc and self.exit_at:
            gn = self.gs_now
            if gn is not None and not sc.get("seen") and now - sc.get("t0", now) < self.STEAM_COVER_MAX:
                # v2.49: Hub sigue tapando hasta que otra ventana (la del launcher/juego) tenga el foco; solo entonces se cierra con un margen
                if gn[1] != self.STEAM_UI_APP and self.gs_base is not None and gn != self.gs_base:
                    sc["seen"] = now
                    self.exit_at = max(self.exit_at, now + self.STEAM_COVER_GRACE)
                else:
                    self.exit_at = max(self.exit_at, now + 0.6)
            if now - sc["chk"] >= 0.25:
                sc["chk"] = now
                sc["bad"] = 0 if launchwatch.alive(sc["lid"], sc["nd"]) else sc["bad"] + 1
                if sc["bad"] >= 3:       # v2.41: el proceso desapareció mientras Hub tapaba: no es que el juego abriera, se cerró
                    print(f"[jugar] {sc['lid']}: el juego se cerró nada más abrir; Hub NO se cierra (mira hub-run.sh / su registro)", file=sys.stderr, flush=True)
                    self.exit_at, self.steam_cover = None, None
                    self.toast("El juego se cerró nada más abrir. Ejecuta su hub-run.sh en un terminal para ver el motivo")
        elif sc:
            self.steam_cover = None
        if self.play_pr:
            rc, age = self.play_pr.poll(), now - self.play_t
            if rc is not None:
                self.game_pids = [q for q in self.game_pids if q != self.play_pr.pid]
                self.play_pr = None
                try:
                    md = launchlog.report(self.play_id, self.play_name or self.play_id, rc, age, getattr(self, "play_out", None))
                    msg = f"El juego terminó enseguida (código {rc}). Registro guardado: abre su ficha → «Ver registro del último arranque»"
                    print(f"[jugar] informe del arranque fallido: {md}", file=sys.stderr, flush=True)
                except OSError:
                    msg = f"El juego terminó enseguida (código {rc}). Mira ~/Games/launcher/state/{self.play_id}.log"
                print(f"[jugar] {self.play_id}: el lanzador terminó a los {age:.1f}s con código {rc}; Hub se queda abierto", file=sys.stderr, flush=True)
                self.toast(msg)
            elif age >= self.play_wait:
                self.play_pr = None
                print(f"[jugar] {self.play_id}: sigue vivo a los {age:.0f}s → se considera arrancado", file=sys.stderr, flush=True)
                history.record(self.play_id, "jugar", True, f"seguía vivo a los {age:.0f}s", snap=getattr(self, "_hist_snap", None))
                if self.libchk.get(self.play_id) and self.play_id not in (self.cfg.get("libs_ok") or []):
                    self.cfg["libs_ok"] = sorted(set(self.cfg.get("libs_ok") or []) | {self.play_id})   # arrancó: el aviso de ldd era falso
                    config.save_settings(self.cfg)
                if self.cfg.get("close_on_play", True) and not getattr(self, "play_win", False):
                    self.exit_at = now
                elif getattr(self, "play_win", False):
                    print("[jugar] versión de Windows (Proton): Hub se queda abierto hasta que la ventana del juego aparezca", file=sys.stderr, flush=True)
                    self.toast("Proton está abriendo el juego (la primera vez tarda). Hub sigue abierto; ciérralo tú cuando veas la ventana")
        if self.exit_at and now >= self.exit_at:
            self.exit_at = 0
            self.why = "JUGAR: el juego se lanzó y Hub se cierra para no taparlo"
            print("[jugar] cerrando Hub; el juego sigue en su propio proceso", file=sys.stderr, flush=True)
            self.running = False
        if self.want_front:
            self.want_front = False
            self.bring_to_front()
        if self.hb_repo:
            r, self.hb_repo = self.hb_repo, ""
            self.open_repo(r)
        if not self.win_focus and now - self.lost_at > 2.0 and pygame.key.get_focused():
            self.win_focus = True   # red de seguridad: SDL dice que hay foco pero no llegó FOCUSGAINED → no quedarse sordo
            print("[foco] SDL informa foco de nuevo: se reanuda la entrada del mando", file=sys.stderr, flush=True)
        modes = self.__dict__.setdefault("_mode_ts", collections.deque(maxlen=8))
        for qb, qts in self.pad_q:                     # v3.17: un MODE que ya está en la cola cuenta aunque venga detrás (ver abajo)
            if qb == "MODE" and qts not in modes:
                modes.append(qts)
        while self.pad_q:
            b, ts = self.pad_q[0]
            if b.startswith("~"):                      # soltado (evdev): deja de repetir
                self.pad_q.popleft()
                self.held.pop(b[1:], None)
                continue
            # v3.17: el botón del QAM (y otros atajos de Steam) llega como «guía + A»: Steam+A abre el QAM. En un mismo informe evdev los
            # códigos van en orden (BTN_SOUTH 0x130 antes que BTN_MODE 0x13C), así que la A se procesaba antes que la guía y pulsaba lo que
            # tuviera el foco (JUGAR → se abría el juego). Los botones esperan CHORD_WIN; si hay un MODE a menos de eso, se descartan.
            if b not in DIRS and b != "MODE" and now - ts < CHORD_WIN and not any(qb == "MODE" for qb, _ in self.pad_q):
                break                                  # aún puede llegar la guía: se decide en el siguiente fotograma
            self.pad_q.popleft()
            self.t_act = now                           # el mando por evdev también cuenta como actividad (Ajustes no baja a 20 fps mientras navegas)
            # Hub lee el mando directo de /dev/input (no pasa por Steam): si hay un menú de Steam/QAM encima, ese mando también
            # le llega a Hub. Se ignora mientras Hub no tiene el foco, justo después de recuperarlo y si el evento ya es viejo.
            if b == "MODE":   # botón Steam/guía: probablemente abre un menú encima
                self.mute_until = max(self.mute_until, now + 1.5)
                print("[foco] botón Steam/guía: entrada del mando en pausa 1,5 s", file=sys.stderr, flush=True)
                continue
            if b not in DIRS and any(abs(ts - m) <= CHORD_WIN for m in modes):
                print(f"[foco] {b} junto al botón Steam/guía (atajo de Steam, p. ej. el del QAM): ignorado", file=sys.stderr, flush=True)
                continue
            if not self.win_focus or self._gs_over() or now < self.mute_until or now - ts > 0.6:
                self.dropped += 1
                if self.dropped in (1, 20, 100):
                    print(f"[foco] mando ignorado ({b}) · ventana={'sí' if self.win_focus else 'NO'} · menú encima={'SÍ' if self._gs_over() else 'no'} · pausa={max(0, self.mute_until - now):.1f}s · total {self.dropped}", file=sys.stderr, flush=True)
                continue
            self.last_input = now
            self.press(b, hold=b in DIRS, now=now)
        for e in pygame.event.get():
            self.t_act = now
            if e.type not in _MOTION_EV:
                self._io_gen += 1                      # v3.14: arrastrar o mover el ratón no obliga a releer lo cacheado con memo()
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN, pygame.JOYBUTTONDOWN, pygame.CONTROLLERBUTTONDOWN):
                self.last_input = now
            if e.type == pygame.QUIT:
                self.why = "evento QUIT de SDL (ventana cerrada, Steam/Gamescope cerró el juego, o el sistema pidió salir)"
                print(f"[salida] {self.why} · inactivo {time.time() - self.last_input:.0f}s", file=sys.stderr, flush=True)
                self.running = False
            elif e.type in self._WEV:
                print(f"[ventana] {time.strftime('%H:%M:%S')} {pygame.event.event_name(e.type)} · foco SDL={'sí' if pygame.key.get_focused() else 'NO'}", file=sys.stderr, flush=True)
                if e.type in (getattr(pygame, "WINDOWFOCUSLOST", -1), getattr(pygame, "WINDOWHIDDEN", -1), getattr(pygame, "WINDOWMINIMIZED", -1)):
                    self.lost_at = now
                    self.win_focus = False
                    self.held.clear()
                    self.pad_q.clear()
                elif e.type == getattr(pygame, "WINDOWFOCUSGAINED", -1):
                    self.win_focus = True
                    self.mute_until = max(self.mute_until, now + 0.4)   # el botón que cerró el menú no debe llegar a Hub
                    self.pad_q.clear()
            elif e.type == pygame.TEXTINPUT:
                if self.modal and self.modal.get("kind") == "osk":
                    self._osk_log(self.modal, "TEXTINPUT", f"{len(e.text)} car.")
                if self.modal and self.modal.get("kind") == "osk" and e.text and e.text.isprintable():
                    if (e.text, ) == self._last_char[:1] and now - self._last_char[1] < 0.08:
                        continue   # ya contado por KEYDOWN
                    self.modal["text"] += e.text
            elif e.type == pygame.KEYDOWN:
                om = self.modal if (self.modal and self.modal.get("kind") == "osk") else None
                if om:   # diagnóstico: qué le llega a Hub mientras se escribe (NUNCA el carácter: puede ser una contraseña)
                    self._osk_log(om, "KEYDOWN", pygame.key.name(e.key) if not (e.unicode and e.unicode.isprintable() and e.key != pygame.K_SPACE) else "<carácter>")
                if self.modal and self.modal.get("kind") == "osk" and e.key == pygame.K_BACKSPACE:
                    self.modal["text"] = self.modal["text"][:-1]
                elif self.modal and self.modal.get("kind") == "osk" and self.modal.get("steam") and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._osk_ok(self.modal)
                elif self.modal and self.modal.get("kind") == "osk" and e.unicode and e.unicode.isprintable() and e.key not in (
                        pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.modal["text"] += e.unicode
                    self._last_char = (e.unicode, now)
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif om and om.get("steam"):
                    pass   # con el teclado de Steam abierto, ninguna otra tecla (flechas, tab, etc.) debe mover el foco de Hub
                elif e.key in self.keymap:
                    self.press(self.keymap[e.key], hold=True, now=now)
            elif e.type == pygame.KEYUP and e.key in self.keymap:
                self.held.pop(self.keymap[e.key], None)
            elif self.sdlc and e.type == pygame.CONTROLLERDEVICEADDED:
                self._open_ctrl(e.device_index)
            elif self.sdlc and e.type == pygame.CONTROLLERBUTTONDOWN and e.button in self.cbmap:
                self.press(self.cbmap[e.button], hold=True, now=now)
            elif self.sdlc and e.type == pygame.CONTROLLERBUTTONUP and e.button in self.cbmap:
                self.held.pop(self.cbmap[e.button], None)
            elif self.sdlc and e.type == pygame.CONTROLLERAXISMOTION and e.axis in (pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY):
                if not self.cfg.get("stick_nav", True):
                    continue
                val = e.value / 32768.0
                names = ("LEFT", "RIGHT") if e.axis == pygame.CONTROLLER_AXIS_LEFTX else ("UP", "DOWN")
                for a, sign in ((names[0], -1), (names[1], 1)):
                    v = val * sign
                    st = self.stick.get(a)
                    if v > 0.75 and not st:   # empujar de verdad (histéresis: se suelta por debajo de 0.45)
                        self.stick[a] = {"t": now, "v": v, "blocked": False}
                        self.press(a, hold=True, now=now)
                        print(f"[mando] stick {a} v={v:.2f}", file=sys.stderr, flush=True)
                    elif st and v < 0.45:
                        self.stick.pop(a, None)
                        self.held.pop(a, None)
                    elif st and abs(v - st["v"]) > 0.03:
                        st["v"], st["t"] = v, now
            elif e.type == pygame.MOUSEWHEEL:
                v = self._view_at(pygame.mouse.get_pos()) or self._main_view()
                if v:
                    v.off -= e.y * self.n(90)
                    v.vel, v.target = 0, None
                    v.clamp()                          # v3.10: sin esto, la rueda en una página corta la dejaba desplazada un fotograma
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.show_focus = False
                v = self._view_at(e.pos)
                w = self._widget_at(e.pos)
                if v:
                    v.vel = 0
                self.touch = {"pos": e.pos, "last": e.pos, "view": v, "drag": False, "t": now, "hot": w.key if w else None, "samples": [],
                              "modal": id(self.modal) if self.modal else None, "finger": bool(getattr(e, "touch", False))}
            elif e.type == pygame.MOUSEMOTION and self.touch and e.buttons[0]:
                t = self.touch
                dy = e.pos[1] - t["last"][1]
                if not t["drag"] and (abs(e.pos[1] - t["pos"][1]) > self.n(14) or abs(e.pos[0] - t["pos"][0]) > self.n(14)):
                    t["drag"] = True
                if t["drag"] and t["view"]:
                    t["view"].off -= dy
                    t["view"].clamp()
                    t["samples"] = (t["samples"] + [(now, dy)])[-6:]
                t["last"] = e.pos
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.touch:
                t, self.touch = self.touch, None
                if not t["drag"] and not t.get("lp"):
                    w = self._widget_at(e.pos)
                    # v3.10: solo se pulsa lo que estaba bajo el dedo al tocar. Si mientras tanto se abrió un menú (p. ej. al terminar una
                    # descarga) o la pantalla cambió, soltar no debe pulsar el botón nuevo que haya quedado debajo («toque fantasma»)
                    if w and (w.key != t.get("hot") or (id(self.modal) if self.modal else None) != t.get("modal")):
                        w = None
                    if w and w.cb:
                        dur = now - t["t"]
                        kind = "dedo" if t.get("finger") else "ratón"
                        # v3.18: el botón del QAM llegaba como un clic en la pantalla y pulsaba lo que hubiera debajo (JUGAR → juego).
                        # Un clic con un menú de Steam encima, justo tras el botón guía o sin foco no se cuenta; uno «instantáneo» de ratón
                        # (pulsar y soltar en menos de 30 ms, como los sintéticos) espera 0,25 s en el Modo Juego por si se abre un menú encima.
                        if not self.win_focus or self._gs_over() or now < self.mute_until:
                            print(f"[toque] {kind} sobre «{w.key}» ignorado: menú de Steam encima / sin foco / tras el botón guía", file=sys.stderr, flush=True)
                        elif not t.get("finger") and dur < 0.03 and self.in_game_mode():
                            self.__dict__.setdefault("_tap_wait", []).append((now, w.key, t.get("modal")))
                            print(f"[toque] clic instantáneo ({dur * 1000:.0f} ms) sobre «{w.key}»: espera 0,25 s por si es un atajo de Steam", file=sys.stderr, flush=True)
                        else:
                            self.focus = w.key
                            self.fire(w)
                            self.sfx.play("confirm")
                elif t["view"] and t["samples"]:
                    ts = t["samples"]
                    dt = max(0.016, ts[-1][0] - ts[0][0])
                    if now - ts[-1][0] < 0.1:
                        t["view"].vel = -sum(d for _, d in ts) / dt
        self._check_long_press(now)
        tw = self.__dict__.get("_tap_wait")
        while tw and now - tw[0][0] >= TAP_WAIT:        # v3.18: clics instantáneos en espera (ver arriba)
            t_up, key, mid = tw.pop(0)
            lost = (not self.win_focus or self._gs_over() or self.lost_at > t_up or self.mute_until > t_up
                    or (id(self.modal) if self.modal else None) != mid)
            w = next((x for x in self.widgets if x.key == key), None)
            if lost or not w or not w.cb:
                print(f"[toque] clic instantáneo sobre «{key}» descartado ({'se abrió un menú o cambió el foco' if lost else 'ya no está'})",
                      file=sys.stderr, flush=True)
                continue
            self.focus = w.key
            self.fire(w)
            self.sfx.play("confirm")
        for a, (t0, tl) in list(self.held.items()):
            if now - t0 > 6.0:                         # red de seguridad: nadie mantiene la cruceta 6 s; si se perdió el «soltar», no repetir para siempre
                self.held.pop(a, None)
                print(f"[mando] {a} llevaba 6 s «pulsado» sin soltarse: se suelta", file=sys.stderr, flush=True)
                continue
            if now - t0 > 0.4 and now - tl > 0.11:
                self.held[a][1] = now
                self.queue.append(a)
        while self.queue:
            self.act(self.queue.popleft())

    def _safe_reset(self):
        """v3.10: si una pantalla falla 5 fotogramas seguidos, se vuelve a Inicio sin menús en vez de repetir el error hasta cerrar Hub."""
        print("[error] la pantalla actual falla una y otra vez: vuelvo a Inicio (el error queda arriba en hub.log)", file=sys.stderr, flush=True)
        try:
            self.modal = self.detail = self.rview = None
            self.touch = None
            self.held.clear()
            self.tab = "home"
            self.focus, self.reveal = None, True
            self.toast("Algo falló al dibujar esa pantalla; he vuelto a Inicio (detalles en hub.log)")
        except Exception:  # noqa: BLE001
            pass

    def _view_at(self, pos):
        for v in reversed(self.active_views):      # la última en dibujarse (p. ej. la lista de un modal) está encima
            if v.h and v.rect.collidepoint(pos):
                return v

    def _main_view(self):
        return next(iter(reversed([v for v in self.active_views])), None) if self.active_views else None

    def _widget_at(self, pos):
        for w in reversed(self.widgets):
            if w.rect.collidepoint(pos) and (not w.view or w.view.rect.collidepoint(pos)) and (w.cb or w.focus):
                return w
        return None

    def nav(self, d):
        cur = next((w for w in self.widgets if w.key == self.focus), None)
        cands = [w for w in self.widgets if w.focus and w.cb is not None and w is not cur]
        if not cur:
            if cands:
                self.focus = min(cands, key=lambda w: (w.rect.y, w.rect.x)).key
                self.reveal = True
            return
        cx, cy = cur.rect.center
        vert = d in ("UP", "DOWN")
        c6 = self.n(6)
        ahead = []
        for w in cands:
            dx, dy = w.rect.centerx - cx, w.rect.centery - cy
            if d == "UP" and dy > -c6 or d == "DOWN" and dy < c6 or d == "LEFT" and dx > -c6 or d == "RIGHT" and dx < c6:
                continue
            ahead.append((abs(dy) if vert else abs(dx), abs(dx) if vert else abs(dy), w))
        if vert:
            # arriba/abajo: lo que está AL LADO (comparte la mitad de la altura, p. ej. la barra lateral junto al héroe) no está «encima»
            def lado(w):
                ov = min(w.rect.bottom, cur.rect.bottom) - max(w.rect.top, cur.rect.top)
                return ov > 0.5 * min(w.rect.h, cur.rect.h)
            limpio = [t for t in ahead if not lado(t[2])]
            if limpio:
                ahead = limpio
            # las pestañas (barra lateral o superior) y el contenido son dos «columnas»: arriba/abajo no salta de una a otra si hay algo en la suya
            mia = str(cur.key).startswith("tab:")
            col = [t for t in ahead if str(t[2].key).startswith("tab:") == mia]
            if col:
                ahead = col
        best = None
        if ahead:
            # primero la fila (o columna) más cercana en esa dirección y, dentro de ella, la más alineada: la cruceta recorre la ficha
            # por filas en vez de saltarse botones que quedan a un lado (el «Jugar» de la derecha, el «Instalar»…).
            if not vert:       # izquierda/derecha: primero lo que está en la MISMA fila (si no, una pestaña o botón suelto de otra fila «gana» a la tarjeta de al lado)
                same = [(p, w) for p, sec, w in ahead if sec <= max(cur.rect.h * 0.6, self.n(28))]
                if same:
                    self.focus, self.reveal = min(same, key=lambda t: t[0])[1].key, True
                    return
            near = min(p for p, _, _ in ahead)
            tol = max(self.n(28), (cur.rect.h if vert else cur.rect.w) * 0.4)      # holgura: las tarjetas que entran animadas no están a la misma altura
            band = [(sec, w) for p, sec, w in ahead if p <= near + tol]
            best = min(band, key=lambda t: t[0])[1]
        if best:
            self.focus, self.reveal = best.key, True

    def act(self, a):
        """Ejecuta la acción y pone el sonido que le toca (mover, aceptar, volver, cambiar de sección, abrir un menú)."""
        w0 = next((w for w in self.widgets if w.key == self.focus), None)
        before = (self.focus, self.tab, self.modal is not None, self.detail is not None, self.explore, self.rview is not None)
        self._act(a)
        after = (self.focus, self.tab, self.modal is not None, self.detail is not None, self.explore, self.rview is not None)
        if a in DIRS:
            if after[0] != before[0]:
                self.sfx.play("move")
        elif a == "A":
            if w0 is not None and w0.cb is not None:
                self.sfx.play("open" if after[2] and not before[2] else "confirm")
        elif a == "B":
            if after[1:] != before[1:]:
                self.sfx.play("back")
        elif a in ("LB", "RB"):
            if after[1] != before[1]:
                self.sfx.play("tab")

    def _act(self, a):
        self.show_focus = True
        w = next((w for w in self.widgets if w.key == self.focus), None)
        if self.tab == "art" and self.art and self.art.get("pv") is not None and not self.modal:
            if a in ("LEFT", "RIGHT"):
                return self.art_pv_move(-1 if a == "LEFT" else 1)
            if a == "B":
                self.art["pv"], self.focus, self.reveal = None, None, True
                return
        if a in DIRS:
            if a in ("LEFT", "RIGHT") and w and w.adj:
                w.adj(-1 if a == "LEFT" else 1)
            else:
                self.nav(a)
            return
        if self.modal:
            return self.modal_act(a, w)
        if a == "A":
            if w and w.cb:
                self.fire(w)
        elif a == "B":
            if self.rview:
                self.rview, self.focus = None, None
            elif self.detail and self.detail in self.more_open:
                self.more_open.discard(self.detail)          # v2.74: B cierra primero los ajustes del juego
                self.focus = None
            elif self.detail:
                self.detail = None
                self.focus = None
            elif self.tab == "settings" and getattr(self, "set_page", None):
                self.settings_back()
            elif self.tab == "games" and self.explore == "list":
                self.explore, self.focus, self.reveal = "cats", None, True
            elif self.tab == "art":
                if self.art and self.art.get("step") == "kind":
                    self.art["step"], self.focus, self.reveal = "game", None, True
                else:
                    self.go_tab("steam")
            elif self.tab == "steam":
                self.go_tab("home")
            elif self.tab in SUBTAB:
                self.go_tab("games")
            elif self.tab != "home":
                self.go_tab("home")
        elif a == "X":
            (w.x if w and w.x else self.screen_x)()
        elif a == "Y":
            (w.y if w and w.y else self.screen_y)()
        elif a in ("LB", "RB") and self.tab == "art" and self.art and self.art.get("step") == "kind":
            ks = list(sgdb.KINDS)
            self.art["pv"] = None
            self.art_kind(ks[(ks.index(self.art["kind"]) + (1 if a == "RB" else -1)) % len(ks)])
        elif a in ("LB", "RB") and not self.detail and not self.rview:
            keys = [t for t, _ in TABS]
            i = keys.index(SUBTAB.get(self.tab, self.tab)) + (1 if a == "RB" else -1)
            self.go_tab(keys[i % len(keys)])

    def go_tab(self, t):
        if t == "games" and self.tab != "games" and self.tab not in SUBTAB:
            self.explore = "cats"
        if t == "settings" and self.tab != "settings":
            self.set_page = None
        self.tab, self.detail, self.rview, self.focus = t, None, None, None
        self.reveal = True
        if t == "library" and not self.lib_loaded and not self.lib_busy:
            self.lib_load()
        if t == "downloads":
            self.recv_scan()

    def update(self, dt):
        now = time.time()
        for a, st in list(self.stick.items()):   # un stick "empujado" que no varía nada durante 3 s = deriva: se ignora hasta que vuelva al centro
            if not st["blocked"] and now - st["t"] > 3.0:
                st["blocked"] = True
                self.held.pop(a, None)
                print(f"[mando] deriva del stick ({a}, v={st['v']:.2f}) ignorada; usa la cruceta o baja la sensibilidad en AJUSTES", file=sys.stderr, flush=True)
        for v in self.views.values():
            if v.target is not None:
                if self.touch and self.touch.get("drag"):
                    v.target = None
                else:
                    d = v.target - v.off
                    if abs(d) < 1.0:
                        v.off, v.target = v.target, None
                    else:
                        v.off += d * min(1.0, dt * 24)
                    continue
            if abs(v.vel) > 8 and not (self.touch and self.touch["view"] is v and self.touch["drag"]):
                v.off += v.vel * dt
                v.vel *= 0.93 ** (dt * 60)
                v.clamp()
            else:
                v.vel = 0 if not (self.touch and self.touch["drag"]) else v.vel

    # ═══ acciones de negocio ═════════════════════════════════
    def entry(self, eid):
        return next((e for e in self.entries if e["id"] == eid), None)

    def reload(self):
        self.entries = catalog.load()
        self._inst_gen = getattr(self, "_inst_gen", 0) + 1   # un refresco en vuelo con el catálogo viejo descarta su resultado
        self._inst_c = None

    def _inst_build(self, entries):
        """Calcula la información de instalación de todas las tarjetas (índices en O(1)); se usa en segundo plano al caducar la caché."""
        lg = install.launcher_games()
        ix = install.build_index(lg, entries)
        d = {"_lg": lg, "_ix": ix}
        for e in entries:
            d[e["id"]] = install.installed_info(e, lg, entries, ix)
        return d

    def _inst_refresh(self):
        """La caché caduca a los 10 s, pero se renueva en un hilo y se cambia de golpe: antes se vaciaba y recalculaba todo dentro de UN fotograma (tirón de 50-250 ms)."""
        if getattr(self, "_inst_busy", False):
            return
        self._inst_busy, ents, gen = True, list(self.entries), getattr(self, "_inst_gen", 0)

        def job():
            try:
                t0 = time.perf_counter()
                d = self._inst_build(ents)
                if gen == getattr(self, "_inst_gen", 0):
                    self._inst_c = (time.time(), d)
                ms = 1000 * (time.perf_counter() - t0)
                if self.perf.on and ms >= 40:
                    print(f"[rendimiento] caché de instalados renovada en segundo plano: {ms:.0f} ms ({len(ents)} tarjetas)", file=sys.stderr, flush=True)
            except Exception as ex:  # noqa: BLE001
                print(f"[instalado] no pude renovar la caché: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            finally:
                self._inst_busy = False
        threading.Thread(target=job, daemon=True).start()

    def inst(self, e):
        c = getattr(self, "_inst_c", None)
        if c is None:
            c = self._inst_c = (time.time(), {})
        elif time.time() - c[0] > 10:
            self._inst_refresh()          # sigue sirviendo lo anterior mientras se recalcula
        if "_lg" not in c[1]:
            t0 = time.perf_counter()
            c[1]["_lg"] = install.launcher_games()
            c[1]["_ix"] = install.build_index(c[1]["_lg"], self.entries)
            if self.perf.on:
                self.perf.note("launcher_games", 1000 * (time.perf_counter() - t0))
        if e["id"] not in c[1]:
            t0 = time.perf_counter()
            c[1][e["id"]] = install.installed_info(e, c[1]["_lg"], self.entries, c[1].get("_ix"))
            if self.perf.on:
                self.perf.note("installed_info", 1000 * (time.perf_counter() - t0))
        return c[1][e["id"]]

    @staticmethod
    def rk(e):
        return e["repo"] + "|" + (e.get("asset_filter") or "")

    def fetch(self, e, force=False):
        if not e.get("repo") or self.rk(e) in self.loading:
            return
        self.loading.add(self.rk(e))

        def job():
            try:
                self.rel[self.rk(e)], self.rel_sum[self.rk(e)] = github.latest_and_summary(e["repo"], self.cfg.get("arch", "x86_64"), force=force, filt=e.get("asset_filter", ""))
                self.rel_t[self.rk(e)] = time.time()
                if force:
                    self.rel_sel.pop(self.rk(e), None)
            finally:
                self.loading.discard(self.rk(e))
        threading.Thread(target=job, daemon=True).start()

    def check_all(self):
        """Busca versiones nuevas SOLO de lo instalado (antes eran las ~1100 fichas del catálogo = 1100 llamadas) y una vez por repositorio.
        Con If-None-Match (ETag) la respuesta 304 no gasta cuota; si GitHub dice que hay límite se para en seco."""
        self.toast("Comprobando actualizaciones…")

        def job():
            seen, n, stop = set(), 0, ""
            for e in list(self.entries):
                if not (e.get("repo") and self.running) or self.rk(e) in seen or not self.inst(e)["installed"]:
                    continue
                seen.add(self.rk(e))
                if ghstats.blocked():
                    stop = f"límite de GitHub ({ghstats.S['blocked_why']}): reintenta en {ghstats.blocked() // 60 + 1} min"
                    break
                try:
                    self.rel[self.rk(e)] = github.latest(e["repo"], self.cfg.get("arch", "x86_64"), force=True, filt=e.get("asset_filter", ""))
                    n += 1
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(0.25)
            print(f"[gh] comprobación: {n} repos instalados · {ghstats.summary()}", file=sys.stderr, flush=True)
            self.toast(stop or f"Comprobación terminada: {n} repos instalados · {ghstats.S['notmod']} sin cambios")
        threading.Thread(target=job, daemon=True).start()

    def open_detail(self, e):
        """v2.64: primero lo guardado en disco (0 llamadas). Se consulta GitHub solo si no hay nada guardado, o si hay datos y «consultar al abrir» está en SÍ
        (con la caché de 6 h y el ETag eso casi nunca gasta cuota)."""
        self.detail, self.focus = e["id"], None
        self.views.setdefault("detail", View()).off = 0
        k = self.rk(e)
        if k in self.rel or not e.get("repo"):
            return
        hit = github.from_cache(e["repo"], self.cfg.get("arch", "x86_64"), e.get("asset_filter", ""))
        if hit:
            self.rel[k], self.rel_sum[k], self.rel_t[k] = hit
        if not hit or self.cfg.get("fetch_on_open", True):
            self.fetch(e)

    def open_page(self, e):
        if e.get("repo"):
            self.open_url(f"https://github.com/{e['repo']}")

    def play(self, e):
        exe = config.LAUNCHER / "bin" / "play"
        if not exe.exists():
            self.toast("No encuentro el launcher unificado (~/Games/launcher)")
            return
        if self.exit_at or self.play_pr or getattr(self, "steam_wait", None):
            return
        lid = self.inst(e)["launcher_id"]
        blk = self.own_block(e, lid)
        if blk:
            print(f"[jugar] «{lid}»: {blk}", file=sys.stderr, flush=True)
            self.toast(blk)
            return
        self.play_win = False
        try:
            if self.os_state(lid).get("active") == "windows":
                self.play_win = True       # Proton tarda (la 1.ª vez crea el prefijo y descarga DLSS): Hub no se cierra a los 6 s
                self.link_game_win(e)
            else:
                self.link_game_linux(e)
        except (OSError, ValueError, KeyError):
            pass
        if self._exe_missing(e, lid):
            return
        chk = launchlog.libs_check(lid)
        miss = chk["miss"]
        self.libchk[lid] = miss
        ok_siempre = lid in (self.cfg.get("libs_ok") or [])
        if miss and lid not in self.libs_ok and not ok_siempre:
            def igual():
                self.libs_ok.add(lid)
                self.cfg["libs_ok"] = sorted(set(self.cfg.get("libs_ok") or []) | {lid})   # no volver a preguntar por este juego
                config.save_settings(self.cfg)
                self.modal = None
                self.play(e)
            libs = ", ".join(miss[:6]) + (" …" if len(miss) > 6 else "")
            if chk["container"]:
                msg = (f"Se compiló dentro del distrobox «{chk['container']}» y el launcher lo abre en el sistema, donde no encuentro: {libs}.\n"
                       "Si ya te arrancaba, pulsa LANZAR: Hub no volverá a preguntar por este juego.")
            else:
                msg = (f"El juego pide: {libs}\nAsí probablemente no arrancará: el port se compiló contra bibliotecas que tu sistema no tiene "
                       "(no es un fallo de Hub). Si aun así te funciona, pulsa LANZAR y Hub no volverá a preguntar.")
            self.modal = {"kind": "choice", "title": "Faltan bibliotecas del sistema", "prev": None, "msg": msg,
                          "options": [("LANZAR DE TODOS MODOS", igual), ("CANCELAR", lambda: setattr(self, "modal", None))]}
            self.focus = None
            return
        sc = self.steam_shortcut(lid, e["name"]) if self.via_steam_ok() else None
        if not sc and self.via_steam_ok() and not e.get("_force_direct") and not e.get("_no_qam"):
            # v3.17: sin atajo en Steam → QAM Rail lo crea en caliente (con su arte) y lo lanza: el juego sale en la barra lateral, con su
            # perfil de TDP y su tiempo de juego. Si QAM Rail no está o falla, se sigue como antes (abajo).
            self.play_via_qam(e, lid)
            return
        if not sc and self.in_game_mode() and not os.environ.get("SteamGameId") and not e.get("_force_direct"):
            # v3.16: Hub abierto desde el QAM (no es un juego de Steam) y el juego no tiene atajo: lanzado a pelo, gamescope no lo mostraría
            def igual(e=e):
                self.modal = None
                self.play(dict(e, _force_direct=True))
            self.modal = {"kind": "choice", "title": "Este juego no tiene atajo en Steam", "prev": None,
                          "msg": f"En el Modo Juego, «{e['name']}» se abriría sin verse (gamescope solo muestra lo que lanza Steam). Crea su atajo con "
                                 "«Añadir a Steam» en su ficha, o abre Forgeinator desde Steam.",
                          "options": [("LANZAR DE TODOS MODOS", igual), ("CANCELAR", lambda: setattr(self, "modal", None))]}
            self.focus = None
            print(f"[jugar] «{lid}»: sin atajo de Steam en el Modo Juego y Hub no es un juego de Steam: pregunto antes de lanzarlo a pelo",
                  file=sys.stderr, flush=True)
            return
        if sc:
            try:        # v3.10: el acceso de este juego, sin la pantalla del launcher (por si se regeneró con «play --shortcuts»). v3.15: canal activo
                if chan.is_active():
                    directplay.set_shortcut(lid, self.cfg.get("direct_play", True))
            except OSError as ex:
                print(f"[arranque directo] {lid}: {ex}", file=sys.stderr, flush=True)
            splash = self.cfg.get("steam_splash", True)
            ok, how = steamlib.launch_later(sc["appid"], delay=1 if splash else 2)
            print(f"[jugar] «{lid}» vía su acceso de Steam «{sc['name']}» (appid {sc['appid']}): {'ok' if ok else 'falló'} · {how}", file=sys.stderr, flush=True)
            if ok:
                history.record(lid, "jugar", None, "lanzado vía Steam", version=self.inst(e).get("version", ""))
                wl = steamlib.watch_launch(lid, e["name"])       # si no abre o se cierra enseguida, queda un informe (antes: nada)
                print(f"[jugar] vigía del arranque: {wl or 'no se pudo dejar'}", file=sys.stderr, flush=True)
                self.cfg["last_played"] = {"id": e["id"], "t": time.time()}
                config.save_settings(self.cfg)
                if splash:
                    # v2.39: Hub se queda con su pantalla de carga hasta que el juego aparezca (o 5 s). Si Steam no lo abre mientras Hub sigue en marcha
                    # (hipótesis de v1.96), se cierra Hub y se vuelve a pedir: queda en el registro qué pasó.
                    self.play_eid, self.play_id, self.play_name = e["id"], lid, e["name"]
                    self.steam_wait = {"t": time.time(), "appid": sc["appid"], "lid": lid, "nd": launchwatch.needles(lid), "chk": 0.0}
                    return
                self.toast(f"Abriendo «{sc['name']}» con su acceso de Steam… Hub se cierra")
                self.exit_at = time.time() + 0.4    # Steam solo abre el juego cuando Hub (otra app) ya no está en marcha
                return
        try:
            self.play_out = launchlog.new_out(lid)
            fo = open(self.play_out, "wb")           # salida del lanzador y del juego: si no abre, ahí está el porqué
            cmd = directplay.command(lid) if self.cfg.get("direct_play", True) else [str(exe), lid]     # v3.10: sin la pantalla del launcher
            print(f"[jugar] «{lid}»: {'arranque directo' if len(cmd) > 2 else 'con la pantalla del launcher'}", file=sys.stderr, flush=True)
            pr = subprocess.Popen(cmd, stdout=fo, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            fo.close()
        except OSError as ex:
            self.toast(f"No se pudo lanzar: {ex}")
            return
        self.game_pids.append(pr.pid)
        self._hist_snap = history.snapshot(lid, self.inst(e).get("version", ""))
        history.record(lid, "jugar", None, "lanzado", snap=self._hist_snap)
        self.cfg["last_played"] = {"id": e["id"], "t": time.time()}
        config.save_settings(self.cfg)
        self.brow_t = 0   # un juego en marcha: Hub nunca debe volver a ponerse delante
        self.play_pr, self.play_t, self.play_id, self.play_name = pr, time.time(), lid, e["name"]
        self.play_eid = e["id"]
        print(f"[jugar] lanzado «{lid}» (pid {pr.pid}) · cerrar Hub: {self.cfg.get('close_on_play', True)} (espera {self.play_wait:.0f}s a ver si arranca)", file=sys.stderr, flush=True)
        self.toast("Abriendo el juego…" + (" Hub se cierra cuando arranque" if self.cfg.get("close_on_play", True) else ""))

    def play_via_qam(self, e, lid):
        """v3.17: pide a QAM Rail (socket local) que cree el atajo de Steam del juego si falta, con el arte del Hub, y lo lance."""
        if getattr(self, "_qam_busy", False):
            return
        self._qam_busy = True
        self.toast(f"Preparando «{e['name']}» en Steam…")
        try:
            exe = directplay.ensure_script(lid, self.cfg.get("direct_play", True))
        except OSError as ex:
            self._qam_busy = False
            print(f"[jugar] «{lid}»: no pude escribir su script de atajo: {ex}", file=sys.stderr, flush=True)
            self.play(dict(e, _no_qam=True))
            return
        art = {k: f for k, f in self.art_files(e).items() if k in qamlink.ART_KEYS}
        as_game = bool(os.environ.get("SteamGameId"))       # Hub es un juego de Steam: el otro solo abre cuando Hub se cierra
        game = qamlink.game_request(lid, e["name"], str(exe), art=art, appid=qamlink.known_appids(config.DATA).get(lid),
                                    run_delay_ms=1500 if as_game else 0)
        ver = self.inst(e).get("version", "")

        def job():
            r = qamlink.ping()
            if r.get("ok"):
                r = qamlink.run_shortcut(game)
            self.__dict__.setdefault("_uiq", []).append(lambda: self._qam_done(e, lid, r, ver))
        threading.Thread(target=job, daemon=True).start()

    def _qam_done(self, e, lid, r, ver):
        self._qam_busy = False
        if not r.get("ok"):
            print(f"[jugar] «{lid}»: QAM Rail no pudo lanzarlo por Steam ({r.get('error')}: {r.get('detail', '')})", file=sys.stderr, flush=True)
            self.play(dict(e, _no_qam=True))           # lo de antes: atajo existente, o preguntar antes de lanzarlo a pelo
            return
        appid = r["appid"]
        qamlink.remember_appid(config.DATA, lid, appid)
        self._sc_t = 0                                  # que la próxima búsqueda de atajos vea el nuevo
        print(f"[jugar] «{lid}» vía QAM Rail: atajo {'creado' if r.get('created') else 'existente'} (appid {appid}), lanzado por Steam",
              file=sys.stderr, flush=True)
        history.record(lid, "jugar", None, "lanzado vía Steam (QAM Rail)", version=ver)
        self.cfg["last_played"] = {"id": e["id"], "t": time.time()}
        config.save_settings(self.cfg)
        close = self.cfg.get("close_on_play", True) or bool(os.environ.get("SteamGameId"))
        self.toast(f"Abriendo «{e['name']}» por Steam" + ("… Hub se cierra" if close else ""))
        if close:
            self.exit_at = time.time() + (0.3 if os.environ.get("SteamGameId") else 0.8)

    def libs_for(self, lid):
        """Bibliotecas que faltan (ldd en un hilo, una vez por juego y sesión; se repite si cambia el binario al lanzar).
        Vacío si ya arrancó bien con ellas «faltando» o le dijiste LANZAR DE TODOS MODOS (falso aviso: p. ej. compilado en distrobox)."""
        if lid in (self.cfg.get("libs_ok") or []):
            return []
        if lid not in self.libchk:
            self.libchk[lid] = []

            def job():
                self.libchk[lid] = launchlog.libs_check(lid)["miss"]
            threading.Thread(target=job, daemon=True).start()
        return self.libchk.get(lid) or []

    def _cwd_migrate(self):
        """Hasta v1.95, al reconocer tu archivo Hub cambiaba [run] cwd a tu carpeta de ROMs (para que el selector del juego empezara allí).
        Los juegos que guardan su configuración en la carpeta de trabajo (Silent Hill: config.cfg) la escribían entonces en la de ROMs
        y «olvidaban» los ajustes. Una vez: se restaura el cwd original y se deja el enlace a tu ROM dentro de la carpeta del juego."""
        if self.cfg.get("cwd_fix_v196"):
            return
        fixed = []
        try:
            tomls = sorted((config.LAUNCHER / "games").glob("*.toml"))
        except OSError:
            tomls = []
        for f in tomls:
            try:
                if gamecfg.state(f.stem)["libcwd"]:
                    gamecfg.set_libcwd(f.stem, "", False)
                    fixed.append(f.stem)
            except (OSError, ValueError):
                continue
        for e in list(self.entries):
            lk = library.link_get(e["id"])
            if not lk:
                continue
            try:
                inf = install.installed_info(e, None, self.entries)
                if inf["installed"]:
                    library.place_default(e, lk, inf["dir"])
            except (OSError, ValueError):
                continue
        self.cfg["auto_libcwd"] = False
        self.cfg["cwd_fix_v196"] = True
        config.save_settings(self.cfg)
        if fixed:
            print(f"[carpeta de trabajo] restaurada en: {', '.join(fixed)}", file=sys.stderr, flush=True)
            self.toast("Carpeta de trabajo = carpeta del juego otra vez en: " + ", ".join(fixed[:3]) + (" …" if len(fixed) > 3 else "") +
                       " (su configuración ya no irá a tu carpeta de ROMs)")

    def via_steam_ok(self) -> bool:
        """Lanzar por el atajo de Steam del juego: si Hub corre como juego de Steam o, v3.16, si estamos en el Modo Juego aunque a Hub lo
        abriera otro (el QAM): gamescope solo muestra ventanas que vienen de Steam, y un juego lanzado a pelo quedaba invisible."""
        return bool(self.cfg.get("play_via_steam", True) and (os.environ.get("SteamGameId") or self.in_game_mode()))

    def in_game_mode(self) -> bool:
        """v3.16: ¿sesión de gamescope (Modo Juego)? Variables de gamescope o un proceso gamescope en marcha (se mira una vez)."""
        v = self.__dict__.get("_gm")
        if v is None:
            v = bool(os.environ.get("GAMESCOPE_WAYLAND_DISPLAY") or os.environ.get("SteamGameId")
                     or (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower() == "gamescope" or _gamescope_running())
            self._gm = v
        return v

    def steam_shortcut(self, lid, name=""):
        now = time.time()
        if now - getattr(self, "_sc_t", 0) > 30:
            try:
                self._sc_items = steamlib.shortcuts()
            except Exception:  # noqa: BLE001
                self._sc_items = []
            self._sc_t = now
        return steamlib.find(lid, name, self._sc_items)

    def toggle_direct_play(self):
        """v3.10: abrir los juegos sin la pantalla previa del launcher (Hub ya se encarga de actualizar)."""
        on = self.cfg["direct_play"] = not self.cfg.get("direct_play", True)
        config.save_settings(self.cfg)
        try:
            n = directplay.apply_all(on) if chan.is_active() else 0
        except OSError as ex:
            n = 0
            print(f"[arranque directo] {ex}", file=sys.stderr, flush=True)
        self.toast(("Los juegos se abren directamente, sin la pantalla del launcher" if on else "Los juegos vuelven a abrir con la pantalla del launcher")
                   + (f" ({n} accesos de Steam ajustados)" if n else ""))

    def toggle_via_steam(self):
        self.cfg["play_via_steam"] = not self.cfg.get("play_via_steam", True)
        config.save_settings(self.cfg)
        self.toast("Al pulsar JUGAR: " + ("abrir con el acceso de Steam del juego (sale con su nombre en Big Picture)" if self.cfg["play_via_steam"]
                                           else "Hub abre el juego directamente (en Big Picture se ve como Forgeinator)"))

    def auto_place(self, e, inf):
        """Una vez por juego y sesión: si su README dice dónde quiere tu archivo («Place … in `gamedata/`») y la ficha no lo sabe,
        se guarda en requires.place y se enlaza tu archivo ahí, dentro de la carpeta de la versión elegida."""
        req = e.get("requires") or {}
        if not e.get("repo") or req.get("place") or req.get("rom_dest") or e["id"] in self._place_done:
            return
        self._place_done.add(e["id"])

        def job():
            txt = ghapi.readme_raw(e["repo"])
            pl = [p for p in roms.place_from_text(txt) if p != "."]
            if len(pl) != 1:
                return
            try:
                catalog.add_local(dict(e, requires=dict(req, place=pl[0], place_from="readme")))
                self.reload()
                e2 = self.entry(e["id"]) or e
                lk = library.link_get(e["id"])
                t = library.place(e2, lk, inf["dir"]) if lk else None
            except (OSError, ValueError) as ex:
                print(f"[readme] {e['id']}: no pude aplicar «{pl[0]}»: {ex}", file=sys.stderr, flush=True)
                return
            print(f"[readme] {e['id']}: el README pide el archivo en {pl[0]}" + (f" → enlazado {t}" if t else ""), file=sys.stderr, flush=True)
            self.toast(f"{e['name']}: su README pide tu archivo en «{pl[0]}»" + (": enlazado ahí" if t else " (se enlazará al reconocerlo)"))
        threading.Thread(target=job, daemon=True).start()

    def os_state(self, lid):
        """osver.state cacheado por fecha del .toml (la ficha se dibuja 45 veces por segundo)."""
        try:
            k = gamecfg.path_of(lid).stat().st_mtime_ns
        except OSError:
            k = None
        c = self._osv.get(lid)
        if not c or c[0] != k:
            try:
                st = dict(osver.state(lid), **osver.folders(lid))
            except (OSError, ValueError):
                st = {"root": None, "split": False, "active": "linux", "linux": False, "windows": False, "dir": "", "cwd": ""}
            c = self._osv[lid] = (k, st)
        return c[1]

    def choose_os(self, e, which):
        lid = self.inst(e)["launcher_id"]
        st = self.os_state(lid)
        cur = st["active"] if st["split"] else "linux"
        if which == cur:
            self.toast("Ya es la versión elegida")
            return
        if which == "windows" and not st["windows"]:
            exes = osver.found_exes(e, lid)
            if exes:                                     # v2.98: el instalador ya lo dejó en windows/instalado; falta registrarlo
                self.toast("El juego de Windows ya está instalado: elige su .exe")
                return self.pick_windows_exe(e, start=exes[0].parent)
            return self.install_windows_dl(e)
        try:
            osver.set_active(lid, which)
        except (OSError, ValueError) as ex:
            self.toast(f"No pude cambiar de versión: {ex}")
            return
        self._osv.pop(lid, None)
        self.libchk.pop(lid, None)
        self.toast("JUGAR y Steam abrirán ahora la versión de " + ("Windows (Proton)" if which == "windows" else "Linux"))

    def asset_view(self, e, inf, assets, wlist):
        """Qué builds se muestran en la ficha: «linux» o «windows». Lo elegido manda; si no, Windows solo si no hay de Linux o ese es el activo."""
        want = self.asset_os.get(e["id"])
        if want == "windows" and wlist:
            return "windows"
        if want == "linux" and assets:
            return "linux"
        if wlist and not assets:
            return "windows"
        if wlist and not any(a["class"]["os"] == "linux" for a in assets):
            return "windows"        # lo «genérico» de una release sin nada de Linux es, casi seguro, el build de Windows
        if wlist and inf["installed"]:
            st = self.os_state(inf["launcher_id"])
            if st.get("split") and st.get("active") == "windows":
                return "windows"
        return "linux"

    def rel_for(self, e):
        """Release que se muestra e instala: la elegida a mano o, si no, la última."""
        return self.rel_sel.get(self.rk(e)) or self.rel.get(self.rk(e))

    def peek_asset(self, e, a):
        """Ficha → VER QUÉ TRAE EL ARCHIVO: lista el contenido de un .zip de la release leyendo solo su índice (sin bajarlo entero)."""
        if not a:
            return
        if not a["name"].lower().endswith(".zip"):
            self.toast("Solo sé mirar dentro de los .zip sin bajarlos; los demás se ven al instalar")
            return
        self.toast("Leyendo el índice del archivo…")

        def job():
            try:
                ents = peek.zip_entries(a["url"])
                lines = peek.summary(ents)
                msg = f"{len(ents)} archivo(s):\n" + "\n".join(lines)
            except Exception as ex:  # noqa: BLE001
                msg = f"No pude leerlo sin bajarlo ({type(ex).__name__}: {ex}).\nSe verá al instalar."
            self._rcp_q.append(lambda: self.confirm("Dentro de " + a["name"], msg, lambda: None))
        threading.Thread(target=job, daemon=True).start()

    def frozen(self, e) -> bool:
        return e["id"] in (self.cfg.get("frozen") or {})

    def toggle_freeze(self, e):
        """v2.43: congela las actualizaciones de UN juego: el launcher deja de comprobar/preguntar/actualizar ([update] type = «none») y Hub
        no lo marca con actualización. Descongelar restaura el tipo original. No impide instalar a mano otra versión."""
        lid = self.inst(e)["launcher_id"]
        fz = dict(self.cfg.get("frozen") or {})
        if e["id"] in fz:
            rec = fz.pop(e["id"])
            try:
                if rec.get("type") and rec["type"] != "none":
                    osver.set_update_type(lid, rec["type"])
            except OSError as ex:
                print(f"[congelar] {lid}: no pude restaurar [update] ({ex})", file=sys.stderr, flush=True)
            self.toast("Actualizaciones de este juego: vuelven a comprobarse")
        else:
            try:
                prev = osver.set_update_type(lid, "none")
            except (OSError, ValueError) as ex:
                prev = None
                print(f"[congelar] {lid}: el .toml no se tocó ({ex}); solo Hub deja de avisar", file=sys.stderr, flush=True)
            lcs = self.cfg.get("lc_saved") or {}
            if prev == "none" and lid in lcs:        # el interruptor global lo había apagado: el tipo original pasa a ser el de la congelación
                prev = lcs.pop(lid)
            fz[e["id"]] = {"type": prev, "tag": self.inst(e)["version"] or ""}
            self.toast("Congelado: ni avisos ni actualizaciones automáticas" + ("" if prev is not None else " (solo en Hub: el launcher no tenía [update])"))
        self.cfg["frozen"] = fz
        config.save_settings(self.cfg)
        self._inst_c = None

    def pick_release(self, e):
        """Ficha → ELEGIR OTRA RELEASE: instalar una anterior (p. ej. la última no trae Windows o Linux y otra sí)."""
        lst = self.rel_sum.get(self.rk(e)) or []
        if not lst:
            self.toast("Aún no tengo la lista de releases: pulsa REFRESCAR")
            return

        def pick(tag):
            def job():
                v = github.latest(e["repo"], self.cfg.get("arch", "x86_64"), filt=e.get("asset_filter", ""), tag=tag)
                if v.get("tag") != tag:       # v2.44: antes, si la etiqueta no estaba, se quedaba con la última sin decirlo
                    self._rcp_q.append(lambda: self.toast(f"No encuentro la release {tag} en la lista de GitHub (¿pulsa REFRESCAR?)"))
                    return
                self._rcp_q.append(lambda: (self.rel_sel.__setitem__(self.rk(e), v), self.sel_asset.pop(e["id"], None), self.sel_win.pop(e["id"], None),
                                            self.asset_os.pop(e["id"], None), self.toast(f"Release elegida: {tag}")))
            threading.Thread(target=job, daemon=True).start()

        def label(r):
            return f"{r['tag']} · {r['published']} · Linux {r['linux']} · Windows {r['windows']}" + (" · pre" if r["prerelease"] else "")
        self._rel_menu(e, lst, 0, pick, label)

    def _rel_menu(self, e, lst, off, pick, label, step=7):
        """Lista de releases de 7 en 7 (v2.44: antes solo las 7 últimas); «MÁS ANTIGUAS» pasa a las siguientes."""
        opts = []
        if off == 0:
            opts.append(("ÚLTIMA (automática)", lambda: (self.rel_sel.pop(self.rk(e), None), self.toast("Vuelves a la última release"))))
        else:
            opts.append(("◂ MÁS NUEVAS", lambda: self._rel_menu(e, lst, max(0, off - step), pick, label, step)))
        opts += [(label(r), (lambda t=r["tag"]: pick(t))) for r in lst[off:off + step]]
        if off + step < len(lst):
            opts.append((f"MÁS ANTIGUAS…  ({len(lst) - off - step} más)", lambda: self._rel_menu(e, lst, off + step, pick, label, step)))
        self.modal = {"kind": "choice", "title": f"Elegir release ({off + 1}–{min(off + step, len(lst))} de {len(lst)})", "prev": None,
                      "msg": "Cada línea dice cuántos builds de Linux y de Windows trae esa release. Para volver atrás: elige la que funcionaba, instálala y CONGÉLALA.", "options": opts}
        self.focus = None

    def install_windows_dl(self, e, fresh=False):
        rel = self.rel_for(e) or {}
        wa = rel.get("win_assets") or []
        if not wa:
            self.toast("Esta release no publica un build de Windows")
            return
        a = wa[min(self.sel_win.get(e["id"], 0), len(wa) - 1)]
        if not shutil.which("umu-run"):
            self.toast("Falta umu-run (en Bazzite viene instalado): no puedo abrir builds de Windows")
            return
        if (a.get("class") or {}).get("kind") == "instalador":
            self.install_windows_setup(e, a, rel)
            return
        lid = self.inst(e)["launcher_id"]
        root = osver.root_of(lid) if not fresh else config.GAMES_DIR / e.get("folder", e["id"])
        prot = Path(osver.proton_path()).name
        msg = (f"Hub descargará {a['name']} ({fmt_size(a['size'])}) y lo abrirá con Proton ({prot}) mediante umu-run.\n" +
               (f"Carpeta: {root}/windows" if fresh else
                f"Actualiza {root}/windows (las partidas de «proton-prefix» y la versión de Linux no se tocan)." if self.os_state(lid).get("windows") else
                f"Reorganiza la carpeta del juego:\n{root}/linux  ← lo que tienes ahora\n{root}/windows  ← la versión de Windows\n"
                "Después eliges cuál abren JUGAR y Steam, y puedes volver a Linux cuando quieras."))

        def go():
            if any(d.meta.get("install_win") == e["id"] and d.state in ("queued", "active", "paused") for d in self.mgr.list()):
                self.toast("Ya se está descargando")
                return
            self.mgr.add(a["url"], config.path("downloads_dir"), name=a["name"], sha256=a.get("sha256"),
                         meta={"install_win": e["id"], "fresh": fresh, "version": rel.get("tag", ""), "asset": a["name"], "title": e["name"] + " (Windows)"})
            self.dl_pulse = time.time()
            self.toast("Versión de Windows añadida a DESCARGAS; se instalará sola al terminar")
        self.confirm("Versión de Windows (Proton)", msg, go)

    def install_windows_setup(self, e, a, rel):
        """v2.94: la release solo trae un instalador de Windows (Setup.exe). Se descarga, se abre con Proton en el «C:» del juego y, al acabar,
        eliges el .exe instalado (el mismo flujo de «ya tengo el juego de Windows»). El juego se instala FUERA de la carpeta del juego."""
        inf = self.inst(e)
        lid = inf["launcher_id"] if inf.get("installed") else None
        have = self._setup_on_disk(e, a)
        if have:                                             # v3.01: ya está descargado (450 MB en ReStreet): no se vuelve a bajar
            print(f"[windows] instalador ya descargado: {have}", file=sys.stderr, flush=True)
            self.setup_menu(e, have, lid)
            return
        target = osver.setup_target(e, lid)
        msg = (f"Esta release no trae el juego suelto: trae un INSTALADOR de Windows ({a['name']}, {fmt_size(a['size'])}).\n"
               "Hub lo descarga y lo abre con Proton. En el instalador:\n"
               "  1) tu ISO está en la unidad G: (G:\\)\n  2) como destino elige G:\\instalado (vacía; es " + str(target) + ")\n"
               "     Usa G: y no Z:: en Bazzite Z: es la raíz del sistema, casi sin espacio libre.\n"
               "Cuando termine, vuelve a Hub y pulsa «ELEGIR EL .EXE INSTALADO».")

        def go():
            if any(d.meta.get("install_setup") == e["id"] and d.state in ("queued", "active", "paused") for d in self.mgr.list()):
                self.toast("Ya se está descargando")
                return
            self.mgr.add(a["url"], config.path("downloads_dir"), name=a["name"], sha256=a.get("sha256"),
                         meta={"install_setup": e["id"], "lid": lid, "version": rel.get("tag", ""), "asset": a["name"], "title": e["name"] + " (instalador de Windows)"})
            self.dl_pulse = time.time()
            self.toast("Instalador añadido a DESCARGAS; se abrirá al terminar")
        self.confirm("Instalador de Windows (Proton)", msg, go)

    def _setup_on_disk(self, e, a):
        """El instalador `a` ya descargado (en DESCARGAS o en la carpeta de descargas, con el mismo tamaño), o None."""
        for d in self.mgr.list():
            if d.state == "done" and d.meta.get("asset") == a["name"] and getattr(d, "path", None) and Path(d.path).is_file():
                return str(d.path)
        f = config.path("downloads_dir") / a["name"]
        try:
            if f.is_file() and (not a.get("size") or f.stat().st_size == a["size"]):
                return str(f)
        except OSError:
            pass
        return None

    def _game_iso(self, e):
        """Tu archivo del juego reconocido (ISO/ROM), o el primer disco enlazado; None si no hay."""
        lk = library.link_get(e["id"])
        if lk and Path(lk).exists():
            return lk
        return next((p for p in library.disc_links(e["id"]).values() if Path(p).exists()), None)

    def win_installed(self, e, lid):
        """¿Dejó el instalador un juego en windows/instalado? Con caché de 5 s (la ficha lo pregunta en cada fotograma)."""
        c = self.__dict__.setdefault("_winst_c", {})
        hit = c.get(e["id"])
        now = time.time()
        if hit and now - hit[0] < 5:
            return hit[1]
        try:
            v = bool(osver.found_exes(e, lid))           # v3.02: también si el instalador lo dejó en su ruta por defecto del «C:»
        except OSError:
            v = False
        c[e["id"]] = (now, v)
        return v

    def _after_installer(self, e, lid, since=None):
        """v2.98: el instalador terminó. Si dejó el juego en windows/instalado, se pide elegir su .exe (sin esto JUGAR seguía ofreciendo «descargar»)."""
        self.__dict__.get("_winst_c", {}).pop(e["id"], None)
        exes = osver.installed_exes(e, lid)
        print(f"[windows] instalador terminado {e['id']}: {len(exes)} .exe en windows/instalado", file=sys.stderr, flush=True)
        if not exes and since:                               # v3.01: el instalador pudo usar su ruta por defecto dentro del «C:»
            exes = osver.new_exes(e, lid, since - 120)
            print(f"[windows] .exe nuevos en el prefijo: {[str(x) for x in exes[:8]]}", file=sys.stderr, flush=True)
        if exes:
            self.toast("Instalación terminada: elige el .exe del juego para que JUGAR lo abra")
            self.pick_windows_exe(e, start=exes[0].parent)
        else:
            self.toast("El instalador se cerró sin dejar el juego (ni en windows/instalado ni en el «C:»). Mira windows/hub-installer.log")

    def setup_menu(self, e, setup, lid=None, auto=False):
        """Qué hacer con el instalador ya descargado: abrirlo (otra vez), o elegir el .exe cuando ya está instalado."""
        def run():
            iso = self._game_iso(e)
            try:
                res = osver.run_installer(e, Path(setup), lid, iso)
            except (OSError, ValueError) as ex:
                self.toast(f"No pude abrir el instalador: {ex}")
                print(f"[windows] instalador {e['id']}: {ex}", file=sys.stderr, flush=True)
                return
            proc = res.pop("proc", None)
            print(f"[windows] instalador {e['id']}: {res}", file=sys.stderr, flush=True)
            if iso and lid:
                self.link_into_prefix(e, lid, res.get("iso") or iso)       # v2.98: también en Escritorio y Documentos del «C:» (como en v2.44)
            self.toast("Instalador abierto con Proton. Tu ISO y el destino están en la unidad G: (" + ("ISO enlazada" if iso else "sin ISO reconocida") + ")")
            if proc is not None:
                t0 = time.time()

                def wait():
                    proc.wait()
                    self._rcp_q.append(lambda: self._after_installer(e, lid, t0))
                threading.Thread(target=wait, daemon=True).start()

        def pick():
            tg = osver.setup_target(e, lid)
            if lid is None and not self.inst(e).get("installed"):
                self.toast("Este juego aún no está registrado en Hub: instala antes cualquier versión (aunque sea la de Linux) y vuelve aquí")
                return
            self.pick_windows_exe(e, start=tg if tg.is_dir() else None)
        # v3.02: sin menú intermedio. Al terminar de instalar, Hub busca el juego solo (windows/instalado y el «C:»); «buscarlo a mano»
        # queda como último recurso en AJUSTES DEL JUEGO › ARCHIVOS («¿Ya tienes el juego de Windows?»).
        self._setup_pick = pick
        run()

    def pick_windows_exe(self, e, start=None):
        """Ficha → MÁS OPCIONES: elige el .exe de un juego de Windows que ya tienes y ábrelo con Proton (umu-run) o Wine."""
        lid = self.inst(e)["launcher_id"]
        st = self.os_state(lid)
        start = Path(start) if start else (Path(st.get("dir") or "") if st.get("dir") and Path(st["dir"]).is_dir() else self._first_dir())

        def chosen(p):
            exe = Path(p)

            def run(runner):
                if runner == "proton" and not shutil.which("umu-run"):
                    self.toast("Falta umu-run (en Bazzite viene instalado): prueba con Wine")
                    return
                if runner == "wine" and not osver.find_wine():
                    self.toast("No hay Wine en el sistema, ni en Bottles, Lutris o GE-Proton: instala un runner en Bottles o usa Proton")
                    return

                def job():
                    try:
                        res = osver.attach_windows(lid, exe, runner)
                    except (OSError, ValueError) as ex:
                        self.toast(f"No pude preparar la versión de Windows: {ex}")
                        print(f"[windows] {e['id']}: {ex}", file=sys.stderr, flush=True)
                        return
                    self._osv.pop(lid, None)
                    self.libchk.pop(lid, None)
                    print(f"[windows] {e['id']}: {res}", file=sys.stderr, flush=True)
                    self.toast(f"Listo: JUGAR abrirá {exe.name} con {'Wine' if runner == 'wine' else 'Proton'}. Si falla, activa REGISTRO DE PROTON")
                threading.Thread(target=job, daemon=True).start()
            self.modal = {"kind": "choice", "title": f"Abrir {exe.name} con…", "prev": None,
                          "msg": f"Carpeta: {exe.parent}\nNo se copia nada: Hub enlaza esa carpeta dentro del juego. Sus partidas de Windows irán a «proton-prefix».",
                          "options": [("PROTON (GE-Proton con umu-run, recomendado)", lambda: run("proton")), ("WINE (sistema, Bottles, Lutris o el de GE-Proton)", lambda: run("wine"))]}
            self.focus = None
        self.open_picker(f"Elige el .exe de {e['name']}", start, {".exe"}, chosen)

    def toggle_proton_log(self, e):
        lid = self.inst(e)["launcher_id"]
        try:
            osver.set_proton_log(lid, not osver.proton_log(lid))
        except OSError as ex:
            self.toast(f"No pude cambiarlo: {ex}")
            return
        self.toast("Registro de Proton " + ("activado: abre el juego y mira proton-logs/steam-0.log" if osver.proton_log(lid) else "desactivado"))

    def _exe_missing(self, e, lid):
        """v2.29: antes de lanzar, ¿existe el ejecutable del .toml? Si no (una actualización cambió la estructura), se dice claro y se ofrece
        corregirlo; antes JUGAR no hacía nada y no quedaba ni un mensaje. True = no seguir lanzando."""
        try:
            p = launchlog.binary_of(lid)
            if p is None or Path(p).is_file():
                return False
            idir = Path(osver.folders(lid)["dir"])
            new = install.find_executable(idir) if idir.is_dir() else ""
        except (OSError, ValueError, KeyError):
            return False
        print(f"[jugar] «{lid}»: el ejecutable del launcher no existe ({p}); detectado en la carpeta: {new or 'ninguno'}", file=sys.stderr, flush=True)
        if not new:
            self.confirm("NO ENCUENTRO EL JUEGO", f"El launcher espera {p} y no está. Reinstala el juego desde su ficha (INSTALAR) o revisa la carpeta {idir}.", lambda: None)
            return True

        def fix():
            self.modal = None
            old = install.repair_run(lid, idir, new)
            self._inst_c = None
            self.toast(f"Corregido: ahora abre {new}" if old else "No pude corregir el .toml del launcher")
            if old:
                self.play(e)
        self.modal = {"kind": "choice", "title": "El juego cambió de sitio", "prev": None,
                      "msg": f"El launcher espera «{Path(p).name}» en {Path(p).parent} y ya no está (una actualización cambió la carpeta).\nHe encontrado: {new}",
                      "options": [("CORREGIR Y JUGAR", fix), ("CANCELAR", lambda: setattr(self, "modal", None))]}
        self.focus = None
        return True

    def run_setup(self, e):
        """Abre el configurador que trae el port (…-setup), con tu ISO ya enlazada en su carpeta."""
        try:
            sp = install.setup_exe(osver.folders(self.inst(e)["launcher_id"])["dir"])
        except (OSError, ValueError, KeyError):
            sp = ""
        if not sp:
            self.toast("Este juego no trae configurador")
            return
        self.link_game_linux(e)
        try:
            out = launchlog.new_out(self.inst(e)["launcher_id"])
            with open(out, "wb") as fo:
                pr = subprocess.Popen([sp], cwd=str(Path(sp).parent), stdout=fo, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as ex:
            self.toast(f"No pude abrir el configurador: {ex}")
            return
        self.game_pids.append(pr.pid)
        lk = library.link_get(e["id"])
        print(f"[configurar] {e['id']}: {sp} (pid {pr.pid})", file=sys.stderr, flush=True)
        self.toast("Configurador abierto. " + (f"Tu archivo: {Path(lk).name}" if lk else "Te pedirá tu ISO"))

    def link_game_linux(self, e):
        """Igual que en Windows, para la versión de Linux: deja el enlace a tu ISO/ROM en la carpeta del juego, en la de trabajo (cwd)
        y en linux/ si la instalación está separada, para que el selector de archivos del lanzador la tenga a mano. Nunca pisa archivos."""
        lk = library.link_get(e["id"])
        if not lk or not Path(lk).exists() or not self.cfg.get("link_in_project", True):
            return []
        dirs = []
        try:
            lid = self.inst(e)["launcher_id"]
            st = self.os_state(lid)
            f = osver.folders(lid)
            if st.get("split") and st.get("root"):
                dirs.append(Path(st["root"]) / "linux")
            dirs += [Path(f["dir"]) if f.get("dir") else None, Path(f["cwd"]) if f.get("cwd") else None]
        except (OSError, ValueError, KeyError):
            return []
        made, seen = [], set()
        for d in dirs:
            if not d or str(d) in seen or not d.is_dir():
                continue
            seen.add(str(d))
            try:
                library.place(e, lk, d)
                t = library.place_default(e, lk, d)
                if t:
                    made.append(str(t))
                for p in library.disc_links(e["id"]).values():      # v2.42: los demás discos del port, al lado
                    if Path(p).exists() and str(Path(p).resolve()) != str(Path(lk).resolve()):
                        library.place_default(e, p, d)
            except OSError:
                continue
        if made:
            print(f"[linux] enlace al juego en: {', '.join(made)}", file=sys.stderr, flush=True)
        return made

    def link_game_win(self, e):
        """Deja en <carpeta>/windows un enlace a tu ROM/ISO reconocida: el selector de archivos del lanzador de Windows (p. ej.
        VCSLauncher.exe) empieza ahí. Nunca pisa un archivo real; no escribe a través de windows/game (carpeta de tu juego)."""
        lk = library.link_get(e["id"])
        extras = [p for p in library.disc_links(e["id"]).values() if Path(p).exists()]
        if not lk or not Path(lk).exists():
            if not extras:
                return None
            lk = extras[0]
        try:
            lid = self.inst(e)["launcher_id"]
            st = self.os_state(lid)
            if not st.get("windows") or not st.get("root"):
                return None
            win = Path(st["root"]) / "windows"
            library.place(e, lk, win)
            t = library.place_default(e, lk, win)
            print(f"[windows] enlace al juego en {win}: {t}", file=sys.stderr, flush=True)
            for p in extras:                              # v2.41: los demás discos del port (Chains of Olympus y Ghost of Sparta)
                library.place_default(e, p, win)
            if ownwine.available(win):
                ownwine.note_disc(win, t or lk, extras)   # para «Wine propio», apunta qué ISO es de cada juego (por su ID)
                self._own_c = {}
            self.link_into_prefix(e, lid, t or lk)
            return t
        except (OSError, ValueError, KeyError):
            return None

    def link_into_prefix(self, e, lid, target):
        """Pone también el enlace dentro del «C:» de Proton/Wine (Escritorio y Documentos): el diálogo de abrir de Windows los enseña a primera vista.
        Si el prefijo aún no existe (primer arranque), espera a que lo cree Proton (hasta ~2 min) en un hilo."""
        if not target:
            return

        def job():
            for _ in range(40):
                try:
                    made = osver.link_into_prefix(lid, Path(target))
                except OSError as ex:
                    print(f"[windows] enlace en el prefijo: {ex}", file=sys.stderr, flush=True)
                    return
                if made is not None:
                    if made:
                        print(f"[windows] enlace en el prefijo: {', '.join(made)}", file=sys.stderr, flush=True)
                    return
                time.sleep(3)
        threading.Thread(target=job, daemon=True).start()

    def _on_done_win(self, d, e):
        d.meta["phase"] = "Instalando versión de Windows…"
        try:
            if d.meta.get("fresh"):
                res = osver.install_windows_only(e, d.path, d.meta.get("version", ""), d.meta.get("asset", ""))
            else:
                lid = self.inst(e)["launcher_id"]
                hint = (osver.meta(osver.root_of(lid)).get("linux") or {}).get("exe") or e["name"]
                res = osver.install_windows(lid, d.path, d.meta.get("version", ""), osver.asset_glob(d.meta.get("asset", "")), Path(str(hint)).stem)
                self._osv.pop(lid, None)
                self.libchk.pop(lid, None)
            self.link_game_win(e)
            d.meta["phase"] = f"Instalada (Windows: {res['exe']})"
            self._inst_c = None
            history.record(self.inst(e)["launcher_id"], "instalar", True, "versión de Windows " + d.meta.get("version", ""), version=d.meta.get("version", ""))
            self.toast(f"{e['name']}: versión de Windows lista; JUGAR y Steam la abrirán")
        except Exception as ex:  # noqa: BLE001
            d.meta["phase"] = f"Error al instalar la versión de Windows: {ex}"
            history.record(e.get("launcher_id") or e["id"], "instalar", False, "Windows: " + str(ex), version=d.meta.get("version", ""))
            self.toast("Falló la versión de Windows: " + str(ex))

    def rel_date(self, e, tag) -> str:
        """Fecha de publicación de la release `tag` si está en la lista guardada (las 40 últimas)."""
        return next((r["published"] for r in (self.rel_sum.get(self.rk(e)) or []) if r.get("tag") == tag), "")

    def toggle_cfg(self, key, default, label):
        self.cfg[key] = not self.cfg.get(key, default)
        config.save_settings(self.cfg)
        self.toast(f"{label}: " + ("sí" if self.cfg[key] else "no"))

    def toggle_launcher_checks(self):
        """v2.48: interruptor global de la comprobación de actualizaciones del launcher al abrir cada juego."""
        self.cfg["launcher_checks"] = not self.cfg.get("launcher_checks", True)
        n = lcheck.apply(self.cfg)
        config.save_settings(self.cfg)
        self.toast(("El launcher vuelve a comprobar al abrir" if self.cfg["launcher_checks"] else "El launcher ya no comprueba al abrir ningún juego") + f" · {n} juegos cambiados")

    def own_block(self, e, lid):
        """«Wine propio»: antes de lanzar, ¿está todo? Devuelve el motivo si no (antes el script salía en silencio) o ""."""
        try:
            if osver.windows_runner(lid) != "own" or self.os_state(lid).get("active") != "windows":
                return ""
        except (OSError, ValueError, KeyError):
            return ""
        self._own_c = {}
        oi = self.own_info(lid)
        if not oi:
            return ""
        if not oi["wine_ok"]:
            b = oi["cfg"]["binary"]
            return f"No encuentro tu Wine propio ({ownwine.expand(b)}): ficha > Windows > CAMBIAR EL WINE" if b else "Elige tu Wine propio: ficha > Windows > ELEGIR EL WINE"
        if oi["cfg"]["profile"] != "gow" or oi["cfg"]["mode"] != "direct":
            return ""
        g = oi["cfg"]["game"]
        nm = ownwine.GAMES[g][1]
        if not oi["built"][g]:
            return f"{nm} aún no está compilado: ficha > Windows > COMPILAR"
        if not oi["disc"][g]:
            return f"Falta tu ISO USA de {nm} ({ownwine.GAMES[g][0]}): ficha > Windows > ELEGIR ISO"
        return ""

    def _note_disc_link(self, e, path):
        """Si el port pide varios discos (serials) y este es uno de ellos por su ID, lo guarda para ese juego. Devuelve el ID o None."""
        sers = (e.get("requires") or {}).get("serials") or []
        if len(sers) < 2:
            return None
        try:
            r = discid.read_id(path)
        except OSError:
            r = None
        for s in sers:
            if r and discid.norm(r["id"]) == discid.norm(s):
                library.disc_link_set(e["id"], s, path)
                return s
        return None

    def pick_disc(self, e, serial):
        """Ficha > Windows (Wine propio): elige el ISO USA de UN juego del port; se reconoce por su ID."""
        dirs = [Path(os.path.expandvars(str(d))).expanduser() for d in self.cfg["watch_dirs"]]
        start = self.rom_dir_for(e.get("platform")) or next((d for d in dirs if d.is_dir()), Path.home())

        def chosen(p):
            r = discid.read_id(p)
            if not r:
                self.toast("No sé leer el ID de ese archivo (solo ISO). ¿Es un .chd/.cso o no es un UMD?")
                return
            if discid.norm(r["id"]) != discid.norm(serial):
                self.toast(f"Ese archivo es {r['id']} ({r['note'] or r['kind']}); aquí hace falta {serial}")
                return
            library.disc_link_set(e["id"], serial, p)
            if not library.link_get(e["id"]):
                library.link_set(e["id"], p)
            self.link_game_win(e)
            self._own_c = {}
            self.toast(f"ISO de {ownwine.disc_label(serial)} guardado")
        self.open_picker(f"Elige el ISO USA ({serial})", start, {".iso"}, chosen)

    def toggle_steam_splash(self):
        self.cfg["steam_splash"] = not self.cfg.get("steam_splash", True)
        config.save_settings(self.cfg)
        self.toast("Pantalla de carga al abrir por Steam: " + ("sí" if self.cfg["steam_splash"] else "no"))

    def cycle_proton_default(self):
        """v2.65: Proton por defecto de los juegos de Windows: AUTOMÁTICO → cada Proton instalado → AUTOMÁTICO."""
        opts = [""] + [p for _, p in osver.list_protons()]
        cur = self.cfg.get("proton_default", "")
        nxt = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else ""
        self.cfg["proton_default"] = nxt
        osver.DEFAULT_PROTON = nxt
        config.save_settings(self.cfg)
        self.toast("Proton por defecto: " + (Path(nxt).name if nxt else "automático") + " · los juegos que ya tienen su hub-run.sh lo cambian desde su ficha")

    def toggle_close_on_play(self):
        self.cfg["close_on_play"] = not self.cfg.get("close_on_play", True)
        config.save_settings(self.cfg)
        self.toast("Al pulsar JUGAR: " + ("Hub se cierra" if self.cfg["close_on_play"] else "Hub se queda abierto"))

    # ── ficha: Steam, partidas portátiles y carpeta de la biblioteca ──
    def steam_art(self, e):
        exe = config.LAUNCHER / "bin" / "play"
        if not exe.exists():
            self.toast("No encuentro el launcher unificado (~/Games/launcher)")
            return
        lid = self.inst(e)["launcher_id"]
        if any(b.state in ("queued", "running") and getattr(b, "label", "") == "ARTE PARA STEAM" and b.entry["id"] == e["id"] for b in self.builds):
            self.toast("Ya está en marcha")
            return
        job = cmdjob.CmdJob("ARTE PARA STEAM", e["name"], [("Generando acceso para Steam", [exe, "--shortcuts"])], e)
        self.builds.append(job)
        job.start()
        self.toast("Generando el acceso… mira DESCARGAS. El arte se elige con «ELEGIR ARTE»")

    def steam_apply(self, e):
        exe = config.LAUNCHER / "bin" / "play"
        if steamsetup.in_game_mode():
            self._desktop_go("AÑADIR A STEAM", "Hace falta el MODO ESCRITORIO (Steam no se toca desde Big Picture). Hub te llevará al escritorio y abrirá allí «Preparar Steam» para aplicar este juego y los demás. ¿Seguir?")
            return
        self.confirm("AÑADIR A STEAM", "Esto CIERRA Steam, hace copia de shortcuts.vdf y añade/actualiza los accesos con su icono y arte. ¿Seguir?",
                     lambda: self._run_steam(e, exe))

    def _run_steam(self, e, exe):
        job = cmdjob.CmdJob("ARTE PARA STEAM", e["name"], [("Aplicando en Steam", [exe, "--steam", "--yes"])], e)
        self.builds.append(job)
        job.start()
        self.toast("Aplicando en Steam… mira DESCARGAS")

    def steam_all(self):
        """Dentro del escritorio: accesos + arte de TODOS los juegos del launcher y luego --steam (cierra Steam, copia shortcuts.vdf)."""
        exe = config.LAUNCHER / "bin" / "play"
        if not exe.exists():
            self.toast("No encuentro el launcher unificado (~/Games/launcher)")
            return
        if any(b.state in ("queued", "running") and getattr(b, "label", "") == "STEAM: TODO" for b in self.builds):
            self.toast("Ya está en marcha")
            return
        # `bin/play --art` pregunta por teclado «¿Cuál es el juego?»: Hub no puede responder, así que el arte se elige antes con «ELEGIR ARTE»
        missing = [x["name"] for x in self.entries if self.inst(x)["installed"] and not self.art_files(x)
                   and not (config.LAUNCHER / "art" / self.inst(x)["launcher_id"]).is_dir()]
        if missing:
            print(f"[steam] juegos SIN arte (se añadirán a Steam sin carátula): {missing}", file=sys.stderr, flush=True)
            self.toast(f"{len(missing)} juego(s) sin arte: elígelo antes con «Elegir arte» ({missing[0]}…)")
        job = cmdjob.CmdJob("STEAM: TODO", "Todos los juegos", [("Generando accesos", [exe, "--shortcuts"]),
                                                            ("Aplicando en Steam (cierra Steam)", [exe, "--steam", "--yes"])], {"id": "_steam_all", "name": "Todos los juegos"})
        self.builds.append(job)
        self.steam_job = job
        job.start()
        self.toast("Aplicando… Steam se cerrará; cuando acabe vuelve a modo juego")

    def steam_to_desktop(self):
        self._desktop_go("AÑADIR TODO A STEAM", "Hub te llevará al ESCRITORIO y abrirá allí la pantalla «Preparar Steam» para personalizar cada juego y aplicar. Al terminar, vuelves a Big Picture tú (o con el botón). ¿Seguir?")

    def _desktop_go(self, title, msg):
        def go():
            ok, m = steamsetup.to_desktop()
            self.toast(m)
            print(f"[steam] pasar al escritorio: {ok} · {m}", file=sys.stderr, flush=True)
            if ok:
                self.exit_at = time.time() + 2.0
                self.why = "cambio al escritorio para preparar Steam"
        self.confirm(title, msg, go)

    def steam_back(self):
        def go():
            ok, msg = steamsetup.to_game_mode()
            self.toast(msg)
            print(f"[steam] volver al modo juego: {ok} · {msg}", file=sys.stderr, flush=True)
        self.confirm("VOLVER AL MODO JUEGO", "Se cerrará esta sesión de escritorio y volverás a Big Picture. ¿Seguir?", go)

    def draw_steam(self, body):
        self.begin("steam", body)
        pad, gap = self.n(48), self.n(24)
        y = self.n(30)
        self.text("Preparar Steam", pad, self.cy(y), 40, TXT, True)
        y += self.n(62)
        msg = ("Personaliza cada juego (fondo, icono, portada) y luego pulsa APLICAR. Aplicar cierra Steam, guarda una copia de shortcuts.vdf y añade todos los accesos con su arte." if not steamsetup.in_game_mode()
               else "Estás en Big Picture: aplicar no es posible aquí (Steam no puede cerrarse). Pasa al escritorio con el botón de abajo.")
        for ln in self.wrap(msg, 21, self.W - 2 * pad):
            self.text(ln, pad, self.cy(y), 21, DIM)
            y += self.n(30)
        y += self.n(10)
        job = getattr(self, "steam_job", None)
        tw = (self.W - 2 * pad - gap) // 2
        if steamsetup.in_game_mode():
            self.tile("st_desk", (pad, y, tw, self.n(130)), "Pasar al escritorio", "Hub se abre allí en «Preparar Steam»", self.steam_to_desktop, ACC, big=28)
        else:
            self.tile("st_apply", (pad, y, tw, self.n(130)), "Aplicar a Steam", "Accesos + arte de todos los juegos", self.steam_all, ACC, big=28)
            self.tile("st_back", (pad + tw + gap, y, tw, self.n(130)), "Volver al modo juego", "Cuando termines", self.steam_back, None, big=28)
        y += self.n(160)
        if job:
            col = OK if job.state == "done" else ERR if job.state == "error" else WARN
            self.text(f"{job.stage}" + (" — LISTO: ya puedes volver al modo juego" if job.state == "done" else ""), pad, self.cy(y), 24, col, True, self.W - 2 * pad)
            y += self.n(40)
            for ln in list(job.log)[-6:]:
                self.text(ln, pad, self.cy(y), 17, DIM, maxw=self.W - 2 * pad)
                y += self.n(24)
            y += self.n(16)
        self.text("Tus juegos", pad, self.cy(y), 28, TXT, True)
        y += self.n(54)
        cols = 3 if self.W < self.n(2000) else 4
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ch = self.n(150)
        reg = [e for e in self.entries if self.inst(e)["installed"]]
        for k, e in enumerate(reg):
            st = gamecfg.state(self.inst(e)["launcher_id"])
            self.tile(f"stg:{e['id']}", (pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + gap), cw, ch), e["name"],
                      "Arte propio listo" if st.get("art") else "Elegir arte", lambda e=e: self.art_open(e), self.tint(e["name"], 0.30, 0.45),
                      x=lambda e=e: self.custom_art(e), y=lambda e=e: self.open_detail(e), cover=self.cover(e, (cw, ch)))
        if not reg:
            self.text("No hay juegos instalados todavía.", pad, self.cy(y), 22, DIM)
        self.end()

    def toggle_portable(self, e):
        inf = self.inst(e)
        lid = inf["launcher_id"]
        st = gamecfg.state(lid)
        if not st["exists"]:
            self.toast("El juego no está registrado en el launcher")
            return
        if st["portable"]:
            gamecfg.set_portable(lid, False)
            self.toast("Partidas: vuelven a su sitio normal (los archivos copiados se quedan)")
            return
        old = [d for d, _ in gamecfg.find_old_data([e["name"], e["id"], lid, Path(inf["dir"]).name])]

        def go():
            try:
                gamecfg.set_portable(lid, True)
                done = gamecfg.migrate_data(inf["dir"], [e["name"], e["id"], lid, Path(inf["dir"]).name])
                print(f"[juego] {lid}: partidas en la carpeta del juego; copiado: {[str(a) for a, _ in done]}", file=sys.stderr, flush=True)
                self.toast(f"Partidas dentro de {inf['dir']}" + (f" (copiadas {len(done)} carpetas)" if done else ""))
            except (OSError, ValueError) as ex:
                self.toast(f"No se pudo: {ex}")
        msg = (f"Los ajustes y partidas del juego se guardarán en {inf['dir']}/config y /data. "
               + (f"Se COPIARÁN las que ya existen ({', '.join(d.name for d in old)}); las originales no se borran. " if old else "")
               + "Solo funciona si el juego respeta XDG_CONFIG_HOME/XDG_DATA_HOME; se puede revertir.")
        self.confirm("PARTIDAS EN LA CARPETA DEL JUEGO", msg, go)

    IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    def custom_art(self, e):
        inf = self.inst(e)
        if not gamecfg.state(inf["launcher_id"])["exists"]:
            self.toast("El juego no está registrado en el launcher")
            return
        start = next((d for d in (Path(config.path("downloads_dir")), Path.home() / "Pictures", Path.home() / "Downloads", Path.home()) if d.is_dir()), Path.home())

        def go(path):
            try:
                res = artgen.generate(path, e["name"], Path(inf["dir"]) / "art")
                gamecfg.set_art(inf["launcher_id"], {k: str(v) for k, v in res.items()})
                self._cov = {}
                print(f"[arte] {inf['launcher_id']}: generado desde {path} → {Path(inf['dir']) / 'art'}", file=sys.stderr, flush=True)
                self.toast("Arte creado en la carpeta del juego. Usa «AÑADIR A STEAM» para aplicarlo")
            except (OSError, ValueError, pygame.error) as ex:
                self.toast(f"No pude usar esa imagen: {ex}")
        self.open_picker(f"Elige el fondo para «{e['name']}»", start, self.IMG_EXTS, go)

    def clear_art(self, e):
        try:
            gamecfg.set_art(self.inst(e)["launcher_id"], None)
            self._cov = {}
            self.toast("Arte propio quitado del launcher (los archivos de art/ no se borran)")
        except (OSError, ValueError) as ex:
            self.toast(f"No se pudo: {ex}")

    ART_ORDER = ("cover", "hero", "banner", "grid", "portrait", "vertical")
    ART_ORDER_V = ("portrait", "vertical", "grid", "cover", "poster", "hero", "banner")

    def art_files(self, e):
        """Arte de la carpeta del juego. Se guarda mientras no cambie la carpeta (su mtime): Inicio lo pedía en cada fotograma
        para cada tarjeta (iterdir ×41 = 120 ms en el Ally); ahora es un stat por tarjeta."""
        d = Path(self.inst(e)["dir"]) / "art"
        try:
            m = d.stat().st_mtime_ns
        except OSError:
            return {}
        c = self.__dict__.setdefault("_artf", {})
        hit = c.get(str(d))
        if hit and hit[0] == m:
            return dict(hit[1])
        out = self._art_scan(d)
        c[str(d)] = (m, out)
        return dict(out)

    def _art_scan(self, d):
        out = {}
        try:
            for f in d.iterdir():
                if f.suffix.lower() in self.IMG_EXTS:
                    out.setdefault(f.stem.lower(), f)
        except OSError:
            pass
        return out

    def art_import(self, e):
        """Arte que ya bajó el launcher (--art) → copia a la carpeta del juego (sin pisar nada). Una vez por sesión y juego."""
        done = self.__dict__.setdefault("_imp", set())
        if e["id"] in done:
            return
        done.add(e["id"])
        inf = self.inst(e)
        if not inf["installed"]:
            return
        src = config.LAUNCHER / "art" / inf["launcher_id"]
        dst = Path(inf["dir"]) / "art"
        try:
            for f in src.iterdir():
                if f.suffix.lower() in self.IMG_EXTS and not any((dst / (f.stem + x)).exists() for x in self.IMG_EXTS):
                    dst.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst / f.name)
        except OSError:
            pass

    @staticmethod
    def fit_blur(img, size):
        """Si la imagen no tiene la proporción de la tarjeta: se muestra entera y el hueco se rellena con ella misma, ampliada y difuminada."""
        w, h = img.get_size()
        if abs((w / h) / (size[0] / size[1]) - 1) < 0.3:
            return artgen._cover(img, size)
        sm = pygame.transform.smoothscale(artgen._cover(img, size), (max(8, size[0] // 24), max(8, size[1] // 24)))
        bg = pygame.transform.smoothscale(sm, size)
        dark = pygame.Surface(size, pygame.SRCALPHA)
        dark.fill((0, 0, 0, 110))
        bg.blit(dark, (0, 0))
        k = min(size[0] / w, size[1] / h)
        fg = pygame.transform.smoothscale(img, (max(1, int(w * k)), max(1, int(h * k))))
        bg.blit(fg, ((size[0] - fg.get_width()) // 2, (size[1] - fg.get_height()) // 2))
        return bg

    def cover(self, e, size, small=False):
        """Imagen de la carpeta del juego (art/) para la tarjeta, rellenando con desenfoque si no encaja; o None (todavía).
        Se prepara en un hilo (leer + escalar + desenfocar cuesta 25-100 ms en la Ally) y aparece en cuanto está lista."""
        key = (e["id"], size)
        if key in self._cov:
            return self._cov[key]
        if key in self._cov_jobs:
            return None
        if small and len(self._cov_jobs) >= 3:      # las miniaturas de Explorar se cargan de 3 en 3 para no ahogar la CPU del Ally
            return None
        f = None
        try:
            self.art_import(e)
            files = self.art_files(e)
            order = self.ART_ORDER_V if size[1] > size[0] else self.ART_ORDER      # tarjeta vertical → arte vertical primero; apaisada → héroe/banner
            f = next((files[k] for k in order if k in files), None)
        except (OSError, pygame.error):
            f = None
        if not f:
            f = covers.path_for(e["id"])
        if not f:
            self._cov[key] = None
            return None
        self._cov_jobs.add(key)
        k = self.k

        def job():
            sur = None
            try:
                img = pygame.image.load(str(f)).convert()
                sur = self.fit_blur(img, size)
                g = pygame.Surface(size, pygame.SRCALPHA)
                g.fill((0, 0, 0, 70))
                sur.blit(g, (0, 0))
                sur = artgen._round(sur, int(26 * k))
            except (OSError, pygame.error, ValueError):
                sur = None
            self._cov_done.append((key, sur))
        threading.Thread(target=job, daemon=True).start()
        return None

    def _cov_collect(self):
        """Pasa a la caché las portadas que los hilos ya terminaron (se llama una vez por fotograma)."""
        dl = getattr(self, "_doctor_l", None)
        if dl:
            self._doctor_l = None
            self.show_log(dl)
        done = self._cov_done
        while done:
            key, sur = done.pop(0)
            self._cov_jobs.discard(key)
            self._cov[key] = sur
            while len(self._cov) > 420:                 # tope de memoria: se olvidan las más antiguas (se vuelven a cargar si hace falta)
                self._cov.pop(next(iter(self._cov)))

    # ── elegir arte en SteamGridDB (juego → tipo → imagen) ──
    def art_open(self, e):
        if not self.inst(e)["installed"] or not gamecfg.state(self.inst(e)["launcher_id"])["exists"]:
            self.toast("Instala el juego primero (así sé en qué carpeta guardar el arte)")
            return
        src = self.cfg.get("art_source", "sgdb")
        if src not in artsrc.ORDER:
            src = "sgdb"
        if src == "sgdb" and not sgdb.key():
            src = "libretro"   # sin clave se empieza por la fuente que no la necesita
        self.art = {"src": src, "e": e, "step": "game", "games": [], "gid": None, "kind": "portrait", "imgs": [], "raw": {}, "surf": {}, "busy": "Buscando…", "err": "", "picked": {}}
        self.tab, self.detail, self.focus, self.reveal = "art", None, None, True
        self.views.setdefault("art", View()).off = 0
        self.art_search(self.search_name(e))

    def art_bg(self, fn, msg):
        a = self.art
        a["busy"], a["err"] = msg, ""
        a["jobs"] = a.get("jobs", 0) + 1
        wk = self.__dict__.setdefault("_work", {})
        wid = object()
        wk[wid] = ("Arte: " + msg.rstrip("…").rstrip("."), time.time())

        def job():
            try:
                fn()
            except Exception as ex:  # noqa: BLE001
                a["err"] = f"{type(ex).__name__}: {ex}"[:300]
                print(f"[arte] error: {a['err']}", file=sys.stderr, flush=True)
            finally:
                a["jobs"] -= 1
                wk.pop(wid, None)
                if a["jobs"] <= 0:
                    a["busy"] = ""
        threading.Thread(target=job, daemon=True).start()

    def art_search(self, term):
        a = self.art
        a["term"] = term
        a["tok"] = tok = a.get("tok", 0) + 1
        src = a["src"]

        def go():
            games = artsrc.search(src, term, a["e"])
            if a["tok"] == tok and a["src"] == src:   # una búsqueda vieja (otra fuente/otro nombre) no pisa a la nueva
                a["games"] = games
        self.art_bg(go, f"Buscando «{term}»…")

    def art_switch(self):
        self.art_use(artsrc.ORDER[(artsrc.ORDER.index(self.art["src"]) + 1) % len(artsrc.ORDER)])

    def art_use(self, src):
        a = self.art
        if src == a["src"] and a.get("games") is not None and a["step"] == "game" and a["games"]:
            return
        a.update(src=src, step="game", games=[], imgs=[], raw={}, surf={}, picked={}, gid=None)
        self.cfg["art_source"] = a["src"]
        config.save_settings(self.cfg)
        self.focus, self.reveal = None, True
        if a["src"] == "sgdb" and not sgdb.key():
            a["err"] = "SteamGridDB necesita clave: pégala con «PEGAR CLAVE»"
            return
        if a["src"] == "tgdb" and not artsrc.tgdb_key():
            a["err"] = "TheGamesDB necesita clave de API: pégala con «PEGAR CLAVE»"
            return
        if a["src"] == "screenscraper" and not (artsrc.ss_creds()["user"] and artsrc.ss_creds()["password"]):
            a["err"] = "ScreenScraper necesita tu usuario y contraseña (botones de arriba)"
            return
        self.art_search(a.get("term") or self.search_name(a["e"]))

    def art_ss_field(self, name, label):
        def done(t):
            if t.strip():
                sgdb.env_set(name, t)
                c = artsrc.ss_creds()
                self.toast(f"{label} guardado en ~/Games/launcher/.env")
                if self.art and self.art["src"] == "screenscraper" and c["user"] and c["password"]:
                    self.art["err"] = ""
                    self.art_search(self.art.get("term") or self.search_name(self.art["e"]))
        self.osk(label + " de ScreenScraper (screenscraper.fr)", done, sgdb.env_get(name) if name.endswith("USER") else "")

    def art_tgdb_key(self):
        def done(t):
            if t.strip():
                sgdb.env_set("THEGAMESDB_KEY", t)
                self.toast("Clave de TheGamesDB guardada en ~/Games/launcher/.env")
                if self.art and self.art["src"] == "tgdb":
                    self.art["err"] = ""
                    self.art_search(self.art.get("term") or self.search_name(self.art["e"]))
        self.osk("Clave de API de TheGamesDB (thegamesdb.net)", done, "")

    def art_paste_key(self):
        self.osk("Clave de SteamGridDB (steamgriddb.com → Preferences → API)", lambda t: (sgdb.save_key(t), self.art_switch() if self.art["src"] != "sgdb" else self.art_search(self.art.get("term", ""))) if t.strip() else None, "")

    def art_research(self):
        if self.art:
            self.osk("Nombre del juego en SteamGridDB", lambda t: (self.art_search(t.strip()), self.art.update(step="game")) if t.strip() else None, self.art.get("term", ""))

    def art_game(self, g):
        a = self.art
        a["gid"], a["gname"], a["step"] = g["id"], g["name"], "kind"
        self.focus, self.reveal = None, True
        self.art_kind(a["kind"])

    def art_kind(self, kind):
        a = self.art
        a.update(kind=kind, imgs=[], pv=None)
        self.focus, self.reveal = None, True
        self.views.setdefault("art", View()).off = 0
        gid = a["gid"]

        def go():
            imgs = artsrc.images(a["src"], kind, gid, a["e"])
            if a.get("kind") != kind or a["step"] != "kind":
                return   # ya cambiaste de tipo o de juego: esta respuesta es vieja
            a["imgs"], a["tdone"] = imgs, 0
            todo = [i for i in imgs if i["id"] not in a["raw"]]
            a["terrs"] = []
            t0 = time.time()
            from concurrent.futures import ThreadPoolExecutor

            def one(i):
                if a.get("kind") != kind or a["step"] != "kind":
                    return
                try:
                    a["raw"][i["id"]] = artsrc.thumb_bytes(a["src"], i["thumb"], 30)
                except Exception as ex:  # noqa: BLE001
                    a["raw"][i["id"]] = b""
                    a.setdefault("terrs", []).append(str(ex)[:160] or type(ex).__name__)
                    print(f"[arte] miniatura {i['id']} falló: {type(ex).__name__}: {ex}"[:200], file=sys.stderr, flush=True)
                a["tdone"] += 1
                a["busy"] = f"Cargando miniaturas {a['tdone']}/{len(todo)}…"
            with ThreadPoolExecutor(max_workers=6) as ex:
                list(ex.map(one, todo))
            if a.get("terrs"):       # v2.79: antes solo decía «sin miniatura» y la causa iba al terminal
                a["err"] = f"{len(a['terrs'])} de {len(todo)} miniaturas no cargaron: {a['terrs'][0]}"
            print(f"[arte] {kind}: {len(imgs)} opciones, {len(todo)} miniaturas en {time.time() - t0:.1f}s", file=sys.stderr, flush=True)
        self.art_bg(go, f"Cargando {sgdb.KINDS[kind][2].lower()}…")

    def art_preview(self, i):
        a = self.art
        if not a["imgs"]:
            return
        a["pv"] = i % len(a["imgs"])
        self.focus, self.reveal = "pv_use", True
        img = a["imgs"][a["pv"]]
        a.setdefault("full", {})
        if img["id"] not in a["full"]:
            a["full"][img["id"]] = None

            def go():
                try:
                    a["full"][img["id"]] = artsrc.get_bytes(a["src"], img["url"], 60)
                except Exception:  # noqa: BLE001
                    a["full"][img["id"]] = b""
            threading.Thread(target=go, daemon=True).start()

    def art_pv_move(self, d):
        a = self.art
        if a.get("pv") is not None and a["imgs"]:
            self.art_preview(a["pv"] + d)

    def art_pv_surface(self, img):
        """La mejor imagen disponible: la completa si ya bajó; si no, la miniatura ampliada."""
        a = self.art
        fs = a.setdefault("fsurf", {})
        raw = (a.get("full") or {}).get(img["id"])
        if raw and fs.get(img["id"]) is None:
            try:
                fs[img["id"]] = pygame.image.load(io.BytesIO(raw)).convert()
            except pygame.error:
                fs[img["id"]] = False
        if fs.get(img["id"]):
            return fs[img["id"]], True
        return a["surf"].get(img["id"]) or None, False

    def draw_art_preview(self, a, pad, gap, y):
        img = a["imgs"][a["pv"]]
        n = len(a["imgs"])
        self.text(f"{sgdb.KINDS[a['kind']][2]} · opción {a['pv'] + 1} de {n}" + (f"  ·  {img['style']}" if img.get("style") else ""), pad, self.cy(y), 24, TXT, True, self.W - 2 * pad)
        y += self.n(50)
        bw = int((self.W - 2 * pad) * 0.60)
        bh = self.n(660)
        box = pygame.Rect(pad, self.cy(y), bw, bh)
        self.rr(box, PANEL, 22)
        sf, full = self.art_pv_surface(img)
        if sf:
            k = min((box.w - self.n(24)) / sf.get_width(), (box.h - self.n(24)) / sf.get_height())
            sc = pygame.transform.smoothscale(sf, (max(1, int(sf.get_width() * k)), max(1, int(sf.get_height() * k))))
            self.screen.blit(sc, sc.get_rect(center=box.center))
        else:
            self.text("Cargando…", box.centerx, box.centery, 24, DIM, anchor="c")
        if sf and not full:
            self.text("miniatura (bajando la imagen completa…)", box.x + self.n(16), box.bottom - self.n(34), 17, WARN)
        rx = pad + bw + gap
        rw = self.W - pad - rx
        self.text("Así se verá en Hub", rx, self.cy(y), 21, DIM, True)
        mock = pygame.Rect(rx, self.cy(y + self.n(36)), rw, int(rw * 0.39))
        if sf:
            m = self.fit_blur(sf, mock.size)
            g = pygame.Surface(mock.size, pygame.SRCALPHA)
            g.fill((0, 0, 0, 70))
            m.blit(g, (0, 0))
            self.screen.blit(artgen._round(m, int(26 * self.k)), mock)
            self.text(a["e"]["name"], mock.x + self.n(18), mock.y + self.n(16), 24, TXT, True, mock.w - self.n(36))
        by = y + self.n(36) + mock.h + self.n(26)
        self.button("pv_use", (rx, by, rw, self.n(72)), "USAR ESTA IMAGEN", lambda: self.art_pick(img), "primary", 22)
        by += self.n(86)
        hw = (rw - self.n(14)) // 2
        self.button("pv_prev", (rx, by, hw, self.n(64)), "‹ ANTERIOR", lambda: self.art_pv_move(-1), "normal", 19)
        self.button("pv_next", (rx + hw + self.n(14), by, hw, self.n(64)), "SIGUIENTE ›", lambda: self.art_pv_move(1), "normal", 19)
        by += self.n(78)
        self.button("pv_close", (rx, by, rw, self.n(64)), "VOLVER A LA LISTA", lambda: a.__setitem__("pv", None), "normal", 19)
        self.cur.nh = max(self.cur.nh, y + bh + self.n(60))

    def art_pick(self, img):
        a = self.art
        e, kind = a["e"], a["kind"]
        inf = self.inst(e)
        dst = Path(inf["dir"]) / "art"
        a["pv"] = None

        def go():
            tmp = dst / f"_{kind}.dl"
            artsrc.fetch(a["src"], img["url"], tmp)
            sur = pygame.image.load(str(tmp))
            pygame.image.save(sur, str(dst / f"{kind}.png"))
            tmp.unlink(missing_ok=True)
            for old in dst.glob(f"{kind}.*"):
                if old.suffix.lower() != ".png":
                    old.unlink(missing_ok=True)
            files = {k: str(f) for k, f in self.art_files(e).items() if k in ("icon", "portrait", "banner", "hero", "logo")}
            gamecfg.set_art(inf["launcher_id"], files)
            a["picked"][kind] = img["id"]
            self._cov = {}
            print(f"[arte] {inf['launcher_id']}: {kind} elegido ({img['id']}) → {dst}", file=sys.stderr, flush=True)
            self.toast(f"{sgdb.KINDS[kind][2]} guardado en la carpeta del juego")
        self.art_bg(go, "Descargando…")

    def draw_art(self, body):
        a = self.art
        if not a:
            self.go_tab("steam")
            return
        self.begin("art", body)
        pad, gap = self.n(48), self.n(20)
        y = self.n(26)
        e = a["e"]
        self.text(f"Arte de {e['name']}", pad, self.cy(y), 34, TXT, True, self.W - 2 * pad)
        y += self.n(56)
        if a["busy"]:
            self.text(a["busy"], pad, self.cy(y), 21, WARN, True)
            y += self.n(40)
        if a["err"]:
            self.text(a["err"], pad, self.cy(y), 19, ERR, maxw=self.W - 2 * pad)
            y += self.n(36)
        # selector de fuente: 3 opciones tocables, la activa resaltada
        self.text("Fuente de imágenes", pad, self.cy(y), 17, DIM, True)
        y += self.n(30)
        x = pad
        for src in artsrc.ORDER:
            lab = {"sgdb": "SteamGridDB", "libretro": "libretro", "tgdb": "TheGamesDB", "screenscraper": "ScreenScraper"}[src]
            w = self.n(250)
            self.button(f"a_s:{src}", (x, y, w, self.n(56)), lab, lambda src=src: self.art_use(src), "chipsel" if a["src"] == src else "normal", 19, pill=True)
            x += w + self.n(12)
        y += self.n(72)
        # cuenta: si falta se pide (botón destacado). Si ya existe, solo se ve su estado; CAMBIARLA vive al final de la pantalla, lejos del camino
        # (v2.77: estaba justo bajo el selector de fuente y se pulsaba sin querer)
        miss = False
        if a["src"] == "sgdb":
            miss = not sgdb.key()
            if miss:
                self.button("a_key", (pad, y, self.n(360), self.n(52)), "PEGAR CLAVE", self.art_paste_key, "primary", 18, pill=True)
        elif a["src"] == "tgdb":
            miss = not artsrc.tgdb_key()
            if miss:
                self.button("a_tkey", (pad, y, self.n(360), self.n(52)), "PEGAR CLAVE", self.art_tgdb_key, "primary", 18, pill=True)
        elif a["src"] == "screenscraper":
            cr = artsrc.ss_creds()
            miss = not (cr["user"] and cr["password"])
            bad = "no aceptó" in (a["err"] or "") or "DESARROLLADOR" in (a["err"] or "")
            if miss or bad:
                self.button("a_ssu", (pad, y, self.n(380), self.n(52)), "USUARIO: " + cr["user"][:18] if cr["user"] else "USUARIO", lambda: self.art_ss_field("SCREENSCRAPER_USER", "Usuario"), "primary" if (bad or not cr["user"]) else "normal", 17, pill=True, mark=bool(cr["user"]))
                self.button("a_ssp", (pad + self.n(392), y, self.n(340), self.n(52)), "CONTRASEÑA", lambda: self.art_ss_field("SCREENSCRAPER_PASSWORD", "Contraseña"), "primary" if (bad or not cr["password"]) else "normal", 17, pill=True, mark=bool(cr["password"]))
        if miss or a["src"] == "libretro":
            y += self.n(68) if miss else 0
        if a["step"] == "game":
            self.text("¿Cuál es el juego en " + {"sgdb": "SteamGridDB", "libretro": "libretro", "tgdb": "TheGamesDB", "screenscraper": "ScreenScraper"}[a["src"]] + "?", pad, self.cy(y), 24, DIM)
            y += self.n(46)
            cols = 3
            cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
            for k, g in enumerate(a["games"]):
                self.tile(f"ag:{g['id']}", (pad + (k % cols) * (cw + gap), y + (k // cols) * (self.n(120) + gap), cw, self.n(120)), g["name"], "", lambda g=g: self.art_game(g), self.tint(g["name"], 0.28, 0.4), big=24)
            y += ((len(a["games"]) + cols - 1) // cols) * (self.n(120) + gap)
            if not a["games"] and not a["busy"]:
                self.text("Sin resultados con ese nombre.", pad, self.cy(y), 22, DIM)
                y += self.n(46)
            self.button("ag_other", (pad, y, self.n(520), self.n(70)), "BUSCAR CON OTRO NOMBRE", self.art_research, "primary", 20)
            y += self.n(96)
            y = self._art_account(a, pad, y)
        else:
            if a.get("pv") is not None and a["imgs"]:
                self.draw_art_preview(a, pad, gap, y)
                self.end()
                return
            self.text(f"{a.get('gname', '')} — elige una imagen de cada tipo (LB/RB cambia el tipo)", pad, self.cy(y), 21, DIM, maxw=self.W - 2 * pad)
            y += self.n(46)
            x = pad
            for kd, (_, _, lab) in sgdb.KINDS.items():
                w = self.font(19, True).size(lab)[0] + self.n(70)
                self.button(f"ak:{kd}", (x, y, w, self.n(52)), lab, lambda kd=kd: self.art_kind(kd), "chipsel" if a["kind"] == kd else "normal", 19, pill=True, mark=kd in a["picked"])
                x += w + self.n(10)
            y += self.n(76)
            cols = {"banner": 3, "hero": 3, "logo": 3, "portrait": 5, "icon": 6}[a["kind"]]
            cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
            ratio = {"portrait": 1.5, "banner": 0.47, "hero": 0.32, "icon": 1.0, "logo": 0.4}[a["kind"]]
            ch = int(cw * max(ratio, 0.3))
            if not a["imgs"] and not a["busy"]:
                self.text("No hay imágenes de este tipo para ese juego.", pad, self.cy(y), 22, DIM)
            for k, img in enumerate(a["imgs"]):
                r, foc = self.reg(f"ai:{img['id']}", (pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + gap), cw, ch), lambda k=k: self.art_preview(k))
                self.rr(r, PANEL2 if foc else PANEL, 18)
                sf = a["surf"].get(img["id"])
                if sf is None and a["raw"].get(img["id"]):
                    try:
                        sf = a["surf"][img["id"]] = pygame.image.load(io.BytesIO(a["raw"][img["id"]])).convert()
                    except pygame.error:
                        sf = a["surf"][img["id"]] = False
                if sf:
                    fw, fh = sf.get_size()
                    kf = min((r.w - self.n(16)) / fw, (r.h - self.n(16)) / fh)
                    sc = pygame.transform.smoothscale(sf, (max(1, int(fw * kf)), max(1, int(fh * kf))))
                    self.screen.blit(sc, sc.get_rect(center=r.center))
                elif img["id"] in a["raw"] and not a["raw"][img["id"]]:
                    self.text("sin miniatura (A para ver)", r.centerx, r.centery, 18, WARN, anchor="c")
                elif sf is None:
                    self.text("…", r.centerx, r.centery, 26, DIM, anchor="c")
                if a["picked"].get(a["kind"]) == img["id"]:
                    self.rr(r, OK, 18, max(3, self.n(4)))
                if foc:
                    self.glow(r)
                    self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 22, max(3, self.n(3)))
            y += ((len(a["imgs"]) + cols - 1) // cols) * (ch + gap)
            y = self._art_account(a, pad, y + self.n(30))
        self.end()

    def _art_account(self, a, pad, y):
        """Panel «CUENTA Y CONEXIÓN» al final de la pantalla de arte: estado de la clave, cambiarla (con confirmación) y probar la conexión."""
        src = a["src"]
        host = {"sgdb": "www.steamgriddb.com", "libretro": "thumbnails.libretro.com", "tgdb": "api.thegamesdb.net", "screenscraper": "www.screenscraper.fr"}[src]
        have = {"sgdb": bool(sgdb.key()), "tgdb": bool(artsrc.tgdb_key()), "libretro": True, "screenscraper": all(artsrc.ss_creds().values())}[src]
        r = pygame.Rect(pad, self.cy(y), self.W - 2 * pad, self.n(150))
        self.rr(r, PANEL, 20)
        self.text("CUENTA Y CONEXIÓN", r.x + self.n(24), r.y + self.n(20), 16, DIM, True)
        self.text(("Sin cuenta: libretro no pide clave." if src == "libretro" else ("Clave guardada ✓" if have else "Falta la clave: pégala arriba.")) + "   Servidor: " + host,
                  r.x + self.n(24), r.y + self.n(52), 18, OK if have else WARN, False, r.w - self.n(48))
        bw = self.n(340)
        by = y + self.n(84)
        bx = pad + self.n(24)
        if src != "libretro" and have:
            fn = {"sgdb": self.art_paste_key, "tgdb": self.art_tgdb_key, "screenscraper": lambda: self.art_ss_field("SCREENSCRAPER_USER", "Usuario")}[src]
            self.button("a_chg", (bx, by, bw, self.n(52)), "CAMBIAR CLAVE…" if src != "screenscraper" else "CAMBIAR CUENTA…",
                        lambda: self.confirm("¿Cambiar la clave?", "La clave actual se reemplazará por la que pegues a continuación. La anterior queda guardada como copia por si te equivocas.", fn), "ghost", 16, pill=True)
            bx += bw + self.n(14)
        self.button("a_net", (bx, by, bw, self.n(52)), "PROBAR CONEXIÓN", lambda: self.art_net_test(host), "normal", 16, pill=True)
        return y + self.n(170)

    def art_net_test(self, host):
        def done(lines, err):
            msg = "\n".join(lines) if lines else f"No pude probar: {err}"
            msg += "\n\nSi falla el TCP o el TLS con la VPN: prueba otro servidor/país. Si solo falla IPv6, Hub ya reintenta por IPv4 solo."
            self.modal = {"kind": "choice", "title": "Prueba de conexión", "prev": None, "msg": msg, "options": [("CERRAR", lambda: None)]}
            self.focus = None
        self.work("Probando la conexión con " + host + "…", lambda: nethttp.diagnose(host, "/api/v2/" if "steamgriddb" in host else "/"), done)

    def toggle_libcwd(self, e):
        lid = self.inst(e)["launcher_id"]
        st = gamecfg.state(lid)
        if not st["exists"]:
            self.toast("El juego no está registrado en el launcher")
            return
        try:
            if st["libcwd"]:
                gamecfg.set_libcwd(lid, "", False)
                self.toast("El selector de archivos vuelve a abrirse donde antes")
                return
            lk = library.link_get(e["id"])
            if not lk:
                self.toast("Primero elige/reconoce el archivo del juego: así sé cuál es tu carpeta de la biblioteca")
                return
            gamecfg.set_libcwd(lid, str(Path(lk).expanduser().parent), True)
            self.toast(f"El selector empezará en {Path(lk).parent}. Ojo: si el juego guarda su configuración en su carpeta de trabajo, ahora irá ahí")
        except (OSError, ValueError) as ex:
            self.toast(f"No se pudo: {ex}")

    def draw_launcher_panel(self, e, inf, x0, y, colw, px, inner):
        """Dos bloques: «Partidas y configuración» (dónde guarda el juego y dónde arranca) y «Steam y arte»."""
        st = gamecfg.state(inf["launcher_id"]) if inf["installed"] else {"exists": False, "portable": False, "libcwd": False}
        lk = library.link_get(e["id"])
        reg = inf["installed"] and st["exists"]

        def panel(title, lines, rows):
            nonlocal y
            lw = [(self.wrap(t, 18, inner), c) for t, c in lines]
            h = 18 + 34 + sum(len(w) * 25 for w, _ in lw) + 12 + rows * 86 + 14
            p = pygame.Rect(x0, y, colw, self.n(h))
            self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
            yy = y + self.n(18)
            self.text(title, px, self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            for w, c in lw:
                for ln in w:
                    self.text(ln, px, self.cy(yy), 18, c)
                    yy += self.n(25)
            return p, yy + self.n(12)

        p, yy = panel("PARTIDAS Y CONFIGURACIÓN", [
            ("Partidas y ajustes del juego: " + ("dentro de su carpeta (config/ y data/), se mueven con el juego" if st["portable"]
                                                  else "en ~/.config y ~/.local/share (lo normal en Linux)"), TXT if st["portable"] else DIM),
            ("El juego arranca en: " + ("tu carpeta de ROMs. Su diálogo «abrir archivo» empieza ahí, pero también guardará ahí su configuración"
                                        if st["libcwd"] else "su propia carpeta (recomendado: su configuración se queda con el juego)"), WARN if st["libcwd"] else DIM)], 2)
        self.button("sport", (px, yy, inner, self.n(72)), ("GUARDAR PARTIDAS FUERA DE LA CARPETA DEL JUEGO" if st["portable"] else "GUARDAR PARTIDAS DENTRO DE LA CARPETA DEL JUEGO"),
                    lambda: self.toggle_portable(e), size=18, enabled=reg)
        yy += self.n(86)
        self.button("scwd", (px, yy, inner, self.n(72)), ("QUE ARRANQUE EN SU CARPETA (RECOMENDADO)" if st["libcwd"] else "QUE ARRANQUE EN TU CARPETA DE ROMS"),
                    lambda: self.toggle_libcwd(e), "primary" if st["libcwd"] else "normal", 17, enabled=reg and bool(st["libcwd"] or lk))
        y = p.bottom + self.n(24)

        # v2.77: dos tarjetas con una sola idea cada una: el ARTE (qué imágenes tiene y cómo elegirlas) y STEAM (acceso y añadirlo)
        af = self.art_files(e) if inf["installed"] else {}
        names = {"icon": "icono", "portrait": "portada", "banner": "banner", "hero": "fondo", "logo": "logo"}
        have_ = [v for k, v in names.items() if k in af]
        miss_ = [v for k, v in names.items() if k not in af]
        key_ok = bool(sgdb.key())
        lines_ = [("Tiene: " + (", ".join(have_) if have_ else "ninguna imagen propia todavía") + (".  Faltan: " + ", ".join(miss_) + "." if have_ and miss_ else "."), OK if have_ else DIM),
                  ("Se guardan en " + str(Path(inf["dir"]) / "art") + ". " + ("SteamGridDB: clave guardada." if key_ok else "SteamGridDB: falta la clave (se pide al elegir arte)."), DIM)]
        p, yy = panel("ARTE DEL JUEGO", lines_, 1)
        hb = (inner - 2 * self.n(14)) // 3
        self.button("sartg", (px, yy, hb, self.n(72)), "ELEGIR ARTE", lambda: self.art_open(e), "primary", 19, enabled=reg)
        self.button("sartc", (px + hb + self.n(14), yy, hb, self.n(72)), "USAR MI IMAGEN", lambda: self.custom_art(e), size=18, enabled=reg)
        self.button("sartx", (px + 2 * (hb + self.n(14)), yy, hb, self.n(72)), "QUITAR ARTE PROPIO",
                    lambda: self.confirm("¿Quitar el arte propio?", "El juego dejará de usar estas imágenes en el launcher y en Steam. Los archivos de art/ no se borran.", lambda: self.clear_art(e)),
                    "ghost", 16, enabled=reg and st.get("art", False))
        y = p.bottom + self.n(24)
        p, yy = panel("STEAM", [("Crea el acceso (.sh) del juego y, desde el modo escritorio, añádelo a Steam con su icono y arte.", DIM)], 1)
        bw = (inner - self.n(14)) // 2
        self.button("sart", (px, yy, bw, self.n(72)), "GENERAR ACCESO (.sh)", lambda: self.steam_art(e), size=18, enabled=reg)
        self.button("sapp", (px + bw + self.n(14), yy, bw, self.n(72)), "AÑADIR A STEAM", lambda: self.steam_apply(e), size=18, enabled=reg)
        return p.bottom + self.n(24)

    def do_install(self, e, clean=None):
        rel = self.rel_for(e) or {}
        assets = rel.get("assets") or []
        wa = rel.get("win_assets") or []
        # v3.10: INSTALAR/ACTUALIZAR desde cualquier sitio (X, Inicio, menú de pulsación larga) sigue a la versión que toca: si la release
        # solo trae Windows, o en la ficha se eligió Windows, se instala la de Windows con Proton (antes: «no hay build compatible»)
        if wa and self.asset_view(e, self.inst(e), assets, wa) == "windows":
            return self.install_windows_dl(e, fresh=not self.inst(e)["installed"])
        if not assets:
            self.toast("No hay un build compatible para descargar" + (" (ni para Linux ni para Windows)" if rel.get("tag") else ""))
            return
        cur = self.inst(e)
        if clean is None and cur["installed"] and cur["version"] and rel.get("tag") and rel["tag"] != cur["version"]:
            # v2.43: cambiar de versión (sobre todo bajar a una anterior) por encima mezcla archivos viejos y nuevos; el proyecto de BT3 avisa de ello
            self.modal = {"kind": "choice", "title": f"Instalar {rel['tag']} (ahora tienes {cur['version']})", "prev": self.focus,
                          "msg": "LIMPIA (recomendada): aparta tu copia actual a «.prev», instala esta versión en una carpeta vacía y recupera de la apartada tus partidas, "
                                 "ajustes y datos (sin pisar nada de lo nuevo).\nPOR ENCIMA: actualiza los archivos del programa por etapas (si algo falla, todo vuelve a su sitio; lo reemplazado queda en .hub-replaced/) y no toca tus datos." + self._own_upd_note(cur),
                          "options": [("INSTALAR LIMPIA (guarda la actual en .prev)", lambda: self.do_install(e, True)),
                                      ("INSTALAR POR ENCIMA", lambda: self.do_install(e, False))]}
            self.focus = None
            return
        a = assets[min(self.sel_asset.get(e["id"], 0), len(assets) - 1)]
        try:
            lid0 = self.inst(e)["launcher_id"]
            st0 = self.os_state(lid0)
            if st0.get("split") and st0.get("active") == "windows":
                if not st0.get("linux"):
                    self.toast("La carpeta del juego solo tiene la versión de Windows: no instalo Linux encima")
                    return
                osver.set_active(lid0, "linux")      # el .toml apuntaba a windows/: sin esto el build de Linux se extraía ahí dentro
                self._osv.pop(lid0, None)
        except (OSError, ValueError, KeyError):
            pass
        if any(d.meta.get("install") == e["id"] and d.state in ("queued", "active", "paused") for d in self.mgr.list()):
            self.toast("Ya se está descargando")
            return
        self.mgr.add(a["url"], config.path("downloads_dir"), name=a["name"], sha256=a.get("sha256"),
                     meta={"install": e["id"], "version": rel.get("tag", ""), "asset": a["name"], "title": e["name"], "clean": bool(clean)})
        self.dl_pulse = time.time()
        self.toast("Añadida a DESCARGAS; se instalará sola al terminar")

    def _own_upd_note(self, inf) -> str:
        """Aviso si el juego trae su propio actualizador (Hub no lo toca)."""
        try:
            u = install.own_updater(Path(inf["dir"]))
        except (OSError, KeyError, TypeError):
            return ""
        return ("\nEste juego trae su propio actualizador (" + ", ".join(u[:3]) + "): Hub no lo toca.") if u else ""

    def use_hub_script(self, e):
        try:
            osver.use_hub_script(self.inst(e)["launcher_id"])
        except OSError as ex:
            self.toast(f"No pude: {ex}")
            return
        self._own_c = {}
        self.toast("Listo: ahora manda el script de Hub. Tu script anterior está en hub-run.sh.mio")

    def layout_bad(self, inf) -> str:
        """Nombre de la subcarpeta duplicada de esta instalación ('' si está bien). Se comprueba como mucho cada 8 s por carpeta."""
        d = inf.get("dir")
        if not d:
            return ""
        c = self.__dict__.setdefault("_lay_c", {})
        now = time.time()
        hit = c.get(str(d))
        if hit and now - hit[0] < 8:
            return hit[1]
        try:
            n = install.nested_dir(Path(d))
        except OSError:
            n = None
        c[str(d)] = (now, n.name if n else "")
        return c[str(d)][1]

    def repair_dir(self, e, inf):
        lid, dest = inf.get("launcher_id") or e["id"], Path(inf["dir"])

        def done(r, err):
            self._lay_c = {}
            self._inst_c = None
            if err:
                self.toast(f"No pude reparar: {err}")
            elif r.get("ok"):
                self.toast(f"Carpeta reparada: ejecutable {r['exe']}" + (" · lo reemplazado está en .hub-replaced/" if r.get("backup") else ""))
            else:
                self.toast("No hay nada que reparar" if not r.get("nested") else "Reparé la carpeta pero no encuentro el ejecutable")
        self.work("Reparando la carpeta de " + e["name"] + "…", lambda: install.repair_folder(lid, dest), done)

    def _on_done_setup(self, d, e):
        """Llega desde el hilo de la descarga: el menú se abre en el hilo de la interfaz (v3.00)."""
        d.meta["phase"] = "Instalador descargado"
        lid = d.meta.get("lid")
        self._rcp_q.append(lambda: (self.setup_menu(e, d.path, lid, auto=True), self.sfx.play("open")))

    def _on_done(self, d):
        if d.meta.get("install_setup"):
            es = self.entry(d.meta["install_setup"])
            if es:
                self._on_done_setup(d, es)
            return
        if d.meta.get("install_win"):
            ew = self.entry(d.meta["install_win"])
            if ew:
                self._on_done_win(d, ew)
            return
        eid = d.meta.get("install")
        e = self.entry(eid) if eid else None
        if not e:
            return
        d.meta["phase"] = "Instalando…"
        try:
            res = install.install(e, d.path, d.meta.get("asset", ""), d.meta.get("version", ""), clean=bool(d.meta.get("clean")))
            d.meta["phase"] = "Instalado" + ("" if res["exe"] else " (sin ejecutable detectado: revisa el .toml)")
            d.meta["result"] = res
            if res.get("repaired"):
                print(f"[instalar] {e['id']}: la versión nueva cambió de ejecutable ({res['repaired']} → {res['exe']}); .toml del launcher corregido", file=sys.stderr, flush=True)
            self._inst_c = None
            lk = library.link_get(e["id"])
            if lk:
                library.place(e, lk, res["dir"])
                library.place_rom(e, lk)
                if self.cfg.get("link_in_project", True):
                    library.place_default(e, lk, res["dir"])
                self._inst_c = None
                self._auto_libcwd(e)
            up = res.get("update") or {}
            extra = (f" · {up['replaced']} archivos reemplazados (copia en .hub-replaced)" if up.get("replaced") else "") + (f" · {len(up['skipped'])} respetados" if up.get("skipped") else "")
            history.record(res.get("launcher_id") or self.inst(e)["launcher_id"], "actualizar" if up else "instalar", True, d.meta.get("version", ""), version=d.meta.get("version", ""))
            self.toast(f"{e['name']}: instalado" + extra + (f" · tu copia anterior está en {Path(res['backup']).name} ({res['restored']} archivos recuperados)" if res.get("backup") else ""))
        except Exception as ex:  # noqa: BLE001
            d.meta["phase"] = f"Error al instalar: {type(ex).__name__}: {ex}"
            print(f"[instalar] {e['id']} {d.meta.get('version', '')}: FALLÓ ({type(ex).__name__}: {ex}); archivo {d.path}", file=sys.stderr, flush=True)
            history.record(e.get("launcher_id") or e["id"], "instalar", False, f"{type(ex).__name__}: {ex}", version=d.meta.get("version", ""))
            self.toast(f"Falló la instalación ({type(ex).__name__}): {ex}")

    # ── buscar repos dentro de la app / añadir por tarjeta ──
    def _whoami(self):
        try:
            self.gh_login = ghapi.user()
            auth.set_login(self.gh_login)
        except ghapi.GitHubError:
            pass

    def _clip_watcher(self):
        warned = False
        last = None
        while self.running:
            # cada lectura lanza un proceso (wl-paste/xclip) que Steam cuenta como parte del juego: solo con Hub delante y cada 2,5 s
            if not self.modal and not self.rview and getattr(self, "win_focus", True):
                try:
                    txt = self.clipboard()
                    if txt != last:
                        last = txt
                        r = catalog.repo_of(txt)
                        au = catalog.asset_url(txt)
                        if au:
                            self.clip_url = au
                            print(f"[clip] enlace de descarga en el portapapeles: {au}", file=sys.stderr, flush=True)
                            self.toast("Enlace de descarga copiado — pulsa DESCARGAR CON HUB")
                        elif r:
                            self.clip_seen = self.clip_repo = r
                            print(f"[clip] repo detectado en el portapapeles: {r}", file=sys.stderr, flush=True)
                            self.toast(f"Repo copiado: {r} — usa el botón verde de abajo para analizarlo")
                        elif self.clip_seen:
                            self.clip_seen = ""   # cambió el contenido: si vuelves a copiar el mismo repo, avisa otra vez
                except Exception as ex:  # noqa: BLE001
                    if not warned:
                        warned = True
                        print(f"[clip] no pude leer el portapapeles: {ex}", file=sys.stderr, flush=True)
            time.sleep(2.5)

    def add_url(self, url, title=""):
        """Descarga una URL directa con el gestor de Hub, en data/downloads. Si es de un repo del catálogo, se instala sola."""
        url = (url or "").strip()
        if not re.fullmatch(r"https?://\S+", url):
            self.toast("Eso no es una dirección http(s)")
            return
        name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]) or "descarga"
        meta = {"title": title or name, "asset": name}
        repo = catalog.repo_of(url) if "github.com" in url else ""
        e = next((x for x in self.entries if repo and (x.get("repo") or "").lower() == repo.lower()), None)
        if e:
            meta.update({"install": e["id"], "title": e["name"], "version": ""})
        self.clip_url = ""
        self.mgr.add(url, config.path("downloads_dir"), name=name, meta=meta)
        self.toast("Descarga añadida" + (f" · se instalará como {e['name']}" if e else f" · irá a {self.cfg['downloads_dir']}"))
        self.go_tab("downloads")

    def add_url_osk(self):
        self.osk("Dirección de descarga (pegar enlace directo)", self.add_url, self.clip_url or "", "p. ej. enlace de un release de GitHub")

    def run_search(self, q=None):
        if q is not None:
            self.sq = q.strip()
        if not self.sq:
            return
        self.sbusy, self.serr = True, ""
        qq = f"{self.sq} {self.ssuf}".strip()

        def job():
            try:
                self.sres = ghapi.search(qq)
            except ghapi.GitHubError as ex:
                self.sres, self.serr = [], str(ex)
            finally:
                self.sbusy = False
        threading.Thread(target=job, daemon=True).start()

    def open_repo(self, full):
        rv = {"repo": full, "loading": True, "info": None, "readme": "", "rel": None, "err": "", "name": self.sq or full.split("/")[1],
              "platform": "", "folder": re.sub(r"[^\w.-]+", "", full.split("/")[1]) or catalog.slug(full)}
        self.rview, self.clip_repo = rv, ""
        self.views.setdefault("repo", View()).off = 0
        self.focus = None

        def job():
            try:
                rv["info"] = ghapi.repo_info(full)
                rv["platform"] = catalog.platform_from_tags(rv["info"]["topics"]) or (self.entries and "")
                rv["readme"] = ghapi.readme(full)
                rv["hints"] = roms.hints_from_text(ghapi.readme_raw(full) + "\n" + (rv["info"].get("description") or ""))
                rv["rel"] = github.latest(full, self.cfg.get("arch", "x86_64"))
                if not self.sq:
                    rv["name"] = rv["info"]["name"]
            except ghapi.GitHubError as ex:
                rv["err"] = str(ex)
            finally:
                rv["loading"] = False
        threading.Thread(target=job, daemon=True).start()

    def repo_dupes(self):
        rv = self.rview
        return catalog.find_dupes(rv["repo"], rv["name"], self.entries, install.launcher_games())

    def _new_id(self, base):
        ids, n, cand = {e["id"] for e in self.entries}, 2, base
        while cand in ids:
            cand, n = f"{base}-{n}", n + 1
        return cand

    def add_from_repo(self, variant_of=None, label=""):
        rv, info = self.rview, self.rview["info"] or {}
        name, folder = rv["name"].strip() or rv["repo"], rv["folder"]
        entry = {"name": name, "repo": rv["repo"], "folder": folder, "platform": rv["platform"], "tags": info.get("topics", []),
                 "notes": info.get("description", "")}
        hints = {k: v for k, v in (rv.get("hints") or {}).items() if v}
        if hints:
            entry["requires"] = roms.merge_requires({}, hints)
        if variant_of:
            name = f"{variant_of.get('group') or variant_of['name'].split(' — ')[0]} — {label}"
            entry.update(name=name, folder=f"{variant_of['folder']}-{catalog.slug(label)}", variant=True, platform=variant_of.get("platform", ""))
        if variant_of and not variant_of.get("variant"):
            # la tarjeta original pasa a ser también una variante (si no, el catálogo la fusionaría con la nueva)
            catalog.add_local({"id": variant_of["id"], "name": variant_of["name"], "repo": variant_of["repo"], "folder": variant_of["folder"],
                               "platform": variant_of.get("platform", ""), "variant": True, "group": variant_of["name"]})
        entry["id"] = self._new_id(catalog.slug(entry["folder"]))
        e = catalog.add_local(entry)
        self.reload()
        self.rview, self.tab = None, "games"
        ne = self.entry(e["id"])
        self.toast(f"Tarjeta creada: {name}")
        if ne:
            self.open_detail(ne)

    def ask_variant(self, base):
        self.osk("Etiqueta de la variante (p. ej. Latino, ISO modificada)", lambda t: t.strip() and self.add_from_repo(base, t.strip()), "")

    # ── sesión de GitHub ──
    def gh_login_flow(self):
        cid = (self.cfg.get("github_client_id") or "").strip()
        if not cid:
            self.osk("Client ID de tu OAuth App de GitHub (Device Flow activado)", self._save_client_id, "", "se crea en github.com/settings/developers")
            return

        def job():
            try:
                dev = ghapi.device_start(cid)
            except ghapi.GitHubError as ex:
                self.toast(f"No se pudo iniciar sesión: {ex}")
                return
            self.device = {"code": dev["user_code"], "url": dev.get("verification_uri", "https://github.com/login/device"), "cancel": False}
            self.modal = {"kind": "device", "prev": self.focus}
            self.focus = None
            try:
                tok = ghapi.device_poll(cid, dev, stop=lambda: self.device is None or self.device["cancel"])
                auth.save(tok, "", "device")
                self.modal, self.device = None, None
                self._whoami()
                self.toast(f"Sesión iniciada en GitHub{(' como ' + self.gh_login) if self.gh_login else ''}")
            except (ghapi.GitHubError, OSError) as ex:
                if self.modal and self.modal.get("kind") == "device":
                    self.modal = None
                self.device = None
                self.toast(f"Inicio de sesión: {ex}")
        threading.Thread(target=job, daemon=True).start()

    def gh_check(self):
        self.toast("Consultando tu cuota de GitHub…")

        def job():
            try:
                self.toast(ghapi.rate_limit())
            except ghapi.GitHubError as ex:
                self.toast(f"GitHub: {ex}")
        threading.Thread(target=job, daemon=True).start()

    def toggle_stick(self):
        self.cfg["stick_nav"] = not self.cfg.get("stick_nav", True)
        config.save_settings(self.cfg)
        self.stick.clear()
        self.held.clear()
        self.toast("Stick izquierdo: " + ("activado" if self.cfg["stick_nav"] else "desactivado (usa la cruceta)"))

    def _last_update_txt(self):
        return self.memo(("upd_txt", _fsig(config.STATE / "update.json")), self._last_update_txt_read, 30.0)

    def _last_update_txt_read(self):
        try:
            import json
            u = json.loads((config.STATE / "update.json").read_text(encoding="utf-8"))
            return (f"  ·  actualizado {u['from']} → {u['to']} ({u['when'][:16].replace('T', ' ')})" if u.get("ok")
                    else f"  ·  último intento falló ({u.get('to')}): volvió a {u.get('from')}")
        except (OSError, ValueError, KeyError):
            return ""

    def _tests_last_txt(self):
        return self.memo(("tests_txt", _fsig(config.STATE / "tests" / "resumen.txt")), self._tests_last_txt_read, 30.0)

    def _tests_last_txt_read(self):
        try:
            return (config.STATE / "tests" / "resumen.txt").read_text(encoding="utf-8").strip() or "todavía no"
        except OSError:
            return "todavía no se han ejecutado"

    def show_tests_report(self):
        f = config.STATE / "tests" / "informe.md"
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()[-3000:]
        except OSError:
            lines = ["(todavía no hay informe: ejecuta las pruebas primero)"]

        class _L:
            title, stage, state, logfile = "Informe de pruebas", "data/tests/informe.md", "done", f
            log = collections.deque(lines, maxlen=3000)
        self.show_log(_L())

    def run_tests(self):
        exe = Path(config.__file__).resolve().parent.parent / "bin" / "hub-tests"
        if not exe.exists():
            self.toast("No encuentro bin/hub-tests (reinstala Hub)")
            return
        if any(b.state in ("queued", "running") and getattr(b, "label", "") == "PRUEBAS" for b in self.builds):
            self.toast("Las pruebas ya están en marcha")
            return
        job = cmdjob.CmdJob("PRUEBAS", "Pruebas de Hub", [("Ejecutando pruebas", [sys.executable, str(exe)])])
        self.builds.append(job)
        job.start()
        self.toast("Pruebas en marcha… mira DESCARGAS. El resultado queda en ÚLTIMO RESULTADO")

    def _look_norm(self):
        """Ajustes antiguos («dark», «aurora»…) → tema + paleta de ahora; deja cfg con nombres válidos."""
        n0 = self.cfg.get("theme", "dark")
        if hubthemes.studio.is_studio(n0):                    # v2.97: identidad del Estudio
            nm, pal, lay = hubthemes.studio.normalize(n0, (self.cfg.get("pals") or {}).get(n0), (self.cfg.get("layouts") or {}).get(n0))
            self.cfg.setdefault("pals", {})[nm] = pal
            self.cfg.setdefault("layouts", {})[nm] = lay
            return
        fam, pal = themes_fam.normalize(n0, (self.cfg.get("pals") or {}).get(themes_fam.normalize(n0)[0]))
        self.cfg["theme"] = fam
        self.cfg.setdefault("pals", {})[fam] = pal

    def _a11y(self):
        """v3.09: opciones de accesibilidad de Ajustes (para todos los temas). Todas apagadas = los temas se ven como siempre."""
        return a11ymod.flags(self.__dict__.get("cfg"))

    def reduced_motion(self):
        return bool((self.__dict__.get("cfg") or {}).get("reduce_motion"))

    def fx_level(self):
        """2 = calidad alta («glass»), 1 = equilibrada, 0 = rendimiento."""
        return a11ymod.fx_level((self.__dict__.get("cfg") or {}).get("fx", "glass"))

    def _pal(self):
        return self.cfg["pals"][self.cfg["theme"]]

    def _bg(self):
        return (self.cfg.get("bgs") or {}).get(self.cfg["theme"])

    def _layout(self):
        return (self.cfg.get("layouts") or {}).get(self.cfg["theme"])

    def _fam(self, name=None):
        """Familia (heredada) o identidad del Estudio con la misma forma: label, desc, pals, bgs."""
        name = name or self.cfg.get("theme")
        return hubthemes.studio.family(name) if hubthemes.studio.is_studio(name) else themes_fam.FAMILIES[themes_fam.normalize(name)[0]]

    def _ar_load_last(self):
        """Última petición de apariencia ya confirmada (está en appearance.json). Se lee una vez, ANTES de reescribir ese archivo."""
        if "_ar_last" not in self.__dict__:
            try:
                self._ar_last = (json.loads((config.DATA / "appearance.json").read_text(encoding="utf-8")) or {}).get("request")
            except Exception:  # noqa: BLE001
                self._ar_last = None
        return self._ar_last

    def _publish_look(self, request=None):
        """v2.90/v2.91: el motor de temas publica la apariencia activa en data/appearance.json. Un fallo se anota en el log (no corta la interfaz).
        v2.96: conserva la confirmación de la última petición (si no, al arrancar se perdía y la petición vieja se volvía a aplicar)."""
        if not chan.is_active():
            return                                  # v3.15: la apariencia que leen el lanzador y el QAM la publica solo el canal activo
        self._ar_load_last()
        try:
            from .themes import publish
            publish.publish(config.DATA / "appearance.json", self.cfg.get("theme", "dark"), self._pal(), self._bg(),
                            request or self.__dict__.get("_ar_last"), layout=self._layout(), quality=self.cfg.get("fx", "glass"), a11y=a11ymod.flags(self.cfg))
        except Exception as ex:  # noqa: BLE001
            print(f"[apariencia] no se pudo publicar appearance.json: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)

    def poll_appearance_request(self, force=False):
        """v2.91: recoge data/appearance-request.json (máx. 1 vez por segundo), la valida, aplica los cambios y publica el resultado."""
        now = time.time()
        if not force and now - self.__dict__.get("_ar_t", 0) < 1.0:
            return None
        self._ar_t = now
        if not chan.is_active():
            return None                             # v3.15: las peticiones de apariencia las atiende solo el canal activo
        from .themes import appearance_request as ar
        path = config.DATA / "appearance-request.json"
        try:
            mt = path.stat().st_mtime
        except OSError:
            return None
        if mt == self.__dict__.get("_ar_mt"):
            return None
        self._ar_mt = mt
        req = ar.read(path)
        rid = req.get("request_id") if isinstance(req, dict) else None
        last = self._ar_load_last() or {}
        if rid and rid == last.get("id"):
            res = {"id": rid, "status": "duplicate", "errors": []}
        else:
            cur = (self.cfg.get("theme", "dark"), self._pal(), self._bg())
            if isinstance(req, tuple):
                ok, errs, ch = False, ["JSON ilegible: " + req[1]], {}
            else:
                ok, errs, ch = ar.validate(req, cur)
            res = {"id": rid or "?", "status": "applied" if ok else "rejected", "errors": errs}
            if ok:
                self.set_look(ch.get("theme"), pal=ch.get("palette"), bg=ch.get("background"), layout=ch.get("layout"))
            else:
                print(f"[apariencia] petición {rid!r} rechazada: {'; '.join(errs)}", file=sys.stderr, flush=True)
        if res["status"] != "duplicate":
            self._ar_last = res
        self._publish_look(self.__dict__.get("_ar_last"))
        return res

    def set_look(self, theme=None, fx=None, pal=None, bg=None, layout=None):
        """Tema, paleta, fondo y efectos (cristal/rendimiento). Invalida todas las cachés que dependen de los colores."""
        if theme:
            if theme in themes_fam.LEGACY and theme not in themes_fam.FAMILIES:      # nombre antiguo («dark», «aurora»): trae su propia paleta
                theme, pal = themes_fam.LEGACY[theme]
            self.cfg["theme"] = theme
        self._look_norm()
        studio_ = hubthemes.studio.is_studio(self.cfg["theme"])
        if pal:
            self.cfg["pals"][self.cfg["theme"]] = (hubthemes.studio.normalize(self.cfg["theme"], pal)[1] if studio_
                                                   else themes_fam.normalize(self.cfg["theme"], pal)[1])
            self.cfg.setdefault("bgs", {}).pop(self.cfg["theme"], None)      # cada paleta trae su fondo; se elige otro después
        if bg:
            self.cfg.setdefault("bgs", {})[self.cfg["theme"]] = bg
        if layout and studio_:
            self.cfg.setdefault("layouts", {})[self.cfg["theme"]] = hubthemes.studio.normalize(self.cfg["theme"], None, layout)[2]
        if fx:
            self.cfg["fx"] = fx
        config.save_settings(self.cfg)
        apply_theme(self.cfg["theme"], self._pal(), self._bg(), self._layout(), self._a11y())
        self._publish_look()
        self.k = self.k0 * SCALE
        if hasattr(self, "sfx"):
            self.sfx.set_profile(SND)
        fam = FONT_FAMS.get(FONT) or FONT_FAMS[None]
        self._font_path = pygame.font.match_font(fam) or pygame.font.match_font(FONT_FAMS[None]) or None
        self._font_bold = pygame.font.match_font(fam, bold=True) or self._font_path
        self._font_fat = False
        self._font_medium = None if FONT == "vt323" else (fonts.medium_path(FONT) if FONT in fonts.MEDIUM else self._sys_medium(fam))
        if FONT in fonts.DL:                      # tipografía del tema: de data/fonts si ya se bajó; si no, se pide y se sigue con la del sistema
            fp = fonts.paths(FONT)
            if fp:
                self._font_path, self._font_bold, self._font_fat = fp
                tried = self.__dict__.setdefault("_med_tried", set())
                if FONT in fonts.MEDIUM and not self._font_medium and FONT not in tried and not os.environ.get("HUB_NO_FONT_DL"):
                    want = FONT
                    tried.add(want)                   # una vez por sesión: sin red no se reintenta en cada cambio de tema                   # v3.09: quien ya tenía la fuente baja ahora su Medium, sin aviso (nada cambia hasta que se use)
                    fonts.ensure(want, lambda ok: self._rcp_q.append(
                        lambda: setattr(self, "_font_medium", fonts.medium_path(want)) if FONT == want else None))
            elif not os.environ.get("HUB_NO_FONT_DL"):
                want = FONT
                fonts.ensure(want, lambda ok: self._rcp_q.append(lambda: (self.set_look(), self.toast("Tipografía del tema descargada")) if ok and FONT == want else None))
        self._fonts, self._glyph_ok = {}, {}
        self._amb, self._gl_c, self._tc, self._gr_c, self._ring_c, self._gly_c, self._disc_c, self._corner_c = None, {}, {}, {}, {}, {}, {}, {}
        self._aa_c, self._aa_bytes = {}, 0
        for k in ("_vis_c",):
            if hasattr(self, k):
                delattr(self, k)
        if self.modal:
            self.modal.pop("_bd", None)
        for v in getattr(self, "views", {}).values():
            if hasattr(v, "cache"):
                v.cache = None

    def resize(self, w, h):
        """Cambia el tamaño de la ventana en caliente (pruebas a 1280×720 / 1920×1080 del Ally) y recalcula escala y cachés."""
        self.screen = pygame.display.set_mode((w, h))
        self.W, self.H = w, h
        self.k0 = max(0.7, min(1.6, h / 1080.0)) * float(os.environ.get("HUB_FONT_SCALE", "1"))
        self.k = self.k0 * SCALE
        self._fonts, self._glyph_ok, self._tc = {}, {}, {}
        self.set_look()

    def pick_theme(self, nm):
        """Aplica un tema concreto (cuadrícula de Ajustes) con un fundido desde lo que había en pantalla."""
        if nm == self.cfg.get("theme") or (nm not in THEME_ORDER and nm not in STUDIO_ORDER):
            return
        self._xfade_start()
        self.set_look(theme=nm)
        self.toast(f"Tema: {THEME_LABEL[nm].partition(' (')[0].lower()} · {self._pal_label()}")

    def _pal_label(self):
        return next((p[1] for p in self._fam(FAMILY)["pals"] if p[0] == PAL), PAL).lower()

    def pick_layout(self, lay):
        """v2.97: forma de Inicio de una identidad del Estudio (solo las que declara compatibles)."""
        if lay == STUDIO_LAYOUT:
            return
        self._xfade_start()
        self.set_look(layout=lay)
        self.toast("Inicio: " + hubthemes.studio.LAYOUT_LABEL.get(lay, lay).lower())

    def pick_pal(self, pid):
        if pid == PAL:
            return
        self._xfade_start()
        self.set_look(pal=pid)
        self.toast(f"Paleta: {self._pal_label()}")

    def pick_bg(self, bid):
        if bid == (ANIM or "none"):
            return
        self.set_look(bg=bid)
        self.toast("Fondo: " + themes_fam.ANIM_LABEL.get(bid, bid).lower())

    def toggle_theme(self, step=1):
        """Tema siguiente (step=1) o anterior (step=-1); da la vuelta por los dos lados."""
        self._xfade_start()
        cur = themes_fam.normalize(self.cfg.get("theme", "dark"))[0]     # desde el Estudio (prueba) se vuelve a los temas heredados
        self.set_look(theme=THEME_ORDER[(THEME_ORDER.index(cur) + step) % len(THEME_ORDER)])
        i = THEME_ORDER.index(self.cfg["theme"])
        self.toast(f"Tema {i + 1} de {len(THEME_ORDER)}: " + THEME_LABEL[self.cfg["theme"]].partition(" (")[0].lower() + " · " + self._pal_label())

    def toggle_fx(self):
        self.set_look(fx=a11ymod.next_fx(self.cfg.get("fx", "glass")))      # v3.09: alta → equilibrada → rendimiento
        self.toast("Efectos: " + FX_LABEL[self.cfg["fx"]])

    A11Y_NAME = {"reduce_motion": "Movimiento reducido", "high_contrast": "Alto contraste", "large_text": "Texto grande"}

    def toggle_a11y(self, k):
        """v3.09: opciones de accesibilidad (todos los temas). Se guardan y se vuelve a aplicar el tema con ellas."""
        self.cfg[k] = not self.cfg.get(k, False)
        if self.cfg[k] and k == "reduce_motion":
            for a in ("_xfade", "_bursts"):
                self.__dict__.pop(a, None)
        self.set_look()
        self.toast(f"{self.A11Y_NAME.get(k, k)}: " + ("sí" if self.cfg[k] else "no"))

    def toggle_adv(self):
        self.adv_open = not self.adv_open
        self.cfg["adv_open"] = self.adv_open
        config.save_settings(self.cfg)

    def toggle_autoupdate(self):
        self.cfg["auto_update"] = not self.cfg.get("auto_update", True)
        config.save_settings(self.cfg)
        self.toast("Actualizar al abrir Hub: " + ("sí" if self.cfg["auto_update"] else "no"))

    def channel_txt(self):
        me, act = config.CHANNEL, chan.active()
        other = "dev" if me == "stable" else "stable"
        txt = f"esta copia es {chan.LABEL[me]} {config.VERSION} · activa: {chan.LABEL.get(act, '?')}"
        if act != me:
            return txt + " · TOCAR PARA ACTIVAR ESTA"
        return txt + (f" · TOCAR PARA ACTIVAR {chan.LABEL[other].upper()}" if chan.installed(other) else f" ({chan.LABEL[other]} no instalada)")

    def switch_channel(self):
        """v3.15: elige qué copia gestiona lo compartido (atajos de Steam, apariencia). Si esta pasa a activa, ajusta los atajos ya."""
        me, act = config.CHANNEL, chan.active()
        if not me:
            return
        want = me if act != me else ("dev" if me == "stable" else "stable")
        if want != me and not chan.installed(want):
            self.toast(f"{chan.LABEL[want]} no está instalada en {chan.copy_dir(want)}")
            return

        def do():
            self.modal = None
            chan.set_active(want)
            self.memo_clear()
            n = 0
            if want == me:
                try:
                    n = directplay.apply_all(self.cfg.get("direct_play", True))
                except OSError as ex:
                    print(f"[arranque directo] {ex}", file=sys.stderr, flush=True)
                self._publish_look()
            print(f"[canal] canal activo: {chan.LABEL[want]}", file=sys.stderr, flush=True)
            self.toast(f"Canal activo: {chan.LABEL[want]}" + (f" ({n} atajos de Steam ajustados)" if n else
                       "" if want == me else ". Abre esa copia para que ajuste los atajos de los juegos"))
        self.modal = {"kind": "choice", "title": f"¿Activar {chan.LABEL[want]}?", "prev": None,
                      "msg": f"La copia {chan.LABEL[want]} pasará a gestionar los atajos de los juegos en Steam y la apariencia del QAM. "
                             "La biblioteca es la misma; cada copia guarda sus propios ajustes.",
                      "options": [(f"ACTIVAR {chan.LABEL[want].upper()}", do), ("CANCELAR", lambda: setattr(self, "modal", None))]}
        self.focus = None

    def update_hub(self):
        """Ajustes → ACTUALIZAR HUB: si hay un zip nuevo lo instala y reinicia; si no, lo dice."""
        if config.CHANNEL == "stable":
            self.toast("La versión estable se actualiza desde el QAM: Apps › Forgeinator 3000 (releases de GitHub)")
            return
        if self.upd_ready:
            self.upd_now()
            return
        self.toast("Buscando zip nuevo…")

        def job():
            self.upd_check()
            self.toast(f"Hay una actualización: {self.upd_ready['ver']}. Toca el aviso de abajo" if self.upd_ready
                       else f"Hub {config.VERSION} está al día (no hay zip más nuevo en ~/Games/actualizaciones)")
        threading.Thread(target=job, daemon=True).start()

    def _covers_txt(self):
        b = getattr(self, "_cvb", None)
        if b and b.get("busy"):
            return f"descargando {b['i']}/{b['n']}…"
        # se pinta en cada fotograma de Ajustes: se calcula como mucho cada 5 s (antes ~9700 stat por fotograma = scroll a 8 fps)
        now, c = time.time(), getattr(self, "_cvt", None)
        if not c or now - c[0] > 5 or c[2] != len(self.entries):
            todo = covers.missing(self.entries)
            c = self._cvt = (now, len(todo), len(self.entries), covers.recent_misses(todo))
        st = getattr(self, "_cvb", None)
        if st and st.get("busy"):
            return f"descargando {st['i']} de {st['n']}…"
        sin = c[3]
        return f"faltan {c[1]} de {c[2]}" + (f" ({sin} sin carátula en ninguna fuente: se reintentan cada {covers.RETRY_DAYS} días)" if sin else "")

    def covers_batch(self):
        """v3.20: SteamGridDB (con clave) y libretro (sin clave, juegos de consola), 4 a la vez; los que no existen en ninguna fuente
        no se vuelven a pedir hasta pasados covers.RETRY_DAYS días. Si solo quedan esos, este botón los reintenta."""
        if getattr(self, "_cvb", None) and self._cvb.get("busy"):
            return
        nuevos = covers.missing(self.entries, include_misses=False)
        retry = not nuevos
        st = self._cvb = {"busy": True, "i": 0, "n": len(covers.missing(self.entries)) if retry else len(nuevos)}
        if not sgdb.key():
            self.toast("Sin clave de SteamGridDB: solo libretro (juegos de consola). La clave se pega en Ajustes › Imágenes")

        def prog(i, n, name):
            st["i"], st["n"] = i, n

        def job():
            t0 = time.time()
            r = covers.batch(self.entries, prog, retry_misses=retry)
            st["busy"] = False
            self._cvt = None
            self._cov = {}
            print(f"[carátulas] {r['ok']} nuevas, {r['sin']} sin resultado, {r['error']} con error, {r['omitidos']} omitidas "
                  f"(sin resultado hace poco) en {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
            self.toast(f"Carátulas: {r['ok']} nuevas, {r['sin']} sin resultado, {r['error']} con error")
        threading.Thread(target=job, daemon=True).start()
        self.toast("Reintentando las que no se encontraron…" if retry else "Descargando carátulas en segundo plano…")

    def show_buildlog(self):
        s = buildlog.stats()
        ls = [buildlog.summary(), ""]
        for t, k in (("Herramientas", "tools"), ("Contenedores", "containers"), ("Hilos (-j)", "jobs"), ("Errores frecuentes", "fails")):
            ls.append(t + ": " + (", ".join(f"{a} ×{b}" for a, b in s[k]) or "—"))

        class _L:
            title, stage, state, logfile = "Compilaciones", "data/buildlog.jsonl", "done", config.DATA / "buildlog.jsonl"
            log = collections.deque(ls, maxlen=400)
        self.show_log(_L())

    def run_doctor(self):
        def job():
            txt = doctor.report()

            class _L:
                title, stage, state, logfile = "Doctor", "comprobaciones", "done", config.STATE / "doctor.txt"
                log = collections.deque(txt.splitlines(), maxlen=400)
            try:
                _L.logfile.write_text(txt + "\n", encoding="utf-8")
            except OSError:
                pass
            self._doctor_l = _L
        self._doctor_l = None
        threading.Thread(target=job, daemon=True).start()
        self.toast("Comprobando…")

    def show_hublog(self):
        f = config.STATE / "hub.log"
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
        except OSError:
            lines = ["(todavía no hay hub.log: arranca Hub con bin/hub para que se genere)"]
        lines = ["ERROR " + x if re.search(r"\bERROR\b|Traceback|\[gh\].*HTTP [45]", x) and not x.startswith("ERROR") else x for x in lines]

        class _L:
            title, stage, state, logfile = "Registro de Hub", "hub.log (últimas líneas)", "done", f
            log = collections.deque(lines, maxlen=400)
        self.show_log(_L())

    def _save_client_id(self, t):
        self.cfg["github_client_id"] = t.strip()
        config.save_settings(self.cfg)
        self.toast("Client ID guardado. Pulsa de nuevo INICIAR SESIÓN")

    def gh_paste_token(self):
        def save(t):
            t = t.strip()
            if not t:
                return
            try:
                auth.save(t, "", "token")
            except OSError as ex:
                self.toast(f"No pude guardar el token: {ex}")
                return

            def chk():
                try:
                    self.gh_login = ghapi.user()
                    auth.set_login(self.gh_login)
                    self.toast(f"Token guardado. Sesión como {self.gh_login}")
                except (ghapi.GitHubError, OSError) as ex:
                    auth.clear()
                    self.gh_login = ""
                    self.toast(f"Token no válido, no se guardó: {ex}")
            threading.Thread(target=chk, daemon=True).start()
        self.osk("Token de acceso de GitHub (PEGAR)", save, "", "se guarda en data/credentials.json (permisos 600)")

    def gh_logout(self):
        def go():
            auth.clear()
            self.gh_login = ""
            self.toast("Sesión cerrada: credenciales guardadas borradas")
        self.confirm("¿Cerrar sesión de GitHub?", "Se borra el token guardado por Hub (data/credentials.json). Tu cuenta de GitHub no cambia.", go)

    # ── navegador / repositorio manual ──
    @staticmethod
    def search_name(e):
        n = e.get("group") or e["name"]
        return re.sub(r"\s*[\(\[][^)\]]*[\)\]]", "", n).split(" — ")[0].strip() or n

    def open_url(self, url):
        """Abre el navegador elegido en AJUSTES (auto = el de Steam dentro de Big Picture, si no el del sistema). Con un navegador propio, al cerrarlo vuelve a Hub."""
        mode = self.cfg.get("browser", "auto")
        self.brow_t = time.time()
        if mode == "hub":
            return self._open_hub_browser(url)
        if mode == "minitube":   # ajuste antiguo (v1.90–v2.10): ya no existe ese navegador
            mode = self.cfg["browser"] = "auto"
            config.save_settings(self.cfg)
        if mode == "auto" and self._hb_ok is True and os.environ.get("SteamGameId"):   # en Big Picture, el navegador táctil de Hub si está instalado
            return self._open_hub_browser(url)
        cmds = []
        if mode not in ("auto", "steam", "system") and mode.strip():
            import shlex
            parts = shlex.split(mode)
            cmds.append([x.replace("{url}", url) for x in parts] + ([] if any("{url}" in x for x in parts) else [url]))
        in_steam = bool(os.environ.get("SteamGameId") or os.environ.get("GAMESCOPE_WAYLAND_DISPLAY"))
        if mode == "steam" or (mode == "auto" and in_steam):
            cmds.append(["steam", "-ifrunning", "steam://openurl/" + url])
        cmds.append(["xdg-open", url])
        for c in cmds:
            try:
                pr = subprocess.Popen(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[navegador] {c[0]} -> {url}", file=sys.stderr, flush=True)
                self.toast(f"Abriendo navegador: {url}")
                if mode not in ("auto", "steam", "system") and c is cmds[0]:
                    self.brow_proc = pr
                    threading.Thread(target=self._browser_wait, args=(pr,), daemon=True).start()
                return
            except OSError:
                continue
        self.toast(f"No hay navegador disponible. Dirección: {url}")

    def _open_url_fallback(self, url):
        in_steam = bool(os.environ.get("SteamGameId") or os.environ.get("GAMESCOPE_WAYLAND_DISPLAY"))
        for c in (["steam", "-ifrunning", "steam://openurl/" + url] if in_steam else None, ["xdg-open", url]):
            if not c:
                continue
            try:
                subprocess.Popen(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
        self.toast(f"No hay navegador disponible. Dirección: {url}")

    def hb_ready(self):
        if self._hb_ok is None:
            self._hb_ok = hubbrowser.ready()
        return self._hb_ok

    def install_hub_browser(self, ask=True):
        if any(getattr(b, "label", "") == "NAVEGADOR DE HUB" and b.state in ("queued", "running") for b in self.builds):
            self.toast("Ya se está instalando (mira DESCARGAS)")
            return

        def go():
            job = hubbrowser.SetupJob()
            self.builds.append(job)
            job.start(lambda ok: (setattr(self, "_hb_ok", None), self.toast("Navegador de Hub " + ("instalado" if ok else "no se pudo instalar: mira DESCARGAS → REGISTRO"))))
            self.go_tab("downloads")
        if not ask:
            return go()
        self.confirm("¿Instalar el navegador de Hub?", "Descarga PyQt6 + Qt WebEngine (~150 MB, ocupa ~550 MB en data/). Tiene pantalla completa, desplazamiento táctil, teclado de Steam, zoom y descargas que van directas a Hub. Puedes seguir usando Hub mientras se instala.", go)

    def _open_hub_browser(self, url):
        if self.hb_opening and time.time() - self.hb_opening < 90:
            self.toast("Ya se está abriendo el navegador de Hub…")
            return
        if self._hb_ok is False:
            self.install_hub_browser()
            return
        self.hb_opening = time.time()
        self.toast("Abriendo el navegador de Hub… (la primera vez tarda unos segundos)")

        def job():
            try:
                if not self.hb_ready():
                    self.hb_opening = 0
                    self.install_hub_browser()
                    return
                t0 = time.time()
                lvl = int(self.cfg.get("browser_level", 0))
                self.hb_fatal = False
                pr = subprocess.Popen(hubbrowser.command(url, UI.zoom), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=hubbrowser.env(lvl), start_new_session=True)
                threading.Thread(target=self._hub_browser_err, args=(pr,), daemon=True).start()
                threading.Thread(target=self._hub_browser_watchdog, args=(pr,), daemon=True).start()
                print(f"[navegador] hub -> {url}  (compatibilidad gráfica: {hubbrowser.LEVELS[min(lvl, 2)][0]})", file=sys.stderr, flush=True)
                self.brow_proc = pr
                self._hub_browser_reader(pr, t0, url, lvl)
            except OSError as ex:
                self.toast(f"No pude abrir el navegador de Hub: {ex}")
            finally:
                self.hb_opening = 0
        threading.Thread(target=job, daemon=True).start()

    def _hub_browser_watchdog(self, pr):
        """Si la ventana no está lista en READY_TIMEOUT s (p. ej. se queda esperando a Vulkan/GPU en Gamescope), se corta y se reintenta en el nivel siguiente."""
        t = time.time()
        while time.time() - t < hubbrowser.READY_TIMEOUT:
            if pr.poll() is not None or not self.hb_opening:
                return
            time.sleep(0.5)
        if pr.poll() is None and self.hb_opening:
            print(f"[navegador] la ventana no estuvo lista en {hubbrowser.READY_TIMEOUT}s: lo cierro y reintento", file=sys.stderr, flush=True)
            self.hb_fatal = True
            try:
                os.killpg(pr.pid, 9)
            except OSError:
                pass

    def _hub_browser_err(self, pr):
        """Copia el stderr del navegador al registro y, si Chromium declara un error FATAL de sandbox/zygote (se quedaba ~60 s colgado antes de morir), lo corta y reintenta ya."""
        for ln in pr.stderr:
            print(ln.rstrip(), file=sys.stderr, flush=True)
            if "FATAL" in ln and ("zygote" in ln or "sandbox" in ln.lower()):
                self.hb_fatal = True
                print("[navegador] error fatal de Chromium (sandbox): lo cierro y reintento", file=sys.stderr, flush=True)
                try:
                    os.killpg(pr.pid, 9)
                except OSError:
                    pass

    def _hub_browser_reader(self, pr, t0=0, url="", lvl=0):
        repo = ""
        for ln in pr.stdout:
            ln = ln.strip()
            if ln == "HUB ready":
                self.hb_opening = 0
                print(f"[navegador] navegador de Hub listo en {time.time() - t0:.1f}s", file=sys.stderr, flush=True)
            if ln.startswith("HUB repo "):
                repo = ln[9:].strip()
            elif ln.startswith("HUB done "):
                self.toast("Descargado: " + Path(ln[9:].strip()).name)
            print(f"[navegador] {ln}", file=sys.stderr, flush=True)
        pr.wait()
        try:   # que no quede ningún proceso de Chromium vivo
            os.killpg(pr.pid, 9)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        dur = time.time() - t0
        print(f"[navegador] el navegador de Hub terminó (código {pr.returncode}) tras {dur:.0f}s", file=sys.stderr, flush=True)
        if (self.hb_fatal or (pr.returncode in (-4, -5, -6, -7, -11) and dur < 60)) and lvl < len(hubbrowser.LEVELS) - 1:
            # se colgó (señal): reintenta con otro nivel de compatibilidad y lo recuerda
            self.cfg["browser_level"] = lvl + 1
            config.save_settings(self.cfg)
            print(f"[navegador] se colgó; reintento en nivel «{hubbrowser.LEVELS[lvl + 1][0]}»", file=sys.stderr, flush=True)
            self.toast(f"El navegador se colgó: reintentando en modo «{hubbrowser.LEVELS[lvl + 1][0].lower()}»")
            self.hb_opening = 0
            self.want_front = False
            return self._open_hub_browser(url or "https://www.google.com")
        self.hb_repo = repo
        if self.cfg.get("return_to_hub", True):
            self.want_front = True

    def _browser_wait(self, pr):
        try:
            pr.wait()
        except Exception:  # noqa: BLE001
            return
        if self.cfg.get("return_to_hub", True):
            self.want_front = True
            print("[navegador] cerrado: volviendo a Hub", file=sys.stderr, flush=True)

    def bring_to_front(self):
        """Vuelve a Hub: lo más fiable disponible, anotado en hub.log. (En Steam/Gamescope no hay garantía: depende de la versión de Steam.)
        Solo si Hub abrió un navegador en la última media hora: sin eso, tocar la ventana (restaurar/activar) al arrancar dejaba el logo de Steam girando."""
        if self.game_pids or time.time() - self.brow_t > 1800:
            print("[volver] omitido: Hub no abrió ningún navegador recientemente", file=sys.stderr, flush=True)
            return
        steps = []
        try:
            w = pygame.Window.from_display_module()
            w.restore()
            w.focus()
            steps.append("pygame")
        except Exception as ex:  # noqa: BLE001
            steps.append(f"pygame falló ({type(ex).__name__})")
        if shutil.which("xdotool"):
            subprocess.Popen(["xdotool", "search", "--pid", str(os.getpid()), "windowactivate"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            steps.append("xdotool")
        gid = os.environ.get("SteamGameId")
        if gid and shutil.which("steam") and self.cfg.get("steam_resume", False):   # desactivado: Steam responde «game is already running»
            subprocess.Popen(["steam", "-ifrunning", f"steam://rungameid/{gid}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            steps.append("steam rungameid")
        print("[volver] " + ", ".join(steps), file=sys.stderr, flush=True)

    # ── actualización de Hub desde zip ──
    def _upd_loop(self, every=60.0):
        for _ in range(8):                       # no compite con el arranque de la ventana
            if not self.running:
                return
            time.sleep(0.25)
        while self.running:
            self.upd_check()
            self._upd_first.set()
            for _ in range(int(every * 4)):
                if not self.running:
                    return
                time.sleep(0.25)

    def upd_check(self):
        if self.upd_busy:
            return
        d = selfupdate.probe()
        self.upd_ready = {"ver": d["new"], "file": d.get("file")} if d.get("new") else None

    def upd_now(self):
        """Un toque: instala el zip pendiente y reinicia Hub con el código nuevo."""
        if self.upd_busy or not self.upd_ready:
            return
        ver = self.upd_ready["ver"]
        self.upd_busy = f"Instalando {ver}…"

        def job():
            ok, out = selfupdate.apply()
            if ok:
                self.upd_busy = f"Listo: reiniciando con la versión {ver}…"
                selfupdate.restart()
                time.sleep(0.6)
                self.running = False
            else:
                last = [ln for ln in out.splitlines() if ln.strip()][-1:] or ["sin detalle"]
                self.upd_busy = ""
                self.toast("No se pudo actualizar: " + last[0][:140] + "  (Hub sigue como estaba)")
                print("[actualizar] falló:\n" + out, file=sys.stderr, flush=True)
        threading.Thread(target=job, daemon=True).start()

    def draw_updbanner(self):
        if (not self.upd_ready and not self.upd_busy) or self.modal or self.rview:
            return
        w, h = min(self.W - self.n(80), self.n(1100)), self.n(76)
        x, y = (self.W - w) // 2, self.H - self.n(self.FH) - h - self.n(24)
        if self.upd_busy:
            r = pygame.Rect(x, y, w, h)
            self.rr(r, PANEL2, 16)
            self.rr(r, ACC, 16, 2)
            self.text(self.upd_busy + "." * (int(self.t * 2) % 4), r.centerx, r.centery, 24, TXT, True, anchor="c")
            return
        self.button("updgo", (x, y, w, h), f"ACTUALIZACIÓN {self.upd_ready['ver']} LISTA  ·  TOCA PARA INSTALAR Y REINICIAR ›", self.upd_now, "primary", 22)

    # ── descargas del navegador ──
    def _dl_loop(self):
        while self.running:
            try:
                for kind, val in self.dlw.poll():
                    if kind == "start":
                        self.toast(f"Descarga detectada: {val.name}  (en {val.parent})")
                        print(f"[descarga] inicio: {val}", file=sys.stderr, flush=True)
                        if self.cfg.get("return_to_hub", True) and not (self.brow_proc and self.brow_proc.poll() is None and self.cfg.get("browser") == "hub"):
                            self.want_front = True
                    else:
                        print(f"[descarga] terminada: {val}", file=sys.stderr, flush=True)
                        self.dl_done = {"path": val, "t": time.time()}
                        self.recv_scan()
                        self.toast(f"Descarga terminada: {val.name}")
                        e = self.entry(self.detail) if self.detail else None
                        if e and not self.watch:
                            self.detected[e["id"]] = str(val)
                        if self.cfg.get("return_to_hub", True):
                            self.want_front = True
            except Exception as ex:  # noqa: BLE001
                print(f"[descarga] error: {ex}", file=sys.stderr, flush=True)
            time.sleep(1.0)

    # ── archivos recibidos por un navegador: descomprimir, mover, enlazar con un juego, guardar en la biblioteca ──
    def recv_scan(self):
        if self.recv_busy:
            return
        self.recv_busy = True

        def job():
            try:
                ext_root = config.BROWSER_DL.parent / "extraido"
                dirs = [config.BROWSER_DL] + [Path(x) for x in self.cfg.get("watch_dirs", [])]
                if ext_root.is_dir():
                    dirs += [d for d in ext_root.iterdir() if d.is_dir()]
                self.recv = received.scan(dirs, exclude=[config.path("downloads_dir")])
            except Exception as ex:  # noqa: BLE001
                print(f"[recibidos] error: {ex}", file=sys.stderr, flush=True)
            finally:
                self.recv_busy = False
        threading.Thread(target=job, daemon=True).start()

    def recv_open(self, r):
        p = Path(r["path"])
        inside = str(p.resolve()).startswith(str(config.BROWSER_DL.parent.resolve()) + os.sep)
        mem = received.members(p)
        sysg = received.guess_systems(p)
        msg = f"{p}\n{fmt_size(r['size'])}" + (f"\nDentro: {', '.join(mem[:3])}" if mem else "") + (f"\nParece de: {', '.join(sysg)}" if sysg else "")
        opts = [("ENLAZAR CON UN JUEGO DEL CATÁLOGO…", lambda: self.recv_link(p))]
        if sysg:
            opts.append((f"GUARDAR EN MI BIBLIOTECA ({sysg[0]})…", lambda: self.recv_store(p, sysg)))
        if p.suffix.lower() in received.ARCH:
            opts.append(("DESCOMPRIMIR (carpeta «extraido» del proyecto)", lambda: self.recv_unpack(p)))
        if not inside:
            opts.append(("MOVER A LA CARPETA DE DESCARGAS DEL PROYECTO", lambda: self.recv_move(p)))
        self.modal = {"kind": "choice", "title": p.name, "msg": msg, "prev": None, "options": opts}
        self.focus = None

    def recv_bg(self, work, ok_msg):
        def job():
            try:
                self.toast(ok_msg(work()))
            except Exception as ex:  # noqa: BLE001
                print(f"[recibidos] error: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
                self.toast(f"No se pudo: {ex}")
            self.recv_busy = False
            self.recv_scan()
        threading.Thread(target=job, daemon=True).start()

    def recv_unpack(self, p):
        self.toast(f"Descomprimiendo {p.name}…")
        self.recv_bg(lambda: received.unpack(p, config.BROWSER_DL.parent / "extraido"), lambda d: f"Descomprimido en {d}")

    def recv_move(self, p):
        self.recv_bg(lambda: received.move(p, config.BROWSER_DL), lambda d: f"Movido a {d}")

    def recv_link(self, p):
        cands = received.suggest(self.entries, p)
        opts = [(f"{e['name']}  ({e.get('platform', '')})", lambda e=e: self.recv_use(e, p)) for e in cands]
        opts.append(("NINGUNO: elegir el juego yo en la pestaña JUEGOS", lambda: (self.go_tab("games"), self.toast("Abre el juego y usa ELEGIR ARCHIVO"))))
        self.modal = {"kind": "choice", "title": "¿A qué juego pertenece?", "msg": p.name + ("" if cands else "\nNo encuentro un juego con ese nombre en el catálogo."),
                      "prev": None, "options": opts}
        self.focus = None

    def recv_use(self, e, p):
        self.open_detail(e)
        self.tab = "games"
        self.check_file(e, p)

    def recv_store(self, p, systems):
        roots = self.roms_roots()
        if not roots:
            self.toast("No encuentro tu carpeta de ROMs (AJUSTES → CARPETA DE ROMS)")
            return
        opts = []
        for sy in systems[:2]:
            if not esde.accepts(sy, p.suffix) and p.suffix.lower() in received.ARCH:
                continue
            for mode, lab in (("copy", "COPIAR"), ("move", "MOVER")):
                opts.append((f"{lab} A {sy}", lambda sy=sy, mode=mode: self.recv_bg(
                    lambda: (esde.store(p, sy, roots[0], mode), setattr(self, "lib_loaded", False))[0], lambda d: f"Guardado en {d.parent}")))
        if not opts:
            self.toast("ES-DE no acepta ese formato comprimido para esa plataforma: descomprime primero")
            return
        self.modal = {"kind": "choice", "title": "Guardar en tu biblioteca (ES-DE)", "msg": f"{p.name}\nRaíz: {roots[0]}", "prev": None, "options": opts}
        self.focus = None

    def draw_dlbanner(self):
        if self.tab == "downloads" and not self.detail:
            return
        a = list(self.dlw.active.values())
        if not a and not (self.dl_done and time.time() - self.dl_done["t"] < 60):
            return
        w, h = min(self.W - self.n(80), self.n(900)), self.n(64)
        x, y = self.W - w - self.n(24), self.n(self.HH) + self.n(10)
        if a:
            r = pygame.Rect(x, y, w, h)
            self.rr(r, (30, 60, 100), 14)
            t = a[0]
            self.text(f"DESCARGANDO: {t['name']}", r.x + self.n(18), r.y + self.n(8), 20, TXT, True, r.w - self.n(36))
            self.text(f"{fmt_size(t['size'])}  ·  {fmt_size(t['speed'])}/s  ·  {t['path'].parent}" + (f"  (+{len(a) - 1} más)" if len(a) > 1 else ""), r.x + self.n(18), r.y + self.n(34), 17, DIM, maxw=r.w - self.n(110))
            self.button("dlign", (r.right - self.n(92), r.y + self.n(8), self.n(84), self.n(48)), "IGNORAR", lambda t=t: (self.dlw.ignored.add(t["path"]), self.dlw.active.pop(t["path"], None)), size=14, focus=False)
            ph = (time.time() * 0.8) % 1.0
            bw = int(r.w * 0.25)
            pygame.draw.rect(self.screen, ACC, (r.x + int((r.w - bw) * ph), r.bottom - self.n(5), bw, self.n(4)), border_radius=2)
        else:
            d = self.dl_done["path"]
            self.button("dlbanner", (x, y, w - self.n(70), h), f"DESCARGA TERMINADA: {d.name}  —  VER ›", lambda: (self.go_tab("downloads"), setattr(self, "dl_done", None)), "ok", 19)
            self.button("dlbannerx", (x + w - self.n(62), y, self.n(62), h), "×", lambda: setattr(self, "dl_done", None), size=26)

    def browser_menu(self):
        cur = self.cfg.get("browser", "auto")
        self.modal = {"kind": "choice", "title": "Navegador para abrir enlaces", "prev": None, "msg":
                      f"Actual: {cur}\nAUTOMÁTICO: en Big Picture el de Hub si está instalado; si no el de Steam o el del sistema.\nNAVEGADOR PROPIO (p. ej. firefox): ventana aparte; al cerrarla Hub vuelve solo y sirve su bloqueo de pop-ups.",
                      "options": [("NAVEGADOR DE HUB (Qt)", self._pick_hub_browser), ("FIREFOX", lambda: self._preset_browser("firefox")), ("MICROSOFT EDGE", lambda: self._preset_browser("edge")),
                                  ("AUTOMÁTICO", lambda: self._set_browser("auto")), ("NAVEGADOR DE STEAM", lambda: self._set_browser("steam")),
                                  ("NAVEGADOR DEL SISTEMA (xdg-open)", lambda: self._set_browser("system")),
                                  ("COMANDO PROPIO…", lambda: self.osk("Comando del navegador ({url} = dirección)", self._set_browser, cur if cur not in ("auto", "steam", "system") else "firefox {url}",
                                                                       "ej.: firefox {url}  ·  flatpak run org.mozilla.firefox {url}  ·  chromium --app={url}"))]}
        self.focus = None

    BROWSERS = {"firefox": ("Firefox", "org.mozilla.firefox", ["firefox"]),
                "edge": ("Microsoft Edge", "com.microsoft.Edge", ["microsoft-edge-stable", "microsoft-edge"])}

    zoom = 1.5

    def toggle_hblevel(self):
        self.cfg["browser_level"] = (int(self.cfg.get("browser_level", 0)) + 1) % len(hubbrowser.LEVELS)
        config.save_settings(self.cfg)
        self.toast("Navegador de Hub: " + hubbrowser.LEVELS[self.cfg["browser_level"]][0])

    def toggle_zoom(self):
        z = [1.0, 1.25, 1.5, 1.75, 2.0]
        UI.zoom = z[(z.index(UI.zoom) + 1) % len(z)] if UI.zoom in z else 1.5
        self.cfg["browser_zoom"] = UI.zoom
        config.save_settings(self.cfg)
        self.toast(f"Zoom del navegador: {UI.zoom}")
        if "com.microsoft.Edge" in self.cfg.get("browser", "") or "microsoft-edge" in self.cfg.get("browser", ""):
            self._preset_browser("edge")
        self.toast(f"Zoom del navegador (Edge): {UI.zoom}")

    @classmethod
    def find_browser(cls, key):
        """Comando listo para usar ('... {url}') si el navegador está instalado (Flatpak o nativo), o ''."""
        _, fid, bins = cls.BROWSERS[key]
        z = cls.zoom
        # Edge (Chromium): pantalla completa (evita el 4:3), zoom de interfaz y eventos táctiles. Firefox: entrada táctil XInput2.
        extra = ("--env=MOZ_USE_XINPUT2=1", "") if key == "firefox" else ("", f"--start-fullscreen --force-device-scale-factor={z} --touch-events=enabled")
        try:
            if shutil.which("flatpak") and subprocess.run(["flatpak", "info", fid], capture_output=True, timeout=10).returncode == 0:
                return f"flatpak run {extra[0]} {fid} {extra[1]} {{url}}".replace("  ", " ")
        except (OSError, subprocess.SubprocessError):
            pass
        for b in bins:
            if shutil.which(b):
                return f"{b} {extra[1]} {{url}}".replace("  ", " ")
        return ""

    def _pick_hub_browser(self):
        self._set_browser("hub")
        if not self.hb_ready():
            self.install_hub_browser()

    def _preset_browser(self, key):
        name, fid, _ = self.BROWSERS[key]
        cmd = self.find_browser(key)
        if not cmd:
            self.toast(f"No encuentro {name}. Instálalo (Discover o: flatpak install flathub {fid}) y vuelve a elegirlo")
            print(f"[navegador] {name} no instalado", file=sys.stderr, flush=True)
            return
        print(f"[navegador] {name}: {cmd}", file=sys.stderr, flush=True)
        self._set_browser(cmd)

    def _set_browser(self, v):
        self.cfg["browser"] = (v or "auto").strip() or "auto"
        config.save_settings(self.cfg)
        self.toast("Navegador: " + self.cfg["browser"])

    def toggle_return(self):
        self.cfg["return_to_hub"] = not self.cfg.get("return_to_hub", True)
        config.save_settings(self.cfg)
        self.toast("Volver a Hub al empezar/terminar una descarga: " + ("sí" if self.cfg["return_to_hub"] else "no"))

    def search_google(self, text):
        q = urllib.parse.quote_plus(f"{text} recomp github".strip())
        self.open_url(f"https://www.google.com/search?q={q}")

    def search_github(self, e):
        q = urllib.parse.quote_plus(self.search_name(e) + " recomp")
        self.open_url(f"https://github.com/search?q={q}&type=repositories")

    def set_repo(self, e, text):
        repo = catalog.repo_of(text)
        if not repo:
            self.toast("Eso no parece un repositorio (usa owner/repo o la URL de GitHub)")
            return
        catalog.add_local({"id": e["id"], "name": e["name"], "repo": repo, "folder": e.get("folder", e["id"]), "platform": e.get("platform", "")})
        self.reload()
        self.rel.pop(repo + "|" + (e.get("asset_filter") or ""), None)
        self.toast(f"Repositorio de «{e['name']}»: {repo}")
        ne = self.entry(e["id"])
        ne and self.fetch(ne)

    def add_game_flow(self):
        """Ajustes → añadir juego: pide el nombre, abre la búsqueda en GitHub y luego pide el repositorio elegido."""
        def got_name(name):
            name = name.strip()
            if not name:
                return
            tmp = {"id": catalog.slug(name), "name": name, "folder": re.sub(r"[^\w.-]+", "", name) or catalog.slug(name), "platform": ""}
            self.search_github(tmp)

            def got_repo(txt):
                repo = catalog.repo_of(txt)
                if not repo:
                    self.toast("Eso no parece un repositorio (owner/repo o URL de GitHub)")
                    return
                catalog.add_local({"name": name, "repo": repo, "folder": tmp["folder"]})
                self.reload()
                self.toast(f"Añadido «{name}» ({repo})")
            self.pending_osk = ("Pega o escribe el repositorio elegido (owner/repo o URL)", got_repo, "", "ej.: z3xox/Tenkaichi3Decomp")
        self.osk("¿Qué juego quieres buscar? (se abrirá GitHub con «nombre recomp»)", got_name, "")

    # ── compilar desde el código ──
    def start_build(self, e):
        if any(b.entry["id"] == e["id"] and b.state in ("queued", "running") for b in self.builds):
            self.toast("Ya se está compilando")
            return
        cont = self.container_name_for(e, self.inst(e)["launcher_id"])      # v2.80: el de ESTE juego (antes siempre el global)
        if cont and not build.distrobox_ok():
            self.toast("No encuentro distrobox. Quita el contenedor en AJUSTES para compilar en el sistema")
            return
        if cont and self.ctr_ok(cont) is False:
            self.confirm("El contenedor no existe", f"«{cont}» no existe en este equipo, así que la compilación fallaría. ¿Elegir o crear otro ahora?", lambda: self.pick_container(e))
            return
        cmd = (e.get("build") or {}).get("cmd", "")
        job = build.BuildJob(e, cont, cmd, int(self.cfg.get("build_jobs", 4)))
        self.builds.append(job)
        job.start()
        self.toast("Compilando… sigue el progreso en DESCARGAS")

    def build_plan(self, e):
        """Lee las instrucciones del repo (README/BUILDING), arma un plan editable y lo enseña ANTES de ejecutar nada."""
        if e["id"] in self._planning:
            return
        self._planning.add(e["id"])
        self.toast("Leyendo las instrucciones de compilación del repo…")

        def job():
            try:
                dest = config.GAMES_DIR / e.get("folder", e["id"])
                plan = buildplan.plan_for(e, dest, ghapi.get, self.cfg.get("build_container", "fedora"))
            except Exception as ex:  # noqa: BLE001
                plan = None
                print(f"[plan] {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            finally:
                self._planning.discard(e["id"])
            if not plan:
                self.toast("No encontré instrucciones de compilación en el repo. Usa EDITAR COMANDO o PORT A LINUX")
                return
            cmd = buildplan.to_cmd(plan)
            self.modal = {"kind": "choice", "title": "Plan de compilación (revísalo)", "prev": None,
                          "msg": buildplan.describe(plan) + "\n\nSe ejecuta dentro del contenedor, parando en el primer error.",
                          "options": [("COMPILAR CON ESTE PLAN", lambda: self._plan_run(e, cmd)),
                                      ("EDITAR LOS COMANDOS…", lambda: self._plan_edit(e, buildplan.to_oneline(plan))),
                                      ("CERRAR", lambda: None)]}
            self.focus = None
        threading.Thread(target=job, daemon=True).start()

    def _plan_save(self, e, cmd):
        catalog.add_local({"id": e["id"], "name": e["name"], "repo": e["repo"], "folder": e.get("folder", e["id"]), "platform": e.get("platform", ""),
                           "build": {"cmd": cmd}})
        self.reload()

    def _plan_run(self, e, cmd):
        self._plan_save(e, cmd)
        self.start_build(self.entry(e["id"]) or e)

    def _plan_edit(self, e, cmd):
        def got(t):
            self._plan_run(e, t.strip()) if t.strip() else None
        self.osk("Comandos encadenados con && ($REPO = carpeta del repo, $JOBS = hilos)", got, cmd)

    def start_port(self, e, mode):
        if any(b.entry["id"] == e["id"] and b.state in ("queued", "running") and getattr(b, "label", "") == "PORT A LINUX" for b in self.builds):
            self.toast("Ya hay un port en marcha para este juego")
            return
        cont = self.cfg.get("build_container", "fedora")
        if cont and not build.distrobox_ok():
            self.toast("No encuentro distrobox. Quita el contenedor en AJUSTES para usar el sistema")
            return
        if mode == "agent" and not shutil.which("claude"):
            self.toast("Falta Claude Code (`claude`). Usa INFORME + COPIAR PROMPT con tu chat de Claude Pro")
            return
        job = port.PortJob(e, cont, mode, self.cfg)
        self.builds.append(job)
        job.start()
        self.toast("Preparando informe de port… sigue el progreso en DESCARGAS")

    def port_run(self, e):
        self.confirm("¿Ejecutar Claude Code en local?",
                     "Trabaja en una copia aparte (data/port/…), rama linux-port, y solo puede compilar vía distrobox. "
                     "Gasta el uso de tu plan Pro (límites compartidos con claude.ai). Necesitas haber hecho login en `claude`.",
                     lambda: self.start_port(e, "agent"))

    def port_copy(self, e):
        f = port.workdir(e).parent / "PROMPT_CHAT.txt"
        try:
            txt = f.read_text(encoding="utf-8")
        except OSError:
            self.toast("Primero pulsa INFORME DE PORT")
            return
        for c in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-ib"]):
            try:
                subprocess.run(c, input=txt.encode(), timeout=5, check=True)
                self.toast("Prompt copiado: pégalo en tu chat de Claude")
                return
            except (OSError, subprocess.SubprocessError):
                continue
        self.toast(f"No hay portapapeles; el prompt está en {f}")

    def edit_build_cmd(self, e):
        cur = (e.get("build") or {}).get("cmd") or build.default_cmd(config.GAMES_DIR / e.get("folder", e["id"])) or \
            "cd '$REPO' && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j$JOBS"

        def save(t):
            catalog.add_local({"id": e["id"], "name": e["name"], "repo": e["repo"], "folder": e.get("folder", e["id"]), "platform": e.get("platform", ""),
                               "build": {"cmd": t.strip()}})
            self.reload()
            self.toast("Comando de compilación guardado")
        self.osk("Comando de compilación ($REPO = carpeta del repo, $JOBS = hilos)", save, cur)

    def set_container(self):
        """Contenedor POR DEFECTO para compilar (Ajustes de Hub): los juegos sin contenedor propio usan este. Lista real, sin teclear."""
        def show(names):
            cur = self.cfg.get("build_container", "fedora")

            def save(n):
                self.cfg["build_container"] = n
                config.save_settings(self.cfg)
                self.toast("Contenedor por defecto: " + (n or "(sistema)"))
            opts = [(("✓ " if n == cur else "") + n, (lambda n=n: save(n))) for n in names]
            opts += [(("✓ " if not cur else "") + "EL SISTEMA (compilar sin contenedor)", lambda: save("")),
                     ("ESCRIBIR OTRO NOMBRE…", lambda: self.osk("Nombre del distrobox para compilar", lambda t: save(t.strip()), cur))]
            self.modal = {"kind": "choice", "title": "Contenedor por defecto para compilar", "prev": None,
                          "msg": f"Ahora: «{cur or 'el sistema'}». Cada juego puede tener el suyo (ficha → CONTENEDOR); este es para los que no.", "options": opts}
            self.focus = None
        if not recipes.have_distrobox():
            self.toast("Falta distrobox: se compila en el sistema")
            return
        self.work("Buscando contenedores…", build.refresh_containers, lambda r, err: self._rcp_q.append(lambda: show(r or [])))

    def build_kind(self, e):
        """(clave, etiqueta, color) según lo que publica el repo; None si aún no se consultó."""
        if not e["repo"]:
            return ("norepo", "SIN REPOSITORIO", DIM)
        r = self.rel.get(self.rk(e))
        if r is None:
            return None
        if r.get("error") and not r.get("tag"):
            return None
        a = r.get("assets") or []
        if r.get("win_assets") and not any(x["class"]["os"] == "linux" for x in a):
            return ("win", "SOLO WINDOWS · PROTON", WARN)
        if a:
            return ("linux", "BUILD LINUX", OK) if a[0]["class"]["os"] == "linux" else ("generic", "BUILD (¿LINUX?)", WARN)
        if r.get("has_windows"):
            return ("win", "SOLO WINDOWS · COMPILAR", WARN)
        return ("src", "SIN BUILD · COMPILAR", WARN)

    # ── archivo aportado por el usuario ──







    # ── pestaña BIBLIOTECA: tus juegos (ES-DE: ~/Nextcloud/Emulation/roms/<plataforma>) cruzados con el catálogo ──
    def lib_load(self, rescan=False):
        rs = self.roms_roots()
        if not rs:
            self.lib_loaded, self.lib_rows = True, []
            self.lib_msg = "No encuentro tu carpeta de ROMs (estándar ES-DE: ~/Nextcloud/Emulation/roms). Pulsa CARPETA DE ROMS."
            return
        self.lib_busy, self.lib_msg = True, "Leyendo tu biblioteca…"

        def job():
            try:
                idx = [] if rescan else roms.load_index()
                if not idx:
                    idx = roms.scan(rs, lambda n: setattr(self, "lib_msg", f"Indexando tu biblioteca… {n} archivos"))
                self.rom_index = idx
                rows = roms.rows_from_index(idx)
                self.lib_msg = f"{len(rows)} juegos. Cruzando con el catálogo…"
                self.lib_rows = roms.match_catalog(rows, self.entries)
                n = sum(1 for r in self.lib_rows if r["match"])
                self.lib_msg = f"{len(self.lib_rows)} juegos en {len({r['folder'] for r in self.lib_rows})} plataformas · {n} con port en tu catálogo"
            except Exception as ex:  # noqa: BLE001
                self.lib_msg = f"Error: {ex}"
            finally:
                self.lib_busy, self.lib_loaded = False, True
        threading.Thread(target=job, daemon=True).start()

    def lib_open(self, r):
        e = self.entry(r["match"]) if r["match"] else None
        if e:
            self.open_detail(e)
            self.tab = "games"
        else:
            self.go_tab("search")
            self.run_search(r["name"])

    def lib_web(self, r):
        self.open_url(f"https://github.com/search?q={urllib.parse.quote_plus(r['name'] + ' recomp')}&type=repositories")

    def draw_library(self, body):
        self.begin("library", body)
        pad = self.n(40)
        y = self.n(18)
        self.text(self.lib_msg or "Tu biblioteca", pad, self.cy(y), 21, WARN if self.lib_busy else DIM, maxw=self.W - 2 * pad - self.n(640))
        self.button("lrescan", (self.W - pad - self.n(620), y - self.n(10), self.n(300), self.n(72)), "REINDEXAR", lambda: self.lib_load(True), size=18, enabled=not self.lib_busy)
        self.button("ldir", (self.W - pad - self.n(310), y - self.n(10), self.n(310), self.n(72)), "CARPETA DE ROMS", self.set_rom_dirs, size=18)
        y += self.n(84)
        rows = self.lib_rows
        counts = collections.Counter(r["folder"] for r in rows)
        chips = [("all", "TODOS", ""), ("match", "CON PORT", ""), ("nomatch", "SIN PORT", "")]
        x = pad
        for key, label, _ in chips:
            w = self.font(20, True).size(label)[0] + self.n(40)
            self.button(f"lm:{key}", (x, y, w, self.n(72)), label, lambda k=key: (setattr(self, "lib_mode", k), setattr(self, "lib_limit", 60)),
                        "primary" if self.lib_mode == key else "normal", 20)
            x += w + self.n(12)
        y += self.n(86)
        x = pad
        for key, label in [("", "TODAS LAS PLATAFORMAS")] + [(f, f"{f.upper()} · {c}" + ("" if esde.system_for(f) else " · sin clasificar")) for f, c in sorted(counts.items(), key=lambda kv: kv[0].lower())]:
            w = self.font(19, True).size(label)[0] + self.n(36)
            if x + w > self.W - pad:
                x, y = pad, y + self.n(84)
            self.button(f"lp:{key}", (x, y, w, self.n(72)), label, lambda k=key: (setattr(self, "lib_plat", k), setattr(self, "lib_limit", 60)),
                        "primary" if self.lib_plat == key else "normal", 19)
            x += w + self.n(10)
        y += self.n(94)
        vis = [r for r in rows if (not self.lib_plat or r["folder"] == self.lib_plat)
               and (self.lib_mode == "all" or (self.lib_mode == "match") == bool(r["match"]))]
        if not vis:
            self.text("Sin juegos con este filtro." if rows else ("" if self.lib_busy else "Biblioteca vacía."), self.W // 2, self.cy(y + self.n(50)), 22, DIM, anchor="mid")
        for r in vis[:self.lib_limit]:
            rc, foc = self.reg(f"lr:{r['path']}", (pad, y, self.W - 2 * pad, self.n(96)), lambda r=r: self.lib_open(r), x=lambda r=r: self.lib_web(r))
            if rc.colliderect(self.cur.rect):
                self.rr(rc, PANEL2 if foc else PANEL, 14)
                self.rr(rc, ACC if foc else LINE, 14, max(2, self.n(3 if foc else 1)))
                self.text(r["name"], rc.x + self.n(22), rc.y + self.n(12), 23, TXT, True, rc.w - self.n(560))
                self.text(f"{r['folder']} · {Path(r['path']).name}", rc.x + self.n(22), rc.y + self.n(52), 16, DIM, maxw=rc.w - self.n(560))
                e = self.entry(r["match"]) if r["match"] else None
                if e:
                    lab = f"Con port: {e['name']}"
                    tw = min(self.font(17, True).size(lab)[0] + self.n(28), self.n(520))
                    pr = pygame.Rect(rc.right - self.n(22) - tw, rc.y + self.n(30), tw, self.n(36))
                    self.rr(pr, BG, 18)
                    self.text(lab, pr.centerx, pr.centery, 17, OK, True, pr.w - self.n(16), "c")
                else:                                   # v2.27: sin píldora naranja en cada fila; solo una pista discreta
                    self.text("Buscar port ›", rc.right - self.n(30), rc.centery, 17, ACC if foc else DIM, False, anchor="mr")
            y += self.n(108)
        if len(vis) > self.lib_limit:
            self.button("lmore", (pad, y, self.W - 2 * pad, self.n(72)), f"MOSTRAR MÁS ({len(vis) - self.lib_limit} restantes)",
                        lambda: setattr(self, "lib_limit", self.lib_limit + 60), size=20)
            y += self.n(92)
        self.cur.nh = max(self.cur.nh, y + self.n(30))
        self.end()

    # ── tu colección existente (Nextcloud/Emulation/roms…) ──
    def roms_roots(self):
        return roms.roots(self.cfg)

    def set_rom_dirs(self):
        cur = ", ".join(self.cfg.get("rom_dirs") or [str(r) for r in self.roms_roots()])

        def save(t):
            self.cfg["rom_dirs"] = [x.strip() for x in t.split(",") if x.strip()]
            config.save_settings(self.cfg)
            self.toast("Carpetas de ROMs guardadas; se reindexarán al buscar")
            try:
                roms.INDEX.unlink()
            except OSError:
                pass
            self.lib_load(True)
        self.osk("Carpeta(s) de ROMs (separadas por coma). Subcarpeta = plataforma, p. ej. ~/Nextcloud/Emulation/roms", save, cur, "ej.: ~/Nextcloud/Emulation/roms")

    def readme_hints(self, e):
        """LEER DATOS DEL README: descarga el README, extrae región/versión/formato/serial/hashes y abre la ficha del archivo requerido."""
        self.roms_msg[e["id"]] = "Leyendo el README del repositorio…"

        def job():
            txt = ghapi.readme_raw(e["repo"])
            h = roms.hints_from_text(txt)
            try:
                catalog.add_local(dict(e, requires=roms.merge_requires(e.get("requires"), h)))
                self.reload()
            except ValueError as ex:
                self.roms_msg[e["id"]] = str(ex)
                return
            found = any(h[k] for k in ("serials", "sha1", "crc32", "md5", "formats", "region", "version"))
            self.roms_msg[e["id"]] = "" if found else "El README no es específico: lee la página del proyecto, copia el texto y pulsa PEGAR TEXTO COPIADO en la ficha."
            self.open_info(e["id"])
        threading.Thread(target=job, daemon=True).start()

    def open_info(self, eid):
        self.modal = {"kind": "info", "eid": eid, "prev": None}
        self.focus = None
        self.views.setdefault("info", View()).off = 0

    def _save_req(self, eid, **kw):
        e = self.entry(eid)
        if not e:
            return
        req = dict(e.get("requires") or {})
        for k, v in kw.items():
            if v:
                req[k] = v
            else:
                req.pop(k, None)
        catalog.add_local(dict(e, requires=req))
        self.reload()

    # ── borrar un juego: todo va a la papelera de Hub (recuperable) ──
    def delete_plan(self, e):
        """(casillas, avisos). Solo propone lo que existe y es seguro mover; nunca tus ROMs."""
        inf, items, notes = self.inst(e), [], []

        def usable(pairs):
            ok = []
            for pth, kind in pairs:
                try:
                    trash.check_path(pth, kind)
                    ok.append((Path(pth), kind))
                except trash.Unsafe as ex:
                    notes.append(f"No se toca: {ex}")
            return ok
        d = Path(inf["dir"])
        if d.is_dir():
            ok = usable([(d, "project")])
            if ok:
                items.append({"key": "dir", "label": "Carpeta del juego", "paths": ok, "checked": True, "size": None})
        lid = inf["launcher_id"]
        lp = [f for f in (config.LAUNCHER / "games" / f"{lid}.toml", config.LAUNCHER / "games" / f"{lid}.toml.new", config.LAUNCHER / "art" / lid) if f.exists()]
        ok = usable([(f, "launcher") for f in lp])
        if ok:
            items.append({"key": "launcher", "label": "Entrada del launcher y carátulas", "paths": ok, "checked": True, "size": None})
        fs = []
        for dl in self.mgr.list():
            if dl.meta.get("install") == e["id"]:
                fs += [dl.path, dl.part]
        fs += [j.path for j in self.cjobs.list() if j.entry_id == e["id"] and j.path]
        fs = [Path(f) for f in dict.fromkeys(str(f) for f in fs) if Path(f).is_file()]
        ok = usable([(f, "download") for f in fs])
        if ok:
            items.append({"key": "dl", "label": f"Archivos descargados de este juego ({len(ok)})", "paths": ok, "checked": False, "size": None})
        if catalog.is_local_only(e["id"]):
            items.append({"key": "card", "label": "Quitar la tarjeta de mi lista", "paths": [], "checked": False, "size": (0, True)})
        return items, notes

    def open_delete(self, e):
        items, notes = self.delete_plan(e)
        if not items:
            notes.append("No hay nada de este juego que borrar.")
        m = {"kind": "delete", "title": f"Borrar «{e['name']}»", "msg": "Se mueve a la papelera de Hub: puedes restaurarlo en Ajustes. Marca lo que quieres borrar.",
             "items": items, "notes": notes, "opened": time.time(), "armed": 0.0, "prev": self.focus, "eid": e["id"], "go": self._delete_game}
        self.modal, self.focus = m, "del:no"
        threading.Thread(target=self._delete_sizes, args=(m,), daemon=True).start()

    @staticmethod
    def _delete_sizes(m):
        for it in m["items"]:
            if it.get("size") is None:
                tot, done = 0, True
                for pth, _k in it["paths"]:
                    b, c = trash.size_of(pth)
                    tot, done = tot + b, done and c
                it["size"] = (tot, done)

    def _delete_game(self, m):
        e = self.entry(m["eid"])
        chosen = [it for it in m["items"] if it["checked"]]
        paths = [pk for it in chosen for pk in it["paths"]]
        card = any(it["key"] == "card" for it in chosen)
        name = e["name"] if e else m["eid"]
        self.close_modal()

        def job():
            try:
                op = trash.move_to_trash(paths, name, m["eid"]) if paths else None
            except (trash.Unsafe, OSError) as ex:
                print(f"[borrar] no se borró nada: {ex}", file=sys.stderr, flush=True)
                self.toast(f"No se borró nada: {ex}")
                return
            print(f"[borrar] {name}: {len(paths)} elementos → {op}", file=sys.stderr, flush=True)
            if card:
                catalog.remove_local(m["eid"])
                self.detail = None
            self._inst_c, self._trash_c = None, None
            self.reload()
            self.toast("Movido a la papelera de Hub. Restaurar: Ajustes → Papelera" if op else "Tarjeta quitada de tu lista")
        threading.Thread(target=job, daemon=True).start()

    def trash_ops(self):
        c = getattr(self, "_trash_c", None)
        if c is None or time.time() - c[0] > 5:
            c = self._trash_c = (time.time(), trash.list_ops() if trash.root().is_dir() else [])
        return c[1]

    def trash_restore_last(self):
        ops = self.trash_ops()
        if not ops:
            self.toast("La papelera está vacía")
            return

        def job():
            try:
                ok, skipped = trash.restore(ops[-1]["dir"])
            except (OSError, ValueError) as ex:
                self.toast(f"No se pudo restaurar: {ex}")
                return
            self._inst_c, self._trash_c = None, None
            self.toast(f"Restaurado: {ops[-1]['label']}" + (f" (no se pisó: {skipped[0]})" if skipped else ""))
        threading.Thread(target=job, daemon=True).start()

    def trash_empty_ask(self):
        ops = self.trash_ops()
        if not ops:
            self.toast("La papelera ya está vacía")
            return
        m = {"kind": "delete", "title": "Vaciar la papelera", "msg": "Esto borra de verdad lo que hay dentro y NO se puede deshacer.",
             "items": [{"key": "trash", "label": f"Papelera de Hub ({len(ops)} borrados)", "paths": [(trash.root(), "trash")], "checked": True, "size": None}],
             "notes": [], "opened": time.time(), "armed": 0.0, "prev": self.focus, "go": self._trash_empty}
        self.modal, self.focus = m, "del:no"
        threading.Thread(target=self._delete_sizes, args=(m,), daemon=True).start()

    def _trash_empty(self, m):
        self.close_modal()

        def job():
            n = trash.empty()
            self._trash_c = None
            self.toast(f"Papelera vaciada ({n})")
        threading.Thread(target=job, daemon=True).start()

    def info_edit(self, eid, key, title, hint=""):
        e = self.entry(eid)
        cur = (e.get("requires") or {}).get(key, "")
        cur = " ".join(cur) if isinstance(cur, list) else str(cur)

        def save(t):
            t = t.strip()
            self._save_req(eid, **{key: (t.split() if key == "formats" else t)})
            self.open_info(eid)
        self.osk(title, save, cur, hint)

    def info_paste(self, eid):
        txt = self.clipboard_full()
        if not txt:
            self.toast("No hay texto copiado. Selecciona y copia el texto en la página del proyecto (Ctrl+C) y vuelve")
            return
        h = roms.hints_from_text(txt)
        if not any(h[k] for k in ("serials", "sha1", "crc32", "md5", "formats", "region", "version")):
            h["snippets"] = [re.sub(r"\s+", " ", txt)[:240]]
            note = "No reconocí datos concretos; guardé el texto como nota."
        else:
            h["snippets"] = (h["snippets"] or [re.sub(r"\s+", " ", txt)[:240]])[:3]
            note = "Datos añadidos a la tarjeta."
        e = self.entry(eid)
        self._save_req(eid, **roms.merge_requires(e.get("requires"), h))
        self.toast(note)

    def info_clear(self, eid):
        e = self.entry(eid)
        keep = {k: v for k, v in (e.get("requires") or {}).items() if k in ("place", "files")}
        catalog.add_local(dict(e, requires=keep))
        self.reload()

    def rom_search(self, e):
        rs = self.roms_roots()
        if not rs:
            self.set_rom_dirs()
            return
        self.roms_msg[e["id"]] = "Indexando tu biblioteca…"

        def job():
            try:
                idx = self.rom_index or roms.load_index()
                if not idx or e["id"] not in self.rom_scanned:
                    idx = roms.scan(rs, lambda n: self.roms_msg.__setitem__(e["id"], f"Indexando tu biblioteca… {n} archivos"))
                    self.rom_index = idx
                    self.rom_scanned.add(e["id"])
                self.roms_msg[e["id"]] = f"{len(idx)} archivos indexados. Comparando…"
                res = roms.find(e, idx, cb=lambda d, t: self.roms_msg.__setitem__(e["id"], f"Comparando {d}/{t}…"))
            except Exception as ex:  # noqa: BLE001
                self.roms_msg[e["id"]] = f"Error: {ex}"
                return
            if not res:
                self.roms_msg[e["id"]] = f"{len(idx)} archivos indexados; ninguno coincide. Prueba LEER DATOS DEL README o ELEGIR ARCHIVO."
                return
            best = res[0]
            self.roms_msg[e["id"]] = f"{len(res)} candidato(s); mejor: {Path(best['path']).name} ({best['how']})"
            plain = formats.kind(best["path"]) == "plain"
            if best["strong"] and plain:
                self._accept(e, Path(best["path"]), best["how"])
            elif best["strong"]:
                self.roms_msg[e["id"]] += " · preparando…"
                self.check_file(e, Path(best["path"]))
            else:
                self.modal = {"kind": "confirm", "title": Path(best["path"]).name,
                              "msg": f"Parece ser el de tu colección ({best['how']}), pero no hay hash para verificarlo.\n{best['path']}\n¿Usarlo?",
                              "cb": (lambda: self._accept(e, Path(best["path"]), "elegido de tu biblioteca")) if plain else (lambda: self.check_file(e, Path(best["path"]))), "prev": None}
        threading.Thread(target=job, daemon=True).start()

    # ── catálogo local (daemon JSON-RPC propio) ──
    def _cat_autostart(self):
        ok, msg = catalogservice.autostart()
        print(f"[catalogo] autoarranque: {'OK' if ok else 'no'} · {msg}", file=sys.stderr, flush=True)

    def toggle_cat_autostart(self):
        self.cfg["catalog_autostart"] = not self.cfg.get("catalog_autostart", True)
        config.save_settings(self.cfg)
        self.toast("El servicio de catálogo " + ("arrancará con Hub" if self.cfg["catalog_autostart"] else "ya no arranca con Hub (se arranca al buscar)"))
        if self.cfg["catalog_autostart"]:
            threading.Thread(target=self._cat_autostart, daemon=True).start()

    def cat_err(self, ex):
        cs = catalogservice
        if isinstance(ex, cs.TokenError):
            return f"Servicio de catálogo: token no válido o ausente ({ex})"
        if isinstance(ex, cs.TransportError):
            return f"No hay conexión con tu servicio de catálogo: {ex}"
        if isinstance(ex, cs.RpcError):
            return f"El servicio respondió: {ex.message} (código {ex.code})"
        return f"Servicio de catálogo: {ex}"

    def cat_refresh_health(self):
        """Estado por fuente, en segundo plano y como mucho cada 60 s. Nunca arranca el daemon por sí solo."""
        now = time.time()
        if self.cat_hb or now - self.cat_hb_t < 60:
            return
        self.cat_hb, self.cat_hb_t = True, now

        def job():
            try:
                hl = catalogservice.health(start=False)
                if isinstance(hl, list):
                    self.cat_health = {h.get("source", "?"): h.get("status", "OK") for h in hl if isinstance(h, dict)}
            except catalogservice.CatalogError:
                pass
            finally:
                self.cat_hb = False
        threading.Thread(target=job, daemon=True).start()

    def cat_open(self, e):
        self.toast("Buscando en tu servidor…")

        def job():
            try:
                hl = catalogservice.health()
                if not isinstance(hl, list):   # result null / tipo raro: sin estado por fuente, pero se sigue buscando
                    print(f"[catalogo] health devolvió {type(hl).__name__} (se esperaba lista): {hl!r}"[:200], file=sys.stderr, flush=True)
                    hl = []
                self.cat_health = {h.get("source", "?"): h.get("status", "OK") for h in hl if isinstance(h, dict)}
                res = catalogservice.search(self.search_name(e), system=e.get("platform") or None, requires=e.get("requires") or None)
            except catalogservice.CatalogError as ex:
                print(f"[catalogo] {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
                self.toast(self.cat_err(ex))
                return
            try:
                res = sorted((r for r in res if isinstance(r, dict)), key=lambda r: -float(r.get("confidence") or 0))[:8]
            except (TypeError, ValueError) as ex:   # result null / no lista / confidence no numérica
                print(f"[catalogo] respuesta inesperada de search: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
                self.toast(f"Respuesta inesperada del servicio: {type(ex).__name__}: {ex}")
                return
            if not res:
                self.toast("Tu servidor no encontró nada con ese nombre")
                return
            opts = []
            for r in res:
                src, st = r.get("source", "?"), self.cat_health.get(r.get("source", "?"), "OK")
                lab = f"{r.get('title', '?')} · {r.get('platform', '')} · {src} · {float(r.get('confidence') or 0) * 100:.0f}%"
                if st == "DEAD":
                    opts.append(("(caída) " + lab, lambda src=src: self.toast(f"La fuente «{src}» está caída ahora mismo")))
                else:
                    opts.append((lab + ("  (aviso)" if st == "WARN" else ""), lambda r=r: self.cat_variants(e, r)))
            self.modal = {"kind": "choice", "title": "Resultados en tu servidor", "msg": f"Para: {e['name']}", "prev": None, "options": opts}
            self.focus = None
        threading.Thread(target=job, daemon=True).start()

    def cat_variants(self, e, r):
        self.toast("Consultando variantes…")

        def job():
            try:
                vs = catalogservice.variants(r["source"], r["item_id"], requires=e.get("requires") or None)
            except (catalogservice.CatalogError, TypeError, KeyError) as ex:
                print(f"[catalogo] {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
                self.toast(self.cat_err(ex) if isinstance(ex, catalogservice.CatalogError) else f"Respuesta inesperada del servicio: {type(ex).__name__}: {ex}")
                return
            if not isinstance(vs, list):
                self.toast("Respuesta inesperada del servicio: variants no devolvió una lista")
                return
            vs = [v for v in vs if isinstance(v, dict)][:60]
            if not vs:
                self.toast("Ese resultado no tiene variantes descargables")
                return
            opts = [(f"{v.get('filename', '?')} · {v.get('region', '')} · {v.get('format', '')} · {v.get('size', '')}" + ("" if v.get("resumable") else "  (sin pausa)"),
                     lambda v=v: self.cat_start(e, r, v)) for v in vs]
            self.modal = {"kind": "choice", "title": r.get("title", "Variantes"), "msg": "Elige el archivo", "prev": None, "options": opts}
            self.focus = None
        threading.Thread(target=job, daemon=True).start()

    def cat_start(self, e, r, v):
        def job():
            try:
                dest = Path(config.path("downloads_dir")).expanduser().resolve()
                dest.mkdir(parents=True, exist_ok=True)
                print(f"[catalogo] download dest_dir={dest} variante={v.get('variant_id')}", file=sys.stderr, flush=True)
                jid = catalogservice.download(r["source"], v["variant_id"], dest)["job_id"]
            except (catalogservice.CatalogError, KeyError, TypeError, OSError) as ex:
                print(f"[catalogo] download falló: {type(ex).__name__}: {ex} {getattr(ex, 'code', '')} {getattr(ex, 'data', '')}", file=sys.stderr, flush=True)
                self.toast(self.cat_err(ex) if isinstance(ex, catalogservice.CatalogError) else f"No pude crear la carpeta de descargas: {ex}" if isinstance(ex, OSError) else f"Respuesta inesperada del servicio: {ex}")
                if isinstance(ex, catalogservice.ServiceError) and "desconocid" in (ex.message or "").lower():
                    self.cat_variants(e, r)   # variant_id caducado (el daemon se reinició): regla de oro, repetir variants antes de otro download
                return
            self.cjobs.add(jid, v.get("filename") or r.get("title", "archivo"), catalogjobs.parse_size(v.get("size")), bool(v.get("resumable")), e["id"], r.get("source", ""))
            print(f"[catalogo] descarga {jid}: {v.get('filename')} desde {r.get('source')}", file=sys.stderr, flush=True)
            self.dl_pulse = time.time()
            self.toast("Descargando desde tu servidor (pestaña DESCARGAS)")
        threading.Thread(target=job, daemon=True).start()

    # ── Quiver (API pública de solo lectura: build de Linux con el SHA-256 que ellos fijaron) ──
    def quiver_open(self, e):
        self.toast("Buscando en Quiver…")

        def job():
            try:
                res = quiversrc.search(self.search_name(e))
            except quiversrc.QuiverError as ex:
                print(f"[quiver] {ex}", file=sys.stderr, flush=True)
                self.toast(f"Quiver: {ex}")
                return
            if not res:
                self.toast("Quiver no tiene nada con ese nombre para Linux")
                return
            opts = [(quiversrc.label(r), lambda r=r: self.quiver_pick(e, r)) for r in res]
            self.modal = {"kind": "choice", "title": "Resultados en Quiver", "msg": f"Para: {e['name']}", "prev": None, "options": opts}
            self.focus = None
        threading.Thread(target=job, daemon=True).start()

    def quiver_pick(self, e, r):
        self.toast("Consultando la release verificada…")

        def job():
            try:
                info = quiversrc.app(r["slug"])
                ver, files = quiversrc.assets(r["slug"])
            except quiversrc.QuiverError as ex:
                print(f"[quiver] {ex}", file=sys.stderr, flush=True)
                self.toast(f"Quiver: {ex}")
                return
            if not files:
                self.toast("Esa app no tiene un archivo para Linux x86_64 en su release verificada")
                return
            repo = (info.get("repo") or "").lower()
            if repo and e.get("repo") and repo != e["repo"].lower():
                self.confirm("El repositorio no coincide", f"Quiver: {info['repo']}\nTu tarjeta: {e['repo']}\n¿Instalar igualmente como «{e['name']}»?",
                             lambda: self.quiver_start(e, r, ver, files[0]))
                return
            self.quiver_start(e, r, ver, files[0])
        threading.Thread(target=job, daemon=True).start()

    def quiver_start(self, e, r, ver, a):
        if any(d.meta.get("install") == e["id"] and d.state in ("queued", "active") for d in self.mgr.list()):
            self.toast("Ya se está descargando")
            return
        self.mgr.add(a["url"], config.path("downloads_dir"), name=a["name"], sha256=a.get("sha256"),
                     meta={"install": e["id"], "version": ver, "asset": a["name"], "title": e["name"], "source": "quiver"})
        print(f"[quiver] {r['slug']} {ver}: {a['name']} sha256={'sí' if a.get('sha256') else 'NO'}", file=sys.stderr, flush=True)
        self.dl_pulse = time.time()
        self.toast(f"{a['name']} añadida a DESCARGAS" + ("" if a.get("sha256") else " (Quiver no fijó SHA-256 de este archivo)"))

    def _cat_wait(self, job):
        """El motor se paró esperando al usuario: aviso sonoro y mensaje; la tarjeta de DESCARGAS queda marcada."""
        msg = job.meta.get("message") or "el servicio necesita que hagas algo"
        print(f"[catalogo] {job.job_id} espera al usuario: {msg}", file=sys.stderr, flush=True)
        self.dl_pulse = time.time()
        self.toast(f"{job.name}: {msg}")
        self.sfx.play("open")

    def _cat_done(self, job):
        """El daemon terminó: mismo flujo que un archivo elegido a mano (library.match + adopt)."""
        e = self.entry(job.entry_id)
        print(f"[catalogo] completa {job.job_id}: {job.path} · " + (f"sha1={job.sha1} crc32={job.crc32}" if job.sha1 or job.crc32 else "sin hash (el servicio no lo informó)"), file=sys.stderr, flush=True)
        if not e or not job.path:
            self.toast("Descarga completa" + (f" en {job.path}" if job.path else ""))
            return
        if Path(job.path).is_dir():
            self.toast(f"El servicio devolvió una carpeta, no un archivo: {Path(job.path).name}")
            return
        if not Path(job.path).is_file():
            print(f"[catalogo] el servicio dice 'completa' pero NO existe el archivo: {job.path}", file=sys.stderr, flush=True)
            self.toast(f"El servicio terminó pero el archivo no existe: {Path(job.path).name}. Revisa el servicio (service.py)")
            return
        self.toast(f"Descargado: {Path(job.path).name}. Comprobando…")
        self.check_file(e, Path(job.path))

    def rom_dir_for(self, plat):
        """Carpeta de ROMs de esa plataforma bajo tus raíces de ROMs (p. ej. …/roms/n64); None si no existe."""
        sysn = roms.canon(plat or "")
        if not sysn:
            return None
        for r in self.roms_roots():
            try:
                for d in sorted(r.iterdir()):
                    if d.is_dir() and not d.name.startswith(".") and (d.name.lower() == sysn or roms.canon(d.name) == sysn):
                        return d
            except OSError:
                continue
        return None

    def pick_file(self, e):
        dirs = [Path(os.path.expandvars(str(d))).expanduser() for d in self.cfg["watch_dirs"]]
        start = self.rom_dir_for(e.get("platform")) or next((d for d in dirs if d.is_dir()), Path.home())
        self.open_picker("Elige tu archivo", start, None, lambda p: self.check_file(e, p), plat=e.get("platform"))

    def toggle_watch(self, e):
        if self.watch and self.watch["eid"] == e["id"]:
            self.watch = None
            self.toast("Vigilancia detenida")
        else:
            self.watch = {"eid": e["id"], "since": time.time() - 2, "seen": set()}
            self.toast("Vigilando carpetas de descargas…")

    def _watcher(self):
        while self.running:
            w = self.watch
            if w:
                e = self.entry(w["eid"])
                req = (e or {}).get("requires") or {}
                strong = bool(req.get("sha1") or req.get("crc32") or req.get("serials") or req.get("md5"))
                try:
                    for p in library.candidates(self.cfg["watch_dirs"], req, w["since"]):
                        if p in w["seen"] or not library.stable(p, 0.8):
                            continue
                        w["seen"].add(p)
                        if formats.kind(p) in ("archive", "convert"):
                            pk = formats.peek_zip(p, req) if p.suffix.lower() == ".zip" else {"ok": False}
                            if pk["ok"] or not strong or p.suffix.lower() != ".zip":
                                self.detected[e["id"]] = str(p)
                                self.toast(f"Detectado ({p.suffix.lower()}): {p.name} — pulsa USAR DETECTADO para prepararlo")
                            continue
                        if strong:
                            r = library.match(p, req)
                            if r["ok"]:
                                self._accept(e, p, r["how"])
                                self.watch = None
                                break
                        else:
                            self.detected[e["id"]] = str(p)
                            self.toast(f"Detectado: {p.name}")
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(2)

    # ── modales ──
    def use_steam_kb(self):
        k = self.cfg.get("keyboard", "auto")
        return k == "steam" or (k == "auto" and bool(os.environ.get("SteamGameId") or os.environ.get("GAMESCOPE_WAYLAND_DISPLAY")))

    def steam_kb_open(self):
        """Pide a Steam su teclado en pantalla (steam://open/keyboard). Lo que teclees llega como texto a Hub."""
        now = time.monotonic()
        if now - getattr(self, "_kb_t", -9) < 1.5:   # evita abrirlo dos veces seguidas (parpadeo de foco)
            return
        self._kb_t = now
        try:
            pygame.key.start_text_input()
        except Exception as ex:  # noqa: BLE001
            print(f"[teclado] start_text_input falló: {ex}", file=sys.stderr, flush=True)
        for cmd in (["steam", "-ifrunning", "steam://open/keyboard"], ["xdg-open", "steam://open/keyboard"]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    print(f"[teclado] {' '.join(cmd)}", file=sys.stderr, flush=True)
                    return
                except OSError as ex:
                    print(f"[teclado] {cmd[0]} falló: {ex}", file=sys.stderr, flush=True)
        self.toast("No pude abrir el teclado de Steam; usa TECLADO DE HUB")

    def _osk_log(self, m, kind, what):
        """Una línea por evento mientras hay un teclado abierto (limitada a 400 por teclado) para entender cuelgues/saltos de foco."""
        n = m["_ev"] = m.get("_ev", 0) + 1
        if n <= 400:
            print(f"[tecla] {kind} {what} · teclado={'steam' if m.get('steam') else 'hub'} · foco={self.focus} · ventana={'sí' if pygame.key.get_focused() else 'NO'}", file=sys.stderr, flush=True)

    def toggle_keyboard(self):
        cur = self.cfg.get("keyboard", "auto")
        self.cfg["keyboard"] = {"auto": "steam", "steam": "hub", "hub": "auto"}.get(cur, "auto")
        config.save_settings(self.cfg)
        self.toast("Teclado: " + {"auto": "AUTOMÁTICO (Steam dentro de Big Picture)", "steam": "STEAM", "hub": "DE HUB"}[self.cfg["keyboard"]])

    def osk(self, title, cb, text="", hint=""):
        st = self.use_steam_kb()
        self.modal = {"kind": "osk", "title": title, "text": text, "cb": cb, "shift": False, "hint": hint, "prev": self.focus, "steam": st}
        self.focus = None
        if st:
            self.steam_kb_open()

    def confirm(self, title, msg, cb):
        self.modal = {"kind": "confirm", "title": title, "msg": msg, "cb": cb, "prev": self.focus}
        self.focus = None

    def open_picker(self, title, start, exts, cb, plat=None, filt="", prev=None):
        self.modal = {"kind": "picker", "title": title, "dir": Path(start), "exts": exts, "cb": cb, "prev": prev if prev is not None else self.focus, "plat": plat, "filt": filt}
        self.focus = None
        self.views.setdefault("picker", View()).off = 0
        self._list_dir()

    def _picker_filter(self, m):
        if m.get("filt"):
            m["filt"] = ""
            self._list_dir()
            return
        d, ex, cb, plat, title = m["dir"], m["exts"], m["cb"], m.get("plat"), m["title"]
        prev = m.get("prev")

        def back(t):
            self.open_picker(title, d, ex, cb, plat=plat, filt=t.strip(), prev=prev)
        self.osk("Filtrar por nombre (parte del nombre)", back, "", "Ej.: banjo")

    @staticmethod
    def _lead(name: str) -> str:
        """Letra del índice A–Z del selector: la primera letra/cifra (sin acentos); cifras y símbolos → «#»."""
        import unicodedata
        for c in unicodedata.normalize("NFD", name).casefold():
            if c.isalpha() and c.isascii():
                return c.upper()
            if c.isalnum():
                return "#"
        return "#"

    def _list_dir(self):
        m = self.modal
        d, items = m["dir"], []
        az = m.get("sort", "az") == "az"
        try:
            for p in d.iterdir():
                if p.name.startswith("."):
                    continue
                if p.is_dir():
                    items.append((0, p.name.lower(), p, 0))
                elif (not m["exts"] or p.suffix.lower() in m["exts"]) and (not m.get("filt") or m["filt"].lower() in p.name.lower()):
                    st = p.stat()
                    items.append((1, p.name.lower() if az else -st.st_mtime, p, st.st_size))
        except OSError:
            pass
        m["items"] = sorted(items, key=lambda x: x[:2])
        # índice A–Z (v2.76): primera posición de cada letra; se usa el grupo más numeroso (archivos o carpetas) y el otro solo para letras que le falten
        nf = sum(1 for it in m["items"] if it[0] == 1)
        pref = 1 if nf >= len(m["items"]) - nf else 0
        first = {}
        for grp in (pref, 1 - pref):
            for i, it in enumerate(m["items"]):
                if it[0] == grp:
                    first.setdefault(self._lead(it[2].name), i)
        m["letters"] = sorted(first.items(), key=lambda kv: (kv[0] != "#", kv[0])) if (az and len(m["items"]) >= 12) else []
        self.views["picker"].off = 0
        self.focus = None

    def picker_jump(self, idx):
        """Lleva la lista del selector a la fila idx y la deja enfocada (para el mando)."""
        m = self.modal
        if not m or m.get("kind") != "picker" or not m.get("items"):
            return
        idx = max(0, min(idx, len(m["items"]) - 1))
        pv = self.views["picker"]
        pv.off = max(0.0, min(float(idx * self.n(80)), float(max(0, pv.h - pv.rect.h))))
        pv.target = None
        self.focus = f"f:{m['items'][idx][2].name}"

    def picker_letter_step(self, step):
        """L1/R1: letra anterior/siguiente respecto a la fila que se ve arriba."""
        m = self.modal
        lt = m.get("letters") or []
        if not lt:
            return False
        pv = self.views["picker"]
        top = int(pv.off // max(1, self.n(80)))
        idxs = [i for _, i in lt]
        if step > 0:
            nxt = [i for i in idxs if i > top]
            self.picker_jump(nxt[0] if nxt else idxs[-1])
        else:
            prv = [i for i in idxs if i < top]
            self.picker_jump(prv[-1] if prv else idxs[0])
        return True

    def close_modal(self):
        if self.modal and self.modal.get("kind") == "osk":
            try:
                pygame.key.stop_text_input()
            except Exception:  # noqa: BLE001
                pass
        prev = self.modal.get("prev") if self.modal else None
        self.modal = None
        self.focus = prev

    def _osk_ok(self, m):
        self.close_modal()
        m["cb"](m["text"])
        if self.pending_osk:
            t, cb, tx, h = self.pending_osk
            self.pending_osk = None
            self.osk(t, cb, tx, h)

    @staticmethod
    def clipboard_full():
        for c in (["wl-paste", "-n"], ["xclip", "-o", "-selection", "clipboard"], ["xsel", "-ob"]):
            try:
                r = subprocess.run(c, capture_output=True, text=True, timeout=3)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                continue
        try:
            return (pygame.scrap.get_text() or "").strip()   # scrap.init() SOLO en __init__ (hilo principal): llamarlo desde hilos mata el vídeo de SDL
        except Exception:  # noqa: BLE001
            return ""

    def _osk_paste(self, m):
        """PEGAR del teclado en pantalla: una sola lectura del portapapeles (antes eran dos procesos wl-paste/xclip por pulsación)."""
        txt = self.clipboard()
        if txt:
            m["text"] = m["text"] + txt
        else:
            self.toast("Portapapeles vacío o no disponible")

    @staticmethod
    def clipboard():
        for c in (["wl-paste", "-n"], ["xclip", "-o", "-selection", "clipboard"], ["xsel", "-ob"]):
            try:
                r = subprocess.run(c, capture_output=True, text=True, timeout=2)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip().splitlines()[0]
            except (OSError, subprocess.SubprocessError):
                continue
        try:
            t = pygame.scrap.get_text()
            return (t or "").strip().splitlines()[0] if t else ""
        except Exception:  # noqa: BLE001
            return ""

    def modal_act(self, a, w):
        m = self.modal
        if a == "A":
            if w and w.cb:
                self.fire(w)
        elif a == "B":
            self.close_modal()
        elif m["kind"] == "info" and a == "X":
            self.confirm("¿Borrar los datos de la ficha?", "Se borran región, versión, formatos, serial, hashes y frases de esta tarjeta (no toca tus archivos).",
                         lambda: (self.info_clear(m["eid"]), self.open_info(m["eid"])))
        elif m["kind"] == "osk" and a == "X":
            m["text"] = m["text"][:-1]
        elif m["kind"] == "osk" and a == "Y":
            m["shift"] = not m["shift"]
        elif m["kind"] == "picker" and a == "X":
            m["dir"] = m["dir"].parent
            self._list_dir()
        elif m["kind"] == "picker" and a in ("LB", "RB"):
            self.picker_letter_step(1 if a == "RB" else -1)

    def screen_x(self):
        if self.detail:
            e = self.entry(self.detail)
            e and self.do_install(e)
        elif self.tab in ("games", "home"):
            self.check_all()
        elif self.tab == "search" and not self.rview:
            self.open_url(f"https://github.com/search?q={urllib.parse.quote_plus((self.sq + ' ' + self.ssuf).strip())}&type=repositories")

    def screen_y(self):
        if self.detail:
            e = self.entry(self.detail)
            e and self.open_page(e)
        elif self.tab == "library":
            self.lib_load(True)
        elif self.tab == "search":
            self.osk("Nombre del juego", self.run_search, self.sq)
        elif self.tab == "art":
            self.art_research()
        elif self.tab == "games":
            self.osk("Buscar juego", lambda t: (setattr(self, "query", t.strip()), setattr(self, "explore", "list"), setattr(self, "filter", "Todos")), self.query)
        elif self.tab == "downloads":
            self.mgr.clear_finished()

    # ═══ dibujo ══════════════════════════════════════════════
    HH, FH = 96, 60     # v2.02: pestañas de ≥ 7 mm en el Ally

    def key_hint(self, x, y, key, label):
        if key == "◀ ▶":
            circ = pygame.Rect(0, 0, self.n(60), self.n(34))
            circ.center = (x + circ.w // 2, y)
            pygame.draw.rect(self.screen, PANEL2, circ, border_radius=self.n(17))
            self.tri(circ.centerx - self.n(13), circ.centery, self.n(12), "left", TXT)
            self.tri(circ.centerx + self.n(13), circ.centery, self.n(12), "right", TXT)
            return self.text(label, circ.right + self.n(10), y, 19, DIM, anchor="ml").right + self.n(34)
        tw = self.font(17, True).size(key)[0]
        circ = pygame.Rect(0, 0, max(self.n(40), tw + self.n(24)), self.n(34))
        circ.center = (x + circ.w // 2, y)
        pygame.draw.rect(self.screen, PANEL2, circ, border_radius=self.n(17))
        self.text(key, circ.centerx, circ.centery, 17, TXT, True, anchor="c")
        r2 = self.text(label, circ.right + self.n(10), y, 19, DIM, anchor="ml")
        return r2.right + self.n(34)

    def ambient(self):
        """Fondo con profundidad (degradado + dos resplandores suaves), preparado UNA vez por tamaño de ventana: nada se calcula por fotograma."""
        key = (self.W, self.H, self.cfg.get("fx"), self.cfg.get("theme"), PAL)
        c = getattr(self, "_amb", None)
        if c and c[0] == key:
            return c[1]
        if (ORBS or PATTERN) and self.cfg.get("fx") != "perf":
            return self._ambient_glass(key)
        if self.cfg.get("fx") == "perf" or (FAMILY, PAL) != ("limpio", "oscuro"):
            flat = pygame.Surface((self.W, self.H)).convert()
            flat.fill(BG)
            self._amb = (key, flat)
            return flat
        sw, sh = 64, max(8, int(64 * self.H / self.W))
        sm = pygame.Surface((sw, sh))
        for y in range(sh):
            t = y / (sh - 1)
            pygame.draw.line(sm, (int(15 - 6 * t), int(16 - 7 * t), int(24 - 12 * t)), (0, y), (sw, y))
        for (cx, cy, rad, col) in ((0.86, 0.05, 0.55, (10, 100, 255)), (0.08, 0.98, 0.5, (110, 70, 220))):
            glow = pygame.Surface((sw, sh), pygame.SRCALPHA)       # una capa por resplandor (en una sola, el segundo borraba parte del primero)
            for r in range(int(rad * sw), 0, -1):
                a = int(34 * (1 - r / (rad * sw)) ** 2)
                pygame.draw.circle(glow, (*col, a), (int(cx * sw), int(cy * sh)), r)
            sm.blit(glow, (0, 0))
        big = pygame.transform.smoothscale(sm, (self.W, self.H)).convert()
        self._amb = (key, big)
        return big

    def _ambient_glass(self, key):
        """Fondo del tema Cristal: degradado índigo→azul noche con tres resplandores grandes y suaves; se calcula pequeño y se amplía una vez."""
        sw, sh = 320, max(8, int(320 * self.H / self.W))
        sm = pygame.Surface((sw, sh))
        for y in range(sh):
            t = y / (sh - 1)
            pygame.draw.line(sm, tuple(int(a + (b - a) * t) for a, b in zip(*(GRAD or (BG, BG)))), (0, y), (sw, y))
        for (cx, cy, rad, col, al) in ORBS or ():
            glow = pygame.Surface((sw, sh), pygame.SRCALPHA)       # una capa por resplandor: el borde transparente de uno no borra a otro
            for r in range(int(rad * sw), 0, -1):
                a = int(al * (1 - r / (rad * sw)) ** 1.6)
                pygame.draw.circle(glow, (*col, a), (int(cx * sw), int(cy * sh)), r)
            sm.blit(glow, (0, 0))
        big = sm
        while big.get_width() * 2 < self.W:                 # se amplía de dos en dos: de golpe salen bloques visibles
            big = pygame.transform.smoothscale(big, (big.get_width() * 2, big.get_height() * 2))
        big = pygame.transform.smoothscale(big, (self.W, self.H)).convert()
        self._pattern(big)
        self._amb = (key, big)
        return big

    def _pattern(self, s):
        """Trama del tema sobre el fondo ya ampliado (una vez por tamaño): rejilla en perspectiva (Neón) o líneas de barrido (Fósforo)."""
        W, H = s.get_size()
        if PATTERN == "scan":
            ln = pygame.Surface((W, H), pygame.SRCALPHA)
            for y in range(0, H, max(3, self.n(4))):
                pygame.draw.line(ln, (0, 0, 0, 70), (0, y), (W, y))
            s.blit(ln, (0, 0))
        elif PATTERN == "grid":
            ln = pygame.Surface((W, H), pygame.SRCALPHA)
            hz, col = int(H * 0.60), LINE
            for i in range(-14, 15):                                # líneas que huyen al punto de fuga
                pygame.draw.line(ln, (*col, 60), (W // 2 + i * W // 40, hz), (W // 2 + i * W // 5, H), max(1, self.n(2)))
            y, step = float(hz), 3.0
            while y < H:                                            # horizontales cada vez más separadas
                pygame.draw.line(ln, (*col, int(30 + 60 * (y - hz) / max(1, H - hz))), (0, int(y)), (W, int(y)), max(1, self.n(2)))
                step *= 1.32
                y += step
            pygame.draw.line(ln, (*ACC, 150), (0, hz), (W, hz), max(2, self.n(3)))
            s.blit(ln, (0, 0))

    def glass(self, h, top):
        """Barra translúcida (cacheada): más opaca hacia el borde de la pantalla y más clara hacia el contenido, con un filo de luz."""
        key = ("_gl", self.W, h, top, self.cfg.get("fx"), self.cfg.get("theme"), PAL)
        c = getattr(self, "_gl_c", None)
        if c is None:
            c = self._gl_c = {}
        if key not in c and GLASS and self.cfg.get("fx") != "perf":
            gs = pygame.Surface((self.W, h), pygame.SRCALPHA)
            for yy in range(h):
                k = (1 - yy / h) if top else (yy / h)
                pygame.draw.line(gs, (*PANEL, int(222 + 30 * k)), (0, yy), (self.W, yy))
            edge = h - 1 if top else 0
            pygame.draw.line(gs, (255, 255, 255, 40), (0, edge), (self.W, edge))
            c[key] = gs
        if key not in c and (self.cfg.get("fx") == "perf" or (FAMILY, PAL) != ("limpio", "oscuro")):
            gs = pygame.Surface((self.W, h), pygame.SRCALPHA)
            gs.fill((*PANEL, 255))
            edge = h - 1 if top else 0
            pygame.draw.line(gs, LINE, (0, edge), (self.W, edge))
            c[key] = gs
        if key not in c:
            gs = pygame.Surface((self.W, h), pygame.SRCALPHA)
            for yy in range(h):
                k = (1 - yy / h) if top else (yy / h)           # 1 en el borde de la pantalla, 0 junto al contenido
                pygame.draw.line(gs, (12, 13, 18, int(226 + 24 * k)), (0, yy), (self.W, yy))
            edge = h - 1 if top else 0
            pygame.draw.line(gs, (255, 255, 255, 26), (0, edge), (self.W, edge))
            c[key] = gs
        return c[key]

    def header(self):
        hh = self.n(self.HH)
        self.screen.set_clip(None)
        self.screen.blit(self.glass(hh, True), (0, 0))
        self.text("Forgeinator", self.n(40), hh // 2, 30, TXT, True, anchor="ml")
        n_act = sum(1 for d in self.mgr.list() + self.cjobs.list() if d.state in ("active", "queued", "waiting")) + sum(1 for b in self.builds if b.state in ("queued", "running"))
        labels = [(key, label.capitalize() if label.isupper() else label) for key, label in TABS]
        w, gap = self.n(190), self.n(4)
        total = len(labels) * w + (len(labels) - 1) * gap + 2 * self.n(6)
        x = self.W - self.n(40) - total
        self.rr((x, self.n(6), total, hh - self.n(12)), PANEL, 26)
        x += self.n(6)
        for key, label in labels:
            self.button(f"tab:{key}", (x, self.n(10), w, hh - self.n(20)), label, lambda k=key: self.go_tab(k),
                        "seg" if (SUBTAB.get(self.tab, self.tab) == key and not self.detail) else "ghost", 21, pill=True)
            if key == "downloads" and n_act:
                # insignia con el número de descargas en curso; late un instante al añadir una
                pulse = max(0.0, 1.0 - (time.time() - getattr(self, "dl_pulse", 0)) / 1.2)
                rad = self.n(14) + int(self.n(5) * pulse)
                cx, cy = x + w - self.n(18), self.n(10) + self.n(4)
                pygame.draw.circle(self.screen, ACC, (cx, cy), rad)
                self.text(str(n_act), cx, cy, 17, (255, 255, 255), True, anchor="c")
            x += w + gap

    SIDE_W = 104

    def draw_sidebar(self):
        """Barra lateral del prototipo: logotipo, cuatro secciones con icono y la versión. Los iconos se dibujan con primitivas (sin fuentes de iconos)."""
        sw = self.n(self.SIDE_W)
        self.screen.set_clip(None)
        self.rr((0, 0, sw, self.H), PANEL, 0)
        pygame.draw.line(self.screen, LINE, (sw - 1, 0), (sw - 1, self.H), max(1, self.n(2)))
        self.text("RECOMP", sw // 2, self.n(34), 18, ACC, True, anchor="c")
        self.text("HUB", sw // 2, self.n(56), 18, ACC, True, anchor="c")
        n_act = sum(1 for d in self.mgr.list() + self.cjobs.list() if d.state in ("active", "queued", "waiting")) + sum(1 for b in self.builds if b.state in ("queued", "running"))
        y = self.n(92)
        for key, label in TABS:
            r = pygame.Rect(self.n(10), y, sw - self.n(20), self.n(78))
            _, foc = self.reg(f"tab:{key}", r, lambda k=key: self.go_tab(k))
            sel = SUBTAB.get(self.tab, self.tab) == key and not self.detail
            if sel:
                self.rr(r, ACC, 16)
            elif foc:
                self.rr(r, PANEL2, 16)
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(6), self.n(6)), FOCUS or TXT, 18, max(2, self.n(3)))
            col = ON_ACC if sel else (TXT if foc else DIM)
            self._side_icon(key, r.centerx, r.y + self.n(28) - self.tab_hop(key, sel), self.n(13), col)
            self.text(label.capitalize(), r.centerx, r.y + self.n(60), 15, col, True, anchor="c")
            if key == "downloads" and n_act:
                pygame.draw.circle(self.screen, ERR if not sel else ON_ACC, (r.right - self.n(14), r.y + self.n(14)), self.n(10))
                self.text(str(n_act), r.right - self.n(14), r.y + self.n(14), 13, (255, 255, 255) if not sel else ACC, True, anchor="c")
            y += self.n(88)
        self.text("v" + config.VERSION, sw // 2, self.H - self.n(24), 14, DIM, anchor="c")

    def _side_icon(self, key, cx, cy, r, col):
        w = max(2, self.n(2))
        P = pygame.draw
        s = self.screen
        ic = icons.get({"home": "house", "games": "compass", "downloads": "download", "settings": "settings"}.get(key, ""), int(r * 2.5), col)
        if ic is not None:
            s.blit(ic, ic.get_rect(center=(int(cx), int(cy))))
            return
        if key == "home":
            P.polygon(s, col, [(cx - r, cy), (cx, cy - r), (cx + r, cy)], w)
            P.rect(s, col, (cx - r * 0.7, cy, r * 1.4, r * 0.95), w)
        elif key == "games":
            P.circle(s, col, (cx, cy), r, w)
            P.polygon(s, col, [(cx - r * 0.4, cy + r * 0.4), (cx + r * 0.15, cy + r * 0.15), (cx + r * 0.4, cy - r * 0.4), (cx - r * 0.15, cy - r * 0.15)])
        elif key == "downloads":
            P.line(s, col, (cx, cy - r), (cx, cy + r * 0.35), w)
            P.lines(s, col, False, [(cx - r * 0.5, cy - r * 0.15), (cx, cy + r * 0.4), (cx + r * 0.5, cy - r * 0.15)], w)
            P.lines(s, col, False, [(cx - r, cy + r * 0.3), (cx - r, cy + r), (cx + r, cy + r), (cx + r, cy + r * 0.3)], w)
        else:
            P.circle(s, col, (cx, cy), r * 0.8, w)
            P.circle(s, col, (cx, cy), r * 0.3, w)
            for a in range(0, 360, 45):
                v = pygame.math.Vector2(1, 0).rotate(a)
                P.line(s, col, (cx + v.x * r * 0.8, cy + v.y * r * 0.8), (cx + v.x * r * 1.15, cy + v.y * r * 1.15), w + 1)

    def draw_clipbanner(self):
        """Copiaste un repo de GitHub en el navegador: botón flotante para analizarlo y crear su tarjeta, desde cualquier pestaña."""
        if self.hb_opening and time.time() - self.hb_opening < 90:
            w, h = min(self.W - self.n(80), self.n(900)), self.n(80)
            r = pygame.Rect((self.W - w) // 2, self.n(120), w, h)
            self.rr(r, PANEL2, 16)
            self.rr(r, ACC, 16, 2)
            dots = "." * (int(self.t * 2) % 4)
            self.text("Abriendo el navegador de Hub" + dots, r.centerx, r.centery, 26, TXT, True, anchor="c")
        if self.clip_url and not self.modal and not self.rview:
            w, h = min(self.W - self.n(80), self.n(1100)), self.n(76)
            x, y = (self.W - w) // 2, self.H - self.n(self.FH) - h - self.n(110) - (self.n(90) if self.clip_repo else 0)
            nm = urllib.parse.unquote(self.clip_url.rsplit("/", 1)[-1].split("?")[0])[:60]
            self.button("clipdl", (x, y, w - self.n(90), h), f"DESCARGAR CON HUB: {nm} ›", lambda: self.add_url(self.clip_url), "ok", 21)
            self.button("clipdlx", (x + w - self.n(80), y, self.n(80), h), "×", lambda: setattr(self, "clip_url", ""), size=30)
        if not self.clip_repo or self.rview or self.modal or (self.tab == "search" and not self.detail):
            return
        w, h = min(self.W - self.n(80), self.n(1100)), self.n(76)
        x, y = (self.W - w) // 2, self.H - self.n(self.FH) - h - self.n(110)
        self.button("clipgo", (x, y, w - self.n(90), h), f"REPO COPIADO: {self.clip_repo}  —  ANALIZAR Y CREAR TARJETA ›", lambda: self.open_repo(self.clip_repo), "ok", 21)
        self.button("clipx", (x + w - self.n(80), y, self.n(80), h), "×", lambda: setattr(self, "clip_repo", ""), size=30)

    def footer(self, hints):
        y0 = self.H - self.n(self.FH)
        self.screen.set_clip(None)
        self.screen.blit(self.glass(self.n(self.FH), False), (0, y0))
        x = self.n(40)
        for k, lab in hints:
            x = self.key_hint(x, y0 + self.n(self.FH) // 2, k, lab)

    def draw(self):
        self.new, self.active_views = [], []
        m_bd = (self.modal or {}).get("_bd")
        if m_bd is not None and m_bd[0] == (self.W, self.H):
            self.screen.set_clip(None)
            self.screen.blit(m_bd[1], (0, 0))          # con un menú abierto no se redibuja lo de detrás: se usa su instantánea desenfocada
            self.new = []
            self.draw_modal()
            self._hold_ring()
            self._toast()
            self._finish_widgets()
            return
        self.draw_bg()
        side = LAYOUT == "side"
        if side:                                   # barra lateral: el contenido se dibuja en una subsuperficie a la derecha y luego sus rects se pasan a pantalla
            full, ox = self.screen, self.n(self.SIDE_W)
            self.screen = full.subsurface((ox, 0, self.W - ox, self.H))
            self.W -= ox
            self.HH = 0
        body = pygame.Rect(0, self.n(self.HH), self.W, self.H - self.n(self.HH) - self.n(self.FH))
        if self.rview:
            self.draw_repo(body)
            hints = [("A", "Elegir"), ("B", "Atrás")]
        elif self.detail and self.entry(self.detail):
            self.draw_detail(body)
            hints = [("A", "Elegir"), ("X", "Instalar"), ("Y", "Página del proyecto"), ("B", "Atrás")]
        elif self.tab == "art":
            self.draw_art(body)
            hints = ([("A", "Usar esta"), ("◀ ▶", "Ver otra opción"), ("B", "Volver a la lista")] if (self.art or {}).get("pv") is not None
                     else [("A", "Ver y elegir"), ("LB/RB", "Tipo de imagen"), ("Y", "Buscar otro nombre"), ("B", "Atrás")])
        elif self.tab == "steam":
            self.draw_steam(body)
            hints = [("A", "Elegir arte (SteamGridDB)"), ("X", "Usar mi imagen"), ("Y", "Ficha del juego"), ("B", "Atrás")]
        elif self.tab == "home":
            self.draw_home(body)
            hints = [("A", "Jugar"), ("Y", "Opciones del juego"), ("X", "Actualizar"), ("LB/RB", "Secciones")]
        elif self.tab == "games" and self.explore == "cats":
            self.draw_explore(body)
            hints = [("A", "Abrir"), ("Y", "Buscar por nombre"), ("X", "Comprobar actualizaciones"), ("LB/RB", "Secciones")]
        elif self.tab == "games":
            self.draw_games(body)
            hints = [("A", "Abrir"), ("B", "Consolas"), ("Y", "Buscar"), ("LB/RB", "Secciones")]
        elif self.tab == "library":
            self.draw_library(body)
            hints = [("A", "Abrir / buscar repo"), ("B", "Atrás"), ("X", "Buscar en GitHub (navegador)"), ("Y", "Reindexar")]
        elif self.tab == "search":
            self.draw_search(body)
            hints = [("A", "Elegir"), ("B", "Atrás"), ("X", "Abrir en el navegador"), ("Y", "Escribir nombre")]
        elif self.tab == "downloads":
            self.draw_downloads(body)
            hints = [("A", "Pausar / reanudar"), ("X", "Cancelar / quitar"), ("Y", "Limpiar terminadas"), ("LB/RB", "Pestañas")]
        else:
            self.draw_settings(body)
            hints = [("A", "Elegir"), ("◀ ▶", "Ajustar"), ("LB/RB", "Pestañas")]
        if not side:
            self.header()
        self.footer(hints)
        if side:
            self.screen, self.W = full, self.W + ox
            del self.HH
            seen = set()
            for w in self.new:
                if id(w.rect) not in seen:
                    seen.add(id(w.rect))
                    w.rect.x += ox
            for v in self.active_views:
                v.rect.x += ox
            self.screen.set_clip(None)
            self.draw_sidebar()
        self.draw_clipbanner()
        self.draw_updbanner()
        self.draw_dlbanner()
        if self.modal:
            self.new = []
            self.screen.set_clip(None)
            self.modal["_bd"] = ((self.W, self.H), self._frost())      # instantánea desenfocada y oscurecida de lo de detrás (una vez, al abrir)
            self.screen.blit(self.modal["_bd"][1], (0, 0))
            self.draw_modal()
        self.draw_wait()
        self._hold_ring()
        self._toast()
        self.draw_fx()
        self._finish_widgets()

    def _frost(self):
        """Lo que hay en pantalla, desenfocado (bajar y subir de tamaño) y oscurecido: el fondo «esmerilado» de los menús. Se calcula una sola vez por menú."""
        w, h = self.W, self.H
        if self.cfg.get("fx") == "perf":                 # modo rendimiento: sin desenfoque, solo oscurecer lo de detrás
            dark = self.screen.copy()
            dark.fill((110, 110, 118), special_flags=pygame.BLEND_RGB_MULT)
            return dark.convert()
        q = 14 + int(24 * (MAT or {}).get("blur", 0.0))    # v3.09: el material Glass desenfoca más (solo aquí, una vez al abrir el menú)
        small = pygame.transform.smoothscale(self.screen, (max(8, w // q), max(8, h // q)))
        big = pygame.transform.smoothscale(small, (w, h))
        big.fill((132, 132, 142), special_flags=pygame.BLEND_RGB_MULT)
        return big.convert()

    def _toast(self):
        self._workbar()
        if time.time() < self.toast_t:
            tw = min(self.W - self.n(80), self.n(1000))
            lines = self.wrap(self.toast_msg, 21, tw - self.n(40), max_lines=3)
            h = self.n(24 + 29 * len(lines))
            r = pygame.Rect(0, 0, tw, h)
            r.midbottom = (self.W // 2, self.H - self.n(self.FH) - self.n(18))
            self.rr(r, PANEL2, 14, a=245 if GLASS else None)      # el fondo sigue al tema: con TXT oscuro (Claro, Tinta, Bloque) uno negro fijo no se leía
            self.rr(r, ACC, 14, 2)
            for i, ln in enumerate(lines):
                self.text(ln, r.centerx, r.y + self.n(14 + 29 * i), 21, TXT, anchor="mid")

    def _finish_widgets(self):
        self.widgets = self.new
        ok = {w.key for w in self.widgets if w.focus and w.cb}
        if self.focus not in ok:
            cands = [w for w in self.widgets if w.focus and w.cb and (w.view or self.modal)]
            cands = cands or [w for w in self.widgets if w.focus and w.cb]
            self.focus = min(cands, key=lambda w: (w.rect.y, w.rect.x)).key if cands else None

    t_act = 0.0
    _io_gen = 0

    def memo(self, key, fn, ttl=2.0):
        """v3.14: lo que una pantalla lee del disco al dibujarse (claves guardadas, registros, update.json…) se lee una vez
        y se reutiliza hasta la siguiente pulsación/evento o como mucho `ttl` segundos (por si lo cambia un hilo). Antes se leía en cada
        fotograma: 45 lecturas por segundo, y algunas (buildlog.jsonl, launch-logs/) crecen con el uso."""
        c = self.__dict__.setdefault("_memo_c", {})
        now = time.monotonic()
        hit = c.get(key)
        if hit and hit[0] == self._io_gen and now - hit[1] < ttl:
            return hit[2]
        v = fn()
        if len(c) > 256:
            c.clear()
        c[key] = (self._io_gen, now, v)
        return v

    def memo_clear(self):
        self.__dict__.get("_memo_c", {}).clear()
    STEAM_WAIT_MAX = 5.0
    STEAM_COVER_MAX = 12.0    # v2.49: tope de espera a que otra ventana tome el foco
    STEAM_COVER_GRACE = 1.5   # margen tras ver la ventana del launcher/juego
    STEAM_COVER = 4.0      # tras detectar el juego, Hub tapa la pantalla unos segundos más: así no se ve la interfaz de Steam hasta que sale la ventana del juego

    def power_state(self):
        """Energía del equipo (TDP, batería), releída cada 10 s."""
        now = time.time()
        if now - getattr(self, "_pw_t", 0) > 10:
            try:
                self._pw = power.snapshot()
            except Exception:  # noqa: BLE001
                self._pw = {}
            self._pw_t = now
        return self._pw

    def power_saving(self) -> bool:
        return power.saving(self.cfg.get("power_mode", "auto"), self.power_state())

    def target_fps(self):
        """Ajustes es una pantalla estática (muchas filas, nada se mueve): sin pulsaciones desde hace 1 s baja a 20 fps y la CPU/GPU del Ally descansa.
        Modo AHORRO (TDP bajo o batería baja, o elegido en Ajustes): 30 fps, y 15 en cualquier pantalla tras 3 s sin tocar nada."""
        save = self.power_saving()
        moving = bool(self.touch) or any(v.target is not None or abs(v.vel) > 8 for v in self.views.values())
        quiet = not self.perf.on and time.time() > self.toast_t and not self.held and not getattr(self, "modal", None) and not moving and not getattr(self, "_work", None)
        idle = time.time() - self.t_act
        if self.tab == "settings" and quiet and idle > 1.0:
            return 15 if save else 20
        if save:
            return 15 if (quiet and idle > 3.0) else 30
        if quiet and idle > 5.0 and not (ANIM and self.fx_level() >= 2 and not self.reduced_motion()):
            return 30                                  # v3.14: sin fondo animado y 5 s sin tocar nada, nada se mueve: 30 fps (la 1.ª pulsación vuelve a 45)
        return 45

    def cycle_power_mode(self):
        order = ["auto", "save", "perf"]
        cur = self.cfg.get("power_mode", "auto")
        self.cfg["power_mode"] = order[(order.index(cur) + 1) % 3] if cur in order else "auto"
        config.save_settings(self.cfg)
        self._pw_t = 0
        self.toast("Modo de energía: " + self.power_label())

    def power_label(self) -> str:
        m = self.cfg.get("power_mode", "auto")
        s = self.power_state()
        now = "ahorro" if self.power_saving() else "normal"
        tdp = f", TDP {s['tdp_w']:g} W" if s.get("tdp_w") else ""
        return {"auto": f"AUTOMÁTICO (ahora: {now}{tdp})", "save": "AHORRO (30 fps, 15 en reposo, sin animaciones)",
                "perf": "RENDIMIENTO (45 fps siempre)"}.get(m, m)

    def frame(self, dt=1 / 45):
        self.t += dt
        self._cov_collect()
        if self.perf.on:
            self.perf.frame(self, dt)
            return
        self.pump()
        self.update(dt)
        self.draw()

    _idx_busy = False

    def update_index(self):
        """Baja awesome-decomp-games y escribe data/imports/00-awesome-decomp.json (en un hilo; no toca tu catálogo)."""
        if self._idx_busy:
            self.toast("Ya se está actualizando la lista…")
            return
        self._idx_busy = True
        self.toast("Descargando la lista de proyectos…")

        def job():
            try:
                from . import indexers
                r = indexers.update()
                self.reload()
                self._inst_c = None
                self.toast(f"Lista actualizada: {r['listos']} listos para usar + {r['solo_codigo']} solo código")
                print(f"[indexador] awesome-decomp: {r}", file=sys.stderr, flush=True)
            except Exception as ex:  # noqa: BLE001
                print(f"[indexador] error: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
                self.toast(f"No se pudo actualizar la lista: {type(ex).__name__}")
            finally:
                self._idx_busy = False
        threading.Thread(target=job, daemon=True).start()

    # ── v2.85: mantener pulsado un juego (como en el teléfono) ──
    def lp_secs(self):
        try:
            return max(0.25, min(1.5, float(self.cfg.get("long_press", 0.45))))
        except (TypeError, ValueError):
            return 0.45

    def _lp_entry(self, key):
        """Juego al que pertenece la tarjeta de Inicio tocada (None si no es una tarjeta de juego)."""
        if not key or self.modal or self.detail:
            return None
        if key == "hero":
            return getattr(self, "_hero_e", None)
        if key.startswith("home:"):
            return next((x for x in self.entries if x.get("id") == key[5:]), None)
        return None

    def _lp_menu(self, key):
        """v2.92: ¿qué menú corresponde a esta tarjeta? → (título, opciones) o None. Inicio y Explorar: el juego; Biblioteca: la fila; Descargas: sus acciones."""
        if not key or self.modal or self.detail:
            return None
        e = self._lp_entry(key)
        if e is None and key.startswith("card:"):
            eid = key[5:].split("#")[0]
            e = next((x for x in self.entries if x.get("id") == eid), None)
        if e is not None:
            return e["name"], self._game_options(e)
        if key.startswith("lr:"):
            r = next((x for x in self.lib_rows if f"lr:{x['path']}" == key), None)
            if r is None:
                return None
            opts = [("ABRIR" if r["match"] else "BUSCAR UN PORT", lambda: self.lib_open(r)), ("BUSCAR EN GITHUB", lambda: self.lib_web(r))]
            return r["name"], opts
        acts = self.__dict__.get("_lp_actions", {}).get(key)
        if acts:
            d = next((x for x in self.mgr.list() if f"dl:{x.id}" == key), None)
            return (d.meta.get("title") or d.name or "Descarga") if d else "Descarga", acts
        return None

    def _check_long_press(self, now):
        t = self.touch
        if not t or t["drag"] or t.get("lp") or not t.get("hot"):
            return
        if now - t["t"] < self.lp_secs():
            return
        m = self._lp_menu(t["hot"])
        if m is None:
            return
        t["lp"] = True
        self.long_press_menu(m[0], m[1], t["pos"])

    def _hold_ring(self):
        """Mientras mantienes el dedo sobre una tarjeta de juego: un arco que se completa (avisa de que va a salir el menú)."""
        t = self.touch
        if not t or t["drag"] or t.get("lp") or not t.get("hot") or self.modal:
            return
        p = (time.time() - t["t"]) / self.lp_secs()
        if p < 0.25 or self._lp_menu(t["hot"]) is None:
            return
        r = self.n(34)
        rect = pygame.Rect(0, 0, 2 * r, 2 * r)
        rect.center = t["pos"]
        pygame.draw.circle(self.screen, BG, rect.center, r)
        pygame.draw.arc(self.screen, FOCUS or ACC, rect, -1.5708, -1.5708 + 6.2832 * min(1.0, p), max(3, self.n(5)))

    def _game_options(self, e):
        installed = bool((self.inst(e) or {}).get("installed"))
        opts = [("JUGAR", lambda: self.play(e))] if installed else [("INSTALAR", lambda: self.do_install(e))]
        lat = self.rel.get(self.rk(e)) if hasattr(self, "rel") else None
        inf = self.inst(e) or {}
        if installed and lat and lat.get("tag") and inf.get("version") and lat["tag"] != inf["version"] and not self.frozen(e):
            opts.append((f"ACTUALIZAR A {lat['tag']}", lambda: self.do_install(e)))
        opts.append(("ABRIR LA FICHA", lambda: self.open_detail(e)))
        if installed:
            opts += [("HISTORIAL", lambda: self.show_history(e)), ("EXPORTAR DIAGNÓSTICO", lambda: self.export_diag(e))]
        if e.get("repo"):
            opts.append(("PÁGINA DEL PROYECTO", lambda: self.open_page(e)))
        return opts

    def long_press_menu(self, title, opts, pos=None):
        """Menú pequeño con sonido y vibración (v2.85, generalizado en v2.92)."""
        self.sfx.play("open")
        haptic.pulse(self, "hold")
        self.modal = {"kind": "choice", "title": title, "prev": None, "msg": "", "options": opts, "compact": True, "at": pos}
        self.focus = None

    def long_press_game(self, e, pos=None):
        self.long_press_menu(e["name"], self._game_options(e), pos)

    def toggle_haptics(self):
        self.cfg["haptics"] = not self.cfg.get("haptics", True)
        config.save_settings(self.cfg)
        if self.cfg["haptics"]:
            ok = haptic.pulse(self, "hold")
            self.toast("Vibración: activada" + ("" if ok else " (no detecto un mando que vibre)"))
        else:
            self.toast("Vibración: desactivada")

    def toggle_sfx(self):
        self.sfx.enabled = not self.sfx.enabled
        self.cfg["sounds"] = self.sfx.enabled
        config.save_settings(self.cfg)
        if self.sfx.enabled:
            if not self.sfx.tried:
                self.sfx._init()
            self.sfx.play("confirm")
        self.toast("Sonidos: " + ("activados" if self.sfx.enabled else "desactivados"))

    def cycle_sfx_volume(self):
        steps = (0.25, 0.5, 0.75, 1.0)
        nxt = next((v for v in steps if v > self.sfx.volume + 1e-6), steps[0])
        self.sfx.set_volume(nxt)
        self.cfg["sound_volume"] = nxt
        config.save_settings(self.cfg)
        self.sfx.play("move")

    def toggle_perf(self):
        self.perf.on = not self.perf.on
        self.cfg["perf_log"] = self.perf.on
        self.perf.start_sampler()
        config.save_settings(self.cfg)
        self.toast("Rendimiento: " + ("registrando en hub.log" if self.perf.on else "apagado"))

    _WEV = tuple(getattr(pygame, n) for n in ("WINDOWCLOSE", "WINDOWHIDDEN", "WINDOWMINIMIZED", "WINDOWFOCUSLOST", "WINDOWFOCUSGAINED",
                                               "WINDOWEXPOSED", "APP_TERMINATING", "APP_WILLENTERBACKGROUND", "APP_DIDENTERBACKGROUND",
                                               "WINDOWTAKEFOCUS", "WINDOWRESTORED") if hasattr(pygame, n))

    def _signals(self):
        """Registra por qué se cierra: señales (SSH colgado, kill, Steam). SIGHUP/SIGPIPE se IGNORAN para que no mueran por cerrar la sesión SSH."""
        import signal
        if threading.current_thread() is not threading.main_thread():
            return

        def on(sig, *_):
            name = signal.Signals(sig).name
            print(f"[salida] señal {name} recibida · inactivo {time.time() - self.last_input:.0f}s", file=sys.stderr, flush=True)
            if sig in (signal.SIGTERM, signal.SIGINT):
                self.why = f"señal {name}"
                self.running = False

        for n in ("SIGHUP", "SIGPIPE", "SIGTERM", "SIGINT", "SIGUSR1"):
            try:
                signal.signal(getattr(signal, n), on)
            except (ValueError, OSError, AttributeError):
                pass

    STEAM_UI_APP = 769   # appid de la interfaz de Steam (QAM, menú Steam, teclado): GAMESCOPE_FOCUSED_APP vale 769 cuando la tiene

    def _gs_changed(self, smp):
        """Hilo de gsfocus: cambió la ventana o la app con foco en Gamescope. La referencia de Hub es la primera lectura que no sea la UI de Steam."""
        key = (smp["win"], smp["app"])
        if self.gs_base is None and smp["app"] != self.STEAM_UI_APP:
            self.gs_base = key
            print(f"[foco] gamescope: referencia ventana={smp['win']} app={smp['app']} · kbd={smp['kbd']} · leído en {smp.get('display', '?')}", file=sys.stderr, flush=True)
        else:
            hub = self.gs_base is not None and key == self.gs_base
            tag = "Hub vuelve a tener el foco" if hub else "OTRA ventana/app tiene el foco (menú de Steam encima)"
            print(f"[foco] gamescope {time.strftime('%H:%M:%S')}: ventana={smp['win']} app={smp['app']} · {tag}", file=sys.stderr, flush=True)
            if hub:
                self.mute_until = max(self.mute_until, time.time() + 0.4)   # que el botón que cerró el menú no llegue a Hub
        self.gs_now = key

    def _gs_over(self):
        now = self.gs_now
        over = now is not None and (now[1] == self.STEAM_UI_APP or (self.gs_base is not None and now != self.gs_base))
        t = time.time()
        if not over:
            self.gs_over_t = 0
        elif not getattr(self, "gs_over_t", 0):
            self.gs_over_t = t
        elif t - self.gs_over_t > 90 and now[1] != self.STEAM_UI_APP:   # válvula: si Hub recreó su ventana el id cambió
            print(f"[foco] gamescope: 90 s con otra ventana {now}; se toma como la nueva referencia de Hub", file=sys.stderr, flush=True)
            self.gs_base, self.gs_over_t, over = now, 0, False
        return over

    def _vivo(self):
        """Latido en hub.log cada 2 min: memoria, hilos, descriptores. Si Hub muere, la última línea dice cuánto vivió y con qué recursos."""
        while self.running:
            time.sleep(120)
            try:
                rss = next((int(l.split()[1]) // 1024 for l in open("/proc/self/status") if l.startswith("VmRSS")), 0)
                fds = len(os.listdir("/proc/self/fd"))
            except OSError:
                rss = fds = 0
            print(f"[vivo] {time.time() - self.t0:.0f}s · inactivo {time.time() - self.last_input:.0f}s · RAM {rss} MB · hilos {threading.active_count()} · fds {fds} · fps {self.fps:.0f}",
                  file=sys.stderr, flush=True)
            try:
                from . import logrot
                if logrot.maybe_rotate(config.STATE / "hub.log"):
                    print(f"[registro] hub.log pasó de {logrot.LIMIT // 1048576} MB: lo anterior está en hub.log.old", file=sys.stderr, flush=True)
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    def _kill_descendants(spare=()):
        """Al salir, ningún proceso hijo de Hub debe quedar vivo (Steam espera a todos y, si queda alguno, no deja relanzar el juego)."""
        me = os.getpid()
        kids = {}
        try:
            for d in os.listdir("/proc"):
                if d.isdigit():
                    try:
                        st = open(f"/proc/{d}/stat").read()
                        ppid = int(st.rsplit(")", 1)[1].split()[1])
                        kids.setdefault(ppid, []).append(int(d))
                    except (OSError, ValueError, IndexError):
                        continue
        except OSError:
            return
        keep = set()
        todo = list(spare)
        while todo:   # el juego lanzado con JUGAR y todo lo suyo NO se toca
            q = todo.pop()
            keep.add(q)
            todo += kids.get(q, [])
        todo, seen = [k for k in kids.get(me, []) if k not in keep], []
        while todo:
            p = todo.pop()
            seen.append(p)
            todo += kids.get(p, [])
        for p in seen:
            try:
                os.kill(p, 9)
            except OSError:
                pass
        if seen:
            print(f"[salida] cerré {len(seen)} proceso(s) hijo(s) que seguían vivos", file=sys.stderr, flush=True)

    def _quiet_display_quit(self):
        """Quién cerró el vídeo: si fue código de Python (pygame.display.quit / pygame.quit) queda su pila en el registro; si no sale nada, lo cerró SDL/el servidor gráfico."""
        q = getattr(self, "_dq_calls", None)
        print("[video] llamadas a display.quit/pygame.quit desde Python: " + (" || ".join(q) if q else "ninguna (lo cerró SDL o el servidor gráfico)"), file=sys.stderr, flush=True)

    def _watch_display_quit(self):
        """Envuelve pygame.display.quit y pygame.quit para anotar quién las llama (solo guarda cadenas; coste nulo)."""
        import traceback as tb
        self._dq_calls = []
        for mod, name in ((pygame.display, "quit"), (pygame, "quit")):
            orig = getattr(mod, name)
            if getattr(orig, "_hub_wrapped", False):
                continue

            def w(*a, _o=orig, _n=f"{mod.__name__}.{name}", **k):
                self._dq_calls.append(_n + " desde " + " < ".join(f"{os.path.basename(f.filename)}:{f.lineno} {f.name}" for f in tb.extract_stack(limit=6)[:-1][::-1]))
                del self._dq_calls[:-6]
                return _o(*a, **k)
            w._hub_wrapped = True
            setattr(mod, name, w)

    def _video_diag(self):
        """Foto del entorno cuando SDL pierde el vídeo. El `ps` (lento: ~300 ms) solo la primera vez por sesión; después, una línea corta."""
        rt = os.environ.get("XDG_RUNTIME_DIR", "")
        socks = [f for f in (os.listdir(rt) if rt and os.path.isdir(rt) else []) if f.startswith(("wayland", "gamescope"))]
        self._vloss = getattr(self, "_vloss", 0) + 1
        out = ""
        if self._vloss == 1:
            try:
                out = "\n[video] procesos:\n" + subprocess.run("ps -eo pid,etimes,comm | grep -i -E 'gamescope|steam|firefox|edge|xwayland|kwin|plasma' | grep -v grep | head -20",
                                                              shell=True, capture_output=True, text=True, timeout=5).stdout
            except (OSError, subprocess.SubprocessError):
                out = "\n[video] (ps no disponible)"
        print(f"[video] PERDIDO #{self._vloss} tras {time.time() - self.last_input:.0f}s sin tocar nada. SDL: {pygame.get_error()!r} · display_init={pygame.display.get_init()} · DISPLAY={os.environ.get('DISPLAY')} "
              f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY')} · sockets: {socks}{out}", file=sys.stderr, flush=True)

    def _recover_video(self):
        """Reabre la ventana si el servidor gráfico sigue vivo (hasta ~40 s de intentos). Conserva todo el estado de la UI."""
        self._video_diag()
        for intento in range(1, 21):
            for d in (os.environ.get("SDL_VIDEODRIVER"), None, "x11", "wayland"):
                try:
                    pygame.display.quit()
                    if d:
                        os.environ["SDL_VIDEODRIVER"] = d
                    pygame.display.init()
                    size = os.environ.get("HUB_WINDOW")
                    size = tuple(int(v) for v in size.lower().split("x")) if size else None
                    self.screen = pygame.display.set_mode(size) if size else pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    pygame.display.set_caption("Forgeinator 3000")
                    pygame.mouse.set_visible(bool(size))
                    self.W, self.H = self.screen.get_size()
                    self._tc.clear()
                    print(f"[video] ventana reabierta (intento {intento}, driver={pygame.display.get_driver()}, {self.W}x{self.H})", file=sys.stderr, flush=True)
                    self.fails = 0
                    return True
                except Exception as ex:  # noqa: BLE001
                    last = f"{type(ex).__name__}: {ex}"
            print(f"[video] intento {intento} fallido: {last}", file=sys.stderr, flush=True)
            time.sleep(2)
        return False

    def run(self):
        clock = pygame.time.Clock()
        self.t0, self.why, self.fails = time.time(), "", 0
        self._signals()
        try:   # si el bucle se queda parado, la pila de TODOS los hilos queda en hub.log; también a demanda: kill -USR2 <pid>
            import faulthandler
            import signal
            faulthandler.register(signal.SIGUSR2, file=sys.stderr, all_threads=True)
            self._fh = faulthandler
        except (ImportError, AttributeError, ValueError, OSError, RuntimeError):
            self._fh = None
        threading.Thread(target=self._vivo, daemon=True).start()
        self.perf.start_sampler()
        self._watch_display_quit()
        print("[inicio] Hub en marcha (SIGHUP/SIGPIPE ignoradas; el motivo de cualquier cierre queda como [salida])", file=sys.stderr, flush=True)
        try:
            while self.running:
                dt = clock.tick(self.target_fps()) / 1000.0
                self.fps = clock.get_fps()
                if self._fh:
                    self._fh.dump_traceback_later(20, repeat=True, file=sys.stderr)   # se reinicia cada fotograma: solo salta si Hub lleva 20 s sin dibujar
                try:
                    self.frame(dt)
                    if self.perf.on:
                        tf = time.perf_counter()
                        pygame.display.flip()
                        self.perf.cycle(dt * 1000, (time.perf_counter() - tf) * 1000, self)
                    else:
                        pygame.display.flip()
                    self.fails = 0
                except Exception as ex:  # noqa: BLE001
                    import traceback
                    if isinstance(ex, pygame.error) and (not pygame.display.get_init() or any(k in str(ex) for k in ("not initialized", "Surface quit", "display Surface"))):
                        print(f"[video] el fotograma lanzó pygame.error: {ex}\n{traceback.format_exc()}", file=sys.stderr, flush=True)
                        self._quiet_display_quit()
                        if self._recover_video():
                            continue
                        self.why = "se perdió el sistema de vídeo y no se pudo reabrir la ventana"
                        break
                    self.fails += 1
                    print(f"[error] excepción en un fotograma ({self.fails}):\n{traceback.format_exc()}", file=sys.stderr, flush=True)
                    if self.fails == 5:
                        self._safe_reset()
                    if self.fails >= 30:
                        self.why = "30 excepciones seguidas en la interfaz"
                        break
                    time.sleep(0.1)
        finally:
            self.running = False
            if getattr(self, "_fh", None):
                self._fh.cancel_dump_traceback_later()
            print(f"[salida] Hub termina tras {time.time() - self.t0:.0f}s · motivo: {self.why or 'no registrado (¿cierre normal desde la UI?)'}", file=sys.stderr, flush=True)
            self.mgr.shutdown()
            try:
                if self.brow_proc and self.brow_proc.poll() is None and self.cfg.get("browser") == "hub":
                    os.killpg(self.brow_proc.pid, 9)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            self._kill_descendants(self.game_pids)

    # ── pantalla: juegos ──
    # ── pantallas pensadas para mando: pocas opciones, tarjetas grandes ──
    @staticmethod
    def tint(name, v=0.34, sat=0.55):
        import colorsys
        h = (sum(ord(c) * (i + 3) for i, c in enumerate(name)) % 360) / 360.0
        return tuple(int(255 * c) for c in colorsys.hsv_to_rgb(h, sat, v))

    def tile(self, key, rect, title, sub, cb, color=None, x=None, y=None, big=26, badge="", cover=None, logo=None):
        r, foc = self.reg(key, rect, cb, True, None, x, y)
        base = color or PANEL
        if foc:
            base = tuple(min(255, c + 16) for c in base)
        self.rr(r, base, 26 * RADK, a=(170 if color else None) if GLASS else None)
        if OUTLINE:
            self.rr(r, LINE, 26 * RADK, max(1, self.n(2)))
        if cover is not None:
            self.screen.blit(cover, r)
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 30 * RADK, max(3, self.n(4)))
        tc = on_color(base) if color else TXT
        ty = self.para(title, r.x + self.n(24), r.y + self.n(22), big, r.w - self.n(48), tc, True, 2)
        if sub:
            self.text(sub, r.x + self.n(24), ty + self.n(4), 19, (TILE_SUB if tc == (255, 255, 255) else tc) if color else DIM, maxw=r.w - self.n(48))
        if badge:
            bw = self.font(18, True).size(badge)[0] + self.n(28)
            pr = pygame.Rect(r.x + self.n(24), r.bottom - self.n(58), bw, self.n(36))
            self.rr(pr, (0, 0, 0), 18)
            self.text(badge, pr.centerx, pr.centery, 18, (255, 255, 255), True, anchor="c")
        if logo is not None:                       # logo de la consola (PRO100BYTE/console-logos) sobre una placa oscura abajo a la derecha
            pw, ph = logo.get_width() + self.n(24), logo.get_height() + self.n(16)
            plate = pygame.Rect(r.right - pw - self.n(16), r.bottom - ph - self.n(14), pw, ph)
            self.rr(plate, (240, 243, 247), 14)
            self.screen.blit(logo, logo.get_rect(center=plate.center))
        return r

    @staticmethod
    def ago(t):
        d = max(0, time.time() - t)
        return "hace un momento" if d < 90 else f"hace {int(d // 60)} min" if d < 3600 else f"hace {int(d // 3600)} h" if d < 172800 else f"hace {int(d // 86400)} días"










    def gh_web_login(self):
        """Abre GitHub en el navegador elegido (el navegador conserva su propia sesión)."""
        if ghcookies.saved():
            self.open_url("https://github.com/")
            return
        self.open_url("https://github.com/login")
        self.toast("Tras entrar, queda guardada en ese navegador. O importa cookies: Ajustes → Avanzado → GitHub")

    def gh_cookies_import(self):
        def done(p):
            try:
                f, user = ghcookies.import_file(p)
            except (ValueError, OSError) as ex:
                self.toast(f"Cookies: {ex}")
                return
            self.toast(f"Cookies de GitHub guardadas{(' (' + user + ')') if user else ''}: .env del launcher + {f.name}")
        self.open_picker("Elige el .json exportado con Cookie-Editor", self._first_dir(), {".json"}, done)

    def gh_cookies_forget(self):
        ghcookies.forget()
        self.toast("Cookies de GitHub borradas de Hub (cierra también la sesión en github.com/settings/sessions)")

    def open_repo_web(self, text):
        t = (text or "").strip().rstrip("/")
        m = re.search(r"github\.com/([\w.-]+/[\w.-]+)", t) or re.fullmatch(r"([\w.-]+/[\w.-]+)", t)
        if not m:
            self.toast("Escribe owner/repo o la URL del repositorio")
            return
        self.open_url("https://github.com/" + m.group(1).removesuffix(".git"))





    # ── pantalla: detalle ──

    # ── pantalla: buscar repos ──

    def paste_repo(self):
        r = catalog.repo_of(self.clipboard())
        if r:
            self.open_repo(r)
        else:
            self.osk("Repositorio (owner/repo o URL de GitHub)", lambda t: catalog.repo_of(t) and self.open_repo(catalog.repo_of(t)) or self.toast("No es un repositorio válido"),
                     "", "ej.: z3xox/Tenkaichi3Decomp")

    # ── pantalla: repositorio elegido ("este") ──

    # ── pantalla: descargas ──
    def disc(self, cx, cy, rad, col):
        """Círculo relleno con bordes suaves (a 4× y reducido; se guarda por radio y color)."""
        key = (int(rad), tuple(col))
        c = getattr(self, "_disc_c", None)
        if c is None or len(c) > 200:
            c = self._disc_c = {}
        sf = c.get(key)
        if sf is None:
            S, size = 4, int(rad) * 2 + 4
            big = pygame.Surface((size * S, size * S), pygame.SRCALPHA)
            pygame.draw.circle(big, (*col, 255), (size * S // 2, size * S // 2), int(rad) * S)
            sf = c[key] = pygame.transform.smoothscale(big, (size, size))
        self.screen.blit(sf, (int(cx - sf.get_width() / 2), int(cy - sf.get_height() / 2)))

    def ring_progress(self, cx, cy, rad, frac, col, track=None, th=None):
        """Anillo de progreso con bordes suaves: se dibuja 4 veces más grande y se reduce (una vez por combinación; se guarda)."""
        th = th or max(4, self.n(7))
        frac = max(0.0, min(1.0, frac))
        q = round(frac * 120)                                  # 120 pasos: el anillo avanza sin saltos visibles y la caché no crece sin fin
        key = (rad, th, q, tuple(col), tuple(track or BG))
        c = getattr(self, "_ring_c", None)
        if c is None or len(c) > 400:
            c = self._ring_c = {}
        sf = c.get(key)
        if sf is None:
            S = 4
            size = (2 * rad + 4) * S
            big = pygame.Surface((size, size), pygame.SRCALPHA)
            m = size // 2
            R = rad * S
            T = th * S
            pygame.draw.circle(big, (*(track or BG), 255), (m, m), R, T)
            if q > 0:
                r_mid = R - T / 2
                steps = max(8, int(160 * q / 120))
                outer, inner = [], []
                for i in range(steps + 1):
                    ang = -math.pi / 2 + 2 * math.pi * (q / 120) * i / steps
                    outer.append((m + R * math.cos(ang), m + R * math.sin(ang)))
                    inner.append((m + (R - T) * math.cos(ang), m + (R - T) * math.sin(ang)))
                pygame.draw.polygon(big, (*col, 255), outer + inner[::-1])
                for ang in (-math.pi / 2, -math.pi / 2 + 2 * math.pi * (q / 120)):     # extremos redondeados
                    pygame.draw.circle(big, (*col, 255), (m + r_mid * math.cos(ang), m + r_mid * math.sin(ang)), T / 2)
            sf = pygame.transform.smoothscale(big, (size // S, size // S))
            c[key] = sf
        self.screen.blit(sf, (cx - sf.get_width() // 2, cy - sf.get_height() // 2))

    def glyph(self, kind, cx, cy, sz, col):
        """Iconos dibujados con formas (no dependen de que la fuente tenga el carácter). Los de línea fina se dibujan a 4× y se reducen: sin escalones."""
        if kind in ("check", "cross", "dots", "down", "gear") and sz >= 12:
            key = (kind, int(sz), tuple(col))
            box = int(sz * 2.4)
            c = getattr(self, "_gly_c", None)
            if c is None or len(c) > 200:
                c = self._gly_c = {}
            sf = c.get(key)
            if sf is None:
                S = 4
                big = pygame.Surface((box * S, box * S), pygame.SRCALPHA)
                self._glyph_raw(kind, box * S // 2, box * S // 2, sz * S, col, big)
                sf = c[key] = pygame.transform.smoothscale(big, (box, box))
            self.screen.blit(sf, (int(cx - box / 2), int(cy - box / 2)))
            return
        self._glyph_raw(kind, cx, cy, sz, col, None)

    def _glyph_raw(self, kind, cx, cy, sz, col, d=None):
        w = max(3, sz // 7)
        d = d if d is not None else self.screen
        if kind == "check":
            pygame.draw.lines(d, col, False, [(cx - sz * .5, cy), (cx - sz * .12, cy + sz * .38), (cx + sz * .52, cy - sz * .4)], w)
        elif kind == "down":
            pygame.draw.line(d, col, (cx, cy - sz * .5), (cx, cy + sz * .3), w)
            pygame.draw.polygon(d, col, [(cx - sz * .42, cy + sz * .08), (cx + sz * .42, cy + sz * .08), (cx, cy + sz * .55)])
        elif kind == "cross":
            pygame.draw.line(d, col, (cx - sz * .4, cy - sz * .4), (cx + sz * .4, cy + sz * .4), w)
            pygame.draw.line(d, col, (cx - sz * .4, cy + sz * .4), (cx + sz * .4, cy - sz * .4), w)
        elif kind == "dots":
            for i in (-1, 0, 1):
                pygame.draw.circle(d, col, (cx + i * sz * .5, cy), max(2, w * .6))
        elif kind == "gear":
            pygame.draw.circle(d, col, (cx, cy), sz * .42, w)
            for i in range(8):
                ang = i * math.pi / 4
                pygame.draw.line(d, col, (cx + math.cos(ang) * sz * .42, cy + math.sin(ang) * sz * .42), (cx + math.cos(ang) * sz * .62, cy + math.sin(ang) * sz * .62), w)
        elif kind == "file":
            pygame.draw.rect(d, col, (cx - sz * .38, cy - sz * .5, sz * .76, sz), w, border_radius=max(2, w))
            pygame.draw.line(d, col, (cx - sz * .2, cy), (cx + sz * .2, cy), max(2, w - 1))
            pygame.draw.line(d, col, (cx - sz * .2, cy + sz * .25), (cx + sz * .2, cy + sz * .25), max(2, w - 1))
        elif kind == "pause":
            for dx in (-.22, .22):
                pygame.draw.rect(d, col, (cx + dx * sz - w / 2, cy - sz * .4, w, sz * .8), border_radius=2)



    def show_log(self, b):
        self.modal = {"kind": "log", "job": b, "prev": self.focus}
        self.focus = None
        self.views.setdefault("log", View()).off = 1e9

    def _log_title_slug(self):
        t = str((self.modal or {}).get("job").title if self.modal else "registro")
        return re.sub(r"[^\w.-]+", "-", t).strip("-").lower()[:40] or "registro"

    def log_copy(self):
        """COPIAR del visor: lo que se ve ahora (con o sin ruido) al portapapeles."""
        m = self.modal
        if not m or m.get("kind") != "log":
            return
        txt = "\n".join(logview.lines(m["job"].log, m.get("quiet", True)))
        try:
            pygame.scrap.put_text(txt)
            self.toast(f"Copiado: {len(txt.splitlines())} líneas")
        except Exception:  # noqa: BLE001
            self.toast("No pude copiar al portapapeles: usa GUARDAR")

    def log_save(self):
        """GUARDAR del visor: el registro COMPLETO (sin códigos de color, con el ruido) en ~/hub-log-<título>.txt para adjuntarlo."""
        m = self.modal
        if not m or m.get("kind") != "log":
            return
        p = Path.home() / f"hub-log-{self._log_title_slug()}.txt"
        try:
            p.write_text("\n".join(logview.lines(m["job"].log, False)) + "\n", encoding="utf-8")
            self.toast(f"Guardado en {p}")
        except OSError as ex:
            self.toast(f"No pude guardar: {ex}")

    def log_noise(self):
        if self.modal:
            self.modal["quiet"] = not self.modal.get("quiet", True)

    def log_jump(self, end):
        if self.modal:
            self.modal["follow"] = bool(end)
            self.views.setdefault("log", View()).off = 1e9 if end else 0

    class _TextLog:
        """Lo mínimo que pide el visor de registros (el mismo de las compilaciones) para mostrar un texto."""
        state, stage = "done", ""

        def __init__(self, title, path, text):
            self.title, self.logfile, self.log = title, path, text.splitlines()

    def show_launchlog(self, e=None):
        f = launchlog.latest(self.inst(e)["launcher_id"]) if e else launchlog.latest()
        if not f:
            self.toast("No hay arranques fallidos guardados")
            return
        self.show_log(self._TextLog("Último arranque fallido", f, f.read_text(encoding="utf-8", errors="replace")))

    def export_diag(self, e):
        """EXPORTAR DIAGNÓSTICO: junta todos los registros del juego en ~/diag-<id>.md (en un hilo, con rueda) y lo muestra."""
        inf = self.inst(e)
        lid = inf["launcher_id"]

        def done(p, err):
            if err or not p:
                self.toast(f"No pude exportar el diagnóstico: {err}")
                return
            try:
                txt = Path(p).read_text(encoding="utf-8")
            except OSError:
                txt = ""
            self.toast(f"Diagnóstico guardado en {p}  (adjúntalo en el chat)")
            self._rcp_q.append(lambda: self.show_log(self._TextLog("Diagnóstico de " + e["name"], Path(p), txt)))
        self.work("Reuniendo registros de " + e["name"] + "…", lambda: diag.build(lid, e["name"], e.get("folder", e["id"]), inf.get("version", "")), done)

    def show_history(self, e):
        lid = self.inst(e)["launcher_id"]
        self.show_log(self._TextLog("Historial de " + e["name"], history._file(lid), history.text(lid, e["name"])))

    def send_launchlogs(self):
        """Junta los últimos informes en ENVIAR.md, lo copia al portapapeles y dice dónde está."""
        launchlog.scan_orphans()
        p = launchlog.bundle()
        try:
            pygame.scrap.put_text(p.read_text(encoding="utf-8"))
            cop = " y copiado al portapapeles"
        except Exception:  # noqa: BLE001
            cop = ""
        self.toast(f"Preparado{cop}: {p}  (o en una terminal: bin/hub-logs)")
        self.show_log(self._TextLog("Registros de arranque (lo que me tienes que enviar)", p, p.read_text(encoding="utf-8")))

    def build_x(self, b):
        if b.state in ("queued", "running"):
            self.confirm("¿Cancelar la compilación?", f"{b.title}\nSe detiene el proceso de Hub; no se borra nada.", b.cancel)
        else:
            self.builds = [x for x in self.builds if x is not b]

    def dl_main(self, d):
        if getattr(d, "catalog", False):
            e = self.entry(d.entry_id)
            if d.state == "done" and e:
                self.rview, self.tab = None, "games"
                self.open_detail(e)
            return
        if d.state in ("active", "queued"):
            self.mgr.pause(d.id)
        elif d.state in ("paused", "error", "cancelled"):
            self.mgr.resume(d.id)
        else:
            if d.meta.get("install_setup") and getattr(d, "path", None) and Path(d.path).is_file():     # v2.96: VER vuelve al menú del instalador
                es = self.entry(d.meta["install_setup"])
                if es:
                    self.setup_menu(es, d.path, d.meta.get("lid"))
                    return
            e = self.entry(d.meta.get("install") or d.meta.get("install_win") or d.meta.get("install_setup") or d.meta.get("entry") or "")
            if e:
                self.rview, self.tab = None, "games"
                self.open_detail(e)

    def dl_cancel(self, d):
        if getattr(d, "catalog", False):
            if d.state in ("done", "cancelled", "error"):
                self.cjobs.remove(d.id)
            else:
                self.confirm("¿Cancelar descarga?", f"{d.name}\nSe le pide a tu servidor que la detenga.", lambda: self.cjobs.cancel(d.id))
            return
        if d.state in ("done", "cancelled", "error"):
            self.mgr.remove(d.id)
        else:
            self.confirm("¿Cancelar descarga?", f"{d.meta.get('title') or d.name}\nSe borrará solo el archivo parcial de esta descarga.",
                         lambda: self.mgr.cancel(d.id))

    # ── pantalla: ajustes ──


    def _first_dir(self):
        for d in self.cfg["watch_dirs"]:
            p = Path(os.path.expandvars(str(d))).expanduser()
            if p.is_dir():
                return p
        return Path.home()

    def import_list(self, src):
        def job():
            try:
                if str(src) == "recomplauncher:":
                    dest, n = recompsite.import_catalog(lambda i, t: self.toast(f"RecompLauncher: leyendo {i}/{t}…") if i % 20 == 0 else None)
                else:
                    dest, n = catalog.import_source(str(src))
                self.reload()
                self.toast(f"{n} juegos importados ({Path(dest).name})")
            except Exception as ex:  # noqa: BLE001
                self.toast(f"No pude importar: {ex}")
        self.toast("Importando…")
        threading.Thread(target=job, daemon=True).start()

    def add_repo(self, text):
        repo = catalog.repo_of(text)
        if not repo:
            self.toast("Eso no parece un repositorio (usa owner/repo o la URL de GitHub)")
            return
        name = repo.split("/")[1]
        catalog.add_local({"name": name, "repo": repo, "folder": name})
        self.reload()
        self.toast(f"Añadido {repo}")

    # ── modales: dibujo ──

