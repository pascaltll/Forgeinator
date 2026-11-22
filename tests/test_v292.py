"""v2.92: pulsación larga también en Explorar, Biblioteca y Descargas (mismo menú pequeño, con sonido y vibración)."""
import time

import pygame

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


def _post(tipo, **kw):
    pygame.event.post(pygame.event.Event(tipo, **kw))


def _abrir_explorar(ui):
    ui.modal = None
    ui.detail = None
    ui.go_tab("games")
    ui.explore = "list" if hasattr(ui, "explore") else None
    run(ui, 4)


def test_explorar_mantener_pulsado_abre_menu(ui, H, monkeypatch):
    import pytest
    _abrir_explorar(ui)
    w = next((w for w in ui.widgets if w.key.startswith("card:")), None)
    if w is None:
        ui.explore = "all"
        run(ui, 4)
        w = next((w for w in ui.widgets if w.key.startswith("card:")), None)
    if w is None:
        pytest.skip("sin tarjetas de juego visibles en Explorar en esta batería")
    sonidos = []
    monkeypatch.setattr(ui.sfx, "play", lambda n: sonidos.append(n) or True)
    monkeypatch.setattr(H.haptic, "pulse", lambda u, k="hold": True)
    ui.cfg["long_press"] = 0.3
    _post(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1)
    run(ui, 1)
    assert ui.modal is None and ui.detail is None
    time.sleep(0.35)
    run(ui, 2)
    assert ui.modal and ui.modal["kind"] == "choice" and "open" in sonidos
    labs = [o[0] for o in ui.modal["options"]]
    assert "ABRIR LA FICHA" in labs and ("JUGAR" in labs or "INSTALAR" in labs)
    _post(pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1)
    run(ui, 2)
    assert ui.modal is not None and ui.detail is None          # soltar no abre la ficha por debajo


def test_explorar_toque_corto_sigue_abriendo_la_ficha(ui, H):
    import pytest
    _abrir_explorar(ui)
    w = next((w for w in ui.widgets if w.key.startswith("card:")), None)
    if w is None:
        pytest.skip("sin tarjetas de juego visibles en Explorar en esta batería")
    ui.cfg["long_press"] = 0.6
    _post(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1)
    _post(pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1)
    run(ui, 3)
    assert ui.modal is None and ui.detail is not None


def test_menu_de_biblioteca(ui):
    ui.modal = ui.detail = None
    ui.lib_rows = [{"path": "/r/a.iso", "name": "Juego A", "folder": "ps2", "match": None},
                   {"path": "/r/b.iso", "name": "Juego B", "folder": "ps2", "match": ui.entries[0]["id"]}]
    t, opts = ui._lp_menu("lr:/r/a.iso")
    assert t == "Juego A" and [o[0] for o in opts] == ["BUSCAR UN PORT", "BUSCAR EN GITHUB"]
    t, opts = ui._lp_menu("lr:/r/b.iso")
    assert opts[0][0] == "ABRIR"
    assert ui._lp_menu("lr:/no/existe") is None


def test_menu_de_descargas_usa_las_acciones_de_la_tarjeta(ui):
    ui.modal = ui.detail = None
    hechos = []
    ui._lp_actions = {"dl:zz": [("PAUSAR", lambda: hechos.append("p")), ("CANCELAR", lambda: hechos.append("c"))]}
    t, opts = ui._lp_menu("dl:zz")
    assert [o[0] for o in opts] == ["PAUSAR", "CANCELAR"]
    opts[1][1]()
    assert hechos == ["c"]
    assert ui._lp_menu("dl:otra") is None


def test_no_hay_menu_con_modal_o_ficha_abiertos(ui):
    ui.lib_rows = [{"path": "/r/a.iso", "name": "A", "folder": "x", "match": None}]
    ui.modal = {"kind": "choice", "title": "x", "options": []}
    assert ui._lp_menu("lr:/r/a.iso") is None
    ui.modal = None


def test_menu_de_juego_ofrece_actualizar_si_hay_version_nueva(ui, monkeypatch):
    e = ui.entries[0]
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="1.0", launcher_id=x["id"], dir="/tmp/x") if x is e else real(x))
    monkeypatch.setattr(ui, "frozen", lambda x: False)
    monkeypatch.setattr(ui, "rel", {ui.rk(e): {"tag": "2.0"}})
    labs = [o[0] for o in ui._game_options(e)]
    assert "ACTUALIZAR A 2.0" in labs and labs[0] == "JUGAR"
    monkeypatch.setattr(ui, "rel", {ui.rk(e): {"tag": "1.0"}})
    assert not any(l.startswith("ACTUALIZAR") for l in [o[0] for o in ui._game_options(e)])
