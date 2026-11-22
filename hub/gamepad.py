"""Mando vía evdev (/dev/input/event*), igual que los updaters actuales.
Por posición del botón: BTN_SOUTH (0x130) y START (0x13b) → "A"; BTN_EAST (0x131) → "B"; X/Y, LB/RB y la cruceta para el editor."""
import glob
import os
import select
import struct
import threading
import time

_EV = struct.calcsize("llHHi")
_CODES = {0x130: "A", 0x13B: "A", 0x131: "B", 0x133: "X", 0x134: "Y", 0x136: "LB", 0x137: "RB", 0x13A: "SEL", 0x13C: "MODE"}
_HAT = {0x10: ("LEFT", "RIGHT"), 0x11: ("UP", "DOWN")}  # cruceta (ABS_HAT0X / ABS_HAT0Y)


def start(callback, alive=lambda: True):
    """Escucha todos los mandos (y los que se conecten después) y llama callback("A"|"B")."""

    def run():
        fds: dict = {}

        def drop(fd):
            for p, v in list(fds.items()):
                if v == fd:
                    del fds[p]
            try:
                os.close(fd)
            except OSError:
                pass

        while alive():
            for p in glob.glob("/dev/input/event*"):
                if p not in fds:
                    try:
                        fds[p] = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
                    except OSError:
                        pass
            end = time.time() + 2.0
            while time.time() < end and alive():
                if not fds:
                    time.sleep(0.2)
                    continue
                try:
                    ready, _, _ = select.select(list(fds.values()), [], [], 0.2)
                except (OSError, ValueError):
                    for fd in list(fds.values()):
                        drop(fd)
                    break
                for fd in ready:
                    try:
                        data = os.read(fd, _EV * 32)
                    except BlockingIOError:
                        continue
                    except OSError:
                        drop(fd)
                        continue
                    if not data:
                        drop(fd)
                        continue
                    for i in range(0, len(data) - _EV + 1, _EV):
                        _s, _u, typ, code, val = struct.unpack("llHHi", data[i:i + _EV])
                        if typ == 1 and val == 1 and code in _CODES:
                            callback(_CODES[code])
                        elif typ == 1 and val == 0 and code in _CODES:
                            callback("~" + _CODES[code])            # soltado
                        elif typ == 3 and code in _HAT and val in (-1, 1):
                            callback(_HAT[code][0 if val < 0 else 1])
                        elif typ == 3 and code in _HAT and val == 0:   # cruceta al centro: se sueltan las dos direcciones del eje
                            callback("~" + _HAT[code][0])
                            callback("~" + _HAT[code][1])
        for fd in list(fds.values()):
            drop(fd)

    threading.Thread(target=run, daemon=True).start()
