"""#variant_id desconocido: download falla con ServiceError; Hub avisa, NO reintenta download en bucle y vuelve a pedir variants."""
import pytest
pytest.importorskip("pygame")
pytestmark = pytest.mark.ui
from _catui_helpers import make_ui, pump_until, run


@pytest.fixture(scope="module")
def ui():
    return make_ui()


@pytest.fixture
def ent(ui):
    e = {"id": "sh-ps1", "name": "Silent Hill", "platform": "PlayStation", "variants": []}
    ui.entries.append(e)
    ui.modal, ui.toast_msg = None, ""
    yield e
    ui.entries.remove(e)
    ui.modal = None


def test_desconocido_repite_variants_y_no_reintenta_download(ui, daemon, ent):
    daemon.rpc_errors["download"] = (-32001, "variant_id 'v0' desconocido", None)
    r = {"source": "nas", "item_id": "sh1", "title": "Silent Hill"}
    v = {"variant_id": "v0", "filename": "a.bin", "size": "1 MB"}
    ui.cat_start(ent, r, v)
    assert pump_until(ui, lambda: daemon.count("variants") == 1)
    run(ui, 20)
    assert daemon.count("download") == 1                      # ni un reintento automático
    assert daemon.count("variants") == 1                      # se repitió variants antes de poder volver a bajar
    assert ui.cjobs.list() == []
    assert pump_until(ui, lambda: ui.modal and ui.modal.get("kind") == "choice")


def test_otro_error_no_repite_variants(ui, daemon, ent):
    daemon.rpc_errors["download"] = (-2, "No such file", None)
    ui.cat_start(ent, {"source": "nas", "item_id": "sh1"}, {"variant_id": "v0", "filename": "a.bin"})
    assert pump_until(ui, lambda: daemon.count("download") == 1)
    run(ui, 15)
    assert daemon.count("variants") == 0 and daemon.count("download") == 1


def test_mkdir_de_descargas_falla_avisa_y_no_mata_el_hilo(ui, daemon, ent, monkeypatch):
    from pathlib import Path
    def boom(self, *a, **k):
        raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(Path, "mkdir", boom)
    ui.cat_start(ent, {"source": "nas", "item_id": "sh1"}, {"variant_id": "v0", "filename": "a.bin"})
    assert pump_until(ui, lambda: "carpeta de descargas" in ui.toast_msg)
    assert daemon.count("download") == 0
