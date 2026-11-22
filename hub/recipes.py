"""Recetas «compilar en contenedor»: proyectos que hay que compilar (y a veces instalar paquetes) y que en Bazzite no queremos instalar en el sistema.

Una receta (hub/recipes/*.toml) dice: qué imagen de distrobox, cómo comprobar dependencias, qué preparar, cómo compilar y dónde queda el ejecutable.
Hub la ejecuta en dos fases, para que veas qué se va a instalar antes de instalarlo:
  1) crear el contenedor, dejar el código en <juego>/linux, enlazar tu ISO y ejecutar la comprobación de dependencias del proyecto;
  2) (tras aceptar) instalar esos paquetes DENTRO del contenedor, preparar, compilar, traer las bibliotecas que el sistema no tenga y escribir hub-run.sh.
El juego se ejecuta en el sistema (por defecto) o dentro del contenedor (ficha → «Ejecutar en»)."""
import os
import re
import shlex
import shutil
import subprocess
import tomllib
from pathlib import Path

DIR = Path(__file__).with_name("recipes")


def load_all() -> list:
    out = []
    try:
        for p in sorted(DIR.glob("*.toml")):
            try:
                r = tomllib.loads(p.read_text(encoding="utf-8"))
                r["_file"] = p.name
                out.append(r)
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return out


def for_entry(entry: dict) -> dict | None:
    repo = str(entry.get("repo", "")).lower()
    for r in load_all():
        if "build" not in r:               # receta solo de «contenedor para ejecutar» (runtime_for)
            continue
        m = r.get("match") or {}
        if repo and repo in [x.lower() for x in m.get("repos", [])]:
            return r
        if entry.get("id") in m.get("ids", []):
            return r
    return None


def runtime_for(entry: dict) -> dict | None:
    """Receta [runtime] del juego: un distrobox donde EJECUTAR una release ya compilada para otra distribución (p. ej. Ubuntu 26.04)."""
    repo = str(entry.get("repo", "")).lower()
    for r in load_all():
        if "runtime" not in r:
            continue
        m = r.get("match") or {}
        if (repo and repo in [x.lower() for x in m.get("repos", [])]) or entry.get("id") in m.get("ids", []):
            return r
    return None


def pm_of(image: str, pm: str = "") -> str:
    """Gestor de paquetes del contenedor: el que diga la receta o, si no, por la imagen (ubuntu/debian → apt; lo demás → dnf)."""
    if pm:
        return pm
    return "apt" if re.search(r"ubuntu|debian|mint|kali", str(image), re.I) else "dnf"


def install_cmd(pm: str, pkgs) -> str:
    """Orden de shell (dentro del contenedor) que instala pkgs sin preguntar."""
    ps = " ".join(_sq(p) for p in pkgs)
    if pm == "apt":
        # un nombre que no exista en esa versión de la distribución haría fallar TODA la instalación: se avisa y se instala el resto
        return (f"sudo apt-get update -q; ok=; for p in {ps}; do if apt-cache show \"$p\" >/dev/null 2>&1; then ok=\"$ok $p\"; "
                f"else echo \"(no existe en esta distribución: $p)\"; fi; done; "
                f"sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $ok")
    return f"sudo dnf install -y {ps}"


def create_cmd(name: str, image: str) -> str:
    return (f"distrobox list --no-color | awk -F'|' 'NR>1{{gsub(/ /,\"\",$2);print $2}}' | grep -qx {_sq(name)} || "
            f"distrobox create --name {_sq(name)} --image {_sq(image)} --yes")


