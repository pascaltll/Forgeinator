"""Eight curated identities for the v3 theme catalog."""
from ..schema import ThemePreset

PRESETS = {
    "minimal": ThemePreset("minimal", "Minimal", "Clean library, strong hierarchy, little decoration", "essential", "posters", ("posters", "grid", "list"), "obsidian", ("obsidian", "ocean", "emerald", "violet", "paper", "cloud"), "solid", ("clean", "library")),
    "showcase": ThemePreset("showcase", "Showcase", "Featured game, editorial hero, and shelves", "premium", "hero", ("hero", "shelf", "posters", "grid"), "ocean", ("ocean", "obsidian", "sunset", "emerald", "violet"), "solid", ("cinematic", "featured")),
    "glass": ThemePreset("glass", "Glass", "Layered translucent panels and atmospheric depth", "premium", "mosaic", ("mosaic", "grid", "coverflow", "hero"), "ocean", ("ocean", "violet", "emerald", "sunset", "neon"), "glass", ("translucent", "depth")),
    "flow": ThemePreset("flow", "Flow", "Horizontal console navigation and flowing covers", "console", "xmb", ("xmb", "coverflow", "shelf", "posters"), "ocean", ("ocean", "violet", "sunset", "obsidian"), "soft", ("horizontal", "console")),
    "arcade": ThemePreset("arcade", "Arcade", "Pixel-era details, numbered slots, and vivid accents", "retro", "slots", ("slots", "grid", "list"), "neon", ("neon", "lcd", "sunset", "obsidian"), "arcade", ("retro", "pixel", "arcade")),
    "terminal": ThemePreset("terminal", "Terminal", "Monospaced catalog with crisp CRT-inspired details", "retro", "list", ("list", "grid"), "lcd", ("lcd", "neon", "obsidian", "ocean"), "outline", ("crt", "monospace")),
    "editorial": ThemePreset("editorial", "Editorial", "Paper-like catalog, typography, and index structure", "expressive", "list", ("list", "posters", "shelf"), "paper", ("paper", "cloud", "obsidian"), "paper", ("paper", "serif")),
    "brutalist": ThemePreset("brutalist", "Brutalist", "Bold blocks, oversized numbers, and graphic contrast", "expressive", "blocks", ("blocks", "grid", "slots"), "neon", ("neon", "sunset", "paper", "obsidian"), "outline", ("bold", "graphic")),
}
PRESET_ORDER = tuple(PRESETS)
