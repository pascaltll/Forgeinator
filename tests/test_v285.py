"""v2.85: mantener pulsado un juego de Inicio abre su menú (con sonido y vibración); un toque normal sigue jugando."""
import time

import pygame

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


def _post(ui, tipo, **kw):
    pygame.event.post(pygame.event.Event(tipo, **kw))


def _tarjeta(ui, monkeypatch=None, theme="limpio"):
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda e: dict(real(e), installed=True, version="1.0", launcher_id=e["id"], dir="/tmp/x") if ui.entries.index(e) < 3 else real(e))
    ui.set_look(theme=theme, fx="glass")
    ui.go_tab("home")
    ui._inst_c = None
    run(ui, 4)
    return next((w for w in ui.widgets if w.key.startswith("home:")), None)


def _sin_modal(ui):
    ui.modal = None
    ui.detail = None


def test_mantener_pulsado_abre_menu_con_sonido_y_vibracion(ui, H, monkeypatch):
    w = _tarjeta(ui, monkeypatch)
    if w is None:
        import pytest
        pytest.skip("sin juegos instalados en Inicio en esta batería")
    _sin_modal(ui)
    sonidos, pulsos = [], []
    monkeypatch.setattr(ui.sfx, "play", lambda n: sonidos.append(n) or True)
    monkeypatch.setattr(H.haptic, "pulse", lambda u, k="hold": pulsos.append(k) or True)
    ui.cfg["long_press"] = 0.3
    _post(ui, pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1)
    run(ui, 1)
    assert ui.modal is None
    time.sleep(0.35)
    run(ui, 2)
    assert ui.modal and ui.modal["kind"] == "choice"
    labs = [o[0] for o in ui.modal["options"]]
    assert "ABRIR LA FICHA" in labs and ("JUGAR" in labs or "INSTALAR" in labs)
    assert "open" in sonidos and pulsos == ["hold"]
    # al soltar el dedo NO se dispara el juego ni se elige nada del menú recién abierto
    _post(ui, pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1)
    run(ui, 2)
    assert ui.modal is not None


def test_toque_corto_no_abre_menu(ui, H, monkeypatch):
    w = _tarjeta(ui, monkeypatch)
    if w is None:
        import pytest
        pytest.skip("sin juegos instalados en Inicio en esta batería")
    _sin_modal(ui)
    jugados = []
    monkeypatch.setattr(ui, "play", lambda e: jugados.append(e["id"]))
    ui.cfg["long_press"] = 0.6
    _post(ui, pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1)
    _post(ui, pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1)
    run(ui, 2)
    assert ui.modal is None and len(jugados) == 1


def test_arrastrar_cancela_la_pulsacion_larga(ui, H, monkeypatch):
    w = _tarjeta(ui, monkeypatch)
    if w is None:
        import pytest
        pytest.skip("sin juegos instalados en Inicio en esta batería")
    _sin_modal(ui)
    ui.cfg["long_press"] = 0.3
    c = w.rect.center
    _post(ui, pygame.MOUSEBUTTONDOWN, pos=c, button=1)
    _post(ui, pygame.MOUSEMOTION, pos=(c[0], c[1] - 80), rel=(0, -80), buttons=(1, 0, 0))
    run(ui, 1)
    time.sleep(0.35)
    run(ui, 2)
    assert ui.modal is None


def test_haptic_sin_mando_no_falla_y_respeta_el_ajuste(ui, H):
    ui.ctrls = {}
    assert H.haptic.pulse(ui, "hold") is False

    class C:
        llamadas = []

        def rumble(self, a, b, ms):
            C.llamadas.append((a, b, ms))
    ui.ctrls = {0: C()}
    ui.cfg["haptics"] = True
    assert H.haptic.pulse(ui, "hold") is True and C.llamadas
    ui.cfg["haptics"] = False
    n = len(C.llamadas)
    assert H.haptic.pulse(ui, "hold") is False and len(C.llamadas) == n

    class Roto:
        def rumble(self, *a):
            raise RuntimeError("sin vibración")
    ui.cfg["haptics"] = True
    ui.ctrls = {0: Roto()}
    assert H.haptic.pulse(ui, "hold") is False


def test_ajuste_de_vibracion_aparece_y_alterna(ui, H):
    ui.cfg["haptics"] = True
    ui.ctrls = {}
    ui.toggle_haptics()
    assert ui.cfg["haptics"] is False
    ui.toggle_haptics()
    assert ui.cfg["haptics"] is True


def test_heroe_tambien_abre_menu(ui, H, monkeypatch):
    _tarjeta(ui, monkeypatch, "prototipo")
    h = next((w for w in ui.widgets if w.key == "hero"), None)
    assert h is not None
    _sin_modal(ui)
    ui.cfg["long_press"] = 0.3
    _post(ui, pygame.MOUSEBUTTONDOWN, pos=h.rect.center, button=1)
    run(ui, 1)
    time.sleep(0.35)
    run(ui, 2)
    assert ui.modal and ui.modal["kind"] == "choice" and ui.modal["title"]
