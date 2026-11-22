"""Servidor falso de la API de Quiver (solo lectura) para probar hub.quiversrc."""
import http.server
import json
import threading
from urllib.parse import urlparse, parse_qs


def asset(name, os_="linux", arch="x64", size=100, checksum="sha256:" + "ab" * 32):
    return {"id": name, "url": f"https://example.invalid/{name}", "filename": name, "os": os_, "architecture": arch, "format": "x", "size": size, "checksum": checksum}


BANJO_ASSETS = [
    asset("BanjoRecompiled-v1.0.2-Linux-ARM64.tar.gz", arch="arm64"),
    asset("BanjoRecompiled-v1.0.2-Linux-Flatpak-X64.zip"),
    asset("BanjoRecompiled-v1.0.2-Linux-X64.tar.gz", checksum="sha256:" + "cd" * 32),
    asset("BanjoRecompiled-v1.0.2-macOS.zip", os_="macos", arch="unknown"),
]


class FakeQuiver:
    def __init__(self):
        self.requests = []          # (método, ruta, cabeceras)
        self.status = None          # fuerza este HTTP
        self.assets = BANJO_ASSETS
        self.repo = "BanjoRecomp/BanjoRecomp"
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _go(self, method):
                outer.requests.append((method, self.path, dict(self.headers)))
                if outer.status:
                    self.send_response(outer.status)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                u = urlparse(self.path)
                path = u.path.removeprefix("/api/v1")
                if path == "/apps":
                    body = {"items": [{"slug": "banjokazooie-banjorecompiled", "name": "Banjo-Kazooie", "projectName": "Banjo Recompiled", "consoles": ["n64"],
                                       "supportedOS": ["linux", "windows"], "verified": {"version": "v1.0.2", "pinned": True}},
                                      {"slug": "sin-version", "name": "Otro", "consoles": ["ps1"]}, "basura", {"name": "sin slug"}],
                            "nextCursor": "x", "isDone": False}
                elif path.endswith("/releases"):
                    body = {"items": [{"id": "r1", "version": "v1.0.2", "assets": outer.assets}], "isDone": True}
                elif path.startswith("/apps/"):
                    body = {"entry": {"name": "Banjo-Kazooie", "consoles": ["n64"], "launcher": {"folderName": "BanjoKazooie-BanjoRecompiled"}},
                            "project": {"name": "Banjo Recompiled", "provider": "github", "repository": outer.repo}}
                else:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                raw = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self._go("GET")

            def do_POST(self):
                self._go("POST")
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/api/v1"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()

    def gets(self, prefix=""):
        return [r for r in self.requests if r[0] == "GET" and r[1].startswith("/api/v1" + prefix)]
