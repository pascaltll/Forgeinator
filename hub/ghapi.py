"""API de GitHub para buscar/inspeccionar repos y para iniciar sesión (device flow). Usa el token guardado si lo hay."""
import base64
import sys
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from . import auth, config, ghstats


class GitHubError(Exception):
    pass


def _api():
    return os.environ.get("HUB_GITHUB_API", "https://api.github.com")


def _web():
    return os.environ.get("HUB_GITHUB_WEB", "https://github.com")


def _headers(extra=None):
    h = {"User-Agent": "recomp-hub", "Accept": "application/vnd.github+json"}
    t = auth.token()
    if t:
        h["Authorization"] = f"Bearer {t}"
    h.update(extra or {})
    return h


def _err(e, path=""):
    if isinstance(e, urllib.error.HTTPError):
        h = e.headers or {}
        rem, reset, retry = h.get("X-RateLimit-Remaining"), h.get("X-RateLimit-Reset"), h.get("Retry-After")
        try:
            body = json.loads(e.read().decode("utf-8", "replace")).get("message", "")
        except Exception:  # noqa: BLE001
            body = ""
        wait = ""
        try:
            if retry:
                wait = f" Reintenta en {int(retry)} s."
            elif reset:
                wait = f" Se restablece en {max(1, int((int(reset) - time.time()) / 60))} min."
        except ValueError:
            pass
        sesion = bool(auth.token())
        print(f"[gh] {path} -> HTTP {e.code} sesion={'si' if sesion else 'no'} restante={rem} reset={reset} retry={retry} msg={body[:160]!r}", file=sys.stderr, flush=True)
        if e.code == 401:
            return "token no válido o caducado (AJUSTES → GITHUB: cerrar sesión y volver a iniciar)"
        if e.code in (403, 429):
            if "secondary" in body.lower() or retry:
                return "GitHub pide ir más despacio (límite secundario)." + wait
            if rem == "0" or "rate limit" in body.lower():
                return ("límite de GitHub alcanzado" + (" aunque hay sesión (límite de búsquedas: 30/min)" if sesion else " (sin sesión: 10 búsquedas/min, 60 consultas/h)") + "." + wait)
            return f"GitHub rechazó la petición (403, probable límite{' aunque hay sesión' if sesion else ' sin sesión'}): {body[:100] or 'sin detalle'}"
        return {404: "no encontrado", 422: "búsqueda no válida"}.get(e.code, f"GitHub respondió {e.code}")
    return f"sin conexión ({type(e).__name__})"


def get(path, params=None, timeout=12):
    url = _api() + path + ("?" + urllib.parse.urlencode(params) if params else "")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=_headers()), timeout=timeout) as r:
            ghstats.note(path, r.status, r.headers, bool(auth.token()))
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        ghstats.note(path, e.code, e.headers, bool(auth.token()))
        ghstats.block_from(e.code, e.headers, "")
        raise GitHubError(_err(e, path)) from None
    except Exception as e:  # noqa: BLE001
        raise GitHubError(_err(e, path)) from None


def search(query: str, per_page=20) -> list:
    d = get("/search/repositories", {"q": query, "per_page": per_page})
    return [{"full_name": x["full_name"], "description": x.get("description") or "", "stars": x.get("stargazers_count", 0),
             "language": x.get("language") or "", "updated": (x.get("pushed_at") or "")[:10], "archived": bool(x.get("archived")),
             "fork": bool(x.get("fork"))} for x in d.get("items", [])]


def repo_info(repo: str) -> dict:
    x = get(f"/repos/{repo}")
    lic = (x.get("license") or {}).get("spdx_id") or ""
    return {"full_name": x["full_name"], "name": x["name"], "description": x.get("description") or "", "stars": x.get("stargazers_count", 0),
            "forks": x.get("forks_count", 0), "license": "" if lic == "NOASSERTION" else lic, "topics": x.get("topics") or [],
            "updated": (x.get("pushed_at") or "")[:10], "archived": bool(x.get("archived")), "fork": bool(x.get("fork")),
            "language": x.get("language") or "", "homepage": x.get("homepage") or "", "html_url": x.get("html_url", "")}


def clean_markdown(md: str, limit=2400) -> str:
    t = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)                       # html
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)          # imágenes / badges
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)      # enlaces → texto
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"[`*_]{1,3}", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t[:limit] + ("…" if len(t) > limit else "")


def readme(repo: str) -> str:
    try:
        d = get(f"/repos/{repo}/readme")
        return clean_markdown(base64.b64decode(d.get("content", "")).decode("utf-8", "replace"))
    except GitHubError:
        return ""


def readme_raw(repo: str) -> str:
    """README sin limpiar (para extraer serials/hashes sin perder guiones bajos ni asteriscos)."""
    try:
        d = get(f"/repos/{repo}/readme")
        return base64.b64decode(d.get("content", "")).decode("utf-8", "replace")
    except GitHubError:
        return ""


def rate_limit() -> str:
    """Resumen legible del estado de tu cuota (comprueba que el token se está usando)."""
    d = get("/rate_limit")
    r = d.get("resources", {})
    f = lambda k: f"{r.get(k, {}).get('remaining', '?')}/{r.get(k, {}).get('limit', '?')}"  # noqa: E731
    reset = r.get("core", {}).get("reset")
    mins = f", se restablece en {max(0, int((reset - time.time()) / 60))} min" if reset else ""
    return f"{'CON sesión' if auth.token() else 'SIN sesión'} · general {f('core')} · búsquedas {f('search')}{mins} · {ghstats.summary()}"


def user() -> str:
    return get("/user").get("login", "")


# ── inicio de sesión sin teclado (device flow): hace falta el Client ID de una OAuth App tuya con "Device Flow" activado ──
def _post(url, data, timeout=15):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers={"User-Agent": "recomp-hub", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise GitHubError(_err(e)) from None


def device_start(client_id: str) -> dict:
    d = _post(_web() + "/login/device/code", {"client_id": client_id, "scope": ""})
    if "device_code" not in d:
        raise GitHubError(d.get("error_description") or d.get("error") or "respuesta inesperada (¿Device Flow activado en tu OAuth App?)")
    return d


def device_poll(client_id: str, dev: dict, stop=lambda: False) -> str:
    """Espera a que autorices en github.com/login/device. Devuelve el token o lanza GitHubError."""
    interval = int(dev.get("interval", 5))
    end = time.time() + int(dev.get("expires_in", 900))
    while time.time() < end and not stop():
        time.sleep(interval)
        d = _post(_web() + "/login/oauth/access_token", {"client_id": client_id, "device_code": dev["device_code"],
                                                          "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        if d.get("access_token"):
            return d["access_token"]
        e = d.get("error", "")
        if e == "slow_down":
            interval += 5
        elif e in ("expired_token", "access_denied"):
            raise GitHubError("código caducado" if e == "expired_token" else "acceso denegado")
    raise GitHubError("cancelado" if stop() else "se agotó el tiempo")
