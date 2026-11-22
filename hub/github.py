"""Releases de GitHub y elección del asset adecuado. Caché en data/cache/gh (15 min) y token opcional (GITHUB_TOKEN)."""
import json
import os
import re
import time
import urllib.error
import urllib.request

from . import auth, config, ghstats

API = os.environ.get("HUB_GITHUB_API", "https://api.github.com")
TTL = 6 * 3600


class GitHubError(Exception):
    pass


def _headers():
    h = {"User-Agent": "recomp-hub", "Accept": "application/vnd.github+json"}
    tok = auth.token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def tok_set():
    return bool(auth.token())


def _cache_file(repo):
    return config.CACHE / "gh" / (repo.replace("/", "__") + ".json")


def from_cache(repo: str, arch="x86_64", filt="") -> tuple:
    """v2.64: (última, resumen, momento_guardado) leyendo SOLO el disco (0 llamadas a GitHub), sea cual sea su edad. None si no hay nada guardado."""
    try:
        c = json.loads(_cache_file(repo).read_text(encoding="utf-8"))
        r = {"releases": c["data"], "stale": False, "error": None}
        return latest(repo, arch, filt=filt, r=r), summary(repo, arch, filt, r=r), float(c.get("t", 0))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def releases(repo: str, force=False, timeout=10) -> dict:
    """{"releases": [...], "stale": bool, "error": str|None}. Con red caída devuelve lo cacheado (stale=True)."""
    cf = _cache_file(repo)
    cached = None
    try:
        cached = json.loads(cf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if cached and not force and time.time() - cached.get("t", 0) < TTL:
        return {"releases": cached["data"], "stale": False, "error": None}
    wait = ghstats.blocked()
    if wait and cached:            # cortacircuitos: con el límite ya alcanzado no se vuelve a llamar hasta que pase (se enseña lo guardado)
        return {"releases": cached["data"], "stale": True, "error": f"límite de GitHub ({ghstats.S['blocked_why']}): reintenta en {wait // 60 + 1} min"}
    if wait:
        return {"releases": [], "stale": False, "error": f"límite de GitHub ({ghstats.S['blocked_why']}): reintenta en {wait // 60 + 1} min"}
    path = f"/repos/{repo}/releases?per_page=40"     # v2.44: había 15; proyectos que publican cada pocas horas dejaban fuera la versión buena
    hd = _headers()
    if cached and cached.get("etag"):
        hd["If-None-Match"] = cached["etag"]      # 304 = sin cambios y NO gasta cuota
    try:
        req = urllib.request.Request(f"{API}{path}", headers=hd)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ghstats.note(path, r.status, r.headers, tok_set())
            data = json.loads(r.read().decode("utf-8"))
            etag = r.headers.get("ETag", "")
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps({"t": time.time(), "data": data, "etag": etag}), encoding="utf-8")
        return {"releases": data, "stale": False, "error": None}
    except urllib.error.HTTPError as e:
        import sys
        h = e.headers or {}
        ghstats.note(path, e.code, h, tok_set())
        if e.code == 304 and cached:
            cached["t"] = time.time()
            try:
                cf.write_text(json.dumps(cached), encoding="utf-8")
            except OSError:
                pass
            return {"releases": cached["data"], "stale": False, "error": None}
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            body = ""
        k = ghstats.block_from(e.code, h, body)
        print(f"[gh] releases {repo} -> HTTP {e.code} tipo={k or '-'} sesion={'si' if tok_set() else 'no'} restante={h.get('X-RateLimit-Remaining')} "
              f"limite={h.get('X-RateLimit-Limit')} recurso={h.get('X-RateLimit-Resource')} reset={h.get('X-RateLimit-Reset')} retry={h.get('Retry-After')}",
              file=sys.stderr, flush=True)
        who = " aunque hay sesión" if tok_set() else ": inicia sesión en Ajustes → GitHub"
        msg = {401: "token no válido o caducado"}.get(e.code) or (
            {"primario": "cuota de GitHub agotada" + who, "secundario": "GitHub pide ir más despacio (límite secundario)", "otro": "GitHub no respondió (403)" + who + ". Reintenta en un minuto"}.get(k)
            if e.code in (403, 429) else None) or {404: "repositorio o releases no encontrados"}.get(e.code, f"GitHub respondió {e.code}")
    except Exception as e:  # noqa: BLE001  (sin red, tiempo agotado…)
        msg = f"sin conexión ({type(e).__name__})"
    if cached:
        return {"releases": cached["data"], "stale": True, "error": msg}
    return {"releases": [], "stale": False, "error": msg}


