"""v3.25 · Complementos (plugins) de Forgeinator: conectores instalables desde un zip.

Un complemento es una carpeta con `forgeinator-plugin.json` y un programa (en cualquier lenguaje) que habla el **protocolo de
conectores v1**: JSON, una línea por mensaje, por su entrada y salida estándar (stdio). Forgeinator lo arranca por operación, le
pasa la configuración de la fuente y recibe sistemas, juegos y el avance de las descargas. Ver docs/PLUGINS.md.

- Zona de instalación: ~/.local/share/forgeinator/plugins/<id>/ (común a estable y dev). Estado en plugins/estado.json.
- Instalar: se valida el zip (manifiesto, id, rutas sin «..» ni enlaces, tamaño, programa dentro del complemento o intérprete permitido).
  Una versión anterior no se borra: va a plugins/.anteriores/. Quitar un complemento lo mueve a plugins/.papelera/.
- Seguridad: un complemento ejecuta código en tu equipo, como cualquier programa. Se instala solo tras confirmar, sus permisos
  declarados se enseñan antes y nunca recibe más secretos que los campos de su propia fuente."""
import json
import os
import re
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from . import config

MANIFEST = "forgeinator-plugin.json"
SCHEMA = 1
PROTOCOL = 1
TYPES = ("connector",)
PERMS = {"network": "usa la red (internet o tu red local)", "files": "lee o escribe archivos fuera de su carpeta de descarga",
         "exec": "ejecuta otros programas del sistema"}
INTERPRETERS = ("python3", "python", "sh", "bash", "node")
MAX_ZIP = 64 * 1024 * 1024
ID_RX = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
FIELD_RX = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
CALL_TIMEOUT = 60
SEARCH_DIRS = ("~/Games/actualizaciones", "~/Downloads", "~/Descargas")


class PluginError(OSError):
    pass


def root() -> Path:
    return config.DATA / "plugins"


def _state_file() -> Path:
    return root() / "estado.json"


def _state() -> dict:
    try:
        return json.loads(_state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(st: dict):
    root().mkdir(parents=True, exist_ok=True)
    tmp = _state_file().with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, _state_file())


# ---------------------------------------------------------------- manifiesto
def _ver(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+]", str(v))[:4])


def validate(m: dict) -> dict:
    """Comprueba el manifiesto y devuelve una copia normalizada. Lanza PluginError con el motivo en claro."""
    if not isinstance(m, dict):
        raise PluginError("El manifiesto no es un objeto JSON")
    if m.get("schema") != SCHEMA:
        raise PluginError(f"Manifiesto de versión {m.get('schema')!r}: esta versión de Forgeinator entiende la {SCHEMA}")
    pid = str(m.get("id", ""))
    if not ID_RX.match(pid):
        raise PluginError("Id no válido: minúsculas, números y guiones (2–40)")
    if m.get("type", "connector") not in TYPES:
        raise PluginError(f"Tipo desconocido: {m.get('type')}")
    if int(m.get("protocol", 0) or 0) != PROTOCOL:
        raise PluginError(f"Usa el protocolo de conectores {m.get('protocol')}; Forgeinator habla el {PROTOCOL}")
    run = m.get("run")
    if not (isinstance(run, list) and run and all(isinstance(x, str) and x for x in run)):
        raise PluginError("«run» debe ser una lista: el programa y sus argumentos")
    if run[0] not in INTERPRETERS and (run[0].startswith("/") or ".." in Path(run[0]).parts):
        raise PluginError(f"El programa «{run[0]}» debe estar dentro del complemento o ser {', '.join(INTERPRETERS)}")
    fields = []
    for f in m.get("fields") or []:
        if not isinstance(f, dict) or not FIELD_RX.match(str(f.get("key", ""))):
            raise PluginError(f"Campo no válido: {f!r}")
        fields.append({"key": f["key"], "label": str(f.get("label") or f["key"])[:80], "default": str(f.get("default") or ""),
                       "secret": bool(f.get("secret")), "required": bool(f.get("required"))})
    perms = [p for p in m.get("permissions") or [] if p in PERMS]
    return {"schema": SCHEMA, "id": pid, "name": str(m.get("name") or pid)[:60], "version": str(m.get("version") or "0"),
            "type": m.get("type", "connector"), "protocol": PROTOCOL, "run": list(run), "fields": fields, "permissions": perms,
            "description": str(m.get("description") or "")[:400], "author": str(m.get("author") or "")[:80],
            "homepage": str(m.get("homepage") or "")[:200], "min_forgeinator": str(m.get("min_forgeinator") or "")}


