"""v2.35: el aviso (toast) se lee en todos los temas."""
import time

import pytest

pygame = pytest.importorskip("pygame")


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.set_look(theme="dark", fx="glass")


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_aviso_legible_en_todos_los_temas(ui):
    import hub.ui as H
    for th in H.THEME_ORDER:
        ui.set_look(theme=th, fx="glass")
        ui.tab = "home"
        ui.toast_msg, ui.toast_t = "Aviso de prueba", time.time() + 5
        for _ in range(3):
            ui.frame()
        tw = min(ui.W - ui.n(80), ui.n(1000))
        x, y = ui.W // 2 - tw // 2 + ui.n(12), ui.H - ui.n(ui.FH) - ui.n(18) - ui.n(24 + 29) + ui.n(6)
        bg = tuple(ui.screen.get_at((x, y))[:3])
        assert _ratio(H.TXT, bg) >= 4.0, (th, H.TXT, bg, _ratio(H.TXT, bg))
