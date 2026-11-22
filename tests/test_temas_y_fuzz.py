"""Robustez de la interfaz: contraste de cada tema, render de TODAS las pantallas y menús en cada tema×efecto, cambio de tema en caliente
y un fuzz con mando que mete miles de pulsaciones buscando cierres, errores y focos perdidos. Las capturas quedan en reports/capturas/temas/."""
import copy
import os
import random
import threading
import time
import types
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from hub.ui import THEME_ORDER as THEMES  # noqa: E402  (el orden real de la interfaz)
THEMES = list(THEMES)
FXS = ["glass", "perf"]
DIRS = ["UP", "DOWN", "LEFT", "RIGHT"]
ACTS = DIRS * 3 + ["A", "A", "A", "B", "X", "Y", "LB", "RB"]
OUT = Path(os.environ.get("REPORT_DIR") or Path(__file__).parent / "reports") / "capturas" / "temas"


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.fixture(scope="module")
def H():
    os.environ["HUB_WINDOW"] = "1280x800"
    import hub.ui as m
    return m


@pytest.fixture(scope="module")
def ui(H):
    u = H.UI()
    yield u
    u.running = False


@pytest.fixture(autouse=True)
def sin_efectos_reales(H, monkeypatch):
    """El fuzz pulsa de todo: nada puede abrir navegadores, lanzar procesos ni reiniciar Hub de verdad."""
    fake = types.SimpleNamespace(
        Popen=lambda *a, **k: types.SimpleNamespace(poll=lambda: 1, pid=1, wait=lambda *a, **k: 1, stdout=iter(()), terminate=lambda: None, returncode=1),
        run=lambda *a, **k: types.SimpleNamespace(returncode=1, stdout="", stderr=""),
        DEVNULL=-3, PIPE=-1, STDOUT=-2, CalledProcessError=Exception, TimeoutExpired=Exception, check_output=lambda *a, **k: b"", SubprocessError=Exception)
    monkeypatch.setattr(H, "subprocess", fake, raising=False)
    monkeypatch.setattr(H.selfupdate, "apply", lambda *a, **k: (False, "prueba"))
    monkeypatch.setattr(H.selfupdate, "restart", lambda *a, **k: None)
    monkeypatch.setattr(os, "execv", lambda *a, **k: None)
    monkeypatch.setattr(os, "execvp", lambda *a, **k: None)
    import webbrowser
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: True)
    monkeypatch.setattr(H.UI, "open_url", lambda self, *a, **k: None)


@pytest.fixture(autouse=True)
def estado_limpio(ui):
    antes = set(threading.enumerate())
    ui.modal = None
    cfg0 = copy.deepcopy(ui.cfg)                         # TODA la configuración: lo que cambie una prueba no se cuela en la siguiente
    yield
    # los hilos que lanzó esta prueba (búsquedas, informes…) pueden abrir un modal más tarde, ya dentro de la SIGUIENTE prueba;
    # en un equipo lento eso pasaba de verdad: esperamos a que acaben (máx. 4 s en total) antes de limpiar
    fin = time.time() + 4
    for t in [t for t in threading.enumerate() if t not in antes and t.is_alive()]:
        t.join(max(0.0, fin - time.time()))
    vivos = [t.name for t in threading.enumerate() if t not in antes and t.is_alive()]
    if vivos:
        _HILOS_LARGOS.append(vivos)
    ui.modal, ui.toast_msg, ui.adv_open = None, "", False
    ui.set_page = None                                   # el fuzz entra en categorías de Ajustes y cambia opciones: se dejan como al empezar
    ui.cfg.clear()
    ui.cfg.update(cfg0)
    ui.set_look(theme="dark", fx="glass")
    ui.go_tab("home")


_HILOS_LARGOS = []


def run(u, n=2):
    for _ in range(n):
        u.frame()
        time.sleep(0.005)


# ── paleta ──────────────────────────────────────────────────
@pytest.mark.parametrize("theme", THEMES)
def test_contraste_de_la_paleta(H, theme):
    t = H.THEMES[theme]
    pares = [("TXT", "BG", 7.0), ("TXT", "PANEL", 7.0), ("TXT", "PANEL2", 6.0), ("DIM", "BG", 4.5), ("DIM", "PANEL", 4.0),
             ("ACC", "BG", 3.5), ("ACC", "PANEL", 3.5), ("OK", "PANEL", 3.0), ("WARN", "PANEL", 3.0), ("ERR", "PANEL", 3.0)]
    malos = [f"{a}/{b}={ratio(t[a], t[b]):.1f}<{m}" for a, b, m in pares if ratio(t[a], t[b]) < m]
    assert not malos, f"{theme}: {malos}"
    on = t.get("ON_ACC", (255, 255, 255))
    assert ratio(on, t["ACC"]) >= 3.5, f"{theme}: texto sobre botón primario ilegible ({ratio(on, t['ACC']):.1f})"
    for fondo in ((38, 128, 78), (170, 52, 52), t["ACC"]):                 # botones ok / peligro / primario: el color de letra que elige on_color
        assert ratio(H.on_color(fondo, t.get("ON_ACC")), fondo) >= 3.5, (theme, fondo)
    assert ratio(t["LINE"], t["BG"]) >= 1.2, "los contornos no se distinguen del fondo"


