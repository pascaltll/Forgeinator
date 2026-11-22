"""Detener un proceso Y todo lo que lanzó (v2.81). Antes «CANCELAR» una compilación solo enviaba SIGTERM al proceso directo (bash/distrobox) y
sus hijos (cmake, ninja, python…) seguían corriendo con la tubería abierta: el trabajo no terminaba nunca y parecía que no dejaba cancelar."""
import os
import signal
import threading
import time


def clean_env(extra=None):
    """Entorno sin lo que el modo juego de Steam inyecta (v2.82): LD_PRELOAD (gameoverlayrenderer) y LD_LIBRARY_PATH (runtime) se heredan al
    contenedor y cualquier programa de dentro, incluido bash, falla con «error while loading shared libraries: libGL.so.1» (código 127)."""
    e = {k: v for k, v in os.environ.items() if k not in ("LD_PRELOAD", "LD_LIBRARY_PATH") and not k.startswith("BASH_FUNC_")}   # BASH_FUNC_*: funciones de Bazzite/gamescope («post_gamescope_start») que dan «syntax error» al entrar
    if extra:
        e.update(extra)
    return e


def kill_tree(proc, grace: float = 3.0):
    """SIGTERM al grupo de procesos (hay que haberlo lanzado con start_new_session=True) y SIGKILL si sigue vivo tras `grace` segundos."""
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            proc.terminate()
        except OSError:
            pass

    def hard():
        time.sleep(grace)
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                try:
                    proc.kill()
                except OSError:
                    pass
    threading.Thread(target=hard, daemon=True).start()
