"""Accesos de Steam de tus juegos (shortcuts.vdf, formato binario) para abrir un juego «como él mismo» en Big Picture:
con su nombre, su arte y su propia entrada en el selector de ventanas, en vez de como si fuera Recomp Hub.

Steam agrupa todo lo que lanza un juego no-Steam bajo ese juego (aunque sea un proceso hijo), así que si Hub lanza el juego directamente,
Big Picture lo muestra como «Recomp Hub». Si el juego ya tiene acceso (lo crea `bin/play --steam` o AÑADIR A STEAM), Hub le pide a Steam
`steam://rungameid/<id>` justo después de cerrarse, desde fuera de su propio árbol de procesos (systemd-run --user), y Steam lo abre como esa app."""
import os
import shutil
import struct
import subprocess
from pathlib import Path

ROOTS = ("~/.local/share/Steam", "~/.steam/steam", "~/.steam/root", "~/.var/app/com.valvesoftware.Steam/data/Steam")


def parse_vdf(data: bytes) -> dict:
    """Lector mínimo del VDF binario de Steam (mapas 0x00, cadenas 0x01, enteros de 32 bits 0x02, fin de mapa 0x08)."""
    pos = 0

    def cstr():
        nonlocal pos
        end = data.index(b"\x00", pos)
        s = data[pos:end].decode("utf-8", "replace")
        pos = end + 1
        return s

    def mapping():
        nonlocal pos
        out = {}
        while pos < len(data):
            t = data[pos]
            pos += 1
            if t == 0x08:
                return out
            k = cstr()
            if t == 0x00:
                out[k] = mapping()
            elif t == 0x01:
                out[k] = cstr()
            elif t == 0x02:
                out[k] = struct.unpack_from("<i", data, pos)[0]
                pos += 4
            elif t == 0x07:
                out[k] = struct.unpack_from("<Q", data, pos)[0]
                pos += 8
            else:
                raise ValueError(f"tipo VDF desconocido 0x{t:02x}")
        return out
    return mapping()


def shortcut_files() -> list:
    seen, out = set(), []
    for r in ROOTS:
        base = Path(os.path.expanduser(r)) / "userdata"
        try:
            for f in base.glob("*/config/shortcuts.vdf"):
                rp = f.resolve()
                if rp not in seen:
                    seen.add(rp)
                    out.append(f)
        except OSError:
            continue
    return sorted(out, key=lambda f: -f.stat().st_mtime)


def shortcuts() -> list:
    """[{appid, name, exe, options, start}] de todos los usuarios de Steam de este equipo."""
    res = []
    for f in shortcut_files():
        try:
            d = parse_vdf(f.read_bytes())
        except (OSError, ValueError, struct.error, IndexError):
            continue
        sc = d.get("shortcuts") or d.get("Shortcuts") or {}
        for v in sc.values():
            if not isinstance(v, dict):
                continue
            g = {k.lower(): x for k, x in v.items()}
            res.append({"appid": g.get("appid"), "name": g.get("appname", ""), "exe": str(g.get("exe", "")).strip('"'),
                        "options": str(g.get("launchoptions", "")), "start": str(g.get("startdir", "")).strip('"')})
    return res


def find(lid: str, name: str = "", items=None) -> dict | None:
    """El acceso de Steam de este juego del launcher: el de shortcuts/<lid>.sh o `bin/play <lid>`; si no, uno con el mismo nombre."""
    items = shortcuts() if items is None else items
    for s in items:
        if s["appid"] is None:
            continue
        exe, opts = s["exe"], s["options"].split()
        if exe.endswith(f"/shortcuts/{lid}.sh") or (exe.endswith("/bin/play") and opts[:1] == [lid]) or (exe.endswith("/play") and lid in opts):
            return s
    n = name.strip().lower()
    if n:
        for s in items:
            if s["appid"] is not None and s["name"].strip().lower() == n:
                return s
    return None


def game_id(appid: int) -> int:
    """Id para steam://rungameid de un acceso no-Steam."""
    return ((int(appid) & 0xFFFFFFFF) << 32) | 0x02000000


def launch_later(appid: int, delay=2) -> tuple:
    """Pide a Steam que abra el acceso dentro de `delay` s, desde una unidad de systemd del usuario (fuera del árbol de procesos de Hub,
    así Steam no lo cuenta como parte de Hub y Hub puede cerrarse antes). Devuelve (ok, cómo)."""
    st = shutil.which("steam")
    if not st:
        return False, "no encuentro el comando steam"
    url = f"steam://rungameid/{game_id(appid)}"
    sr = shutil.which("systemd-run")
    if sr:
        try:
            p = subprocess.run([sr, "--user", "--collect", "--quiet", f"--on-active={delay}", "--timer-property=AccuracySec=100ms", st, url],
                               capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                return True, f"systemd-run → {url}"
            why = (p.stderr or p.stdout).strip()[-200:]
        except (OSError, subprocess.SubprocessError) as ex:
            why = str(ex)
    else:
        why = "sin systemd-run"
    try:
        subprocess.Popen([st, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True, f"steam directo ({why})"
    except OSError as ex:
        return False, str(ex)


def watch_launch(lid: str, name: str) -> str:
    """Deja un vigía aparte (hub.launchwatch) que escribe un informe si el juego pedido a Steam no abre o se cierra enseguida.
    Va en una unidad de systemd del usuario para sobrevivir al cierre de Hub. Devuelve cómo se lanzó ("" si no se pudo)."""
    import sys
    if os.environ.get("HUB_NO_WATCH"):
        return ""
    root = str(Path(__file__).resolve().parent.parent)
    argv = [sys.executable, "-m", "hub.launchwatch", lid, name]
    sr = shutil.which("systemd-run")
    if sr:
        envs = [f"--setenv={k}={os.environ[k]}" for k in ("HUB_DATA", "LAUNCHER_DIR", "HUB_GAMES", "HOME", "PATH", "PYTHONUSERBASE") if os.environ.get(k)]
        try:
            p = subprocess.run([sr, "--user", "--collect", "--quiet", f"--working-directory={root}", *envs, *argv], capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                return "systemd-run"
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return "proceso suelto"
    except OSError:
        return ""
