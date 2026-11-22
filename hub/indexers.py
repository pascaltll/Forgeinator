"""Indexador del catálogo público «awesome-decomp-games» (data/games.json) → data/imports/00-awesome-decomp.json.

Reglas (acordadas): entran los proyectos de tipo recomp estática, port de código fuente, engine-remake y decompilación **que tienen release**
(aunque estén archivados o sin actividad: un proyecto terminado no necesita actualizaciones; se marcan «sin-mantenimiento»).
El resto de recomp/port/remake/decompilación (sin release: hay que compilarlos) entra con la etiqueta «solo-codigo» y la UI lo oculta
salvo en Explorar → «Solo código». Se descartan disassembly, browser-port, tool y mods, y lo que no esté en GitHub.
Nunca pisa tu catálogo: se salta los repos que ya están en el seed, en tus entradas o en otras listas importadas."""
import json
import re
import urllib.request
from pathlib import Path

from . import catalog, config

URL = "https://raw.githubusercontent.com/SubmitGame/awesome-decomp-games/main/data/games.json"
OUT_NAME = "00-awesome-decomp.json"      # el «00-» hace que cualquier otra lista (RecompLauncher, Quiver…) y tu catálogo local lo pisen a él, no al revés
CORE = ("static-recomp", "source-port", "engine-remake", "decompilation")
KIND = {"static-recomp": "recompilación estática", "source-port": "port de código fuente", "engine-remake": "remake de motor", "decompilation": "decompilación"}
PLAT = {"N64": "Nintendo 64", "PS1": "PlayStation", "PS2": "PlayStation 2", "PS3": "PlayStation 3", "PS4": "PlayStation 4", "PS5": "PlayStation 5",
        "GBA": "Game Boy Advance", "Game Boy Color": "Game Boy Color", "GameCube": "GameCube", "DS": "Nintendo DS", "3DS": "Nintendo 3DS",
        "Switch": "Nintendo Switch", "Wii U": "Wii U", "og xbox": "Xbox", "Mobile": "Móvil", "Android / iOS": "Móvil", "Genesis": "Sega Genesis",
        "N64 / GameCube": "Nintendo 64", "PS1 / PSP / Saturn": "PlayStation", "Other": "", "Others": "", "Mac": "macOS"}
NO_FILES = {"PC", "DOS", "Mobile", "Móvil", "Mac", "macOS", "Arcade", ""}   # plataformas donde no se pide «tu propia copia» por defecto


def platform(p) -> str:
    p = str(p or "").strip()
    return PLAT.get(p, p)


def _date(s) -> str:
    return str(s or "")[:7]


def _entry(g: dict) -> dict:
    plat = platform(g.get("platform"))
    raw = str(g.get("platform") or "")
    if "/" in raw:   # categoría mezclada («PS1 / PSP / Saturn»): elegir por las pistas del propio juego, no siempre la primera
        g2 = catalog.guess_console({"name": g.get("title"), "repo": g.get("repo"), "notes": g.get("description")})
        opts = {platform(x.strip()) for x in raw.split("/")} | {x.strip() for x in raw.split("/")}
        if g2 and (g2 in opts or g2 == "PSP" and "PSP" in raw):
            plat = g2
    has_rel = bool(g.get("release"))
    old = bool(g.get("archived") or g.get("inactive"))
    tags = [g["type"]]
    if plat:
        tags.append(plat.lower())
    if not has_rel:
        tags.append("solo-codigo")
    if old:
        tags.append("sin-mantenimiento")
    bits = [KIND.get(g["type"], g["type"])]
    if g.get("stars"):
        bits.append(f"★ {g['stars']}")
    if has_rel:
        bits.append(f"última versión {g['release']}" + (f" ({_date(g.get('release_date'))})" if g.get("release_date") else ""))
    if g.get("last_commit"):
        bits.append("último commit " + _date(g["last_commit"]))
    if g.get("archived"):
        bits.append("repositorio archivado (terminado o abandonado)")
    elif g.get("inactive"):
        bits.append("sin actividad reciente")
    if not has_rel:
        bits.append("sin release: hay que compilarlo")
    desc = str(g.get("description") or "").strip()
    e = {"id": "ad-" + catalog.slug(g["repo"].replace("/", "-")), "name": str(g.get("title") or g["repo"].split("/")[-1]).strip(),
         "repo": g["repo"], "platform": plat, "folder": catalog.slug(g["repo"].split("/")[-1]), "tags": tags,
         "notes": (desc + "\n" if desc else "") + " · ".join(bits)}
    if g.get("homepage"):
        e["notes"] += "\n" + str(g["homepage"])
    if plat not in NO_FILES or g.get("needs_assets"):
        e["requires"] = {"note": "Necesitas tu propia copia del juego; el proyecto no incluye sus archivos."}
    return e


def build(data: dict, skip_repos=()) -> list:
    """Entradas del Hub a partir del JSON de awesome-decomp-games; ordenadas: con release primero, luego por estrellas."""
    skip = {str(r).lower() for r in skip_repos}
    seen, out = set(), []
    for g in data.get("games", []):
        repo = str(g.get("repo") or "")
        if g.get("type") not in CORE or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or "github.com" not in str(g.get("url") or "github.com"):
            continue
        k = repo.lower()
        if k in skip or k in seen:
            continue
        seen.add(k)
        out.append((bool(g.get("release")), g.get("stars") or 0, _entry(g)))
    out.sort(key=lambda t: (not t[0], -t[1]))
    return [e for _, _, e in out]


def known_repos() -> set:
    """Repos que ya tienes (seed + tus entradas + otras listas importadas distintas de la nuestra)."""
    s = set()
    for src in [catalog.SEED, catalog.LOCAL] + [p for p in sorted(catalog.IMPORTS.glob("*.json")) if p.name != OUT_NAME]:
        for e in catalog._load_file(src):
            if e.get("repo"):
                s.add(e["repo"].lower())
    return s


def fetch(url=URL, timeout=40) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "recomp-hub"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(30_000_000).decode("utf-8"))


def update(data=None, dest=None) -> dict:
    """Descarga (o usa `data`), filtra y escribe la lista. Si el resultado sale vacío NO toca la anterior.
    Devuelve {total, listos, solo_codigo, sin_mantenimiento, nuevos_omitidos, path}."""
    data = fetch() if data is None else data
    if not isinstance(data, dict) or not isinstance(data.get("games"), list):
        raise ValueError("el JSON no tiene la forma esperada ({'games': [...]})")
    skip = known_repos()
    entries = build(data, skip)
    if not entries:
        raise ValueError("el filtro dejó 0 proyectos; se conserva la lista anterior")
    dest = Path(dest) if dest else catalog.IMPORTS / OUT_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(dest)
    solo = sum(1 for e in entries if "solo-codigo" in e["tags"])
    return {"total": len(entries), "listos": len(entries) - solo, "solo_codigo": solo,
            "sin_mantenimiento": sum(1 for e in entries if "sin-mantenimiento" in e["tags"]), "ya_los_tenias": len(skip), "path": str(dest)}
