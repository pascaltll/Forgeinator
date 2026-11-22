"""Archivos que YA recibiste por un navegador (zip/7z/rar/iso/rom…): listarlos, descomprimirlos, moverlos a la carpeta del proyecto,
sugerir a qué juego del catálogo pertenecen y en qué plataforma de tu biblioteca ES-DE guardarlos. Nunca borra ni pisa nada sin que lo pidas."""
import os
import shutil
import subprocess
import tarfile
import time
import zipfile
from pathlib import Path

from . import esde, formats, roms

ROMEXT = {".iso", ".bin", ".cue", ".img", ".mdf", ".gcm", ".z64", ".n64", ".v64", ".sfc", ".smc", ".nes", ".gba", ".gb", ".gbc", ".nds", ".3ds", ".cia",
          ".elf", ".wbfs", ".gdi", ".chd", ".rvz", ".wia", ".gcz", ".pkg", ".nsp", ".xci", ".wad", ".pbp", ".cso", ".md", ".gen", ".sms", ".gg", ".pce", ".a26", ".lnx"}
ARCH = {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".xz", ".bz2"}
GENERIC = {".bin", ".iso", ".cue", ".img", ".mdf", ".chd", ".zip", ".7z", ".rar", ".md", ".gen"}
PARTIAL = (".crdownload", ".part", ".download", ".opdownload", ".hub-part")


def scan(dirs, exclude=(), days=14, limit=15) -> list:
    now, out, seen = time.time(), [], set()
    ex = [Path(x).expanduser().resolve() for x in exclude]
    for d in dirs:
        d = Path(os.path.expandvars(str(d))).expanduser()
        try:
            for p in d.iterdir():
                try:
                    if (not p.is_file() or p.name.startswith(".") or p.name.endswith(PARTIAL) or p in seen or p.parent.resolve() in ex):
                        continue
                    if p.suffix.lower() not in ROMEXT | ARCH:
                        continue
                    st = p.stat()
                    if now - st.st_mtime > days * 86400:
                        continue
                    seen.add(p)
                    out.append({"path": p, "size": st.st_size, "mtime": st.st_mtime})
                except OSError:
                    continue
        except OSError:
            continue
    return sorted(out, key=lambda r: -r["mtime"])[:limit]


def members(path) -> list:
    p = Path(path)
    try:
        if p.suffix.lower() == ".zip":
            return [n for n, _, _ in formats.zip_members(p)]
    except (OSError, zipfile.BadZipFile):
        pass
    return []


def guess_systems(path) -> list:
    """Sistemas ES-DE probables: por la extensión de lo que hay dentro del zip (o del propio archivo); si no, por el nombre."""
    exts = {Path(n).suffix.lower() for n in members(path)} or {Path(path).suffix.lower()}
    exts -= {""}
    specific = exts - GENERIC
    out = []
    if specific:
        out = [s["name"] for s in esde.systems() if any(esde.accepts(s["name"], e) for e in specific)]
    if not out:
        g = esde.system_for(Path(path).stem)
        out = [g] if g else []
    return out[:4]


def suggest(entries, path, limit=4) -> list:
    stem = Path(path).stem
    sc = []
    for e in entries:
        best = max((roms.name_score(n, stem) for n in {e["name"], e.get("group") or ""} - {""}), default=0)
        if best > 0:
            sc.append((best, e))
    return [e for _, e in sorted(sc, key=lambda x: -x[0])[:limit]]


def unpack(path, dest_root) -> Path:
    """Descomprime en <dest_root>/<nombre>/ (nunca sobre una carpeta existente). Devuelve la carpeta."""
    p, dest_root = Path(path), Path(dest_root)
    dest = dest_root / p.stem
    n = 1
    while dest.exists():
        dest = dest_root / f"{p.stem} ({n})"
        n += 1
    dest.mkdir(parents=True)
    ext = p.suffix.lower()
    try:
        if ext == ".zip":
            with zipfile.ZipFile(p) as z:
                z.extractall(dest)
        elif ext in (".tar", ".gz", ".tgz", ".xz", ".bz2") and tarfile.is_tarfile(p):
            with tarfile.open(p) as t:
                t.extractall(dest, filter="data")
        else:
            tool = formats.sevenz()
            if not tool:
                raise OSError("no hay 7z ni bsdtar para descomprimir este formato")
            argv = [tool, "-xf", str(p), "-C", str(dest)] if tool.endswith("bsdtar") else [tool, "x", "-y", f"-o{dest}", str(p)]
            r = subprocess.run(argv, capture_output=True, text=True, timeout=3600)
            if r.returncode != 0:
                raise OSError((r.stderr or r.stdout or "error al descomprimir").strip()[-200:])
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return dest


def move(path, dest_dir) -> Path:
    """Mueve a dest_dir sin pisar nada (añade (1), (2)… si el nombre existe)."""
    p, dest_dir = Path(path), Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    d = dest_dir / p.name
    n = 1
    while d.exists():
        d = dest_dir / f"{p.stem} ({n}){p.suffix}"
        n += 1
    shutil.move(str(p), str(d))
    return d
