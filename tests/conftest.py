"""Fixtures comunes. El entorno se aísla ANTES de importar Hub: nada toca tu ~/Games ni tu daemon real
(salvo los tests marcados `live`, que se activan a propósito con CATALOG_LIVE=1)."""
import os
import signal
import socket
import sys
import tempfile
import time
import platform
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _find_hub_src():
    cands = [os.environ.get("HUB_SRC"), str(HERE.parent / "src"), str(HERE.parent), str(HERE.parent / "recomp-hub"), str(Path.home() / "Games" / "recomp-hub")]   # v3.11: el código junto a las pruebas primero (repositorio)
    for c in cands:
        if c and (Path(c) / "hub" / "catalogservice.py").is_file():
            return Path(c)
    raise RuntimeError("No encuentro el código de Hub (carpeta con hub/catalogservice.py). Exporta HUB_SRC=/ruta/a/recomp-hub")


HUB_SRC = _find_hub_src()
SESSION_TMP = Path(tempfile.mkdtemp(prefix="hubtests-"))
for sub in ("data", "l", "g", "svc", "home"):
    (SESSION_TMP / sub).mkdir()
os.environ.update(HUB_DATA=str(SESSION_TMP / "data"), LAUNCHER_DIR=str(SESSION_TMP / "l"), HUB_GAMES=str(SESSION_TMP / "g"),
                  HUB_CATALOG_DIR=str(SESSION_TMP / "nosvc"), HUB_CATALOG_URL="http://127.0.0.1:1/rpc",
                  HUB_CATALOG_TOKEN_FILE=str(SESSION_TMP / "home" / "token"), HUB_CATALOG_LOG=str(SESSION_TMP / "home" / "service.log"),
                  SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", HUB_NO_PAD="1", HUB_NO_FONT_DL="1", HUB_NO_WATCH="1",
                  FORGEINATOR_SOCK=f"/tmp/fgt-{os.getpid()}.sock", QAM_RAIL_SOCK=f"/tmp/qrt-{os.getpid()}.sock",   # v3.23: nunca los sockets reales
                  FORGEINATOR_NO_SYSTEMD="1")
# ── casa falsa: las pruebas no leen ni escriben NADA de tu carpeta personal (ROMs, Descargas, Steam, ~/.config/autostart…) ──
# Las rutas reales que necesitan las pruebas «live» se calculan aquí, ANTES de cambiar HOME.
REAL_HOME = Path.home()
REAL = dict(URL=os.environ.get("CATALOG_LIVE_URL", "http://localhost:8765/rpc"),
            TOKEN_FILE=Path(os.environ.get("CATALOG_LIVE_TOKEN_FILE", "~/.cache/catalog-service/token")).expanduser(),
            LOG_FILE=Path("~/.cache/catalog-service/service.log").expanduser(),
            SERVICE_DIR=Path("~/Games/local-catalog-service").expanduser())
FAKE_HOME = SESSION_TMP / "home"
FAKE_ROMS = FAKE_HOME / "Nextcloud" / "Emulation" / "roms"
# biblioteca de prueba fija (igual en tu Ally y aquí): 150 juegos en 3 plataformas, más de los 60 que caben → sale «MOSTRAR MÁS»
for _plat, _ext, _n in (("ps2", ".iso", 70), ("psx", ".chd", 50), ("snes", ".sfc", 30)):
    (FAKE_ROMS / _plat).mkdir(parents=True, exist_ok=True)
    for _i in range(_n):
        (FAKE_ROMS / _plat / f"Juego de prueba {_plat} {_i:03d} (USA){_ext}").write_bytes(b"x")
for _d in ("Downloads", ".config", ".local/share", ".cache"):
    (FAKE_HOME / _d).mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTHONUSERBASE", str(REAL_HOME / ".local"))      # los paquetes «pip --user» siguen viéndose en subprocesos
os.environ.update(HOME=str(FAKE_HOME), XDG_CONFIG_HOME=str(FAKE_HOME / ".config"), XDG_DATA_HOME=str(FAKE_HOME / ".local/share"),
                  XDG_CACHE_HOME=str(FAKE_HOME / ".cache"))
os.environ.setdefault("HUB_WINDOW", "1280x800")
os.environ["HUB_SMOOTH_SCROLL"] = "0"   # las pruebas antiguas miran la posición justo después de pulsar; las nuevas lo activan (test_v201, navegación)
os.environ["HUB_SYSFS"] = str(SESSION_TMP / "sysfs")   # el TDP/batería reales no cambian el comportamiento en las pruebas (test_calidad los anota aparte)
for _k in ("SteamGameId", "SteamAppId", "GAMESCOPE_WAYLAND_DISPLAY"):   # desde Modo Juego: Hub no debe creer que está dentro de Steam        # si las pruebas se lanzan desde Steam, JUGAR no debe pedirle nada a Steam
    os.environ.pop(_k, None)
sys.path.insert(0, str(HUB_SRC))

from hub import catalogservice as _cs  # noqa: E402

