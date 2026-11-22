"""v2.46: REGISTRO de un CmdJob (sin logfile) no debe tumbar la app."""
import os, time
from test_v195 import juego  # noqa: F401
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from hub import cmdjob


def test_registro_de_cmdjob_no_cae():
    import hub.ui as H
    u = H.UI()
    j = cmdjob.CmdJob("wine", "Preparar Wine", [])
    j.log.append("línea de prueba")
    u.builds.append(j)
    u.show_log(j)
    for _ in range(4):
        u.frame()
        time.sleep(0.01)
    assert u.modal and u.modal["kind"] == "log"
    u.close_modal()


def test_gsfocus_sin_xprop_spy_no_revienta(monkeypatch):
    from hub import gsfocus
    import threading
    monkeypatch.setattr(gsfocus, "sample", lambda: {"win": 1, "app": "a", "display": None})
    monkeypatch.setattr(gsfocus, "_spy", lambda *a: False)
    n = {"c": 0}
    def alive():
        n["c"] += 1
        return n["c"] < 3
    err = []
    old = threading.excepthook
    threading.excepthook = lambda a: err.append(a.exc_value)
    try:
        gsfocus.start(lambda s: None, alive, every=0.01)
        time.sleep(0.5)
    finally:
        threading.excepthook = old
    assert not err


def test_descarga_reintenta_corte_ssl():
    import ssl, urllib.error
    from hub.downloads import Manager as Downloads
    assert Downloads._transient(urllib.error.URLError(ssl.SSLEOFError("eof")))
    assert not Downloads._transient(ValueError("x"))


def test_interruptor_global_del_launcher(tmp_path, monkeypatch):
    from hub import config, lcheck
    d = tmp_path / "games"
    d.mkdir()
    (d / "a.toml").write_text('id="a"\n[update]\ntype = "github-archive"\nrepo="x/y"\n[run]\nexe="a"\n')
    (d / "b.toml").write_text('id="b"\n[update]\ntype = "none"\n')
    monkeypatch.setattr(config, "LAUNCHER", tmp_path)
    cfg = {"launcher_checks": False}
    assert lcheck.apply(cfg) == 1
    assert 'type = "none"' in (d / "a.toml").read_text() and cfg["lc_saved"] == {"a": "github-archive"}
    cfg["launcher_checks"] = True
    assert lcheck.apply(cfg) == 1
    assert 'type = "github-archive"' in (d / "a.toml").read_text()
    assert 'type = "none"' in (d / "b.toml").read_text()


def test_ghstats_cuenta_por_tipo():
    from hub import ghstats
    ghstats.reset_all()
    ghstats.note("/repos/u/r/releases?per_page=40", 200, {}, True)
    ghstats.note("/repos/v/s/releases?per_page=40", 304, {}, True)
    assert ghstats.S["by"] == {"/repos/*/releases": 2}
    assert "por tipo" in ghstats.summary()


def test_la_cobertura_espera_a_la_ventana_del_launcher(monkeypatch):
    import hub.ui as H
    from hub import launchwatch
    monkeypatch.setattr(launchwatch, "alive", lambda *a, **k: True)
    u = H.UI()
    now = time.time()
    u.gs_base = (10, 100)
    u.gs_now = (10, 100)                      # aún solo Hub (o nada) con el foco
    u.exit_at = now + 0.1
    u.steam_cover = {"lid": "x", "nd": ["x"], "chk": now, "bad": 0, "t0": now}
    u.pump()
    assert u.exit_at > now + 0.4              # no se cierra: sigue esperando
    u.gs_now = (20, u.STEAM_UI_APP)           # el fragmento de Steam NO cuenta
    u.pump()
    assert not u.steam_cover.get("seen")
    u.gs_now = (30, 555)                      # ventana del launcher con foco
    u.pump()
    assert u.steam_cover.get("seen")
    assert u.exit_at >= now + u.STEAM_COVER_GRACE - 0.1
    u.exit_at, u.steam_cover = None, None



def test_la_pantalla_de_carga_tapa_tambien_mientras_hub_espera_al_launcher(monkeypatch):
    import hub.ui as H
    u = H.UI()
    now = time.time()
    u.play_eid, u.play_id, u.play_name = "", "x", "Juego X"
    u.exit_at = now + 5
    u.steam_cover = {"lid": "x", "nd": ["x"], "chk": now, "bad": 0, "t0": now, "w0": now - 3}
    u.frame()
    px = u.screen.get_at((5, 5))[:3]
    assert px == tuple(H.BG)[:3] or sum(abs(a - b) < 8 for a, b in zip(px, tuple(H.BG)[:3])) == 3   # esquina: color de fondo plano, sin la UI
    u.exit_at, u.steam_cover = None, None


def test_asset_pc_a_secas_es_windows():
    from hub import github
    assert github.classify("SilentHillPC-beta.zip")["os"] == "windows"
    assert github.classify("silent-hill-pc.zip")["os"] == "windows"
    assert github.classify("Game-PC-linux.zip")["os"] == "linux"       # linux manda
    assert github.classify("rpcs3-build.zip")["os"] == "?"


