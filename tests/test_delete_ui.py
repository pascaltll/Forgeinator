"""Borrar un juego desde la UI: casillas, confirmación en dos pasos, papelera y restauración."""
import time
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import shot, wait_for
from hub import catalog, catalogjobs, config, install, trash


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u


def run(u, n=3):
    for _ in range(n):
        u.frame()
        time.sleep(0.01)


@pytest.fixture
def juego(ui, tmp_path, monkeypatch):
    """Un juego instalado (carpeta + launcher + arte + descarga + enlace a una ROM tuya)."""
    g = tmp_path / "Games"
    (g / "launcher" / "games").mkdir(parents=True)
    (g / "launcher" / "art" / "solowin").mkdir(parents=True)
    (g / "launcher" / "art" / "solowin" / "icon.png").write_bytes(b"png")
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", g / "launcher")
    dl = tmp_path / "descargas"
    dl.mkdir()
    orig = config.path
    monkeypatch.setattr(config, "path", lambda k: dl if k == "downloads_dir" else orig(k))
    e = {"id": "solowin", "name": "Solo Windows", "repo": "u/solowin", "platform": "PC", "folder": "SoloWin"}
    d = g / "SoloWin"
    d.mkdir()
    (d / "game.exe").write_text("exe")
    install.register(e, d, "game.exe", "a.zip", "v1")
    rom = tmp_path / "ROMs" / "mi-rom.chd"
    rom.parent.mkdir()
    rom.write_text("MI ROM")
    (d / "rom.chd").symlink_to(rom)
    zipf = dl / "solowin-v1.zip"
    zipf.write_text("zip")
    j = catalogjobs.CatalogJob("j9", "x", 0, True, "solowin", "nas")
    j.path, j.state = str(zipf), "done"
    ui._jobs_backup = dict(ui.cjobs._jobs)
    ui.cjobs._jobs[j.id] = j
    ui.entries.append(e)
    ui._inst_c = None
    ui.modal, ui.toast_msg, ui.detail = None, "", None
    yield dict(e=e, dir=d, rom=rom, zip=zipf, g=g)
    ui.cjobs._jobs = ui._jobs_backup
    if e in ui.entries:
        ui.entries.remove(e)
    ui.modal, ui._inst_c, ui._trash_c = None, None, None


def abrir(ui, j):
    ui.open_delete(j["e"])
    run(ui)
    return ui.modal


def widgets(ui):
    return {w.key: w for w in ui.widgets}


def test_plan_propone_solo_lo_que_existe_y_las_descargas_desmarcadas(ui, juego):
    m = abrir(ui, juego)
    claves = {it["key"]: it for it in m["items"]}
    assert set(claves) == {"dir", "launcher", "dl"}
    assert claves["dir"]["checked"] and claves["launcher"]["checked"]
    assert claves["dl"]["checked"] is False, "los archivos descargados NO vienen marcados"
    assert len(claves["launcher"]["paths"]) == 2          # el .toml y el arte


def test_el_foco_inicial_es_cancelar(ui, juego):
    abrir(ui, juego)
    assert ui.focus == "del:no"


def test_calcula_tamanos_en_segundo_plano(ui, juego):
    m = abrir(ui, juego)
    assert wait_for(lambda: all(it["size"] is not None for it in m["items"]), 5)
    assert m["items"][0]["size"][1] is True


def test_el_boton_borrar_esta_bloqueado_el_primer_segundo(ui, juego):
    m = abrir(ui, juego)
    assert widgets(ui)["del:go"].cb is None, "durante el primer segundo el botón no hace nada"
    m["opened"] -= 5
    run(ui)
    assert widgets(ui)["del:go"].cb is not None
    assert juego["dir"].exists()


def test_doble_toque_rapido_no_confirma(ui, juego):
    m = abrir(ui, juego)
    m["opened"] -= 5                                  # ya pasó el bloqueo inicial
    hecho = []
    m["go"] = lambda mm: hecho.append(1)
    run(ui)
    widgets(ui)["del:go"].cb()                        # 1.er toque: arma
    assert m["armed"] > 0 and not hecho
    run(ui)
    widgets(ui)["del:go"].cb()                        # 2.º toque inmediato (< 0.8 s): no cuenta
    assert not hecho and juego["dir"].exists()


def test_confirma_con_segundo_toque_deliberado(ui, juego):
    m = abrir(ui, juego)
    m["opened"] -= 5
    hecho = []
    m["go"] = lambda mm: hecho.append(1)
    run(ui)
    widgets(ui)["del:go"].cb()
    m["armed"] -= 1.2                                 # pasó más de 0.8 s
    run(ui)
    widgets(ui)["del:go"].cb()
    assert hecho == [1]


def test_el_armado_caduca_a_los_5_segundos(ui, juego):
    m = abrir(ui, juego)
    m["opened"] -= 10
    run(ui)
    widgets(ui)["del:go"].cb()
    m["armed"] -= 6
    run(ui)
    assert m["armed"] == 0.0, "pasado el plazo vuelve a pedir el primer toque"


def test_sin_nada_marcado_no_se_puede_borrar(ui, juego):
    m = abrir(ui, juego)
    m["opened"] -= 5
    for it in m["items"]:
        it["checked"] = False
    run(ui)
    m["go"] = lambda mm: pytest.fail("no debe borrar")
    w = widgets(ui)["del:go"]
    assert w.cb is None, "sin casillas marcadas el botón no hace nada"


