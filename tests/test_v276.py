"""v2.76: actualizar por encima aplana la carpeta superior del zip; reparar una carpeta que ya quedó anidada (BT4/BT3)."""
import os
import zipfile
from pathlib import Path

import pytest

from hub import install

ELF = b"\x7fELF" + b"\0" * 60


def _zip(path: Path, top: str, files: dict):
    with zipfile.ZipFile(path, "w") as z:
        for n, data in files.items():
            zi = zipfile.ZipInfo(f"{top}/{n}")
            zi.external_attr = (0o755 if data.startswith(b"\x7fELF") else 0o644) << 16
            z.writestr(zi, data)


def _viejo(d: Path):
    d.mkdir()
    (d / "BT4decomp").write_bytes(ELF + b"old")
    (d / "README.txt").write_text("old")
    (d / "lib").mkdir()
    (d / "lib" / "a.so").write_text("old")
    (d / "gamedata").mkdir()
    (d / "gamedata" / "disc.bin").write_text("MI DISCO")
    (d / "saves").mkdir()
    (d / "saves" / "s1").write_text("partida")


NUEVO = {"BT4decomp": ELF + b"new", "README.txt": b"new", "lib/a.so": b"new", "lib/b.so": b"new", "CHANGELOG.txt": b"c"}


def test_actualizar_por_encima_aplana_y_conserva_datos(tmp_path):
    d = tmp_path / "juego"
    _viejo(d)
    z = tmp_path / "r.zip"
    _zip(z, "BT4decomp", NUEVO)
    install.extract(z, d)
    assert (d / "BT4decomp").is_file() and (d / "BT4decomp").read_bytes().endswith(b"new")
    assert (d / "lib" / "b.so").exists() and (d / "CHANGELOG.txt").exists()
    assert (d / "gamedata" / "disc.bin").read_text() == "MI DISCO" and (d / "saves" / "s1").read_text() == "partida"
    assert os.access(d / "BT4decomp", os.X_OK)
    assert install.nested_dir(d) is None


def test_actualizar_no_escribe_a_traves_de_enlace_duro(tmp_path):
    d, prev = tmp_path / "juego", tmp_path / "juego.prev"
    _viejo(d)
    prev.mkdir()
    os.link(d / "README.txt", prev / "README.txt")
    z = tmp_path / "r.zip"
    _zip(z, "BT4decomp", NUEVO)
    install.extract(z, d)
    assert (d / "README.txt").read_text() == "new"
    assert (prev / "README.txt").read_text() == "old"          # la copia apartada sigue intacta


def test_destino_vacio_sigue_aplanando(tmp_path):
    d = tmp_path / "nuevo"
    z = tmp_path / "r.zip"
    _zip(z, "BT4decomp", NUEVO)
    install.extract(z, d)
    assert (d / "BT4decomp").is_file() and not (d / "BT4decomp" / "BT4decomp").exists()


def test_zip_sin_carpeta_superior_no_se_toca(tmp_path):
    d = tmp_path / "juego"
    _viejo(d)
    z = tmp_path / "r.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("README.txt", "new")
        zf.writestr("lib/b.so", "new")
    install.extract(z, d)
    assert (d / "README.txt").read_text() == "new" and (d / "lib" / "b.so").exists()


def _anidado(d: Path):
    """El estado real de Carlos: en la raíz «BT4decomp» es una CARPETA con la versión nueva y los datos viejos siguen en la raíz."""
    d.mkdir()
    (d / "README.txt").write_text("old")
    (d / "gamedata").mkdir()
    (d / "gamedata" / "disc.bin").write_text("MI DISCO")
    (d / "saves").mkdir()
    (d / "saves" / "s1").write_text("partida")
    (d / "mods").mkdir()
    (d / "mods" / "mio.lua").write_text("mi mod")
    n = d / "BT4decomp"
    n.mkdir()
    (n / "BT4decomp").write_bytes(ELF + b"new")
    (n / "README.txt").write_text("new")
    (n / "lib").mkdir()
    (n / "lib" / "b.so").write_text("new")
    (n / "mods").mkdir()
    (n / "mods" / "skill_list.lua").write_text("nuevo")
    (n / "mods" / "mio.lua").write_text("pisaria el tuyo")


