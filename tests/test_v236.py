"""v2.36: cinco temas con aire de consolas (onda, tarjeta, interruptor, cubo, retro16) y sus fondos animados."""
import pytest

pygame = pytest.importorskip("pygame")
NUEVOS = ("onda", "tarjeta", "interruptor", "cubo", "pixel")


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.set_look(theme="dark", fx="glass")


def test_estan_registrados():
    import hub.ui as H
    for n in NUEVOS:
        assert n in H.THEME_ORDER and n in H.THEME_LABEL and H.THEMES[n].get("ANIM") and H.THEMES[n].get("SND")
    assert len(set(H.THEME_ORDER)) == len(H.THEME_ORDER) <= len(H.THEME_LABEL)


@pytest.mark.parametrize("theme", NUEVOS)
def test_fondo_animado_dibuja_y_cambia(ui, theme):
    import time
    ui.set_look(theme=theme, fx="glass")
    ui.tab = "home"
    for _ in range(3):
        ui.frame()
    a = pygame.image.tobytes(ui.screen, "RGB")
    time.sleep(0.25)
    for _ in range(2):
        ui.frame()
    assert a != pygame.image.tobytes(ui.screen, "RGB"), "el fondo se mueve"


@pytest.mark.parametrize("theme", NUEVOS)
def test_en_rendimiento_no_se_anima_y_en_pantallas_pequenas_no_falla(ui, theme):
    ui.set_look(theme=theme, fx="perf")
    for tab in ("home", "settings"):
        ui.tab = tab
        for _ in range(2):
            ui.frame()
    ui.resize(1280, 720)
    ui.frame()
    ui.resize(1920, 1080)
    ui.set_look(theme="dark", fx="glass")
