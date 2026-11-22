"""#auth: 401/403 → TokenError, sin reintentos ni arrancar nada; el job no se queda colgado."""
import pytest

from hub import catalogservice as cs
from _catjobs_helpers import until
from hub import catalogjobs as cj


def test_token_cambiado_es_tokenerror_y_no_reintenta(daemon, cs, monkeypatch):
    cs.TOKEN_FILE.write_text("OTRO")
    arranques = []
    monkeypatch.setattr(cs, "ensure_running", lambda *a, **k: arranques.append(1))
    with pytest.raises(cs.TokenError):
        cs.search("x")
    assert arranques == [] and daemon.calls == []


def test_token_ausente_intenta_arrancar_una_vez(daemon, cs, monkeypatch):
    cs.TOKEN_FILE.unlink()
    n = []
    monkeypatch.setattr(cs, "ensure_running", lambda *a, **k: n.append(1))
    with pytest.raises(cs.TokenMissing):
        cs.search("x")
    assert n == [1]


@pytest.mark.parametrize("status", [401, 403])
def test_http_status(daemon, cs, status):
    daemon.http_status = status
    with pytest.raises(cs.TokenError):
        cs.health(start=False)


def test_job_con_token_rechazado_acaba_en_error_tras_3(daemon, cs, tmp_path):
    daemon.job_script = [{"state": "running"}]
    jobs = cj.Jobs(every=0.02)
    cs.TOKEN_FILE.write_text("MAL")
    j = jobs.add("job_1", "a.bin")
    assert until(lambda: j.state == "error")
    assert daemon.calls == []     # el daemon nunca vio una llamada válida; el cliente no tocó el token
    assert cs.TOKEN_FILE.read_text() == "MAL"
