"""Flujo de Quiver en la UI real: buscar → elegir → release verificada → descarga con SHA-256 en el gestor de Hub."""
import pytest
pytest.importorskip("pygame")
pytestmark = pytest.mark.ui
from _catui_helpers import make_ui, pump_until, run
from fakes.quiver import FakeQuiver
from hub import quiversrc as q


@pytest.fixture(scope="module")
def ui():
    return make_ui()


@pytest.fixture
def fq(monkeypatch):
    f = FakeQuiver()
    monkeypatch.setattr(q, "BASE", f.url)
    monkeypatch.setattr(q, "FALLBACK", "")
    monkeypatch.setattr(q, "_MIN_GAP", 0)
    q._cache.clear()
    yield f
    f.stop()


@pytest.fixture
def ent(ui, monkeypatch):
    e = {"id": "banjo-kazooie", "name": "Banjo-Kazooie", "platform": "N64", "repo": "BanjoRecomp/BanjoRecomp", "variants": []}
    ui.entries.append(e)
    ui.modal, ui.toast_msg = None, ""
    anadidas = []
    monkeypatch.setattr(ui.mgr, "add", lambda url, d, **k: anadidas.append((url, k)))
    yield e, anadidas
    ui.entries.remove(e)
    ui.modal = None


def test_buscar_muestra_resultados(ui, fq, ent):
    e, _ = ent
    ui.quiver_open(e)
    assert pump_until(ui, lambda: ui.modal and ui.modal.get("kind") == "choice")
    assert ui.modal["title"] == "Resultados en Quiver" and len(ui.modal["options"]) == 2


def test_sin_resultados_avisa(ui, fq, ent, monkeypatch):
    e, _ = ent
    monkeypatch.setattr(q, "search", lambda *a, **k: [])
    ui.quiver_open(e)
    assert pump_until(ui, lambda: "no tiene nada" in ui.toast_msg)


def test_elegir_descarga_el_archivo_linux_con_sha256(ui, fq, ent):
    e, anadidas = ent
    ui.quiver_pick(e, {"slug": "banjokazooie-banjorecompiled"})
    assert pump_until(ui, lambda: anadidas)
    url, k = anadidas[0]
    assert url.endswith("Linux-X64.tar.gz") and k["sha256"] == "cd" * 32 and k["name"].endswith("Linux-X64.tar.gz")
    assert k["meta"]["install"] == e["id"] and k["meta"]["version"] == "v1.0.2" and k["meta"]["source"] == "quiver"


def test_repositorio_distinto_pide_confirmacion_y_no_descarga(ui, fq, ent):
    e, anadidas = ent
    fq.repo = "otro/proyecto"
    ui.quiver_pick(e, {"slug": "x"})
    assert pump_until(ui, lambda: ui.modal and ui.modal.get("kind") == "confirm")
    assert anadidas == []
    ui.modal["cb"]()
    assert len(anadidas) == 1


def test_sin_build_de_linux_avisa(ui, fq, ent):
    e, anadidas = ent
    fq.assets = []
    ui.quiver_pick(e, {"slug": "x"})
    assert pump_until(ui, lambda: "Linux x86_64" in ui.toast_msg)
    assert anadidas == []


def test_error_de_red_avisa_sin_morir(ui, ent, monkeypatch):
    e, anadidas = ent
    monkeypatch.setattr(q, "BASE", "http://127.0.0.1:1/api/v1")
    monkeypatch.setattr(q, "FALLBACK", "")
    q._cache.clear()
    ui.quiver_open(e)
    assert pump_until(ui, lambda: "Quiver:" in ui.toast_msg)


def test_no_duplica_si_ya_se_descarga(ui, fq, ent, monkeypatch):
    e, anadidas = ent
    class D: meta = {"install": "banjo-kazooie"}; state = "active"
    monkeypatch.setattr(ui.mgr, "list", lambda: [D()])
    ui.quiver_start(e, {"slug": "x"}, "v1", {"url": "u", "name": "n", "sha256": None})
    assert anadidas == [] and "Ya se está" in ui.toast_msg


def test_sin_sha256_lo_dice(ui, fq, ent):
    e, anadidas = ent
    ui.quiver_start(e, {"slug": "x"}, "v1", {"url": "u", "name": "n", "sha256": None})
    assert "SHA-256" in ui.toast_msg and anadidas[0][1]["sha256"] is None


def test_la_ficha_dibuja_el_boton_de_quiver(ui, fq, ent):
    e, _ = ent
    ui.open_detail(e)
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = "versiones"
    run(ui, 6)
    assert any(getattr(w, "key", None) == "quiver" for w in ui.widgets)
    ui.go_tab("games")
