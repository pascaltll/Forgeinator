"""Biblioteca local: carpetas vigiladas e identificación de archivos por nombre/serial/tamaño/SHA-1/CRC32.
No descarga nada: solo reconoce el archivo que TÚ ya tienes y lo ordena/enlaza."""
import hashlib
import os
import re
import shutil
import zlib
from pathlib import Path

from . import config, discid

EXTS = {".iso", ".bin", ".cue", ".chd", ".z64", ".n64", ".v64", ".nds", ".3ds", ".cia", ".gcm", ".rvz", ".wbfs", ".nsp", ".xci",
        ".sfc", ".smc", ".gba", ".gb", ".gbc", ".nes", ".zip", ".7z", ".rar", ".pkg", ".img", ".mdf", ".cso", ".elf"}


def hashes(path, cb=None, limit=None):
    """(sha1, crc32 hex) leyendo el archivo una sola vez. limit = máx. bytes (None = todo)."""
    h, c, total = hashlib.sha1(), 0, os.path.getsize(path)
    done = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b or (limit and done >= limit):
                break
            h.update(b)
            c = zlib.crc32(b, c)
            done += len(b)
            if cb:
                cb(done, total)
    return h.hexdigest(), f"{c & 0xFFFFFFFF:08x}"


def md5_of(path, limit=3 << 30) -> str:
    if os.path.getsize(path) > limit:
        return ""
    h = hashlib.md5()  # noqa: S324 (identificación de archivos, no seguridad)
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def scan_serial(path, serials, window=4 << 20):
    """Busca un serial (p. ej. SCUS-94426) en nombre y en los primeros/últimos MiB (SYSTEM.CNF en ISO PS1/PS2)."""
    nm = re.sub(r"[-_ .]", "", Path(path).name.upper())
    for s in serials:
        if re.sub(r"[-_ .]", "", s.upper()) in nm:
            return s
    did = discid.read_id(path)          # lee el ID real del disco (PARAM.SFO / SYSTEM.CNF), esté donde esté dentro del archivo
    if did:
        for s in serials:
            if discid.matches(did["id"], [s]):
                return s
    try:
        with open(path, "rb") as f:
            blob = f.read(window)
    except OSError:
        return None
    up = blob.upper().translate(None, b"-_. ")
    for s in serials:
        if re.sub(r"[-_ .]", "", s.upper()).encode() in up:
            return s
    return None


def match(path, req: dict, cb=None) -> dict:
    """¿Este archivo es el que pide el port? req={serials[], sha1[], crc32[], formats[], min_size, max_size}.
    Devuelve {ok, how, sha1, crc32}. 'ok' solo si hay coincidencia fuerte (hash o serial); si solo hay formato/tamaño → 'weak'."""
    p = Path(path)
    r = {"ok": False, "weak": False, "how": "", "sha1": "", "crc32": ""}
    ext = p.suffix.lower()
    fmts = [f.lower() for f in req.get("formats", [])]
    if fmts and ext not in fmts:
        return r
    sz = p.stat().st_size
    if sz < req.get("min_size", 0) or sz > req.get("max_size", 1 << 62):
        return r
    if req.get("sha1") or req.get("crc32"):
        sha1, crc = hashes(p, cb)
        r["sha1"], r["crc32"] = sha1, crc
        if sha1 in [x.lower() for x in req.get("sha1", [])] or crc in [x.lower() for x in req.get("crc32", [])]:
            r.update(ok=True, how="hash")
            return r
    if req.get("md5") and md5_of(p) in [x.lower() for x in req["md5"]]:
        r.update(ok=True, how="md5")
        return r
    if req.get("serials"):
        s = scan_serial(p, req["serials"])
        if s:
            r.update(ok=True, how=f"serial {s}")
            return r
    if not (req.get("sha1") or req.get("crc32") or req.get("serials") or req.get("md5")):
        r.update(weak=True, how="formato/tamaño (sin hash conocido)")
    return r


def candidates(dirs, req, newer_than=0):
    """Archivos de las carpetas vigiladas que podrían ser el pedido (por extensión), más recientes primero."""
    out = []
    for d in dirs:
        d = Path(os.path.expandvars(str(d))).expanduser()
        if not d.is_dir():
            continue
        try:
            for p in d.iterdir():
                if p.is_file() and not p.name.endswith((".part", ".crdownload", ".tmp")) and p.suffix.lower() in (EXTS | {x.lower() for x in req.get("formats", [])}):
                    st = p.stat()
                    if st.st_mtime >= newer_than:
                        out.append((st.st_mtime, p))
        except OSError:
            continue
    return [p for _, p in sorted(out, reverse=True)]


def stable(path, wait=1.0):
    """True si el tamaño no cambia (descarga del navegador terminada)."""
    import time
    try:
        a = os.path.getsize(path)
        time.sleep(wait)
        return a == os.path.getsize(path) and a > 0
    except OSError:
        return False


def adopt(path, platform, mode="link") -> Path:
    """Coloca el archivo en la biblioteca: 'link' (enlace simbólico, no mueve nada), 'copy' o 'move'."""
    dest_dir = config.path("library_dir") / (re.sub(r"[^\w.-]+", "_", platform) or "otros")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(path).name
    if dest.exists() or dest.is_symlink():
        return dest
    if mode == "copy":
        shutil.copy2(path, dest)
    elif mode == "move":
        shutil.move(str(path), dest)
    else:
        dest.symlink_to(Path(path).resolve())
    return dest


LINKS = config.DATA / "links.json"


_LINKS_C = [None, None]


