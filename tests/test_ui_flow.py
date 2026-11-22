"""Flujo del catálogo en la UI real de Hub (pygame en modo dummy): buscar → variantes → descargar → terminar, con cada fallo."""
import time
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import wait_for
from fakes.daemon import default_variants
from hub import catalogservice as cs


@pytest.fixture(scope="module", params=["1280x800", "1920x1080"], ids=["ally-1280x800", "fullhd"])
def ui(request):
    import os
    os.environ["HUB_WINDOW"] = request.param
    import hub.ui as H
    u = H.UI()
    u.size_name = request.param
    yield u
    try:
        u.running = False
    except Exception:  # noqa: BLE001
        pass


def run(u, n=3):
    for _ in range(n):
        u.frame()
        time.sleep(0.01)


def pump_until(u, pred, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        run(u, 2)
        if pred():
            return True
    return bool(pred())


@pytest.fixture
def silent_hill(ui, monkeypatch):
    e = {"id": "silent-hill-ps1", "name": "Silent Hill", "platform": "PlayStation", "variants": []}
    ui.entries.append(e)
    llamadas = []
    monkeypatch.setattr(ui, "check_file", lambda ent, p: llamadas.append((ent["id"], str(p))))
    ui.modal, ui.toast_msg = None, ""
    ui.cjobs.every = 0.05
    ui.cjobs.clear_finished()
    yield e, llamadas
    ui.entries.remove(e)
    ui.modal = None
    for j in list(ui.cjobs.list()):
        ui.cjobs.remove(j.id)


@pytest.fixture
def dest(ui, tmp_path, monkeypatch):
    from hub import config
    d = tmp_path / "descargas"
    orig = config.path
    monkeypatch.setattr(config, "path", lambda key: d if key == "downloads_dir" else orig(key))
    return d


def elegir(u, i):
    """Lo que hace el botón del modal: cierra y ejecuta la opción."""
    cb = u.modal["options"][i][1]
    u.close_modal()
    cb()


def abrir_resultados(u, e):
    u.cat_open(e)
    assert pump_until(u, lambda: u.modal and u.modal.get("kind") == "choice"), f"no salió la lista de resultados: {u.toast_msg}"


def abrir_variantes(u, e, n_res=0):
    abrir_resultados(u, e)
    elegir(u, n_res)
    assert pump_until(u, lambda: u.modal and "Elige el archivo" in u.modal.get("msg", "")), f"no salieron las variantes: {u.toast_msg}"


# ── búsqueda ────────────────────────────────────────────────────────────────
def test_busqueda_envia_nombre_y_plataforma_y_ordena(ui, silent_hill, daemon):
    e, _ = silent_hill
    abrir_resultados(ui, e)
    assert daemon.calls[0][0] == "health" and daemon.calls[1] == ("search", {"query": "Silent Hill", "system": "PlayStation"})
    labs = [o[0] for o in ui.modal["options"]]
    assert labs[0].startswith("Silent Hill · PlayStation · nas · 95%") and labs[1].startswith("(caída)")


def test_busqueda_sin_resultados(ui, silent_hill, daemon):
    daemon.results["search"] = []
    ui.cat_open(silent_hill[0])
    assert pump_until(ui, lambda: "no encontró nada" in ui.toast_msg) and ui.modal is None


@pytest.mark.parametrize("fallo,texto", [((-2, "No such file or directory", None), "código -2"), ((-32603, "interno", None), "código -32603")])
def test_busqueda_con_error_rpc_muestra_codigo(ui, silent_hill, daemon, fallo, texto):
    daemon.rpc_errors["search"] = fallo
    ui.cat_open(silent_hill[0])
    assert pump_until(ui, lambda: texto in ui.toast_msg), ui.toast_msg


def test_busqueda_con_token_malo(ui, silent_hill, daemon):
    daemon.http_status = 401
    ui.cat_open(silent_hill[0])
    assert pump_until(ui, lambda: "token" in ui.toast_msg.lower()), ui.toast_msg


def test_busqueda_sin_servicio(ui, silent_hill, cs):
    cs.TOKEN_FILE.write_text("x")
    ui.cat_open(silent_hill[0])
    assert pump_until(ui, lambda: "No hay conexión" in ui.toast_msg or "service.py" in ui.toast_msg), ui.toast_msg


def test_fuente_caida_solo_avisa(ui, silent_hill, daemon):
    abrir_resultados(ui, silent_hill[0])
    elegir(ui, 1)
    assert "caída" in ui.toast_msg and ui.modal is None


# ── variantes ───────────────────────────────────────────────────────────────
def test_variantes_24_se_muestran_todas_con_scroll(ui, silent_hill, daemon):
    """El caso real: Silent Hill PS1 tiene 24 variantes y Hub enseñaba 9."""
    daemon.results["variants"] = default_variants(24)
    abrir_variantes(ui, silent_hill[0])
    assert len(ui.modal["options"]) == 24
    run(ui)
    v = ui.views["choice"]
    assert v.h > v.rect.h, "con 24 variantes la lista tiene que poder desplazarse"


def test_variantes_tope_60(ui, silent_hill, daemon):
    daemon.results["variants"] = default_variants(75)
    abrir_variantes(ui, silent_hill[0])
    assert len(ui.modal["options"]) == 60


def test_variantes_vacias(ui, silent_hill, daemon):
    daemon.results["variants"] = []
    abrir_resultados(ui, silent_hill[0])
    elegir(ui, 0)
    assert pump_until(ui, lambda: "no tiene variantes" in ui.toast_msg)


def test_variantes_ignora_elementos_que_no_son_dict(ui, silent_hill, daemon):
    daemon.results["variants"] = [None, "x", 3] + default_variants(2)
    abrir_variantes(ui, silent_hill[0])
    assert len(ui.modal["options"]) == 2


def test_variantes_con_campos_ausentes(ui, silent_hill, daemon):
    daemon.results["variants"] = [{"variant_id": "z"}]
    abrir_variantes(ui, silent_hill[0])
    assert ui.modal["options"][0][0].startswith("? ·")


def test_variantes_marca_sin_pausa(ui, silent_hill, daemon):
    abrir_variantes(ui, silent_hill[0])
    labs = [o[0] for o in ui.modal["options"]]
    assert "(sin pausa)" in labs[1] and "(sin pausa)" not in labs[0]


def test_variantes_error_rpc(ui, silent_hill, daemon):
    abrir_resultados(ui, silent_hill[0])
    daemon.rpc_errors["variants"] = (-32602, "item_id requerido", None)
    elegir(ui, 0)
    assert pump_until(ui, lambda: "código -32602" in ui.toast_msg)


# ── lista del modal con scroll real (límites y geometría) ───────────────────
def abrir_lista(u, n, msg="Elige el archivo", hechos=None):
    hechos = [] if hechos is None else hechos
    opts = [(f"opción {i}", (lambda i=i: hechos.append(i))) for i in range(n)]
    u.modal = {"kind": "choice", "title": "T", "msg": msg, "prev": None, "options": opts}
    u.focus = None
    run(u, 3)
    return u.views["choice"], hechos


@pytest.mark.parametrize("n", [0, 1, 3, 9, 10, 11, 20, 24, 60])
def test_lista_cabe_en_pantalla_y_todo_es_alcanzable_con_el_mando(ui, n):
    v, hechos = abrir_lista(ui, n)
    screen = pygame.Rect(0, 0, ui.W, ui.H)
    assert screen.contains(v.rect), f"la lista se sale de la pantalla {ui.W}x{ui.H}: {v.rect}"
    if n:
        run(ui, 2)
        assert ui.focus == "ch:0"
    for i in range(1, n):
        ui.act("DOWN")
        run(ui, 2)
        assert ui.focus == f"ch:{i}", f"DOWN no llegó a la opción {i} (foco {ui.focus})"
        w = next(w for w in ui.widgets if w.key == f"ch:{i}")
        assert v.rect.contains(w.rect), f"la opción {i} enfocada no se ve (rect {w.rect}, lista {v.rect})"
    if n:
        ui.act("A")
        assert hechos == [n - 1], "A ejecuta la opción enfocada (la última)"
    ui.modal = None


def test_lista_sube_con_el_mando_hasta_el_principio(ui):
    v, _ = abrir_lista(ui, 40)
    for _ in range(39):
        ui.act("DOWN")
        run(ui, 1)
    assert v.off > 0
    for _ in range(39):
        ui.act("UP")
        run(ui, 1)
    assert ui.focus == "ch:0" and v.off == 0
    ui.modal = None


def test_flechas_segun_la_posicion(ui, monkeypatch):
    llamadas = []
    monkeypatch.setattr(ui, "_fade_edge", lambda v, top, bg: llamadas.append(top))
    v, _ = abrir_lista(ui, 3)
    assert llamadas == [], "con pocas opciones no hay flechas"
    v, _ = abrir_lista(ui, 40)
    llamadas.clear(); run(ui, 1)
    assert llamadas == [False], "arriba del todo: solo flecha hacia abajo"
    v.off = (v.h - v.rect.h) / 2
    llamadas.clear(); run(ui, 1)
    assert sorted(llamadas) == [False, True], "a mitad: las dos flechas"
    v.off = v.h
    llamadas.clear(); run(ui, 1)
    assert llamadas == [True], "al final: solo flecha hacia arriba"
    ui.modal = None


def _post(u, ev, **kw):
    pygame.event.post(pygame.event.Event(ev, **kw))
    u.pump()


def test_scroll_con_la_rueda_del_raton(ui):
    v, _ = abrir_lista(ui, 40)
    assert v.off == 0
    _post(ui, pygame.MOUSEWHEEL, x=0, y=-3, flipped=False, which=0, precise_x=0.0, precise_y=-3.0)
    run(ui, 1)
    assert v.off > 0, "la rueda debe mover la lista del modal, no la pantalla de fondo"
    ui.modal = None


def test_scroll_arrastrando_con_el_dedo_y_pulsar_una_fila(ui):
    hechos = []
    v, _ = abrir_lista(ui, 40, hechos=hechos)
    c = v.rect.center
    _post(ui, pygame.MOUSEBUTTONDOWN, pos=c, button=1)
    _post(ui, pygame.MOUSEMOTION, pos=(c[0], c[1] - 160), rel=(0, -160), buttons=(1, 0, 0))
    _post(ui, pygame.MOUSEBUTTONUP, pos=(c[0], c[1] - 160), button=1)
    run(ui, 1)
    assert v.off > 100 and hechos == [], "arrastrar desplaza y NO pulsa ninguna opción"
    run(ui, 2)
    w = next(w for w in ui.widgets if w.key.startswith("ch:") and v.rect.contains(w.rect))
    idx = int(w.key[3:])
    _post(ui, pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1)
    _post(ui, pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1)
    assert hechos == [idx] and ui.modal is None, "un toque sin arrastre sí elige la opción"


def test_lista_con_mensaje_largo_no_se_sale(ui):
    msg = "\n".join(f"línea {i} " + "palabra " * 12 for i in range(6))
    v, _ = abrir_lista(ui, 15, msg=msg)
    assert pygame.Rect(0, 0, ui.W, ui.H).contains(v.rect) and v.rect.h > ui.n(150)
    ui.modal = None


def test_la_lista_empieza_arriba_cada_vez(ui):
    v, _ = abrir_lista(ui, 40)
    v.off = 600
    ui.modal = None
    v2, _ = abrir_lista(ui, 40)
    assert v2.off == 0


# ── descarga ────────────────────────────────────────────────────────────────
def descargar(u, e, i=0):
    abrir_variantes(u, e)
    elegir(u, i)


def test_descarga_ok_sin_sha1_crc32(ui, silent_hill, daemon, dest):
    e, llamadas = silent_hill
    descargar(ui, e)
    assert pump_until(ui, lambda: ui.cjobs.list()), ui.toast_msg
    j = ui.cjobs.list()[0]
    assert pump_until(ui, lambda: j.state == "done", 12)
    assert pump_until(ui, lambda: llamadas, 5)
    assert llamadas[0][0] == e["id"] and Path(llamadas[0][1]).is_file() and Path(llamadas[0][1]).parent == dest
    assert j.sha1 is None and j.crc32 is None


def test_descarga_manda_dest_dir_absoluto_y_lo_crea(ui, silent_hill, daemon, dest):
    assert not dest.exists()
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: daemon.count("download"))
    p = next(pr for m, pr in reversed(daemon.calls) if m == "download")   # después de «download» llegan consultas job_status
    assert p["dest_dir"] == str(dest.resolve()) and Path(p["dest_dir"]).is_absolute() and dest.is_dir()
    assert p["source"] == "nas" and p["variant_id"] == "v0"


