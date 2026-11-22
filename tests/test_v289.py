import re
from pathlib import Path
from conftest import HUB_SRC  # noqa: E402
SRC = HUB_SRC / "hub" / "ui_detail.py"
def test_pliegues_y_nombres():
    s = SRC.read_text()
    assert "def fold_row" in s and 'fold_row(e, "ver"' in s and 'fold_row(e, "winexe"' in s
    assert "COMPILAR AQUÍ" not in s and "PLAN DE COMPILACIÓN (LEE" not in s
    assert "abierto" in s and "cerrado" in s
