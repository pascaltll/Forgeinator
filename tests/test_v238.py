"""v2.38: temas como familias (paletas + fondos), inicios nuevos (verticales, mosaico, por plataforma, títulos) y pantalla de espera."""
import time

import pytest

pygame = pytest.importorskip("pygame")

from hub import themes_fam as T  # noqa: E402


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.cfg["pals"], u.cfg["bgs"] = {}, {}
    u.set_look(theme="dark", fx="glass")
    u.resize(1920, 1080)


def run(ui, n=3):
    for _ in range(n):
        ui.frame()


def _con_juegos(ui, monkeypatch, n):
    ents = ui.entries[:n]
    ids = {e["id"] for e in ents}
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="v1", launcher_id=x["id"]) if x["id"] in ids else real(x))
    return ents


def _todas():
    import hub.ui as H
    return [(f, p[0]) for f, v in T.FAMILIES.items() for p in v["pals"] if H]


def test_catorce_temas_con_paletas_y_fondos():
    assert len(T.FAMILIES) == 15 and "obsidian" in T.FAMILIES      # 14 heredados + Obsidian (v2.93: una sola paleta, sin fondo animado por diseño)
    for f, v in T.FAMILIES.items():
        if f == "obsidian":
            assert len(v["pals"]) == 1 and v["bgs"] == ["none"]
            continue
        assert len(v["pals"]) >= 3 and len(v["bgs"]) >= 3, f
        assert len({p[0] for p in v["pals"]}) == len(v["pals"])
        assert v["bgs"][-1] == "none"


@pytest.mark.parametrize("fam,pal", _todas())
def test_contraste_de_cada_paleta(fam, pal):
    import hub.ui as H
    t = T.build(H._LEG, fam, pal)
    pares = [("TXT", "BG", 6.0), ("TXT", "PANEL", 6.0), ("DIM", "BG", 3.8), ("DIM", "PANEL", 3.4), ("ACC", "BG", 3.0), ("ACC", "PANEL", 3.0)]
    malos = [f"{a}/{b}={ratio(t[a], t[b]):.1f}<{m}" for a, b, m in pares if ratio(t[a], t[b]) < m]
    assert not malos, f"{fam}/{pal}: {malos}"
    assert ratio(t.get("ON_ACC", (255, 255, 255)), t["ACC"]) >= 3.5, f"{fam}/{pal}: texto sobre acento"
    assert ratio(t["LINE"], t["BG"]) >= 1.15, f"{fam}/{pal}: contornos"
    for bg in T.FAMILIES[fam]["bgs"]:
        d = T.build(H._LEG, fam, pal, bg)
        assert d["ANIM"] == (None if bg == "none" else bg)


def test_nombres_antiguos_se_migran():
    assert T.normalize("dark") == ("limpio", "oscuro") and T.normalize("light") == ("limpio", "claro")
    assert T.normalize("aurora") == ("cristal", "aurora") and T.normalize("retro16") == ("pixel", "16bits")
    assert T.normalize("neon") == ("neon", "rosa") and T.normalize("???") == ("limpio", "oscuro")
    assert T.normalize("limpio", "no-existe") == ("limpio", "claro")


def test_paleta_y_fondo_se_guardan_por_tema(ui):
    import hub.ui as H
    ui.cfg["pals"], ui.cfg["bgs"] = {}, {}
    ui.set_look(theme="dark")
    assert (ui.cfg["theme"], H.PAL, H.FAMILY) == ("limpio", "oscuro", "limpio")
    ui.pick_pal("oceano")
    assert H.PAL == "oceano" and ui.cfg["pals"]["limpio"] == "oceano"
    ui.pick_bg("drift")
    assert H.ANIM == "drift" and ui.cfg["bgs"]["limpio"] == "drift"
    ui.pick_bg("none")
    assert H.ANIM is None
    ui.pick_theme("neon")
    assert H.FAMILY == "neon" and H.PAL == "rosa" and H.ANIM == "gridrun"
    ui.pick_theme("limpio")
    assert H.PAL == "oceano", "al volver a un tema se recupera la paleta que tenía"
    ui.pick_pal("claro")
    assert (H.PAL, H.ANIM) == ("claro", "motes"), "cambiar de paleta recupera el fondo propio de la paleta"
    ui.set_look(theme="aurora")
    assert (H.FAMILY, H.PAL, H.ANIM, H.FONT) == ("cristal", "aurora", "aurora", "poppins")


