"""v1.82: bin/hub-tests (lanzador de pruebas dentro de Hub) y el resumen que lee Avanzado."""
import os
import subprocess
import sys
from pathlib import Path

from conftest import HUB_SRC

LAUNCH = HUB_SRC / "bin" / "hub-tests"


def test_lanzador_existe_y_es_ejecutable():
    assert LAUNCH.exists()


def test_resumen_sin_ejecuciones(tmp_path, monkeypatch):
    env = {"HUB_DIR": str(tmp_path / "h"), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, str(LAUNCH), "--resumen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0 and "ejecutado" in r.stdout


def test_sin_carpeta_tests_avisa(tmp_path):
    h = tmp_path / "h"
    (h / "bin").mkdir(parents=True)
    (h / "bin" / "hub-tests").write_text(LAUNCH.read_text())
    r = subprocess.run([sys.executable, str(h / "bin" / "hub-tests")], env={"HUB_DIR": str(h), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert r.returncode == 2 and "tests/" in r.stdout


def test_ejecuta_y_escribe_informe(tmp_path):
    h = tmp_path / "h"
    (h / "bin").mkdir(parents=True)
    (h / "bin" / "hub-tests").write_text(LAUNCH.read_text())
    (h / "tests").mkdir()
    (h / "tests" / "conftest.py").write_text("")
    (h / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n\ndef test_mal():\n    assert False\n")
    r = subprocess.run([sys.executable, str(h / "bin" / "hub-tests"), "-k", "test_"], env={"HUB_DIR": str(h), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "PYTHONUSERBASE": os.environ.get("PYTHONUSERBASE", "")},
                       capture_output=True, text=True, timeout=120)
    res = (h / "data" / "tests" / "resumen.txt").read_text()
    assert r.returncode == 1 and "FALLÓ" in res and "1 failed" in res
    assert "test_mal" in (h / "data" / "tests" / "informe.md").read_text()
