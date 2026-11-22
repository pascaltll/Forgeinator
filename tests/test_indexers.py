"""Indexador de awesome-decomp-games: reglas de filtrado, marcas, no pisar tu catálogo, escritura segura y su efecto en la UI."""
import json

import pytest

from hub import catalog, indexers


def g(title, repo, typ="static-recomp", plat="N64", release="v1", archived=False, inactive=False, **kw):
    return dict({"title": title, "repo": repo, "url": f"https://github.com/{repo}", "type": typ, "platform": plat, "release": release,
                 "release_date": "2026-01-05T00:00:00Z", "archived": archived, "inactive": inactive, "stars": 10, "last_commit": "2026-10-01T00:00:00Z",
                 "description": "desc", "homepage": None}, **kw)


DATA = {"games": [
    g("Juego A", "o/a"),                                                         # recomp con release → listo
    g("Juego B", "o/b", typ="decompilation"),                                    # decompilación con release → listo
    g("Juego C", "o/c", typ="source-port", release=None),                        # sin release → solo código
    g("Viejo D", "o/d", archived=True),                                          # archivado con release → entra, sin mantenimiento
    g("Inactivo E", "o/e", inactive=True, plat="PC"),                            # inactivo con release → entra
    g("Desm F", "o/f", typ="disassembly"),                                       # tipo descartado
    g("Web G", "o/g", typ="browser-port"),                                       # tipo descartado
    g("Tool H", "o/h", typ="tool"),                                              # tipo descartado
    g("Sin repo I", "", plat="PC"),                                              # sin repo (no GitHub)
    g("GitLab J", "o/j", url="https://gitlab.com/o/j"),                          # otro host
    g("Dup K", "o/a"),                                                           # mismo repo que A
    g("Mayús L", "O/A"),                                                         # mismo repo, otra capitalización
    g("PS1 M", "o/m", plat="PS1"),
    g("Raro N", "o/n", plat="Other"),
]}


def test_filtra_por_tipo_y_se_queda_con_los_de_github_sin_duplicados():
    es = indexers.build(DATA)
    assert {e["repo"] for e in es} == {"o/a", "o/b", "o/c", "o/d", "o/e", "o/m", "o/n"}
    assert len(es) == 7, "un repo repetido (aunque cambie la capitalización) entra una sola vez"


def test_los_archivados_con_release_entran_y_se_marcan_sin_mantenimiento():
    es = {e["repo"]: e for e in indexers.build(DATA)}
    assert "sin-mantenimiento" in es["o/d"]["tags"] and "repositorio archivado" in es["o/d"]["notes"]
    assert "sin-mantenimiento" in es["o/e"]["tags"] and "sin actividad reciente" in es["o/e"]["notes"]
    assert "sin-mantenimiento" not in es["o/a"]["tags"]


def test_sin_release_es_solo_codigo_y_con_release_no():
    es = {e["repo"]: e for e in indexers.build(DATA)}
    assert "solo-codigo" in es["o/c"]["tags"] and "hay que compilarlo" in es["o/c"]["notes"]
    assert all("solo-codigo" not in es[r]["tags"] for r in ("o/a", "o/b", "o/d"))


def test_orden_primero_los_listos_y_luego_por_estrellas():
    d = {"games": [g("Pocas", "o/1", stars=1), g("Muchas", "o/2", stars=999), g("Sin rel muchas", "o/3", release=None, stars=5000)]}
    assert [e["repo"] for e in indexers.build(d)] == ["o/2", "o/1", "o/3"]


def test_nombres_de_plataforma_al_estilo_de_hub():
    es = {e["repo"]: e for e in indexers.build(DATA)}
    assert es["o/a"]["platform"] == "Nintendo 64" and es["o/m"]["platform"] == "PlayStation" and es["o/n"]["platform"] == ""
    assert indexers.platform("Xbox 360") == "Xbox 360" and indexers.platform("og xbox") == "Xbox" and indexers.platform(None) == ""


def test_consolas_piden_tu_copia_y_pc_no():
    es = {e["repo"]: e for e in indexers.build(DATA)}
    assert "tu propia copia" in es["o/a"]["requires"]["note"]
    assert "requires" not in es["o/e"]                      # PC
    d = {"games": [g("X", "o/x", plat="PC", needs_assets="byo")]}
    assert "requires" in indexers.build(d)[0]


def test_no_pisa_lo_que_ya_tienes():
    es = indexers.build(DATA, skip_repos={"O/A", "o/b"})
    assert {e["repo"] for e in es} == {"o/c", "o/d", "o/e", "o/m", "o/n"}


def test_los_ids_son_estables_y_unicos_y_normalize_los_acepta():
    es = indexers.build(DATA)
    assert len({e["id"] for e in es}) == len(es) and es[0]["id"].startswith("ad-")
    parsed = catalog.parse(es)
    assert len(parsed) == len(es) and all(p["repo"] and p["name"] for p in parsed)
    assert "solo-codigo" in next(p for p in parsed if p["repo"] == "o/c")["tags"], "las etiquetas sobreviven a catalog.parse"


