"""Versión de Linux y versión de Windows (Proton) del MISMO juego, dentro de su carpeta:

    <carpeta del juego>/linux/            lo que ya tenías (el build nativo)
    <carpeta del juego>/windows/          el build de Windows + hub-run.sh (umu-run + GE-Proton)
    <carpeta del juego>/proton-prefix/    el «disco C:» de Proton de este juego (sus partidas de Windows viven aquí)
    <carpeta del juego>/.hub-versions.json

La elegida se aplica al games/<id>.toml del launcher (install_dir, [run] exe, [update] asset), así JUGAR en Hub y el acceso de Steam
(shortcuts/<id>.sh → bin/play <id>) abren siempre la misma. Mover a linux/ es un renombrado dentro del mismo disco, con diario para deshacerlo."""
import json
import os
import re
import shutil
import stat
import subprocess
import tomllib
from pathlib import Path

from . import config, gamecfg, install

META = ".hub-versions.json"
JOURNAL = ".hub-move.json"
SUBS = ("linux", "windows")
RUNNER = "hub-run.sh"
_SKIP_EXE = re.compile(r"setup|unins|install|vc_?redist|dxsetup|crash|report|update|helper|launcher_?config", re.I)


def _expand(p) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(p))))


def _tilde(p: Path) -> str:
    s, h = str(p), str(Path.home())
    return "~" + s[len(h):] if s.startswith(h + "/") else s


def _toml(lid):
    p = gamecfg.path_of(lid)
    txt = p.read_text(encoding="utf-8")
    return p, txt, tomllib.loads(txt)


def root_of(lid) -> Path | None:
    """Carpeta del juego (la de arriba de linux/ y windows/ si ya está reorganizado)."""
    try:
        _, _, t = _toml(lid)
    except (OSError, ValueError):
        return None
    d = _expand(t.get("install_dir", ""))
    return d.parent if d.name in SUBS and (d.parent / META).exists() else d