def runtime_steps(recipe: dict, entry: dict, cwd=None, exe=None) -> list:
    """[(descripción, argv)]: crear el contenedor de ejecución (si falta) e instalar lo que pide la release. Repetirlo no rompe nada."""
    rt = recipe.get("runtime") or {}
    name = str(rt.get("name", "hub-{id}")).format(id=entry.get("id", "juego"), repo=entry.get("repo", ""))
    image = rt.get("image", "ubuntu:24.04")
    pkgs = list(rt.get("packages") or [])
    steps = [(f"Crear el contenedor «{name}» ({image})", ["bash", "-c", create_cmd(name, image)])]
    if pkgs:
        steps.append((f"Instalar {len(pkgs)} paquetes dentro del contenedor (la primera vez tarda)", enter(name, install_cmd(pm_of(image, rt.get("pm", "")), pkgs))))
    if rt.get("auto_libs") and exe:
        steps.append(("Buscar e instalar las bibliotecas que le faltan al juego", enter(name, auto_libs_cmd(pm_of(image, rt.get("pm", "")), exe), cwd)))
    for cmd in rt.get("check", []):
        steps.append(("Comprobar: " + cmd[:50], enter(name, cmd, cwd)))
    return steps


_DISTRO = re.compile(r"(ubuntu|debian|fedora)[-_ ]?(\d{1,2}(?:\.\d{2})?)", re.I)


def runtime_guess(entry: dict, install_dir, asset: str = "", missing=()) -> dict | None:
    """Receta de ejecución DEDUCIDA para cualquier juego (v2.31): la distribución sale de `linux-package.json` (build_os), del nombre del
    paquete («…ubuntu26.04…») o, si al sistema le faltan bibliotecas y nada dice la distribución, se propone Fedora (la base de Bazzite).
    Los paquetes no se conocen: runtime_steps los busca dentro del contenedor a partir de lo que `ldd` echa en falta."""
    image, why = "", ""
    try:
        import json
        for f in [Path(install_dir) / "linux-package.json", *Path(install_dir).glob("*/linux-package.json")][:4]:
            if f.is_file():
                bo = (json.loads(f.read_text(encoding="utf-8")).get("build_os") or {})
                if bo.get("ID") and bo.get("VERSION_ID"):
                    image, why = f"{str(bo['ID']).lower()}:{bo['VERSION_ID']}", "lo dice linux-package.json"
                    break
    except (OSError, ValueError):
        pass
    if not image:
        m = _DISTRO.search(str(asset))
        if m:
            image, why = f"{m.group(1).lower()}:{m.group(2)}", "lo dice el nombre del paquete"
    if not image and missing:
        image, why = "fedora:latest", "al sistema le faltan bibliotecas"
    if not image:
        return None
    return {"runtime": {"image": image, "name": "hub-{id}", "packages": [], "auto_libs": True, "why": why}, "_guess": True}


def auto_libs_cmd(pm: str, exe) -> str:
    """Dentro del contenedor: instala los paquetes que traen las bibliotecas que `ldd` no encuentra para exe (hasta 3 rondas)."""
    e = _sq(exe)
    if pm == "apt":
        find = ("command -v apt-file >/dev/null || sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y apt-file >/dev/null; sudo apt-file update >/dev/null 2>&1; "
                "pk=; for l in $miss; do p=$(apt-file search -l \"/$l\" 2>/dev/null | grep -v -e '-dev$' -e 'dbg' | head -1); "
                "if [ -n \"$p\" ]; then pk=\"$pk $p\"; else echo \"(ningún paquete trae $l)\"; fi; done; "
                "[ -z \"$pk\" ] && break; sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $pk")
        pre = "sudo apt-get update -q; "
    else:
        find = "pk=; for l in $miss; do pk=\"$pk */$l\"; done; sudo dnf install -y --skip-unavailable $pk || break"
        pre = ""
    return (f"{pre}for i in 1 2 3; do miss=$(ldd {e} 2>/dev/null | awk '/not found/{{print $1}}' | sort -u); [ -z \"$miss\" ] && break; "
            f"echo \"Faltan: $miss\"; {find}; done; "
            f"if ldd {e} 2>/dev/null | grep -q 'not found'; then echo 'AÚN FALTAN:'; ldd {e} | grep 'not found'; exit 3; else echo 'bibliotecas completas'; fi")


def runtime_name(recipe: dict, entry: dict) -> str:
    return str((recipe.get("runtime") or {}).get("name", "hub-{id}")).format(id=entry.get("id", "juego"), repo=entry.get("repo", ""))


