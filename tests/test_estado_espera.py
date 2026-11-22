"""Estado «waiting_interaction» del daemon de catálogo: el motor se detiene esperando al usuario y la descarga se reanuda sola."""
import time

import pytest

from hub import catalogjobs as cj


class _CS:
    """job_status guionizado (sustituye a catalogservice.job_status)."""
    def __init__(self, script):
        self.script, self.n = script, 0

    def __call__(self, job_id):
        st = self.script[min(self.n, len(self.script) - 1)]
        self.n += 1
        return st


@pytest.fixture()
def jobs(monkeypatch):
    avisos, hechos = [], []
    j = cj.Jobs(on_done=hechos.append, every=0.01, on_wait=avisos.append)
    j.avisos, j.hechos = avisos, hechos
    return j


def _correr(jobs, monkeypatch, script, n=8):
    monkeypatch.setattr(cj.cs, "job_status", _CS(script))
    job = jobs.add("job_1", "Juego", 100)
    for _ in range(n):
        jobs.poll(job)
    return job


def test_el_estado_se_traduce_y_guarda_el_mensaje(jobs, monkeypatch):
    j = _correr(jobs, monkeypatch, [{"state": "waiting_interaction", "message": "Resuelve el captcha en la ventana", "progress": 0.3}])
    assert j.state == "waiting" and j.meta["message"] == "Resuelve el captcha en la ventana" and j.meta["phase"] == "Esperando tu intervención"
    assert j.speed == 0.0 and abs(j.progress - 0.3) < 1e-9


def test_avisa_una_sola_vez_por_parada_y_otra_si_vuelve_a_parar(jobs, monkeypatch):
    script = [{"state": "waiting_interaction", "message": "a"}] * 3 + [{"state": "running", "progress": 0.5}] + [{"state": "waiting_interaction", "message": "b"}] * 3
    j = _correr(jobs, monkeypatch, script, n=7)
    assert [x.meta["message"] for x in jobs.avisos] == ["a", "b"] or len(jobs.avisos) == 2
    assert j.state == "waiting"


def test_se_reanuda_y_termina(jobs, monkeypatch, tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"x")
    script = [{"state": "waiting_interaction", "message": "m"}, {"state": "running", "progress": 0.6}, {"state": "completed", "path": str(f), "progress": 1}]
    j = _correr(jobs, monkeypatch, script, n=3)
    assert j.state == "done" and j.path == str(f) and jobs.hechos == [j]


def test_el_hilo_sigue_consultando_mientras_espera(jobs, monkeypatch):
    monkeypatch.setattr(cj.cs, "job_status", _CS([{"state": "waiting_interaction", "message": "m"}] * 5 + [{"state": "failed", "error": "x"}]))
    j = jobs.add("job_2", "J", 10)
    for _ in range(100):
        if j.state == "error":
            break
        time.sleep(0.02)
    assert j.state == "error", "una descarga en espera sigue en la lista de vivas y se consulta"


def test_estado_desconocido_no_rompe(jobs, monkeypatch):
    j = _correr(jobs, monkeypatch, [{"state": "algo_nuevo"}], n=2)
    assert j.state == "queued"


@pytest.mark.ui
def test_la_tarjeta_y_la_insignia_reflejan_la_espera(monkeypatch):
    import hub.ui as H
    u = H.UI()
    try:
        j = u.cjobs.add("job_9", "Silent Hill", 0)
        j.state, j.meta["message"] = "waiting", "Pulsa el botón en la página"
        u.go_tab("downloads")
        for _ in range(4):
            u.frame()
        keys = {w.key for w in u.widgets}
        assert f"dl:{j.id}" in keys
        u._cat_wait(j)
        assert "Pulsa el botón" in u.toast_msg
    finally:
        u.cjobs.remove(j.id)
        u.running = False
