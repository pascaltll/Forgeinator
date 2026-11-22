"""Fuentes de carátulas intercambiables para el selector de arte: «sgdb» (SteamGridDB, con clave) y «libretro» (libretro-thumbnails, sin cuenta ni clave).
Interfaz común: search(src, term, entry) → [{id, name}] · images(src, kind, gid, entry) → [{id, url, thumb, w, h}] · get_bytes(src, url) · fetch(src, url, dest)."""
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config, nethttp, sgdb

LIBRETRO = os.environ.get("HUB_LIBRETRO_BASE", "https://thumbnails.libretro.com")
NAMES = {"sgdb": "SteamGridDB (clave)", "libretro": "libretro (sin clave)", "tgdb": "TheGamesDB (clave)", "screenscraper": "ScreenScraper (cuenta de desarrollador)"}
ORDER = ("sgdb", "libretro", "tgdb")   # ScreenScraper sigue en el código pero fuera del menú (exige credenciales de desarrollador)
TGDB_API = os.environ.get("HUB_TGDB_API", "https://api.thegamesdb.net")
# id de plataforma de TheGamesDB (solo para ordenar resultados; si alguno no coincide, no pasa nada)
TGDB_PLAT = [("nintendo 64", 3), ("n64", 3), ("gamecube", 2), ("wii u", 38), ("wii", 9), ("super nintendo", 6), ("snes", 6), ("nes", 7), ("game boy advance", 5),
             ("game boy color", 41), ("game boy", 4), ("nintendo ds", 8), ("3ds", 4912), ("playstation 2", 11), ("playstation 3", 12), ("psp", 13), ("playstation", 10),
             ("dreamcast", 16), ("saturn", 17), ("mega drive", 18), ("genesis", 18), ("xbox 360", 15), ("xbox", 14), ("pc", 1)]
TGDB_KINDS = {"portrait": (("boxart", "front"),), "banner": (("banner", None), ("screenshot", None)), "hero": (("fanart", None), ("screenshot", None)), "icon": (("boxart", "front"),), "logo": (("clearlogo", None),)}
SS_API = os.environ.get("HUB_SCREENSCRAPER_API", "https://api.screenscraper.fr/api2")
SS_KINDS = {"portrait": ("box-2D", "box-2D-front"), "banner": ("sstitle", "marquee", "ss"), "hero": ("fanart", "ss", "sstitle"), "icon": ("box-2D", "wheel"), "logo": ("wheel-hd", "wheel")}
# tipo de Hub → carpetas de libretro-thumbnails (en orden de preferencia)
LR_KINDS = {"portrait": ("Named_Boxarts",), "banner": ("Named_Titles", "Named_Boxarts"), "hero": ("Named_Snaps", "Named_Titles"), "icon": ("Named_Boxarts",), "logo": ("Named_Logos",)}
# palabra clave de la plataforma (minúsculas) → carpeta de sistema en libretro-thumbnails
LR_SYSTEMS = [
    ("nintendo 64", "Nintendo - Nintendo 64"), ("n64", "Nintendo - Nintendo 64"), ("gamecube", "Nintendo - GameCube"), ("wii u", "Nintendo - Wii U"),
    ("wii", "Nintendo - Wii"), ("super nintendo", "Nintendo - Super Nintendo Entertainment System"), ("snes", "Nintendo - Super Nintendo Entertainment System"),
    ("nes", "Nintendo - Nintendo Entertainment System"), ("game boy advance", "Nintendo - Game Boy Advance"), ("game boy color", "Nintendo - Game Boy Color"),
    ("game boy", "Nintendo - Game Boy"), ("nintendo ds", "Nintendo - Nintendo DS"), ("3ds", "Nintendo - Nintendo 3DS"),
    ("playstation 2", "Sony - PlayStation 2"), ("playstation 3", "Sony - PlayStation 3"), ("psp", "Sony - PlayStation Portable"),
    ("playstation", "Sony - PlayStation"), ("psx", "Sony - PlayStation"), ("ps1", "Sony - PlayStation"),
    ("dreamcast", "Sega - Dreamcast"), ("saturn", "Sega - Saturn"), ("mega drive", "Sega - Mega Drive - Genesis"), ("genesis", "Sega - Mega Drive - Genesis"),
    ("master system", "Sega - Master System - Mark III"), ("game gear", "Sega - Game Gear"), ("xbox 360", "Microsoft - Xbox 360"), ("xbox", "Microsoft - Xbox"),
]
UA = "recomp-hub/1"


def lr_system(platform: str):
    p = (platform or "").lower()
    return next((v for k, v in LR_SYSTEMS if k in p), None)


def _open(url, headers=None, timeout=20, tries=3, method="GET"):
    """v2.77: nethttp (normal → IPv4 → normal) con la causa real en el error; 401/403/404 se relanzan para que cada fuente los interprete."""
    return nethttp.get(url, headers, timeout=timeout, tries=tries, method=method)


