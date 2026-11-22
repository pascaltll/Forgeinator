"""Registro de arranques: qué pasó cuando pulsas JUGAR y el juego no abre.
- La salida del lanzador y del juego se guarda en data/launch-logs/<id>-<fecha>.out (antes iba a /dev/null).
- Si el lanzador termina enseguida, se escribe data/launch-logs/<id>-<fecha>.md con el diagnóstico (código de salida, cola de la salida, log del launcher,
  su .toml, ¿existe/ejecutable el binario?, bibliotecas que faltan según ldd, sesión gráfica, versión de Hub y del sistema).
- Un arranque que parecía bueno pero murió después se detecta al abrir Hub la próxima vez (scan_orphans).
- bundle() junta los últimos informes en ENVIAR.md (para pegarlo en el chat) y bin/hub-logs lo imprime. Nunca incluye tokens ni cookies."""
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import config

KEEP = 30
ERRORY = re.compile(r"error|fail|cannot|can't|not found|no such|segmentation|abort|exception|undefined symbol|permission denied|denied|killed|core dumped", re.I)
# Líneas que Steam/gamescope/AppImage escriben SIEMPRE y no son un fallo: no deben convertir un arranque que funcionó en un «informe de error»
NOISE = re.compile(r"gameoverlayrenderer\.so.*(cannot be preloaded|ELFCLASS32)|ATTENTION: default value of option .* overridden by environment|"
                   r"pid \d+ != \d+, skipping destruction|\[Gamescope WSI\]|ProtonFixes\[\d+\] (INFO|WARN)", re.I)


def real_errors(text: str) -> bool:
    """¿Hay alguna línea con aspecto de error que NO sea ruido conocido?"""
    return any(ERRORY.search(ln) and not NOISE.search(ln) for ln in (text or "").splitlines())


def quiet(text: str) -> str:
    """El texto sin las líneas de ruido conocido (para mostrar el registro sin ahogar lo importante)."""
    return "\n".join(ln for ln in (text or "").splitlines() if not NOISE.search(ln))