def test_todos_los_temas_tienen_etiqueta_y_orden(H):
    assert set(H.THEME_ORDER) <= set(H.THEMES) and set(H.THEME_ORDER) <= set(H.THEME_LABEL)


# ── render ──────────────────────────────────────────────────
def _carpeta_de_prueba():
    """Una carpeta propia con archivos: el test no depende de lo que haya en tu HOME."""
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="hubpick-"))
    (d / "carpeta").mkdir()
    for n in ("juego.iso", "otro juego.iso", "notas.txt"):
        (d / n).write_bytes(b"x")
    return d


def pantallas(u):
    e = next((x for x in u.entries if x.get("repo")), u.entries[0])
    solo = next((x for x in u.entries if not x.get("repo")), e)

    def tab(t, **kw):
        def f():
            u.modal = None                       # cada pantalla empieza sin la ventana de la anterior, sea cual sea el orden
            u.go_tab(t)
            for k, v in kw.items():
                setattr(u, k, v)
        return f

    def detail(x, more=False):
        def f():
            u.go_tab("games")
            u.open_detail(x)
            (u.more_open.add if more else u.more_open.discard)(x["id"])
        return f

    def biblioteca():
        u.modal = None
        u.go_tab("library")
        if not u.lib_loaded and not u.lib_busy:
            u.lib_load()
        fin = time.time() + 15
        while (u.lib_busy or not u.lib_loaded) and time.time() < fin:     # la biblioteca de prueba (casa falsa, 150 juegos) se lee en un hilo
            time.sleep(0.02)
        u.lib_limit = 60
    def modal(kind):
        def f():
            u.go_tab("home")
            if kind == "confirm":
                u.confirm("BORRAR", "Mensaje de prueba bastante largo para ver cómo se ajusta en varias líneas dentro de la ventana.", lambda: None)
            elif kind == "osk":
                u.osk("Buscar", lambda t: None, "texto", "pista")
                u.modal["steam"] = False
            elif kind == "osk_steam":                     # la variante con el teclado de Steam (la que sale en Modo Juego)
                u.osk("Buscar", lambda t: None, "texto", "pista")
                u.modal["steam"] = True
            elif kind == "picker":
                u.open_picker("Elige un archivo", _carpeta_de_prueba(), {".iso"}, lambda p: None)
        return f
    return [("inicio", tab("home")), ("explorar", tab("games", explore="cats")), ("lista", tab("games", filter="Todos", explore="list")),
            ("descargas", tab("downloads")), ("ajustes", tab("settings", adv_open=False)), ("ajustes_avanzado", tab("settings", adv_open=True)),
            ("biblioteca", biblioteca), ("buscar", tab("search")), ("steam", tab("steam")), ("arte", tab("art")),
            ("ficha", detail(e)), ("ficha_mas", detail(e, True)), ("ficha_solo_codigo", detail(solo)),
            ("modal_confirmar", modal("confirm")), ("modal_teclado", modal("osk")), ("modal_teclado_steam", modal("osk_steam")), ("modal_archivos", modal("picker"))]


def _rango(surf, rect):
    """(mín, máx) del canal verde a resolución real: el texto fino no se pierde como al reducir la imagen."""
    r = rect.clip(surf.get_rect())
    if r.w < 4 or r.h < 4:
        return None
    g = pygame.image.tobytes(surf.subsurface(r), "RGB")[1::3]
    return min(g), max(g)


