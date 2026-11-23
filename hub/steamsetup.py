"""Pasar de Big Picture/Game Mode al escritorio para aplicar los cambios a Steam, y volver.
Todo se apoya en `steamos-session-select` (SteamOS/Bazzite). Hub no cierra Steam por su cuenta: eso lo hace `bin/play --steam` en el escritorio."""
import os
import shutil
import subprocess
from pathlib import Path

from . import config

AUTOSTART = Path(os.environ.get("XDG_CONFIG_HOME") or "~/.config").expanduser() / "autostart" / "recomp-hub-steam-setup.desktop"
ARGS = ("--steam-setup",)


def in_game_mode() -> bool:
    return bool(os.environ.get("GAMESCOPE_WAYLAND_DISPLAY") or os.environ.get("SteamGamepadUI") or os.environ.get("SteamDeck") == "1" and not os.environ.get("XDG_CURRENT_DESKTOP"))


def session_tool():
    return shutil.which("steamos-session-select")


def write_autostart(root: Path = None) -> Path:
    root = root or config.ROOT
    AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    AUTOSTART.write_text("[Desktop Entry]\nType=Application\nName=Forgeinator: preparar Steam\n"
                         f"Exec={root}/bin/hub --steam-setup\nX-KDE-autostart-after=panel\nTerminal=false\n", encoding="utf-8")
    return AUTOSTART


def clear_autostart():
    try:
        AUTOSTART.unlink()
    except OSError:
        pass


def _select(tool: str, target: str, wait=8.0, unit: bool = False) -> tuple:
    """Pide el cambio de sesión SIN bloquearse: en Bazzite la herramienta cierra Steam y puede tardar más que cualquier espera.
    (ok, texto). ok si terminó con 0 o si sigue trabajando pasado `wait` s (está haciendo el cambio). La salida queda en data/session-select.log."""
    import time
    log = config.STATE / "session-select.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        fo = open(log, "ab")
        fo.write(f"\n--- {time.strftime('%F %T')} {tool} {target}\n".encode())
        fo.flush()
        cmd = [tool, target]
        env = None
        if unit:     # v2.44: Hub corre como «juego» de Steam y SteamOS Manager rechaza el cambio de sesión de un proceso dentro de un juego
            cmd = [shutil.which("systemd-run"), "--user", "--collect", "--wait", "--quiet", f"--property=StandardOutput=append:{log}",
                   f"--property=StandardError=append:{log}", tool, target]
            env = {k: v for k, v in os.environ.items() if k not in ("LD_PRELOAD",) and not k.startswith("SteamGame") and k != "SteamAppId"}
        pr = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=fo, stderr=subprocess.STDOUT, start_new_session=True, env=env)
        fo.close()
    except OSError as ex:
        return False, str(ex)
    t0 = time.time()
    while time.time() - t0 < wait:
        rc = pr.poll()
        if rc is not None:
            break
        time.sleep(0.1)
    rc = pr.poll()
    try:
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
    except OSError:
        tail = []
    if rc is None:
        return True, "sigue trabajando (cambiando la sesión)"
    return rc == 0, f"código {rc}" + (": " + " | ".join(tail) if tail and rc else "")


def to_desktop() -> tuple:
    """(ok, mensaje). Deja el autostart escrito ANTES de pedir el cambio de sesión; si no hay herramienta, lo borra."""
    tool = session_tool()
    if not tool:
        return False, "No encuentro steamos-session-select: cambia tú al escritorio (Steam → Energía → Cambiar a escritorio) y abre «Forgeinator: preparar Steam»."
    write_autostart()
    errs = []
    for target in ("plasma", "desktop", "plasma-wayland-persistent", "plasma-x11-persistent"):
        if shutil.which("systemd-run"):                 # primero como unidad transitoria del usuario (fuera del «juego»); si no, la llamada directa de siempre
            ok, how = _select(tool, target, unit=True)
            if ok:
                return True, f"Cambiando al escritorio ({target})…"
            errs.append(f"{target} (unidad): {how.split(':')[0]}")
        ok, how = _select(tool, target)
        if ok:
            return True, f"Cambiando al escritorio ({target})…"
        errs.append(f"{target}: {how}")
    clear_autostart()
    try:
        within = "within a game" in (config.STATE / "session-select.log").read_text(encoding="utf-8", errors="replace")[-3000:]
    except OSError:
        within = False
    hint = " SteamOS rechaza el cambio porque Hub corre dentro de un juego de Steam: usa Steam → Energía → Cambiar a escritorio." if within else ""
    return False, "No se pudo cambiar de sesión con steamos-session-select (" + "; ".join(errs)[:300] + ")." + hint + " Detalle en data/session-select.log"


def to_game_mode() -> tuple:
    tool = session_tool()
    if not tool:
        return False, "No encuentro steamos-session-select: vuelve a Big Picture con el acceso «Volver al modo juego» del escritorio."
    try:
        r = subprocess.run([tool, "gamescope"], capture_output=True, text=True, timeout=20)
        return r.returncode == 0, "Volviendo al modo juego…" if r.returncode == 0 else (r.stderr.strip() or "falló el cambio de sesión")
    except (OSError, subprocess.SubprocessError) as ex:
        return False, str(ex)
