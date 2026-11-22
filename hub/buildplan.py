"""Plan de compilación a partir de lo que el propio repo explica (README, BUILDING.md…), sin IA.

Lee los bloques de código de las secciones de Linux/compilar, descarta lo que es de otro sistema (Windows, macOS, Android…),
traduce apt→dnf (el distrobox es Fedora), ordena los pasos y devuelve un plan EDITABLE. Hub nunca lo ejecuta sin que lo veas.

Futuro asistente: `PROVIDERS` es una lista de funciones `(docs, ctx) -> plan|None`. Hoy solo está la heurística; un proveedor nuevo
(p. ej. Claude Code local con `claude -p`) se añade con `register(fn)` y se usa cuando la heurística no encuentra nada o la compilación falla.
`docs` = [(nombre, texto)]; `ctx` = {"entry", "dest", "container", "error_log"}.
"""
import base64
import re
from pathlib import Path

NEG = re.compile(r"\b(windows|win32|win64|msvc|visual studio|vs ?20\d\d|macos|mac os|osx|apple|xcode|android|ios|switch|wii|ps[2345]|xbox|powershell|cmd|wsl|mingw|msys2?)\b", re.I)
LIN = re.compile(r"\b(linux|ubuntu|debian|fedora|arch|unix|gnu|steam ?deck|bazzite)\b", re.I)
POS = re.compile(r"(build|compil|install|setup|set up|getting started|prerequisit|depend|requirement|quick ?start|usage|instructions)", re.I)
LANG_OK = {"", "sh", "bash", "shell", "console", "zsh", "terminal", "text", "txt", "shell-session", "sh-session"}
CMDS = {"git", "cmake", "make", "gmake", "ninja", "meson", "cargo", "sudo", "apt", "apt-get", "dnf", "yum", "pacman", "zypper", "pip", "pip3", "python", "python3",
        "cd", "mkdir", "export", "npm", "yarn", "pnpm", "tar", "cp", "ln", "chmod", "rustup", "source", "bash", "sh", "premake5", "xmake", "bazel", "go", "dotnet",
        "configure", "autoreconf", "./configure", "scons", "just", "nix", "nix-shell", "ccmake", "mv", "unzip", "7z"}
WIN_BAD = re.compile(r"(\.exe\b|\.bat\b|\.ps1\b|msbuild|vcpkg|choco\b|winget|scoop\b|powershell|\bbrew\b|xcodebuild|open -a|%\w+%|\\\w)", re.I)
SCRIPT_OK = re.compile(r"(build|setup|configure|install|prepare|bootstrap|gen|init|submodule)", re.I)

APT_DNF = {
    "build-essential": "@development-tools", "pkg-config": "pkgconf-pkg-config", "libsdl2-dev": "SDL2-devel", "libsdl2-image-dev": "SDL2_image-devel",
    "libsdl2-ttf-dev": "SDL2_ttf-devel", "libsdl2-mixer-dev": "SDL2_mixer-devel", "libsdl3-dev": "SDL3-devel", "libasound2-dev": "alsa-lib-devel",
    "libpulse-dev": "pulseaudio-libs-devel", "libx11-dev": "libX11-devel", "libgl1-mesa-dev": "mesa-libGL-devel", "libgl-dev": "mesa-libGL-devel",
    "libglu1-mesa-dev": "mesa-libGLU-devel", "libdrm-dev": "libdrm-devel", "libgtk-3-dev": "gtk3-devel", "zlib1g-dev": "zlib-devel",
    "libcurl4-openssl-dev": "libcurl-devel", "libssl-dev": "openssl-devel", "python3-dev": "python3-devel", "libudev-dev": "systemd-devel",
    "libusb-1.0-0-dev": "libusb1-devel", "libglew-dev": "glew-devel", "libglfw3-dev": "glfw-devel", "nlohmann-json3-dev": "json-devel",
    "libboost-all-dev": "boost-devel", "libtinyxml2-dev": "tinyxml2-devel", "libvulkan-dev": "vulkan-loader-devel", "libwayland-dev": "wayland-devel",
    "libxext-dev": "libXext-devel", "libxrandr-dev": "libXrandr-devel", "libxi-dev": "libXi-devel", "libxcursor-dev": "libXcursor-devel",
    "libxinerama-dev": "libXinerama-devel", "libxss-dev": "libXScrnSaver-devel", "libogg-dev": "libogg-devel", "libvorbis-dev": "libvorbis-devel",
    "libfreetype6-dev": "freetype-devel", "libpng-dev": "libpng-devel", "libjpeg-dev": "libjpeg-turbo-devel", "libzstd-dev": "libzstd-devel",
    "libfmt-dev": "fmt-devel", "libspdlog-dev": "spdlog-devel", "libopenal-dev": "openal-soft-devel", "libsdl2-net-dev": "SDL2_net-devel",
    "pkgconf": "pkgconf-pkg-config", "libxxhash-dev": "xxhash-devel", "libbz2-dev": "bzip2-devel", "liblzma-dev": "xz-devel", "libncurses-dev": "ncurses-devel", "libncurses5-dev": "ncurses-devel",
    "g++": "gcc-c++", "gcc": "gcc", "clang": "clang", "lld": "lld", "make": "make", "cmake": "cmake", "ninja-build": "ninja-build", "git": "git",
    "python3": "python3", "python3-pip": "python3-pip", "unzip": "unzip", "p7zip-full": "p7zip", "curl": "curl", "wget": "wget", "xz-utils": "xz",
}
PROVIDERS = []


