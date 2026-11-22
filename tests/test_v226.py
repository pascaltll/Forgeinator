"""v2.26: Inicio sin duplicados, filtros vacíos fuera y caché del arte por carpeta."""
import time

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    return H.UI()


def ids(u):
    return {w.key for w in u.widgets}


def run(u, n=4):
    for _ in range(n):
        u.frame()
        time.sleep(0.01)


def test_inicio_sin_duplicados(ui):
    ui.go_tab("home")
    run(ui)
    w = ids(ui)
    assert "go_lib" in w and "go_upd" in w and "go_dl" in w and "go_steam" in w
    assert not ({"go_explore", "go_ghlogin", "go_ghopen"} & w)


def test_github_sigue_en_ajustes(ui):
    ui.go_tab("settings")
    ui.set_page = "github"
    run(ui)
    assert {"gh_web", "gh_open"} <= ids(ui)
    ui.set_page = None


def test_filtros_vacios_no_se_dibujan(ui):
    ui.go_tab("games")
    ui.explore = "cats"
    run(ui)
    assert "chip:Instalados" not in ids(ui)          # en las pruebas no hay nada instalado


def test_arte_en_cache_hasta_que_cambia_la_carpeta(ui, tmp_path, monkeypatch):
    d = tmp_path / "juego"
    (d / "art").mkdir(parents=True)
    (d / "art" / "cover.png").write_bytes(b"x")
    monkeypatch.setattr(ui, "inst", lambda e: {"dir": str(d)})
    n = []
    real = ui._art_scan
    monkeypatch.setattr(ui, "_art_scan", lambda p: (n.append(1), real(p))[1])
    assert "cover" in ui.art_files({}) and "cover" in ui.art_files({}) and len(n) == 1
    time.sleep(0.02)
    (d / "art" / "hero.png").write_bytes(b"x")
    assert "hero" in ui.art_files({}) and len(n) == 2
