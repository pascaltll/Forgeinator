"""v2.10: reinicio tras actualizar dentro del propio wrapper; archivos .py vacíos detectados al arrancar."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import HUB_SRC as SRC  # noqa: E402  (src/ en desarrollo, la raíz en el repositorio)


def _env(tmp_path, **x):
    py = str(Path(sys.executable).parent)
    e = {"PATH": f"{py}:/usr/bin:/bin", "HOME": str(tmp_path), "HUB_NOUPDATE": "1", "WAYLAND_DISPLAY": "w-1", "PYTHONUSERBASE": os.environ.get("PYTHONUSERBASE", "")}
    e.update(x)
    return e


def _arbol(tmp_path, main):
    d = tmp_path / "h"
    (d / "bin").mkdir(parents=True)
    (d / "hub").mkdir()
    shutil.copy(SRC / "bin" / "hub", d / "bin" / "hub")
    (d / "main.py").write_text(main)
    return d


def test_restart_en_wrapper_deja_marca(tmp_path, monkeypatch):
    from hub import selfupdate, config
    monkeypatch.setattr(selfupdate, "ROOT", tmp_path)
    monkeypatch.setattr(config, "STATE", tmp_path / "data")       # v3.15: la marca va en los registros del canal (instalación antigua: data/)
    monkeypatch.setenv("HUB_WRAPPER", "1")
    selfupdate.restart()
    assert (tmp_path / "data" / "restart.flag").exists()


def test_wrapper_relanza_en_el_mismo_proceso(tmp_path):
    cuenta = tmp_path / "n"
    main = f"""import os, pathlib
n = pathlib.Path({str(cuenta)!r})
k = int(n.read_text()) + 1 if n.exists() else 1
n.write_text(str(k))
if k == 1:
    assert os.environ.get('HUB_WRAPPER') == '1'
    (pathlib.Path(__file__).parent / 'data' / 'restart.flag').write_text('1')
"""
    d = _arbol(tmp_path, main)
    r = subprocess.run(["bash", str(d / "bin" / "hub")], env=_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert cuenta.read_text() == "2", r.stdout + r.stderr
    assert "reinicio tras actualizar" in (d / "data" / "hub.log").read_text()


def test_wrapper_avisa_de_py_vacios(tmp_path):
    d = _arbol(tmp_path, "pass\n")
    (d / "hub" / "downloads.py").write_text("")
    subprocess.run(["bash", str(d / "bin" / "hub")], env=_env(tmp_path), capture_output=True, text=True, timeout=120)
    log = (d / "data" / "hub.log").read_text()
    assert "archivos .py vacíos (downloads.py" in log


def test_init_vacio_es_normal_y_no_dispara_reinstalacion(tmp_path):
    d = _arbol(tmp_path, "pass\n")
    (d / "hub" / "__init__.py").write_text("")
    subprocess.run(["bash", str(d / "bin" / "hub")], env=_env(tmp_path), capture_output=True, text=True, timeout=120)
    assert "vacíos" not in (d / "data" / "hub.log").read_text()
