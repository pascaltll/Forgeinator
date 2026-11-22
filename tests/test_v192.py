"""v1.92: texto invisible → rectángulo, cruceta por filas (alcanzabilidad de todos los botones), rendimiento de Ajustes, miniaturas de Explorar,
iconos de Lucide, registros de arranques fallidos y Descargas sin solapes."""
import subprocess
import time
import types

import pytest

from conftest import report_section
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, pantallas, run  # noqa: F401

pygame = pytest.importorskip("pygame")
DIRS = ("UP", "DOWN", "LEFT", "RIGHT")


# ── rectángulos por caracteres invisibles ────────────────────
def test_caracteres_invisibles_no_llegan_a_la_pantalla(ui):
    ui._sane_c = {}
    assert ui.sane("recompilación​ estática‍") == "recompilación estática"
    assert ui.sane("static recomp‑port") == "static recomp-port"
    assert ui.sane("Zelda ❤️") in ("Zelda ❤", "Zelda ")          # emoji de color: o se dibuja o se quita; nunca un cuadrado
    assert ui.sane("a⁠b﻿c­") == "abc"
    ui._deny = ("\U0001F3AE",)
    ui._sane_c, ui._glyph_ok = {}, {}
    try:
        assert ui.sane("Juego \U0001F3AE") == "Juego "
    finally:
        ui._deny, ui._sane_c, ui._glyph_ok = (), {}, {}


# ── cruceta ─────────────────────────────────────────────
@pytest.mark.parametrize("theme", ["dark", "prototipo"])
def test_con_la_cruceta_se_llega_a_todos_los_botones_de_cada_pantalla(H, ui, theme):
    """Para cada pantalla: grafo «desde este botón, ARRIBA/ABAJO/IZQ/DER va a…»; todo botón enfocable debe poder alcanzarse desde el primero."""
    ui.set_look(theme=theme, fx="perf")
    fallos = []
    for nombre, preparar in pantallas(ui):
        if nombre.startswith("modal"):
            continue
        ui._ex_seen = None                  # con la animación de entrada en marcha (el peor caso: las tarjetas a alturas distintas)
        preparar()
        run(ui, 3)
        ws = [w for w in ui.widgets if w.focus and w.cb is not None]
        if len(ws) < 2:
            continue
        graf = {}
        for w in ws:
            for d in DIRS:
                ui.focus = w.key
                ui.nav(d)
                graf.setdefault(w.key, set()).add(ui.focus)
        ini = min(ws, key=lambda w: (w.rect.y, w.rect.x)).key
        vistos, cola = {ini}, [ini]
        while cola:
            for n in graf.get(cola.pop(), ()):
                if n not in vistos and n in graf:
                    vistos.add(n)
                    cola.append(n)
        # las pestañas se alcanzan con LB/RB; el resto debe poder alcanzarse con la cruceta
        perdidos = sorted(k for k in graf if k not in vistos and not str(k).startswith("tab:"))
        if perdidos:
            por = {w.key: w for w in ws}
            fallos.append((nombre, f"{len(perdidos)} de {len(ws)} inalcanzables", [(k, tuple(por[k].rect)) for k in perdidos[:3]],
                           "inicio", ini, tuple(por[ini].rect), "filtro", ui.filter, "consulta", ui.query, "tam", ui.screen.get_size(), "t", round(ui.t, 2)))
    assert not fallos, fallos


