"""v2.02: descargas con peso y velocidad aunque el servicio no los mande bien, zona de descargas en dos secciones,
todos los temas a las medidas del prototipo y ningún botón por debajo de 7 mm."""
import time

import pytest

pygame = pytest.importorskip("pygame")

from conftest import report_section
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, pantallas, run  # noqa: F401


# ── velocidad y tamaño de los trabajos del catálogo ──────────────────
def test_velocidad_se_calcula_aqui_si_el_servicio_manda_0(monkeypatch):
    from hub import catalogjobs
    j = catalogjobs.CatalogJob("a", "Juego", size=0)
    t = [1000.0]
    monkeypatch.setattr(catalogjobs.time, "time", lambda: t[0])
    j.apply({"state": "running", "total_bytes": 100_000_000, "downloaded": 10_000_000, "bytes_per_s": 0})
    assert j.size == 100_000_000 and j.done == 10_000_000 and j.speed == 0
    t[0] += 2
    j.apply({"state": "running", "total_bytes": 100_000_000, "downloaded": 30_000_000, "bytes_per_s": 0})   # el fallo del servicio: siempre 0
    assert j.speed == pytest.approx(10_000_000)
    assert j.eta() == pytest.approx(7.0)
    t[0] += 2
    j.apply({"state": "running", "total_bytes": 100_000_000, "downloaded": 30_000_000, "bytes_per_s": 0})   # un intervalo sin datos no la tira a 0 de golpe
    assert 0 < j.speed < 10_000_000


def test_si_el_servicio_da_velocidad_se_usa_la_suya():
    from hub import catalogjobs
    j = catalogjobs.CatalogJob("b", "Juego")
    j.apply({"state": "running", "size": 50, "downloaded": 10, "bytes_per_s": 1234})
    assert j.speed == 1234


def test_tamano_como_texto_y_por_progreso():
    from hub import catalogjobs
    j = catalogjobs.CatalogJob("c", "Juego")
    j.apply({"state": "running", "size": "2 GB", "progress": 0.25})
    assert j.size == 2 * 1024 ** 3 and j.done == j.size // 4


def test_navegador_velocidad_media_sin_caer_a_0(tmp_path):
    from hub import dlwatch
    w = dlwatch.DLWatch([tmp_path])
    f = tmp_path / "juego.iso.part"
    f.write_bytes(b"x" * 1000)
    w.poll(now=100.0)
    f.write_bytes(b"x" * 3000)
    w.poll(now=101.0)
    a = next(iter(w.active.values()))
    assert a["speed"] == pytest.approx(2000)
    w.poll(now=102.0)                       # el navegador no escribió en este segundo
    assert a["speed"] == pytest.approx(1000)  # media de los últimos ~3 s, no 0


# ── zona de descargas ───────────────────────────────────────────────
class _D:
    def __init__(s, i, st, p, t, size=8e8):
        s.id, s.state, s.progress, s.meta, s.name, s.url = i, st, p, {"title": t}, t, "u"
        s.speed, s.size = (3e6 if st == "active" else 0), size
        s.done = int(p * size) if size else 123_000_000
        s.error, s.verified, s.catalog = "", st == "done", False

    def eta(s):
        return 60 if s.size else None


def _textos(ui):
    from hub import layoutdump
    return layoutdump.capture(ui, 3)


@pytest.mark.parametrize("theme", ["prototipo", "dark"])
def test_descargas_en_curso_y_terminadas_con_peso(H, ui, theme):
    ui.set_look(theme=theme, fx="perf")
    ds = [_D(1, "active", .4, "Juego A"), _D(2, "active", 0, "Juego B", size=0), _D(3, "done", 1, "Juego C")]
    orig = ui.mgr.list
    ui.mgr.list = lambda: ds
    try:
        ui.resize(1920, 1080)
        ui.go_tab("downloads")
        cap = _textos(ui)
        ts = [t["s"] for t in cap["texts"]]
        joined = "\n".join(ts)
        assert "En curso" in joined and "Terminadas" in joined
        assert any("faltan" in s for s in ts), ts          # «320 MB de 800 MB · faltan 480 MB»
        assert any("el tamaño total aún no se sabe" in s for s in ts)
        assert ts.index(next(s for s in ts if "En curso" in s)) < ts.index(next(s for s in ts if "Terminadas" in s))
        for w in cap["widgets"]:
            if w["key"] in ("clear", "addurl") or w["key"].endswith((":m", ":x")):
                assert w["rect"].h >= ui.n(70), w
    finally:
        ui.mgr.list = orig
        ui.resize(1280, 800)


# ── medidas de todos los temas ──────────────────────────────────────
@pytest.mark.parametrize("w,h", [(1280, 720), (1920, 1080)])
@pytest.mark.parametrize("theme", ["prototipo", "dark", "light"])
def test_ningun_boton_por_debajo_de_7mm_ni_botones_que_se_pisan(H, ui, theme, w, h):
    from hub import layoutdump
    if theme not in H.THEMES:
        pytest.skip(f"sin tema {theme}")
    ui.resize(w, h)
    try:
        ui.set_look(theme=theme, fx="perf")
        fallos, filas = [], []
        for nombre, preparar in pantallas(ui):
            preparar()
            run(ui, 2)
            def medir():
                cap = layoutdump.capture(ui, 2)
                ws = [x for x in cap["widgets"] if x["rect"].w > 0 and x["rect"].h > 0 and not x["key"].endswith(":m") and not x["key"].endswith(":x")]
                pis = [(p["key"], q["key"]) for i, p in enumerate(ws) for q in ws[i + 1:]
                       if (lambda c: c.w > 2 and c.h > 2)(p["rect"].clip(q["rect"]))
                       and not (p["rect"].contains(q["rect"]) or q["rect"].contains(p["rect"]))]
                return cap, ws, pis
            cap, ws, pis = medir()
            if pis:                      # puede ser la animación de entrada de las tarjetas a medio camino: se mide otra vez al terminar
                for _ in range(40):
                    time.sleep(0.03)
                    ui.frame()
                cap, ws, pis = medir()
            a = layoutdump.analyze(ui, cap)
            if a["small_targets"]:
                fallos.append((nombre, "pequeños", a["small_targets"][:6]))
            if pis:
                fallos.append((nombre, "se pisan", pis[:6]))
            justos = sorted((round(layoutdump._mm(min(x["rect"].w, x["rect"].h), cap["size"][0]), 2), x["key"]) for x in ws)
            justos = [j for j in justos if j[0] < 7.2]
            if justos:                           # margen: en el Ally la misma pantalla puede medir unas décimas menos
                fallos.append((nombre, "por debajo de 7,2 mm", justos[:6]))
            filas.append(f"| {nombre} | {len(cap['widgets'])} | {min((round(layoutdump._mm(min(x['rect'].w, x['rect'].h), cap['size'][0]), 1) for x in ws), default='-')} mm |")
        report_section(f"Medidas táctiles · tema {theme} · {w}×{h}", "| pantalla | botones | el más pequeño |\n|---|---|---|\n" + "\n".join(filas))
        assert not fallos, fallos
    finally:
        ui.resize(1280, 800)


def test_todos_los_temas_tienen_la_escala_del_prototipo(H):
    for name in H.THEMES:
        assert H.THEMES[name].get("SCALE", 1.25) >= 1.25 or name == "prototipo", name
