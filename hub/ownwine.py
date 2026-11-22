"""v2.40 · «Wine propio»: abrir la versión de Windows con un Wine compilado por ti (ruta + prefijo + DLL de DXVK/VKD3D), sin Proton.
Primer perfil: God of War PSP (gow-psp-recomp). El Wine corre en el sistema (no hace falta distrobox para jugar).
Hub no instala ni actualiza Wine, DXVK ni el toolchain: son tuyos. Solo escribe hub-run.sh, compila el juego (`--build`) y
tras actualizar el proyecto borra lo generado (gen/, mingw_full/, eboot/) para que se recompile."""
import json
import os
import shlex
import shutil
import stat
from pathlib import Path

from . import discid

GENERIC = {"binary": "", "prefix": "", "overrides": "", "debug": "-all"}     # cualquier otro juego: Wine y prefijo los eliges tú
DEFAULT = {
    "binary": "$HOME/wine-11.21/loader/wine",
    "prefix": "$HOME/Games/gow-psp-prefix-staging",
    "overrides": "mscms=n,b;d3d11,dxgi,d3d12,d3d12core=n,b;libvkd3d-1,libvkd3d-shader-1,libvkd3d-utils-1=n,b",
    "debug": "-all",
    "game": "coo",
    "res_scale": 2,
    "fps": 60,
}
GAMES = {"coo": ("UCUS98653", "Chains of Olympus"), "gos": ("UCUS98737", "Ghost of Sparta")}
LAUNCHER = "GoWLauncher.exe"
DATA = "GoW_PSP_data"
CLEAN = ("gen", "mingw_full", "mingw_gos_full", "eboot")        # lo que se regenera al actualizar el proyecto; deps/toolchain/mingw_tools se reutilizan


def expand(s) -> str:
    return os.path.expandvars(os.path.expanduser(str(s)))


def cfg(w: dict, profile: str | None = None) -> dict:
    """Ajustes de «Wine propio» de un juego. profile: «gow» (God of War PSP: launcher + dos juegos directos) o «generic» (un .exe con tu Wine)."""
    own = (w or {}).get("own") or {}
    prof = profile or own.get("profile") or "gow"
    c = dict(DEFAULT if prof == "gow" else GENERIC)
    c.update(own)
    c["profile"] = prof
    if prof == "gow":
        if c.get("game") not in GAMES:
            c["game"] = "coo"
        c["mode"] = own.get("mode") or ("direct" if "game" in own else "launcher")     # lo guardado en v2.40/41 abría el juego directo
    return c


def disc_label(serial: str) -> str:
    g = serial_game(serial)
    return f"{GAMES[g][1]} ({serial})" if g else serial


def generic_exe(win: Path, w: dict) -> Path | None:
    rel = (w or {}).get("game_exe")
    p = Path(win) / rel if rel else None
    return p if p and p.is_file() else None


def base_dir(win: Path, w: dict | None = None) -> Path | None:
    """Carpeta donde está GoWLauncher.exe (windows/ o una subcarpeta)."""
    win = Path(win)
    rel = ((w or {}).get("game_exe") or "")
    if rel and Path(rel).name == LAUNCHER and (win / rel).is_file():
        return (win / rel).parent
    if (win / LAUNCHER).is_file():
        return win
    try:
        for p in win.glob(f"*/{LAUNCHER}"):
            return p.parent
    except OSError:
        pass
    return None


def available(win: Path, w: dict | None = None) -> bool:
    """¿Es God of War PSP (trae GoWLauncher.exe)? Para cualquier otro juego, ver `supported`."""
    return base_dir(win, w) is not None


def supported(win: Path, w: dict | None = None) -> bool:
    return available(win, w) or generic_exe(win, w or {}) is not None


def build_dir(base: Path) -> Path:
    return Path(base) / DATA / "build"


def game_exe(base: Path, game: str) -> Path:
    """El .exe compilado de un juego. v2.68: el launcher puede dejarlo en mingw_full/ o en mingw_<juego>_full/ (Ghost of Sparta): se busca en todas."""
    bd, did = build_dir(base), GAMES[game][0]
    first = bd / "mingw_full" / f"gow_rt_{did}_full.exe"
    if first.is_file():
        return first
    try:
        for p in sorted(bd.glob(f"mingw*/gow_rt_{did}*.exe")):
            if p.is_file():
                return p
    except OSError:
        pass
    return first


def built(base: Path, game: str) -> bool:
    return game_exe(base, game).is_file()


