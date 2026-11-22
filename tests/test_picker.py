"""Selector de archivos: abre en la carpeta de ROMs de la plataforma, filtro por nombre y paginado táctil."""
import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import shot


@pytest.fixture()
def ui(tmp_path, monkeypatch):
    import hub.ui as H
    from hub import config
    roms = tmp_path / "roms"
    (roms / "n64").mkdir(parents=True)
    (roms / "psx").mkdir()
    for i in range(120):
        (roms / "n64" / f"juego{i:03}.z64").write_bytes(b"x")
    (roms / "n64" / "Banjo-Kazooie (USA).z64").write_bytes(b"x")
    u = H.UI()
    monkeypatch.setitem(u.cfg, "rom_dirs", [str(roms)])
    u.roms_dir = roms
    return u


def _frames(u, n=3):
    for _ in range(n):
        u.frame()


def test_abre_en_la_carpeta_de_la_plataforma(ui):
    assert ui.rom_dir_for("Nintendo 64").name == "n64"
    assert ui.rom_dir_for("PlayStation").name == "psx"
    assert ui.rom_dir_for("Sega Saturn") is None and ui.rom_dir_for("") is None
    e = {"id": "x", "platform": "Nintendo 64"}
    ui.pick_file(e)
    assert ui.modal["kind"] == "picker" and ui.modal["dir"].name == "n64"


def test_sin_carpeta_de_plataforma_cae_al_comportamiento_anterior(ui):
    ui.pick_file({"id": "x", "platform": "Sega Saturn"})
    assert ui.modal["dir"].name != "n64"


def test_filtro_por_nombre_y_quitar_filtro(ui):
    ui.pick_file({"id": "x", "platform": "Nintendo 64"})
    m = ui.modal
    assert len(m["items"]) == 121
    ui._picker_filter(m)                        # abre el teclado en pantalla
    assert ui.modal["kind"] == "osk"
    ui.modal["text"] = "banjo"
    ui._osk_ok(ui.modal)
    assert ui.modal["kind"] == "picker" and [p.name for _, _, p, _ in ui.modal["items"]] == ["Banjo-Kazooie (USA).z64"]
    ui._picker_filter(ui.modal)                 # segundo toque: quita el filtro
    assert len(ui.modal["items"]) == 121


def _tap(u, key):
    w = next(w for w in u.widgets if w.key == key)
    w.cb()


def test_botones_de_pagina_desplazan_la_lista(ui):
    ui.pick_file({"id": "x", "platform": "Nintendo 64"})
    _frames(ui)
    pv = ui.views["picker"]
    assert pv.h > pv.rect.h
    _tap(ui, "pg:dn")
    _frames(ui)
    primera = pv.off
    assert primera > pv.rect.h * 0.8, "una página abajo debe mover casi una pantalla"
    _tap(ui, "pg:dn")
    _frames(ui)
    assert pv.off > primera
    _tap(ui, "pg:up")
    _tap(ui, "pg:up")
    _frames(ui)
    assert pv.off == 0
    for _ in range(40):                          # nunca pasa del final
        _tap(ui, "pg:dn")
        _frames(ui, 1)
    assert pv.off <= pv.h - pv.rect.h + 1


def test_captura(ui):
    ui.pick_file({"id": "x", "platform": "Nintendo 64"})
    _frames(ui, 4)
    shot(ui, "73_selector.png")
