"""Guardar tu juego en TU biblioteca estilo ES-DE: <raíz>/roms/<sistema>/archivo. Los nombres de sistema (psx, ps2, gc, n64…) salen de la lista oficial de ES-DE
(catalog/esde_systems.json, generada de su es_systems.xml, licencia MIT). Copia o mueve solo archivos TUYOS, nunca pisa uno existente."""
import json
import os
import re
import shutil
from pathlib import Path

from . import config

_F = Path(__file__).resolve().parent.parent / "catalog" / "esde_systems.json"
# alias de texto (plataforma del catálogo o carpeta) → nombre de sistema ES-DE
ALIAS = {
    "psx": ["ps1", "psx", "psone", "playstation", "playstation1", "sonyplaystation"], "ps2": ["ps2", "playstation2"], "ps3": ["ps3", "playstation3"],
    "psp": ["psp", "playstationportable"], "psvita": ["psvita", "vita", "playstationvita"], "n64": ["n64", "nintendo64"],
    "gc": ["gc", "gamecube", "ngc", "nintendogamecube"], "wii": ["wii", "nintendowii"], "wiiu": ["wiiu", "nintendowiiu"],
    "nds": ["nds", "ds", "nintendods"], "n3ds": ["3ds", "n3ds", "nintendo3ds"], "gba": ["gba", "gameboyadvance"], "gb": ["gb", "gameboy"],
    "gbc": ["gbc", "gameboycolor"], "snes": ["snes", "sfc", "supernintendo", "superfamicom", "supernes"], "nes": ["nes", "nintendoentertainmentsystem"],
    "famicom": ["famicom"], "switch": ["switch", "nintendoswitch"], "xbox": ["xbox", "microsoftxbox"], "xbox360": ["xbox360", "x360"],
    "dreamcast": ["dc", "dreamcast", "segadreamcast"], "saturn": ["saturn", "segasaturn"], "genesis": ["genesis", "segagenesis"],
    "megadrive": ["megadrive", "md", "segamegadrive"], "mastersystem": ["mastersystem", "sms"], "gamegear": ["gamegear"], "segacd": ["segacd"],
    "pcengine": ["pcengine", "turbografx16"], "3do": ["3do"], "atarijaguar": ["jaguar", "atarijaguar"], "pc": ["pc", "dos", "ibmpc"],
}
SAME = [{"gb", "gbc"}, {"genesis", "megadrive"}, {"nes", "famicom"}, {"psx", "ps1"}]
_N = lambda t: re.sub(r"[^a-z0-9]+", "", str(t).lower())  # noqa: E731
_cache = None


def systems() -> list:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_F.read_text(encoding="utf-8"))["systems"]
        except (OSError, ValueError, KeyError):
            _cache = []
    return _cache


def system_for(text) -> str:
    """'PlayStation' / 'Sony PlayStation 2' / 'psx' → nombre de sistema ES-DE ('' si no se reconoce)."""
    n = _N(text)
    if not n:
        return ""
    for k, al in ALIAS.items():
        if n in al or n == k:
            return k
    names = {s["name"]: s for s in systems()}
    if n in names:
        return n
    strip = lambda t: re.sub(r"^(sony|nintendo|sega|microsoft|atari|snk|bandai|nec|commodore|ibm)", "", _N(t))  # noqa: E731
    for s in systems():
        if _N(s["full"]) == n or strip(s["full"]) == strip(text):
            return s["name"]
    best, key = "", ""
    for k, al in ALIAS.items():
        for a in al:
            if len(a) > 3 and (a in n) and len(a) > len(best) and not re.search(r"\d", n.replace(a, "", 1)):
                best, key = a, k
    return key


def same(a: str, b: str) -> bool:
    return a == b or any(a in g and b in g for g in SAME)


def accepts(system: str, ext: str) -> bool:
    s = next((x for x in systems() if x["name"] == system), None)
    return bool(s) and ext.lower() in s["ext"]


def is_inside(path, roots) -> bool:
    p = Path(path).resolve()
    return any(str(p).startswith(str(Path(r).resolve()) + os.sep) for r in roots)


def companions(path) -> list:
    """Archivos que viajan juntos: .cue + sus .bin, .bin + su .cue, .gdi + pistas."""
    p, out = Path(path), []
    try:
        if p.suffix.lower() in (".cue", ".gdi"):
            for m in re.finditer(r'(?:FILE\s+"([^"]+)"|^\d+\s+\d+\s+\d+\s+\d+\s+(\S+))', p.read_text(errors="ignore"), re.M):
                f = p.parent / (m.group(1) or m.group(2))
                if f.is_file():
                    out.append(f)
        elif p.suffix.lower() == ".bin":
            c = p.with_suffix(".cue")
            if c.is_file():
                out.append(c)
    except OSError:
        pass
    return out


def target_dir(root, system) -> Path:
    return Path(root) / system


def plan(path, system, root) -> dict:
    """Qué se haría: archivos origen → destino. Sin tocar nada."""
    p = Path(path)
    files = [p] + [c for c in companions(p) if c != p]
    d = target_dir(root, system)
    return {"dir": d, "files": [(f, d / f.name) for f in files], "size": sum(f.stat().st_size for f in files if f.exists())}


def store(path, system, root, mode="copy", cb=None) -> Path:
    """Copia o mueve (mode='copy'|'move') el archivo y sus compañeros a <root>/<sistema>/. Devuelve la ruta final del principal.
    Nunca sobrescribe: si el destino existe se usa tal cual."""
    pl = plan(path, system, root)
    pl["dir"].mkdir(parents=True, exist_ok=True)
    need = sum(s.stat().st_size for s, d in pl["files"] if not d.exists())
    if shutil.disk_usage(pl["dir"]).free < need + (512 << 20):
        raise OSError(f"Poco espacio en {pl['dir']}: hacen falta ~{(need >> 30) + 1} GB")
    main = pl["files"][0][1]
    done = 0
    for src, dst in pl["files"]:
        if dst.exists():
            continue
        tmp = dst.with_name(dst.name + ".hub-part")
        with open(src, "rb") as a, open(tmp, "wb") as b:
            while True:
                buf = a.read(8 << 20)
                if not buf:
                    break
                b.write(buf)
                done += len(buf)
                if cb:
                    cb(done, max(1, need))
        os.replace(tmp, dst)
        shutil.copystat(src, dst, follow_symlinks=False)
        if mode == "move":
            try:
                src.unlink()
            except OSError:
                pass
    return main
