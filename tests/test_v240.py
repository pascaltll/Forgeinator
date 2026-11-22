"""v2.40: «Wine propio» (God of War PSP): lanzador, compilar, ISO por ID y qué se borra al actualizar."""
import os
import stat
import subprocess

import pytest

from test_v195 import juego, _t  # noqa: F401
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio  # noqa: F401

pygame = pytest.importorskip("pygame")


def _gow(tmp_path, juego_d):
    """Un 'gow-psp-recomp' falso: GoWLauncher.exe + build/ con todas las carpetas, y un wine falso que anota sus argumentos."""
    from hub import osver
    src = tmp_path / "gowsrc"
    b = src / "GoW_PSP_data" / "build"
    for n in ("gen", "mingw_full", "eboot", "deps", "toolchain", "mingw_tools"):
        (b / n).mkdir(parents=True)
        (b / n / "x").write_text("1")
    (b / "mingw_full" / "gow_rt_UCUS98653_full.exe").write_text("exe")
    (src / "GoWLauncher.exe").write_text("MZ")
    wine = tmp_path / "wine"
    wine.write_text('#!/bin/sh\nprintf "WINE %s\\n" "$*" > "$LOG"\nprintf "PFX=%s OV=%s\\n" "$WINEPREFIX" "$WINEDLLOVERRIDES" >> "$LOG"\n')
    wine.chmod(0o755)
    osver.attach_windows("sh", src / "GoWLauncher.exe", "proton")
    return src, wine


def _own(tmp_path, wine):
    from hub import osver
    r = osver.root_of("sh")
    m = osver.meta(r)
    w = m["windows"]
    w["own"] = {"binary": str(wine), "prefix": str(tmp_path / "pfx")}
    osver._save_meta(r, m)
    osver.set_windows_runner("sh", "own")
    osver.set_own("sh", mode="direct")
    return r


