"""Instalar un port descargado: extraer (zip/tar/AppImage), localizar el ejecutable y generar games/<id>.toml
para el launcher unificado. Nunca sobrescribe un .toml existente (escribe .toml.new) ni borra nada."""
import json
import os
import re
import shutil
import stat
import tarfile
import time
import zipfile
from pathlib import Path

from . import config


def _safe_members_zip(z, dest):
    base = dest.resolve()
    for i in z.infolist():
        t = (dest / i.filename).resolve()
        if base != t and base not in t.parents:
            raise ValueError(f"ruta peligrosa en el zip: {i.filename}")
        yield i


_ARCH = re.compile(r"\.(zip|7z|rar|tar(\.\w+)?|tgz|txz)$", re.I)
_DOC = re.compile(r"\.(txt|md|sha\d*|sig|asc|pdf|json|url|nfo)$", re.I)


def _seven(archive: Path, dest: Path):
    """Extrae un .7z con la herramienta del sistema (7z, 7zz, 7za, bsdtar o unar); si no hay ninguna, lo dice claro."""
    import subprocess
    for tool, cmd in (("7z", ["7z", "x", "-y", "-o{d}", "{a}"]), ("7zz", ["7zz", "x", "-y", "-o{d}", "{a}"]), ("7za", ["7za", "x", "-y", "-o{d}", "{a}"]),
                      ("bsdtar", ["bsdtar", "-xf", "{a}", "-C", "{d}"]), ("unar", ["unar", "-q", "-o", "{d}", "{a}"])):
        if shutil.which(tool):
            r = subprocess.run([c.format(d=str(dest), a=str(archive)) for c in cmd], capture_output=True, text=True, timeout=1800)
            if r.returncode:
                raise OSError(f"{tool} no pudo abrir {archive.name}: {(r.stderr or r.stdout)[-160:]}")
            return
    raise OSError(f"{archive.name} es un {archive.suffix} y no encuentro 7z/bsdtar/unar. En el equipo: sudo rpm-ostree install p7zip (o `distrobox enter fedora -- sudo dnf install p7zip`)")


def _run_installer(archive: Path, dest: Path):
    """Instalador autoextraíble «.run». Primero como makeself SIN ejecutar su script (--noexec --target); si no lo es, como los que
    reciben la carpeta de destino por argumento (p. ej. gow-native-pc: `bash x.run <carpeta nueva>`, sin root). Siempre a una carpeta
    temporal nueva dentro de dest: nunca escribe fuera ni pisa lo que ya hay."""
    import subprocess
    tmp = dest / ".hub-run-tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    env = dict(os.environ, HOME=str(dest / ".hub-run-home"))        # si el instalador ignora el destino, que no escriba en tu carpeta personal
    last = ""
    for argv in (["sh", str(archive), "--noexec", "--target", str(tmp)], ["bash", str(archive), str(tmp)]):
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL, env=env)
            last = (r.stderr or r.stdout)[-200:]
        except (OSError, subprocess.SubprocessError) as ex:
            last = str(ex)
            continue
        if r.returncode == 0 and tmp.is_dir() and any(tmp.iterdir()):
            break
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(dest / ".hub-run-home", ignore_errors=True)
        raise OSError(f"no pude extraer {archive.name}: {last or 'el instalador no dejó nada'}")
    for p in list(tmp.iterdir()):
        if not (dest / p.name).exists():
            shutil.move(str(p), dest / p.name)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(dest / ".hub-run-home", ignore_errors=True)


def _unwrap_nested(dest: Path, before=frozenset(), depth=2):
    """Si lo extraído es solo otro archivo comprimido (más papeles sueltos), lo abre también: p. ej. un lanzador dentro de un .zip dentro del .zip de la release."""
    for _ in range(depth):
        kids = [p for p in dest.iterdir() if p.name not in before and not p.name.startswith(".hub-")]      # solo lo recién extraído (puede ser una actualización por encima)
        arch = [p for p in kids if p.is_file() and _ARCH.search(p.name) and not p.name.lower().endswith(".appimage")]
        other = [p for p in kids if p not in arch and not (p.is_file() and _DOC.search(p.name))]
        if len(arch) != 1 or other:
            return
        a = arch[0]
        tmp = dest / ".hub-nested"
        shutil.rmtree(tmp, ignore_errors=True)
        _extract_once(a, tmp)
        for p in list(tmp.iterdir()):
            shutil.move(str(p), dest / p.name) if not (dest / p.name).exists() else None
        shutil.rmtree(tmp, ignore_errors=True)
        a.unlink(missing_ok=True)


def _flatten(dest: Path):
    """Si todo está dentro de una única carpeta, sube su contenido un nivel.
    v2.76: la carpeta se aparta primero a un nombre temporal; antes, si dentro había un archivo con el MISMO nombre que la carpeta
    (BT4decomp/BT4decomp) la comparación chocaba con la propia carpeta y no se aplanaba nada."""
    kids = [p for p in dest.iterdir()]
    if len(kids) == 1 and kids[0].is_dir() and not kids[0].is_symlink():  # carpeta contenedora única
        tmp = dest / ".hub-unwrap"
        os.replace(kids[0], tmp)
        for p in list(tmp.iterdir()):
            shutil.move(str(p), dest / p.name)
        try:
            tmp.rmdir()
        except OSError:
            pass


