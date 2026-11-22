"""v1.96: JUGAR abre el juego con su propio acceso de Steam (Big Picture lo muestra con su nombre, no como Recomp Hub),
la carpeta de trabajo vuelve a ser la del juego (Silent Hill guardaba su config en la carpeta de ROMs) y la ficha dice dónde está cada cosa."""
import struct
import types

import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")


def _vdf(entries):
    def s(k, v):
        return b"\x01" + k.encode() + b"\x00" + v.encode() + b"\x00"

    def i(k, v):
        return b"\x02" + k.encode() + b"\x00" + struct.pack("<i", v)
    body = b""
    for n, e in enumerate(entries):
        body += b"\x00" + str(n).encode() + b"\x00" + i("appid", e["appid"]) + s("AppName", e["name"]) + s("Exe", e["exe"]) + \
            s("StartDir", '"/x"') + s("LaunchOptions", e.get("opts", "")) + b"\x00tags\x00\x08" + b"\x08"
    return b"\x00shortcuts\x00" + body + b"\x08\x08"


@pytest.fixture
def steam(tmp_path, monkeypatch):
    from hub import steamlib
    f = tmp_path / ".local/share/Steam/userdata/123/config/shortcuts.vdf"
    f.parent.mkdir(parents=True)
    f.write_bytes(_vdf([{"appid": -1234567890, "name": "Silent Hill", "exe": '"/home/b/Games/launcher/shortcuts/sh.sh"'},
                        {"appid": 77, "name": "BT3", "exe": '"/home/b/Games/launcher/bin/play"', "opts": "bt3-latino --launcher"},
                        {"appid": 88, "name": "Crash Team Racing", "exe": "/usr/bin/otro"}]))
    monkeypatch.setattr(steamlib, "ROOTS", (str(tmp_path / ".local/share/Steam"),))
    return steamlib


def test_lee_los_accesos_de_steam(steam):
    items = steam.shortcuts()
    assert [x["name"] for x in items] == ["Silent Hill", "BT3", "Crash Team Racing"]
    assert steam.find("sh", "", items)["appid"] == -1234567890
    assert steam.find("bt3-latino", "", items)["name"] == "BT3", "bin/play <id> en las opciones"
    assert steam.find("ctr", "Crash Team Racing", items)["appid"] == 88, "si no, por nombre"
    assert steam.find("nada", "Otro", items) is None
    assert steam.game_id(-1234567890) == ((-1234567890 & 0xFFFFFFFF) << 32) | 0x02000000


def test_pide_el_juego_a_steam_fuera_del_arbol_de_hub(steam, monkeypatch):
    llam = []
    monkeypatch.setattr(steam.shutil, "which", lambda n: f"/usr/bin/{n}")
    monkeypatch.setattr(steam.subprocess, "run", lambda cmd, **k: llam.append(cmd) or types.SimpleNamespace(returncode=0, stdout="", stderr=""))
    ok, how = steam.launch_later(77)
    assert ok and llam[0][:3] == ["/usr/bin/systemd-run", "--user", "--collect"] and llam[0][-1] == f"steam://rungameid/{steam.game_id(77)}"


