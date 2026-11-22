"""Calidad medida en TU equipo: cuánto tarda en dibujarse cada pantalla y si algún texto REAL de tu catálogo (nombres y notas de tus listas
importadas) tiene caracteres que tu fuente no puede dibujar (los rectángulos). Todo sale en data/tests/informe.md."""
import json
import statistics
import time

import pytest

from conftest import HUB_SRC, report_section
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")
BUDGET_MS = 1000 / 45          # Hub dibuja a 45 fps
DISASTER_MS = 250              # por encima, la pantalla se nota congelada: eso sí es un fallo


def _pantallas(ui):
    def home():
        ui.go_tab("home")

    def cats():
        ui.go_tab("games")
        ui.explore = "cats"

    def lista():
        ui.go_tab("games")
        ui.filter, ui.query, ui.explore = "Todos", "", "list"

    def dl():
        ui.go_tab("downloads")

    def ajustes():
        ui.go_tab("settings")
        ui.adv_open = False

    def avanzado():
        ui.go_tab("settings")
        ui.adv_open = True

    def ficha():
        ui.go_tab("games")
        ui.open_detail(ui.entries[0])
    return [("inicio", home), ("explorar", cats), ("lista", lista), ("descargas", dl), ("ajustes", ajustes), ("ajustes avanzado", avanzado), ("ficha", ficha)]


def _energia_real():
    """TDP, batería y CPU de ESTE equipo ahora (de /sys real, no del aislado de las pruebas)."""
    from pathlib import Path
    from hub import power
    old = power.ROOT
    power.ROOT = Path("/sys")
    try:
        return power.snapshot()
    finally:
        power.ROOT = old


HIST = HUB_SRC / "data" / "tests" / "rendimiento.jsonl"


def _guardar_y_comparar(theme, filas_ms, energia):
    """Añade esta medición al historial (data/tests/rendimiento.jsonl) y compara con la última de cada TDP distinto."""
    rec = {"t": time.strftime("%Y-%m-%d %H:%M"), "theme": theme, "tdp": energia.get("tdp_w"), "bat": (energia.get("battery") or {}).get("pct"),
           "p95": {n: round(p, 1) for n, _, p in filas_ms}}
    hist = []
    try:
        HIST.parent.mkdir(parents=True, exist_ok=True)
        hist = [json.loads(ln) for ln in HIST.read_text().splitlines() if ln.strip()] if HIST.exists() else []
        hist = (hist + [rec])[-200:]
        HIST.write_text("\n".join(json.dumps(h, ensure_ascii=False) for h in hist) + "\n")
    except (OSError, ValueError):
        hist = [rec]
    ult = {}
    for h in hist:
        if h.get("theme") == theme:
            ult[h.get("tdp")] = h
    if len(ult) < 2:
        return "Para comparar, repite `bin/hub-tests` con otro TDP (p. ej. 7 W y 13 W): aquí saldrá una tabla con los dos."
    cols = sorted(ult, key=lambda x: (x is None, x or 0))
    head = "| pantalla | " + " | ".join(f"TDP {c:g} W ({ult[c]['t'][5:]})" if c else "TDP ?" for c in cols) + " |"
    sep = "|---|" + "---|" * len(cols)
    names = list(rec["p95"])
    rows = [f"| {n} | " + " | ".join(str(ult[c]["p95"].get(n, "—")) for c in cols) + " |" for n in names]
    return "p95 en ms, la última medición con cada TDP:\n\n" + "\n".join([head, sep] + rows)


def medir_pantallas(ui, n=20):
    """[(pantalla, mediana_ms, p95_ms)] dibujando cada pantalla n veces (tras calentar cachés)."""
    out = []
    for nombre, ir in _pantallas(ui):
        ui.modal = None
        ir()
        run(ui, 6)
        ms = []
        for _ in range(n):
            t0 = time.perf_counter()
            ui.draw()
            ms.append((time.perf_counter() - t0) * 1000)
        out.append((nombre, statistics.median(ms), sorted(ms)[int(len(ms) * 0.95) - 1]))
    ui.adv_open = False
    return out