_KEEP = frozenset({"gamedata", "saves", "net_session", "user_data", "mods", "songs", "stages", "textures", "tbo", "art"})   # datos del jugador: nunca se pisan


def _aside(path: Path) -> Path:
    """Aparta (rename, sin copiar) lo que estorba a «<carpeta>/.hub-replaced/<nombre>»; así nada se pierde."""
    bak = path.parent / ".hub-replaced"
    bak.mkdir(exist_ok=True)
    t, n = bak / path.name, 2
    while t.exists() or t.is_symlink():
        t = bak / f"{path.name}.{n}"
        n += 1
    os.replace(path, t)
    return t


def _zip_strip(mem, dest: Path) -> int:
    """1 si el zip trae TODO dentro de una única carpeta Y se está actualizando por encima de una instalación que ya tiene esos mismos nombres
    (v2.76: la carpeta no se anidaba solo cuando la de destino estaba vacía; en BT4/BT3 la versión nueva acababa en «BT4decomp/BT4decomp»)."""
    names = [i.filename for i in mem if i.filename and not i.filename.startswith("__MACOSX")]
    tops = {x.split("/", 1)[0] for x in names}
    if len(tops) != 1 or not all("/" in x.rstrip("/") or x.endswith("/") for x in names):
        return 0
    top = next(iter(tops))
    try:
        have = {p.name for p in Path(dest).iterdir()}
    except OSError:
        return 0
    kids = {x.split("/", 2)[1] for x in names if x.count("/") >= 1 and x.split("/", 2)[1]}
    return 1 if have and (kids & have or top in have) else 0


def _zip_put(z, i, dest: Path, strip: int):
    parts = i.filename.split("/")
    rel = "/".join(parts[strip:]) if strip else i.filename
    if not rel.strip("/"):
        return
    tgt = dest / rel
    if i.is_dir():
        if tgt.exists() and not tgt.is_dir():
            _aside(tgt)
        tgt.mkdir(parents=True, exist_ok=True)
        return
    tgt.parent.mkdir(parents=True, exist_ok=True)
    if tgt.is_dir() and not tgt.is_symlink():
        _aside(tgt)                                       # una carpeta con el nombre del archivo nuevo (caso «BT4decomp»)
    elif tgt.exists() or tgt.is_symlink():
        tgt.unlink()                                      # romper el enlace duro: escribir «a través» de él alteraba también la copia .prev
    with z.open(i) as src, open(tgt, "wb") as out:
        shutil.copyfileobj(src, out)
    mode = (i.external_attr >> 16) & 0o777
    if mode & 0o111:
        tgt.chmod(mode | 0o755)