def _clean(name):
    return re.sub(r"[&*/:`<>?\\|\"]", "_", name)


def _toks(s):
    return [t for t in re.findall(r"[a-z0-9]+", re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s.lower())) if t not in ("the", "of", "recompiled", "recomp", "decompiled", "port", "native")]


def _index(system, folder):
    """Nombres (sin .png) que hay en <sistema>/<carpeta>/, desde el listado HTML del servidor; cache 7 días."""
    cache = config.DATA / "cache" / "libretro"
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / (re.sub(r"\W+", "_", system + "_" + folder) + ".txt")
    try:
        if time.time() - f.stat().st_mtime < 7 * 86400:
            return f.read_text(encoding="utf-8").splitlines()
    except OSError:
        pass
    html = _open(f"{LIBRETRO}/{urllib.parse.quote(system)}/{folder}/", timeout=60).decode("utf-8", "replace")
    names = sorted({urllib.parse.unquote(m)[:-4] for m in re.findall(r'href="([^"?/][^"]*\.png)"', html, re.I)})
    f.write_text("\n".join(names), encoding="utf-8")
    return names


def search(src, term, entry=None):
    if src == "sgdb":
        return sgdb.search(term)
    if src == "screenscraper":
        return ss_search(term, entry)
    if src == "tgdb":
        return tgdb_search(term, entry)
    system = lr_system((entry or {}).get("platform", ""))
    if not system:
        raise OSError(f"libretro no tiene carpeta para la plataforma «{(entry or {}).get('platform') or '?'}» (PC y PS4 no están)")
    q = set(_toks(term))
    scored = []
    for n in _index(system, "Named_Boxarts"):
        t = set(_toks(n))
        if q and t:
            ov = len(q & t)
            if ov:
                scored.append((ov / len(q | t), n))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return [{"id": n, "name": n, "system": system} for _, n in scored[:12]]


def images(src, kind, gid, entry=None):
    if src == "sgdb":
        return sgdb.images(kind, gid)
    if src == "screenscraper":
        return ss_images(kind, gid)
    if src == "tgdb":
        return tgdb_images(kind, gid)
    system = lr_system((entry or {}).get("platform", ""))
    out = []
    for folder in LR_KINDS[kind]:
        url = f"{LIBRETRO}/{urllib.parse.quote(system)}/{folder}/{urllib.parse.quote(_clean(gid))}.png"
        try:
            _open(url, tries=1, method="HEAD", timeout=25)
        except Exception:  # noqa: BLE001
            continue
        out.append({"id": f"{folder}:{gid}", "url": url, "thumb": url, "w": None, "h": None, "style": folder})
    return out


def get_bytes(src, url, timeout=45):
    if src == "sgdb":
        return sgdb._get(url, raw=True, timeout=timeout)
    return _open(url, timeout=timeout)


