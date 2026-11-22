"""Single source of truth for theme-engine registries."""
from .presets.catalog import PRESETS, PRESET_ORDER
from .palettes.core import PALETTES
from .layouts.registry import LAYOUTS
from .materials.registry import MATERIALS

REGISTRY = {
    "presets": PRESETS,
    "palettes": PALETTES,
    "layouts": LAYOUTS,
    "materials": MATERIALS,
}
