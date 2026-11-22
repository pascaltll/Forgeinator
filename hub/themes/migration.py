"""Read-only migration adapter for Recomp Hub v2.85 appearance settings."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from .registry import PRESETS, PALETTES
from .schema import SCHEMA_VERSION

# Explicit legacy mappings. Preserve source values where they can be represented safely.
LEGACY_PRESETS = {
    "dark": ("minimal", "obsidian", "grid"), "light": ("minimal", "cloud", "posters"),
    "limpio": ("minimal", "obsidian", "posters"), "quiver": ("minimal", "obsidian", "list"),
    "prototipo": ("showcase", "sunset", "hero"), "cristal": ("glass", "ocean", "mosaic"),
    "aurora": ("glass", "violet", "mosaic"), "onda": ("flow", "ocean", "xmb"),
    "tarjeta": ("arcade", "neon", "slots"), "cubo": ("flow", "violet", "coverflow"),
    "interruptor": ("minimal", "cloud", "posters"), "brasa": ("showcase", "sunset", "shelf"),
    "pixel": ("arcade", "lcd", "slots"), "retro16": ("arcade", "neon", "slots"),
    "neon": ("arcade", "neon", "grid"), "fosforo": ("terminal", "lcd", "list"),
    "tinta": ("editorial", "paper", "list"), "bloque": ("brutalist", "neon", "blocks"),
    # v3.10: Obsidian (familia heredada nº 15 desde v2.93) es Minimal con la paleta obsidian: mismos colores, portadas y sin animación
    "obsidian": ("minimal", "obsidian", "posters"),
}
LEGACY_SOURCE_FAMILY = {
    "dark": "limpio", "light": "limpio", "aurora": "cristal", "retro16": "pixel",
}
LEGACY_PALETTES = {
    "claro": "cloud", "oscuro": "obsidian", "azul": "ocean", "celeste": "ocean",
    "8bits": "lcd", "16bits": "neon", "rojoazul": "sunset", "naranja": "sunset",
    "amarillo": "sunset", "verde": "emerald", "rosa": "sunset",
    "oceano": "ocean", "menta": "emerald", "rosa": "sunset", "grafito": "obsidian",
    "esmeralda": "emerald", "violeta": "violet", "ambar": "sunset", "atardecer": "sunset",
    "dorado": "sunset", "hielo": "ocean", "bosque": "emerald", "oro": "sunset",
    "gameboy": "lcd", "lima": "emerald", "sol": "sunset", "mono": "obsidian",
    "crema": "paper", "sepia": "paper", "azulpapel": "cloud", "nocturno": "obsidian",
}
LEGACY_LAYOUTS = {
    "grid": "grid", "posters": "posters", "list": "list", "hero": "hero", "orbs": "mosaic",
    "xmb": "xmb", "slots": "slots", "coverflow": "coverflow", "switch": "posters",
    "blocks": "blocks",
}
LEGACY_ANIMATIONS = {"none", "motes", "drift", "aurora", "stars", "embers", "gridrun", "scanbar", "shapes", "silk", "cubes", "spincube", "diag"}


def migrate_v285(old: Mapping[str, Any]) -> dict[str, Any]:
    """Translate v2.85's theme/pals/bgs/fx values without mutating `old`.

    This is intentionally conservative: unsupported legacy customizations are recorded
    under `migration_notes` rather than silently reinterpreted as unrelated settings.
    """
    old = old if isinstance(old, Mapping) else {}
    old_theme = str(old.get("theme", "dark"))
    preset, default_palette, layout = LEGACY_PRESETS.get(old_theme, LEGACY_PRESETS["dark"])
    old_pals = old.get("pals", {}) if isinstance(old.get("pals", {}), Mapping) else {}
    old_bgs = old.get("bgs", {}) if isinstance(old.get("bgs", {}), Mapping) else {}
    source_family = LEGACY_SOURCE_FAMILY.get(old_theme, old_theme)
    legacy_palette = old_pals.get(old_theme, old_pals.get(source_family))
    palette = LEGACY_PALETTES.get(str(legacy_palette), default_palette)
    if palette not in PRESETS[preset].supported_palettes:
        palette = default_palette
    legacy_bg = old_bgs.get(old_theme, old_bgs.get(source_family))
    motion_bg = legacy_bg if legacy_bg in LEGACY_ANIMATIONS else "none"
    old_fx = old.get("fx", "glass")
    render = {"quality": "low" if old_fx == "perf" else "auto", "blur_enabled": old_fx != "perf"}
    result = {
        "schema_version": SCHEMA_VERSION,
        "active_preset": preset,
        "appearance": {
            "layout": layout,
            "palette": {"id": palette, "mode": PALETTES[palette].mode},
            "material": "glass" if old_theme in {"cristal", "aurora", "onda"} else "solid",
            "motion": {"background": motion_bg, "intensity": 0.5, "speed": 1.0, "reduce_motion": False},
            "audio": {"enabled": True, "profile": "soft", "volume": 0.65},
            "render": render,
        },
        "migration_notes": {
            "source": "v2.85",
            "legacy_theme": old_theme,
            "legacy_source_family": source_family,
            "legacy_palette": legacy_palette,
            "legacy_background": legacy_bg,
            "legacy_fx": old_fx,
            "unmapped_keys": [],
        },
    }
    return result