def container_name(recipe: dict, entry: dict) -> str:
    return str((recipe.get("container") or {}).get("name", "hub-{id}")).format(id=entry.get("id", "juego"), repo=entry.get("repo", ""))


def parse_deps(text: str, ignore_marker: str = "(launcher)") -> list:
    """Paquetes de los bloques «install them with: sudo dnf install …» de la comprobación del proyecto.
    Un bloque cuyas carencias están TODAS marcadas con ignore_marker (p. ej. «(launcher)») se descarta."""
    pkgs, miss = [], []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if "missing:" in ln:
            miss.append(ln)
        elif "install them with" in ln:
            cmd = ""
            j = i + 1
            while j < len(lines) and lines[j].strip():
                part = lines[j].strip()
                if part.startswith("[deps]"):
                    break
                cmd += " " + part.rstrip("\\")
                j += 1
            i = j - 1
            skip = bool(miss) and bool(ignore_marker) and all(ignore_marker in m for m in miss)
            m = re.search(r"(?:dnf|apt-get|apt)\s+install\s+(?:-y\s+)?(.*)", cmd)
            if m and not skip:
                for p in shlex.split(m.group(1)):
                    if not p.startswith("-") and p not in pkgs:
                        pkgs.append(p)
            miss = []
        i += 1
    return pkgs


def _sq(s) -> str:
    return shlex.quote(str(s))


def _cenv():
    from . import proctree
    return proctree.clean_env()


def fix_command(t: str) -> str:
    """Errata típica al teclear con el teclado en pantalla: «sudo install -y x» / «install -y x» / «dnf» sin install → se completa con dnf (si no, `install` de coreutils da «invalid option -- y»)."""
    t = (t or "").strip()
    import re
    m = re.match(r"^(sudo\s+)?install\s+(-y\b.*)$", t)
    if m:
        return f"{m.group(1) or 'sudo '}dnf install {m.group(2)}"
    return t


def enter(container: str, shell_cmd: str, cwd: Path | None = None) -> list:
    """argv que ejecuta `shell_cmd` dentro del contenedor (opcionalmente en cwd, que está en $HOME y por tanto compartido)."""
    pre = f"cd {_sq(cwd)} && " if cwd else ""
    return ["distrobox", "enter", container, "--", "bash", "-c", pre + shell_cmd]


