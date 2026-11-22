"""v2.06: bin/hub desde una terminal sin pantalla hereda la del Hub abierto; los paneles suavizados cuestan una copia por panel."""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import HUB_SRC  # noqa: E402
HUB = HUB_SRC / "bin" / "hub"


def _arbol(tmp_path):
    d = tmp_path / "h"
    (d / "bin").mkdir(parents=True)
    shutil.copy(HUB, d / "bin" / "hub")
    (d / "main.py").write_text("import os\nopen(os.environ['SALIDA'], 'w').write(f\"{os.environ.get('WAYLAND_DISPLAY','-')}|{os.environ.get('XDG_RUNTIME_DIR','-')}|{os.environ.get('DISPLAY','-')}\")\n")
    return d


def _entorno(tmp_path, **extra):
    py = str(Path(sys.executable).parent)
    e = {"PATH": f"{py}:/usr/bin:/bin", "HOME": str(tmp_path), "HUB_NOUPDATE": "1", "SALIDA": str(tmp_path / "salida.txt"),
         "PYTHONUSERBASE": os.environ.get("PYTHONUSERBASE", "")}
    e.update(extra)
    return e


@pytest.mark.skipif(not shutil.which("pgrep"), reason="necesita pgrep")
def test_sin_pantalla_en_la_terminal_usa_la_del_hub_abierto(tmp_path):
    d = _arbol(tmp_path)
    viejo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", str(d / "main.py")],
                             env={"PATH": "/usr/bin:/bin", "WAYLAND_DISPLAY": "wayland-9", "XDG_RUNTIME_DIR": "/run/user/1234", "DISPLAY": ":7"})
    try:
        time.sleep(0.3)
        r = subprocess.run(["bash", str(d / "bin" / "hub")], env=_entorno(tmp_path), capture_output=True, text=True, timeout=60)
        assert (tmp_path / "salida.txt").read_text() == "wayland-9|/run/user/1234|:7", r.stdout + r.stderr
        assert "uso la del Hub abierto" in (d / "data" / "hub.log").read_text()
        assert viejo.wait(timeout=5) != 0, "el Hub anterior se cerró"
    finally:
        viejo.kill()


def test_con_pantalla_propia_no_se_cambia(tmp_path):
    d = _arbol(tmp_path)
    r = subprocess.run(["bash", str(d / "bin" / "hub")], env=_entorno(tmp_path, WAYLAND_DISPLAY="wayland-1", XDG_RUNTIME_DIR="/run/user/1000"),
                       capture_output=True, text=True, timeout=60)
    assert (tmp_path / "salida.txt").read_text() == "wayland-1|/run/user/1000|-"
    assert "AVISO" not in (d / "data" / "hub.log").read_text()


def test_sin_pantalla_y_sin_hub_abierto_avisa(tmp_path):
    d = _arbol(tmp_path)
    r = subprocess.run(["bash", str(d / "bin" / "hub")], env=_entorno(tmp_path), capture_output=True, text=True, timeout=60)
    assert "AVISO: no hay pantalla" in (d / "data" / "hub.log").read_text()


@pytest.mark.ui
def test_los_paneles_suavizados_son_una_copia_cacheada():
    pygame = pytest.importorskip("pygame")
    import hub.ui as H
    u = H.UI()
    u.set_look(theme="prototipo", fx="glass")
    u.screen.fill((13, 16, 20))
    rects = [(40 + (i % 6) * 190, 40 + (i // 6) * 120, 180, 110) for i in range(18)] + [(20 + i * 7, 600, 160, 60) for i in range(40)]
    for r in rects:
        u.rr(r, H.PANEL, 20)
    n = len(u._aa_c)
    t = time.perf_counter()
    for _ in range(100):
        for r in rects:
            u.rr(r, H.PANEL, 20)
    ms = (time.perf_counter() - t) / 100 * 1000
    assert len(u._aa_c) == n, "no se vuelven a preparar"
    assert ms < 2.0, f"58 paneles tardan {ms:.2f} ms por fotograma (antes del arreglo: 3,6 ms)"
    esq = {tuple(u.screen.get_at((x, y)))[:3] for x in range(40, 52) for y in range(40, 52)}
    assert len(esq) > 5, "las esquinas siguen suaves"
    assert tuple(u.screen.get_at((120, 90)))[:3] == tuple(H.PANEL)