def register(fn):
    PROVIDERS.append(fn)


def _blocks(md: str):
    """[(títulos de las secciones, lenguaje, [líneas])] de cada bloque de código."""
    stack, out, cur, lang = [], [], None, ""
    for ln in md.splitlines():
        m = re.match(r"^\s*(```+|~~~+)\s*([\w+.-]*)", ln)
        if m and cur is None:
            cur, lang = [], m.group(2).lower()
            continue
        if m and cur is not None and ln.strip().startswith(("```", "~~~")):
            out.append(([t for _, t in stack], lang, cur))
            cur = None
            continue
        if cur is not None:
            cur.append(ln)
            continue
        h = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", ln)
        if h:
            lv = len(h.group(1))
            stack = [(l, t) for l, t in stack if l < lv] + [(lv, h.group(2))]
    return out


def _join(lines):
    out, buf = [], ""
    for ln in lines:
        s = ln.rstrip()
        if s.endswith("\\"):
            buf += s[:-1].rstrip() + " "
            continue
        full = (buf + s).strip()
        out += [p.strip() for p in full.split(" && ")] if not full.lstrip().startswith("#") else [full]
        buf = ""
    if buf:
        out.append(buf.strip())
    return out


def _tidy(c: str) -> str:
    c = re.sub(r"\s+#\s.*$", "", c).strip()
    return re.sub(r"(?<=\s)-j\s*\d+\b", "-j$JOBS", c)


def _clean(s: str) -> str:
    s = re.sub(r"^\s*(\$|>|%|#!?)\s+(?=\S)", "", s) if re.match(r"^\s*[$>]\s", s) else s
    return s.strip()


def _first(cmd):
    t = cmd.split()
    while t and (t[0] == "sudo" or "=" in t[0] and not t[0].startswith(("-", "./"))):
        t = t[1:]
    return t[0] if t else ""


def _kind(c: str) -> str:
    f = _first(c)
    if f in ("cd", "mkdir", "export", "cp", "mv", "ln", "chmod", "tar", "unzip", "source"):
        return "prep"
    if f in ("apt", "apt-get", "dnf", "yum", "pacman", "zypper") and re.search(r"\b(install|-S|-Sy|-Syu)\b", c):
        return "deps"
    if c.startswith("git submodule") or "submodule" in c:
        return "prep"
    if re.search(r"\bcmake\b.*--build|\bmake\b|\bninja\b|\bcargo build\b|\bmeson (compile|install)\b|\bgmake\b|\bscons\b|\bxmake\b|\bgo build\b", c):
        return "build"
    if re.search(r"\bcmake\b|\bmeson setup\b|\bconfigure\b|\bpremake5\b|\bccmake\b", c):
        return "config"
    return "prep"


def _to_dnf(c: str):
    """apt/apt-get install … → dnf install -y … (nombres traducidos). Devuelve (cmd, [sin traducción])."""
    f = _first(c)
    if f in ("dnf", "yum") and re.search(r"\binstall\b", c):
        c = re.sub(r"^(sudo\s+)?", "sudo ", c)
        return (c if re.search(r"\s-y\b", c) else re.sub(r"\binstall\b", "install -y", c, count=1)), []
    if f not in ("apt", "apt-get") or "install" not in c:
        return c, []
    pk = [p for p in c.split("install", 1)[1].split() if not p.startswith("-")]
    out, unk = [], []
    for p in pk:
        if p in APT_DNF:
            out.append(APT_DNF[p])
        else:
            m = re.match(r"^lib(.+)-dev$", p)
            out.append(f"lib{m.group(1)}-devel" if m else p)
            unk.append(p)
    return "sudo dnf install -y " + " ".join(dict.fromkeys(out)), unk


def _usable(c: str, repo_name: str) -> bool:
    if not c or c.startswith("#") or WIN_BAD.search(c) or re.search(r"\s--version\b|\s-V$", c):
        return False
    f = _first(c)
    if f.startswith("./"):
        return bool(SCRIPT_OK.search(f))
    if f not in CMDS or f in ("pacman", "zypper", "apk", "emerge", "nix", "nix-shell"):
        return False
    if f == "git" and re.search(r"\bgit (clone|pull|checkout|fetch|remote)\b", c):
        return False
    if f == "cd":
        a = c.split(None, 1)[-1].strip("/ '\"")
        return a not in ("", repo_name) and not a.endswith(("/" + repo_name,)) and a != ".."
    if f in ("npm", "yarn", "pnpm", "dotnet", "go", "nix", "nix-shell"):
        return False
    return True


def heuristic(docs, ctx=None):
    """docs = [(nombre, texto)]. Devuelve un plan o None."""
    ctx = ctx or {}
    repo_name = Path(str((ctx.get("entry") or {}).get("repo", "")).rstrip("/")).name.replace(".git", "")
    cands = []
    for name, text in docs:
        for titles, lang, lines in _blocks(text):
            head = " / ".join(titles)
            if NEG.search(head) and not LIN.search(head):
                continue
            if lang not in LANG_OK and lang not in ("", "cmake"):
                continue
            score = (3 if LIN.search(head) else 0) + (1 if POS.search(head) else 0) + (1 if "linux" in " ".join(lines).lower() else 0)
            cmds, notes = [], []
            for raw in _join(lines):
                if re.match(r"^\s*#\s*(or\b|alternatively|otherwise|if you)", raw, re.I):
                    break   # lo que sigue es una variante («# or using clang»), no un paso más
                c = _tidy(_clean(raw))
                if re.search(r"git clone.*(--recursive|--recurse-submodules)", c):
                    cmds.append("git submodule update --init --recursive")
                    continue
                if not _usable(c, repo_name):
                    continue
                c, unk = _to_dnf(c)
                if unk:
                    notes.append("Revisa los paquetes (nombre de apt sin traducción exacta): " + ", ".join(unk))
                if re.match(r"^(sudo )?(make|gmake|ninja)\s*$", c) or re.search(r"\bcmake --build\b", c) and "-j" not in c:
                    c += " -j$JOBS" if "make" in c or "build" in c else ""
                if re.match(r"^(sudo )?(make|gmake|ninja)\b", c) and any(re.match(r"^(sudo )?(make|gmake|ninja)\b", x) for x in cmds):
                    continue   # otra variante del mismo comando (otra VERSION…): solo la primera
                cmds.append(c)
            while cmds and _first(cmds[-1]) in ("cd", "mkdir", "export"):
                cmds.pop()      # un «cd build» suelto al final no es un paso
            if cmds:
                cands.append({"name": name, "head": head, "score": score, "cmds": cmds, "notes": notes})
    if not cands:
        return None
    other = re.compile(r"\b(arch|manjaro|opensuse|suse|nix|nixos|gentoo|alpine|void|slackware)\b", re.I)
    deb = re.compile(r"\b(debian|ubuntu|mint|apt)\b", re.I)
    has_fed = any(re.search(r"fedora|\bdnf\b|rhel|centos", c["head"], re.I) for c in cands)
    keep = []
    for c in cands:
        if other.search(c["head"]) and not LIN.search(other.sub("", c["head"])) is False and not re.search(r"fedora", c["head"], re.I):
            continue
        if has_fed and deb.search(c["head"]) and not re.search(r"fedora", c["head"], re.I):
            continue
        keep.append(c)
    cands = keep or cands
    best = max(c["score"] for c in cands)
    chosen = [c for c in cands if c["score"] >= max(1, best - 1) or c["score"] >= 3] or cands[:1]
    tool = None
    steps, notes, seen = [], [], set()
    for b in chosen:
        bt = next((_first(c) for c in b["cmds"] if _kind(c) in ("build", "config")), None)
        if bt and tool and bt != tool:
            notes.append(f"Descartada una alternativa ({bt}) de «{b['head'] or b['name']}»")
            continue
        tool = tool or bt
        notes += b["notes"]
        for c in b["cmds"]:
            if c in seen:
                continue
            seen.add(c)
            steps.append({"kind": _kind(c), "cmd": c, "from": b["head"] or b["name"]})
    if (ctx.get("dest") and (Path(ctx["dest"]) / ".gitmodules").exists()) and not any("submodule" in s["cmd"] for s in steps):
        steps.insert(0, {"kind": "prep", "cmd": "git submodule update --init --recursive", "from": ".gitmodules"})
    order = {"deps": 0, "prep": 1, "config": 2, "build": 3}
    steps = [s for _, s in sorted(enumerate(steps), key=lambda p: (order[p[1]["kind"]] if p[1]["kind"] != "prep" or not p[1]["cmd"].startswith("cd") else 1.5, p[0]))]
    has_build = any(s["kind"] == "build" for s in steps)
    conf = "alta" if has_build and best >= 3 else "media" if has_build else "baja"
    if not has_build:
        notes.append("No encontré el paso que compila: revisa o usa el comando sugerido por los archivos del repo.")
    return {"steps": steps, "notes": list(dict.fromkeys(notes)), "confidence": conf, "source": ", ".join(dict.fromkeys(n for n, _ in docs[:3])), "provider": "heurística"}


