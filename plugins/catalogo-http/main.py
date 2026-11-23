#!/usr/bin/env python3
"""Complemento «Catálogo HTTP v1» para Forgeinator (protocolo de conectores v1 por stdio; ver docs/PLUGINS.md).

Sirve también de ejemplo para escribir el tuyo: solo biblioteca estándar, un mensaje JSON por línea.
  entrada  (Forgeinator → complemento): {"v":1,"id":N,"method":"…","params":{…}}
  salida   (complemento → Forgeinator): {"v":1,"id":N,"ok":true,"result":…}  ·  {"v":1,"id":N,"ok":false,"error":"…","detail":"…"}
           y, durante «download», {"v":1,"id":N,"progress":{"done":…,"total":…,"eta":…,"speed":…}}
Lo que se escribe por stderr acaba en el registro de Forgeinator."""
import hashlib
import json
import queue
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROTOCOL = 1
VERSION = "1.0.0"
OUT = threading.Lock()
cancel = threading.Event()
inbox = queue.Queue()


class Fail(Exception):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code, self.detail = code, detail


def send(obj):
    with OUT:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def reader():
    """Lee stdin en un hilo: así un «cancel» llega aunque estemos a mitad de una descarga."""
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("method") == "cancel":
            cancel.set()
        else:
            inbox.put(msg)
    inbox.put(None)


# ---------------------------------------------------------------- HTTP
def _req(cfg, path, raw=False, headers=None):
    base = (cfg.get("url") or "").rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise Fail("config", "La dirección debe empezar por http:// o https://")
    url = path if path.startswith(("http://", "https://")) else base + "/" + path.lstrip("/")
    h = {"Accept": "application/json", "User-Agent": f"forgeinator-catalogo-http/{VERSION}"}
    if cfg.get("token"):
        h["Authorization"] = "Bearer " + cfg["token"]
    h.update(headers or {})
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30)
    except urllib.error.HTTPError as ex:
        try:
            j = json.loads(ex.read().decode())
            detail = j.get("detail") or j.get("error")
        except ValueError:
            detail = ""
        if ex.code in (401, 403):
            raise Fail("auth", "El servidor rechazó el token") from ex
        if ex.code == 404:
            raise Fail("no_existe", detail or f"No existe: {path}") from ex
        raise Fail("servidor", f"El servidor respondió {ex.code}" + (f": {detail}" if detail else "")) from ex
    except (urllib.error.URLError, OSError) as ex:
        raise Fail("red", f"No conecta con {base}: {getattr(ex, 'reason', ex)}") from ex
    if raw:
        return r
    with r:
        try:
            return json.loads(r.read().decode("utf-8"))
        except ValueError as ex:
            raise Fail("servidor", "El servidor no devolvió JSON") from ex


def catalog(cfg):
    items, cur, seen = [], None, 0
    while True:
        j = _req(cfg, "catalog" + (f"?since={urllib.parse.quote(str(cur))}" if cur else ""))
        items += [x for x in j.get("items") or [] if isinstance(x, dict) and x.get("id") and x.get("system")]
        cur = j.get("next")
        seen += 1
        if not cur or seen > 500:
            return items


# ---------------------------------------------------------------- métodos
def m_hello(p):
    return {"protocol": PROTOCOL, "name": "Catálogo HTTP v1", "version": VERSION, "capabilities": ["test", "systems", "games", "download", "cancel"]}


def m_test(p):
    info = _req(p["config"], "info")
    if int(info.get("protocol", 0)) != 1:
        raise Fail("protocolo", f"El servidor habla el protocolo {info.get('protocol')}, se esperaba el 1")
    n = len({x["system"] for x in catalog(p["config"])})
    return f"«{info.get('name', 'servidor')}» {info.get('version', '')} · {n} sistemas"


def m_systems(p):
    return [{"dir": s, "system": s, "name": s} for s in sorted({str(x["system"]) for x in catalog(p["config"])})]


def m_games(p):
    out = []
    for x in catalog(p["config"]):
        if str(x["system"]) != p.get("dir"):
            continue
        name = x.get("file") or x.get("title") or x["id"]
        out.append({"path": str(x["id"]), "name": Path(str(name)).name, "dir": int(x.get("files") or 1) > 1, "size": x.get("size")})
    return out


def m_download(p, mid):
    cfg, game, dest = p["config"], p["game"], Path(p["dest"])
    files = _req(cfg, f"items/{urllib.parse.quote(str(game['path']), safe='')}/files")
    if not isinstance(files, list) or not files:
        raise Fail("servidor", "El servidor no dio archivos para ese juego")
    total = sum(int(f.get("size") or 0) for f in files)
    many = p.get("is_dir") or len(files) > 1
    if many:
        dest.mkdir(parents=True, exist_ok=True)
    done, t0, last = 0, time.time(), 0.0
    for f in files:
        name = Path(str(f.get("name") or "archivo")).name
        out = dest / name if many else dest
        h = hashlib.sha256()
        with _req(cfg, str(f["url"]), raw=True, headers={"Accept": "*/*"}) as r, open(out, "wb") as fh:
            while True:
                if cancel.is_set():
                    raise Fail("cancelado", "Descarga cancelada")
                b = r.read(1 << 16)
                if not b:
                    break
                fh.write(b)
                h.update(b)
                done += len(b)
                now = time.time()
                if now - last >= 0.5:
                    last = now
                    sp = done / max(now - t0, 1e-3)
                    send({"v": PROTOCOL, "id": mid, "progress": {"done": done, "total": total, "speed": sp,
                                                                  "eta": int((total - done) / sp) if total and sp else None}})
        if f.get("sha256") and h.hexdigest() != str(f["sha256"]).lower():
            raise Fail("integridad", f"{name}: la suma sha256 no coincide (archivo dañado)")
    send({"v": PROTOCOL, "id": mid, "progress": {"done": done, "total": total or done, "speed": 0, "eta": 0}})
    return {"files": len(files), "bytes": done}


def main():
    threading.Thread(target=reader, daemon=True).start()
    while True:
        msg = inbox.get()
        if msg is None:
            return
        mid, method, p = msg.get("id"), msg.get("method"), msg.get("params") or {}
        cancel.clear()
        try:
            if method == "download":
                res = m_download(p, mid)
            elif method in ("hello", "test", "systems", "games"):
                res = globals()["m_" + method](p)
            else:
                raise Fail("metodo", f"Método desconocido: {method}")
            send({"v": PROTOCOL, "id": mid, "ok": True, "result": res})
        except Fail as ex:
            send({"v": PROTOCOL, "id": mid, "ok": False, "error": ex.code, "detail": ex.detail})
        except Exception as ex:  # noqa: BLE001
            print(f"error inesperado: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            send({"v": PROTOCOL, "id": mid, "ok": False, "error": "interno", "detail": f"{type(ex).__name__}: {ex}"})


if __name__ == "__main__":
    main()
