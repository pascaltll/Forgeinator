"""Mirar dentro de un .zip sin descargarlo entero: se lee solo su directorio central con peticiones HTTP «Range» (unos pocos KB)."""
import io
import urllib.request
import zipfile


class _Remote(io.RawIOBase):
    def __init__(self, url, timeout=12):
        self.url, self.timeout, self.pos = url, timeout, 0
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "recomp-hub"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cr = r.headers.get("Content-Range", "")            # «bytes 0-0/12345»
            if r.status != 206 or "/" not in cr:
                raise OSError("el servidor no permite leer por partes")
            self.size = int(cr.rsplit("/", 1)[1])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}", "User-Agent": "recomp-hub"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = r.read()
        self.pos += len(data)
        return data

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def zip_entries(src, timeout=12):
    """[(nombre, tamaño)] de un .zip (ruta local o URL http/https). Lanza OSError/zipfile.BadZipFile si no se puede."""
    f = _Remote(src, timeout) if str(src).startswith(("http://", "https://")) else str(src)
    with zipfile.ZipFile(f) as z:
        return [(i.filename, i.file_size) for i in z.infolist() if not i.is_dir()]


def summary(entries, limit=14):
    """Líneas legibles: lo de más arriba primero, con una marca si hay un archivo comprimido dentro y el total."""
    top = sorted(entries, key=lambda e: (e[0].count("/"), e[0].lower()))
    out = []
    for name, size in top[:limit]:
        mark = "   ← otro archivo comprimido: Hub lo abre solo al instalar" if name.lower().endswith((".zip", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.xz")) else ""
        out.append(f"{name}  ({size / 1048576:.1f} MB){mark}")
    if len(top) > limit:
        out.append(f"… y {len(top) - limit} más")
    return out