def test_attach_windows_con_exe_dentro_de_la_carpeta_del_juego(juego):
    """v2.52: el .exe está en la raíz del juego; split() lo mueve a linux/ y el enlace game debe seguirlo."""
    from hub import osver
    d, toml = juego
    for n in list(d.iterdir()):
        pass
    exe = d / "Juego.exe"
    exe.write_bytes(b"MZ" + b"x" * 50)
    (d / "SilentHillPC").write_bytes(b"elf")
    osver.attach_windows("sh", exe, "wine")
    link = d / "windows" / "game"
    assert link.is_symlink()
    assert (link / "Juego.exe").is_file(), (link.resolve(), list(d.iterdir()))


def test_hub_run_wine_deja_registro_y_es_shell_valido(tmp_path):
    import subprocess
    from hub import osver
    for t in (osver.local_runner_text("game/a.exe", "game", "/p", "wine"), osver.runner_text("a.exe", "/p", "wine")):
        assert "hub-wine.log" in t
        f = tmp_path / "r.sh"
        f.write_text(t)
        assert subprocess.run(["sh", "-n", str(f)]).returncode == 0


def test_hub_run_wine_sin_display_usa_la_pantalla_del_escritorio(tmp_path):
    import subprocess
    from hub import osver
    t = osver.local_runner_text("game/a.exe", "game", "/p", "wine")
    f = tmp_path / "windows" / "hub-run.sh"
    (f.parent / "game").mkdir(parents=True)
    f.write_text(t)
    home = tmp_path / "h"
    home.mkdir()
    w = home / ".local/share/lutris/runners/wine/x/bin/wine"
    w.parent.mkdir(parents=True)
    w.write_text('#!/bin/sh\necho "D=$DISPLAY"\n')
    w.chmod(0o755)
    subprocess.run(["/bin/sh", str(f)], env={"HOME": str(home), "PATH": "/usr/bin:/bin"})
    assert "D=:0" in (tmp_path / "hub-wine.log").read_text()


def test_hub_run_wine_con_display_pero_sin_xauthority(tmp_path):
    import subprocess
    from hub import osver
    t = osver.local_runner_text("game/a.exe", "game", "/p", "wine")
    f = tmp_path / "windows" / "hub-run.sh"
    (f.parent / "game").mkdir(parents=True)
    f.write_text(t)
    home = tmp_path / "h"
    home.mkdir()
    (home / ".Xauthority").write_text("x")
    w = home / ".local/share/lutris/runners/wine/x/bin/wine"
    w.parent.mkdir(parents=True)
    w.write_text('#!/bin/sh\necho "A=$XAUTHORITY"\n')
    w.chmod(0o755)
    subprocess.run(["/bin/sh", str(f)], env={"HOME": str(home), "PATH": "/usr/bin:/bin", "DISPLAY": ":0"})
    assert f"A={home}/.Xauthority" in (tmp_path / "hub-wine.log").read_text()


def test_hub_run_wine_limpia_el_entorno_de_steam(tmp_path):
    import subprocess
    from hub import osver
    t = osver.local_runner_text("game/a.exe", "game", "/p", "wine")
    f = tmp_path / "windows" / "hub-run.sh"
    (f.parent / "game").mkdir(parents=True)
    f.write_text(t)
    home = tmp_path / "h"
    home.mkdir()
    w = home / ".local/share/lutris/runners/wine/x/bin/wine"
    w.parent.mkdir(parents=True)
    w.write_text('#!/bin/sh\necho "P=$LD_PRELOAD L=$LD_LIBRARY_PATH O=$WINEDLLOVERRIDES G=$mesa_glthread"\n')
    w.chmod(0o755)
    subprocess.run(["/bin/sh", str(f)], env={"HOME": str(home), "PATH": "/usr/bin:/bin", "LD_PRELOAD": "/x/gameoverlayrenderer.so", "LD_LIBRARY_PATH": "/home/u/.steam/ubuntu12_32", "WINEDLLOVERRIDES": "dxgi=n", "mesa_glthread": "true"})
    assert "P= L= O= G=" in (tmp_path / "hub-wine.log").read_text()


def test_find_exe_prefiere_el_launcher_hermano(tmp_path):
    from hub import osver
    (tmp_path / "SilentHillPC.exe").write_bytes(b"MZ" + b"x" * 9_000_000)
    (tmp_path / "SilentHillPC_Launcher.exe").write_bytes(b"MZ" + b"x" * 1000)
    assert osver.find_exe(tmp_path, "Silent Hill") == "SilentHillPC_Launcher.exe"
    (tmp_path / "SilentHillPC_Launcher.exe").unlink()
    assert osver.find_exe(tmp_path, "Silent Hill") == "SilentHillPC.exe"