def _is_elf(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def nested_dir(dest) -> "Path | None":
    """Carpeta N dentro de dest que es la release extraída DOS veces: contiene el ejecutable «N/N», o repite la mayoría de los nombres de dest."""
    dest = Path(dest)
    try:
        kids = [p for p in dest.iterdir()]
    except OSError:
        return None
    for c in kids:
        if not c.is_dir() or c.is_symlink() or c.name.startswith(".") or c.name in _KEEP:
            continue
        if _is_elf(c / c.name):
            return c
        try:
            inner = {p.name for p in c.iterdir()}
        except OSError:
            continue
        root = {p.name for p in kids if p != c}
        both = inner & root
        if len(both) >= 4 and len(both) * 10 >= len(inner) * 6:
            return c
    return None


def flatten_nested(dest) -> dict:
    """Reparar (v2.76): sube el contenido de la subcarpeta duplicada a dest. Lo de dest que se sustituye se aparta (rename) a .hub-replaced/;
    los datos del jugador (_KEEP: gamedata, saves, mods…) se conservan y solo se les añade lo que falte. Devuelve {moved, kept, backup, nested} o {}."""
    dest = Path(dest)
    inner = nested_dir(dest)
    if not inner:
        return {}
    tmp = dest / ".hub-flatten"
    n = 2
    while tmp.exists():
        tmp = dest / f".hub-flatten{n}"
        n += 1
    os.replace(inner, tmp)
    moved = kept = 0
    for p in list(tmp.iterdir()):
        t = dest / p.name
        if (t.exists() or t.is_symlink()):
            if p.name in _KEEP and t.is_dir() and p.is_dir() and not t.is_symlink():
                restore_missing(p, t)
                kept += 1
                continue
            _aside(t)
        os.replace(p, t)
        moved += 1
    try:
        tmp.rmdir()
    except OSError:
        _aside(tmp)
    bak = dest / ".hub-replaced"
    return {"moved": moved, "kept": kept, "nested": inner.name, "backup": str(bak) if bak.exists() else ""}


def extract(archive: Path, dest: Path, progress=None) -> Path:
    """Extrae en dest (y abre los archivos comprimidos anidados). Si todo está dentro de una única carpeta, la aplana. Devuelve dest."""
    d0 = Path(dest)
    before = frozenset(p.name for p in d0.iterdir()) if d0.is_dir() else frozenset()
    dest = _extract_once(archive, dest, progress)
    _unwrap_nested(dest, before)
    _flatten(dest)
    if before:                                  # actualización por encima: si la release trajo su carpeta superior (tar/7z), subirla
        nd = nested_dir(dest)
        if nd and nd.name not in before:
            flatten_nested(dest)
    return dest


def _extract_once(archive: Path, dest: Path, progress=None) -> Path:
    archive, dest = Path(archive), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    n = archive.name.lower()
    if n.endswith(".appimage"):
        t = dest / archive.name
        shutil.copy2(archive, t)
        t.chmod(t.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
        return dest
    if n.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            mem = list(_safe_members_zip(z, dest))
            strip = _zip_strip(mem, dest)
            for k, i in enumerate(mem):
                _zip_put(z, i, dest, strip)
                if progress:
                    progress(k + 1, len(mem))
    elif re.search(r"\.(tar(\.\w+)?|tgz|txz)$", n):
        with tarfile.open(archive) as t:
            t.extractall(dest, filter="data")
    elif n.endswith((".7z", ".rar")):
        _seven(archive, dest)
    elif n.endswith(".exe"):                   # v3.10: build de Windows que es un único .exe portátil: se copia tal cual
        shutil.copy2(archive, dest / archive.name)
        return dest
    elif n.endswith(".run"):
        _run_installer(archive, dest)
    else:
        raise ValueError(f"formato no soportado: {archive.name} (usa zip, 7z, rar, tar, .run, .exe de Windows o AppImage)")
    _flatten(dest)
    return dest


def setup_exe(d) -> str:
    """Configurador que trae el propio port (p. ej. «BT4decomp-setup»: desempaqueta TU disco antes del primer arranque).
    Ruta absoluta del ELF ejecutable cuyo nombre acaba en setup/configurator, a 2 niveles como mucho; "" si no hay."""
    d = Path(d)
    try:
        cands = [p for pat in ("*", "*/*") for p in d.glob(pat)
                 if p.is_file() and re.search(r"(setup|configurator)$", p.name, re.I) and os.access(p, os.X_OK)]
    except OSError:
        return ""
    for p in sorted(cands, key=lambda p: len(p.parts)):
        try:
            with open(p, "rb") as f:
                if f.read(4) == b"\x7fELF":
                    return str(p)
        except OSError:
            continue
    return ""


def find_executable(d: Path, hint="") -> str:
    """Ruta relativa del ejecutable más probable (ELF/AppImage con permiso de ejecución)."""
    d = Path(d)
    cands = []
    for p in d.rglob("*"):
        if not p.is_file() or len(p.relative_to(d).parts) > 3:
            continue
        try:
            with open(p, "rb") as f:
                magic = f.read(4)
        except OSError:
            continue
        if magic == b"\x7fELF" and (p.name.lower().endswith(".appimage") or "." not in p.name) and not p.name.startswith("lib"):
            sc = 10
            if hint and hint.lower().replace(" ", "") in p.name.lower().replace("-", "").replace("_", ""):
                sc += 20
            if re.search(r"setup|install|crash|update|helper", p.name, re.I):
                sc -= 15
            sc -= 2 * (len(p.relative_to(d).parts) - 1)
            cands.append((sc, p))
    if not cands:
        return ""
    cands.sort(key=lambda x: -x[0])
    p = cands[0][1]
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return str(p.relative_to(d))


def toml_for(entry: dict, install_dir: Path, exe: str, repo_asset: str = "", requires=None) -> str:
    q = lambda s: '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'  # noqa: E731
    home = str(Path.home())
    idir = str(install_dir)
    if idir.startswith(home):
        idir = "~" + idir[len(home):]
    out = [f"id   = {q(entry.get('launcher_id') or entry['id'])}", f"name = {q(entry['name'])}", f"install_dir = {q(idir)}", "", "preserve = []", "", "[update]"]
    if entry.get("repo") and repo_asset:
        out += ['type = "github-archive"', f"repo = {q(entry['repo'])}", f"asset = {q(repo_asset)}", 'mode = "overlay"',
                f"executables = [{q(exe)}]", 'version_file = ".release_version"', "offline_timeout = 8", "countdown = 5",
                'countdown_default = "launch"']
    else:
        out += ['type = "none"']
    out += ["", "[run]", 'type = "binary"', f"exe = {q(exe)}", 'cwd = "."']
    if requires:
        out.append("require = [" + ", ".join(q(r) for r in [exe] + list(requires)) + "]")
    out += ["", "[health]", "grace_seconds = 10", "", "[ui]", 'theme = "default"']
    if entry.get("platform"):
        out.append(f"subtitle = {q(entry['platform'])}")
    out += ["", "[steam]", f"search = {q(entry['name'])}", ""]
    return "\n".join(out)


def register(entry: dict, install_dir: Path, exe: str, asset: str = "", version: str = "", requires=None) -> Path:
    """Escribe games/<id>.toml en el launcher. Si ya existe, escribe <id>.toml.new y NO toca el original."""
    gdir = config.LAUNCHER / "games"
    gdir.mkdir(parents=True, exist_ok=True)
    lid = entry.get("launcher_id") or entry["id"]
    f = gdir / f"{lid}.toml"
    if f.exists():
        f = gdir / f"{lid}.toml.new"
    f.write_text(toml_for(entry, install_dir, exe, generic_asset(asset), requires), encoding="utf-8")
    if version:
        (Path(install_dir) / ".release_version").write_text(version, encoding="utf-8")
        for g in launcher_games():                      # v2.78: si su .toml lee la versión de OTRO archivo (.installed_tag…), escribirla ahí también
            vf = str(g.get("version_file") or "")
            if g["id"] == lid and vf and vf != ".release_version" and "/" not in vf and not vf.startswith("~"):
                try:
                    (Path(install_dir) / vf).write_text(version, encoding="utf-8")
                except OSError:
                    pass
    return f


def _backup_name(dest: Path) -> Path:
    b = dest.with_name(dest.name + ".prev")
    n = 2
    while b.exists():
        b = dest.with_name(f"{dest.name}.prev{n}")
        n += 1
    return b


def restore_missing(src: Path, dst: Path) -> int:
    """Como `cp -an src/. dst/`: copia a dst lo que dst NO tiene (partidas, ajustes, texturas, datos que el juego creó), sin pisar nada.
    Usa enlace duro si puede (sin duplicar GB) y copia si no. Si en dst una ruta es archivo donde en src era carpeta (o al revés), la salta."""
    n = 0
    src, dst = Path(src), Path(dst)
    for root, dirs, files in os.walk(src):
        r = Path(root).relative_to(src)
        base = dst / r
        if base.exists() and not base.is_dir():
            dirs[:] = []
            continue
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError:
            dirs[:] = []
            continue
        for f in files:
            t, s = base / f, Path(root) / f
            if t.exists() or t.is_symlink() or s.is_symlink():
                continue
            try:
                try:
                    os.link(s, t)
                except OSError:
                    shutil.copy2(s, t)
                n += 1
            except OSError:
                continue
    return n


# ── v2.78: actualizar por etapas (staging → validar → aplicar → comprobar → volver atrás si falla) ──
_PROT_NAMES = frozenset({"hub-run.sh", ".hub-versions.json", "proton-prefix"})   # los gestiona Hub, no la release
_UPD_RE = re.compile(r"(updater|^update[-_.].*\.(sh|exe|py)$)", re.I)


def own_updater(dest) -> list:
    """Actualizadores PROPIOS del juego dentro de su carpeta (Hercules: update/updater.py, BT3/BT4: update/, El Chavo: trg-updater.exe, …).
    Hub no los toca: ni los sobrescribe ni los borra. Lista de rutas relativas ('' si no hay)."""
    d = Path(dest)
    out = []
    try:
        if (d / "update").is_dir():
            out.append("update/")
        for p in list(d.glob("*")) + list(d.glob("*/*")):
            if p.is_file() and _UPD_RE.search(p.name) and ".prev" not in p.parts[-3:] and not any(x.startswith(".hub-") for x in p.relative_to(d).parts):
                out.append(str(p.relative_to(d)))
    except OSError:
        pass
    return sorted(set(out))


def generic_asset(name: str) -> str:
    """Nombre de asset con la versión sustituida por «*» para que el launcher encuentre la siguiente: toystory2-0.6.0-linux-x64.zip → toystory2-*-linux-x64.zip.
    Solo versiones con puntos; «x86_64» o «BT4decomp» no se tocan."""
    return re.sub(r"(?<![\d.])v?\d+(?:\.\d+)+", "*", name or "")


def _family(name: str) -> str:
    return re.sub(r"\d+(?:[._-]\d+)*", "#", name.lower())


def target_dir(entry: dict) -> Path:
    """Carpeta REAL donde instalar/actualizar: la install_dir del .toml si el juego ya está registrado (p. ej. «…/linux»); si la carpeta tiene
    la distribución dividida (.hub-versions.json), la subcarpeta activa; si no, la carpeta por defecto. Antes se extraía siempre en la raíz,
    y en un juego dividido la versión nueva quedaba fuera de linux/ (GTA VCS)."""
    try:
        inf = installed_info(entry)
        d = Path(inf["dir"])
        if inf.get("toml") and d.is_dir():
            return d
    except (OSError, KeyError, ValueError):
        pass
    dest = config.GAMES_DIR / entry.get("folder", entry["id"])
    try:
        m = json.loads((dest / ".hub-versions.json").read_text(encoding="utf-8"))
        sub = dest / str(m.get("active") or "linux")
        if sub.is_dir():
            return sub
    except (OSError, ValueError):
        pass
    return dest


def apply_update(archive: Path, dest: Path, progress=None, need_exe=True, validate=None) -> dict:
    """Actualiza `dest` ENCIMA sin riesgo: extrae a una carpeta temporal, valida, y solo entonces mueve archivo a archivo.
    Lo reemplazado va a «dest/.hub-replaced/upd-<fecha>/» (rename: sin copiar ni tocar la copia .prev por enlaces duros).
    No pisa: datos del jugador (_KEEP), `update/` y actualizadores propios, enlaces simbólicos (tu ISO), hub-run.sh y .hub-versions.json.
    Si algo falla, devuelve todo a su sitio. Devuelve {replaced, added, skipped, saved, exe}."""
    archive, dest = Path(archive), Path(dest)
    stg = dest.parent / f".{dest.name}.hub-staging"
    shutil.rmtree(stg, ignore_errors=True)               # restos de un intento anterior (carpeta temporal de Hub)
    moved, placed, skipped = [], [], []
    old_exe = find_executable(dest, "") if need_exe else ""
    try:
        extract(archive, stg, progress)
        if not any(stg.rglob("*")):
            raise OSError("el paquete está vacío")
        if validate:
            validate(stg)                                    # p. ej. Windows: que traiga un .exe reconocible
        new_exe = find_executable(stg, "") if need_exe else ""
        if need_exe and old_exe and not new_exe:
            raise OSError("el paquete no trae un ejecutable de Linux: no toco tu instalación")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        trash = dest / ".hub-replaced" / f"upd-{stamp}"
        own = {x.rstrip("/") for x in own_updater(dest)}

        def keep(rel: Path, tgt: Path) -> bool:
            top = rel.parts[0]
            if top in _PROT_NAMES or rel.name in _PROT_NAMES:
                return True
            if top == "update" and (dest / "update").is_dir():
                return True                                   # carpeta del actualizador del juego
            if str(rel) in own:
                return True                                   # su actualizador: no lo sustituyo
            if top in _KEEP and (tgt.exists() or tgt.is_symlink()):
                return True                                   # datos del jugador
            if tgt.is_symlink():
                return True                                   # p. ej. el enlace a tu ISO
            return False

        def put_aside(t: Path):
            sv = trash / t.relative_to(dest)
            sv.parent.mkdir(parents=True, exist_ok=True)
            os.replace(t, sv)
            moved.append((t, sv))
        # versiones de AppImage con otro nombre (VCS-Recomp-0.2.4 → 0.3.0): la vieja se aparta; si no, el juego seguiría abriendo la antigua
        newtop = {p.name for p in stg.iterdir() if p.is_file()}
        for p in stg.iterdir():
            if p.is_file() and p.name.lower().endswith(".appimage"):
                for o in dest.iterdir():
                    if o.is_file() and not o.is_symlink() and o.name not in newtop and o.name.lower().endswith(".appimage") and _family(o.name) == _family(p.name):
                        put_aside(o)
        for root, _dirs, files in os.walk(stg):
            r = Path(root).relative_to(stg)
            for f in files:
                rel = r / f
                tgt = dest / rel
                if keep(rel, tgt):
                    skipped.append(str(rel))
                    continue
                par = tgt.parent
                if par.exists() and not par.is_dir():
                    put_aside(par)
                par.mkdir(parents=True, exist_ok=True)
                if tgt.is_dir() and not tgt.is_symlink():
                    put_aside(tgt)
                if tgt.exists() or tgt.is_symlink():
                    put_aside(tgt)
                os.replace(stg / rel, tgt)
                placed.append(tgt)
        exe = find_executable(dest, "") if need_exe else ""
        if need_exe and not exe:
            raise OSError("tras actualizar no queda ningún ejecutable")
        if need_exe and new_exe and not (dest / new_exe).is_file():
            raise OSError(f"falta {new_exe} tras actualizar")
    except Exception:
        for t in reversed(placed):
            try:
                t.unlink()
            except OSError:
                pass
        for t, sv in reversed(moved):
            try:
                t.parent.mkdir(parents=True, exist_ok=True)
                os.replace(sv, t)
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(stg, ignore_errors=True)
    n_old = len([1 for t, _ in moved])
    return {"replaced": n_old, "added": max(0, len(placed) - n_old), "skipped": skipped,
            "saved": str(trash) if moved else "", "exe": exe}


def _sync_meta(dest: Path, exe: str):
    """Distribución dividida: si la carpeta tiene .hub-versions.json, el exe de la subcarpeta (linux/) debe ser el nuevo; si no, al cambiar de
    sistema Hub volvería a escribir el .toml con el ejecutable ANTIGUO."""
    f = dest.parent / ".hub-versions.json"
    try:
        m = json.loads(f.read_text(encoding="utf-8"))
        sec = m.get(dest.name)
        if not isinstance(sec, dict) or not exe:
            return
        old = sec.get("exe")
        if old == exe:
            return
        sec["exe"] = exe
        sec["executables"] = [exe if x == old else x for x in (sec.get("executables") or [exe])]
        f.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, AttributeError):
        pass


def install(entry: dict, archive: Path, asset_name: str = "", version: str = "", progress=None, clean: bool = False, dest=None) -> dict:
    """Extrae → detecta ejecutable → registra en el launcher. Devuelve {dir, exe, toml}.
    clean=True (v2.43, para cambiar a otra versión, sobre todo una anterior): la copia actual se aparta a «<carpeta>.prev», la versión elegida se
    extrae en una carpeta vacía (sin archivos viejos mezclados, sin choques archivo/carpeta) y después se recupera de la apartada lo que falte."""
    dest = Path(dest) if dest else target_dir(entry)      # v2.78: la carpeta REAL del juego (p. ej. «…/linux»), no siempre la raíz
    backup, restored, upd = None, 0, None
    if clean and dest.exists() and any(dest.iterdir()):
        backup = _backup_name(dest)
        dest.rename(backup)
        try:
            extract(archive, dest, progress)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)       # no dejar una carpeta a medias: se devuelve la anterior intacta
            backup.rename(dest)
            raise
        restored = restore_missing(backup, dest)
    elif dest.is_dir() and any(dest.iterdir()) and not str(archive).lower().endswith(".run"):
        upd = apply_update(archive, dest, progress)             # por encima, por etapas y con vuelta atrás
    else:
        extract(archive, dest, progress)
    exe = (upd or {}).get("exe") or find_executable(dest, entry.get("name", "").split(":")[0].split()[0] if entry.get("name") else "")
    _sync_meta(dest, exe)
    toml = register(entry, dest, exe or "", asset_name, version, (entry.get("requires") or {}).get("files"))
    fixed = repair_run(entry.get("launcher_id") or entry["id"], dest, exe or "") if str(toml).endswith(".new") else None
    return {"dir": str(dest), "exe": exe, "toml": str(toml), "repaired": fixed, "backup": str(backup) if backup else None, "restored": restored, "update": upd,
            "own_updater": own_updater(dest)}


