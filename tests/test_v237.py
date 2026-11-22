"""v2.37: Inicio con disposición propia por tema, orden de los temas y timbres nuevos."""
import time

import pytest

pygame = pytest.importorskip("pygame")


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.set_look(theme="dark", fx="glass")
    u.resize(1920, 1080)


def _con_juegos(ui, monkeypatch, n):
    ents = ui.entries[:n]
    ids = {e["id"] for e in ents}
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="v1", launcher_id=x["id"]) if x["id"] in ids else real(x))
    return ents


def run(ui, n=3):
    for _ in range(n):
        ui.frame()


def test_orden_y_cobertura_de_disposiciones():
    import hub.ui as H
    assert len(set(H.THEME_ORDER)) == len(H.THEME_ORDER) == 15 and set(H.THEME_ORDER) <= set(H.THEMES) and set(H.THEME_ORDER) <= set(H.THEME_LABEL)
    assert H.THEME_ORDER[:3] == ("limpio", "quiver", "prototipo") and H.THEME_ORDER[13] == "bloque" and H.THEME_ORDER[-1] == "obsidian"
    combos = {(H.THEMES[t]["HOME"], H.THEMES[t].get("HOMEV")) for t in H.THEME_ORDER[:14]}
    assert len(combos) == 14, "cada tema heredado representa Inicio de una forma distinta"
    assert (H.THEMES["obsidian"]["HOME"], H.THEMES["obsidian"].get("HOMEV")) == ("posters", None)      # v2.93: Obsidian comparte las portadas de Limpio a propósito
    for t in H.THEME_ORDER:
        assert H.THEMES[t].get("SND", "soft") in __import__("hub.sfx", fromlist=["x"]).PROFILES


@pytest.mark.parametrize("n", [0, 1, 9])
def test_todos_los_temas_dibujan_inicio(ui, monkeypatch, n):
    import hub.ui as H
    ents = _con_juegos(ui, monkeypatch, n)
    for th in H.THEME_ORDER:
        ui.set_look(theme=th, fx="glass")
        ui.tab = "home"
        ui.focus = None
        for w, h in ((1920, 1080), (1280, 720)):
            ui.resize(w, h)
            run(ui)
            keys = {x.key for x in ui.widgets}
            assert {f"home:{e['id']}" for e in ents} <= keys or th == "prototipo" and n and any(k.startswith("home:") for k in keys), (th, w, n)
            if n == 0:
                assert "empty_go" in keys, th
        ui.resize(1920, 1080)


def test_se_navega_entre_juegos_en_cada_disposicion(ui, monkeypatch):
    import hub.ui as H
    ents = _con_juegos(ui, monkeypatch, 6)
    for th in H.THEME_ORDER:
        ui.set_look(theme=th, fx="glass")
        ui.tab = "home"
        ui.focus = f"home:{ents[0]['id']}"
        run(ui)
        vistos = {ui.focus}
        for d in ("RIGHT", "RIGHT", "DOWN", "DOWN", "LEFT"):
            ui.nav(d)
            run(ui, 2)
            vistos.add(ui.focus)
        assert len(vistos) >= 2, (th, vistos)


def test_xmb_y_carrusel_se_centran_en_el_enfocado(ui, monkeypatch):
    ents = _con_juegos(ui, monkeypatch, 6)
    for th in ("onda", "cubo"):
        ui.set_look(theme=th, fx="glass")
        ui.tab = "home"
        for k in (0, 3):
            ui.focus = f"home:{ents[k]['id']}"
            run(ui, 3)
            r = next(w.rect for w in ui.widgets if w.key == ui.focus)
            big = max(w.rect.w for w in ui.widgets if w.key.startswith("home:"))
            assert r.w == big, (th, k)


def test_etiquetas_de_plataforma_cortas():
    from hub.ui_homes import HomeLayoutsMixin as M
    assert M._hl_plat({"platform": "PlayStation 4"}) == "PS4"
    assert M._hl_plat({"platform": "PC"}) == "PC"


def test_nuevos_timbres_suenan_distinto():
    from hub import sfx
    base = sfx.synth("soft")
    for p in ("silk", "click", "marimba", "arcade", "blip"):
        g = sfx.synth(p)
        assert all(g[k] != base[k] for k in g) and all(len(v) / 2 / sfx.RATE < 0.6 for v in g.values()), p