def _read_manifest(d: Path) -> dict:
    try:
        return validate(json.loads((d / MANIFEST).read_text(encoding="utf-8")))
    except (OSError, ValueError) as ex:
        raise PluginError(f"No se puede leer {MANIFEST}: {ex}") from ex


# ---------------------------------------------------------------- zip
def _zip_prefix(z: zipfile.ZipFile) -> str:
    names = z.namelist()
    if MANIFEST in names:
        return ""
    tops = {n.split("/", 1)[0] for n in names if n.strip("/")}
    if len(tops) == 1:
        t = next(iter(tops)) + "/"
        if t + MANIFEST in names:
            return t
    raise PluginError(f"El zip no es un complemento: falta {MANIFEST}")


def inspect(zpath) -> dict:
    """Lee el manifiesto de un zip SIN instalarlo (para enseñar nombre, versión y permisos antes de confirmar)."""
    zpath = Path(zpath)
    try:
        with zipfile.ZipFile(zpath) as z:
            pre = _zip_prefix(z)
            m = validate(json.loads(z.read(pre + MANIFEST).decode("utf-8")))
    except (zipfile.BadZipFile, KeyError, ValueError) as ex:
        raise PluginError(f"Zip no válido: {ex}") from ex
    cur = installed().get(m["id"])
    m["installed_version"] = cur["version"] if cur else None
    m["action"] = "instalar" if not cur else ("actualizar" if _ver(m["version"]) > _ver(cur["version"]) else "reinstalar")
    return m


def _safe_members(z: zipfile.ZipFile, pre: str):
    total = 0
    for info in z.infolist():
        n = info.filename
        if not n.startswith(pre) or n == pre:
            continue
        rel = n[len(pre):]
        parts = Path(rel).parts
        if rel.startswith("/") or ".." in parts or "\\" in rel or (parts and ":" in parts[0]):
            raise PluginError(f"Ruta peligrosa en el zip: {n}")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise PluginError(f"El zip trae un enlace simbólico ({n}): no se admite")
        total += info.file_size
        if total > MAX_ZIP * 4:
            raise PluginError("El complemento es demasiado grande")
        yield info, rel


def install(zpath) -> dict:
    """Instala o actualiza. Devuelve el manifiesto instalado. La versión anterior queda en plugins/.anteriores/."""
    zpath = Path(zpath)
    if zpath.stat().st_size > MAX_ZIP:
        raise PluginError("El zip pasa de 64 MB")
    m = inspect(zpath)
    root().mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".nuevo-", dir=root()))
    try:
        with zipfile.ZipFile(zpath) as z:
            pre = _zip_prefix(z)
            for info, rel in _safe_members(z, pre):
                dst = tmp / rel
                if info.is_dir():
                    dst.mkdir(parents=True, exist_ok=True)
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)
                mode = (info.external_attr >> 16) & 0o777
                os.chmod(dst, (mode or 0o644) & 0o755)
        m2 = _read_manifest(tmp)
        exe = tmp / m2["run"][0]
        if m2["run"][0] not in INTERPRETERS:
            if not exe.is_file():
                raise PluginError(f"Falta el programa {m2['run'][0]} dentro del complemento")
            exe.chmod(exe.stat().st_mode | 0o100)
        dest = root() / m2["id"]
        if dest.exists():
            old = installed().get(m2["id"], {}).get("version", "x")
            keep = root() / ".anteriores" / f"{m2['id']}-{old}-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**6:06d}"
            keep.parent.mkdir(parents=True, exist_ok=True)
            os.replace(dest, keep)
        os.replace(tmp, dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)          # solo la carpeta temporal que acabamos de crear
        raise
    st = _state()
    st.setdefault(m2["id"], {})
    st[m2["id"]].update(enabled=st[m2["id"]].get("enabled", True), installed=time.time(), source=zpath.name)
    _save_state(st)
    return dict(m2, enabled=st[m2["id"]]["enabled"], dir=str(dest))


