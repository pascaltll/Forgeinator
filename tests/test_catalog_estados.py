"""#estados: queued/running/waiting_interaction/completed/failed pintados bien; aviso de espera UNA vez por parada."""
from _catjobs_helpers import start_job, until

W = {"state": "waiting_interaction", "phase": "waiting", "progress": 0.3, "bytes_per_s": 999, "message": "Resuelve el captcha <b>ya</b>"}
R = {"state": "running", "phase": "downloading", "progress": 0.5, "bytes_per_s": 1000}


def test_waiting_avisa_una_sola_vez_aunque_siga_esperando(daemon, tmp_path):
    daemon.job_script = [{"state": "queued"}, R, W, W, W, W, W, W]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "waiting")
    assert until(lambda: daemon.count("job_status") >= 8)
    assert len(ev["wait"]) == 1
    assert j.speed == 0 and j.meta["phase"] == "Esperando tu intervención"
    assert j.meta["message"] == "Resuelve el captcha <b>ya</b>"      # opaco: tal cual, sin interpretar
    jobs.cancel(j.id)


def test_nueva_parada_vuelve_a_avisar(daemon, tmp_path):
    daemon.job_script = [W, W, R, R, W, W]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: len(ev["wait"]) == 2)
    jobs.cancel(j.id)


def test_alias_waiting_y_reanuda_sola(daemon, tmp_path):
    daemon.job_script = [dict(W, state="waiting"), R, {"state": "failed", "error": "x"}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "error")
    assert len(ev["wait"]) == 1 and j.error == "x"


def test_mensaje_ausente_no_rompe(daemon, tmp_path):
    daemon.job_script = [{"state": "waiting_interaction"}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: len(ev["wait"]) == 1)
    assert j.meta["message"] == ""
    jobs.cancel(j.id)


def test_completed_notifica_una_vez(daemon, tmp_path):
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "done")
    assert len(ev["done"]) == 1 and j.progress == 1.0
