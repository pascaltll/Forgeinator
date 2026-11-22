"""Energía del equipo (ROG Ally / portátiles): TDP actual, batería y consumo, leídos de /sys sin permisos especiales.
Lo que fije tu plugin de TDP (Decky, hhd, QAM) se ve aquí como el límite de potencia del procesador.
Sirve para el modo AHORRO de Hub (menos fps y sin animaciones con TDP bajo o batería baja) y para anotar el TDP en el informe de pruebas."""
import glob
import os
import time
from pathlib import Path

ROOT = Path(os.environ.get("HUB_SYSFS", "/sys"))
SAVE_TDP_W = 9.0        # con 9 W o menos se considera «modo portátil de ahorro»
SAVE_BATTERY_PCT = 25   # o con batería por debajo de esto y desenchufado


def _read(p):
    try:
        return Path(p).read_text().strip()
    except OSError:
        return None


def _num(p):
    v = _read(p)
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def tdp() -> tuple:
    """(vatios, de dónde) del límite sostenido de potencia (PL1/SPL). (None, '') si el equipo no lo expone."""
    cands = [(ROOT / "class/firmware-attributes/asus-armoury/attributes/ppt_pl1_spl/current_value", 1.0, "asus-armoury ppt_pl1_spl"),
             (ROOT / "devices/platform/asus-nb-wmi/ppt_pl1_spl", 1.0, "asus-nb-wmi ppt_pl1_spl")]
    for p, k, src in cands:
        v = _num(p)
        if v and v > 0:
            return round(v * k, 1), src
    for p in sorted(glob.glob(str(ROOT / "class/drm/card*/device/hwmon/hwmon*/power1_cap"))):
        v = _num(p)
        if v and v > 0:
            return round(v / 1e6, 1), "amdgpu power1_cap"
    return None, ""


def battery() -> dict:
    """{pct, charging} o {} si no hay batería."""
    for d in sorted(glob.glob(str(ROOT / "class/power_supply/BAT*"))):
        pct = _num(Path(d) / "capacity")
        st = (_read(Path(d) / "status") or "").lower()
        if pct is not None:
            return {"pct": int(pct), "charging": st not in ("discharging",)}
    return {}


def power_draw_w():
    for p in sorted(glob.glob(str(ROOT / "class/drm/card*/device/hwmon/hwmon*/power1_average")) +
                    sorted(glob.glob(str(ROOT / "class/drm/card*/device/hwmon/hwmon*/power1_input")))):
        v = _num(p)
        if v and v > 0:
            return round(v / 1e6, 1)
    return None


def snapshot() -> dict:
    w, src = tdp()
    b = battery()
    mhz = _num(ROOT / "devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    return {"tdp_w": w, "tdp_src": src, "battery": b, "draw_w": power_draw_w(), "cpu_mhz": round(mhz / 1000) if mhz else None,
            "epp": _read(ROOT / "devices/system/cpu/cpu0/cpufreq/energy_performance_preference"), "t": time.time()}


def describe(s: dict) -> str:
    parts = [f"TDP {s['tdp_w']:g} W ({s['tdp_src']})" if s.get("tdp_w") else "TDP: el equipo no lo expone"]
    b = s.get("battery") or {}
    if b:
        parts.append(f"batería {b['pct']}% {'cargando/enchufado' if b['charging'] else 'descargando'}")
    if s.get("draw_w"):
        parts.append(f"consumo {s['draw_w']:g} W")
    if s.get("cpu_mhz"):
        parts.append(f"CPU {s['cpu_mhz']} MHz")
    if s.get("epp"):
        parts.append(f"perfil {s['epp']}")
    return " · ".join(parts)


def saving(mode: str, s: dict) -> bool:
    """mode: auto | perf | save. En auto: ahorro con TDP ≤ 9 W o con batería baja desenchufado."""
    if mode == "save":
        return True
    if mode == "perf":
        return False
    w = s.get("tdp_w")
    b = s.get("battery") or {}
    return bool((w and w <= SAVE_TDP_W) or (b and not b.get("charging") and b.get("pct", 100) <= SAVE_BATTERY_PCT))
