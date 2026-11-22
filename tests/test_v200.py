"""v2.0: Ajustes por categorías (con una línea que explica cada opción) y «Más opciones» de la ficha por bloques."""
import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")
CATS = ["look", "play", "files", "catalog", "github", "build", "maint"]


def _keys(ui):
    return {str(w.key) for w in ui.widgets}


@pytest.mark.parametrize("theme", ["prototipo", "dark"])
def test_categorias_entrar_y_volver_con_b(ui, theme):
    ui.set_look(theme=theme, fx="perf")
    ui.adv_open = False
    ui.go_tab("settings")
    run(ui, 3)
    assert {f"cat:{c}" for c in CATS} <= _keys(ui)
    ui.focus = "cat:play"
    ui.act("A")
    run(ui, 2)
    ks = _keys(ui)
    assert ui.set_page == "play" and {"set_back", "viasteam", "closeplay", "power", "steamprep"} <= ks and "theme" not in ks
    ui.act("B")
    run(ui, 2)
    assert ui.set_page is None and ui.focus == "cat:play", "B vuelve a las categorías con el foco donde estaba"


def test_cada_opcion_esta_en_alguna_categoria(ui):
    """Nada se perdió al reorganizar: todo lo que había en Ajustes (antes: principal + Avanzado) está en una categoría."""
    antes = {"theme:limpio", "fx", "set:max_active", "set:connections", "romdir", "chk", "store", "upd", "updauto", "power", "sfx", "sfxv",
             "go_search", "add_repo", "addgame", "imp_url", "imp_file", "idx", "gh_login", "gh_tok", "gh_test", "gh_cookies",
             "blog", "cont", "k_sgdb", "k_tgdb", "covers", "catauto", "steamprep", "viasteam", "closeplay", "browser", "hbinst", "hblvl",
             "bzoom", "kbd", "retnav", "stick", "trash_r", "trash_e", "tests_run", "tests_last", "doctor", "launchlogs", "showlog", "perf"}
    ui.adv_open = False
    vistos = set()
    for c in CATS:
        ui.go_tab("settings")
        ui.settings_open(c)
        run(ui, 2)
        vistos |= _keys(ui)
    assert antes <= vistos, antes - vistos
    ui.settings_back()


def test_todos_los_ajustes_en_una_lista(ui):
    ui.go_tab("settings")
    ui.adv_open = True
    run(ui, 3)
    ks = _keys(ui)
    assert {"theme:limpio", "viasteam", "romdir", "go_search", "gh_login", "cont", "doctor"} <= ks
    ui.adv_open = False


def test_la_ficha_ordena_mas_opciones_en_pestanas(H, ui, monkeypatch):
    ui.set_look(theme="dark", fx="perf")
    e = ui.entries[0]
    ui.more_open.add(e["id"])
    ui.go_tab("games")
    ui.open_detail(e)
    esperado = {"archivos": ["watch", "usedet", "rdir", "s_gh", "refresh", "pick_rel"], "jugar": [], "steam": ["sport", "scwd", "sart", "sartg"],
                "compilar": ["bplan", "build", "pbrief"], "diagnostico": ["del"]}
    for tab, claves in esperado.items():
        ui.more_tab[e["id"]] = tab
        run(ui, 3)
        ks = {str(w.key) for w in ui.widgets}
        assert {"tab_jugar", "tab_archivos", "tab_compilar", "tab_steam", "tab_diagnostico"} <= ks
        assert set(claves) <= ks, (tab, claves, sorted(ks))
        otros = set().union(*[set(v) for k, v in esperado.items() if k != tab])
        assert not (otros & ks), (tab, "mezcla opciones de otra pestaña", otros & ks)
    textos = []
    orig = ui.text
    monkeypatch.setattr(ui, "text", lambda s, *a, **k: (textos.append(str(s)), orig(s, *a, **k))[1])
    ui.more_tab[e["id"]] = "steam"
    run(ui, 1)
    ui.more_open.discard(e["id"])
    assert any("PARTIDAS Y CONFIGURACIÓN" in t for t in textos) and any("El juego arranca en:" in t for t in textos)
    assert not any("SELECTOR EN MI BIBLIOTECA" in t for t in textos)