ENV_OK = ("DISPLAY", "WAYLAND_DISPLAY", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP", "GAMESCOPE_WAYLAND_DISPLAY", "SteamGameId", "SteamDeck", "LANG", "XDG_RUNTIME_DIR")


def dir_() -> Path:
    d = config.DATA / "launch-logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def new_out(lid: str) -> Path:
    """Ruta nueva para la salida de este arranque (y poda los más viejos)."""
    d = dir_()
    p = d / f"{lid}-{_stamp()}.out"
    olds = sorted(d.glob("*.out"), key=lambda f: f.stat().st_mtime)
    for f in olds[:-KEEP]:
        f.unlink(missing_ok=True)
        f.with_suffix(".md").unlink(missing_ok=True)
    return p


def _tail(path, n=120, maxb=24000) -> str:
    try:
        data = Path(path).read_bytes()[-maxb:].decode("utf-8", "replace")
    except OSError:
        return ""
    return "\n".join(data.splitlines()[-n:])


def _run(cmd, timeout=6) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _exec_of(toml_text: str):
    for key in ("exec", "command", "cmd", "path", "executable"):
        m = re.search(rf"^\s*{key}\s*=\s*[\"']?([^\"'\n]+)", toml_text, re.M)
        if m:
            return m.group(1).strip().split(" ")[0]
    return None


def _version() -> str:
    try:
        return (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
    except OSError:
        return "?"


def _toml(lid: str) -> dict:
    try:
        import tomllib
        return tomllib.loads((config.LAUNCHER / "games" / f"{lid}.toml").read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return {}


def _expand(v: str, idir: str) -> str:
    v = str(v).replace("$INSTALL_DIR", idir).replace("${INSTALL_DIR}", idir).replace("$LAUNCHER_ROOT", str(config.LAUNCHER))
    return os.path.expandvars(os.path.expanduser(v))


def binary_of(lid: str):
    """Ruta del ejecutable que lanza el launcher para <lid> ([run] exe + install_dir del .toml), o None."""
    t = _toml(lid)
    run = t.get("run") or {}
    exe = run.get("exe") or run.get("exec") or t.get("exe") or t.get("exec")
    if not exe or (run.get("type") not in (None, "binary")):
        return None
    p = Path(os.path.expanduser(str(exe).split(" ")[0]))
    if not p.is_absolute() and t.get("install_dir"):
        p = Path(os.path.expanduser(str(t["install_dir"]))) / p
    return p


def run_info(lid: str) -> dict:
    """Lo que hace falta para mirar las bibliotecas como las verá el juego: binario, LD_LIBRARY_PATH de [run.env] y el distrobox donde se compiló."""
    t = _toml(lid)
    idir = os.path.expanduser(str(t.get("install_dir") or ""))
    env = (t.get("run") or {}).get("env") or {}
    ld = _expand(env["LD_LIBRARY_PATH"], idir) if env.get("LD_LIBRARY_PATH") else ""
    bi = (t.get("update") or {}).get("build_in") or []
    box = ""
    if isinstance(bi, list) and "distrobox" in bi and "enter" in bi:
        rest = [x for x in bi[bi.index("enter") + 1:] if not str(x).startswith("-")]
        box = str(rest[0]) if rest else ""
    return {"path": binary_of(lid), "ld": ld, "container": box}


_LIBS = {}   # (ruta, LD_LIBRARY_PATH) -> ((mtime, tamaño), faltan): ldd solo se repite si el binario cambió


def missing_libs(path, ld_path="") -> list:
    """Bibliotecas que el binario pide y el sistema no tiene (según ldd, con el LD_LIBRARY_PATH que le pone el launcher),
    sin las que el propio port trae junto al ejecutable."""
    p = Path(path) if path else None
    if not p or not p.is_file() or not shutil.which("ldd"):
        return []
    try:
        st = p.stat()
    except OSError:
        return []
    key = (st.st_mtime_ns, st.st_size)
    ck = (str(p), ld_path or "")
    hit = _LIBS.get(ck)
    if hit and hit[0] == key:
        return hit[1]
    cmd = ["ldd", str(p)]
    if ld_path:
        cmd = ["env", f"LD_LIBRARY_PATH={ld_path}:{os.environ.get('LD_LIBRARY_PATH', '')}".rstrip(":")] + cmd
    miss = []
    for ln in _run(cmd, timeout=4).splitlines():
        if "not found" in ln:
            name = ln.strip().split(" ")[0]
            if not any((d / name).exists() for d in (p.parent, p.parent / "lib", p.parent / "lib64", p.parent / "libs")):
                miss.append(name)
    _LIBS[ck] = (key, miss)
    return miss


def libs_check(lid: str) -> dict:
    """{miss: [...], container: 'fedora' si se compiló en un distrobox}."""
    ri = run_info(lid)
    return {"miss": missing_libs(ri["path"], ri["ld"]), "container": ri["container"]}


def diagnose(lid: str) -> list:
    """Líneas de diagnóstico del juego en el launcher (nada que pueda tardar más de unos segundos)."""
    out = []
    toml = config.LAUNCHER / "games" / f"{lid}.toml"
    ttxt = ""
    try:
        ttxt = toml.read_text(encoding="utf-8", errors="replace")
    except OSError:
        out.append(f"- No existe {toml}")
    p = binary_of(lid)
    exe = _exec_of(ttxt) if (ttxt and p is None) else None
    if p is None and exe:
        p = Path(os.path.expanduser(exe))
        if not p.is_absolute():
            m = re.search(r"^\s*install_dir\s*=\s*[\"']?([^\"'\n]+)", ttxt, re.M)
            if m:
                p = Path(os.path.expanduser(m.group(1).strip())) / exe
    if p is not None:
        out.append(f"- Binario: {p} · existe: {p.exists()} · ejecutable: {os.access(p, os.X_OK) if p.exists() else '-'}")
        if p.is_file() and shutil.which("ldd"):
            ri = run_info(lid)
            miss = missing_libs(p, ri["ld"])
            if ri["container"]:
                out.append(f"- Compilado dentro del distrobox «{ri['container']}» (el launcher lo abre en el sistema)")
            out.append("- Bibliotecas que faltan (ldd): " + (", ".join(miss[:15]) if miss else "ninguna"))
    return out + (["", "### .toml del launcher", "```", ttxt.strip()[:3000], "```"] if ttxt else [])


def report(lid: str, name: str, rc, age: float, out_path, why="el lanzador terminó enseguida") -> Path:
    """Escribe el informe de un arranque fallido y devuelve su ruta."""
    d = dir_()
    base = Path(out_path).stem if out_path else f"{lid}-{_stamp()}"
    md = d / f"{base}.md"
    state_log = config.LAUNCHER / "state" / f"{lid}.log"
    L = [f"# Arranque fallido: {name} ({lid})", "",
         f"- Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')} · Hub {_version()} · {why} · código de salida: {rc} · duración: {age:.1f} s",
         f"- Sistema: {platform.platform()} · Python {platform.python_version()}"]
    L += ["- Entorno: " + ", ".join(f"{k}={os.environ[k]}" for k in ENV_OK if os.environ.get(k)), ""]
    L += ["### Diagnóstico"] + diagnose(lid) + [""]
    raw = _tail(out_path, 400) if out_path else ""
    t = "\n".join(quiet(raw).splitlines()[-120:])
    nz = len(raw.splitlines()) - len(quiet(raw).splitlines())
    L += [f"### Salida del lanzador/juego (últimas líneas; {nz} líneas de ruido conocido de Steam/gamescope omitidas)" if nz else "### Salida del lanzador/juego (últimas líneas)", "```", t or "(vacía: el juego no escribió nada)", "```", ""]
    s = _tail(state_log, 80)
    L += [f"### {state_log}", "```", s or "(no existe o está vacío)", "```"]
    md.write_text("\n".join(L), encoding="utf-8")
    try:
        from . import history
        history.record(lid, "jugar", False, f"código {rc} · " + (history.first_error(raw) or "sin error claro en la salida"), rc=rc, secs=round(age, 1))
    except Exception:  # noqa: BLE001
        pass
    return md


def reports(lid=None) -> list:
    fs = sorted(dir_().glob(f"{lid}-*.md" if lid else "*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [f for f in fs if f.name != "ENVIAR.md"]


def latest(lid=None):
    r = reports(lid)
    return r[0] if r else None


def scan_orphans(max_age=86400) -> int:
    """Salidas de arranques que no tienen informe pero contienen errores (el juego se abrió y murió después, o Hub ya se había cerrado). Crea su informe."""
    n = 0
    for o in dir_().glob("*.out"):
        try:
            st = o.stat()
        except OSError:
            continue
        if o.with_suffix(".md").exists() or time.time() - st.st_mtime > max_age or st.st_size == 0:
            continue
        if time.time() - st.st_mtime < 20:      # puede seguir escribiéndose
            continue
        if real_errors(_tail(o, 200)):
            lid = o.stem.rsplit("-", 2)[0]
            report(lid, lid, "desconocido", 0.0, o, why="el juego se abrió pero la salida contiene errores (Hub ya no estaba para ver cómo acabó)")
            n += 1
    return n


def bundle(limit=8) -> Path:
    """ENVIAR.md = los últimos informes juntos (para pegar en el chat). Devuelve su ruta."""
    fs = reports()[:limit]
    body = [f"# Registros de arranque de Recomp Hub {_version()}", "", f"{len(fs)} informe(s), del más reciente al más antiguo.", ""]
    for f in fs:
        body += [f"---\n<!-- {f.name} -->", f.read_text(encoding="utf-8", errors="replace")[:9000], ""]
    if not fs:
        body.append("No hay arranques fallidos registrados.")
    p = dir_() / "ENVIAR.md"
    p.write_text("\n".join(body), encoding="utf-8")
    return p
