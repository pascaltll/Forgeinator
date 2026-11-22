"""Catálogo de juegos: seed propio + listas importadas (formato apps.json de GithubLauncher/Quiver y similares) + tus entradas.

Una entrada:  {id, name, repo "owner/repo", platform, folder, icon, tags[], notes, requires{serials[], sha1[], formats[], region, note}}
Prioridad (menor → mayor): catalog/seed.json < data/imports/*.json < data/catalog.local.json
"""
import json
import re
import urllib.request
from pathlib import Path

from . import config

SEED = config.ROOT / "catalog" / "seed.json"
IMPORTS = config.DATA / "imports"
LOCAL = config.DATA / "catalog.local.json"


COMMUNITY_INDEX = "https://raw.githubusercontent.com/tgeorgiadis/quiver-community-app-catalog/main/index.json"
PRESETS = [("Comunidad Quiver (Nintendo, PlayStation, Xbox, otras)", COMMUNITY_INDEX),
           ("RecompLauncher (~280 ports de PC, lee su web)", "recomplauncher:")]
_PLAT = [("ps5", "PlayStation 5"), ("ps4", "PlayStation 4"), ("ps2", "PlayStation 2"), ("ps3", "PlayStation 3"), ("psp", "PSP"), ("ps1", "PlayStation"), ("playstation", "PlayStation"),
         ("x360", "Xbox 360"), ("xbox 360", "Xbox 360"), ("xbox", "Xbox"), ("n64", "Nintendo 64"), ("snes", "SNES"), ("gba", "Game Boy Advance"),
         ("gbc", "Game Boy Color"), ("gcn", "GameCube"), ("gamecube", "GameCube"), ("wii", "Wii"), ("nes", "NES"), ("sega", "Sega"),
         ("mobile", "Móvil"), ("pc", "PC"), ("nintendo", "Nintendo")]


# «Plataforma» en algunas listas (Quiver, RecompLauncher…) es dónde CORRE el port (PC/Windows/Linux), no la consola del juego original
HOST = {"pc", "windows", "win", "win64", "linux", "desktop", "steam deck", "steamdeck", "macos", "mac", "native", "pc port", "windows/linux", "pc/linux"}
_GUESS = [(t, n) for t, n in _PLAT if t not in ("pc", "nintendo", "sega", "mobile", "playstation", "xbox")]


def is_host(platform) -> bool:
    return str(platform or "").strip().lower() in HOST


def guess_console(e: dict) -> str:
    """Consola original por palabras sueltas del nombre, repo, carpeta, etiquetas y notas («psp», «ps2», «n64»…); '' si no hay pista clara."""
    words = set(re.split(r"[^a-z0-9]+", " ".join(str(e.get(k) or "") for k in ("name", "repo", "folder", "notes")).lower()))
    words |= {str(x).lower() for x in e.get("tags") or []}
    hits = {n for t, n in _GUESS if t in words}
    return hits.pop() if len(hits) == 1 else ""


def platform_from_tags(tags) -> str:
    t = {str(x).lower() for x in tags or []}
    return next((name for tag, name in _PLAT if tag in t), "")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "juego"


def repo_of(v) -> str:
    """'owner/repo' a partir de 'owner/repo', 'https://github.com/owner/repo(.git)(/...)' o ''."""
    v = str(v or "").strip()
    m = re.search(r"github\.com[/:]([^/\s]+)/([^/\s#?]+)", v)
    if m:
        repo = re.sub(r"\.git$", "", m.group(2))
        return f"{m.group(1)}/{repo}"
    return v if re.fullmatch(r"[\w.-]+/[\w.-]+", v) else ""


_ASSET_EXT = r"\.(zip|7z|rar|tar\.gz|tgz|tar\.xz|tar\.bz2|appimage|iso|chd|rvz|bin|exe|deb|rpm|flatpak|xz|gz)"


def asset_url(v) -> str:
    """URL directa de descarga (asset de release de GitHub o archivo con extensión conocida), o ''."""
    v = str(v or "").strip()
    if not re.fullmatch(r"https?://\S+", v):
        return ""
    if re.match(r"https://github\.com/[^/]+/[^/]+/releases/download/", v):
        return v
    if re.search(_ASSET_EXT + r"(\?\S*)?$", v, re.I):
        return v
    return ""


def _get(d: dict, *names, default=""):
    low = {k.lower().replace("_", ""): v for k, v in d.items()}
    for n in names:
        if n.lower().replace("_", "") in low and low[n.lower().replace("_", "")] not in (None, ""):
            return low[n.lower().replace("_", "")]
    return default


