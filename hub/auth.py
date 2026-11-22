"""Credenciales de GitHub (token de acceso). Se guardan en ~/.config/recomp-hub/credentials.json (fuera del proyecto, así no se suben a git) con permisos 600 (solo tu usuario; NO cifrado).
Prioridad: variable GITHUB_TOKEN > credenciales guardadas. Nunca se imprimen ni se escriben en los logs."""
import json
import os
import stat

from . import config

FILE = config.CONFIG / "credentials.json"
OLD = config.DATA / "credentials.json"   # ubicación de versiones anteriores (dentro del proyecto)


def _migrate():
    """Si quedó un credentials.json antiguo dentro de data/, lo mueve a la carpeta segura."""
    if OLD != FILE and OLD.exists() and not FILE.exists():
        try:
            FILE.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(FILE.parent, 0o700)
            OLD.replace(FILE)
            os.chmod(FILE, 0o600)
        except OSError:
            pass


_migrate()


_C = [None, {}]


def _read() -> dict:
    """v3.14: se relee solo si el archivo cambió (fecha en ns y tamaño). Ajustes y Buscar preguntan por la sesión en cada fotograma."""
    try:
        st = FILE.stat()
    except OSError:
        _C[0], _C[1] = None, {}
        return {}
    sig = (str(FILE), st.st_mtime_ns, st.st_size)
    if _C[0] != sig:
        try:
            d = json.loads(FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        _C[0], _C[1] = sig, d if isinstance(d, dict) else {}
    return dict(_C[1])


def token() -> str:
    return (os.environ.get("GITHUB_TOKEN") or "").strip() or str(_read().get("token", "")).strip()


def login() -> str:
    return str(_read().get("login", ""))


def stored() -> bool:
    return bool(_read().get("token"))


def save(tok: str, login_name: str = "", via: str = "") -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(FILE.parent, 0o700)
    except OSError:
        pass
    data = {"token": tok.strip(), "login": login_name, "via": via}
    fd = os.open(FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.chmod(FILE, 0o600)
    _C[0] = None


def set_login(name: str) -> None:
    d = _read()
    if d.get("token"):
        save(d["token"], name, d.get("via", ""))


def clear() -> bool:
    """Borra SOLO las credenciales guardadas por Hub (no toca la variable GITHUB_TOKEN del entorno)."""
    _C[0] = None
    try:
        FILE.unlink()
        return True
    except OSError:
        return False
