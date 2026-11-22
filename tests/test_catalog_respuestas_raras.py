"""Respuestas raras del daemon (result null, tipos inesperados) no matan el hilo: hay aviso. Y reload() invalida la caché de instalados."""
import time
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


@pytest.mark.parametrize("valor", [None, 5, "texto"])
def test_search_con_resultado_raro(ui, daemon, ent, valor):
    daemon.results["search"] = valor
    ui.toast_msg = ""
    ui.cat_open(ent)
    assert pump_until(ui, lambda: daemon.count("search") == 1 and ("inesperada" in ui.toast_msg or "no encontró nada" in ui.toast_msg))


def test_search_con_confidence_no_numerica(ui, daemon, ent):
    daemon.results["search"] = [{"source": "nas", "item_id": "x", "title": "t", "confidence": "alta"}]
    ui.toast_msg = ""
    ui.cat_open(ent)
    assert pump_until(ui, lambda: "inesperada" in ui.toast_msg)


@pytest.mark.parametrize("valor", [None, {"a": 1}, 7])
def test_variants_con_resultado_raro(ui, daemon, ent, valor):
    daemon.results["variants"] = valor
    ui.toast_msg = ""
    ui.cat_variants(ent, {"source": "nas", "item_id": "sh1", "title": "t"})
    assert pump_until(ui, lambda: "inesperada" in ui.toast_msg or "no tiene variantes" in ui.toast_msg)


def test_reload_invalida_cache_y_descarta_refresco_en_vuelo(ui):
    ui._inst_c = (time.time(), {"viejo": 1})
    g0 = getattr(ui, "_inst_gen", 0)
    ui.reload()
    assert ui._inst_c is None and ui._inst_gen == g0 + 1


@pytest.mark.parametrize("valor", [None, 3, {"a": 1}])
def test_health_raro_no_impide_buscar(ui, daemon, ent, valor):
    daemon.results["health"] = valor
    ui.toast_msg = ""
    ui.cat_open(ent)
    assert pump_until(ui, lambda: daemon.count("search") >= 1)
    assert pump_until(ui, lambda: ui.modal and ui.modal.get("kind") == "choice")
    ui.modal = None


def test_refresh_health_con_null_no_lanza(ui, daemon):
    ui.cat_hb, ui.cat_hb_t = False, 0
    daemon.results["health"] = None
    ui.cat_health = {"nas": "OK"}
    ui.cat_refresh_health()
    assert pump_until(ui, lambda: ui.cat_hb is False and daemon.count("health") >= 1)
    assert ui.cat_health == {"nas": "OK"}
