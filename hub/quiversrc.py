"""Cliente de SOLO LECTURA de la API pública de Quiver (https://api.quiverlauncher.com/api/v1), como un indexador más de Hub.

Qué da: nombre, consolas, repositorio y, sobre todo, los archivos de cada release con su SHA-256 fijado por Quiver.
Qué NO hace: nunca llama a los POST (`…/check`, `…/download-problem`); no necesita cuenta ni token.
Buenas maneras: caché en memoria (la API ya se sirve desde la caché de Cloudflare: 60 s las listas, 30 min fichas y releases),
User-Agent propio, sin ráfagas, IPv4 primero (en algunas redes IPv6 se queda colgado en el TLS) y, si falla el host principal,
el del propio despliegue como reserva. Si todo falla devuelve lo último que tenía en caché (marcado como viejo).
Uso en terminal (desde la carpeta de Hub):  python3 -m hub.quiversrc search "banjo"   |   python3 -m hub.quiversrc assets SLUG   |   python3 -m hub.quiversrc check "banjo"  (prueba real con descarga y SHA-256)
"""
import http.client
import json
import os
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import github

BASE = os.environ.get("HUB_QUIVER_API", "https://api.quiverlauncher.com/api/v1")
FALLBACK = os.environ.get("HUB_QUIVER_FALLBACK", "https://famous-wildebeest-660.convex.site/api/v1")
UA = "recomp-hub (uso personal, solo lectura)"
TTL_LIST, TTL_ITEM = 300, 1800      # s en caché local (≥ lo que ya dice la API)
TIMEOUT = 20

_cache, _lock = {}, threading.Lock()
_last = [0.0]                       # separa las peticiones: nada de ráfagas
_MIN_GAP = 0.25


class QuiverError(Exception):
    pass


class _V4Conn(http.client.HTTPSConnection):
    """HTTPS que prueba primero IPv4 (IPv6 colgado = «handshake timed out»); si no se puede, la conexión normal."""
    def connect(self):
        try:
            ip = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
            sock = socket.create_connection((ip, self.port), self.timeout)
            ctx = ssl.create_default_context()
            self.sock = ctx.wrap_socket(sock, server_hostname=self.host)
        except OSError:
            super().connect()


class _V4Handler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_V4Conn, req)


_opener = urllib.request.build_opener(_V4Handler)


def _fetch(url):
    wait = _MIN_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    last = None
    for i in range(3):                       # SSL «UNEXPECTED_EOF» y cortes puntuales: reintenta con pausa corta
        try:
            with _opener.open(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, OSError, http.client.HTTPException) as ex:
            last = ex
            time.sleep(0.6 * (i + 1))
    raise last


def get(path, ttl=TTL_LIST):
    """GET con caché. Devuelve (datos, viejo). `viejo` = True si salió de la caché por no haber red."""
    now = time.time()
    with _lock:
        hit = _cache.get(path)
    if hit and now - hit[0] < ttl:
        return hit[1], False
    problem = None
    for base in (BASE, FALLBACK):
        if not base:
            continue
        try:
            data = _fetch(base + path)
            with _lock:
                _cache[path] = (time.time(), data)
            return data, False
        except urllib.error.HTTPError as ex:
            if ex.code < 500 and ex.code != 499:      # 404 etc.: la respuesta es esa, el respaldo no la cambia
                raise QuiverError(f"Quiver respondió {ex.code}") from None
            problem = f"HTTP {ex.code}"
        except (urllib.error.URLError, OSError, ValueError) as ex:
            problem = f"{type(ex).__name__}: {getattr(ex, 'reason', ex)}"
    if hit:
        return hit[1], True
    raise QuiverError(f"no pude consultar Quiver ({problem})")


# ── consultas ────────────────────────────────────────────────────────────
def search(text, console=None, limit=8):
    """Apps del catálogo de Quiver que casan con el texto. Lista de {slug, name, project, consoles, version, pinned, os}."""
    text = (text or "").strip()
    if len(text) < 2:
        return []
    q = {"limit": str(max(1, min(int(limit), 24))), "search": text, "os": "linux"}
    if console:
        q["console"] = console
    page, _ = get("/apps?" + urllib.parse.urlencode(q))
    out = []
    for it in (page or {}).get("items") or []:
        if not isinstance(it, dict) or not it.get("slug"):
            continue
        v = it.get("verified") if isinstance(it.get("verified"), dict) else {}
        out.append({"slug": it["slug"], "name": it.get("name") or it["slug"], "project": it.get("projectName") or "",
                    "consoles": [c for c in (it.get("consoles") or []) if isinstance(c, str)],
                    "version": v.get("version", ""), "pinned": bool(v.get("pinned")), "os": it.get("supportedOS") or []})
    return out


