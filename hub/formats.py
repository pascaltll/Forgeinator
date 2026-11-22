"""Variantes de formato de TU copia del juego: comprimidos (zip/7z/rar), CHD, RVZ/WIA… Hub prepara una versión «llana» (iso/bin/cue…)
dentro de data/biblioteca/converted y la compara con lo que pide el port. Solo trabaja con archivos que ya tienes; NO descifra nada.
Lo cifrado/propio de una consola (.pkg de PSN, .nsp/.xci de eShop, .wad…) no se convierte: necesitas tu volcado en formato estándar."""
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from . import config, library

ARCHIVES = {".zip", ".7z", ".rar"}
CONVERT = {".chd": "chdman", ".rvz": "dolphin-tool", ".wia": "dolphin-tool", ".gcz": "dolphin-tool"}
PROPRIETARY = {".pkg": "PSN (cifrado con las claves de la consola)", ".nsp": "eShop de Switch (cifrado)", ".xci": "cartucho de Switch (cifrado)", ".nsz": "Switch comprimido (cifrado)",
               ".wad": "WiiWare/Virtual Console (cifrado)", ".pbp": "PS1/PSP clásico en EBOOT (hay que convertirlo con otra herramienta)", ".cso": "PSP comprimido (conviértelo a ISO con ciso/maxcso)"}
PLAIN = {".iso", ".bin", ".cue", ".img", ".mdf", ".gcm", ".z64", ".n64", ".v64", ".sfc", ".smc", ".nes", ".gba", ".gb", ".gbc", ".nds", ".3ds", ".cia", ".elf", ".wbfs", ".gdi"}
SEVENZ = ("7z", "7zz", "7za", "7zr")


def work_dir() -> Path:
    d = config.path("library_dir") / "converted"
    d.mkdir(parents=True, exist_ok=True)
    return d


def tool(name):
    return shutil.which(name)


def sevenz():
    return next((t for t in (tool(n) for n in SEVENZ) if t), None) or tool("bsdtar")


def kind(path) -> str:
    """plain | archive | convert | proprietary | unknown"""
    e = Path(path).suffix.lower()
    return "archive" if e in ARCHIVES else "convert" if e in CONVERT else "proprietary" if e in PROPRIETARY else "plain" if e in PLAIN else "unknown"


def zip_members(path):
    with zipfile.ZipFile(path) as z:
        return [(i.filename, i.file_size, i.CRC) for i in z.infolist() if not i.is_dir()]


def peek_zip(path, req) -> dict:
    """Mira DENTRO de un .zip sin extraerlo: CRC32 (gratis en el índice), y serial en los primeros MiB."""
    out = {"ok": False, "how": "", "member": ""}
    try:
        mem = zip_members(path)
    except (OSError, zipfile.BadZipFile):
        return out
    crcs = {x.lower() for x in req.get("crc32", [])}
    for name, size, crc in mem:
        if f"{crc:08x}" in crcs:
            return {"ok": True, "how": "crc32 dentro del zip", "member": name}
    if req.get("serials"):
        with zipfile.ZipFile(path) as z:
            for name, size, crc in mem:
                if Path(name).suffix.lower() not in (".iso", ".bin", ".img", ".mdf"):
                    continue
                try:
                    with z.open(name) as f:
                        blob = f.read(4 << 20)
                except (OSError, RuntimeError, zipfile.BadZipFile):
                    continue
                up = blob.upper().translate(None, b"-_. ")
                for s in req["serials"]:
                    if re.sub(r"[-_ .]", "", s.upper()).encode() in up:
                        return {"ok": True, "how": f"serial {s} dentro del zip", "member": name}
    return out


def _need_space(path, factor):
    free = shutil.disk_usage(work_dir()).free
    need = int(os.path.getsize(path) * factor)
    if free < need + (1 << 30):
        raise OSError(f"Poco espacio libre en {work_dir()}: hacen falta ~{(need >> 30) + 1} GB y hay {free >> 30} GB")


