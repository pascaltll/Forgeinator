"""Causa de las pérdidas de vídeo cada ~5 min en Gamescope: pygame.scrap.init() llamado una y otra vez desde el hilo del portapapeles
terminaba con «video system not initialized». Se reprodujo con X11 (Xvfb): init repetido desde un hilo → vídeo perdido a los ~13 s;
init una vez + get_text desde el hilo → estable 30 s."""
import inspect
import re
import shutil
import subprocess
import sys
import textwrap

import pytest

import hub.ui as H


def test_scrap_init_solo_se_llama_una_vez_y_en_init():
    src = inspect.getsource(H)
    llamadas = re.findall(r"^[^#\n]*pygame\.scrap\.init\(\)", src, re.M)
    assert len(llamadas) == 1, "scrap.init() solo en UI.__init__ (hilo principal)"
    assert re.search(r"^[^#\n]*pygame\.scrap\.init\(\)", inspect.getsource(H.UI.__init__), re.M)


@pytest.mark.skipif(not (shutil.which("xvfb-run") and shutil.which("Xvfb")), reason="hace falta Xvfb")
def test_el_hilo_del_portapapeles_no_pierde_el_video_en_x11():
    code = textwrap.dedent("""
        import os, threading, time
        os.environ["SDL_VIDEODRIVER"] = "x11"
        import pygame
        pygame.display.init(); pygame.font.init()
        s = pygame.display.set_mode((320, 200))
        pygame.scrap.init()                       # una vez, hilo principal (como UI.__init__)
        stop = False
        def clip():
            while not stop:
                try: pygame.scrap.get_text()      # como UI.clipboard() sin init
                except Exception: pass
                time.sleep(0.02)
        threading.Thread(target=clip, daemon=True).start()
        t0 = time.time(); c = pygame.time.Clock()
        while time.time() - t0 < 20:
            c.tick(45); pygame.event.pump(); s.fill((9, 9, 9)); pygame.display.flip()
        print("OK" if pygame.display.get_init() else "LOST")
    """)
    r = subprocess.run(["xvfb-run", "-a", sys.executable, "-c", code], capture_output=True, text=True, timeout=90)
    assert "OK" in r.stdout, r.stdout + r.stderr
