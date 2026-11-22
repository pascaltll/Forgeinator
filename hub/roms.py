"""Tu colección de ROMs/ISOs ya existente (p. ej. ~/Nextcloud/Emulation/roms/<plataforma>/…): se indexa y se cruza con lo que pide cada port.
Solo LEE tus archivos (nunca los mueve ni borra) y no descarga nada. Coincidencia fuerte = serial/SHA-1/CRC32 del port; débil = nombre parecido."""
import difflib
import json
import os
import re
import sys
from pathlib import Path

from . import config, esde, formats, library

INDEX = config.DATA / "romindex.json"
HASHES = config.DATA / "romhash.json"
DEFAULT_ROOTS = ("~/Nextcloud/Emulation/roms", "~/Emulation/roms", "~/Nextcloud/Emulation/ROMs", "~/Nextcloud/Emulation")
ROM_EXTS = library.EXTS | {".m3u", ".gdi", ".wad", ".dol", ".nsz", ".rpx", ".wua", ".pbp", ".a26", ".md", ".gen", ".smd", ".gg", ".sms", ".pce", ".ngp", ".ws"}
STOP = {"the", "of", "and", "a", "usa", "eu", "europe", "pal", "ntsc", "ntscu", "ntscj", "japan", "world", "rev", "v", "disc", "en", "es", "fr", "de", "it", "beta", "proto",
        "decomp", "recomp", "port", "pc", "cd", "dvd", "iso", "bin", "cue", "chd"}
_N = lambda t: re.sub(r"[^a-z0-9]+", "", str(t).lower())  # noqa: E731


def canon(text) -> str:
    """Sistema ES-DE (psx, ps2, gc, n64…) de un nombre de carpeta o plataforma; '' si no se reconoce."""
    return esde.system_for(text)


def same_plat(a: str, b: str) -> bool:
    return (not a) or (not b) or esde.same(a, b)


def roots(cfg) -> list:
    rs = cfg.get("rom_dirs") or []
    if not rs:
        rs = [d for d in DEFAULT_ROOTS if Path(d).expanduser().is_dir()][:1]
    return [Path(os.path.expandvars(str(r))).expanduser() for r in rs if Path(os.path.expandvars(str(r))).expanduser().is_dir()]


def scan(rs, cb=None, max_files=200000) -> list:
    """Índice rápido (solo metadatos): [{p, plat, folder, size, mtime}]. La plataforma sale de la 1.ª subcarpeta bajo la raíz."""
    out = []
    for r in rs:
        for root, dirs, files in os.walk(r):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("media", "images", "covers", "manuals", "downloaded_media", "gamelists"))
            rel = Path(root).relative_to(r)
            folder = rel.parts[0] if rel.parts else ""
            for f in files:
                if Path(f).suffix.lower() not in ROM_EXTS or f.startswith("."):
                    continue
                p = Path(root) / f
                try:
                    st = p.stat()
                except OSError:
                    continue
                out.append({"p": str(p), "plat": canon(folder) or (folder.lower() if folder.lower() in {x["name"] for x in esde.systems()} else ""), "folder": folder, "size": st.st_size, "mtime": int(st.st_mtime)})
                if len(out) >= max_files:
                    return out
            if cb:
                cb(len(out))
    try:
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(json.dumps(out), encoding="utf-8")
    except OSError:
        pass
    return out


