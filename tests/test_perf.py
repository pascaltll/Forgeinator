"""Sonda de rendimiento: apagada no hace nada; encendida registra fotogramas lentos y el primer frame de cada pantalla."""
import time

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui

from conftest import wait_for
from hub import perf as perfmod


@pytest.fixture(scope="module")
def ui():
    import hub.ui as H
    return H.UI()


def run(u, n=2):
    for _ in range(n):
        u.frame()


def test_apagada_por_defecto_y_sin_salida(ui, capsys):
    assert ui.perf.on is False
    run(ui, 5)
    assert "[rendimiento]" not in capsys.readouterr().err


def test_encendida_registra_el_cambio_de_pantalla_y_el_primer_frame(ui, capsys, monkeypatch):
    monkeypatch.setattr(perfmod, "THRESHOLD_MS", 0.0)       # todo cuenta como lento: así vemos el formato
    real = ui.draw_settings                  # Ajustes ya dibuja solo lo visible y es muy rápido: se frena a propósito para que el perfilador tenga algo que contar

    def lento(body):
        time.sleep(0.012)
        return real(body)
    monkeypatch.setattr(ui, "draw_settings", lento)
    err = ""
    for _ in range(6):             # el detalle por función depende del perfilador de Python y de que el fotograma tarde algo: se repite (ver README v1.61)
        ui.go_tab("home")
        run(ui, 3)
        capsys.readouterr()
        ui.perf.on = True
        ui.go_tab("settings")
        run(ui, 4)
        err += capsys.readouterr().err
        ui.perf.on = False
        if "ms  " in err:
            break
    assert "pantalla → settings" in err and "fotograma lento" in err and "dibujo" in err and "eventos" in err
    assert "ms  " in err, "debe listar las funciones que más tardaron"


def test_registra_un_dibujo_lento_con_su_causa(ui, capsys, monkeypatch):
    import re
    monkeypatch.setattr(perfmod, "THRESHOLD_MS", 40.0)
    real = ui.draw_home

    def lento(body):
        time.sleep(0.09)
        return real(body)
    ui.perf.on = True
    err = ""
    for _ in range(3):             # el detalle por función depende del perfilador de Python; si un intento no lo trae se repite (ver README v1.61)
        monkeypatch.setattr(ui, "draw_home", real)
        ui.go_tab("settings")
        run(ui, 6)                                            # agota la ventana de observación de la pestaña
        capsys.readouterr()
        monkeypatch.setattr(ui, "draw_home", lento)
        ui.go_tab("home")
        run(ui, 1)
        err = capsys.readouterr().err
        if re.search(r"\d+\.\d+ ms\s+lento\s+\(test_perf\.py", err):
            break
    ui.perf.on = False
    m = re.search(r"fotograma lento (\d+) ms en «home».*dibujo (\d+)", err)
    assert m, err[-600:]
    assert int(m.group(1)) >= 85 and int(m.group(2)) >= 85, "el tiempo del dibujo lento debe quedar registrado"
    assert re.search(r"\d+\.\d+ ms\s+lento\s+\(test_perf\.py", err), "el perfil debe señalar la función culpable\n" + err[-600:]


def test_cuenta_el_tiempo_de_releer_el_launcher(ui, capsys):
    ui.perf.on = True
    ui._inst_c = None
    ui.perf.counters.clear()
    ui.inst(ui.entries[0])
    assert "launcher_games" in ui.perf.counters and "installed_info" in ui.perf.counters
    ui.perf.on = False
    ui.perf.counters.clear()


def test_el_ajuste_se_activa_y_se_guarda(ui, monkeypatch):
    guardado = {}
    from hub import config
    monkeypatch.setattr(config, "save_settings", lambda c: guardado.update(c))
    ui.toggle_perf()
    assert ui.perf.on is True and guardado.get("perf_log") is True
    ui.toggle_perf()
    assert ui.perf.on is False and guardado.get("perf_log") is False


