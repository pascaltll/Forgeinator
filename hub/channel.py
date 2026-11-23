"""v3.15 · Canales estable y dev conviviendo, y dónde vive cada cosa.

Una copia del programa sabe su canal por el archivo CHANNEL de su carpeta («stable» o «dev»). Sin ese archivo es una instalación
antigua (~/Games/recomp-hub): todo sigue en <programa>/data como siempre (modo «legado»).

Con canal (instalado como app del QAM en ~/homebrew/qam-apps/forgeinator y …/forgeinator-dev):
- Biblioteca COMÚN (juegos, descargas, ROMs enlazadas, arte, cachés, registros de compilación):  ~/.local/share/forgeinator
- Claves COMUNES (credentials.json, .env):                                                       ~/.config/forgeinator
- Ajustes de CADA canal (settings.json: tema, opciones):                                         ~/.config/forgeinator/<canal>
- Registros de CADA canal (hub.log, update.json, pruebas, diagnóstico):                          ~/.local/state/forgeinator/<canal>
El programa no escribe nunca dentro de su carpeta: se puede sustituir entero al actualizar.

Canal ACTIVO (archivo `canal` en la biblioteca común): solo él toca lo compartido con fuera del Hub (los atajos de los juegos en
Steam, la apariencia publicada para el lanzador y el QAM). La otra copia se abre y funciona, pero no reescribe nada de eso.
Red de seguridad: si dev no llega a funcionar 20 s en dos arranques seguidos y hay estable instalada, el canal activo vuelve a estable.
Este módulo no importa pygame: lo usan también bin/forgeinator, --qam-status y las pruebas."""
import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = "forgeinator"
CHANNELS = ("stable", "dev")
LABEL = {"stable": "Estable", "dev": "Dev", None: "Instalación antigua"}
FOLDER = {"stable": "forgeinator", "dev": "forgeinator-dev"}       # carpeta de cada copia dentro de qam-apps
BOOT_LIMIT = 2                                                    # arranques seguidos de dev sin confirmar → vuelve a estable
BOOT_OK_AFTER = 20.0                                              # segundos con la interfaz funcionando para dar el arranque por bueno


def _xdg(var, default):
    return Path(os.environ.get(var) or Path(default).expanduser())


def _file_channel(root: Path):
    try:
        ch = (Path(root) / "CHANNEL").read_text(encoding="utf-8").strip().lower()
    except OSError:
        return None
    return ch if ch in CHANNELS else None


def program_channel(root: Path = ROOT):
    """'stable' | 'dev' | None (instalación antigua). HUB_CHANNEL lo fuerza (pruebas)."""
    ch = (os.environ.get("HUB_CHANNEL") or "").strip().lower()
    if ch:
        return ch if ch in CHANNELS else None
    return _file_channel(root)


CHANNEL = program_channel()


def shared_dir() -> Path:
    return _xdg("XDG_DATA_HOME", "~/.local/share") / APP


def config_root() -> Path:
    return _xdg("XDG_CONFIG_HOME", "~/.config") / APP


def conf_dir(ch) -> Path:
    return config_root() / ch


def state_dir(ch) -> Path:
    return _xdg("XDG_STATE_HOME", "~/.local/state") / APP / ch


def layout(ch=CHANNEL, root: Path = ROOT) -> dict:
    """Rutas de esta copia. HUB_DATA (pruebas, usos especiales) lo junta todo en una carpeta, como antes; HUB_CONF / HUB_STATE / HUB_CONFIG
    sustituyen cada parte por separado."""
    env = os.environ
    if env.get("HUB_DATA"):
        data = Path(env["HUB_DATA"])
        conf = state = creds = data
    elif ch:
        data, conf, state, creds = shared_dir(), conf_dir(ch), state_dir(ch), config_root()
    else:
        data = root / "data"
        conf = state = data
        creds = _xdg("XDG_CONFIG_HOME", "~/.config") / "recomp-hub"
    return {"data": data, "conf": Path(env.get("HUB_CONF") or conf), "state": Path(env.get("HUB_STATE") or state),
            "creds": Path(env.get("HUB_CONFIG") or creds)}


# ---------------------------------------------------------------- canal activo
def qam_apps() -> Path:
    return Path(os.environ.get("QAM_APPS_DIR") or "~/homebrew/qam-apps").expanduser()


