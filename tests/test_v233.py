"""v2.33: «Pasar al escritorio» no se bloquea ni pierde el motivo; hub-run.sh de Proton respeta .proton-log."""
import os
import stat
import subprocess

from hub import config, osver, steamsetup


def _tool(tmp_path, body):
    t = tmp_path / "steamos-session-select"
    t.write_text("#!/bin/sh\n" + body + "\n")
    t.chmod(t.stat().st_mode | stat.S_IXUSR)
    return str(t)


def test_select_lento_cuenta_como_en_marcha(tmp_path):
    t = _tool(tmp_path, "sleep 5")
    ok, how = steamsetup._select(t, "plasma", wait=0.5)
    assert ok and "trabajando" in how


def test_select_error_guarda_motivo(tmp_path):
    t = _tool(tmp_path, "echo 'no tienes permiso' >&2; exit 3")
    ok, how = steamsetup._select(t, "plasma", wait=3)
    assert not ok and "código 3" in how and "no tienes permiso" in how
    assert "no tienes permiso" in (config.DATA / "session-select.log").read_text()


def test_to_desktop_prueba_otros_destinos(tmp_path, monkeypatch):
    t = _tool(tmp_path, '[ "$1" = desktop ] && exit 0; exit 1')
    monkeypatch.setattr(steamsetup, "session_tool", lambda: t)
    monkeypatch.setattr(steamsetup, "write_autostart", lambda *a, **k: None)
    ok, m = steamsetup.to_desktop()
    assert ok and "desktop" in m


def test_to_desktop_fallo_muestra_motivo(tmp_path, monkeypatch):
    t = _tool(tmp_path, "echo boom >&2; exit 1")
    monkeypatch.setattr(steamsetup, "session_tool", lambda: t)
    monkeypatch.setattr(steamsetup, "write_autostart", lambda *a, **k: None)
    monkeypatch.setattr(steamsetup, "clear_autostart", lambda *a, **k: None)
    ok, m = steamsetup.to_desktop()
    assert not ok and "boom" in m


def test_runner_proton_respeta_proton_log(tmp_path):
    txt = osver.runner_text("GoWLauncher.exe", "GE-Proton")
    assert ".proton-log" in txt and "PROTON_LOG=1" in txt
    (tmp_path / "windows").mkdir()
    (tmp_path / ".proton-log").write_text("1")
    r = tmp_path / "windows" / "hub-run.sh"
    r.write_text(txt.replace("exec umu-run", "echo LOG=$PROTON_LOG_DIR; echo"))
    out = subprocess.run(["/bin/sh", str(r)], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout
    assert "proton-logs" in out
