"""ID de un disco (ISO): PSP → PSP_GAME/PARAM.SFO (DISC_ID); PS2/PS1 → SYSTEM.CNF. Recorre el sistema de archivos ISO 9660, así que no depende
de en qué parte del archivo caiga el texto (en un UMD de 1,7 GB el ID puede estar mucho más allá de los primeros MB)."""
import re
import struct

SECTOR = 2048


def norm(s) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def _records(f, lba, size):
    f.seek(lba * SECTOR)
    data = f.read(min(size, 1 << 20))
    i = 0
    while i < len(data):
        n = data[i]
        if n == 0:                                  # relleno hasta el siguiente sector
            i = (i // SECTOR + 1) * SECTOR
            continue
        rec = data[i:i + n]
        if len(rec) < 34:
            break
        ext, ln, flags, nl = struct.unpack_from("<I", rec, 2)[0], struct.unpack_from("<I", rec, 10)[0], rec[25], rec[32]
        name = rec[33:33 + nl].decode("latin-1", "replace").split(";")[0].upper()
        yield name, ext, ln, bool(flags & 2)
        i += n


def _find(f, lba, size, name, want_dir):
    for nm, ext, ln, isdir in _records(f, lba, size):
        if nm == name and isdir == want_dir:
            return ext, ln
    return None


def _sfo_disc_id(blob: bytes):
    if blob[:4] != b"\0PSF" or len(blob) < 20:
        return None
    kt, dt, cnt = struct.unpack_from("<III", blob, 8)
    for k in range(min(cnt, 64)):
        ko, _fmt, ln, _mx, do = struct.unpack_from("<HHIII", blob, 20 + 16 * k)
        key = blob[kt + ko: blob.index(b"\0", kt + ko)].decode("latin-1")
        if key == "DISC_ID":
            return blob[dt + do: dt + do + ln].split(b"\0")[0].decode("latin-1")
    return None


def read_id(path):
    """{id, kind, note} o None si no es un ISO 9660 que sepa leer (.chd, .cso, .bin crudo…)."""
    try:
        with open(path, "rb") as f:
            f.seek(16 * SECTOR)
            pvd = f.read(SECTOR)
            if pvd[1:6] != b"CD001":
                return None
            root_lba, root_len = struct.unpack_from("<I", pvd, 156 + 2)[0], struct.unpack_from("<I", pvd, 156 + 10)[0]
            g = _find(f, root_lba, root_len, "PSP_GAME", True)
            if g:
                s = _find(f, g[0], g[1], "PARAM.SFO", False)
                if s:
                    f.seek(s[0] * SECTOR)
                    did = _sfo_disc_id(f.read(min(s[1], 1 << 16)))
                    if did:
                        return {"id": did, "kind": "psp", "note": "digital (PSN)" if did.upper().startswith("NP") else "disco UMD"}
            c = _find(f, root_lba, root_len, "SYSTEM.CNF", False)
            if c:
                f.seek(c[0] * SECTOR)
                txt = f.read(min(c[1], 4096)).decode("latin-1", "replace")
                m = re.search(r"BOOT2?\s*=\s*cdrom0?:\\?([A-Z]{4}_\d{3}\.\d{2})", txt, re.I)
                if m:
                    return {"id": m.group(1).upper(), "kind": "ps2" if "BOOT2" in txt.upper() else "ps1", "note": ""}
    except (OSError, ValueError, struct.error):
        return None
    return None


def matches(found, wanted) -> bool:
    nf = norm(found)
    return bool(nf) and any(norm(w) == nf for w in wanted or [])
