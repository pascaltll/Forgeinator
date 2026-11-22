"""Public API for Recomp Hub Theme Engine Foundation."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from collections.abc import Mapping
from typing import Any
from .resolver import resolve
from .schema import SCHEMA_VERSION, ThemeValidationError


class ThemeEngine:
    def __init__(self, config: Mapping[str, Any] | None = None):
        self._config = dict(config or {})
        self._resolved = resolve(self._config)

    @property
    def appearance(self):
        return self._resolved

    def set_config(self, config: Mapping[str, Any]):
        # Resolve before mutating state: invalid color values cannot partially apply.
        candidate = resolve(config)
        self._config = dict(config)
        self._resolved = candidate
        return candidate

    def update(self, *, preset: str | None = None, layout: str | None = None,
               palette: str | None = None, material: str | None = None,
               overrides: Mapping[str, Any] | None = None):
        from .registry import PRESETS
        config = dict(self._config)
        if preset is not None:
            config["active_preset"] = preset
        appearance = dict(config.get("appearance", {}))
        if layout is not None:
            appearance["layout"] = layout
        if palette is not None:
            p = dict(appearance.get("palette", {})); p["id"] = palette
            appearance["palette"] = p
        if material is not None:
            appearance["material"] = material
        if overrides is not None:
            # Merge per dimension, preserving unrelated settings.
            for key, value in overrides.items():
                if isinstance(value, Mapping) and isinstance(appearance.get(key), Mapping):
                    merged = dict(appearance[key]); merged.update(value); appearance[key] = merged
                else:
                    appearance[key] = value
        config["appearance"] = appearance
        return self.set_config(config)

    def to_dict(self) -> dict[str, Any]:
        return self._resolved.to_dict()


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"schema_version": SCHEMA_VERSION, "active_preset": "minimal", "appearance": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ThemeValidationError(f"Cannot read appearance config: {exc}") from exc
    if not isinstance(data, dict):
        raise ThemeValidationError("Appearance config root must be an object")
    return data


def save_config(path: str | os.PathLike[str], config: Mapping[str, Any]) -> None:
    """Atomic JSON write. Existing file is untouched if serialization/write fails."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(config), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, p)
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise
