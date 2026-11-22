import os, sys
from conftest import HUB_SRC  # noqa: E402
sys.path.insert(0, str(HUB_SRC))
from hub import proctree, recipes


def test_clean_env_sin_preload(monkeypatch):
    monkeypatch.setenv("LD_PRELOAD", "/x/gameoverlayrenderer.so")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/steam/rt")
    e = proctree.clean_env({"A": "1"})
    assert "LD_PRELOAD" not in e and "LD_LIBRARY_PATH" not in e and e["A"] == "1"
    assert recipes._cenv().get("LD_PRELOAD") is None




def test_fix_command_y_bash_func(monkeypatch):
    assert recipes.fix_command("sudo install -y mesa-libGL") == "sudo dnf install -y mesa-libGL"
    assert recipes.fix_command("install -y clang") == "sudo dnf install -y clang"
    assert recipes.fix_command(" sudo dnf install -y clang ") == "sudo dnf install -y clang"
    assert recipes.fix_command("install -D a b") == "install -D a b"
    monkeypatch.setenv("BASH_FUNC_post_gamescope_start%%", "() { if")
    assert not any(k.startswith("BASH_FUNC_") for k in proctree.clean_env())


def test_retarget_runner(tmp_path):
    from hub import osver, recipes
    s = tmp_path / "hub-run.sh"
    s.write_text(recipes.runner_text("build/vcs", ".", "", "hub-viejo"), encoding="utf-8")
    assert osver._retarget_runner(s, "hub-nuevo")
    t = s.read_text()
    assert "distrobox enter hub-nuevo --" in t and "hub-viejo --" not in t
    assert not osver._retarget_runner(s, "hub-nuevo")
