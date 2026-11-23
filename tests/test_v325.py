"""v3.25 · Complementos: zona de instalación, validación del zip, protocolo de conectores v1 por stdio y el complemento de ejemplo
«Catálogo HTTP v1» contra un servidor de prueba."""
import hashlib
import json
import os
import stat
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from conftest import HUB_SRC
from hub import config, plugins, remote, service

EXAMPLE = Path(HUB_SRC) / "plugins" / "catalogo-http"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    for k, sub in (("DATA", "data"), ("CONFIG", "conf"), ("STATE", "state")):
        d = tmp_path / sub
        d.mkdir()
        monkeypatch.setattr(config, k, d)
    roms = tmp_path / "roms"
    roms.mkdir()
    cfg = dict(config.DEFAULT_SETTINGS, rom_dirs=[str(roms)])
    monkeypatch.setattr(config, "settings", lambda: cfg)
    return cfg, roms


def mkplugin(tmp_path, pid="eco", code="", manifest=None, name=None):
    d = tmp_path / "src" / pid
    d.mkdir(parents=True)
    m = {"schema": 1, "id": pid, "name": name or pid.capitalize(), "version": "1.0.0", "type": "connector", "protocol": 1,
         "run": ["python3", "main.py"], "fields": [{"key": "clave", "label": "Clave", "secret": True}], "permissions": ["network"]}
    m.update(manifest or {})
    (d / "forgeinator-plugin.json").write_text(json.dumps(m))
    (d / "main.py").write_text(code)
    return plugins.pack(d, tmp_path / "zips")


ECO = r'''
import json, os, sys, time
for line in sys.stdin:
    m = json.loads(line); mid = m["id"]; p = m.get("params") or {}
    def ok(r): print(json.dumps({"v": 1, "id": mid, "ok": True, "result": r}), flush=True)
    if m["method"] == "hello": ok({"protocol": 1, "capabilities": ["systems", "games", "download"]})
    elif m["method"] == "systems":
        ok([{"dir": "PlayStation", "system": "psx"}, {"dir": "env", "system": "n64", "name": ",".join(sorted(os.environ))},
            {"dir": "cfg", "system": "snes", "name": json.dumps(p["config"], sort_keys=True)}])
    elif m["method"] == "games": ok([{"path": "x/1", "name": "../../Juego (EU).chd", "size": 10}, {"path": "x/2", "name": "Otro.chd"}])
    elif m["method"] == "download":
        for i in range(400):
            print(json.dumps({"v": 1, "id": mid, "progress": {"done": i, "total": 400}}), flush=True)
            time.sleep(0.01)
            if p["game"]["name"] == "Otro.chd" and i == 3:
                open(p["dest"], "w").write("hola"); ok({"bytes": 4}); break
        else:
            print(json.dumps({"v": 1, "id": mid, "ok": False, "error": "x", "detail": "no terminó"}), flush=True)
    elif m["method"] == "cancel": pass
'''


def test_instalar_actualizar_desactivar_quitar(lib, tmp_path):
    z = plugins.pack(EXAMPLE, tmp_path / "zips")
    assert z.name == "forgeinator-plugin-catalogo-http-1.0.0.zip"
    i = plugins.inspect(z)
    assert i["action"] == "instalar" and i["permissions"] == ["network"] and i["fields"][1]["secret"]
    m = plugins.install(z)
    assert m["enabled"] and (plugins.root() / "catalogo-http" / "main.py").is_file()
    assert [p["id"] for p in plugins.connectors()] == ["catalogo-http"]
    assert plugins.inspect(z)["action"] == "reinstalar"
    plugins.install(z)
    assert len(list((plugins.root() / ".anteriores").iterdir())) == 1               # la copia anterior no se borra
    plugins.set_enabled("catalogo-http", False)
    assert plugins.connectors() == [] and plugins.installed()["catalogo-http"]["enabled"] is False
    plugins.install(z)
    assert plugins.installed()["catalogo-http"]["enabled"] is False                 # reinstalar respeta lo que elegiste
    dst = plugins.remove("catalogo-http")
    assert dst.parent.name == ".papelera" and (dst / "main.py").is_file() and plugins.installed() == {}


def _zip(tmp_path, files, name="malo.zip", link=None):
    z = tmp_path / name
    with zipfile.ZipFile(z, "w") as f:
        for n, data in files.items():
            f.writestr(n, data)
        if link:
            zi = zipfile.ZipInfo(link)
            zi.external_attr = (stat.S_IFLNK | 0o777) << 16
            f.writestr(zi, "/etc/passwd")
    return z


