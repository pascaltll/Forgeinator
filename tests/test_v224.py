"""v2.24: «AÑADIR A STEAM» desde la ficha, en modo juego, pasa al escritorio y reabre Hub en «Preparar Steam»."""
import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from hub import steamsetup


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    return H.UI()


def test_ficha_en_modo_juego_pasa_al_escritorio(ui, monkeypatch):
    llamadas = []
    monkeypatch.setattr(steamsetup, "in_game_mode", lambda: True)
    monkeypatch.setattr(steamsetup, "to_desktop", lambda: (llamadas.append(1), (True, "ok"))[1])
    monkeypatch.setattr(ui, "confirm", lambda t, m, go: go())
    ui.exit_at = 0
    ui.steam_apply({"id": "x", "name": "X"})
    assert llamadas == [1] and ui.exit_at > 0


def test_boton_general_sigue_igual(ui, monkeypatch):
    llamadas = []
    monkeypatch.setattr(steamsetup, "to_desktop", lambda: (llamadas.append(1), (True, "ok"))[1])
    monkeypatch.setattr(ui, "confirm", lambda t, m, go: go())
    ui.exit_at = 0
    ui.steam_to_desktop()
    assert llamadas == [1] and ui.exit_at > 0