def test_ficha_recorre_los_pasos_en_orden_y_vuelve(H, ui):
    ui.set_look(theme="dark", fx="perf")
    ui.more_open.clear()
    orig = ui.inst
    ui.inst = lambda e: {**orig(e), "installed": True, "version": "1.0", "launcher_id": e["id"], "dir": "/tmp/x"} if ui.entries.index(e) == 0 else orig(e)
    try:
        ui.go_tab("games")
        ui.open_detail(ui.entries[0])
        run(ui, 4)
        ui.focus = "back"
        ida = []
        for _ in range(8):
            ui.act("DOWN")
            run(ui, 1)
            ida.append(ui.focus)
        prim = "play" if "play" in ida else "rlib"          # v2.74: la ficha muestra solo el paso que toca
        assert prim in ida and ida.index(prim) < ida.index("more"), ida
        vuelta = []
        for _ in range(8):
            ui.act("UP")
            run(ui, 1)
            vuelta.append(ui.focus)
        assert prim in vuelta and "back" in vuelta, (ida, vuelta, [(w.key, w.rect.y) for w in ui.widgets])
    finally:
        del ui.inst


# ── rendimiento de Ajustes ───────────────────────────────────
def test_ajustes_dibuja_solo_lo_visible_y_baja_los_fps_en_reposo(H, ui):
    ui.set_look(theme="prototipo", fx="perf")
    ui.go_tab("settings")
    ui.adv_open = True
    run(ui, 4)
    claves = {w.key for w in ui.widgets}
    assert {"launchlogs", "doctor", "covers"} <= claves, "las filas fuera de pantalla deben seguir registradas para la cruceta"
    ui.t_act = 0
    ui.toast_t = 0
    assert ui.target_fps() == 20, dict(modal=(ui.modal or {}).get("title"), perf=ui.perf.on, held=ui.held, tab=ui.tab)
    ui.t_act = time.time()
    assert ui.target_fps() == 45
    ui.go_tab("home")
    ui.t_act = 0
    assert ui.target_fps() == 30          # v3.14: sin fondo animado (calidad rendimiento), en reposo cualquier pantalla baja a 30
    ui.t_act = time.time()
    assert ui.target_fps() == 45


def test_caches_de_texto_evitan_recalcular(ui):
    ui._fit_c.clear()
    a = ui.fit("Nombre larguísimo de un juego para recortar con puntos suspensivos", 22, 120)
    assert a.endswith("…") and len(ui._fit_c) == 1 and ui.fit("Nombre larguísimo de un juego para recortar con puntos suspensivos", 22, 120) is a


# ── Explorar: miniaturas y entrada ───────────────────────────
def test_miniaturas_de_explorar_cargan_de_tres_en_tres(H, ui, tmp_path, monkeypatch):
    from hub import covers
    monkeypatch.setattr(covers, "path_for", lambda i: tmp_path / "x.png")
    pygame.image.save(pygame.Surface((300, 400)), str(tmp_path / "x.png"))
    ui._cov, ui._cov_jobs = {}, set()
    for e in ui.entries[:8]:
        ui.cover(e, (80, 100), small=True)
    assert len(ui._cov_jobs) <= 3
    t0 = time.time()
    while ui._cov_jobs and time.time() - t0 < 5:
        ui._cov_collect()
        time.sleep(0.02)
    assert not ui._cov_jobs


def test_la_lista_de_explorar_pide_miniatura_y_anima_la_entrada(H, ui, monkeypatch):
    pedidas = []
    orig = ui.thumb
    monkeypatch.setattr(ui, "thumb", lambda e, r, foc=False: pedidas.append(e["id"]) or orig(e, r, foc))
    ui.set_look(theme="prototipo", fx="perf")
    ui.go_tab("games")
    ui.filter, ui.explore = "Todos", "list"
    ui._ex_seen = None
    ui.t = 100.0
    ui.frame(0)
    assert ui.enter(0, ("list", "Todos")) > 0 or ui.enter(5, ("list", "Todos")) > 0, "al entrar las tarjetas deben ir deslizando"
    ui.t = 101.0
    assert ui.enter(13, ("list", "Todos")) == 0
    assert pedidas


def test_orden_de_arte_vertical_prefiere_portada_vertical(ui):
    assert ui.ART_ORDER_V.index("portrait") < ui.ART_ORDER_V.index("hero") and ui.ART_ORDER.index("hero") < ui.ART_ORDER.index("portrait")