def test_reparar_carpeta_anidada(tmp_path):
    d = tmp_path / "bt4"
    _anidado(d)
    assert install.nested_dir(d).name == "BT4decomp"
    r = install.flatten_nested(d)
    assert r["moved"] >= 2 and r["kept"] == 1
    assert (d / "BT4decomp").is_file() and (d / "BT4decomp").read_bytes().endswith(b"new")
    assert (d / "README.txt").read_text() == "new" and (d / "lib" / "b.so").exists()
    assert (d / "gamedata" / "disc.bin").read_text() == "MI DISCO" and (d / "saves" / "s1").read_text() == "partida"
    assert (d / "mods" / "mio.lua").read_text() == "mi mod" and (d / "mods" / "skill_list.lua").read_text() == "nuevo"
    assert (d / ".hub-replaced" / "README.txt").read_text() == "old"     # lo sustituido se apartó, no se perdió
    assert install.nested_dir(d) is None and not (d / ".hub-flatten").exists()


def test_reparar_sin_problema_no_hace_nada(tmp_path):
    d = tmp_path / "ok"
    _viejo(d)
    assert install.nested_dir(d) is None and install.flatten_nested(d) == {}


def test_una_carpeta_normal_no_se_confunde(tmp_path):
    d = tmp_path / "g"
    d.mkdir()
    (d / "game.exe").write_text("x")
    (d / "data").mkdir()
    (d / "data" / "a").write_text("1")
    assert install.nested_dir(d) is None


# ── cambiar archivo (ISO) ──
def test_relink_cambia_los_enlaces_de_linux_y_windows_conservando_el_nombre(tmp_path):
    from hub import library
    root = tmp_path / "chavo"
    (root / "linux").mkdir(parents=True)
    (root / "windows").mkdir()
    a, b = tmp_path / "A.iso", tmp_path / "B.iso"
    a.write_text("a")
    b.write_text("b")
    for sub in ("linux", "windows"):
        (root / sub / "El Chavo Kart.iso").symlink_to(a)
    (root / "windows" / "real.txt").write_text("no es enlace")
    ajeno = tmp_path / "otro.iso"
    ajeno.write_text("x")
    (root / "windows" / "otro.iso").symlink_to(ajeno)
    assert library.relink(root, a, b) == 2
    for sub in ("linux", "windows"):
        assert (root / sub / "El Chavo Kart.iso").resolve() == b.resolve()
    assert (root / "windows" / "otro.iso").resolve() == ajeno.resolve()      # los demás enlaces no se tocan
    assert (root / "windows" / "real.txt").read_text() == "no es enlace"
    assert library.relink(root, a, a) == 0 and library.relink(root, None, b) == 0


def test_relink_desde_la_subcarpeta_linux(tmp_path):
    from hub import library
    root = tmp_path / "j"
    (root / "linux").mkdir(parents=True)
    (root / "windows").mkdir()
    a, b = tmp_path / "A.iso", tmp_path / "B.iso"
    a.write_text("a")
    b.write_text("b")
    (root / "windows" / "x.iso").symlink_to(a)
    assert library.relink(root / "linux", a, b) == 1


# ── abecedario del selector ──
def test_lead_letra_sin_acentos():
    from hub import ui as U
    f = U.UI._lead
    if f is None:
        pytest.skip("clase de la app con otro nombre")
    assert f("Álvaro.iso") == "A" and f("007 Nightfire.iso") == "#" and f("[USA] zelda.z64") == "U"


from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401,E402


