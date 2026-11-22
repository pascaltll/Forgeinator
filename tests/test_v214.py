"""v2.14: CANCELAR descarga inmediato, sin duplicados; enlace al juego en windows/; Hub no se cierra con Proton."""
import threading
import time

import pytest

from test_v195 import juego, _t  # noqa: F401
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio  # noqa: F401

pygame = pytest.importorskip("pygame")


def test_cancelar_activa_pasa_a_cancelada_al_instante(tmp_path):
    from hub import downloads
    m = downloads.Manager.__new__(downloads.Manager)
    m.items, m._lock, m._wake = {}, threading.RLock(), threading.Event()
    m.save = lambda: None
    m._rm_part = lambda d: None
    d = downloads.Download("d1", "http://x/y.zip", str(tmp_path), "y.zip", None, {}, 2)
    d.state = "active"
    m.items["d1"] = d
    m.cancel("d1")
    assert d.state == "cancelled" and d._stop.is_set()


def test_hilo_de_una_cancelada_no_la_convierte_en_error(tmp_path, monkeypatch):
    from hub import downloads
    m = downloads.Manager.__new__(downloads.Manager)
    m.items, m._lock, m._wake, m.on_done = {}, threading.RLock(), threading.Event(), None
    m.save = lambda: None
    m._log_err = lambda d: None
    m._rm_part = lambda d: None
    d = downloads.Download("d1", "http://x/y.zip", str(tmp_path), "y.zip", None, {"_cancel": True}, 2)
    d.state = "cancelled"

    def boom(dd):
        raise OSError("conexión cortada")
    m._probe = boom
    m._run(d)
    assert d.state == "cancelled"


def test_enlace_al_juego_dentro_de_windows(juego, ui, tmp_path, monkeypatch):
    from hub import library, osver
    d, toml = juego
    exe = tmp_path / "pc" / "g.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    osver.attach_windows("sh", exe, "proton")
    rom = tmp_path / "roms" / "juego.iso"
    rom.parent.mkdir()
    rom.write_bytes(b"iso")
    e = {"id": "sh", "name": "SH", "launcher_id": "sh"}
    monkeypatch.setattr(library, "link_get", lambda eid: str(rom))
    monkeypatch.setattr(ui, "inst", lambda e: {"launcher_id": "sh"})
    ui._osv.clear()
    t = ui.link_game_win(e)
    assert t and t.is_symlink() and t.resolve() == rom.resolve()
    assert t.parent == d / "windows"
    assert not (exe.parent / "juego.iso").exists(), "no escribe en la carpeta del juego del usuario"
