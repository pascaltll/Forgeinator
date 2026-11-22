"""v2.81: cancelar de verdad (mata el grupo de procesos), exportar diagnóstico, herramientas del contenedor, versiones por sistema y carpeta de Wine propios."""
import os
import subprocess
import time
from pathlib import Path

from hub import build, cmdjob, config, diag, history, osver, ownwine

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


def _vivos(marca):
    r = subprocess.run(["pgrep", "-f", marca], capture_output=True, text=True)
    return [x for x in r.stdout.split() if x]


def test_cancelar_cmdjob_mata_los_hijos_y_pasa_a_cancelado(tmp_path):
    marca = "sleep 67"
    job = cmdjob.CmdJob("PRUEBA", "x", [("largo", ["sh", "-c", f"{marca} & {marca}; wait"])])
    job.start()
    t0 = time.time()
    while job.state != "running" and time.time() - t0 < 3:
        time.sleep(0.02)
    time.sleep(0.4)
    assert _vivos(marca)
    job.cancel()
    assert job.state == "error" and job.stage == "Cancelado"        # al instante, sin esperar a la tubería
    t0 = time.time()
    while _vivos(marca) and time.time() - t0 < 6:
        time.sleep(0.1)
    assert not _vivos(marca)


def test_cancelar_buildjob_pasa_a_cancelled():
    j = build.BuildJob({"id": "z", "name": "Z", "repo": "o/r"}, "", "", 1)
    j.state = "running"
    import threading
    th = threading.Thread(target=lambda: j.sh(["sh", "-c", "sleep 68 & sleep 68; wait"]), daemon=True)
    th.start()
    time.sleep(0.4)
    j.cancel()
    th.join(6)
    assert j.state == "cancelled" and not th.is_alive()
    t0 = time.time()
    while _vivos("sleep 68") and time.time() - t0 < 6:
        time.sleep(0.1)
    assert not _vivos("sleep 68")


def test_diag_reune_y_tapa_secretos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "launcher")
    monkeypatch.setattr(Path, "home", classmethod(lambda c: tmp_path))
    (tmp_path / "launcher" / "games").mkdir(parents=True)
    (tmp_path / "launcher" / "games" / "gta.toml").write_text('id = "gta"\nsgdb_key = abc123SECRETO\n')
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "hub.log").write_text("[jugar] gta: lanzado\notro\n[trabajo] COMPILAR · fallo\ntoken=ghp_XXXX gta\n")
    history.record("gta", "jugar", False, "Proton abortó", snap={"layout": "windows", "runner": "proton", "proton": "UMU-Proton-10", "version": "v0.2.4"})
    monkeypatch.setattr(osver, "root_of", lambda lid: None)
    p = diag.build("gta", "GTA", "gta", "v0.2.4")
    t = p.read_text()
    assert p.name == "diag-gta.md" and "Proton abortó" in t and "[trabajo] COMPILAR" in t
    assert "abc123SECRETO" not in t and "ghp_XXXX" not in t and "***" in t


def test_versiones_por_sistema(tmp_path, monkeypatch):
    r = tmp_path / "g"
    (r / "linux").mkdir(parents=True)
    (r / "windows").mkdir()
    (r / "linux" / ".release_version").write_text("v0.3.0")
    (r / "windows" / ".release_version").write_text("v0.2.4")
    monkeypatch.setattr(osver, "root_of", lambda lid: r)
    assert osver.versions("g") == {"Linux": "v0.3.0", "Windows": "v0.2.4"}
    monkeypatch.setattr(osver, "root_of", lambda lid: None)
    assert osver.versions("g") == {}


def test_lista_de_wines_propios(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda c: tmp_path))
    monkeypatch.setattr(ownwine, "WINES_HOME", tmp_path / "wines")
    for rel in ("wines/wine-11.21/bin/wine", "wines/ge-9/files/bin/wine", "wine-10.0/loader/wine"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True)
        f.write_text("#!/bin/sh\n")
        f.chmod(0o755)
    (tmp_path / "wines" / "vacio").mkdir()
    n = [x[0] for x in ownwine.list_wines()]
    assert n == ["ge-9", "wine-11.21", "wine-10.0"] and "vacio" not in n


def test_comando_en_contenedor_crea_trabajo_cancelable(ui, H, monkeypatch):
    e = {"id": "vcs-z", "name": "VCS Z", "repo": "o/r", "folder": "vcs-z"}
    monkeypatch.setattr(ui, "inst", lambda e: {"launcher_id": e["id"], "installed": True})
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "hub-vcs")
    monkeypatch.setattr(H.osver, "folders", lambda lid: {"dir": "/tmp"})
    cap = {}
    monkeypatch.setattr(ui, "osk", lambda title, cb, text="", hint="": cap.update(cb=cb, title=title))
    monkeypatch.setattr(H.cmdjob.CmdJob, "start", lambda self, done=None: None)
    n0 = len(ui.builds)
    ui.container_command(e)
    cap["cb"]("sudo dnf install -y clang")
    j = ui.builds[-1]
    assert len(ui.builds) == n0 + 1 and j.label == "COMANDO EN CONTENEDOR"
    argv = j.steps[0][1]
    assert argv[:3] == ["distrobox", "enter", "hub-vcs"] and "sudo dnf install -y clang" in argv[-1]


def test_probar_contenedor_muestra_resultado(ui, H, monkeypatch):
    e = {"id": "vcs-z", "name": "VCS Z", "repo": "o/r", "folder": "vcs-z"}
    monkeypatch.setattr(ui, "inst", lambda e: {"launcher_id": e["id"], "installed": True})
    monkeypatch.setattr(H.osver, "container_of", lambda lid: "hub-vcs")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="DENTRO DE UN CONTENEDOR: sí\nsudo sin clave: sí", stderr=""))
    ui.test_container(e)
    t0 = time.time()
    while time.time() - t0 < 3 and not (ui.modal and ui.modal.get("kind") == "log"):
        while ui._rcp_q:
            ui._rcp_q.pop(0)()
        time.sleep(0.02)
    assert ui.modal and ui.modal["kind"] == "log" and "DENTRO DE UN CONTENEDOR: sí" in "\n".join(ui.modal["job"].log)
    assert history.rows("vcs-z")[-1]["event"] == "contenedor"