# ── elección de asset ────────────────────────────────────────────────────
_BAD_EXT = (".sha256", ".sha1", ".md5", ".sig", ".asc", ".txt", ".json", ".yml", ".yaml", ".sbom", ".pdb", ".dmg", ".msi", ".exe", ".apk",
            ".deb", ".rpm", ".pkg", ".ipa", ".nupkg")


def classify(name: str) -> dict:
    n = name.lower()      # v2.51: «pc» a secas cuenta como Windows (SilentHillPC-….zip)
    os_ = "linux" if re.search(r"linux|appimage|ubuntu|debian|steamos|steamdeck|steam-deck|\.x86_64", n) else \
        "windows" if re.search(r"win(32|64|dows)?([-_.]|$)|\.exe|msvc|mingw|pc([-_. 0-9]|$)", n) else \
        "mac" if re.search(r"mac(os)?|darwin|osx|\.dmg", n) else "?"
    arch = "arm64" if re.search(r"arm64|aarch64|armv8", n) else "x86_64" if re.search(r"x86[_-]?64|amd64|x64|64bit|64-bit", n) else "?"
    kind = "appimage" if n.endswith(".appimage") else "zip" if n.endswith(".zip") else \
        "tar" if re.search(r"\.tar(\.\w+)?$|\.tgz$|\.txz$", n) else "7z" if n.endswith(".7z") else "run" if n.endswith(".run") else \
        "rar" if n.endswith(".rar") else "exe" if n.endswith(".exe") else "bin" if "." not in n.rsplit("/", 1)[-1] else "other"
    return {"os": os_, "arch": arch, "kind": kind}


def score(name: str, arch="x86_64") -> int:
    n = name.lower()
    if n.endswith(_BAD_EXT) or "source" in n or n in ("source code (zip)", "source code (tar.gz)"):
        return -1
    c = classify(name)
    s = 0
    s += {"linux": 50, "?": 5}.get(c["os"], -100)
    s += {arch: 20, "?": 5}.get(c["arch"], -100)
    s += {"appimage": 15, "tar": 8, "zip": 6, "7z": 4, "bin": 3, "run": 2}.get(c["kind"], 0)
    return s


def rank_assets(assets: list, arch="x86_64", filt="") -> list:
    """Assets utilizables, mejor primero. Cada uno: {name,size,url,score,class}."""
    out = []
    for a in assets or []:
        sc = score(a.get("name", ""), arch)
        if sc > 0:
            out.append({"name": a["name"], "size": a.get("size", 0), "url": a.get("browser_download_url", ""),
                        "score": sc, "class": classify(a["name"]), "sha256": (a.get("digest") or "").removeprefix("sha256:") or None})
    out.sort(key=lambda x: -x["score"])
    if filt:  # releaseAssetFilter del catálogo: si algún asset lo contiene, solo esos
        hit = [a for a in out if filt.lower() in a["name"].lower()]
        out = hit or out
    return out


def is_installer(name: str, c=None) -> bool:
    """¿Es un instalador de Windows (.exe llamado Setup/Install…)? No cuenta desinstaladores, símbolos, depuración, código ni servidores."""
    c = c or classify(name)
    n = name.lower()
    return n.endswith(".exe") and c["os"] == "windows" and c["arch"] != "arm64" and bool(re.search(r"setup|install", n)) \
        and not re.search(r"uninstall|symbols|pdb|debug|source|src|server|dedicated", n)


