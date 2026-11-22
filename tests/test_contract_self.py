"""Meta-prueba: el test de contrato live debe PASAR con un daemon correcto y FALLAR (con mensaje útil)
con uno que se comporta como tu service.py actual (completa sin descargar, nombre fijo archivo_descargado.zip)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import HERE, HUB_SRC
from fakes.daemon import FakeDaemon, default_variants


def correr(d, tmp_path, extra_env=None):
    tf = tmp_path / "token"
    tf.write_text(d.token)
    env = dict(os.environ, CATALOG_LIVE="1", CATALOG_LIVE_DOWNLOAD="1", CATALOG_LIVE_URL=d.url, CATALOG_LIVE_TOKEN_FILE=str(tf),
               REPORT_DIR=str(tmp_path / "rep"), HUB_SRC=str(HUB_SRC), CATALOG_LIVE_TIMEOUT="60")
    env.update(extra_env or {})
    p = subprocess.run([sys.executable, "-m", "pytest", "-m", "live", "-q", "-p", "no:cacheprovider", "--no-header", "-rf", str(HERE / "test_contract_live.py")],
                       capture_output=True, text=True, env=env, cwd=str(HERE), timeout=180)
    return p.returncode, p.stdout + p.stderr


def daemon_bueno():
    d = FakeDaemon("T-OK")
    d.known_items = {"sh1"}
    d.with_hashes = True
    d.n_variants, d.variant_size = 24, "16 B"
    d.job_script = None
    return d.start()


def test_el_contrato_pasa_con_un_daemon_correcto(tmp_path):
    d = daemon_bueno()
    try:
        rc, out = correr(d, tmp_path)
    finally:
        d.stop()
    assert rc == 0, out[-2500:]
    assert "24 variantes" in out or "passed" in out


def test_el_contrato_detecta_la_descarga_simulada(tmp_path):
    d = daemon_bueno()
    d.write_file = False
    d.filename = "archivo_descargado.zip"        # lo que hace el service.py actual
    try:
        rc, out = correr(d, tmp_path)
    finally:
        d.stop()
    assert rc != 0
    assert "placeholder" in out or "NO existe el archivo" in out, out[-2500:]


def test_el_contrato_detecta_token_rechazado(tmp_path):
    d = daemon_bueno()
    d.token = "OTRO-TOKEN-DISTINTO"
    tf = tmp_path / "token"
    try:
        tf.write_text("T-OK")
        env = dict(os.environ, CATALOG_LIVE="1", CATALOG_LIVE_URL=d.url, CATALOG_LIVE_TOKEN_FILE=str(tf), REPORT_DIR=str(tmp_path / "rep"), HUB_SRC=str(HUB_SRC))
        p = subprocess.run([sys.executable, "-m", "pytest", "-m", "live", "-q", "-p", "no:cacheprovider", "--no-header", "-rf", "-x", str(HERE / "test_contract_live.py")],
                           capture_output=True, text=True, env=env, cwd=str(HERE), timeout=120)
    finally:
        d.stop()
    assert p.returncode != 0 and "test_02" in p.stdout and "TokenError" in p.stdout + p.stderr


def test_el_contrato_detecta_progreso_que_retrocede(tmp_path):
    d = daemon_bueno()
    d.job_script = [{"state": "running", "phase": "downloading", "progress": 0.6}, {"state": "running", "phase": "downloading", "progress": 0.2}, {"state": "completed", "progress": 1.0}]
    try:
        rc, out = correr(d, tmp_path)
    finally:
        d.stop()
    assert rc != 0 and "retrocede" in out


def test_el_contrato_detecta_estado_desconocido_para_hub(tmp_path):
    d = daemon_bueno()
    d.job_script = [{"state": "downloading", "progress": 0.1}]
    try:
        rc, out = correr(d, tmp_path)
    finally:
        d.stop()
    assert rc != 0 and "estado desconocido para Hub" in out
