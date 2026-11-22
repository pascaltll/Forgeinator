"""v2.91 · protocolo appearance-request.json: validar, aplicar, confirmar en appearance.json; errores al log."""
import json, os, sys
from pathlib import Path
import pytest
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from conftest import HUB_SRC  # noqa: E402
sys.path.insert(0, str(HUB_SRC))
from hub.themes import appearance_request as ar


def req(**ch):
    return {"schema_version": 1, "request_id": "r1", "changes": ch}


def test_validar_peticion_buena():
    ok, errs, ch = ar.validate(req(theme="neon", palette="lima", background="stars"), ("limpio", "oscuro", None))
    assert ok and not errs and ch == {"theme": "neon", "palette": "lima", "background": "stars"}


@pytest.mark.parametrize("r,frag", [
    ({"schema_version": 2, "request_id": "a", "changes": {"theme": "neon"}}, "schema_version"),
    ({"schema_version": 1, "changes": {"theme": "neon"}}, "request_id"),
    ({"schema_version": 1, "request_id": "a", "changes": {}}, "changes"),
    (req(theme="inventado"), "tema desconocido"),
    (req(theme="neon", palette="gameboy"), "no es del tema"),
    (req(theme="neon", background="aurora"), "no existe"),
    (req(theme="neon", colores={"BG": [0, 0, 0]}), "no soportado"),
    ([1, 2], "objeto"),
])
def test_rechazos(r, frag):
    ok, errs, ch = ar.validate(r, ("limpio", "oscuro", None))
    assert not ok and ch == {} and any(frag in e for e in errs), errs


@pytest.fixture
def hub(tmp_path, monkeypatch):
    from hub import ui, config
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "save_settings", lambda cfg: None)
    class U:
        cfg = {"theme": "limpio", "pals": {}, "bgs": {}}
        _pal = lambda s: ui.PAL
        _bg = lambda s: None
        _layout = lambda s: None
        k0 = 1.0
        _look_norm = lambda s: None
        _publish_look = ui.UI._publish_look
        _ar_load_last = ui.UI._ar_load_last
        poll_appearance_request = ui.UI.poll_appearance_request
        def set_look(s, theme=None, fx=None, pal=None, bg=None, layout=None):
            if theme:
                s.cfg["theme"] = theme
            if pal:
                s.cfg["pals"][s.cfg["theme"]] = pal
            ui.apply_theme(s.cfg["theme"], pal)
            s._publish_look()
    return U(), tmp_path


def _write(d, r):
    p = d / "appearance-request.json"
    p.write_text(json.dumps(r))
    st = p.stat(); os.utime(p, (st.st_atime, st.st_mtime + 5))


def test_hub_aplica_y_confirma(hub):
    u, d = hub
    _write(d, req(theme="neon", palette="lima"))
    r = u.poll_appearance_request(force=True)
    assert r == {"id": "r1", "status": "applied", "errors": []}
    j = json.loads((d / "appearance.json").read_text())
    assert j["family"] == "neon" and j["request"]["status"] == "applied" and j["request"]["id"] == "r1"


def test_hub_rechaza_sin_cambiar_nada(hub, capsys):
    u, d = hub
    _write(d, req(theme="neon", palette="gameboy"))
    r = u.poll_appearance_request(force=True)
    assert r["status"] == "rejected" and u.cfg["theme"] == "limpio"
    assert json.loads((d / "appearance.json").read_text())["request"]["status"] == "rejected"
    assert "[apariencia]" in capsys.readouterr().err


def test_hub_json_roto_se_rechaza(hub):
    u, d = hub
    p = d / "appearance-request.json"; p.write_text("{no json")
    r = u.poll_appearance_request(force=True)
    assert r["status"] == "rejected" and "ilegible" in r["errors"][0]


def test_peticion_repetida_y_reinicio_no_reaplican(hub):
    u, d = hub
    _write(d, req(theme="neon", palette="lima"))
    assert u.poll_appearance_request(force=True)["status"] == "applied"
    u.cfg["theme"] = "limpio"                                   # el usuario cambia a mano
    _write(d, req(theme="neon", palette="lima"))                # el fichero se reescribe con el MISMO id
    assert u.poll_appearance_request(force=True)["status"] == "duplicate" and u.cfg["theme"] == "limpio"
    u.__dict__.pop("_ar_last"); u.__dict__.pop("_ar_mt")        # «reinicio»: se recupera el id desde appearance.json
    u._publish_look()                                           # v2.96: al arrancar el Hub publica ANTES de mirar peticiones
    assert json.loads((d / "appearance.json").read_text())["request"]["id"] == "r1"
    _write(d, req(theme="neon", palette="lima"))
    assert u.poll_appearance_request(force=True)["status"] == "duplicate" and u.cfg["theme"] == "limpio"


def test_sin_fichero_no_hace_nada(hub):
    u, d = hub
    assert u.poll_appearance_request(force=True) is None


def test_error_de_publicacion_va_al_log_y_no_rompe(hub, monkeypatch, capsys):
    from hub import config
    u, d = hub
    monkeypatch.setattr(config, "DATA", d / "no" / "existe" / "x")
    monkeypatch.setattr("hub.themes.publish.publish", lambda *a, **k: (_ for _ in ()).throw(PermissionError("denegado")))
    u._publish_look()
    assert "no se pudo publicar" in capsys.readouterr().err