def test_descarga_error_rpc_menos_2_se_muestra_y_no_crea_fila(ui, silent_hill, daemon, dest, capsys):
    daemon.rpc_errors["download"] = (-2, "No such file or directory", None)
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: "código -2" in ui.toast_msg), ui.toast_msg
    assert ui.cjobs.list() == [] and "download falló" in capsys.readouterr().err


def test_descarga_respuesta_sin_job_id(ui, silent_hill, daemon, dest):
    daemon.results["download"] = {"otra_cosa": 1}
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: "Respuesta inesperada" in ui.toast_msg), ui.toast_msg
    assert ui.cjobs.list() == []


def test_descarga_respuesta_no_dict(ui, silent_hill, daemon, dest):
    daemon.results["download"] = "ok"
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: "Respuesta inesperada" in ui.toast_msg), ui.toast_msg


def test_job_completo_pero_el_archivo_no_existe(ui, silent_hill, daemon, dest, capsys):
    """El fallo que viste: el daemon dice 'completa' con archivo_descargado.zip y no hay nada en disco."""
    e, llamadas = silent_hill
    daemon.write_file = False
    daemon.filename = "archivo_descargado.zip"
    descargar(ui, e)
    assert pump_until(ui, lambda: ui.cjobs.list())
    j = ui.cjobs.list()[0]
    assert pump_until(ui, lambda: j.state == "done", 12)
    assert pump_until(ui, lambda: "no existe" in ui.toast_msg, 5), ui.toast_msg
    assert llamadas == [], "no debe intentar comprobar un archivo inexistente"
    assert "NO existe el archivo" in capsys.readouterr().err