def wine_ok(c: dict) -> bool:
    return os.access(expand(c["binary"]), os.X_OK)


def env_args(c: dict) -> list:
    """Variables para `env` (compilar desde Hub, sin shell)."""
    xa = ""
    try:
        xa = sorted(Path(f"/run/user/{os.getuid()}").glob("xauth_*"))[0].as_posix()
    except (OSError, IndexError):
        pass
    out = ["-u", "LD_PRELOAD", "-u", "SDL_VIDEODRIVER", "-u", "SDL_AUDIODRIVER",      # v2.68: sin el overlay de Steam (ruido «ld.so ... ELFCLASS32») ni las variables de modo juego
           f"WINEPREFIX={expand(c['prefix'])}", f"WINEDLLOVERRIDES={c['overrides']}", f"WINEDEBUG={c['debug']}",
           f"DISPLAY={os.environ.get('DISPLAY') or ':0'}"]
    if xa:
        out.append(f"XAUTHORITY={os.environ.get('XAUTHORITY') or xa}")
    return out


def build_steps(win: Path, w: dict, game: str | None = None) -> list:
    """Pasos para CmdJob: [(descripción, argv)]. Primera vez baja el toolchain (~250 MB) y tarda unos 4 min."""
    c = cfg(w)
    g = game or c["game"]
    b = base_dir(win, w)
    if b is None:
        raise OSError(f"no encuentro {LAUNCHER} en la versión de Windows")
    if not wine_ok(c):
        raise OSError(f"no existe el Wine propio: {expand(c['binary'])}")
    return [(f"Compilando {GAMES[g][1]} (~4 min; la primera vez baja el toolchain)",
             ["env", *env_args(c), expand(c["binary"]), str(b / LAUNCHER), "--build", g])]


def build_progress(win: Path, w: dict | None = None):
    """Avance REAL de la compilación (v2.68): archivos ya hechos en .ninja_log / pasos de build.ninja. None si aún no hay build.ninja."""
    b = base_dir(win, w)
    if b is None:
        return None
    d = build_dir(b) / "mingw_full"
    try:
        mt = (d / "build.ninja").stat().st_mtime
        c = _NINJA_TOT.get(str(d))
        if not c or c[0] != mt:
            n = 0
            with open(d / "build.ninja", "rb") as f:
                for ln in f:
                    if ln.startswith(b"build ") and b": phony" not in ln[:400]:
                        n += 1
            c = _NINJA_TOT[str(d)] = (mt, n)
        done = 0
        with open(d / ".ninja_log", "rb") as f:
            done = max(0, sum(1 for _ in f) - 1)
        return min(1.0, done / c[1]) if c[1] else None
    except OSError:
        return None


_NINJA_TOT: dict = {}


def clean_build(win: Path, w: dict | None = None) -> list:
    """Borra gen/, mingw_full/ y eboot/ (nada más) para forzar la recompilación tras una actualización. Devuelve lo borrado."""
    b = base_dir(win, w)
    gone = []
    if b is None:
        return gone
    bd = build_dir(b).resolve()
    for n in CLEAN:
        for t in (bd / n, (b / DATA / n)):
            try:
                t = t.resolve()
                if t.parent in (bd, (b / DATA).resolve()) and t.is_dir() and not t.is_symlink() and t.name == n:
                    shutil.rmtree(t)
                    gone.append(str(t))
            except OSError:
                continue
    return gone


def note_disc(win: Path, target, extra=()) -> dict:
    """Mira el ISO que Hub dejó enlazado, los de `extra` (uno por juego, elegidos en la ficha) y los .iso de la carpeta, y apunta cuál es
    el de cada juego: own-disc-coo / own-disc-gos. Un ISO PSN (NPUG…) o europeo no cuenta."""
    found = {}
    cands = ([Path(target)] if target else []) + [Path(x) for x in extra if x]
    try:
        cands += sorted(Path(win).glob("*.iso")) + sorted(Path(win).glob("*/*.iso"))
    except OSError:
        pass
    # v2.68: los ISOs que el propio launcher ya tiene apuntados (launcher.json → Z:\ruta) y los «God of War» que hay junto al que enlazaste
    try:
        b = base_dir(win)
        lj = json.loads((build_dir(b) / "launcher.json").read_text(encoding="utf-8")) if b else {}
        for v in (lj.get("disc") or {}).values():
            if isinstance(v, str) and v:
                cands.append(Path(v[2:].replace("\\", "/") if v[:2].upper() == "Z:" else v.replace("\\", "/")))
    except (OSError, ValueError, AttributeError):
        pass
    for c0 in list(cands)[:3]:
        try:
            for q in sorted(c0.resolve().parent.glob("*.iso"))[:200]:
                if "god of war" in q.name.lower() and q not in cands:
                    cands.append(q)
        except OSError:
            continue
    for p in cands:
        try:
            r = discid.read_id(p)
        except OSError:
            r = None
        if not r:
            continue
        for g, (did, _) in GAMES.items():
            if g not in found and discid.norm(r["id"]) == discid.norm(did):
                found[g] = str(p.resolve())
    for g, p in found.items():
        try:
            (Path(win) / f"own-disc-{g}").write_text(p, encoding="utf-8")
        except OSError:
            pass
    return found


