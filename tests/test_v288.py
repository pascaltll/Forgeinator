"""v2.88: visor de registros con COPIAR / GUARDAR / ruido / principio-final, y `bin/hub-logs --trabajo` desde la terminal."""
import os
import subprocess
import sys
from pathlib import Path

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from conftest import shot

from conftest import HUB_SRC as SRC  # noqa: E402


def test_logview_quita_colores_y_ruido():
    from hub import logview
    raw = ["\x1b[32m[ OK ]\x1b[0m listo", "pid 12 != 10, skipping destruction (fork without exec?)",
           "ERROR: ld.so: object 'x' from LD_PRELOAD cannot be preloaded (wrong ELF class)", "[tecla] KEYDOWN a", "[rendimiento] fotograma lento", "Failed to download packages"]
    assert logview.lines(raw, True) == ["[ OK ] listo", "Failed to download packages"]
    assert len(logview.lines(raw, False)) == 6 and logview.hidden(raw) == 4
    assert logview.trabajo(["[trabajo] COMANDO · hola", "[tecla] x", "otra"], 5) == ["COMANDO · hola"]


def _abrir_log(ui, n=300):
    log = [f"línea {i}" for i in range(n)] + ["pid 1 != 2, skipping destruction (fork without exec?)", "\x1b[32m[ OK ]\x1b[0m"]
    ui.show_log(ui._TextLog("Prueba de registro", Path("/tmp/x.log"), "\n".join(log)))
    run(ui, 4)


def test_visor_tiene_barra_y_sigue_funcionando(ui, H, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    _abrir_log(ui)
    ks = {str(w.key) for w in ui.widgets}
    assert {"lg:x", "lg:copy", "lg:save", "lg:noise", "lg:top", "lg:end"} <= ks
    shot(ui, "v288-visor-registro.png")
    # GUARDAR: registro completo, sin códigos de color
    ui.log_save()
    f = next(tmp_path.glob("hub-log-*.txt"))
    t = f.read_text()
    assert "skipping destruction" in t and "\x1b" not in t and "línea 299" in t
    # COPIAR: lo que se ve (sin ruido)
    puestos = []
    monkeypatch.setattr(H.pygame.scrap if hasattr(H, "pygame") else __import__("pygame").scrap, "put_text", lambda s: puestos.append(s))
    ui.log_copy()
    assert puestos and "skipping destruction" not in puestos[0]
    # ruido visible → COPIAR lo incluye
    ui.log_noise()
    ui.log_copy()
    assert "skipping destruction" in puestos[-1]
    # saltar al principio / al final
    ui.log_jump(False)
    assert ui.views["log"].off == 0
    ui.log_jump(True)
    assert ui.modal["follow"] is True


def test_hub_logs_trabajo_desde_la_terminal(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "hub.log").write_text("\n".join(["[tecla] KEYDOWN a", "[trabajo] COMANDO EN CONTENEDOR · \x1b[32mhola\x1b[0m",
                                          "[trabajo] COMANDO EN CONTENEDOR · pid 1 != 2, skipping destruction (fork without exec?)",
                                          "[trabajo] COMANDO EN CONTENEDOR · (código 1)"]) + "\n", encoding="utf-8")
    env = dict(os.environ, HUB_DATA=str(d), HUB_DIR=str(SRC), PYTHONPATH=str(SRC))
    r = subprocess.run([sys.executable, str(SRC / "bin" / "hub-logs"), "--trabajo", "10"], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["COMANDO EN CONTENEDOR · hola", "COMANDO EN CONTENEDOR · (código 1)"]
    r2 = subprocess.run([sys.executable, str(SRC / "bin" / "hub-logs"), "--trabajo", "--ruido"], capture_output=True, text=True, env=env, timeout=60)
    assert "skipping destruction" in r2.stdout