def test_update_escribe_de_forma_atomica_y_resume(tmp_path):
    dest = tmp_path / "x" / "00-awesome-decomp.json"
    r = indexers.update(DATA, dest)
    assert dest.is_file() and not dest.with_suffix(".tmp").exists()
    assert r["total"] == 7 and r["solo_codigo"] == 1 and r["listos"] == 6 and r["sin_mantenimiento"] == 2
    assert len(json.loads(dest.read_text(encoding="utf-8"))) == 7


def test_resultado_vacio_o_forma_inesperada_no_borra_la_lista_anterior(tmp_path):
    dest = tmp_path / "l.json"
    indexers.update(DATA, dest)
    antes = dest.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        indexers.update({"games": [g("Solo tool", "o/h", typ="tool")]}, dest)
    with pytest.raises(ValueError):
        indexers.update({"otra": "cosa"}, dest)
    with pytest.raises(ValueError):
        indexers.update([1, 2], dest)
    assert dest.read_text(encoding="utf-8") == antes


def test_fetch_lee_json_por_url(tmp_path):
    f = tmp_path / "games.json"
    f.write_text(json.dumps(DATA), encoding="utf-8")
    assert len(indexers.fetch(f.as_uri())["games"]) == len(DATA["games"])


def test_el_catalogo_real_combinado_no_pisa_el_seed(tmp_path, monkeypatch):
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps([{"id": "mio", "name": "Mi nombre", "repo": "o/a", "platform": "PlayStation", "folder": "MIO"}]), encoding="utf-8")
    imp = tmp_path / "imports"
    imp.mkdir()
    monkeypatch.setattr(catalog, "SEED", seed)
    monkeypatch.setattr(catalog, "IMPORTS", imp)
    monkeypatch.setattr(catalog, "LOCAL", tmp_path / "local.json")
    indexers.update(DATA, imp / indexers.OUT_NAME)
    es = {e["repo"].lower(): e for e in catalog.load()}
    assert es["o/a"]["name"] == "Mi nombre" and es["o/a"]["platform"] == "PlayStation", "tu entrada manda sobre la importada"
    assert "o/c" in es and len([e for e in catalog.load() if e["repo"].lower() == "o/a"]) == 1


# ── efecto en la interfaz ──
pygame = pytest.importorskip("pygame")


@pytest.fixture(scope="module")
def _ui_unica():
    import hub.ui as H
    u = H.UI()
    yield u
    u.running = False


@pytest.fixture()
def ui(_ui_unica):
    """Una sola interfaz para todo el módulo (crear muchas en un mismo proceso hacía fallar después las pruebas de ui_flow); se reinicia el estado en cada prueba."""
    u = _ui_unica
    u.entries = catalog.parse(indexers.build(DATA))
    u._inst_c = u._vis_c = None
    u.filter, u.query, u.explore, u.modal, u.toast_msg = "Todos", "", "cats", None, ""
    u.go_tab("home")
    return u


def names(u):
    return {e["repo"] for e, *_ in u.visible_entries()}


@pytest.mark.ui
def test_la_lista_normal_oculta_solo_codigo_y_su_filtro_solo_muestra_eso(ui):
    ui.filter, ui.query = "Todos", ""
    assert "o/c" not in names(ui) and "o/a" in names(ui)
    ui.filter = "Solo código"
    assert names(ui) == {"o/c"}
    ui.filter = "Nintendo 64"
    assert "o/c" not in names(ui) and "o/a" in names(ui)


@pytest.mark.ui
def test_explorar_cuenta_aparte_y_ofrece_el_mosaico_solo_codigo(ui):
    ui.go_tab("games")
    ui.explore = "cats"
    for _ in range(3):
        ui.frame()
    keys = [w.key for w in ui.widgets]
    assert "cat:Solo código" in keys and "cat:Todos" in keys
    next(w for w in ui.widgets if w.key == "cat:Solo código").cb()
    ui.frame()
    assert ui.filter == "Solo código" and ui.explore == "list"


@pytest.mark.ui
def test_boton_de_ajustes_actualiza_en_un_hilo_y_avisa(ui, monkeypatch):
    llamadas = []
    monkeypatch.setattr(indexers, "update", lambda *a, **k: llamadas.append(1) or {"listos": 5, "solo_codigo": 2, "sin_mantenimiento": 1, "total": 7, "ya_los_tenias": 0, "path": "x"})
    ui.update_index()
    from conftest import wait_for
    wait_for(lambda: not ui._idx_busy, 5)
    assert llamadas == [1] and "5 listos" in ui.toast_msg and "2 solo código" in ui.toast_msg


@pytest.mark.ui
def test_si_falla_la_descarga_avisa_y_se_puede_reintentar(ui, monkeypatch):
    def boom(*a, **k):
        raise OSError("sin red")
    monkeypatch.setattr(indexers, "update", boom)
    ui.update_index()
    from conftest import wait_for
    wait_for(lambda: not ui._idx_busy, 5)
    assert "No se pudo actualizar" in ui.toast_msg and ui._idx_busy is False
