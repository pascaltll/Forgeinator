"""Trabajo genérico en segundo plano (varias órdenes seguidas) con el mismo contrato que build.BuildJob, para verse en DESCARGAS."""
import re
import collections
import sys
import subprocess
import threading
import time

from . import proctree

_N = 0


class CmdJob:
    def __init__(self, label, title, steps, entry=None, cwd=None):
        global _N
        _N += 1
        self.id, self.label, self.title, self.steps, self.cwd = f"c{_N}", label, title, steps, cwd
        self.entry = entry or {"id": ""}
        self.state, self.stage, self.error = "queued", "En cola", ""
        self.log = collections.deque(maxlen=400)
        self.proc, self._stop = None, False
        self.started = time.time()
        self.probe = None          # callable → fracción real (p. ej. ninja) o None
        self.expected = 0          # segundos que suele tardar (si se sabe): da una barra estimada cuando el programa no dice su avance

    _PCT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?%")
    _NM = re.compile(r"[\[(](\d+)\s?/\s?(\d+)[\])]")

    def progress(self):
        """(fracción 0-1, es_estimada). Lee el avance de las últimas líneas ([3/12] o 45 %); si no hay, usa el tiempo contra `expected`."""
        if self.state == "done":
            return 1.0, False
        if self.probe and self.state == "running":
            try:
                v = self.probe()
            except Exception:  # noqa: BLE001
                v = None
            if v is not None:
                return v, False
        for ln in reversed(list(self.log)[-40:]):
            m = self._NM.search(ln)
            if m and int(m.group(2)) > 0 and int(m.group(1)) <= int(m.group(2)):
                return int(m.group(1)) / int(m.group(2)), False
            m = self._PCT.search(ln)
            if m and float(m.group(1)) <= 100:
                return float(m.group(1)) / 100, False
        if self.expected and self.state == "running":
            return min(0.95, (time.time() - self.started) / self.expected), True
        return 0.0, False

    def elapsed_text(self):
        t = int(time.time() - self.started)
        return f"{t // 60}:{t % 60:02d}"

    def cancel(self):
        """v2.81: detiene el proceso y TODO lo que lanzó, y pasa a «Cancelado» al instante (antes esperaba a que la tubería se cerrara y no lo hacía)."""
        self._stop = True
        if self.state in ("queued", "running"):
            self.state, self.stage = "error", "Cancelado"
        proctree.kill_tree(self.proc)

    def start(self, done=None):
        threading.Thread(target=self.run, args=(done,), daemon=True).start()

    NOISE = ("from LD_PRELOAD cannot be preloaded", "default value of option vk_wsi_force_swapchain_to_current_extent")

    def _say(self, ln):
        if any(n in ln for n in self.NOISE):         # v2.68: avisos inofensivos que llenaban el registro de líneas rojas «ERROR»
            self.noise = getattr(self, "noise", 0) + 1
            return
        """Cada línea queda en la ventana (DESCARGAS) Y en hub.log con la etiqueta [trabajo], para poder revisarla después."""
        self.log.append(ln)
        print(f"[trabajo] {self.label} · {ln}"[:400], file=sys.stderr, flush=True)

    def run(self, done=None):
        self.state = "running"
        ok = True
        bad = []
        for desc, argv in self.steps:
            if self._stop:
                break
            self.stage = desc
            if callable(argv):               # paso hecho en Python (p. ej. traer bibliotecas, registrar la versión)
                self._say("· " + desc)
                try:
                    argv(self._say)
                except Exception as ex:  # noqa: BLE001
                    ok = False
                    bad.append(f"«{desc}»")
                    self._say(f"(falló: {ex})")
                continue
            self._say("$ " + " ".join(str(a) for a in argv))
            try:
                self.proc = subprocess.Popen([str(a) for a in argv], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=self.cwd,
                                             env=proctree.clean_env(), start_new_session=True)
                for ln in self.proc.stdout:
                    self._say(ln.rstrip()[:300])
                    if self._stop:
                        break
                rc = self.proc.wait() if not self._stop else 1
            except (OSError, ValueError) as ex:
                self._say(str(ex))
                rc = 1
            if rc != 0:
                ok = False
                bad.append(f"«{desc}» (código {rc})")
                self._say(f"(código {rc})")
        if self._stop:
            self.state, self.stage = "error", "Cancelado"
            self._say("(cancelado)")
        elif ok:
            self.state, self.stage = "done", "Listo"
        else:
            self.state, self.stage, self.error = "error", "Terminó con avisos", "falló " + ", ".join(bad) + " · mira el REGISTRO"
            print(f"[trabajo] {self.label} terminó con avisos: {self.error}", file=sys.stderr, flush=True)
        if done:
            done(self.state == "done")
