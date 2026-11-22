"""Descarga ÚNICA de carátulas desde SteamGridDB para todo el catálogo. Se guardan en data/covers/<id>.<ext>;
lo ya descargado no se vuelve a pedir (ni se pisa), así que repetirlo solo baja lo que falta."""
import os
import time
from pathlib import Path

from . import config, sgdb

EXTS = (".png", ".jpg", ".jpeg", ".webp")


def dir_() -> Path:
    return config.DATA / "covers"


def path_for(entry_id: str):
    d = dir_()
    for x in EXTS:
        p = d / (entry_id + x)
        if p.is_file():
            return p
    return None


def have() -> set:
    """Ids con carátula, con UN solo listado de la carpeta (no 4 stat por juego)."""
    try:
        return {Path(n).stem for n in os.listdir(dir_()) if n.lower().endswith(EXTS)}
    except OSError:
        return set()


def missing(entries):
    h = have()
    return [e for e in entries if e["id"] not in h]


def clean_name(name: str) -> str:
    n = name.split(":")[0] if ":" in name and len(name.split(":")[0]) > 3 else name
    return n.replace("Recompiled", "").replace("Recomp", "").strip() or name


def fetch_one(entry, search=sgdb.search, images=sgdb.images, fetch=sgdb.fetch) -> str:
    """'ok' | 'sin resultados'. Prueba el nombre limpio y luego el completo; usa la primera portada vertical (o banner)."""
    for term in dict.fromkeys([clean_name(entry["name"]), entry["name"]]):
        cands = search(term)
        for c in cands[:3]:
            for kind in ("portrait", "banner", "hero"):
                imgs = images(kind, c["id"], 3)
                if imgs:
                    url = imgs[0]["url"]
                    ext = Path(url.split("?")[0]).suffix.lower()
                    ext = ext if ext in EXTS else ".png"
                    fetch(url, dir_() / (entry["id"] + ext))
                    return "ok"
    return "sin resultados"


def batch(entries, progress=None, stop=lambda: False, pause=0.25, **kw):
    """Baja lo que falta. Devuelve {'ok','sin','error','total'}. progress(i,total,nombre)."""
    todo = missing(entries)
    r = {"ok": 0, "sin": 0, "error": 0, "total": len(todo)}
    for i, e in enumerate(todo, 1):
        if stop():
            break
        if progress:
            progress(i, len(todo), e["name"])
        try:
            r["ok" if fetch_one(e, **kw) == "ok" else "sin"] += 1
        except Exception:  # noqa: BLE001
            r["error"] += 1
        time.sleep(pause)
    return r