GOOD = {"schema": 1, "id": "malo", "name": "M", "version": "1", "type": "connector", "protocol": 1, "run": ["python3", "main.py"]}


@pytest.mark.parametrize("files,link,why", [
    ({"main.py": ""}, None, "falta forgeinator-plugin.json"),
    ({"forgeinator-plugin.json": json.dumps(dict(GOOD, id="Malo!"))}, None, "Id no válido"),
    ({"forgeinator-plugin.json": json.dumps(dict(GOOD, protocol=2))}, None, "protocolo"),
    ({"forgeinator-plugin.json": json.dumps(dict(GOOD, run=["/usr/bin/curl"]))}, None, "dentro del complemento"),
    ({"forgeinator-plugin.json": json.dumps(dict(GOOD, run=["../fuera.sh"]))}, None, "dentro del complemento"),
    ({"forgeinator-plugin.json": json.dumps(GOOD), "../../evil.py": "x"}, None, "Ruta peligrosa"),
    ({"forgeinator-plugin.json": json.dumps(GOOD), "main.py": ""}, "enlace", "enlace simbólico"),
    ({"forgeinator-plugin.json": json.dumps(dict(GOOD, run=["run.sh"]))}, None, "Falta el programa"),
])
def test_zips_malos_no_se_instalan(lib, tmp_path, files, link, why):
    z = _zip(tmp_path, files, link=link)
    with pytest.raises(plugins.PluginError, match=why):
        plugins.install(z)
    assert plugins.installed() == {} and not list(plugins.root().glob(".nuevo-*")) if plugins.root().exists() else True
    assert not (tmp_path / "evil.py").exists()


def test_protocolo_stdio_secretos_y_nombres_seguros(lib, tmp_path, monkeypatch):
    plugins.install(mkplugin(tmp_path, code=ECO))
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_noDebeLlegar")
    monkeypatch.setenv("STEAMGRIDDB_KEY", "nada")
    s = remote.add("plugin", "Eco", {"plugin": "eco", "clave": "s3creta!"}, root="")
    pub = json.loads((config.DATA / "remotes.json").read_text())
    assert "s3creta!" not in json.dumps(pub)                                       # el secreto va aparte (600)
    secf = config.CONFIG / "remotes-secrets.json"
    assert json.loads(secf.read_text())[s["id"]]["clave"] == "s3creta!" and oct(secf.stat().st_mode & 0o777) == "0o600"
    assert remote.kind_label(s) == "Eco"
    sy = {x["system"]: x for x in remote.systems(s)}
    assert sy["psx"]["dir"] == "PlayStation"
    env = sy["n64"]["name"].split(",")
    assert "GITHUB_TOKEN" not in env and "STEAMGRIDDB_KEY" not in env and "FORGEINATOR_PLUGIN_PROTOCOL" in env
    assert json.loads(sy["snes"]["name"]) == {"clave": "s3creta!", "root": ""}  # solo los campos de SU fuente
    gs = remote.games(s, "PlayStation", "psx")
    assert [g["name"] for g in gs] == ["Juego (EU).chd", "Otro.chd"]              # sin «../»: no puede escapar de la carpeta de ROMs
    seen = []
    p = remote.download(s, gs[1], "psx", progress=lambda *a: seen.append(a[0]))
    assert p.read_text() == "hola" and p.parent.name == "psx" and seen
    assert not list(p.parent.glob("*.parte"))


def test_cancelar_y_lo_que_queda_a_medias(lib, tmp_path):
    plugins.install(mkplugin(tmp_path, code=ECO))
    s = remote.add("plugin", "Eco", {"plugin": "eco"}, root="")
    t0 = time.time()
    with pytest.raises(remote.RemoteError, match="cancelada"):
        remote.download(s, {"path": "x/1", "name": "Juego.chd"}, "psx", stop=lambda: time.time() - t0 > 0.3)
    assert time.time() - t0 < 10


def test_complemento_desactivado_o_roto(lib, tmp_path):
    plugins.install(mkplugin(tmp_path, code="import sys\nsys.exit(3)\n"))
    s = remote.add("plugin", "Eco", {"plugin": "eco"}, root="")
    with pytest.raises(remote.RemoteError, match="terminó sin responder"):
        remote.systems(s)
    plugins.set_enabled("eco", False)
    with pytest.raises(remote.RemoteError, match="desactivado"):
        remote.systems(s)
    with pytest.raises(remote.RemoteError, match="no está instalado"):
        remote.add("plugin", "X", {"plugin": "noexiste"})


