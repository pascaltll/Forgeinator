"""v2.28: al actualizar por encima, si la release cambió de estructura, el .toml del launcher se corrige."""
import tomllib
import zipfile

from hub import config, install


def _zip(p, files):
    with zipfile.ZipFile(p, "w") as z:
        for n, d in files.items():
            z.writestr(n, d)
    return p


ELF = b"\x7fELF" + b"\0" * 60


def test_cambio_de_estructura_corrige_el_toml(tmp_path, monkeypatch):
    g, l = tmp_path / "Games", tmp_path / "launcher"
    (l / "games").mkdir(parents=True)
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", l)
    e = {"id": "bt4", "name": "BT4 Tag Team", "repo": "u/bt4", "platform": "PC"}
    old = _zip(tmp_path / "a.zip", {"BT4decomp/BT4decomp": ELF, "BT4decomp/x.dat": b"1", "leeme.txt": b"hola"})
    install.install(e, old, "bt4-linux.zip", "v1")
    f = l / "games" / "bt4.toml"
    txt = f.read_text().replace('cwd = "."', 'cwd = "BT4decomp"') + '\n# hub:art begin\nicon = "/x/icon.png"\n# hub:art end\n'
    f.write_text(txt)
    assert tomllib.loads(txt)["run"]["exe"] == "BT4decomp/BT4decomp"
    import shutil
    shutil.rmtree(g / "bt4" / "BT4decomp")              # la versión nueva trae el binario en la raíz
    new = _zip(tmp_path / "b.zip", {"BT4decomp": ELF, "BT4decomp.dat": b"1", "leeme.txt": b"hola"})
    res = install.install(e, new, "bt4-linux.zip", "v2")
    t = tomllib.loads(f.read_text())
    assert res["repaired"] == "BT4decomp/BT4decomp"
    assert t["run"]["exe"] == "BT4decomp" and t["run"]["cwd"] == "." and t["update"]["executables"] == ["BT4decomp"]
    assert "hub:art begin" in f.read_text() and (l / "games" / "bt4.toml.bak").is_file()


def test_si_el_ejecutable_sigue_ahi_no_toca_nada(tmp_path, monkeypatch):
    g, l = tmp_path / "Games", tmp_path / "launcher"
    (l / "games").mkdir(parents=True)
    monkeypatch.setattr(config, "GAMES_DIR", g)
    monkeypatch.setattr(config, "LAUNCHER", l)
    e = {"id": "j", "name": "Juego", "repo": "u/j", "platform": "PC"}
    z = _zip(tmp_path / "a.zip", {"juego": ELF, "otro": ELF, "d.txt": b"1"})
    install.install(e, z, "j.zip", "v1")
    antes = (l / "games" / "j.toml").read_text()
    res = install.install(e, z, "j.zip", "v2")
    assert res["repaired"] is None and (l / "games" / "j.toml").read_text() == antes