def copy_dir(ch) -> Path:
    return qam_apps() / FOLDER[ch]


def installed(ch) -> bool:
    return _file_channel(copy_dir(ch)) == ch


def flag_file() -> Path:
    return shared_dir() / "canal"


def active():
    """Canal que manda. Sin elegir: estable si está instalada; si no, dev (si está); si no, el de esta copia."""
    try:
        v = flag_file().read_text(encoding="utf-8").strip().lower()
        if v in CHANNELS:
            return v
    except OSError:
        pass
    for ch in CHANNELS:
        if installed(ch):
            return ch
    return CHANNEL


def set_active(ch) -> None:
    if ch not in CHANNELS:
        raise ValueError(ch)
    f = flag_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(".canal.tmp")
    tmp.write_text(ch + "\n", encoding="utf-8")
    os.replace(tmp, f)
    if ch == "dev":
        boot_ok()                                                 # elegir dev a mano empieza la cuenta de cero


def is_active(ch=CHANNEL) -> bool:
    """¿Esta copia gestiona lo compartido? Una instalación antigua siempre (es la única)."""
    return ch is None or active() == ch


# ---------------------------------------------------------------- red de seguridad de dev
def _boots_file() -> Path:
    return state_dir("dev") / "arranques"


def boots() -> int:
    try:
        return int(_boots_file().read_text().strip() or 0)
    except (OSError, ValueError):
        return 0


def boot_begin(ch=CHANNEL) -> int:
    """Al arrancar dev: suma uno. Devuelve la cuenta (antes de confirmar)."""
    if ch != "dev":
        return 0
    n = boots() + 1
    try:
        _boots_file().parent.mkdir(parents=True, exist_ok=True)
        _boots_file().write_text(str(n))
    except OSError:
        pass
    return n


def boot_ok() -> None:
    try:
        _boots_file().parent.mkdir(parents=True, exist_ok=True)
        _boots_file().write_text("0")
    except OSError:
        pass


def notice_file() -> Path:
    return shared_dir() / "aviso-canal.json"


