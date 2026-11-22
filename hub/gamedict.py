"""Diccionario proyecto → juego (v1.85). Sirve para que buscar «ship» encuentre Ocarina of Time o «bt4» el Tenkaichi 4.
Fuentes: catalog/games.json (de serie) + data/games.local.json (tuyo, mismo formato; lo tuyo gana). Todo en minúsculas y sin tildes."""
import json
import re
import unicodedata

from . import config, esde

FILE = config.ROOT / "catalog" / "games.json"
LOCAL = config.DATA / "games.local.json"
_cache = {"key": None, "by_repo": {}, "by_id": {}, "names": []}


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _read(path):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        items = d.get("games") if isinstance(d, dict) else d
        return [x for x in items or [] if isinstance(x, dict)]
    except (OSError, ValueError):
        return []


def _stamp():
    out = []
    for p in (FILE, LOCAL):
        try:
            out.append(p.stat().st_mtime_ns)
        except OSError:
            out.append(0)
    return tuple(out)


def _load():
    key = _stamp()
    if _cache["key"] == key:
        return _cache
    by_repo, by_id, names = {}, {}, []
    for it in _read(FILE) + _read(LOCAL):           # lo local va después: pisa
        for r in it.get("repos") or []:
            by_repo[str(r).lower()] = it
        for i in it.get("ids") or []:
            by_id[str(i).lower()] = it
        for n in it.get("names") or []:
            names.append((norm(n), it))
    _cache.update(key=key, by_repo=by_repo, by_id=by_id, names=names)
    return _cache


def info(e):
    """Entrada del diccionario para esta tarjeta (por repo, por id o por trozo del nombre) o None."""
    c = _load()
    it = c["by_repo"].get(str(e.get("repo") or "").lower()) or c["by_id"].get(str(e.get("id") or "").lower())
    if it:
        return it
    nm = norm(e.get("name"))
    for frag, it in c["names"]:
        if frag and frag in nm:
            return it
    return None


def game_name(e):
    """Nombre del juego si el diccionario lo conoce y aporta algo distinto al nombre de la tarjeta; si no, None."""
    it = info(e)
    g = (it or {}).get("game")
    if not g:
        return None
    return None if norm(g) == norm(e.get("name")) else g


def system_id(e) -> str:
    """Id de ES-DE de la plataforma de la tarjeta («Nintendo 64» → n64), o ''."""
    try:
        return esde.system_for(e.get("platform") or "") or ""
    except Exception:  # noqa: BLE001
        return ""


_hay = {}


def haystack(e) -> str:
    c = _load()
    k = (e.get("id"), e.get("name"), e.get("repo"), e.get("platform"), c["key"])
    if k in _hay:
        return _hay[k]
    if len(_hay) > 4000:
        _hay.clear()
    it = info(e) or {}
    _hay[k] = norm(" ".join([str(e.get("name") or ""), str(e.get("repo") or ""), str(e.get("platform") or ""), system_id(e),
                          str(it.get("game") or ""), " ".join(it.get("aliases") or [])]))
    return _hay[k]


def match(e, query) -> bool:
    """Todas las palabras de la búsqueda aparecen (como trozo) en nombre, repo, plataforma, id ES-DE, nombre del juego o alias."""
    toks = norm(query).split()
    if not toks:
        return True
    h = haystack(e)
    return all(t in h for t in toks)