@pytest.mark.parametrize("fx", FXS)
@pytest.mark.parametrize("theme", THEMES)
def test_render_de_todas_las_pantallas(ui, H, theme, fx):
    ui.set_look(theme=theme, fx=fx)
    OUT.mkdir(parents=True, exist_ok=True)
    W, Hh = ui.W, ui.H
    for nombre, prep in pantallas(ui):
        ui.modal = None
        prep()
        run(ui, 4)
        surf = ui.screen
        # 1) no está en blanco: hay contenido distinto del fondo
        muestra = [tuple(surf.get_at((x, y)))[:3] for x in range(0, W, 16) for y in range(0, Hh, 16)]
        distintos = sum(1 for p in muestra if abs(lum(p) - lum(H.BG)) > 0.02)
        assert distintos > len(muestra) * 0.01, f"{theme}/{fx}/{nombre}: pantalla vacía"
        # 2) el fondo es el del tema (no quedó de otro tema en caché): esquina sin contenido
        # 3) todo widget visible cabe en pantalla y tiene letra legible
        for w in ui.widgets:
            r = w.rect
            if r.w <= 0 or r.h <= 0:
                continue
            assert r.left >= -2 and r.right <= W + 2, f"{theme}/{fx}/{nombre}: {w.key} se sale por los lados {r}"
            vis = r.clip(pygame.Rect(0, 0, W, Hh))
            if w.focus and w.cb is not None and not str(w.key).startswith("k:") and vis.h > r.h * 0.9 and 8 < r.w < W and r.h >= 24:
                c = _rango(surf, vis)
                if c:
                    assert c[1] - c[0] >= 30, f"{theme}/{fx}/{nombre}: {w.key} sin contraste interno (¿texto invisible?)"
        if fx == "glass" or theme == "quiver":
            pygame.image.save(surf, str(OUT / f"{theme}_{fx}_{nombre}.png"))
        ui.modal = None
    ui.go_tab("home")


