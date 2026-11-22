"""Gestor de descargas propio (estilo Motrix): cola, varias conexiones por descarga, pausa/reanudar,
reintentos, verificación SHA-256 y persistencia entre reinicios. Solo librería estándar."""
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

UA = {"User-Agent": "recomp-hub"}
CHUNK = 256 * 1024
STATES = ("queued", "active", "paused", "done", "error", "cancelled")


def _name_from(url, headers):
    cd = headers.get("Content-Disposition", "") if headers else ""
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
    n = urllib.parse.unquote(m.group(1)) if m else urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name)
    return re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", n).strip(". ") or "descarga.bin"


def sha256_file(p, cb=None):
    h = hashlib.sha256()
    total = os.path.getsize(p)
    done = 0
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
            done += len(b)
            if cb:
                cb(done, total)
    return h.hexdigest()


class Download:
    def __init__(self, id, url, dest_dir, name="", sha256=None, meta=None, connections=4):
        self.id, self.url, self.dir = id, url, str(dest_dir)
        self.name, self.sha256, self.meta = name, (sha256 or "").lower() or None, meta or {}
        self.connections = connections
        self.size = 0
        self.done = 0
        self._busy = False
        self.state = "queued"
        self.error = ""
        self.speed = 0.0
        self.verified = None  # None=sin hash, True/False
        self.segments = []   # [start, end_inclusive, pos]
        self.accept_ranges = False
        self.added = time.time()
        self._stop = threading.Event()
        self._lock = threading.Lock()

    @property
    def path(self):
        return Path(self.dir) / (self.name or "descarga.bin")

    @property
    def part(self):
        return Path(str(self.path) + ".part")

    @property
    def progress(self):
        return min(1.0, self.done / self.size) if self.size else 0.0

    def eta(self):
        return (self.size - self.done) / self.speed if self.speed > 1 and self.size else None

    def to_json(self):
        return {"id": self.id, "url": self.url, "dir": self.dir, "name": self.name, "sha256": self.sha256, "meta": self.meta,
                "size": self.size, "done": self.done, "state": self.state, "error": self.error, "verified": self.verified,
                "segments": self.segments, "ranges": self.accept_ranges, "added": self.added, "connections": self.connections}

    @classmethod
    def from_json(cls, j):
        d = cls(j["id"], j["url"], j["dir"], j.get("name", ""), j.get("sha256"), j.get("meta"), j.get("connections", 4))
        d.size, d.done, d.error, d.verified = j.get("size", 0), j.get("done", 0), j.get("error", ""), j.get("verified")
        d.segments, d.accept_ranges, d.added = j.get("segments", []), j.get("ranges", False), j.get("added", time.time())
        st = j.get("state", "paused")
        d.state = st if st in ("done", "error", "cancelled", "paused") else "paused"  # lo activo/en cola tras reiniciar queda pausado
        return d


