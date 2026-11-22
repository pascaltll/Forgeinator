"""v3.10 · repos solo de Windows con un .exe suelto o .rar (God of War II HD), INSTALAR que sigue a Windows, arranque directo sin la
pantalla del launcher, toques fantasma, rueda sin desbordar, recuperación de una pantalla que falla y Obsidian ↔ Minimal."""
import os
import subprocess
import sys
import types
from pathlib import Path

import pygame
import pytest

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from hub import github, install, directplay, config
from hub.themes import migration, legacy, studio

GOW2 = [{"name": "Gow2HD-Windows.exe", "size": 9_000_000, "browser_download_url": "https://x/Gow2HD-Windows.exe"}]


# ── God of War II HD: la release es un único .exe ───────────
def test_exe_suelto_es_el_build_de_windows():
    wa = github.win_assets(GOW2)
    assert len(wa) == 1 and wa[0]["class"]["kind"] == "ejecutable" and wa[0]["name"] == "Gow2HD-Windows.exe"
    assert github.rank_assets(GOW2) == []                       # para Linux no hay nada (como antes)
    v = github._view({"tag_name": "v1", "assets": GOW2}, {"error": None, "stale": False}, "x86_64", "")
    assert v["has_windows"] and v["win_assets"]


def test_exe_que_no_son_el_juego_no_cuentan():
    raros = [{"name": n} for n in ("vc_redist.x64.exe", "crashpad_handler.exe", "uninstall.exe", "Game-server.exe", "debug-symbols.exe")]
    assert github.win_assets(raros) == []
    assert [a["class"]["kind"] for a in github.win_assets([{"name": "Setup.exe"}])] == ["instalador"]


def test_rar_de_windows_y_preferencias():
    wa = github.win_assets([{"name": "Game-windows-x64.rar"}, {"name": "Game-windows-x64.zip"}, {"name": "Game.exe"}])
    assert [a["class"]["kind"] for a in wa] == ["zip", "rar", "ejecutable"]
    assert github.classify("a.rar")["kind"] == "rar" and github.classify("a.exe")["kind"] == "exe"


def test_instalar_un_exe_suelto_lo_copia(tmp_path):
    exe = tmp_path / "Gow2HD-Windows.exe"
    exe.write_bytes(b"MZ" + b"\0" * 100)
    dest = tmp_path / "windows"
    install.extract(exe, dest)
    assert (dest / "Gow2HD-Windows.exe").read_bytes() == exe.read_bytes()


def test_instalar_sigue_a_windows_si_la_release_solo_trae_windows(ui, monkeypatch):
    e = ui.entries[0]
    llamado = []
    monkeypatch.setattr(ui, "rel_for", lambda e_: {"tag": "v1", "assets": [], "win_assets": github.win_assets(GOW2)})
    monkeypatch.setattr(ui, "install_windows_dl", lambda e_, fresh=False: llamado.append(fresh))
    ui.toast_msg = ""
    ui.do_install(e)
    assert llamado, "debía ir a la instalación de Windows"
    assert "No hay un build" not in ui.toast_msg


def test_instalar_sin_nada_avisa(ui, monkeypatch):
    monkeypatch.setattr(ui, "rel_for", lambda e_: {"tag": "v1", "assets": [], "win_assets": []})
    ui.do_install(ui.entries[0])
    assert "ni para Linux ni para Windows" in ui.toast_msg


# ── arranque directo ────────────────────────────────────────
def _launcher(tmp_path):
    root = tmp_path / "launcher"
    for d in ("core", "games", "shortcuts", "state", "bin"):
        (root / d).mkdir(parents=True)
    (root / "core" / "__init__.py").write_text("")
    (root / "core" / "config.py").write_text(
        "from pathlib import Path\nSTATE_DIR = Path(__file__).resolve().parent.parent / 'state'\n"
        "class G:\n    id = 'fake'\n"
        "def load_game(i):\n    if i != 'fake':\n        raise ValueError('no existe')\n    return G()\n")
    (root / "core" / "runner.py").write_text(
        "import os, sys\nclass L:\n    def __init__(s, c):\n        s.cmd = c\n    def exec(s):\n        os.execvp(s.cmd[0], s.cmd)\n"
        "def missing(g):\n    return []\n"
        f"def build(g, extra=()):\n    return L([{sys.executable!r}, '-c', 'import sys; open(sys.argv[1], \"w\").write(\"ok \" + \" \".join(sys.argv[2:]))', "
        f"{str(tmp_path / 'out.txt')!r}] + list(extra))\n")
    play = root / "bin" / "play"
    play.write_text(f"#!/bin/bash\necho \"play $@\" > {tmp_path / 'out.txt'}\n")
    play.chmod(0o755)
    return root


