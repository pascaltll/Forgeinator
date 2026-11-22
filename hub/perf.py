"""Sonda de rendimiento de la interfaz (apagada por defecto). Se activa en AJUSTES → «Registrar rendimiento» o con HUB_PERF=1.
Escribe en hub.log líneas [rendimiento]: los fotogramas lentos (> umbral) con el tiempo de cada fase y las funciones que más tardaron,
y el coste de los 4 primeros fotogramas tras cambiar de pestaña. No cambia nada del funcionamiento cuando está apagada."""
import cProfile
import collections
import os
import pstats
import sys
import threading
import time

THRESHOLD_MS = float(os.environ.get("HUB_PERF_MS", "40"))
WATCH_FRAMES = 4


class Probe:
    def __init__(self, on=False):
        self.on = bool(on) or os.environ.get("HUB_PERF") == "1"
        self.tab, self.watch, self.counters, self.slow = None, 0, {}, 0
        self.samples, self._main, self._sampler = collections.deque(maxlen=400), None, None

    def _sample_loop(self):
        """Cada 50 ms anota dónde está el hilo principal (y en qué están los demás). Si luego hay un parón entre fotogramas, se ve qué hacía."""
        while True:
            time.sleep(0.05)
            try:
                fr = sys._current_frames()
                main = fr.get(self._main)
                if main is None:
                    continue

                def top(f, n=7):
                    out = []
                    while f is not None and len(out) < n:
                        fn = f.f_code.co_filename
                        if "/lib/python" not in fn and "site-packages" not in fn or not out:   # de la pila propia, sin ruido de la biblioteca estándar
                            out.append(f"{os.path.basename(fn)}:{f.f_lineno} {f.f_code.co_name}")
                        f = f.f_back
                    return " < ".join(out)
                others = collections.Counter()
                for tid, f in fr.items():
                    if tid not in (self._main, threading.get_ident()):
                        others[f"{os.path.basename(f.f_code.co_filename)} {f.f_code.co_name}"] += 1
                self.samples.append((time.time(), top(main), dict(others)))
            except Exception:  # noqa: BLE001
                pass

    def start_sampler(self):
        if self.on and self._sampler is None:
            self._main = threading.get_ident()
            self._sampler = threading.Thread(target=self._sample_loop, daemon=True)
            self._sampler.start()

    def note(self, name, ms):
        """Los puntos calientes (p. ej. releer el launcher) suman aquí su tiempo; se muestran junto al fotograma lento."""
        c = self.counters.setdefault(name, [0.0, 0])
        c[0] += ms
        c[1] += 1

    def cycle(self, interval_ms, flip_ms, ui):
        """Lo que NO se ve dentro del fotograma: lo que tarda display.flip (vsync/compositor de gamescope) y el intervalo real entre fotogramas."""
        if flip_ms >= max(8.0, THRESHOLD_MS / 2) or interval_ms >= 3 * max(THRESHOLD_MS, 22):
            print(f"[rendimiento] ciclo {interval_ms:.0f} ms entre fotogramas · flip {flip_ms:.0f} ms en «{ui.tab}»", file=sys.stderr, flush=True)
            if interval_ms >= 200 and self._sampler:
                now = time.time()
                win = [s for s in self.samples if now - interval_ms / 1000 - 0.1 <= s[0] <= now]
                tops = collections.Counter(s[1] for s in win)
                oth = collections.Counter()
                for s in win:
                    oth.update(s[2])
                print(f"[rendimiento]   parón: el hilo principal estaba en ({len(win)} muestras): " + " | ".join(f"{n}× {k}" for k, n in tops.most_common(3))
                      + (" · otros hilos: " + ", ".join(f"{k} ×{v}" for k, v in oth.most_common(4)) if oth else ""), file=sys.stderr, flush=True)

    def frame(self, ui, dt):
        key = (ui.tab, bool(ui.detail), (ui.modal or {}).get("kind"))
        if key != self.tab:
            self.tab, self.watch = key, WATCH_FRAMES
            print(f"[rendimiento] pantalla → {key[0]}{' (ficha)' if key[1] else ''}{' + modal ' + key[2] if key[2] else ''}", file=sys.stderr, flush=True)
        prof = cProfile.Profile() if self.watch else None
        t0 = time.perf_counter()
        if prof:
            prof.enable()
        try:
            t1 = time.perf_counter()
            ui.pump()
            t2 = time.perf_counter()
            ui.update(dt)
            t3 = time.perf_counter()
            ui.draw()
            t4 = time.perf_counter()
        finally:
            if prof:
                prof.disable()
        total = (t4 - t0) * 1000
        first = self.watch
        self.watch = max(0, self.watch - 1)
        if total >= THRESHOLD_MS or (first and total >= THRESHOLD_MS / 2):
            self.slow += 1
            ph = f"eventos {1000 * (t2 - t1):.0f} · lógica {1000 * (t3 - t2):.0f} · dibujo {1000 * (t4 - t3):.0f}"
            ct = " · ".join(f"{k} {v[0]:.0f} ms ({v[1]}×)" for k, v in sorted(self.counters.items(), key=lambda kv: -kv[1][0]))
            print(f"[rendimiento] fotograma lento {total:.0f} ms en «{ui.tab}»: {ph}" + (f" · {ct}" if ct else "") + f" · fps {ui.fps:.0f}", file=sys.stderr, flush=True)
            if prof:
                st = pstats.Stats(prof)
                rows = sorted(((v[3], v[0], k) for k, v in st.stats.items()), reverse=True)
                shown = 0
                for ct_, nc, (fn, ln, name) in ((r[0], r[1], r[2]) for r in rows):
                    if name in ("frame", "draw", "update", "pump", "<module>") or "select" in name or "poll" in name or ct_ * 1000 < 4:
                        continue
                    print(f"[rendimiento]     {ct_ * 1000:6.1f} ms  {name}  ({os.path.basename(fn)}:{ln}) ×{nc}", file=sys.stderr, flush=True)
                    shown += 1
                    if shown >= 10:
                        break
        self.counters.clear()
