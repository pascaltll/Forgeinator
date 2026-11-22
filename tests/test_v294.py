"""v2.94: releases que solo publican un instalador de Windows (ReStreet: FifaStreetSetup.exe): se ofrece, se descarga, se abre con Proton."""
import stat
from pathlib import Path

import pytest

from hub import github, osver

ASSETS = [{"name": "FifaStreetSetup.exe", "size": 25_000_000, "browser_download_url": "https://x/FifaStreetSetup.exe"},
          {"name": "FifaStreetSetup.exe.sha256", "size": 90, "browser_download_url": "https://x/s"}]


def test_el_instalador_ya_no_se_descarta():
    wa = github.win_assets(ASSETS)
    assert [a["name"] for a in wa] == ["FifaStreetSetup.exe"] and wa[0]["class"]["kind"] == "instalador" and wa[0]["class"]["os"] == "windows"


@pytest.mark.parametrize("n", ["Uninstall.exe", "game-debug-setup.exe", "setup-arm64.exe", "server-setup.exe", "game.msi", "tool.exe", "Setup.zip"])
def test_lo_que_no_es_instalador_sigue_fuera(n):
    assert not [a for a in github.win_assets([{"name": n, "size": 1, "browser_download_url": "u"}]) if a["class"].get("kind") == "instalador"]


def test_el_zip_empaquetado_va_antes_que_el_instalador():
    wa = github.win_assets(ASSETS + [{"name": "Game-win64.zip", "size": 9, "browser_download_url": "u"}])
    assert wa[0]["name"] == "Game-win64.zip" and wa[-1]["class"]["kind"] == "instalador"


def test_release_con_solo_instalador_marca_has_windows():
    v = github._view({"tag_name": "v1.3", "assets": ASSETS}, {"error": "", "stale": False}, "x86_64", "")
    assert v["has_windows"] and len(v["win_assets"]) == 1 and v["assets"] == []


def test_script_del_instalador_usa_el_prefijo_del_juego_y_umu(tmp_path):
    t = osver.installer_runner_text(Path("/d/Fifa Setup's.exe"), "/p/GE-Proton")
    assert "proton-prefix" in t and "umu-run" in t and "PROTONPATH" in t and "'/d/Fifa Setup'\\''s.exe'" in t and "unset LD_PRELOAD" in t


def test_run_installer_respeta_la_estructura_del_juego(tmp_path, monkeypatch):
    """v2.94 (corregida): todo dentro de <juego>/windows/; nada de carpetas hermanas."""
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    lanzado = []
    monkeypatch.setattr(osver.subprocess, "Popen", lambda cmd, **kw: lanzado.append((cmd, kw)))
    setup = tmp_path / "dl" / "FifaStreetSetup.exe"
    setup.parent.mkdir()
    setup.write_bytes(b"MZ")
    e = {"id": "fifa-street", "folder": "fifa-street-pc-port", "name": "FIFA Street"}
    res = osver.run_installer(e, setup)
    root = tmp_path / "fifa-street-pc-port"
    sc = Path(res["script"])
    assert sc == root / "windows" / "hub-installer.sh" and sc.stat().st_mode & stat.S_IXUSR
    assert Path(res["target"]) == root / "windows" / "instalado" and Path(res["target"]).is_dir()
    assert Path(res["log"]).parent == root / "windows"
    assert "../proton-prefix" in sc.read_text()                       # el «C:» es el mismo que usará JUGAR
    assert not (tmp_path / "fifa-street-pc-port-windows").exists()    # ya no se crea ninguna carpeta hermana
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dl", "fifa-street-pc-port"]
    assert lanzado and lanzado[0][0][0] == "sh" and "LD_PRELOAD" not in lanzado[0][1]["env"]
    with pytest.raises(OSError):
        osver.run_installer(e, tmp_path / "no-existe.exe")


def test_reorganizar_el_juego_no_toca_windows_instalado(tmp_path, monkeypatch):
    """El instalador deja windows/instalado/ y, al reorganizar (split), lo de Linux va a linux/ y windows/ se queda donde está."""
    from hub import config
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path / "g")
    (config.LAUNCHER / "games").mkdir(parents=True)
    d = tmp_path / "g" / "fifa"
    d.mkdir(parents=True)
    (d / "restreet-launcher").write_bytes(b"\x7fELF")
    (config.LAUNCHER / "games" / "fifa.toml").write_text(
        f'id = "fifa"\nname = "FIFA"\ninstall_dir = "{d}"\n[update]\ntype = "none"\n[run]\ntype = "binary"\nexe = "restreet-launcher"\n')
    tg = osver.setup_target({"id": "fifa", "folder": "fifa"}, "fifa")
    assert tg == d / "windows" / "instalado"
    tg.mkdir(parents=True)
    (tg / "juego.exe").write_bytes(b"MZ")
    osver.split("fifa")
    assert (d / "linux" / "restreet-launcher").is_file() and (tg / "juego.exe").is_file() and not (d / "linux" / "windows").exists()


from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401,E402


def _entry(ui):
    return ui.entries[0]


def test_ui_confirma_y_descarga_el_instalador(ui, monkeypatch):
    e = _entry(ui)
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/umu-run")
    añadidos, confirmaciones = [], []
    monkeypatch.setattr(ui.mgr, "add", lambda url, d, **kw: añadidos.append((url, kw)))
    monkeypatch.setattr(ui, "confirm", lambda t, m, cb: confirmaciones.append((t, m, cb)))
    monkeypatch.setattr(ui, "rel_for", lambda x: {"tag": "v1.3", "win_assets": github.win_assets(ASSETS)})
    ui.install_windows_dl(e)
    assert confirmaciones and "INSTALADOR" in confirmaciones[0][1] and "G:" in confirmaciones[0][1] and "windows/instalado" in confirmaciones[0][1] and "Z:" in confirmaciones[0][1]
    confirmaciones[0][2]()
    assert añadidos and añadidos[0][1]["meta"]["install_setup"] == e["id"] and añadidos[0][0].endswith("FifaStreetSetup.exe")


