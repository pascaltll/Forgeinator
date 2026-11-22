"""Papelera de Hub: rutas permitidas, mover/restaurar/vaciar, enlaces (nunca se borra el destino) y otro disco."""
import os
import time
from pathlib import Path

import pytest

from hub import config, trash


@pytest.fixture
def games(tmp_path, monkeypatch):
    g = tmp_path / "Games"
    g.mkdir()
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", g / "launcher")
    monkeypatch.setattr(config, "DATA", g / "recomp-hub" / "data")
    monkeypatch.setattr(config, "ROOT", g / "recomp-hub")
    (g / "launcher" / "games").mkdir(parents=True)
    (g / "launcher" / "art").mkdir()
    (config.DATA / "downloads").mkdir(parents=True)
    orig = config.path
    monkeypatch.setattr(config, "path", lambda k: config.DATA / "downloads" if k == "downloads_dir" else orig(k))
    return g


def mk(p, text="x"):
    p.mkdir(parents=True, exist_ok=True)
    (p / "f.txt").write_text(text)
    return p


# ── check_path ──────────────────────────────────────────────────────────────
def test_acepta_la_carpeta_de_un_juego(games):
    assert trash.check_path(mk(games / "MiJuego"), "project") == (games / "MiJuego").resolve()


@pytest.mark.parametrize("rel", ["", "launcher", "recomp-hub", "recomp-hub/data", "recomp-hub/data/downloads", ".papelera-hub"])
def test_rechaza_carpetas_protegidas(games, rel):
    (games / ".papelera-hub").mkdir(exist_ok=True)
    with pytest.raises(trash.Unsafe):
        trash.check_path(games / rel if rel else games, "project")


def test_rechaza_un_ancestro_de_hub(games, tmp_path, monkeypatch):
    # carpeta que CONTIENE a Hub: borrarla se llevaría Hub entero
    monkeypatch.setattr(config, "ROOT", games / "Padre" / "recomp-hub")
    mk(games / "Padre" / "recomp-hub")
    with pytest.raises(trash.Unsafe, match="protegida"):
        trash.check_path(games / "Padre", "project")


def test_rechaza_fuera_de_games_y_home(games, tmp_path):
    with pytest.raises(trash.Unsafe, match="fuera"):
        trash.check_path(mk(tmp_path / "otro"), "project")
    with pytest.raises(trash.Unsafe):
        trash.check_path(Path.home(), "project")
    with pytest.raises(trash.Unsafe):
        trash.check_path("/", "project")


def test_rechaza_enlaces_simbolicos_y_inexistentes(games, tmp_path):
    real = mk(tmp_path / "real")
    (games / "enlace").symlink_to(real)
    with pytest.raises(trash.Unsafe, match="enlace"):
        trash.check_path(games / "enlace", "project")
    with pytest.raises(trash.Unsafe, match="no existe"):
        trash.check_path(games / "nada", "project")


def test_project_exige_carpeta(games):
    (games / "suelto.txt").write_text("x")
    with pytest.raises(trash.Unsafe, match="no es una carpeta"):
        trash.check_path(games / "suelto.txt", "project")


def test_descargas_solo_dentro_de_la_carpeta_de_descargas(games, tmp_path):
    f = config.DATA / "downloads" / "juego.zip"
    f.write_text("z")
    assert trash.check_path(f, "download")
    out = tmp_path / "x.zip"
    out.write_text("z")
    with pytest.raises(trash.Unsafe, match="fuera de la carpeta de descargas"):
        trash.check_path(out, "download")
    with pytest.raises(trash.Unsafe):
        trash.check_path(config.DATA / "downloads", "download")     # la carpeta en sí, no


def test_launcher_solo_games_y_art(games):
    (games / "launcher" / "games" / "g.toml").write_text("id='g'")
    (games / "launcher" / "bin").mkdir()
    (games / "launcher" / "bin" / "play").write_text("x")
    assert trash.check_path(games / "launcher" / "games" / "g.toml", "launcher")
    with pytest.raises(trash.Unsafe):
        trash.check_path(games / "launcher" / "bin" / "play", "launcher")
    with pytest.raises(trash.Unsafe, match="tipo desconocido"):
        trash.check_path(games / "launcher" / "games" / "g.toml", "otro")


