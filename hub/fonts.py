"""Tipografías que un tema puede traer de fuera (v2.31). Se bajan UNA vez de google/fonts en GitHub (licencia OFL) a data/fonts/ y, mientras
no estén, el tema se dibuja con la fuente del sistema. Sin red no pasa nada: el tema funciona igual, con otra letra."""
import threading
import urllib.request
from pathlib import Path

from . import config

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
DL = {   # nombre → (normal, negrita o None: se engorda la normal)
    "poppins": ("poppins/Poppins-Regular.ttf", "poppins/Poppins-SemiBold.ttf"),
    "vt323": ("vt323/VT323-Regular.ttf", None),
    "chakra": ("chakrapetch/ChakraPetch-Regular.ttf", "chakrapetch/ChakraPetch-Bold.ttf"),
}
# v3.09: peso medio REAL (archivo propio). Solo Poppins y Chakra Petch lo traen; VT323 tiene un único peso. Se baja junto a los otros
# (si falla, la fuente sigue funcionando: «medium» cae a la negrita). No cambia lo que dibujan los temas que no piden «medium».
MEDIUM = {"poppins": "poppins/Poppins-Medium.ttf", "chakra": "chakrapetch/ChakraPetch-Medium.ttf"}
_busy = set()


def dir_() -> Path:
    return config.DATA / "fonts"


def _file(rel: str) -> Path:
    return dir_() / rel.rsplit("/", 1)[-1]


def _ok(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            return p.stat().st_size > 20_000 and f.read(4) in (b"\x00\x01\x00\x00", b"OTTO", b"true")
    except OSError:
        return False


def paths(name: str):
    """(normal, negrita, negrita_sintética) si la fuente ya está en disco; None si falta."""
    reg, bold = DL.get(name, (None, None))
    if not reg or not _ok(_file(reg)):
        return None
    if bold and _ok(_file(bold)):
        return str(_file(reg)), str(_file(bold)), False
    return str(_file(reg)), str(_file(reg)), False      # sin negrita propia: se usa la normal (engordarla emborrona las de píxel)


def medium_path(name: str):
    """Ruta del archivo «Medium» de la fuente si ya está en disco; None si la fuente no tiene o aún no se bajó."""
    rel = MEDIUM.get(name)
    return str(_file(rel)) if rel and _ok(_file(rel)) else None


def fetch(name: str, timeout=30) -> bool:
    """Descarga los archivos de la fuente (escritura atómica; se comprueba que sea un TTF/OTF). True si quedó utilizable."""
    reg, bold = DL.get(name, (None, None))
    if not reg:
        return False
    dir_().mkdir(parents=True, exist_ok=True)
    for rel in (reg, bold, MEDIUM.get(name)):
        if not rel or _ok(_file(rel)):
            continue
        tmp = _file(rel).with_suffix(".part")
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + rel, headers={"User-Agent": "recomp-hub"}), timeout=timeout) as r:
                tmp.write_bytes(r.read(4_000_000))
            if not _ok(tmp):
                raise OSError("no es una fuente")
            tmp.replace(_file(rel))
        except Exception:  # noqa: BLE001  (sin red, 404…): el tema sigue con la fuente del sistema
            tmp.unlink(missing_ok=True)
            if rel == reg:
                return False
    return paths(name) is not None


def ensure(name: str, done=None):
    """Baja la fuente en segundo plano (una sola vez a la vez por nombre) y llama a done(ok)."""
    if name in _busy or name not in DL:
        return
    _busy.add(name)

    def job():
        try:
            ok = fetch(name)
        finally:
            _busy.discard(name)
        if done:
            done(ok)
    threading.Thread(target=job, daemon=True).start()
