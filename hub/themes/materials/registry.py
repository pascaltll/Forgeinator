"""Surface materials independent from preset, palette, and renderer quality."""
from ..schema import Material

MATERIALS = {
    "solid": Material("solid", "Solid", 1.0, 0.0, 0.18, 1.0, 1.0, "Opaque, restrained surfaces"),
    "glass": Material("glass", "Glass", 0.78, 0.55, 0.30, 1.0, 1.15, "Translucent surfaces; blur is optional at runtime"),
    "soft": Material("soft", "Soft", 0.94, 0.0, 0.12, 0.0, 1.45, "Rounded, low-contrast surfaces"),
    "outline": Material("outline", "Outline", 1.0, 0.0, 0.0, 2.0, 0.45, "Hard edges and visible outlines"),
    "paper": Material("paper", "Paper", 1.0, 0.0, 0.04, 0.5, 0.7, "Flat printed-paper surfaces"),
    "arcade": Material("arcade", "Arcade", 1.0, 0.0, 0.24, 1.5, 0.35, "Hard-edged, high-energy surfaces"),
}