def fetch(src, url, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(get_bytes(src, url, 90))
    return dest


# ── TheGamesDB (thegamesdb.net) ──
def tgdb_key():
    return os.environ.get("THEGAMESDB_KEY") or sgdb.env_get("THEGAMESDB_KEY")


def _tgdb(path, **params):
    import json
    k = tgdb_key()
    if not k:
        raise OSError("TheGamesDB necesita clave de API (botón PEGAR CLAVE). Se pide en thegamesdb.net / su foro")
    try:
        raw = _open(f"{TGDB_API}{path}?" + urllib.parse.urlencode({"apikey": k, **params}), timeout=45)
    except urllib.error.HTTPError as ex:
        if ex.code in (401, 403):
            raise OSError("TheGamesDB no aceptó la clave de API: revísala (CAMBIAR CLAVE)")
        raise
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise OSError("TheGamesDB respondió algo que no es JSON: " + raw.decode("utf-8", "replace").strip()[:120])


def tgdb_search(term, entry=None):
    d = _tgdb("/v1.1/Games/ByGameName", name=term)
    games = ((d.get("data") or {}).get("games")) or []
    plat = ((entry or {}).get("platform") or "").lower()
    want = next((v for k, v in TGDB_PLAT if k in plat), None)
    out = []
    for g in games:
        if not isinstance(g, dict) or not g.get("id"):
            continue
        yr = str(g.get("release_date") or "")[:4]
        out.append((0 if want and g.get("platform") == want else 1, {"id": str(g["id"]), "name": f"{g.get('game_title', '?')}" + (f" ({yr})" if yr else "")}))
    out.sort(key=lambda t: t[0])
    return [g for _, g in out][:12]


def tgdb_images(kind, gid):
    d = _tgdb("/v1/Games/Images", games_id=gid)
    data = d.get("data") or {}
    base = data.get("base_url") or {}
    orig, thumb = base.get("original") or "https://cdn.thegamesdb.net/images/original/", base.get("thumb") or base.get("small") or ""
    imgs = ((data.get("images") or {}).get(str(gid))) or []
    out, seen = [], set()
    for typ, side in TGDB_KINDS[kind]:
        for m in imgs:
            if m.get("type") == typ and (side is None or m.get("side") == side) and m.get("filename") and m["filename"] not in seen:
                seen.add(m["filename"])
                url = orig + m["filename"]
                out.append({"id": f"{typ}:{m.get('id', len(out))}", "url": url, "thumb": (thumb + m["filename"]) if thumb else url, "w": None, "h": None, "style": typ})
    return out[:16]


# ── ScreenScraper (screenscraper.fr) ──
def ss_creds():
    return {"user": sgdb.env_get("SCREENSCRAPER_USER"), "password": sgdb.env_get("SCREENSCRAPER_PASSWORD"),
            "devid": sgdb.env_get("SCREENSCRAPER_DEV_ID"), "devpassword": sgdb.env_get("SCREENSCRAPER_DEV_PASSWORD")}


def _ss(endpoint, **params):
    import json
    c = ss_creds()
    if not c["user"] or not c["password"]:
        raise OSError("ScreenScraper: falta usuario o contraseña (botones USUARIO y CONTRASEÑA)")
    q = {"output": "json", "softname": "recomp-hub", "ssid": c["user"], "sspassword": c["password"], **params}
    if c["devid"]:
        q.update(devid=c["devid"], devpassword=c["devpassword"])
    raw = _open(f"{SS_API}/{endpoint}?" + urllib.parse.urlencode(q), timeout=60)
    txt = raw.decode("utf-8", "replace")
    try:
        return json.loads(txt)
    except ValueError:
        low = txt.lower()
        if "veloppeur" in low or "developer" in low or "devid" in low:
            raise OSError("ScreenScraper exige credenciales de DESARROLLADOR (devid/devpassword), no solo tu cuenta (" + txt.strip()[:70] + "). "
                          "Pídelas en el foro de screenscraper.fr y ponlas en ~/Games/launcher/.env como SCREENSCRAPER_DEV_ID y SCREENSCRAPER_DEV_PASSWORD")
        if any(w in low for w in ("login", "identifiant", "erreur de", "unauthor", "403", "401", "mot de passe", "password")):
            raise OSError("ScreenScraper no aceptó tu usuario o contraseña («" + txt.strip()[:90] + "»). Cámbialos con los botones USUARIO / CONTRASEÑA")
        raise OSError("ScreenScraper respondió: " + (txt.strip()[:160] or "respuesta vacía"))


def _ss_name(j):
    ns = j.get("noms") or []
    for pref in ("us", "wor", "eu", "ss"):
        for n in ns:
            if n.get("region") == pref and n.get("text"):
                return n["text"]
    return (ns[0].get("text") if ns else j.get("nom")) or "?"


def ss_search(term, entry=None):
    d = _ss("jeuRecherche.php", recherche=term)
    jeux = ((d.get("response") or {}).get("jeux")) or []
    plat = ((entry or {}).get("platform") or "").lower().split()
    out = []
    for j in jeux:
        if not isinstance(j, dict) or not j.get("id"):
            continue
        sysname = ((j.get("systeme") or {}).get("text") or "")
        hit = any(w in sysname.lower() for w in plat if len(w) > 2)
        out.append((0 if hit else 1, {"id": str(j["id"]), "name": f"{_ss_name(j)} · {sysname}" if sysname else _ss_name(j)}))
    out.sort(key=lambda t: t[0])
    return [g for _, g in out][:12]


def ss_images(kind, gid):
    d = _ss("jeuInfos.php", gameid=gid)
    medias = (((d.get("response") or {}).get("jeu")) or {}).get("medias") or []
    out, seen = [], set()
    for typ in SS_KINDS[kind]:
        for m in medias:
            if m.get("type") == typ and m.get("url") and m["url"] not in seen:
                seen.add(m["url"])
                out.append({"id": f"{typ}:{m.get('region', '')}:{len(out)}", "url": m["url"], "thumb": m["url"], "w": None, "h": None, "style": m.get("region", "")})
    return out[:16]


def thumb_bytes(src, url, timeout=30):
    """Miniatura con caché en disco (data/cache/art/): volver a ver las mismas opciones es instantáneo."""
    import hashlib
    f = config.DATA / "cache" / "art" / (hashlib.sha1(url.encode()).hexdigest() + ".bin")
    try:
        if f.stat().st_size > 0:
            return f.read_bytes()
    except OSError:
        pass
    data = get_bytes(src, url, timeout)
    if data:
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        except OSError:
            pass
    return data