from fakes.daemon import FakeDaemon  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture
def tmp_home(tmp_path):
    return tmp_path


@pytest.fixture
def cs(monkeypatch, tmp_path):
    """Módulo catalogservice apuntando a rutas temporales y a un puerto cerrado."""
    monkeypatch.setattr(_cs, "URL", f"http://127.0.0.1:{free_port()}/rpc")
    monkeypatch.setattr(_cs, "TOKEN_FILE", tmp_path / "token")
    monkeypatch.setattr(_cs, "LOG_FILE", tmp_path / "service.log")
    monkeypatch.setattr(_cs, "SERVICE_DIR", tmp_path / "svc")
    return _cs


@pytest.fixture
def daemon(cs, tmp_path):
    d = FakeDaemon("SECRETO").start()
    cs.URL = d.url
    cs.TOKEN_FILE.write_text("SECRETO")
    yield d
    d.stop()


@pytest.fixture
def real_cs(monkeypatch):
    """Cliente apuntando al daemon REAL (para los tests de contrato)."""
    monkeypatch.setattr(_cs, "URL", REAL["URL"])
    monkeypatch.setattr(_cs, "TOKEN_FILE", REAL["TOKEN_FILE"])
    monkeypatch.setattr(_cs, "LOG_FILE", REAL["LOG_FILE"])
    monkeypatch.setattr(_cs, "SERVICE_DIR", REAL["SERVICE_DIR"])
    return _cs


@pytest.fixture
def spawned():
    """Recoge PIDs de daemons lanzados por el autoarranque para matarlos al acabar."""
    pids = []
    yield pids
    for p in pids:
        try:
            os.kill(p, signal.SIGTERM)
        except OSError:
            pass


def wait_for(pred, timeout=10.0, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return pred()


# ── informe en Markdown (para pegarlo en el chat) ────────────────────────────
_results = []
_extra = []          # secciones de texto que los tests quieren ver en el informe (p. ej. «cómo se ve» cada pantalla)


def report_section(title, body):
    _extra.append((title, body))


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        msg = ""
        if report.outcome == "failed":
            msg = (report.longreprtext or "").strip().splitlines()
            msg = next((ln for ln in reversed(msg) if ln.startswith("E ")), msg[-1] if msg else "")
        elif report.outcome == "skipped":
            msg = getattr(report, "wasxfail", "") or (report.longrepr[2] if isinstance(report.longrepr, tuple) else "")
            if hasattr(report, "wasxfail") or "[conformidad" in str(msg):
                _results.append((report.nodeid, "xfail", msg))
                return
        _results.append((report.nodeid, report.outcome, msg))


def pytest_sessionfinish(session, exitstatus):
    outdir = Path(os.environ.get("REPORT_DIR") or HERE / "reports")
    outdir.mkdir(parents=True, exist_ok=True)
    n = {k: sum(1 for r in _results if r[1] == k) for k in ("passed", "failed", "skipped", "xfail")}
    lines = ["# Informe de pruebas — Recomp Hub / catálogo", "",
             f"- Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}", f"- Python: {platform.python_version()} · Hub: {HUB_SRC}",
             f"- Resultado: **{n['passed']} OK · {n['failed']} FALLAN · {n['xfail']} desvíos menores · {n['skipped']} omitidos**", ""]
    bad = [r for r in _results if r[1] == "failed"]
    if bad:
        lines += ["## Fallos", ""] + [f"- `{r[0]}` → {r[2]}" for r in bad] + [""]
    xf = [r for r in _results if r[1] == "xfail"]
    if xf:
        lines += ["## Desvíos menores del estándar (no bloquean)", ""] + [f"- `{r[0].split('::')[-1]}` → {r[2]}" for r in xf] + [""]
    sk = [r for r in _results if r[1] == "skipped"]
    if sk:
        lines += ["## Omitidos", ""] + [f"- `{r[0]}` → {r[2]}" for r in sk] + [""]
    live = [r for r in _results if "contract_live" in r[0]]
    if live:
        lines += ["## Contrato contra tu daemon real", ""] + [f"- {'OK  ' if r[1] == 'passed' else r[1].upper()} `{r[0].split('::')[-1]}` {r[2]}" for r in live] + [""]
    for title, body in _extra:
        lines += [f"## {title}", "", body, ""]
    (outdir / "informe.md").write_text("\n".join(lines), encoding="utf-8")
    (outdir / "detalle.md").write_text("\n".join(lines), encoding="utf-8")       # bin/hub-tests lo incorpora a su informe (omitidos, «Cómo se ve»…)


def shot(ui, name):
    """Guarda una captura en reports/capturas/ (junto al informe); nunca falla el test por no poder escribirla."""
    import pygame
    d = Path(os.environ.get("REPORT_DIR") or (Path(__file__).parent / "reports")) / "capturas"
    try:
        d.mkdir(parents=True, exist_ok=True)
        pygame.image.save(ui.screen, str(d / name))
    except Exception:  # noqa: BLE001
        pass
