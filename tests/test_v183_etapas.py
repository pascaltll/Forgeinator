"""v1.83+: carátulas en lote, registro de compilaciones, doctor, diccionario de juegos, Ajustes avanzados."""
import pytest

from hub import buildlog, covers, doctor, config, gamedict


@pytest.fixture(scope="module")
def ui():
    pytest.importorskip("pygame")
    import hub.ui as H
    return H.UI()


def _entries(n=3):
    return [{"id": f"g{i}", "name": f"Juego {i}: Recompiled"} for i in range(n)]


def test_covers_batch_descarga_solo_lo_que_falta(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    es = _entries()
    (tmp_path / "covers").mkdir()
    (tmp_path / "covers" / "g0.png").write_bytes(b"x")
    calls = []
    kw = dict(search=lambda t: [{"id": 1, "name": t}],
              images=lambda k, i, n: [{"url": "http://x/a.jpg"}],
              fetch=lambda u, d: (calls.append(d.name), d.parent.mkdir(parents=True, exist_ok=True), d.write_bytes(b"y")))
    r = covers.batch(es, pause=0, **kw)
    assert r == {"ok": 2, "sin": 0, "error": 0, "total": 2}
    assert sorted(calls) == ["g1.jpg", "g2.jpg"]
    assert covers.batch(es, pause=0, **kw)["total"] == 0          # idempotente


def test_covers_sin_resultados_y_errores(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    r = covers.batch(_entries(1), pause=0, search=lambda t: [], images=None, fetch=None)
    assert r["sin"] == 1
    def boom(t): raise OSError("red")
    assert covers.batch(_entries(1), pause=0, search=boom)["error"] == 1


def test_buildlog_registra_y_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    assert "sin compilaciones" in buildlog.summary()
    buildlog.record({"id": "a", "name": "A"}, "fedora", "cmake -B build && make -j$JOBS", 4, True, 30)
    buildlog.record({"id": "b", "name": "B"}, "fedora", "cargo build", 4, False, 5, "falló")
    s = buildlog.stats()
    assert s["total"] == 2 and s["ok"] == 1
    assert ("cmake", 1) in s["tools"] and ("fedora", 2) in s["containers"]
    assert "1/2" in buildlog.summary()
    (tmp_path / "buildlog.jsonl").open("a").write("basura\n")      # línea corrupta no rompe
    assert buildlog.stats()["total"] == 2


def test_doctor_informa_sin_red(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    rs = doctor.checks(network=False)
    assert all(st in ("ok", "aviso", "fallo") for st, _, _ in rs)
    txt = doctor.report(network=False)
    assert "✓" in txt or "!" in txt


def test_doctor_detecta_toml_duplicados(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LAUNCHER", tmp_path)
    (tmp_path / "games").mkdir()
    for n in ("a", "b"):
        (tmp_path / "games" / f"{n}.toml").write_text('install_dir = "/x/juego"\n')
    st, txt, _ = doctor._duplicates()
    assert st == "aviso" and "a.toml" in txt


def test_ajustes_esenciales_y_avanzado(ui):
    ui.adv_open = False
    ui.go_tab("settings")
    for _ in range(3):
        ui.frame()
    ks = {getattr(w, "key", None) for w in ui.widgets}
    # v2.0: Ajustes abre con categorías; lo ocasional no está a la vista
    assert {"cat:look", "cat:play", "cat:maint", "adv"} <= ks and "go_search" not in ks and "doctor" not in ks
    ui.go_tab("home")


def test_ajustes_avanzado_abierto_muestra_lo_ocasional(ui):
    ui.adv_open = True
    ui.go_tab("settings")
    for _ in range(3):
        ui.frame()
    ks = {getattr(w, "key", None) for w in ui.widgets}
    assert {"go_search", "doctor", "covers", "blog"} <= ks
    ui.adv_open = False
    ui.go_tab("home")


def test_explorar_ya_no_ofrece_buscar_en_github_pero_si_biblioteca(ui):
    ui.go_tab("games")
    ui.explore = "plat" if hasattr(ui, "explore") else None
    for _ in range(3):
        ui.frame()
    ks = {getattr(w, "key", None) for w in ui.widgets}
    assert "x_search" not in ks
    ui.go_tab("home")


def test_diccionario_proyecto_a_juego():
    e = {"id": "x", "name": "Shipwright", "repo": "HarbourMasters/Shipwright"}
    assert gamedict.game_name(e) == "The Legend of Zelda: Ocarina of Time"
    assert gamedict.match(e, "ocarina") and gamedict.match(e, "soh")
    assert not gamedict.match(e, "mario kart")