def repair_run(lid: str, dest: Path, exe: str, force: bool = False):
    """Tras actualizar por encima: si el .toml que ya existía apunta a un ejecutable que YA NO está (la release nueva cambió de estructura,
    p. ej. «BT4decomp/BT4decomp» → «BT4decomp») y el recién detectado sí, corrige [run] exe/cwd y [update] executables. No toca nada más.
    Devuelve el ejecutable anterior si corrigió, o None."""
    import tomllib
    f = config.LAUNCHER / "games" / f"{lid}.toml"
    try:
        txt = f.read_text(encoding="utf-8")
        t = tomllib.loads(txt)
    except (OSError, ValueError):
        return None
    run = t.get("run") or {}
    old = str(run.get("exe") or "")
    if not exe or run.get("type", "binary") != "binary" or not old or old == exe:
        return None
    try:
        idir = Path(str(t.get("install_dir") or dest)).expanduser()
        if idir.resolve() != Path(dest).resolve() or (not force and (idir / old).is_file()) or not (Path(dest) / exe).is_file():
            return None
    except OSError:
        return None
    q = lambda v: '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'  # noqa: E731
    same_dir = os.path.normpath(str(run.get("cwd") or ".")) == os.path.normpath(str(Path(old).parent))
    out, sec = [], ""
    for ln in txt.split("\n"):
        st = ln.strip()
        if st.startswith("[") and st.endswith("]"):
            sec = st[1:-1].strip()
        elif sec == "run" and re.match(r"\s*exe\s*=", ln):
            ln = f"exe = {q(exe)}"
        elif sec == "run" and re.match(r"\s*cwd\s*=", ln) and same_dir:
            ln = f"cwd = {q(str(Path(exe).parent))}"      # arrancaba junto a su ejecutable: que siga así (ahí busca sus datos)
        elif sec == "update" and re.match(r"\s*executables\s*=", ln):
            ln = f"executables = [{q(exe)}]"
        out.append(ln)
    try:
        f.with_suffix(".toml.bak").write_text(txt, encoding="utf-8")
        f.write_text("\n".join(out), encoding="utf-8")
    except OSError:
        return None
    _LG_CACHE.pop(str(f), None)
    return old


