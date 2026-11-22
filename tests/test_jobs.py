"""catalogjobs: parse_size, CatalogJob.apply (todas las formas de job_status) y Jobs (poll/cancel/hilo)."""
import time

import pytest

from conftest import wait_for
from hub import catalogjobs as cj
from hub import catalogservice as cs


# ── parse_size ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("txt,n", [("3.2 GB", int(3.2 * 1024 ** 3)), ("700 MB", 700 * 1024 ** 2), ("1,5 GB", int(1.5 * 1024 ** 3)),
                                   ("12 MB", 12 * 1024 ** 2), ("512 KB", 512 * 1024), ("1024", 1024), ("1 TB", 1024 ** 4),
                                   ("1 GiB", 1024 ** 3), ("600mb", 600 * 1024 ** 2), (" 2 GB ", 2 * 1024 ** 3), ("0 MB", 0),
                                   ("", 0), (None, 0), ("abc", 0), ("GB", 0), ("-3 MB", 0), ("3.2.1 GB", 0), (12345, 12345)])
def test_parse_size(txt, n):
    assert cj.parse_size(txt) == n


# ── apply ───────────────────────────────────────────────────────────────────
def job(size=1000):
    return cj.CatalogJob("j1", "Silent Hill", size=size, resumable=True, entry_id="e", source="nas")


def test_estado_inicial():
    j = job()
    assert j.id == "cat:j1" and j.state == "queued" and j.progress == 0 and j.catalog is True and j.eta() is None
    assert j.meta["title"] == "Silent Hill" and j.meta["resumable"] is True and j.meta["source"] == "nas"


@pytest.mark.parametrize("estado,esperado", [("queued", "queued"), ("running", "active"), ("completed", "done"), ("failed", "error")])
def test_mapa_de_estados(estado, esperado):
    j = job()
    j.apply({"state": estado})
    assert j.state == esperado


def test_estado_desconocido_no_cambia_el_actual():
    j = job()
    j.apply({"state": "running"})
    j.apply({"state": "paused_by_alien"})
    assert j.state == "active"


@pytest.mark.parametrize("p,esperado", [(0.5, 0.5), (-1, 0.0), (7, 1.0), ("x", 0.0), (None, 0.0), (True, 1.0)])
def test_progreso_acotado_y_robusto(p, esperado):
    j = job(size=0)
    j.apply({"state": "running", "progress": p})
    assert j.progress == pytest.approx(esperado)


def test_progreso_con_tamano_conocido():
    j = job(1000)
    j.apply({"state": "running", "progress": 0.25, "bytes_per_s": 100})
    assert j.done == 250 and j.progress == pytest.approx(0.25) and j.eta() == pytest.approx(7.5)


def test_eta_none_si_velocidad_cero_o_sin_tamano():
    j = job(1000)
    j.apply({"state": "running", "progress": 0.5, "bytes_per_s": 0})
    assert j.eta() is None
    k = job(0)
    k.apply({"state": "running", "progress": 0.5, "bytes_per_s": 500})
    assert k.eta() is None


@pytest.mark.parametrize("fase,txt", [("resolving_cdn", "Resolviendo servidor…"), ("downloading", "Descargando"), ("extracting", "extracting"), (None, "")])
def test_fases(fase, txt):
    j = job()
    j.apply({"state": "running", "phase": fase})
    assert j.meta["phase"] == txt


def test_completado_sin_sha1_crc32_ni_path():
    j = job()
    j.apply({"state": "completed", "progress": 1.0})
    assert j.state == "done" and j.path == "" and j.sha1 is None and j.crc32 is None and j.meta["phase"] == "Completa" and j.progress == 1.0


def test_completado_con_todo():
    j = job()
    j.apply({"state": "completed", "path": "/x/a.bin", "sha1": "ab" * 20, "crc32": "DEADBEEF"})
    assert (j.path, j.sha1, j.crc32) == ("/x/a.bin", "ab" * 20, "DEADBEEF")


def test_fallo_con_y_sin_mensaje():
    j = job()
    j.apply({"state": "failed", "error": "disco lleno"})
    assert j.state == "error" and j.error == "disco lleno"
    k = job()
    k.apply({"state": "failed"})
    assert "falló" in k.error


def test_bytes_per_s_none_y_estado_no_dict():
    j = job()
    j.apply({"state": "running", "bytes_per_s": None})
    assert j.speed == 0.0


# ── Jobs.poll ───────────────────────────────────────────────────────────────
class FakeCS:
    """Sustituye cs.job_status/job_cancel."""
    def __init__(self, monkeypatch):
        self.script, self.cancelled, self.cancel_error = [], [], None
        monkeypatch.setattr(cs, "job_status", self.status)
        monkeypatch.setattr(cs, "job_cancel", self.cancel)

    def status(self, jid):
        v = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(v, Exception):
            raise v
        return v

    def cancel(self, jid):
        self.cancelled.append(jid)
        if self.cancel_error:
            raise self.cancel_error


@pytest.fixture
def fcs(monkeypatch):
    return FakeCS(monkeypatch)


