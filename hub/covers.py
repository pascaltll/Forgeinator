"""Descarga de carátulas para todo el catálogo (SteamGridDB y, para juegos de consola, libretro-thumbnails). Se guardan en data/covers/<id>.<ext>;
lo ya descargado no se vuelve a pedir (ni se pisa), así que repetirlo solo baja lo que falta."""
import concurrent.futures
import json
import os
import threading
import time
import urllib.parse
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


MISS_FILE = ".sin-resultado.json"
RETRY_DAYS = 14                      # v3.20: un juego sin carátula en ninguna fuente no se vuelve a buscar hasta pasados estos días
WORKERS = 4                          # v3.20: descargas a la vez (antes, una tras otra con 0,25 s de pausa)


def _misses_path() -> Path:
    return dir_() / MISS_FILE


def misses() -> dict:
    """{id: cuándo se buscó sin resultado} de los que no tienen carátula en ninguna fuente."""
    try:
        d = json.loads(_misses_path().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_misses(d: dict) -> None:
    try:
        dir_().mkdir(parents=True, exist_ok=True)
        tmp = _misses_path().with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=0, sort_keys=True), encoding="utf-8")
        os.replace(tmp, _misses_path())
    except OSError:
        pass


def recent_misses(entries) -> int:
    """Cuántos de estos se buscaron sin resultado hace menos de RETRY_DAYS."""
    m, now = misses(), time.time()
    return sum(1 for e in entries if now - float(m.get(e["id"], 0)) <= RETRY_DAYS * 86400)


def missing(entries, include_misses=True):
    """Sin carátula. include_misses=False quita los que no se encontraron hace menos de RETRY_DAYS (no se vuelven a pedir)."""
    h = have()
    todo = [e for e in entries if e["id"] not in h]
    if include_misses:
        return todo
    m, now = misses(), time.time()
    return [e for e in todo if now - float(m.get(e["id"], 0)) > RETRY_DAYS * 86400]


def clean_name(name: str) -> str:
    n = name.split(":")[0] if ":" in name and len(name.split(":")[0]) > 3 else name
    return n.replace("Recompiled", "").replace("Recomp", "").strip() or name


def _save(url, dest_stem: str, fetch) -> None:
    ext = Path(url.split("?")[0]).suffix.lower()
    ext = ext if ext in EXTS else ".png"
    fetch(url, dir_() / (dest_stem + ext))


def fetch_sgdb(entry, search=sgdb.search, images=sgdb.images, fetch=sgdb.fetch) -> bool:
    """SteamGridDB: nombre limpio y luego el completo; los 2 primeros candidatos; portada vertical o, si no, banner.
    v3.20: antes probaba 3 candidatos × 3 tipos × 2 nombres (hasta 18 consultas por cada juego que no existe)."""
    for term in dict.fromkeys([clean_name(entry["name"]), entry["name"]]):
        for c in search(term)[:2]:
            for kind in ("portrait", "banner"):
                imgs = images(kind, c["id"], 3)
                if imgs:
                    _save(imgs[0]["url"], entry["id"], fetch)
                    return True
    return False


def fetch_libretro(entry) -> bool:
    """v3.20: libretro-thumbnails (sin clave; lo usa RetroArch) para juegos de consola: el índice de cada sistema se baja una vez
    (caché de 7 días) y se busca en local, así que cuesta una sola descarga por juego."""
    from . import artsrc
    system = artsrc.lr_system(entry.get("platform", ""))
    if not system:
        return False
    q = set(artsrc._toks(clean_name(entry["name"])))
    best, score = None, 0.0
    for n in artsrc._index(system, "Named_Boxarts"):
        t = set(artsrc._toks(n))
        if q and t:
            sc = len(q & t) / len(q | t)
            if sc > score or (sc == score and best and len(n) < len(best)):
                best, score = n, sc
    if not best or score < 0.6:
        return False
    url = f"{artsrc.LIBRETRO}/{urllib.parse.quote(system)}/Named_Boxarts/{urllib.parse.quote(artsrc._clean(best))}.png"
    _save(url, entry["id"], lambda u, d: artsrc.fetch("libretro", u, d))
    return True


def fetch_one(entry, search=sgdb.search, images=sgdb.images, fetch=sgdb.fetch, libretro=True) -> str:
    """'ok' | 'sin resultados'. Primero SteamGridDB; si no hay nada y es de consola, libretro."""
    err = None
    if search is not sgdb.search or sgdb.key():
        try:
            if fetch_sgdb(entry, search, images, fetch):
                return "ok"
        except Exception as ex:  # noqa: BLE001  (Cloudflare, red…): se prueba libretro igualmente
            err = ex
    if libretro:
        try:
            if fetch_libretro(entry):
                return "ok"
        except OSError:
            pass
    if err:
        raise err
    return "sin resultados"


def batch(entries, progress=None, stop=lambda: False, retry_misses=False, workers=WORKERS, pause=None, **kw):
    """Baja lo que falta, varias a la vez. Devuelve {'ok','sin','error','total','omitidos'}. progress(i,total,nombre).
    Los que no tienen carátula en ninguna fuente se apuntan y no se reintentan hasta RETRY_DAYS (salvo retry_misses)."""
    every = missing(entries)
    todo = missing(entries, include_misses=retry_misses)
    r = {"ok": 0, "sin": 0, "error": 0, "total": len(todo), "omitidos": len(every) - len(todo)}
    m = misses()
    lock = threading.Lock()
    done = [0]

    def one(e):
        if stop():
            return None
        try:
            res = "ok" if fetch_one(e, **kw) == "ok" else "sin"
        except Exception:  # noqa: BLE001
            res = "error"
        with lock:
            done[0] += 1
            r[res] += 1
            if res == "sin":
                m[e["id"]] = time.time()
            elif res == "ok":
                m.pop(e["id"], None)
            if progress:
                progress(done[0], len(todo), e["name"])
        return res
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(one, todo))
    _save_misses(m)
    return r