def test_lanzador_propio_pasa_wine_disco_y_banderas(juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    r = _own(tmp_path, wine)
    from hub import osver, ownwine
    assert osver.windows_runner("sh") == "own"
    sh = (r / "windows" / "hub-run.sh").read_text()
    assert subprocess.run(["sh", "-n", "-c", sh]).returncode == 0 and "umu-run" not in sh
    iso = tmp_path / "Chains.iso"
    iso.write_text("x")
    (r / "windows" / "own-disc-coo").write_text(str(iso))
    log = tmp_path / "log"
    p = subprocess.run([str(r / "windows" / "hub-run.sh")], env=dict(os.environ, LOG=str(log)), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    t = log.read_text()
    assert "gow_rt_UCUS98653_full.exe --boot --disc Z:" + str(iso).replace("/", "\\") in t
    assert "--fullscreen --fps 60 --renderer gpu --res-scale 2" in t
    assert f"PFX={tmp_path / 'pfx'}" in t and "mscms=n,b" in t and "d3d12core=n,b" in t


def test_sin_compilar_o_sin_iso_dice_que_falta(juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    r = _own(tmp_path, wine)
    env = dict(os.environ, LOG=str(tmp_path / "l"), HUB_GOW="gos")
    p = subprocess.run([str(r / "windows" / "hub-run.sh")], env=env, capture_output=True, text=True)
    assert p.returncode == 3 and "aún no está compilado" in p.stderr
    p = subprocess.run([str(r / "windows" / "hub-run.sh")], env=dict(os.environ, LOG=str(tmp_path / "l")), capture_output=True, text=True)
    assert p.returncode == 4 and "ISO USA" in p.stderr


def test_compilar_usa_wine_propio_y_el_launcher(juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    r = _own(tmp_path, wine)
    from hub import ownwine, osver
    w = osver.meta(r)["windows"]
    (desc, argv), = ownwine.build_steps(r / "windows", w, "gos")
    assert argv[0] == "env" and argv[-3].endswith("GoWLauncher.exe") and argv[-2:] == ["--build", "gos"] and argv[-4] == str(wine)
    assert any(a.startswith("WINEPREFIX=") for a in argv) and any(a.startswith("WINEDLLOVERRIDES=mscms") for a in argv)


def test_actualizar_borra_solo_lo_generado_y_conserva_el_wine_propio(juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    r = _own(tmp_path, wine)
    from hub import osver
    import zipfile
    z = tmp_path / "rel.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("GoWLauncher.exe", "MZ2")
    # la instalación de Windows vive en windows/ (aquí con enlace «game»: usamos install_windows sobre un windows real)
    win = r / "windows"
    (win / "game").unlink()
    (win / "GoW_PSP_data" / "build").mkdir(parents=True)
    b = win / "GoW_PSP_data" / "build"
    for n in ("gen", "mingw_full", "eboot", "deps", "toolchain", "mingw_tools"):
        (b / n).mkdir()
        (b / n / "x").write_text("1")
    (win / "GoWLauncher.exe").write_text("MZ")
    m = osver.meta(r)
    m["windows"].pop("local", None)
    m["windows"]["game_exe"] = "GoWLauncher.exe"
    osver._save_meta(r, m)
    osver.install_windows("sh", z, "v9")
    assert osver.windows_runner("sh") == "own"
    m2 = osver.meta(r)["windows"]
    assert m2["own"]["binary"] == str(wine) and m2["rebuild"] is True
    for n in ("gen", "mingw_full", "eboot"):
        assert not (b / n).exists(), n
    for n in ("deps", "toolchain", "mingw_tools"):
        assert (b / n / "x").exists(), n
    assert "umu-run" not in (win / "hub-run.sh").read_text()


def test_el_iso_se_reconoce_por_su_id(tmp_path, monkeypatch):
    from pathlib import Path
    from hub import ownwine, discid
    a, b = tmp_path / "a.iso", tmp_path / "b.iso"
    a.write_text("a"); b.write_text("b")
    ids = {str(a): "UCUS98737", str(b): "NPUG80325"}
    monkeypatch.setattr(discid, "read_id", lambda p: {"id": ids.get(str(p.resolve()) if hasattr(p, "resolve") else str(p), "")} if str(p.resolve()) in ids else None)
    f = ownwine.note_disc(tmp_path, a)
    assert list(f) == ["gos"] and ownwine.disc_of(tmp_path, "gos") == str(a.resolve()) and ownwine.disc_of(tmp_path, "coo") == ""


def test_la_ficha_dibuja_el_panel(H, ui, juego, tmp_path, monkeypatch):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    _own(tmp_path, wine)
    e = {"id": "sh", "name": "Silent Hill"}
    oi = ui.own_info("sh")
    assert oi and oi["wine_ok"] and oi["built"]["coo"] and not oi["built"]["gos"] and not oi["disc"]["coo"]
    ui.set_win_runner(e, "own")
    ui.set_own_game(e, "gos")
    ui._own_c = {}
    assert ui.own_info("sh")["cfg"]["game"] == "gos"
    assert "HUB_GOW" in (d / "windows" / "hub-run.sh").read_text() and 'GAME="${HUB_GOW:-gos}"' in (d / "windows" / "hub-run.sh").read_text()


def test_el_panel_se_dibuja_sin_fallar(H, ui, juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    _own(tmp_path, wine)
    ui.frame()
    oi = ui.own_info("sh")
    e = {"id": "sh", "name": "Silent Hill"}
    y = ui._own_panel(e, oi, 40, 40, 900)
    assert y > 40
    oi["wine_ok"], oi["rebuild"] = False, True
    assert ui._own_panel(e, oi, 40, 40, 900) > y


# ── v2.41 ──
def test_varios_discos_por_id(H, ui, tmp_path, monkeypatch):
    from hub import library, discid
    monkeypatch.setattr(library, "LINKS", tmp_path / "links.json")
    a, b, c = tmp_path / "coo.iso", tmp_path / "gos.iso", tmp_path / "psn.iso"
    for p in (a, b, c):
        p.write_text("x")
    ids = {str(a): "UCUS98653", str(b): "UCUS98737", str(c): "NPUG80325"}
    monkeypatch.setattr(discid, "read_id", lambda p: {"id": ids[str(p)], "kind": "psp", "note": ""} if str(p) in ids else None)
    e = {"id": "gow", "requires": {"serials": ["UCUS98653", "UCUS98737"]}}
    assert ui._note_disc_link(e, a) == "UCUS98653" and ui._note_disc_link(e, b) == "UCUS98737" and ui._note_disc_link(e, c) is None
    assert library.disc_links("gow") == {"UCUS98653": str(a), "UCUS98737": str(b)}
    assert ui._note_disc_link({"id": "x", "requires": {"serials": ["UCUS98653"]}}, a) is None   # un solo disco: sigue el camino de siempre


def test_antes_de_lanzar_dice_que_falta(H, ui, juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    r = _own(tmp_path, wine)
    e = {"id": "sh", "name": "Silent Hill"}
    ui.os_state("sh")
    ui._osv.pop("sh", None)
    from hub import osver
    osver.set_active("sh", "windows")
    ui._osv.pop("sh", None)
    msg = ui.own_block(e, "sh")
    assert "ISO USA" in msg                      # coo está compilado pero no hay ISO
    (r / "windows" / "own-disc-coo").write_text(str(tmp_path / "wine"))
    ui._own_c = {}
    assert ui.own_block(e, "sh") == ""
    ui.set_own_game(e, "gos")
    assert "aún no está compilado" in ui.own_block(e, "sh")


def test_el_vigia_no_cierra_hub_si_el_juego_muere(H, ui, monkeypatch):
    import time
    from hub import launchwatch
    ui.exit_at = time.time() + 3
    ui.steam_cover = {"lid": "x", "nd": ["x"], "chk": 0, "bad": 0}
    monkeypatch.setattr(launchwatch, "alive", lambda *a, **k: False)
    for _ in range(3):
        ui.steam_cover["chk"] = 0
        ui.pump()
    assert ui.exit_at is None and ui.steam_cover is None


def test_elegir_wine_propio_hace_que_el_launcher_abra_hub_run(H, ui, juego, tmp_path):
    d, toml = juego
    src, wine = _gow(tmp_path, d)
    from hub import osver, launchlog
    e = {"id": "sh", "name": "Silent Hill"}
    r = osver.root_of("sh")
    m = osver.meta(r)
    m["windows"]["own"] = {"binary": str(wine), "prefix": str(tmp_path / "pfx")}
    osver._save_meta(r, m)
    ui.set_win_runner(e, "own")
    assert osver.windows_runner("sh") == "own"
    assert launchlog.binary_of("sh").resolve() == (r / "windows" / "hub-run.sh").resolve(), launchlog.binary_of("sh")


# ── v2.42 ──
def test_por_defecto_abre_el_launcher_y_directo_es_opcional(juego, tmp_path):
    d, _ = juego
    src, wine = _gow(tmp_path, d)
    from hub import osver
    r = osver.root_of("sh")
    m = osver.meta(r)
    m["windows"]["own"] = {"binary": str(wine), "prefix": str(tmp_path / "pfx")}
    osver._save_meta(r, m)
    osver.set_windows_runner("sh", "own")
    assert osver.meta(r)["windows"]["own"]["mode"] == "launcher"
    log = tmp_path / "salida.log"
    p = subprocess.run([str(r / "windows" / "hub-run.sh"), "--x"], env=dict(os.environ, LOG=str(log)), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "GoWLauncher.exe --x" in log.read_text() and "gow_rt" not in log.read_text()
    osver.set_own("sh", mode="direct")
    p = subprocess.run([str(r / "windows" / "hub-run.sh")], env=dict(os.environ, LOG=str(log)), capture_output=True, text=True)
    assert p.returncode == 4                     # directo: pide el ISO
    p = subprocess.run([str(r / "windows" / "hub-run.sh")], env=dict(os.environ, LOG=str(log), HUB_MODE="launcher"), capture_output=True, text=True)
    assert p.returncode == 0 and "GoWLauncher.exe" in log.read_text()


def test_wine_propio_en_cualquier_juego(H, ui, juego, tmp_path):
    d, _ = juego
    from hub import osver, ownwine, launchlog
    exe = tmp_path / "otro" / "Juego.exe"
    exe.parent.mkdir()
    exe.write_text("MZ")
    wine = tmp_path / "wine"
    wine.write_text('#!/bin/sh\nprintf "WINE %s\\n" "$*" > "$LOG"\nprintf "PFX=%s OV=[%s]\\n" "$WINEPREFIX" "$WINEDLLOVERRIDES" >> "$LOG"\n')
    wine.chmod(0o755)
    osver.attach_windows("sh", exe, "proton")
    e = {"id": "sh", "name": "Silent Hill"}
    oi = ui.own_info("sh")
    assert oi and oi["cfg"]["profile"] == "generic" and not oi["wine_ok"]      # aparece para cualquier juego, aún sin Wine
    ui.set_win_runner(e, "own")
    assert "ELEGIR EL WINE" in ui.own_block(e, "sh") or "Elige tu Wine" in ui.own_block(e, "sh")
    osver.set_own("sh", binary=str(wine), overrides="d3d11=n,b")
    ui._own_c = {}
    assert ui.own_block(e, "sh") == ""
    r = osver.root_of("sh")
    log = tmp_path / "salida.log"
    p = subprocess.run([str(r / "windows" / "hub-run.sh"), "-a"], env=dict(os.environ, LOG=str(log)), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    t = log.read_text()
    assert "Juego.exe -a" in t and "OV=[d3d11=n,b]" in t and "proton-prefix" in t
    assert launchlog.binary_of("sh").resolve() == (r / "windows" / "hub-run.sh").resolve()
    ui.frame()
    assert ui._own_panel(e, ui.own_info("sh"), 40, 40, 900) > 40


def test_panel_de_discos_para_cualquier_port_de_varios_discos(H, ui, tmp_path, monkeypatch):
    from hub import library
    monkeypatch.setattr(library, "LINKS", tmp_path / "links.json")
    ui.frame()
    e = {"id": "multi", "name": "Multi", "requires": {"serials": ["AAAA00001", "UCUS98737"]}}
    y = ui._discs_panel(e, 40, 40, 900)
    assert y > 40
    assert ui._discs_panel({"id": "x", "requires": {"serials": ["A"]}}, 40, 40, 900) == 40


# ── v2.43 ──
def test_congelar_actualizaciones_de_un_juego(H, ui, juego, tmp_path):
    d, toml = juego
    from hub import osver
    t0 = toml.read_text()
    if "[update]" not in t0:
        toml.write_text(t0 + '\n[update]\ntype = "github-archive"\nrepo = "a/b"\nasset = "x.zip"\ncountdown = 5\n')
    e = {"id": "sh", "name": "Silent Hill"}
    ui.cfg["frozen"] = {}
    ui.toggle_freeze(e)
    assert ui.frozen(e) and 'type = "none"' in toml.read_text().split("[update]")[1].split("[")[0]
    assert ui.cfg["frozen"]["sh"]["type"] == "github-archive"
    ui.toggle_freeze(e)
    assert not ui.frozen(e) and 'type = "github-archive"' in toml.read_text()
    assert ui.cfg["frozen"] == {}


def test_fondos_baratos_se_dibujan_cada_cuadro_y_los_brillos_van_en_cache(H, ui, monkeypatch):
    import hub.ui as HH
    n = {"anim": 0}
    real = ui.draw_anim
    monkeypatch.setattr(ui, "draw_anim", lambda: (n.__setitem__("anim", n["anim"] + 1), real())[1])
    ui.set_look(theme="cubo", fx="glass")
    ui.cfg["bgs"] = {"cubo": "spincube"}
    ui.set_look(theme="cubo", fx="glass")
    assert HH.ANIM not in ("aurora", "drift"), HH.ANIM
    n["anim"] = 0
    for _ in range(6):
        ui.draw_bg()
    assert n["anim"] == 6                         # cada fotograma, sin caché: la animación no va a tirones


# ── v2.44 ──
def test_elegir_release_pagina_de_7_en_7(H, ui):
    e = {"id": "rl", "name": "Rl", "repo": "a/b"}
    lst = [{"tag": f"v0.{i}", "published": "2026-11-01", "linux": 1, "windows": 1, "prerelease": False} for i in range(20)]
    ui.rel_sum[ui.rk(e)] = lst
    ui.pick_release(e)
    labs = [o[0] for o in ui.modal["options"]]
    assert labs[0].startswith("ÚLTIMA") and labs[1].startswith("v0.0") and labs[7].startswith("v0.6") and labs[-1].startswith("MÁS ANTIGUAS") and "(13 más)" in labs[-1]
    ui.modal["options"][-1][1]()                        # MÁS ANTIGUAS
    labs = [o[0] for o in ui.modal["options"]]
    assert labs[0].startswith("◂ MÁS NUEVAS") and labs[1].startswith("v0.7") and "8–14 de 20" in ui.modal["title"]
    ui.modal["options"][-1][1](); ui.modal["options"][-1][1]()
    assert ui.modal["options"][-1][0].startswith("v0.19") and "15–20" in ui.modal["title"] or "20 de 20" in ui.modal["title"]


def test_github_pide_40_releases():
    import inspect
    from hub import github
    assert "per_page=40" in inspect.getsource(github.releases)


def _zipf(path, files):
    import zipfile
    with zipfile.ZipFile(path, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
    return path


def test_instalacion_limpia_aparta_la_actual_y_recupera_tus_datos(tmp_path, monkeypatch):
    from hub import install, config
    g, l = tmp_path / "Games", tmp_path / "launcher"
    (l / "games").mkdir(parents=True)
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", l)
    ELF = b"\x7fELF" + b"\0" * 60
    e = {"id": "bt3", "name": "BT3 Latino", "repo": "u/bt3", "platform": "PC"}
    install.install(e, _zipf(tmp_path / "v2.zip", {"bt3": ELF, "lib/viejo.so": b"NUEVA?", "dato.bin": b"v2"}), "bt3.zip", "v2")
    (g / "bt3" / "saves").mkdir()
    (g / "bt3" / "saves" / "card1").write_text("MI PARTIDA")
    (g / "bt3" / "extra_mod.txt").write_text("mod")
    res = install.install(e, _zipf(tmp_path / "v1.zip", {"bt3": ELF, "dato.bin": b"v1"}), "bt3.zip", "v1", clean=True)
    assert (g / "bt3" / "dato.bin").read_bytes() == b"v1"                   # lo nuevo manda
    assert (g / "bt3" / "saves" / "card1").read_text() == "MI PARTIDA"      # tus datos vuelven
    assert (g / "bt3" / "extra_mod.txt").exists()
    assert res["backup"] and res["backup"].endswith("bt3.prev") and (g / "bt3.prev" / "dato.bin").read_bytes() == b"v2" and res["restored"] >= 2
    res2 = install.install(e, _zipf(tmp_path / "v3.zip", {"bt3": ELF}), "bt3.zip", "v3", clean=True)
    assert res2["backup"].endswith("bt3.prev2")                              # no pisa la copia anterior


def test_instalacion_limpia_que_falla_devuelve_la_carpeta_anterior(tmp_path, monkeypatch):
    from hub import install, config
    g, l = tmp_path / "Games", tmp_path / "launcher"
    (l / "games").mkdir(parents=True)
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", l)
    e = {"id": "j", "name": "J", "repo": "u/j", "platform": "PC"}
    install.install(e, _zipf(tmp_path / "a.zip", {"j": b"\x7fELF", "x": b"1"}), "j.zip", "v1")
    bad = tmp_path / "b.zip"
    bad.write_bytes(b"no soy un zip")
    with pytest.raises(Exception):
        install.install(e, bad, "j.zip", "v0", clean=True)
    assert (g / "j" / "x").read_bytes() == b"1" and not (g / "j.prev").exists()


def test_cambiar_de_version_pregunta_limpia_o_por_encima(H, ui, monkeypatch):
    e = ui.entries[0]
    monkeypatch.setattr(ui, "inst", lambda x: {"installed": True, "version": "v2", "launcher_id": x["id"]})
    monkeypatch.setattr(ui, "rel_for", lambda x: {"tag": "v1", "assets": [{"name": "a.zip", "url": "http://x/a.zip"}]})
    ui.modal = None
    ui.do_install(e)
    labs = [o[0] for o in ui.modal["options"]]
    assert labs[0].startswith("INSTALAR LIMPIA") and labs[1].startswith("INSTALAR POR ENCIMA") and "v1" in ui.modal["title"] and "v2" in ui.modal["title"]
    ui.modal = None


def test_interruptores_de_comprobar_al_arrancar_y_al_abrir_ficha(H, ui, monkeypatch):
    import time
    ui.cfg["check_on_start"] = False
    ui.cfg["fetch_on_open"] = True
    n = {"c": 0, "f": 0}
    monkeypatch.setattr(ui, "check_all", lambda: n.__setitem__("c", n["c"] + 1))
    monkeypatch.setattr(ui, "fetch", lambda *a, **k: n.__setitem__("f", n["f"] + 1))
    ui._boot_chk, ui._t_first_pump = False, time.time() - 10
    ui.pump()
    assert n["c"] == 0 and ui._boot_chk                                       # por defecto NO comprueba solo
    ui.cfg["check_on_start"] = True
    ui._boot_chk, ui._t_first_pump = False, time.time() - 10
    ui.pump()
    assert n["c"] == 1
    ui.pump()
    assert n["c"] == 1                                                         # una sola vez
    e = ui.entries[0]
    ui.rel.pop(ui.rk(e), None)
    ui.cfg["fetch_on_open"] = False
    ui.open_detail(e)
    assert n["f"] == 1                                                         # sin caché (p. ej. tras reinstalar) consulta ESTE juego aunque el interruptor esté apagado
    ui.rel[ui.rk(e)] = {"tag": "v1"}
    ui.open_detail(e)
    assert n["f"] == 1                                                         # con caché y apagado: no gasta llamadas
    ui.detail = None
    ui.cfg["check_on_start"] = False
    ui.toggle_cfg("check_on_start", False, "x")
    assert ui.cfg["check_on_start"] is True
    ui.toggle_cfg("check_on_start", False, "x")
    assert ui.cfg["check_on_start"] is False


def test_cambio_a_escritorio_prueba_primero_una_unidad_de_usuario(tmp_path, monkeypatch):
    from hub import steamsetup, config
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(steamsetup, "AUTOSTART", tmp_path / "a.desktop")
    tool = tmp_path / "sess"
    tool.write_text("#!/bin/sh\necho x\n"); tool.chmod(0o755)
    monkeypatch.setattr(steamsetup, "session_tool", lambda: str(tool))
    vistos = []
    real = steamsetup.subprocess.Popen

    def espia(cmd, *a, **k):
        vistos.append(list(cmd))
        return real(["true"], *a, **{kk: vv for kk, vv in k.items() if kk != "env"})
    monkeypatch.setattr(steamsetup.subprocess, "Popen", espia)
    monkeypatch.setattr(steamsetup.shutil, "which", lambda n: "/usr/bin/systemd-run" if n == "systemd-run" else None)
    ok, m = steamsetup.to_desktop()
    assert ok and vistos[0][0] == "/usr/bin/systemd-run" and "--user" in vistos[0] and "--wait" in vistos[0] and vistos[0][-2:] == [str(tool), "plasma"]


def test_si_steamos_dice_dentro_de_un_juego_el_mensaje_lo_explica(tmp_path, monkeypatch):
    from hub import steamsetup, config
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(steamsetup, "AUTOSTART", tmp_path / "a.desktop")
    tool = tmp_path / "sess"
    tool.write_text("#!/bin/sh\necho 'AuthFailed: Cannot message SteamOS Manager from within a game' >&2\nexit 1\n"); tool.chmod(0o755)
    monkeypatch.setattr(steamsetup, "session_tool", lambda: str(tool))
    monkeypatch.setattr(steamsetup.shutil, "which", lambda n: None)
    ok, m = steamsetup.to_desktop()
    assert not ok and "Cambiar a escritorio" in m and "dentro de un juego" in m


def test_ver_descarga_lleva_a_la_ficha(H, ui):
    class D: pass
    e = ui.entries[0]
    for k in ("install", "install_win"):
        d = D(); d.state = "done"; d.meta = {k: e["id"]}
        ui.detail, ui.rview, ui.tab = None, "x", "steam"
        ui.dl_main(d)
        assert ui.detail == e["id"] and ui.tab == "games" and ui.rview is None


def test_ficha_lee_el_disco_antes_que_github(H, ui, monkeypatch):
    from hub import github
    e = next(x for x in ui.entries if x.get("repo"))
    k = ui.rk(e)
    calls = {"f": 0}
    monkeypatch.setattr(ui, "fetch", lambda *a, **kw: calls.__setitem__("f", calls["f"] + 1))
    ui.cfg["fetch_on_open"] = False
    ui.rel.pop(k, None)
    monkeypatch.setattr(github, "from_cache", lambda *a, **kw: ({"tag": "v9", "published": "2026-01-01", "assets": []}, [], 1234.0))
    ui.open_detail(e)
    assert ui.rel[k]["tag"] == "v9" and ui.rel_t[k] == 1234.0 and calls["f"] == 0          # con datos guardados y el interruptor en NO: 0 llamadas
    ui.rel.pop(k)
    monkeypatch.setattr(github, "from_cache", lambda *a, **kw: None)
    ui.open_detail(e)
    assert calls["f"] == 1                                                                  # sin nada guardado: 1 llamada a ESTE juego


def test_github_from_cache_sin_archivo_es_none():
    from hub import github
    assert github.from_cache("no/existe-" + "x" * 8) is None


def test_ajustes_agrupados(H, ui):
    from test_temas_y_fuzz import run
    ui.tab, ui.adv_open = "settings", False
    ui.set_page = "github"; run(ui, 3)
    ks = {w.key for w in ui.widgets}
    assert {"gh_use", "chk", "chk_start", "fetch_open", "lchk", "gh_login"} <= ks
    ui.set_page = "files"; run(ui, 3)
    ks = {w.key for w in ui.widgets}
    assert "chk_start" not in ks and "fetch_open" not in ks and "lchk" not in ks and "romdir" in ks
    ui.set_page = "play"; run(ui, 3)
    assert "proton_def" in {w.key for w in ui.widgets}
    ui.set_page = None


def test_paso1_de_la_ficha_muestra_los_dos_discos_con_check(H, ui, tmp_path, monkeypatch):
    from hub import library
    from test_temas_y_fuzz import run
    monkeypatch.setattr(library, "LINKS", tmp_path / "links.json")
    e = dict(ui.entries[0], id="gow-test", name="GoW test", requires={"serials": ["UCUS98653", "UCUS98737"]})
    ui.entries.append(e)
    iso = tmp_path / "coo.iso"
    iso.write_text("x")
    library.disc_link_set("gow-test", "UCUS98653", str(iso))
    vistos = []
    orig = ui.text
    monkeypatch.setattr(ui, "text", lambda t, *a, **k: (vistos.append(str(t)), orig(t, *a, **k))[1])
    ui.detail = "gow-test"
    run(ui, 3)
    assert any("1 de 2 discos" in t and "✓" in t and "✗" in t for t in vistos), [t for t in vistos if "disco" in t]
    iso2 = tmp_path / "gos.iso"
    iso2.write_text("x")
    library.disc_link_set("gow-test", "UCUS98737", str(iso2))
    vistos.clear()
    run(ui, 3)
    assert any("2 de 2 discos" in t for t in vistos)
    ui.entries.remove(e)
    ui.detail = None


def test_script_own_tiene_registro_de_mandos(tmp_path):
    from hub import ownwine
    import subprocess
    for w in ({"game_exe": "g.exe", "own": {"profile": "generic"}}, {"own": {"profile": "gow"}}):
        t = ownwine.script_text(tmp_path, w)
        assert ".proton-log" in t and "hub-own.log" in t and "+winebus" in t
        f = tmp_path / "x.sh"; f.write_text(t)
        assert subprocess.run(["sh", "-n", str(f)]).returncode == 0


def test_actualizar_conserva_ajustes_del_launcher_gow(tmp_path, monkeypatch):
    import zipfile
    from hub import osver, config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    root = tmp_path / "gow"
    b = root / "windows" / "GoW_PSP_data" / "build"
    b.mkdir(parents=True)
    (b / "launcher.json").write_text('{"fps": 60}')
    z = tmp_path / "n.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("GoWLauncher.exe", "x")
        zf.writestr("GoW_PSP_data/build/launcher.json", '{"fps": 30}')
    monkeypatch.setattr(osver, "split", lambda lid: root)
    try:
        osver.install_windows("gow", z, version="v9")
    except OSError:
        pass                                           # set_active necesita un juego real; el respaldo ya corrió
    assert (b / "launcher.json").read_text() == '{"fps": 60}'


def test_descarga_reintentar_con_hilo_vivo_no_arranca_segundo_hilo(tmp_path):
    from hub import downloads
    m = downloads.Manager.__new__(downloads.Manager)
    d = downloads.Download("d1", "http://x/a", tmp_path)
    d.size, d.done = 100, 250
    assert d.progress == 1.0                           # nunca más de 100 %
    d._busy, d.state = True, "cancelled"
    m.items = {"d1": d}
    m.save = lambda: None
    m._wake = __import__("threading").Event()
    m.resume("d1")
    assert d.state == "cancelled" and d.meta.get("_resume")   # espera a que termine el hilo anterior


def test_note_disc_encuentra_el_segundo_disco_por_launcher_json(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from hub import ownwine, discid
    win = tmp_path / "windows"
    b = win / ownwine.DATA / "build"
    b.mkdir(parents=True)
    (win / ownwine.LAUNCHER).write_text("x")
    roms = tmp_path / "roms"
    roms.mkdir()
    a, c = roms / "God of War - A.iso", roms / "God of War - B.iso"
    a.write_text("a"); c.write_text("b")
    (b / "launcher.json").write_text(json.dumps({"disc": {"gos": "Z:" + str(c).replace("/", "\\")}}))
    ids = {str(a): {"id": ownwine.GAMES["coo"][0]}, str(c): {"id": ownwine.GAMES["gos"][0]}}
    monkeypatch.setattr(discid, "read_id", lambda p: ids.get(str(Path(p).resolve())) if True else None)
    found = ownwine.note_disc(win, a)
    assert set(found) == {"coo", "gos"} and (win / "own-disc-gos").exists()


def test_progreso_real_de_compilacion_con_ninja(tmp_path):
    from hub import ownwine
    win = tmp_path / "windows"
    d = win / ownwine.DATA / "build" / "mingw_full"
    d.mkdir(parents=True)
    (win / ownwine.LAUNCHER).write_text("x")
    assert ownwine.build_progress(win) is None
    (d / "build.ninja").write_text("".join(f"build o{i}.o: C_COMPILER x\n" for i in range(10)) + "build all: phony o0.o\n")
    (d / ".ninja_log").write_text("# ninja log v7\n" + "".join(f"0\t1\t0\to{i}.o\th\n" for i in range(4)))
    assert ownwine.build_progress(win) == 0.4


def test_cmdjob_no_apunta_el_ruido_de_steam():
    from hub import cmdjob
    j = cmdjob.CmdJob("X", "t", [])
    j._say("ERROR: ld.so: object 'x/gameoverlayrenderer.so' from LD_PRELOAD cannot be preloaded (wrong ELF class: ELFCLASS32): ignored.")
    j._say("clang: error real")
    assert list(j.log) == ["clang: error real"]


def test_juego_compilado_en_mingw_gos_full(tmp_path):
    from hub import ownwine
    b = tmp_path
    d = b / ownwine.DATA / "build" / "mingw_gos_full"
    d.mkdir(parents=True)
    assert not ownwine.built(b, "gos")
    (d / "gow_rt_UCUS98737_full.exe").write_text("x")
    assert ownwine.built(b, "gos") and not ownwine.built(b, "coo")
