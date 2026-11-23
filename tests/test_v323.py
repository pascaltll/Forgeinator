"""v3.23 · forgeinatord: cola de descargas fuera del Hub, socket JSON, eventos, pausa/cancelar, persistencia y arranque en segundo plano."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from conftest import HUB_SRC
from hub import config, remote, service


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "CONFIG", tmp_path / "conf")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    p = Path("/tmp") / f"fg-{os.getpid()}-{time.time_ns()}.sock"
    monkeypatch.setenv("FORGEINATOR_SOCK", str(p))
    src = remote.add("local", "USB", {"path": str(tmp_path / "usb")})
    yield p, src
    p.unlink(missing_ok=True)


def slow_downloader(delay=0.4, fail=None):
    def dl(src, game, system, progress=None, stop=lambda: False, cfg=None):
        for i in range(10):
            if stop():
                raise remote.RemoteError("Descarga cancelada")
            progress and progress((i + 1) * 100, 1000, 9 - i, 1e6)
            time.sleep(delay / 10)
        if fail and game["name"] == fail:
            raise remote.RemoteError("El servidor rechazó el usuario o la contraseña")
        return Path("/tmp/x") / game["name"]
    return dl


def _serve(path, q):
    svc = service.Service(q)
    t = threading.Thread(target=svc.serve, args=(path,), daemon=True)
    t.start()
    for _ in range(50):
        if service._alive(path):
            break
        time.sleep(0.05)
    return svc, t


def _wait(cond, t=10):
    t0 = time.time()
    while not cond() and time.time() - t0 < t:
        time.sleep(0.05)
    assert cond()


def test_cola_eventos_y_estados(env):
    path, src = env
    q = service.Queue(max_active=1, downloader=slow_downloader(fail="malo.chd"))
    svc, t = _serve(path, q)
    try:
        assert service.call("ping", start=False)["protocol"] == 1
        ev = []
        s = socket.socket(socket.AF_UNIX)
        s.connect(str(path))
        s.sendall(b'{"v":1,"id":"e","method":"events.subscribe"}\n')
        f = s.makefile("rb")
        assert json.loads(f.readline())["result"]["subscribed"]
        threading.Thread(target=lambda: [ev.append(json.loads(ln)) for ln in f], daemon=True).start()
        a = service.call("downloads.add", {"source": src["id"], "game": {"path": "psx/a.chd", "name": "a.chd"}, "system": "psx"}, start=False)["id"]
        b = service.call("downloads.add", {"source": src["id"], "game": {"path": "psx/malo.chd", "name": "malo.chd"}, "system": "psx"}, start=False)["id"]
        dup = service.call("downloads.add", {"source": src["id"], "game": {"path": "psx/a.chd", "name": "a.chd"}, "system": "psx"}, start=False)["id"]
        assert dup == a                                                                        # no se duplica
        st = {d["id"]: d["state"] for d in service.call("downloads.list", start=False)}
        assert st[a] == "active" and st[b] == "queued"                                          # de una en una
        _wait(lambda: {d["id"]: d["state"] for d in service.call("downloads.list", start=False)}.get(b) == "error")
        ds = {d["id"]: d for d in service.call("downloads.list", start=False)}
        assert ds[a]["state"] == "done" and "contraseña" in ds[b]["error"]
        kinds = [e["event"] for e in ev]
        assert "download.progress" in kinds and "download.done" in kinds and "download.error" in kinds
        service.call("downloads.clear", start=False)
        assert [d["id"] for d in service.call("downloads.list", start=False)] == []
        with pytest.raises(service.ServiceError) as ei:
            service.call("downloads.pause", {"id": "nope"}, start=False)
        assert ei.value.code == "no_existe"
        with pytest.raises(service.ServiceError):
            service.call("hackear", start=False)
        s.close()
    finally:
        service.call("shutdown", start=False)
        t.join(5)
    assert not path.exists()


def test_pausar_cancelar_y_retomar_tras_reinicio(env):
    path, src = env
    q = service.Queue(max_active=1, downloader=slow_downloader(delay=3))
    svc, t = _serve(path, q)
    try:
        a = service.call("downloads.add", {"source": src["id"], "game": {"path": "p/a", "name": "a"}, "system": "psx"}, start=False)["id"]
        b = service.call("downloads.add", {"source": src["id"], "game": {"path": "p/b", "name": "b"}, "system": "psx"}, start=False)["id"]
        service.call("downloads.pause", {"id": a}, start=False)
        _wait(lambda: {d["id"]: d["state"] for d in service.call("downloads.list", start=False)}[a] == "paused")
        service.call("downloads.cancel", {"id": b}, start=False)
        _wait(lambda: {d["id"]: d["state"] for d in service.call("downloads.list", start=False)}[b] == "cancelled")
        service.call("downloads.resume", {"id": a}, start=False)
        _wait(lambda: {d["id"]: d["state"] for d in service.call("downloads.list", start=False)}[a] == "active")
    finally:
        service.call("shutdown", start=False)
        t.join(5)
    q2 = service.Queue(max_active=1, downloader=slow_downloader(delay=0.1))      # «reinicio»: lo activo vuelve a la cola
    assert {x["id"]: x["state"] for x in q2.items}[a] == "queued"
    q2.pump()
    _wait(lambda: q2.get(a)["state"] == "done")


def test_arranque_en_segundo_plano_y_cliente(env, monkeypatch):
    path, src = env
    monkeypatch.setenv("FORGEINATOR_NO_SYSTEMD", "1")
    monkeypatch.setenv("HUB_DATA", str(config.DATA))
    monkeypatch.setenv("PYTHONPATH", str(HUB_SRC))
    monkeypatch.chdir(HUB_SRC)
    try:
        assert service.start_detached(wait=10)
        r = service.call("ping", start=False)
        assert r["pid"] != os.getpid()                                                   # otro proceso: sobrevive al Hub
        assert (path.stat().st_mode & 0o777) == 0o600
        r = subprocess.run([str(HUB_SRC / "bin" / "forgeinatord"), "--estado"], capture_output=True, text=True, timeout=20,
                           env=dict(os.environ))
        assert '"protocol": 1' in r.stdout
    finally:
        try:
            service.call("shutdown", start=False)
        except OSError:
            pass
        _wait(lambda: not path.exists(), 10)


def test_interfaz_encola_en_el_servicio(env, monkeypatch):
    from test_temas_y_fuzz import H  # noqa: F401
    import hub.ui as U
    path, src = env
    q = service.Queue(max_active=1, downloader=slow_downloader(delay=1))
    svc, t = _serve(path, q)
    try:
        ui = U.UI.__new__(U.UI)
        ui.cfg, ui._io_gen = {}, 0
        msgs = []
        ui.toast = msgs.append
        ui._remote_get(src, {"path": "psx/x.chd", "name": "x.chd"}, "psx")
        assert "en cola" in msgs[-1] and q.items and q.items[0]["name"] == "x.chd"
        _wait(lambda: q.items[0]["state"] == "active")
        assert "bajando «x.chd»" in ui._remote_txt()
    finally:
        service.call("shutdown", start=False)
        t.join(5)