def normalize(d: dict):
    """Acepta variantes de claves (name/Name, repo/Repository/GitHubRepo, folder/FolderName…). None si no sirve."""
    if not isinstance(d, dict):
        return None
    if str(_get(d, "repositorysource", default="github")).lower() not in ("github", ""):
        return None  # GitLab u otros: Hub solo descarga de GitHub
    name = str(_get(d, "name", "title", "displayname", "appname"))
    repo = repo_of(_get(d, "repo", "repository", "githubrepo", "github", "url", "source", "releaseurl"))
    folder = str(_get(d, "folder", "foldername", "dir"))
    if not name and not repo:
        return None
    name = name or repo.split("/")[-1]
    e = {
        "id": str(_get(d, "id", "slug", default="")) or slug(folder or name),
        "name": name, "repo": repo, "folder": folder or slug(name),
        "platform": str(_get(d, "platform", "console", "system")) or platform_from_tags(_get(d, "tags", default=[])),
        "asset_filter": str(_get(d, "releaseassetfilter", "assetfilter")),
        "icon": str(_get(d, "icon", "iconurl", "image", "cover")),
        "tags": list(_get(d, "tags", default=[]) or []),
        "notes": str(_get(d, "notes", "description", "desc")),
    }
    if d.get("variant"):
        e["variant"] = True
    if d.get("group"):
        e["group"] = str(d["group"])
    if _get(d, "launcherid", "launcher_id"):
        e["launcher_id"] = str(_get(d, "launcherid", "launcher_id"))
    if isinstance(d.get("build"), dict):
        e["build"] = d["build"]
    req = _get(d, "requires", default={})
    if isinstance(req, dict) and req:
        e["requires"] = req
    return e


def _expand(d: dict) -> list:
    """Una entrada con "variants": [...] se convierte en una entrada por variante (comparten juego, difieren en repo/carpeta/ISO/mod).
    Cada variante hereda del juego lo que no defina: {id,label,repo,folder,launcher_id,platform,notes,requires}."""
    vs = d.get("variants") if isinstance(d, dict) else None
    if not isinstance(vs, list) or not vs:
        return [d]
    base = {k: v for k, v in d.items() if k != "variants"}
    out = []
    for v in vs:
        if not isinstance(v, dict):
            continue
        e = dict(base)
        e.update(v)
        label = str(v.get("label", "")).strip()
        e["group"] = str(base.get("name", ""))
        e["variant"] = True
        e["name"] = f"{base.get('name', '')} — {label}" if label else str(base.get("name", ""))
        e["id"] = str(v.get("id") or f"{base.get('id') or slug(base.get('name', ''))}-{slug(label)}")
        out.append(e)
    return out


def parse(obj) -> list:
    """Lista de entradas normalizadas desde: lista, {"apps": [...]}, {"games": [...]} o {nombre: {...}}."""
    if isinstance(obj, dict):
        for k in ("apps", "games", "projects", "entries", "items", "ports"):
            if isinstance(obj.get(k), list):
                obj = obj[k]
                break
        else:
            if obj and all(isinstance(v, dict) for v in obj.values()):
                obj = [dict(v, name=v.get("name", k)) for k, v in obj.items()]
            else:
                obj = [obj]
    out = []
    for d0 in obj if isinstance(obj, list) else []:
        for d in _expand(d0):
            e = normalize(d)
            if e:
                if d.get("group"):
                    e["group"] = d["group"]
                out.append(e)
    return out