def serial_game(serial: str) -> str:
    return next((g for g, (d, _) in GAMES.items() if discid.norm(d) == discid.norm(serial)), "")


def disc_of(win: Path, game: str) -> str:
    try:
        p = (Path(win) / f"own-disc-{game}").read_text(encoding="utf-8").strip()
        return p if p and Path(p).exists() else ""
    except OSError:
        return ""


INPUT_LOG = ('if [ -f "$HERE/../.proton-log" ]; then   # v2.66: registro de mandos y entrada → ../hub-own.log (ficha → AVANZADO → REGISTRO DE PROTON)\n'
             '  export WINEDEBUG="err+all,fixme+all,+winebus,+hid,+hidraw,+dinput,+xinput,+joystick"\n'
             '  { echo "=== $(date) · $0 ==="; echo "DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY SDL_VIDEODRIVER=$SDL_VIDEODRIVER LD_PRELOAD=$LD_PRELOAD"; ls -l /dev/input/js* /dev/hidraw* 2>&1 | head -20; } >>"$HERE/../hub-own.log"\n'
             '  exec >>"$HERE/../hub-own.log" 2>&1\n'
             'fi\n')


def _head(win: Path, c: dict) -> str:
    q = shlex.quote
    pfx = c["prefix"] or "$HERE/../proton-prefix"
    return ("#!/bin/sh\n"
            "# Recomp Hub: versión de Windows con tu Wine propio (sin Proton). Puedes editar este archivo.\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            f'BIN="{c["binary"].replace(str(Path.home()), "$HOME")}"\n'
            f'export WINEPREFIX="{pfx}"\n'
            'mkdir -p "$WINEPREFIX"\n'
            + (f"export WINEDLLOVERRIDES={q(c['overrides'])}\n" if c["overrides"] else "")
            + f"export WINEDEBUG={q(c['debug'])}\n"
            'export DISPLAY="${DISPLAY:-:0}"\n'
            'export XAUTHORITY="${XAUTHORITY:-$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1)}"\n'
            '[ -x "$BIN" ] || { echo "Recomp Hub: no existe el Wine propio «$BIN» (ficha > Windows > ELEGIR WINE)" >&2; exit 127; }\n')


