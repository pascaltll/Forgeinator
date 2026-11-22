"""v2.19: el binario compilado en el contenedor lleva su RPATH y arranca sin LD_LIBRARY_PATH."""
import os
import subprocess

import pytest

from test_v195 import juego  # noqa: F401
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio  # noqa: F401


def _fake_distrobox(tmp_path, monkeypatch):
    b = tmp_path / "bin"
    b.mkdir()
    log = tmp_path / "calls.txt"
    # distrobox falso: "enter NAME -- cmd..." ejecuta cmd en el sistema con un patchelf falso que lo apunta al log
    (b / "patchelf").write_text(f"#!/bin/sh\necho \"$@\" >> {log}\n")
    (b / "distrobox").write_text("#!/bin/sh\nshift 3\nexec \"$@\"\n")
    for n in ("patchelf", "distrobox"):
        (b / n).chmod(0o755)
    monkeypatch.setenv("PATH", f"{b}:{os.environ['PATH']}")
    return log


def test_patch_rpath_ajusta_binario_y_bibliotecas(tmp_path, monkeypatch):
    from hub import recipes
    log = _fake_distrobox(tmp_path, monkeypatch)
    exe = tmp_path / "build" / "vcs"
    libs = tmp_path / "build" / "lib"
    libs.mkdir(parents=True)
    exe.write_bytes(b"x")
    (libs / "libavcodec.so.61").write_bytes(b"x")
    msgs = []
    recipes.patch_rpath(exe, libs, "hub-x", msgs.append)
    calls = log.read_text().splitlines()
    assert any("--force-rpath --set-rpath $ORIGIN/lib" in c and c.endswith("vcs") for c in calls)
    assert any("--set-rpath $ORIGIN " in c + " " and "libavcodec.so.61" in c for c in calls)
    assert "$ORIGIN/lib" in msgs[0]


def test_patch_rpath_falla_claro_si_no_hay_binario(tmp_path):
    import pytest
    from hub import recipes
    with pytest.raises(OSError):
        recipes.patch_rpath(tmp_path / "no", tmp_path / "lib", "x")


def test_la_receta_de_gta_incluye_el_paso_rpath():
    from hub import recipes
    r = recipes.load_all()
    rec = next(v for v in (r.values() if isinstance(r, dict) else r) if "gothamor/gta-vcs-recomp" in (v.get("match") or {}).get("repos", []))
    pasos = recipes.phase2(rec, {"id": "gta-vcs-recomp"}, __import__("pathlib").Path("/x"), [], None, lambda say: None)
    nombres = [p[0] for p in pasos]
    assert any("RPATH" in n for n in nombres)
    assert nombres.index(next(n for n in nombres if "RPATH" in n)) > nombres.index(next(n for n in nombres if "bibliotecas" in n))


def _rels():
    def a(n):
        return {"name": n, "size": 1000, "browser_download_url": "u/" + n}
    return [{"tag_name": "v3", "published_at": "2026-11-01T00:00:00Z", "assets": [a("gow-linux-x64.tar.gz")]},
            {"tag_name": "v2", "published_at": "2026-10-01T00:00:00Z", "assets": [a("gow-linux-x64.tar.gz"), a("gow-windows-x64.zip")]},
            {"tag_name": "v1", "published_at": "2026-09-01T00:00:00Z", "assets": [a("gow-windows-x64.zip")]}]


def test_latest_con_tag_y_resumen_de_releases(monkeypatch):
    from hub import github
    monkeypatch.setattr(github, "releases", lambda repo, force=False, timeout=10: {"releases": _rels(), "stale": False, "error": None})
    assert github.latest("a/b")["tag"] == "v3" and not github.latest("a/b")["win_assets"]
    v2 = github.latest("a/b", tag="v2")
    assert v2["tag"] == "v2" and len(v2["win_assets"]) == 1 and len(v2["assets"]) >= 1
    s = {r["tag"]: r for r in github.summary("a/b")}
    assert s["v3"]["windows"] == 0 and s["v2"]["windows"] == 1 and s["v1"]["linux"] == 0


def test_la_ficha_ofrece_elegir_release_e_instala_la_elegida(H, ui, juego, monkeypatch):
    from hub import github
    from test_temas_y_fuzz import run
    from test_v212 import _ficha, _a
    monkeypatch.setattr(github, "releases", lambda repo, force=False, timeout=10: {"releases": _rels(), "stale": False, "error": None})
    e = _ficha(H, ui, juego, monkeypatch, [_a("G-linux-x64.tar.gz")], [])
    ui.rel_sum[ui.rk(e)] = github.summary("a/b")
    ui.asset_os[e["id"]] = "windows"
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = "versiones"
    run(ui, 3)
    assert "pick_rel" in {w.key for w in ui.widgets}
    ui.pick_release(e)
    labels = [o[0] for o in ui.modal["options"]]
    assert labels[0].startswith("ÚLTIMA") and any("v2" in l and "Windows 1" in l for l in labels)
    next(o for o in ui.modal["options"] if o[0].startswith("v2"))[1]()
    import time
    for _ in range(50):
        ui.pump()
        if ui.rk(e) in ui.rel_sel:
            break
        time.sleep(0.05)
    assert ui.rel_for(e)["tag"] == "v2" and ui.rel_for(e)["win_assets"]
    ui.modal = None
    run(ui, 3)
    assert ui.rel[ui.rk(e)]["tag"] == "v2" or ui.rel_for(e)["tag"] == "v2"


def test_release_solo_windows_sin_la_palabra_windows_se_ofrece_para_proton(monkeypatch):
    """GoW PSP publica «GoW_PSP_Launcher-v1.5.0.zip» (solo Windows) sin decir el sistema: antes Hub lo trataba como un build de Linux dudoso."""
    from hub import github
    rels = [{"tag_name": "v1.5.0", "published_at": "2026-11-07T00:00:00Z",
             "assets": [{"name": "GoW_PSP_Launcher-v1.5.0.zip", "size": 9, "browser_download_url": "u/l.zip"}]},
            {"tag_name": "v1.0.0", "published_at": "2026-08-01T00:00:00Z",
             "assets": [{"name": "GoW_PSP_windows_x64.zip", "size": 9, "browser_download_url": "u/w.zip"}]}]
    monkeypatch.setattr(github, "releases", lambda repo, force=False, timeout=10: {"releases": rels, "stale": False, "error": None})
    v = github.latest("a/b")
    assert [w["name"] for w in v["win_assets"]] == ["GoW_PSP_Launcher-v1.5.0.zip"] and v["win_assets"][0]["class"]["os"] == "¿windows?" and v["has_windows"]
    assert github.latest("a/b", tag="v1.0.0")["win_assets"][0]["class"]["os"] == "windows"
    # con un build de Linux claro, lo ambiguo NO se ofrece como Windows
    both = [{"name": "g-linux-x64.tar.gz", "size": 1, "browser_download_url": "a"}, {"name": "g-data.zip", "size": 1, "browser_download_url": "b"}]
    assert github.win_assets(both) == []
    assert github.win_assets([{"name": "g-source.zip"}, {"name": "g-setup.zip"}]) == []
