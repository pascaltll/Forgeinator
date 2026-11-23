"""v3.23 · forgeinatord (E5b): el servicio de descargas de Forgeinator, sin ventana.

Las descargas de las bibliotecas remotas viven aquí y no en la interfaz: siguen aunque cierres el Hub o abras un juego, hay cola
(persistente: tras un reinicio se retoma) y varias a la vez. El Hub, el QAM y el teléfono son clientes que solo piden cosas.

Socket UNIX $XDG_RUNTIME_DIR/forgeinator.sock (FORGEINATOR_SOCK lo sustituye), permisos 600. Una línea JSON por mensaje:
  → {"v":1,"id":…,"method":"downloads.add","params":{…}}      ← {"v":1,"id":…,"ok":true,"result":…} | {"ok":false,"error","detail"}
Métodos: ping · sources.list · sources.test · browse · downloads.add · downloads.list · downloads.pause · downloads.resume ·
downloads.cancel · downloads.clear · events.subscribe (la conexión queda abierta y recibe {"event":…} por línea) · shutdown.
Se arranca solo cuando un cliente lo necesita (start_detached) y se apaga tras IDLE_EXIT s sin descargas ni clientes.
Contrato completo: claude/forgeinator-servicio-protocolo.md. Solo biblioteca estándar (+ rclone para las descargas)."""
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from . import config, remote

V = 1
IDLE_EXIT = 600.0
STATES = ("queued", "active", "paused", "done", "error", "cancelled")


def sock_path() -> Path:
    if os.environ.get("FORGEINATOR_SOCK"):
        return Path(os.environ["FORGEINATOR_SOCK"])
    run = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(run) / "forgeinator.sock"


def _queue_file() -> Path:
    return config.DATA / "remote-queue.json"


