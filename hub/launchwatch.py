"""Vigía de un arranque pedido a Steam (v2.30). Cuando JUGAR pasa por el acceso de Steam, Hub se cierra y no ve la salida del juego:
si no abría, no quedaba NADA (caso BT4). Este proceso aparte mira un minuto si el juego llegó a abrirse y si aguantó; si no, deja el
informe de siempre en launch-logs/ (diagnóstico del .toml, bibliotecas y registro del launcher).

    python -m hub.launchwatch <launcher_id> [nombre]"""
import os
import sys
import time
from pathlib import Path

from . import launchlog

APPEAR, STAY = 60.0, 25.0      # s para que aparezca · s que debe aguantar abierto


def needles(lid: str) -> list:
    """Textos que delatan al juego o a su lanzador en la línea de órdenes de un proceso."""
    out = []
    try:
        t = launchlog._toml(lid)
        d = os.path.expanduser(str(t.get("install_dir") or ""))
        if d:
            out += [d.rstrip("/") + "/", os.path.realpath(d).rstrip("/") + "/"]
    except (OSError, ValueError):
        pass
    return list(dict.fromkeys(out))


def alive(lid: str, nd: list) -> bool:
    me = os.getpid()
    for p in Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) == me:
            continue
        try:
            cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if "launchwatch" in cmd:
            continue
        if any(n in cmd for n in nd) or ("main.py" in cmd and f" {lid}" in cmd and "launcher" in cmd):
            return True
    return False


def watch(lid: str, name: str, is_alive, sleep=time.sleep, now=time.time, appear=APPEAR, stay=STAY, step=1.0):
    """Devuelve (veredicto, segundos): "ok" · "never" (no llegó a abrirse) · "died" (se cerró enseguida)."""
    t0, seen = now(), None
    while True:
        a = is_alive()
        t = now()
        if a and seen is None:
            seen = t
        if seen is None and t - t0 >= appear:
            return "never", t - t0
        if seen is not None:
            if not a:
                return ("died", t - seen) if t - seen < stay else ("ok", t - seen)
            if t - seen >= stay:
                return "ok", t - seen
        sleep(step)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return 2
    lid, name = argv[0], (argv[1] if len(argv) > 1 else argv[0])
    nd = needles(lid)
    time.sleep(2.0)                                   # Steam recibe la orden 2 s después (launch_later)
    verdict, secs = watch(lid, name, lambda: alive(lid, nd))
    if verdict == "ok":
        return 0
    why = ("Steam no llegó a abrir el juego en %d s (lanzado por su acceso de Steam; Hub ya estaba cerrado)" % int(secs) if verdict == "never"
           else "se cerró a los %.0f s de abrirse (lanzado por su acceso de Steam; Hub no pudo capturar su salida)" % secs)
    try:
        md = launchlog.report(lid, name, "desconocido", secs, None, why)
        print(f"[vigia] {lid}: {why} → {md}", file=sys.stderr, flush=True)
    except OSError as ex:
        print(f"[vigia] {lid}: no pude escribir el informe: {ex}", file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
