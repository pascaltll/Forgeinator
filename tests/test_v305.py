"""v3.05 · upgrade de temas, fase B: Minimal y Showcase con Explorar y Descargas propios; los demás, como siempre."""
import pygame

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from hub import downloads
from hub.themes import studio, legacy


def _dls():
    out = []
    for i, (st, prog, nm) in enumerate((("active", 0.42, "ReStreet-2.1.5-Setup.exe"), ("queued", 0, "BT3-Latino.zip"),
                                         ("paused", 0.7, "GTA-VCS-windows.zip"), ("done", 1.0, "CTR-Turbocharged.AppImage"))):
        d = downloads.Download(f"x{i}", "https://x/" + nm, "/tmp", nm, meta={"title": nm})
        d.state, d.size = st, 1000
        d.done = int(1000 * prog)
        d.speed = 5_000_000 if st == "active" else 0
        out.append(d)
    return out


def _dibuja(ui, monkeypatch, theme, tab):
    monkeypatch.setattr(ui.mgr, "list", _dls)
    ui.modal = ui.detail = None
    ui.set_look(theme=theme, fx="perf")
    ui.go_tab(tab)
    if tab == "games":
        ui.explore, ui.filter, ui.query = "list", "Todos", ""
    run(ui, 3)
    return {w.key: w for w in ui.widgets}


def test_studio_declara_pantallas_solo_donde_hay_dibujo():
    assert studio.build("v3:minimal")["SCREENS"] == {"explore": "posters", "downloads": "rows"}
    assert studio.build("v3:showcase")["SCREENS"] == {"explore": "shelf_big", "downloads": "featured"}
    assert all(studio.build("v3:" + p)["SCREENS"] for p in studio.ORDER) and "SCREENS" not in legacy.build("limpio")


def test_minimal_descargas_en_filas_a_todo_el_ancho(ui, monkeypatch):
    w = _dibuja(ui, monkeypatch, "v3:minimal", "downloads")
    rs = [w[f"dl:x{i}"].rect for i in range(4)]
    assert len({r.x for r in rs}) == 1 and all(r.w > ui.W * 0.8 for r in rs)


def test_showcase_descarga_activa_protagonista(ui, monkeypatch):
    w = _dibuja(ui, monkeypatch, "v3:showcase", "downloads")
    a, q = w["dl:x0"].rect, w["dl:x1"].rect
    assert a.w > ui.W * 0.8 and a.h > q.h and q.w < ui.W * 0.6 and q.top > a.bottom


def test_heredados_descargas_igual_que_siempre(ui, monkeypatch):
    w = _dibuja(ui, monkeypatch, "limpio", "downloads")
    a, p_ = w["dl:x0"].rect, w["dl:x2"].rect                 # se ordenan por estado: activa, pausada, en cola…
    assert a.w == p_.w < ui.W * 0.6 and a.y == p_.y and p_.x > a.x            # dos columnas


def test_explorar_portadas_verticales(ui, monkeypatch):
    for th, lo, hi in (("v3:minimal", 4, 7), ("v3:showcase", 3, 5), ("v3:flow", 3, 7)):
        w = _dibuja(ui, monkeypatch, th, "games")
        cards = sorted((x.rect for k, x in w.items() if k.startswith("card:")), key=lambda r: (r.y, r.x))
        assert cards and cards[0].h > cards[0].w                                   # verticales
        cols = len({r.x for r in cards})                                           # la entrada escalonada desplaza en vertical, no en horizontal
        assert lo <= cols <= hi, (th, cols)
    w = _dibuja(ui, monkeypatch, "limpio", "games")
    c = next(x.rect for k, x in w.items() if k.startswith("card:"))
    assert c.w > c.h                                                               # heredado: la ficha apaisada de siempre
    ui.set_look(theme="limpio", fx="glass")


def test_navegacion_con_mando_en_las_variantes(ui, monkeypatch):
    for th, tab in (("v3:minimal", "games"), ("v3:showcase", "downloads"), ("v3:showcase", "games")):
        _dibuja(ui, monkeypatch, th, tab)
        for d in ((0, 1), (1, 0), (0, 1), (-1, 0)):
            ui.nav(d)
            run(ui, 1)
        assert ui.focus is not None, (th, tab)
    ui.set_look(theme="limpio", fx="glass")


# ── v3.06: Flow, Glass y Showcase con estantes ──
def test_estantes_una_fila_por_consola_y_ver_todos(ui, monkeypatch):
    w = _dibuja(ui, monkeypatch, "v3:flow", "games")
    cards = [x for k, x in w.items() if k.startswith("card:")]
    plats = {}
    for x in cards:
        e = ui.entry(x.key[5:].split("#")[0])
        plats.setdefault(e["platform"] or "Otros", set()).add(x.rect.y)
    assert all(len(ys) == 1 for ys in plats.values()), plats          # cada consola, en una sola fila
    mas = [x for k, x in w.items() if k.startswith("shelf:")]
    if mas:
        p = mas[0].key[6:]
        mas[0].cb()
        assert ui.filter == p
    ui.filter = "Todos"
    ui.set_look(theme="limpio", fx="glass")


