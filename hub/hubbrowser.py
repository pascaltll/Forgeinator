"""Navegador propio de Hub (browser/hub_browser.py, Qt WebEngine): instalación y lanzamiento."""
import collections
import subprocess
import threading
import time
from pathlib import Path

from . import config

ROOT = Path(__file__).resolve().parent.parent
WRAP = ROOT / "bin" / "hub-browser"
_N = 0


def ready() -> bool:
    try:
        return subprocess.run([str(WRAP), "--check"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# niveles de compatibilidad: si Chromium se cuelga (SIGTRAP -5 / SIGSEGV -11), da un error FATAL o no muestra la ventana en READY_TIMEOUT s, Hub sube de nivel solo y lo recuerda.
# (nombre, flags de Chromium, variables de entorno de Qt)
LEVELS = [("AUTO", "", {}),
          ("OPENGL Y SIN SANDBOX", "--no-sandbox", {"QSG_RHI_BACKEND": "opengl"}),
          ("SOFTWARE Y SIN SANDBOX", "--no-sandbox --disable-gpu", {"QSG_RHI_BACKEND": "opengl", "QT_QUICK_BACKEND": "software"})]
READY_TIMEOUT = 25


def env(level: int) -> dict:
    import os
    name, fl, ev = LEVELS[max(0, min(level, len(LEVELS) - 1))]
    flags = (os.environ.get("HUB_BROWSER_FLAGS", "") + " " + fl).strip()
    return dict(os.environ, HUB_BROWSER_FLAGS=flags, LANG="C.UTF-8", LC_ALL="C.UTF-8", **ev)


def command(url: str, zoom: float) -> list:
    return [str(WRAP), url, "--zoom", str(zoom), "--download-dir", str(config.BROWSER_DL), "--profile", str(config.DATA / "browser")]


class SetupJob:
    """Mismo contrato que build.BuildJob para verse en DESCARGAS: id, state, stage, error, log, title, cancel."""
    label = "NAVEGADOR DE HUB"
    title = "Instalar navegador de Hub (PyQt6 + Qt WebEngine)"

    def __init__(self):
        global _N
        _N += 1
        self.id, self.state, self.stage, self.error = f"hb{_N}", "queued", "En cola", ""
        self.entry = {"id": ""}
        self.log = collections.deque(maxlen=400)
        self.proc, self._stop = None, False
        self.started = time.time()

    def cancel(self):
        self._stop = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def start(self, done=None):
        threading.Thread(target=self.run, args=(done,), daemon=True).start()

    def run(self, done=None):
        self.state, self.stage = "running", "Instalando (descarga ~150 MB, ocupa ~550 MB)…"
        try:
            self.proc = subprocess.Popen([str(WRAP), "--setup"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for ln in self.proc.stdout:
                self.log.append(ln.rstrip()[:300])
                if ln.strip():
                    self.stage = ln.strip()[:90]
            rc = self.proc.wait()
        except OSError as ex:
            rc = 1
            self.log.append(str(ex))
        if self._stop:
            self.state, self.stage = "error", "Cancelado"
        elif rc == 0:
            self.state, self.stage = "done", "Listo: ya puedes usar el navegador de Hub"
        else:
            self.state, self.stage, self.error = "error", "Falló la instalación", "mira el REGISTRO (¿falta espacio, red o librerías del sistema?)"
        if done:
            done(self.state == "done")
