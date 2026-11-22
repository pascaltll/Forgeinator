"""v1.80: enlace del juego en la carpeta del proyecto."""
import os
from pathlib import Path

from hub import library


def _rom(tmp_path):
    r = tmp_path / "roms" / "ps2" / "juego.iso"
    r.parent.mkdir(parents=True)
    r.write_bytes(b"x" * 10)
    return r


def test_crea_enlace_en_la_raiz_del_proyecto(tmp_path):
    rom, proj = _rom(tmp_path), tmp_path / "proj"
    proj.mkdir()
    t = library.place_default({"repo": "a/b"}, rom, proj)
    assert t == proj / "juego.iso" and t.is_symlink() and t.resolve() == rom.resolve()


def test_idempotente_y_reemplaza_enlace_viejo(tmp_path):
    rom, proj = _rom(tmp_path), tmp_path / "proj"
    proj.mkdir()
    (proj / "juego.iso").symlink_to(tmp_path / "otro")
    t = library.place_default({}, rom, proj)
    assert t.resolve() == rom.resolve()
    assert library.place_default({}, rom, proj) == t


def test_no_pisa_un_archivo_real(tmp_path):
    rom, proj = _rom(tmp_path), tmp_path / "proj"
    proj.mkdir()
    (proj / "juego.iso").write_bytes(b"real")
    t = library.place_default({}, rom, proj)
    assert not t.is_symlink() and t.read_bytes() == b"real"


def test_respeta_place_y_rom_dest(tmp_path):
    rom, proj = _rom(tmp_path), tmp_path / "proj"
    proj.mkdir()
    assert library.place_default({"requires": {"place": "x/y"}}, rom, proj) is None
    assert library.place_default({"requires": {"rom_dest": str(tmp_path / "d")}}, rom, proj) is None
    assert not list(proj.iterdir())


def test_carpeta_inexistente_o_vacio(tmp_path):
    rom = _rom(tmp_path)
    assert library.place_default({}, rom, tmp_path / "nada") is None
    assert library.place_default({}, None, tmp_path) is None
