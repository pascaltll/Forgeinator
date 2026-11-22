"""#sin hash: completed sin sha1/crc32 es válido; con hashes se guardan; nunca falla por no tenerlos."""
from _catjobs_helpers import start_job, until


def test_completo_sin_hash(daemon, tmp_path):
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "done")
    assert j.sha1 is None and j.crc32 is None and len(ev["done"]) == 1


def test_completo_con_hash(daemon, tmp_path):
    daemon.with_hashes = True
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "done")
    assert len(j.sha1) == 40 and len(j.crc32) == 8


def test_hash_nulo_explicito(daemon, tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"x")
    daemon.job_script = [{"state": "completed", "path": str(f), "sha1": None, "crc32": None}]
    jobs, j, ev = start_job(daemon, tmp_path)
    assert until(lambda: j.state == "done") and len(ev["done"]) == 1