# ── iconos ───────────────────────────────────────────────
def test_iconos_lucide_se_tiñen_y_escalan():
    from hub import icons
    for n in ("house", "compass", "download", "settings", "play", "check", "gamepad-2"):
        assert icons.available(n), n
    s = icons.get("house", 48, (255, 138, 61))
    assert s.get_size() == (48, 48)
    opacos = [s.get_at((x, y)) for x in range(48) for y in range(48) if s.get_at((x, y)).a > 200]
    assert opacos and all(c.r > 240 and 120 < c.g < 150 and c.b < 80 for c in opacos), "el icono debe llevar el color pedido"
    assert icons.get("no-existe", 48, (0, 0, 0)) is None


# ── registros de arranque ────────────────────────────────────
def test_informe_de_arranque_fallido(tmp_path, monkeypatch):
    from hub import config, launchlog as L
    monkeypatch.setattr(config, "DATA", tmp_path / "d")
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "games").mkdir(parents=True)
    (config.LAUNCHER / "state").mkdir()
    (config.LAUNCHER / "games" / "g.toml").write_text('exec="/ruta/que/no/existe"\n')
    (config.LAUNCHER / "state" / "g.log").write_text("linea del launcher\n")
    o = L.new_out("g")
    o.write_text("error while loading shared libraries: libSDL3.so.0\n")
    md = L.report("g", "Juego G", 127, 1.5, o)
    t = md.read_text()
    assert "código de salida: 127" in t and "libSDL3.so.0" in t and "existe: False" in t and "linea del launcher" in t
    assert L.latest("g") == md and L.latest("otro") is None
    b = L.bundle()
    assert "libSDL3.so.0" in b.read_text() and b.name == "ENVIAR.md" and b not in L.reports()
    assert "token" not in t.lower() and "cookie" not in t.lower()


def test_arranque_que_murio_despues_se_detecta_al_abrir(tmp_path, monkeypatch):
    from hub import config, launchlog as L
    monkeypatch.setattr(config, "DATA", tmp_path / "d")
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    o = L.new_out("zelda")
    o.write_text("loading\nSegmentation fault (core dumped)\n")
    old = time.time() - 120
    import os
    os.utime(o, (old, old))
    ok = L.dir_() / "bueno-20260101-000000.out"
    ok.write_text("todo bien\n")
    os.utime(ok, (old, old))
    assert L.scan_orphans() == 1 and L.latest("zelda") is not None and L.latest("bueno") is None
    assert L.scan_orphans() == 0


def test_poda_de_registros_antiguos(tmp_path, monkeypatch):
    from hub import config, launchlog as L
    monkeypatch.setattr(config, "DATA", tmp_path / "d")
    for i in range(L.KEEP + 6):
        (L.dir_() / f"g-2026010{i % 10}-{i:06d}.out").write_text("x")
    L.new_out("g")
    assert len(list(L.dir_().glob("*.out"))) <= L.KEEP


def test_jugar_que_termina_enseguida_guarda_el_informe_y_se_ve_en_la_ficha(H, ui, tmp_path, monkeypatch):
    from hub import config, launchlog as L
    monkeypatch.setattr(config, "DATA", tmp_path / "d")
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "bin").mkdir(parents=True)
    play = config.LAUNCHER / "bin" / "play"
    play.write_text("#!/bin/sh\necho 'boom: no se pudo abrir' >&2\nexit 3\n")
    play.chmod(0o755)
    monkeypatch.setattr(H_ui_mod(), "subprocess", subprocess)         # aquí SÍ se lanza un proceso real (un script que falla)
    e = ui.entries[0]
    orig = ui.inst
    ui.inst = lambda x: {**orig(x), "installed": True, "version": "1.0", "launcher_id": "g1", "dir": str(tmp_path)} if x is e else orig(x)
    try:
        ui.play(e)
        t0 = time.time()
        while ui.play_pr and time.time() - t0 < 10:
            ui.pump()
            time.sleep(0.05)
        assert "código 3" in ui.toast_msg and "Registro guardado" in ui.toast_msg, ui.toast_msg
        assert "boom" in L.latest("g1").read_text()
        ui.set_look(theme="dark", fx="perf")
        ui.go_tab("games")
        ui.open_detail(e)
        run(ui, 4)
        assert "launchlog" in {w.key for w in ui.widgets}, "v2.75: si el arranque falló, el registro es un botón de la ficha"
        ui.show_launchlog(e)
        run(ui, 2)
        assert ui.modal and ui.modal["kind"] == "log" and any("boom" in ln for ln in ui.modal["job"].log)
        ui.close_modal()
        ui.send_launchlogs()
        assert (L.dir_() / "ENVIAR.md").exists() and "ENVIAR.md" in ui.toast_msg
    finally:
        del ui.inst
        ui.modal = None


