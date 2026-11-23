"""v3.24 · E3: informes de error y sugerencias.

- record_crash(): guarda cada error (cierre del Hub o excepción en un fotograma) en STATE/errores/, con contexto (pantalla, tema, versión, canal).
- build(): arma el informe (versión, sistema, contexto, lo que escribió el usuario, último error, final de hub.log y de forgeinatord.log).
- Redactor: tapa los secretos ANTES de que el texto salga a ningún sitio:
    · los valores reales de tus credenciales (credentials.json, remotes-secrets.json, cookies de GitHub, .env, clave de SteamGridDB,
      variables de entorno con TOKEN/KEY/SECRET/PASS en el nombre), estén donde estén en el texto;
    · patrones: tokens de GitHub, «Bearer …», «clave=valor», cookies, usuario:contraseña@ en direcciones;
    · tu usuario en las rutas (/home/<usuario> → ~), el nombre del equipo y las IP (salvo 127.0.0.1).
- Salidas: save_zip() (informe.md + registros, ya tapados) e issue_url() (issue de GitHub ya rellenado, por enlace: sin token).
Nada sale del equipo sin que el usuario lo vea antes en la vista previa."""
import getpass
import json
import os
import platform
import re
import socket
import sys
import time
import traceback
import urllib.parse
import zipfile
from pathlib import Path

from . import config

REPO = "pascaltll/Forgeinator"
MAX_CRASHES = 20
URL_MAX = 7000                                   # GitHub corta las direcciones muy largas (~8 kB)
CTX = {}                                         # lo pone la interfaz: pantalla, página de ajustes, tema…
_last_sig = {"sig": None}

SECRET_KV = re.compile(r"(?i)(\b[\w.-]*(?:token|key|secret|passw(?:or)?d|pwd|cookie|authorization|session)[\w.-]*[\"']?\s*[=:]\s*[\"']?)"
                       r"(?!\*\*\*)[^\s\"',;}]+")
PATTERNS = [
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,})"), "***"),
    (re.compile(r"(?i)\b(bearer|token|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 ***"),
    (re.compile(r"(?i)(cookie:\s*).*"), r"\1***"),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"), r"\1***@"),        # usuario:contraseña@ en una dirección
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+@"), r"\1***@"),
]
_OCT = r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
IP = re.compile(rf"(?<![\d.])(?!127\.0\.0\.1(?![\d.]))(?:{_OCT}\.){{3}}{_OCT}(?![\d.])")


def crash_dir() -> Path:
    return config.STATE / "errores"


