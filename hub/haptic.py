"""Vibración de los mandos (v2.85): un golpecito al mantener pulsado un juego. Usa los mandos que Hub ya tiene abiertos (SDL), así que no abre nada nuevo
ni duplica pulsaciones. Si no hay mando, o no soporta vibración (el táctil de la pantalla no vibra por sí solo en Linux), no hace nada y no molesta.
Sin verificar en el Ally: depende de que SDL vea el mando integrado con vibración."""
import time

PATTERNS = {                    # (motor grave 0..1, motor agudo 0..1, milisegundos)
    "hold": (0.35, 0.55, 55),   # al abrir el menú del juego: un toque corto y claro
    "tick": (0.0, 0.3, 25),     # una marca muy suave (reservado)
}
stats = {"sent": 0, "failed": 0}


def pulse(ui, kind: str = "hold") -> bool:
    """Devuelve True si algún mando recibió la orden."""
    if not ui.cfg.get("haptics", True):
        return False
    low, high, ms = PATTERNS.get(kind, PATTERNS["hold"])
    ok = False
    for c in list((getattr(ui, "ctrls", None) or {}).values()):
        try:
            c.rumble(low, high, ms)
            ok = True
        except Exception:  # noqa: BLE001 — sin soporte de vibración: se ignora
            stats["failed"] += 1
    if ok:
        stats["sent"] += 1
        stats["last"] = time.time()
    return ok
