"""v1.94: plataforma correcta cuando otra lista dice dónde corre el port (PSP ≠ PC) y aviso de bibliotecas sin falsos positivos
(LD_LIBRARY_PATH del .toml, compilados en distrobox, «no volver a preguntar», y aprender cuando sí arrancó)."""
import json
import stat
import types

import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")


# ── plataforma ───────────────────────────────────────────────
@pytest.fixture
def cat(tmp_path, monkeypatch):
    from hub import catalog
    seed, imp, loc = tmp_path / "seed.json", tmp_path / "imports", tmp_path / "local.json"
    imp.mkdir()
    seed.write_text(json.dumps([{"id": "lcs", "name": "GTA: Liberty City Stories", "repo": "elmasas/lcs-recomp", "platform": "PSP"}]))
    monkeypatch.setattr(catalog, "SEED", seed)
    monkeypatch.setattr(catalog, "IMPORTS", imp)
    monkeypatch.setattr(catalog, "LOCAL", loc)
    return catalog, imp


def test_una_lista_que_dice_pc_no_pisa_la_consola(cat):
    catalog, imp = cat
    (imp / "quiver.json").write_text(json.dumps([{"name": "LCS Recomp", "repo": "elmasas/lcs-recomp", "platform": "PC", "notes": "nuevo"}]))
    e = next(x for x in catalog.load() if x["repo"] == "elmasas/lcs-recomp")
    assert e["platform"] == "PSP" and e["notes"] == "nuevo", "lo demás sí se actualiza"


def test_consola_deducida_si_solo_hay_pc(cat):
    catalog, imp = cat
    (imp / "otra.json").write_text(json.dumps([
        {"name": "Vice City Stories (PSP recomp)", "repo": "x/vcs-port", "platform": "Windows"},
        {"name": "Doom clásico", "repo": "y/doom-port", "platform": "PC"},
        {"name": "Mezcla ps2 y psp", "repo": "z/raro", "platform": "PC"}]))
    by = {x["repo"]: x["platform"] for x in catalog.load()}
    assert by["x/vcs-port"] == "PSP"
    assert by["y/doom-port"] == "PC", "un juego de PC de verdad sigue siendo PC"
    assert by["z/raro"] == "PC", "con dos pistas distintas no se adivina"


def test_una_consola_si_puede_corregir_otra_consola(cat):
    catalog, imp = cat
    (imp / "fix.json").write_text(json.dumps([{"name": "LCS", "repo": "elmasas/lcs-recomp", "platform": "PlayStation 2"}]))
    assert next(x for x in catalog.load() if x["repo"] == "elmasas/lcs-recomp")["platform"] == "PlayStation 2"


# ── bibliotecas ──────────────────────────────────────────────
def _juego(tmp_path, monkeypatch, extra=""):
    from hub import config
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "games").mkdir(parents=True)
    (config.LAUNCHER / "bin").mkdir()
    d = tmp_path / "lcs"
    (d / "build").mkdir(parents=True)
    b = d / "build" / "lcs"
    b.write_bytes(b"\x7fELF")
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    (config.LAUNCHER / "games" / "lcs.toml").write_text(
        f'id = "lcs"\nname = "LCS"\ninstall_dir = "{d}"\n\n[update]\ntype = "git-build"\nbuild_in = ["distrobox", "enter", "fedora", "--", "bash", "-c"]\n'
        f'\n[run]\ntype = "binary"\nexe = "build/lcs"\ncwd = "."\n{extra}')
    (config.LAUNCHER / "bin" / "play").write_text("#!/bin/sh\n")
    return d, b


@pytest.fixture
def ldd(monkeypatch):
    from hub import launchlog as L
    L._LIBS.clear()
    vistos = []

    def fake(cmd, timeout=6):
        vistos.append(cmd)
        env = next((c for c in cmd if str(c).startswith("LD_LIBRARY_PATH=")), "")
        return "\tlibfmt.so.10 => not found\n" if "/extra" not in env else "\tlibfmt.so.10 => /extra/libfmt.so.10\n"
    monkeypatch.setattr(L.shutil, "which", lambda n: "/usr/bin/ldd" if n == "ldd" else None)
    monkeypatch.setattr(L, "_run", fake)
    return L, vistos


def test_distrobox_y_ld_library_path_del_toml(tmp_path, monkeypatch, ldd):
    L, vistos = ldd
    d, b = _juego(tmp_path, monkeypatch)
    ri = L.run_info("lcs")
    assert ri["path"] == b and ri["container"] == "fedora" and ri["ld"] == ""
    assert L.libs_check("lcs") == {"miss": ["libfmt.so.10"], "container": "fedora"}
    d, b = _juego(tmp_path / "2", monkeypatch, '\n[run.env]\nLD_LIBRARY_PATH = "/extra:$INSTALL_DIR/lib"\n')
    L._LIBS.clear()
    assert L.run_info("lcs")["ld"] == f"/extra:{d}/lib"
    assert L.libs_check("lcs")["miss"] == [], "con el LD_LIBRARY_PATH que pone el launcher la biblioteca sí aparece"
    assert any(c[0] == "env" for c in vistos)


def test_lanzar_igual_no_vuelve_a_preguntar_y_arrancar_lo_aprende(H, ui, tmp_path, monkeypatch, ldd):
    _juego(tmp_path, monkeypatch)
    lanzados = []
    monkeypatch.setattr(H.subprocess, "Popen", lambda *a, **k: lanzados.append(a) or types.SimpleNamespace(pid=4243, poll=lambda: None), raising=False)
    monkeypatch.setattr(ui, "inst", lambda e: {"installed": True, "launcher_id": "lcs", "version": "1", "dir": "x"})
    monkeypatch.setattr(H.config, "save_settings", lambda s: None)
    ui.cfg["libs_ok"] = []
    ui.libs_ok.discard("lcs")
    ui.play_pr = ui.exit_at = None
    e = {"id": "lcs", "name": "LCS"}
    try:
        ui.play(e)
        assert "distrobox «fedora»" in ui.modal["msg"] and not lanzados
        dict(ui.modal["options"])["LANZAR DE TODOS MODOS"]()
        assert lanzados and "lcs" in ui.cfg["libs_ok"]
        assert ui.libs_for("lcs") == [], "la ficha ya no avisa"
        # arrancó bien sin haber dicho nada: se aprende solo
        ui.cfg["libs_ok"] = []
        ui.libs_ok.clear()
        ui.libchk["lcs"] = ["libfmt.so.10"]
        ui.play_pr, ui.play_t, ui.play_id = types.SimpleNamespace(poll=lambda: None, pid=1), 0, "lcs"
        ui.cfg["close_on_play"] = False
        ui.pump()
        assert "lcs" in ui.cfg["libs_ok"]
    finally:
        ui.play_pr = None
        ui.exit_at = 0
        ui.game_pids.clear()
        ui.cfg["libs_ok"] = []
        ui.cfg["close_on_play"] = True


def test_categoria_mezclada_del_indexador_elige_por_el_juego():
    """awesome-decomp agrupa «PS1 / PSP / Saturn»: antes todo salía «PlayStation» aunque fuera de PSP."""
    from hub import indexers
    base = {"type": "static-recomp", "platform": "PS1 / PSP / Saturn"}
    assert indexers._entry(dict(base, repo="a/lcs-psp-recomp", title="Liberty City Stories PSP"))["platform"] == "PSP"
    assert indexers._entry(dict(base, repo="b/ctr", title="Crash Team Racing"))["platform"] == "PlayStation"
