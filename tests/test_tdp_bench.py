"""Prueba de rendimiento por TDP (como la de fluidez de QAM Rail): Hub le pide cada TDP a «Panel de Control» (vía Decky), espera a que
se aplique y mide cada pantalla, la velocidad de CPU de un hilo y el consumo. Al terminar deja el TDP que había.
Solo se ejecuta si la pides:   HUB_TDP_BENCH=auto bin/hub-tests     (o HUB_TDP_BENCH=7,10,13 para elegir los vatios)."""
import hashlib
import os
import statistics
import time

import pytest

from conftest import report_section
from test_calidad import _energia_real, _guardar_y_comparar, medir_navegacion, medir_pantallas
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")
PEDIDO = os.environ.get("HUB_TDP_BENCH", "")


def _cpu_score(seg=1.0):
    """Hashes SHA-256 por segundo en un hilo (Hub dibuja en uno)."""
    end, n, b = time.perf_counter() + seg, 0, b"x" * 64
    while time.perf_counter() < end:
        for _ in range(2000):
            b = hashlib.sha256(b).digest()
        n += 2000
    return n / seg


def _multi_score(seg=1.5):
    """Hashes/s con todos los núcleos a la vez (como la prueba de QAM Rail): aquí sí se nota el límite de potencia."""
    import subprocess
    import sys
    code = ("import hashlib,sys,time\nend=time.perf_counter()+float(sys.argv[1]);n=0;b=b'x'*64\n"
            "while time.perf_counter()<end:\n    for _ in range(2000): b=hashlib.sha256(b).digest()\n    n+=2000\nprint(n)\n")
    ps = [subprocess.Popen([sys.executable, "-c", code, str(seg)], stdout=subprocess.PIPE, text=True) for _ in range(os.cpu_count() or 4)]
    return sum(int((p.communicate()[0] or "0").strip() or 0) for p in ps) / seg


def _aviso(txt):
    try:
        sys_out = __import__("sys").__stderr__
        sys_out.write(txt + "\n")
        sys_out.flush()
    except OSError:
        pass


@pytest.mark.skipif(not PEDIDO, reason="activa con HUB_TDP_BENCH=auto (o 7,10,13): cambia el TDP de verdad mediante Panel de Control")
def test_rendimiento_por_tdp(ui):
    from hub import power, tdpctl
    st = tdpctl.state()
    if not st.get("supported", True) or st.get("tdp_control_enabled") is False:
        pytest.skip(f"Panel de Control no controla el TDP ahora: {st}")
    original = st.get("watts") or st.get("global_watts")       # el perfil de Hub (ns:hub), que es el que Panel aplica dentro de Hub
    lim = st.get("limits") or {}
    if PEDIDO == "auto":
        niveles = tdpctl.levels(lim.get("min") or 7, (lim.get("max_ac") if st.get("on_ac") else lim.get("max")) or lim.get("max") or 15)
    else:
        niveles = sorted({int(x) for x in PEDIDO.replace(" ", "").split(",") if x})
    ui.set_look(theme="prototipo", fx="glass")
    filas, todo, nav, notas, sin_efecto = [], [], [], [], []
    _aviso(f"\n*** PRUEBA POR TDP: no toques el Ally ni lo desenchufes durante ~{len(niveles) * 25} s (niveles {niveles} W) ***")
    for i in (3, 2, 1):
        _aviso(f"    empieza en {i}…")
        time.sleep(1)
    try:
        for w in niveles:
            _aviso(f"    {w} W…")
            r = tdpctl.set_watts(w)
            time.sleep(4.5)                                      # que el firmware aplique el límite (lo mismo espera QAM Rail)
            try:
                dr = tdpctl.draw()
            except Exception as ex:  # noqa: BLE001
                dr = {"error": str(ex)}
            notas.append(f"- {w} W → Panel respondió ok={r.get('ok')} aplicado={r.get('applied_w')} detalle={r.get('detail')!r} · "
                         f"get_power_draw: aplicado={dr.get('applied')} consumo={dr.get('watts')} enchufado={dr.get('on_ac')}")
            en = _energia_real()
            consumo = []
            t0 = time.time()
            crudo = medir_pantallas(ui)
            consumo.append(en.get("draw_w"))
            cpu = statistics.median(_cpu_score(0.5) for _ in range(3))
            multi = _multi_score()
            ms, fr = medir_navegacion(ui)
            nav.append((w, statistics.median([x for xs in ms.values() for x in xs]), max(max(v) for v in ms.values())))
            en2 = _energia_real()
            consumo.append(en2.get("draw_w"))
            ap = en2.get("tdp_w") or r.get("applied_w")
            if ap is None or abs(float(ap) - w) > 1:                 # el límite que lee el firmware no es el pedido: no vale esta medición
                sin_efecto.append((w, ap))
            todo.append((w, ap, crudo, cpu, [c for c in consumo if c]))
            _guardar_y_comparar("prototipo", crudo, dict(en2, tdp_w=ap or w))
            peor = max(crudo, key=lambda t: t[2])
            filas.append(f"| {w} W | {ap if ap is not None else '?'} | {peor[0]} {peor[2]:.1f} | {statistics.median(t[2] for t in crudo):.1f} | "
                         f"{cpu / 1e6:.2f} M/s | {multi / 1e6:.1f} M/s | {(sum(c for c in consumo if c) / max(1, len([c for c in consumo if c]))) if any(consumo) else '?'} | "
                         f"{time.time() - t0:.0f} s |")
    finally:
        if original:
            try:
                tdpctl.set_watts(original)
            except Exception as ex:  # noqa: BLE001
                report_section("Rendimiento por TDP · AVISO", f"No pude devolver el TDP a {original} W: {ex}. Ponlo a mano en Panel de Control.")
    report_section("Rendimiento por TDP (Panel de Control)",
                   f"Niveles: {niveles} · TDP al empezar: {original} W (restaurado al terminar).\n\n"
                   "| pedido | aplicado (sysfs) | pantalla más lenta (p95 ms) | p95 mediano | CPU 1 hilo | CPU todos los núcleos | consumo W | duración |\n"
                   "|---|---|---|---|---|---|---|---|\n" + "\n".join(filas) +
                   "\n\nNavegación con la cruceta (reacción por pulsación): " + " · ".join(f"{w} W: mediana {m:.1f} ms, peor {p:.0f} ms" for w, m, p in nav) +
                   "\n\nLo que dijo Panel de Control en cada nivel:\n" + "\n".join(notas) +
                   "\n\nHub escribe su propio perfil de Panel (ns:hub), que es el que Panel aplica mientras Hub está delante; el global no lo cambia. "
                   "Si «aplicado (sysfs)» no coincide con lo pedido, la prueba falla: esa fila no mide ese TDP."
                   "\nPresupuesto: 22 ms para 45 fps; en modo ahorro (TDP ≤ 9 W) Hub apunta a 30 fps (33 ms).")
    assert not sin_efecto, f"el límite del firmware no sigue lo pedido (pedido, leído): {sin_efecto}"
    assert all(max(t[2] for t in c) < 250 for _, _, c, _, _ in todo), "alguna pantalla tarda más de 250 ms por fotograma"


