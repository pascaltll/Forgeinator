"""Recomp Hub Theme Engine Foundation (v3 architecture, phase 1)."""
from .engine import ThemeEngine, load_config, save_config
from .migration import migrate_v285
from .resolver import resolve
from .registry import PRESETS, PALETTES, LAYOUTS, MATERIALS
from .schema import Appearance, ThemeValidationError, SCHEMA_VERSION
from . import legacy, publish, studio  # noqa: F401  (fase A: puente con los temas del Hub)

__all__ = [
    "ThemeEngine", "load_config", "save_config", "migrate_v285", "resolve",
    "PRESETS", "PALETTES", "LAYOUTS", "MATERIALS", "Appearance",
    "ThemeValidationError", "SCHEMA_VERSION", "legacy", "publish", "studio",
]