def test_job_completo_sin_path(ui, silent_hill, daemon, dest):
    daemon.job_script = [{"state": "completed", "progress": 1.0}]
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: "Descarga completa" in ui.toast_msg, 10), ui.toast_msg


def test_job_falla_en_el_servidor(ui, silent_hill, daemon, dest):
    daemon.job_script = [{"state": "running", "progress": 0.1}, {"state": "failed", "error": "RomsFun: HTTP 404"}]
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: ui.cjobs.list())
    j = ui.cjobs.list()[0]
    assert pump_until(ui, lambda: j.state == "error", 10) and j.error == "RomsFun: HTTP 404"


def test_job_status_devuelve_error_rpc_menos_2(ui, silent_hill, daemon, dest):
    daemon.job_script = [(-2, "No such file or directory")]
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: ui.cjobs.list())
    j = ui.cjobs.list()[0]
    assert pump_until(ui, lambda: j.state == "error", 10)
    assert "No such file" in j.error, "el error del daemon debe verse en la fila de DESCARGAS"


def test_daemon_se_cae_a_mitad_de_descarga(ui, silent_hill, daemon, dest):
    daemon.job_script = [{"state": "running", "progress": 0.3}]
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: ui.cjobs.list())
    j = ui.cjobs.list()[0]
    assert pump_until(ui, lambda: j.state == "active", 5)
    daemon.http_status = 500
    assert pump_until(ui, lambda: j.state == "error", 10) and "se perdió la conexión" in j.error


