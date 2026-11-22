"""#cancelar: job_cancel se envía en cualquier estado (también esperando); un sondeo en vuelo no lo resucita; sin pausa/reanudar."""
from _catjobs_helpers import start_job, until
from hub import catalogjobs as cj


def test_cancelar_en_espera_manda_job_cancel(daemon, tmp_path):
    daemon.job_script = [{"state": "waiting_interaction", "message": "m"}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "waiting")
    jobs.cancel(j.id)
    assert j.state == "cancelled"
    assert daemon.count("job_cancel") == 1 and daemon.calls[-1][0] in ("job_cancel", "job_status")


def test_cancelado_no_vuelve_a_activo_ni_a_error(daemon, tmp_path):
    daemon.job_script = [{"state": "running", "progress": .2}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "active")
    jobs.cancel(j.id)
    jobs.poll(j)     # respuesta tardía: el daemon aún diría "failed: cancelado" o "running"
    assert j.state == "cancelled" and ev["done"] == []


def test_no_hay_polling_tras_cancelar(daemon, tmp_path):
    daemon.job_script = [{"state": "running"}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "active")
    jobs.cancel(j.id)
    n = daemon.count("job_status")
    import time; time.sleep(0.3)
    assert daemon.count("job_status") <= n + 1


def test_cancelar_con_daemon_caido_marca_cancelado(daemon, tmp_path):
    jobs, j, ev = start_job(daemon, tmp_path)
    daemon.stop()
    jobs.cancel(j.id)
    assert j.state == "cancelled"