# ---------------------------------------------------------------- cola
class Queue:
    def __init__(self, max_active=2, downloader=None):
        self.lock = threading.RLock()
        self.items = []                                 # [{id, source, path, name, dir, size, system, state, done, total, eta, speed, error, t}]
        self.stops = {}
        self.max_active = max_active
        self.downloader = downloader or remote.download
        self.listeners = []
        self.last_activity = time.time()
        self._load()

    # persistencia: lo que estaba activo al apagarse vuelve a la cola
    def _load(self):
        try:
            d = json.loads(_queue_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = []
        for it in d if isinstance(d, list) else []:
            if it.get("state") == "active":
                it["state"] = "queued"
            self.items.append(it)

    def _save(self):
        try:
            f = _queue_file()
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_name(f.name + ".tmp")
            tmp.write_text(json.dumps(self.items, indent=1, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, f)
        except OSError:
            pass

    def emit(self, event, it):
        msg = {"event": event, "download": dict(it)}
        for fn in list(self.listeners):
            try:
                fn(msg)
            except Exception:  # noqa: BLE001
                self.listeners.remove(fn)

    def add(self, source, game, system):
        with self.lock:
            for it in self.items:
                if it["source"] == source and it["path"] == game["path"] and it["state"] in ("queued", "active", "paused"):
                    return it["id"]                     # ya está en la cola
            it = {"id": uuid.uuid4().hex[:10], "source": source, "path": game["path"], "name": game["name"], "dir": bool(game.get("dir")),
                  "size": game.get("size"), "system": system, "state": "queued", "done": 0, "total": game.get("size") or 0, "eta": None,
                  "speed": 0.0, "error": None, "t": time.time()}
            self.items.append(it)
            self._save()
        self.emit("download.added", it)
        self.pump()
        return it["id"]

    def get(self, did):
        it = next((x for x in self.items if x["id"] == did), None)
        if not it:
            raise KeyError(did)
        return it

    def pause(self, did):
        with self.lock:
            it = self.get(did)
            if it["state"] == "active":
                self.stops[did] = "paused"
            elif it["state"] == "queued":
                it["state"] = "paused"
                self._save()
        self.emit("download.state", it)

    def resume(self, did):
        with self.lock:
            it = self.get(did)
            if it["state"] in ("paused", "error", "cancelled"):
                it.update(state="queued", error=None)
                self._save()
        self.pump()

    def cancel(self, did):
        with self.lock:
            it = self.get(did)
            if it["state"] == "active":
                self.stops[did] = "cancelled"
            elif it["state"] in ("queued", "paused"):
                it["state"] = "cancelled"
                self._save()
        self.emit("download.state", it)

    def clear(self):
        with self.lock:
            self.items = [x for x in self.items if x["state"] in ("queued", "active", "paused")]
            self._save()

    def busy(self) -> bool:
        return any(x["state"] in ("queued", "active") for x in self.items)

    def pump(self):
        with self.lock:
            active = sum(1 for x in self.items if x["state"] == "active")
            for it in self.items:
                if active >= self.max_active:
                    break
                if it["state"] == "queued":
                    it["state"] = "active"
                    active += 1
                    threading.Thread(target=self._run, args=(it,), daemon=True, name=f"dl-{it['id']}").start()
            self._save()

    def _run(self, it):
        self.last_activity = time.time()
        self.emit("download.state", it)
        last = [0.0]

        def prog(b, tot, eta, spd):
            it.update(done=b, total=tot or it["total"], eta=eta, speed=spd)
            if time.time() - last[0] >= 1.0:
                last[0] = time.time()
                self.emit("download.progress", it)

        try:
            src = remote.get(it["source"])
            dest = self.downloader(src, {"path": it["path"], "name": it["name"], "dir": it["dir"]}, it["system"], prog,
                                   stop=lambda: it["id"] in self.stops)
            it.update(state="done", dest=str(dest), done=it.get("total") or it["done"], eta=0)
            self.emit("download.done", it)
        except remote.RemoteError as ex:
            why = self.stops.get(it["id"])
            it.update(state=why or "error", error=None if why else str(ex))
            self.emit("download.state" if why else "download.error", it)
        except Exception as ex:  # noqa: BLE001
            it.update(state="error", error=f"{type(ex).__name__}: {ex}")
            self.emit("download.error", it)
        finally:
            self.stops.pop(it["id"], None)
            self.last_activity = time.time()
            with self.lock:
                self._save()
            self.pump()


# ---------------------------------------------------------------- servidor
class Service:
    def __init__(self, queue=None):
        self.q = queue or Queue(max_active=int(config.settings().get("max_active", 2) or 2))
        self.clients = 0
        self.stop = threading.Event()

    def handle(self, msg, conn_send):
        m, p = msg.get("method"), msg.get("params") or {}
        if m == "ping":
            from . import channel
            return {"version": config.VERSION, "channel": channel.CHANNEL or "legacy", "pid": os.getpid(), "protocol": V,
                    "methods": sorted(METHODS)}
        if m == "sources.list":
            return remote.sources()
        if m == "sources.test":
            return remote.test(remote.get(p["source"]))
        if m == "browse":
            s = remote.get(p["source"])
            return remote.systems(s) if not p.get("path") else remote.games(s, p["path"], p.get("system") or "")
        if m == "downloads.add":
            return {"id": self.q.add(p["source"], p["game"], p["system"])}
        if m == "downloads.list":
            return [dict(x) for x in self.q.items]
        if m in ("downloads.pause", "downloads.resume", "downloads.cancel"):
            getattr(self.q, m.split(".")[1])(p["id"])
            return True
        if m == "downloads.clear":
            self.q.clear()
            return True
        if m == "events.subscribe":
            self.q.listeners.append(conn_send)
            return {"subscribed": True}
        if m == "shutdown":
            self.stop.set()
            return True
        raise LookupError(m)

    def serve(self, path: Path = None):
        path = Path(path or sock_path())
        if path.exists():
            if _alive(path):
                raise SystemExit(f"forgeinatord ya está en marcha ({path})")
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        svc = self

        class H(socketserver.StreamRequestHandler):
            def handle(self):
                svc.clients += 1
                lock = threading.Lock()

                def send(obj):
                    with lock:
                        self.wfile.write((json.dumps(obj, ensure_ascii=False) + "\n").encode())
                        self.wfile.flush()
                try:
                    for raw in self.rfile:
                        if len(raw) > 65536:
                            break
                        msg, rid = {}, None
                        try:
                            msg = json.loads(raw.decode())
                            if not isinstance(msg, dict):
                                raise ValueError("se esperaba un objeto JSON")
                            rid = msg.get("id")
                            res = {"v": V, "id": rid, "ok": True, "result": svc.handle(msg, send)}
                        except KeyError as ex:
                            res = {"v": V, "id": rid, "ok": False, "error": "no_existe", "detail": f"no existe: {ex}"}
                        except LookupError as ex:
                            res = {"v": V, "id": rid, "ok": False, "error": "metodo", "detail": f"método desconocido: {ex}"}
                        except remote.RemoteError as ex:
                            res = {"v": V, "id": rid, "ok": False, "error": "remota", "detail": str(ex)}
                        except (ValueError, TypeError) as ex:
                            res = {"v": V, "id": rid, "ok": False, "error": "invalido", "detail": str(ex)}
                        send(res)
                        if svc.stop.is_set():
                            break
                except (OSError, ValueError):
                    pass
                finally:
                    if send in svc.q.listeners:
                        svc.q.listeners.remove(send)
                    svc.clients -= 1
                    svc.q.last_activity = time.time()

        class S(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
            daemon_threads = True

        srv = S(str(path), H)
        os.chmod(path, 0o600)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.q.pump()
        print(f"[servicio] forgeinatord {config.VERSION} escuchando en {path} (pid {os.getpid()})", file=sys.stderr, flush=True)
        try:
            while not self.stop.wait(2.0):
                if not self.q.busy() and self.clients == 0 and time.time() - self.q.last_activity > IDLE_EXIT:
                    print("[servicio] sin descargas ni clientes: me apago", file=sys.stderr, flush=True)
                    break
        finally:
            srv.shutdown()
            srv.server_close()
            try:
                path.unlink()
            except OSError:
                pass


METHODS = ("ping", "sources.list", "sources.test", "browse", "downloads.add", "downloads.list", "downloads.pause", "downloads.resume",
           "downloads.cancel", "downloads.clear", "events.subscribe", "shutdown")


# ---------------------------------------------------------------- cliente
def _alive(path: Path) -> bool:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(str(path))
            return True
    except OSError:
        return False


class ServiceError(OSError):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code


def call(method, params=None, timeout=10.0, start=True):
    """Una petición al servicio (lo arranca si hace falta y start=True)."""
    path = sock_path()
    if not _alive(path):
        if not start:
            raise ServiceError("sin_servicio", "forgeinatord no está en marcha")
        start_detached()
    msg = {"v": V, "id": uuid.uuid4().hex[:8], "method": method, "params": params or {}}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(str(path))
        s.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode())
        f = s.makefile("rb")
        line = f.readline()
    r = json.loads(line.decode() or "{}")
    if not r.get("ok"):
        raise ServiceError(r.get("error", "?"), r.get("detail", "respuesta vacía del servicio"))
    return r.get("result")


def start_detached(wait=5.0):
    """Arranca forgeinatord fuera del proceso del Hub (sigue vivo aunque el Hub se cierre). Con systemd, como unidad pasajera del
    usuario (se ve con `systemctl --user status forgeinatord`); si no, como proceso en su propia sesión."""
    path = sock_path()
    root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, "-m", "hub.service"]
    env = dict(os.environ, PYTHONPATH=str(root))
    log = config.STATE / "forgeinatord.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    started = False
    if not os.environ.get("FORGEINATOR_NO_SYSTEMD") and _which("systemd-run"):
        r = subprocess.run(["systemd-run", "--user", "--collect", "--quiet", "--unit", f"forgeinatord-{int(time.time())}",
                            f"--working-directory={root}", "--setenv=PYTHONPATH=" + str(root)]
                           + [f"--setenv={k}={os.environ[k]}" for k in ("HUB_DATA", "HUB_CONF", "HUB_STATE", "HUB_CONFIG", "FORGEINATOR_SOCK",
                                                                       "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "HUB_RCLONE") if os.environ.get(k)]
                           + ["sh", "-c", f'exec "$0" -m hub.service >> "{log}" 2>&1', sys.executable],
                           capture_output=True, text=True, timeout=10)
        started = r.returncode == 0
    if not started:
        with open(log, "ab") as lf:
            subprocess.Popen(cmd, cwd=str(root), env=env, stdout=lf, stderr=lf, stdin=subprocess.DEVNULL, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < wait:
        if _alive(path):
            return True
        time.sleep(0.1)
    raise ServiceError("no_arranca", f"forgeinatord no arrancó (mira {log})")


def _which(n):
    from shutil import which
    return which(n)


def _estado() -> int:
    try:
        print(json.dumps(call("ping", start=False), ensure_ascii=False))
        for d in call("downloads.list", start=False):
            print(f"{d['state']:9} {d['name']} ({d['system']})" + (f" · {d['error']}" if d.get("error") else ""))
        return 0
    except OSError as ex:
        print(f"forgeinatord no está en marcha: {ex}")
        return 1


if __name__ == "__main__":
    if "--estado" in sys.argv:
        sys.exit(_estado())
    Service().serve()
