"""Trabajos de descarga que gestiona el daemon de catálogo, con la misma forma que downloads.Download para reutilizar la fila de DESCARGAS.
El daemon hace la transferencia; aquí solo se consulta job_status cada 500 ms."""
import json
import os
import re
import threading
import time
import uuid

from . import catalogservice as cs

_STATE = {"queued": "queued", "running": "active", "completed": "done", "failed": "error",
          "waiting_interaction": "waiting", "waiting": "waiting"}   # waiting = el motor se detuvo y necesita que el usuario haga algo (captcha, pulsar, abrir una página…)
PHASES = {"resolving_cdn": "Resolviendo servidor…", "downloading": "Descargando"}


def parse_size(s) -> int:
    """'3.2 GB' → bytes (0 si no se entiende)."""
    m = re.match(r"\s*([\d.,]+)\s*([KMGT]?)i?B?\s*$", str(s or ""), re.I)
    if not m:
        return 0
    try:
        n = float(m.group(1).replace(",", "."))
    except ValueError:
        return 0
    return int(n * 1024 ** max(0, "_KMGT".find(m.group(2).upper() or "_")))


class CatalogJob:
    catalog = True   # la UI distingue estos de los Download normales

    def __init__(self, job_id, title, size=0, resumable=True, entry_id="", source=""):
        self.id = "cat:" + job_id
        self.job_id = job_id
        self.name = title
        self.url = ""
        self.meta = {"title": title, "resumable": bool(resumable), "source": source, "phase": "", "install": ""}
        self.entry_id = entry_id
        self.size, self.done, self.speed = int(size or 0), 0, 0.0
        self.state, self.error, self.verified = "queued", "", None
        self.path, self.sha1, self.crc32 = "", None, None
        self.added = time.time()
        self.fails = 0
        self.notified = False
        self.alerted = False
        self._last, self._ema = None, 0.0

    def to_dict(self):
        return {"job_id": self.job_id, "title": self.name, "size": self.size, "resumable": self.meta.get("resumable", True),
                "entry_id": self.entry_id, "source": self.meta.get("source", ""), "added": self.added, "state": self.state, "error": self.error,
                "path": self.path, "sha1": self.sha1, "crc32": self.crc32, "notified": self.notified}

    @classmethod
    def from_dict(cls, d):
        j = cls(str(d["job_id"]), str(d.get("title") or "archivo"), d.get("size") or 0, d.get("resumable", True), d.get("entry_id", ""), d.get("source", ""))
        j.added, j.error, j.path = float(d.get("added") or time.time()), str(d.get("error") or ""), str(d.get("path") or "")
        j.sha1, j.crc32, j.notified = d.get("sha1"), d.get("crc32"), bool(d.get("notified"))
        st = d.get("state", "queued")
        j.state = "queued" if (st in ("queued", "active", "waiting") or (st == "done" and not j.notified)) else st      # los vivos se vuelven a consultar: el servicio sigue descargando sin Hub
        if j.state == "done":
            j.done, j._p, j.meta["phase"] = j.size, 1.0, "Completa"
        return j

    @property
    def progress(self):
        return self.done / self.size if self.size else getattr(self, "_p", 0.0)

    def eta(self):
        return (self.size - self.done) / self.speed if self.speed > 1 and self.size else None

    def apply(self, st: dict):
        """Aplica un job_status. Tolera campos que falten (sha1/crc32 aún no existen en el daemon)."""
        self.state = _STATE.get(st.get("state"), self.state)
        p = st.get("progress")
        if isinstance(p, (int, float)):
            self._p = max(0.0, min(1.0, float(p)))
            if self.size:
                self.done = int(self.size * self._p)
        tot = None
        for k in ("size", "total_bytes", "bytes_total", "total"):
            v = st.get(k)
            v = parse_size(v) if isinstance(v, str) else v       # algunos servicios mandan «3.2 GB»
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                tot = v
                break
        if tot:
            self.size = int(tot)
        hecho = next((st.get(k) for k in ("downloaded", "bytes_done", "done_bytes", "bytes") if isinstance(st.get(k), (int, float))), None)
        if hecho is not None:
            self.done = int(hecho)
        elif self.size and isinstance(p, (int, float)):
            self.done = int(self.size * self._p)
        bps = float(st.get("bytes_per_s") or 0)
        now = time.time()
        if bps <= 0 and self.done and self._last and now > self._last[0]:
            # el servicio no da la velocidad (o la calcula mal y siempre da 0): se calcula aquí con lo descargado entre consultas
            inst = max(0.0, (self.done - self._last[1]) / (now - self._last[0]))
            bps = inst if not self._ema else 0.7 * self._ema + 0.3 * inst
            self._ema = bps
        self._last = (now, self.done)
        self.speed = bps
        ph = st.get("phase")
        self.meta["phase"] = PHASES.get(ph, ph or "")
        self.meta["message"] = str(st.get("message") or "")
        if self.state == "waiting":
            self.speed = 0.0
            self.meta["phase"] = "Esperando tu intervención"
        if st.get("state") == "completed":
            self.path = str(st.get("path") or "")
            self.sha1, self.crc32 = st.get("sha1"), st.get("crc32")
            self.done, self._p, self.speed = self.size, 1.0, 0.0
            self.meta["phase"] = "Completa"
        elif st.get("state") == "failed":
            self.error = str(st.get("error") or "falló en el servidor")


