"""v2.05: tema Cristal (paneles translúcidos), Explorar con buscador y filtros, anillos y bordes de Descargas sin escalones."""
import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import shot
from test_descargas_v165 import _D


@pytest.fixture()
def ui():
    import hub.ui as H
    u = H.UI()
    yield u
    u.running = False


def _escalones(sf, caja):
    """Cuántos píxeles de la caja tienen un valor intermedio entre el fondo y el borde del anillo: si es 0, el borde está sin suavizar."""
    return len({tuple(sf.get_at((x, y)))[:3] for x in range(caja[0], caja[0] + caja[2]) for y in range(caja[1], caja[1] + caja[3])})


def test_cristal_existe_y_esta_completo(ui):
    import hub.ui as H
    assert "cristal" in H.THEMES and "cristal" in H.THEME_ORDER and "cristal" in H.THEME_LABEL
    ui.set_look(theme="cristal", fx="glass")
    assert H.GLASS and H.LAYOUT == "side" and H.SCALE == 1.25
    ui.set_look(theme="dark")
    assert not H.GLASS, "al cambiar de tema se apaga el cristal"


def test_los_paneles_de_cristal_dejan_ver_el_fondo(ui):
    import hub.ui as H
    ui.set_look(theme="cristal", fx="glass")
    ui.screen.blit(ui.ambient(), (0, 0))
    antes = tuple(ui.screen.get_at((600, 400)))[:3]
    ui.rr((500, 350, 300, 100), H.PANEL, 20)
    dentro = tuple(ui.screen.get_at((650, 400)))[:3]
    assert dentro != tuple(H.PANEL), "no es un color sólido"
    assert dentro != antes, "pero se nota el panel"
    ui.rr((500, 350, 300, 100), H.ACC, 20)
    assert tuple(ui.screen.get_at((650, 400)))[:3] == tuple(H.ACC), "el acento va opaco"


def test_en_modo_rendimiento_el_cristal_es_opaco(ui):
    import hub.ui as H
    ui.set_look(theme="cristal", fx="perf")
    ui.screen.blit(ui.ambient(), (0, 0))
    ui.rr((500, 350, 300, 100), H.PANEL, 20)
    assert tuple(ui.screen.get_at((650, 400)))[:3] == tuple(H.PANEL)


def test_el_fondo_de_cristal_no_tiene_saltos_bruscos(ui):
    """Antes los resplandores se pisaban y dejaban un borde duro: entre dos píxeles vecinos del fondo no puede haber un salto grande."""
    ui.set_look(theme="cristal", fx="glass")
    a = ui.ambient()
    peor = 0
    for y in (10, 200, 400, 700):
        fila = [tuple(a.get_at((x, y)))[:3] for x in range(0, ui.W, 4)]
        for p, q in zip(fila, fila[1:]):
            peor = max(peor, max(abs(i - j) for i, j in zip(p, q)))
    assert peor <= 4, f"salto de {peor} niveles entre vecinos"


def test_el_fondo_oscuro_tampoco_pierde_su_resplandor(ui):
    ui.set_look(theme="dark", fx="glass")
    a = ui.ambient()
    cerca = tuple(a.get_at((int(ui.W * .86), int(ui.H * .05))))[:3]
    lejos = tuple(a.get_at((int(ui.W * .5), int(ui.H * .5))))[:3]
    assert cerca[2] > lejos[2] + 3, "el azul de arriba a la derecha se ve"


def test_explorar_tiene_buscador_y_filtros(ui):
    ui.go_tab("games")
    for _ in range(4):
        ui.frame()
    keys = {w.key for w in ui.widgets}
    assert "search_all" in keys
    assert "chip:Instalados" not in keys, "v2.26: un filtro vacío (aquí no hay nada instalado) no se dibuja"
    shot(ui, "76_explorar_v205.png")


def test_el_buscador_de_explorar_lleva_a_la_lista_filtrada(ui):
    ui.go_tab("games")
    ui.frame()
    next(w for w in ui.widgets if w.key == "search_all").cb()
    assert ui.pending_osk is not None or ui.modal, "abre el teclado"
    cb = ui.pending_osk[1] if ui.pending_osk else None
    if cb:
        cb("silent")
        assert ui.explore == "list" and ui.query == "silent" and ui.filter == "Todos"


def test_anillo_de_descarga_con_bordes_suaves(ui):
    ui.set_look(theme="prototipo")
    ui.screen.fill((0, 0, 0))
    ui.ring_progress(200, 200, 46, 0.4, (255, 138, 61), track=(40, 40, 40), th=7)
    assert _escalones(ui.screen, (150, 150, 100, 100)) > 12, "tiene tonos intermedios (suavizado)"
    n = len(ui._ring_c)
    ui.ring_progress(200, 200, 46, 0.4, (255, 138, 61), track=(40, 40, 40), th=7)
    assert len(ui._ring_c) == n, "se reutiliza, no se vuelve a dibujar"
    for f in (0, 0.01, 1.0, 1.5, -1):
        ui.ring_progress(200, 200, 46, f, (255, 138, 61))      # extremos sin fallar


def test_botones_redondeados_con_esquinas_suaves(ui):
    ui.set_look(theme="prototipo")
    ui.screen.fill((13, 16, 20))
    ui.rr((100, 100, 200, 72), (255, 138, 61), 36)
    esquina = {tuple(ui.screen.get_at((x, y)))[:3] for x in range(100, 112) for y in range(100, 112)}
    assert len(esquina) > 6, "la esquina tiene tonos intermedios"
    assert tuple(ui.screen.get_at((200, 136)))[:3] == (255, 138, 61)
    ui.rr((10, 10, 8, 8), (1, 2, 3), 36)                          # más pequeño que el radio: no revienta


def test_descargas_en_todos_los_temas_dibuja_y_captura(ui):
    ds = [_D(1, "done", 1, "A"), _D(2, "active", .4, "B"), _D(3, "error", 0, "C"), _D(4, "queued", 0, "D")]
    ui.mgr.list = lambda: ds
    for th in ("dark", "light", "quiver", "prototipo", "cristal"):
        ui.set_look(theme=th, fx="glass")
        ui.go_tab("downloads")
        for _ in range(4):
            ui.frame()
        shot(ui, f"77_descargas_{th}.png")
    ui.set_look(theme="dark")


def test_los_efectos_se_notan_en_prototipo(ui):
    """Antes el interruptor de EFECTOS no hacía nada fuera del tema Oscuro: ahora Prototipo tiene fondo con profundidad (y liso en RENDIMIENTO)."""
    ui.set_look(theme="prototipo", fx="glass")
    a = ui.ambient()
    ui.set_look(theme="prototipo", fx="perf")
    b = ui.ambient()
    esq = (int(ui.W * .92), int(ui.H * .03))
    centro = (ui.W // 2, ui.H // 2)
    assert tuple(a.get_at(esq))[:3] != tuple(a.get_at(centro))[:3], "con cristal el fondo tiene resplandor"
    assert tuple(b.get_at(esq))[:3] == tuple(b.get_at(centro))[:3], "en rendimiento es liso"
    assert tuple(a.get_at(esq))[0] > tuple(b.get_at(esq))[0], "el resplandor de Prototipo es del color del acento (naranja)"
