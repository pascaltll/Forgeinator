"""v3.14: tope de hub.log durante la sesión. bin/hub lo rota al arrancar (> 1 MB → hub.log.old), pero en una sesión larga las compilaciones
escriben cada línea ([trabajo]) y el archivo puede crecer muchos MB. El latido [vivo] llama aquí cada 2 min: si pasa de LIMIT, copia el
contenido a hub.log.old y vacía hub.log. Es seguro porque bin/hub lo abre en modo añadir (`>>` o `tee -a`, O_APPEND): las líneas
siguientes se escriben al principio del archivo vacío, sin huecos. Si no se puede comprobar ese modo, no toca nada."""
import os
import shutil
from pathlib import Path

LIMIT = 8 * 1024 * 1024
O_APPEND = 0o2000


def _append_mode(log: Path) -> bool:
    """¿El stderr de este proceso escribe en `log` en modo añadir, o va a una tubería (tee -a de bin/hub)?"""
    try:
        tgt = os.readlink("/proc/self/fd/2")
    except OSError:
        return False
    if tgt.startswith("pipe:"):
        return True                                   # bin/hub con terminal: `tee -a`, que abre el archivo con O_APPEND
    try:
        if Path(tgt).resolve() != log.resolve():
            return False
        for ln in open("/proc/self/fdinfo/2"):
            if ln.startswith("flags:"):
                return bool(int(ln.split()[1], 8) & O_APPEND)
    except (OSError, ValueError):
        pass
    return False


def maybe_rotate(log: Path, limit: int = LIMIT, check_mode=_append_mode) -> bool:
    try:
        if log.stat().st_size <= limit or not check_mode(log):
            return False
        shutil.copyfile(log, log.with_name(log.name + ".old"))
        os.truncate(log, 0)
        return True
    except OSError:
        return False
