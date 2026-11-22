"""v2.32: efectos en todos los temas (fondo animado, destello al pulsar, halo, salto de icono), sonidos por tema y tema anterior/siguiente."""
import time

import pytest

from hub import sfx


def test_cada_timbre_suena_distinto_y_corto():
    base = sfx.synth("soft")
    for p in ("glass", "chip", "wood"):
        g = sfx.synth(p)
        assert set(g) == set(sfx.NAMES) and all(g[k] != base[k] for k in g), p
        assert all(len(v) / 2 / sfx.RATE < 0.5 for v in g.values()), "ninguno pasa de medio segundo"
    assert sfx.synth("no-existe") == base


def test_cambiar_de_timbre_sin_audio_no_rompe():
    s = sfx.Sfx(True, 0.5)
    s.set_profile("chip")
    assert s.profile == "chip"
    s.set_profile("raro")
    assert s.profile == "soft"


pygame = pytest.importorskip("pygame")
pytestmark_ui = pytest.mark.ui


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.set_look(theme="dark", fx="glass")


def run(u, n=3):
    for _ in range(n):
        u.frame()
        time.sleep(0.01)


@pytest.mark.ui
def test_todos_los_temas_tienen_fondo_animado_y_timbre(ui):
    import hub.ui as H
    for th in H.THEME_ORDER:
        ui.set_look(theme=th, fx="glass")
        assert H.ANIM or th == "obsidian", f"{th} sin fondo animado"      # Obsidian: fondo liso por diseño (v2.93)
        assert H.SND in sfx.PROFILES and ui.sfx.profile == H.SND
        for tab in ("home", "settings"):
            ui.go_tab(tab)
            run(ui)


@pytest.mark.ui
def test_tema_anterior_y_siguiente_dan_la_vuelta(ui):
    import hub.ui as H
    ui.set_look(theme=H.THEME_ORDER[0])
    ui.toggle_theme(-1)
    assert ui.cfg["theme"] == H.THEME_ORDER[-1]
    ui.toggle_theme(1)
    assert ui.cfg["theme"] == H.THEME_ORDER[0]
    ui.go_tab("settings")
    ui.set_page = "look"
    run(ui)
    keys = {w.key for w in ui.widgets}
    assert {f"theme:{t}" for t in H.THEME_ORDER} <= keys
    ui.set_page = None


@pytest.mark.ui
def test_pulsar_deja_un_destello_y_no_cambia_la_accion(ui):
    ui.set_look(theme="neon", fx="glass")
    ui.go_tab("home")
    run(ui)
    hecho = []

    class W:
        rect, cb = pygame.Rect(100, 100, 300, 80), staticmethod(lambda: hecho.append(1) or "ret")
    assert ui.fire(W) == "ret" and hecho == [1] and len(ui._bursts) == 1
    run(ui, 2)
    time.sleep(0.5)
    run(ui, 1)
    assert ui._bursts == [], "el destello se apaga solo"
    ui.set_look(fx="perf")
    ui.fire(W)
    assert ui._bursts == [] and hecho == [1, 1], "en «rendimiento» no hay destello, pero la acción se hace"
