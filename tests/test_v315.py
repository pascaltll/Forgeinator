"""v3.15 · Canales estable y dev conviviendo (biblioteca común, ajustes aparte), migración desde ~/Games/recomp-hub, paquetes para
el QAM y logo pixel art."""
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from conftest import HUB_SRC

sys.path.insert(0, str(HUB_SRC))
from hub import channel as ch  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Un HOME de mentira con XDG y qam-apps propios."""
    h = tmp_path / "home"
    h.mkdir()
    for k in ("HUB_DATA", "HUB_CONF", "HUB_STATE", "HUB_CONFIG", "HUB_CHANNEL", "HUB_LEGACY_DATA"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("XDG_DATA_HOME", str(h / ".local/share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(h / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(h / ".local/state"))
    monkeypatch.setenv("QAM_APPS_DIR", str(h / "homebrew/qam-apps"))
    return h


def _copy(home, c):
    d = home / "homebrew/qam-apps" / ch.FOLDER[c]
    d.mkdir(parents=True, exist_ok=True)
    (d / "CHANNEL").write_text(c + "\n")
    return d


# ---------------------------------------------------------------- rutas
def test_rutas_legado_canal_y_pruebas(home, tmp_path, monkeypatch):
    root = tmp_path / "prog"
    root.mkdir()
    assert ch.program_channel(root) is None
    lay = ch.layout(None, root)
    assert lay["data"] == lay["conf"] == lay["state"] == root / "data"
    assert lay["creds"] == home / ".config/recomp-hub"                 # como antes de v3.15
    (root / "CHANNEL").write_text("dev\n")
    assert ch.program_channel(root) == "dev"
    lay = ch.layout("dev", root)
    assert lay["data"] == home / ".local/share/forgeinator"            # biblioteca común
    assert lay["conf"] == home / ".config/forgeinator/dev"             # ajustes de dev
    assert lay["state"] == home / ".local/state/forgeinator/dev"
    assert lay["creds"] == home / ".config/forgeinator"                # claves comunes
    assert ch.layout("stable", root)["data"] == lay["data"] and ch.layout("stable", root)["conf"] != lay["conf"]
    (root / "CHANNEL").write_text("cualquiera")
    assert ch.program_channel(root) is None
    monkeypatch.setenv("HUB_DATA", str(tmp_path / "t"))
    lay = ch.layout("dev", root)
    assert lay["data"] == lay["conf"] == lay["state"] == lay["creds"] == tmp_path / "t"


@pytest.mark.parametrize("chan", [None, "stable", "dev"])
def test_bash_y_python_dan_las_mismas_carpetas(home, tmp_path, chan):
    root = tmp_path / "prog"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "_dirs.sh").write_text((HUB_SRC / "bin" / "_dirs.sh").read_text())
    if chan:
        (root / "CHANNEL").write_text(chan + "\n")
    out = subprocess.run(["bash", "-c", f'D="{root}"; . "$D/bin/_dirs.sh"; echo "$HUB_CH|$DATA_DIR|$STATE_DIR"'],
                         capture_output=True, text=True, env=os.environ.copy()).stdout.strip().split("|")
    lay = ch.layout(chan, root)
    assert out == [chan or "", str(lay["data"]), str(lay["state"])]


# ---------------------------------------------------------------- canal activo y red de seguridad
def test_canal_activo_por_defecto_y_cambio(home):
    assert ch.active() is ch.CHANNEL or ch.active() in (None, "stable", "dev")
    _copy(home, "dev")
    assert ch.active() == "dev" and ch.installed("dev") and not ch.installed("stable")
    _copy(home, "stable")
    assert ch.active() == "stable"                                       # sin elegir: manda estable si está
    ch.set_active("dev")
    assert ch.active() == "dev" and ch.is_active("dev") and not ch.is_active("stable")
    assert ch.is_active(None)                                            # la instalación antigua siempre gestiona lo suyo
    with pytest.raises(ValueError):
        ch.set_active("beta")


def test_red_de_seguridad_de_dev(home):
    _copy(home, "dev")
    _copy(home, "stable")
    ch.set_active("dev")
    assert ch.boot_begin("dev") == 1 and ch.boot_begin("stable") == 0
    assert not ch.safety_check()                                         # un fallo no basta
    ch.boot_ok()
    assert ch.boots() == 0
    ch.boot_begin("dev")
    ch.boot_begin("dev")
    assert ch.safety_check() and ch.active() == "stable" and ch.boots() == 0
    assert "Estable" in ch.take_notice() and ch.take_notice() is None    # el aviso se muestra una vez
    ch.set_active("dev")
    ch.boot_begin("dev")
    ch.boot_begin("dev")
    (home / "homebrew/qam-apps/forgeinator/CHANNEL").unlink()
    assert not ch.safety_check() and ch.active() == "dev"               # sin estable instalada no hay adónde volver


# ---------------------------------------------------------------- migración
def _legacy(home):
    L = home / "Games/recomp-hub/data"
    (L / "downloads/navegador").mkdir(parents=True)
    (L / "downloads/juego.iso").write_bytes(b"x" * 4096)
    (L / "covers").mkdir()
    (L / "covers/a.png").write_bytes(b"png")
    (L / "imports").mkdir()
    (L / "imports/lista.json").write_text("{}")
    (L / "links.json").write_text(json.dumps({"g": str(L / "downloads/juego.iso"), "otro": "/media/sd/rom.iso"}))
    (L / "settings.json").write_text(json.dumps({"theme": "aurora", "downloads_dir": str(L / "downloads"),
                                                 "watch_dirs": [str(L / "downloads/navegador"), "~/Downloads"]}))
    (L / "hub.log").write_text("viejo")
    (L / "browser-venv").mkdir()
    (L / "roto.json").write_text("{no es json")
    (home / ".config/recomp-hub").mkdir(parents=True)
    (home / ".config/recomp-hub/credentials.json").write_text('{"token": "t"}')
    return L


def test_migracion_copia_sin_tocar_el_origen(home):
    L = _legacy(home)
    before = {p: p.stat().st_mtime_ns for p in L.rglob("*")}
    lay = ch.layout("dev", home)
    rep = ch.migrate(lay)
    D = lay["data"]
    assert rep["hecho"] and rep["origen"] == str(L)
    assert json.loads((D / "links.json").read_text()) == {"g": str(D / "downloads/juego.iso"), "otro": "/media/sd/rom.iso"}
    assert (D / "downloads/juego.iso").read_bytes() == b"x" * 4096
    assert rep["pesado"]["downloads"] in ("enlazada", "copiada")
    if rep["pesado"]["downloads"] == "enlazada":
        assert (D / "downloads/juego.iso").stat().st_ino == (L / "downloads/juego.iso").stat().st_ino   # sin ocupar más disco
    assert (D / "imports/lista.json").exists() and (D / "roto.json").read_text() == "{no es json"
    for n in ("hub.log", "browser-venv", "settings.json"):
        assert not (D / n).exists(), n                                   # registros, venv (no se puede mover) y ajustes: aparte
    cr = lay["creds"] / "credentials.json"
    assert json.loads(cr.read_text()) == {"token": "t"} and (cr.stat().st_mode & 0o777) == 0o600
    assert {p: p.stat().st_mtime_ns for p in L.rglob("*")} == before   # el origen, intacto
    assert (home / ".config/recomp-hub/credentials.json").exists()
    assert ch.migrate(lay)["hecho"] is False                             # una sola vez
    info = json.loads((D / ".migrado").read_text())
    assert info["origen"] == str(L) and "_old" not in info


def test_ajustes_de_cada_canal(home):
    L = _legacy(home)
    _copy(home, "dev")
    for c in ("dev", "stable"):
        lay = ch.layout(c, home)
        ch.migrate(lay)
    lay_d = ch.layout("dev", home)
    assert ch.seed_settings(lay_d) == str(L / "settings.json")
    s = json.loads((lay_d["conf"] / "settings.json").read_text())
    D = lay_d["data"]
    assert s["theme"] == "aurora" and s["downloads_dir"] == str(D / "downloads") and s["watch_dirs"][0] == str(D / "downloads/navegador")
    assert ch.seed_settings(lay_d) == "propios"
    s["theme"] = "dark"
    (lay_d["conf"] / "settings.json").write_text(json.dumps(s))
    lay_s = ch.layout("stable", home)
    assert json.loads((lay_s["conf"] / "settings.json").read_text() if (lay_s["conf"] / "settings.json").exists() else "{}") == {}
    ch.seed_settings(lay_s)
    assert json.loads((lay_s["conf"] / "settings.json").read_text())["theme"] == "aurora"   # cada canal, los suyos


def test_sin_instalacion_antigua(home):
    lay = ch.layout("stable", home)
    rep = ch.migrate(lay, sources=[])
    assert rep["hecho"] and rep["origen"] is None and (lay["data"] / ".migrado").exists()
    assert ch.seed_settings(lay, sources=[]) == ""


# ---------------------------------------------------------------- forgeinator-ctl, bin/hub, hub-update
def _ctl(home, root, *args):
    env = dict(os.environ, HUB_DIR=str(root))
    t = time.time()
    r = subprocess.run([sys.executable, str(HUB_SRC / "bin" / "forgeinator-ctl"), *args], capture_output=True, text=True, env=env, timeout=20)
    return r, time.time() - t


def _fake_copy(home, c):
    d = _copy(home, c)
    for n in ("hub", "bin"):
        if not (d / n).exists():
            (d / n).symlink_to(HUB_SRC / n)
    (d / "VERSION").write_text("9.9\n")
    return d


def test_qam_status_rapido_y_completo(home):
    d = _fake_copy(home, "dev")
    r, dt = _ctl(home, d, "--qam-status")
    st = json.loads(r.stdout.strip().splitlines()[-1])
    assert r.returncode == 0 and dt < 2.0
    assert st["channel"] in ("dev", "legacy") and st["installed"]["dev"] is True and isinstance(st["notices"], list)
    assert "version" in st and "running" in st


def test_ctl_canal(home):
    _fake_copy(home, "dev")
    s = _fake_copy(home, "stable")
    r, _ = _ctl(home, s, "--canal")
    assert "canal activo: Estable" in r.stdout
    r, _ = _ctl(home, s, "--canal", "dev")
    assert r.returncode == 0 and ch.active() == "dev"
    r, _ = _ctl(home, s, "--resolve-active")
    assert r.stdout.strip() == str(home / "homebrew/qam-apps/forgeinator-dev")
    (home / "homebrew/qam-apps/forgeinator-dev/CHANNEL").unlink()
    r, _ = _ctl(home, s, "--canal", "dev")
    assert r.returncode == 1 and "No está instalada" in r.stderr


def test_instalacion_antigua_abre_la_del_qam(home, tmp_path):
    old = tmp_path / "Games/recomp-hub"
    (old / "bin").mkdir(parents=True)
    for n in ("hub", "_dirs.sh"):
        (old / "bin" / n).write_text((HUB_SRC / "bin" / n).read_text())
    d = _copy(home, "dev")
    (d / "bin").mkdir()
    (d / "bin" / "forgeinator").write_text('#!/bin/sh\necho "ABIERTA $0 $*"\n')
    (d / "bin" / "forgeinator").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ("HUB_DATA", "HUB_LEGACY")}
    r = subprocess.run(["bash", str(old / "bin" / "hub"), "--list"], capture_output=True, text=True, env=env, timeout=20)
    assert "ABIERTA" in r.stdout and "--active --list" in r.stdout
    assert "instalación antigua" in (old / "data/hub.log").read_text()
    env["HUB_LEGACY"] = "1"                                              # forzar la vieja
    r = subprocess.run(["bash", str(old / "bin" / "hub"), "--list"], capture_output=True, text=True, env=env, timeout=30)
    assert "ABIERTA" not in r.stdout


def test_hub_update_no_toca_la_estable(home, tmp_path):
    s = _fake_copy(home, "stable")
    upd = home / "Games/actualizaciones"
    upd.mkdir(parents=True)
    (upd / "recomp-hub-update-v99.0.zip").write_bytes(b"PK")
    env = dict(os.environ, HUB_DIR=str(s))
    r = subprocess.run([sys.executable, str(HUB_SRC / "bin" / "hub-update"), "--json"], capture_output=True, text=True, env=env, timeout=20)
    assert json.loads(r.stdout)["new"] is None
    r = subprocess.run([sys.executable, str(HUB_SRC / "bin" / "hub-update"), "--auto"], capture_output=True, text=True, env=env, timeout=20)
    assert r.returncode == 0 and (upd / "recomp-hub-update-v99.0.zip").exists()
    d = _fake_copy(home, "dev")
    r = subprocess.run([sys.executable, str(HUB_SRC / "bin" / "hub-update"), "--json"], capture_output=True, text=True,
                       env=dict(os.environ, HUB_DIR=str(d)), timeout=20)
    assert json.loads(r.stdout)["new"] == "99.0"                         # dev sí recoge los zip


# ---------------------------------------------------------------- paquetes
@pytest.fixture(scope="module")
def rel(tmp_path_factory):
    out = tmp_path_factory.mktemp("rel")
    r = subprocess.run([sys.executable, str(HUB_SRC / "tools" / "make_release.py"), "--out", str(out), "--dev", "--version", "9.9"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    return out


@pytest.mark.parametrize("c,top", [("stable", "forgeinator"), ("dev", "forgeinator-dev")])
def test_zip_de_app_del_qam(rel, c, top):
    z = zipfile.ZipFile(rel / f"{top}-9.9.zip")
    names = z.namelist()
    assert all(n.startswith(top + "/") for n in names)
    assert z.read(f"{top}/CHANNEL").decode().strip() == c and z.read(f"{top}/VERSION").decode().strip() == "9.9"
    assert not any("/data/" in n or "__pycache__" in n for n in names)
    m = json.loads(z.read(f"{top}/qam-app.json"))
    assert m["schema"] == 1 and m["id"] == top and m["version"] == "9.9" and m["launch"] == "bin/forgeinator"
    assert m["status"] == "bin/forgeinator --qam-status" and m["install"] == "install.sh" and m["keep"] == []
    assert "~/.local/share/forgeinator" in m["data_dirs"]
    assert ("update" in m) == (c == "stable")
    if c == "stable":
        assert m["update"]["repo"] == "pascaltll/Forgeinator" and m["update"]["checksum"] == "SHA256SUMS"
    for k, p in m["art"].items():
        assert f"{top}/{p}" in names, k
    for n in (f"{top}/bin/forgeinator", f"{top}/bin/forgeinator-ctl", f"{top}/bin/hub", f"{top}/install.sh"):
        assert (z.getinfo(n).external_attr >> 16) & 0o111, n             # ejecutables


def test_sumas_sha256(rel):
    sums = dict(reversed(ln.split("  ")) for ln in (rel / "SHA256SUMS").read_text().splitlines())
    assert set(sums) == {"forgeinator-9.9.zip", "forgeinator-dev-9.9.zip", "install-hub-v9.9.sh", "recomp-hub-update-v9.9.zip"}
    for n, h in sums.items():
        assert hashlib.sha256((rel / n).read_bytes()).hexdigest() == h


def test_install_sh_e_instalacion_completa(rel, home):
    qa = home / "homebrew/qam-apps"
    qa.mkdir(parents=True)
    zipfile.ZipFile(rel / "forgeinator-dev-9.9.zip").extractall(qa)
    for p in (qa / "forgeinator-dev").rglob("*"):
        if p.is_file() and (p.parent.name == "bin" or p.name in ("install.sh", "main.py")):
            p.chmod(0o755)
    r = subprocess.run(["bash", str(qa / "forgeinator-dev/install.sh")], capture_output=True, text=True, timeout=120)
    if "Falta pygame" in r.stderr:
        pytest.skip("sin pygame para el python3 del sistema")
    assert r.returncode == 0 and "(dev) listo" in r.stdout
    r = subprocess.run([str(qa / "forgeinator-dev/bin/forgeinator"), "--qam-status"], capture_output=True, text=True, timeout=20)
    st = json.loads(r.stdout)
    assert st["channel"] == "dev" and st["version"] == "9.9" and st["active"] == "dev"
    assert not (qa / "forgeinator-dev/data").exists()


def test_el_instalador_no_crea_data_en_una_copia_con_canal(rel, tmp_path):
    dest = tmp_path / "copia"
    dest.mkdir()
    (dest / "CHANNEL").write_text("dev\n")
    r = subprocess.run(["bash", str(rel / "install-hub-v9.9.sh")], capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, HUB_DIR=str(dest), FORCE="1"))
    assert r.returncode == 0, r.stderr[-400:]
    assert not (dest / "data").exists() and (dest / "CHANNEL").read_text() == "dev\n" and (dest / "bin/forgeinator").exists()


# ---------------------------------------------------------------- interfaz
def test_la_copia_inactiva_no_toca_lo_compartido(monkeypatch, tmp_path):
    from test_temas_y_fuzz import H  # noqa: F401
    import hub.ui as U
    from hub import config
    ui = U.UI.__new__(U.UI)
    ui.cfg = {"theme": "dark", "direct_play": True}
    called = []
    monkeypatch.setattr(U.chan, "is_active", lambda *a: False)
    monkeypatch.setattr(U.directplay, "apply_all", lambda *a, **k: called.append("apply") or 3)
    monkeypatch.setattr(U.directplay, "set_shortcut", lambda *a, **k: called.append("set"))
    monkeypatch.setattr(config, "DATA", tmp_path)
    ui._publish_look()
    assert not (tmp_path / "appearance.json").exists()
    (tmp_path / "appearance-request.json").write_text('{"request_id": "x", "theme": "light"}')
    assert U.UI.poll_appearance_request(ui, force=True) is None
    ui.toast = lambda m: called.append(m)
    ui.cfg["direct_play"] = False
    ui.cfg = dict(ui.cfg)
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    U.UI.toggle_direct_play(ui)
    assert "apply" not in called


def test_fila_de_canal_y_cambio(monkeypatch, home):
    from test_temas_y_fuzz import H  # noqa: F401
    import hub.ui as U
    from hub import config
    _copy(home, "dev")
    _copy(home, "stable")
    monkeypatch.setattr(config, "CHANNEL", "dev")
    ui = U.UI.__new__(U.UI)
    ui.cfg = {"direct_play": True}
    msgs, applied = [], []
    ui.toast = msgs.append
    ui._publish_look = lambda *a: None
    monkeypatch.setattr(U.directplay, "apply_all", lambda on: applied.append(on) or 2)
    assert "esta copia es Dev" in ui.channel_txt() and "activa: Estable" in ui.channel_txt() and "ACTIVAR ESTA" in ui.channel_txt()
    ui.switch_channel()
    assert ui.modal["kind"] == "choice" and "Dev" in ui.modal["title"]
    ui.modal["options"][0][1]()
    assert ch.active() == "dev" and applied == [True] and "Canal activo: Dev" in msgs[-1]
    assert "ACTIVAR ESTABLE" in ui.channel_txt()
    monkeypatch.setattr(config, "CHANNEL", "stable")
    ui.update_hub()
    assert "desde el QAM" in msgs[-1]


# ---------------------------------------------------------------- logo
def test_logo_pixel_reproducible(tmp_path):
    src = HUB_SRC / "tools" / "brand"
    for n in ("pixel_logo.py", "cartucho-base.svg"):
        (tmp_path / n).write_text((src / n).read_text())
    r = subprocess.run([sys.executable, str(tmp_path / "pixel_logo.py")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "cartucho.svg").read_text() == (src / "cartucho.svg").read_text()
    svg = (src / "cartucho.svg").read_text()
    assert 'viewBox="0 0 128 128"' in svg and "YUNQUE Y MARTILLO (generado)" in svg


def test_iconos_de_la_marca():
    pygame = pytest.importorskip("pygame")
    b = HUB_SRC / "assets" / "brand"
    for n, size in (("icon-512.png", 512), ("icon-256.png", 256), ("icon-64.png", 64), ("steam-capsule.png", (600, 900)),
                    ("steam-header.png", (920, 430)), ("github-social.png", (1280, 640))):
        im = pygame.image.load(str(b / n))
        assert im.get_size() == (size if isinstance(size, tuple) else (size, size)), n
    im = pygame.image.load(str(b / "icon-512.png"))
    assert im.get_at((256, 2)).a == 0 or im.get_at((0, 0)).a == 0       # icono redondo: sin fondo fuera del cartucho
    assert pygame.image.load(str(b / "icon-square.png")).get_at((0, 0)).a == 255


def test_actualizar_dev_con_zip_conserva_su_manifiesto(rel, tmp_path):
    """El zip de actualización (el de siempre) se aplica a la copia dev: su qam-app.json sigue siendo el de dev, no el del repositorio."""
    dest = tmp_path / "forgeinator-dev"
    dest.mkdir()
    (dest / "CHANNEL").write_text("dev\n")
    r = subprocess.run(["bash", str(rel / "install-hub-v9.9.sh")], capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, HUB_DIR=str(dest), FORCE="1"))
    assert r.returncode == 0
    m = json.loads((dest / "qam-app.json").read_text())
    assert m["id"] == "forgeinator-dev" and m["version"] == (dest / "VERSION").read_text().strip() and m["launch"] == "bin/forgeinator" and "update" not in m
