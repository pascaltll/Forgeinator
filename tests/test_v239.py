"""v2.39: «Más» no flota sobre los juegos, el fondo animado no se recompone al tocar, y pantalla de carga al abrir por Steam."""
import time

import pytest

pygame = pytest.importorskip("pygame")

from hub import themes_fam as T  # noqa: E402


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.cfg["pals"], u.cfg["bgs"] = {}, {}
    u.set_look(theme="dark", fx="glass")
    u.resize(1920, 1080)


def _juegos(ui, monkeypatch, n=12):
    ents = ui.entries[:n]
    ids = {e["id"] for e in ents}
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="v1", launcher_id=x["id"]) if x["id"] in ids else real(x))
    return ents


@pytest.mark.parametrize("fam", list(T.FAMILIES))
def test_mas_no_pisa_los_juegos(ui, monkeypatch, fam):
    _juegos(ui, monkeypatch)
    ui.set_look(theme=fam)
    ui.go_tab("home") if hasattr(ui, "go_tab") else None
    for _ in range(4):
        ui.frame()
    ws = list(ui.widgets)
    mas = [w for w in ws if str(w.key).split(":")[0] in ("go_lib", "go_upd", "go_dl", "go_steam") or w.key in ("go_lib", "go_upd", "go_dl", "go_steam")]
    juegos = [w for w in ws if str(w.key).startswith("home:")]
    assert mas and juegos, f"{fam}: sin widgets que comparar ({len(mas)}/{len(juegos)})"
    for m in mas:
        for g in juegos:
            inter = m.rect.clip(g.rect)
            assert inter.w * inter.h == 0, f"{fam}: {m.key} pisa {g.key}"


def test_tocar_no_recompone_el_fondo(ui, monkeypatch):
    import hub.ui as H
    ui.set_look(theme="cristal", fx="glass")
    ui.pick_bg(T.FAMILIES["cristal"]["bgs"][0])
    for _ in range(3):
        ui.frame()
    n0 = getattr(ui, "bg_composed", 0)
    ui.t_act = time.time()
    for _ in range(5):
        ui.frame()
    assert getattr(ui, "bg_composed", 0) - n0 <= 1, "al tocar, el fondo no debe recomponerse cada cuadro"
    assert H.ANIM


def test_descargas_tap_tiempos(ui):
    ui.set_look(theme="cristal", fx="glass")
    ui.go_tab("home")
    ui.frame()
    t = time.perf_counter()
    ui.go_tab("downloads")
    ui.frame()
    assert time.perf_counter() - t < 0.5


def _steam(ui, monkeypatch):
    import hub.ui as H
    e = ui.entries[0]
    monkeypatch.setattr(ui, "inst", lambda x: dict(installed=True, version="v1", launcher_id=x["id"]))
    monkeypatch.setattr(H.steamlib, "launch_later", lambda a, delay=2: calls.append((a, delay)) or (True, "ok"))
    return e


calls = []


def test_steam_muestra_carga_y_sale_al_aparecer(ui, monkeypatch, tmp_path):
    import hub.ui as H
    calls.clear()
    e = ui.entries[0]
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="v1", launcher_id=x["id"]))
    monkeypatch.setattr(H.steamlib, "launch_later", lambda a, delay=2: calls.append((a, delay)) or (True, "ok"))
    monkeypatch.setattr(ui, "steam_shortcut", lambda *a, **k: {"appid": 123, "name": "X"}, raising=False)
    monkeypatch.setattr(ui, "via_steam_ok", lambda: True, raising=False)
    monkeypatch.setattr(H.launchlog, "libs_check", lambda lid: {"miss": [], "container": None})
    monkeypatch.setattr(H.steamlib, "watch_launch", lambda *a, **k: None, raising=False)
    import pathlib
    monkeypatch.setattr(H.config, "LAUNCHER", pathlib.Path(str(tmp_path)))
    (tmp_path / "bin").mkdir(); (tmp_path / "bin" / "play").write_text("#!/bin/sh\n")
    for n in ("os_state",):
        monkeypatch.setattr(ui, n, lambda lid: {"active": "linux"})
    for n in ("link_game_linux", "link_game_win"):
        monkeypatch.setattr(ui, n, lambda *a, **k: None)
    monkeypatch.setattr(ui, "_exe_missing", lambda *a, **k: False)
    ui.cfg["steam_splash"] = True
    ui.exit_at = None
    ui.play(e)
    assert getattr(ui, "steam_wait", None), "play() debía entrar en la espera de Steam"
    assert not ui.exit_at and calls[0][1] == 1
    ui.frame()  # dibuja la pantalla de carga sin fallar
    monkeypatch.setattr(H.launchwatch, "alive", lambda *a, **k: True)
    ui.steam_wait["nd"] = ["x"]; ui.steam_wait["chk"] = 0
    ui.pump()
    assert ui.exit_at and not ui.steam_wait
    ui.exit_at = None


def test_steam_sin_aparecer_reintenta_y_sale(ui, monkeypatch):
    import hub.ui as H
    calls.clear()
    monkeypatch.setattr(H.steamlib, "launch_later", lambda a, delay=2: calls.append((a, delay)) or (True, "ok"))
    monkeypatch.setattr(H.launchwatch, "alive", lambda *a, **k: False)
    ui.exit_at = None
    ui.steam_wait = {"t": time.time() - 6, "appid": 9, "lid": "x", "nd": ["x"], "chk": 0}
    ui.pump()
    assert ui.exit_at and not ui.steam_wait and calls == [(9, 2)]
    ui.exit_at = None
