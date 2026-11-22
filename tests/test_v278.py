"""v2.78: actualizar por etapas (apply_update), carpeta real del juego (GTA VCS), actualizadores propios, versión en otro archivo, TLS 1.2."""
import json
import os
import zipfile
from pathlib import Path

import pytest

from hub import config, install, nethttp

ELF = b"\x7fELF" + b"\0" * 60


def _zip(path: Path, files: dict, top=""):
    with zipfile.ZipFile(path, "w") as z:
        for n, data in files.items():
            zi = zipfile.ZipInfo((top + "/" if top else "") + n)
            zi.external_attr = (0o755 if data.startswith(b"\x7fELF") else 0o644) << 16
            z.writestr(zi, data)


def _juego(d: Path):
    d.mkdir()
    (d / "Game").write_bytes(ELF + b"old")
    (d / "README.txt").write_text("old")
    (d / "gamedata").mkdir()
    (d / "gamedata" / "disc.bin").write_text("MI DISCO")
    (d / "update").mkdir()
    (d / "update" / "updater.py").write_text("PROPIO")
    (d / "hub-run.sh").write_text("MIO")
    (d / "disc.iso").symlink_to("/dev/null")


def test_por_encima_etapas_conserva_y_guarda_lo_reemplazado(tmp_path):
    d = tmp_path / "j"
    _juego(d)
    z = tmp_path / "r.zip"
    _zip(z, {"Game": ELF + b"new", "README.txt": b"new", "lib/b.so": b"x", "gamedata/disc.bin": b"PISADO", "update/updater.py": b"AJENO",
             "hub-run.sh": b"AJENO", "disc.iso": b"AJENO"})
    r = install.apply_update(z, d)
    assert (d / "Game").read_bytes().endswith(b"new") and (d / "README.txt").read_text() == "new" and (d / "lib" / "b.so").exists()
    assert (d / "gamedata" / "disc.bin").read_text() == "MI DISCO"
    assert (d / "update" / "updater.py").read_text() == "PROPIO"
    assert (d / "hub-run.sh").read_text() == "MIO" and (d / "disc.iso").is_symlink()
    assert r["replaced"] == 2 and r["saved"] and (Path(r["saved"]) / "README.txt").read_text() == "old"
    assert not (tmp_path / ".j.hub-staging").exists()


def test_paquete_sin_ejecutable_no_toca_nada(tmp_path):
    d = tmp_path / "j"
    _juego(d)
    z = tmp_path / "r.zip"
    _zip(z, {"README.txt": b"new", "docs/a.txt": b"x"})
    with pytest.raises(OSError):
        install.apply_update(z, d)
    assert (d / "README.txt").read_text() == "old" and not (d / "docs").exists()
    assert not (tmp_path / ".j.hub-staging").exists()


def test_fallo_a_mitad_vuelve_atras(tmp_path, monkeypatch):
    d = tmp_path / "j"
    _juego(d)
    z = tmp_path / "r.zip"
    _zip(z, {"Game": ELF + b"new", "README.txt": b"new", "lib/b.so": b"x"})
    real = os.replace
    n = {"c": 0}

    def flaky(a, b):
        n["c"] += 1
        if "lib" in str(b) and "hub-replaced" not in str(b):
            raise OSError("disco lleno")
        return real(a, b)
    monkeypatch.setattr(os, "replace", flaky)
    with pytest.raises(OSError):
        install.apply_update(z, d)
    monkeypatch.setattr(os, "replace", real)
    assert (d / "Game").read_bytes().endswith(b"old") and (d / "README.txt").read_text() == "old"


def test_appimage_con_otra_version_aparta_la_vieja(tmp_path):
    d = tmp_path / "j"
    d.mkdir()
    (d / "VCS-Recomp-0.2.4-x86_64.AppImage").write_bytes(ELF + b"old")
    z = tmp_path / "VCS.zip"
    _zip(z, {"VCS-Recomp-0.3.0-x86_64.AppImage": ELF + b"new"})
    r = install.apply_update(z, d)
    assert (d / "VCS-Recomp-0.3.0-x86_64.AppImage").is_file() and not (d / "VCS-Recomp-0.2.4-x86_64.AppImage").exists()
    assert r["exe"] == "VCS-Recomp-0.3.0-x86_64.AppImage"


def test_no_escribe_a_traves_de_enlace_duro(tmp_path):
    d, prev = tmp_path / "j", tmp_path / "j.prev"
    _juego(d)
    prev.mkdir()
    os.link(d / "README.txt", prev / "README.txt")
    z = tmp_path / "r.zip"
    _zip(z, {"Game": ELF + b"new", "README.txt": b"new"})
    install.apply_update(z, d)
    assert (prev / "README.txt").read_text() == "old" and (d / "README.txt").read_text() == "new"


