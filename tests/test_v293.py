"""v2.93 · tema Obsidian: familia real, seleccionable, persistente, con el contraste y la estructura pedidos; las 14 anteriores intactas."""
import json

import pytest

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from hub import themes_fam as tf
from hub.themes import legacy

HEX = {"BG": "#101114", "PANEL": "#1F2127", "PANEL2": "#2B2E36", "LINE": "#484C56", "TXT": "#EFF1F6", "DIM": "#A4AAB5", "ACC": "#C4C4CE",
       "OK": "#48D678", "WARN": "#FFB840", "ERR": "#FF645C", "SEG": "#3A3C42", "ON_ACC": "#101114", "FOCUS": "#E1E2E6"}
VIEJAS = ["limpio", "quiver", "prototipo", "cristal", "onda", "tarjeta", "cubo", "interruptor", "brasa", "pixel", "neon", "fosforo", "tinta", "bloque"]


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def test_obsidian_registrado_y_las_14_siguen():
    assert "obsidian" in tf.FAMILIES and tuple(tf.ORDER[:14]) == tuple(VIEJAS) and len(tf.ORDER) == 15
    assert "obsidian" in legacy.FAMILIES and len(legacy.FAMILIES["obsidian"]["palettes"]) == 1


def test_colores_exactos_y_estructura():
    d = legacy.build("obsidian")
    for k, h in HEX.items():
        assert d[k] == _rgb(h), k
    assert d["HOME"] == "posters" and d["ANIM"] is None and not d["GLASS"] and d["FONT"] is None and d["SND"] == "soft"
    assert not d.get("GRAD") and not d.get("ORBS") and not d.get("OUTLINE")
    assert d["FAMILY"] == "obsidian" and d["PAL"] == "obsidian"


def test_contraste_de_obsidian():
    assert legacy.check_contrast(legacy.build("obsidian")) == []


def test_sin_animacion_aunque_se_pida_otra():
    assert legacy.build("obsidian", None, "none")["ANIM"] is None
    assert tf.FAMILIES["obsidian"]["bgs"] == ["none"]


def test_aparece_en_el_selector_y_se_aplica(ui):
    import hub.ui as Hm
    ui.go_tab("settings")
    ui.set_page = "look"
    run(ui)
    assert "theme:obsidian" in {w.key for w in ui.widgets}
    ui.set_look(theme="obsidian")
    run(ui)
    assert ui.cfg["theme"] == "obsidian" and Hm.BG == _rgb(HEX["BG"]) and Hm.ACC == _rgb(HEX["ACC"]) and Hm.HOME == "posters"
    ui.set_page = None


def test_persiste_tras_reiniciar(ui, tmp_path, monkeypatch):
    from hub import config
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(config, "DATA", tmp_path)
    ui.set_look(theme="obsidian")
    config.save_settings(ui.cfg)
    guardado = json.loads((tmp_path / "settings.json").read_text())
    assert guardado["theme"] == "obsidian"
    assert config.settings()["theme"] == "obsidian"          # «reiniciar»: se vuelve a leer del disco
    assert tf.normalize(guardado["theme"]) == ("obsidian", "obsidian")


@pytest.mark.parametrize("tab", ["home", "games", "downloads", "settings"])
def test_cuatro_secciones_se_dibujan_con_obsidian(ui, tab):
    ui.modal = None
    ui.detail = None
    ui.set_look(theme="obsidian")
    ui.go_tab(tab)
    run(ui, 4)
    assert ui.widgets, tab
    h = ui.widgets[0]
    assert ui.cfg["theme"] == "obsidian"


def test_navegacion_con_mando_y_teclado(ui):
    ui.modal = None
    ui.detail = None
    ui.set_look(theme="obsidian")
    ui.go_tab("settings")
    ui.set_page = "look"
    run(ui, 3)
    antes = ui.focus
    for d in ((0, 1), (1, 0), (0, -1)):
        ui.nav(d)
        run(ui, 1)
    assert ui.focus is not None
    ui.set_page = None


def test_las_14_anteriores_no_cambian():
    import os
    from hub import ui as U
    for f in VIEJAS:
        for p in [x["id"] for x in legacy.FAMILIES[f]["palettes"]]:
            assert legacy.build(f, p) == tf.build(U._LEG, f, p), (f, p)
