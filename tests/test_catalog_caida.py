"""#caída: 1-2 fallos de red no matan el job; 3 seguidos lo marcan y dejan de sondear; ensure_running se intenta una vez."""
import time

from hub import catalogjobs as cj
from hub import catalogservice as cs
from _catjobs_helpers import start_job, until


def test_tres_fallos_seguidos_marcan_error_y_paran_el_sondeo(daemon, tmp_path):
    daemon.job_script = [{"state": "running", "progress": 0.1}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "active")
    daemon.stop()
    assert until(lambda: j.state == "error")
    assert "se perdió la conexión con el servicio" in j.error and j.fails == 3
    assert ev["done"] == []


def test_dos_fallos_y_vuelve_no_mata(daemon, tmp_path, monkeypatch):
    real, n = cs.job_status, [0]

    def flaky(jid):
        n[0] += 1
        if n[0] in (2, 3):
            raise cs.TransportError("simulado")
        return real(jid)
    monkeypatch.setattr(cs, "job_status", flaky)
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "done")
    assert j.error == ""


def test_job_status_usa_timeout_corto(daemon, monkeypatch):
    vistos = []
    real = cs._post
    monkeypatch.setattr(cs, "_post", lambda m, p, t: (vistos.append((m, t)), real(m, p, t))[1])
    daemon.job_script = [{"state": "running"}]
    daemon.jobs["job_1"] = {"t0": 0, "dest": "", "polls": 0}
    cs.job_status("job_1")
    assert vistos[-1] == ("job_status", 5)


def test_cada_fallo_intenta_arrancar_el_servicio_solo_una_vez(cs, monkeypatch):
    llamadas = []
    monkeypatch.setattr(cs, "ensure_running", lambda *a, **k: llamadas.append(1))
    try:
        cs.job_status("x")
    except cs.CatalogError:
        pass
    assert llamadas == [1]


def test_espera_de_arranque_por_defecto_15s():
    import inspect
    assert inspect.signature(cs.ensure_running).parameters["wait"].default >= 15
