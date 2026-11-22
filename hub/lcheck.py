"""v2.48: interruptor global de la comprobación de actualizaciones que hace el LAUNCHER al abrir cada juego (una consulta a GitHub por arranque).
Apagado: pone `[update] type = "none"` en cada .toml (guardando el tipo original en cfg["lc_saved"]); encendido: lo restaura."""
import re

from . import config, gamecfg


def _type_of(txt):
    sec = ""
    for ln in txt.split("\n"):
        st = ln.strip()
        if st.startswith("[") and st.endswith("]"):
            sec = st[1:-1].strip()
        elif sec == "update":
            m = re.match(r'\s*type\s*=\s*"([^"]*)"', ln)
            if m:
                return m.group(1)
    return None


def _set(txt, typ):
    out, sec = [], ""
    for ln in txt.split("\n"):
        st = ln.strip()
        if st.startswith("[") and st.endswith("]"):
            sec = st[1:-1].strip()
        elif sec == "update" and re.match(r'\s*type\s*=', ln):
            ln = f'type = "{typ}"'
        out.append(ln)
    return "\n".join(out)


def apply(cfg: dict) -> int:
    """Deja los .toml según cfg["launcher_checks"] (True por defecto). Devuelve cuántos cambió."""
    on = cfg.get("launcher_checks", True)
    saved = cfg.setdefault("lc_saved", {})
    n = 0
    d = config.LAUNCHER / "games"
    if not d.is_dir():
        return 0
    for f in sorted(d.glob("*.toml")):
        try:
            txt = f.read_text(encoding="utf-8")
        except OSError:
            continue
        cur = _type_of(txt)
        if cur is None:
            continue
        lid = f.stem
        try:
            if not on and cur != "none":
                saved[lid] = cur
                gamecfg._write(f, _set(txt, "none"))
                n += 1
            elif on and cur == "none" and saved.get(lid):
                gamecfg._write(f, _set(txt, saved.pop(lid)))
                n += 1
        except OSError:
            continue
    if on:
        for k in [k for k in saved if not (d / f"{k}.toml").exists()]:
            saved.pop(k, None)
    return n
