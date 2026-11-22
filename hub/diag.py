"""Exportar diagnóstico de UN juego (v2.81): un solo archivo `~/diag-<id>.md` con todo lo necesario para ver por qué no arranca o se queda en negro,
sin tener que teclear comandos: historial con la foto del entorno, informes de arranque, registros de Proton/Wine/launcher, scripts de arranque (hub-run.sh,
hub-container.sh), .toml, .hub-versions.json, listado de carpetas, contenedores y la parte de hub.log que habla del juego.
Las líneas con token/clave/contraseña se tapan. No toca nada del juego: solo lee."""
import json
import re
import subprocess
import time
from pathlib import Path

from . import config, history, launchlog

SECRET = re.compile(r"(?i)(\b\w*(?:token|key|secret|passw(?:or)?d|cookie|authorization|bearer)\w*\s*[=:]\s*)\S+")
MAXB = 60000


def _redact(t: str) -> str:
    return SECRET.sub(r"\1***", t)


def _tail(path, n=150) -> str:
    try:
        data = Path(path).read_bytes()[-MAXB:].decode("utf-8", "replace")
    except OSError:
        return "(no existe o no se puede leer)"
    return "\n".join(data.splitlines()[-n:])


def _head(path, n=80) -> str:
    try:
        return "\n".join(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[:n])
    except OSError:
        return "(no existe)"


def _sec(L, title, body, lang=""):
    L += [f"## {title}", f"```{lang}", _redact(str(body)).rstrip() or "(vacío)", "```", ""]


def _ls(d: Path, depth=1) -> str:
    try:
        r = subprocess.run(["ls", "-la", "--time-style=long-iso", str(d)], capture_output=True, text=True, timeout=6)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return "(no se pudo listar)"


def build(lid: str, name: str = "", folder: str = "", version: str = "") -> Path:
    from . import osver
    L = [f"# Diagnóstico de {name or lid} ({lid})", "", f"- Generado: {time.strftime('%Y-%m-%d %H:%M:%S')} · Hub {launchlog._version()}", ""]
    _sec(L, "Historial (configuraciones y errores)", history.text(lid, name or lid))
    snap = history.snapshot(lid, version)
    _sec(L, "Entorno ahora", json.dumps(snap, indent=1, ensure_ascii=False), "json")
    root = None
    try:
        root = osver.root_of(lid)
    except (OSError, ValueError, KeyError):
        pass
    if root is not None:
        root = Path(root)
        _sec(L, f"Carpeta del juego: {root}", _ls(root))
        for sub in ("linux", "windows"):
            if (root / sub).is_dir():
                _sec(L, f"{root / sub}", _ls(root / sub))
        _sec(L, ".hub-versions.json", _head(root / ".hub-versions.json", 60), "json")
        for rel in ("hub-run.sh", "linux/hub-run.sh", "linux/hub-container.sh", "windows/hub-run.sh"):
            p = root / rel
            if p.is_file():
                _sec(L, rel, _head(p, 70), "bash")
        for rel in ("windows/hub-wine.log", "windows/proton-logs/steam-0.log", "proton-logs/steam-0.log", "linux/hub-run.log"):
            p = root / rel
            if p.is_file():
                _sec(L, f"{rel} (últimas líneas)", _tail(p, 120))
        for p in sorted(root.glob("**/proton-logs/*.log"))[:2] + sorted(root.glob("**/steam-*.log"))[:1]:
            if p.is_file() and not any(str(p).endswith(r) for r in ("proton-logs/steam-0.log",)):
                _sec(L, f"{p.relative_to(root)} (últimas líneas)", _tail(p, 120))
    toml = config.LAUNCHER / "games" / f"{lid}.toml"
    _sec(L, f"{toml}", _head(toml, 90), "toml")
    _sec(L, "Registro del launcher (state/<id>.log)", _tail(config.LAUNCHER / "state" / f"{lid}.log", 80))
    for rp in launchlog.reports(lid)[-2:]:
        _sec(L, f"Informe de arranque {Path(rp).name}", _tail(rp, 160))
    try:
        r = subprocess.run(["distrobox", "list", "--no-color"], capture_output=True, text=True, timeout=8)
        _sec(L, "distrobox list", r.stdout or r.stderr)
    except (OSError, subprocess.SubprocessError):
        _sec(L, "distrobox list", "(distrobox no disponible)")
    hl = config.DATA / "hub.log"
    try:
        lines = [ln for ln in hl.read_text(encoding="utf-8", errors="replace").splitlines() if lid in ln or "[trabajo]" in ln or "[instalar]" in ln][-80:]
    except OSError:
        lines = ["(no hay hub.log)"]
    _sec(L, "hub.log (líneas de este juego, instalaciones y trabajos)", "\n".join(lines))
    out = Path.home() / f"diag-{re.sub(r'[^A-Za-z0-9._-]+', '-', lid)}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out