def _load_file(p: Path) -> list:
    try:
        return parse(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return []


def _extra_requirements() -> dict:
    try:
        d = json.loads((config.ROOT / "catalog" / "requirements.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k.lower(): v for k, v in d.items() if isinstance(v, dict) and not k.startswith("_")}


def _apply_requirements(e: dict):
    """Completa lo que el port pide del disco (serial/región/nota) con catalog/requirements.json, sin pisar lo que ya traiga la tarjeta."""
    extra = _extra_requirements().get((e.get("repo") or "").lower())
    if not extra:
        return
    req = dict(e.get("requires") or {})
    for k, v in extra.items():
        if not req.get(k):
            req[k] = v
    e["requires"] = req


def load() -> list:
    """Catálogo combinado y sin duplicados (por repo o id); lo posterior pisa a lo anterior."""
    entries, order, id_key = {}, [], {}
    sources = [SEED] + sorted(IMPORTS.glob("*.json")) + [LOCAL]
    for src in sources:
        for e in _load_file(src):
            key = id_key.get(e["id"]) or (e["id"] if (e.get("variant") or not e["repo"]) else e["repo"].lower())
            id_key.setdefault(e["id"], key)
            if key not in entries:
                order.append(key)
                entries[key] = e
            else:
                merged = dict(entries[key])
                keep_plat = merged.get("platform") and not is_host(merged["platform"]) and is_host(e.get("platform"))
                merged.update({k: v for k, v in e.items() if v not in ("", [], {}, None)})
                if keep_plat:
                    merged["platform"] = entries[key]["platform"]   # PSP no pasa a «PC» porque otra lista diga dónde corre el port
                entries[key] = merged
    vrepos = {e["repo"].lower() for e in entries.values() if e.get("variant") and e["repo"]}
    ids, res = set(), []
    for k in order:
        e = entries[k]
        if not e.get("variant") and e["repo"] and e["repo"].lower() in vrepos:
            continue  # el mismo repo ya está como variante propia (p. ej. BT3 USA/Latino)
        base, n = e["id"], 2
        while e["id"] in ids:
            e["id"] = f"{base}-{n}"
            n += 1
        ids.add(e["id"])
        _apply_requirements(e)
        if is_host(e.get("platform")):
            g = guess_console(e)
            if g:
                e["platform"] = g
        res.append(e)
    return res


def import_source(src: str, name=None) -> tuple:
    """Importa una lista desde archivo local o URL (http/https) a data/imports/. Devuelve (ruta, nº de entradas)."""
    if re.match(r"https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "recomp-hub"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(8_000_000).decode("utf-8", "replace")
    else:
        raw = Path(src).expanduser().read_text(encoding="utf-8")
    obj = json.loads(raw)
    if isinstance(obj, dict) and isinstance(obj.get("lists"), list):  # índice de listas (catálogo comunitario)
        total, last = 0, None
        for it in obj["lists"]:
            loc = it.get("remoteLocation") or it.get("location") or ""
            if loc.startswith("http"):
                last, n = import_source(loc)
                total += n
        if not total:
            raise ValueError("el índice no trae listas descargables")
        return last, total
    entries = parse(obj)
    if not entries:
        raise ValueError("la lista no contiene juegos reconocibles (se espera name + repo)")
    IMPORTS.mkdir(parents=True, exist_ok=True)
    dest = IMPORTS / f"{slug(name or Path(src).stem or 'lista')}.json"
    dest.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    return dest, len(entries)


def add_local(entry: dict):
    """Añade/actualiza una entrada tuya en data/catalog.local.json."""
    cur = _load_file(LOCAL)
    e = normalize(entry)
    if not e:
        raise ValueError("falta name o repo")
    cur = [c for c in cur if c["id"] != e["id"]] + [e]
    config.DATA.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(json.dumps(cur, indent=1, ensure_ascii=False), encoding="utf-8")
    return e


def is_local_only(eid: str) -> bool:
    """¿La tarjeta existe SOLO en tu catalog.local.json (no viene del catálogo de serie ni de una lista importada)?"""
    if not any(e["id"] == eid for e in _load_file(LOCAL)):
        return False
    others = [SEED] + sorted(IMPORTS.glob("*.json"))
    return not any(e["id"] == eid for src in others for e in _load_file(src))


def remove_local(eid: str) -> bool:
    cur = _load_file(LOCAL)
    new = [c for c in cur if c["id"] != eid]
    if len(new) == len(cur):
        return False
    LOCAL.write_text(json.dumps(new, indent=1, ensure_ascii=False), encoding="utf-8")
    return True


def find_dupes(repo: str, name: str, entries=None, launcher_games=None) -> dict:
    """{"exact": entrada|None, "launcher": id|None, "similar": [entradas]}: ¿ya existe este repo/juego en tu catálogo o launcher?"""
    import difflib
    entries = load() if entries is None else entries
    low = repo.lower()
    exact = [e for e in entries if e["repo"].lower() == low]
    lid = next((g["id"] for g in (launcher_games or []) if g.get("repo") and g["repo"] == low), None)
    norm = lambda t: re.sub(r"[^a-z0-9]+", "", str(t).lower())  # noqa: E731
    n = norm(name)
    sim = []
    if n:
        for e in entries:
            if e in exact:
                continue
            m = norm(e.get("group") or e["name"])
            if m and (difflib.SequenceMatcher(None, n, m).ratio() >= 0.82 or (len(n) >= 6 and (n in m or m in n))):
                sim.append(e)
    return {"exact": exact, "launcher": lid, "similar": sim[:5]}
