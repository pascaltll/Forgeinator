"""Actualización de Hub desde zip: sondeo (¿hay una versión nueva en ~/Games/actualizaciones?) y aplicación + reinicio.
La lógica de instalar vive en bin/hub-update (script independiente: sigue funcionando aunque el código de Hub esté roto)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "hub-update"


def probe(timeout=15):
    """{current, new, file}; new=None si no hay nada. Nunca lanza: si falla devuelve {current, new: None, error}."""
    try:
        r = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, timeout=timeout, env=dict(os.environ, HUB_DIR=str(ROOT)))
        d = json.loads((r.stdout or "").strip().splitlines()[-1])
        return d if isinstance(d, dict) else {"new": None}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as ex:
        return {"current": "?", "new": None, "error": str(ex)}


def apply(timeout=600):
    """Instala lo pendiente. Devuelve (ok, texto_de_salida)."""
    try:
        r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=timeout, env=dict(os.environ, HUB_DIR=str(ROOT)))
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        return ("✓ Recomp Hub" in out or "✓ Craftinador" in out or "✓ Forgeinator" in out), out
    except (OSError, subprocess.SubprocessError) as ex:
        return False, str(ex)


def restart():
    """Reinicia Hub tras actualizar. Dentro de bin/hub (HUB_WRAPPER=1) solo deja una marca y es el propio wrapper, que Steam ya
    vigila, quien relanza: una copia lanzada por fuera moría cuando Steam daba por terminado el «juego» al salir el Hub viejo."""
    if os.environ.get("HUB_WRAPPER"):
        try:
            (ROOT / "data").mkdir(parents=True, exist_ok=True)
            (ROOT / "data" / "restart.flag").write_text("1")
            return
        except OSError:
            pass
    launcher = ROOT / "bin" / "hub"
    subprocess.Popen(["sh", "-c", 'sleep 1; HUB_NOUPDATE=1 exec "$0"', str(launcher)], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(ROOT))
