"""Publica la apariencia activa en un JSON atómico (`data/appearance.json`) para que otros programas (lanzador, QAM Rail,
la sección de personalización) la lean sin importar Python."""
from __future__ import annotations
from .engine import save_config
from . import legacy


def publish(path, name, pal=None, bg=None, request=None, layout=None, quality=None, a11y=None):
    """`request` = {id, status, errors} de la última petición procesada (se publica como confirmación).
    v3.09: `quality` (cfg fx: glass | balanced | perf) y `a11y` (reduce_motion, high_contrast, large_text) se publican para cualquier tema."""
    from . import studio
    data = (studio.appearance(name, pal, bg, layout, quality=quality, a11y=a11y) if studio.is_studio(name)
            else legacy.appearance(name, pal, bg))
    if quality is not None:
        data["quality"] = quality
    if a11y is not None:
        data["accessibility"] = {k: bool(a11y.get(k)) for k in ("reduce_motion", "high_contrast", "large_text")}
    if request:
        data["request"] = request
    save_config(path, data)
    return data