def _strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _strings(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _strings(v, out)


def _secret_files():
    c = config.CONFIG
    fs = list(c.rglob("*.json")) if c.is_dir() else []
    fs += [c / ".env", config.DATA / ".env", config.ROOT / ".env", config.DATA / "github-cookies.json",
           config.LAUNCHER / ".env", config.LAUNCHER / "state" / ".sgdb_key", config.LAUNCHER / "state" / ".sgdb_key.prev",
           Path.home() / ".config" / "recomp-hub" / "credentials.json"]
    return fs


def secret_values() -> set:
    """Los valores reales de tus secretos (para taparlos aunque aparezcan sin «clave=» delante)."""
    vals = []
    for f in _secret_files():
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if f.suffix == ".json":
            try:
                _strings(json.loads(txt), vals)
                continue
            except ValueError:
                pass
        for ln in txt.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            v = ln.split("=", 1)[1] if "=" in ln else ln
            vals.append(v.strip().strip("\"'"))
    for k, v in os.environ.items():
        if re.search(r"(?i)token|key|secret|pass|cookie|auth", k) and not re.search(r"(?i)keyboard|keymap|xkb|pass_?through", k):
            vals.append(v)
    # cortos o triviales no: taparían palabras normales («true», «dark», rutas)
    return {v for v in vals if len(v) >= 8 and not v.startswith(("/", "~", "http://", "https://")) and v.lower() not in ("true", "false", "null")}


class Redactor:
    def __init__(self, extra=()):
        self.values = sorted(secret_values() | {v for v in extra if v and len(v) >= 6}, key=len, reverse=True)
        self.home = str(Path.home())
        try:
            self.user = getpass.getuser()
        except Exception:  # noqa: BLE001
            self.user = ""
        h = socket.gethostname().split(".")[0]
        self.host = h if len(h) >= 4 and not re.fullmatch(r"[\d-]+", h) and h != self.user else ""

    def __call__(self, text: str) -> str:
        t = str(text)
        for v in self.values:
            t = t.replace(v, "***")
        for rx, rep in PATTERNS:
            t = rx.sub(rep, t)
        t = SECRET_KV.sub(r"\1***", t)
        if self.home and self.home != "/":
            t = re.sub(rf"(?<![\w/.-]){re.escape(self.home)}(?![\w.-])", "~", t)
        if self.user and len(self.user) >= 3:
            t = re.sub(rf"(/(?:var/)?home/){re.escape(self.user)}\b", r"\1<usuario>", t)
            t = re.sub(rf"\b{re.escape(self.user)}@", "<usuario>@", t)
        if self.host:
            t = re.sub(rf"\b{re.escape(self.host)}\b", "<equipo>", t)
        return IP.sub("<ip>", t)


# ---------------------------------------------------------------- errores guardados
def _sig(tb_txt: str) -> str:
    frames = re.findall(r'File "([^"]+)", line (\d+)', tb_txt)
    last = tb_txt.strip().splitlines()[-1] if tb_txt.strip() else ""
    return "|".join(f"{Path(f).name}:{n}" for f, n in frames[-4:]) + "|" + last.split(":")[0]


def record_crash(etype, value, tb, where="ui", fatal=True) -> Path | None:
    """Guarda el error con su contexto. Los errores de fotograma que se repiten (misma pila) se guardan una sola vez."""
    try:
        txt = "".join(traceback.format_exception(etype, value, tb))
        sig = _sig(txt)
        if not fatal and sig == _last_sig["sig"]:
            return None
        _last_sig["sig"] = sig
        d = crash_dir()
        d.mkdir(parents=True, exist_ok=True)
        ts = time.time()
        rec = {"ts": ts, "fatal": bool(fatal), "where": where, "version": config.VERSION, "channel": config.CHANNEL or "",
               "error": f"{getattr(etype, '__name__', etype)}: {value}", "traceback": txt, "sig": sig, "ctx": dict(CTX)}
        p = d / f"error-{time.strftime('%Y%m%d-%H%M%S', time.localtime(ts))}-{int(ts * 1000) % 1000:03d}.json"
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        for old in sorted(d.glob("error-*.json"))[:-MAX_CRASHES]:
            old.unlink(missing_ok=True)
        return p
    except Exception as ex:  # noqa: BLE001  (registrar un error nunca debe provocar otro)
        print(f"[informe] no pude guardar el error: {ex}", file=sys.stderr, flush=True)
        return None


def crashes() -> list:
    out = []
    for p in sorted(crash_dir().glob("error-*.json"), reverse=True):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
            r["file"] = str(p)
            out.append(r)
        except (OSError, ValueError):
            continue
    return out


def _seen_file() -> Path:
    return crash_dir() / ".visto"


def unseen_fatal() -> dict | None:
    """El último cierre por error que aún no se ha avisado (para el aviso al arrancar)."""
    try:
        seen = float(_seen_file().read_text().strip())
    except (OSError, ValueError):
        seen = 0.0
    for r in crashes():
        if r.get("fatal") and r.get("ts", 0) > seen:
            return r
    return None


def mark_seen():
    try:
        crash_dir().mkdir(parents=True, exist_ok=True)
        newest = max([r.get("ts", 0) for r in crashes()] + [time.time()])
        _seen_file().write_text(repr(newest))
    except OSError:
        pass


# ---------------------------------------------------------------- informe
def _tail(p: Path, n: int) -> list:
    try:
        data = p.read_bytes()[-400_000:].decode("utf-8", "replace")
    except OSError:
        return []
    from . import logview
    return logview.lines(data.splitlines(), True, n)


def _os_name() -> str:
    try:
        for ln in Path("/etc/os-release").read_text().splitlines():
            if ln.startswith("PRETTY_NAME="):
                return ln.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.system()


def system_info() -> dict:
    info = {"Sistema": _os_name(), "Núcleo": platform.release(), "Python": platform.python_version()}
    try:
        import pygame
        info["pygame / SDL"] = f"{pygame.version.ver} / {'.'.join(map(str, pygame.version.SDL))}"
        if pygame.display.get_init():
            info["Vídeo"] = f"{pygame.display.get_driver()} {'x'.join(map(str, pygame.display.get_window_size() or ()))}".strip()
    except Exception:  # noqa: BLE001
        pass
    gm = "Big Picture (gamescope)" if os.environ.get("SteamGameId") or os.environ.get("GAMESCOPE_WAYLAND_DISPLAY") else "escritorio"
    info["Modo"] = gm
    try:
        dmi = Path("/sys/class/dmi/id/product_name").read_text().strip()
        if dmi:
            info["Equipo"] = dmi
    except OSError:
        pass
    return info


KINDS = {"error": ("Informe de error", "bug", "[Fallo] "), "idea": ("Sugerencia", "enhancement", "[Idea] ")}


def build(kind="error", note="", crash=None, log_lines=200, red=None) -> dict:
    """Arma el informe YA TAPADO. Devuelve {title, md, files: {nombre: texto}, issue_body, kind}."""
    red = red or Redactor()
    title_k, _, pre = KINDS.get(kind, KINDS["error"])
    if crash is None and kind == "error":
        cs = crashes()
        crash = cs[0] if cs else None
    L = [f"# Forgeinator · {title_k.lower()}", "",
         f"- **Versión:** {config.VERSION}" + (f" (canal {config.CHANNEL})" if config.CHANNEL else ""),
         f"- **Fecha:** {time.strftime('%Y-%m-%d %H:%M')}"]
    L += [f"- **{k}:** {v}" for k, v in system_info().items()]
    ctx = (crash or {}).get("ctx") or CTX
    if ctx:
        L.append("- **Dónde:** " + ", ".join(f"{k} = {v}" for k, v in ctx.items() if v not in (None, "")))
    L += ["", "## " + ("Qué pasó" if kind == "error" else "La idea"), "", note.strip() or "(sin descripción)", ""]
    if crash:
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(crash.get("ts", 0)))
        L += ["## Último error" + (" (cerró el Hub)" if crash.get("fatal") else " (en un fotograma, el Hub siguió)"), "",
              f"{when} · versión {crash.get('version', '?')} · {crash.get('error', '')}", "", "```", crash.get("traceback", "").rstrip(), "```", ""]
    files = {}
    if kind == "error":
        hl = _tail(config.STATE / "hub.log", log_lines)
        if hl:
            files["hub.log"] = "\n".join(hl)
        dl = _tail(config.STATE / "forgeinatord.log", 60)
        if dl:
            files["forgeinatord.log"] = "\n".join(dl)
        for name, txt in files.items():
            L += [f"## {name} (últimas {len(txt.splitlines())} líneas, sin ruido)", "", "```", txt, "```", ""]
    md = red("\n".join(L))
    files = {k: red(v) for k, v in files.items()}
    first = note.strip().splitlines()[0][:70] if note.strip() else ((crash or {}).get("error", "")[:70] or title_k)
    title = red(pre + first)
    return {"kind": kind, "title": title, "md": md, "files": files, "crash": crash, "issue_body": _issue_body(md, kind)}


