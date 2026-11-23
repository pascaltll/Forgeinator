"""v3.22 · Bibliotecas remotas (E5a): explorar y descargar ROMs de un servidor WebDAV, SMB, SFTP, FTP o de cualquier remoto de rclone.

Requisito de la fuente: estructura tipo ES-DE, <carpeta>/<sistema>/<juego> (p. ej. roms/psx/Crash.chd). Lo bajado va a TU biblioteca
(library_dir/roms/<sistema>/), con el mismo nombre de sistema ES-DE que usa el resto del Hub.

Todo el transporte lo hace rclone (40+ servicios, reanudación, avance en JSON); este módulo solo le pasa la conexión y lee su salida.
- Fuentes:  ~/.local/share/forgeinator/remotes.json      (nombre, tipo, dirección, usuario, carpeta: sin secretos)
- Secretos: ~/.config/forgeinator/remotes-secrets.json  (contraseñas ya «oscurecidas» con `rclone obscure`, permisos 600)
Protocolo y contrato: claude/forgeinator-servicio-protocolo.md (proyecto). Solo biblioteca estándar + el ejecutable rclone."""
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from . import config, esde

KINDS = {   # tipo → (nombre visible, backend de rclone, campos que se piden)
    "webdav": ("WebDAV (Nextcloud, Synology, Apache…)", "webdav", ("url", "user", "pass")),
    "smb": ("Carpeta compartida de Windows / Samba", "smb", ("host", "user", "pass", "share")),
    "sftp": ("SFTP / SSH", "sftp", ("host", "user", "pass", "port")),
    "ftp": ("FTP", "ftp", ("host", "user", "pass", "port")),
    "rclone": ("Remoto ya configurado en rclone", None, ("remote",)),
    "local": ("Carpeta de este equipo o montada (USB, NFS…)", "local", ()),
}
SECRET = ("pass",)
TIMEOUT_LIST = 60


class RemoteError(OSError):
    pass