register(heuristic)


def plan_from_docs(docs, ctx=None):
    """Primer proveedor que devuelve un plan con pasos."""
    for fn in PROVIDERS:
        try:
            p = fn(docs, ctx)
        except Exception:  # noqa: BLE001
            p = None
        if p and p.get("steps"):
            return p
    return None


def to_cmd(plan) -> str:
    """Script para BuildJob ($REPO y $JOBS los rellena él): para en el primer fallo."""
    return "cd '$REPO'\nset -e\n" + "\n".join(s["cmd"] for s in plan["steps"])


def to_oneline(plan) -> str:
    """Lo mismo en una línea (para el editor de texto): comandos unidos con &&."""
    return "cd '$REPO' && " + " && ".join(s["cmd"] for s in plan["steps"])


def describe(plan, width=84) -> str:
    names = {"deps": "dependencias", "prep": "preparar", "config": "configurar", "build": "compilar"}
    ls = [f"Fuente: {plan['source']} · confianza {plan['confidence']} · {plan['provider']}", ""]
    for i, s in enumerate(plan["steps"], 1):
        c = s["cmd"] if len(s["cmd"]) <= width else s["cmd"][:width - 1] + "…"
        ls.append(f"{i}. {names.get(s['kind'], s['kind'])}: {c}")
    for n in plan["notes"]:
        ls += ["", "• " + n]
    return "\n".join(ls)


_DOC_NAMES = re.compile(r"^(readme|build|building|compil|install|setup|develop|contribut|linux)[\w .-]*\.(md|markdown|txt)$", re.I)


def read_local(dest, limit=200_000):
    d = Path(dest)
    docs = []
    for base in (d, d / "docs", d / "doc"):
        try:
            for f in sorted(base.iterdir()):
                if f.is_file() and _DOC_NAMES.match(f.name) and f.stat().st_size < limit:
                    docs.append((f.relative_to(d).as_posix(), f.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    docs.sort(key=lambda t: (0 if t[0].lower().startswith("readme") else 1, t[0]))
    return docs[:5]


def fetch_remote(repo, api_get):
    """README + documentos de compilación del repo vía API de GitHub (api_get = ghapi.get)."""
    docs = []
    items = []
    for sub in ("", "docs/"):
        try:
            r = api_get(f"/repos/{repo}/contents/{sub}")
        except Exception:  # noqa: BLE001
            continue
        items += r if isinstance(r, list) else []
    for it in items:
        if it.get("type") == "file" and _DOC_NAMES.match(it.get("name", "")) and it.get("size", 0) < 200_000:
            try:
                d = api_get(f"/repos/{repo}/contents/{it['path']}")
                docs.append((it["path"], base64.b64decode(d.get("content", "")).decode("utf-8", "replace")))
            except Exception:  # noqa: BLE001
                continue
    docs.sort(key=lambda t: (0 if t[0].lower().startswith("readme") else 1, t[0]))
    return docs[:5]


def plan_for(entry, dest, api_get, container=""):
    """Plan para una entrada: lee el repo local si ya está clonado; si no, la API. None si no hay nada que leer o entender."""
    docs = read_local(dest) if (Path(dest) / ".git").is_dir() else []
    if not docs and entry.get("repo") and "/" in str(entry["repo"]) and not Path(str(entry["repo"])).exists():
        docs = fetch_remote(entry["repo"], api_get)
    return plan_from_docs(docs, {"entry": entry, "dest": str(dest), "container": container}) if docs else None