# ---------------------------------------------------------------- complemento de ejemplo contra un servidor HTTP v1
def fake_server(token="T0k3n-del-servidor"):
    disc1, disc2, single = b"A" * 70000, b"B" * 1000, b"ROM" * 5000
    files = {"g1": [{"name": "Crash (EU).chd", "data": single}],
             "g2": [{"name": "FF7 (CD1).chd", "data": disc1}, {"name": "FF7 (CD2).chd", "data": disc2}],
             "g3": [{"name": "Roto.chd", "data": b"xx", "sha": "0" * 64}]}
    items = [{"id": "g1", "title": "Crash", "system": "psx", "file": "Crash (EU).chd", "size": len(single)},
             {"id": "g2", "title": "Final Fantasy VII", "system": "psx", "files": 2, "size": len(disc1) + len(disc2)},
             {"id": "g3", "title": "Roto", "system": "n64", "file": "Roto.chd"}]

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _j(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.headers.get("Authorization") != "Bearer " + token:
                return self._j(401, {"error": "auth", "detail": "token"})
            path = self.path.split("/v1/", 1)[-1]
            if path == "info":
                return self._j(200, {"name": "NAS de prueba", "version": "0.1", "protocol": 1})
            if path.startswith("catalog"):
                if "since=2" in path:
                    return self._j(200, {"items": items[2:], "next": None})
                return self._j(200, {"items": items[:2], "next": "2"})
            if path.startswith("items/") and path.endswith("/files"):
                gid = path.split("/")[1]
                return self._j(200, [{"name": f["name"], "size": len(f["data"]), "url": f"dl/{gid}/{i}",
                                      "sha256": f.get("sha") or hashlib.sha256(f["data"]).hexdigest()} for i, f in enumerate(files[gid])])
            if path.startswith("dl/"):
                _, gid, i = path.split("/")
                d = files[gid][int(i)]["data"]
                self.send_response(200)
                self.send_header("Content-Length", str(len(d)))
                self.end_headers()
                self.wfile.write(d)
                return
            return self._j(404, {"error": "no_existe"})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/forgeinator/v1", token, files


def test_ejemplo_catalogo_http_de_punta_a_punta(lib, tmp_path):
    cfg, roms = lib
    srv, url, tok, files = fake_server()
    try:
        plugins.install(plugins.pack(EXAMPLE, tmp_path / "z"))
        bad = remote.add("plugin", "Malo", {"plugin": "catalogo-http", "url": url, "token": "otro"}, root="")
        with pytest.raises(remote.RemoteError, match="rechazó el token"):
            remote.test(bad)
        s = remote.add("plugin", "NAS", {"plugin": "catalogo-http", "url": url, "token": tok}, root="")
        assert remote.test(s).startswith("«NAS de prueba» 0.1 · 2 sistemas")
        assert [x["system"] for x in remote.systems(s)] == ["n64", "psx"]           # las dos páginas del catálogo
        gs = {g["name"]: g for g in remote.games(s, "psx", "psx")}
        assert set(gs) == {"Crash (EU).chd", "Final Fantasy VII"} and gs["Final Fantasy VII"]["dir"]
        p1 = remote.download(s, gs["Crash (EU).chd"], "psx", cfg=cfg)
        assert p1 == roms / "psx" / "Crash (EU).chd" and p1.read_bytes() == files["g1"][0]["data"]
        p2 = remote.download(s, gs["Final Fantasy VII"], "psx", cfg=cfg)
        assert sorted(x.name for x in p2.iterdir()) == ["FF7 (CD1).chd", "FF7 (CD2).chd"]
        g3 = remote.games(s, "n64", "n64")[0]
        with pytest.raises(remote.RemoteError, match="sha256 no coincide"):
            remote.download(s, g3, "n64", cfg=cfg)
        assert not (roms / "n64" / "Roto.chd").exists() and list((roms / "n64").glob("*.incompleto"))
        with pytest.raises(remote.RemoteError, match="Ya tienes"):
            remote.download(s, gs["Crash (EU).chd"], "psx", cfg=cfg)
    finally:
        srv.shutdown()


def test_servicio_metodos_de_complementos(lib, tmp_path):
    svc = service.Service(service.Queue(max_active=1))
    z = plugins.pack(EXAMPLE, tmp_path / "z")
    assert "plugins.install" in svc.handle({"method": "ping"}, None)["methods"]
    assert svc.handle({"method": "plugins.inspect", "params": {"path": str(z)}}, None)["action"] == "instalar"
    r = svc.handle({"method": "plugins.install", "params": {"path": str(z)}}, None)
    assert r["id"] == "catalogo-http" and "run" not in r
    assert [x["id"] for x in svc.handle({"method": "plugins.list"}, None)] == ["catalogo-http"]
    assert svc.handle({"method": "plugins.disable", "params": {"id": "catalogo-http"}}, None) is True
    with pytest.raises(ValueError):
        svc.handle({"method": "plugins.install", "params": {"path": "/etc/passwd"}}, None)
    assert ".papelera" in svc.handle({"method": "plugins.remove", "params": {"id": "catalogo-http"}}, None)["moved_to"]


def test_interfaz_zona_de_complementos(lib, tmp_path, monkeypatch):
    from test_temas_y_fuzz import H, run  # noqa: F401
    import hub.ui as U
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    plugins.pack(EXAMPLE, home / "Downloads")
    ui = U.UI.__new__(U.UI)
    ui.cfg, _ = lib
    ui.modal = ui.focus = None
    ui._io_gen = 0
    msgs = []
    ui.toast = msgs.append
    ui.use_steam_kb = lambda: False

    def pick(prefix):
        opts = dict(ui.modal["options"])
        k = next(k for k in opts if k.startswith(prefix))
        ui.modal = None
        opts[k]()

    def wait(cond, t=10):
        t0 = time.time()
        while not cond() and time.time() - t0 < t:
            q = ui.__dict__.get("_uiq")
            while q:
                q.pop(0)()
            time.sleep(0.02)
        assert cond(), msgs[-3:]

    assert ui._plugins_txt() == "ninguno instalado"
    ui.plugins_menu()
    pick("+ INSTALAR")
    pick("forgeinator-plugin-catalogo-http")
    assert "red" in ui.modal["msg"] and ui.modal["title"].startswith("¿Instalar")
    pick("INSTALAR")
    wait(lambda: ui.modal and ui.modal.get("title") == "Catálogo HTTP v1")
    assert "1 instalado" in ui._plugins_txt()
    monkeypatch.setattr(U.remote, "rclone_bin", lambda: None)
    ui.remote_add()
    names = [k for k, _ in ui.modal["options"]]
    assert "COMPLEMENTO · CATÁLOGO HTTP V1" in names and not any(k.startswith("WEBDAV") for k in names)
    pick("COMPLEMENTO")
    assert ui.modal["kind"] == "osk" and ui.modal["text"] == "https://"


def test_el_ejemplo_minimo_de_la_guia_funciona(lib, tmp_path):
    cfg, roms = lib
    doc = (Path(HUB_SRC) / "docs" / "PLUGINS.md").read_text(encoding="utf-8")
    code = doc.split("## 5.", 1)[1].split("```python", 1)[1].split("```", 1)[0]
    plugins.install(mkplugin(tmp_path, pid="demo", code=code, manifest={"fields": []}))
    s = remote.add("plugin", "Demo", {"plugin": "demo"}, root="")
    assert [x["system"] for x in remote.systems(s)] == ["psx"]
    g = remote.games(s, "psx", "psx")[0]
    assert remote.download(s, g, "psx", cfg=cfg).read_bytes() == b"hola!"


def test_terminal_forgeinator_ctl_plugins(lib, tmp_path):
    import subprocess
    z = plugins.pack(EXAMPLE, tmp_path / "z")
    env = dict(os.environ, HUB_DATA=str(tmp_path / "solo"))
    ctl = [sys.executable, str(Path(HUB_SRC) / "bin" / "forgeinator-ctl"), "--plugins"]
    r = subprocess.run(ctl + ["ver", str(z)], capture_output=True, text=True, env=env, timeout=20)
    assert r.returncode == 0 and json.loads(r.stdout)["action"] == "instalar"
    r = subprocess.run(ctl + ["instalar", str(z)], capture_output=True, text=True, env=env, timeout=20)
    assert r.returncode == 0 and "permisos: network" in r.stderr
    r = subprocess.run(ctl + ["lista"], capture_output=True, text=True, env=env, timeout=20)
    assert [p["id"] for p in json.loads(r.stdout)] == ["catalogo-http"]
    r = subprocess.run(ctl + ["quitar", "catalogo-http"], capture_output=True, text=True, env=env, timeout=20)
    assert ".papelera" in json.loads(r.stdout)["movido_a"]
    r = subprocess.run(ctl + ["instalar", "/no/existe.zip"], capture_output=True, text=True, env=env, timeout=20)
    assert r.returncode == 1 and r.stderr.startswith("Error:")
