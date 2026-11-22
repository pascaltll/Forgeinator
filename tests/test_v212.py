"""v2.12: usar un .exe de Windows que ya tienes (Proton / Wine) desde la ficha del juego."""
import stat
import subprocess
import tomllib

import pytest

from test_v195 import juego, _t  # noqa: F401
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio  # noqa: F401

pygame = pytest.importorskip("pygame")


def _exe(tmp_path):
    g = tmp_path / "descargas" / "GoW"
    (g / "bin").mkdir(parents=True)
    (g / "bin" / "GoW.exe").write_bytes(b"MZ" + b"x" * 100)
    (g / "data.pak").write_bytes(b"d")
    return g / "bin" / "GoW.exe"


def test_enlaza_sin_copiar_y_activa_windows(juego, tmp_path):
    from hub import osver
    d, toml = juego
    exe = _exe(tmp_path)
    res = osver.attach_windows("sh", exe, "proton")
    assert res["exe"] == "GoW.exe"
    link = d / "windows" / "game"
    assert link.is_symlink() and link.resolve() == exe.parent.resolve()
    assert not list((d / "windows").glob("*.exe")), "no se copia nada"
    r = d / "windows" / "hub-run.sh"
    txt = r.read_text()
    assert r.stat().st_mode & stat.S_IXUSR
    assert 'exec umu-run "$HERE/game/GoW.exe"' in txt and 'cd -P "$HERE/game"' in txt and "proton-prefix" in txt
    assert subprocess.run(["sh", "-n", str(r)]).returncode == 0
    t = _t(toml)
    assert t["install_dir"].endswith("SilentHill/windows") and t["run"]["exe"] == "hub-run.sh"
    st = osver.state("sh")
    assert st["active"] == "windows" and st["windows"] and st["linux"]
    assert (d / "linux" / "SilentHillPC").exists(), "lo de Linux sigue ahí"


def test_wine_usa_wine(juego, tmp_path):
    from hub import osver
    d, _ = juego
    osver.attach_windows("sh", _exe(tmp_path), "wine")
    txt = (d / "windows" / "hub-run.sh").read_text()
    assert 'exec wine "$HERE/game/GoW.exe"' in txt and "umu-run" not in txt


def test_repetir_cambia_de_exe_sin_romper(juego, tmp_path):
    from hub import osver
    d, _ = juego
    osver.attach_windows("sh", _exe(tmp_path))
    otro = tmp_path / "otro"
    otro.mkdir()
    (otro / "Otro.exe").write_bytes(b"MZ")
    osver.attach_windows("sh", otro / "Otro.exe")
    assert (d / "windows" / "game").resolve() == otro.resolve()
    assert 'game/Otro.exe' in (d / "windows" / "hub-run.sh").read_text()


def test_no_acepta_lo_que_no_es_exe(juego, tmp_path):
    from hub import osver
    f = tmp_path / "x.txt"
    f.write_text("no")
    with pytest.raises(OSError):
        osver.attach_windows("sh", f)
    with pytest.raises(OSError):
        osver.attach_windows("sh", tmp_path / "no-existe.exe")


def test_juego_sin_carpeta_se_crea(juego, tmp_path):
    from hub import osver, config
    import shutil
    d, toml = juego
    shutil.rmtree(d)
    osver.attach_windows("sh", _exe(tmp_path))
    assert (d / "windows" / "hub-run.sh").is_file() and not (d / "linux").exists()
    assert tomllib.loads(toml.read_text())["run"]["exe"] == "hub-run.sh"


def test_registro_de_proton_activa_la_variable(juego, tmp_path):
    from hub import osver
    d, _ = juego
    osver.attach_windows("sh", _exe(tmp_path))
    assert not osver.proton_log("sh")
    osver.set_proton_log("sh", True)
    assert osver.proton_log("sh") and (d / ".proton-log").exists()
    assert "PROTON_LOG=1" in (d / "windows" / "hub-run.sh").read_text()
    osver.set_proton_log("sh", False)
    assert not osver.proton_log("sh")


