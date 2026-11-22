"""v2.29: JUGAR avisa si el ejecutable del launcher no existe y ofrece corregirlo; botón CONFIGURAR para ports con «…-setup»."""
import tomllib

import pytest

from hub import config, install

ELF = b"\x7fELF" + b"\0" * 60


def _x(p, data=ELF):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    p.chmod(0o755)
    return p


def test_setup_exe_encuentra_el_configurador(tmp_path):
    _x(tmp_path / "BT4decomp" / "BT4decomp")
    s = _x(tmp_path / "BT4decomp" / "BT4decomp-setup")
    assert install.setup_exe(tmp_path) == str(s)
    assert install.find_executable(tmp_path) == "BT4decomp/BT4decomp", "el configurador nunca es el ejecutable del juego"


def test_setup_exe_ignora_guiones_y_no_ejecutables(tmp_path):
    _x(tmp_path / "juego")
    _x(tmp_path / "install-setup", b"#!/bin/sh\n")
    (tmp_path / "otro-setup").write_bytes(ELF)
    (tmp_path / "otro-setup").chmod(0o644)
    assert install.setup_exe(tmp_path) == ""


pygame = pytest.importorskip("pygame")


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    return H.UI()


@pytest.mark.ui
def test_jugar_avisa_y_corrige_si_falta_el_ejecutable(ui, tmp_path, monkeypatch):
    g, l = tmp_path / "Games", tmp_path / "launcher"
    (l / "games").mkdir(parents=True)
    (l / "bin").mkdir()
    (l / "bin" / "play").write_text("#!/bin/sh\n")
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", l)
    e = {"id": "bt4x", "name": "BT4 X", "repo": "u/bt4x", "platform": "PC"}
    d = g / "bt4x"
    _x(d / "BT4decomp" / "BT4decomp")
    install.register(e, d, "BT4decomp", "a.zip", "v1")          # el .toml apunta a la raíz; el binario está en la subcarpeta
    monkeypatch.setattr(ui, "inst", lambda x: {"launcher_id": "bt4x", "installed": True, "dir": str(d), "version": "v1"})
    ui.modal, ui.exit_at, ui.play_pr = None, 0, None
    assert ui._exe_missing(e, "bt4x") is True
    assert ui.modal and ui.modal["kind"] == "choice" and "BT4decomp/BT4decomp" in ui.modal["msg"]
    monkeypatch.setattr(ui, "play", lambda x: None)
    ui.modal["options"][0][1]()
    t = tomllib.loads((l / "games" / "bt4x.toml").read_text())
    assert t["run"]["exe"] == "BT4decomp/BT4decomp" and t["run"]["cwd"] == "BT4decomp", "sigue arrancando junto a su ejecutable"
    assert ui._exe_missing(e, "bt4x") is False