def test_poll_aplica_estado_y_notifica_una_sola_vez(fcs):
    hechos = []
    jobs = cj.Jobs(on_done=hechos.append)
    j = cj.CatalogJob("j1", "t")
    fcs.script = [{"state": "completed", "path": "/x"}]
    jobs.poll(j)
    jobs.poll(j)
    jobs.poll(j)
    assert j.state == "done" and hechos == [j]


def test_on_done_que_falla_no_rompe_el_poll(fcs, capsys):
    jobs = cj.Jobs(on_done=lambda j: 1 / 0)
    j = cj.CatalogJob("j1", "t")
    fcs.script = [{"state": "completed"}]
    jobs.poll(j)
    assert j.state == "done" and "on_done falló" in capsys.readouterr().out


def test_sin_on_done(fcs):
    j = cj.CatalogJob("j1", "t")
    fcs.script = [{"state": "completed"}]
    cj.Jobs().poll(j)
    assert j.notified is True


def test_dos_fallos_no_matan_el_trabajo_tres_si(fcs):
    jobs, j = cj.Jobs(), cj.CatalogJob("j1", "t")
    fcs.script = [cs.TransportError("x")]
    jobs.poll(j); jobs.poll(j)
    assert j.state == "queued" and j.fails == 2
    jobs.poll(j)
    assert j.state == "error" and "se perdió la conexión" in j.error


def test_un_exito_reinicia_el_contador_de_fallos(fcs):
    jobs, j = cj.Jobs(), cj.CatalogJob("j1", "t")
    fcs.script = [cs.TransportError("x"), cs.TransportError("x"), {"state": "running"}, cs.TransportError("x")]
    for _ in range(4):
        jobs.poll(j)
    assert j.state == "active" and j.fails == 1


def test_error_rpc_menos_2_cuenta_como_fallo(fcs):
    jobs, j = cj.Jobs(), cj.CatalogJob("j1", "t")
    fcs.script = [cs.ServiceError(-2, "no such file", None)]
    for _ in range(3):
        jobs.poll(j)
    assert j.state == "error" and "no such file" in j.error


def test_respuesta_no_dict_se_tolera(fcs):
    j = cj.CatalogJob("j1", "t")
    fcs.script = [["raro"]]
    cj.Jobs().poll(j)
    assert j.state == "queued"


# ── Jobs.add / cancel / remove / clear ──────────────────────────────────────
def test_add_list_remove_clear(fcs):
    fcs.script = [{"state": "running"}]
    jobs = cj.Jobs(every=0.02)
    a = jobs.add("a", "A")
    time.sleep(0.01)
    b = jobs.add("b", "B")
    assert [x.job_id for x in jobs.list()] == ["a", "b"]
    jobs.remove(a.id)
    assert [x.job_id for x in jobs.list()] == ["b"]
    jobs.remove("cat:no-existe")
    b.state = "done"
    jobs.clear_finished()
    assert jobs.list() == []


def test_clear_finished_respeta_los_activos(fcs):
    fcs.script = [{"state": "running"}]
    jobs = cj.Jobs(every=0.02)
    a, b, c = jobs.add("a", "A"), jobs.add("b", "B"), jobs.add("c", "C")
    a.state, b.state = "error", "cancelled"
    jobs.clear_finished()
    assert [x.job_id for x in jobs.list()] == ["c"]


def test_cancel_avisa_al_daemon(fcs):
    fcs.script = [{"state": "running"}]
    jobs = cj.Jobs(every=0.02)
    j = jobs.add("a", "A")
    jobs.cancel(j.id)
    assert fcs.cancelled == ["a"] and j.state == "cancelled"


def test_cancel_marca_cancelado_aunque_el_daemon_falle(fcs, capsys):
    fcs.script = [{"state": "running"}]
    fcs.cancel_error = cs.TransportError("caído")
    jobs = cj.Jobs(every=0.02)
    j = jobs.add("a", "A")
    jobs.cancel(j.id)
    assert j.state == "cancelled" and "job_cancel falló" in capsys.readouterr().out


def test_cancel_id_desconocido_no_hace_nada(fcs):
    fcs.script = [{"state": "running"}]
    jobs = cj.Jobs()
    jobs.cancel("cat:zzz")
    assert fcs.cancelled == []


# ── hilo de sondeo con daemon real (falso) ──────────────────────────────────
def test_hilo_de_sondeo_completa_el_trabajo(daemon, tmp_path):
    hechos = []
    jobs = cj.Jobs(on_done=hechos.append, every=0.05)
    jid = cs.download("nas", "v1", tmp_path)["job_id"]
    j = jobs.add(jid, "Silent Hill", 1000, True, "e", "nas")
    assert wait_for(lambda: j.state == "done", 8)
    assert hechos == [j] and j.path.endswith("Silent Hill (USA).bin")
    assert [x.job_id for x in jobs.list()] == [jid]


def test_hilo_termina_solo_y_se_reabre(fcs):
    fcs.script = [{"state": "completed"}]
    jobs = cj.Jobs(every=0.01)
    jobs.add("a", "A")
    assert wait_for(lambda: jobs._t and not jobs._t.is_alive(), 5)       # ~20 ciclos sin trabajo activo
    jobs.add("b", "B")
    assert jobs._t.is_alive() or wait_for(lambda: all(x.state == "done" for x in jobs.list()), 3)
