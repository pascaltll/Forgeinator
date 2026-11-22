"""v1.97: dónde quiere el port tu archivo según su README («Place your ROM in `gamedata/`») → se enlaza ahí, dentro de la carpeta del juego."""
import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")


@pytest.mark.parametrize("txt,esperado", [
    ("Place your Silent Hill (USA).bin disc image in the `gamedata/` folder next to the executable.", ["gamedata/"]),
    ("Put EBOOT.ELF and the PSP_GAME folder in lcs/game/ before running.", ["lcs/game/"]),
    ('Extract the ISO into the "assets" directory.', ["assets/"]),
    ("Coloca tu ROM en la carpeta `roms/`.", ["roms/"]),
    ("Copy your baserom.us.z64 into the root of the repository.", ["."]),
    ("Copy baserom.z64 to `baserom.us.z64`.", []),
    ("Install with sudo apt install libsdl2 into /usr/lib.", []),
    ("Download the latest release and extract it to a folder of your choice.", []),
    ("The game reads saves from the saves folder.", []),
])
def test_lee_del_readme_donde_va_tu_archivo(txt, esperado):
    from hub import roms
    assert roms.place_from_text(txt) == esperado


def test_una_sola_carpeta_clara_se_guarda_en_la_ficha():
    from hub import roms
    h = roms.hints_from_text("Place your disc image (.bin) in the `gamedata/` folder.")
    req = roms.merge_requires({}, h)
    assert req["place"] == "gamedata/" and req["place_from"] == "readme"
    assert "place" not in roms.merge_requires({"rom_dest": "~/.local/share/x"}, h), "una carpeta fija del catálogo manda"
    h2 = roms.hints_from_text("Put the ROM in `a/`. Or put the ROM in `b/`.")
    assert "place" not in roms.merge_requires({}, h2), "con dudas no se adivina"


def test_enlaza_en_la_carpeta_con_su_cue(tmp_path):
    from hub import library
    roms_d = tmp_path / "roms"
    roms_d.mkdir()
    (roms_d / "SH.bin").write_bytes(b"x")
    (roms_d / "SH.cue").write_text('FILE "SH.bin" BINARY\n')
    game = tmp_path / "SH" / "linux"
    game.mkdir(parents=True)
    t = library.place({"requires": {"place": "gamedata/"}}, roms_d / "SH.cue", game)
    assert t == game / "gamedata" / "SH.cue" and t.is_symlink() and (game / "gamedata" / "SH.bin").is_symlink()


def test_la_ficha_lo_aplica_sola_una_vez(H, ui, tmp_path, monkeypatch):
    import threading
    from hub import library
    roms_d = tmp_path / "roms"
    roms_d.mkdir()
    (roms_d / "SH.bin").write_bytes(b"x")
    game = tmp_path / "SH"
    game.mkdir()
    guardado, llamadas = {}, []

    class Sync:
        def __init__(self, target, daemon=None):
            self.t = target

        def start(self):
            self.t()
    e = {"id": "shx", "name": "Silent Hill", "repo": "a/b", "requires": {}}
    monkeypatch.setattr(threading, "Thread", Sync)
    monkeypatch.setattr(H.ghapi, "readme_raw", lambda repo: llamadas.append(repo) or "Place your .bin disc image in the `gamedata/` folder.")
    monkeypatch.setattr(H.catalog, "add_local", lambda d: guardado.update(d))
    monkeypatch.setattr(ui, "reload", lambda: None)
    monkeypatch.setattr(ui, "entry", lambda i: dict(e, **guardado) if i == "shx" else None)
    monkeypatch.setattr(library, "link_get", lambda i: str(roms_d / "SH.bin") if i == "shx" else None)
    ui._place_done.discard("shx")
    ui.auto_place(e, {"dir": str(game), "installed": True})
    ui.auto_place(e, {"dir": str(game), "installed": True})
    assert llamadas == ["a/b"], "una vez por sesión"
    assert guardado["requires"]["place"] == "gamedata/" and (game / "gamedata" / "SH.bin").is_symlink()