def test_ui_al_terminar_abre_el_instalador_sin_menu(ui, monkeypatch):
    """v3.02: descargado el instalador, se abre directamente (antes: menú «abrir / elegir .exe»)."""
    e = _entry(ui)
    abiertos = []
    monkeypatch.setattr(osver, "run_installer", lambda ent, setup, lid=None, iso=None: abiertos.append(str(setup)) or {"target": "/t", "log": "/l"})

    class D:
        meta = {"install_setup": e["id"], "lid": None}
        path = Path("/tmp/FifaStreetSetup.exe")
    ui.modal = None
    ui._on_done(D())
    run(ui, 1)
    assert abiertos == ["/tmp/FifaStreetSetup.exe"] and ui.modal is None
    assert D.meta["phase"] == "Instalador descargado"


def test_ui_sin_umu_run_avisa_y_no_descarga(ui, monkeypatch):
    e = _entry(ui)
    monkeypatch.setattr("shutil.which", lambda n: None)
    monkeypatch.setattr(ui, "rel_for", lambda x: {"tag": "v1.3", "win_assets": github.win_assets(ASSETS)})
    avisos = []
    monkeypatch.setattr(ui, "toast", lambda m, *a, **k: avisos.append(m))
    ui.install_windows_dl(e)
    assert avisos and "umu-run" in avisos[0]


def test_ver_en_descargas_vuelve_a_abrir_el_instalador(ui, tmp_path, monkeypatch):
    e = _entry(ui)
    f = tmp_path / "FifaStreetSetup.exe"
    f.write_bytes(b"MZ")
    abiertos = []
    monkeypatch.setattr(osver, "run_installer", lambda ent, setup, lid=None, iso=None: abiertos.append(str(setup)) or {})

    class D:
        catalog = False
        state = "done"
        meta = {"install_setup": e["id"], "lid": None}
        path = str(f)
    ui.dl_main(D())
    assert abiertos == [str(f)]


# ── v2.98 ──
def test_script_crea_unidad_propia_para_iso_y_espacio():
    t = osver.installer_runner_text(Path("/d/Setup.exe"), "/p")
    assert "dosdevices" in t and "wineboot" in t and 'ln -s "$HERE"' in t and ".hub-drive" in t
    assert t.index("dosdevices") < t.index("exec umu-run '/d/Setup.exe'")
    assert "rm " not in t and "ln -sf" not in t            # nunca pisa una unidad que ya existía


def test_run_installer_enlaza_la_iso_en_windows(tmp_path, monkeypatch):
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    monkeypatch.setattr(osver.subprocess, "Popen", lambda cmd, **kw: "PROC")
    setup = tmp_path / "Setup.exe"; setup.write_bytes(b"MZ")
    iso = tmp_path / "FIFA Street.iso"; iso.write_bytes(b"x")
    e = {"id": "fifa", "folder": "fifa"}
    res = osver.run_installer(e, setup, None, iso)
    ln = tmp_path / "fifa" / "windows" / "FIFA Street.iso"
    assert ln.samefile(iso) and res["proc"] == "PROC"
    real = tmp_path / "fifa" / "windows" / "otra.iso"; real.write_bytes(b"real")
    assert osver.link_iso(real.parent, tmp_path / "x" / "otra.iso") == ""             # ISO inexistente: no hace nada
    (tmp_path / "x").mkdir(); (tmp_path / "x" / "otra.iso").write_bytes(b"y")
    assert osver.link_iso(real.parent, tmp_path / "x" / "otra.iso") == str(real) and real.read_bytes() == b"real"   # no pisa un archivo real


def test_installed_exes_ignora_desinstaladores(tmp_path, monkeypatch):
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    d = tmp_path / "fifa" / "windows" / "instalado" / "ReStreet"
    d.mkdir(parents=True)
    for n in ("ReStreet.exe", "unins000.exe", "vc_redist.x64.exe", "FifaStreetSetup.exe"):
        (d / n).write_bytes(b"MZ")
    assert [p.name for p in osver.installed_exes({"id": "fifa", "folder": "fifa"})] == ["ReStreet.exe"]


def test_tras_el_instalador_se_pide_el_exe_y_la_ficha_no_ofrece_descargar(ui, tmp_path, monkeypatch):
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    e = _entry(ui)
    d = tmp_path / e.get("folder", e["id"]) / "windows" / "instalado"
    d.mkdir(parents=True)
    (d / "Juego.exe").write_bytes(b"MZ")
    abiertos, descargas = [], []
    monkeypatch.setattr(ui, "pick_windows_exe", lambda x, start=None: abiertos.append(start))
    monkeypatch.setattr(ui, "install_windows_dl", lambda x, fresh=False: descargas.append(1))
    ui._after_installer(e, None)
    assert abiertos == [d]
    monkeypatch.setattr(ui, "inst", lambda x: {"launcher_id": None, "installed": True})
    monkeypatch.setattr(ui, "os_state", lambda lid: {"split": False, "active": "linux", "windows": False, "linux": True})
    ui.choose_os(e, "windows")
    assert abiertos == [d, d] and not descargas
    assert ui.win_installed(e, None)
