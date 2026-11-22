"""v1.95: versión de Linux y de Windows (Proton) del mismo juego dentro de su carpeta (linux/ y windows/),
la elegida se aplica al .toml del launcher (JUGAR y Steam abren la misma)."""
import json
import tomllib
import types
import zipfile

import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")

TOML = '''id = "sh"
name = "Silent Hill"
install_dir = "@DIR@"

preserve = []

[update]
type = "github-archive"
repo = "SlickAmogus/silent-hill-decomp"
asset = "*linux-x64*.tar.gz"
mode = "overlay"
executables = ["SilentHillPC"]
version_file = ".release_version"

[run]
type = "binary"
exe = "SilentHillPC"
cwd = "/roms/psx"
require = ["SilentHillPC", "data/rom.bin"]

[health]
grace_seconds = 10
'''


@pytest.fixture
def juego(tmp_path, monkeypatch):
    from hub import config, osver
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path / "g")
    (config.LAUNCHER / "games").mkdir(parents=True)
    d = tmp_path / "g" / "SilentHill"
    (d / "data").mkdir(parents=True)
    (d / "SilentHillPC").write_bytes(b"\x7fELF")
    (d / "data" / "rom.bin").write_bytes(b"ROM")
    (d / "saves").mkdir()
    (d / "saves" / "slot1").write_text("partida")
    (d / ".release_version").write_text("v1")
    (config.LAUNCHER / "games" / "sh.toml").write_text(TOML.replace("@DIR@", str(d)))
    monkeypatch.setattr(osver, "proton_path", lambda: "/home/x/.local/share/Steam/compatibilitytools.d/GE-Proton11-11")
    return d, config.LAUNCHER / "games" / "sh.toml"


def _zip(tmp_path):
    z = tmp_path / "SHPC-windows-x64_2026.09.27.1.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("SHPC/SilentHillPC.exe", b"MZ" + b"x" * 5000)
        f.writestr("SHPC/vc_redist.x64.exe", b"MZ" + b"x" * 90000)
        f.writestr("SHPC/setup.exe", b"MZ")
        f.writestr("SHPC/readme.txt", "hola")
    return z


def _t(p):
    return tomllib.loads(p.read_text())


def test_reorganizar_mueve_todo_a_linux_y_apunta_el_toml(juego):
    from hub import osver
    d, toml = juego
    root = osver.split("sh")
    assert root == d and (d / "linux" / "SilentHillPC").exists() and (d / "linux" / "saves" / "slot1").read_text() == "partida"
    assert not (d / "SilentHillPC").exists() and not (d / ".hub-move.json").exists()
    t = _t(toml)
    assert t["install_dir"].endswith("SilentHill/linux") and t["run"]["exe"] == "SilentHillPC" and t["run"]["cwd"] == "/roms/psx"
    assert osver.split("sh") == d, "dos veces no mueve nada más"
    st = osver.state("sh")
    assert st["split"] and st["active"] == "linux" and st["linux"] and not st["windows"]


def test_si_algo_falla_al_mover_se_deshace(juego, monkeypatch):
    from hub import osver
    import os
    d, toml = juego
    real = os.rename
    n = {"c": 0}

    def rename(a, b):
        n["c"] += 1
        if n["c"] == 3:
            raise OSError("disco")
        return real(a, b)
    monkeypatch.setattr(osver.os, "rename", rename)
    with pytest.raises(OSError):
        osver.split("sh")
    monkeypatch.setattr(osver.os, "rename", real)
    assert (d / "SilentHillPC").exists() and (d / "saves").is_dir() and not (d / "linux").exists()
    assert _t(toml)["install_dir"] == str(d)


def test_version_de_windows_con_proton_y_cambiar_entre_las_dos(juego, tmp_path):
    from hub import osver
    d, toml = juego
    res = osver.install_windows("sh", _zip(tmp_path), "v2", osver.asset_glob("SHPC-windows-x64_2026.09.27.1.zip"), "SilentHillPC")
    assert res["exe"] == "SilentHillPC.exe", "el juego, no el redistribuible grande ni el instalador"
    run_sh = (d / "windows" / "hub-run.sh").read_text()
    assert 'umu-run "$HERE/SilentHillPC.exe"' in run_sh and "GE-Proton11-11" in run_sh and "proton-prefix" in run_sh
    t = _t(toml)
    assert t["install_dir"].endswith("SilentHill/windows") and t["run"]["exe"] == "hub-run.sh"
    assert t["update"]["asset"] == "*windows-x64*.zip" and t["update"]["executables"] == ["hub-run.sh"]
    assert t["run"]["require"] == ["hub-run.sh", "data/rom.bin"] and (d / "windows" / "data" / "rom.bin").read_bytes() == b"ROM", "los datos del juego se enlazan, no se copian"
    assert (d / "windows" / ".release_version").read_text() == "v2"
    osver.set_active("sh", "linux")
    t = _t(toml)
    assert t["install_dir"].endswith("SilentHill/linux") and t["run"]["exe"] == "SilentHillPC" and t["update"]["asset"] == "*linux-x64*.tar.gz"
    assert t["run"]["require"] == ["SilentHillPC", "data/rom.bin"]
    assert osver.state("sh")["active"] == "linux"
    assert toml.with_suffix(".toml.hub-bak").exists(), "copia del .toml original"


