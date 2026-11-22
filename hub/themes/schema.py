"""Typed, versioned data contracts for Recomp Hub's appearance engine.

Pure Python: deliberately has no pygame/UI dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ThemePreset:
    id: str
    label: str
    description: str
    category: str
    default_layout: str
    supported_layouts: tuple[str, ...]
    default_palette: str
    supported_palettes: tuple[str, ...]
    default_material: str = "solid"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Palette:
    id: str
    label: str
    mode: str
    colors: Mapping[str, tuple[int, int, int]]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Layout:
    id: str
    label: str
    renderer: str
    capabilities: tuple[str, ...]
    supported_families: tuple[str, ...] = ()


@dataclass(frozen=True)
class Material:
    id: str
    label: str
    opacity: float
    blur: float
    shadow: float
    border_width: float
    radius_scale: float
    description: str = ""


@dataclass(frozen=True)
class Appearance:
    """Resolved appearance. All fields are normalized and safe to apply."""
    schema_version: int
    preset: str
    family: str
    layout: str
    palette: str
    palette_mode: str
    material: str
    colors: Mapping[str, tuple[int, int, int]]
    geometry: Mapping[str, Any] = field(default_factory=dict)
    typography: Mapping[str, Any] = field(default_factory=dict)
    motion: Mapping[str, Any] = field(default_factory=dict)
    audio: Mapping[str, Any] = field(default_factory=dict)
    render: Mapping[str, Any] = field(default_factory=dict)
    accessibility: Mapping[str, Any] = field(default_factory=dict)
    custom: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_preset": self.preset,
            "appearance": {
                "family": self.family,
                "layout": self.layout,
                "palette": {"id": self.palette, "mode": self.palette_mode},
                "material": self.material,
                "colors": {k: list(v) for k, v in self.colors.items()},
                "geometry": dict(self.geometry),
                "typography": dict(self.typography),
                "motion": dict(self.motion),
                "audio": dict(self.audio),
                "render": dict(self.render),
                "accessibility": dict(self.accessibility),
                "custom": dict(self.custom),
            },
        }


class ThemeValidationError(ValueError):
    """Raised when a theme definition or user override is invalid."""


def rgb(value: Any, *, key: str = "color") -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ThemeValidationError(f"{key}: expected RGB triplet")
    out = []
    for channel in value:
        if isinstance(channel, bool) or not isinstance(channel, (int, float)):
            raise ThemeValidationError(f"{key}: RGB channels must be numbers")
        if int(channel) != channel or not 0 <= int(channel) <= 255:
            raise ThemeValidationError(f"{key}: RGB channel outside 0..255")
        out.append(int(channel))
    return tuple(out)  # type: ignore[return-value]


def bounded_number(value: Any, default: float, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(low, min(high, float(value)))


def mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