def _links():
    """v3.14: links.json leído una vez y reutilizado mientras no cambie (mismo tamaño y fecha en ns). La ficha lo consultaba en cada
    fotograma; ahora cuesta un stat. Lo escriba quien lo escriba (este proceso, un hilo u otro programa), el cambio se ve al momento."""
    import json
    try:
        st = LINKS.stat()
    except OSError:
        return {}
    sig = (str(LINKS), st.st_mtime_ns, st.st_size)
    if _LINKS_C[0] != sig:
        try:
            d = json.loads(LINKS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        _LINKS_C[0], _LINKS_C[1] = sig, d if isinstance(d, dict) else {}
    return _LINKS_C[1]


def link_get(eid):
    return _links().get(eid)


def link_set(eid, path):
    import json
    try:
        cur = json.loads(LINKS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    cur[eid] = str(path)
    LINKS.parent.mkdir(parents=True, exist_ok=True)
    LINKS.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    _LINKS_C[0] = None


def disc_links(eid) -> dict:
    """v2.40+: un port que pide VARIOS discos (God of War PSP: Chains of Olympus y Ghost of Sparta) guarda uno por ID: {UCUS98653: ruta, …}."""
    try:
        d = _links().get("_discs", {}).get(eid, {})
    except AttributeError:
        return {}
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(v, str)}


def disc_link_set(eid, serial, path):
    import json
    try:
        cur = json.loads(LINKS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    cur.setdefault("_discs", {}).setdefault(eid, {})[serial] = str(path)
    LINKS.parent.mkdir(parents=True, exist_ok=True)
    LINKS.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    _LINKS_C[0] = None


def place(entry, src, install_dir):
    """Si el catálogo indica requires.place (ruta relativa en la carpeta del port), enlaza ahí el archivo. No pisa nada."""
    rel = (entry.get("requires") or {}).get("place")
    if not rel:
        return None
    t = Path(install_dir) / rel
    if str(rel).endswith("/"):           # una carpeta («gamedata/»): el enlace lleva el nombre de tu archivo
        t = t / Path(src).name
    if t.exists() or t.is_symlink():
        return t
    t.parent.mkdir(parents=True, exist_ok=True)
    t.symlink_to(Path(src).resolve())
    if str(rel).endswith("/"):
        _companions(Path(src), t.parent)
    return t


def place_default(entry, src, install_dir):
    """Enlace del juego en la carpeta del proyecto (v1.80): si el catálogo no fija `requires.place`/`rom_dest`, deja un enlace
    simbólico a la ROM de la biblioteca en la raíz de la instalación, que es donde suele abrirse el selector de archivos del port.
    Nunca pisa un archivo real; reemplaza solo enlaces propios que apunten a otro sitio. Devuelve la ruta o None."""
    req = entry.get("requires") or {}
    if req.get("place") or rom_dest_for(entry) or not install_dir or not src:
        return None
    d = Path(install_dir)
    if not d.is_dir():
        return None
    t = d / Path(src).name
    target = Path(src).resolve()
    if t.is_symlink():
        if Path(os.readlink(t)) == target:
            return t
        t.unlink()
    elif t.exists():
        return t
    t.symlink_to(target)
    _companions(Path(src), d)
    return t


def _companions(src: Path, d: Path):
    """.cue ↔ .bin (y pistas de .gdi): se enlazan juntos; un .cue sin su .bin no sirve."""
    try:
        from . import esde
        for c in esde.companions(src):
            ct = d / c.name
            if not (ct.exists() or ct.is_symlink()):
                ct.symlink_to(c.resolve())
    except OSError:
        pass


# Carpeta donde ciertos ports buscan/muestran la ROM (su selector de archivos empieza ahí). Se puede fijar por entrada con requires.rom_dest.
ROM_DEST = {"harbourmasters/lighthouse": "~/.local/share/lighthouse"}


def rom_dest_for(entry):
    rel = (entry.get("requires") or {}).get("rom_dest") or ROM_DEST.get(str(entry.get("repo", "")).lower())
    return Path(os.path.expandvars(str(rel))).expanduser() if rel else None


def place_rom(entry, src):
    """Enlaza la ROM ya extraída en la carpeta de ROM del port. Reemplaza enlaces propios; nunca pisa un archivo real."""
    d = rom_dest_for(entry)
    if not d:
        return None
    d.mkdir(parents=True, exist_ok=True)
    t = d / Path(src).name
    if t.is_symlink():
        if Path(os.readlink(t)) == Path(src).resolve():
            return t
        t.unlink()
    elif t.exists():
        return t
    t.symlink_to(Path(src).resolve())
    return t


def relink(install_dir, old, new) -> int:
    """Cambiar de archivo (v2.76): los enlaces simbólicos que apuntaban al archivo ANTERIOR (en la carpeta del juego, en linux/ y en windows/)
    pasan a apuntar al nuevo, CONSERVANDO su nombre (el juego puede tenerlo configurado). Solo toca enlaces; nunca un archivo real.
    Devuelve cuántos reenlazó."""
    if not install_dir or not old or not new or Path(old) == Path(new):
        return 0
    d = Path(install_dir)
    roots = {d}
    if d.name in ("linux", "windows"):
        roots.add(d.parent)
    n = 0
    try:
        old_r, new_r = Path(old).resolve(), Path(new).resolve()
    except OSError:
        return 0
    for r in list(roots):
        for sub in (".", "linux", "windows"):
            base = r / sub
            try:
                kids = list(base.iterdir()) if base.is_dir() else []
            except OSError:
                continue
            for x in kids:
                if not x.is_symlink():
                    continue
                try:
                    cur = Path(os.readlink(x))
                    if cur != Path(old) and (cur if cur.is_absolute() else x.parent / cur).resolve() != old_r:
                        continue
                    x.unlink()
                    x.symlink_to(new_r)
                    n += 1
                except OSError:
                    continue
    return n
