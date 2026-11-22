"""Cliente JSON-RPC 2.0 del daemon local de catálogo (http://localhost:8765/rpc). Solo biblioteca estándar.
Uso en terminal:  python3 hub/catalogservice.py health | search "texto" [sistema] | variants FUENTE ITEM_ID"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = os.environ.get("HUB_CATALOG_URL", "http://localhost:8765/rpc")
TOKEN_FILE = Path(os.environ.get("HUB_CATALOG_TOKEN_FILE", "~/.cache/catalog-service/token")).expanduser()
LOG_FILE = Path(os.environ.get("HUB_CATALOG_LOG", "~/.cache/catalog-service/service.log")).expanduser()
SERVICE_DIR = Path(os.environ.get("HUB_CATALOG_DIR", "~/Games/local-catalog-service")).expanduser()


class CatalogError(Exception):
    pass


class TransportError(CatalogError):
    """Puerto cerrado, tiempo agotado o respuesta que no es JSON-RPC."""


class TokenError(CatalogError):
    """No hay token, o el daemon lo rechaza (401/403)."""


class TokenMissing(TokenError):
    """El archivo del token no existe o está vacío (suele pasar si el daemon aún no arrancó: él lo crea)."""


class RpcError(CatalogError):
    def __init__(self, code, message, data=None):
        super().__init__(f"[{code}] {message}")
        self.code, self.message, self.data = code, message, data


class MethodNotFound(RpcError):
    pass


class InvalidParams(RpcError):
    pass


class ServiceError(RpcError):
    """Código propio del daemon (o uno que no conocemos): se conserva .code y .message tal cual."""


def token() -> str:
    try:
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError as ex:
        raise TokenMissing(f"no puedo leer el token ({TOKEN_FILE}): {ex}") from None
    if not t:
        raise TokenMissing(f"el archivo del token está vacío ({TOKEN_FILE})")
    return t


def _hostport():
    from urllib.parse import urlparse
    u = urlparse(URL)
    return u.hostname or "localhost", u.port or 80


def port_open(timeout=0.3) -> bool:
    try:
        with socket.create_connection(_hostport(), timeout=timeout):
            return True
    except OSError:
        return False


def _log_tail(n=6) -> str:
    try:
        return " | ".join(LOG_FILE.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-n:])
    except OSError:
        return ""


def ensure_running(wait=15.0):
    """Si el puerto no responde, arranca el daemon (sesión propia, sin stdin, log a archivo) y espera hasta `wait` s."""
    if port_open():
        try:
            token()
            return
        except TokenMissing:
            pass   # algo escucha pero no hay token: seguimos esperando a que aparezca
    svc = SERVICE_DIR / "service.py"
    if not svc.exists():
        raise TransportError(f"el servicio no responde en {URL} y no existe {svc}")
    venv = SERVICE_DIR / ".venv" / "bin" / "python"
    py = str(venv) if venv.exists() else (shutil.which("python3") or sys.executable)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not port_open():   # si ya escucha alguien (solo faltaba el token) no se lanza otro daemon encima
        with open(LOG_FILE, "ab") as lg:
            subprocess.Popen([py, str(svc)], stdin=subprocess.DEVNULL, stdout=lg, stderr=lg, start_new_session=True, cwd=str(SERVICE_DIR))
    end = time.time() + wait
    while time.time() < end:
        if port_open():
            try:
                token()          # el daemon puede crear el token justo después de abrir el puerto
                return
            except TokenMissing:
                pass
        time.sleep(0.2)
    if port_open():
        raise TokenMissing(f"el servicio escucha pero no aparece el token ({TOKEN_FILE}) tras {wait:.0f} s. Log: {_log_tail() or LOG_FILE}")
    raise TransportError(f"arranqué el servicio pero no quedó listo (puerto/token) en {wait:.0f} s. Log: {_log_tail() or LOG_FILE}")


_id = [0]


def _post(method, params, timeout):
    _id[0] += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _id[0], "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={"X-Catalog-Token": token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as ex:
        if ex.code in (401, 403):
            raise TokenError(f"el servicio rechazó el token (HTTP {ex.code}); ¿cambió {TOKEN_FILE}?") from None
        try:
            raw = ex.read()          # un error JSON-RPC puede venir con HTTP 4xx/5xx
            json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, OSError):
            raise TransportError(f"HTTP {ex.code} del servicio") from None
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as ex:
        raise TransportError(f"{type(ex).__name__}: {getattr(ex, 'reason', ex)}") from None
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise TransportError("el servicio respondió algo que no es JSON: " + raw.decode("utf-8", "replace")[:120]) from None


def call(method, params=None, timeout=10, start=True):
    """Llama a un método. Si el servicio no responde (y start=True), intenta arrancarlo y reintenta una vez."""
    try:
        resp = _post(method, params, timeout)
    except (TransportError, TokenMissing):
        if not start:
            raise
        try:
            ensure_running()
        except (OSError, subprocess.SubprocessError) as ex:   # permiso / intérprete inexistente: que no mate el hilo llamante
            raise TransportError(f"no pude arrancar el servicio: {type(ex).__name__}: {ex}") from None
        resp = _post(method, params, timeout)
    if not isinstance(resp, dict):
        raise TransportError("respuesta JSON-RPC inválida")
    err = resp.get("error")
    if err:
        code = err.get("code") if isinstance(err, dict) else None
        msg = str(err.get("message", "")) if isinstance(err, dict) else str(err)
        data = err.get("data") if isinstance(err, dict) else None
        cls = {-32601: MethodNotFound, -32602: InvalidParams}.get(code, ServiceError)
        raise cls(code, msg, data)
    if "result" not in resp:
        raise TransportError("respuesta sin result ni error")
    return resp["result"]


def autostart():
    """Para llamar al iniciar Hub: deja el daemon corriendo si está instalado. Devuelve (ok, mensaje); nunca lanza."""
    if not (SERVICE_DIR / "service.py").exists():
        return False, f"no hay {SERVICE_DIR / 'service.py'}: el servicio de catálogo no está instalado aquí"
    try:
        ensure_running()
        return True, "servicio de catálogo listo"
    except CatalogError as ex:
        return False, str(ex)
    except (OSError, subprocess.SubprocessError) as ex:
        return False, f"no pude arrancar el servicio: {type(ex).__name__}: {ex}"


def health(start=True):
    return call("health", {}, start=start)


def search(query, system=None, requires=None):
    p = {"query": query}
    if system:
        p["system"] = system
    if requires:
        p["requires"] = requires
    return call("search", p)


def variants(source, item_id, requires=None):
    p = {"source": source, "item_id": item_id}
    if requires:
        p["requires"] = requires
    return call("variants", p)


def download(source, variant_id, dest_dir):
    return call("download", {"source": source, "variant_id": variant_id, "dest_dir": str(dest_dir)})


def job_status(job_id):
    return call("job_status", {"job_id": job_id}, timeout=5)


def job_cancel(job_id):
    return call("job_cancel", {"job_id": job_id}, timeout=5)


def _main(argv):
    if not argv or argv[0] not in ("health", "search", "variants"):
        print(__doc__)
        return 2
    try:
        if argv[0] == "health":
            out = health()
        elif argv[0] == "search" and len(argv) >= 2:
            out = search(argv[1], argv[2] if len(argv) > 2 else None)
        elif argv[0] == "variants" and len(argv) >= 3:
            out = variants(argv[1], argv[2])
        else:
            print(__doc__)
            return 2
    except CatalogError as ex:
        print(f"{type(ex).__name__}: {ex}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