def win_assets(assets: list) -> list:
    """Builds de Windows x64 empaquetados (zip/7z/tar/rar) para la versión con Proton; el más probable primero. Los instaladores .exe (Setup/Install) van al final,
    marcados con class.kind = «instalador» (v2.94); un .exe suelto que no es instalador, con class.kind = «ejecutable» (v3.10); .msi nunca.
    Si la release no trae NADA marcado como Linux, los zip/7z/tar cuyo nombre no dice el sistema (p. ej. «GoW_PSP_Launcher-v1.5.0.zip») se ofrecen
    también, con la etiqueta «¿windows?»: en proyectos que solo publican para Windows el nombre casi nunca lo dice."""
    assets = assets or []
    has_linux = any(classify(a.get("name", ""))["os"] == "linux" for a in assets)
    out = []
    for a in assets:
        n = a.get("name", "")
        c = classify(n)
        if is_installer(n, c):        # v2.94: proyectos que solo publican «Setup.exe» (p. ej. ReStreet): se ofrecen, marcados como instalador
            out.append({"name": n, "size": a.get("size", 0), "url": a.get("browser_download_url", ""), "class": dict(c, kind="instalador"),
                        "score": 7, "sha256": (a.get("digest") or "").removeprefix("sha256:") or None})
            continue
        if c["kind"] == "exe":       # v3.10: un .exe suelto que no es instalador (p. ej. «Gow2HD-Windows.exe»): es el propio juego/lanzador portátil
            if c["os"] == "windows" and c["arch"] != "arm64" and not re.search(r"uninstall|symbols|pdb|debug|source|src|server|dedicated|crash|vc_?redist|dxsetup", n, re.I):
                out.append({"name": n, "size": a.get("size", 0), "url": a.get("browser_download_url", ""), "class": dict(c, kind="ejecutable"),
                            "score": 9, "sha256": (a.get("digest") or "").removeprefix("sha256:") or None})
            continue
        guess = c["os"] == "?" and not has_linux
        if (c["os"] != "windows" and not guess) or c["kind"] not in ("zip", "7z", "tar", "rar") or c["arch"] == "arm64" \
                or re.search(r"setup|install|symbols|pdb|debug|source|src|sources", n, re.I):
            continue
        if guess:
            c = dict(c, os="¿windows?")
        out.append({"name": n, "size": a.get("size", 0), "url": a.get("browser_download_url", ""), "class": c,
                    "score": (20 if c["arch"] == "x86_64" else 5) + {"zip": 6, "7z": 4, "tar": 3, "rar": 2}[c["kind"]] - (12 if guess else 0),
                    "sha256": (a.get("digest") or "").removeprefix("sha256:") or None})
    return sorted(out, key=lambda x: -x["score"])


def _view(rel: dict, r: dict, arch: str, filt: str) -> dict:
    return {"tag": rel.get("tag_name", ""), "name": rel.get("name") or rel.get("tag_name", ""),
            "published": (rel.get("published_at") or "")[:10], "notes": rel.get("body") or "",
            "html_url": rel.get("html_url", ""),
            "has_windows": bool(win_assets(rel.get("assets", []))) or any(classify(a.get("name", ""))["os"] == "windows" and not a.get("name", "").lower().endswith(_BAD_EXT[:10])
                                                                         for a in rel.get("assets", [])),
            "assets": rank_assets(rel.get("assets", []), arch, filt),
            "win_assets": win_assets(rel.get("assets", [])),
            "error": r["error"], "stale": r["stale"]}


def latest(repo: str, arch="x86_64", prerelease=False, force=False, filt="", tag="", r=None) -> dict:
    """Mejor release disponible (o la de `tag`): {tag,name,published,notes,assets(ordenados),html_url,error,stale} o con error."""
    r = r or releases(repo, force=force)
    rel = None
    if tag:
        rel = next((x for x in r["releases"] if x.get("tag_name") == tag and not x.get("draft")), None)
    if rel is None:
        rel = next((x for x in r["releases"] if not x.get("draft") and (prerelease or not x.get("prerelease"))), None)
    if rel is None and r["releases"]:
        rel = next((x for x in r["releases"] if not x.get("draft")), None)
    if rel is None:
        return {"error": r["error"] or "sin releases publicadas", "stale": r["stale"], "assets": []}
    return _view(rel, r, arch, filt)


def summary(repo: str, arch="x86_64", filt="", r=None) -> list:
    """Releases recientes: [{tag, published, prerelease, linux, windows}] con cuántos builds de cada sistema trae cada una. Con `r` no hace ninguna petición."""
    r = r or releases(repo)
    out = []
    for x in r["releases"]:
        if x.get("draft"):
            continue
        v = _view(x, r, arch, filt)
        lin = [a for a in v["assets"] if a["class"]["os"] == "linux"] or ([] if v["win_assets"] else v["assets"][:0])
        out.append({"tag": v["tag"], "published": v["published"], "prerelease": bool(x.get("prerelease")),
                    "linux": len(lin), "windows": len(v["win_assets"])})
    return out


def latest_and_summary(repo: str, arch="x86_64", force=False, filt="") -> tuple:
    """(última release, resumen de las recientes) con UNA sola consulta a GitHub."""
    r = releases(repo, force=force)
    return latest(repo, arch, filt=filt, r=r), summary(repo, arch, filt, r=r)
