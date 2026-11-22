"""v2.25: JUGAR deja el enlace a tu ISO también en la carpeta de la versión de Linux."""
import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from hub import library, osver


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    return H.UI()


def test_enlace_en_carpeta_de_linux_y_cwd(ui, tmp_path, monkeypatch):
    iso = tmp_path / "mi.iso"
    iso.write_text("iso")
    proj, cwd = tmp_path / "proj", tmp_path / "proj" / "linux"
    cwd.mkdir(parents=True)
    e = {"id": "gx", "name": "GX", "platform": "PS2"}
    monkeypatch.setattr(library, "link_get", lambda i: str(iso))
    monkeypatch.setattr(ui, "inst", lambda x: {"launcher_id": "gx"})
    monkeypatch.setattr(ui, "os_state", lambda lid: {"split": False, "root": None})
    monkeypatch.setattr(osver, "folders", lambda lid: {"dir": str(proj), "cwd": str(cwd)})
    made = ui.link_game_linux(e)
    assert (proj / "mi.iso").is_symlink() and (cwd / "mi.iso").is_symlink() and len(made) == 2
    assert ui.link_game_linux(e)                      # idempotente
    (cwd / "mi.iso").unlink()
    (cwd / "mi.iso").write_text("real")
    ui.link_game_linux(e)
    assert (cwd / "mi.iso").read_text() == "real", "no pisa archivos reales"
