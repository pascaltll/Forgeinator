"""v3.16 · Hub abierto desde el QAM (no es un juego de Steam) en el Modo Juego: los juegos se lanzan por su atajo de Steam; sin atajo,
se pregunta antes de lanzarlos a pelo (gamescope no los mostraría)."""
import os
import time

from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401


def test_modo_juego_sin_steamgameid_lanza_por_steam(ui, monkeypatch):
    monkeypatch.delenv("SteamGameId", raising=False)
    ui.cfg["play_via_steam"] = True
    ui._gm = False
    assert not ui.via_steam_ok()                                   # escritorio: como siempre
    ui._gm = True
    assert ui.via_steam_ok()                                       # Modo Juego, abierto desde el QAM
    ui.cfg["play_via_steam"] = False
    assert not ui.via_steam_ok()
    ui.cfg["play_via_steam"] = True
    del ui._gm
    monkeypatch.setenv("GAMESCOPE_WAYLAND_DISPLAY", "gamescope-0")
    assert ui.in_game_mode()
    del ui._gm


def test_sin_atajo_pregunta_en_vez_de_lanzar_invisible(H, ui, tmp_path, monkeypatch):
    import types
    from hub import config
    monkeypatch.delenv("SteamGameId", raising=False)
    monkeypatch.setenv("QAM_RAIL_SOCK", str(tmp_path / "no-hay-qam.sock"))    # v3.17: sin QAM Rail → se pregunta como en v3.16
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "bin").mkdir(parents=True)
    (config.LAUNCHER / "bin" / "play").write_text("#!/bin/sh\n")
    (config.LAUNCHER / "bin" / "play").chmod(0o755)
    ui._gm = True
    lanzados = []
    monkeypatch.setattr(H.subprocess, "Popen", lambda *a, **k: lanzados.append(a) or types.SimpleNamespace(pid=4242, poll=lambda: None), raising=False)
    monkeypatch.setattr(ui, "inst", lambda e: {"installed": True, "launcher_id": "ctr", "version": "1", "dir": "x"})
    monkeypatch.setattr(ui, "libs_for", lambda lid: [])
    monkeypatch.setattr(ui, "_exe_missing", lambda e, lid: False)
    monkeypatch.setattr(ui, "steam_shortcut", lambda lid, name="": None)
    monkeypatch.setattr(H.config, "save_settings", lambda s: None)
    ui.play_pr = ui.exit_at = None
    e = {"id": "ctr", "name": "Crash Team Racing"}
    try:
        ui.play(e)
        t0 = time.time()
        while not ui.modal and time.time() - t0 < 5:
            ui.pump()
            time.sleep(0.02)
        assert ui.modal and ui.modal["title"] == "Este juego no tiene atajo en Steam" and not lanzados, "no se lanza a ciegas"
        dict(ui.modal["options"])["LANZAR DE TODOS MODOS"]()
        assert lanzados and ui.modal is None
    finally:
        ui.play_pr = None
        ui.game_pids.clear()
        del ui._gm