def test_selector_con_abecedario(ui, tmp_path):
    for n in ["Zelda.z64", "Banjo.z64", "Alpha.iso", "Bomberman.z64", "Castlevania.iso", "Dino.iso", "Earthworm.iso", "Final.iso",
              "Gex.iso", "Halo.iso", "Ico.iso", "Jak.iso", "Kirby.z64", "Lego.iso", "Mario.z64", "Ninja.iso", "007 Nightfire.iso", "Xbox 360 game.iso"]:
        (tmp_path / n).write_text("x" * 10)
    elegido = []
    ui.detail = None
    ui.open_picker("Elige tu archivo", tmp_path, None, elegido.append)
    m = ui.modal
    letras = dict(m["letters"])
    assert list(letras)[0] == "#" and "Z" in letras and "X" in letras and list(letras)[1] == "A"       # «#» (cifras) primero, como en la lista
    assert [it[2].name for it in m["items"]][:3] == ["007 Nightfire.iso", "Alpha.iso", "Banjo.z64"]            # orden alfabético, no por fecha
    run(ui, 2)
    ui.picker_jump(letras["Z"])
    assert ui.focus == "f:Zelda.z64"
    ui.picker_jump(0)
    assert ui.picker_letter_step(1) and ui.focus == "f:Alpha.iso"
    ui.picker_letter_step(1)
    assert ui.focus == "f:Banjo.z64"
    ui.picker_letter_step(-1)
    assert ui.focus == "f:Alpha.iso"
    run(ui, 2)
    from conftest import shot
    shot(ui, "v276_selector_abecedario.png")
    ui.close_modal()


def test_selector_pocas_filas_sin_abecedario(ui, tmp_path):
    for n in ("a.iso", "b.iso"):
        (tmp_path / n).write_text("x")
    ui.open_picker("x", tmp_path, None, lambda p: None)
    assert ui.modal["letters"] == []
    ui.close_modal()


# ── script de arranque editado a mano (Pokémon) ──
def test_write_script_no_pisa_el_script_editado_a_mano(tmp_path):
    from hub import ownwine
    win = tmp_path / "windows"
    win.mkdir()
    (win / "juego.exe").write_text("MZ")
    w = {"game_exe": "juego.exe", "own": {"binary": "/usr/bin/true", "prefix": "", "profile": "generic"}}
    assert ownwine.write_script(win, w) == "ok" and not ownwine.is_custom(win)          # sin script previo: lo escribe Hub
    assert ownwine.write_script(win, w) == "ok"                                         # y uno de Hub se puede reescribir
    mio = "#!/bin/bash\n# arranco un servidor y luego wine\nwine juego.exe\n"
    (win / "hub-run.sh").write_text(mio)
    assert ownwine.is_custom(win)
    assert ownwine.write_script(win, w) == "custom"
    assert (win / "hub-run.sh").read_text() == mio                                      # intacto
    assert "Recomp Hub:" in (win / "hub-run.sh.hub").read_text()                        # lo que habría escrito Hub, al lado
    assert ownwine.write_script(win, w, force=True) == "ok"
    assert (win / "hub-run.sh.mio").read_text() == mio and not ownwine.is_custom(win)   # elegir el de Hub guarda el tuyo


# ═══ v2.77: red con VPN, arte, indicador de trabajo ═══
import socket
import ssl
import urllib.error


def test_nethttp_describe_dice_la_causa():
    from hub import nethttp as N
    assert "tiempo agotado" in N.describe(urllib.error.URLError(socket.timeout("timed out")))
    assert "DNS" in N.describe(urllib.error.URLError(socket.gaierror(-2, "x")))
    assert "certificado" in N.describe(urllib.error.URLError(ssl.SSLCertVerificationError("bad")))
    assert "rechazada" in N.describe(ConnectionRefusedError())


