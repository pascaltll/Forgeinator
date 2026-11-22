"""v2.01: el mando por evdev también avisa al soltar (una dirección ya no se queda «pulsada» repitiendo sola), el mando cuenta como
actividad (Ajustes no baja a 20 fps mientras navegas), desplazamiento suave al seguir el foco y God of War III Remastered es de PS4."""
import struct
import time

import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")


def test_evdev_manda_pulsar_y_soltar(monkeypatch, tmp_path):
    from hub import gamepad
    ev = lambda typ, code, val: struct.pack("llHHi", 0, 0, typ, code, val)  # noqa: E731
    data = ev(3, 0x11, 1) + ev(3, 0x11, 0) + ev(1, 0x130, 1) + ev(1, 0x130, 0)
    r, w = __import__("os").pipe()
    __import__("os").write(w, data)
    got = []
    monkeypatch.setattr(gamepad.glob, "glob", lambda p: ["/dev/input/event-falso"])
    monkeypatch.setattr(gamepad.os, "open", lambda p, flags: r)
    fake_ioctl_ok = True
    try:
        vivo = {"n": 0}

        def alive():
            vivo["n"] += 1
            return vivo["n"] < 6
        gamepad.start(got.append, alive)
        t0 = time.time()
        while len(got) < 5 and time.time() - t0 < 3:
            time.sleep(0.05)
    finally:
        __import__("os").close(w)
    assert got[:5] == ["DOWN", "~UP", "~DOWN", "A", "~A"] or ("DOWN" in got and "~DOWN" in got and "~A" in got), got


def test_soltar_detiene_la_repeticion_y_nada_se_queda_pulsado(ui):
    ui.go_tab("home")
    ui.held.clear()
    ui.win_focus, ui.mute_until = True, 0
    now = time.time()
    ui.pad_q.append(("DOWN", now))
    ui.pump()
    assert "DOWN" in ui.held
    ui.pad_q.append(("~DOWN", time.time()))
    ui.pump()
    assert "DOWN" not in ui.held
    ui.held["UP"] = [time.time() - 7, time.time() - 7]     # un «soltar» perdido
    ui.queue.clear()
    ui.pump()
    assert "UP" not in ui.held and not ui.queue


def test_el_mando_cuenta_como_actividad_en_ajustes(ui):
    ui.go_tab("settings")
    ui.held.clear()
    ui.t_act, ui.toast_t, ui.modal = 0, 0, None
    ui.cfg["power_mode"] = "perf"
    assert ui.target_fps() == 20
    ui.win_focus, ui.mute_until = True, 0
    ui.pad_q.append(("RIGHT", time.time()))
    ui.pad_q.append(("~RIGHT", time.time()))
    ui.pump()
    assert ui.target_fps() == 45, "navegando con la cruceta (evdev) no puede ir a 20 fps"
    ui.cfg["power_mode"] = "auto"


def test_desplazamiento_suave_y_fps_mientras_se_mueve(ui):
    ui.set_look(theme="dark", fx="perf")
    ui.smooth_scroll = True
    ui.go_tab("settings")
    ui.adv_open = True
    run(ui, 3)
    v = ui.views["settings"]
    v.off, v.target = 0, None
    run(ui, 1)
    cerca = next(w for w in ui.widgets if w.view is v and w.rect.top > v.rect.bottom and w.rect.top < v.rect.bottom + v.rect.h)   # justo debajo
    ui.focus, ui.reveal = cerca.key, True
    ui.frame()
    assert v.target is not None, "el foco lejos de la vista se acerca con animación"
    ui.t_act, ui.toast_t = 0, 0
    assert ui.target_fps() == 45, "mientras se desplaza no baja a 20 fps"
    for _ in range(20):
        ui.frame()
    assert v.target is None
    ui.adv_open = False
    ui.smooth_scroll = False


def test_god_of_war_iii_remastered_es_de_ps4():
    from hub import catalog
    e = next(x for x in catalog._load_file(catalog.SEED) if x["repo"].lower() == "felipeprado0/spartanport")   # el catálogo base (otras pruebas importan listas)
    assert e["platform"] == "PlayStation 4"
    assert catalog.guess_console({"name": "Some ps4 port", "repo": "a/b"}) == "PlayStation 4"
