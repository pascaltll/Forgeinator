"""v2.23: ID del disco (PSP/PS2), requisitos por repositorio, enlace dentro del prefijo de Proton y aviso de región."""
import json
import os
import struct
from pathlib import Path

import pytest

from hub import catalog, discid, library, osver
from test_v195 import juego  # noqa: F401
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio  # noqa: F401

S = 2048


def _rec(name, ext, size, isdir):
    nb = name.encode()
    n = 33 + len(nb)
    n += n % 2
    r = bytearray(n)
    r[0] = n
    struct.pack_into("<I", r, 2, ext)
    struct.pack_into(">I", r, 6, ext)
    struct.pack_into("<I", r, 10, size)
    struct.pack_into(">I", r, 14, size)
    r[25] = 2 if isdir else 0
    r[32] = len(nb)
    r[33:33 + len(nb)] = nb
    return bytes(r)


def _sfo(disc_id):
    key = b"DISC_ID\0"
    data = disc_id.encode() + b"\0"
    kt = 20 + 16
    dt = kt + len(key)
    hdr = b"\0PSF" + struct.pack("<IIII", 0x101, kt, dt, 1)
    idx = struct.pack("<HHIII", 0, 0x204, len(data), 16, 0)
    return hdr + idx + key + data


def _iso(path, files, pad_mb=0):
    """ISO 9660 mínimo. files: {"PSP_GAME/PARAM.SFO": bytes} o {"SYSTEM.CNF": bytes}."""
    img = bytearray(S * 40)
    pvd = bytearray(S)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[156:190] = _rec("\0", 20, S, True)[:34]
    img[16 * S:17 * S] = pvd
    root = b""
    lba = 22
    place = {}
    dirs = {}
    for p, data in files.items():
        parts = p.split("/")
        if len(parts) == 2:
            dirs.setdefault(parts[0], []).append((parts[1], data))
        else:
            place[parts[0]] = data
    root += _rec("\0", 20, S, True) + _rec("\1", 20, S, True)
    nxt = 22
    chunks = {}
    for d, items in dirs.items():
        dl = nxt
        nxt += 1
        body = _rec("\0", dl, S, True) + _rec("\1", 20, S, True)
        for nm, data in items:
            body += _rec(nm + ";1", nxt, len(data), False)
            chunks[nxt] = data
            nxt += 1
        chunks[dl] = body
        root += _rec(d, dl, S, True)
    for nm, data in place.items():
        root += _rec(nm + ";1", nxt, len(data), False)
        chunks[nxt] = data
        nxt += 1
    img[20 * S:20 * S + len(root)] = root
    img += bytearray(max(0, (nxt + 2) * S - len(img)))
    for l, data in chunks.items():
        img[l * S:l * S + len(data)] = data
    if pad_mb:
        img += bytearray(pad_mb << 20)
    Path(path).write_bytes(bytes(img))
    return Path(path)


def test_lee_el_id_de_un_umd_de_psp(tmp_path):
    p = _iso(tmp_path / "gow.iso", {"PSP_GAME/PARAM.SFO": _sfo("UCUS98737")}, pad_mb=6)
    d = discid.read_id(p)
    assert d["id"] == "UCUS98737" and d["kind"] == "psp" and "UMD" in d["note"]


def test_distingue_la_edicion_psn(tmp_path):
    d = discid.read_id(_iso(tmp_path / "x.iso", {"PSP_GAME/PARAM.SFO": _sfo("NPUG80325")}))
    assert d["id"] == "NPUG80325" and "PSN" in d["note"]
    assert not discid.matches(d["id"], ["UCUS98653", "UCUS98737"])
    assert discid.matches("UCUS-98653", ["UCUS98653"])


def test_lee_el_id_de_un_iso_de_ps2(tmp_path):
    cnf = b"BOOT2 = cdrom0:\\SLUS_215.90;1\r\nVER = 1.00\r\n"
    d = discid.read_id(_iso(tmp_path / "v.iso", {"SYSTEM.CNF": cnf}))
    assert d["id"] == "SLUS_215.90" and d["kind"] == "ps2"
    assert discid.matches(d["id"], ["SLUS-21590"])


def test_no_iso_devuelve_none(tmp_path):
    f = tmp_path / "a.chd"
    f.write_bytes(b"MComprHD" + b"\0" * 5000)
    assert discid.read_id(f) is None and discid.read_id(tmp_path / "nada.iso") is None


def test_scan_serial_ya_encuentra_ids_lejanos(tmp_path):
    p = _iso(tmp_path / "x.iso", {"PSP_GAME/PARAM.SFO": _sfo("UCUS98737")}, pad_mb=1)
    assert library.scan_serial(p, ["UCUS98653", "UCUS98737"], window=100) == "UCUS98737"
    q = _iso(tmp_path / "y.iso", {"PSP_GAME/PARAM.SFO": _sfo("NPUG80325")})
    assert library.scan_serial(q, ["UCUS98653", "UCUS98737"]) is None


def test_el_catalogo_completa_lo_que_pide_cada_port(tmp_path, monkeypatch):
    e = {"id": "x", "repo": "DrummingBird1/gow-psp-recomp", "requires": {"region": "EUR"}}
    catalog._apply_requirements(e)
    assert e["requires"]["serials"] == ["UCUS98653", "UCUS98737"] and e["requires"]["region"] == "EUR", "no pisa lo que ya traía la tarjeta"
    o = {"id": "y", "repo": "otro/repo"}
    catalog._apply_requirements(o)
    assert "requires" not in o


def test_enlace_dentro_del_prefijo_de_proton(tmp_path, monkeypatch):
    root = tmp_path / "juego"
    (root / "proton-prefix" / "drive_c" / "users" / "steamuser").mkdir(parents=True)
    (root / "proton-prefix" / "drive_c" / "users" / "Public").mkdir()
    iso = tmp_path / "gow.iso"
    iso.write_bytes(b"x")
    monkeypatch.setattr(osver, "root_of", lambda lid: root)
    made = osver.link_into_prefix("g", iso)
    u = root / "proton-prefix" / "drive_c" / "users" / "steamuser"
    assert len(made) == 2 and (u / "Desktop" / "gow.iso").samefile(iso) and (u / "Documents" / "gow.iso").samefile(iso)   # v3.03: enlace duro
    assert not (root / "proton-prefix" / "drive_c" / "users" / "Public" / "Desktop").exists()
    assert osver.link_into_prefix("g", iso) == [], "segunda vez: ya estaban"
    # prefijo sin crear todavía → None (se reintenta)
    root2 = tmp_path / "otro"
    root2.mkdir()
    monkeypatch.setattr(osver, "root_of", lambda lid: root2)
    assert osver.link_into_prefix("g", iso) is None


def test_aviso_de_region_dice_el_id_de_tu_archivo_y_el_que_pide_el_port(H, ui, juego, tmp_path):
    import time
    e = ui.entries[0]
    e["requires"] = {"serials": ["UCUS98653", "UCUS98737"], "note": "Solo discos USA"}
    iso = _iso(tmp_path / "God of War - Chains of Olympus (USA) (PSN).iso", {"PSP_GAME/PARAM.SFO": _sfo("NPUG80325")})
    ui.check_file(e, iso)
    for _ in range(100):
        if ui.modal:
            break
        time.sleep(0.05)
    m = ui.modal["msg"]
    assert "NPUG80325" in m and "PSN" in m and "UCUS98653" in m and "Solo discos USA" in m
    assert ui.match_res[e["id"]]["disc"]["id"] == "NPUG80325"
