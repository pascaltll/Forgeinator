"""v2.27: limpieza visual y cuatro temas nuevos (Neón, Tinta, Fósforo, Bloque)."""
import time

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.set_look(theme="dark")


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


@pytest.mark.parametrize("th", ["neon", "tinta", "fosforo", "bloque"])
def test_tema_nuevo_se_dibuja_y_se_lee(ui, th):
    import hub.ui as H
    assert th in H.THEME_ORDER and th in H.THEME_LABEL
    ui.set_look(theme=th)
    for tab in ("home", "games", "downloads", "settings", "library"):
        ui.go_tab(tab)
        for _ in range(3):
            ui.frame()
            time.sleep(0.01)
    t = H.THEMES[th]
    for bg in ("BG", "PANEL", "PANEL2"):
        assert ratio(t["TXT"], t[bg]) >= 7, f"{th}: texto sobre {bg}"
        assert ratio(t["DIM"], t[bg]) >= 4.5, f"{th}: texto secundario sobre {bg}"


def test_tema_cambia_tipografia_y_vuelve(ui):
    import hub.ui as H
    ui.set_look(theme="fosforo")
    assert H.FONT == "mono" and H.PATTERN == "scan" and H.FONTK < 1
    ui.set_look(theme="dark")
    assert H.FONT is None and H.PATTERN is None and H.FONTK == 1.0


def test_lista_sin_insignia_no_instalado(ui):
    from pathlib import Path
    src = Path(__import__("hub").__file__).parent
    assert "NO INSTALADO" not in (src / "ui_explore.py").read_text(encoding="utf-8")
    assert "SIN PORT CONOCIDO" not in (src / "ui.py").read_text(encoding="utf-8")
