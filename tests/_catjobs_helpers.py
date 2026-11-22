"""Utilidades comunes de test_catalog_*: Jobs reales contra el daemon falso."""
import time

from hub import catalogjobs as cj
from hub import catalogservice as cs


def start_job(daemon, tmp_path, **kw):
    """search→variants→download como manda la regla de oro; devuelve (jobs, job, eventos)."""
    ev = {"wait": [], "done": []}
    jobs = cj.Jobs(on_done=ev["done"].append, on_wait=ev["wait"].append, every=0.02)
    cs.search("silent hill")
    v = cs.variants("nas", "sh1")
    jid = cs.download("nas", v[0]["variant_id"], tmp_path)["job_id"]
    j = jobs.add(jid, "Silent Hill.bin", 1000, True, "e1", "nas")
    return jobs, j, ev


def until(pred, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return bool(pred())
