"""Rutas y ajustes de Recomp Hub. Todo lo del usuario vive en data/ (se conserva al reinstalar)."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("HUB_DATA") or ROOT / "data")
CACHE = DATA / "cache"
LAUNCHER = Path(os.environ.get("LAUNCHER_DIR") or "~/Games/launcher").expanduser()  # el launcher unificado
GAMES_DIR = Path(os.environ.get("HUB_GAMES") or "~/Games").expanduser()            # donde se instalan los ports
SETTINGS_FILE = DATA / "settings.json"
try:
    VERSION = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
except OSError:
    VERSION = "?"
# Credenciales: FUERA de la carpeta del proyecto (así no acaban en git). HUB_CONFIG las redirige; con HUB_DATA personalizado (tests) van ahí.
CONFIG = Path(os.environ.get("HUB_CONFIG") or (DATA if os.environ.get("HUB_DATA") else Path(os.environ.get("XDG_CONFIG_HOME") or "~/.config").expanduser() / "recomp-hub"))

DEFAULT_SETTINGS = {
    "extract_to_library": True,                 # los archivos comprimidos se extraen y la biblioteca guarda el archivo llano
    "delete_archive": True,                     # …y se elimina el paquete (zip/rar/7z) una vez comprobada la copia
    "auto_libcwd": False,                       # v1.96: apagado. Cambiar [run] cwd hacía que juegos como Silent Hill guardaran su config en la carpeta de ROMs                        # al reconocer el archivo del juego, su selector de archivos empieza en esa carpeta
    "haptics": True,                            # v2.85: vibración del mando al mantener pulsado un juego
    "long_press": 0.45,                         # segundos manteniendo el dedo para abrir el menú de un juego
    "sounds": True,                             # sonidos de la interfaz (sintetizados; data/sounds/<nombre>.wav los sustituye)
    "sound_volume": 0.5,
    "perf_log": False,                          # sonda de rendimiento: fotogramas lentos a hub.log
    "downloads_dir": str(DATA / "downloads"),   # TODAS las descargas de Hub, dentro del proyecto (data/ no se sube a git)
    "library_dir": "~/Games/library",           # biblioteca local, ordenada por plataforma
    "watch_dirs": [str(DATA / "downloads" / "navegador"), "~/Downloads", "~/Descargas"],  # carpetas vigiladas para el archivo requerido del juego
    "catalog_autostart": True,                  # arrancar el servicio local de catálogo al abrir Hub
    "max_active": 2,                            # descargas simultáneas
    "connections": 4,                           # conexiones por descarga
    "arch": "x86_64",
    "theme": "dark",                            # dark | light
    "fx": "glass",                              # glass (alta: todo) | balanced (v3.09: fondo quieto, sin destellos) | perf (sin blur, fondo liso)
    "reduce_motion": False,                     # v3.09: accesibilidad, para todos los temas (Ajustes › Aspecto)
    "high_contrast": False,
    "large_text": False,
    "check_on_start": False,                    # v2.43: comprobar al arrancar Hub si hay versiones nuevas de lo instalado
    "proton_default": "",                       # v2.65: carpeta del Proton que usan por defecto los juegos de Windows ("" = automático: UMU-Proton, luego GE-Proton)
    "launcher_checks": True,                    # v2.48: el launcher consulta GitHub al abrir cada juego
    "lc_saved": {},
    "fetch_on_open": True,                      # v2.43: consultar GitHub al abrir la ficha de un juego
    "frozen": {},                               # v2.43: juegos con las actualizaciones congeladas {id: {"type": tipo original de [update], "tag": versión}}
    "auto_update": True,                        # al abrir, instalar un recomp-hub-update-vX.zip más nuevo si lo hay en ~/Games/actualizaciones
    "direct_play": True,                        # v3.10: abrir los juegos sin la pantalla previa del launcher (actualizar lo hace Hub)
    "close_on_play": True,                      # al pulsar JUGAR, Hub se cierra (el juego queda en su propio proceso)
}


def load_env():
    """DATA/.env o ROOT/.env (CLAVE=valor), sin pisar variables ya definidas (p. ej. GITHUB_TOKEN)."""
    for f in (DATA / ".env", ROOT / ".env"):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            k, v = k.strip().removeprefix("export ").strip(), v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if k and k not in os.environ:
                os.environ[k] = v


BROWSER_DL = DATA / "downloads" / "navegador"   # aquí debe guardar tu navegador lo que descargues; Hub solo vigila esta carpeta


def settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    try:
        s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    # migración: la carpeta antigua de versiones previas pasa a la del proyecto
    if s.get("downloads_dir") in ("~/Games/hub-downloads", "~/Games/hub-downloads/"):
        s["downloads_dir"] = DEFAULT_SETTINGS["downloads_dir"]
    if str(BROWSER_DL) not in [str(x) for x in s.get("watch_dirs", [])]:
        s["watch_dirs"] = [str(BROWSER_DL)] + list(s.get("watch_dirs", []))
    return s


def save_settings(s: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")


def path(key: str) -> Path:
    return Path(os.path.expandvars(str(settings()[key]))).expanduser()
