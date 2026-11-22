"""v2.97 · Estudio de temas (prueba): 8 identidades del motor nuevo, adaptador Appearance → Hub, Ajustes, persistencia y peticiones."""
import json

import pytest

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from hub import themes_fam as tf
from hub.themes import studio, legacy, appearance_request as ar
from hub.themes.registry import PRESETS

IDS = [studio.PREFIX + p for p in studio.ORDER]
COMBOS = [(n, pal) for n in IDS for pal in studio.palettes(n)]
MATRIZ = {"minimal": ("posters", "obsidian", "solid"), "showcase": ("hero", "ocean", "solid"), "glass": ("mosaic", "ocean", "glass"),
          "flow": ("xmb", "ocean", "soft"), "arcade": ("slots", "neon", "arcade"), "terminal": ("list", "lcd", "outline"),
          "editorial": ("list", "paper", "paper"), "brutalist": ("blocks", "neon", "outline")}
SONIDO = {"minimal": "soft", "showcase": "glass", "glass": "glass", "flow": "silk", "arcade": "chip", "terminal": "click", "editorial": "wood", "brutalist": "click"}


def test_matriz_del_documento():
    for p, (lay, pal, mat) in MATRIZ.items():
        pr = PRESETS[p]
        assert (pr.default_layout, pr.default_palette, pr.default_material) == (lay, pal, mat), p
        a = studio.appearance(studio.PREFIX + p)
        assert a["layout"]["studio"] == lay and a["palette"] == pal and a["studio"]["engine"]["appearance"]["material"] == mat
        assert a["audio"]["profile"] == SONIDO[p]


@pytest.mark.parametrize("n,pal", COMBOS)
def test_cada_combinacion_da_un_tema_completo_y_legible(n, pal):
    d = studio.build(n, pal)
    for k in tf.COLOR_KEYS[:13]:
        assert k in d and len(d[k]) == 3, (n, pal, k)
    assert legacy.check_contrast(d) == [], (n, pal)
    assert d["FAMILY"] == n and d["PAL"] == pal


def test_solo_layouts_compatibles():
    assert studio.normalize("v3:terminal", None, "hero")[2] == "list"          # no declarado → el predeterminado
    assert studio.normalize("v3:flow", None, "shelf")[2] == "shelf"
    assert studio.build("v3:flow", None, None, "shelf")[ "HOME"] == "posters" and studio.build("v3:flow", None, None, "shelf")["HOMEV"] == "shelf"


def test_material_y_tipografia_se_traducen():
    g, t, e, a = (studio.build("v3:" + p) for p in ("glass", "terminal", "editorial", "arcade"))
    assert g["GLASS"] and g["GRAD"] and not t["GLASS"] and t["OUTLINE"] and a["OUTLINE"]
    assert t["FONT"] == "mono" and e["FONT"] == "serif" and a["FONT"] == "vt323" and studio.build("v3:minimal")["FONT"] is None
    assert t["RADK"] < 0.2 < studio.build("v3:flow")["RADK"]
    assert studio.build("v3:minimal")["ANIM"] is None and g["ANIM"] == "aurora"
    assert studio.build("v3:glass", None, None, None, reduce_motion=True)["ANIM"] is None


def test_cambiar_paleta_no_cambia_identidad():
    a, b = studio.build("v3:showcase", "ocean"), studio.build("v3:showcase", "sunset")
    for k in ("HOME", "HOMEV", "FONT", "FONTK", "SND", "RADK", "OUTLINE", "GLASS", "ANIM"):
        assert a[k] == b[k], k
    assert a["BG"] != b["BG"]


def test_los_15_heredados_no_cambian():
    from hub import ui as U
    for f, fam in tf.FAMILIES.items():
        for p in fam["pals"]:
            assert legacy.build(f, p[0]) == tf.build(U._LEG, f, p[0])
    assert len(tf.ORDER) == 15 and not any(studio.is_studio(x) for x in tf.ORDER)


