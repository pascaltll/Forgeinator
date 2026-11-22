"""v1.66: siempre extraído a la biblioteca (archivo llano), paquete eliminado, y enlace en la carpeta de ROM del port."""
import threading
import zipfile

import pytest

pygame = pytest.importorskip("pygame")
pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def _ui_unica():
    import hub.ui as H
    u = H.UI()
    yield u
    u.running = False


class _Sync:
    def __init__(self, target, daemon=None):
        self.t = target

    def start(self):
        self.t()


def _montaje(tmp_path):
    root = tmp_path / "roms"
    (root / "n64").mkdir(parents=True)
    z = root / "n64" / "Banjo.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("Banjo.z64", b"ROMDATA" * 100)
    work = tmp_path / "converted" / "Banjo"
    work.mkdir(parents=True)
    plain = work / "Banjo.z64"
    plain.write_bytes(b"ROMDATA" * 100)
    return root, z, plain


def test_extrae_a_la_biblioteca_borra_el_zip_y_enlaza_en_el_port(_ui_unica, tmp_path, monkeypatch):
    from hub import library
    u = _ui_unica
    root, z, plain = _montaje(tmp_path)
    dest_dir = tmp_path / "share" / "lighthouse"
    e = {"id": "bk", "name": "BK", "platform": "Nintendo 64", "repo": "x/y", "requires": {"rom_dest": str(dest_dir)}}
    monkeypatch.setattr(u, "roms_roots", lambda: [root])
    monkeypatch.setattr(threading, "Thread", _Sync)
    monkeypatch.setattr(u, "_auto_libcwd", lambda ent: "")
    monkeypatch.setattr(library, "link_set", lambda i, p: None)
    monkeypatch.setattr(library, "adopt", lambda *a, **k: None)
    monkeypatch.setattr(u, "inst", lambda ent: {"installed": False})
    u.cfg["esde_store"] = "ask"
    u._accept(e, plain, "ok", original=z)
    final = root / "n64" / "Banjo.z64"
    assert final.read_bytes() == b"ROMDATA" * 100
    assert not z.exists(), "el paquete se elimina"
    assert not plain.exists() and not plain.parent.exists(), "sin restos en la caché"
    lk = dest_dir / "Banjo.z64"
    assert lk.is_symlink() and lk.resolve() == final.resolve()


def test_si_falla_la_copia_no_se_borra_el_zip(_ui_unica, tmp_path, monkeypatch):
    from hub import esde
    u = _ui_unica
    root, z, plain = _montaje(tmp_path)
    e = {"id": "bk2", "name": "BK", "platform": "Nintendo 64"}
    monkeypatch.setattr(u, "roms_roots", lambda: [root])
    monkeypatch.setattr(threading, "Thread", _Sync)

    def boom(*a, **k):
        raise OSError("disco lleno")
    monkeypatch.setattr(esde, "store", boom)
    u._accept(e, plain, "ok", original=z)
    assert z.exists() and plain.exists()


def test_se_puede_desactivar(_ui_unica, tmp_path, monkeypatch):
    u = _ui_unica
    root, z, plain = _montaje(tmp_path)
    monkeypatch.setattr(u, "roms_roots", lambda: [root])
    called = []
    monkeypatch.setattr(u, "_store_extracted", lambda *a: called.append(1))
    monkeypatch.setattr(u, "_accept_final", lambda *a: None)
    u.cfg["extract_to_library"] = False
    u.cfg["esde_store"] = "link"
    u._accept({"id": "z", "name": "Z", "platform": "Nintendo 64"}, plain, "ok", original=z)
    u.cfg["extract_to_library"] = True
    assert not called


def test_place_rom_no_pisa_un_archivo_real(tmp_path):
    from hub import library
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.z64").write_bytes(b"real")
    src = tmp_path / "a.z64"
    src.write_bytes(b"otro")
    library.place_rom({"requires": {"rom_dest": str(d)}}, src)
    assert (d / "a.z64").read_bytes() == b"real"


def test_lighthouse_tiene_carpeta_por_defecto():
    from hub import library
    assert str(library.rom_dest_for({"repo": "HarbourMasters/Lighthouse"})).endswith(".local/share/lighthouse")
    assert library.rom_dest_for({"repo": "otro/x"}) is None
