"""v2.80: un solo selector de contenedor por juego (existentes · el sistema · crear), sin bloquear la interfaz; compilar usa el contenedor del juego."""
import threading
import time

import pytest

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


def _entrada(ui, i="vcs-x"):
    return {"id": i, "name": "VCS X", "repo": "o/r", "folder": i, "platform": "PC"}


def _vaciar(ui, n=60):
    t0 = time.time()
    while time.time() - t0 < 3:
        while ui._rcp_q:
            ui._rcp_q.pop(0)()
        if ui.modal:
            break
        time.sleep(0.02)


def test_container_name_for_prioridad(ui, H, monkeypatch):
    e = _entrada(ui)
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "")
    monkeypatch.setattr(H.recipes, "for_entry", lambda e: None)
    ui._rcp.pop(e["id"], None)
    ui.cfg["build_container"] = "global"
    ui.cfg["ctr_by_game"] = {}
    assert ui.container_name_for(e, "vcs-x") == "global"
    ui.cfg["ctr_by_game"] = {"vcs-x": "propio"}
    assert ui.container_name_for(e, "vcs-x") == "propio"
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "del-juego")
    assert ui.container_name_for(e, "vcs-x") == "del-juego"


def test_pick_container_lista_existentes_sistema_y_crear(ui, H, monkeypatch):
    e = _entrada(ui)
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    monkeypatch.setattr(H.build, "refresh_containers", lambda: [f"c{i}" for i in range(12)])    # antes se cortaba en 8
    monkeypatch.setattr(H.osver, "in_container", lambda lid: False)
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "c3")
    monkeypatch.setattr(ui, "inst", lambda e: {"launcher_id": e["id"], "installed": True})
    ui.pick_container(e)
    _vaciar(ui)
    assert ui.modal and ui.modal["kind"] == "choice"
    labs = [o[0] for o in ui.modal["options"]]
    assert len(labs) == 14 and "✓ c3" in labs and labs[-1].startswith("CREAR UN CONTENEDOR NUEVO") and any("EL SISTEMA" in x for x in labs)


def test_pick_container_sin_distrobox_avisa(ui, H, monkeypatch):
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: False)
    monkeypatch.setattr(ui, "inst", lambda e: {"launcher_id": e["id"], "installed": True})
    ui.pick_container(_entrada(ui))
    assert ui.modal is None


def test_elegir_en_carpeta_sin_versiones_separadas_se_recuerda_en_ajustes(ui, H, monkeypatch):
    e = _entrada(ui)

    def sin_meta(lid, n):
        raise OSError("este juego aún no tiene versiones separadas (linux/ y windows/)")
    monkeypatch.setattr(H.osver, "set_container", sin_meta)
    monkeypatch.setattr(H.osver, "in_container", lambda lid: False)
    ui.cfg["ctr_by_game"] = {}
    ui._fix_container(e, "vcs-x", "hub-vcs")
    assert ui.cfg["ctr_by_game"]["vcs-x"] == "hub-vcs"


def test_set_container_global_no_bloquea_y_usa_lista(ui, H, monkeypatch):
    llamado = {}
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    hilo = []

    def lento():
        hilo.append(threading.current_thread() is not threading.main_thread())
        time.sleep(0.2)
        return ["fedora", "ubuntu"]
    monkeypatch.setattr(H.build, "refresh_containers", lento)
    t0 = time.time()
    ui.set_container()
    assert time.time() - t0 < 0.1          # la llamada vuelve enseguida: la consulta va en un hilo
    _vaciar(ui)
    assert hilo == [True] and ui.modal and any(o[0].endswith("fedora") for o in ui.modal["options"])
    assert ui.modal["options"][-1][0].startswith("ESCRIBIR OTRO")


def test_compilar_con_contenedor_inexistente_pide_elegir(ui, H, monkeypatch):
    e = _entrada(ui)
    monkeypatch.setattr(H.build, "distrobox_ok", lambda: True)
    monkeypatch.setattr(H.build, "_CC", {"x": (time.time(), ["otro"])})
    monkeypatch.setattr(ui, "inst", lambda e: {"launcher_id": e["id"], "installed": True})
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "no-existe")
    ui.builds = []
    ui.start_build(e)
    assert ui.modal and "no existe" in str(ui.modal.get("title", "") + ui.modal.get("msg", "")).lower()
    assert not ui.builds


def test_ctr_ok_tres_estados(ui, H, monkeypatch):
    monkeypatch.setattr(H.build, "_CC", {})
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: False)
    assert ui.ctr_ok("x") is None and ui.ctr_ok("") is None
    monkeypatch.setattr(H.build, "_CC", {"x": (time.time(), ["a"])})
    assert ui.ctr_ok("a") is True and ui.ctr_ok("b") is False


def test_ajustes_compilar_muestra_contenedor_del_juego_y_aviso(ui, H, monkeypatch):
    from conftest import shot
    e = next(x for x in ui.entries if x.get("repo"))
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "hub-no-existe")
    monkeypatch.setattr(H.build, "_CC", {"x": (time.time(), ["fedora"])})
    ui.open_detail(e)
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = "compilar"
    run(ui, 6)
    claves = {getattr(w, "key", None) for w in ui.widgets}
    assert "bcont" in claves
    shot(ui, "v280-compilar-contenedor.png")
    ui.go_tab("games")
