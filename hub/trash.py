"""Papelera de Hub: «borrar» MUEVE a ~/Games/.papelera-hub/<operación>/ (recuperable); solo se borra de verdad al vaciarla.
Solo toca rutas permitidas: la carpeta de un juego dentro de GAMES_DIR, archivos dentro de la carpeta de descargas y el registro/arte
de ESE juego en el launcher. Nunca Hub, el launcher entero, tu home, tus ROMs ni enlaces simbólicos."""
import json
import os
import re
import shutil
import time
from pathlib import Path

from . import config


class Unsafe(ValueError):
    """La ruta no está permitida para borrar."""


def root() -> Path:
    return config.GAMES_DIR / ".papelera-hub"


def _inside(child: Path, parent: Path) -> bool:
    return parent in child.parents


def _protected_trees():
    """Estas carpetas y TODO lo de dentro (y cualquier carpeta que las contenga) están protegidas."""
    return [config.ROOT, config.LAUNCHER, config.DATA, root()]


def _protected_points():
    """Estas carpetas solo se protegen a sí mismas y a sus ancestros (tu home contiene tus juegos, es normal)."""
    return [Path.home(), config.GAMES_DIR, Path("/")]


def check_path(p, kind: str) -> Path:
    """Devuelve la ruta real si es seguro moverla a la papelera; si no, lanza Unsafe con el motivo."""
    p = Path(p).expanduser()
    if p.is_symlink():
        raise Unsafe(f"{p} es un enlace simbólico: no se borra")
    if not p.exists():
        raise Unsafe(f"{p} no existe")
    rp = p.resolve()
    if kind == "project":
        base = config.GAMES_DIR.resolve()
        if not _inside(rp, base):
            raise Unsafe(f"{rp} está fuera de {base}")
        for f in _protected_trees():
            try:
                f = f.resolve()
            except OSError:
                continue
            if f == rp or _inside(rp, f) or _inside(f, rp):
                raise Unsafe(f"{rp} es una carpeta protegida de Hub o del launcher ({f})")
        for f in _protected_points():
            try:
                f = f.resolve()
            except OSError:
                continue
            if f == rp or _inside(f, rp):
                raise Unsafe(f"{rp} es una carpeta protegida ({f})")
        if not rp.is_dir():
            raise Unsafe(f"{rp} no es una carpeta")
    elif kind == "download":
        base = Path(config.path("downloads_dir")).expanduser().resolve()
        if not _inside(rp, base):
            raise Unsafe(f"{rp} está fuera de la carpeta de descargas {base}")
    elif kind == "launcher":
        lg = config.LAUNCHER.resolve()
        if rp.parent not in ((lg / "games"), (lg / "art")):
            raise Unsafe(f"{rp} no es un registro ni arte del launcher")
    else:
        raise Unsafe(f"tipo desconocido: {kind}")
    return rp


def size_of(path, limit_s=6.0) -> tuple:
    """(bytes, completo). No sigue enlaces; corta a los limit_s segundos en carpetas enormes."""
    p, end, total = Path(path), time.time() + limit_s, 0
    try:
        if p.is_file() or p.is_symlink():
            return p.lstat().st_size, True
    except OSError:
        return 0, True
    stack = [str(p)]
    while stack:
        if time.time() > end:
            return total, False
        try:
            with os.scandir(stack.pop()) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total, True


def _slug(s):
    return re.sub(r"[^\w.-]+", "-", str(s)).strip("-")[:40] or "juego"


def move_to_trash(items, label, eid="") -> Path:
    """items: [(ruta, tipo)]. Valida TODAS antes de mover nada. Devuelve la carpeta de la operación."""
    real = [(check_path(p, k), k) for p, k in items]
    op = root() / f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(label)}"
    n = 1
    while op.exists():
        n += 1
        op = root() / f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(label)}-{n}"
    op.mkdir(parents=True)
    meta = {"label": label, "eid": eid, "time": time.time(), "items": []}
    try:
        for i, (rp, kind) in enumerate(real):
            name = f"{i}-{rp.name}"
            try:
                os.rename(rp, op / name)
            except OSError:
                shutil.move(str(rp), str(op / name))     # otro disco: copia conservando enlaces y borra el origen
            meta["items"].append({"orig": str(rp), "name": name, "kind": kind})
    finally:
        (op / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return op


def list_ops() -> list:
    out = []
    if root().is_dir():
        for d in sorted(root().iterdir()):
            try:
                m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            m["dir"] = str(d)
            out.append(m)
    return out


def restore(op_dir) -> tuple:
    """Devuelve (restaurados, omitidos[motivo]). No pisa nada que ya exista en el destino."""
    d = Path(op_dir)
    m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    ok, skipped, left = 0, [], []
    for it in m["items"]:
        src, dst = d / it["name"], Path(it["orig"])
        if not (src.exists() or src.is_symlink()):
            continue
        if dst.exists() or dst.is_symlink():
            skipped.append(f"{dst} ya existe")
            left.append(it)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(src, dst)
        except OSError:
            shutil.move(str(src), str(dst))
        ok += 1
    if left:
        m["items"] = left
        (d / "meta.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    else:
        shutil.rmtree(d, ignore_errors=True)
    return ok, skipped


def empty() -> int:
    """Borra de verdad todo lo de la papelera. Devuelve cuántas operaciones."""
    ops = list_ops()
    for o in ops:
        shutil.rmtree(o["dir"], ignore_errors=True)
    return len(ops)
