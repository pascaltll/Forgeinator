"""Capas translúcidas: fondo ambiental y barras de cristal cacheados, contenido bajo las barras, fondo esmerilado de los menús (una sola vez)."""
import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import shot


@pytest.fixture(scope="module")
def _ui_unica():
    import hub.ui as H
    u = H.UI()
    yield u
    u.running = False


@pytest.fixture()
def ui(_ui_unica):
    u = _ui_unica
    u.modal = None
    u.go_tab("home")
    for _ in range(3):
        u.frame()
    return u


def test_el_fondo_ambiental_se_prepara_una_vez_por_tamano(ui):
    a = ui.ambient()
    assert ui.ambient() is a and a.get_size() == (ui.W, ui.H)
    px = [a.get_at((x, y))[:3] for x, y in ((5, 5), (ui.W - 5, 5), (5, ui.H - 5), (ui.W // 2, ui.H // 2))]
    assert all(max(p) < 60 for p in px), "debe seguir siendo un fondo oscuro"
    assert len(set(px)) > 1, "tiene que haber degradado/resplandor, no un color liso"


def test_las_barras_son_translucidas_y_cacheadas(ui):
    g = ui.glass(ui.n(ui.HH), True)
    assert ui.glass(ui.n(ui.HH), True) is g and g.get_size() == (ui.W, ui.n(ui.HH))
    alphas = [g.get_at((10, y))[3] for y in range(g.get_height())]
    assert all(150 <= a <= 255 for a in alphas[:-1]) and min(alphas) < 255, "translúcida pero legible"
    assert alphas[0] > alphas[-3], "más opaca en el borde de la pantalla que junto al contenido"


def test_el_contenido_pasa_por_debajo_de_la_barra_superior(ui):
    ui.views["home"].off = 200
    ui.frame()
    ui.frame()
    hh = ui.n(ui.HH)
    # el contenido (tarjetas/títulos) sigue dibujándose bajo la barra: el clip de la vista principal cubre toda la pantalla
    ui.screen.set_clip(None)
    ui.begin("home", pygame.Rect(0, hh, ui.W, ui.H - hh - ui.n(ui.FH)))
    assert ui.screen.get_clip() == pygame.Rect(0, 0, ui.W, ui.H)
    ui.end()
    ui.begin("otra", pygame.Rect(10, hh + 5, 300, 300))
    assert ui.screen.get_clip() == pygame.Rect(10, hh + 5, 300, 300), "las vistas de los menús siguen recortadas a su rectángulo"
    ui.end()


def test_el_menu_guarda_su_fondo_una_vez_y_no_redibuja_lo_de_detras(ui, monkeypatch):
    llamadas = []
    real = ui.draw_home
    monkeypatch.setattr(ui, "draw_home", lambda body: llamadas.append(1) or real(body))
    ui.confirm("¿Seguro?", "texto", lambda: None)
    ui.frame()
    assert len(llamadas) == 1 and ui.modal["_bd"][0] == (ui.W, ui.H)
    bd = ui.modal["_bd"][1]
    for _ in range(5):
        ui.frame()
    assert len(llamadas) == 1, "con el menú abierto no se vuelve a dibujar la pantalla de detrás"
    assert ui.modal["_bd"][1] is bd, "la instantánea desenfocada no se recalcula"
    assert any(w.key == "m:yes" for w in ui.widgets), "el menú sigue siendo interactivo"
    ui.close_modal()
    ui.frame()
    assert len(llamadas) == 2, "al cerrar vuelve a dibujarse la pantalla normal"


def test_cada_menu_nuevo_hace_su_propia_instantanea(ui):
    ui.confirm("uno", "a", lambda: None)
    ui.frame()
    b1 = ui.modal["_bd"][1]
    ui.close_modal()
    ui.confirm("dos", "b", lambda: None)
    ui.frame()
    assert ui.modal["_bd"][1] is not b1


def test_si_cambia_el_tamano_de_la_ventana_se_rehace_el_fondo(ui):
    ui.confirm("x", "y", lambda: None)
    ui.frame()
    ui.modal["_bd"] = ((1, 1), ui.modal["_bd"][1])          # como si la ventana hubiera tenido otro tamaño
    ui.frame()
    assert ui.modal["_bd"][0] == (ui.W, ui.H), "una instantánea de otro tamaño se descarta y se rehace"
    assert ui.modal["_bd"][1].get_size() == (ui.W, ui.H)


def test_el_fondo_esmerilado_esta_desenfocado_y_oscurecido(ui):
    ui.screen.fill((255, 255, 255))
    pygame.draw.rect(ui.screen, (0, 0, 0), (ui.W // 2 - 4, 0, 8, ui.H))
    f = ui._frost()
    assert f.get_size() == (ui.W, ui.H)
    claro = f.get_at((20, 20))[:3]
    assert max(claro) < 200, "oscurecido"
    borde = f.get_at((ui.W // 2 - 4, ui.H // 2))[:3]
    assert 10 < borde[0] < 120, "la línea negra fina queda difuminada, no nítida"


def test_captura_de_cristal(ui):
    shot(ui, "74_inicio_cristal.png")
    ui.confirm("¿Seguro?", "esto es una prueba", lambda: None)
    ui.frame()
    shot(ui, "75_menu_esmerilado.png")
