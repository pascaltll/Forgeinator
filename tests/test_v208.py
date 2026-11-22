"""v2.08: el foco de Gamescope se vigila con UN xprop -spy (antes un proceso nuevo cada 0,4 s)."""
import os
import stat
import time

from hub import gsfocus


def _fake(tmp_path, counter):
    p = tmp_path / "xprop"
    p.write_text(f"""#!/bin/sh
echo x >> {counter}
if [ "$2" = "-spy" ]; then
  echo 'GAMESCOPE_FOCUSED_APP(CARDINAL) = 111'
  echo 'GAMESCOPE_FOCUSED_WINDOW(CARDINAL) = 5'
  sleep 0.3
  echo 'GAMESCOPE_FOCUSED_APP(CARDINAL) = 769'
  sleep 5
else
  echo 'GAMESCOPE_FOCUSED_WINDOW(CARDINAL) = 5'
  echo 'GAMESCOPE_FOCUSED_APP(CARDINAL) = 111'
fi
""")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_un_solo_proceso_y_detecta_cambios(tmp_path, monkeypatch):
    cnt = tmp_path / "n"
    monkeypatch.setenv("HUB_XPROP", str(_fake(tmp_path, cnt)))
    monkeypatch.setenv("DISPLAY", ":9")
    monkeypatch.delenv("HUB_FOCUS_POLL", raising=False)
    gsfocus._GOOD[0] = None
    got = []
    run = [True]
    gsfocus.start(got.append, alive=lambda: run[0], every=0.05)
    t = time.time()
    while time.time() - t < 4 and not any(s["app"] == 769 for s in got):
        time.sleep(0.05)
    time.sleep(0.5)
    run[0] = False
    assert got[0]["app"] == 111 and any(s["app"] == 769 for s in got)
    # sondeos iniciales (uno por pantalla candidata hasta acertar) + 1 spy; nada de un proceso cada 0,4 s
    assert len(cnt.read_text().split()) <= 6
