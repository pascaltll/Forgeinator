"""Doctor: comprobaciones rápidas de los problemas que ya nos han dado guerra. Cada una devuelve (estado, texto, pista)
con estado 'ok' | 'aviso' | 'fallo'. Sin red salvo la prueba TLS opcional."""
import os
import shutil
import socket
import ssl
import sys
from pathlib import Path

from . import config


def _display():
    if sys.platform != "linux":
        return ("ok", "Pantalla", "")
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"):
        return ("ok", "Pantalla: DISPLAY/WAYLAND definido", "")
    return ("fallo", "Sin DISPLAY ni WAYLAND_DISPLAY", "Lanza Hub desde el escritorio o con DISPLAY=:0 (por SSH hace falta exportarlo).")


def _xauth():
    if os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("XAUTHORITY") and not (Path.home() / ".Xauthority").exists():
        return ("aviso", "DISPLAY sin XAUTHORITY", "Por SSH exporta XAUTHORITY (en Bazzite: /run/user/1000/xauth_*).")
    return ("ok", "XAUTHORITY correcto", "")


def _disk():
    try:
        free = shutil.disk_usage(config.GAMES_DIR if config.GAMES_DIR.exists() else Path.home()).free / 1e9
    except OSError:
        return ("aviso", "No pude medir el disco", "")
    if free < 2:
        return ("fallo", f"Quedan {free:.1f} GB libres", "Libera espacio antes de descargar o compilar.")
    if free < 10:
        return ("aviso", f"Quedan {free:.1f} GB libres", "Pocos para compilar juegos grandes.")
    return ("ok", f"{free:.0f} GB libres", "")


def _launcher():
    if (config.LAUNCHER / "launcher").exists() or (config.LAUNCHER / "bin").exists() or config.LAUNCHER.exists():
        return ("ok", f"Launcher presente ({config.LAUNCHER})", "")
    return ("aviso", "No encuentro el launcher unificado", "Sin él, JUGAR y las carátulas del launcher no funcionan.")


def _duplicates():
    d = config.LAUNCHER / "games"
    seen, dup = {}, []
    try:
        for t in sorted(d.glob("*.toml")):
            import re
            m = re.search(r'install_dir\s*=\s*"([^"]+)"', t.read_text(encoding="utf-8", errors="replace"))
            if m:
                k = m.group(1).rstrip("/")
                if k in seen:
                    dup.append(f"{seen[k]} y {t.name}")
                seen[k] = t.name
    except OSError:
        pass
    if dup:
        return ("aviso", f"{len(dup)} juego(s) comparten carpeta: {dup[0]}", "Dos .toml con el mismo install_dir confunden «instalado».")
    return ("ok", "Sin .toml duplicados", "")


def _setup():
    bad = []
    try:
        for p in config.GAMES_DIR.iterdir():
            if p.is_dir() and any(p.glob("*-setup*")):
                bad.append(p.name)
    except OSError:
        pass
    if bad:
        return ("aviso", f"Instaladores sin ejecutar en {bad[0]}", "Un *-setup* suele ser un instalador de Windows: no es el juego.")
    return ("ok", "Sin instaladores sueltos", "")


def _tls(host="api.github.com", timeout=6):
    try:
        ip = socket.getaddrinfo(host, 443, socket.AF_INET)[0][4][0]
        with socket.create_connection((ip, 443), timeout) as s:
            ssl.create_default_context().wrap_socket(s, server_hostname=host).close()
        return ("ok", f"TLS a {host} por IPv4", "")
    except Exception as ex:  # noqa: BLE001
        return ("fallo", f"TLS a {host} falla ({type(ex).__name__})", "Prueba otra red o define HTTPS_PROXY; el cliente ya fuerza IPv4 y reintenta.")


def checks(network=True):
    fs = [_display, _xauth, _disk, _launcher, _duplicates, _setup] + ([_tls] if network else [])
    out = []
    for f in fs:
        try:
            out.append(f())
        except Exception as ex:  # noqa: BLE001
            out.append(("aviso", f"{f.__name__}: {type(ex).__name__}", ""))
    return out


def report(network=True) -> str:
    mark = {"ok": "✓", "aviso": "!", "fallo": "✗"}
    ls = []
    for st, txt, hint in checks(network):
        ls.append(f"{mark[st]} {txt}" + (f"\n    → {hint}" if hint and st != "ok" else ""))
    return "\n".join(ls)


if __name__ == "__main__":
    print(report("--no-net" not in sys.argv))