def test_las_excepciones_del_dibujo_se_propagan_aunque_se_perfile(ui, monkeypatch):
    ui.perf.on = True
    ui.perf.watch = 3
    monkeypatch.setattr(ui, "draw", lambda: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        ui.frame()
    ui.perf.on = False


def test_ajustes_dibuja_el_interruptor(ui):
    ui.adv_open = True
    ui.go_tab("settings")
    run(ui, 3)
    assert "perf" in {w.key for w in ui.widgets}
    ui.go_tab("home")


def test_las_portadas_se_preparan_en_un_hilo_y_aparecen_despues(ui, tmp_path, monkeypatch):
    img = tmp_path / "p.png"
    s = pygame.Surface((640, 360))
    s.fill((200, 30, 30))
    pygame.image.save(s, str(img))
    monkeypatch.setattr(ui, "art_import", lambda e: None)
    monkeypatch.setattr(ui, "art_files", lambda e: {k: img for k in ui.ART_ORDER})
    ui._cov, ui._cov_jobs, ui._cov_done = {}, set(), []
    e = {"id": "a"}
    assert ui.cover(e, (200, 120)) is None, "la primera llamada no bloquea: la portada se prepara aparte"
    wait_for(lambda: ui._cov_done, 5)
    ui.frame()                                   # el fotograma recoge lo que terminó el hilo
    sur = ui.cover(e, (200, 120))
    assert sur is not None and sur.get_size() == (200, 120)


def test_sin_imagen_no_lanza_hilo_y_recuerda_que_no_hay(ui, monkeypatch):
    monkeypatch.setattr(ui, "art_import", lambda e: None)
    monkeypatch.setattr(ui, "art_files", lambda e: {})
    ui._cov, ui._cov_jobs, ui._cov_done = {}, set(), []
    assert ui.cover({"id": "z"}, (50, 50)) is None
    assert ui._cov == {("z", (50, 50)): None} and not ui._cov_jobs


def test_imagen_corrupta_no_rompe_el_fotograma(ui, tmp_path, monkeypatch):
    mala = tmp_path / "x.png"
    mala.write_bytes(b"no soy una imagen")
    monkeypatch.setattr(ui, "art_import", lambda e: None)
    monkeypatch.setattr(ui, "art_files", lambda e: {k: mala for k in ui.ART_ORDER})
    ui._cov, ui._cov_jobs, ui._cov_done = {}, set(), []
    ui.cover({"id": "m"}, (50, 50))
    wait_for(lambda: ui._cov_done, 5)
    ui.frame()
    assert ui._cov[("m", (50, 50))] is None and not ui._cov_jobs


def test_cycle_registra_un_flip_lento_y_calla_si_es_rapido(ui, capsys):
    ui.perf.cycle(22, 1, ui)
    assert capsys.readouterr().err == ""
    ui.perf.cycle(30, 60, ui)
    err = capsys.readouterr().err
    assert "ciclo 30 ms" in err and "flip 60 ms" in err


def test_un_paron_entre_fotogramas_dice_donde_estaba_el_hilo_principal(capsys):
    """Los parones de 300-700 ms que NO salen del dibujo: el muestreador anota la pila del hilo principal y la muestra al detectarlos."""
    import time
    from hub import perf
    pr = perf.Probe(True)
    pr.start_sampler()

    class _U:
        tab = "settings"
    def bloqueado():
        time.sleep(0.45)
    bloqueado()
    pr.cycle(450, 2, _U())
    err = capsys.readouterr().err
    assert "ciclo 450 ms" in err and "parón: el hilo principal estaba en" in err and "bloqueado" in err


@pytest.mark.ui
def test_se_anota_quien_cierra_el_video(capsys):
    """Cuando SDL pierde el vídeo, el registro dice si fue código de Python (con su pila) o el servidor gráfico."""
    import pygame
    import hub.ui as H
    u = H.UI()
    orig_dq, orig_q = pygame.display.quit, pygame.quit
    try:
        u._watch_display_quit()
        u._quiet_display_quit()
        assert "ninguna" in capsys.readouterr().err
        pygame.display.quit()
        u._quiet_display_quit()
        err = capsys.readouterr().err
        assert "pygame.display.quit desde" in err and "test_se_anota_quien_cierra_el_video" in err
    finally:
        pygame.display.quit, pygame.quit = orig_dq, orig_q
        pygame.display.init()
        u.screen = pygame.display.set_mode((1280, 720))
        u.running = False


@pytest.mark.ui
def test_el_diagnostico_de_video_solo_hace_ps_la_primera_vez(capsys, monkeypatch):
    import subprocess
    import hub.ui as H
    u = H.UI()
    try:
        n = []
        real = subprocess.run
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: (n.append(1) if a and "ps -eo" in str(a[0]) else None, real(*a, **k))[1])   # otros hilos (portapapeles) también llaman a subprocess
        u._video_diag()
        u._video_diag()
        err = capsys.readouterr().err
        assert len(n) == 1 and "PERDIDO #1" in err and "PERDIDO #2" in err and "sin tocar nada" in err
    finally:
        u.running = False
