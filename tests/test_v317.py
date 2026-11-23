"""v3.17 · Atajos de Steam automáticos a través de QAM Rail (socket local): el juego sale en la barra lateral con su perfil de TDP."""
import json
import os
import socket
import threading
import time
import types
from pathlib import Path

import pytest

from conftest import HUB_SRC  # noqa: F401
from hub import qamlink, directplay, config
from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


class FakeQam:
    """Un QAM Rail de mentira: responde como diga `handler(msg) -> dict|bytes|None` (None = no responde)."""

    def __init__(self, path, handler):
        self.path, self.handler, self.seen = str(path), handler, []
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(self.path)
        self.srv.listen(4)
        self.t = threading.Thread(target=self._loop, daemon=True)
        self.t.start()

    def _loop(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            with c:
                buf = b""
                while b"\n" not in buf:
                    ch = c.recv(4096)
                    if not ch:
                        break
                    buf += ch
                msg = json.loads(buf.decode())
                self.seen.append(msg)
                r = self.handler(msg)
                if r is None:
                    time.sleep(3)
                    continue
                c.sendall(r if isinstance(r, bytes) else (json.dumps(r) + "\n").encode())

    def close(self):
        try:
            self.srv.shutdown(socket.SHUT_RDWR)        # despierta el accept() del hilo
        except OSError:
            pass
        self.srv.close()
        self.t.join(timeout=4)


def good(msg):
    if msg["op"] == "ping":
        return {"v": 1, "request_id": msg["request_id"], "ok": True, "version": "0.54.0", "ops": ["ping", "steam.run_shortcut"]}
    return {"v": 1, "request_id": msg["request_id"], "ok": True, "appid": 3141592653, "created": True, "launched": True}


@pytest.fixture
def sock(tmp_path, monkeypatch):
    p = Path("/tmp") / f"qr-{os.getpid()}-{time.time_ns()}.sock"    # rutas cortas: los sockets UNIX tienen límite de longitud
    monkeypatch.setenv("QAM_RAIL_SOCK", str(p))
    yield p
    p.unlink(missing_ok=True)


def test_sin_qam(sock):
    r = qamlink.ping()
    assert not r["ok"] and r["error"] == "sin_qam"


def test_ping_y_lanzar(sock, tmp_path):
    q = FakeQam(sock, good)
    try:
        assert qamlink.ping()["ok"]
        art = tmp_path / "portrait.png"
        art.write_bytes(b"png")
        g = qamlink.game_request("ctr", "Crash Team Racing", "/x/shortcuts/ctr.sh", art={"portrait": art, "hero": tmp_path / "no.png", "otro": art},
                                 appid=7, run_delay_ms=1500)
        r = qamlink.run_shortcut(g)
        assert r["ok"] and r["appid"] == 3141592653
        m = q.seen[-1]
        assert m["v"] == 1 and m["op"] == "steam.run_shortcut" and m["from"] == "forgeinator"
        assert m["game"] == {"key": "forgeinator:ctr", "name": "Crash Team Racing", "exe": "/x/shortcuts/ctr.sh", "start_dir": "/x/shortcuts",
                             "launch_options": "", "art": {"portrait": str(art)}, "run_delay_ms": 1500, "appid": 7}
    finally:
        q.close()


@pytest.mark.parametrize("handler,err", [
    (lambda m: {"v": 1, "request_id": m["request_id"], "ok": True, "version": "0.53", "ops": ["ping"]}, "sin_op"),
    (lambda m: b"esto no es json\n", "respuesta"),
    (lambda m: {"v": 1, "request_id": "otra", "ok": True, "ops": ["steam.run_shortcut"]}, "respuesta"),
])
def test_respuestas_malas(sock, handler, err):
    q = FakeQam(sock, handler)
    try:
        assert qamlink.ping()["error"] == err
    finally:
        q.close()


def test_sin_appid_y_tiempo(sock):
    q = FakeQam(sock, lambda m: {"v": 1, "request_id": m["request_id"], "ok": True} if m["op"] != "ping" else good(m))
    try:
        assert qamlink.run_shortcut({"key": "k"})["error"] == "respuesta"
    finally:
        q.close()
    sock.unlink()
    q = FakeQam(sock, lambda m: None)
    try:
        t = time.time()
        r = qamlink.run_shortcut({"key": "k"}, timeout=0.5)
        assert r["error"] == "tiempo" and time.time() - t < 2.5
    finally:
        q.close()


def test_appids_recordados(tmp_path):
    assert qamlink.known_appids(tmp_path) == {}
    qamlink.remember_appid(tmp_path, "ctr", 5)
    qamlink.remember_appid(tmp_path, "gow2", 6)
    assert qamlink.known_appids(tmp_path) == {"ctr": 5, "gow2": 6}


def test_script_del_atajo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    p = directplay.ensure_script("ctr", True)
    assert p == tmp_path / "l/shortcuts/ctr.sh" and directplay.HUB_MARK in p.read_text() and os.access(p, os.X_OK)
    p.write_text("#!/bin/sh\n# a mano\n")
    directplay.ensure_script("ctr", True)
    assert p.read_text() == "#!/bin/sh\n# a mano\n"                     # uno hecho a mano no se toca
    assert directplay.LAUNCHER_MARK in directplay.ensure_script("otro", False).read_text()


def _prep(H, ui, tmp_path, monkeypatch):
    monkeypatch.delenv("SteamGameId", raising=False)
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    monkeypatch.setattr(config, "DATA", tmp_path / "d")
    (config.LAUNCHER / "bin").mkdir(parents=True)
    (config.LAUNCHER / "bin" / "play").write_text("#!/bin/sh\n")
    (config.LAUNCHER / "bin" / "play").chmod(0o755)
    ui._gm = True
    ui.cfg["play_via_steam"] = True
    lanzados = []
    monkeypatch.setattr(H.subprocess, "Popen", lambda *a, **k: lanzados.append(a) or types.SimpleNamespace(pid=4242, poll=lambda: None), raising=False)
    monkeypatch.setattr(ui, "inst", lambda e: {"installed": True, "launcher_id": "ctr", "version": "1", "dir": str(tmp_path / "g")})
    monkeypatch.setattr(ui, "libs_for", lambda lid: [])
    monkeypatch.setattr(ui, "_exe_missing", lambda e, lid: False)
    monkeypatch.setattr(ui, "steam_shortcut", lambda lid, name="": None)
    monkeypatch.setattr(H.config, "save_settings", lambda s: None)
    ui.play_pr = ui.exit_at = None
    ui._qam_busy = False
    return lanzados


def _wait(ui, cond, t=5):
    t0 = time.time()
    while not cond() and time.time() - t0 < t:
        ui.pump()
        time.sleep(0.02)


def test_jugar_crea_el_atajo_y_lanza_por_steam(H, ui, tmp_path, monkeypatch, sock):
    lanzados = _prep(H, ui, tmp_path, monkeypatch)
    q = FakeQam(sock, good)
    try:
        ui.play({"id": "ctr", "name": "Crash Team Racing"})
        _wait(ui, lambda: ui.exit_at)
        assert ui.exit_at and not lanzados and ui.modal is None                 # lanzado por Steam, nada a pelo
        assert qamlink.known_appids(config.DATA) == {"ctr": 3141592653}
        g = q.seen[-1]["game"]
        assert g["exe"] == str(config.LAUNCHER / "shortcuts" / "ctr.sh") and g["run_delay_ms"] == 0
        assert (config.LAUNCHER / "shortcuts" / "ctr.sh").exists()
    finally:
        q.close()
        ui.exit_at = None
        del ui._gm


def test_sin_qam_vuelve_a_preguntar(H, ui, tmp_path, monkeypatch, sock):
    lanzados = _prep(H, ui, tmp_path, monkeypatch)
    try:
        ui.play({"id": "ctr", "name": "Crash Team Racing"})
        _wait(ui, lambda: ui.modal)
        assert ui.modal and ui.modal["title"] == "Este juego no tiene atajo en Steam" and not lanzados
    finally:
        ui.modal = None
        del ui._gm


def test_hub_como_juego_de_steam_pide_retraso_y_cierra(H, ui, tmp_path, monkeypatch, sock):
    _prep(H, ui, tmp_path, monkeypatch)
    monkeypatch.setenv("SteamGameId", "123")
    ui.cfg["close_on_play"] = False
    q = FakeQam(sock, good)
    try:
        ui.play({"id": "ctr", "name": "Crash Team Racing"})
        _wait(ui, lambda: ui.exit_at)
        assert q.seen[-1]["game"]["run_delay_ms"] == 1500 and ui.exit_at              # Steam no abre otro juego hasta que Hub se cierra
    finally:
        q.close()
        ui.exit_at = None
        ui.cfg["close_on_play"] = True
        del ui._gm


def _pad(ui, items):
    ui.pad_q.clear()
    for b, ts in items:
        ui.pad_q.append((b, ts))


def test_boton_qam_guia_mas_a_no_pulsa(ui, monkeypatch):
    """El botón del QAM llega como guía + A en el mismo informe (A primero, por código): la A no debe pulsar JUGAR."""
    pulsados = []
    monkeypatch.setattr(ui, "press", lambda b, hold=False, now=None: pulsados.append(b))
    monkeypatch.setattr(ui, "_gs_over", lambda: False)
    ui.win_focus, ui.mute_until = True, 0
    ui._mode_ts.clear() if hasattr(ui, "_mode_ts") else None
    t = time.time()
    _pad(ui, [("A", t), ("MODE", t + 0.001)])
    ui.pump()
    assert pulsados == []
    ui.mute_until = 0
    t = time.time()
    _pad(ui, [("A", t)])                           # la guía llega en el siguiente informe
    ui.pump()
    assert pulsados == []                          # la A espera
    ui.pad_q.append(("MODE", t + 0.03))
    time.sleep(0.15)
    ui.pump()
    assert pulsados == []
    ui.mute_until = 0
    ui._mode_ts.clear()
    t = time.time()
    _pad(ui, [("A", t), ("DOWN", t + 0.01)])       # una A sola sí se pulsa (como mucho 0,12 s después), y en orden
    ui.pump()
    time.sleep(0.15)
    ui.pump()
    assert pulsados == ["A", "DOWN"]


def test_clic_del_boton_qam_no_pulsa(ui, monkeypatch):
    """v3.18: en el Modo Juego, el botón del QAM llega como un clic instantáneo: espera 0,25 s y se descarta si se abre un menú."""
    import pygame
    hechos = []
    ui.modal = None
    ui.go_tab("home")
    run(ui, 2)
    w = next(x for x in ui.widgets if x.cb and x.rect.w > 20)
    monkeypatch.setattr(w, "cb", lambda: hechos.append(1))
    monkeypatch.setattr(ui, "_widget_at", lambda pos: w)
    ui._gm, ui.win_focus, ui.mute_until = True, True, 0
    over = [False]
    monkeypatch.setattr(ui, "_gs_over", lambda: over[0])
    try:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1))
        ui.pump()
        assert hechos == []                                     # en espera
        over[0] = True                                          # se abre el QAM encima
        time.sleep(0.3)
        ui.pump()
        assert hechos == []
        over[0] = False
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1))
        ui.pump()
        time.sleep(0.3)
        ui.pump()
        assert hechos == [1]                                    # sin menú encima, se pulsa (con 0,25 s de retraso)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1, touch=True))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1, touch=True))
        ui.pump()
        assert hechos == [1, 1]                                 # el dedo de verdad no espera
    finally:
        del ui._gm
