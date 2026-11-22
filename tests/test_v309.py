"""v3.09 · tanda 1 de temas: parámetros globales ligeros (accesibilidad para todos los temas, 3 niveles de calidad, factores del fondo,
desenfoque Glass solo tras los diálogos, niveles tipográficos y densidad declarados, peso medio real) y el círculo de progreso en temas claros."""
import shutil
import time

import pygame
import pytest

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from test_v305 import _dibuja
from hub import a11y, themes_fam, fonts, config
from hub.themes import studio, legacy

LEG = [(f, p[0]) for f in themes_fam.ORDER for p in themes_fam.FAMILIES[f]["pals"]]
STU = ["v3:" + p for p in studio.ORDER]


# ── accesibilidad: funciones puras ──────────────────────────
def test_sin_opciones_el_tema_no_se_toca():
    for f, p in LEG:
        t = legacy.build(f, p)
        assert a11y.apply(t, a11y.flags({})) is t
    for n in STU:
        t = studio.build(n)
        assert a11y.apply(t, {"reduce_motion": False, "high_contrast": False, "large_text": False}) is t


def test_apply_theme_sin_opciones_igual_que_antes():
    import hub.ui as Hm
    for f, p in LEG[::4] + [(n, None) for n in STU]:
        Hm.apply_theme(f, p, None, None, a11y.flags({}))
        d = Hm.theme_dict(f, p, None, None)
        assert all(getattr(Hm, k) == v for k, v in d.items()), f


@pytest.mark.parametrize("name,pal", LEG + [(n, None) for n in STU])
def test_alto_contraste_cumple_los_minimos(name, pal):
    t = a11y.apply(studio.build(name) if name.startswith("v3:") else legacy.build(name, pal), {"high_contrast": True})
    for bg in ("BG", "PANEL", "PANEL2"):
        assert a11y.contrast(t["TXT"], t[bg]) >= 7.0 and a11y.contrast(t["DIM"], t[bg]) >= 4.5, (name, pal, bg)
        assert a11y.contrast(t["FOCUS"], t[bg]) >= 3.0
    assert a11y.contrast(t["LINE"], t["BG"]) >= 3.0 and a11y.contrast(t["ACC"], t["BG"]) >= 3.0
    assert a11y.contrast(t["ON_ACC"], t["ACC"]) >= 3.0
    assert t["OUTLINE"] and not t["GLASS"] and t["ORBS"] is None and t["PATTERN"] is None
    if t.get("MAT"):
        assert t["MAT"]["opacity"] == 1.0 and t["MAT"]["blur"] == 0.0


def test_texto_grande_y_movimiento_reducido():
    t = legacy.build("fosforo", "verde")
    g = a11y.apply(t, {"large_text": True})
    assert g["FONTK"] == round(t.get("FONTK", 1.0) * 1.2, 3)
    s = studio.build("v3:glass")
    assert s["ANIM"] == "aurora" and a11y.apply(s, {"reduce_motion": True})["ANIM"] is None
    assert studio.build("v3:glass", a11y={"reduce_motion": True})["ANIM"] is None


def test_niveles_de_calidad():
    assert [a11y.fx_level(x) for x in ("glass", "balanced", "perf", "raro")] == [2, 1, 0, 2]
    assert a11y.next_fx("glass") == "balanced" and a11y.next_fx("balanced") == "perf" and a11y.next_fx("perf") == "glass"


# ── accesibilidad en la interfaz ────────────────────────────
def test_ajustes_trae_las_tres_opciones_y_se_aplican(ui):
    import hub.ui as Hm
    ui.set_look(theme="limpio", pal="oscuro", fx="glass")
    k0 = Hm.FONTK
    ui.go_tab("settings")
    ui.settings_open("look")
    run(ui, 2)
    keys = {w.key for w in ui.widgets}
    assert {"a11y_rm", "a11y_hc", "a11y_lt"} <= keys
    ui.toggle_a11y("large_text")
    assert ui.cfg["large_text"] and Hm.FONTK == round(k0 * 1.2, 3)
    assert config.settings()["large_text"] is True
    ui.toggle_a11y("high_contrast")
    assert Hm.OUTLINE and a11y.contrast(Hm.DIM, Hm.PANEL2) >= 4.5
    ui.toggle_a11y("large_text")
    ui.toggle_a11y("high_contrast")
    assert Hm.FONTK == k0 and not Hm.OUTLINE