def _run(argv, cb=None):
    p = subprocess.run([str(a) for a in argv], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _pick(names, want):
    """Qué miembros extraer: los de formato aceptado; si es .cue/.bin se llevan los dos con el mismo nombre."""
    ok = [n for n in names if Path(n).suffix.lower() in (set(want) or (library.EXTS - ARCHIVES))]
    if not ok:
        ok = [n for n in names if Path(n).suffix.lower() in PLAIN]
    cues = [n for n in ok if n.lower().endswith(".cue")]
    if cues:
        stems = {Path(c).stem for c in cues}
        ok = [n for n in names if Path(n).stem in stems or n in cues] or ok
    return ok


def resolve(path, req, cb=None) -> dict:
    """Devuelve {path, how, note, need}. path = archivo llano listo para comparar/enlazar (o None si no se pudo).
    need = herramienta que falta (con consejo en note)."""
    p, k = Path(path), kind(path)
    want = {f.lower() for f in req.get("formats", [])}
    if k == "plain" or (k == "unknown"):
        return {"path": p, "how": "", "note": "", "need": ""}
    if k == "proprietary":
        return {"path": None, "how": "", "need": "", "note": f"{p.suffix.lower()}: {PROPRIETARY[p.suffix.lower()]}. Hub no lo descifra ni lo convierte: usa tu propio volcado en formato estándar (iso/bin/chd…)."}
    out = work_dir() / re.sub(r"[^\w.-]+", "_", p.stem)
    out.mkdir(parents=True, exist_ok=True)
    try:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as z:
                names = [i.filename for i in z.infolist() if not i.is_dir()]
                sel = _pick(names, want)
                if not sel:
                    return {"path": None, "how": "", "need": "", "note": "El zip no contiene ningún iso/bin/cue/rom reconocible."}
                _need_space(p, 4)
                for n in sel:
                    dest = out / Path(n).name
                    if not dest.exists():
                        with z.open(n) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst, 1 << 20)
            main = next((out / Path(n).name for n in sel if Path(n).suffix.lower() in want), out / Path(sel[0]).name)
            return {"path": main, "how": "extraído del zip", "note": "", "need": ""}
        if p.suffix.lower() in (".7z", ".rar"):
            t = sevenz()
            if not t:
                return {"path": None, "how": "", "need": "7z", "note": "Para abrir .7z/.rar instala 7zip (p. ej. `sudo dnf install p7zip p7zip-plugins`, en Bazzite: `brew install sevenzip` o dentro del distrobox)."}
            _need_space(p, 4)
            argv = [t, "x", "-y", f"-o{out}", str(p)] if "bsdtar" not in t else [t, "-xf", str(p), "-C", str(out)]
            rc, txt = _run(argv)
            if rc:
                return {"path": None, "how": "", "need": "", "note": "No pude extraer: " + txt.strip()[-200:]}
            found = [x for x in out.rglob("*") if x.is_file()]
            sel = _pick([str(x) for x in found], want)
            return {"path": Path(sel[0]) if sel else None, "how": "extraído del archivo", "note": "" if sel else "El archivo no contiene un iso/bin/cue reconocible.", "need": ""}
        if p.suffix.lower() == ".chd":
            t = tool("chdman")
            if not t:
                return {"path": None, "how": "", "need": "chdman", "note": "Para leer .chd hace falta `chdman` (paquete mame-tools / mame). Instálalo en el sistema o en tu distrobox y vuelve a intentarlo."}
            _need_space(p, 6)
            want_iso = ".iso" in want and ".bin" not in want and ".cue" not in want
            cue, iso = out / (p.stem + ".cue"), out / (p.stem + ".iso")
            rc, txt = (1, "")
            if not want_iso:
                rc, txt = _run([t, "extractcd", "-i", p, "-o", cue, "-ob", out / (p.stem + ".bin"), "-f"])
                if rc == 0:
                    b = out / (p.stem + ".bin")
                    return {"path": b if (".bin" in want or not want) else cue, "how": "convertido de CHD (chdman)", "note": "", "need": ""}
            rc, txt = _run([t, "extractdvd", "-i", p, "-o", iso, "-f"])
            if rc == 0:
                return {"path": iso, "how": "convertido de CHD (chdman)", "note": "", "need": ""}
            return {"path": None, "how": "", "need": "", "note": "chdman no pudo convertirlo: " + txt.strip()[-200:]}
        if p.suffix.lower() in (".rvz", ".wia", ".gcz"):
            t = tool("dolphin-tool")
            if not t:
                return {"path": None, "how": "", "need": "dolphin-tool", "note": "Para RVZ/WIA/GCZ hace falta `dolphin-tool` (viene con Dolphin; en Flatpak: `flatpak run --command=dolphin-tool org.DolphinEmu.dolphin-emu`)."}
            _need_space(p, 5)
            iso = out / (p.stem + ".iso")
            rc, txt = _run([t, "convert", "-i", p, "-o", iso, "-f", "iso"])
            return {"path": iso if rc == 0 else None, "how": "convertido a ISO (dolphin-tool)", "need": "", "note": "" if rc == 0 else "dolphin-tool falló: " + txt.strip()[-200:]}
    except (OSError, zipfile.BadZipFile) as ex:
        return {"path": None, "how": "", "need": "", "note": str(ex)}
    return {"path": p, "how": "", "note": "", "need": ""}
