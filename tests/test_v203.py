"""v2.03: una batería que da el mismo resultado en tu Ally y aquí.
- Las pruebas usan una casa temporal: no leen tus ROMs, Descargas ni Steam, ni escriben en tu ~/.config.
- Lo que cambia hardware real (el TDP) solo corre si lo pides, y escribe el perfil de Hub, que es el que Panel aplica.
- bin/hub-tests busca solo un Python que sirva y no se corta si un archivo de pruebas no se puede importar."""
import ast
import importlib.machinery
import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import conftest
from conftest import HUB_SRC

HERE = Path(__file__).resolve().parent
LAUNCH = HUB_SRC / "bin" / "hub-tests"


# ── aislamiento ─────────────────────────────────────────────────────
def test_las_pruebas_usan_una_casa_temporal():
    assert Path.home() == conftest.FAKE_HOME
    assert conftest.FAKE_HOME != conftest.REAL_HOME
    assert str(Path("~/Downloads").expanduser()).startswith(str(conftest.FAKE_HOME))
    assert os.environ["XDG_CONFIG_HOME"].startswith(str(conftest.FAKE_HOME))


def test_la_biblioteca_es_la_de_prueba_y_no_la_tuya():
    from hub import roms
    assert roms.roots({}) == [conftest.FAKE_ROMS]
    n = sum(1 for _ in conftest.FAKE_ROMS.rglob("*") if _.is_file())
    assert n == 150                       # más de los 60 que caben: «MOSTRAR MÁS» sale siempre, en cualquier equipo


def test_no_se_ven_tus_accesos_de_steam():
    from hub import steamlib
    assert all(str(f).startswith(str(conftest.FAKE_HOME)) for f in steamlib.shortcut_files())


def test_las_rutas_de_las_pruebas_live_siguen_siendo_las_reales():
    assert str(conftest.REAL["TOKEN_FILE"]).startswith(str(conftest.REAL_HOME))


# ── lo que toca hardware real tiene que pedirse ─────────────────────
PELIGROSO = ("set_watts", "set_tdp_watts")


def _llama(fn):
    """¿Llama a algo que cambia el TDP? tdpctl.set_watts(...) o tdpctl.call("set_tdp_watts", ...)."""
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and f.attr in PELIGROSO:
            return True
        if isinstance(f, ast.Attribute) and f.attr == "call" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value in PELIGROSO:
            return True
    return False


def _protegida(fn):
    for d in fn.decorator_list:
        src = ast.unparse(d)
        if "skipif" in src:
            return True
    return False


def test_ninguna_prueba_cambia_el_tdp_sin_pedirlo():
    """En v2.01 el «solo si HUB_TDP_BENCH» quedó en una función auxiliar y la prueba corría siempre. Esto lo habría pillado."""
    sueltas = []
    for f in sorted(HERE.glob("test_*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_") and _llama(fn) and not _protegida(fn):
                if "steam_falso" in fn.name or "sin_steam" in fn.name:     # contra un Steam de mentira: no toca nada
                    continue
                sueltas.append(f"{f.name}::{fn.name}")
    assert not sueltas, f"cambian el TDP de verdad sin skipif: {sueltas}"


def test_el_bench_esta_saltado_si_no_se_pide():
    import test_tdp_bench as tb
    marks = [m for m in getattr(tb.test_rendimiento_por_tdp, "pytestmark", []) if m.name == "skipif"]
    assert marks, "la prueba de TDP necesita su skipif"
    if not os.environ.get("HUB_TDP_BENCH"):
        assert marks[0].args[0] is True


def test_el_bench_escribe_el_perfil_de_hub():
    """Panel aplica el perfil del contexto (ns:hub tiene el suyo); escribir el global no cambia el límite."""
    src = (HUB_SRC / "hub" / "tdpctl.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "set_watts")
    code = ast.unparse(fn)
    assert "'game'" in code and "'global'" not in code


# ── bin/hub-tests: qué Python usa ──────────────────────────────────
def _launcher():
    loader = importlib.machinery.SourceFileLoader("hub_tests_cli", str(LAUNCH))
    spec = importlib.util.spec_from_loader("hub_tests_cli", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def _falso(tmp_path, nombre, version, falta=""):
    p = tmp_path / nombre
    p.write_text(f"#!/bin/sh\necho {version}\necho {falta}\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def test_python_viejo_o_sin_pygame_no_vale(tmp_path):
    m = _launcher()
    viejo = m.probe(_falso(tmp_path, "py310", "3.10.14"))
    assert not viejo["ok"] and viejo["missing"][0].startswith("Python 3.10")
    sin = m.probe(_falso(tmp_path, "py313", "3.13.1", "pygame"))
    assert not sin["ok"] and sin["missing"] == ["pygame"]
    bueno = m.probe(_falso(tmp_path, "pyok", "3.12.2"))
    assert bueno["ok"]


def test_elige_el_primero_que_sirve_y_explica_los_demas(tmp_path, monkeypatch):
    m = _launcher()
    lista = [_falso(tmp_path, "a", "3.10.1"), _falso(tmp_path, "b", "3.13.0", "pygame"), _falso(tmp_path, "c", "3.12.0")]
    monkeypatch.setattr(m, "candidates", lambda: lista)
    elegido, probados = m.choose()
    assert elegido["py"] == lista[2]
    monkeypatch.setattr(m, "candidates", lambda: lista[:2])
    elegido, probados = m.choose()
    assert elegido is None
    txt = m.explain(probados)
    assert "Python 3.10" in txt and f"{lista[1]} -m pip install pygame-ce" in txt


def test_un_archivo_que_no_importa_no_corta_la_bateria(tmp_path):
    h = tmp_path / "h"
    (h / "bin").mkdir(parents=True)
    (h / "bin" / "hub-tests").write_text(LAUNCH.read_text())
    (h / "tests").mkdir()
    (h / "tests" / "conftest.py").write_text("")
    (h / "tests" / "test_roto.py").write_text("import modulo_que_no_existe\n")
    (h / "tests" / "test_bien.py").write_text("def test_ok():\n    assert True\n")
    r = subprocess.run([sys.executable, str(h / "bin" / "hub-tests")], env={"HUB_DIR": str(h), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "PYTHONUSERBASE": os.environ.get("PYTHONUSERBASE", "")},
                       capture_output=True, text=True, timeout=120)
    inf = (h / "data" / "tests" / "informe.md").read_text()
    assert "1 passed" in inf and "test_roto" in inf, inf
    assert "Python" in inf.split("## Fallos")[0]          # la cabecera dice con qué Python se ejecutó