def test_las_casillas_se_marcan_con_el_toque(ui, juego):
    m = abrir(ui, juego)
    idx = next(i for i, it in enumerate(m["items"]) if it["key"] == "dl")
    run(ui)
    widgets(ui)[f"del:{idx}"].cb()
    assert m["items"][idx]["checked"] is True
    widgets(ui)[f"del:{idx}"].cb()
    assert m["items"][idx]["checked"] is False


def test_b_cancela_y_no_se_borra_nada(ui, juego):
    abrir(ui, juego)
    ui.modal_act("B", None)
    assert ui.modal is None and juego["dir"].exists()


def test_cancelar_no_borra(ui, juego):
    abrir(ui, juego)
    widgets(ui)["del:no"].cb()
    assert ui.modal is None and juego["dir"].exists()


def test_borrado_completo_va_a_la_papelera_y_la_rom_sobrevive(ui, juego):
    m = abrir(ui, juego)
    m["opened"] -= 5
    ui._delete_game(m)
    assert wait_for(lambda: not juego["dir"].exists(), 5)
    assert wait_for(lambda: trash.list_ops(), 5)
    assert juego["rom"].read_text() == "MI ROM", "la ROM del usuario no se toca"
    assert juego["zip"].exists(), "la descarga estaba desmarcada: se conserva"
    assert not (config.LAUNCHER / "games" / "solowin.toml").exists() and not (config.LAUNCHER / "art" / "solowin").exists()
    assert "papelera" in ui.toast_msg.lower()
    assert not ui.inst(juego["e"])["installed"]


def test_borrar_tambien_las_descargas_si_se_marcan(ui, juego):
    m = abrir(ui, juego)
    next(it for it in m["items"] if it["key"] == "dl")["checked"] = True
    ui._delete_game(m)
    assert wait_for(lambda: not juego["zip"].exists(), 5)
    assert juego["rom"].exists()


def test_restaurar_lo_ultimo(ui, juego):
    m = abrir(ui, juego)
    ui._delete_game(m)
    assert wait_for(lambda: not juego["dir"].exists() and trash.list_ops(), 5)
    ui._trash_c = None
    ui.trash_restore_last()
    assert wait_for(lambda: juego["dir"].exists(), 5)
    assert (juego["dir"] / "game.exe").exists() and (config.LAUNCHER / "games" / "solowin.toml").exists()
    assert (juego["dir"] / "rom.chd").is_symlink() and juego["rom"].read_text() == "MI ROM"


def test_ajustes_dibuja_la_seccion_papelera(ui, juego):
    m = abrir(ui, juego)
    ui._delete_game(m)
    wait_for(lambda: trash.list_ops(), 5)
    ui._trash_c = None
    ui.adv_open = True
    ui.go_tab("settings")
    run(ui, 3)
    claves = {w.key for w in ui.widgets}
    assert {"trash_r", "trash_e"} <= claves
    ui.go_tab("home")


def test_vaciar_papelera_pide_confirmacion_en_dos_pasos(ui, juego):
    m = abrir(ui, juego)
    ui._delete_game(m)
    wait_for(lambda: trash.list_ops(), 5)
    ui._trash_c = None
    ui.trash_empty_ask()
    run(ui)
    mm = ui.modal
    assert mm["title"] == "Vaciar la papelera" and ui.focus == "del:no"
    assert trash.list_ops(), "aún no se ha borrado nada"
    mm["opened"] -= 5
    run(ui)
    widgets(ui)["del:go"].cb()
    mm["armed"] -= 1.2
    run(ui)
    widgets(ui)["del:go"].cb()
    assert wait_for(lambda: not trash.list_ops(), 5)
    assert juego["rom"].read_text() == "MI ROM"


def test_no_hay_nada_que_borrar(ui, juego, tmp_path):
    e = {"id": "vacio", "name": "Vacío", "repo": "u/vacio", "platform": "PC", "folder": "Vacio"}
    ui.entries.append(e)
    ui.open_delete(e)
    run(ui)
    assert ui.modal["items"] == [] and any("nada" in n.lower() for n in ui.modal["notes"])
    ui.modal["opened"] -= 5
    run(ui)
    assert widgets(ui)["del:go"].cb is None
    ui.entries.remove(e)


def test_quitar_tarjeta_local(ui, juego):
    e = catalog.add_local({"id": "mia", "name": "Mía", "repo": "u/mia", "platform": "PC", "folder": "Mia"})
    ui.reload()
    assert catalog.is_local_only("mia")
    ui.open_delete(ui.entry("mia"))
    run(ui)
    card = next(it for it in ui.modal["items"] if it["key"] == "card")
    assert card["checked"] is False
    card["checked"] = True
    ui._delete_game(ui.modal)
    assert wait_for(lambda: ui.entry("mia") is None, 5)


def test_tarjeta_del_catalogo_de_serie_no_se_puede_quitar(ui, juego):
    assert not catalog.is_local_only("lcs")


def test_el_panel_de_la_ficha_tiene_el_boton_borrar(ui, juego):
    ui.open_detail(juego["e"])
    ui.more_open.add(juego["e"]["id"])
    ui.more_tab[juego["e"]["id"]] = "avanzado"
    run(ui, 3)
    ui.views["detail"].off = 99999
    run(ui, 3)
    assert "del" in widgets(ui)
    shot(ui, "70_zona_borrado.png")
    ui.detail = None


def test_capturas_del_modal(ui, juego):
    m = abrir(ui, juego)
    wait_for(lambda: all(it["size"] is not None for it in m["items"]), 5)
    m["opened"] -= 5
    run(ui)
    shot(ui, "71_borrar_modal.png")
    widgets(ui)["del:go"].cb()
    m["armed"] -= 1.0
    run(ui)
    shot(ui, "72_borrar_armado.png")
    ui.close_modal()