def meta(root: Path) -> dict:
    try:
        return json.loads((Path(root) / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_meta(root: Path, m: dict):
    (Path(root) / META).write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")


def folders(lid) -> dict:
    """Dónde está el juego (install_dir) y su carpeta de trabajo ([run] cwd, relativa a install_dir)."""
    try:
        _, _, t = _toml(lid)
    except (OSError, ValueError):
        return {"dir": "", "cwd": ""}
    d = _expand(t.get("install_dir", ""))
    c = str((t.get("run") or {}).get("cwd") or ".")
    cp = _expand(c)
    return {"dir": str(d), "cwd": str(cp if cp.is_absolute() else (d / c).resolve() if c != "." else d)}


def state(lid) -> dict:
    """{root, split, active, linux, windows} — linux/windows: True si esa versión está en disco."""
    r = root_of(lid)
    if r is None:
        return {"root": None, "split": False, "active": "linux", "linux": False, "windows": False}
    m = meta(r)
    split = bool(m) and ((r / "linux").is_dir() or (r / "windows").is_dir())
    return {"root": r, "split": split, "active": m.get("active", "linux"),
            "linux": (r / "linux").is_dir() if split else (r.is_dir() and any(r.iterdir())),
            "windows": (r / "windows" / RUNNER).is_file(), "meta": m}


# ── reorganizar: lo actual pasa a linux/ ─────────────────────
def split(lid) -> Path:
    """Mueve el contenido de la carpeta del juego a <carpeta>/linux (renombrados; con diario) y apunta el .toml allí. Idempotente."""
    p, txt, t = _toml(lid)
    root = _expand(t.get("install_dir", ""))
    if root.name in SUBS and (root.parent / META).exists():
        return root.parent
    if not root.is_dir():
        raise OSError(f"no existe {root}")
    lin = root / "linux"
    if lin.exists() and not lin.is_dir():
        raise OSError(f"{lin} existe y no es una carpeta")
    lin.mkdir(exist_ok=True)
    items = [x for x in root.iterdir() if x.name not in (*SUBS, META, JOURNAL, "proton-prefix")]
    jr = root / JOURNAL
    moved = []
    try:
        for x in items:
            dst = lin / x.name
            if dst.exists() or dst.is_symlink():
                raise OSError(f"ya existe {dst}; no piso nada")
            os.rename(x, dst)                      # mismo disco: instantáneo y sin copiar
            moved.append(x.name)
            jr.write_text(json.dumps({"moved": moved}), encoding="utf-8")
    except OSError:
        for n in reversed(moved):                  # deshacer lo movido
            try:
                os.rename(lin / n, root / n)
            except OSError:
                pass
        jr.unlink(missing_ok=True)
        if not any(lin.iterdir()):
            lin.rmdir()
        raise
    exe = (t.get("run") or {}).get("exe", "")
    up = t.get("update") or {}
    m = {"active": "linux", "linux": {"exe": exe, "asset": up.get("asset", ""), "executables": up.get("executables") or ([exe] if exe else []),
                                      "require": (t.get("run") or {}).get("require") or []},
         "moved": moved}
    _save_meta(root, m)
    jr.unlink(missing_ok=True)
    _apply(lid, root, "linux", m)
    return root


def unsplit(lid) -> Path:
    """Deshace la reorganización si solo hay versión de Linux: todo vuelve a la carpeta del juego."""
    st = state(lid)
    root = st["root"]
    if not st["split"]:
        return root
    if st["windows"]:
        raise OSError("hay versión de Windows: bórrala antes de deshacer (o déjalo reorganizado)")
    lin = root / "linux"
    for x in list(lin.iterdir()):
        if (root / x.name).exists():
            raise OSError(f"ya existe {root / x.name}; no piso nada")
    for x in list(lin.iterdir()):
        os.rename(x, root / x.name)
    lin.rmdir()
    m = st["meta"]
    _set_toml(lid, root, (m.get("linux") or {}).get("exe", ""), (m.get("linux") or {}).get("asset", ""),
              (m.get("linux") or {}).get("executables") or [], (m.get("linux") or {}).get("require"))
    (root / META).unlink(missing_ok=True)
    return root


# ── versión de Windows ───────────────────────────────────────
def find_exe(d: Path, hint="") -> str:
    """El .exe del juego (no instaladores, redistribuibles ni lanzadores de crash), relativo a d."""
    d = Path(d)
    hint = re.sub(r"[^a-z0-9]", "", str(hint).lower())
    cands = []
    for p in d.rglob("*.exe"):
        if len(p.relative_to(d).parts) > 3 or _SKIP_EXE.search(p.name):
            continue
        sc = 10 - 2 * (len(p.relative_to(d).parts) - 1)
        nm = re.sub(r"[^a-z0-9]", "", p.stem.lower())
        if hint and (hint in nm or nm in hint):
            sc += 20
        try:
            sc += min(10, p.stat().st_size >> 22)   # el juego suele ser el .exe grande
        except OSError:
            pass
        cands.append((sc, p))
    if not cands:
        return ""
    best = max(cands, key=lambda c: c[0])[1]
    # v2.58: si junto al .exe elegido hay «<nombre>_Launcher.exe» (Silent Hill: SilentHillPC.exe + SilentHillPC_Launcher.exe), el juego
    # solo arranca bien desde su launcher (escribe config.cfg y lo lanza): se prefiere ese
    for sfx in ("_Launcher", "Launcher", "-Launcher", "_launcher"):
        lau = best.with_name(best.stem + sfx + best.suffix)
        if lau.is_file():
            return str(lau.relative_to(d))
    return str(best.relative_to(d))


DEFAULT_PROTON = ""   # v2.65: lo fija Hub al arrancar y al cambiarlo en Ajustes → Al jugar (carpeta de un Proton de compatibilitytools.d)


def proton_path() -> str:
    """Proton para umu-run. Orden: $HUB_PROTON; UMU-Proton más reciente; GE-Proton más reciente; si no hay, 'UMU-Proton' (umu lo descarga).
    UMU-Proton va primero porque GE-Proton11-11 aborta en esta máquina (win32u.NtGdiCreateColorSpace sin implementar) y UMU-Proton-10 abre Silent Hill."""
    env = os.environ.get("HUB_PROTON", "").strip()
    if env:
        return env
    d = DEFAULT_PROTON.strip()
    if d and (Path(d) / "proton").is_file():
        return d
    umu, ge = [], []
    for base in (Path.home() / ".local/share/Steam/compatibilitytools.d", Path.home() / ".steam/root/compatibilitytools.d"):
        try:
            for d in base.iterdir():
                if not (d / "proton").is_file():
                    continue
                nums = tuple(int(x) for x in re.findall(r"\d+", d.name)[:3])
                if d.name.startswith("UMU-Proton"):
                    umu.append((nums, -len(d.name), str(d)))
                elif d.name.startswith("GE-Proton"):
                    ge.append((nums, -len(d.name), str(d)))
        except OSError:
            continue
    for lst in (umu, ge):
        if lst:
            return max(lst)[2]
    return "UMU-Proton"


def list_protons() -> list:
    """[(nombre, ruta)] de los Proton instalados (UMU-Proton, GE-Proton, Proton-…) en compatibilitytools.d, el más nuevo primero."""
    out = {}
    for base in (Path.home() / ".local/share/Steam/compatibilitytools.d", Path.home() / ".steam/root/compatibilitytools.d"):
        try:
            for d in base.iterdir():
                if (d / "proton").is_file():
                    out.setdefault(d.name, str(d))
        except OSError:
            continue
    return sorted(out.items(), key=lambda kv: (kv[0].startswith("UMU"), tuple(int(x) for x in re.findall(r"\d+", kv[0])[:3]), kv[0]), reverse=True)


def windows_proton(lid) -> str:
    """Proton fijado para este juego ('' = automático)."""
    r = root_of(lid)
    return str(((meta(r) if r else {}).get("windows") or {}).get("proton") or "")


def set_windows_proton(lid, path: str) -> str:
    """Fija con qué Proton se abre ESTE juego ('' = automático) y reescribe windows/hub-run.sh si usa Proton. No toca el prefijo."""
    r = root_of(lid)
    if r is None:
        raise OSError("no encuentro la carpeta del juego")
    m = meta(r)
    w = m.get("windows") or {}
    if not w:
        raise OSError("este juego no tiene versión de Windows")
    if path:
        w["proton"] = path
    else:
        w.pop("proton", None)
    m["windows"] = w
    _save_meta(r, m)
    if (w.get("runner") or "proton") == "proton":
        set_windows_runner(lid, "proton")
    return path


WINE_GLOBS = (".var/app/com.usebottles.bottles/data/bottles/runners/*/bin/wine", ".var/app/net.lutris.Lutris/data/lutris/runners/wine/*/bin/wine",
              ".local/share/lutris/runners/wine/*/bin/wine", ".local/share/Steam/compatibilitytools.d/*/files/bin/wine",
              ".steam/root/compatibilitytools.d/*/files/bin/wine")
# Bazzite no trae «wine» en el sistema: se usa el de Bottles, Lutris o el que lleva dentro GE-Proton (v2.31)
WINE_FIND = ('if ! command -v wine >/dev/null 2>&1; then   # sin Wine en el sistema: el de Bottles, Lutris o el de GE-Proton\n'
             '  for w in ' + " ".join(f'"$HOME"/{g}' for g in WINE_GLOBS) + '; do\n'
             '    [ -x "$w" ] && { PATH="$(dirname "$w"):$PATH"; export PATH; break; }\n'
             '  done\n'
             'fi\n'
             'command -v wine >/dev/null 2>&1 || { echo "Recomp Hub: no hay Wine (instala un runner en Bottles o elige Proton)" >&2; exit 127; }\n')


def find_wine() -> str:
    """Ruta del «wine» que usará el juego: el del sistema o, si no hay, el de Bottles / Lutris / GE-Proton. "" si no hay ninguno."""
    w = shutil.which("wine")
    if w:
        return w
    home = Path.home()
    for g in WINE_GLOBS:
        try:
            c = sorted((p for p in home.glob(g) if os.access(p, os.X_OK)), key=lambda p: str(p))
        except OSError:
            continue
        if c:
            return str(c[-1])
    return ""


WINE_DISPLAY = ('[ -z "$DISPLAY" ] && export DISPLAY=:0   # v2.54/55: lanzado por SSH/terminal remota → pantalla del escritorio (XWayland)\n'
                'if [ -z "$XAUTHORITY" ]; then   # sin esto X responde «Authorization required»\n'
                '  for a in "/run/user/$(id -u)"/xauth_* "$HOME/.Xauthority"; do [ -f "$a" ] && { export XAUTHORITY="$a"; break; }; done\n'
                'fi\n')


WINE_CLEAN = ('unset LD_PRELOAD   # v2.56: lanzado por Steam hereda la superposición de Steam (gameoverlayrenderer), que rompe a Wine\n'
              'case "$LD_LIBRARY_PATH" in *[Ss]team*) unset LD_LIBRARY_PATH;; esac\n'
              'unset WINEDLLOVERRIDES mesa_glthread   # el modo juego los pone (dxgi=n, glthread) y el juego cae con «page fault 0x0»\n'
              'unset SDL_VIDEODRIVER SDL_AUDIODRIVER   # v2.63: el modo juego pone SDL_VIDEODRIVER=x11; el SDL2.dll de Windows no tiene ese driver («Failed to initialise SDL»)\n')
WINE_LOG = ('export WINEDEBUG="${WINEDEBUG:--all,err+all,fixme+all}"   # v2.53: lo que diga Wine queda en ../hub-wine.log\n'
            'echo "=== $(date) · $0 ===" >>"$HERE/../hub-wine.log"\n')


def runner_text(exe_rel: str, proton: str, runner: str = "proton") -> str:
    if runner == "wine":
        return ("#!/bin/sh\n"
                "# Recomp Hub: versión de Windows con Wine del sistema. Puedes editar este archivo.\n"
                'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
                'export WINEPREFIX="${WINEPREFIX:-$HERE/../proton-prefix}"   # el «C:» de este juego\n'
                'mkdir -p "$WINEPREFIX"\n'
                f'cd -P "$(dirname "$HERE/{exe_rel}")" || exit 1\n'
                + WINE_FIND + WINE_DISPLAY + WINE_CLEAN + WINE_LOG +
                f'exec wine "$HERE/{exe_rel}" "$@" >>"$HERE/../hub-wine.log" 2>&1\n')
    return ("#!/bin/sh\n"
            "# Recomp Hub: versión de Windows con Proton (umu-run). Puedes editar este archivo.\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            'export WINEPREFIX="${WINEPREFIX:-$HERE/../proton-prefix}"   # el «C:» de este juego: sus partidas de Windows están aquí\n'
            'export GAMEID="${GAMEID:-0}"\n'
            f'export PROTONPATH="${{PROTONPATH:-{proton}}}"\n'
            'mkdir -p "$WINEPREFIX"\n'
            + WINE_DISPLAY + WINE_CLEAN +
            'if [ -f "$HERE/../.proton-log" ]; then   # registro de Proton: ./proton-logs/steam-0.log (actívalo desde la ficha del juego)\n'
            '  export PROTON_LOG=1 PROTON_LOG_DIR="$HERE/../proton-logs"; mkdir -p "$PROTON_LOG_DIR"\n'
            "fi\n"
            f'cd -P "$(dirname "$HERE/{exe_rel}")" || exit 1   # el juego busca config.cfg y gamedata/ junto a su .exe; Steam lo lanza desde otra carpeta\n'
            f'exec umu-run "$HERE/{exe_rel}" "$@"\n')


def local_runner_text(exe_rel: str, cwd_rel: str, proton: str, runner: str = "proton") -> str:
    """hub-run.sh para un juego de Windows que ya tenías (windows/game → su carpeta). Registro de Proton: crea el archivo .proton-log junto a proton-prefix."""
    head = ("#!/bin/sh\n"
            "# Recomp Hub: versión de Windows de un juego que ya tenías. Puedes editar este archivo.\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            'export WINEPREFIX="${WINEPREFIX:-$HERE/../proton-prefix}"   # el «C:» de este juego: sus partidas de Windows están aquí\n'
            'mkdir -p "$WINEPREFIX"\n'
            'if [ -f "$HERE/../.proton-log" ]; then   # registro: ./proton-logs/steam-0.log (créalo desde la ficha del juego)\n'
            '  export PROTON_LOG=1 PROTON_LOG_DIR="$HERE/../proton-logs"; mkdir -p "$PROTON_LOG_DIR"\n'
            "fi\n"
            f'cd -P "$HERE/{cwd_rel}" || exit 1\n')
    if runner == "wine":
        return head + WINE_FIND + WINE_DISPLAY + WINE_CLEAN + WINE_LOG + f'exec wine "$HERE/{exe_rel}" "$@" >>"$HERE/../hub-wine.log" 2>&1\n'
    return (head + WINE_DISPLAY + WINE_CLEAN + 'export GAMEID="${GAMEID:-0}"\n'
            f'export PROTONPATH="${{PROTONPATH:-{proton}}}"\n'
            f'exec umu-run "$HERE/{exe_rel}" "$@"\n')


def attach_windows(lid, exe: Path, runner: str = "proton") -> dict:
    """Usa un juego de Windows que ya está en tu disco: <carpeta>/windows/game enlaza a la carpeta del .exe (no se copia ni se toca)
    y hub-run.sh lo abre con Proton (umu-run) o Wine. Reorganiza antes la carpeta del juego (lo actual pasa a linux/)."""
    exe = Path(exe).expanduser()
    if not exe.is_file() or exe.suffix.lower() != ".exe":
        raise OSError("elige el archivo .exe del juego")
    if runner not in ("proton", "wine"):
        raise ValueError(runner)
    _, _, t = _toml(lid)
    idir = _expand(t.get("install_dir", ""))
    if idir.name not in SUBS:
        idir.mkdir(parents=True, exist_ok=True)
    try:
        inside = exe.resolve().relative_to(idir.resolve())       # el .exe está dentro de la carpeta del juego: split() lo va a mover a linux/
    except ValueError:
        inside = None
    root = split(lid)
    lin = root / "linux"
    if inside is not None and not exe.exists() and (lin / inside).is_file():
        exe = lin / inside                                       # v2.52: antes el enlace apuntaba a la raíz, ya vacía → «game/…exe» no existía
    if lin.is_dir() and not any(lin.iterdir()):
        lin.rmdir()
    win = root / "windows"
    win.mkdir(exist_ok=True)
    link = win / "game"
    if link.is_symlink() or link.exists():
        if not link.is_symlink():
            raise OSError(f"{link} existe y no es un enlace; no piso nada")
        link.unlink()
    link.symlink_to(exe.parent.resolve())
    r = win / RUNNER
    r.write_text(local_runner_text(f"game/{exe.name}", "game", proton_path(), runner), encoding="utf-8")
    r.chmod(r.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    m = meta(root)
    m["windows"] = {"exe": RUNNER, "game_exe": f"game/{exe.name}", "asset": "", "executables": [RUNNER], "local": str(exe.parent.resolve()), "runner": runner}
    _save_meta(root, m)
    set_active(lid, "windows")
    return {"root": str(root), "exe": exe.name, "runner": runner}


def link_file(src, dst) -> bool:
    """v3.03: deja en `dst` tu ISO/ROM. Primero un ENLACE DURO (mismo archivo, sin copiar; Wine lo ve como un archivo normal: el enlace
    simbólico no aparecía en el selector del instalador de ReStreet) y, si está en otro disco, un enlace simbólico. Nunca pisa un archivo real:
    solo sustituye enlaces simbólicos (los que dejó Hub). Devuelve True si cambió algo."""
    src, dst = Path(src).resolve(), Path(dst)
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        return False                                  # archivo real (o el enlace duro ya hecho): no se toca
    try:
        os.link(src, dst)
    except OSError:
        dst.symlink_to(src)
    return True


def link_into_prefix(lid, target: Path):
    """Enlaza `target` (tu ISO/ROM) en Escritorio y Documentos del usuario de Windows del prefijo del juego (…/proton-prefix/…/drive_c/users/<usuario>).
    Devuelve las rutas creadas ([] si ya estaban) o None si el prefijo aún no tiene usuarios (Proton lo crea en el primer arranque). Nunca pisa un archivo."""
    root = root_of(lid)
    target = Path(target)
    if root is None or not target.exists():
        return []
    made = []
    found = False
    for base in (root / "proton-prefix", root / "proton-prefix" / "pfx"):
        users = base / "drive_c" / "users"
        if not users.is_dir():
            continue
        for u in sorted(users.iterdir()):
            if not u.is_dir() or u.name.lower() in ("public", "all users", "default"):
                continue
            found = True
            for sub in ("Desktop", "Documents"):
                d = u / sub
                try:
                    d.mkdir(exist_ok=True)
                    ln = d / target.name
                    if link_file(target, ln):
                        made.append(str(ln))
                except OSError:
                    continue
    return made if found else None


def proton_log(lid) -> bool:
    r = root_of(lid)
    return bool(r and (r / ".proton-log").exists())


def set_proton_log(lid, on: bool):
    r = root_of(lid)
    if r is None:
        raise OSError("no encuentro la carpeta del juego")
    f = r / ".proton-log"
    if on:
        f.write_text("1")
    else:
        f.unlink(missing_ok=True)


def install_windows(lid, archive: Path, version="", asset_glob="", hint="") -> dict:
    """Extrae el build de Windows en <carpeta>/windows, escribe hub-run.sh y lo activa. Reorganiza antes si hacía falta."""
    root = split(lid)
    win = root / "windows"
    keep = {}                                          # v2.68: ajustes del launcher de GoW PSP sobreviven a la actualización
    for f in win.glob("**/GoW_PSP_data/build/launcher*"):
        try:
            if f.is_file():
                keep[f] = f.read_bytes()
        except OSError:
            pass
    if win.is_dir() and any(win.iterdir()):             # v2.78: por etapas y con vuelta atrás; no pisa saves, ISO enlazada ni el actualizador propio
        def _val(stg):
            if not find_exe(stg, hint):
                raise OSError("el paquete de Windows no trae un .exe reconocible: no toco tu instalación")
        install.apply_update(Path(archive), win, need_exe=False, validate=_val)
    else:
        install.extract(Path(archive), win)
    for f, data in keep.items():
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        except OSError:
            pass
    exe = find_exe(win, hint)
    if not exe:
        raise OSError("el paquete de Windows no trae un .exe reconocible")
    r = win / RUNNER
    r.write_text(runner_text(exe, proton_path()), encoding="utf-8")
    r.chmod(r.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    if version:
        (win / ".release_version").write_text(version, encoding="utf-8")
    m = meta(root)
    prev = m.get("windows") or {}
    m["windows"] = {"exe": RUNNER, "game_exe": exe, "asset": asset_glob, "executables": [RUNNER], "runner": "proton"}
    if prev.get("runner") in ("wine", "own"):         # v2.40: actualizar no devuelve el juego a Proton
        m["windows"]["runner"] = prev["runner"]
        if prev["runner"] == "wine":
            r.write_text(runner_text(exe, proton_path(), "wine"), encoding="utf-8")
        else:
            from . import ownwine
            m["windows"]["own"] = prev.get("own") or {}
            if ownwine.supported(win, m["windows"]):
                gone = ownwine.clean_build(win, m["windows"]) if version and ownwine.cfg(m["windows"])["profile"] == "gow" else []
                ownwine.write_script(win, m["windows"])
                m["windows"]["rebuild"] = bool(gone) or bool(prev.get("rebuild"))
    for k in ("proton", "skip_launcher"):             # v2.67: actualizar conserva el Proton elegido y «saltar el launcher»
        if prev.get(k):
            m["windows"][k] = prev[k]
    _save_meta(root, m)
    if (prev.get("proton") or prev.get("skip_launcher")) and m["windows"]["runner"] in ("proton", "wine"):
        set_windows_runner(lid, m["windows"]["runner"])      # reescribe hub-run.sh con esas dos elecciones
    set_active(lid, "windows")
    return {"root": str(root), "exe": exe}


def install_windows_only(entry: dict, archive: Path, version="", asset_name="") -> dict:
    """Juego que solo publica build de Windows: <carpeta>/windows + hub-run.sh y su .toml (sin versión de Linux)."""
    root = config.GAMES_DIR / entry.get("folder", entry["id"])
    win = root / "windows"
    install.extract(Path(archive), win)
    exe = find_exe(win, entry.get("name", ""))
    if not exe:
        raise OSError("el paquete de Windows no trae un .exe reconocible")
    r = win / RUNNER
    r.write_text(runner_text(exe, proton_path()), encoding="utf-8")
    r.chmod(r.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    glob = asset_glob(asset_name) if asset_name else ""
    toml = install.register(entry, win, RUNNER, glob, version)
    _save_meta(root, {"active": "windows", "windows": {"exe": RUNNER, "game_exe": exe, "asset": glob, "executables": [RUNNER]}})
    return {"dir": str(win), "exe": exe, "toml": str(toml)}


def asset_glob(name: str) -> str:
    """Patrón estable para las actualizaciones del launcher: SHPC-windows-x64_2026.09.27.1.zip → *windows-x64*.zip."""
    n = name.lower()
    ext = next((e for e in (".tar.gz", ".tar.xz", ".zip", ".7z", ".tgz") if n.endswith(e)), Path(n).suffix)
    m = re.search(r"(win(dows|64|32)?[-_.]?(x64|x86_64|amd64)?)", n)
    return f"*{m.group(1).strip('-_.')}*{ext}" if m else name


# ── aplicar la elegida al .toml ──────────────────────────────
def _set_kv(lines, section, key, val_toml):
    sp = gamecfg._section_span(lines, section)
    if sp is None:
        if val_toml is None:
            return lines
        return lines + ["", f"[{section}]", f"{key} = {val_toml}"]
    i, j = sp
    for k in range(i + 1, j):
        if re.match(rf"\s*{re.escape(key)}\s*=", lines[k]):
            if val_toml is None:
                return lines[:k] + lines[k + 1:]
            return lines[:k] + [f"{key} = {val_toml}"] + lines[k + 1:]
    if val_toml is None:
        return lines
    return lines[:j] + [f"{key} = {val_toml}"] + lines[j:]


def _q(s):
    return json.dumps(str(s), ensure_ascii=False)


def _set_toml(lid, idir: Path, exe: str, asset: str, executables, require, update_type=None, run_type=None):
    p, txt, t = _toml(lid)
    lines = txt.split("\n")
    for k, ln in enumerate(lines):           # install_dir está arriba, fuera de toda tabla
        if ln.lstrip().startswith("["):
            break
        if re.match(r"\s*install_dir\s*=", ln):
            lines[k] = f"install_dir = {_q(_tilde(idir))}"
    lines = _set_kv(lines, "run", "exe", _q(exe))
    if run_type:
        lines = _set_kv(lines, "run", "type", _q(run_type))
    if update_type and (t.get("update") or {}).get("type") is not None:
        lines = _set_kv(lines, "update", "type", _q(update_type))
    if require is not None:
        lines = _set_kv(lines, "run", "require", "[" + ", ".join(_q(x) for x in require) + "]" if require else None)
    if (t.get("update") or {}).get("type") == "github-archive":
        if asset:
            lines = _set_kv(lines, "update", "asset", _q(asset))
        lines = _set_kv(lines, "update", "executables", "[" + ", ".join(_q(x) for x in executables) + "]" if executables else None)
    gamecfg._write(p, "\n".join(lines))


def _apply(lid, root: Path, which: str, m: dict):
    v = m.get(which) or {}
    req = list((m.get("linux") or {}).get("require") or [])
    lexe = (m.get("linux") or {}).get("exe", "")
    if which == "windows":
        # lo que el port exige junto al ejecutable (datos del juego, enlaces a tu ROM…) se enlaza desde linux/, sin copiar
        others = [r for r in req if r != lexe]
        for r in others:
            src, dst = root / "linux" / r, root / "windows" / r
            if (src.exists() or src.is_symlink()) and not (dst.exists() or dst.is_symlink()):
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.symlink_to(src.resolve() if src.is_symlink() else src)
        req = [v.get("exe", RUNNER)] + others if req else []
        # enlaces a tu ROM que Hub dejó en linux/ (place_default): la versión de Windows también los necesita
        for x in ((root / "linux").iterdir() if (root / "linux").is_dir() else []):
            dst = root / "windows" / x.name
            if x.is_symlink() and not (dst.exists() or dst.is_symlink()):
                try:
                    tgt = Path(os.readlink(x))
                    if tgt.is_absolute() and root not in tgt.parents:
                        dst.symlink_to(tgt)
                except OSError:
                    pass
    _set_toml(lid, root / which, v.get("exe", ""), v.get("asset", ""), v.get("executables") or [], req if req else None,
              update_type=_update_type_for(lid, m, v), run_type=v.get("run_type"))


def set_update_type(lid, typ: str) -> str:
    """v2.43: cambia `[update] type` del .toml del launcher (p. ej. «none» para congelar un juego: ni comprueba ni pregunta ni actualiza).
    Devuelve el tipo que tenía. Lanza OSError si el .toml no tiene [update]."""
    p, txt, t = _toml(lid)
    cur = (t.get("update") or {}).get("type")
    if cur is None:
        raise OSError("el .toml del launcher no tiene [update]")
    if cur != typ:
        gamecfg._write(p, "\n".join(_set_kv(txt.split("\n"), "update", "type", _q(typ))))
    return cur


def _update_type_for(lid, m: dict, v: dict):
    """Un build compilado aquí (o un .exe de Windows elegido a mano) no se actualiza con el archivo de la release: [update] type = «none» mientras esté activo
    y se restaura el original (github-archive…) al volver a otra versión."""
    try:
        cur = (_toml(lid)[2].get("update") or {}).get("type")
    except (OSError, ValueError):
        return None
    if v.get("built") or v.get("local"):      # v3.00: también un .exe de Windows elegido a mano (ya tenías el juego, o lo dejó un instalador):
        if cur and cur != "none":              # el launcher no tiene su versión en windows/ y lo «actualizaba» (lo volvía a bajar) en cada arranque
            m["saved_update_type"] = cur
        return "none"
    return m.pop("saved_update_type", None) if cur == "none" else None


def use_hub_script(lid) -> str:
    """Reescribe hub-run.sh con lo que Hub tiene configurado (Wine, prefijo…); el script editado a mano queda como hub-run.sh.mio."""
    from . import ownwine
    r = root_of(lid)
    if r is None:
        raise OSError("no encuentro la carpeta del juego")
    w = meta(r).get("windows") or {}
    return ownwine.write_script(r / "windows", w, force=True)


def set_active(lid, which: str) -> dict:
    if which not in SUBS:
        raise ValueError(which)
    st = state(lid)
    if not st["split"] or not st[which]:
        raise OSError(f"no hay versión de {'Windows' if which == 'windows' else 'Linux'} instalada")
    m = st["meta"]
    _apply(lid, st["root"], which, m)
    m["active"] = which
    _save_meta(st["root"], m)
    return state(lid)


# ── build nativo compilado en un contenedor y «ejecutar dentro del distrobox» ─────────
def attach_linux_build(lid, exe_rel: str, cwd_rel: str, libs_rel: str, container: str, recipe_id: str = "", activate: bool = True) -> dict:
    """Registra <carpeta>/linux/<exe_rel> (compilado en `container`) como la versión de Linux: escribe linux/hub-run.sh y la activa.
    Si la carpeta aún no está reorganizada (solo hay windows/), crea el diario .hub-versions.json sin mover nada."""
    from . import recipes
    root = root_of(lid)
    if root is None or not (root / "linux").is_dir():
        raise OSError("no encuentro la carpeta linux/ del juego")
    lin = root / "linux"
    if not (lin / exe_rel).is_file():
        raise OSError(f"no existe {lin / exe_rel}: compila primero")
    r = lin / RUNNER
    r.write_text(recipes.runner_text(exe_rel, cwd_rel, libs_rel, container), encoding="utf-8")
    r.chmod(r.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    if in_container(lid) and not (meta(root).get("linux") or {}).get("built"):
        set_in_container(lid, False)           # deshace el envoltorio de la release antes de guardarla
    m = meta(root) or {"active": "windows" if (root / "windows" / RUNNER).is_file() else "linux"}
    prev = m.get("linux")
    if prev and not prev.get("built"):
        m["linux_release"] = prev              # la release (AppImage/binario) se conserva para poder volver a ella
    m["linux"] = {"exe": RUNNER, "asset": "", "executables": [RUNNER], "require": [], "built": {"exe": exe_rel, "cwd": cwd_rel, "libs": libs_rel,
                                                                                            "container": container, "recipe": recipe_id}}
    m["linux_built"] = m["linux"]
    m["container"] = container
    _save_meta(root, m)
    if activate:
        set_active(lid, "linux")
    return state(lid)


def versions(lid) -> dict:
    """{'Linux': 'v0.3.0', 'Windows': 'v0.2.4'}: la versión instalada de cada sistema (lee .release_version de linux/ y windows/; en una carpeta sin dividir, la de la raíz)."""
    r = root_of(lid)
    if r is None:
        return {}
    out = {}

    def rd(d):
        try:
            return (Path(d) / ".release_version").read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    if (r / "linux").is_dir() or (r / "windows").is_dir():
        if (r / "linux").is_dir():
            out["Linux"] = rd(r / "linux")
        if (r / "windows").is_dir():
            out["Windows"] = rd(r / "windows")
    return out


def container_of(lid) -> str:
    """Distrobox de este juego (el de su receta o el que elegiste); '' si no hay."""
    r = root_of(lid)
    return str(meta(r).get("container", "")) if r else ""


def set_container(lid, name: str):
    r = root_of(lid)
    if r is None:
        raise OSError("no encuentro la carpeta del juego")
    m = meta(r)
    if not m:
        raise OSError("este juego aún no tiene versiones separadas (linux/ y windows/)")
    m["container"] = name
    _save_meta(r, m)


def in_container(lid) -> bool:
    """¿La versión de Linux se abre dentro del distrobox?"""
    r = root_of(lid)
    if not r:
        return False
    v = meta(r).get("linux") or {}
    return bool((r / "linux" / ".run-in-container").exists()) if v.get("built") else bool(v.get("container_wrap"))


def _retarget_runner(script: Path, cont: str) -> bool:
    """Cambia el contenedor escrito en un hub-run.sh de build nativo: `exec distrobox enter <viejo> -- ...` → <cont>. Sin eso, elegir otro
    contenedor después de compilar no cambiaba dónde se lanza el juego."""
    import re, shlex
    try:
        t = script.read_text(encoding="utf-8")
    except OSError:
        return False
    n = re.sub(r"(exec distrobox enter )(\S+|'[^']*')( --)", lambda m: m.group(1) + shlex.quote(cont) + m.group(3), t)
    if n != t:
        script.write_text(n, encoding="utf-8")
    return n != t


def set_in_container(lid, on: bool, container: str = "") -> bool:
    """Ficha → «Ejecutar en»: sistema / contenedor.
    · build compilado por Hub: crea/quita linux/.run-in-container (hub-run.sh lo mira).
    · cualquier otra versión de Linux (p. ej. un AppImage): pone/quita un envoltorio hub-container.sh que lo abre con `distrobox enter`."""
    from . import recipes
    st = state(lid)
    root = st["root"]
    if root is None or not st["linux"]:
        raise OSError("no hay versión de Linux instalada")
    m = st["meta"] or {}
    if not st["split"]:
        raise OSError("reorganiza la carpeta del juego primero (linux/ y windows/)")
    v = m.setdefault("linux", {})
    cont = container or m.get("container") or ""
    if on and not cont:
        raise OSError("elige antes el distrobox del juego")
    if v.get("built"):
        f = root / "linux" / ".run-in-container"
        if on:
            f.write_text(cont, encoding="utf-8")
            _retarget_runner(root / "linux" / "hub-run.sh", cont)    # v2.84: el nombre del contenedor está escrito DENTRO de hub-run.sh (de cuando se compiló)
        else:
            f.unlink(missing_ok=True)
        return on
    lin = root / "linux"
    wrap = lin / "hub-container.sh"
    if on:
        # el envoltorio se reescribe SIEMPRE (una versión nueva de Hub corrige los ya creados); el ejecutable original es el de la 1.ª vez
        orig = v.get("container_wrap")
        if not orig:
            try:
                t = _toml(lid)[2]
            except (OSError, ValueError):
                t = {}
            orig = {"exe": v.get("exe", ""), "executables": list(v.get("executables") or []), "run_type": (t.get("run") or {}).get("type", "binary"),
                    "cwd": str((t.get("run") or {}).get("cwd") or ".")}
        cwd = _expand(orig.get("cwd") or ".")
        exe_abs = Path(orig["exe"]) if Path(orig["exe"]).is_absolute() else (lin / orig["exe"]).resolve()
        appimg = orig["run_type"] == "appimage" or str(exe_abs).lower().endswith(".appimage")
        cwd_abs = cwd if cwd.is_absolute() else (lin / cwd).resolve()
        wrap.write_text(recipes.container_wrapper_text(str(exe_abs), cont, str(cwd_abs), appimg), encoding="utf-8")
        wrap.chmod(wrap.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
        v["container_wrap"] = orig
        v["exe"], v["run_type"] = "hub-container.sh", "binary"
        v["executables"] = ["hub-container.sh"] + [x for x in v["container_wrap"]["executables"] if x != "hub-container.sh"]   # el AppImage nuevo de una actualización necesita seguir siendo ejecutable
    else:
        o = v.pop("container_wrap", None)
        if o:
            v["exe"], v["executables"], v["run_type"] = o["exe"], o["executables"], o["run_type"]
            wrap.unlink(missing_ok=True)
    m["linux"] = v
    _save_meta(root, m)
    if m.get("active") == "linux":
        _apply(lid, root, "linux", m)
        _save_meta(root, m)
    return on


# ── Windows: Proton o Wine ───────────────────────────────────
def windows_runner(lid) -> str:
    r = root_of(lid)
    return (meta(r).get("windows") or {}).get("runner", "proton") if r else "proton"


def set_own(lid, **changes) -> dict:
    """Cambia ajustes de «Wine propio» de un juego (binary, prefix, overrides, mode, game…) y reescribe windows/hub-run.sh."""
    from . import ownwine
    r = root_of(lid)
    if r is None:
        raise OSError("no encuentro la carpeta del juego")
    m = meta(r)
    w = m.get("windows") or {}
    w["own"] = dict(ownwine.cfg(w), **changes)
    ownwine.write_script(r / "windows", w)
    m["windows"] = w
    _save_meta(r, m)
    return w["own"]


_LAU_SFX = ("_Launcher", "Launcher", "-Launcher", "_launcher")


def launcher_pair(lid) -> tuple:
    """(launcher_rel, juego_rel) si el .exe de Windows de este juego es un lanzador con su .exe hermano (Silent Hill:
    SilentHillPC_Launcher.exe + SilentHillPC.exe); rutas relativas a windows/. ('', '') si no hay pareja."""
    r = root_of(lid)
    w = (meta(r).get("windows") or {}) if r else {}
    exe = w.get("game_exe") or ""
    if not exe:
        return "", ""
    p = Path(exe)
    for sfx in _LAU_SFX:
        if p.stem.endswith(sfx) and len(p.stem) > len(sfx):
            g = p.with_name(p.stem[:-len(sfx)] + p.suffix)
            if (r / "windows" / g).is_file():
                return exe, str(g)
    return "", ""


def windows_skip_launcher(lid) -> bool:
    r = root_of(lid)
    return bool(r and (meta(r).get("windows") or {}).get("skip_launcher"))


def set_windows_skip_launcher(lid, on: bool) -> bool:
    """Abre el .exe del juego directo, sin su launcher (que en modo juego no se maneja con mando). Reescribe windows/hub-run.sh."""
    r = root_of(lid)
    if r is None:
        raise OSError("no encuentro la carpeta del juego")
    if on and not launcher_pair(lid)[1]:
        raise OSError("este juego no tiene un launcher aparte que saltar")
    m = meta(r)
    w = m.get("windows") or {}
    if on:
        w["skip_launcher"] = True
    else:
        w.pop("skip_launcher", None)
    m["windows"] = w
    _save_meta(r, m)
    rn = w.get("runner") or "proton"
    if rn in ("proton", "wine"):
        set_windows_runner(lid, rn)
    return on


def set_windows_runner(lid, runner: str) -> str:
    """Cambia con qué se abre la versión de Windows (Proton con umu-run, o Wine del sistema) reescribiendo windows/hub-run.sh. No toca el prefijo."""
    if runner not in ("proton", "wine", "own"):
        raise ValueError(runner)
    r = root_of(lid)
    if r is None or not (runner == "own" or (r / "windows" / RUNNER).is_file()):
        raise OSError("no hay versión de Windows instalada")
    m = meta(r)
    w = m.get("windows") or {}
    if runner == "own":
        from . import ownwine
        if not ownwine.supported(r / "windows", w):
            raise OSError("no encuentro el .exe de la versión de Windows para abrirlo con tu Wine")
        prof = "gow" if ownwine.available(r / "windows", w) else "generic"
        w["own"] = ownwine.cfg(dict(w, own=dict(w.get("own") or {}, profile=prof)), prof)
        ownwine.write_script(r / "windows", w)
        w["runner"] = "own"
        m["windows"] = w
        _save_meta(r, m)
        return runner
    exe = w.get("game_exe")
    if not exe:
        raise OSError("no sé cuál es el .exe de esta versión de Windows")
    if w.get("skip_launcher"):
        exe = launcher_pair(lid)[1] or exe
    pp = w.get("proton") or proton_path()
    txt = local_runner_text(exe, "game", pp, runner) if w.get("local") else runner_text(exe, pp, runner)
    f = r / "windows" / RUNNER
    f.write_text(txt, encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    w["runner"] = runner
    m["windows"] = w
    _save_meta(r, m)
    return runner


# ── Linux: release (AppImage / binario) o compilado por Hub ──
def linux_methods(lid) -> dict:
    """{active: release|built, release: bool, built: bool}: qué formas de abrir Linux hay guardadas (no se pisan entre sí)."""
    r = root_of(lid)
    m = meta(r) if r else {}
    cur = m.get("linux") or {}
    return {"active": "built" if cur.get("built") else "release",
            "release": bool(m.get("linux_release") or (cur and not cur.get("built"))),
            "built": bool(m.get("linux_built") or cur.get("built"))}


def set_linux_method(lid, which: str) -> str:
    """Cambia entre abrir la release (AppImage/binario) o el juego compilado por Hub. Cada una conserva lo suyo; el modo contenedor
    del método que se deja vuelve a «sistema» (se elige otra vez en el nuevo)."""
    if which not in ("release", "built"):
        raise ValueError(which)
    st = state(lid)
    root = st["root"]
    if root is None or not st["split"]:
        raise OSError("este juego aún no tiene versiones separadas (linux/ y windows/)")
    cur = linux_methods(lid)["active"]
    if which == cur:
        return which
    if in_container(lid):
        set_in_container(lid, False)
    m = meta(root)
    m["linux_" + cur] = m.get("linux")
    new = m.get("linux_" + which)
    if not new:
        raise OSError("todavía no hay " + ("un juego compilado por Hub" if which == "built" else "una release de Linux"))
    m["linux"] = new
    _save_meta(root, m)
    if m.get("active") == "linux":
        _apply(lid, root, "linux", m)
        _save_meta(root, m)
    return which

# ── instaladores de Windows (v2.94): el proyecto solo publica un «Setup.exe» ──
def setup_root(entry: dict, lid=None) -> Path:
    """Carpeta del juego (la que tiene linux/ y windows/). Su «proton-prefix» es el que usa el instalador y luego JUGAR."""
    return (root_of(lid) if lid else None) or (config.GAMES_DIR / entry.get("folder", entry["id"]))


def setup_target(entry: dict, lid=None) -> Path:
    """Carpeta vacía donde el instalador pone el juego: <juego>/windows/instalado. Va dentro de windows/, que reorganizar la carpeta no mueve."""
    return setup_root(entry, lid) / "windows" / "instalado"


DRIVE_LETTERS = ("g", "h", "i", "j")


def installer_runner_text(setup: Path, proton: str, iso=None) -> str:
    """v2.98: antes del instalador crea el prefijo (si no existe) y una unidad propia (G:, o la siguiente libre) que apunta a <juego>/windows.
    Así el instalador (1) tiene tu ISO a mano en G:\ y (2) mide el espacio libre de TU disco: en Bazzite «Z:» es «/», de solo lectura y casi
    sin espacio, y un instalador que mire la raíz de la unidad cree que no caben los ~15 GB aunque /var/home tenga de sobra."""
    letters = " ".join(DRIVE_LETTERS)
    return ("#!/bin/sh\n"
            "# Recomp Hub: abre el instalador de Windows con Proton (umu-run) en el «C:» del juego.\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            'export WINEPREFIX="${WINEPREFIX:-$HERE/../proton-prefix}"   # el «C:» del juego (hermano de windows/)\n'
            'export GAMEID="${GAMEID:-0}"\n'
            f'export PROTONPATH="${{PROTONPATH:-{proton}}}"\n'
            'mkdir -p "$WINEPREFIX"\n'
            'export PROTON_USE_XALIA=0   # v3.02: Xalia (mando en ventanas de Windows) se caía con el instalador de ReStreet\n'
            + WINE_DISPLAY + WINE_CLEAN +
            'if [ ! -d "$WINEPREFIX/drive_c" ] && [ ! -d "$WINEPREFIX/pfx/drive_c" ]; then\n'
            '  echo "Hub: creando el prefijo de Proton…"; umu-run wineboot -u || true\n'
            'fi\n'
            'for P in "$WINEPREFIX" "$WINEPREFIX/pfx"; do\n'
            '  [ -d "$P/dosdevices" ] || continue\n'
            f'  for L in {letters}; do\n'
            '    D="$P/dosdevices/$L:"\n'
            '    if [ -L "$D" ] && [ "$(readlink "$D")" = "$HERE" ]; then echo "Hub: unidad ${L}: = $HERE"; echo "$L" >"$HERE/.hub-drive"; break; fi\n'
            '    if [ ! -e "$D" ] && [ ! -L "$D" ]; then ln -s "$HERE" "$D" && echo "Hub: unidad ${L}: = $HERE" && echo "$L" >"$HERE/.hub-drive"; break; fi\n'
            '  done\n'
            'done\n'
            + (_iso_links_sh(iso) if iso else '') +
            f'cd -P "$(dirname {_sh(setup)})" || exit 1\n'
            f'exec umu-run {_sh(setup)} "$@"\n')


def _iso_links_sh(iso) -> str:
    """v3.02: enlaza tu ISO en Escritorio y Documentos de TODOS los usuarios del prefijo justo antes del instalador. Proton usa
    «steamuser» (no tu usuario de Linux), y antes el enlace iba solo al primer usuario que existiera."""
    return ('for U in "$WINEPREFIX"/drive_c/users/* "$WINEPREFIX"/pfx/drive_c/users/*; do\n'
            '  [ -d "$U" ] || continue\n'
            '  case "$(basename "$U")" in Public|public|"All Users"|Default) continue;; esac\n'
            '  for S in Desktop Documents; do\n'
            '    mkdir -p "$U/$S" 2>/dev/null\n'
            f'    L="$U/$S/$(basename {_sh(iso)})"\n'
            '    [ -L "$L" ] && rm -f "$L"   # v3.03: el enlace simbólico de Hub se cambia por uno duro (Wine no lo mostraba)\n'
            f'    [ -e "$L" ] || {{ ln {_sh(iso)} "$L" 2>/dev/null || ln -s {_sh(iso)} "$L"; }} && echo "Hub: ISO en $L"\n'
            '  done\n'
            'done\n')


def _sh(p) -> str:
    return "'" + str(p).replace("'", "'\\''") + "'"


def link_iso(win: Path, iso) -> str:
    """Enlace a tu ISO dentro de <juego>/windows (se ve en G:\\ desde el instalador). Nunca pisa un archivo real."""
    if not iso or not Path(iso).exists():
        return ""
    win.mkdir(parents=True, exist_ok=True)
    t = win / Path(iso).name
    link_file(iso, t)
    return str(t)


def installed_exes(entry: dict, lid=None) -> list:
    """.exe que dejó el instalador en <juego>/windows/instalado (sin desinstaladores ni redistribuibles)."""
    d = setup_target(entry, lid)
    if not d.is_dir():
        return []
    bad = re.compile(r"unins|uninstall|vc_?redist|dxsetup|dotnet|directx|crashpad|setup", re.I)
    out = []
    for p in sorted(d.rglob("*.exe")):
        if not bad.search(p.name) and len(p.relative_to(d).parts) <= 4:
            out.append(p)
    return out


def new_exes(entry: dict, lid=None, since: float = 0.0) -> list:
    """v3.01: .exe que pudo dejar un instalador fuera de windows/instalado (su ruta por defecto dentro del «C:» del prefijo:
    Program Files, AppData, C:\\Games…), creados o cambiados desde `since`. Sin los de Windows/Proton ni desinstaladores."""
    root = setup_root(entry, lid)
    bad = re.compile(r"unins|uninstall|vc_?redist|dxsetup|dotnet|directx|crashpad|setup|install|update|crash|helper|ndp\d", re.I)
    skip = {"windows", "programdata", "public"}
    noise = ("windows nt", "internet explorer", "windows media player", "common files", "steam", "windows defender", "windows photo viewer")
    seen, out = set(), []
    for base in [setup_target(entry, lid)] + [root / "proton-prefix" / x / "drive_c" for x in ("", "pfx")]:
        if not base.is_dir():
            continue
        for p in base.rglob("*.exe"):
            try:
                rel = p.relative_to(base).parts
                if rel and rel[0].lower() in skip or any(x.lower() in noise for x in rel):
                    continue
                if bad.search(p.name) or p.stat().st_mtime < since or len(rel) > 8:
                    continue
                r = p.resolve()
            except OSError:
                continue
            if r not in seen:
                seen.add(r)
                out.append(p)
    return sorted(out, key=lambda x: -x.stat().st_mtime)


def found_exes(entry: dict, lid=None) -> list:
    """El juego que dejó un instalador: primero windows/instalado; si no, cualquier .exe de juego dentro del «C:» del prefijo."""
    return installed_exes(entry, lid) or new_exes(entry, lid, 0.0)


def run_installer(entry: dict, setup: Path, lid=None, iso=None) -> dict:
    """Prepara <juego>/windows/hub-installer.sh y lo lanza (Proton, prefijo del juego). Devuelve {script, prefix, target, log}."""
    setup = Path(setup)
    if not setup.is_file():
        raise OSError(f"no encuentro el instalador {setup}")
    root = setup_root(entry, lid)
    target = setup_target(entry, lid)
    target.mkdir(parents=True, exist_ok=True)
    sc = target.parent / "hub-installer.sh"          # dentro de windows/, no en la raíz: así no acaba en linux/ al reorganizar
    iso_r = str(Path(iso).resolve()) if iso and Path(iso).exists() else None
    prot = (windows_proton(lid) if lid else "") or proton_path()      # v3.03: el Proton elegido para el juego, si hay uno
    sc.write_text(installer_runner_text(setup, prot, iso_r), encoding="utf-8")
    sc.chmod(sc.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    log = target.parent / "hub-installer.log"
    isol = link_iso(target.parent, iso)
    from . import proctree
    with open(log, "ab") as lf:
        proc = subprocess.Popen(["sh", str(sc)], cwd=str(root), env=proctree.clean_env(), stdout=lf, stderr=lf, start_new_session=True)
    return {"script": str(sc), "prefix": str(root / "proton-prefix"), "target": str(target), "log": str(log), "iso": isol, "proc": proc}
