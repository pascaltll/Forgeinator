"""v2.11: Hub no depende de MiniTube."""
import re
from pathlib import Path

from conftest import HUB_SRC as SRC  # noqa: E402


def test_no_queda_codigo_de_minitube():
    for p in list((SRC / "hub").glob("*.py")) + list((SRC / "bin").glob("*")) + list((SRC / "browser").glob("*.py")):
        if p.is_file():
            txt = "\n".join(l for l in p.read_text(errors="ignore").splitlines() if "ajuste antiguo" not in l)   # migración del ajuste viejo
            assert not re.search(r"minitube|ytmini", txt, re.I), p


def test_ajuste_minitube_antiguo_pasa_a_automatico(monkeypatch):
    from hub import ui
    o = type("O", (), {"cfg": {"browser": "minitube"}, "brow_t": 0, "_hb_ok": False, "toast": lambda s, m: None})()
    monkeypatch.setattr(ui.config, "save_settings", lambda c: None)
    monkeypatch.setattr(ui.subprocess, "Popen", lambda *a, **k: None)
    ui.UI.open_url(o, "https://github.com/")
    assert o.cfg["browser"] == "auto"
