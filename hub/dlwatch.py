"""Vigila las carpetas de descargas del navegador (el de Steam, Firefox, Chromium…): detecta cuándo EMPIEZA una descarga (archivo .crdownload/.part/.tmp
nuevo o que crece), su tamaño/velocidad, y cuándo TERMINA. No toca los archivos. Hub no puede ver el interior del navegador; esto es lo que se ve desde fuera."""
import os
import time
from pathlib import Path

PARTIAL = (".crdownload", ".part", ".download", ".opdownload")   # solo extensiones propias de navegadores (.tmp/.partial son demasiado genéricas)


def _ignore(name):
    return name.startswith(".") or name.startswith("~") or name.endswith("~")   # ocultos: sincronizadores, temporales de otros programas


class DLWatch:
    def __init__(self, dirs, direct=False):
        self.direct = direct      # también detectar archivos que se escriben directo (sin parcial): da falsos positivos, apagado por defecto
        self.ignored = set()
        self.dirs = [Path(os.path.expandvars(str(d))).expanduser() for d in dirs]
        self.known = {p: s for p, s in self._scan().items()}     # lo que ya había: se ignora
        self.stale = {p: s for p, s in self.known.items() if p.name.endswith(PARTIAL)}   # parciales abandonados de antes: no son una descarga nueva salvo que vuelvan a crecer
        self.active = {}      # ruta final → {name,size,speed,t0,last,stable_since,partial}
        self.recent = []      # terminadas: {name,path,size,t}

    def _scan(self):
        out = {}
        for d in self.dirs:
            try:
                for p in d.iterdir():
                    if p.is_file() and not _ignore(p.name):
                        out[p] = p.stat().st_size
            except OSError:
                continue
        return out

    @staticmethod
    def final_of(p):
        return p.with_name(p.name[: -len(next(x for x in PARTIAL if p.name.endswith(x)))]) if p.name.endswith(PARTIAL) else p

    def poll(self, now=None):
        """Devuelve eventos [("start", name), ("done", path)] desde la última llamada."""
        now = now or time.time()
        ev, cur = [], self._scan()
        seen = set()
        for p, size in cur.items():
            fin = self.final_of(p)
            part = p.name.endswith(PARTIAL)
            if p in self.stale:
                if self.stale[p] == size:
                    continue
                del self.stale[p]
            if fin in self.ignored or (not part and not self.direct and fin not in self.active):
                continue
            if fin in self.known and not part and self.known[fin] == size:
                continue
            if not part and fin in self.known and p == fin and fin not in self.active and size == self.known[fin]:
                continue
            a = self.active.get(fin)
            if a is None:
                if not part and fin in self.known:
                    continue
                if not part and size == 0:
                    continue
                a = self.active[fin] = {"name": fin.name, "size": size, "speed": 0.0, "t0": now, "last": now, "stable_since": now, "partial": part, "path": fin, "marks": [(now, size)]}
                ev.append(("start", fin))
            else:
                if a["partial"] and not part:
                    a["stable_since"] = now - 10        # el navegador renombró el parcial al nombre final: terminada
                if size != a["size"] and not (a["stable_since"] == now - 10):
                    a["stable_since"] = now
                # velocidad media de los últimos ~3 s (el navegador escribe a trozos: entre dos lecturas el tamaño a veces no cambia)
                marks = [m for m in a.setdefault("marks", []) if now - m[0] <= 3.0] + [(now, size)]
                a["marks"] = marks
                a["speed"] = max(0.0, (marks[-1][1] - marks[0][1]) / (marks[-1][0] - marks[0][0])) if len(marks) > 1 and marks[-1][0] > marks[0][0] else 0.0
                a["size"], a["last"], a["partial"] = size, now, part
            seen.add(fin)
        for fin, a in list(self.active.items()):
            done = False
            if fin not in seen:                               # desapareció el parcial: ¿existe el final?
                done = fin.exists()
                if not done:
                    del self.active[fin]                      # cancelada
                    continue
            elif not a["partial"] and now - a["stable_since"] >= 3.0 and a["size"] > 0:
                done = True                                   # navegador que escribe directo: tamaño estable 3 s
            if done:
                try:
                    sz = fin.stat().st_size
                except OSError:
                    sz = a["size"]
                del self.active[fin]
                self.known[fin] = sz
                self.recent = ([{"name": fin.name, "path": fin, "size": sz, "t": now}] + self.recent)[:8]
                ev.append(("done", fin))
        return ev
