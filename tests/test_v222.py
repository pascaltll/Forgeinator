"""v2.22: las descargas del servicio de catálogo sobreviven al cierre de Hub (el servicio sigue descargando sin él)."""
import time

from hub import catalogjobs, catalogservice as cs


def _esperar(f, t=3):
    t0 = time.time()
    while time.time() - t0 < t:
        if f():
            return True
        time.sleep(0.02)
    return False


def test_se_recuerdan_y_se_retoman_al_reabrir(tmp_path, monkeypatch):
    f = tmp_path / "d" / "jobs.json"
    monkeypatch.setattr(cs, "job_status", lambda jid: {"state": "running", "progress": 0.3})
    a = catalogjobs.Jobs(every=0.01, store=f)
    a.add("J1", "juego.zip", 1000, True, "e1", "src")
    assert f.is_file()
    # Hub se cierra y se vuelve a abrir; el servicio terminó mientras tanto
    monkeypatch.setattr(cs, "job_status", lambda jid: {"state": "completed", "path": "/x/juego.zip", "progress": 1})
    hecho = []
    b = catalogjobs.Jobs(on_done=hecho.append, every=0.01, store=f)
    assert b.restore() == 1
    assert _esperar(lambda: hecho)
    j = b.list()[0]
    assert j.job_id == "J1" and j.entry_id == "e1" and j.state == "done" and j.path == "/x/juego.zip"
    # y al abrir otra vez, ya procesada, no se vuelve a notificar
    c = catalogjobs.Jobs(on_done=hecho.append, every=0.01, store=f)
    assert c.restore() == 0 and c.list()[0].state == "done" and len(hecho) == 1


def test_terminada_sin_procesar_se_procesa_al_volver(tmp_path, monkeypatch):
    f = tmp_path / "jobs.json"
    a = catalogjobs.Jobs(store=f)
    j = a.add("J2", "x.iso", 10, True, "e2", "s")
    j.state, j.path = "done", "/x.iso"      # terminó pero Hub murió antes de procesarla (notified=False)
    a._save()
    monkeypatch.setattr(cs, "job_status", lambda jid: {"state": "completed", "path": "/x.iso"})
    hecho = []
    b = catalogjobs.Jobs(on_done=hecho.append, every=0.01, store=f)
    assert b.restore() == 1 and _esperar(lambda: hecho)


def test_archivo_roto_o_ausente_no_rompe(tmp_path):
    f = tmp_path / "jobs.json"
    assert catalogjobs.Jobs(store=f).restore() == 0
    f.write_text("{no json")
    assert catalogjobs.Jobs(store=f).restore() == 0
    f.write_text('[{"sin":"job_id"}, 5]')
    assert catalogjobs.Jobs(store=f).restore() == 0
