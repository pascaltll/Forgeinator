"""Limpieza de registros para verlos (v2.88): quita los códigos de color (ESC[32m…) y, si se pide, el ruido que no ayuda a diagnosticar.
Lo usan el visor del Hub (COPIAR / GUARDAR) y `bin/hub-logs --trabajo` en la terminal, para que ambos enseñen lo mismo."""
import re

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b|\r")
NOISE = re.compile(
    r"skipping destruction \(fork without exec\?\)"           # ruido de distrobox/podman
    r"|from LD_PRELOAD cannot be preloaded"                    # overlay de Steam de 32 bits
    r"|^\s*\[(tecla|rendimiento|vivo|foco|ventana)\]"          # el diario interno del Hub
    r"|^\[rendimiento\]|^\[trabajo\]\s+\S*\s*\[rendimiento\]"
)


def clean(line) -> str:
    return ANSI.sub("", str(line)).rstrip("\n")


def lines(raw, quiet: bool = True, limit: int | None = None) -> list:
    """Líneas limpias de códigos de color; con quiet=True sin el ruido. `limit` = solo las últimas N."""
    out = [clean(x) for x in raw]
    if quiet:
        out = [x for x in out if not NOISE.search(x)]
    return out[-limit:] if limit else out


def hidden(raw) -> int:
    """Cuántas líneas oculta el modo silencioso."""
    return len(raw) - len(lines(raw, True))


def trabajo(raw, n: int = 80, quiet: bool = True) -> list:
    """Solo las líneas de trabajos ([trabajo] …) de hub.log, sin la etiqueta repetida; para la terminal."""
    out = []
    for x in lines(raw, quiet):
        if x.startswith("[trabajo]"):
            out.append(x[len("[trabajo]"):].lstrip())
    return out[-n:]
