"""Accesibilidad y nivel de calidad (v3.09, tanda 1 de temas). Funciones puras sobre el dict de tema que dibuja el Hub.

Con las tres opciones apagadas el dict sale IDÉNTICO (los 15 temas heredados se ven píxel a píxel como antes). Con alguna encendida
se aplica igual a TODOS los temas, heredados y del Estudio:
  · reduce_motion — sin fondo animado; además la UI quita entradas escalonadas, fundidos, destellos, latido del foco y saltos (ui.py/ui_fx.py).
  · high_contrast — texto, texto secundario, líneas, acento y foco con contraste suficiente; paneles opacos con contorno, sin brillos ni tramas.
  · large_text    — toda la letra ×1,2 (FONTK).
Calidad (cfg «fx»): glass = alta · balanced = equilibrada (fondo quieto, sin destellos; blur de menús y materiales sí) · perf = rendimiento."""
from __future__ import annotations

FLAGS = ("reduce_motion", "high_contrast", "large_text")
LARGE_TEXT = 1.2
FX_LEVELS = ("glass", "balanced", "perf")          # orden del ciclo en Ajustes
FX_RANK = {"glass": 2, "balanced": 1, "perf": 0}

# objetivos de contraste (WCAG 2.1): texto normal 7:1 (AAA), secundario 4.5:1 (AA), componentes y foco 3:1 (1.4.11)
TXT_MIN, DIM_MIN, UI_MIN, STATE_MIN = 7.0, 4.5, 3.0, 4.5


def flags(cfg) -> dict:
    cfg = cfg or {}
    return {k: bool(cfg.get(k, False)) for k in FLAGS}


def fx_level(fx) -> int:
    """2 = alta (todo), 1 = equilibrada, 0 = rendimiento. Valor desconocido = alta (lo que hacía antes cualquier cosa ≠ «perf»)."""
    return FX_RANK.get(fx, 2)


def next_fx(fx) -> str:
    cur = fx if fx in FX_LEVELS else "glass"
    return FX_LEVELS[(FX_LEVELS.index(cur) + 1) % len(FX_LEVELS)]


def lum(c) -> float:
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(a, b) -> float:
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def is_light(c) -> bool:
    return lum(c) > 0.4


def _mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def push(col, against, target, toward=None):
    """El color más parecido a `col` (mezclándolo hacia blanco o negro) que alcanza `target` de contraste contra todos los `against`."""
    against = [tuple(x) for x in against if x]
    col = tuple(col)
    if all(contrast(col, a) >= target for a in against):
        return col
    if toward is None:
        toward = (255, 255, 255) if not is_light(against[0]) else (0, 0, 0)
    for k in range(1, 21):
        c = _mix(col, toward, k / 20)
        if all(contrast(c, a) >= target for a in against):
            return c
    return tuple(toward)


def high_contrast(t: dict) -> dict:
    t = dict(t)
    bgs = [t["BG"], t["PANEL"], t["PANEL2"]]
    t["TXT"] = push(t["TXT"], bgs, TXT_MIN)
    far = (255, 255, 255) if not is_light(t["TXT"]) else (0, 0, 0)       # lo contrario del texto
    for k in ("BG", "PANEL", "PANEL2", "SEG"):     # ni el blanco/negro puro llega (paneles saturados): se separa el panel
        if t.get(k) and contrast(t["TXT"], t[k]) < TXT_MIN:
            t[k] = push(t[k], [t["TXT"]], TXT_MIN, toward=far)
    bgs = [t["BG"], t["PANEL"], t["PANEL2"]]
    t["DIM"] = push(t["DIM"], bgs, DIM_MIN)
    t["LINE"] = push(t["LINE"], [t["BG"], t["PANEL"]], UI_MIN)
    for k in ("OK", "WARN", "ERR"):
        if t.get(k):
            t[k] = push(t[k], [t["PANEL"]], STATE_MIN)
    t["ACC"] = push(t["ACC"], [t["BG"], t["PANEL"]], UI_MIN)
    t["FOCUS"] = push(t.get("FOCUS") or t["ACC"], [t["BG"], t["PANEL"], t["PANEL2"]], UI_MIN)
    dark = _mix(t["BG"], (0, 0, 0), 0.8)
    t["ON_ACC"] = (255, 255, 255) if contrast((255, 255, 255), t["ACC"]) >= contrast(dark, t["ACC"]) else dark
    t["OUTLINE"], t["GLASS"], t["ORBS"], t["PATTERN"] = True, False, None, None
    if t.get("MAT"):
        t["MAT"] = {**t["MAT"], "opacity": 1.0, "blur": 0.0, "border": max(1.5, t["MAT"].get("border", 0))}
    return t


def apply(t: dict, fl: dict | None) -> dict:
    """Dict de tema + opciones de accesibilidad → dict a dibujar. Sin opciones: el MISMO objeto, sin tocar."""
    if not fl or not any(fl.get(k) for k in FLAGS):
        return t
    t = dict(t)
    if fl.get("reduce_motion"):
        t["ANIM"] = None
    if fl.get("high_contrast"):
        t = high_contrast(t)
    if fl.get("large_text"):
        t["FONTK"] = round(float(t.get("FONTK", 1.0)) * LARGE_TEXT, 3)
    return t
