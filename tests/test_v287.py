"""v2.87: el contenedor se gestiona en UN sitio (pestaña COMPILAR Y CONTENEDOR); JUGAR solo muestra el estado y un acceso."""
from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from conftest import shot


def _abrir(ui, H, monkeypatch, tab):
    e = next(x for x in ui.entries if x.get("repo"))
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    monkeypatch.setattr(H.build, "_CC", {"x": (9e12, ["fedora"])})
    ui.open_detail(e)
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = tab
    run(ui, 6)
    return e, {str(getattr(w, "key", "")) for w in ui.widgets}


def test_tarjeta_unica_en_compilar(ui, H, monkeypatch):
    e, ks = _abrir(ui, H, monkeypatch, "compilar")
    assert {"bcont", "ctr_test", "ctr_cmd", "ctr_stop"} <= ks
    shot(ui, "v287-compilar-y-contenedor.png")


def test_el_contenedor_no_esta_duplicado_en_otras_pestanas(ui, H, monkeypatch):
    for tab in ("jugar", "archivos", "steam", "diagnostico"):
        e, ks = _abrir(ui, H, monkeypatch, tab)
        assert not ({"ctr_test", "ctr_cmd", "ctr_stop", "pick_ctr", "pick_ctr_l"} & ks), (tab, ks)


def test_compilar_sin_repo_sigue_visible_si_hay_distrobox(ui, H, monkeypatch):
    e = next(x for x in ui.entries if x.get("repo"))
    sin = dict(e, repo="")
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    monkeypatch.setattr(ui, "build_kind", lambda x: None)
    ui.entries.append(sin)
    try:
        ui.open_detail(sin)
        ui.more_open.add(sin["id"])
        ui.more_tab[sin["id"]] = "jugar"
        run(ui, 6)
        assert "tab_compilar" in {str(w.key) for w in ui.widgets}
    finally:
        ui.entries.remove(sin)
