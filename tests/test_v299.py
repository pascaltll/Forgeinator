"""v2.99: el selector Linux/Windows vuelve a la vista principal de la ficha (estaba ahí en v2.44)."""
from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from hub import github, osver

A = [{"name": "ReStreet-linux-x64.zip", "size": 9, "browser_download_url": "u1"}, {"name": "FifaStreetSetup.exe", "size": 9, "browser_download_url": "u2"}]


def _ficha(ui, monkeypatch, st):
    e = ui.entries[0]
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="v1.3", launcher_id="fifa", dir="/tmp/fifa") if x is e else real(x))
    ui._inst_c = None
    ui.rel[ui.rk(e)] = github._view({"tag_name": "v1.3", "assets": A}, {"error": "", "stale": False}, "x86_64", "")
    monkeypatch.setattr(ui, "fetch", lambda *a, **k: None)
    monkeypatch.setattr(ui, "os_state", lambda lid: st)
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/" + n)
    ui.modal = None
    ui.more_open.discard(e["id"])
    ui.go_tab("games")
    ui.open_detail(e)
    run(ui, 3)
    return e


def test_selector_en_la_vista_principal_y_cambia(ui, monkeypatch):
    st = {"root": None, "split": True, "active": "windows", "linux": True, "windows": True, "meta": {}}
    _ficha(ui, monkeypatch, st)
    ks = {w.key: w for w in ui.widgets}
    assert "os_linux" in ks and "os_windows" in ks and "more" in ks
    assert ks["os_linux"].rect.bottom <= ks["more"].rect.top
    hechos = []
    monkeypatch.setattr(osver, "set_active", lambda lid, wh: hechos.append(wh))
    ks["os_linux"].cb()
    assert hechos == ["linux"]


def test_sin_windows_instalado_ofrece_el_instalador(ui, monkeypatch):
    st = {"root": None, "split": False, "active": "linux", "linux": True, "windows": False, "meta": {}}
    _ficha(ui, monkeypatch, st)
    w = next(w for w in ui.widgets if w.key == "os_windows")
    w.cb()
    assert ui.modal and "Instalador" in ui.modal.get("title", "")
    ui.modal = None


def test_tarjeta_versiones_estados_y_acciones(ui, monkeypatch, tmp_path):
    """v3.02: cada fila dice qué es, en qué estado está y una sola acción."""
    from hub import config
    st = {"root": None, "split": False, "active": "linux", "linux": True, "windows": False, "meta": {}}
    monkeypatch.setattr(config, "path", lambda k: tmp_path)
    textos = []
    real_text = ui.text
    monkeypatch.setattr(ui, "text", lambda s, *a, **k: (textos.append(str(s)), real_text(s, *a, **k))[1])
    e = _ficha(ui, monkeypatch, st)
    w = {x.key: x for x in ui.widgets}
    assert "VERSIONES DE ESTE JUEGO" in textos and "JUGAR abre: Linux" in textos
    assert any(t.startswith("sin instalar") and "instalador" in t for t in textos)
    (tmp_path / "FifaStreetSetup.exe").write_bytes(b"x" * 9)         # ya descargado → «ABRIR INSTALADOR», sin volver a bajar
    textos.clear()
    run(ui, 2)
    assert "instalador descargado · sin instalar" in textos


def test_xalia_apagada_en_el_instalador():
    from pathlib import Path
    assert "PROTON_USE_XALIA=0" in osver.installer_runner_text(Path("/d/S.exe"), "/p")