def safety_check() -> bool:
    """Si dev manda, falló BOOT_LIMIT arranques seguidos y estable está instalada: estable pasa a mandar y queda un aviso. True si cambió."""
    if active() != "dev" or boots() < BOOT_LIMIT or not installed("stable"):
        return False
    set_active("stable")
    boot_ok()
    try:
        notice_file().write_text(json.dumps({"t": time.time(), "texto": f"Dev no arrancó bien {BOOT_LIMIT} veces seguidas: el canal activo "
                                             "vuelve a ser Estable. Puedes volver a activar Dev en Ajustes."}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return True


def take_notice():
    """Aviso pendiente de la red de seguridad (se muestra una vez)."""
    f = notice_file()
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        f.unlink()
        return d.get("texto")
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- migración desde ~/Games/recomp-hub/data
SKIP = {"hub.log", "hub.log.old", "restart.flag", "session-select.log", "doctor.txt", "tests", "update.json", "browser-venv",
        "browser-pylibs", "__pycache__", "settings.json", "appearance-request.json"}
HEAVY = {"downloads", "builds", "build", "backups", "port", "covers", "cache", "launch-logs", "history", "browser"}
CROSS_DEVICE_COPY_MAX = 512 * 1024 * 1024


def legacy_dirs() -> list:
    c = [os.environ.get("HUB_LEGACY_DATA"), "~/Games/recomp-hub/data"]
    return [Path(x).expanduser() for x in c if x and Path(x).expanduser().is_dir()]


def _size(p: Path) -> int:
    n = 0
    for dp, _dn, fn in os.walk(p):
        for f in fn:
            try:
                n += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return n


def _link_tree(src: Path, dst: Path) -> str:
    """Copia de una carpeta pesada con enlaces duros (al instante y sin ocupar más disco; los originales quedan intactos).
    Otro disco: copia normal si cabe en el límite; si no, se deja donde está."""
    try:
        shutil.copytree(src, dst, copy_function=os.link, symlinks=True, dirs_exist_ok=True)
        return "enlazada"
    except OSError:
        if _size(src) <= CROSS_DEVICE_COPY_MAX:
            shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
            return "copiada"
        return "se queda en su sitio"


def _rewrite(obj, old: str, new: str):
    if isinstance(obj, str):
        return new + obj[len(old):] if obj == old or obj.startswith(old + "/") else obj
    if isinstance(obj, list):
        return [_rewrite(x, old, new) for x in obj]
    if isinstance(obj, dict):
        return {k: _rewrite(v, old, new) for k, v in obj.items()}
    return obj


def migrate(lay=None, sources=None) -> dict:
    """Una sola vez por biblioteca: copia lo de la instalación antigua a la biblioteca común, sin borrar ni mover nada del origen.
    Los .json pequeños se reescriben para que sus rutas apunten a la carpeta nueva. Devuelve un informe (también en .migrado)."""
    lay = lay or layout()
    data, creds = lay["data"], lay["creds"]
    mark = data / ".migrado"
    if mark.exists():
        return {"hecho": False, "motivo": "ya migrado"}
    srcs = legacy_dirs() if sources is None else [Path(s) for s in sources if Path(s).is_dir()]
    rep = {"hecho": True, "origen": None, "copiado": [], "pesado": {}, "omitido": []}
    data.mkdir(parents=True, exist_ok=True)
    if srcs:
        src = srcs[0]
        rep["origen"] = str(src)
        old, new = str(src.resolve()), str(data.resolve())
        for p in sorted(src.iterdir()):
            dst = data / p.name
            if p.name in SKIP or dst.exists():
                rep["omitido"].append(p.name)
                continue
            try:
                if p.is_dir() and p.name in HEAVY:
                    rep["pesado"][p.name] = _link_tree(p, dst)
                elif p.is_dir():
                    shutil.copytree(p, dst, symlinks=True)
                    rep["copiado"].append(p.name + "/")
                elif p.suffix == ".json" and p.stat().st_size < 8 * 1024 * 1024:
                    try:
                        d = _rewrite(json.loads(p.read_text(encoding="utf-8")), old, new)
                        dst.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
                    except ValueError:
                        shutil.copy2(p, dst)
                    rep["copiado"].append(p.name)
                else:
                    shutil.copy2(p, dst)
                    rep["copiado"].append(p.name)
            except OSError as ex:
                rep["omitido"].append(f"{p.name} ({ex.__class__.__name__})")
        rep["_old"], rep["_new"] = old, new
    # claves: ~/.config/recomp-hub (y data/ antigua) → ~/.config/forgeinator, con permisos 600
    for name in ("credentials.json", ".env"):
        dst = creds / name
        if dst.exists():
            continue
        for cand in [_xdg("XDG_CONFIG_HOME", "~/.config") / "recomp-hub" / name] + [s / name for s in srcs]:
            if cand.is_file():
                creds.mkdir(parents=True, exist_ok=True)
                try:
                    os.chmod(creds, 0o700)
                except OSError:
                    pass
                shutil.copy2(cand, dst)
                os.chmod(dst, 0o600)
                rep["copiado"].append(f"claves: {name}")
                break
    info = {k: v for k, v in rep.items() if not k.startswith("_")}
    info["t"] = time.time()
    mark.write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    return rep


def seed_settings(lay=None, sources=None, rep=None) -> str:
    """Ajustes de este canal la primera vez: los de la instalación antigua (con sus rutas a la biblioteca nueva) o, si no, los del otro
    canal. Devuelve de dónde salieron ('' = ninguno: valores por defecto)."""
    lay = lay or layout()
    f = lay["conf"] / "settings.json"
    if f.exists():
        return "propios"
    cands = []
    srcs = legacy_dirs() if sources is None else [Path(s) for s in sources if Path(s).is_dir()]
    for s in srcs:
        cands.append((s / "settings.json", str(s.resolve()), str(lay["data"].resolve())))
    for ch in CHANNELS:
        if ch != CHANNEL:
            cands.append((conf_dir(ch) / "settings.json", None, None))
    for cand, old, new in cands:
        try:
            d = json.loads(cand.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if old and new:
            d = _rewrite(d, old, new)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        return str(cand)
    return ""


def describe() -> dict:
    lay = layout()
    return {"channel": CHANNEL, "label": LABEL.get(CHANNEL), "active": active(), "is_active": is_active(),
            "installed": {ch: installed(ch) for ch in CHANNELS}, **{k: str(v) for k, v in lay.items()}}
