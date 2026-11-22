"""Logos de plataforma (PRO100BYTE/console-logos, licencia MIT del repositorio; los logos son de sus marcas). Vienen ya incluidos en assets/platform-logos/
(PNG recortados a 100 px de alto, 1,4 MB en total): no hace falta red ni consume la cuota de GitHub. `logo(texto)` devuelve la Surface escalada o None."""
import re
from pathlib import Path

from . import esde

DIR = Path(__file__).resolve().parent.parent / "assets" / "platform-logos"
_N = lambda t: re.sub(r"[^a-z0-9]+", "", str(t).lower())  # noqa: E731
# sistema ES-DE → nombre de archivo (sin .png) cuando el nombre largo de ES-DE no coincide con el del paquete
MAP = {
    "psx": "Sony Playstation", "ps2": "Sony Playstation 2", "ps3": "Sony Playstation 3", "ps4": "Sony Playstation 4", "ps5": "Sony Playstation 5",
    "psp": "Sony PSP", "psvita": "Sony PS Vita", "n64": "Nintendo 64", "gc": "Nintendo GameCube", "wii": "Nintendo Wii", "wiiu": "Nintendo Wii U",
    "switch": "Nintendo Switch", "nds": "Nintendo DS", "n3ds": "Nintendo 3DS", "gba": "Nintendo Game Boy Advance", "gb": "Nintendo Game Boy",
    "gbc": "Nintendo Game Boy Color", "snes": "Super Nintendo Entertainment System", "nes": "Nintendo Entertainment System", "famicom": "Nintendo Famicom",
    "sfc": "Nintendo Super Famicom", "xbox": "Microsoft Xbox", "xbox360": "Microsoft Xbox 360", "xboxone": "Microsoft Xbox One", "dreamcast": "Sega Dreamcast",
    "saturn": "Sega Saturn", "genesis": "Sega Genesis", "megadrive": "Sega Mega Drive", "mastersystem": "Sega Master System", "gamegear": "Sega Game Gear",
    "segacd": "Sega CD", "sega32x": "Sega 32X", "sg-1000": "Sega SG-1000", "pcengine": "NEC TurboGrafx-16", "tg16": "NEC TurboGrafx-16", "tg-cd": "NEC TurboGrafx-CD",
    "pcenginecd": "NEC TurboGrafx-CD", "3do": "3DO Interactive Multiplayer", "atarijaguar": "Atari Jaguar", "atari2600": "Atari 2600", "atari5200": "Atari 5200",
    "atari7800": "Atari 7800", "atarilynx": "Atari Lynx", "atarist": "Atari ST", "neogeo": "SNK Neo Geo", "neogeocd": "SNK Neo Geo CD", "ngp": "SNK Neo Geo Pocket",
    "ngpc": "SNK Neo Geo Pocket Color", "colecovision": "ColecoVision", "intellivision": "Mattel Intellivision", "vectrex": "GCE Vectrex", "virtualboy": "Nintendo Virtual Boy",
    "wonderswan": "WonderSwan", "wonderswancolor": "Wonderswan Color", "pc": "Windows", "windows": "Windows", "dos": "MS-DOS", "steam": "Steam", "scummvm": "ScummVM",
    "mame": "MAME", "arcade": "MAME", "fbneo": "Final Burn Neo", "c64": "Commodore 64", "amiga": "Commodore Amiga", "amigacd32": "Commodore Amiga CD32",
    "zxspectrum": "Sinclair ZX Spectrum", "msx": "Microsoft MSX", "msx2": "Microsoft MSX2", "amstradcpc": "Amstrad CPC", "apple2": "Apple II", "android": "Android",
    "cdi": "Philips CD-i", "pico8": "Pico-8-10", "tic80": "TIC-80", "n3ds-new": "New Nintendo 3DS", "gameandwatch": "Nintendo Game & Watch", "pokemini": "Nintendo Pokémon Mini",
    "stv": "SEGA ST-V", "cps1": "Capcom Play System", "atomiswave": "Sammy Atomiswave", "naomigd": "Sega Naomi", "sufami": "Nintendo Sufami Turbo",
    "supergrafx": "NEC PC Engine SuperGrafx", "videopac": "Phillips Videopac+", "x68000": "Sharp X6800", "pc98": "NEC PC-9801", "pc88": "NEC PC-8801",
    "fds": "Nintendo Famicom Disk System-02", "macintosh": "Apple Mac OS", "msx1": "Microsoft MSX", "msxturbor": "Microsoft MSX Turbo R", "oric": "Oric Atmos",
    "ti99": "Texas Instruments TI 99 4A", "openbor": "OpenBOR-01", "gamecom": "Tiger Game.com", "dragon32": "Dragon 32 64", "tanodragon": "Dragon 32 64",
    "sgb": "Nintendo Super Game Boy-02", "sega32xjp": "Sega 32X", "sega32xna": "Sega 32X", "windows9x": "Windows", "amiga600": "Commodore Amiga",
    "atarixe": "Atari XEGS", "bbcmicro": "BBC Microcomputer System", "triforce": "Sega Triforce", "to8": "Thomson TO7", "coco": "Tandy TRS-80",
}
_idx = None
_surf = {}


def index() -> dict:
    """{nombre normalizado: archivo}."""
    global _idx
    if _idx is None:
        _idx = {}
        if DIR.is_dir():
            for f in DIR.glob("*.png"):
                _idx.setdefault(_N(f.stem), f)
    return _idx


def path_for(text) -> "Path | None":
    """Archivo del logo para una plataforma escrita como sea («PlayStation 2», «ps2», «Sony PlayStation 2»…) o None."""
    t = str(text or "").strip()
    if not t:
        return None
    ix = index()
    n0 = _N(t)
    for pre in ("", "sony", "nintendo", "sega", "microsoft", "atari", "nec", "snk", "commodore", "sharp"):      # exacto primero: «Xbox One» no es «Xbox»
        if pre + n0 in ix:
            return ix[pre + n0]
    sysn = esde.system_for(t)
    for cand in ([MAP[sysn]] if sysn in MAP else []) + [t] + [s["full"] for s in esde.systems() if s["name"] == sysn][:1]:
        f = ix.get(_N(cand))
        if f:
            return f
    n = _N(t)
    if n in MAP:
        return ix.get(_N(MAP[n]))
    for pre in ("sony", "nintendo", "sega", "microsoft", "atari", "nec", "snk", "commodore", "sharp"):      # «PlayStation 4» → «Sony Playstation 4»
        f = ix.get(pre + n)
        if f:
            return f
    return None


def logo(text, h, max_w=None):
    """Surface del logo con h px de alto (o el ancho máximo si es muy ancho), o None. Cacheada."""
    f = path_for(text)
    if not f:
        return None
    key = (str(f), h, max_w)
    if key not in _surf:
        import pygame
        try:
            im = pygame.image.load(str(f)).convert_alpha()
        except Exception:  # noqa: BLE001
            _surf[key] = None
            return None
        w = max(1, round(im.get_width() * h / im.get_height()))
        if max_w and w > max_w:
            w, h = max_w, max(1, round(im.get_height() * max_w / im.get_width()))
        _surf[key] = pygame.transform.smoothscale(im, (w, h))
    return _surf[key]


def coverage() -> tuple:
    """(sistemas de ES-DE con logo, sin logo) — para el informe de pruebas."""
    ok, no = [], []
    for s in esde.systems():
        (ok if path_for(s["name"]) or path_for(s["full"]) else no).append(s["name"])
    return ok, no
