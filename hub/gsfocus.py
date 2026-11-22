"""Quién tiene el foco en Gamescope: lee GAMESCOPE_FOCUSED_WINDOW/APP de la ventana raíz con un único `xprop -spy` (si falla, consulta cada 1 s).
Sirve para saber si hay un menú de Steam (QAM, overlay, teclado) encima de Hub aunque SDL siga diciendo que la ventana tiene foco."""
import os
import sys
import re
import shutil
import subprocess
import threading
import time

PROPS = ("GAMESCOPE_FOCUSED_WINDOW", "GAMESCOPE_FOCUSED_APP", "GAMESCOPE_KEYBOARD_FOCUS_DISPLAY")


_GOOD = [None]   # display donde se encontró la propiedad (se reutiliza)


def displays():
    """Candidatos: el que ya funcionó, :0 (Xwayland principal de Gamescope, donde viven las propiedades de foco), :1 y el DISPLAY de Hub."""
    c = [_GOOD[0], ":0", ":1", os.environ.get("DISPLAY")]
    return [d for i, d in enumerate(c) if d and d not in c[:i]]


def sample(xprop=None, display=None):
    if display:
        return _sample(xprop, display)
    for d in displays():
        r = _sample(xprop, d)
        if r:
            _GOOD[0] = d
            r["display"] = d
            return r
    return None


def _sample(xprop=None, display=None):
    """{'win': int|None, 'app': int|None, 'kbd': str} o None si no hay Gamescope/xprop."""
    xprop = xprop or os.environ.get("HUB_XPROP") or shutil.which("xprop")
    if not xprop:
        return None
    env = dict(os.environ)
    if display:
        env["DISPLAY"] = display
    try:
        out = subprocess.run([xprop, "-root", *PROPS], capture_output=True, text=True, timeout=2, env=env).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    vals = {}
    for m in re.finditer(r"^(GAMESCOPE_\w+)\(\w+\)\s*=\s*(.+)$", out, re.M):
        vals[m.group(1)] = m.group(2).strip()
    if "GAMESCOPE_FOCUSED_WINDOW" not in vals:
        return None
    num = lambda k: int(re.match(r"\d+", vals[k]).group(0)) if re.match(r"\d+", vals.get(k, "")) else None
    return {"win": num("GAMESCOPE_FOCUSED_WINDOW"), "app": num("GAMESCOPE_FOCUSED_APP"), "kbd": vals.get("GAMESCOPE_KEYBOARD_FOCUS_DISPLAY", "")}


def _parse(out, vals):
    for m in re.finditer(r"^(GAMESCOPE_\w+)\(\w+\)\s*=\s*(.+)$", out, re.M):
        vals[m.group(1)] = m.group(2).strip()
    num = lambda k: int(re.match(r"\d+", vals[k]).group(0)) if re.match(r"\d+", vals.get(k, "")) else None
    return {"win": num("GAMESCOPE_FOCUSED_WINDOW"), "app": num("GAMESCOPE_FOCUSED_APP"), "kbd": vals.get("GAMESCOPE_KEYBOARD_FOCUS_DISPLAY", "")}


def _spy(display, on_sample, alive):
    """UN solo proceso `xprop -spy` que imprime cuando cambia una propiedad (antes: uno nuevo cada 0,4 s, ~2,5 procesos/s
    que Steam tenía que registrar como parte del juego). Devuelve False si no se pudo usar."""
    xprop = os.environ.get("HUB_XPROP") or shutil.which("xprop")
    if not xprop or os.environ.get("HUB_FOCUS_POLL"):
        return False
    env = dict(os.environ)
    env["DISPLAY"] = display

    def die_with_parent():
        try:
            import ctypes
            ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, 15)   # PR_SET_PDEATHSIG, SIGTERM
        except Exception:
            pass
    try:
        p = subprocess.Popen([xprop, "-root", "-spy", *PROPS], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env,
                             preexec_fn=die_with_parent)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    vals, got = {}, False
    try:
        for line in p.stdout:
            got = True
            smp = _parse(line, vals)
            if smp["win"] is not None:
                smp["display"] = display
                on_sample(smp)
            if not alive():
                break
    finally:
        try:
            p.kill()
        except OSError:
            pass
    return got


def start(on_change, alive=lambda: True, every=0.4):
    """Hilo que llama on_change(sample_dict) cuando cambia la ventana/app con foco. No hace nada si no hay Gamescope."""
    def run():
        every_s = every
        first = sample()
        if first is None:
            print(f"[foco] gamescope: no encuentro GAMESCOPE_FOCUSED_WINDOW en {', '.join(displays()) or '(sin DISPLAY)'} (¿falta xprop o no es Gamescope?)", file=sys.stderr, flush=True)
            return
        on_change(first)
        last = [first]

        def feed(s):
            if (s["win"], s["app"]) != (last[0]["win"], last[0]["app"]):
                last[0] = s
                on_change(s)
        if first.get("display") and _spy(first["display"], feed, alive):
            if not alive():
                return
            print("[foco] xprop -spy terminó; vuelvo a consultar cada 1 s", file=sys.stderr, flush=True)
            every_s = max(every_s, 1.0)
        while alive():
            time.sleep(every_s)
            s = sample()
            if s:
                feed(s)
    threading.Thread(target=run, daemon=True).start()