@pytest.mark.parametrize("theme", ["prototipo", "dark", "cristal"])
def test_tiempo_de_dibujo_de_cada_pantalla(ui, theme):
    ui.set_look(theme=theme, fx="glass")
    filas, lentas, crudo = [], [], []
    energia = _energia_real()
    from hub import power
    for nombre, ir in _pantallas(ui):
        ui.modal = None
        ir()
        run(ui, 6)                                   # calentar cachés (fuentes, portadas, textos)
        ms = []
        for _ in range(20):
            t0 = time.perf_counter()
            ui.draw()
            ms.append((time.perf_counter() - t0) * 1000)
        med, p95 = statistics.median(ms), sorted(ms)[int(len(ms) * 0.95) - 1]
        marca = "" if p95 <= BUDGET_MS else "  ← más de 22 ms: puede bajar de 45 fps"
        filas.append(f"| {nombre} | {med:.1f} | {p95:.1f} |{marca}")
        crudo.append((nombre, med, p95))
        if p95 > DISASTER_MS:
            lentas.append((nombre, round(p95)))
    w, h = ui.screen.get_size()
    modo = "AHORRO" if power.saving("auto", energia) else "normal"
    report_section(f"Rendimiento · tema {theme} · {w}×{h}",
                   f"Energía ahora: {power.describe(energia)} → Hub usaría el modo {modo} (en automático).\n\n"
                   "Milisegundos por fotograma, medidos en este equipo (presupuesto: 22 ms para 45 fps; en modo ahorro, 33 ms para 30 fps).\n\n"
                   "| pantalla | mediana | p95 |\n|---|---|---|\n" + "\n".join(filas) + "\n\n" + _guardar_y_comparar(theme, crudo, energia))
    ui.adv_open = False
    assert not lentas, f"pantallas que tardan más de {DISASTER_MS} ms por fotograma: {lentas}"


def _textos_reales():
    """Nombres, plataformas y notas de TUS listas (data/imports, catalog.local.json), solo lectura. En el entorno de pruebas aislado no existen."""
    out = []
    d = HUB_SRC / "data"
    for f in sorted((d / "imports").glob("*.json")) + [d / "catalog.local.json"]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        items = data if isinstance(data, list) else data.get("games") or data.get("apps") or []
        for x in items:
            if isinstance(x, dict):
                for k in ("name", "title", "game", "platform", "notes", "description"):
                    if isinstance(x.get(k), str):
                        out.append((f.name, x[k]))
    return out


def test_ningun_texto_real_del_catalogo_sale_como_rectangulo(ui):
    from hub import catalog
    textos = _textos_reales() + [("catálogo", f"{e['name']} {e.get('platform', '')} {e.get('notes', '')}") for e in catalog.load()]
    malos = {}
    for src, t in textos:
        for ch in ui.sane(t):
            if ord(ch) > 127 and not ui.has_glyph(ch):
                malos.setdefault(ch, (src, t[:60]))
    subs = dict(list(ui.glyph_subs.items())[:20]) if getattr(ui, "glyph_subs", None) else {}
    report_section("Caracteres de tu catálogo",
                   f"{len(textos)} textos revisados (de {len({s for s, _ in textos})} fuentes). " +
                   (f"Sin glifo en tu fuente tras limpiarlos: {', '.join(f'U+{ord(c):04X} «{c}» ({s}: {e!r})' for c, (s, e) in malos.items())}" if malos
                    else "Todos se pueden dibujar.") +
                   (f"\nSustituidos al dibujar (no salen como rectángulo): {subs}" if subs else ""))
    assert not malos, f"saldrían como rectángulo: {[f'U+{ord(c):04X}' for c in malos]}"


def test_modo_ahorro_por_tdp_o_bateria(tmp_path, monkeypatch):
    from hub import power
    root = tmp_path / "sys"
    a = root / "devices/platform/asus-nb-wmi"
    a.mkdir(parents=True)
    (a / "ppt_pl1_spl").write_text("7\n")
    b = root / "class/power_supply/BAT0"
    b.mkdir(parents=True)
    (b / "capacity").write_text("80\n")
    (b / "status").write_text("Discharging\n")
    monkeypatch.setattr(power, "ROOT", root)
    s = power.snapshot()
    assert s["tdp_w"] == 7 and s["battery"] == {"pct": 80, "charging": False}
    assert power.saving("auto", s) and not power.saving("perf", s) and power.saving("save", {})
    (a / "ppt_pl1_spl").write_text("13\n")
    assert not power.saving("auto", power.snapshot())
    (b / "capacity").write_text("20\n")
    assert power.saving("auto", power.snapshot()), "batería baja y desenchufado"
    assert "TDP 13 W" in power.describe(power.snapshot())