def test_playdirect_abre_el_juego_sin_el_launcher(tmp_path):
    root = _launcher(tmp_path)
    r = subprocess.run([sys.executable, str(directplay.SCRIPT), "--root", str(root), "fake", "--x"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out.txt").read_text() == "ok --x"


def test_playdirect_cede_al_launcher_si_falla(tmp_path):
    root = _launcher(tmp_path)
    subprocess.run([sys.executable, str(directplay.SCRIPT), "--root", str(root), "otro", "--y"], capture_output=True, text=True, timeout=30)
    assert (tmp_path / "out.txt").read_text().strip() == "play otro --y"


def test_accesos_de_steam_directos_y_de_vuelta(tmp_path, monkeypatch):
    root = _launcher(tmp_path)
    monkeypatch.setattr(config, "LAUNCHER", root)
    gen = root / "shortcuts" / "fake.sh"
    orig = '#!/usr/bin/env bash\n# generado por launcher (play --shortcuts): no lo edites, se regenera\nexec "$(dirname "$(readlink -f "$0")")/../bin/play" fake "$@"\n'
    gen.write_text(orig)
    gen.chmod(0o755)
    mio = root / "shortcuts" / "mio.sh"
    mio.write_text("#!/bin/bash\necho hecho a mano\n")
    assert directplay.apply_all(True) == 1
    assert directplay.state("fake") == "direct" and directplay.state("mio") == "custom"
    assert (root / "shortcuts" / "fake.sh.launcher").read_text() == orig
    assert directplay.apply_all(True) == 0                       # idempotente
    r = subprocess.run([str(gen), "--z"], capture_output=True, text=True, timeout=30, env={**os.environ, "HOME": str(tmp_path)})
    assert (tmp_path / "out.txt").read_text() == "ok --z", r.stderr
    assert directplay.apply_all(False) == 1 and gen.read_text() == orig
    assert mio.read_text() == "#!/bin/bash\necho hecho a mano\n"


def test_jugar_desde_hub_usa_el_arranque_directo(ui, monkeypatch):
    ui.cfg["direct_play"] = True
    assert directplay.command("x")[1:] == [str(directplay.SCRIPT), "--root", str(config.LAUNCHER), "x"]
    assert ui.__class__.toggle_direct_play
    ui.toggle_direct_play()
    assert ui.cfg["direct_play"] is False
    ui.toggle_direct_play()
    assert ui.cfg["direct_play"] is True


# ── revisión de lógica ──────────────────────────────────────
def test_soltar_no_pulsa_un_boton_que_aparecio_debajo(ui, monkeypatch):
    ui.set_look(theme="limpio", fx="perf")
    ui.go_tab("home")
    run(ui, 2)
    w = next(x for x in ui.widgets if x.cb)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1))
    run(ui, 1)
    disparos = []
    ui.confirm("Prueba", "¿Seguro?", lambda: disparos.append(1))       # se abre un menú mientras el dedo sigue apoyado
    run(ui, 2)
    pos = next((x.rect.center for x in ui.widgets if x.cb), w.rect.center)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
    run(ui, 2)
    assert not disparos and ui.modal is not None
    ui.modal = None


def test_un_toque_normal_sigue_funcionando(ui):
    ui.set_look(theme="limpio", fx="perf")
    ui.go_tab("settings")
    run(ui, 3)
    w = next(x for x in ui.widgets if str(x.key).startswith("cat:"))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=w.rect.center, button=1))
    run(ui, 1)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=w.rect.center, button=1))
    run(ui, 2)
    assert getattr(ui, "set_page", None) == w.key[4:]
    ui.settings_back()


def test_rueda_en_pagina_corta_no_desplaza(ui):
    ui.go_tab("home")
    run(ui, 2)
    v = ui._main_view()
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=3, flipped=False))
    ui.pump()
    assert v.off >= 0


def test_pantalla_que_falla_vuelve_a_inicio(ui):
    ui.detail = ui.entries[0]["id"]
    ui.modal = {"kind": "confirm", "title": "x", "msg": "y", "cb": lambda: None}
    ui._safe_reset()
    assert ui.tab == "home" and ui.modal is None and ui.detail is None
    assert "Inicio" in ui.toast_msg


# ── Obsidian ────────────────────────────────────────────────
def test_obsidian_es_minimal_con_la_paleta_obsidian():
    m = migration.migrate_v285({"theme": "obsidian"})
    assert m["active_preset"] == "minimal" and m["appearance"]["palette"]["id"] == "obsidian" and m["appearance"]["layout"] == "posters"
    a, b = legacy.build("obsidian"), studio.build("v3:minimal", "obsidian", "posters")
    for k in ("BG", "PANEL", "PANEL2", "LINE", "TXT", "DIM", "ACC", "OK", "WARN", "ERR"):
        assert a[k] == b[k], k                                   # no pueden divergir: el día que se fusionen, se ve igual
    assert a["HOME"] == b["HOME"] == "posters" and a.get("ANIM") is None


def test_version_del_paquete_igual_que_version():
    """v3.13: el QAM Rail toma la versión de hub/__init__.py; tiene que coincidir con VERSION."""
    import re
    from conftest import HUB_SRC
    v = (HUB_SRC / "VERSION").read_text().strip()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (HUB_SRC / "hub" / "__init__.py").read_text())
    assert m and m.group(1) == v


def test_qam_app_json_valido_y_con_arte():
    import json
    from conftest import HUB_SRC
    m = json.loads((HUB_SRC / "qam-app.json").read_text())
    assert m["id"] == "forgeinator" and m["name"] == "Forgeinator 3000" and (HUB_SRC / m["launch"]).is_file()
    assert "data" in m["keep"]
    for k in ("capsule", "header", "hero", "logo", "icon"):
        assert (HUB_SRC / m["art"][k]).is_file(), k
