"""v1.65: Descargas en tarjetas, insignia en la pestaña y selector del juego en tu carpeta de ROM al reconocerla."""
import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import shot


class _D:
    def __init__(s, i, st, p, t):
        s.id, s.state, s.progress, s.meta, s.name, s.url = i, st, p, {"title": t}, t, "u"
        s.speed, s.done, s.size = (3e6 if st == "active" else 0), int(p * 8e8), 8e8
        s.error, s.verified, s.catalog = "Fallo\nmás detalle", st == "done", False

    def eta(s):
        return 60


@pytest.fixture(scope="module")
def _ui_unica():
    import hub.ui as H
    u = H.UI()
    yield u
    u.running = False


def _con_descargas(u):
    ds = [_D(1, "done", 1, "A"), _D(2, "active", .4, "B"), _D(3, "error", 0, "C"), _D(4, "queued", 0, "D")]
    u.mgr.list = lambda: ds
    u.go_tab("downloads")
    for _ in range(4):
        u.frame()
    return ds


def test_descargas_dibuja_tarjetas_y_registra_sus_botones(_ui_unica):
    u = _ui_unica
    _con_descargas(u)
    keys = {w.key for w in u.widgets}
    shot(u, "descargas_v165")
    assert u.tab == "downloads"
    assert {"dl:1", "dl:2", "dl:3", "dl:4"} <= keys


def test_la_insignia_cuenta_activas_y_en_cola(_ui_unica):
    u = _ui_unica
    ds = _con_descargas(u)
    n = sum(1 for d in ds if d.state in ("active", "queued"))
    assert n == 2
    u.dl_pulse = __import__("time").time()
    u.frame()  # no debe fallar con el latido


def test_error_largo_se_recorta_a_una_linea(_ui_unica):
    u = _ui_unica
    _con_descargas(u)
    for _ in range(2):
        u.frame()   # el texto de error con saltos de línea no revienta el dibujo


def test_auto_libcwd_activa_el_selector(_ui_unica, tmp_path, monkeypatch):
    import hub.ui as H
    from hub import gamecfg, library
    u = _ui_unica
    e = {"id": "bk", "name": "BK", "platform": "Nintendo 64"}
    rom = tmp_path / "roms" / "BK.z64"
    rom.parent.mkdir()
    rom.write_bytes(b"x")
    calls = []
    monkeypatch.setattr(u, "inst", lambda ent: {"installed": True, "launcher_id": "bk"})
    monkeypatch.setattr(gamecfg, "state", lambda lid: {"exists": True, "libcwd": False})
    monkeypatch.setattr(library, "link_get", lambda i: str(rom))
    monkeypatch.setattr(gamecfg, "set_libcwd", lambda lid, f, on: calls.append((lid, f, on)))
    u.cfg["auto_libcwd"] = True        # v1.96: apagado por defecto (cambiar cwd movía la config de juegos como Silent Hill); sigue funcionando si lo activas
    assert "selector" in u._auto_libcwd(e)
    assert calls == [("bk", str(rom.parent), True)]
    u.cfg["auto_libcwd"] = False
    calls.clear()
    assert u._auto_libcwd(e) == "" and not calls


def test_las_tarjetas_no_usan_caracteres_fuera_de_la_fuente():
    """Un glifo que la fuente no trae se ve como un cuadrado: los iconos de las tarjetas se dibujan con formas."""
    import inspect
    import hub.ui as H
    src = inspect.getsource(H.UI.draw_downloads) + inspect.getsource(H.UI.dl_card)
    assert not [c for c in src if ord(c) > 0x2000 and c not in "—…·«»"], "no uses símbolos Unicode dentro de las tarjetas"