def load_index() -> list:
    try:
        return json.loads(INDEX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


# ── datos que los repos mencionan en su README ──
SERIAL_RX = re.compile(r"\b((?:SL|SC)(?:US|ES|PS|PM|ED|PX|PH|KA|AJ)|PBPX|PAPX|ULUS|ULES|UCUS|UCES|NPUG|BLUS|BLES|BCUS|BCES|GALE|GM4E|G8ME)[-_ ]?(\d{3})[._]?(\d{2})\b", re.I)
SHA1_RX = re.compile(r"\b[0-9a-f]{40}\b", re.I)
CRC_RX = re.compile(r"crc-?32\W{0,12}(?:is\W{0,3})?([0-9a-f]{8})\b|\b([0-9a-f]{8})\W{1,6}crc-?32", re.I)
EXT_RX = re.compile(r"\.(z64|n64|v64|iso|bin|cue|chd|nds|3ds|cia|gcm|rvz|wbfs|nsp|xci|sfc|smc|gba|gbc|gb|nes|elf|cso|pkg)\b", re.I)


MD5_RX = re.compile(r"\b[0-9a-f]{32}\b", re.I)
REGION_RX = re.compile(r"\b(NTSC-?U/?C?|NTSC-?J|NTSC|PAL(?:-?[A-Z]{1,2})?|USA|US version|North America|Europe(?:an)?|Japan(?:ese)?|JPN|EUR|World|Latin America|Spanish|Español)\b", re.I)
VERSION_RX = re.compile(r"\b(?:v(?:ersion)?\.?\s?\d+(?:\.\d+){0,2}|rev(?:ision)?\.?\s?[0-9A-Z]\b|1\.\d{2}\b|disc\s?\d|Greatest Hits|Platinum|Player'?s Choice|Black Label)", re.I)
SNIP_RX = re.compile(r"\b(rom|iso|dump|disc|image|base game|original game|vanilla|clean|assets|required?|requires?|need|must|legally|your own|copy of|extract|place|put)\b", re.I)


def _uniq(seq):
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out


_PLACE_VERB = r"(?:place|put|copy|move|drop|extract|unzip|store|paste|coloca|pon|copia|mueve)"
_PLACE_RX = re.compile(_PLACE_VERB + r"\b[^\n]{0,120}?\b(?:in|into|to|inside|under|en|dentro de)\s+(?:the\s+|la\s+|el\s+)?(?:(?:folder|directory|carpeta)\s+)?"
                       r"(?:`([^`\n]{1,60})`|\"([^\"\n]{1,60})\"|'([^'\n]{1,60})'|([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*/))"
                       r"(?:\s+(?:folder|directory|dir|carpeta))?", re.I)
_ROOT_RX = re.compile(_PLACE_VERB + r"\b[^\n]{0,120}?\b(?:in|into|to|next to|alongside|beside|junto a|en)\s+(?:the\s+)?"
                      r"(?:root|same (?:folder|directory)|(?:game|executable|exe|binary)(?:'s)? (?:folder|directory)|raíz|carpeta del (?:juego|ejecutable))", re.I)
_GAMEFILE_RX = re.compile(r"\b(rom|iso|dump|disc|disk|image|baserom|game files?|game data|assets|bin|cue|eboot|psp_game|archivo del juego)\b|" + EXT_RX.pattern, re.I)


def place_from_text(txt: str) -> list:
    """Carpetas (relativas a la del juego) donde el README pide tu archivo: «Place your ROM in the `gamedata/` folder» → ['gamedata/'].
    «. » = junto al ejecutable. Solo frases que hablan del archivo del juego; nada de rutas absolutas ni URLs."""
    out = []
    for ln in re.split(r"(?<=[.!?])\s+|\n+", txt or ""):
        if not _GAMEFILE_RX.search(ln):
            continue
        for m in _PLACE_RX.finditer(ln):
            p = next(g for g in m.groups() if g).strip().strip("/").replace("\\", "/")
            if not p or p.startswith(("~", "/", "$", "%")) or "://" in p or " " in p or p.lower() in ("root", ".", "./"):
                if p.lower() in ("root", ".", "./"):
                    out.append(".")
                continue
            if EXT_RX.search(p) and "/" not in p:     # «copy baserom.z64 to `baserom.us.z64`» es un nombre de archivo, no una carpeta
                continue
            if re.search(r"\.(z64|iso|bin|cue|elf)$", p, re.I):
                p = p.rsplit("/", 1)[0] if "/" in p else ""
                if not p:
                    continue
            out.append(p + "/")
        if _ROOT_RX.search(ln):
            out.append(".")
    return _uniq(out)


def hints_from_text(txt: str) -> dict:
    """Todo lo que un README (o un texto que copies de la página del proyecto) dice sobre el archivo requerido:
    serial, SHA-1/CRC32/MD5, formatos, región, versión y las frases clave (para que las leas tú)."""
    txt = txt or ""
    ser = _uniq(f"{m.group(1).upper()}-{m.group(2)}.{m.group(3)}" for m in SERIAL_RX.finditer(txt))
    sha = sorted({m.group(0).lower() for m in SHA1_RX.finditer(txt)})
    md5 = sorted({m.group(0).lower() for m in MD5_RX.finditer(txt)})
    crc = sorted({(m.group(1) or m.group(2)).lower() for m in CRC_RX.finditer(txt)})
    fm = _uniq("." + m.group(1).lower() for m in EXT_RX.finditer(txt))
    reg = _uniq(m.group(1).upper() if len(m.group(1)) <= 7 else m.group(1).title() for m in REGION_RX.finditer(txt))
    ver = _uniq(re.sub(r"\s+", " ", m.group(0)).strip() for m in VERSION_RX.finditer(txt))
    snips = []
    for ln in re.split(r"(?<=[.!?])\s+|\n+", txt):
        ln = re.sub(r"\s+", " ", re.sub(r"[`*_#>|]+", " ", ln)).strip()
        if 12 < len(ln) < 400 and SNIP_RX.search(ln) and (REGION_RX.search(ln) or EXT_RX.search(ln) or re.search(r"\b(rom|iso|dump|disc|game|copy)\b", ln, re.I)):
            snips.append(ln[:240])
    return {"serials": ser[:12], "sha1": sha[:12], "crc32": crc[:12], "md5": md5[:12], "formats": fm[:8], "region": reg[:6],
            "version": ver[:6], "snippets": _uniq(snips)[:8], "place": place_from_text(txt)[:4]}


def merge_requires(req: dict, h: dict) -> dict:
    """Une lo detectado con lo que ya tiene la tarjeta (sin borrar lo que escribiste a mano)."""
    out = dict(req or {})
    for k in ("serials", "sha1", "crc32", "md5", "formats", "snippets"):
        out[k] = _uniq(list(out.get(k) or []) + list(h.get(k) or []))
        if not out[k]:
            out.pop(k)
    pl = [p for p in (h.get("place") or []) if p != "."]
    if len(pl) == 1 and not out.get("place") and not out.get("rom_dest"):
        out["place"] = pl[0]            # una sola carpeta clara en el README: ahí se enlaza tu archivo (dentro de la carpeta del juego)
        out["place_from"] = "readme"
    for k in ("region", "version"):
        cur = [x.strip() for x in str(out.get(k) or "").split(",") if x.strip()]
        cur = _uniq(cur + list(h.get(k) or []))
        if cur:
            out[k] = ", ".join(cur)
    return out


def req_lines(req: dict) -> list:
    req = req or {}
    L = []
    for key, lab in (("region", "Región"), ("version", "Versión / disco"), ("formats", "Formatos aceptados"), ("serials", "Serial / ID"),
                     ("sha1", "SHA-1"), ("crc32", "CRC32"), ("md5", "MD5")):
        v = req.get(key)
        if v:
            L.append(f"{lab}: " + (" ".join(v) if key == "formats" else ", ".join(v) if isinstance(v, list) else str(v)))
    if req.get("note"):
        L.append("Nota: " + str(req["note"]))
    return L


# ── cruce ──
def toks(t) -> list:
    t = re.sub(r"[\(\[][^)\]]*[\)\]]", " ", str(t))
    return [w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP and (len(w) > 1 or w.isdigit())]


def name_score(name: str, fname: str) -> float:
    """0 si no son el mismo juego. Exige que las palabras de uno estén TODAS en el otro (así «Need for Speed Carbon» ≠ «Need for Speed Most Wanted»,
    «Tenkaichi 2» ≠ «Tenkaichi 3») y que se parezcan (Jaccard ≥ 0.7)."""
    sa, sb = set(toks(name)), set(toks(Path(fname).stem))
    if not sa or not sb or not (sa <= sb or sb <= sa):
        return 0.0
    return round(len(sa & sb) / len(sa | sb), 3) if len(sa & sb) / len(sa | sb) >= 0.7 else 0.0


def _hash_cache():
    try:
        return json.loads(HASHES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def find(entry: dict, index: list, hash_limit=3 << 30, cb=None) -> list:
    """Candidatos de tu colección para este port, mejores primero: [{path, how, strong, score}].
    Fuerte: serial/SHA-1/CRC32 que pide el port (se leen archivos de la plataforma probable; hashes en caché).
    Débil: nombre parecido en la carpeta de la plataforma (hay que confirmarlo)."""
    req = entry.get("requires") or {}
    want = canon(entry.get("platform", ""))
    fm = {f.lower() for f in req.get("formats", [])}
    pool = [x for x in index if same_plat(want, x["plat"]) and (not fm or Path(x["p"]).suffix.lower() in fm or Path(x["p"]).suffix.lower() in (formats.ARCHIVES | set(formats.CONVERT)))]
    name = entry.get("group") or entry["name"]
    res, cache, dirty = [], _hash_cache(), False
    strong_req = bool(req.get("sha1") or req.get("crc32") or req.get("serials") or req.get("md5"))
    for i, x in enumerate(pool):
        p, sc = x["p"], name_score(name, x["p"])
        how, strong = "", False
        ext = Path(p).suffix.lower()
        if ext == ".zip" and strong_req:
            pk = formats.peek_zip(p, req)
            if pk["ok"]:
                res.append({"path": p, "how": pk["how"], "strong": True, "score": 1.0})
            elif sc >= 0.7:
                res.append({"path": p, "how": f"zip con nombre parecido ({int(sc * 100)}%)", "strong": False, "score": sc})
            continue
        if ext in formats.CONVERT or ext in (".7z", ".rar"):
            if sc >= 0.7:
                res.append({"path": p, "how": f"{ext} con nombre parecido ({int(sc * 100)}%): hay que convertirlo/extraerlo", "strong": False, "score": sc})
            continue
        if strong_req:
            sz = x["size"]
            key = f"{p}|{sz}|{x['mtime']}"
            if req.get("serials") and Path(p).suffix.lower() in (".iso", ".bin", ".img", ".mdf", ".cue", ".chd") and (sc >= 0.3 or len(pool) <= 60):
                try:
                    s = library.scan_serial(p, req["serials"])
                except OSError:
                    s = None
                if s:
                    how, strong = f"serial {s}", True
            if not strong and (req.get("sha1") or req.get("crc32")) and sz <= hash_limit and (sc >= 0.3 or len(pool) <= 40 or key in cache):
                h = cache.get(key)
                if not h:
                    try:
                        h = list(library.hashes(p))
                    except OSError:
                        h = None
                    if h:
                        cache[key] = h
                        dirty = True
                if h and (h[0] in [v.lower() for v in req.get("sha1", [])] or h[1] in [v.lower() for v in req.get("crc32", [])]):
                    how, strong = "hash", True
        if not strong and req.get("md5") and x["size"] <= hash_limit and (sc >= 0.3 or len(pool) <= 40):
            try:
                if library.md5_of(p) in [v.lower() for v in req["md5"]]:
                    how, strong = "md5", True
            except OSError:
                pass
        if strong:
            res.append({"path": p, "how": how, "strong": True, "score": 1.0})
        elif sc >= 0.7:
            res.append({"path": p, "how": f"nombre parecido ({int(sc * 100)}%)", "strong": False, "score": sc})
        if cb:
            cb(i + 1, len(pool))
    if dirty:
        try:
            HASHES.write_text(json.dumps(cache), encoding="utf-8")
        except OSError:
            pass
    return sorted(res, key=lambda r: (not r["strong"], -r["score"]))[:12]


def clean_title(fname: str) -> str:
    """Nombre legible de un archivo de ROM: sin extensión ni etiquetas (USA), [!], (Disc 1)…"""
    t = re.sub(r"[\(\[][^)\]]*[\)\]]", " ", Path(fname).stem)
    t = re.sub(r"[_.]+", " ", t)
    return re.sub(r"\s+", " ", t).strip() or Path(fname).stem


def rows_from_index(index: list) -> list:
    """Un renglón por juego (se ignoran .cue/.m3u/.gdi si hay otro archivo con el mismo nombre en la misma carpeta)."""
    stems = {}
    for x in index:
        p = Path(x["p"])
        if p.suffix.lower() not in (".cue", ".m3u", ".gdi"):
            stems[(str(p.parent), p.stem)] = 1
    out = []
    for x in index:
        p = Path(x["p"])
        if p.suffix.lower() in (".cue", ".m3u", ".gdi") and (str(p.parent), p.stem) in stems:
            continue
        out.append({"name": clean_title(p.name), "plat": x["plat"], "folder": x["folder"], "path": x["p"], "size": x["size"], "match": None, "how": ""})
    out.sort(key=lambda r: (r["folder"].lower(), r["name"].lower()))
    return out


def match_catalog(rows: list, entries: list, threshold=0.7) -> list:
    """Rellena row['match'] (id del catálogo) cuando el juego de tu colección coincide con una tarjeta (misma plataforma o sin plataforma)."""
    cat = []
    for e in entries:
        names = {e["name"], e.get("group") or ""} - {""}
        cat.append((e, canon(e.get("platform", "")), [(set(toks(n)), n) for n in names]))
    for r in rows:
        rt = set(toks(r["name"]))
        if not rt:
            continue
        best, bs = None, 0.0
        for e, ep, names in cat:
            if not same_plat(ep, r["plat"]):
                continue
            for nt, n in names:
                if not nt or not (nt & rt):
                    continue
                sc = name_score(n, r["name"])
                if sc > bs:
                    best, bs = e, sc
        if best and bs >= threshold:
            r["match"], r["how"] = best["id"], f"{int(bs * 100)}%"
            print(f"[match] «{r['name']}» ({r['folder']}) -> {best['id']} «{best['name']}» {int(bs * 100)}%", file=sys.stderr, flush=True)
        elif rt:
            print(f"[match] «{r['name']}» ({r['folder']}): sin coincidencia", file=sys.stderr, flush=True)
    return rows