def repair_folder(lid: str, dest) -> dict:
    """Botón REPARAR CARPETA: aplana la subcarpeta duplicada, vuelve a localizar el ejecutable y corrige el .toml del launcher (exe y cwd)."""
    dest = Path(dest)
    r = flatten_nested(dest)
    if not r:
        return {"ok": False, "why": "no hay subcarpeta duplicada"}
    exe = find_executable(dest, "")
    r["exe"] = exe
    r["ok"] = bool(exe) and (dest / exe).is_file()
    r["toml"] = repair_run(lid, dest, exe, force=True) if exe else None
    return r


_LG_CACHE = {}   # ruta -> (mtime_ns, tamaño, registro): releer y parsear cada .toml costaba ~2,5 ms en el Ally (64 ms por pasada con ~25 juegos)


def launcher_games() -> list:
    """Juegos ya registrados en el launcher unificado: [{id, repo, dir, version_file}] (lee games/*.toml; solo reparsea los que cambiaron)."""
    import tomllib
    out, seen = [], set()
    for f in sorted((config.LAUNCHER / "games").glob("*.toml")):
        try:
            st = f.stat()
            key = (st.st_mtime_ns, st.st_size)
            hit = _LG_CACHE.get(str(f))
            if hit and hit[0] == key:
                out.append(dict(hit[1]))
                seen.add(str(f))
                continue
            t = tomllib.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        up = t.get("update") or {}
        rec = {"id": t.get("id", f.stem), "repo": (up.get("repo") or "").lower(), "name": t.get("name", ""),
               "dir": Path(os.path.expandvars(str(t.get("install_dir", "")))).expanduser(),
               "version_file": up.get("version_file", ".release_version")}
        _LG_CACHE[str(f)] = (key, rec)
        seen.add(str(f))
        out.append(dict(rec))
    for k in [k for k in _LG_CACHE if k not in seen]:
        del _LG_CACHE[k]
    return out