def test_el_script_se_ejecuta_en_la_carpeta_del_exe(juego, tmp_path):
    from hub import osver
    d, _ = juego
    exe = _exe(tmp_path)
    osver.attach_windows("sh", exe)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    out = tmp_path / "salida.txt"
    fake = bin_ / "umu-run"
    fake.write_text(f'#!/bin/sh\necho "$PWD|$1|$2|$GAMEID" > {out}\n')
    fake.chmod(0o755)
    import os
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}")
    assert subprocess.run(["sh", str(d / "windows" / "hub-run.sh"), "-windowed"], env=env).returncode == 0
    cwd, arg1, arg2, gid = out.read_text().strip().split("|")
    assert cwd == str(exe.parent.resolve()) and arg1.endswith("game/GoW.exe") and arg2 == "-windowed" and gid == "0"
    assert (d / "proton-prefix").is_dir()


def _ficha(H, ui, juego, monkeypatch, assets, wins, installed=True):
    from test_temas_y_fuzz import run
    d, _ = juego
    monkeypatch.setattr(H.shutil, "which", lambda n: "/usr/bin/umu-run" if n == "umu-run" else None)
    e = ui.entries[0]
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=installed, version="v1", launcher_id="sh", dir=str(d)) if x is e else real(x))
    ui._inst_c = None
    ui.rel[ui.rk(e)] = {"tag": "v2", "published": "2026-11-01", "assets": assets, "win_assets": wins}
    ui.set_look(theme="dark", fx="perf")
    ui.go_tab("games")
    ui.open_detail(e)
    run(ui, 3)
    return e


def _a(n):
    return {"name": n, "size": 9 << 20, "url": "u/" + n, "sha256": None, "class": {"os": "linux", "arch": "x86_64"}}


def test_ficha_muestra_y_elige_builds_de_windows(H, ui, juego, monkeypatch):
    from test_temas_y_fuzz import run
    wins = [{"name": "G-windows-x64.zip", "size": 9 << 20, "url": "u1", "sha256": None, "class": {"os": "windows", "arch": "x86_64"}},
            {"name": "G-windows-x64-lite.zip", "size": 5 << 20, "url": "u2", "sha256": None, "class": {"os": "windows", "arch": "x86_64"}}]
    e = _ficha(H, ui, juego, monkeypatch, [_a("G-linux-x64.tar.gz")], wins)
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = "versiones"
    run(ui, 3)
    ks = {w.key for w in ui.widgets}
    assert {"av_linux", "av_windows", "asset:0"} <= ks and "wasset:0" not in ks
    assert {"g_fetch", "g_lchk"} <= ks                                   # v2.64: interruptores globales dentro de la ficha
    ui.asset_os[e["id"]] = "windows"
    run(ui, 3)
    ks = {w.key for w in ui.widgets}
    assert {"wasset:0", "wasset:1"} <= ks and "asset:0" not in ks
    ui.sel_win[e["id"]] = 1
    added = []
    monkeypatch.setattr(ui.mgr, "add", lambda *a, **k: added.append((a, k)))
    ui.install_windows_dl(e)
    ui.modal["cb"]()
    assert added[0][0][0] == "u2" and added[0][1]["name"] == "G-windows-x64-lite.zip"


def test_solo_windows_se_ve_directo_y_sin_selector(H, ui, juego, monkeypatch):
    from test_temas_y_fuzz import run
    wins = [{"name": "G-windows-x64.zip", "size": 9 << 20, "url": "u1", "sha256": None, "class": {"os": "windows", "arch": "x86_64"}}]
    e = _ficha(H, ui, juego, monkeypatch, [], wins, installed=False)
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = "versiones"
    run(ui, 3)
    ks = {w.key for w in ui.widgets}
    assert "wasset:0" in ks and "av_linux" not in ks
