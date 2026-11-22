"""Contador de peticiones a GitHub y estado de la cuota (cabeceras X-RateLimit-*). Sirve para saber si el token se envía, cuántas llamadas hace Hub
y para parar a tiempo (cortacircuitos) en vez de seguir golpeando cuando ya hay límite. Nunca guarda ni imprime el token."""
import threading
import time

_L = threading.Lock()
S = {"calls": 0, "ok": 0, "notmod": 0, "errors": 0, "auth": 0, "anon": 0, "limit": None, "remaining": None, "reset": None, "resource": "",
     "blocked_until": 0.0, "blocked_why": "", "last": "", "by": {}}


def reset_all():
    with _L:
        S.update(calls=0, ok=0, notmod=0, errors=0, auth=0, anon=0, limit=None, remaining=None, reset=None, resource="", blocked_until=0.0, blocked_why="", last="", by={})


def note(path, code, headers, sent_token):
    """Anota una respuesta. 304 (sin cambios) no gasta cuota cuando hay sesión."""
    h = headers or {}
    with _L:
        S["calls"] += 1
        import re as _re
        k = _re.sub(r"/repos/[^/]+/[^/?]+", "/repos/*", str(path).split("?")[0])
        S["by"][k] = S["by"].get(k, 0) + 1
        S["auth" if sent_token else "anon"] += 1
        if code == 304:
            S["notmod"] += 1
        elif 200 <= code < 300:
            S["ok"] += 1
        else:
            S["errors"] += 1
        for key, hk in (("limit", "X-RateLimit-Limit"), ("remaining", "X-RateLimit-Remaining"), ("reset", "X-RateLimit-Reset")):
            try:
                v = h.get(hk)
                if v is not None:
                    S[key] = int(v)
            except (ValueError, AttributeError):
                pass
        S["resource"] = (h.get("X-RateLimit-Resource") if hasattr(h, "get") else "") or S["resource"]
        S["last"] = f"{code} {path}"


def kind(code, headers, body=""):
    """Tipo de rechazo: 'primario' (cuota agotada), 'secundario' (demasiado rápido / abuso), 'sin-sesion', 'otro' o '' si no es un límite."""
    if code not in (403, 429):
        return ""
    h = headers or {}
    b = (body or "").lower()
    if "secondary" in b or "abuse" in b or h.get("Retry-After"):
        return "secundario"
    if h.get("X-RateLimit-Remaining") == "0" or "rate limit" in b:
        return "primario"
    return "otro"


def block(seconds, why):
    with _L:
        S["blocked_until"] = max(S["blocked_until"], time.time() + max(1, seconds))
        S["blocked_why"] = why


def blocked():
    """Segundos que faltan para poder volver a llamar (0 si no hay bloqueo)."""
    with _L:
        return max(0, int(S["blocked_until"] - time.time()))


def block_from(code, headers, body=""):
    k = kind(code, headers, body)
    if not k:
        return k
    h = headers or {}
    try:
        wait = int(h.get("Retry-After") or 0)
    except ValueError:
        wait = 0
    if not wait:
        try:
            wait = max(60, int(h.get("X-RateLimit-Reset") or 0) - int(time.time())) if k == "primario" else 60
        except ValueError:
            wait = 60
    block(min(wait, 3600), k)
    return k


def summary():
    with _L:
        s = dict(S)
    rem = f"{s['remaining']}/{s['limit']}" if s["limit"] is not None else "?"
    mins = f", se restablece en {max(0, int((s['reset'] - time.time()) / 60))} min" if s["reset"] else ""
    return (f"Hub ha hecho {s['calls']} llamadas ({s['ok']} nuevas, {s['notmod']} sin cambios, {s['errors']} con error) · "
            f"con sesión {s['auth']}, sin sesión {s['anon']} · cuota {rem}{mins}"
            + (" · por tipo: " + ", ".join(f"{k} {v}" for k, v in sorted(s["by"].items(), key=lambda x: -x[1])[:4]) if s["by"] else ""))