def test_movimiento_reducido_quita_fondo_transiciones_y_animaciones(ui, monkeypatch):
    import hub.ui as Hm
    ui.set_look(theme="v3:arcade", fx="glass")
    assert Hm.ANIM == "embers"
    ui.cfg["reduce_motion"] = True
    ui.set_look()
    assert Hm.ANIM is None
    monkeypatch.setattr(type(ui), "draw_anim", lambda self: (_ for _ in ()).throw(AssertionError("fondo animado")))
    Hm.ANIM = "embers"                       # aunque un tema lo pida, con movimiento reducido no se anima
    ui.draw_bg()
    ui._ex_seen = None
    assert ui.enter(0, "x") == 0
    ui.__dict__.pop("_xfade", None)
    ui._xfade_start()
    assert "_xfade" not in ui.__dict__
    w = type("W", (), {"rect": pygame.Rect(10, 10, 100, 60), "cb": lambda s: None})()
    ui.__dict__.pop("_bursts", None)
    ui.fire(w)
    assert not ui.__dict__.get("_bursts")
    assert ui.tab_hop("home", True) == 0 and ui.tab_hop("games", True) == 0
    ui.show_focus = True
    ui.glow(pygame.Rect(50, 50, 120, 80))
    g = [v for v in ui._glow_c.values()][-1]
    assert g.get_alpha() == 96


def test_calidad_equilibrada_fondo_quieto_sin_destellos_con_blur(ui, monkeypatch):
    import hub.ui as Hm
    ui.set_look(theme="v3:arcade", fx="balanced")
    called = []
    monkeypatch.setattr(type(ui), "draw_anim", lambda self: called.append(1))
    ui.draw_bg()
    assert not called
    w = type("W", (), {"rect": pygame.Rect(10, 10, 100, 60), "cb": lambda s: None})()
    ui.__dict__.pop("_bursts", None)
    ui.fire(w)
    assert not ui.__dict__.get("_bursts")
    sizes = []
    real = pygame.transform.smoothscale
    monkeypatch.setattr(Hm.pygame.transform, "smoothscale", lambda s, sz, *a: (sizes.append(sz), real(s, sz, *a))[1])
    ui._frost()
    assert sizes, "equilibrada conserva el desenfoque de los menús"
    ui.set_look(fx="glass")
    called.clear()
    ui.draw_bg()
    assert called, "calidad alta sí anima el fondo"


def test_toggle_fx_recorre_los_tres_niveles(ui):
    ui.set_look(theme="limpio", fx="glass")
    seen = []
    for _ in range(3):
        ui.toggle_fx()
        seen.append(ui.cfg["fx"])
    assert seen == ["balanced", "perf", "glass"]


# ── desenfoque Glass: solo tras los diálogos y una sola vez ─
def test_desenfoque_glass_una_vez_al_abrir_el_menu(ui, monkeypatch):
    import hub.ui as Hm
    ui.set_look(theme="v3:glass", fx="glass")
    assert Hm.MAT["blur"] == 0.55
    n = []
    real = type(ui)._frost
    monkeypatch.setattr(type(ui), "_frost", lambda self: (n.append(1), real(self))[1])
    ui.confirm("Prueba", "¿Seguro?", lambda: None)
    run(ui, 6)
    assert len(n) == 1


