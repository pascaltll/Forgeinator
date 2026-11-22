"""Autoarranque del daemon: ensure_running / autostart / call() con reintento. Lanza procesos reales (el daemon falso)."""
import os
import sys
import textwrap
from pathlib import Path

import pytest

from conftest import free_port, wait_for, HERE

DAEMON = HERE / "fakes" / "daemon.py"


def make_service(cs, port, token="SECRETO", open_delay=0, token_delay=0.3, write_token=True, venv=False, body=None):
    cs.SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    tf = f", '--token-file', {str(cs.TOKEN_FILE)!r}" if write_token else ""
    code = body or textwrap.dedent(f"""
        import runpy, sys
        sys.argv = ['d', '{port}', '{token}', '--open-delay', '{open_delay}', '--token-delay', '{token_delay}'{tf}]
        runpy.run_path({str(DAEMON)!r}, run_name='__main__')
    """)
    (cs.SERVICE_DIR / "service.py").write_text(code)
    if venv:
        b = cs.SERVICE_DIR / ".venv" / "bin"
        b.mkdir(parents=True)
        (b / "python").symlink_to(sys.executable)
    cs.URL = f"http://127.0.0.1:{port}/rpc"


@pytest.fixture
def svc_pidfile(tmp_path, monkeypatch, spawned):
    pf = tmp_path / "pid"
    monkeypatch.setenv("FAKE_PID_FILE", str(pf))
    yield pf
    if pf.exists():
        try:
            spawned.append(int(pf.read_text()))
        except ValueError:
            pass


def test_autostart_sin_service_py(cs):
    ok, msg = cs.autostart()
    assert ok is False and "service.py" in msg


def test_autostart_arranca_y_espera_el_token(cs, svc_pidfile):
    make_service(cs, free_port(), token_delay=0.5)
    ok, msg = cs.autostart()
    assert ok is True and cs.TOKEN_FILE.read_text() == "SECRETO"
    assert cs.health(start=False)[0]["source"] == "nas"


def test_el_daemon_corre_en_sesion_propia_y_loguea_a_archivo(cs, svc_pidfile):
    make_service(cs, free_port())
    cs.ensure_running()
    pid = int(svc_pidfile.read_text())
    assert os.getsid(pid) != os.getsid(0), "debe lanzarse con start_new_session=True"
    log = cs.LOG_FILE.read_text()
    assert "fake daemon arrancando" in log, "stdout del daemon debe ir a service.log (nunca DEVNULL)"


def test_usa_el_python_del_venv_si_existe(cs, svc_pidfile):
    make_service(cs, free_port(), venv=True)
    cs.ensure_running()
    assert "fake daemon arrancando con " + str(cs.SERVICE_DIR / ".venv" / "bin" / "python") in cs.LOG_FILE.read_text()


def test_no_lanza_un_segundo_daemon_si_ya_responde(cs, svc_pidfile):
    make_service(cs, free_port())
    cs.ensure_running()
    antes = svc_pidfile.read_text()
    cs.ensure_running()
    cs.ensure_running()
    assert svc_pidfile.read_text() == antes
    assert cs.LOG_FILE.read_text().count("fake daemon arrancando") == 1


def test_puerto_abierto_pero_token_tarda_no_duplica_daemon(cs, svc_pidfile):
    """Puerto escuchando y token que aparece 0.8 s después: espera, no lanza otro daemon."""
    make_service(cs, free_port(), token_delay=0.8)
    cs.ensure_running()                      # primer arranque
    cs.TOKEN_FILE.unlink()                   # simulamos "se perdió el token" con el daemon vivo
    import threading
    threading.Timer(0.5, lambda: cs.TOKEN_FILE.write_text("SECRETO")).start()
    cs.ensure_running(wait=3)
    assert cs.LOG_FILE.read_text().count("fake daemon arrancando") == 1


def test_escucha_pero_el_token_nunca_aparece(cs, svc_pidfile):
    make_service(cs, free_port(), write_token=False)
    with pytest.raises(cs.TokenMissing) as e:
        cs.ensure_running(wait=1.2)
    assert "no aparece el token" in str(e.value) and "fake daemon arrancando" in str(e.value), "el mensaje debe incluir el final del log"


def test_el_puerto_nunca_se_abre(cs, svc_pidfile):
    make_service(cs, free_port(), body="import time\nprint('arrancando y colgado', flush=True)\ntime.sleep(30)\n")
    with pytest.raises(cs.TransportError) as e:
        cs.ensure_running(wait=1.0)
    assert "no quedó listo" in str(e.value) and "arrancando y colgado" in str(e.value), "el error debe incluir el final del log"


def test_el_servicio_muere_al_arrancar_y_el_log_dice_por_que(cs):
    make_service(cs, free_port(), body="import sys\nprint('Traceback: falta una librería', file=sys.stderr, flush=True)\nsys.exit(3)\n")
    with pytest.raises(cs.TransportError) as e:
        cs.ensure_running(wait=1.0)
    assert "falta una librería" in str(e.value)


def test_call_arranca_el_servicio_y_reintenta_una_vez(cs, svc_pidfile):
    make_service(cs, free_port(), token_delay=0.4)
    assert cs.call("health")[0]["source"] == "nas"      # sin token y sin puerto → autoarranque → ok


def test_call_con_token_ausente_pero_servicio_vivo(cs, svc_pidfile):
    make_service(cs, free_port(), token_delay=0.2)
    cs.ensure_running()
    cs.TOKEN_FILE.unlink()
    import threading
    threading.Timer(0.4, lambda: cs.TOKEN_FILE.write_text("SECRETO")).start()
    assert cs.call("health")[0]["source"] == "nas"


def test_autostart_devuelve_false_y_nunca_lanza(cs):
    make_service(cs, free_port(), body="import sys; sys.exit(1)\n")
    ok, msg = cs.autostart()
    assert ok is False and isinstance(msg, str) and msg


def test_log_tail_vacio_si_no_hay_log(cs):
    assert cs._log_tail() == ""
    cs.LOG_FILE.write_text("a\nb\nc\n")
    assert cs._log_tail(2) == "b | c"
