"""Defensive validation and sanitization for user-controlled appearance data."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from .schema import ThemeValidationError, bounded_number, rgb

ALLOWED_MOTION = {"none", "motes", "drift", "aurora", "stars", "embers", "gridrun", "scanbar", "shapes", "silk", "cubes", "spincube", "diag"}
ALLOWED_AUDIO = {"soft", "glass", "chip", "wood", "silk", "click", "marimba", "none"}
ALLOWED_SPACING = {"compact", "comfortable", "spacious"}
ALLOWED_FONT = {"system", "serif", "mono", "notosans", "poppins", "chakra", "vt323"}


def validate_overrides(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, Any] = {}
    geom = raw.get("geometry")
    if isinstance(geom, Mapping):
        out["geometry"] = {
            "radius": bounded_number(geom.get("radius"), 12, 0, 32),
            "spacing": geom.get("spacing") if geom.get("spacing") in ALLOWED_SPACING else "comfortable",
            "outline": bool(geom.get("outline", False)),
        }
    typo = raw.get("typography")
    if isinstance(typo, Mapping):
        font = typo.get("family", "system")
        out["typography"] = {
            "family": font if font in ALLOWED_FONT else "system",
            "scale": bounded_number(typo.get("scale"), 1.0, 0.75, 1.5),
            "weight": typo.get("weight") if typo.get("weight") in {"normal", "medium", "bold"} else "normal",
        }
    motion = raw.get("motion")
    if isinstance(motion, Mapping):
        bg = motion.get("background", "none")
        out["motion"] = {
            "background": bg if bg in ALLOWED_MOTION else "none",
            "intensity": bounded_number(motion.get("intensity"), 0.5, 0.0, 1.0),
            "speed": bounded_number(motion.get("speed"), 1.0, 0.1, 2.0),
            "reduce_motion": bool(motion.get("reduce_motion", False)),
        }
    audio = raw.get("audio")
    if isinstance(audio, Mapping):
        profile = audio.get("profile", "soft")
        out["audio"] = {"enabled": bool(audio.get("enabled", True)), "profile": profile if profile in ALLOWED_AUDIO else "soft", "volume": bounded_number(audio.get("volume"), 0.65, 0.0, 1.0)}
    render = raw.get("render")
    if isinstance(render, Mapping):
        out["render"] = {"quality": render.get("quality") if render.get("quality") in {"auto", "high", "balanced", "low"} else "auto", "blur_enabled": bool(render.get("blur_enabled", True))}
    accessibility = raw.get("accessibility")
    if isinstance(accessibility, Mapping):
        out["accessibility"] = {"high_contrast": bool(accessibility.get("high_contrast", False)), "reduce_motion": bool(accessibility.get("reduce_motion", False)), "large_text": bool(accessibility.get("large_text", False))}
    colors = raw.get("colors")
    if isinstance(colors, Mapping):
        out["colors"] = {str(k): rgb(v, key=str(k)) for k, v in colors.items() if k in {"BG", "PANEL", "PANEL2", "LINE", "TXT", "DIM", "ACC", "OK", "WARN", "ERR", "FOCUS"}}
    return out
