"""v3.00: un .exe de Windows elegido a mano (o dejado por un instalador) no lo «actualiza» el launcher en cada arranque."""
import tomllib

from test_v195 import juego, TOML  # noqa: F401
from hub import osver


def _upd(toml):
    return tomllib.loads(toml.read_text())["update"]["type"]


def test_exe_elegido_a_mano_desactiva_y_restaura_el_update(juego, tmp_path):
    d, toml = juego
    assert _upd(toml) == "github-archive"
    inst = d / "windows" / "instalado"
    inst.mkdir(parents=True)
    (inst / "ReStreet.exe").write_bytes(b"MZ")
    osver.attach_windows("sh", inst / "ReStreet.exe")
    assert _upd(toml) == "none"                          # antes quedaba github-archive apuntando a windows/ sin .release_version → bajaba en cada arranque
    osver.set_active("sh", "linux")
    assert _upd(toml) == "github-archive"                # al volver a Linux, como estaba
    osver.set_active("sh", "windows")
    assert _upd(toml) == "none"


def test_new_exes_encuentra_la_ruta_por_defecto_del_instalador(tmp_path, monkeypatch):
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    c = tmp_path / "fifa" / "proton-prefix" / "drive_c"
    game = c / "users" / "steamuser" / "AppData" / "Local" / "ReStreet"
    game.mkdir(parents=True)
    (game / "ReStreet.exe").write_bytes(b"MZ")
    (game / "unins000.exe").write_bytes(b"MZ")
    (c / "windows" / "system32").mkdir(parents=True)
    (c / "windows" / "system32" / "notepad.exe").write_bytes(b"MZ")
    (c / "Program Files" / "Common Files").mkdir(parents=True)
    (c / "Program Files" / "Common Files" / "x.exe").write_bytes(b"MZ")
    got = [p.name for p in osver.new_exes({"id": "fifa", "folder": "fifa"})]
    assert got == ["ReStreet.exe"]
    import time
    assert osver.new_exes({"id": "fifa", "folder": "fifa"}, since=time.time() + 60) == []


from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401,E402


def test_no_se_vuelve_a_descargar_un_instalador_que_ya_esta(ui, monkeypatch, tmp_path):
    from hub import config, github
    e = ui.entries[0]
    f = tmp_path / "ReStreet-2.1.5-Setup.exe"
    f.write_bytes(b"MZ" * 10)
    monkeypatch.setattr(config, "path", lambda k: tmp_path)
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/umu-run")
    a = github.win_assets([{"name": f.name, "size": 20, "browser_download_url": "u"}])
    monkeypatch.setattr(ui, "rel_for", lambda x: {"tag": "v2.1.5", "win_assets": a})
    bajadas, menus = [], []
    monkeypatch.setattr(ui.mgr, "add", lambda *x, **k: bajadas.append(1))
    monkeypatch.setattr(ui, "setup_menu", lambda x, path, lid=None: menus.append(path))
    ui.install_windows_dl(e)
    assert menus == [str(f)] and not bajadas
    f.write_bytes(b"MZ")                                   # tamaño distinto → no se fía y vuelve a preguntar/descargar
    monkeypatch.setattr(ui, "confirm", lambda t, m, cb: cb())
    ui.install_windows_dl(e)
    assert bajadas == [1]


def test_tras_instalador_busca_en_el_prefijo(ui, monkeypatch, tmp_path):
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    e = ui.entries[0]
    g = tmp_path / e.get("folder", e["id"]) / "proton-prefix" / "drive_c" / "Games" / "ReStreet"
    g.mkdir(parents=True)
    (g / "ReStreet.exe").write_bytes(b"MZ")
    abiertos = []
    monkeypatch.setattr(ui, "pick_windows_exe", lambda x, start=None: abiertos.append(start))
    import time
    ui._after_installer(e, None, time.time())
    assert abiertos == [g]


def test_iso_para_todos_los_usuarios_del_prefijo_incluido_steamuser(tmp_path):
    """v3.02: el enlace iba a users/bazzite, pero Proton usa users/steamuser: el instalador no veía la ISO."""
    import subprocess
    from pathlib import Path
    iso = tmp_path / "FIFA Street (Europe).iso"
    iso.write_bytes(b"x")
    pre = tmp_path / "pfx"
    for u in ("bazzite", "steamuser", "Public"):
        (pre / "drive_c" / "users" / u).mkdir(parents=True)
    sh = osver._iso_links_sh(str(iso))
    subprocess.run(["sh", "-c", f'WINEPREFIX="{pre}"\n' + sh], check=True, capture_output=True)
    for u in ("bazzite", "steamuser"):
        for d in ("Desktop", "Documents"):
            ln = pre / "drive_c" / "users" / u / d / iso.name
            assert ln.exists() and not ln.is_symlink() and ln.samefile(iso), (u, d)   # v3.03: enlace duro (mismo archivo, sin copiar)
    assert not (pre / "drive_c" / "users" / "Public" / "Desktop").exists()
    t = osver.installer_runner_text(Path("/d/S.exe"), "/p", str(iso))
    assert t.index("Hub: ISO en") < t.index("exec umu-run")


def test_found_exes_ve_el_juego_en_el_c_y_no_steam(tmp_path, monkeypatch):
    from hub import config
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    c = tmp_path / "fifa" / "proton-prefix" / "drive_c"
    (c / "Program Files (x86)" / "Steam").mkdir(parents=True)
    (c / "Program Files (x86)" / "Steam" / "steam.exe").write_bytes(b"MZ")
    e = {"id": "fifa", "folder": "fifa"}
    assert osver.found_exes(e) == []
    g = c / "ReStreet"
    g.mkdir()
    (g / "ReStreet.exe").write_bytes(b"MZ")
    assert [p.name for p in osver.found_exes(e)] == ["ReStreet.exe"]



def test_enlace_duro_sustituye_el_simbolico_de_hub_y_no_pisa_archivos(tmp_path):
    iso = tmp_path / "juego.iso"
    iso.write_bytes(b"datos")
    d = tmp_path / "Desktop"
    d.mkdir()
    (d / "juego.iso").symlink_to(iso)                       # lo que dejaban las versiones anteriores
    assert osver.link_file(iso, d / "juego.iso")
    assert not (d / "juego.iso").is_symlink() and (d / "juego.iso").samefile(iso)
    assert not osver.link_file(iso, d / "juego.iso")        # ya está: no cambia nada
    otro = d / "otro.iso"
    otro.write_bytes(b"real")
    assert not osver.link_file(iso, otro) and otro.read_bytes() == b"real"
    assert iso.read_bytes() == b"datos"                     # el original sigue intacto


def test_el_script_cambia_el_simbolico_por_duro(tmp_path):
    import subprocess
    iso = tmp_path / "j.iso"
    iso.write_bytes(b"x")
    u = tmp_path / "pfx" / "drive_c" / "users" / "steamuser" / "Desktop"
    u.mkdir(parents=True)
    (u / "j.iso").symlink_to(iso)
    subprocess.run(["sh", "-c", f'WINEPREFIX="{tmp_path / "pfx"}"\n' + osver._iso_links_sh(str(iso))], check=True, capture_output=True)
    assert not (u / "j.iso").is_symlink() and (u / "j.iso").samefile(iso)