class Manager:
    def __init__(self, state_file=None, max_active=2, connections=4, opener=None):
        self.state_file = Path(state_file or config.DATA / "downloads.json")
        self.max_active, self.connections = max_active, connections
        self.items = {}
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._quit = False
        self._seq = 0
        self.on_done = None      # callback(download) al terminar bien
        self._load()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()

    # ── persistencia ──
    def _load(self):
        try:
            for j in json.loads(self.state_file.read_text(encoding="utf-8")):
                d = Download.from_json(j)
                self.items[d.id] = d
                self._seq = max(self._seq, int(re.sub(r"\D", "", d.id) or 0))
        except (OSError, ValueError, KeyError):
            pass

    def save(self):
        with self._lock:
            data = [d.to_json() for d in self.items.values()]
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            tmp.replace(self.state_file)
        except OSError:
            pass

    # ── API ──
    def add(self, url, dest_dir, name="", sha256=None, meta=None, start=True):
        import sys
        print(f"[dl] añadida: {url} -> {dest_dir}", file=sys.stderr, flush=True)
        with self._lock:
            self._seq += 1
            d = Download(f"d{self._seq}", url, dest_dir, name, sha256, meta, self.connections)
            d.state = "queued" if start else "paused"
            self.items[d.id] = d
        self.save()
        self._wake.set()
        return d

    def pause(self, id):
        d = self.items.get(id)
        if d and d.state in ("queued", "active"):
            d._stop.set()
            if d.state == "queued":
                d.state = "paused"
            self.save()

    def resume(self, id):
        d = self.items.get(id)
        if d and d._busy and d.state in ("paused", "cancelled"):
            d.meta["_resume"] = True          # v2.68: el hilo anterior sigue vivo; reencola cuando termine (evita dos hilos sumando bytes)
            d.error = ""
            return
        if d and d.state in ("paused", "error", "cancelled"):
            d._stop.clear()
            d.error = ""
            d.state = "queued"
            self.save()
            self._wake.set()

    def cancel(self, id, delete_files=True):
        """Cancela y (por defecto) borra SOLO el .part de la propia descarga."""
        d = self.items.get(id)
        if not d:
            return
        d._stop.set()
        if d.state != "active":
            d.state = "cancelled"
            if delete_files:
                self._rm_part(d)
        else:
            # activa: pasa a «cancelada» YA (antes seguía como activa hasta que el servidor soltaba la conexión: con una
            # conexión parada eran hasta 20 s en los que CANCELAR parecía no hacer nada); el hilo borra el .part al terminar
            d.meta["_cancel"] = True
            d.state = "cancelled"
        self.save()

    def remove(self, id):
        """Quita de la lista (no borra el archivo final)."""
        d = self.items.get(id)
        if d and d.state != "active":
            self.items.pop(id, None)
            self.save()

    def clear_finished(self):
        with self._lock:
            for k in [k for k, d in self.items.items() if d.state in ("done", "cancelled")]:
                self.items.pop(k)
        self.save()

    def list(self):
        with self._lock:
            return sorted(self.items.values(), key=lambda d: d.added)

    def shutdown(self):
        self._quit = True
        for d in list(self.items.values()):
            d._stop.set()
        self._wake.set()
        self._thr.join(3)
        self.save()

    @staticmethod
    def _rm_part(d):
        try:
            d.part.unlink()
        except OSError:
            pass
        d.done = 0
        d.segments = []

    # ── bucle ──
    def _loop(self):
        while not self._quit:
            with self._lock:
                active = [d for d in self.items.values() if d.state == "active"]
                queued = sorted((d for d in self.items.values() if d.state == "queued" and not d._busy), key=lambda d: d.added)
            for d in queued[:max(0, self.max_active - len(active))]:
                d.state = "active"
                d._busy = True
                threading.Thread(target=self._run, args=(d,), daemon=True).start()
            self._wake.wait(0.4)
            self._wake.clear()

    @staticmethod
    def _log_err(d):
        import sys
        print(f"[dl] ERROR {d.url} -> {d.error}", file=sys.stderr, flush=True)

    @staticmethod
    def _transient(e):
        """Cortes de red que suelen arreglarse reintentando (SSL EOF, reinicio de conexión, tiempo agotado)."""
        import ssl
        inner = getattr(e, "reason", e)
        return isinstance(e, (ssl.SSLError, ConnectionError, TimeoutError, urllib.error.URLError)) or isinstance(inner, (ssl.SSLError, ConnectionError, TimeoutError))

    def _open(self, d, headers=None, timeout=20):
        h = dict(UA)
        h.update(headers or {})
        return urllib.request.urlopen(urllib.request.Request(d.url, headers=h), timeout=timeout)

    def _probe(self, d):
        """Tamaño, nombre y soporte de Range (petición Range 0-0)."""
        with self._open(d, {"Range": "bytes=0-0"}) as r:
            cr = r.headers.get("Content-Range", "")
            if r.status == 206 and "/" in cr and cr.rsplit("/", 1)[1].isdigit():
                d.size, d.accept_ranges = int(cr.rsplit("/", 1)[1]), True
            else:
                d.size = int(r.headers.get("Content-Length") or 0)
                d.accept_ranges = False
            if not d.name:
                d.name = _name_from(r.geturl(), r.headers)
            d.url = r.geturl()

    def _run(self, d):
        try:
            self._run_inner(d)
        finally:
            d._busy = False
            if d.meta.pop("_resume", False) and d.state in ("paused", "cancelled"):
                d._stop.clear()
                d.state = "queued"
                self._wake.set()

    def _run_inner(self, d):
        try:
            Path(d.dir).mkdir(parents=True, exist_ok=True)
            if not d.size or not d.name:
                self._probe(d)
            valid = d.segments and d.part.exists() and d.accept_ranges and d.size and \
                sum(s[2] - s[0] for s in d.segments) == d.done
            if not valid:
                d.done = 0
                n = max(1, min(d.connections, 8)) if (d.accept_ranges and d.size > 4 * CHUNK) else 1
                if d.size:
                    step = -(-d.size // n)
                    d.segments = [[i * step, min(d.size, (i + 1) * step) - 1, i * step] for i in range(n)]
                else:
                    d.segments = [[0, -1, 0]]
                with open(d.part, "wb") as f:
                    if d.size:
                        f.truncate(d.size)
            self._transfer(d)
            if d._stop.is_set():
                d.state = "cancelled" if d.meta.pop("_cancel", False) else "paused"
                if d.state == "cancelled":
                    self._rm_part(d)
                return
            d.part.replace(d.path)
            import sys
            print(f"[dl] terminada: {d.path} ({d.size} bytes)", file=sys.stderr, flush=True)
            d.state, d.done = "done", d.size or d.done
            if d.sha256:
                d.verified = sha256_file(d.path) == d.sha256
                if not d.verified:
                    d.state, d.error = "error", "SHA-256 no coincide: archivo corrupto o distinto al esperado"
            if d.state == "done" and self.on_done:
                try:
                    self.on_done(d)
                except Exception:  # noqa: BLE001
                    pass
        except urllib.error.HTTPError as e:
            if d.meta.pop("_cancel", False):
                d.state = "cancelled"
                self._rm_part(d)
            else:
                d.state, d.error = "error", f"El servidor respondió {e.code}"
                self._log_err(d)
        except Exception as e:  # noqa: BLE001
            if d.meta.pop("_cancel", False):
                d.state = "cancelled"
                self._rm_part(d)
            elif self._transient(e) and d.meta.get("_retry", 0) < 3:
                n = d.meta["_retry"] = d.meta.get("_retry", 0) + 1
                import sys
                print(f"[dl] corte de red ({type(e).__name__}); reintento {n}/3 en {2 * n}s: {d.url}", file=sys.stderr, flush=True)
                time.sleep(2 * n)
                d.state = "queued"
            else:
                d.state, d.error = "error", f"{type(e).__name__}: {e}"
                self._log_err(d)
        finally:
            d.speed = 0
            self.save()
            self._wake.set()

    def _transfer(self, d):
        errors = []
        stop = d._stop
        marks = [(time.time(), d.done)]

        def worker(seg):
            tries = 0
            while not stop.is_set() and (seg[1] < 0 or seg[2] <= seg[1]):
                try:
                    hdr = {"Range": f"bytes={seg[2]}-{seg[1]}"} if d.accept_ranges else {}
                    with self._open(d, hdr, 8) as r:
                        if d.accept_ranges and r.status != 206:
                            raise OSError("el servidor ignoró Range")
                        fd = os.open(d.part, os.O_WRONLY | os.O_CREAT)
                        try:
                            while not stop.is_set():
                                b = r.read(CHUNK)
                                if not b:
                                    break
                                if seg[1] >= 0:
                                    b = b[:seg[1] - seg[2] + 1]
                                os.pwrite(fd, b, seg[2])
                                with d._lock:
                                    seg[2] += len(b)
                                    d.done += len(b)
                                if seg[1] >= 0 and seg[2] > seg[1]:
                                    break
                        finally:
                            os.close(fd)
                    if seg[1] < 0:
                        seg[1] = seg[2] - 1  # sin tamaño conocido: terminó el flujo
                        return
                    if seg[2] <= seg[1] and not stop.is_set():
                        raise OSError("conexión cerrada antes de tiempo")
                except Exception as e:  # noqa: BLE001
                    tries += 1
                    if tries > 5 or isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404):
                        errors.append(e)
                        stop.set()
                        return
                    time.sleep(min(0.5 * tries, 3))

        ths = [threading.Thread(target=worker, args=(s,), daemon=True) for s in d.segments]
        for t in ths:
            t.start()
        last_save = time.time()
        while any(t.is_alive() for t in ths):
            time.sleep(0.25)
            now = time.time()
            marks.append((now, d.done))
            marks[:] = [m for m in marks if now - m[0] <= 3]
            if len(marks) > 1:
                d.speed = (marks[-1][1] - marks[0][1]) / max(1e-3, marks[-1][0] - marks[0][0])
            if now - last_save > 2:
                self.save()
                last_save = now
        if not d.size:
            d.size = d.done
        if errors:
            raise errors[0]
