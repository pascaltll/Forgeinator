"""Compilar un port desde el código: clonar el repo (git) y compilar, normalmente dentro de un distrobox (p. ej. fedora).
Registra el resultado en el launcher como 'git-build' para que él lo siga actualizando. Nunca borra ni pisa carpetas existentes."""
import collections
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from . import buildlog, config, install, proctree

_N = 0


def distrobox_ok() -> bool:
    try:
        return subprocess.run(["distrobox", "--version"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def containers() -> list:
    """Nombres de los distrobox existentes (solo lectura)."""
    try:
        r = subprocess.run(["distrobox", "list", "--no-color"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for ln in r.stdout.splitlines()[1:]:
        cols = [c.strip() for c in ln.split("|")]
        if len(cols) >= 2 and cols[1]:
            out.append(cols[1])
    return out


_CC = {}


def containers_cached(max_age: float = 60.0) -> list:
    """Como containers() pero con caché: `distrobox list` tarda ~1 s y NO debe ejecutarse en el hilo de la interfaz (usa containers() en un hilo y esto para leer)."""
    import time
    t, v = _CC.get("x", (0, []))
    return v if time.time() - t <= max_age else []


def refresh_containers() -> list:
    import time
    v = containers()
    _CC["x"] = (time.time(), v)
    return v


def default_cmd(d: Path) -> str:
    """Comando de compilación sugerido según los archivos del repo ($REPO y $JOBS los rellena Hub/launcher)."""
    d = Path(d)
    if (d / "CMakeLists.txt").exists():
        return "cd '$REPO' && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j$JOBS"
    if (d / "meson.build").exists():
        return "cd '$REPO' && meson setup build --buildtype=release && ninja -C build -j$JOBS"
    if (d / "Cargo.toml").exists():
        return "cd '$REPO' && cargo build --release -j$JOBS"
    if (d / "Makefile").exists() or (d / "makefile").exists():
        return "cd '$REPO' && make -j$JOBS"
    return ""


def find_artifact(d: Path, since: float, hint: str = "") -> str:
    """Ejecutable ELF recién generado dentro de d (relativo). Gana el que coincide con el nombre del juego, luego el más grande."""
    d, cands = Path(d), []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in (".git", "CMakeFiles", "node_modules", "_deps", "deps")]
        if len(Path(root).relative_to(d).parts) > 6:
            dirs[:] = []
            continue
        for f in files:
            p = Path(root) / f
            try:
                st = p.stat()
                if st.st_mtime < since - 5 or not st.st_mode & 0o111 or ".so" in f or f.endswith((".a", ".o", ".sh", ".py")):
                    continue
                with open(p, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            h = 1 if hint and hint.lower().replace(" ", "") in f.lower() else 0
            cands.append((h, st.st_size, p))
    if not cands:
        return ""
    cands.sort(key=lambda x: (-x[0], -x[1]))
    return str(cands[0][2].relative_to(d))


class BuildJob:
    def __init__(self, entry, container, cmd="", jobs=4):
        global _N
        _N += 1
        self.id, self.entry, self.container, self.cmd, self.jobs = f"b{_N}", entry, container, cmd, jobs
        self.state, self.stage, self.error, self.result = "queued", "En cola", "", None
        self.log = collections.deque(maxlen=400)
        self.proc, self._stop = None, False
        self.started = time.time()
        self.logfile = config.DATA / "builds" / f"{entry['id']}-{int(self.started)}.log"

    @property
    def title(self):
        return self.entry["name"]

    def line(self, t):
        self.log.append(t)
        try:
            self.logfile.parent.mkdir(parents=True, exist_ok=True)
            with open(self.logfile, "a", encoding="utf-8") as f:
                f.write(t + "\n")
        except OSError:
            pass

    def sh(self, argv):
        self.line("$ " + " ".join(str(a) for a in argv))
        self.proc = subprocess.Popen([str(a) for a in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                     env=proctree.clean_env({"GIT_TERMINAL_PROMPT": "0"}), start_new_session=True)
        for ln in self.proc.stdout:
            self.line(ln.rstrip())
            if self._stop:
                break
        return self.proc.wait() if not self._stop else 1

    def cancel(self):
        """v2.81: detiene el proceso y todo lo que lanzó (grupo de procesos). Dentro de un distrobox el contenedor puede seguir ocupado: ficha → REINICIAR CONTENEDOR."""
        self._stop = True
        if self.state in ("queued", "running"):
            self.state, self.stage = "cancelled", "Cancelado"
        proctree.kill_tree(self.proc)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        e = self.entry
        self.state = "running"
        try:
            repo = e["repo"]
            if not repo:
                raise RuntimeError("esta entrada no tiene repositorio")
            dest = config.GAMES_DIR / e.get("folder", e["id"])
            self.stage = "Descargando código"
            if (dest / ".git").is_dir():
                if self.sh(["git", "-C", dest, "fetch", "--quiet", "origin"]) or self.sh(["git", "-C", dest, "merge", "--ff-only", "@{u}"]):
                    self.line("(aviso: no pude avanzar el repo; se compila lo que hay)")
            elif dest.exists() and any(dest.iterdir()):
                raise RuntimeError(f"{dest} ya existe y no es un repositorio git: no la toco")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                url = repo if os.path.exists(repo) else f"https://github.com/{repo}.git"
                if self.sh(["git", "clone", "--progress", url, dest]):
                    raise RuntimeError("falló git clone")
            if self._stop:
                raise RuntimeError("cancelado")
            cmd = self.cmd or default_cmd(dest)
            if not cmd:
                raise RuntimeError("no sé cómo compilar este proyecto: pulsa PLAN DE COMPILACIÓN (lee el README) o EDITAR COMANDO")
            self.cmd = cmd
            expanded = cmd.replace("$REPO", str(dest)).replace("$JOBS", str(self.jobs))
            wrapper = ["distrobox", "enter", self.container, "--", "bash", "-c"] if self.container else ["bash", "-c"]
            self.stage = "Compilando" + (f" en {self.container}" if self.container else "")
            t0 = time.time()
            if self.sh(wrapper + [expanded]):
                raise RuntimeError("falló la compilación (mira el registro)")
            if self._stop:
                raise RuntimeError("cancelado")
            art = (e.get("build") or {}).get("artifact") or find_artifact(dest, t0, e["name"].split(":")[0].split()[0])
            self.stage = "Registrando en el launcher"
            ref = "origin/main"
            r = subprocess.run(["git", "-C", str(dest), "rev-parse", "--abbrev-ref", "origin/HEAD"], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip().startswith("origin/"):
                ref = r.stdout.strip()
            toml = install.register_build(e, dest, art, self.container, cmd, ref, self.jobs)
            self.result = {"dir": str(dest), "exe": art, "toml": str(toml)}
            self.line(f"Listo. Ejecutable: {art or '(no detectado: ponlo en el .toml)'}  ·  {toml}")
            self.state, self.stage = "done", "Compilado" + ("" if art else " (sin ejecutable detectado)")
            buildlog.record(e, self.container, self.cmd, self.jobs, True, time.time() - self.started)
        except Exception as ex:  # noqa: BLE001
            self.state = "cancelled" if self._stop else "error"
            self.error = str(ex)
            self.stage = "Cancelado" if self._stop else "Error"
            self.line("ERROR: " + str(ex))
            if not self._stop:
                buildlog.record(e, self.container, self.cmd, self.jobs, False, time.time() - self.started, str(ex))
