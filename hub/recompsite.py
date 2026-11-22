"""Lector de recomplauncher.com (catálogo público de ports de PC): sitemap.xml -> /game/<slug> -> repo de GitHub.
Lee solo páginas públicas que su robots.txt permite, con pocas conexiones y reintentos; Hub luego consulta GitHub para releases/builds."""
import html
import json
import os
import re
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import catalog

BASE = os.environ.get("HUB_RECOMPLAUNCHER_BASE", "https://recomplauncher.com")
SELF_REPOS = {"elripalda/recompstore", "elripalda/recomplauncher"}
_PLAT_WORDS = [("psp", "PSP"), ("playstation portable", "PSP"), ("ps2", "PlayStation 2"), ("playstation 2", "PlayStation 2"), ("ps1", "PlayStation"),
               ("playstation", "PlayStation"), ("xbox 360", "Xbox 360"), ("xbox", "Xbox"), ("nintendo 64", "Nintendo 64"), ("n64", "Nintendo 64"),
               ("gamecube", "GameCube"), ("wii u", "Wii U"), ("wii", "Wii"), ("super nintendo", "SNES"), ("snes", "SNES"), ("game boy advance", "Game Boy Advance"),
               ("gba", "Game Boy Advance"), ("nintendo ds", "Nintendo DS"), ("3ds", "Nintendo 3DS"), ("dreamcast", "Dreamcast"), ("saturn", "Sega Saturn"),
               ("genesis", "Mega Drive"), ("mega drive", "Mega Drive"), ("switch", "Switch")]


def _get(url, timeout=30, tries=3):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (recomp-hub)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(2_000_000).decode("utf-8", "replace")
        except Exception as ex:  # noqa: BLE001
            last = ex
    raise last


def slugs(base=None) -> list:
    base = base or BASE
    xml = _get(base + "/sitemap.xml")
    return sorted(set(re.findall(r"/game/([A-Za-z0-9_.~%-]+)</loc>", xml)))


def parse_page(slug, page, base=None) -> dict:
    base = base or BASE
    t = re.search(r"<title>(.*?)</title>", page, re.S)
    title = html.unescape(t.group(1)).strip() if t else slug
    title = re.sub(r"\s*[·|]\s*RecompLauncher\s*$", "", title)
    name, _, tagline = title.partition(" — ")
    d = re.search(r'<meta name="description" content="([^"]*)"', page)
    desc = html.unescape(d.group(1)).strip() if d else ""
    systems = ""
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            j = json.loads(m.group(1))
        except ValueError:
            continue
        for o in j if isinstance(j, list) else [j]:
            if isinstance(o, dict) and o.get("operatingSystem"):
                systems = str(o["operatingSystem"])
    repo = ""
    for m in re.finditer(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", page):
        r = catalog.repo_of(f"{m.group(1)}/{m.group(2)}")
        if r and r.lower() not in SELF_REPOS and m.group(1).lower() not in ("sponsors", "orgs", "features", "settings"):
            repo = r
            break
    low = f"{tagline} {desc}".lower()
    plat = next((p for w, p in _PLAT_WORDS if re.search(r"\b" + re.escape(w) + r"\b", low)), "PC")
    tags = ["recomplauncher"] + (["linux"] if "linux" in systems.lower() else [])
    return {"id": slug, "name": name.strip() or slug, "repo": repo, "platform": plat, "folder": slug, "tags": tags,
            "notes": (tagline + (" · " if tagline and desc else "") + desc)[:300] if (tagline or desc) else "", "source": f"{base}/game/{slug}"}


def fetch_all(progress=None, base=None, workers=5) -> list:
    base = base or BASE
    sl = slugs(base)
    out, lock, n = [], threading.Lock(), [0]

    def one(s):
        try:
            e = parse_page(s, _get(f"{base}/game/{s}"), base)
        except Exception as ex:  # noqa: BLE001
            print(f"[recomplauncher] {s}: {ex}", flush=True)
            e = None
        with lock:
            n[0] += 1
            if e:
                out.append(e)
            if progress:
                progress(n[0], len(sl))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, sl))
    return sorted(out, key=lambda e: e["name"].lower())


def import_catalog(progress=None, base=None) -> tuple:
    """Escribe data/imports/recomplauncher.json. (ruta, nº de juegos)."""
    items = fetch_all(progress, base)
    if not items:
        raise RuntimeError("no pude leer ningún juego de recomplauncher.com")
    catalog.IMPORTS.mkdir(parents=True, exist_ok=True)
    p = catalog.IMPORTS / "recomplauncher.json"
    p.write_text(json.dumps({"apps": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    return p, len(items)