def test_ajustes_ofrece_paletas_y_fondos(ui):
    import hub.ui as H
    ui.set_look(theme="cristal")
    ui.go_tab("settings")
    ui.set_page = "look"
    run(ui)
    keys = {w.key for w in ui.widgets}
    assert {f"theme:{t}" for t in H.THEME_ORDER} <= keys
    assert {f"pal:{p[0]}" for p in T.FAMILIES["cristal"]["pals"]} <= keys
    assert {f"bg:{b}" for b in T.FAMILIES["cristal"]["bgs"]} <= keys
    ui.set_page = None


@pytest.mark.parametrize("n", [0, 1, 9])
def test_todos_los_temas_y_paletas_dibujan_inicio(ui, monkeypatch, n):
    import hub.ui as H
    ents = _con_juegos(ui, monkeypatch, n)
    for fam, v in T.FAMILIES.items():
        for pal in (v["pals"][0][0], v["pals"][-1][0]):
            ui.cfg["pals"] = {}
            ui.set_look(theme=fam, pal=pal, fx="glass")
            ui.tab = "home"
            ui.focus = None
            run(ui)
            keys = {x.key for x in ui.widgets}
            assert {f"home:{e['id']}" for e in ents} <= keys or fam == "prototipo" and n and any(k.startswith("home:") for k in keys), (fam, pal, n)
    ui.resize(1280, 720)
    run(ui)
    ui.resize(1920, 1080)


def test_mosaico_no_superpone_teselas(ui, monkeypatch):
    ents = _con_juegos(ui, monkeypatch, 12)
    ui.set_look(theme="cristal", fx="glass")
    ui.tab = "home"
    run(ui)
    rs = [w.rect for w in ui.widgets if w.key.startswith("home:")]
    assert len(rs) >= len(ents) - 1
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            assert not a.colliderect(b), (a, b)
    assert max(r.w for r in rs) > 2 * min(r.w for r in rs), "una tesela grande"


def test_portadas_verticales_en_los_temas_pedidos(ui, monkeypatch):
    _con_juegos(ui, monkeypatch, 6)
    for fam, pal in (("onda", None), ("tarjeta", None), ("interruptor", None), ("pixel", "8bits"), ("pixel", "16bits")):
        ui.cfg["pals"] = {}
        ui.set_look(theme=fam, pal=pal, fx="glass")
        ui.tab = "home"
        ui.focus = None
        run(ui)
        rs = [w.rect for w in ui.widgets if w.key.startswith("home:")]
        assert rs and all(r.h > r.w for r in rs), (fam, pal, [(r.w, r.h) for r in rs][:3])


def test_neon_agrupa_por_plataforma(ui, monkeypatch):
    ents = _con_juegos(ui, monkeypatch, 8)
    ui.set_look(theme="neon", fx="glass")
    ui.tab = "home"
    run(ui)
    ys = [(w.rect.y, w.key) for w in ui.widgets if w.key.startswith("home:")]
    assert len(ys) == len(ents)
    plats = [ui._hl_plat(next(e for e in ents if f"home:{e['id']}" == k)) or "OTROS" for _, k in sorted(ys)]
    assert plats == sorted(plats), "las filas quedan juntas por plataforma"


def test_las_disposiciones_usan_el_nombre_del_juego(ui, monkeypatch):
    import hub.ui as H
    e = {"id": "x", "name": "Proyecto Raro", "platform": "N64"}
    monkeypatch.setattr(H.gamedict, "game_name", lambda ent: "The Legend of Zelda")
    assert ui._hl_title(e) == "The Legend of Zelda"
    monkeypatch.setattr(H.gamedict, "game_name", lambda ent: None)
    assert ui._hl_title(e) == "Proyecto Raro"


def test_pantalla_de_espera_se_dibuja_en_cada_tema(ui, monkeypatch):
    import hub.ui as H
    ents = _con_juegos(ui, monkeypatch, 2)

    class Pr:
        pid = 1

        def poll(self):
            return None
    for fam in T.ORDER:
        ui.set_look(theme=fam, fx="glass")
        ui.play_pr, ui.play_t, ui.play_id, ui.play_name, ui.play_eid = Pr(), time.time() - 1, ents[0]["id"], ents[0]["name"], ents[0]["id"]
        ui.play_win = fam == "pixel"
        run(ui, 2)
        ui.play_pr = None
    run(ui)
    assert H.FAMILY == T.ORDER[-1]