def test_mosaico_con_grandes_y_sin_solapes(ui, monkeypatch):
    w = _dibuja(ui, monkeypatch, "v3:glass", "games")
    rs = [x.rect for k, x in w.items() if k.startswith("card:")]
    assert len({(r.w, r.h) for r in rs}) >= 2 if len(rs) > 1 else True    # al menos dos tamaños
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            assert not a.colliderect(b), (a, b)
    ui.set_look(theme="limpio", fx="glass")


def test_barra_grande_en_descargas_anchas(ui, monkeypatch):
    import hub.ui as Hm
    for th in ("v3:flow", "v3:showcase"):
        w = _dibuja(ui, monkeypatch, th, "downloads")
        r = w["dl:x0"].rect
        assert r.w > ui.W * 0.8
        hits = [ui.screen.get_at((x, y))[:3] for y in range(r.bottom - ui.n(80), r.bottom - ui.n(20)) for x in range(r.x + ui.n(180), r.x + ui.n(260), 4)]
        assert Hm.ACC in hits, th                                          # el tramo hecho de la barra, con el color de la descarga activa
    ui.set_look(theme="limpio", fx="glass")


# ── v3.07: Arcade y Terminal ──
def test_arcade_portadas_numeradas_y_barra_por_bloques(ui, monkeypatch):
    import hub.ui as Hm
    textos = []
    real = ui.text
    monkeypatch.setattr(ui, "text", lambda s, *a, **k: (textos.append(str(s)), real(s, *a, **k))[1])
    w = _dibuja(ui, monkeypatch, "v3:arcade", "games")
    assert "01" in textos and "02" in textos
    cards = [x.rect for k, x in w.items() if k.startswith("card:")]
    assert cards and cards[0].h > cards[0].w
    w = _dibuja(ui, monkeypatch, "v3:arcade", "downloads")
    r = w["dl:x0"].rect
    assert r.w < ui.W * 0.6                                                  # misma rejilla de dos columnas
    fila = [ui.screen.get_at((x, y))[:3] for y in range(r.y + ui.n(116), r.y + ui.n(132)) for x in range(r.x + ui.n(150), r.right - ui.n(30), 3)]
    assert Hm.ACC in fila                                                     # bloques hechos
    ui.set_look(theme="limpio", fx="glass")


def test_terminal_catalogo_de_texto_y_procesos(ui, monkeypatch):
    textos = []
    real = ui.text
    monkeypatch.setattr(ui, "text", lambda s, *a, **k: (textos.append(str(s)), real(s, *a, **k))[1])
    w = _dibuja(ui, monkeypatch, "v3:terminal", "games")
    cards = [x.rect for k, x in w.items() if k.startswith("card:")]
    assert cards and all(r.w > ui.W * 0.8 and r.h >= ui.n(72) for r in cards)   # una línea por juego, tocable (≥ 7,2 mm)
    assert any(t.startswith("== ") and t.endswith(" ==") for t in textos) and any(t.strip().endswith("001") for t in textos)
    textos.clear()
    w = _dibuja(ui, monkeypatch, "v3:terminal", "downloads")
    assert all(w[f"dl:x{i}"].rect.w > ui.W * 0.8 for i in range(4))
    assert any(t.startswith("[") and "#" in t and t.endswith("%") for t in textos)
    ui.set_look(theme="limpio", fx="glass")



# ── v3.08: Editorial y Brutalist ──
def test_editorial_indice_y_tabla(ui, monkeypatch):
    textos = []
    real = ui.text
    monkeypatch.setattr(ui, "text", lambda s, *a, **k: (textos.append((str(s), a[2] if len(a) > 2 else k.get("size"))), real(s, *a, **k))[1])
    w = _dibuja(ui, monkeypatch, "v3:editorial", "games")
    cards = [x.rect for k, x in w.items() if k.startswith("card:")]
    assert cards and all(r.w > ui.W * 0.8 and r.h >= ui.n(72) for r in cards)
    assert any(t.endswith(" juegos") or t.endswith(" juego") for t, _ in textos)
    w = _dibuja(ui, monkeypatch, "v3:editorial", "downloads")
    assert all(w[f"dl:x{i}"].rect.w > ui.W * 0.8 for i in range(4))
    ui.set_look(theme="limpio", fx="glass")


def test_brutalist_bloques_de_dos_tamanos_y_sin_solapes(ui, monkeypatch):
    w = _dibuja(ui, monkeypatch, "v3:brutalist", "games")
    rs = [x.rect for k, x in w.items() if k.startswith("card:")]
    assert len({r.w for r in rs}) >= 2 if len(rs) > 1 else True
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            assert not a.colliderect(b)
    w = _dibuja(ui, monkeypatch, "v3:brutalist", "downloads")
    assert w["dl:x0"].rect.h >= ui.n(260)
    ui.set_look(theme="limpio", fx="glass")