_WARNED = set()


def _warn_once(msg):
    """Una vez por sesión (la caché se renueva cada 10 s y repetía el aviso cada vez)."""
    if msg not in _WARNED:
        _WARNED.add(msg)
        import sys
        print(msg, file=sys.stderr, flush=True)


def _simple(folder) -> bool:
    return bool(folder) and "/" not in folder and folder not in (".", "..")


def build_index(lg, entries):
    """Índices para installed_info en O(1) por tarjeta, sin crear Paths ni tocar el disco por tarjeta
    (antes: O(tarjetas × registros) por llamada y un is_dir/iterdir por tarjeta: 50-250 ms por pasada con 2000+ tarjetas en el Ally)."""
    gstr = str(config.GAMES_DIR)
    by_id, by_dir, by_repo, gdir = {}, {}, {}, {}
    for i, g in enumerate(lg):
        gdir[i] = str(g["dir"])
        by_id.setdefault(g["id"], []).append((i, g))
        by_dir.setdefault(gdir[i], []).append((i, g))
        if g["repo"]:
            by_repo.setdefault(g["repo"], []).append((i, g))
    claims = {}
    for o in entries or []:
        claims.setdefault(("id", o["id"]), set()).add(o["id"])
        if o.get("launcher_id"):
            claims.setdefault(("id", o["launcher_id"]), set()).add(o["id"])
        f = o.get("folder", o["id"])
        claims.setdefault(("dir", gstr + "/" + f if _simple(f) else str(config.GAMES_DIR / f)), set()).add(o["id"])
    top = {}   # carpetas de primer nivel de GAMES_DIR y si tienen algo dentro (una sola lectura del disco)
    try:
        with os.scandir(gstr) as it:
            for de in it:
                try:
                    if de.is_dir():
                        with os.scandir(de.path) as sub:
                            top[de.name] = next(sub, None) is not None
                except OSError:
                    continue
    except OSError:
        pass
    return {"by_id": by_id, "by_dir": by_dir, "by_repo": by_repo, "claims": claims, "gdir": gdir, "top": top, "gstr": gstr}


