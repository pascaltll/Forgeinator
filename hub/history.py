"""Historial por juego (v2.79): en qué configuración funcionó cada cosa y en cuál falló.
Cada evento (jugar, instalar/actualizar, compilar) guarda una línea en data/history/<id>.jsonl con una FOTO del entorno de ese momento:
versión del juego, distribución (linux/windows), runner (Proton/Wine/propio) y su versión, contenedor y la lista de distrobox, sistema y versión de Hub.
Así, cuando algo falla, queda escrito con qué combinación; y la ficha muestra qué configuraciones han funcionado. Nunca guarda tokens ni claves."""
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

from . import config

KEEP = 300
_CONT = {"t": 0.0, "v": []}


def _dir() -> Path:
    d = config.DATA / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file(lid: str) -> Path:
    return _dir() / (str(lid).replace("/", "_") + ".jsonl")


def containers(max_age=120.0) -> list:
    """Contenedores distrobox existentes: ['nombre (imagen)', …]. Se cachea 2 min; vacío si no hay distrobox."""
    now = time.time()
    if now - _CONT["t"] < max_age:
        return _CONT["v"]
    out = []
    if shutil.which("distrobox"):
        try:
            r = subprocess.run(["distrobox", "list", "--no-color"], capture_output=True, text=True, timeout=5).stdout
            for ln in r.splitlines()[1:]:
                p = [x.strip() for x in ln.split("|")]
                if len(p) >= 4 and p[1]:
                    out.append(f"{p[1]} ({p[3]})")
        except (OSError, subprocess.SubprocessError):
            pass
    _CONT.update(t=now, v=out)
    return out


def _osrel() -> str:
    try:
        d = dict(ln.split("=", 1) for ln in Path("/etc/os-release").read_text().splitlines() if "=" in ln)
        return (d.get("PRETTY_NAME") or d.get("NAME") or "").strip('"')
    except OSError:
        return ""


def snapshot(lid: str, version: str = "") -> dict:
    """Foto del entorno ahora mismo para este juego. Nunca lanza."""
    s = {"hub": "", "version": version, "layout": "", "runner": "", "proton": "", "container": "", "containers": [], "system": "", "kernel": platform.release()}
    try:
        from . import launchlog, osver
        s["hub"] = launchlog._version()
        r = osver.root_of(lid)
        if r is not None:
            m = osver.meta(r)
            act = m.get("active") or ("linux" if (r / "linux").is_dir() else "")
            s["layout"] = act
            s["container"] = m.get("container") or ""
            if act == "windows":
                s["runner"] = (m.get("windows") or {}).get("runner", "proton")
                if s["runner"] in ("proton", "own") or True:
                    s["proton"] = Path(osver.proton_path()).name
        ri = launchlog.run_info(lid)
        if ri.get("container") and not s["container"]:
            s["container"] = ri["container"]
    except Exception:  # noqa: BLE001
        pass
    s["containers"] = containers()
    s["system"] = _osrel()
    return s


def record(lid: str, event: str, ok=None, detail: str = "", snap: dict | None = None, version: str = "", **extra) -> dict:
    """Añade una línea. ok: True/False; None = pendiente/informativo. Poda a las últimas KEEP."""
    row = {"t": int(time.time()), "event": event, "ok": ok, "detail": (detail or "")[:300]}
    row.update(extra)
    row["env"] = snap if snap is not None else snapshot(lid, version)
    try:
        f = _file(lid)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        lines = f.read_text(encoding="utf-8").splitlines()
        if len(lines) > KEEP:
            f.write_text("\n".join(lines[-KEEP:]) + "\n", encoding="utf-8")
    except OSError:
        pass
    return row


def rows(lid: str) -> list:
    out = []
    try:
        for ln in _file(lid).read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def first_error(text: str) -> str:
    """Última línea con aspecto de error real (sin el ruido conocido de Steam/gamescope)."""
    from . import launchlog
    best = ""
    for ln in (text or "").splitlines():
        if launchlog.ERRORY.search(ln) and not launchlog.NOISE.search(ln):
            best = ln.strip()
    return best[:200]


def config_key(env: dict) -> str:
    e = env or {}
    parts = [e.get("layout") or "?"]
    if e.get("layout") == "windows":
        parts.append(e.get("runner") or "proton")
        if e.get("proton"):
            parts.append(e["proton"])
    if e.get("container"):
        parts.append("contenedor " + e["container"])
    if e.get("version"):
        parts.append(e["version"])
    return " · ".join(parts)


def matrix(lid: str) -> list:
    """[{config, ok, fail, last_ok, last_fail, error}] por configuración, las más recientes primero. Solo cuentan eventos con resultado."""
    by = {}
    for r in rows(lid):
        if r.get("ok") is None or r.get("event") not in ("jugar", "compilar", "instalar", "actualizar"):
            continue
        k = (r["event"] if r["event"] in ("compilar",) else "jugar/instalar", config_key(r.get("env")))
        d = by.setdefault(k, {"what": k[0], "config": k[1], "ok": 0, "fail": 0, "last_ok": 0, "last_fail": 0, "error": ""})
        if r["ok"]:
            d["ok"] += 1
            d["last_ok"] = r["t"]
        else:
            d["fail"] += 1
            d["last_fail"] = r["t"]
            d["error"] = r.get("detail") or d["error"]
    return sorted(by.values(), key=lambda d: -max(d["last_ok"], d["last_fail"]))


def text(lid: str, name: str = "") -> str:
    rs = rows(lid)
    L = [f"# Historial de {name or lid}", ""]
    if not rs:
        return "\n".join(L + ["Todavía no hay eventos: se irán guardando al jugar, instalar/actualizar y compilar."])
    L += ["## Configuraciones (✓ funcionó · ✗ falló)"]
    for d in matrix(lid):
        t = max(d["last_ok"], d["last_fail"])
        L.append(f"- {'✓' if d['ok'] and not d['fail'] else '✗' if d['fail'] and not d['ok'] else '±'} {d['what']}: {d['config']} — {d['ok']} bien, {d['fail']} mal "
                 f"(último {time.strftime('%d/%m %H:%M', time.localtime(t))})" + (f"\n    error: {d['error']}" if d["fail"] and d["error"] else ""))
    if not matrix(lid):
        L.append("- (aún sin resultados: los arranques quedan «pendientes» hasta saber si abrieron)")
    L += ["", "## Últimos eventos"]
    for r in rs[-25:][::-1]:
        e = r.get("env") or {}
        mark = {True: "✓", False: "✗"}.get(r.get("ok"), "·")
        L.append(f"- {time.strftime('%d/%m %H:%M', time.localtime(r['t']))} {mark} {r['event']} — {config_key(e)}" + (f" — {r['detail']}" if r.get("detail") else ""))
    last = rs[-1].get("env") or {}
    L += ["", "## Entorno del último evento",
          f"- Hub {last.get('hub', '?')} · {last.get('system', '?')} · kernel {last.get('kernel', '?')}",
          f"- Contenedores: {', '.join(last.get('containers') or []) or '(ninguno / sin distrobox)'}"]
    return "\n".join(L)
