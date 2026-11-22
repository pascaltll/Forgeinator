"""installed_info con índices: mismo resultado que el camino lento, y mucho más rápido con miles de tarjetas (medido en el Ally: 50-250 ms por pasada)."""
import random
import time
from pathlib import Path

import pytest

from hub import config, install


def _mundo(n, nlg, seed=1):
    rnd = random.Random(seed)
    entries, lg = [], []
    for i in range(n):
        e = {"id": f"e{i}", "name": f"E{i}", "repo": f"o{i % (n // 3 + 1)}/r{i % 7}" if i % 5 else "", "folder": f"f{i % (n - 3)}"}
        if i % 11 == 0:
            e["launcher_id"] = f"L{rnd.randrange(nlg)}"
        entries.append(e)
    for j in range(nlg):
        e = entries[rnd.randrange(n)]
        lg.append({"id": rnd.choice([f"L{j}", e["id"]]), "repo": (e["repo"] or "").lower() if j % 2 else "", "name": f"g{j}",
                   "dir": config.GAMES_DIR / rnd.choice([e.get("folder", e["id"]), f"otra{j}"]), "version_file": ".release_version"})
    return entries, lg


def test_indice_da_lo_mismo_que_el_camino_lento():
    entries, lg = _mundo(400, 60)
    ix = install.build_index(lg, entries)
    for e in entries:
        a = install.installed_info(e, lg, entries)
        b = install.installed_info(e, lg, entries, ix)
        assert a == b, e["id"]


def test_el_camino_rapido_no_toca_el_disco_por_tarjeta(tmp_path, monkeypatch):
    """Con 2400 tarjetas sin instalar, la pasada no hace is_dir/iterdir por tarjeta (una sola lectura de GAMES_DIR)."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    (tmp_path / "f1").mkdir()
    (tmp_path / "f1" / "x").write_text("x")
    (tmp_path / "vacia").mkdir()
    entries = [{"id": f"e{i}", "repo": "", "folder": f"f{i}"} for i in range(2400)] + [{"id": "v", "repo": "", "folder": "vacia"}]
    ix = install.build_index([], entries)
    llamadas = []
    real = Path.is_dir
    monkeypatch.setattr(Path, "is_dir", lambda self: (llamadas.append(1), real(self))[1])
    res = {e["id"]: install.installed_info(e, [], entries, ix) for e in entries}
    assert not llamadas
    assert res["e1"]["dir"] == str(tmp_path / "f1") and not res["e2"]["installed"] and not res["v"]["installed"]


def test_launcher_games_solo_reparsea_lo_que_cambio(tmp_path, monkeypatch):
    import tomllib
    monkeypatch.setattr(config, "LAUNCHER", tmp_path)
    (tmp_path / "games").mkdir()
    f = tmp_path / "games" / "a.toml"
    f.write_text('id = "a"\nname = "A"\ninstall_dir = "~/x"\n[update]\nrepo = "O/R"\n')
    n = []
    real = tomllib.loads
    monkeypatch.setattr(tomllib, "loads", lambda s, *a, **k: (n.append(1), real(s, *a, **k))[1])
    install._LG_CACHE.clear()
    assert install.launcher_games()[0]["repo"] == "o/r" and len(n) == 1
    install.launcher_games()
    assert len(n) == 1, "sin cambios no se vuelve a parsear"
    f.write_text('id = "a"\nname = "A2"\ninstall_dir = "~/x"\n[update]\nrepo = "O/R"\n')
    assert install.launcher_games()[0]["name"] == "A2" and len(n) == 2


def test_con_miles_de_tarjetas_la_pasada_completa_es_corta():
    entries, lg = _mundo(2400, 30)
    t0 = time.perf_counter()
    ix = install.build_index(lg, entries)
    for e in entries:
        install.installed_info(e, lg, entries, ix)
    ms = 1000 * (time.perf_counter() - t0)
    assert ms < 400, f"{ms:.0f} ms"   # el camino lento tardaba varios segundos con esta carga


@pytest.mark.ui
def test_la_cache_caducada_se_renueva_en_segundo_plano(monkeypatch):
    import hub.ui as H
    u = H.UI()
    try:
        e = u.entries[0]
        for _ in range(250):          # un refresco previo (prewarm de la UI) puede seguir en vuelo: esperarlo
            if not getattr(u, "_inst_busy", False):
                break
            time.sleep(0.02)
        u.inst(e)
        t, d = u._inst_c
        u._inst_c = (t - 60, d)
        llamadas = []
        monkeypatch.setattr(u, "_inst_build", lambda ents: (llamadas.append(len(ents)), {"_lg": [], "_ix": install.build_index([], ents)})[1])
        antes = u.inst(e)           # no bloquea: sirve lo anterior
        assert antes is d[e["id"]]
        for _ in range(100):
            if llamadas and not u._inst_busy:
                break
            time.sleep(0.02)
        assert llamadas and time.time() - u._inst_c[0] < 5
    finally:
        u.running = False


def test_el_aviso_de_asociacion_por_repo_sale_una_sola_vez(capsys):
    install._WARNED.clear()
    entries = [{"id": "a", "repo": "o/r", "folder": "fa"}, {"id": "b", "repo": "o/r", "folder": "fb"}]
    lg = [{"id": "x", "repo": "o/r", "name": "X", "dir": config.GAMES_DIR / "fx", "version_file": ".release_version"}]
    ix = install.build_index(lg, entries)
    for _ in range(5):
        install.installed_info(entries[0], lg, entries, ix)
    assert capsys.readouterr().err.count("SOLO por compartir repo") == 1