def test_en_ahorro_baja_los_fps_y_quita_animaciones(ui, monkeypatch):
    monkeypatch.setattr(ui, "power_saving", lambda: True)
    ui.set_look(theme="prototipo", fx="perf")
    ui.go_tab("home")
    ui.modal, ui.toast_t = None, 0
    ui.held.clear()
    ui.t_act = time.time()
    assert ui.target_fps() == 30
    ui.t_act = 0
    assert ui.target_fps() == 15
    ui._ex_seen = None
    assert ui.enter(0, "x") == 0
    monkeypatch.setattr(ui, "power_saving", lambda: False)
    ui.t_act = time.time()
    assert ui.target_fps() == 45


def medir_navegacion(ui):
    """Como la prueba de fluidez de QAM Rail, pero con la cruceta de Hub: recorre secciones, categorías de Ajustes, la lista de Ajustes,
    Explorar y una ficha. Para cada pulsación mide lo que tarda Hub en reaccionar y dibujar el fotograma siguiente, y cuántos fotogramas
    tarda en asentarse el desplazamiento suave. Devuelve {acción: [ms…]} y {acción: [fotogramas…]}."""
    ms, fr = {}, {}
    suave, ui.smooth_scroll = ui.smooth_scroll, True      # como en el Ally

    def paso(nombre, accion, n=1):
        for _ in range(n):
            t0 = time.perf_counter()
            ui.act(accion)
            ui.frame()
            ms.setdefault(nombre, []).append((time.perf_counter() - t0) * 1000)
            k = 1
            while any(v.target is not None for v in ui.views.values()) and k < 60:
                ui.frame()
                k += 1
            fr.setdefault(nombre, []).append(k)

    ui.modal = None
    ui.go_tab("home")
    run(ui, 3)
    paso("cambiar de sección (RB)", "RB", 3)
    ui.go_tab("settings")
    ui.set_page, ui.adv_open = None, False
    run(ui, 3)
    for c in ("look", "play", "files", "maint"):
        ui.focus = "cat:" + c
        paso("abrir categoría de Ajustes (A)", "A")
        paso("volver (B)", "B")
    ui.adv_open = True
    ui.focus = None
    run(ui, 2)
    paso("bajar por Ajustes (lista completa)", "DOWN", 25)
    paso("subir por Ajustes (lista completa)", "UP", 10)
    ui.adv_open = False
    ui.go_tab("games")
    ui.explore = "cats"
    run(ui, 3)
    ui.focus = next((w.key for w in ui.widgets if str(w.key).startswith("cat:")), None)
    paso("abrir una consola en Explorar (A)", "A")
    paso("bajar por la lista de juegos", "DOWN", 20)
    ui.focus = next((w.key for w in ui.widgets if str(w.key).startswith("card:") and w.key == ui.focus), ui.focus)
    paso("abrir la ficha de un juego (A)", "A")
    paso("bajar por la ficha", "DOWN", 8)
    paso("volver (B)", "B", 2)
    ui.smooth_scroll = suave
    return ms, fr


def tabla_navegacion(ms, fr):
    filas = []
    for k, xs in ms.items():
        s = sorted(xs)
        p95 = s[min(len(s) - 1, int(len(s) * 0.95))]
        f = statistics.median(fr.get(k) or [1])
        filas.append(f"| {k} | {len(xs)} | {statistics.median(xs):.1f} | {p95:.1f} | {f:g} |" + ("  ← lento" if p95 > 33 else ""))
    return ("| acción | veces | reacción mediana ms | p95 ms | fotogramas hasta asentarse |\n|---|---|---|---|---|\n" + "\n".join(filas) +
            "\n\nReacción = de la pulsación al fotograma dibujado (sin pantalla real: es el coste de CPU). El desplazamiento suave tarda unos "
            "6–8 fotogramas (~0,15 s) a propósito; en modo ahorro es directo.")


@pytest.mark.parametrize("theme", ["prototipo", "dark", "cristal"])
def test_navegacion_con_la_cruceta_reaccion_y_fluidez(ui, theme):
    ui.set_look(theme=theme, fx="glass")
    ms, fr = medir_navegacion(ui)
    energia = _energia_real()
    from hub import power
    report_section(f"Navegación con la cruceta · tema {theme}", f"Energía: {power.describe(energia)}\n\n" + tabla_navegacion(ms, fr))
    peor = max(max(v) for v in ms.values())
    ui.set_page, ui.adv_open = None, False
    ui.go_tab("home")
    assert peor < 250, f"alguna pulsación tardó {peor:.0f} ms en dibujarse"
