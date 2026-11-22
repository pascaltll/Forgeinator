"""#path inexistente: completed con un path que no existe → aviso claro, log, y NO se llama a check_file."""
import pytest
pytest.importorskip("pygame")
pytestmark = pytest.mark.ui
from _catui_helpers import make_ui, pump_until, run


@pytest.fixture(scope="module")
def ui():
    return make_ui()


@pytest.fixture
def ent(ui, monkeypatch):
    e = {"id": "sh-ps1", "name": "Silent Hill", "platform": "PlayStation", "variants": []}
    ui.entries.append(e)
    llamadas = []
    monkeypatch.setattr(ui, "check_file", lambda ent, p: llamadas.append(str(p)))
    ui.cjobs.every = 0.05
    ui.toast_msg = ""
    yield e, llamadas
    ui.entries.remove(e)
    for j in list(ui.cjobs.list()):
        ui.cjobs.remove(j.id)


def _lanzar(ui, daemon, e, tmp_path):
    from hub import catalogservice as cs
    cs.search("sh")
    v = cs.variants("nas", "sh1")
    jid = cs.download("nas", v[0]["variant_id"], tmp_path)["job_id"]
    ui.cjobs.add(jid, "Silent Hill.bin", 100, True, e["id"], "nas")


def test_path_que_no_existe(ui, daemon, ent, tmp_path, capsys):
    e, llamadas = ent
    daemon.write_file = False
    _lanzar(ui, daemon, e, tmp_path)
    assert pump_until(ui, lambda: "no existe" in ui.toast_msg)
    assert llamadas == []
    assert "NO existe el archivo" in capsys.readouterr().err


def test_path_que_existe_se_comprueba(ui, daemon, ent, tmp_path):
    e, llamadas = ent
    _lanzar(ui, daemon, e, tmp_path)
    assert pump_until(ui, lambda: len(llamadas) == 1)


def test_path_es_una_carpeta_no_cuenta_como_archivo(ui, daemon, ent, tmp_path):
    e, llamadas = ent
    daemon.job_script = [{"state": "completed", "path": str(tmp_path)}]
    _lanzar(ui, daemon, e, tmp_path)
    assert pump_until(ui, lambda: "carpeta" in ui.toast_msg)
    assert llamadas == []
