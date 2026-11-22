"""Ajustes por juego sobre su games/<id>.toml del launcher unificado (editar con marcadores, con copia .hub-bak y validando con tomllib):
· portátil: partidas/configuración dentro de la carpeta del juego (XDG_CONFIG_HOME/XDG_DATA_HOME = $INSTALL_DIR/config|data) + preserve.
· selector en tu biblioteca: [run] cwd = <carpeta de ROMs de la plataforma>, para que el diálogo de «elegir archivo» del juego empiece ahí.
Nunca toca los datos del juego; solo copia (no mueve) las partidas que ya tenías cuando activas el modo portátil."""
import os
import re
import shutil
import tomllib
from pathlib import Path

from . import config

B_ENV = ("# hub:portable begin", "# hub:portable end")
CWD_MARK = "# hub:cwd-orig"


def path_of(lid) -> Path:
    return config.LAUNCHER / "games" / f"{lid}.toml"


def _load(p: Path):
    txt = p.read_text(encoding="utf-8")
    return txt, tomllib.loads(txt)


def state(lid) -> dict:
    p = path_of(lid)
    try:
        txt, t = _load(p)
    except (OSError, ValueError):
        return {"exists": False, "portable": False, "libcwd": False, "art": False}
    return {"exists": True, "portable": B_ENV[0] in txt, "libcwd": CWD_MARK in txt, "art": ART_B[0] in txt,
            "install_dir": str(Path(os.path.expandvars(str(t.get("install_dir", "")))).expanduser())}


def _write(p: Path, new: str):
    tomllib.loads(new)                                  # si no es TOML válido, no se escribe nada
    bak = p.with_suffix(".toml.hub-bak")
    if not bak.exists():
        shutil.copy2(p, bak)
    p.write_text(new, encoding="utf-8")


def _section_span(lines, name):
    """(inicio_cabecera, fin_exclusivo) de una tabla [name] o None."""
    for i, ln in enumerate(lines):
        if ln.strip() == f"[{name}]":
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("["):
                j += 1
            return i, j
    return None


def set_portable(lid, on: bool) -> str:
    p = path_of(lid)
    txt, _ = _load(p)
    lines = [ln for ln in txt.splitlines()]
    # quitar un bloque anterior
    out, skip = [], False
    for ln in lines:
        if ln.strip() == B_ENV[0]:
            skip = True
            continue
        if ln.strip() == B_ENV[1]:
            skip = False
            continue
        if not skip:
            out.append(ln)
    lines = out
    if on:
        block = [B_ENV[0], 'XDG_CONFIG_HOME = "$INSTALL_DIR/config"', 'XDG_DATA_HOME = "$INSTALL_DIR/data"', B_ENV[1]]
        sp = _section_span(lines, "run.env")
        if sp:
            lines[sp[0] + 1:sp[0] + 1] = block
        else:
            lines += ["", "[run.env]"] + block
        # preserve: que el actualizador nunca toque config/ ni data/
        for i, ln in enumerate(lines):
            m = re.match(r"^(\s*)preserve\s*=\s*\[(.*)\]\s*$", ln)
            if m:
                cur = re.findall(r'"([^"]*)"', m.group(2))
                for d in ("config/", "data/"):
                    if d not in cur:
                        cur.append(d)
                lines[i] = f'{m.group(1)}preserve = [' + ", ".join(f'"{c}"' for c in cur) + "]"
                break
    new = "\n".join(lines).rstrip("\n") + "\n"
    _write(p, new)
    return new


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _roots(roots=None):
    home = Path.home()
    return roots or [home / ".config", home / ".local" / "share"]


def find_old_data(names, roots=None) -> list:
    """[(carpeta, 'config'|'data')] que el juego ya creó en ~/.config y ~/.local/share (por parecido de nombre)."""
    keys = {_norm(n) for n in names if len(_norm(n)) >= 5}
    out = []
    for i, r in enumerate(_roots(roots)):
        try:
            for d in r.iterdir():
                n = _norm(d.name)
                if d.is_dir() and len(n) >= 5 and any(k in n or n in k for k in keys):
                    out.append((d, "config" if i == 0 else "data"))
        except OSError:
            continue
    return out


def migrate_data(install_dir, names, roots=None) -> list:
    """COPIA (no mueve) lo encontrado a <install_dir>/config|data/<nombre>; no pisa nada existente. Devuelve [(origen, destino)]."""
    done = []
    for d, base in find_old_data(names, roots):
        dest = Path(install_dir) / base / d.name
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(d, dest, symlinks=True)
        done.append((d, dest))
    return done


def set_libcwd(lid, folder, on: bool) -> str:
    """Pone/quita [run] cwd = <carpeta de la biblioteca>. Guarda el valor original en un comentario para poder volver."""
    p = path_of(lid)
    txt, _ = _load(p)
    lines = txt.splitlines()
    sp = _section_span(lines, "run")
    if not sp:
        raise ValueError("el .toml no tiene sección [run]")
    a, b = sp
    cwd_i = next((i for i in range(a + 1, b) if re.match(r"^\s*cwd\s*=", lines[i])), None)
    mark_i = next((i for i in range(a + 1, b) if lines[i].strip().startswith(CWD_MARK)), None)
    if on:
        orig = lines[cwd_i].split("=", 1)[1].strip() if (cwd_i is not None and mark_i is None) else None
        q = '"' + str(folder).replace("\\", "\\\\").replace('"', '\\"') + '"'
        if cwd_i is not None:
            lines[cwd_i] = f"cwd = {q}"
        else:
            lines.insert(a + 1, f"cwd = {q}")
            b += 1
        if mark_i is None:
            lines.insert(a + 1, f'{CWD_MARK} = {orig if orig else chr(34) + "." + chr(34)}')
    else:
        if mark_i is not None:
            orig = lines[mark_i].split("=", 1)[1].strip()
            if cwd_i is not None:
                lines[cwd_i] = f"cwd = {orig}"
            del lines[mark_i]
    new = "\n".join(lines).rstrip("\n") + "\n"
    _write(p, new)
    return new


ART_B = ("# hub:art begin", "# hub:art end")


def _strip_block(lines, mark):
    out, skip = [], False
    for ln in lines:
        if ln.strip() == mark[0]:
            skip = True
            continue
        if ln.strip() == mark[1]:
            skip = False
            continue
        if not skip:
            out.append(ln)
    return out


def set_art(lid, art: dict | None) -> str:
    """Enlaza el arte propio: [steam] icon/portrait/banner/hero/logo y [ui] background (hero). art=None lo quita.
    Si el .toml ya trae alguna de esas claves a mano, esa clave NO se pisa."""
    p = path_of(lid)
    txt, _ = _load(p)
    lines = _strip_block(txt.splitlines(), ART_B)
    if art:
        def have(sec, key):
            sp = _section_span(lines, sec)
            return bool(sp) and any(re.match(rf"^\s*{key}\s*=", lines[i]) for i in range(sp[0] + 1, sp[1]))
        for sec, keys in (("steam", {k: art[k] for k in ("icon", "portrait", "banner", "hero", "logo") if k in art}),
                          ("ui", {"background": art.get("hero")} if art.get("hero") else {})):
            add = [f'{k} = "{v}"' for k, v in keys.items() if not have(sec, k)]
            if not add:
                continue
            blk = [ART_B[0]] + add + [ART_B[1]]
            sp = _section_span(lines, sec)
            if sp:
                lines[sp[0] + 1:sp[0] + 1] = blk
            else:
                lines += ["", f"[{sec}]"] + blk
    new = "\n".join(lines).rstrip("\n") + "\n"
    _write(p, new)
    return new