def test_jugar_usa_el_acceso_de_steam_y_se_cierra(H, ui, steam, monkeypatch, tmp_path):
    from hub import config
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "bin").mkdir(parents=True)
    (config.LAUNCHER / "bin" / "play").write_text("#!/bin/sh\n")
    monkeypatch.setattr(H.config, "save_settings", lambda s: None)
    lanz, pop = [], []
    monkeypatch.setattr(H.steamlib, "launch_later", lambda appid, delay=2: lanz.append(appid) or (True, "prueba"))
    monkeypatch.setattr(H.subprocess, "Popen", lambda *a, **k: pop.append(a) or types.SimpleNamespace(pid=9, poll=lambda: None), raising=False)
    monkeypatch.setattr(ui, "inst", lambda e: {"installed": True, "launcher_id": "sh", "version": "1", "dir": "x"})
    monkeypatch.setattr(H.launchlog, "libs_check", lambda lid: {"miss": [], "container": ""})
    ui._sc_t = 0
    ui.cfg["play_via_steam"] = True        # el fuzz de otras pruebas pulsa todos los botones de Ajustes, este incluido
    ui.cfg["steam_splash"] = False          # v2.39: con pantalla de carga Hub espera; este test fija el modo clásico (se cierra enseguida)
    ui.play_pr = None
    ui.exit_at = 0
    e = {"id": "sh", "name": "Silent Hill"}
    try:
        monkeypatch.setenv("SteamGameId", "999")
        ui.play(e)
        assert lanz == [-1234567890] and not pop and ui.exit_at > 0
        ui.exit_at = 0
        monkeypatch.delenv("SteamGameId")
        ui.play(e)
        assert pop, "fuera de Steam, Hub lo abre directamente como siempre"
    finally:
        ui.exit_at = 0
        ui.play_pr = None
        ui.game_pids.clear()


def test_la_carpeta_de_trabajo_vuelve_a_la_del_juego(H, ui, tmp_path, monkeypatch):
    from hub import config, gamecfg, library
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "games").mkdir(parents=True)
    d = tmp_path / "SH"
    d.mkdir()
    roms = tmp_path / "roms" / "psx"
    roms.mkdir(parents=True)
    (roms / "Silent Hill (USA).bin").write_bytes(b"x")
    (roms / "Silent Hill (USA).cue").write_text('FILE "Silent Hill (USA).bin" BINARY\n')
    (config.LAUNCHER / "games" / "sh.toml").write_text(f'id = "sh"\nname = "SH"\ninstall_dir = "{d}"\n\n[run]\ntype = "binary"\nexe = "SilentHillPC"\ncwd = "."\n')
    gamecfg.set_libcwd("sh", str(roms), True)
    assert gamecfg.state("sh")["libcwd"]
    e = {"id": "sh", "name": "SH", "launcher_id": "sh", "requires": {}}
    monkeypatch.setattr(ui, "entries", [e])
    monkeypatch.setattr(library, "link_get", lambda i: str(roms / "Silent Hill (USA).cue") if i == "sh" else None)
    monkeypatch.setattr(H.install, "installed_info", lambda *a, **k: {"installed": True, "dir": str(d), "launcher_id": "sh", "version": "1"})
    monkeypatch.setattr(H.config, "save_settings", lambda s: None)
    ui.cfg.pop("cwd_fix_v196", None)
    ui.cfg["auto_libcwd"] = True
    ui._cwd_migrate()
    import tomllib
    t = tomllib.loads((config.LAUNCHER / "games" / "sh.toml").read_text())
    assert t["run"]["cwd"] == "." and not gamecfg.state("sh")["libcwd"]
    assert (d / "Silent Hill (USA).cue").is_symlink() and (d / "Silent Hill (USA).bin").is_symlink(), "el .cue viaja con su .bin"
    assert ui.cfg["auto_libcwd"] is False and ui.cfg["cwd_fix_v196"]
    ui._cwd_migrate()          # una sola vez


def test_carpetas_de_un_juego(tmp_path, monkeypatch):
    from hub import config, osver
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "games").mkdir(parents=True)
    (config.LAUNCHER / "games" / "a.toml").write_text(f'id = "a"\ninstall_dir = "{tmp_path}/A"\n[run]\nexe = "x"\ncwd = "."\n')
    (config.LAUNCHER / "games" / "b.toml").write_text(f'id = "b"\ninstall_dir = "{tmp_path}/B"\n[run]\nexe = "x"\ncwd = "/roms/psx"\n')
    assert osver.folders("a") == {"dir": f"{tmp_path}/A", "cwd": f"{tmp_path}/A"}
    assert osver.folders("b")["cwd"] == "/roms/psx"
