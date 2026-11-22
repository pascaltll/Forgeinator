"""v2.34: selector de temas en cuadrícula (una miniatura por tema, un toque) y fundido al cambiar."""
import pytest

pygame = pytest.importorskip("pygame")


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.set_look(theme="dark", fx="glass")


def run(u, n=3):
    for _ in range(n):
        u.frame()


def test_cuadricula_con_todos_los_temas(ui):
    import hub.ui as H
    ui.set_look(theme="dark", fx="glass")
    ui.tab, ui.set_page = "settings", "look"
    run(ui)
    ks = {w.key for w in ui.widgets}
    assert {f"theme:{t}" for t in H.THEME_ORDER} <= ks
    assert "theme_prev" not in ks and "theme_next" not in ks


def test_tocar_una_miniatura_cambia_el_tema_con_fundido(ui):
    import hub.ui as H
    ui.set_look(theme="dark", fx="glass")
    ui.pick_theme("neon")
    assert ui.cfg["theme"] == "neon" and "_xfade" in ui.__dict__
    run(ui, 2)
    ui.pick_theme("neon")                      # el mismo: no hace nada
    assert ui.cfg["theme"] == "neon"
    ui.pick_theme("inventado")
    assert ui.cfg["theme"] == "neon"


def test_sin_fundido_en_rendimiento(ui):
    ui.set_look(theme="dark", fx="perf")
    ui.__dict__.pop("_xfade", None)
    ui.pick_theme("brasa")
    assert "_xfade" not in ui.__dict__ and ui.cfg["theme"] == "brasa"
    ui.set_look(theme="dark", fx="glass")


@pytest.mark.parametrize("theme", ["dark", "tinta", "bloque", "fosforo"])
def test_cuadricula_se_dibuja_sin_errores(ui, theme):
    ui.set_look(theme=theme, fx="glass")
    ui.tab, ui.set_page = "settings", "look"
    run(ui, 4)
    ui.resize(1280, 720)
    run(ui, 2)
    ui.resize(1920, 1080)
    run(ui, 2)