def script_text(win: Path, w: dict) -> str:
    c = cfg(w)
    if c["profile"] == "generic":
        ex = generic_exe(win, w)
        rel = os.path.relpath(ex, win) if ex else (w.get("game_exe") or "")
        return (_head(win, c) + INPUT_LOG + f'cd -P "$(dirname "$HERE/{rel}")" || exit 1\n'
                f'exec "$BIN" "$HERE/{rel}" "$@"\n')
    b = base_dir(win, w)
    rel = os.path.relpath(b, win) if b else "."
    q = shlex.quote
    return ("#!/bin/sh\n"
            "# Recomp Hub: versión de Windows con tu Wine propio (sin Proton). Puedes editar este archivo.\n"
            "# Abre el launcher (HUB_MODE=launcher) o un juego directo (HUB_MODE=direct). Cambiar de juego: HUB_GOW=gos ./hub-run.sh\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            f'BASE="$HERE/{rel}"\n'
            f'BIN="{c["binary"].replace(str(Path.home()), "$HOME")}"\n'
            f'export WINEPREFIX="{c["prefix"]}"\n'
            f"export WINEDLLOVERRIDES={q(c['overrides'])}\n"
            f"export WINEDEBUG={q(c['debug'])}\n"
            'export DISPLAY="${DISPLAY:-:0}"\n'
            'export XAUTHORITY="${XAUTHORITY:-$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1)}"\n'
            + INPUT_LOG +
            f'MODE="${{HUB_MODE:-{c["mode"]}}}"\n'
            '[ -n "$HUB_GOW" ] && MODE=direct\n'
            'if [ "$MODE" = launcher ]; then\n'
            '  [ -x "$BIN" ] || { echo "Recomp Hub: no existe el Wine propio $BIN" >&2; exit 127; }\n'
            '  cd -P "$BASE" || exit 1\n'
            '  exec "$BIN" "$BASE/GoWLauncher.exe" "$@"\n'
            'fi\n'
            f'GAME="${{HUB_GOW:-{c["game"]}}}"\n'
            'case "$GAME" in coo) ID=UCUS98653;; gos) ID=UCUS98737;; *) echo "Recomp Hub: juego desconocido $GAME" >&2; exit 2;; esac\n'
            '[ -x "$BIN" ] || { echo "Recomp Hub: no existe el Wine propio $BIN" >&2; exit 127; }\n'
            'EXE="$BASE/GoW_PSP_data/build/mingw_full/gow_rt_${ID}_full.exe"\n'
            '[ -f "$EXE" ] || for f in "$BASE"/GoW_PSP_data/build/mingw*/gow_rt_${ID}*.exe; do [ -f "$f" ] && EXE="$f" && break; done\n'
            '[ -f "$EXE" ] || { echo "Recomp Hub: $GAME aún no está compilado (Hub: ficha > Windows > COMPILAR)" >&2; exit 3; }\n'
            'DISC="${HUB_DISC:-$(cat "$HERE/own-disc-$GAME" 2>/dev/null)}"\n'
            '[ -n "$DISC" ] && [ -f "$DISC" ] || { echo "Recomp Hub: no tengo tu ISO USA ($ID) de $GAME; enlázala desde Hub" >&2; exit 4; }\n'
            'WDISC="Z:$(printf %s "$DISC" | tr / \'\\\\\')"\n'
            'cd -P "$BASE" || exit 1\n'
            f'exec "$BIN" "$EXE" --boot --disc "$WDISC" --fullscreen --fps {int(c["fps"])} --renderer gpu --res-scale {int(c["res_scale"])} "$@"\n')


def is_custom(win: Path) -> bool:
    """¿El hub-run.sh lo escribió una persona (no lleva la cabecera «# Recomp Hub:» en sus primeras líneas)?"""
    try:
        head = (Path(win) / "hub-run.sh").read_text(encoding="utf-8", errors="replace").splitlines()[:4]
    except OSError:
        return False
    return not any("Recomp Hub:" in ln for ln in head)


def write_script(win: Path, w: dict, force: bool = False) -> str:
    """Escribe hub-run.sh. v2.76: si el que hay lo editaste tú a mano (Pokémon: arranca un servidor Python y luego Wine) NO se pisa: lo que Hub habría
    escrito queda en hub-run.sh.hub y devuelve «custom». force=True (botón «USAR EL SCRIPT DEL HUB»): tu script se guarda antes como hub-run.sh.mio."""
    f = Path(win) / "hub-run.sh"
    txt = script_text(win, w)
    if f.exists() and is_custom(win):
        if not force:
            (Path(win) / "hub-run.sh.hub").write_text(txt, encoding="utf-8")
            return "custom"
        shutil.copy2(f, Path(win) / "hub-run.sh.mio")
    f.write_text(txt, encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return "ok"


# ── carpeta de Wine propios (v2.81) ──
WINES_HOME = Path.home() / "wines"          # una subcarpeta por versión: ~/wines/wine-11.21/bin/wine


def _wine_in(d: Path) -> str:
    for rel in ("bin/wine", "loader/wine", "files/bin/wine", "wine"):
        p = d / rel
        try:
            if p.is_file() and os.access(p, os.X_OK):
                return str(p)
        except OSError:
            continue
    return ""


def list_wines() -> list:
    """[(nombre, ruta al ejecutable «wine»)] de los Wine propios que hay en ~/wines, ~/Games/wines y las carpetas ~/wine-* (una por versión)."""
    out, seen = [], set()
    bases = [WINES_HOME, Path.home() / "Games" / "wines"]
    cands = []
    for b in bases:
        try:
            cands += [d for d in sorted(b.iterdir()) if d.is_dir()]
        except OSError:
            continue
    try:
        cands += [d for d in sorted(Path.home().glob("wine-*")) if d.is_dir()]
    except OSError:
        pass
    for d in cands:
        w = _wine_in(d)
        if w and w not in seen:
            seen.add(w)
            out.append((d.name, w))
    return out