def installed() -> dict:
    """{id: manifiesto + enabled + dir} de lo que hay en la zona de complementos (los rotos salen con «error»)."""
    out, st = {}, _state()
    if not root().is_dir():
        return out
    for d in sorted(root().iterdir()):
        if d.name.startswith(".") or not d.is_dir():
            continue
        try:
            m = _read_manifest(d)
        except PluginError as ex:
            out[d.name] = {"id": d.name, "name": d.name, "version": "?", "error": str(ex), "enabled": False, "dir": str(d), "fields": [],
                           "permissions": [], "type": "?"}
            continue
        if m["id"] != d.name:
            continue
        out[m["id"]] = dict(m, enabled=st.get(m["id"], {}).get("enabled", True), dir=str(d))
    return out


def get(pid: str) -> dict:
    p = installed().get(pid)
    if not p:
        raise PluginError(f"El complemento «{pid}» no está instalado")
    if p.get("error"):
        raise PluginError(f"El complemento «{pid}» está roto: {p['error']}")
    return p


def set_enabled(pid: str, on: bool):
    get(pid)
    st = _state()
    st.setdefault(pid, {})["enabled"] = bool(on)
    _save_state(st)


def remove(pid: str) -> Path:
    """No borra: mueve la carpeta a plugins/.papelera/<id>-<fecha>."""
    d = root() / pid
    if not ID_RX.match(pid) or not d.is_dir():
        raise PluginError(f"El complemento «{pid}» no está instalado")
    dst = root() / ".papelera" / f"{pid}-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**6:06d}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.replace(d, dst)
    st = _state()
    st.pop(pid, None)
    _save_state(st)
    return dst


def candidates() -> list:
    """Zips que parecen complementos en las carpetas de siempre (para la lista «Instalar»)."""
    out = []
    for d in SEARCH_DIRS:
        p = Path(d).expanduser()
        if not p.is_dir():
            continue
        for f in sorted(p.glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True):
            if f.name.startswith("recomp-hub-update-") or f.name.startswith("forgeinator-"):
                if "plugin" not in f.name:
                    continue
            try:
                with zipfile.ZipFile(f) as z:
                    _zip_prefix(z)
                out.append(f)
            except (zipfile.BadZipFile, PluginError, OSError):
                continue
    return out[:12]


def connectors() -> list:
    return [p for p in installed().values() if p.get("type") == "connector" and p.get("enabled") and not p.get("error")]