def test_selector_aplica_persiste_y_cambia_inicio(ui, tmp_path, monkeypatch):
    import hub.ui as Hm
    from hub import config
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "s.json")
    monkeypatch.setattr(config, "DATA", tmp_path)
    ui.modal = ui.detail = None
    ui.go_tab("settings")
    ui.set_page = "look"
    run(ui, 2)
    ks = {w.key for w in ui.widgets}
    assert {f"theme:{n}" for n in IDS} <= ks
    ui.pick_theme("v3:arcade")
    run(ui, 2)
    assert ui.cfg["theme"] == "v3:arcade" and Hm.HOME == "slots" and Hm.FONT == "vt323" and Hm.SND == "chip"
    ks = {w.key for w in ui.widgets}
    assert {"lay:slots", "lay:grid", "lay:list"} <= ks and "pal:lcd" in ks
    ui.pick_layout("list")
    ui.pick_pal("lcd")
    assert Hm.HOME == "list" and Hm.PAL == "lcd" and Hm.STUDIO_LAYOUT == "list"
    s = json.loads((tmp_path / "s.json").read_text())
    assert s["theme"] == "v3:arcade" and s["layouts"]["v3:arcade"] == "list" and s["pals"]["v3:arcade"] == "lcd"
    j = json.loads((tmp_path / "appearance.json").read_text())
    assert j["family"] == "v3:arcade" and j["layout"]["studio"] == "list" and "studio" in j
    for tab in ("home", "games", "downloads", "settings"):
        ui.go_tab(tab)
        run(ui, 3)
        assert ui.widgets
    ui.set_look(theme="limpio")
    ui.set_page = None
    assert Hm.FAMILY == "limpio"


def test_todas_las_identidades_dibujan_las_cuatro_pantallas(ui):
    ui.modal = ui.detail = None
    for n in IDS:
        ui.set_look(theme=n)
        for tab in ("home", "games", "downloads", "settings"):
            ui.go_tab(tab)
            run(ui, 2)
    ui.set_look(theme="limpio")


def test_lb_rb_desde_el_estudio_vuelve_a_los_heredados(ui):
    import hub.ui as Hm
    ui.set_look(theme="v3:glass")
    ui.toggle_theme(1)
    assert ui.cfg["theme"] in Hm.THEME_ORDER


def test_peticion_de_estudio():
    ok, errs, ch = ar.validate({"schema_version": 1, "request_id": "a", "changes": {"theme": "v3:flow", "palette": "violet", "layout": "coverflow"}},
                               ("limpio", "oscuro", None))
    assert ok and ch["layout"] == "coverflow"
    for bad in ({"theme": "v3:terminal", "layout": "hero"}, {"theme": "v3:editorial", "palette": "neon"}, {"theme": "v3:nada"},
                {"theme": "neon", "layout": "list"}):
        ok, errs, ch = ar.validate({"schema_version": 1, "request_id": "a", "changes": bad}, ("limpio", "oscuro", None))
        assert not ok and errs, bad


def test_v304_material_llega_al_dibujo():
    """v3.04: cada identidad lleva el material del registro del motor; los heredados, ninguno."""
    from hub.themes.registry import MATERIALS
    for p in studio.ORDER:
        d = studio.build(studio.PREFIX + p)
        m = MATERIALS[PRESETS[p].default_material]
        assert d["MAT"] == {"opacity": m.opacity, "shadow": m.shadow, "border": m.border_width,     # v3.09: + blur (solo Glass)
                            "blur": m.blur if p == "glass" else 0.0}, p
    assert "MAT" not in legacy.build("limpio") and "MAT" not in legacy.build("obsidian")


def test_v304_rr_dibuja_sombra_y_borde_solo_con_material(ui):
    import hub.ui as Hm
    pygame = __import__("pygame")
    ui.set_look(theme="v3:terminal", fx="glass")
    assert Hm.MAT and Hm.MAT["border"] == 2.0
    ui.screen.fill(Hm.BG)
    r = pygame.Rect(200, 200, 300, 160)
    ui.rr(r, Hm.PANEL, 14)
    assert ui.screen.get_at((r.x + 1, r.centery))[:3] == Hm.LINE          # borde del material en el filo
    ui.set_look(theme="v3:showcase", fx="glass")
    ui.screen.fill(Hm.BG)
    ui.rr(r, Hm.PANEL, 14)
    assert ui.screen.get_at((r.centerx, r.bottom + 3))[:3] != Hm.BG        # sombra debajo
    ui.set_look(theme="v3:showcase", fx="perf")                            # rendimiento: sin sombra
    ui.screen.fill(Hm.BG)
    ui.rr(r, Hm.PANEL, 14)
    assert ui.screen.get_at((r.centerx, r.bottom + 3))[:3] == Hm.BG
    ui.set_look(theme="limpio", fx="glass")
    assert Hm.MAT is None
