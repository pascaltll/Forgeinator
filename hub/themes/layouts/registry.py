"""Layout catalog. Layout IDs describe content organization, not visual skin."""
from ..schema import Layout

LAYOUTS = {
    "grid": Layout("grid", "Grid", "grid", ("covers", "keyboard", "gamepad")),
    "posters": Layout("posters", "Posters", "posters", ("covers", "keyboard", "gamepad")),
    "list": Layout("list", "List", "list", ("text", "covers", "gamepad")),
    "hero": Layout("hero", "Hero", "hero", ("featured", "covers", "gamepad")),
    "coverflow": Layout("coverflow", "Coverflow", "coverflow", ("covers", "depth", "animation", "gamepad")),
    "xmb": Layout("xmb", "XMB", "xmb", ("covers", "horizontal", "gamepad")),
    "slots": Layout("slots", "Slots", "slots", ("covers", "numbering", "gamepad")),
    "shelf": Layout("shelf", "Shelf", "shelf", ("covers", "rows", "gamepad")),
    "mosaic": Layout("mosaic", "Mosaic", "mosaic", ("covers", "depth", "gamepad")),
    "blocks": Layout("blocks", "Blocks", "blocks", ("text", "numbering", "gamepad")),
}
