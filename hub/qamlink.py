"""v3.17 · Enlace con QAM Rail: atajos de Steam automáticos para los juegos.

Steam solo reconoce como juego (barra lateral, perfil de TDP por juego, tiempo de juego, capturas) lo que lanza él mismo con un appid.
Crear un atajo escribiendo shortcuts.vdf obliga a cerrar Steam; QAM Rail, que vive dentro de Steam, puede crearlo en caliente
(SteamClient.Apps.AddShortcut) y lanzarlo (RunGame). Este módulo le pide eso por un socket local.

Protocolo v1 (documentado en el proyecto: claude/forgeinator-qam-atajos.md):
  socket UNIX  $XDG_RUNTIME_DIR/qam-rail.sock  (QAM_RAIL_SOCK lo sustituye; pruebas)
  una línea JSON de petición → una línea JSON de respuesta → se cierra
  {"v":1,"op":"ping","request_id":…}                         → {"v":1,"request_id":…,"ok":true,"version":"0.54.0","ops":[…]}
  {"v":1,"op":"steam.run_shortcut","request_id":…,"from":"forgeinator","game":{…}}
                                                             → {"v":1,"request_id":…,"ok":true,"appid":N,"created":bool,"launched":true}
                                                             → {"v":1,"request_id":…,"ok":false,"error":"código","detail":"…"}
Solo biblioteca estándar. Nada se queda escuchando: el Hub conecta cuando el usuario pulsa JUGAR."""
import json
import os
import socket
import uuid
from pathlib import Path

V = 1
OP_PING = "ping"
OP_RUN = "steam.run_shortcut"
ART_KEYS = ("portrait", "banner", "hero", "logo", "icon")      # nombres del arte del Hub (art/<clave>.png)


def socket_path() -> Path:
    if os.environ.get("QAM_RAIL_SOCK"):
        return Path(os.environ["QAM_RAIL_SOCK"])
    run = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(run) / "qam-rail.sock"


def _call(msg: dict, timeout: float) -> dict:
    p = socket_path()
    if not p.exists():
        return {"ok": False, "error": "sin_qam", "detail": f"no está {p} (QAM Rail no instalado, sin enlace o Decky parado)"}
    msg = {"v": V, "request_id": uuid.uuid4().hex, **msg}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(str(p))
            s.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode())
            buf = b""
            while b"\n" not in buf and len(buf) < 65536:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
    except socket.timeout:
        return {"ok": False, "error": "tiempo", "detail": f"QAM Rail no respondió en {timeout:.0f} s"}
    except OSError as ex:
        return {"ok": False, "error": "conexion", "detail": f"{type(ex).__name__}: {ex}"}
    try:
        r = json.loads(buf.split(b"\n", 1)[0].decode() or "{}")
    except ValueError:
        return {"ok": False, "error": "respuesta", "detail": "respuesta ilegible de QAM Rail"}
    if not isinstance(r, dict):
        return {"ok": False, "error": "respuesta", "detail": "respuesta ilegible de QAM Rail"}
    if r.get("request_id") not in (None, msg["request_id"]):
        return {"ok": False, "error": "respuesta", "detail": "la respuesta no es de esta petición"}
    return r


def ping(timeout: float = 1.0) -> dict:
    """¿Hay un QAM Rail que sepa crear y lanzar atajos? {'ok', 'version', 'ops'}."""
    r = _call({"op": OP_PING}, timeout)
    if r.get("ok") and OP_RUN not in (r.get("ops") or []):
        return {"ok": False, "error": "sin_op", "detail": f"QAM Rail {r.get('version', '?')} no sabe crear atajos (falta {OP_RUN})"}
    return r


def game_request(lid: str, name: str, exe: str, start_dir: str = "", launch_options: str = "", art: dict = None, appid=None,
                 run_delay_ms: int = 0) -> dict:
    """La parte «game» de la petición. key es estable (el mismo juego siempre da el mismo atajo). run_delay_ms: QAM Rail espera eso
    antes de RunGame (si Hub es a su vez un juego de Steam, Steam no abre otro hasta que Hub se cierra)."""
    g = {"key": f"forgeinator:{lid}", "name": name, "exe": exe, "start_dir": start_dir or str(Path(exe).parent),
         "launch_options": launch_options, "art": {k: str(v) for k, v in (art or {}).items() if k in ART_KEYS and v and Path(v).is_file()},
         "run_delay_ms": int(run_delay_ms)}
    if appid:
        g["appid"] = int(appid)
    return g


def run_shortcut(game: dict, timeout: float = 15.0) -> dict:
    """Pide a QAM Rail que cree (si falta) el atajo del juego con su arte y lo lance."""
    r = _call({"op": OP_RUN, "from": "forgeinator", "game": game}, timeout)
    if r.get("ok") and not isinstance(r.get("appid"), int):
        return {"ok": False, "error": "respuesta", "detail": "QAM Rail no devolvió el appid"}
    return r


# ---------------------------------------------------------------- appids conocidos (biblioteca común)
def _store(data_dir: Path) -> Path:
    return Path(data_dir) / "steam-appids.json"


def known_appids(data_dir: Path) -> dict:
    try:
        d = json.loads(_store(data_dir).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def remember_appid(data_dir: Path, lid: str, appid: int) -> None:
    d = known_appids(data_dir)
    if d.get(lid) == appid:
        return
    d[lid] = int(appid)
    f = _store(data_dir)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, f)