def _installed_fast(entry, lg, ix):
    """Igual que el camino general pero con cadenas y diccionarios: sin crear Paths ni mirar el disco por tarjeta (salvo juegos registrados)."""
    eid, lid, repo = entry["id"], entry.get("launcher_id"), (entry.get("repo") or "").lower()
    folder = entry.get("folder", eid)
    exp = ix["gstr"] + "/" + folder
    gdir, claims = ix["gdir"], ix["claims"]
    cand = {}
    for k in (eid, lid):
        for i, g in ix["by_id"].get(k, ()):
            cand[i] = g
    for i, g in ix["by_dir"].get(exp, ()):
        cand[i] = g
    if repo:
        for i, g in ix["by_repo"].get(repo, ()):
            if i not in cand:
                ids = claims.get(("id", g["id"]), set()) | claims.get(("dir", gdir[i]), set())
                if not any(x != eid for x in ids):
                    cand[i] = g
    same = sorted(cand.items(), key=lambda kv: (kv[1]["id"] != eid and kv[1]["id"] != lid, gdir[kv[0]] != exp, kv[0]))
    mi, m = same[0] if same else (None, None)
    if m and not (m["id"] == eid or lid == m["id"] or gdir[mi] == exp):
        _warn_once(f"[instalado] «{eid}» se asocia a «{m['id']}» SOLO por compartir repo {repo} (carpeta {gdir[mi]})")
    d = gdir[mi] if m else exp
    if m:
        p = Path(d)
        has = p.is_dir() and any(p.iterdir())
    else:
        has = ix["top"].get(folder, False)
    ver = ""
    if has or m:
        try:
            ver = (Path(d) / (m["version_file"] if m else ".release_version")).read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return {"installed": bool(has and (ver or m)), "version": ver, "dir": d, "toml": bool(m), "launcher_id": m["id"] if m else eid}


