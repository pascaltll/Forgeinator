"""v2.79: historial por juego (foto del entorno al jugar/instalar/compilar) y causa visible de las miniaturas de arte."""
import json

import pytest

from hub import buildlog, config, history, launchlog


@pytest.fixture
def datos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "launcher")
    monkeypatch.setattr(history, "containers", lambda max_age=120.0: ["hub-gta-vcs (fedora:41)"])
    return tmp_path


def _env(**k):
    e = {"hub": "2.79", "version": "v0.2.4", "layout": "linux", "runner": "", "proton": "", "container": "", "containers": [], "system": "Bazzite", "kernel": "6"}
    e.update(k)
    return e


def test_record_guarda_foto_y_poda(datos):
    r = history.record("gta", "jugar", True, "ok", snap=_env())
    assert r["env"]["version"] == "v0.2.4"
    for i in range(history.KEEP + 20):
        history.record("gta", "jugar", None, str(i), snap=_env())
    assert len(history.rows("gta")) == history.KEEP


def test_matriz_agrupa_por_configuracion(datos):
    history.record("gta", "jugar", True, snap=_env(layout="linux"))
    history.record("gta", "jugar", True, snap=_env(layout="linux"))
    history.record("gta", "jugar", False, "Proton abortó", snap=_env(layout="windows", runner="proton", proton="UMU-Proton-10"))
    history.record("gta", "jugar", None, "lanzado", snap=_env(containers=["hub-gta-vcs (fedora:41)"]))   # pendiente: no cuenta
    m = {d["config"]: d for d in history.matrix("gta")}
    assert m["linux · v0.2.4"]["ok"] == 2 and m["linux · v0.2.4"]["fail"] == 0
    w = m["windows · proton · UMU-Proton-10 · v0.2.4"]
    assert w["fail"] == 1 and "abortó" in w["error"]
    t = history.text("gta", "GTA")
    assert "✓" in t and "✗" in t and "hub-gta-vcs (fedora:41)" in t


def test_contenedor_en_la_configuracion(datos):
    history.record("lcs", "compilar", False, "falta cmake", snap=_env(container="hub-lcs"))
    assert "contenedor hub-lcs" in history.matrix("lcs")[0]["config"]


def test_buildlog_alimenta_el_historial(datos):
    buildlog.record({"id": "lcs", "name": "LCS"}, "hub-lcs", "cmake --build .", 4, False, 12.0, "cmake: command not found")
    r = history.rows("lcs")[-1]
    assert r["event"] == "compilar" and r["ok"] is False and "cmake" in r["detail"] and r["container"] == "hub-lcs"


def test_informe_de_arranque_fallido_va_al_historial(datos, monkeypatch):
    out = datos / "o.out"
    out.write_text("linea normal\nerror while loading shared libraries: libfoo.so: cannot open\n")
    monkeypatch.setattr(launchlog, "diagnose", lambda lid: ["- ok"])
    launchlog.report("gta", "GTA", 127, 1.5, out)
    r = history.rows("gta")[-1]
    assert r["event"] == "jugar" and r["ok"] is False and "libfoo" in r["detail"] and r["rc"] == 127


def test_first_error_ignora_ruido_de_steam():
    t = "ATTENTION: default value of option force_s3tc_enable overridden by environment\nfoo\nSegmentation fault (core dumped)\n"
    assert "Segmentation" in history.first_error(t)
    assert history.first_error("ATTENTION: default value of option x overridden by environment") == ""


def test_snapshot_nunca_lanza(datos):
    s = history.snapshot("no-existe", "v1")
    assert s["version"] == "v1" and s["containers"] == ["hub-gta-vcs (fedora:41)"]