# ── mover / restaurar / vaciar ──────────────────────────────────────────────
def test_mover_y_restaurar(games):
    d = mk(games / "MiJuego", "datos")
    op = trash.move_to_trash([(d, "project")], "Mi Juego", "mj")
    assert not d.exists() and (op / "meta.json").is_file()
    ops = trash.list_ops()
    assert len(ops) == 1 and ops[0]["label"] == "Mi Juego" and ops[0]["eid"] == "mj"
    ok, skipped = trash.restore(op)
    assert ok == 1 and skipped == [] and (d / "f.txt").read_text() == "datos" and not op.exists()


def test_valida_todo_antes_de_mover_nada(games, tmp_path):
    d = mk(games / "MiJuego")
    with pytest.raises(trash.Unsafe):
        trash.move_to_trash([(d, "project"), (tmp_path / "fuera", "project")], "x")
    assert (d / "f.txt").exists() and not trash.root().exists()


def test_el_destino_de_un_enlace_dentro_del_juego_no_se_toca(games, tmp_path):
    rom = tmp_path / "ROMs" / "Silent Hill.chd"
    rom.parent.mkdir()
    rom.write_text("MI ROM")
    d = mk(games / "MiJuego")
    (d / "game.chd").symlink_to(rom)
    op = trash.move_to_trash([(d, "project")], "MiJuego")
    assert rom.read_text() == "MI ROM"
    assert (op / "0-MiJuego" / "game.chd").is_symlink()          # el enlace viaja, la ROM no se mueve
    trash.empty()
    assert rom.read_text() == "MI ROM", "vaciar la papelera NO debe seguir el enlace y borrar tu ROM"


def test_restaurar_no_pisa_lo_que_ya_existe(games):
    d = mk(games / "MiJuego", "viejo")
    op = trash.move_to_trash([(d, "project")], "MiJuego")
    mk(games / "MiJuego", "nuevo")
    ok, skipped = trash.restore(op)
    assert ok == 0 and len(skipped) == 1 and (games / "MiJuego" / "f.txt").read_text() == "nuevo"
    assert op.exists(), "lo no restaurado se queda en la papelera"


def test_otro_disco_usa_copia_conservando_enlaces(games, tmp_path, monkeypatch):
    rom = tmp_path / "r.bin"
    rom.write_text("R")
    d = mk(games / "MiJuego")
    (d / "enl").symlink_to(rom)
    real = os.rename

    def falla(a, b):
        raise OSError(18, "Invalid cross-device link")
    monkeypatch.setattr(os, "rename", falla)
    op = trash.move_to_trash([(d, "project")], "MiJuego")
    monkeypatch.setattr(os, "rename", real)
    assert not d.exists() and (op / "0-MiJuego" / "enl").is_symlink() and rom.read_text() == "R"


def test_operaciones_en_el_mismo_segundo_no_chocan(games):
    a, b = mk(games / "A"), mk(games / "B")
    o1 = trash.move_to_trash([(a, "project")], "Mismo")
    o2 = trash.move_to_trash([(b, "project")], "Mismo")
    assert o1 != o2 and len(trash.list_ops()) == 2


def test_empty_y_listas_vacias(games):
    assert trash.list_ops() == [] and trash.empty() == 0
    trash.move_to_trash([(mk(games / "A"), "project")], "A")
    assert trash.empty() == 1 and trash.list_ops() == []


def test_list_ops_ignora_carpetas_sin_meta(games):
    (trash.root() / "basura").mkdir(parents=True)
    assert trash.list_ops() == []


# ── size_of ─────────────────────────────────────────────────────────────────
def test_size_of(games, tmp_path):
    d = games / "S"
    (d / "sub").mkdir(parents=True)
    (d / "a").write_bytes(b"1" * 100)
    (d / "sub" / "b").write_bytes(b"2" * 50)
    big = tmp_path / "enorme"
    big.write_bytes(b"3" * 10_000)
    (d / "enlace").symlink_to(big)
    assert trash.size_of(d) == (150, True)                      # no cuenta el destino del enlace
    assert trash.size_of(d / "a") == (100, True)
    assert trash.size_of(games / "no-existe") == (0, True)
    assert trash.size_of(d, limit_s=-1)[1] is False             # límite de tiempo → resultado parcial
