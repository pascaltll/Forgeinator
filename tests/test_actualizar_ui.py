"""v1.81: Ajustes muestra la versión y el resultado de la última actualización; botón y ajuste automático."""
import json

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    u._upd_first.wait(10)             # que el primer sondeo real termine antes de simular los nuestros
    yield u
    u.running = False


def test_version_visible_y_ultimo_resultado(ui):
    from hub import config
    assert config.VERSION not in ("", "?")
    f = config.DATA / "update.json"
    antes = f.read_text() if f.exists() else None
    try:
        f.write_text(json.dumps({"ok": True, "from": "1.80", "to": "1.81", "when": "2026-11-08T16:00:00"}))
        assert "1.80 → 1.81" in ui._last_update_txt()
        f.write_text(json.dumps({"ok": False, "from": "1.80", "to": "1.81", "when": "x"}))
        assert "falló" in ui._last_update_txt()
    finally:
        f.unlink(missing_ok=True)
        if antes:
            f.write_text(antes)


def test_toggle_autoupdate(ui):
    a = ui.cfg.get("auto_update", True)
    ui.toggle_autoupdate()
    assert ui.cfg["auto_update"] is (not a)
    ui.toggle_autoupdate()
    assert ui.cfg["auto_update"] is a


def _keys(ui):
    return [getattr(w, "key", None) for w in ui.widgets]


def test_aviso_aparece_con_zip_pendiente_y_desaparece_sin_el(ui, monkeypatch):
    import hub.selfupdate as su
    from _catui_helpers import run
    monkeypatch.setattr(su, "probe", lambda *a, **k: {"current": "1.0", "new": "9.9", "file": "/x.zip"})
    ui.modal = None
    ui.upd_check()
    run(ui, 2)
    assert ui.upd_ready == {"ver": "9.9", "file": "/x.zip"} and "updgo" in _keys(ui)
    monkeypatch.setattr(su, "probe", lambda *a, **k: {"current": "9.9", "new": None, "file": None})
    ui.upd_check()
    run(ui, 2)
    assert ui.upd_ready is None and "updgo" not in _keys(ui)


def test_un_toque_instala_y_reinicia(ui, monkeypatch):
    import hub.selfupdate as su
    from _catui_helpers import pump_until
    llamadas = []
    monkeypatch.setattr(su, "apply", lambda *a, **k: (True, "✓ Recomp Hub 1.0 → 9.9"))
    monkeypatch.setattr(su, "restart", lambda: llamadas.append("restart"))
    ui.upd_ready, ui.upd_busy = {"ver": "9.9", "file": "/x.zip"}, ""
    ui.running = True
    ui.upd_now()
    assert pump_until(ui, lambda: ui.running is False, 5)
    assert llamadas == ["restart"] and "reiniciando" in ui.upd_busy
    ui.running, ui.upd_busy, ui.upd_ready = True, "", None


def test_si_falla_no_reinicia_y_avisa(ui, monkeypatch):
    import hub.selfupdate as su
    from _catui_helpers import pump_until
    monkeypatch.setattr(su, "apply", lambda *a, **k: (False, "✗ falló (roto); restauré la versión 1.0"))
    monkeypatch.setattr(su, "restart", lambda: (_ for _ in ()).throw(AssertionError("no debe reiniciar")))
    ui.upd_ready, ui.upd_busy, ui.toast_msg = {"ver": "9.9", "file": "/x.zip"}, "", ""
    ui.upd_now()
    assert pump_until(ui, lambda: "No se pudo actualizar" in ui.toast_msg, 5)
    assert ui.upd_busy == "" and ui.running
    ui.upd_ready = None


def test_ajustes_sin_novedad_dice_que_esta_al_dia(ui, monkeypatch):
    import hub.selfupdate as su
    from _catui_helpers import pump_until
    monkeypatch.setattr(su, "probe", lambda *a, **k: {"current": "1.0", "new": None})
    ui.upd_ready, ui.toast_msg = None, ""
    ui.update_hub()
    assert pump_until(ui, lambda: "al día" in ui.toast_msg, 5)


def test_probe_real_lee_json_de_hub_update(tmp_path, monkeypatch):
    import json, subprocess, sys
    from conftest import HUB_SRC
    home = tmp_path / "home"
    (home / "Games" / "actualizaciones").mkdir(parents=True)
    (home / "Games" / "actualizaciones" / "install-hub-v9.9.sh").write_text("#!/bin/bash\n")
    r = subprocess.run([sys.executable, str(HUB_SRC / "bin" / "hub-update"), "--json"], capture_output=True, text=True,
                       env={"HOME": str(home), "HUB_DIR": str(HUB_SRC), "PATH": "/usr/bin:/bin"})
    d = json.loads(r.stdout)
    assert d["new"] == "9.9" and d["file"].endswith("install-hub-v9.9.sh")
