"""Shared color palettes. Presets may recommend palettes, never own their colors."""
from ..schema import Palette


def _p(pid, label, bg, panel, panel2, line, text, dim, accent, focus=None, mode="dark", tags=()):
    return Palette(pid, label, mode, {
        "BG": bg, "PANEL": panel, "PANEL2": panel2, "LINE": line,
        "TXT": text, "DIM": dim, "ACC": accent,
        "OK": (72, 214, 120) if mode == "dark" else (26, 140, 58),
        "WARN": (255, 184, 64) if mode == "dark" else (184, 108, 0),
        "ERR": (255, 100, 92) if mode == "dark" else (207, 36, 28),
        "FOCUS": focus or accent,
    }, tuple(tags))


PALETTES = {
    "obsidian": _p("obsidian", "Obsidian", (16,17,20), (31,33,39), (43,46,54), (72,76,86), (239,241,246), (164,170,181), (196,196,206), tags=("dark", "neutral")),
    "ocean": _p("ocean", "Ocean", (8,24,39), (18,45,66), (27,61,86), (48,91,119), (230,244,252), (164,194,211), (56,189,248), tags=("dark", "blue")),
    "emerald": _p("emerald", "Emerald", (11,27,22), (25,53,40), (37,72,54), (67,105,80), (232,248,237), (169,203,179), (40,190,130), tags=("dark", "green")),
    "violet": _p("violet", "Violet", (24,17,38), (47,34,70), (62,46,91), (103,82,137), (245,239,255), (190,176,214), (164,122,245), tags=("dark", "purple")),
    "sunset": _p("sunset", "Sunset", (40,19,22), (72,34,39), (91,45,49), (137,75,72), (255,241,233), (216,177,166), (241,140,97), tags=("dark", "warm")),
    "paper": _p("paper", "Paper", (232,220,196), (248,240,224), (239,228,207), (190,171,143), (48,40,31), (112,96,76), (156,105,62), mode="light", tags=("light", "warm")),
    "neon": _p("neon", "Neon", (16,12,38), (36,27,78), (51,39,100), (102,82,158), (246,241,255), (191,180,218), (255,79,203), focus=(60,232,224), tags=("dark", "arcade")),
    "lcd": _p("lcd", "LCD", (15,42,22), (34,75,39), (48,91,48), (87,125,61), (230,244,190), (184,207,132), (167,201,87), tags=("dark", "retro")),
    "cloud": _p("cloud", "Cloud", (239,244,249), (255,255,255), (229,236,243), (190,202,215), (28,39,52), (91,106,122), (31,119,180), mode="light", tags=("light", "neutral")),
}

DEFAULT_PALETTE = "obsidian"
