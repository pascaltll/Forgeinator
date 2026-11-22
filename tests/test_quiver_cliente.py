"""Cliente de Quiver (hub.quiversrc) contra un servidor falso: solo lectura, caché, reserva, elección de archivo."""
import time

import pytest

from conftest import free_port
from fakes.quiver import FakeQuiver
from hub import quiversrc as q


@pytest.fixture
def fq(monkeypatch):
    f = FakeQuiver()
    monkeypatch.setattr(q, "BASE", f.url)
    monkeypatch.setattr(q, "FALLBACK", "")
    monkeypatch.setattr(q, "_MIN_GAP", 0)
    q._cache.clear()
    yield f
    f.stop()
    q._cache.clear()


def test_busqueda_manda_os_linux_y_texto_y_usa_user_agent_propio(fq):
    res = q.search("banjo")
    ruta = fq.gets("/apps")[0][1]
    assert "search=banjo" in ruta and "os=linux" in ruta and "limit=8" in ruta
    assert fq.requests[0][2]["User-Agent"].startswith("recomp-hub")
    assert [r["slug"] for r in res] == ["banjokazooie-banjorecompiled", "sin-version"]     # basura y sin slug se ignoran
    assert res[0]["version"] == "v1.0.2" and res[0]["pinned"] and res[0]["consoles"] == ["n64"]
    assert "sin versión verificada" in q.label(res[1])


def test_texto_corto_no_consulta(fq):
    assert q.search("a") == [] and q.search("") == [] and q.search(None) == []
    assert fq.requests == []


def test_filtro_de_consola(fq):
    q.search("banjo", console="n64")
    assert "console=n64" in fq.gets("/apps")[0][1]


def test_elige_linux_x64_tar_y_no_flatpak_arm_ni_mac(fq):
    ver, files = q.assets("banjokazooie-banjorecompiled")
    assert ver == "v1.0.2"
    assert [f["name"] for f in files] == ["BanjoRecompiled-v1.0.2-Linux-X64.tar.gz"]
    assert files[0]["sha256"] == "cd" * 32 and files[0]["url"].startswith("https://")


def test_flatpak_solo_si_no_hay_otra_cosa(fq):
    from fakes.quiver import asset
    fq.assets = [asset("Juego-Linux-Flatpak-X64.zip"), asset("Juego-Mac.zip", os_="macos")]
    _, files = q.assets("x")
    assert [f["name"] for f in files] == ["Juego-Linux-Flatpak-X64.zip"]


def test_sin_checksum_no_inventa_hash(fq):
    from fakes.quiver import asset
    fq.assets = [asset("Juego-Linux-X64.tar.gz", checksum="")]
    _, files = q.assets("x")
    assert files[0]["sha256"] is None


def test_sin_archivo_de_linux(fq):
    from fakes.quiver import asset
    fq.assets = [asset("Juego-Win.zip", os_="windows"), asset("Juego-arm.tar.gz", arch="arm64")]
    assert q.assets("x")[1] == []


def test_ficha_da_repo_y_carpeta(fq):
    a = q.app("banjokazooie-banjorecompiled")
    assert a["repo"] == "BanjoRecomp/BanjoRecomp" and a["folder"] == "BanjoKazooie-BanjoRecompiled" and a["consoles"] == ["n64"]


def test_cache_evita_repetir_peticiones(fq):
    q.search("banjo")
    q.search("banjo")
    q.assets("a")
    q.assets("a")
    assert len(fq.gets("/apps?")) == 1 and len(fq.gets("/apps/a/releases")) == 1


def test_cache_caduca(fq, monkeypatch):
    q.search("banjo")
    monkeypatch.setattr(q, "TTL_LIST", -1)
    q.get("/apps?limit=8&search=banjo&os=linux", -1)
    assert len(fq.gets("/apps?")) == 2


def test_nunca_hace_post(fq):
    q.search("banjo")
    q.app("a")
    q.assets("a")
    assert {m for m, *_ in fq.requests} == {"GET"}


def test_404_es_error_claro_y_no_prueba_la_reserva(fq, monkeypatch):
    fq.status = 404
    monkeypatch.setattr(q, "FALLBACK", "http://127.0.0.1:1/api/v1")
    with pytest.raises(q.QuiverError, match="404"):
        q.search("banjo")


def test_cae_a_la_reserva_si_el_principal_no_responde(fq, monkeypatch):
    monkeypatch.setattr(q, "FALLBACK", fq.url)
    monkeypatch.setattr(q, "BASE", f"http://127.0.0.1:{free_port()}/api/v1")
    assert q.search("banjo")


def test_error_500_prueba_la_reserva(fq, monkeypatch):
    malo = FakeQuiver()
    malo.status = 503
    try:
        monkeypatch.setattr(q, "BASE", malo.url)
        monkeypatch.setattr(q, "FALLBACK", fq.url)
        assert q.search("banjo")
        assert malo.requests and fq.requests
    finally:
        malo.stop()


def test_sin_red_ni_cache_error_claro(monkeypatch):
    q._cache.clear()
    monkeypatch.setattr(q, "BASE", f"http://127.0.0.1:{free_port()}/api/v1")
    monkeypatch.setattr(q, "FALLBACK", "")
    with pytest.raises(q.QuiverError, match="no pude consultar Quiver"):
        q.search("banjo")


def test_sin_red_pero_con_cache_vieja_sirve_lo_ultimo(fq, monkeypatch):
    q.search("banjo")
    fq.stop()
    monkeypatch.setattr(q, "TTL_LIST", -1)
    datos, viejo = q.get("/apps?limit=8&search=banjo&os=linux", -1)
    assert viejo is True and datos["items"]


def test_pausa_entre_peticiones(fq, monkeypatch):
    monkeypatch.setattr(q, "_MIN_GAP", 0.2)
    t = time.time()
    q.app("a")
    q.assets("a")
    assert time.time() - t >= 0.18


def test_conexion_v4_cae_a_la_normal_si_no_hay_ipv4(monkeypatch):
    llamadas = []
    monkeypatch.setattr(q.socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(OSError("sin v4")))
    monkeypatch.setattr(q.http.client.HTTPSConnection, "connect", lambda self: llamadas.append("normal"))
    q._V4Conn("example.invalid", 443, timeout=1).connect()
    assert llamadas == ["normal"]
