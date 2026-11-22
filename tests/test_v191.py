"""v1.91: uso de la API de GitHub (token enviado, ETag/304, tipos de límite, cortacircuitos, solo lo instalado), glifos que la fuente no tiene
y descripción en texto de cómo se ve cada pantalla a 1280×720 y 1920×1080 (el panel del ROG Ally)."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from conftest import report_section
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, pantallas, run  # noqa: F401  (fixtures compartidas)

pygame = pytest.importorskip("pygame")


# ── servidor falso de GitHub ───────────────────────────────────────
class Fake:
    mode = "ok"
    log = []


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        Fake.log.append({"path": self.path, "auth": self.headers.get("Authorization"), "inm": self.headers.get("If-None-Match")})
        if Fake.mode == "primary":
            self.send_response(403)
            self.send_header("X-RateLimit-Remaining", "0")
            self.send_header("X-RateLimit-Limit", "60")
            self.send_header("X-RateLimit-Reset", str(int(time.time()) + 1800))
            body = b'{"message":"API rate limit exceeded for 1.2.3.4."}'
        elif Fake.mode == "secondary":
            self.send_response(403)
            self.send_header("Retry-After", "30")
            body = b'{"message":"You have exceeded a secondary rate limit."}'
        elif self.headers.get("If-None-Match") == '"abc"':
            self.send_response(304)
            self.send_header("X-RateLimit-Remaining", "4999")
            self.end_headers()
            return
        else:
            self.send_response(200)
            self.send_header("ETag", '"abc"')
            self.send_header("X-RateLimit-Remaining", "4999")
            self.send_header("X-RateLimit-Limit", "5000")
            body = json.dumps([{"tag_name": "v1", "assets": [], "draft": False, "prerelease": False}]).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def gh(tmp_path, monkeypatch):
    from hub import github, ghstats, config
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(github, "API", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr(config, "CACHE", tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "tok-de-prueba")
    Fake.mode, Fake.log = "ok", []
    ghstats.reset_all()
    yield github
    srv.shutdown()
    ghstats.reset_all()


def test_el_token_se_envia_y_sin_token_no(gh, monkeypatch):
    gh.releases("a/b", force=True)
    assert Fake.log[-1]["auth"] == "Bearer tok-de-prueba"
    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.setattr(gh.auth, "_read", lambda: {})
    gh.releases("c/d", force=True)
    assert Fake.log[-1]["auth"] is None


def test_etag_304_no_vuelve_a_bajar_nada(gh):
    from hub import ghstats
    assert gh.releases("a/b", force=True)["releases"][0]["tag_name"] == "v1"
    r = gh.releases("a/b", force=True)
    assert Fake.log[-1]["inm"] == '"abc"' and r["releases"] and not r["error"] and not r["stale"]
    assert ghstats.S["notmod"] == 1 and ghstats.S["auth"] == 2 and ghstats.S["anon"] == 0


def test_limite_primario_distingue_y_corta_el_circuito(gh):
    from hub import ghstats
    Fake.mode = "primary"
    r = gh.releases("a/b", force=True)
    assert "agotada" in r["error"] and ghstats.blocked() > 60 and ghstats.S["blocked_why"] == "primario"
    n = len(Fake.log)
    for rp in ("x/y", "z/w", "a/b"):
        assert "límite" in gh.releases(rp, force=True)["error"]
    assert len(Fake.log) == n, "con el límite alcanzado no debe seguir llamando a GitHub"


def test_limite_secundario_es_otro_mensaje(gh):
    from hub import ghstats
    Fake.mode = "secondary"
    r = gh.releases("a/b", force=True)
    assert "más despacio" in r["error"] and ghstats.S["blocked_why"] == "secundario" and 0 < ghstats.blocked() <= 30


def test_clasificacion_de_403():
    from hub import ghstats
    assert ghstats.kind(200, {}) == "" and ghstats.kind(404, {}) == ""
    assert ghstats.kind(403, {"X-RateLimit-Remaining": "0"}) == "primario"
    assert ghstats.kind(403, {"Retry-After": "5"}) == "secundario"
    assert ghstats.kind(403, {}, "Resource not accessible") == "otro"
    assert ghstats.kind(429, {}, "secondary rate limit") == "secundario"


def test_comprobar_actualizaciones_solo_lo_instalado_y_una_vez_por_repo(ui, monkeypatch):
    from hub import github
    llamadas = []
    monkeypatch.setattr(github, "latest", lambda repo, *a, **k: llamadas.append(repo) or {"tag": "v9"})
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    ents = [{"id": f"e{i}", "name": f"E{i}", "repo": "o/r" if i < 3 else f"o/r{i}", "platform": ""} for i in range(1100)]
    instalado = {"e0", "e1", "e5", "e6"}                     # e0 y e1 comparten repo
    monkeypatch.setattr(ui, "entries", ents)
    monkeypatch.setattr(ui, "inst", lambda e: {"installed": e["id"] in instalado, "version": "1"})
    ui.check_all()
    t0 = time.time()
    while "Comprobación terminada" not in ui.toast_msg and time.time() - t0 < 10:
        time.sleep(0.02)
    assert sorted(llamadas) == ["o/r", "o/r5", "o/r6"], llamadas      # 3 llamadas en vez de 1100


# ── glifos ─────────────────────────────────────────────────
POBRE = tuple("✓✔↑↓▶◀▲▼‹›●★✕×↻•")


@pytest.mark.parametrize("theme", ["dark", "prototipo"])
def test_ninguna_pantalla_dibuja_un_glifo_que_la_fuente_no_tiene(H, ui, theme):
    """Simula la fuente del Ally (sin ✓ ↑ ▶ ‹ ›…): lo que llegue a la pantalla debe estar ya sustituido, nunca como cuadrado."""
    ui._deny = POBRE
    ui._glyph_ok, ui._sane_c = {}, {}
    llegan, orig = [], ui.sane
    ui.sane = lambda s: llegan.append(orig(s)) or llegan[-1]
    try:
        ui.set_look(theme=theme, fx="perf")
        for nombre, preparar in pantallas(ui):
            preparar()
            run(ui, 2)
        malos = sorted({ch for s in llegan for ch in s if ch in POBRE})
        assert not malos, f"{theme}: se dibujarían como cuadrado: {malos}"
        assert ui.glyph_subs, "el test no ejerció la sustitución (¿ya no hay flechas ni ‹ › en la interfaz?)"
    finally:
        del ui.sane
        ui._deny = ()
        ui._glyph_ok, ui._sane_c = {}, {}


def test_sane_sustituye_y_respeta_lo_que_si_existe(ui):
    ui._deny = ("✓",)
    ui._glyph_ok, ui._sane_c = {}, {}
    try:
        assert ui.sane("Sesión ✓") == "Sesión ok" and ui.sane("canción — año") == "canción — año"
    finally:
        ui._deny = ()
        ui._glyph_ok, ui._sane_c = {}, {}


# ── cómo se ve (texto) ─────────────────────────────────────
TAMANOS = [(1280, 720), (1920, 1080)]


@pytest.mark.parametrize("w,h", TAMANOS)
@pytest.mark.parametrize("theme", ["prototipo", "dark"])
def test_descripcion_en_texto_de_cada_pantalla(H, ui, theme, w, h):
    from hub import layoutdump
    ui.resize(w, h)
    orig_inst = ui.inst

    def falsa(e):                      # cuatro juegos «instalados» para ver el héroe y las tarjetas
        d = dict(orig_inst(e))
        if ui.entries.index(e) < 4:
            d.update(installed=True, version="1.0", launcher_id=e["id"], dir="/tmp/x")
        return d
    ui.inst = falsa
    ui.cfg["last_played"] = {"id": ui.entries[1]["id"], "t": time.time() - 7300}
    try:
        ui.set_look(theme=theme, fx="perf")
        partes, fallos = [], []
        for nombre, preparar in pantallas(ui):
            preparar()
            run(ui, 2)
            txt, a = layoutdump.report(ui, nombre, with_ascii=(theme == "prototipo" and nombre in ("inicio", "explorar", "ficha")))
            partes.append(txt)
            if a["missing_glyphs"]:
                fallos.append((nombre, "glifos", a["missing_glyphs"]))
            if a["offscreen"]:
                fallos.append((nombre, "texto fuera de pantalla", a["offscreen"]))
            if a["min_text_px"] and a["min_text_px"] < 13:
                fallos.append((nombre, "letra < 13 px", a["min_text_px"]))
            if theme == "prototipo" and nombre == "inicio" and (a["overlaps"] or a["small_targets"]):
                fallos.append((nombre, "se pisan / botones pequeños", (a["overlaps"], a["small_targets"])))
        report_section(f"Cómo se ve · tema {theme} · {w}×{h}", "\n\n".join(partes))
        assert not fallos, fallos
    finally:
        del ui.inst
        ui.cfg.pop("last_played", None)
        ui.resize(1280, 800)


def test_todos_los_temas_usan_las_medidas_del_prototipo(H, ui):
    ui.resize(1920, 1080)
    try:
        ui.set_look(theme="dark")
        k_dark = ui.k
        ui.set_look(theme="prototipo")
        assert ui.k == pytest.approx(k_dark) and ui.n(ui.SIDE_W) >= 130      # v2.02: el resto de temas, al tamaño del prototipo
        ui.go_tab("home")
        run(ui, 3)
        assert min(w.rect.h for w in ui.widgets if w.key.startswith("tab:")) >= 90      # ≥ 7 mm táctiles en la barra lateral
    finally:
        ui.resize(1280, 800)


# ── logos de plataforma ────────────────────────────────────
def test_logos_de_plataforma_se_resuelven_y_se_ven():
    from hub import platformart as pa
    for txt, esperado in (("PlayStation", "Sony Playstation"), ("PlayStation 2", "Sony Playstation 2"), ("psx", "Sony Playstation"), ("PSP", "Sony PSP"),
                          ("PC", "Windows"), ("PlayStation 4", "Sony Playstation 4"), ("Xbox One", "Microsoft Xbox One"), ("Nintendo 64", "Nintendo 64"),
                          ("snes", "Super Nintendo Entertainment System"), ("Sega Dreamcast", "Sega Dreamcast")):
        f = pa.path_for(txt)
        assert f is not None and f.stem == esperado, (txt, f)
    assert pa.path_for("") is None and pa.path_for("consola inventada") is None
    s = pa.logo("PlayStation 2", 40, 150)
    assert s is not None and s.get_height() <= 40 and s.get_width() <= 150
    ok, no = pa.coverage()
    report_section("Logos de plataforma", f"{len(ok)} de {len(ok) + len(no)} sistemas de ES-DE con logo. Sin logo: {', '.join(no)}")
    assert len(ok) >= 140
    assert len(list(pa.DIR.glob("*.png"))) >= 240, "faltan los PNG de assets/platform-logos"


def test_explorar_y_inicio_dibujan_el_logo(H, ui, monkeypatch):
    from hub import platformart as pa
    pedidos = []
    orig = pa.logo
    monkeypatch.setattr(pa, "logo", lambda t, *a, **k: pedidos.append(t) or orig(t, *a, **k))
    ui.set_look(theme="prototipo", fx="perf")
    ui.go_tab("games")
    ui.explore = "cats"
    run(ui, 3)
    assert any("PlayStation" in str(t) for t in pedidos), pedidos
