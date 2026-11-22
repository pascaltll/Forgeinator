"""Robustez: ningún OSError crudo debe matar hilos en segundo plano (arranque del daemon, poller, mkdir de descargas)."""
import subprocess

import pytest

from hub import catalogjobs as cj
from hub import catalogservice as cs
from _catjobs_helpers import until


def test_popen_que_falla_se_convierte_en_transporterror(cs, tmp_path, monkeypatch):
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "service.py").write_text("")
    (tmp_path / "token").write_text("T")

    def boom(*a, **k):
        raise PermissionError("sin permiso")
    monkeypatch.setattr(subprocess, "Popen", boom)
    with pytest.raises(cs.TransportError, match="no pude arrancar el servicio"):
        cs.search("x")


def test_autostart_nunca_lanza(cs, tmp_path, monkeypatch):
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "service.py").write_text("")
    monkeypatch.setattr(cs, "ensure_running", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    ok, msg = cs.autostart()
    assert ok is False and "OSError" in msg


def test_poller_sobrevive_a_excepcion_inesperada(monkeypatch, capsys):
    def raro(jid):
        raise OSError("crudo")
    monkeypatch.setattr(cs, "job_status", raro)
    jobs = cj.Jobs(every=0.01)
    j = jobs.add("job_1", "a.bin")
    assert until(lambda: j.state == "error")
    assert "OSError" in j.error
    assert "job_status inesperado" in capsys.readouterr().out
