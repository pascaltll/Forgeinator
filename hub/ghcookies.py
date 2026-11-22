"""Cookies de GitHub exportadas del navegador (Cookie-Editor / EditThisCookie, JSON). Se filtran a las imprescindibles de sesión y se guardan:
  · data/github-cookies.json (0600) → copia local de las cookies importadas;
  · GITHUB_COOKIES=… en el .env del launcher (0600) → cabecera Cookie para scripts.
Nunca se imprimen valores."""
import json
import os
from pathlib import Path

from . import config, sgdb

ESSENTIAL = ("user_session", "__Host-user_session_same_site", "logged_in", "dotcom_user", "_device_id", "saved_user_sessions", "_gh_sess")
ENV = "GITHUB_COOKIES"


def _file() -> Path:
    return config.DATA / "github-cookies.json"


def parse(text: str) -> list:
    """Filtra a cookies esenciales de github.com. Lanza ValueError si el archivo no sirve."""
    try:
        rows = json.loads(text)
    except ValueError as ex:
        raise ValueError("no es un JSON válido (exporta con Cookie-Editor → Export → JSON)") from ex
    if not isinstance(rows, list):
        raise ValueError("el JSON debe ser una lista de cookies")
    out = []
    for c in rows:
        if not isinstance(c, dict):
            continue
        dom = str(c.get("domain", ""))
        if (dom == "github.com" or dom.endswith(".github.com")) and c.get("name") in ESSENTIAL and c.get("value"):
            out.append(c)
    if not any(c["name"] in ("user_session", "__Host-user_session_same_site") for c in out):
        raise ValueError("no hay cookie de sesión de github.com (¿exportaste con la sesión iniciada?)")
    return out


def header(cookies: list) -> str:
    seen = {}
    for c in cookies:
        seen[c["name"]] = c["value"]
    return "; ".join(f"{k}={v}" for k, v in seen.items())


def save(cookies: list) -> Path:
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
    os.chmod(f, 0o600)
    sgdb.env_set(ENV, header(cookies))            # escribe en ~/Games/launcher/.env con permisos 0600
    return f


def import_file(path) -> tuple:
    """(ruta_json, usuario|''). ValueError con mensaje claro si no sirve."""
    cs = parse(Path(path).read_text(encoding="utf-8"))
    f = save(cs)
    user = next((c["value"] for c in cs if c["name"] == "dotcom_user"), "")
    return f, user


def saved() -> bool:
    return _file().is_file()


def user() -> str:
    try:
        return next((c["value"] for c in json.loads(_file().read_text(encoding="utf-8")) if c.get("name") == "dotcom_user"), "")
    except (OSError, ValueError):
        return ""


def forget():
    try:
        _file().unlink()
    except OSError:
        pass
    f = config.LAUNCHER / ".env"
    try:
        ls = [ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.strip().removeprefix("export ").startswith(ENV + "=")]
        f.write_text("\n".join(ls) + ("\n" if ls else ""), encoding="utf-8")
    except OSError:
        pass
