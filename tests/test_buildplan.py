"""Plan de compilación leído del README (heurística): Linux sí, Windows/macOS no, apt→dnf, sin ejecutar nada sin verlo."""
import pytest

from hub import buildplan as B

README = """# Proj
## Building
### Windows
```
msbuild x.sln
vcpkg install sdl2
```
### Linux
```bash
sudo apt-get install -y build-essential libsdl2-dev libfoo-dev ninja-build
git clone --recursive https://github.com/a/b
cd b
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```
### macOS
```
brew install sdl2
cmake -B mac
```
## Run
```
./b
```
"""


def plan(md=README, **ctx):
    return B.plan_from_docs([("README.md", md)], {"entry": {"repo": "a/b"}, **ctx})


def test_descarta_windows_y_macos_y_arranque():
    cmds = [s["cmd"] for s in plan()["steps"]]
    assert not any("msbuild" in c or "vcpkg" in c or "brew" in c or "-B mac" in c or c == "./b" for c in cmds)


def test_traduce_apt_a_dnf_y_avisa_de_lo_dudoso():
    p = plan()
    d = next(s["cmd"] for s in p["steps"] if s["kind"] == "deps")
    assert d.startswith("sudo dnf install -y") and "SDL2-devel" in d and "@development-tools" in d and "libfoo-devel" in d
    assert any("libfoo-dev" in n for n in p["notes"])


def test_orden_submodulos_y_jobs():
    p = plan()
    kinds = [s["kind"] for s in p["steps"]]
    assert kinds == sorted(kinds, key=["deps", "prep", "config", "build"].index)
    assert any("submodule" in s["cmd"] for s in p["steps"]), "git clone --recursive se convierte en submódulos"
    assert p["steps"][-1]["cmd"].endswith("-j$JOBS") and p["confidence"] == "alta"


def test_no_incluye_git_clone_ni_cd_al_repo():
    cmds = [s["cmd"] for s in plan()["steps"]]
    assert not any(c.startswith(("git clone", "cd b")) for c in cmds)


def test_script_para_en_el_primer_error_y_una_linea():
    p = plan()
    assert B.to_cmd(p).startswith("cd '$REPO'\nset -e\n")
    assert "&&" in B.to_oneline(p) and "\n" not in B.to_oneline(p)


def test_alternativas_de_otra_herramienta_se_descartan():
    md = "## Linux\n```\nmake\n```\n## Linux (alternativa)\n```\ncmake -B b\ncmake --build b\n```\n"
    p = plan(md)
    assert [s["cmd"] for s in p["steps"]] == ["make -j$JOBS"]
    assert any("Descartada" in n for n in p["notes"])


SHIP = """# Building
## Windows
```powershell
cmake -S . -B build
```
## Linux
### Install dependencies
#### Debian/Ubuntu
```sh
sudo apt-get install gcc g++ git cmake ninja-build libsdl2-dev
```
#### Arch
```sh
sudo pacman -S gcc cmake sdl2
```
#### Fedora
```sh
sudo dnf install gcc gcc-c++ git cmake ninja-build SDL2-devel
# or using clang
sudo dnf install clang
```
### Verify cmake version
```sh
cmake --version
```
### Build
```bash
git submodule update --init
cmake -H. -Bbuild-cmake -GNinja
cmake --build build-cmake
```
### Generate a distributable
```bash
cd build-cmake
cpack -G TGZ
```
## macOS
```bash
brew install sdl2
```
"""


def test_elige_el_bloque_de_fedora_y_no_las_variantes_de_otras_distros():
    p = plan(SHIP)
    cmds = [s["cmd"] for s in p["steps"]]
    assert "sudo dnf install gcc gcc-c++ git cmake ninja-build SDL2-devel".replace("install", "install -y") in cmds
    assert not any("apt" in c or "pacman" in c or "clang" in c or "--version" in c for c in cmds)
    assert cmds[-1] == "cmake --build build-cmake -j$JOBS"
    assert not any(c.startswith("cd ") for c in cmds), "el «cd build» del bloque de distribuibles no entra"


def test_makes_con_distintas_versiones_solo_cuenta_el_primero():
    p = plan("## Linux\n```\nmake VERSION=jp -j4\nmake VERSION=eu\n```\n")
    assert [s["cmd"] for s in p["steps"]] == ["make VERSION=jp -j$JOBS"]


def test_sin_instrucciones_devuelve_none():
    assert B.plan_from_docs([("README.md", "# Hola\nsolo texto")]) is None


def test_sin_paso_de_compilar_baja_confianza():
    p = plan("## Linux\n```\nsudo apt install git\n```\n")
    assert p["confidence"] == "baja" and any("compila" in n for n in p["notes"])


def test_lee_del_repo_local_y_detecta_gitmodules(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text("## Linux\n```\ncmake -B build\ncmake --build build\n```\n")
    (tmp_path / ".gitmodules").write_text("[submodule x]\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "BUILDING.md").write_text("## Linux\n```\nsudo dnf install SDL2-devel\n```\n")
    p = B.plan_for({"repo": "a/b"}, tmp_path, lambda *a: (_ for _ in ()).throw(AssertionError("no debe usar la API")))
    assert p["steps"][0]["cmd"] == "sudo dnf install -y SDL2-devel" or p["steps"][0]["kind"] in ("deps", "prep")
    assert any("submodule" in s["cmd"] for s in p["steps"])


def test_proveedores_adicionales_se_pueden_registrar():
    llamado = []
    B.PROVIDERS.insert(0, lambda docs, ctx: llamado.append(1) or {"steps": [{"kind": "build", "cmd": "x", "from": ""}], "notes": [], "confidence": "media", "source": "ia", "provider": "asistente"})
    try:
        assert plan()["provider"] == "asistente" and llamado
    finally:
        B.PROVIDERS.pop(0)


def test_la_api_se_usa_si_no_hay_clon(tmp_path):
    import base64

    def api(path, params=None):
        if path.endswith("/contents/"):
            return [{"type": "file", "name": "README.md", "path": "README.md", "size": 50}]
        return {"content": base64.b64encode(b"## Linux\n```\nmake\n```\n").decode()}
    p = B.plan_for({"repo": "a/b"}, tmp_path / "no", api)
    assert p and p["steps"][-1]["cmd"] == "make -j$JOBS"


@pytest.mark.ui
def test_la_ficha_ofrece_el_boton_y_el_modal_muestra_el_plan(monkeypatch):
    import threading
    import hub.ui as H
    u = H.UI()
    e = {"id": "zz", "name": "ZZ", "repo": "a/b", "platform": "Nintendo 64"}
    monkeypatch.setattr(B, "plan_for", lambda *a, **k: plan())
    monkeypatch.setattr(threading, "Thread", type("T", (), {"__init__": lambda s, target, daemon=None: setattr(s, "t", target), "start": lambda s: s.t()}))
    u.build_plan(e)
    assert u.modal and u.modal["kind"] == "choice" and "dnf install" in u.modal["msg"]
    assert [o[0] for o in u.modal["options"]][0] == "COMPILAR CON ESTE PLAN"
    u.running = False
