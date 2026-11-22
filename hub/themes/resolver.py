"""Deterministic appearance resolver: preset defaults + validated user overrides."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from .registry import PRESETS, PALETTES, LAYOUTS, MATERIALS
from .schema import Appearance, SCHEMA_VERSION, ThemeValidationError
from .validation import validate_overrides


def resolve(config: Mapping[str, Any] | None = None) -> Appearance:
    config = config if isinstance(config, Mapping) else {}
    preset_id = config.get("active_preset", "minimal")
    if preset_id not in PRESETS:
        preset_id = "minimal"
    preset = PRESETS[preset_id]
    raw = config.get("appearance", {})
    raw = raw if isinstance(raw, Mapping) else {}

    family = preset.id
    layout = raw.get("layout", preset.default_layout)
    if layout not in preset.supported_layouts or layout not in LAYOUTS:
        layout = preset.default_layout
    palette_data = raw.get("palette", {})
    palette_data = palette_data if isinstance(palette_data, Mapping) else {}
    palette_id = palette_data.get("id", preset.default_palette)
    if palette_id not in preset.supported_palettes or palette_id not in PALETTES:
        palette_id = preset.default_palette
    palette = PALETTES[palette_id]
    mode = palette_data.get("mode", palette.mode)
    if mode not in {"dark", "light"}:
        mode = palette.mode
    material_id = raw.get("material", preset.default_material)
    if material_id not in MATERIALS:
        material_id = preset.default_material

    clean = validate_overrides(raw)
    colors = dict(palette.colors)
    colors.update(clean.get("colors", {}))
    # A palette's base mode is authoritative unless the selected palette has an explicit light/dark variant.
    if mode != palette.mode:
        # No guessed inversion: retain palette colors and record the requested mode only.
        pass
    return Appearance(
        schema_version=SCHEMA_VERSION, preset=preset_id, family=family,
        layout=layout, palette=palette_id, palette_mode=mode, material=material_id,
        colors=colors,
        geometry=clean.get("geometry", {"radius": 12.0, "spacing": "comfortable", "outline": False}),
        typography=clean.get("typography", {"family": "system", "scale": 1.0, "weight": "normal"}),
        motion=clean.get("motion", {"background": "none", "intensity": 0.5, "speed": 1.0, "reduce_motion": False}),
        audio=clean.get("audio", {"enabled": True, "profile": "soft", "volume": 0.65}),
        render=clean.get("render", {"quality": "auto", "blur_enabled": True}),
        accessibility=clean.get("accessibility", {"high_contrast": False, "reduce_motion": False, "large_text": False}),
    )
