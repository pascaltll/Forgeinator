"""v3.22 · Bibliotecas remotas con rclone: un servidor WebDAV de verdad (rclone serve webdav) en local, con usuario y contraseña."""
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from hub import config, remote

pytestmark = pytest.mark.skipif(not remote.rclone_bin(), reason="sin rclone")


def _port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture
def dav(tmp_path):
    srv = tmp_path / "srv"
    (srv / "roms/psx").mkdir(parents=True)
    (srv / "roms/n64").mkdir(parents=True)
    (srv / "roms/cosas").mkdir(parents=True)                          # no es un sistema: no sale
    (srv / "roms/psx/Crash Team Racing (USA).chd").write_bytes(os.urandom(300_000))
    (srv / "roms/psx/leeme.txt").write_text("no es un juego")
    (srv / "roms/psx/Final Fantasy VII (USA)").mkdir()
    (srv / "roms/psx/Final Fantasy VII (USA)/disc1.chd").write_bytes(b"1" * 1000)
    (srv / "roms/psx/Final Fantasy VII (USA)/FF7.m3u").write_text("disc1.chd\n")
    (srv / "roms/n64/Mario 64 (USA).z64").write_bytes(b"z" * 5000)
    port = _port()
    p = subprocess.Popen([remote.rclone_bin(), "serve", "webdav", str(srv), "--addr", f"127.0.0.1:{port}", "--user", "carlos", "--pass", "s3cr'eto"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", srv
    p.terminate()
    p.wait(timeout=10)


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "CONFIG", tmp_path / "conf")
    roms = tmp_path / "Games/roms"
    roms.mkdir(parents=True)
    return {"rom_dirs": [str(roms)]}, roms


def test_webdav_explorar_y_descargar(dav, lib, tmp_path):
    url, srv = dav
    cfg, roms = lib
    s = remote.add("webdav", "Mi NAS", {"url": url, "user": "carlos", "pass": "s3cr'eto"})
    assert "s3cr" not in (config.DATA / "remotes.json").read_text()                 # sin secretos en la biblioteca
    sec = config.CONFIG / "remotes-secrets.json"
    assert (sec.stat().st_mode & 0o777) == 0o600 and "s3cr'eto" not in sec.read_text()   # oscurecida y privada
    assert [x["system"] for x in remote.systems(s)] == ["n64", "psx"]
    assert "2 sistemas" in remote.test(s)
    gs = remote.games(s, "psx", "psx")
    assert [g["name"] for g in gs] == ["Crash Team Racing (USA).chd", "Final Fantasy VII (USA)"]   # leeme.txt fuera
    seen = []
    d = remote.download(s, gs[0], "psx", progress=lambda *a: seen.append(a), cfg=cfg)
    assert d == roms / "psx/Crash Team Racing (USA).chd" and d.read_bytes() == (srv / "roms/psx/Crash Team Racing (USA).chd").read_bytes()
    d2 = remote.download(s, gs[1], "psx", cfg=cfg)                                  # juego de varios archivos (carpeta)
    assert sorted(p.name for p in d2.iterdir()) == ["FF7.m3u", "disc1.chd"]
    with pytest.raises(remote.RemoteError, match="Ya tienes"):
        remote.download(s, gs[0], "psx", cfg=cfg)                                  # nunca pisa


def test_contrasena_mala_y_servidor_caido(dav, lib):
    url, _ = dav
    s = remote.add("webdav", "Mal", {"url": url, "user": "carlos", "pass": "otra"})
    with pytest.raises(remote.RemoteError, match="usuario o la contraseña|rechaz"):
        remote.systems(s)
    s2 = remote.add("webdav", "Caido", {"url": "http://127.0.0.1:9", "user": "x", "pass": "y"})
    with pytest.raises(remote.RemoteError):
        remote.systems(s2)


def test_local_y_borrar(lib, tmp_path):
    src = tmp_path / "usb"
    (src / "roms/gba").mkdir(parents=True)
    (src / "roms/gba/Zelda.gba").write_bytes(b"g" * 100)
    s = remote.add("local", "USB", {"path": str(src)})
    assert [x["system"] for x in remote.systems(s)] == ["gba"]
    assert [x["id"] for x in remote.sources()] == [s["id"]]
    remote.remove(s["id"])
    assert remote.sources() == []


def test_cadena_de_conexion_escapa_comillas(lib):
    s = remote.add("sftp", "Casa", {"host": "nas.local", "user": "o'brien", "port": "2222"})
    spec = remote.remote_spec(s, "psx/a b.chd")
    assert spec == ":sftp,host='nas.local',port='2222',user='o''brien':roms/psx/a b.chd"


def test_interfaz_anadir_explorar_bajar(dav, lib, monkeypatch):
    from test_temas_y_fuzz import H, run  # noqa: F401
    import hub.ui as U
    ui = U.UI.__new__(U.UI)
    cfg, roms = lib
    ui.cfg = cfg
    ui.modal = ui.focus = None
    ui._io_gen = 0
    msgs = []
    ui.toast = msgs.append
    ui.use_steam_kb = lambda: False
    ui.lib_loaded = True
    url, _ = dav

    def wait(cond, t=20):
        t0 = time.time()
        while not cond() and time.time() - t0 < t:
            q = ui.__dict__.get("_uiq")
            while q:
                q.pop(0)()
            time.sleep(0.05)
        assert cond(), msgs[-3:]

    def pick(prefix):
        opts = dict(ui.modal["options"])
        k = next(k for k in opts if k.startswith(prefix))
        ui.modal = None
        opts[k]()

    def type_(text):
        m = ui.modal
        assert m["kind"] == "osk"
        ui.modal = None
        m["cb"](text)

    ui.remotes_menu()
    pick("+ AÑADIR")
    pick("WEBDAV")
    type_(url)
    type_("carlos")
    type_("s3cr'eto")
    type_("roms")
    type_("NAS de casa")
    wait(lambda: any("guardada" in m for m in msgs))
    assert "2 sistemas" in msgs[-1]
    ui.remotes_menu()
    pick("NAS DE CASA")
    wait(lambda: ui.modal and ui.modal.get("kind") == "choice" and "sistemas" in ui.modal.get("msg", ""))
    pick("PSX")
    wait(lambda: ui.modal and "juegos" in ui.modal.get("msg", ""))
    pick("Crash Team Racing")
    wait(lambda: not ui._rdl["busy"])
    assert (roms / "psx/Crash Team Racing (USA).chd").exists() and "ya está en tu biblioteca" in msgs[-1]
    assert ui.lib_loaded is False