def installed_info(entry: dict, lg=None, entries=None, ix=None) -> dict:
    """{installed, version, dir, launcher_id}. Primero busca el juego ya registrado en el launcher (por id o por repo,
    usando SU install_dir); si no, mira la carpeta que Hub usaría (GAMES_DIR/folder). `ix` = build_index(lg, entries) para ir rápido."""
    lg = launcher_games() if lg is None else lg
    if ix is not None and _simple(entry.get("folder", entry["id"])):
        return _installed_fast(entry, lg, ix)
    ix = None   # nombres de carpeta raros: camino general
    repo = (entry.get("repo") or "").lower()
    expected = config.GAMES_DIR / entry.get("folder", entry["id"])
    def own(g):  # ¿este registro del launcher es de ESTA tarjeta (id, launcher_id o carpeta esperada)?
        return g["id"] == entry["id"] or entry.get("launcher_id") == g["id"] or g["dir"] == expected

    def claimed_by_other(g):  # otra tarjeta con el MISMO repo ya es dueña de ese registro (p. ej. Carbon vs Most Wanted)
        if ix is not None:
            ids = ix["claims"].get(("id", g["id"]), set()) | ix["claims"].get(("dir", g["dir"]), set())
            return any(i != entry["id"] for i in ids)
        return any(o["id"] != entry["id"] and (o["id"] == g["id"] or o.get("launcher_id") == g["id"] or config.GAMES_DIR / o.get("folder", o["id"]) == g["dir"])
                   for o in (entries or []))
    if ix is not None:
        cand = {}
        for k in (entry["id"], entry.get("launcher_id")):
            for i, g in ix["by_id"].get(k, ()):
                cand[i] = g
        for i, g in ix["by_dir"].get(expected, ()):
            cand[i] = g
        for i, g in (ix["by_repo"].get(repo, ()) if repo else ()):
            if i not in cand and not claimed_by_other(g):
                cand[i] = g
        same = [cand[i] for i in sorted(cand)]
    else:
        same = [g for g in lg if own(g) or (repo and g["repo"] == repo and not claimed_by_other(g))]
    # varios registros pueden compartir repo (p. ej. dos versiones de BT3): gana id exacto, luego la carpeta esperada
    same.sort(key=lambda g: (g["id"] != entry["id"] and g["id"] != entry.get("launcher_id"), g["dir"] != expected))
    m = same[0] if same else None
    if m and not own(m):
        _warn_once(f"[instalado] «{entry['id']}» se asocia a «{m['id']}» SOLO por compartir repo {repo} (carpeta {m['dir']})")
    d = m["dir"] if m else config.GAMES_DIR / entry.get("folder", entry["id"])
    has = d.is_dir() and any(d.iterdir())
    ver = ""
    if has or m:    # sin carpeta ni registro no hay versión que leer (evita ~230 lecturas fallidas por pasada)
        try:
            ver = (d / (m["version_file"] if m else ".release_version")).read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return {"installed": bool(has and (ver or m)), "version": ver, "dir": str(d), "toml": bool(m), "launcher_id": m["id"] if m else entry["id"]}


def register_build(entry: dict, install_dir: Path, artifact: str, container: str, cmd: str, ref: str, jobs: int = 4) -> Path:
    """games/<id>.toml tipo git-build (el launcher seguirá actualizando/compilando). No pisa un .toml existente (.toml.new)."""
    q = lambda v: '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'  # noqa: E731
    home = str(Path.home())
    idir = str(install_dir)
    idir = "~" + idir[len(home):] if idir.startswith(home) else idir
    lid = entry.get("launcher_id") or entry["id"]
    bin_ = ('["distrobox", "enter", %s, "--", "bash", "-c"]' % q(container)) if container else '["bash", "-c"]'
    out = [f"id   = {q(lid)}", f"name = {q(entry['name'])}", f"install_dir = {q(idir)}", "", "preserve = []", "", "[update]",
           'type = "git-build"', 'source_repo = "."', 'remote = "origin"', f"ref = {q(ref)}", f"build_in = {bin_}", f"build = {q(cmd)}",
           f"jobs = {int(jobs)}", f"artifact = {q(artifact)}", "offline_timeout = 8", "countdown = 5", 'countdown_default = "launch"', "",
           "[run]", 'type = "binary"', f"exe = {q(artifact)}", 'cwd = "."']
    req = (entry.get("requires") or {}).get("files")
    if req:
        out.append("require = [" + ", ".join(q(r) for r in req) + "]")
    out += ["", "[health]", "grace_seconds = 10", "", "[ui]", 'theme = "default"']
    if entry.get("platform"):
        out.append(f"subtitle = {q(entry['platform'])}")
    out += ["", "[steam]", f"search = {q(entry['name'])}", ""]
    gdir = config.LAUNCHER / "games"
    gdir.mkdir(parents=True, exist_ok=True)
    f = gdir / f"{lid}.toml"
    if f.exists():
        f = gdir / f"{lid}.toml.new"
    f.write_text("\n".join(out), encoding="utf-8")
    return f