def test_niveles_con_peso_en_los_bajos():
    from hub import tdpctl
    assert tdpctl.levels(5, 30) == [5, 7, 9, 18, 30]
    assert tdpctl.levels(7, 15, quick=True) == [7, 11, 15]
    assert tdpctl.levels(9, 9) == [9]


def test_cliente_cdp_contra_un_steam_falso(monkeypatch):
    """Sin Steam real: un servidor local imita el depurador de CEF (/json/list + WebSocket + Runtime.evaluate) y Panel de Control."""
    import base64
    import hashlib as hl
    import json
    import socketserver
    import struct
    import threading
    from hub import tdpctl
    calls = []

    class H(socketserver.BaseRequestHandler):
        def handle(self):
            s = self.request
            req = b""
            while b"\r\n\r\n" not in req:
                req += s.recv(4096)
            line = req.split(b"\r\n")[0].decode()
            port = self.server.server_address[1]
            if "/json/list" in line:
                body = json.dumps([{"title": "Steam", "webSocketDebuggerUrl": f"ws://127.0.0.1:{port}/x"},
                                   {"title": "SharedJSContext", "webSocketDebuggerUrl": f"ws://127.0.0.1:{port}/devtools/page/S"}]).encode()
                s.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
                return
            key = [ln.split(b": ", 1)[1] for ln in req.split(b"\r\n") if ln.lower().startswith(b"sec-websocket-key")][0]
            acc = base64.b64encode(hl.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
            s.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + acc + b"\r\n\r\n")
            b0, b1 = s.recv(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", s.recv(2))[0]
            mask = s.recv(4)
            data = b""
            while len(data) < n:
                data += s.recv(n - len(data))
            msg = json.loads(bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
            expr = msg["params"]["expression"]
            m = json.loads(expr.split("M = ", 1)[1].split(",", 1)[0])
            calls.append((m, expr))
            v = {"get_tdp_state": {"supported": True, "global_watts": 13, "watts": 30, "appid": "ns:hub", "limits": {"min": 5, "max": 30}},
                 "set_tdp_watts": {"requested_w": 7, "applied_w": 7, "ok": True}}[m]
            out = json.dumps({"id": 1, "result": {"result": {"type": "string", "value": json.dumps({"ok": True, "v": v})}}}).encode()
            s.sendall(bytes([0x81]) + (bytes([len(out)]) if len(out) < 126 else bytes([126]) + struct.pack(">H", len(out))) + out)

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(tdpctl, "CDP", f"http://127.0.0.1:{srv.server_address[1]}")
        assert tdpctl.state()["global_watts"] == 13
        r = tdpctl.set_watts(7)
        assert r["applied_w"] == 7 and r["ok"]
        assert [c[0] for c in calls] == ["get_tdp_state", "get_tdp_state", "set_tdp_watts"]
        assert '"Panel de Control"' in calls[-1][1] and "[7, \"game\", \"ns:hub\", \"ns:hub\"]" in calls[-1][1]
    finally:
        srv.shutdown()
        srv.server_close()


def test_sin_steam_da_un_error_claro(monkeypatch):
    from hub import tdpctl
    monkeypatch.setattr(tdpctl, "CDP", "http://127.0.0.1:1")
    with pytest.raises(tdpctl.TdpError, match="depurador de Steam"):
        tdpctl.state()