class Jobs:
    def __init__(self, on_done=None, every=0.5, on_wait=None, store=None):
        self._jobs, self._lock, self.on_done, self.every, self.on_wait = {}, threading.Lock(), on_done, every, on_wait
        self._t = None
        self.store = store          # archivo JSON: las descargas siguen en el servicio aunque Hub se cierre, así que se recuerdan para retomarlas

    def _save(self):
        if not self.store:
            return
        with self._lock:
            rows = [j.to_dict() for j in sorted(self._jobs.values(), key=lambda j: j.added)][-40:]
        try:
            tmp = str(self.store) + ".tmp"
            os.makedirs(os.path.dirname(str(self.store)), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(rows, f)
            os.replace(tmp, self.store)
        except OSError as ex:
            print(f"[catalogo] no pude guardar las descargas del servicio: {ex}", flush=True)

    def restore(self):
        """Recupera las descargas de la sesión anterior. Las que seguían vivas se vuelven a consultar (y si terminaron con Hub cerrado, se procesan al llegar)."""
        if not self.store:
            return 0
        try:
            rows = json.loads(open(self.store, encoding="utf-8").read())
        except (OSError, ValueError):
            return 0
        n = 0
        for d in rows if isinstance(rows, list) else []:
            try:
                j = CatalogJob.from_dict(d)
            except (KeyError, TypeError, ValueError):
                continue
            with self._lock:
                self._jobs.setdefault(j.id, j)
            n += j.state == "queued"
        if n:
            self._start()
        return n

    def list(self):
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.added)

    def add(self, job_id, title, size=0, resumable=True, entry_id="", source=""):
        j = CatalogJob(job_id, title, size, resumable, entry_id, source)
        with self._lock:
            self._jobs[j.id] = j
        self._save()
        self._start()
        return j

    def _start(self):
        if self._t and self._t.is_alive():
            return
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        idle = 0
        while idle < 20:   # ~10 s sin trabajos activos y el hilo termina; add() lo reabre
            with self._lock:
                live = [j for j in self._jobs.values() if j.state in ("queued", "active", "waiting")]
            idle = 0 if live else idle + 1
            for j in live:
                self.poll(j)
            time.sleep(self.every)

    def poll(self, j):
        try:
            st = cs.job_status(j.job_id)
            j.fails = 0
        except cs.CatalogError as ex:
            j.fails += 1
            if j.fails >= 3:   # un fallo suelto de red no mata el trabajo
                j.state, j.error = "error", f"se perdió la conexión con el servicio ({ex})"
                self._save()
            return
        except Exception as ex:  # noqa: BLE001  — nada inesperado debe matar el hilo que sondea a todos los jobs
            print(f"[catalogo] job_status inesperado: {type(ex).__name__}: {ex}", flush=True)
            j.fails += 1
            if j.fails >= 3:
                j.state, j.error = "error", f"se perdió la conexión con el servicio ({type(ex).__name__}: {ex})"
            return
        if j.state == "cancelled":   # el usuario canceló mientras esta consulta volaba: no resucitar el trabajo
            return
        antes = j.state
        j.apply(st if isinstance(st, dict) else {})
        if j.state != antes:
            self._save()
        if j.state == "waiting" and not j.alerted:
            j.alerted = True            # avisa UNA vez por parada, no en cada consulta
            if self.on_wait:
                try:
                    self.on_wait(j)
                except Exception as ex:  # noqa: BLE001
                    print(f"[catalogo] on_wait falló: {ex}", flush=True)
        elif j.state != "waiting":
            j.alerted = False
        if j.state == "done" and not j.notified:
            j.notified = True
            self._save()
            if self.on_done:
                try:
                    self.on_done(j)
                except Exception as ex:  # noqa: BLE001
                    print(f"[catalogo] on_done falló: {ex}", flush=True)

    def cancel(self, id_):
        with self._lock:
            j = self._jobs.get(id_)
        if not j:
            return
        try:
            cs.job_cancel(j.job_id)
        except cs.CatalogError as ex:
            print(f"[catalogo] job_cancel falló: {ex}", flush=True)
        j.state = "cancelled"
        self._save()

    def remove(self, id_):
        with self._lock:
            self._jobs.pop(id_, None)
        self._save()

    def clear_finished(self):
        with self._lock:
            for k in [k for k, j in self._jobs.items() if j.state in ("done", "error", "cancelled")]:
                del self._jobs[k]
        self._save()