def test_proton_prefiere_umu_y_runner_proton_arregla_display(tmp_path, monkeypatch):
    from hub import osver
    base = tmp_path / ".local/share/Steam/compatibilitytools.d"
    for n in ("GE-Proton11-11", "UMU-Proton-10.0-4", "GE-Proton9-2"):
        (base / n).mkdir(parents=True)
        (base / n / "proton").write_text("x")
    monkeypatch.setattr(osver.Path, "home", classmethod(lambda c: tmp_path))
    monkeypatch.delenv("HUB_PROTON", raising=False)
    assert osver.proton_path().endswith("UMU-Proton-10.0-4")
    monkeypatch.setenv("HUB_PROTON", "/x/GE")
    assert osver.proton_path() == "/x/GE"
    for t in (osver.runner_text("a.exe", "/p"), osver.local_runner_text("a.exe", "game", "/p")):
        assert "XAUTHORITY" in t and "unset WINEDLLOVERRIDES" in t and "umu-run" in t
        import subprocess
        f = tmp_path / "r.sh"; f.write_text(t)
        assert subprocess.run(["sh", "-n", str(f)]).returncode == 0


def test_proton_por_juego_se_fija_y_reescribe_el_script(tmp_path, monkeypatch):
    import json
    from hub import osver
    base = tmp_path / ".local/share/Steam/compatibilitytools.d"
    for n in ("GE-Proton11-11", "UMU-Proton-10.0-4"):
        (base / n).mkdir(parents=True)
        (base / n / "proton").write_text("x")
    monkeypatch.setattr(osver.Path, "home", classmethod(lambda c: tmp_path))
    monkeypatch.delenv("HUB_PROTON", raising=False)
    names = [n for n, _ in osver.list_protons()]
    assert set(names) == {"GE-Proton11-11", "UMU-Proton-10.0-4"}
    root = tmp_path / "G"
    (root / "windows").mkdir(parents=True)
    (root / osver.META).write_text(json.dumps({"windows": {"game_exe": "a.exe", "runner": "proton"}}))
    (root / "windows" / osver.RUNNER).write_text("#!/bin/sh\n")
    monkeypatch.setattr(osver, "root_of", lambda lid: root)
    assert osver.windows_proton("x") == ""
    ge = str(base / "GE-Proton11-11")
    osver.set_windows_proton("x", ge)
    assert osver.windows_proton("x") == ge
    assert ge in (root / "windows" / osver.RUNNER).read_text()
    osver.set_windows_proton("x", "")
    assert osver.windows_proton("x") == ""
    assert "UMU-Proton-10.0-4" in (root / "windows" / osver.RUNNER).read_text()


def test_saltar_launcher_abre_el_exe_del_juego(tmp_path, monkeypatch):
    import json
    from hub import osver
    root = tmp_path / "G"
    (root / "windows").mkdir(parents=True)
    for n in ("SilentHillPC.exe", "SilentHillPC_Launcher.exe"):
        (root / "windows" / n).write_text("x")
    (root / osver.META).write_text(json.dumps({"windows": {"game_exe": "SilentHillPC_Launcher.exe", "runner": "wine"}}))
    (root / "windows" / osver.RUNNER).write_text("#!/bin/sh\n")
    monkeypatch.setattr(osver, "root_of", lambda lid: root)
    assert osver.launcher_pair("x") == ("SilentHillPC_Launcher.exe", "SilentHillPC.exe")
    assert not osver.windows_skip_launcher("x")
    osver.set_windows_skip_launcher("x", True)
    t = (root / "windows" / osver.RUNNER).read_text()
    assert "SilentHillPC.exe" in t and "_Launcher" not in t and osver.windows_skip_launcher("x")
    osver.set_windows_skip_launcher("x", False)
    assert "SilentHillPC_Launcher.exe" in (root / "windows" / osver.RUNNER).read_text()


def test_runner_proton_hace_cd_a_la_carpeta_del_exe():
    from hub import osver
    t = osver.runner_text("SilentHillPC.exe", "/p")
    assert t.index('cd -P') < t.index("exec umu-run")
    t2 = osver.runner_text("sub/a.exe", "/p")
    assert 'dirname "$HERE/sub/a.exe"' in t2


def test_runners_windows_limpian_sdl_videodriver():
    from hub import osver
    for t in (osver.runner_text("a.exe", "/p"), osver.runner_text("a.exe", "/p", "wine"), osver.local_runner_text("a.exe", "game", "/p")):
        assert "unset SDL_VIDEODRIVER" in t


def test_proton_por_defecto_global(tmp_path, monkeypatch):
    from hub import osver
    base = tmp_path / ".local/share/Steam/compatibilitytools.d"
    for n in ("GE-Proton9-2", "UMU-Proton-10.0-4"):
        (base / n).mkdir(parents=True)
        (base / n / "proton").write_text("x")
    monkeypatch.setattr(osver.Path, "home", classmethod(lambda c: tmp_path))
    monkeypatch.delenv("HUB_PROTON", raising=False)
    monkeypatch.setattr(osver, "DEFAULT_PROTON", str(base / "GE-Proton9-2"))
    assert osver.proton_path().endswith("GE-Proton9-2")
    monkeypatch.setattr(osver, "DEFAULT_PROTON", str(tmp_path / "no-existe"))
    assert osver.proton_path().endswith("UMU-Proton-10.0-4")          # un valor roto cae al automático