def test_deshacer_si_solo_hay_linux(juego):
    from hub import osver
    d, toml = juego
    osver.split("sh")
    osver.unsplit("sh")
    assert (d / "SilentHillPC").exists() and not (d / "linux").exists() and not (d / ".hub-versions.json").exists()
    assert _t(toml)["install_dir"] == str(d).replace(str(__import__("pathlib").Path.home()), "~") or _t(toml)["install_dir"] == str(d)


def test_solo_windows_se_instala_directo(tmp_path, monkeypatch):
    from hub import config, osver
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path / "g")
    monkeypatch.setattr(osver, "proton_path", lambda: "GE-Proton")
    e = {"id": "dc", "name": "Dino Crisis", "folder": "DinoCrisis", "repo": "a/b"}
    res = osver.install_windows_only(e, _zip(tmp_path), "v1", "DC-win64.zip")
    t = _t(config.LAUNCHER / "games" / "dc.toml")
    assert t["run"]["exe"] == "hub-run.sh" and t["install_dir"].endswith("DinoCrisis/windows") and res["exe"] == "SilentHillPC.exe"
    st = osver.state("dc")
    assert st["split"] and st["active"] == "windows" and st["windows"] and not st["linux"]


def test_assets_de_windows_de_una_release():
    from hub import github
    a = [{"name": n, "size": 1, "browser_download_url": "u/" + n} for n in
         ("SHPC-linux-x64_1.tar.gz", "SHPC-windows-x64_1.zip", "SHPC-windows-x64_1-symbols.zip", "setup-win64.exe", "game-win-arm64.zip")]
    w = github.win_assets(a)
    assert [x["name"] for x in w] == ["SHPC-windows-x64_1.zip", "setup-win64.exe"]      # v2.94: el instalador se ofrece, pero al final y marcado
    assert w[1]["class"]["kind"] == "instalador" and w[0]["class"]["kind"] == "zip"
    assert github.rank_assets(a)[0]["name"] == "SHPC-linux-x64_1.tar.gz", "lo nativo sigue siendo lo primero"


def test_ficha_ofrece_las_dos_versiones_y_steam_sigue_al_toml(H, ui, juego, tmp_path, monkeypatch):
    from hub import osver
    d, toml = juego
    monkeypatch.setattr(H.shutil, "which", lambda n: "/usr/bin/umu-run" if n == "umu-run" else None)
    e = ui.entries[0]
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="v1", launcher_id="sh", dir=str(d)) if x is e else real(x))
    ui._inst_c = None
    ui.rel[ui.rk(e)] = {"tag": "v2", "assets": [], "win_assets": [{"name": "SHPC-windows-x64_1.zip", "size": 9 << 20, "url": "u", "sha256": None}]}
    added = []
    monkeypatch.setattr(ui.mgr, "add", lambda *a, **k: added.append(k))
    ui.set_look(theme="dark", fx="perf")
    ui.go_tab("games")
    ui.open_detail(e)
    run(ui, 3)
    ks = {w.key for w in ui.widgets}
    assert {"os_linux", "os_windows"} <= ks              # v3.02: tarjeta VERSIONES en la vista principal de la ficha
    ui.choose_os(e, "windows")
    assert ui.modal and ui.modal["title"].startswith("Versión de Windows") and "linux  ← lo que tienes ahora" in ui.modal["msg"]
    ui.modal["cb"]()
    assert added and added[0]["meta"]["install_win"] == e["id"]
    # la descarga termina → se instala y queda elegida
    dl = types.SimpleNamespace(meta=dict(added[0]["meta"]), path=_zip(tmp_path))
    ui._on_done(dl)
    assert "Instalada (Windows" in dl.meta["phase"], dl.meta["phase"]
    assert _t(toml)["run"]["exe"] == "hub-run.sh" and ui.os_state("sh")["active"] == "windows"
    ui.choose_os(e, "linux")
    assert _t(toml)["run"]["exe"] == "SilentHillPC"
    ui.modal = None
    ui.rel.pop(ui.rk(e), None)


def test_actualizar_windows_conserva_proton_elegido_y_saltar_launcher(juego, tmp_path):
    from hub import osver
    d, toml = juego
    osver.install_windows("sh", _zip(tmp_path), "v1", osver.asset_glob("SHPC-windows-x64_2026.09.27.1.zip"), "SilentHillPC")
    osver.set_windows_proton("sh", "/x/UMU-Proton-10.0-4")
    m = osver.meta(d)
    m["windows"]["skip_launcher"] = True
    osver._save_meta(d, m)
    osver.install_windows("sh", _zip(tmp_path), "v2", osver.asset_glob("SHPC-windows-x64_2026.09.27.1.zip"), "SilentHillPC")
    w = osver.meta(d)["windows"]
    assert w.get("proton") == "/x/UMU-Proton-10.0-4" and w.get("skip_launcher") is True
    assert "/x/UMU-Proton-10.0-4" in (d / "windows" / "hub-run.sh").read_text()