# ---------------------------------------------------------------- rclone
def rclone_bin():
    """Ruta de rclone: el del sistema, ~/.local/bin o el que se guardó en la biblioteca. None si no hay."""
    for c in (os.environ.get("HUB_RCLONE"), shutil.which("rclone"), str(Path.home() / ".local/bin/rclone"), str(config.DATA / "bin" / "rclone")):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def _run(args, timeout=TIMEOUT_LIST, check=True) -> str:
    rb = rclone_bin()
    if not rb:
        raise RemoteError("Falta rclone. Instálalo con «rpm-ostree install rclone», «brew install rclone» o desde rclone.org "
                          "(un solo archivo en ~/.local/bin)")
    try:
        r = subprocess.run([rb, *args], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as ex:
        raise RemoteError(f"rclone no respondió en {timeout} s (¿servidor caído o sin red?)") from ex
    if check and r.returncode != 0:
        raise RemoteError(_explain(r.stderr))
    return r.stdout


def _explain(err: str) -> str:
    """El error de rclone, corto y en claro."""
    e = (err or "").strip().splitlines()
    last = next((ln for ln in reversed(e) if "ERROR" in ln or "Failed" in ln or "error" in ln.lower()), e[-1] if e else "error desconocido")
    low = last.lower()
    if "401" in low or "unauthorized" in low or "authentication" in low or "permission denied" in low or "login" in low:
        return "El servidor rechazó el usuario o la contraseña"
    if "no such host" in low or "connection refused" in low or "i/o timeout" in low or "no route" in low:
        return "No se pudo conectar con el servidor (dirección, puerto o red)"
    if "directory not found" in low or "not found" in low or "404" in low:
        return "Esa carpeta no existe en el servidor"
    return re.sub(r"^\S+ \S+ (ERROR|NOTICE)\s*:\s*", "", last)[:240]


def obscure(password: str) -> str:
    return _run(["obscure", password], timeout=15).strip() if password else ""


def _q(v) -> str:
    """Valor para una cadena de conexión de rclone (:webdav,url='…':). Las comillas simples se duplican."""
    return "'" + str(v).replace("'", "''") + "'"


# ---------------------------------------------------------------- fuentes guardadas
def _store() -> Path:
    return config.DATA / "remotes.json"


def _secrets() -> Path:
    return config.CONFIG / "remotes-secrets.json"


def _load(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(p: Path, d: dict, private=False) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    if private:
        os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def sources() -> list:
    return [dict(v, id=k) for k, v in sorted(_load(_store()).items(), key=lambda kv: kv[1].get("name", "").lower())]


def get(sid: str) -> dict:
    s = _load(_store()).get(sid)
    if not s:
        raise RemoteError("Esa biblioteca remota ya no existe")
    return dict(s, id=sid)


def add(kind: str, name: str, fields: dict, root: str = "roms") -> dict:
    """Guarda una fuente. La contraseña se oscurece con rclone y va aparte (600); en remotes.json nunca hay secretos."""
    if kind not in KINDS:
        raise RemoteError(f"Tipo desconocido: {kind}")
    sid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "remota"
    st = _load(_store())
    if sid in st:
        sid += "-" + uuid.uuid4().hex[:4]
    pub = {k: str(v) for k, v in fields.items() if k not in SECRET and v not in (None, "")}
    st[sid] = {"name": name.strip() or KINDS[kind][0], "kind": kind, "fields": pub, "root": root.strip("/"), "added": time.time()}
    sec = {k: obscure(v) for k, v in fields.items() if k in SECRET and v}
    if sec:
        allsec = _load(_secrets())
        allsec[sid] = sec
        _save(_secrets(), allsec, private=True)
    _save(_store(), st)
    return dict(st[sid], id=sid)


def remove(sid: str) -> None:
    st = _load(_store())
    st.pop(sid, None)
    _save(_store(), st)
    sec = _load(_secrets())
    if sec.pop(sid, None) is not None:
        _save(_secrets(), sec, private=True)


def remote_spec(src: dict, rel: str = "") -> str:
    """La fuente como cadena de conexión de rclone, con la ruta relativa dentro de su carpeta."""
    kind, f = src["kind"], src.get("fields") or {}
    path = "/".join(p for p in (src.get("root", ""), rel.strip("/")) if p)
    if kind == "local":
        return os.path.join(os.path.expanduser(f.get("path", "/")), path)
    if kind == "rclone":
        return f"{f['remote'].rstrip(':')}:{path}"
    sec = _load(_secrets()).get(src["id"], {})
    opts = []
    if kind == "webdav":
        opts += [f"url={_q(f['url'])}", "vendor=other"]
    elif kind in ("smb", "sftp", "ftp"):
        opts.append(f"host={_q(f['host'])}")
        if f.get("port"):
            opts.append(f"port={_q(f['port'])}")
    if f.get("user"):
        opts.append(f"user={_q(f['user'])}")
    if sec.get("pass"):
        opts.append(f"pass={_q(sec['pass'])}")
    if kind == "smb" and f.get("share"):
        path = "/".join(p for p in (f["share"], path) if p)
    return f":{KINDS[kind][1]}," + ",".join(opts) + ":" + path


# ---------------------------------------------------------------- explorar
def lsjson(src: dict, rel: str = "", dirs_only=False) -> list:
    args = ["lsjson", remote_spec(src, rel), "--no-modtime", "--no-mimetype"]
    if dirs_only:
        args.append("--dirs-only")
    try:
        return json.loads(_run(args) or "[]")
    except ValueError as ex:
        raise RemoteError("Respuesta ilegible de rclone") from ex


def test(src: dict) -> str:
    """Prueba la conexión: lista la carpeta raíz. Devuelve un resumen ('12 sistemas: psx, ps2…')."""
    sy = systems(src)
    if not sy:
        return "Conecta, pero no hay carpetas de sistema (se esperaba <carpeta>/psx, ps2… como en ES-DE)"
    return f"{len(sy)} sistemas: " + ", ".join(s["system"] for s in sy[:8]) + ("…" if len(sy) > 8 else "")


def systems(src: dict) -> list:
    """Carpetas de primer nivel que son sistemas de ES-DE: [{'dir', 'system', 'name'}]."""
    out = []
    for e in lsjson(src, dirs_only=True):
        sy = esde.system_for(e["Name"])
        if sy:
            out.append({"dir": e["Name"], "system": sy, "name": e["Name"]})
    return sorted(out, key=lambda s: s["system"])


def games(src: dict, sysdir: str, system: str) -> list:
    """Juegos de un sistema: archivos con extensión que el sistema acepta, y carpetas (juegos de varios archivos, p. ej. .m3u + .cue)."""
    out = []
    for e in lsjson(src, sysdir):
        name = e["Name"]
        if e.get("IsDir"):
            out.append({"path": f"{sysdir}/{name}", "name": name, "dir": True, "size": None})
        elif esde.accepts(system, Path(name).suffix.lower()) or not esde.systems():
            out.append({"path": f"{sysdir}/{name}", "name": name, "dir": False, "size": e.get("Size")})
    return sorted(out, key=lambda g: g["name"].lower())


# ---------------------------------------------------------------- descargar
def target(system: str, name: str, cfg=None) -> Path:
    """Donde queda: la primera carpeta de ROMs del Hub (Ajustes › Carpetas de ROMs) / <sistema> / nombre."""
    from . import roms
    rs = roms.roots(cfg or config.settings())
    if not rs:
        raise RemoteError("No hay carpeta de ROMs configurada (Ajustes › Carpetas de ROMs)")
    return esde.target_dir(rs[0], system) / name


def download(src: dict, game: dict, system: str, progress=None, stop=lambda: False, cfg=None) -> Path:
    """Baja un juego (archivo o carpeta) a library/roms/<sistema>/. progress(bytes, total, eta_s, velocidad_Bps). No pisa nada existente."""
    dest = target(system, game["name"], cfg)
    if dest.exists():
        raise RemoteError(f"Ya tienes «{game['name']}» en {dest.parent}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rb = rclone_bin()
    if not rb:
        _run(["version"])                                   # lanza el error con las instrucciones
    verb = "copy" if game.get("dir") else "copyto"
    args = [rb, verb, remote_spec(src, game["path"]), str(dest), "--use-json-log", "--stats", "1s", "-v", "--retries", "3", "--low-level-retries", "10"]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL)
    last_err = ""
    try:
        for line in p.stderr:
            if stop():
                p.terminate()
                break
            try:
                j = json.loads(line)
            except ValueError:
                last_err = line
                continue
            st = j.get("stats")
            if st and progress:
                progress(int(st.get("bytes") or 0), int(st.get("totalBytes") or 0), st.get("eta"), float(st.get("speed") or 0))
            if j.get("level") == "error":
                last_err = j.get("msg", "")
        p.wait(timeout=30)
    finally:
        if p.poll() is None:
            p.kill()
    if stop():
        _clean_partial(dest)
        raise RemoteError("Descarga cancelada")
    if p.returncode != 0:
        _clean_partial(dest)
        raise RemoteError(_explain(last_err))
    return dest


def _clean_partial(dest: Path) -> None:
    """Lo que quedó a medias no se borra: se renombra a «<nombre>.incompleto» para que no parezca un juego bueno."""
    for p in [dest, *dest.parent.glob(dest.name + "*.partial")]:
        if p.exists():
            q = p.with_name(p.name + ".incompleto")
            n = 1
            while q.exists():
                n += 1
                q = p.with_name(f"{p.name}.incompleto{n}")
            try:
                os.rename(p, q)
            except OSError:
                pass
