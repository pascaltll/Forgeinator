"""v3.20 · Carátulas: 4 a la vez, menos consultas por juego, libretro como segunda fuente y sin repetir los que no existen."""
import json
import time

import pytest

from hub import covers, config, artsrc


@pytest.fixture
def cdir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    return tmp_path / "covers"


def fake(lat=0.0, exist=lambda name: True):
    calls = {"n": 0}

    def search(term):
        calls["n"] += 1
        time.sleep(lat)
        return [{"id": term, "name": term}] if exist(term) else []

    def images(kind, gid, limit=3):
        calls["n"] += 1
        time.sleep(lat)
        return [{"url": f"https://cdn/x/{gid}.png"}] if kind == "portrait" else []

    def fetch(url, dest):
        calls["n"] += 1
        time.sleep(lat)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"png")
    return calls, dict(search=search, images=images, fetch=fetch, libretro=False)


def test_varias_a_la_vez_y_rapido(cdir):
    es = [{"id": f"g{i}", "name": f"Juego {i}"} for i in range(24)]
    calls, kw = fake(0.05)
    t = time.time()
    r = covers.batch(es, **kw)
    dt = time.time() - t
    assert r["ok"] == 24 and len(covers.have()) == 24
    assert dt < 24 * 3 * 0.05 / 2.5                    # 4 a la vez: bastante menos que una tras otra
    assert calls["n"] == 24 * 3                         # buscar + imágenes + descargar, nada más


def test_los_que_no_existen_no_se_repiten(cdir, monkeypatch):
    es = [{"id": "a", "name": "Existe"}, {"id": "b", "name": "Fantasma"}]
    calls, kw = fake(exist=lambda n: n == "Existe")
    r = covers.batch(es, **kw)
    assert r["ok"] == 1 and r["sin"] == 1
    assert calls["n"] <= 3 + 2                          # el que no existe: una búsqueda por nombre (limpio = completo)
    assert "b" in covers.misses()
    calls["n"] = 0
    r = covers.batch(es, **kw)
    assert r["total"] == 0 and r["omitidos"] == 1 and calls["n"] == 0
    assert [e["id"] for e in covers.missing(es)] == ["b"] and covers.missing(es, include_misses=False) == []
    m = covers.misses()
    m["b"] = time.time() - (covers.RETRY_DAYS + 1) * 86400
    covers._save_misses(m)
    assert [e["id"] for e in covers.missing(es, include_misses=False)] == ["b"]   # pasados los días, se reintenta
    r = covers.batch(es, retry_misses=True, **kw)
    assert r["total"] == 1


def test_libretro_para_juegos_de_consola(cdir, monkeypatch):
    monkeypatch.setattr(artsrc, "_index", lambda system, folder: ["Crash Team Racing (USA)", "Crash Bash (USA)", "Spyro the Dragon (USA)"])
    got = []
    monkeypatch.setattr(artsrc, "fetch", lambda src, url, dest: got.append((src, url)) or dest.parent.mkdir(parents=True, exist_ok=True) or dest.write_bytes(b"p"))
    assert covers.fetch_libretro({"id": "ctr", "name": "Crash Team Racing", "platform": "PlayStation"})
    assert got[0][0] == "libretro" and got[0][1].endswith("/Sony%20-%20PlayStation/Named_Boxarts/Crash%20Team%20Racing%20%28USA%29.png")
    assert not covers.fetch_libretro({"id": "x", "name": "Halo Infinite", "platform": "PC"})            # PC: libretro no tiene
    assert not covers.fetch_libretro({"id": "y", "name": "Gran Turismo 4", "platform": "PlayStation"})   # parecido insuficiente


def test_si_steamgriddb_falla_prueba_libretro(cdir, monkeypatch):
    def boom(term):
        raise OSError("Cloudflare")
    monkeypatch.setattr(covers, "fetch_libretro", lambda e: True)
    assert covers.fetch_one({"id": "a", "name": "A"}, search=boom) == "ok"
    monkeypatch.setattr(covers, "fetch_libretro", lambda e: False)
    with pytest.raises(OSError):
        covers.fetch_one({"id": "a", "name": "A"}, search=boom)