def ensure_source(recipe: dict, entry: dict, src: Path, say=print):
    """Si <juego>/linux no trae el código del proyecto, lo clona (git del sistema; no usa el zip de Windows). Nunca pisa nada."""
    mk = (recipe.get("source") or {}).get("marker", "")
    if mk and (src / mk).exists():
        say(f"El código ya está en {src}")
        return
    if src.exists() and any(src.iterdir()):
        raise OSError(f"{src} no está vacía ni trae {mk}: no clono encima")
    url = str((recipe.get("source") or {}).get("git", "")).format(repo=entry.get("repo", ""))
    if not url:
        raise OSError("la receta no dice de dónde sacar el código")
    src.parent.mkdir(parents=True, exist_ok=True)
    say(f"Clonando {url}")
    r = subprocess.run(["git", "clone", "--depth", "1", url, str(src)], capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise OSError("git clone falló: " + (r.stderr or r.stdout)[-300:])


def link_disc(recipe: dict, src: Path, iso) -> Path:
    """Enlace con el nombre que exige el proyecto hacia TU archivo (nunca copia ni pisa un archivo real)."""
    nm = (recipe.get("disc") or {}).get("name")
    if not nm:
        return Path(iso)
    iso = Path(iso).expanduser()
    if not iso.exists():
        raise OSError(f"no encuentro tu archivo: {iso}")
    t = src / nm
    if t.is_symlink():
        if t.resolve() == iso.resolve():
            return t
        t.unlink()                     # solo enlaces: uno roto o apuntando a otro sitio se rehace
    elif t.exists():
        return t
    t.symlink_to(iso.resolve())
    return t


def phase1(recipe: dict, entry: dict, src: Path):
    """[(descripción, argv)] de la fase 1: contenedor + comprobación de dependencias (sin instalar nada del proyecto)."""
    c = recipe.get("container") or {}
    name = container_name(recipe, entry)
    image = c.get("image", "fedora:43")
    create = create_cmd(name, image)
    prep = install_cmd(pm_of(image, c.get("pm", "")), c.get("base_packages", ["git", "python3"]))
    chk = (recipe.get("deps") or {}).get("check", "")
    return [("Crear el contenedor «%s»" % name, ["bash", "-c", create]),
            ("Preparar el contenedor", enter(name, prep)),
            ("Comprobar dependencias del proyecto", enter(name, (chk + "; true") if chk else "true", src))]


def phase2(recipe: dict, entry: dict, src: Path, pkgs: list, iso: Path | None, finish):
    """[(descripción, argv|callable)] de la fase 2. `finish(say)` registra la versión de Linux en Hub al terminar."""
    name = container_name(recipe, entry)
    steps = []
    if pkgs:
        c = recipe.get("container") or {}
        pm = pm_of(c.get("image", "fedora:43"), c.get("pm", ""))
        steps.append((f"Instalar {len(pkgs)} paquetes dentro del contenedor",
                      ["distrobox", "enter", name, "--", "sudo", "dnf", "install", "-y", *pkgs] if pm == "dnf" else enter(name, install_cmd(pm, pkgs))))
    for cmd in (recipe.get("prepare") or {}).get("run", []):
        steps.append(("Preparar: " + cmd[:50], enter(name, cmd, src)))
    chk = (recipe.get("disc") or {}).get("check")
    if chk and iso:
        steps.append(("Comprobar que es la edición correcta", enter(name, chk.format(iso=_sq(iso)), src)))
    for cmd in (recipe.get("build") or {}).get("run", []):
        steps.append(("Compilar (puede tardar): " + cmd[:40], enter(name, cmd, src)))
    out = recipe.get("output") or {}
    exe = src / out.get("exe", "")
    libs = src / out["libs"] if out.get("libs") else None
    if libs:
        steps.append(("Traer del contenedor las bibliotecas que falten al sistema", lambda say: resolve_libs(exe, libs, name, say)))
    if libs and out.get("rpath", True):
        steps.append(("Fijar la ruta de bibliotecas dentro del binario (RPATH)", lambda say: patch_rpath(exe, libs, name, say)))
    steps.append(("Registrar la versión de Linux en Hub", finish))
    return steps


def missing_libs(exe: Path, libs: Path | None) -> list:
    """Bibliotecas que el SISTEMA no encuentra para exe (y para las .so ya traídas), mirando con ldd y LD_LIBRARY_PATH=libs."""
    env = dict(os.environ)
    if libs:
        env["LD_LIBRARY_PATH"] = str(libs) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    targets = [exe] + (sorted(p for p in libs.glob("*.so*") if p.is_file()) if libs and libs.is_dir() else [])
    out = set()
    for t in targets:
        try:
            r = subprocess.run(["ldd", str(t)], capture_output=True, text=True, env=env, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        for ln in r.stdout.splitlines():
            if "not found" in ln:
                out.add(ln.split()[0])
    return sorted(out)


def resolve_libs(exe: Path, libs: Path, container: str, say=print, rounds: int = 8):
    """Copia al juego, desde el contenedor, las .so que el sistema no tiene; repite porque cada una puede arrastrar otras."""
    libs.mkdir(parents=True, exist_ok=True)
    miss = missing_libs(exe, libs)
    for _ in range(rounds):
        if not miss:
            break
        say("Faltan en el sistema: " + ", ".join(miss))
        for l in miss:
            sh = f'p=$(ldconfig -p | awk -v l={_sq(l)} \'$1==l{{print $NF; exit}}\'); [ -n "$p" ] && cp -L "$p" {_sq(libs)}/'
            subprocess.run(["distrobox", "enter", container, "--", "bash", "-c", sh], stdin=subprocess.DEVNULL, capture_output=True, timeout=300, env=_cenv())
        new = missing_libs(exe, libs)
        if new == miss:
            break
        miss = new
    if miss:
        raise OSError("al sistema aún le faltan: " + ", ".join(miss) + " (activa «Ejecutar en el contenedor»)")
    say(f"El sistema ya encuentra todo ({len(list(libs.glob('*.so*')))} bibliotecas traídas)")


def patch_rpath(exe: Path, libs: Path, container: str, say=print):
    """Graba en el binario (y en las .so traídas) dónde buscar sus bibliotecas, para que arranque SIN LD_LIBRARY_PATH
    (p. ej. cuando lo abre directamente un AppImage). Usa patchelf del contenedor: el sistema (Bazzite) no se toca."""
    if not exe.is_file():
        raise OSError(f"no existe {exe}")
    rel = os.path.relpath(libs, exe.parent)
    sh = (f'command -v patchelf >/dev/null || sudo dnf install -y patchelf >/dev/null 2>&1 || sudo apt-get install -y patchelf >/dev/null 2>&1; '
          f'patchelf --force-rpath --set-rpath {_sq("$ORIGIN/" + rel)} {_sq(exe)} && '
          f'for f in {_sq(libs)}/*.so*; do [ -f "$f" ] && patchelf --force-rpath --set-rpath \'$ORIGIN\' "$f"; done; true')
    r = subprocess.run(["distrobox", "enter", container, "--", "bash", "-c", sh], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600, env=_cenv())
    if r.returncode:
        raise OSError("patchelf falló: " + (r.stderr or r.stdout)[-200:])
    say(f"RPATH fijado: $ORIGIN/{rel}")


def runner_text(exe_rel: str, cwd_rel: str, libs_rel: str, container: str) -> str:
    """hub-run.sh de un build nativo compilado en contenedor. Modo: sistema (por defecto) o contenedor (archivo .run-in-container junto a él)."""
    return ("#!/bin/sh\n"
            f"# Recomp Hub: build nativo compilado en el contenedor «{container}». Puedes editar este archivo.\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            f'cd -P "$HERE/{cwd_rel}" || exit 1\n'
            'if [ -f "$HERE/.run-in-container" ] || [ "$HUB_RUN_MODE" = container ]; then   # ficha → «Ejecutar en: contenedor»\n'
            f'  unset LD_PRELOAD LD_LIBRARY_PATH   # los de Steam (overlay de 32 bits, runtime) rompen clang/lld y el propio distrobox\n'
            f'  exec distrobox enter {shlex.quote(container)} -- "./{Path(exe_rel).name}" "$@"\n'
            "fi\n"
            + (f'export LD_LIBRARY_PATH="$HERE/{libs_rel}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"   # bibliotecas traídas del contenedor\n' if libs_rel else "")
            + f'exec "./{Path(exe_rel).name}" "$@"\n')


def container_wrapper_text(exe_abs: str, container: str, cwd_abs: str, appimage: bool = False) -> str:
    """Envoltorio para ejecutar cualquier ejecutable de Linux del juego (p. ej. un AppImage) dentro de su distrobox."""
    env = "env APPIMAGE_EXTRACT_AND_RUN=1 " if appimage else ""      # FUSE casi nunca está dentro del contenedor
    return ("#!/bin/sh\n"
            f"# Recomp Hub: abre el juego dentro del distrobox «{container}». Se quita desde la ficha («Ejecutar en: sistema»).\n"
            "unset LD_PRELOAD LD_LIBRARY_PATH   # los de Steam (overlay de 32 bits, runtime) se heredaban al contenedor y rompían clang/lld al compilar\n"
            f"cd -P {_sq(cwd_abs)} || exit 1\n"
            f"exec distrobox enter {_sq(container)} -- {env}{_sq(exe_abs)} \"$@\"\n")


_HAVE = {}


def have_distrobox() -> bool:
    """Cacheado 30 s: la ficha lo pregunta en cada fotograma y shutil.which recorre el PATH."""
    import time
    t, v = _HAVE.get("x", (0, False))
    if time.time() - t > 30:
        v = shutil.which("distrobox") is not None
        _HAVE["x"] = (time.time(), v)
    return v