def H_ui_mod():
    import hub.ui
    return hub.ui


# ── Descargas ────────────────────────────────────────────
def test_descargas_sin_solapes_a_los_dos_tamaños_del_ally(H, ui, monkeypatch):
    from hub import layoutdump

    def D(**k):
        d = types.SimpleNamespace(id="x", state="active", progress=.42, speed=3e6, size=8e8, done=3.4e8, meta={"title": "Crash Team Racing (PS1) — Native beta 7.1"},
                                  name="ctr.zip", url="u", error="", verified=False, catalog=False)
        d.eta = lambda: 120
        d.__dict__.update(k)
        return d
    items = [D(id="1"), D(id="2", state="paused", progress=.2), D(id="3", state="done", progress=1, verified=True), D(id="4", state="error", error="Sin conexión")]
    monkeypatch.setattr(ui.mgr, "list", lambda: items)
    partes = []
    try:
        for th in ("prototipo", "dark"):
            for w, h in ((1280, 720), (1920, 1080)):
                ui.resize(w, h)
                ui.set_look(theme=th, fx="perf")
                ui.go_tab("downloads")
                run(ui, 3)
                txt, a = layoutdump.report(ui, "descargas", with_ascii=(th == "prototipo" and w == 1280))
                partes.append(txt)
                assert not a["overlaps"], (th, w, a["overlaps"])
        report_section("Descargas con 4 elementos (cómo se ve)", "\n\n".join(partes))
    finally:
        ui.resize(1280, 800)


def test_lista_con_miles_de_fichas_y_ids_repetidos_sigue_siendo_navegable(H, ui):
    """Catálogo grande con ids repetidos (pasa con listas importadas): cada tarjeta lleva su propia clave de foco y todas se alcanzan con la cruceta."""
    base = dict(ui.entries[0])
    ents = [dict(base, id=f"x{i % 1150}", name=f"Juego {i}", repo=f"o/r{i}") for i in range(1250)]
    orig = ui.entries
    ui.entries = ents
    ui.__dict__.pop("_vis_key", None)
    try:
        ui.set_look(theme="dark", fx="perf")
        ui.go_tab("games")
        ui.filter, ui.explore, ui._ex_seen = "Todos", "list", None
        run(ui, 3)
        ws = [w for w in ui.widgets if w.focus and w.cb is not None]
        claves = [w.key for w in ws]
        assert len(claves) == len(set(claves)), "claves de foco repetidas"
        graf = {}
        for w in ws:
            for d in DIRS:
                ui.focus = w.key
                ui.nav(d)
                graf.setdefault(w.key, set()).add(ui.focus)
        ini = min(ws, key=lambda w: (w.rect.y, w.rect.x)).key
        vistos, cola = {ini}, [ini]
        while cola:
            for n in graf.get(cola.pop(), ()):
                if n not in vistos and n in graf:
                    vistos.add(n)
                    cola.append(n)
        assert not [k for k in graf if k not in vistos and not k.startswith("tab:")]
    finally:
        ui.entries = orig
