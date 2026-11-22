"""v3.10 · Arranque directo de los juegos (sin la pantalla previa del launcher: comprobación de actualizaciones, novedades y cuenta atrás).

Ahora que Hub instala, actualiza y compila, esa pantalla sobra. Dos caminos:
  · JUGAR desde Hub sin Steam: Hub ejecuta hub/playdirect.py <id> en vez de launcher/bin/play <id>.
  · JUGAR por el acceso de Steam (lo normal en Modo Juego): Steam abre launcher/shortcuts/<id>.sh. Hub reescribe ese .sh para que
    llame a playdirect.py; el original (generado por `play --shortcuts`) se guarda al lado como <id>.sh.launcher. Al apagar la opción
    se restaura. El acceso de Steam no cambia (misma ruta), así que no hay que tocar Steam.
Solo se tocan los .sh generados por el launcher (llevan su marca) o los que ya escribió Hub; uno hecho a mano no se toca.
playdirect.py cede a bin/play si algo falla antes de abrir el juego."""
import os
import shutil
from pathlib import Path

from . import config

SCRIPT = Path(__file__).resolve().with_name("playdirect.py")
LAUNCHER_MARK = "# generado por launcher"
HUB_MARK = "# Recomp Hub: arranque directo"
BACKUP_SUFFIX = ".launcher"


def command(lid: str, python=None) -> list:
    """Comando para abrir el juego sin la pantalla del launcher (desde Hub)."""
    import sys
    return [python or sys.executable, str(SCRIPT), "--root", str(config.LAUNCHER), lid]


def shortcut_text(lid: str) -> str:
    return ("#!/usr/bin/env bash\n"
            f"{HUB_MARK} (sin la pantalla del launcher). El original está en {lid}.sh{BACKUP_SUFFIX}; "
            "se restaura desde Hub › Ajustes › Al jugar.\n"
            'export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"\n'
            '[ -z "${DISPLAY:-}" ] && export DISPLAY=:0\n'
            f'HUBPLAY="{SCRIPT}"\n'
            'if [ -f "$HUBPLAY" ]; then\n'
            '  for py in python3 /usr/bin/python3 "$HOME/miniforge3/bin/python3"; do\n'
            '    if command -v "$py" >/dev/null 2>&1 && "$py" -c "import tomllib" >/dev/null 2>&1; then\n'
            f'      exec "$py" "$HUBPLAY" --root "$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)" {lid} "$@"\n'
            "    fi\n"
            "  done\n"
            "fi\n"
            f'exec "$(dirname "$(readlink -f "$0")")/../bin/play" {lid} "$@"\n')


def _launcher_text(lid: str) -> str:
    return ("#!/usr/bin/env bash\n# generado por launcher (play --shortcuts): no lo edites, se regenera\n"
            f'exec "$(dirname "$(readlink -f "$0")")/../bin/play" {lid} "$@"\n')


def _write(p: Path, txt: str):
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(txt, encoding="utf-8")
    tmp.chmod(0o755)
    os.replace(tmp, p)


def state(lid: str) -> str:
    """«direct» (lo escribió Hub) · «launcher» (el generado por el launcher) · «custom» (hecho a mano) · «none» (no hay acceso)."""
    p = config.LAUNCHER / "shortcuts" / f"{lid}.sh"
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "none"
    return "direct" if HUB_MARK in txt else "launcher" if LAUNCHER_MARK in txt else "custom"


def set_shortcut(lid: str, direct: bool) -> bool:
    """Pone (o quita) el arranque directo en el acceso de Steam de un juego. True si cambió algo."""
    p = config.LAUNCHER / "shortcuts" / f"{lid}.sh"
    st = state(lid)
    if direct and st == "launcher":
        shutil.copy2(p, p.with_name(p.name + BACKUP_SUFFIX))
        _write(p, shortcut_text(lid))
        return True
    if direct and st == "direct" and p.read_text(encoding="utf-8", errors="replace") != shortcut_text(lid):
        _write(p, shortcut_text(lid))          # Hub cambió de sitio: se actualiza la ruta
        return True
    if not direct and st == "direct":
        b = p.with_name(p.name + BACKUP_SUFFIX)
        txt = b.read_text(encoding="utf-8", errors="replace") if b.is_file() else _launcher_text(lid)
        _write(p, txt)
        return True
    return False


def apply_all(direct: bool) -> int:
    """Todos los accesos de shortcuts/. Devuelve cuántos cambió."""
    d = config.LAUNCHER / "shortcuts"
    n = 0
    if not d.is_dir():
        return 0
    for p in sorted(d.glob("*.sh")):
        try:
            n += set_shortcut(p.stem, direct)
        except OSError:
            continue
    return n
