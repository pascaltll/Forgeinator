"""Iconos de interfaz de Lucide (lucide-icons/lucide, licencia ISC): PNG blancos de 160 px en assets/icons/, teñidos y escalados bajo demanda."""
from pathlib import Path

import pygame

DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
_base, _c = {}, {}


def available(name) -> bool:
    return (DIR / f"{name}.png").is_file()


def get(name, px, color):
    """Surface del icono `name` de px×px en `color`, o None si no existe."""
    key = (name, px, tuple(color[:3]))
    s = _c.get(key)
    if s is not None:
        return s
    if name not in _base:
        try:
            _base[name] = pygame.image.load(str(DIR / f"{name}.png")).convert_alpha()
        except (OSError, pygame.error):
            _base[name] = None
    b = _base[name]
    if b is None:
        return None
    s = pygame.transform.smoothscale(b, (px, px))
    out = pygame.Surface((px, px), pygame.SRCALPHA)
    out.fill((*color[:3], 255))
    out.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)      # el icono es blanco: MIN deja el color del relleno y el alfa del icono
    if len(_c) > 200:
        _c.clear()
    _c[key] = out
    return out
