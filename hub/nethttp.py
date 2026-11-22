"""Descargas HTTP con tolerancia a VPN/redes raras (v2.77), usadas por SteamGridDB y las demás fuentes de arte.
Intenta: normal → solo IPv4 (muchas VPN no sacan el IPv6) → TLS 1.2 (v2.78: algunas redes cortan el saludo TLS 1.3 con «EOF occurred in violation of protocol») → IPv4 + TLS 1.2.
Los errores dicen QUÉ falló (tiempo agotado, DNS, certificado, conexión rechazada…), no solo «URLError»."""
import http.client
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request


def describe(ex) -> str:
    r = getattr(ex, "reason", None) or ex
    s = str(r)
    if isinstance(r, ssl.SSLCertVerificationError):
        return "certificado TLS no válido (¿la VPN o un proxy intercepta HTTPS?)"
    if isinstance(r, ssl.SSLError):
        return f"fallo TLS ({s[:70]})"
    if isinstance(r, socket.gaierror):
        return "el DNS no resuelve el nombre (¿DNS de la VPN?)"
    if isinstance(r, (TimeoutError, socket.timeout)) or "timed out" in s:
        return "tiempo agotado (la conexión no llega: ¿IPv6 sin salida, VPN lenta o sitio bloqueado?)"
    if isinstance(r, ConnectionRefusedError):
        return "conexión rechazada"
    if isinstance(r, ConnectionResetError) or "reset" in s.lower():
        return "la conexión se cortó a mitad (reset)"
    if isinstance(r, OSError) and getattr(r, "errno", None) in (101, 113):
        return "sin ruta hacia el servidor (red o VPN caída)"
    return f"{type(r).__name__}: {s[:90]}"


class _V4Conn(http.client.HTTPSConnection):
    """HTTPS que resuelve y conecta SOLO por IPv4."""

    def connect(self):
        last = None
        for af, st, pr, _, sa in socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM):
            try:
                s = socket.socket(af, st, pr)
                s.settimeout(self.timeout if isinstance(self.timeout, (int, float)) else None)
                s.connect(sa)
                self.sock = s
                break
            except OSError as ex:
                last = ex
        else:
            raise last or OSError("sin direcciones IPv4")
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._tunnel_host or self.host)


class _V4Handler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_V4Conn, req, context=self._context)


def _ctx(tls12):
    c = ssl.create_default_context()
    if tls12:
        c.maximum_version = ssl.TLSVersion.TLSv1_2
    return c


def _once(url, headers, timeout, method, v4, tls12=False):
    req = urllib.request.Request(url, headers=headers, method=method)
    ctx = _ctx(tls12)
    if v4:
        op = urllib.request.build_opener(urllib.request.ProxyHandler(), _V4Handler(context=ctx))
    else:
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    with op.open(req, timeout=timeout) as r:
        return r.read() if method == "GET" else b""


_MODES = ((False, False, "normal"), (True, False, "solo IPv4"), (False, True, "TLS 1.2"), (True, True, "IPv4 + TLS 1.2"))


def get(url, headers=None, timeout=15, tries=4, method="GET") -> bytes:
    """Bytes de la respuesta. HTTPError 4xx (menos 429) se relanza tal cual para que quien llama decida; el resto de fallos → OSError con la causa."""
    hdr = {"User-Agent": "recomp-hub/1", **(headers or {})}
    host = urllib.parse.urlparse(url).netloc
    seen = []
    for i in range(min(tries, len(_MODES))):
        v4, t12, lab = _MODES[i]
        try:
            return _once(url, hdr, timeout, method, v4, t12)
        except urllib.error.HTTPError as ex:
            if 400 <= ex.code < 500 and ex.code != 429:
                raise
            seen.append(f"{lab}: HTTP {ex.code}")
        except Exception as ex:  # noqa: BLE001
            seen.append(f"{lab}: {describe(ex)}")
        if i + 1 < tries:
            time.sleep(1.0)
    raise OSError(f"{host} no responde. " + " · ".join(dict.fromkeys(seen)) + ". Prueba otro servidor de la VPN, o define HTTPS_PROXY")


def diagnose(host="www.steamgriddb.com", path="/api/v2/") -> list:
    """Prueba paso a paso (DNS → TCP 443 IPv4/IPv6 → TLS → HTTP) y devuelve líneas legibles. Nunca lanza."""
    out = []

    def step(label, fn):
        t0 = time.time()
        try:
            r = fn()
            out.append(f"✓ {label}: {r} ({(time.time() - t0) * 1000:.0f} ms)")
            return True
        except Exception as ex:  # noqa: BLE001
            out.append(f"✗ {label}: {describe(ex)} ({(time.time() - t0):.1f} s)")
            return False
    ips4 = ips6 = []
    try:
        ips4 = [a[4][0] for a in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)]
    except OSError:
        pass
    try:
        ips6 = [a[4][0] for a in socket.getaddrinfo(host, 443, socket.AF_INET6, socket.SOCK_STREAM)]
    except OSError:
        pass
    out.append(f"DNS: IPv4 {', '.join(ips4[:2]) or 'ninguna'} · IPv6 {', '.join(ips6[:1]) or 'ninguna'}")

    def tcp(ip, fam):
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.settimeout(8)
        try:
            s.connect((ip, 443))
        finally:
            s.close()
        return ip
    if ips4:
        step("TCP 443 por IPv4", lambda: tcp(ips4[0], socket.AF_INET))
    if ips6:
        step("TCP 443 por IPv6", lambda: tcp(ips6[0], socket.AF_INET6))
    for v4, t12, lab in _MODES:
        def http_(v4=v4, t12=t12):
            try:
                _once(f"https://{host}{path}", {"User-Agent": "recomp-hub/1"}, 12, "GET", v4, t12)
                return "HTTP 200"
            except urllib.error.HTTPError as ex:
                if ex.code in (401, 403, 404):
                    body = ex.read(600).decode("utf-8", "replace").lower()
                    tag = " (Cloudflare bloquea esta IP)" if ("cloudflare" in body or "just a moment" in body) and ex.code == 403 else ""
                    return f"HTTP {ex.code}{tag}: el servidor responde"
                raise
        step("HTTPS " + lab, http_)
    return out