def test_desenfoque_glass_mas_fuerte_que_el_de_siempre(ui, monkeypatch):
    import hub.ui as Hm
    sizes = []
    real = pygame.transform.smoothscale
    monkeypatch.setattr(Hm.pygame.transform, "smoothscale", lambda s, sz, *a: (sizes.append(sz), real(s, sz, *a))[1])
    ui.set_look(theme="limpio", pal="oscuro", fx="glass")
    ui._frost()
    legacy_small = sizes[0]
    sizes.clear()
    ui.set_look(theme="v3:glass", fx="glass")
    ui._frost()
    assert legacy_small == (max(8, ui.W // 14), max(8, ui.H // 14))          # temas heredados: igual que siempre
    assert sizes[0][0] < legacy_small[0]


# ── factores del fondo ──────────────────────────────────────
def test_factores_del_fondo_declarados():
    import hub.ui as Hm  # noqa: F401
    assert "MOTION" not in legacy.build("limpio")
    assert studio.build("v3:minimal")["MOTION"] is None                       # sin fondo, sin factores
    m = studio.build("v3:glass")["MOTION"]
    assert m == {"speed": 0.6, "intensity": 1.0, "density": 1.0}
    assert studio.build("v3:editorial")["MOTION"]["intensity"] < 1.0


def test_velocidad_del_fondo_escala_el_reloj(ui, monkeypatch):
    import hub.ui as Hm
    tob = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    ui.set_look(theme="v3:arcade", fx="glass")

    def shot(t, mo):
        monkeypatch.setattr(time, "time", lambda: t)
        Hm.MOTION = mo
        ui.__dict__.pop("_anim", None)
        ui.screen.fill((0, 0, 0))
        ui.draw_anim()
        return tob(ui.screen, "RGB")
    a = shot(1000.0, {"speed": 0.5, "intensity": 1.0, "density": 1.0})
    b = shot(500.0, {"speed": 1.0, "intensity": 1.0, "density": 1.0})
    c = shot(1000.0, {"speed": 1.0, "intensity": 1.0, "density": 1.0})
    assert a == b and a != c


def test_densidad_del_fondo_reduce_particulas(ui, monkeypatch):
    import hub.ui as Hm
    ui.set_look(theme="v3:arcade", fx="glass")
    monkeypatch.setattr(time, "time", lambda: 1000.0)
    n = {}
    for dn in (1.0, 0.5):
        Hm.MOTION = {"speed": 1.0, "intensity": 1.0, "density": dn}
        ui.__dict__.pop("_anim", None)
        cnt = []
        real = ui.screen.blit
        scr = ui.screen

        class S:
            def __getattr__(self, k):
                return getattr(scr, k)

            def blit(self, *a, **k):
                cnt.append(1)
                return real(*a, **k)
        ui.screen = S()
        try:
            ui.draw_anim()
        finally:
            ui.screen = scr
        n[dn] = len(cnt)
    assert n[0.5] == 23 and n[1.0] == 46


# ── tipografía y densidad: declaradas ───────────────────────
def test_niveles_tipograficos_y_densidad_declarados():
    for n in STU:
        ts = studio.type_scale(n)
        assert list(ts) == list(studio.TYPE_LEVELS)
        assert all(v["weight"] in ("regular", "medium", "bold") and v["size"] >= 15 for v in ts.values())
        d = studio.density(n)
        assert d["row"] >= 72 and d["name"] in studio.DENSITY
        b = studio.build(n)
        assert b["TYPE"] == ts and b["DENS"] == d
    assert "TYPE" not in legacy.build("limpio")
    a = studio.appearance("v3:brutalist")
    assert a["type_levels"]["numeric"]["size"] == 42 and a["density"]["name"] == "compact"


def test_no_se_aplican_a_las_pantallas_existentes(ui):
    """Declarar niveles no cambia lo que dibuja Inicio: misma imagen con TYPE/DENS puestos o quitados."""
    import hub.ui as Hm
    tob = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    ui.set_look(theme="v3:brutalist", fx="perf")
    ui.go_tab("home")
    run(ui, 3)
    ui.draw()
    a = tob(ui.screen, "RGB")
    Hm.TYPE = Hm.DENS = None
    ui.draw()
    assert tob(ui.screen, "RGB") == a


def test_peso_medio(ui, tmp_path, monkeypatch):
    import hub.ui as Hm
    src = pygame.font.match_font("dejavusans") or pygame.font.match_font("notosans")
    if not src:
        pytest.skip("sin fuente TTF del sistema para la prueba")
    ui.set_look(theme="limpio", pal="oscuro")
    ui._font_medium = None
    Hm.FONT = "poppins"
    assert ui.font(24, weight="medium") is ui.font(24, True)             # sin archivo Medium: la negrita
    Hm.FONT = "vt323"
    assert ui.font(24, weight="medium") is ui.font(24, False)            # VT323: su único peso
    Hm.FONT = "poppins"
    ui._font_medium = src
    f = ui.font(24, weight="medium")
    assert f is not ui.font(24, True) and f is not ui.font(24, False)
    d = fonts.dir_()
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, d / "Poppins-Medium.ttf")
    assert fonts.medium_path("poppins") and fonts.medium_path("vt323") is None and fonts.medium_path("chakra") is None
    assert set(fonts.MEDIUM) == {"poppins", "chakra"}
    (d / "Poppins-Medium.ttf").unlink()
    fnt, case = ui.type_font("caption")
    assert isinstance(fnt, pygame.font.Font)


# ── radius_scale ────────────────────────────────────────────
def test_radius_scale_del_material_por_defecto_no_cambia_nada():
    from hub.themes.registry import MATERIALS, PRESETS
    for p in studio.ORDER:
        r = studio.IDENTITIES[p]["radius"]
        assert studio.build("v3:" + p)["RADK"] == round(r / 14.0, 3)
    m = MATERIALS["soft"]
    assert m.radius_scale > MATERIALS[PRESETS["minimal"].default_material].radius_scale


# ── círculo de progreso en temas claros (prueba visual) ─────
def _disco(ui, monkeypatch, theme, pal):
    import hub.ui as Hm
    monkeypatch.setattr(ui.mgr, "list", __import__("test_v305")._dls)
    ui.set_look(theme=theme, pal=pal, fx="perf")
    w = _dibuja(ui, monkeypatch, theme, "downloads")
    ui.draw()
    r = w["dl:x2"].rect                                     # en pausa al 70 %: disco con número
    rad = ui.n(46)
    cx, cy = r.x + ui.n(34) + rad, r.y + ui.n(24) + rad
    px = tuple(ui.screen.get_at((cx - rad + ui.n(14), cy))[:3])     # dentro del disco, lejos del número
    return px, Hm


@pytest.mark.parametrize("theme,pal", [(f, p) for f, p in LEG if a11y.lum(legacy.build(f, p)["PANEL"]) > 0.4][:6])
def test_circulo_legible_en_temas_claros(ui, monkeypatch, theme, pal):
    px, Hm = _disco(ui, monkeypatch, theme, pal)
    assert a11y.contrast(Hm.TXT, px) >= 7.0, (theme, pal, px)


@pytest.mark.parametrize("theme,pal", [("limpio", "oscuro"), ("fosforo", "verde"), ("obsidian", "obsidian"), ("neon", "neon")])
def test_circulo_igual_que_siempre_en_temas_oscuros(ui, monkeypatch, theme, pal):
    import hub.ui as Hm
    if theme not in themes_fam.FAMILIES:
        pytest.skip("tema no presente")
    pal = pal if pal in [p[0] for p in themes_fam.FAMILIES[theme]["pals"]] else None
    px, Hm = _disco(ui, monkeypatch, theme, pal)
    base = Hm.PANEL
    k = 0.10
    bg = tuple(int(base[i] * (1 - k) + Hm.WARN[i] * k) for i in range(3))
    assert px == tuple(int(bg[i] * .55) for i in range(3))
    d, t = ui.dl_ring_colors(bg)
    assert d == tuple(int(bg[i] * .55) for i in range(3)) and t == tuple(int(bg[i] * .8 + 12) for i in range(3))


# ── apariencia publicada ────────────────────────────────────
def test_appearance_publica_calidad_y_accesibilidad(ui):
    import json
    ui.cfg["high_contrast"] = True
    ui.set_look(theme="v3:glass", fx="balanced")
    j = json.loads((config.DATA / "appearance.json").read_text())
    assert j["quality"] == "balanced" and j["accessibility"] == {"reduce_motion": False, "high_contrast": True, "large_text": False}
    assert j["studio"]["engine"]["appearance"]["render"]["quality"] == "balanced"
    assert j["motion"]["speed"] == 0.6
    ui.cfg["high_contrast"] = False
    ui.set_look(theme="limpio", fx="glass")
    j = json.loads((config.DATA / "appearance.json").read_text())
    assert j["quality"] == "glass" and j["family"] == "limpio"