# ---------------------------------------------------------------- protocolo de conectores v1 (stdio)
class Session:
    """Una conversación con el programa del complemento. Una petición a la vez; el complemento puede mandar «progress» antes de responder."""

    def __init__(self, plugin: dict):
        self.p = plugin
        cmd = list(plugin["run"])
        if cmd[0] not in INTERPRETERS:
            cmd[0] = str(Path(plugin["dir"]) / cmd[0])
        elif cmd[0] in ("python3", "python"):
            cmd[0] = sys.executable or cmd[0]
        env = dict(os.environ, FORGEINATOR_PLUGIN_PROTOCOL=str(PROTOCOL), FORGEINATOR_VERSION=config.VERSION,
                   PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
        for k in list(env):                             # el complemento no hereda los secretos del Hub
            if re.search(r"(?i)token|secret|passw|cookie|_key$|^key$", k):
                env.pop(k)
        try:
            self.proc = subprocess.Popen(cmd, cwd=plugin["dir"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, bufsize=1, env=env, start_new_session=True)
        except OSError as ex:
            raise PluginError(f"No pude arrancar «{plugin['name']}»: {ex}") from ex
        self.n = 0
        self.err = []
        self.lines = queue.Queue()                  # stdout se lee en un hilo: select() no ve lo que ya está en el búfer de Python
        threading.Thread(target=self._drain, daemon=True).start()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            for ln in self.proc.stdout:
                self.lines.put(ln)
        except (OSError, ValueError):
            pass
        self.lines.put(None)

    def _drain(self):
        for ln in self.proc.stderr:
            self.err.append(ln.rstrip())
            del self.err[:-40]
            print(f"[complemento {self.p['id']}] {ln.rstrip()}", file=sys.stderr, flush=True)

    def call(self, method, params=None, progress=None, stop=lambda: False, timeout=CALL_TIMEOUT):
        self.n += 1
        mid = self.n
        try:
            self.proc.stdin.write(json.dumps({"v": PROTOCOL, "id": mid, "method": method, "params": params or {}}, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError) as ex:
            raise PluginError(self._why(f"el complemento se cerró ({ex})")) from ex
        last = time.time()
        cancelled = False
        while True:
            if stop() and not cancelled:
                cancelled = True
                try:
                    self.proc.stdin.write(json.dumps({"v": PROTOCOL, "id": mid, "method": "cancel"}) + "\n")
                    self.proc.stdin.flush()
                except (OSError, ValueError):
                    pass
                cancel_t = time.time()
            if cancelled and time.time() - cancel_t > 5:     # 5 s para que pare por las buenas; luego se le cierra
                self.close(force=True)
                raise PluginError("Descarga cancelada")
            try:
                line = self.lines.get(timeout=0.25)
            except queue.Empty:
                if time.time() - last > timeout:
                    self.close(force=True)
                    raise PluginError("Descarga cancelada" if cancelled else self._why(f"el complemento no responde ({timeout} s)"))
                continue
            if line is None:
                self.lines.put(None)
                time.sleep(0.05)                    # deja llegar las últimas líneas de stderr para explicar el fallo
                raise PluginError(self._why("el complemento terminó sin responder"))
            last = time.time()
            try:
                msg = json.loads(line)
            except ValueError:
                print(f"[complemento {self.p['id']}] línea no JSON: {line.rstrip()[:200]}", file=sys.stderr, flush=True)
                continue
            if msg.get("id") != mid:
                continue
            if "progress" in msg:
                pr = msg["progress"] or {}
                if progress:
                    progress(int(pr.get("done") or 0), int(pr.get("total") or 0), pr.get("eta"), float(pr.get("speed") or 0))
                continue
            if msg.get("ok"):
                return msg.get("result")
            if cancelled or msg.get("error") == "cancelado":
                raise PluginError("Descarga cancelada")
            raise PluginError(str(msg.get("detail") or msg.get("error") or "error del complemento"))

    def _why(self, what):
        tail = " · ".join(self.err[-2:])
        return f"«{self.p['name']}»: {what}" + (f" — {tail}" if tail else "")

    def close(self, force=False):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=0.1 if force else 3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.proc.pid, 15)
                self.proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(self.proc.pid, 9)
                except OSError:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def session(pid: str) -> Session:
    p = get(pid)
    if not p.get("enabled"):
        raise PluginError(f"El complemento «{p['name']}» está desactivado (Ajustes › Archivos › Complementos)")
    s = Session(p)
    try:
        hello = s.call("hello", {"protocol": PROTOCOL, "forgeinator": config.VERSION}, timeout=15)
    except PluginError:
        s.close()
        raise
    if int((hello or {}).get("protocol", 0)) != PROTOCOL:
        s.close()
        raise PluginError(f"«{p['name']}» habla el protocolo {(hello or {}).get('protocol')} y Forgeinator el {PROTOCOL}")
    s.hello = hello
    return s


def pack(src_dir, out_dir) -> Path:
    """Empaqueta una carpeta de complemento como forgeinator-plugin-<id>-<versión>.zip (lo usan tools/make_release.py y las pruebas)."""
    src_dir, out_dir = Path(src_dir), Path(out_dir)
    m = _read_manifest(src_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    z = out_dir / f"forgeinator-plugin-{m['id']}-{m['version']}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"):
                zi = zipfile.ZipInfo.from_file(p, f"{m['id']}/{p.relative_to(src_dir).as_posix()}")
                zi.compress_type = zipfile.ZIP_DEFLATED
                f.writestr(zi, p.read_bytes())
    return z
