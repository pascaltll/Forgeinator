"""v3.14 · rendimiento medido: nada de leer el disco en cada fotograma (Ajustes, ficha, explorador de archivos), links.json en caché por
fecha, 30 fps en reposo sin fondo animado, un solo proceso de portapapeles al PEGAR y tope de hub.log durante la sesión."""
import os
import sys
import threading
import time

import pytest

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio, pantallas  # noqa: F401
from hub import library, logrot

_MAIN = threading.get_ident()
_IO = {"on": False, "n": []}


def _hook(ev, args):
    if _IO["on"] and threading.get_ident() == _MAIN and ev in ("open", "os.scandir", "os.listdir"):
        p = str(args[0]) if args else ""
        if ev == "open" and (p.endswith(".pyc") or "/fonts/" in p or "/assets/" in p):
            return
        _IO["n"].append((ev, p))


sys.addaudithook(_hook)


def _io_frames(u, n=12):
    _IO["n"].clear()
    _IO["on"] = True
    try:
        for _ in range(n):
            u.frame()
    finally:
        _IO["on"] = False
    return list(_IO["n"])


@pytest.mark.parametrize("nm", ["inicio", "explorar", "lista", "descargas", "ajustes", "ajustes_avanzado", "biblioteca", "buscar", "steam",
                                "arte", "ficha", "ficha_mas", "ficha_solo_codigo", "modal_confirmar", "modal_teclado", "modal_archivos"])
def test_ninguna_pantalla_lee_el_disco_en_cada_fotograma(ui, H, nm):
    dict(pantallas(ui))[nm]()
    run(ui, 3)
    io = _io_frames(ui)
    assert len(io) <= 2, f"{nm}: {len(io)} lecturas en 12 fotogramas: {sorted(set(io))[:6]}"


def test_memo_se_renueva_tras_una_pulsacion_y_por_tiempo(ui):
    n = {"c": 0}

    def f():
        n["c"] += 1
        return n["c"]
    ui.memo_clear()
    assert ui.memo("x", f) == 1 and ui.memo("x", f) == 1
    ui.press("DOWN", now=time.time() + 100)           # cualquier pulsación invalida lo cacheado
    assert ui.memo("x", f) == 2
    ui._memo_c["x"] = (ui._io_gen, time.monotonic() - 10, 2)
    assert ui.memo("x", f, ttl=2.0) == 3              # y como mucho ttl segundos (lo que cambia un hilo se ve igual)


def test_links_json_en_cache_y_al_dia(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "LINKS", tmp_path / "links.json")
    assert library.link_get("a") is None
    library.link_set("a", "/x/a.iso")
    assert library.link_get("a") == "/x/a.iso"
    opens = []
    orig = type(library.LINKS).read_text
    monkeypatch.setattr(type(library.LINKS), "read_text", lambda self, *a, **k: (opens.append(1), orig(self, *a, **k))[1])
    for _ in range(50):
        library.link_get("a")
    assert opens == []                                # sin cambios: ni una lectura
    (tmp_path / "links.json").write_text('{"a": "/y/b.iso", "_discs": {"g": {"S1": "/d1"}}}', encoding="utf-8")
    os.utime(tmp_path / "links.json", ns=(time.time_ns() + 10**9, time.time_ns() + 10**9))
    assert library.link_get("a") == "/y/b.iso"        # lo cambió otro programa: se ve al momento
    assert library.disc_links("g") == {"S1": "/d1"}
    library.disc_link_set("g", "S2", "/d2")
    assert library.disc_links("g") == {"S1": "/d1", "S2": "/d2"}
    (tmp_path / "links.json").write_text("roto", encoding="utf-8")
    os.utime(tmp_path / "links.json", ns=(time.time_ns() + 2 * 10**9,) * 2)
    assert library.link_get("a") is None and library.disc_links("g") == {}


def test_reposo_baja_a_30_fps_solo_sin_fondo_animado(ui, H):
    ui.go_tab("home")
    ui.set_look(theme="dark", fx="perf")
    ui.cfg["power_mode"] = "perf"
    ui._pw_t = time.time()
    ui.toast_t = 0
    ui.t_act = time.time()
    assert ui.target_fps() == 45                       # recién tocado
    ui.t_act = time.time() - 6
    assert ui.target_fps() == 30
    ui.set_look(theme="aurora" if "aurora" in H.THEME_ORDER else H.THEME_ORDER[-1], fx="glass")
    if H.ANIM and ui.fx_level() >= 2 and not ui.reduced_motion():
        assert ui.target_fps() == 45                   # con fondo animado no cambia nada
    ui.cfg["power_mode"] = "auto"


def test_pegar_lee_el_portapapeles_una_vez(ui, monkeypatch):
    n = []
    monkeypatch.setattr(type(ui), "clipboard", staticmethod(lambda: (n.append(1), "hola")[1]))
    m = {"text": "x"}
    ui._osk_paste(m)
    assert m["text"] == "xhola" and len(n) == 1
    monkeypatch.setattr(type(ui), "clipboard", staticmethod(lambda: ""))
    ui._osk_paste(m)
    assert m["text"] == "xhola" and "vacío" in ui.toast_msg.lower()


def test_hub_log_se_recorta_en_la_sesion(tmp_path):
    log = tmp_path / "hub.log"
    log.write_bytes(b"a" * 2000)
    assert not logrot.maybe_rotate(log, limit=5000, check_mode=lambda p: True)
    assert not logrot.maybe_rotate(log, limit=1000, check_mode=lambda p: False)    # sin modo añadir comprobado: no se toca
    assert log.stat().st_size == 2000
    assert logrot.maybe_rotate(log, limit=1000, check_mode=lambda p: True)
    assert log.stat().st_size == 0 and (tmp_path / "hub.log.old").read_bytes() == b"a" * 2000


def test_modo_anadir_real(tmp_path):
    log = tmp_path / "hub.log"
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    os.write(fd, b"x" * 100)
    saved = os.dup(2)
    try:
        os.dup2(fd, 2)
        assert logrot._append_mode(log)
        assert logrot.maybe_rotate(log, limit=10)
        os.write(2, b"nuevo\n")
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(fd)
    assert log.read_bytes() == b"nuevo\n"              # sin huecos: lo nuevo empieza al principio
