"""v2.23: archivos comprimidos anidados, .7z y mirar dentro de un zip sin descargarlo."""
import http.server
import threading
import zipfile
from pathlib import Path

import pytest

from hub import install, peek


def _zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for n, d in files.items():
            z.writestr(n, d)
    return path


def test_zip_dentro_de_zip_se_abre_solo(tmp_path):
    inner = _zip(tmp_path / "GoW_PSP_Launcher.zip", {"GoW_PSP/GoWLauncher.exe": b"MZ" * 10, "GoW_PSP/README.txt": b"hola"})
    outer = _zip(tmp_path / "release.zip", {"GoW_PSP_Launcher.zip": inner.read_bytes(), "SHA256.txt": b"abc"})
    d = tmp_path / "out"
    install.extract(outer, d)
    assert (d / "GoWLauncher.exe").is_file() and (d / "README.txt").is_file()
    assert not (d / "GoW_PSP_Launcher.zip").exists() and not (d / ".hub-nested").exists()


def test_no_abre_zip_que_es_parte_del_juego(tmp_path):
    outer = _zip(tmp_path / "r.zip", {"game.exe": b"MZ", "data.zip": b"PK-no-es-un-zip-de-verdad"})
    d = tmp_path / "o"
    install.extract(outer, d)
    assert (d / "game.exe").is_file() and (d / "data.zip").is_file(), "con más archivos al lado, el zip es un dato del juego y se deja"


def test_actualizacion_por_encima_solo_mira_lo_nuevo(tmp_path):
    d = tmp_path / "windows"
    (d / "GoW_PSP_data").mkdir(parents=True)
    (d / "GoW_PSP_data" / "x").write_text("partida")
    inner = _zip(tmp_path / "i.zip", {"L.exe": b"MZ"})
    outer = _zip(tmp_path / "o.zip", {"i.zip": inner.read_bytes()})
    install.extract(outer, d)
    assert (d / "L.exe").is_file() and (d / "GoW_PSP_data" / "x").read_text() == "partida"


def test_7z_sin_herramienta_dice_que_hacer(tmp_path, monkeypatch):
    a = tmp_path / "a.7z"
    a.write_bytes(b"7z")
    monkeypatch.setattr(install.shutil, "which", lambda n: None)
    with pytest.raises(OSError, match="7z"):
        install.extract(a, tmp_path / "d")


def test_7z_con_herramienta(tmp_path, monkeypatch):
    a = tmp_path / "a.7z"
    a.write_bytes(b"7z")
    b = tmp_path / "bin"
    b.mkdir()
    t = b / "7z"
    t.write_text('#!/bin/sh\nfor x in "$@"; do case "$x" in -o*) d="${x#-o}";; esac; done\nmkdir -p "$d"; echo hi > "$d/juego.exe"\n')
    t.chmod(0o755)
    monkeypatch.setenv("PATH", f"{b}:/usr/bin:/bin")
    install.extract(a, tmp_path / "d")
    assert (tmp_path / "d" / "juego.exe").is_file()


class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = Path(self.translate_path(self.path))
        data = p.read_bytes()
        rng = self.headers.get("Range")
        if rng:
            a, b = rng.split("=")[1].split("-")
            a, b = int(a), min(int(b), len(data) - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {a}-{b}/{len(data)}")
            self.send_header("Content-Length", str(b - a + 1))
            self.end_headers()
            self.wfile.write(data[a:b + 1])
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


def test_mirar_dentro_de_un_zip_remoto_sin_bajarlo(tmp_path, monkeypatch):
    big = b"x" * 3_000_000
    _zip(tmp_path / "r.zip", {"GoW_PSP_Launcher.zip": big, "README.txt": b"hola"})
    monkeypatch.chdir(tmp_path)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        ents = peek.zip_entries(f"http://127.0.0.1:{srv.server_address[1]}/r.zip")
    finally:
        srv.shutdown()
    assert {n for n, _ in ents} == {"GoW_PSP_Launcher.zip", "README.txt"}
    ls = peek.summary(ents)
    assert any("otro archivo comprimido" in l for l in ls)
