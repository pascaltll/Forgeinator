"""v2.04: God of War (PS2) del port PC entra en el catálogo con el mismo flujo que Liberty City Stories (clonar, compilar, git-build)."""
import tomllib

from hub import catalog, config, install


def _gow():
    return next(e for e in catalog.load() if e["id"] == "gow-ps2")


def test_la_ficha_de_gow_ps2_esta_en_el_catalogo():
    e = _gow()
    assert e["repo"] == "danielalves96/gow-pc-port"
    assert e["platform"] == "PlayStation 2"
    assert e["launcher_id"] == "gow-ps2"
    assert e["folder"] == "gow-ps2"            # no choca con una carpeta ~/Games/gow-pc-port que ya tengas (AppImage)
    assert "install.sh" in e["build"]["cmd"] and "$REPO" in e["build"]["cmd"] and "$JOBS" in e["build"]["cmd"]
    assert "--compiler g++" in e["build"]["cmd"]   # con el que compiló bien en tu Fedora
    assert e["build"]["artifact"] == "run_gow.sh"
    assert ".iso" in e["requires"]["formats"] and "SCUS-97399" in e["requires"]["serials"]


def test_no_se_confunde_con_gow3():
    ids = [e["id"] for e in catalog.load()]
    assert "gow3-spartanport" in ids and "gow-ps2" in ids
    assert _gow()["repo"] != next(e for e in catalog.load() if e["id"] == "gow3-spartanport")["repo"]


def test_el_registro_git_build_actualiza_con_install_sh_y_lanza_run_gow(tmp_path):
    e = _gow()
    f = install.register_build(e, tmp_path / "gow-ps2", e["build"]["artifact"], "fedora", e["build"]["cmd"], "origin/main", 6)
    t = tomllib.loads(f.read_text(encoding="utf-8"))
    assert t["id"] == "gow-ps2"
    assert t["update"]["type"] == "git-build"
    assert "./install.sh" in t["update"]["build"]
    assert t["update"]["build_in"][:3] == ["distrobox", "enter", "fedora"]
    assert t["run"]["exe"] == "run_gow.sh"
    assert t["run"]["cwd"] == "."
    assert t["ui"]["subtitle"] == "PlayStation 2"


def test_no_se_fija_wayland_a_mano():
    # solo hacía falta al lanzar por SSH; desde Hub/Steam la sesión ya lo trae
    import json
    import pathlib
    seed = (pathlib.Path(config.__file__).parent.parent / "catalog" / "seed.json").read_text(encoding="utf-8")
    assert "WAYLAND_DISPLAY" not in seed and "XDG_RUNTIME_DIR" not in seed
    assert json.loads(seed)