def test_nethttp_reintenta_por_ipv4_y_explica(monkeypatch):
    from hub import nethttp as N
    modos = []

    def falso(url, h, t, m, v4, t12=False):
        modos.append(v4)
        if not v4:
            raise urllib.error.URLError(socket.timeout("timed out"))
        return b"ok"
    monkeypatch.setattr(N, "_once", falso)
    monkeypatch.setattr(N.time, "sleep", lambda s: None)
    assert N.get("https://x.test/a") == b"ok" and modos == [False, True]           # IPv6 colgado → el segundo intento va solo por IPv4
    monkeypatch.setattr(N, "_once", lambda *a: (_ for _ in ()).throw(urllib.error.URLError(socket.gaierror(-2, "x"))))
    with pytest.raises(OSError) as ex:
        N.get("https://x.test/a")
    assert "x.test no responde" in str(ex.value) and "DNS" in str(ex.value) and "URLError" not in str(ex.value)


def test_nethttp_relanza_los_4xx(monkeypatch):
    from hub import nethttp as N
    monkeypatch.setattr(N, "_once", lambda *a: (_ for _ in ()).throw(urllib.error.HTTPError("u", 403, "no", {}, None)))
    with pytest.raises(urllib.error.HTTPError):
        N.get("https://x.test/a")


def test_sgdb_distingue_cloudflare_de_clave_mala(monkeypatch):
    import io
    from hub import sgdb

    def http403(txt):
        def f(*a, **k):
            raise urllib.error.HTTPError("u", 403, "no", {}, io.BytesIO(txt.encode()))
        return f
    monkeypatch.setattr(sgdb.nethttp, "get", http403("<title>Just a moment...</title> cloudflare"))
    with pytest.raises(OSError, match="Cloudflare"):
        sgdb.search("zelda")
    monkeypatch.setattr(sgdb.nethttp, "get", http403('{"error":"bad key"}'))
    with pytest.raises(OSError, match="rechazó la clave"):
        sgdb.search("zelda")


def test_guardar_clave_conserva_la_anterior(tmp_path, monkeypatch):
    from hub import sgdb, config
    monkeypatch.setattr(config, "LAUNCHER", tmp_path)
    monkeypatch.delenv("STEAMGRIDDB_KEY", raising=False)
    monkeypatch.delenv("STEAMGRIDDB_API_KEY", raising=False)
    sgdb.save_key("AAAA")
    sgdb.save_key("BBBB")
    assert sgdb.key() == "BBBB" and (tmp_path / "state" / ".sgdb_key.prev").read_text().strip() == "AAAA"


def test_trabajo_muestra_rueda_y_termina(ui):
    import time
    import threading
    ev = threading.Event()
    res = []
    ui.work("Reparando algo…", lambda: (ev.wait(2), 7)[1], lambda r, e: res.append((r, e)))
    assert ui._work
    run(ui, 2)
    from conftest import shot
    shot(ui, "v277_trabajo.png")
    ev.set()
    for _ in range(100):
        if res:
            break
        time.sleep(0.02)
    assert res == [(7, None)] and not ui._work


def test_pantalla_arte_cambiar_clave_pide_confirmacion(ui, monkeypatch):
    from hub import sgdb
    monkeypatch.setattr(sgdb, "key", lambda: "ABCD1234")
    e = ui.entries[0]
    ui.art = {"src": "sgdb", "e": e, "step": "game", "games": [], "gid": None, "kind": "portrait", "imgs": [], "raw": {}, "surf": {}, "busy": "", "err": "", "picked": {}}
    ui.tab, ui.detail, ui.focus = "art", None, None
    run(ui, 3)
    claves = [w.key for w in ui.widgets]
    assert "a_chg" in claves and "a_net" in claves and "a_key" not in claves          # ya no hay botón de cambiar bajo el selector
    w = next(w for w in ui.widgets if w.key == "a_chg")
    ui.fire(w)
    assert ui.modal and ui.modal["kind"] == "confirm"                                  # un toque no basta: pide confirmar
    from conftest import shot
    ui.close_modal()
    run(ui, 2)
    shot(ui, "v277_arte.png")
    ui.art, ui.tab = None, "home"