def test_cancelar_desde_la_ui(ui, silent_hill, daemon, dest):
    daemon.job_script = [{"state": "running", "progress": 0.3, "bytes_per_s": 1000}]
    descargar(ui, silent_hill[0])
    assert pump_until(ui, lambda: ui.cjobs.list())
    j = ui.cjobs.list()[0]
    ui.dl_cancel(j)
    assert ui.modal and ui.modal["kind"] == "confirm", "cancelar una descarga activa debe pedir confirmación"
    assert daemon.count("job_cancel") == 0
    ui.modal["cb"]()                       # el usuario pulsa ACEPTAR
    assert j.state == "cancelled" and daemon.count("job_cancel") == 1
    ui.modal = None
    ui.dl_cancel(j)                        # ya terminado: QUITAR directamente, sin confirmar
    assert ui.cjobs.list() == []


def test_pantalla_descargas_dibuja_filas_de_catalogo_en_todos_los_estados(ui, silent_hill, daemon, dest):
    for estado in ({"state": "running", "progress": 0.4, "bytes_per_s": 2e6, "phase": "downloading"}, {"state": "failed", "error": "x" * 300}, {"state": "completed", "progress": 1}):
        j = ui.cjobs.add("dibujo", "Silent Hill (USA)", 700 * 1024 ** 2, False, silent_hill[0]["id"], "nas")
        j.apply(estado)
        ui.go_tab("downloads")
        run(ui, 3)
        ui.cjobs.remove(j.id)
    ui.go_tab("library") if hasattr(ui, "go_tab") else None