def _issue_body(md: str, kind: str) -> str:
    """El cuerpo del issue cabe en una dirección: si no cabe se recorta por el final (el registro), cerrando el bloque de código."""
    foot = ("\n\n---\n*Informe generado por Forgeinator (Ajustes › Mantenimiento › Informe). Los secretos y tu usuario ya van tapados. "
            "Si se recortó, el informe completo está en el zip: arrástralo a este issue.*")
    fits = lambda b: len(urllib.parse.quote(b + foot)) <= URL_MAX - 600  # noqa: E731  (deja sitio al título)
    if fits(md):
        return md + foot
    lo, hi = 0, len(md)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(md[:mid] + "\n…(recortado)\n```"):
            lo = mid
        else:
            hi = mid - 1
    body = md[:lo].rsplit("\n", 1)[0] + "\n…(recortado)"
    if body.count("```") % 2:
        body += "\n```"
    return body + foot


def issue_url(rep: dict) -> str:
    _, label, _ = KINDS.get(rep["kind"], KINDS["error"])
    q = urllib.parse.urlencode({"title": rep["title"], "labels": label, "body": rep["issue_body"]}, quote_via=urllib.parse.quote)
    return f"https://github.com/{REPO}/issues/new?{q}"


def save_zip(rep: dict, dest: Path | None = None) -> Path:
    dest = dest or Path.home() / f"forgeinator-informe-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("informe.md", rep["md"] + "\n")
        for name, txt in rep["files"].items():
            z.writestr(name.replace("/", "_") + ".txt", txt + "\n")
    return dest