def app(slug):
    """Ficha: {repo, provider, folder, consoles, games}. Vacío en lo que no venga."""
    d, _ = get(f"/apps/{urllib.parse.quote(slug)}", TTL_ITEM)
    d = d if isinstance(d, dict) else {}
    pr, en = d.get("project") or {}, d.get("entry") or {}
    return {"repo": pr.get("repository") or "", "provider": pr.get("provider") or "", "folder": (en.get("launcher") or {}).get("folderName", ""),
            "consoles": en.get("consoles") or [], "name": en.get("name") or pr.get("name") or slug}


def _usable(a):
    """Un archivo de la release sirve para este equipo: Linux (o sin decir), x64/universal (o sin decir) y con URL."""
    if not isinstance(a, dict) or not a.get("url") or not a.get("filename"):
        return False
    return a.get("os") in ("linux", "unknown", None) and a.get("architecture") in ("x64", "universal", "unknown", None)


def assets(slug):
    """Última release verificada: (versión, [archivos mejor primero]). Cada archivo: {name,size,url,sha256,class,score}.
    El SHA-256 es el que Quiver fijó al salir la release; el gestor de Hub rechaza lo que no coincida."""
    d, _ = get(f"/apps/{urllib.parse.quote(slug)}/releases?limit=1", TTL_ITEM)
    items = (d or {}).get("items") or []
    rel = items[0] if items and isinstance(items[0], dict) else None
    if not rel:
        return "", []
    raw = [a for a in rel.get("assets") or [] if _usable(a)]
    norm = []
    for a in raw:
        ck = a.get("checksum") or ""
        norm.append({"name": a["filename"], "size": a.get("size") or 0, "browser_download_url": a["url"],
                     "digest": ck if ck.startswith("sha256:") else ""})
    ranked = github.rank_assets(norm)
    flat = [a for a in ranked if "flatpak" not in a["name"].lower()]
    return rel.get("version") or "", (flat or ranked)


def label(r):
    """Texto de una fila de resultados."""
    return " · ".join(x for x in (r["name"], r["project"] if r["project"] and r["project"] != r["name"] else "", "/".join(r["consoles"]),
                                  r["version"] + ("" if r["pinned"] else " (sin SHA-256)") if r["version"] else "sin versión verificada") if x)


def check(term="banjo", max_mb=60):
    """Prueba real de punta a punta (lee, descarga el archivo más pequeño que sirva y compara el SHA-256). Devuelve (ok, líneas)."""
    import hashlib
    log = []

    def say(t):
        log.append(t)
        print(t, flush=True)
    try:
        rs = search(term)
        say(f"1) búsqueda «{term}»: {len(rs)} resultado(s)")
        rs = [r for r in rs if r["pinned"]] or rs
        if not rs:
            return False, log
        r = rs[0]
        say(f"2) elegido: {label(r)}")
        a = app(r["slug"])
        say(f"3) ficha: repo={a['repo'] or '?'} carpeta={a['folder'] or '?'}")
        ver, lst = assets(r["slug"])
        say(f"4) release {ver or '?'}: {len(lst)} archivo(s) para Linux x64")
        small = sorted([x for x in lst if x.get("url") and 0 < (x.get("size") or 0) <= max_mb * 1048576], key=lambda x: x["size"])
        if not small:
            say("   (ningún archivo ≤ %d MB para probar la descarga)" % max_mb)
            return False, log
        x = small[0]
        say(f"5) descargando {x['name']} ({x['size'] // 1024} KB)…")
        h = hashlib.sha256()
        req = urllib.request.Request(x["url"], headers={"User-Agent": UA})
        with _opener.open(req, timeout=60) as resp:
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                h.update(chunk)
        got = h.hexdigest()
        want = x.get("sha256")
        if not want:
            say(f"6) sin SHA-256 fijado por Quiver; el de lo descargado es {got[:16]}…")
            return False, log
        say(f"6) SHA-256 {'COINCIDE' if got == want else 'NO COINCIDE'} ({got[:16]}…)")
        return got == want, log
    except (QuiverError, OSError, urllib.error.URLError) as ex:
        say(f"ERROR: {type(ex).__name__}: {ex}")
        return False, log


def _main(argv):
    try:
        if len(argv) >= 2 and argv[0] == "search":
            out = search(argv[1])
        elif argv and argv[0] == "check":
            ok, _ = check(argv[1] if len(argv) > 1 else "banjo")
            print("RESULTADO:", "OK" if ok else "FALLÓ")
            return 0 if ok else 1
        elif len(argv) >= 2 and argv[0] == "assets":
            out = assets(argv[1])
        else:
            print(__doc__)
            return 2
    except QuiverError as ex:
        print(f"QuiverError: {ex}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
