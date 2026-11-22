"""v2.86: «Ajustes del juego» en 5 pestañas por objetivo; los nombres antiguos siguen valiendo; sin ✓ en la pestaña abierta."""
from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


def _abrir(ui, H, monkeypatch, tab):
    e = next(x for x in ui.entries if x.get("repo"))
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    ui.open_detail(e)
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = tab
    run(ui, 6)
    return e, {getattr(w, "key", None) for w in ui.widgets}


def test_cinco_pestanas_con_nombres_nuevos(ui, H):
    assert [k for k, _ in ui.TABS] == ["jugar", "archivos", "compilar", "steam", "diagnostico"]


def test_nombres_antiguos_se_traducen(ui, H):
    e = next(x for x in ui.entries if x.get("repo"))
    for viejo, nuevo in (("juego", "jugar"), ("archivo", "archivos"), ("versiones", "archivos"), ("avanzado", "diagnostico"), ("lanzar", "steam")):
        ui.more_tab[e["id"]] = viejo
        assert ui.more_tab_for(e, 0) == nuevo
    ui.more_tab.pop(e["id"], None)
    assert ui.more_tab_for(e, 0) == "jugar" and ui.more_tab_for(e, 1) == "archivos" and ui.more_tab_for(e, 2) == "archivos"


def test_archivos_y_versiones_en_la_misma_pestana(ui, H, monkeypatch):
    e, ks = _abrir(ui, H, monkeypatch, "archivos")
    assert "tab_archivos" in ks and "tab_versiones" not in ks and "tab_archivo" not in ks
    assert len(ks) > 12, "debe traer lo de archivo y lo de versiones"


def test_diagnostico_tiene_borrar(ui, H, monkeypatch):
    e, ks = _abrir(ui, H, monkeypatch, "diagnostico")
    assert "del" in ks


def test_pestana_abierta_sin_marca_de_hecho(ui, H, monkeypatch):
    import inspect
    from hub import ui_detail
    src = inspect.getsource(ui_detail)
    assert "mark=k_ == tab" not in src and "mark=k == tab" not in src
