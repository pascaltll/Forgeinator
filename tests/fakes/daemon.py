"""Daemon JSON-RPC 2.0 falso, configurable, para inyectar fallos.

Como librería:  d = FakeDaemon(token="T"); d.start(); ...; d.stop()
Como proceso (para probar el autoarranque):  python daemon.py PUERTO TOKEN [--token-file F] [--token-delay S] [--open-delay S]
"""
import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

DEFAULT_HEALTH = [{"source": "nas", "status": "OK", "reason": "", "last_success_ago": 3},
                  {"source": "viejo", "status": "DEAD", "reason": "sin respuesta", "last_success_ago": 9999}]


def default_search():
    return [{"source": "nas", "item_id": "sh1", "title": "Silent Hill", "platform": "PlayStation", "confidence": 0.95},
            {"source": "viejo", "item_id": "sh2", "title": "Silent Hill 2", "platform": "PlayStation 2", "confidence": 0.4}]


def default_variants(n=2, size=None):
    return [{"variant_id": f"v{i}", "item_id": "sh1", "filename": f"Silent Hill (USA) (Disc {i}).bin", "region": "USA", "format": "bin/cue",
             "size": size or f"{600 + i} MB", "url": "x", "resumable": i % 2 == 0} for i in range(n)]


class FakeDaemon:
    def __init__(self, token="SECRETO", port=0):
        self.token = token
        self.calls = []            # (method, params)
        self.headers = []          # cabeceras de cada petición
        self.bodies = []           # cuerpo JSON crudo de cada petición
        self.rpc_errors = {}       # método -> (code, message, data)
        self.results = {}          # método -> resultado fijo
        self.http_status = None    # fuerza este estado HTTP en TODAS las respuestas
        self.raw = None            # fuerza este cuerpo (bytes/str) en la respuesta
        self.delay = 0.0           # retraso antes de responder
        self.job_script = None     # lista de dicts para job_status (el último se repite)
        self.write_file = True     # el job "completo" crea de verdad el archivo
        self.require_dest = False  # download falla con -2 si dest_dir no existe
        self.filename = "Silent Hill (USA).bin"
        self.file_bytes = 16
        self.n_variants, self.variant_size = 2, None
        self.known_items = None    # si es un set, variants de otro item_id da error -32001
        self.with_hashes = False   # el job completo incluye sha1 y crc32 reales
        self.jobs = {}
        self.cancelled = set()
        self._lock = threading.Lock()
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, status, body=b"", ctype="application/json"):
                if isinstance(body, str):
                    body = body.encode()
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.headers.append(dict(self.headers))
                try:
                    req = json.loads(raw)
                except ValueError:
                    req = {}
                outer.bodies.append(req)
                if outer.delay:
                    time.sleep(outer.delay)
                if outer.http_status:
                    return self._send(outer.http_status, outer.raw if outer.raw is not None else b"")
                if self.headers.get("X-Catalog-Token") != outer.token:
                    return self._send(401)
                if outer.raw is not None:
                    return self._send(200, outer.raw)
                m, p, i = req.get("method"), req.get("params") or {}, req.get("id")
                with outer._lock:
                    outer.calls.append((m, p))
                try:
                    self._send(200, json.dumps(outer.dispatch(m, p, i)))
                except BrokenPipeError:
                    pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
        self.srv.daemon_threads = True
        self.port = self.srv.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/rpc"
        self._t = None

    # ── respuestas ───────────────────────────────────────────
    def dispatch(self, m, p, i):
        def ok(r):
            return {"jsonrpc": "2.0", "id": i, "result": r}

        def err(c, msg, data=None):
            e = {"code": c, "message": msg}
            if data is not None:
                e["data"] = data
            return {"jsonrpc": "2.0", "id": i, "error": e}
        if m in self.rpc_errors:
            return err(*self.rpc_errors[m])
        if m in self.results:
            return ok(self.results[m])
        if m == "health":
            return ok(DEFAULT_HEALTH)
        if m == "search":
            if not p.get("query"):
                return err(-32602, "query requerido")
            return ok(default_search())
        if m == "variants":
            if not p.get("item_id"):
                return err(-32602, "item_id requerido")
            if self.known_items is not None and p["item_id"] not in self.known_items:
                return err(-32001, "item desconocido")
            return ok(default_variants(self.n_variants, self.variant_size))
        if m == "download":
            dest = p.get("dest_dir", "")
            if self.require_dest and not Path(dest).is_dir():
                return err(-2, f"No such file or directory: {dest}")
            with self._lock:
                jid = f"job_{len(self.jobs) + 1}"
                self.jobs[jid] = {"t0": time.time(), "dest": dest, "polls": 0}
            return ok({"job_id": jid})
        if m == "job_status":
            j = self.jobs.get(p.get("job_id"))
            if not j:
                return err(-32001, "job desconocido")
            if p["job_id"] in self.cancelled:
                return ok({"state": "failed", "phase": "downloading", "progress": 0.2, "bytes_per_s": 0, "error": "cancelado"})
            j["polls"] += 1
            if self.job_script is not None:
                st = self.job_script[min(j["polls"] - 1, len(self.job_script) - 1)]
                if isinstance(st, tuple):          # (code, message) → error JSON-RPC
                    return err(*st)
                return ok(st)
            if j["polls"] == 1:
                return ok({"state": "running", "phase": "resolving_cdn", "progress": 0.0, "bytes_per_s": 0})
            if j["polls"] == 2:
                return ok({"state": "running", "phase": "downloading", "progress": 0.5, "bytes_per_s": 1048576})
            f = str(Path(j["dest"]) / self.filename)
            if self.write_file:
                Path(f).parent.mkdir(parents=True, exist_ok=True)
                Path(f).write_bytes(b"x" * self.file_bytes)
            st = {"state": "completed", "phase": "downloading", "progress": 1.0, "bytes_per_s": 0, "path": f}
            if self.with_hashes and self.write_file:
                import hashlib, zlib
                data = Path(f).read_bytes()
                st["sha1"], st["crc32"] = hashlib.sha1(data).hexdigest(), f"{zlib.crc32(data) & 0xffffffff:08x}"
            return ok(st)
        if m == "job_cancel":
            self.cancelled.add(p.get("job_id"))
            return ok({})
        return err(-32601, "método desconocido: " + str(m))

    # ── ciclo de vida ────────────────────────────────────────
    def start(self):
        self._t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self._t.start()
        return self

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()

    def count(self, method):
        return sum(1 for m, _ in self.calls if m == method)


def main(argv):
    """Modo proceso: abre el puerto tras --open-delay y crea el token tras --token-delay (como un daemon real)."""
    port, token = int(argv[0]), argv[1]
    opt = {a: argv[i + 1] for i, a in enumerate(argv) if a.startswith("--") and i + 1 < len(argv)}
    if os.environ.get("FAKE_PID_FILE"):
        Path(os.environ["FAKE_PID_FILE"]).write_text(str(os.getpid()))
    print("fake daemon arrancando con", sys.executable, flush=True)
    time.sleep(float(opt.get("--open-delay", 0)))
    d = FakeDaemon(token, port)
    tf = opt.get("--token-file")
    if tf and float(opt.get("--token-delay", 0)) >= 0:
        threading.Timer(float(opt.get("--token-delay", 0)), lambda: Path(tf).write_text(token)).start()
    d.srv.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
