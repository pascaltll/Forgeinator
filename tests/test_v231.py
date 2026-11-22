"""v2.31: Wine sin Wine en el sistema, contenedor deducido para cualquier juego, temas animados y tipografías descargables."""
import json
import subprocess
import time
from pathlib import Path

import pytest

from hub import fonts, osver, recipes


# ── wine ──
def test_wine_de_bottles_si_el_sistema_no_tiene(tmp_path, monkeypatch):
    monkeypatch.setattr(osver.shutil, "which", lambda n: None)
    monkeypatch.setattr(osver.Path, "home", classmethod(lambda c: tmp_path))
    assert osver.find_wine() == ""
    w = tmp_path / ".var/app/com.usebottles.bottles/data/bottles/runners/soda-9.0-1/bin/wine"
    w.parent.mkdir(parents=True)
    w.write_text("#!/bin/sh\n")
    w.chmod(0o755)
    assert osver.find_wine() == str(w)


def test_el_lanzador_de_wine_busca_y_avisa(tmp_path):
    t = osver.runner_text("game/G.exe", "GE", "wine")
    assert 'exec wine "$HERE/game/G.exe"' in t and "bottles/runners" in t and "compatibilitytools.d" in t
    f = tmp_path / "windows" / "hub-run.sh"
    (f.parent / "game").mkdir(parents=True)
    f.write_text(t)
    home = tmp_path / "home"
    home.mkdir()
    r = subprocess.run(["/bin/sh", str(f)], capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin"})
    assert r.returncode == 127 and "no hay Wine" in r.stderr
    w = home / ".local/share/lutris/runners/wine/x/bin/wine"
    w.parent.mkdir(parents=True)
    w.write_text("#!/bin/sh\necho WINE-OK \"$1\"\n")
    w.chmod(0o755)
    r = subprocess.run(["/bin/sh", str(f)], capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin"})
    lg = (tmp_path / "hub-wine.log").read_text()          # v2.53: la salida de Wine va al registro
    assert "WINE-OK" in lg and "G.exe" in lg


# ── contenedor deducido ──
def test_contenedor_deducido_de_linux_package_json(tmp_path):
    (tmp_path / "linux-package.json").write_text(json.dumps({"build_os": {"ID": "ubuntu", "VERSION_ID": "26.04"}}))
    rt = recipes.runtime_guess({"id": "j"}, tmp_path)
    assert rt["runtime"]["image"] == "ubuntu:26.04" and rt["runtime"]["auto_libs"]
    st = recipes.runtime_steps(rt, {"id": "j"}, tmp_path, "/x/juego")
    assert "hub-j" in st[0][1][-1] and "apt-file" in st[1][1][-1] and "/x/juego" in st[1][1][-1]


def test_contenedor_deducido_del_nombre_o_de_lo_que_falta(tmp_path):
    assert recipes.runtime_guess({"id": "j"}, tmp_path, "juego-linux-fedora43.tar.gz")["runtime"]["image"] == "fedora:43"
    assert recipes.runtime_guess({"id": "j"}, tmp_path, "juego.zip", ["libfoo.so.1"])["runtime"]["image"] == "fedora:latest"
    assert recipes.runtime_guess({"id": "j"}, tmp_path, "juego.zip") is None, "sin pistas y sin faltas: no se ofrece nada"
    assert "dnf install" in recipes.auto_libs_cmd("dnf", "/x/y") and "*/$l" in recipes.auto_libs_cmd("dnf", "/x/y")


# ── tipografías ──
def test_fuente_se_descarga_y_valida(tmp_path, monkeypatch):
    src = tmp_path / "srv" / "poppins"
    src.mkdir(parents=True)
    ttf = b"\x00\x01\x00\x00" + b"\0" * 30000
    (src / "Poppins-Regular.ttf").write_bytes(ttf)
    (src / "Poppins-SemiBold.ttf").write_bytes(b"<html>404</html>" * 3000)      # respuesta que no es una fuente
    monkeypatch.setattr(fonts, "BASE", (tmp_path / "srv").as_uri() + "/")
    monkeypatch.setattr(fonts.config, "DATA", tmp_path / "data")
    assert fonts.paths("poppins") is None
    assert fonts.fetch("poppins") is True
    reg, bold, fat = fonts.paths("poppins")
    assert Path(reg).is_file() and bold == reg and not (tmp_path / "data" / "fonts" / "Poppins-SemiBold.ttf").exists()


def test_sin_red_el_tema_sigue(tmp_path, monkeypatch):
    monkeypatch.setattr(fonts, "BASE", (tmp_path / "nada").as_uri() + "/")
    monkeypatch.setattr(fonts.config, "DATA", tmp_path / "data")
    assert fonts.fetch("vt323") is False and fonts.paths("vt323") is None


pygame = pytest.importorskip("pygame")


@pytest.mark.ui
@pytest.mark.parametrize("th", ["aurora", "pixel", "brasa"])
def test_temas_animados_se_dibujan(th):
    import hub.ui as H
    u = test_temas_animados_se_dibujan.__dict__.setdefault("u", None) or H.UI()
    test_temas_animados_se_dibujan.u = u
    u.set_look(theme=th, fx="glass")
    assert H.ANIM and H.FONT in fonts.DL
    u.go_tab("home")
    for _ in range(4):
        u.frame()
        time.sleep(0.01)
    a = pygame.image.tobytes(u.screen, "RGB")
    time.sleep(0.4)
    for _ in range(3):
        u.frame()
    assert pygame.image.tobytes(u.screen, "RGB") != a, "el fondo se mueve"
    u.set_look(fx="perf")
    u.frame()
    b = pygame.image.tobytes(u.screen, "RGB")
    time.sleep(0.3)
    u.frame()
    assert pygame.image.tobytes(u.screen, "RGB") == b, "en «rendimiento» no se anima"
    u.set_look(theme="dark", fx="glass")
