"""SteamGridDB para elegir el arte a mano (el launcher con --art toma siempre el primer resultado).
La clave es la MISMA del launcher: STEAMGRIDDB_KEY en el entorno, ~/Games/launcher/.env o ~/Games/launcher/state/.sgdb_key. Hub no la guarda en otro sitio."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config, nethttp

API = os.environ.get("HUB_SGDB_API", "https://www.steamgriddb.com/api/v2")
UA = "recomp-hub/1"
# tipo → (endpoint, filtros). Medidas estándar de Steam.
KINDS = {
    "portrait": ("grids", {"dimensions": "600x900,342x482"}, "Portada vertical"),
    "banner": ("grids", {"dimensions": "920x430,460x215"}, "Banner"),
    "hero": ("heroes", {}, "Fondo (hero)"),
    "icon": ("icons", {}, "Icono"),
    "logo": ("logos", {}, "Logo"),
}


def key():
    k = os.environ.get("STEAMGRIDDB_KEY") or os.environ.get("STEAMGRIDDB_API_KEY")
    if k:
        return k.strip()
    for f in (config.LAUNCHER / ".env", config.LAUNCHER / "state" / ".sgdb_key"):
        try:
            for ln in f.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if f.name == ".sgdb_key" and ln:
                    return ln
                if ln.startswith(("STEAMGRIDDB_KEY", "export STEAMGRIDDB_KEY", "STEAMGRIDDB_API_KEY")) and "=" in ln:
                    return ln.split("=", 1)[1].strip().strip("\"'")
        except OSError:
            continue
    return ""


def _get(path, params=None, raw=False, timeout=20):
    url = path if path.startswith("http") else API + path
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    hdr = {}
    if url.startswith(API):   # la clave solo va a la API, nunca a los CDN de imágenes
        hdr["Authorization"] = f"Bearer {key()}"
    try:
        data = nethttp.get(url, hdr, timeout=timeout if not raw else max(timeout, 30))      # v2.77: normal → IPv4 → normal, con la causa en el error
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            return b"" if raw else {"data": []}
        body = ""
        try:
            body = ex.read(600).decode("utf-8", "replace").lower()
        except Exception:  # noqa: BLE001
            pass
        if ex.code == 403 and ("cloudflare" in body or "just a moment" in body or "attention required" in body):
            raise OSError("SteamGridDB (Cloudflare) bloquea esta conexión: la IP de tu VPN está marcada. Cambia de servidor VPN o de país") from ex
        raise OSError(f"SteamGridDB rechazó la clave (HTTP {ex.code})") from ex
    return data if raw else json.loads(data.decode("utf-8"))


def search(term):
    """[{id, name}] candidatos para el nombre."""
    d = _get("/search/autocomplete/" + urllib.parse.quote(term, safe=""))
    return [{"id": g["id"], "name": g.get("name", "?")} for g in (d.get("data") or [])][:12]


def images(kind, game_id, limit=12):
    ep, flt, _ = KINDS[kind]
    d = _get(f"/{ep}/game/{game_id}", dict(flt, types="static", nsfw="false", humor="any"))
    out = []
    for i in (d.get("data") or [])[:limit]:
        out.append({"id": i["id"], "url": i["url"], "thumb": i.get("thumb") or i["url"], "w": i.get("width"), "h": i.get("height"), "style": i.get("style", "")})
    return out


def fetch(url, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = _get(url, raw=True, timeout=60)
    dest.write_bytes(data)
    return dest


def save_key(k: str):
    """Guarda la clave en el .env DEL LAUNCHER (una sola copia para los dos proyectos)."""
    f = config.LAUNCHER / ".env"
    old = key()
    if old and old != k.strip():                    # v2.77: la clave anterior se guarda por si el cambio fue un error
        try:
            b = config.LAUNCHER / "state" / ".sgdb_key.prev"
            b.parent.mkdir(parents=True, exist_ok=True)
            b.write_text(old + "\n", encoding="utf-8")
            b.chmod(0o600)
        except OSError:
            pass
    lines = []
    try:
        lines = [ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.strip().startswith(("STEAMGRIDDB_KEY", "export STEAMGRIDDB_KEY"))]
    except OSError:
        pass
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(lines + [f"STEAMGRIDDB_KEY={k.strip()}"]) + "\n", encoding="utf-8")
    try:
        f.chmod(0o600)
    except OSError:
        pass


def env_get(name):
    """Valor de NAME en el entorno o en ~/Games/launcher/.env (el mismo archivo que usa el launcher)."""
    v = os.environ.get(name)
    if v:
        return v.strip()
    try:
        for ln in (config.LAUNCHER / ".env").read_text(encoding="utf-8").splitlines():
            ln = ln.strip().removeprefix("export ").strip()
            if ln.startswith(name + "=") :
                return ln.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def env_set(name, value):
    f = config.LAUNCHER / ".env"
    lines = []
    try:
        lines = [ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.strip().removeprefix("export ").strip().startswith(name + "=")]
    except OSError:
        pass
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(lines + [f"{name}={value.strip()}"]) + "\n", encoding="utf-8")
    try:
        f.chmod(0o600)
    except OSError:
        pass