def test_el_fondo_del_tema_es_plano_en_quiver_y_claro(ui, H):
    for th, fx in (("quiver", "glass"), ("light", "glass"), ("prototipo", "perf")):      # Prototipo tiene resplandor con «cristal» (v2.05); liso con «rendimiento»
        ui.set_look(theme=th, fx=fx)
        ui.modal = None
        ui.go_tab("home")
        run(ui, 4)
        assert tuple(ui.screen.get_at((ui.W - 3, ui.H // 2)))[:3] == H.THEMES[th]["BG"], th
    ui.set_look(theme="dark", fx="glass")


def test_cambio_de_tema_en_caliente_en_cada_pantalla(ui, H):
    for nombre, prep in pantallas(ui):
        ui.modal = None
        prep()
        for th in THEMES + ["dark"]:
            ui.cfg["pals"] = {}
            ui.set_look(theme=th)
            run(ui, 2)
            assert H.BG == H.THEMES[th]["BG"], (nombre, th)
        ui.modal = None
    ui.go_tab("home")


def test_toggle_tema_recorre_todos_y_vuelve(ui, H):
    ui.set_look(theme="limpio")
    vistos = []
    for _ in range(len(THEMES)):
        ui.toggle_theme()
        vistos.append(ui.cfg["theme"])
    assert vistos == THEMES[1:] + ["limpio"]


def test_tema_desconocido_no_rompe(ui, H):
    ui.set_look(theme="inventado")
    run(ui, 3)
    assert H.BG == H.THEMES["dark"]["BG"]
    ui.set_look(theme="dark")


# ── fuzz ────────────────────────────────────────────────────
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("semilla", [1, 2])
def test_fuzz_mando_no_rompe_ni_pierde_el_foco(ui, H, theme, semilla):
    rnd = random.Random(f"{theme}{semilla}")
    ui.set_look(theme=theme, fx="glass" if semilla == 1 else "perf")
    ui.adv_open = bool(semilla % 2 == 0)
    ui.modal = None
    ui.go_tab("home")
    historial = []
    for i in range(350):
        a = rnd.choice(ACTS)
        historial.append((a, ui.tab, ui.focus, bool(ui.modal)))
        try:
            ui.act(a)
            run(ui, 1)
            if i % 25 == 0:
                ui.go_tab(rnd.choice(["home", "games", "downloads", "settings", "library", "steam"]))
                run(ui, 2)
        except Exception as ex:  # noqa: BLE001
            pytest.fail(f"{theme}: {type(ex).__name__}: {ex} tras {historial[-12:]}")
        # el foco, si existe, apunta a un widget que está dibujado (en modales puede ser interno)
        if ui.focus is not None and not ui.modal and i % 10 == 0:
            run(ui, 1)
            claves = {w.key for w in ui.widgets}
            assert ui.focus in claves or not claves, f"{theme}: foco perdido ({ui.focus}) tab={ui.tab} tras {historial[-8:]}"
    ui.modal = None
    ui.go_tab("home")
    ui.set_look(theme="dark", fx="glass")
    ui.adv_open = False


def test_fuzz_con_toques_en_el_centro_de_cada_widget(ui, H):
    """Pulsa (cb) cada widget visible de cada pantalla una vez: ninguno debe lanzar excepción."""
    ui.set_look(theme="quiver", fx="perf")
    for nombre, prep in pantallas(ui):
        ui.modal = None
        prep()
        run(ui, 3)
        for w in list(ui.widgets)[:40]:
            if w.cb is None or str(w.key).startswith(("del", "upd", "tests", "trash_e")):
                continue
            try:
                w.cb()
                run(ui, 1)
            except Exception as ex:  # noqa: BLE001
                pytest.fail(f"{nombre}/{w.key}: {type(ex).__name__}: {ex}")
            ui.modal = None
            prep()
            run(ui, 2)
    ui.set_look(theme="dark", fx="glass")
    ui.go_tab("home")


def test_el_degradado_de_scroll_sigue_al_tema(ui, H):
    """Regresión: el degradado «Más abajo» se quedaba oscuro tras pasar al tema claro."""
    for th in ("dark", "light", "quiver", "dark"):
        ui.set_look(theme=th, fx="perf")
        ui.modal = None
        ui.adv_open = True
        ui.go_tab("settings")
        ui.touch = None
        v = ui.views.setdefault("settings", H.View())
        v.off, v.vel = 0.0, 0.0        # en un equipo lento la inercia de una prueba anterior seguía bajando la lista hasta el final (sin degradado)
        run(ui, 4)
        v = ui.views["settings"]
        assert v.h > v.rect.h
        assert v.off < v.h - v.rect.h - ui.n(10), ("la lista quedó al final: no hay degradado que comprobar", v.off, v.h, v.rect.h)
        px = tuple(ui.screen.get_at((v.rect.x + 6, v.rect.bottom - 3)))[:3]
        assert ratio(px, H.BG) < 1.6, f"{th}: el degradado inferior {px} no es del color del fondo {H.BG} (off {v.off:.0f})"
    ui.adv_open = False
    ui.set_look(theme="dark", fx="glass")


def test_prototipo_barra_lateral_y_coordenadas_globales(ui, H):
    """Con la barra lateral, el contenido se dibuja desplazado: los widgets deben quedar en coordenadas de pantalla (toque y mando)."""
    ui.set_look(theme="prototipo", fx="glass")
    ui.modal = None
    ui.go_tab("home")
    run(ui, 4)
    ox = ui.n(ui.SIDE_W)
    tabs = {w.key: w for w in ui.widgets if str(w.key).startswith("tab:")}
    assert set(tabs) == {"tab:home", "tab:games", "tab:downloads", "tab:settings"}
    assert all(w.rect.right <= ox for w in tabs.values())
    otros = [w for w in ui.widgets if w.key not in tabs and w.cb]
    assert otros and all(w.rect.x >= ox - 2 for w in otros), "hay contenido bajo la barra lateral"
    w = otros[0]
    assert ui._widget_at(w.rect.center).key == w.key        # el toque llega al widget correcto
    assert ui._widget_at(tabs["tab:games"].rect.center).key == "tab:games"
    tabs["tab:games"].cb()
    assert ui.tab == "games"
    ui.go_tab("home")


def test_prototipo_navegacion_con_cruceta_entra_y_sale_de_la_barra(ui, H):
    ui.set_look(theme="prototipo", fx="glass")
    ui.go_tab("settings")
    run(ui, 3)
    ui.focus = next(w.key for w in ui.widgets if w.key == "cat:look")      # v2.0: Ajustes abre con categorías
    for _ in range(6):
        ui.act("LEFT")
        run(ui, 1)
        if str(ui.focus).startswith("tab:"):
            break
    assert str(ui.focus).startswith("tab:"), "desde el contenido, IZQUIERDA debe llegar a la barra lateral"
    ui.act("RIGHT")
    run(ui, 1)
    assert not str(ui.focus).startswith("tab:") or ui.focus is None


def test_prototipo_inicio_con_juegos_muestra_heroe_y_tarjetas(ui, H, monkeypatch):
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda e: dict(real(e), installed=True, version="1.0", launcher_id=e["id"], dir="/tmp/x") if ui.entries.index(e) < 3 else real(e))
    ui.set_look(theme="prototipo", fx="glass")
    ui.go_tab("home")
    ui._inst_c = None
    run(ui, 4)
    ks = {w.key for w in ui.widgets}
    assert "hero" in ks and sum(1 for k in ks if str(k).startswith("home:")) == 3, ("modal abierto: " + str((ui.modal or {}).get("title"))) if ui.modal else sorted(map(str, ks))[:12]
    jugados = []
    monkeypatch.setattr(ui, "play", lambda e: jugados.append(e["id"]))
    next(w for w in ui.widgets if w.key == "hero").cb()
    assert len(jugados) == 1