def test_target_dir_usa_la_subcarpeta_activa(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "launcher")
    root = tmp_path / "gta"
    (root / "linux").mkdir(parents=True)
    (root / ".hub-versions.json").write_text(json.dumps({"active": "linux", "linux": {"exe": "a.AppImage", "executables": ["a.AppImage"]}}))
    e = {"id": "gta", "name": "GTA", "folder": "gta"}
    assert install.target_dir(e) == root / "linux"
    install._sync_meta(root / "linux", "b.AppImage")
    m = json.loads((root / ".hub-versions.json").read_text())
    assert m["linux"]["exe"] == "b.AppImage" and m["linux"]["executables"] == ["b.AppImage"]


def test_target_dir_sin_distribucion_dividida(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "launcher")
    assert install.target_dir({"id": "x", "name": "X", "folder": "x"}) == tmp_path / "x"


def test_install_en_juego_dividido_no_ensucia_la_raiz(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "launcher")
    root = tmp_path / "gta"
    (root / "linux").mkdir(parents=True)
    (root / "linux" / "VCS-0.2.4-x86_64.AppImage").write_bytes(ELF + b"old")
    (root / ".hub-versions.json").write_text(json.dumps({"active": "linux", "linux": {"exe": "VCS-0.2.4-x86_64.AppImage", "executables": ["VCS-0.2.4-x86_64.AppImage"]}}))
    z = tmp_path / "VCS-0.3.0-x86_64.AppImage"
    z.write_bytes(ELF + b"new")
    r = install.install({"id": "gta", "name": "GTA", "folder": "gta"}, z, "VCS-0.3.0-x86_64.AppImage", "v0.3.0")
    assert r["dir"] == str(root / "linux")
    assert (root / "linux" / "VCS-0.3.0-x86_64.AppImage").is_file() and not (root / "VCS-0.3.0-x86_64.AppImage").exists()
    assert (root / "linux" / ".release_version").read_text() == "v0.3.0" and not (root / ".release_version").exists()


def test_own_updater_detecta_los_casos_reales(tmp_path):
    (tmp_path / "update").mkdir()
    (tmp_path / "windows").mkdir()
    (tmp_path / "windows" / "trg-updater.exe").write_bytes(b"x")
    (tmp_path / "update-sacredfire.sh").write_text("x")
    (tmp_path / "juego").write_bytes(b"x")
    u = install.own_updater(tmp_path)
    assert "update/" in u and "windows/trg-updater.exe" in u and "update-sacredfire.sh" in u and "juego" not in u


def test_generic_asset():
    g = install.generic_asset
    assert g("toystory2-0.6.0-linux-x64.zip") == "toystory2-*-linux-x64.zip"
    assert g("SHPC-linux-x64_2026.09.27.1.tar.gz") == "SHPC-linux-x64_*.tar.gz"
    assert g("Quest64Recompiledv0.1.zip") == "Quest64Recompiled*.zip"
    assert g("VCS-Recomp-0.3.0-x86_64.AppImage") == "VCS-Recomp-*-x86_64.AppImage"
    assert g("BT4decomp-linux-x64.zip") == "BT4decomp-linux-x64.zip"


def test_register_escribe_la_version_en_el_version_file_del_toml(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "launcher")
    g = tmp_path / "launcher" / "games"
    g.mkdir(parents=True)
    (g / "x.toml").write_text('id = "x"\nname = "X"\ninstall_dir = "%s"\n[update]\ntype = "none"\nversion_file = ".installed_tag"\n' % (tmp_path / "x"))
    (tmp_path / "x").mkdir()
    install.register({"id": "x", "name": "X"}, tmp_path / "x", "x", "", "v9")
    assert (tmp_path / "x" / ".installed_tag").read_text() == "v9" and (tmp_path / "x" / ".release_version").read_text() == "v9"


def test_nethttp_prueba_tls12_tras_el_fallo_tls(monkeypatch):
    vistos = []

    def falso(url, h, t, m, v4, t12=False):
        vistos.append((v4, t12))
        if not t12:
            raise OSError("EOF occurred in violation of protocol")
        return b"ok"
    monkeypatch.setattr(nethttp, "_once", falso)
    monkeypatch.setattr(nethttp.time, "sleep", lambda s: None)
    assert nethttp.get("https://x.test/") == b"ok"
    assert vistos == [(False, False), (True, False), (False, True)]
