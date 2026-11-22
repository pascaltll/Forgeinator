"""Pedir un TDP a «Panel de Control» (plugin de Decky de Hooandee, GPL-3.0) desde fuera de Steam, para la prueba de rendimiento por TDP.

No copia nada de Panel de Control: llama a sus métodos ya existentes (get_tdp_state, set_tdp_watts, get_power_draw) igual que QAM Rail,
desde el contexto JavaScript compartido de Steam (SharedJSContext), donde viven los plugins de Decky. Hub entra por el depurador remoto
de CEF que Decky deja abierto en 127.0.0.1:8080 (el mismo que usa Panel de Control para leer Steam). Solo local; nada sale del equipo.
Cliente WebSocket mínimo (RFC 6455) para no depender de paquetes externos."""
import base64
import json
import os
import socket
import struct
import urllib.request

CDP = os.environ.get("HUB_CDP", "http://127.0.0.1:8080")
PANEL = "Panel de Control"


class TdpError(Exception):
    pass


def _targets():
    try:
        with urllib.request.urlopen(CDP + "/json/list", timeout=3) as r:
            return json.loads(r.read().decode())
    except (OSError, ValueError) as ex:
        raise TdpError(f"no responde el depurador de Steam en {CDP} (¿Decky instalado y Steam abierto?): {ex}") from None


def _shared_ws() -> str:
    ts = _targets()
    t = next((t for t in ts if t.get("title") == "SharedJSContext"), None) or \
        next((t for t in ts if "SharedJSContext" in str(t.get("title", "")) or "steamloopback" in str(t.get("url", ""))), None)
    if not t or not t.get("webSocketDebuggerUrl"):
        raise TdpError("no encuentro el contexto de Steam donde viven los plugins de Decky (SharedJSContext)")
    return t["webSocketDebuggerUrl"]


class _WS:
    def __init__(self, url, timeout=15):
        assert url.startswith("ws://")
        hostport, _, path = url[5:].partition("/")
        host, _, port = hostport.partition(":")
        self.s = socket.create_connection((host, int(port or 80)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.s.recv(4096)
            if not chunk:
                raise TdpError("el depurador cerró la conexión")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise TdpError("el depurador rechazó la conexión WebSocket")
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _recv(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise TdpError("conexión cerrada")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text: str, opcode=1):
        data = text.encode() if isinstance(text, str) else text
        mask = os.urandom(4)
        n = len(data)
        hdr = bytes([0x80 | opcode]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                                         else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self) -> str:
        msg = b""
        while True:
            b0, b1 = self._recv(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv(8))[0]
            mask = self._recv(4) if b1 & 0x80 else None
            data = self._recv(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 9:
                self.send(data, 10)
                continue
            if op == 8:
                raise TdpError("conexión cerrada por Steam")
            msg += data
            if b0 & 0x80:
                return msg.decode("utf-8", "replace")

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


# Igual que QAM Rail (panelBridge.ts): se prueban las vías conocidas de Decky para llamar a un plugin.
_JS = r"""(async () => {
  const P = %(panel)s, M = %(method)s, LIST = %(list)s, OBJ = %(obj)s;
  const unwrap = (v) => (v && typeof v === "object" && "success" in v && "result" in v) ? (v.success === false ? (() => { throw new Error(String(v.result)); })() : v.result) : v;
  const ways = [
    () => window.DeckyBackend.call("loader/call_plugin_method", P, M, ...LIST),
    () => window.DeckyBackend.call("loader/call_plugin_method", P, M, OBJ),
    () => window.DeckyPluginLoader.callPluginMethod(P, M, OBJ),
  ];
  let err = "";
  for (const w of ways) { try { return JSON.stringify({ok: true, v: unwrap(await w())}); } catch (e) { err += String(e) + " | "; } }
  return JSON.stringify({ok: false, err});
})()"""


def call(method: str, names=(), values=(), timeout=20):
    """Llama a un método del backend de Panel de Control y devuelve su resultado."""
    ws = _WS(_shared_ws(), timeout)
    try:
        js = _JS % {"panel": json.dumps(PANEL), "method": json.dumps(method), "list": json.dumps(list(values)),
                    "obj": json.dumps(dict(zip(names, values)))}
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js, "awaitPromise": True, "returnByValue": True}}))
        while True:
            r = json.loads(ws.recv())
            if r.get("id") == 1:
                break
    finally:
        ws.close()
    res = (r.get("result") or {}).get("result") or {}
    if "exceptionDetails" in (r.get("result") or {}):
        raise TdpError("error de JavaScript en Steam: " + str(r["result"]["exceptionDetails"].get("text", ""))[:200])
    try:
        out = json.loads(res.get("value") or "{}")
    except ValueError:
        raise TdpError("respuesta rara de Steam") from None
    if not out.get("ok"):
        raise TdpError("Panel de Control no respondió: " + str(out.get("err", ""))[:300])
    return out.get("v")


def state() -> dict:
    return call("get_tdp_state") or {}


def draw() -> dict:
    return call("get_power_draw") or {}


def set_watts(w: int) -> dict:
    """TDP del perfil de Hub (scope «game» con su propio contexto). Panel aplica el perfil del contexto actual: si Hub tiene perfil propio
    (ns:hub, follows_global=False), escribir el global no cambia nada. Devuelve {requested_w, applied_w, ok, detail}."""
    st = state()
    ctx = st.get("appid")
    return call("set_tdp_watts", ["watts", "scope", "appid", "context_appid"], [int(round(w)), "game", ctx, ctx]) or {}


def levels(lo: float, hi: float, quick=False) -> list:
    """Niveles con peso en los bajos (como la prueba de fluidez de QAM Rail): mín, mín+2, mín+4, medio y máx."""
    lo, hi = int(-(-lo // 1)), int(hi // 1)
    if hi <= lo:
        return [lo]
    raw = [lo, (lo + hi) // 2, hi] if quick else [lo, lo + 2, lo + 4, round((lo + hi) / 2), hi]
    return sorted({min(hi, max(lo, w)) for w in raw})
