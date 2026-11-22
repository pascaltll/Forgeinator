"""CONTRATO contra tu daemon REAL (no usa el falso). Dice si un fallo es de Hub o de service.py.

  CATALOG_LIVE=1                  → comprueba health/search/variants (no descarga nada)
  CATALOG_LIVE_DOWNLOAD=1         → además descarga de verdad UNA variante (la más pequeña) a una carpeta temporal
  CATALOG_LIVE_FILTER="USA"       → elige la más pequeña entre las variantes que contengan ese texto (nombre o región)
  CATALOG_LIVE_VARIANT=<id>       → fuerza una variante concreta
Opcionales: CATALOG_LIVE_QUERY="Silent Hill"  CATALOG_LIVE_SYSTEM="PlayStation"  CATALOG_LIVE_MAX_MB=1500  CATALOG_LIVE_TIMEOUT=900
            CATALOG_LIVE_URL  CATALOG_LIVE_TOKEN_FILE  CATALOG_LIVE_SOURCE / CATALOG_LIVE_ITEM (fuerzan el ítem)
"""
import os
import time
import zipfile
from pathlib import Path

import pytest

from hub import catalogjobs as cj

pytestmark = [pytest.mark.live, pytest.mark.skipif(os.environ.get("CATALOG_LIVE") != "1", reason="activa con CATALOG_LIVE=1 (usa tu daemon real)")]

QUERY = os.environ.get("CATALOG_LIVE_QUERY", "Silent Hill")
SYSTEM = os.environ.get("CATALOG_LIVE_SYSTEM", "PlayStation")
MAX_MB = float(os.environ.get("CATALOG_LIVE_MAX_MB", "1500"))
TIMEOUT = float(os.environ.get("CATALOG_LIVE_TIMEOUT", "900"))
STATES_OK = set(cj._STATE)       # estados que Hub entiende
PLACEHOLDERS = {"archivo_descargado.zip", "archivo_descargado", "descarga.bin"}


@pytest.fixture(scope="module")
def estado():
    return {}


@pytest.fixture(autouse=True)
def _live(real_cs):
    return real_cs


def test_01_el_puerto_responde(real_cs):
    assert real_cs.port_open(1.0), f"nadie escucha en {real_cs.URL}: ¿arrancó el daemon? Log: {real_cs.LOG_FILE}"


def test_02_hay_token_y_lo_acepta(real_cs):
    assert real_cs.TOKEN_FILE.is_file(), f"no existe {real_cs.TOKEN_FILE}: el daemon debe crearlo al arrancar"
    assert real_cs.token()
    real_cs.health(start=False)       # un 401 aquí = el daemon espera otra cabecera/token


def test_03_health_tiene_la_forma_del_contrato(real_cs):
    hl = real_cs.health(start=False)
    assert isinstance(hl, list) and hl, "health debe devolver una lista no vacía de fuentes"
    for h in hl:
        assert isinstance(h, dict) and h.get("source"), f"fuente sin 'source': {h}"
        assert h.get("status") in ("OK", "WARN", "DEAD"), f"status inesperado en {h}"


def test_04_metodo_inexistente_da_32601(real_cs):
    with pytest.raises(real_cs.RpcError) as e:
        real_cs.call("metodo_que_no_existe", {}, start=False)
    if e.value.code != -32601:
        pytest.xfail(f"[conformidad, no bloquea] método desconocido devuelve {e.value.code}; el estándar JSON-RPC es -32601 (Hub lo muestra igual)")


def test_05_parametros_invalidos_dan_32602(real_cs):
    try:
        r = real_cs.call("search", {}, start=False)
    except real_cs.RpcError as e:
        if e.code != -32602:
            pytest.xfail(f"[conformidad, no bloquea] search sin query da {e.code}; el estándar es -32602")
        return
    pytest.xfail(f"[conformidad, no bloquea] search sin 'query' no da error (devuelve {str(r)[:60]}); debería dar -32602. Hub siempre manda query, no le afecta")


def test_06_search_devuelve_resultados_con_el_esquema(real_cs, estado):
    res = real_cs.search(QUERY, system=SYSTEM)
    assert isinstance(res, list) and res, f"search('{QUERY}', system='{SYSTEM}') no devolvió nada"
    for r in res:
        assert isinstance(r, dict) and r.get("source") and r.get("item_id") and r.get("title"), f"resultado incompleto: {r}"
        assert 0 <= float(r.get("confidence", 0)) <= 1, f"confidence fuera de 0..1: {r}"
    estado["res"] = res
    hl = {h["source"]: h["status"] for h in real_cs.health(start=False)}
    buenos = [r for r in res if QUERY.lower() in str(r["title"]).lower() and hl.get(r["source"], "OK") != "DEAD"]
    assert buenos, f"ningún resultado vivo contiene '{QUERY}': {[(r['source'], r['title']) for r in res][:8]}"
    forzado = (os.environ.get("CATALOG_LIVE_SOURCE"), os.environ.get("CATALOG_LIVE_ITEM"))
    estado["item"] = ({"source": forzado[0], "item_id": forzado[1], "title": QUERY} if all(forzado) else sorted(buenos, key=lambda r: -float(r.get("confidence") or 0))[0])


def test_07_search_sin_system_tambien_funciona(real_cs):
    assert isinstance(real_cs.search(QUERY), list)


def test_08_search_ordenable_por_confianza_y_sin_duplicados_exactos(real_cs, estado):
    res = estado.get("res") or real_cs.search(QUERY, system=SYSTEM)
    claves = [(r["source"], r["item_id"]) for r in res]
    assert len(claves) == len(set(claves)), "hay resultados repetidos (misma fuente+item_id)"


def test_09_variants_forma_y_cantidad(real_cs, estado, capsys):
    it = estado.get("item")
    assert it, "sin ítem: falló el test_06"
    vs = real_cs.variants(it["source"], it["item_id"])
    assert isinstance(vs, list) and vs, f"variants({it['source']}, {it['item_id']}) devolvió una lista vacía"
    with capsys.disabled():
        print(f"\n   → {len(vs)} variantes para «{it['title']}» ({it['source']})")
    ids = []
    for v in vs:
        assert isinstance(v, dict), f"variante que no es objeto: {v!r}"
        for k in ("variant_id", "filename", "region", "format", "size"):
            assert v.get(k) not in (None, ""), f"variante sin '{k}': {v}"
        assert isinstance(v.get("resumable"), bool), f"'resumable' debe ser booleano: {v}"
        assert "/" not in v["filename"] and ".." not in v["filename"], f"filename peligroso (ruta): {v['filename']}"
        ids.append(v["variant_id"])
    assert len(ids) == len(set(ids)), "variant_id repetido"
    estado["vars"] = vs
    estado["sizes_ok"] = [cj.parse_size(v["size"]) for v in vs]
    assert any(s > 0 for s in estado["sizes_ok"]), "ningún 'size' es interpretable ('3.2 GB', '700 MB'…)"


def test_10_variants_item_inexistente_da_error_claro(real_cs, estado):
    it = estado["item"]
    try:
        r = real_cs.variants(it["source"], "ID-QUE-NO-EXISTE-0000")
    except real_cs.RpcError:
        return
    if r:
        pytest.xfail(f"[conformidad, no bloquea] variants de un item inexistente devuelve {len(r)} variantes en vez de error o lista vacía")


# ── descarga real ───────────────────────────────────────────────────────────
def _elegir(estado):
    vs = estado["vars"]
    if os.environ.get("CATALOG_LIVE_VARIANT"):                      # id exacto
        return next(v for v in vs if v["variant_id"] == os.environ["CATALOG_LIVE_VARIANT"])
    filtro = os.environ.get("CATALOG_LIVE_FILTER", "").lower()      # p. ej. "USA" o "Rev 1"
    if filtro:
        vs = [v for v in vs if filtro in (v["filename"] + " " + v["region"]).lower()] or pytest.skip(f"ninguna variante contiene «{filtro}»")
    cand = [(cj.parse_size(v["size"]) or 10 ** 12, v) for v in vs if (cj.parse_size(v["size"]) or 0) <= MAX_MB * 1024 ** 2] or [(cj.parse_size(v["size"]), v) for v in vs]
    return sorted(cand, key=lambda t: t[0])[0][1]


def _seguir(cs, jid, estado, hasta):
    vistos, ultimo, prog = [], None, -1.0
    while time.time() < hasta:
        st = cs.job_status(jid)
        assert isinstance(st, dict), f"job_status debe devolver un objeto, devolvió {st!r}"
        s, ph = st.get("state"), st.get("phase")
        if (s, ph) not in vistos:
            vistos.append((s, ph))
        assert s in STATES_OK, f"estado desconocido para Hub: {s!r} (Hub entiende {sorted(STATES_OK)}); lo vería como 'sin cambios'"
        p = st.get("progress")
        if isinstance(p, (int, float)):
            assert 0 <= p <= 1, f"progress fuera de 0..1: {p}"
            assert p >= prog - 1e-9, f"el progreso retrocede: {prog} → {p}"
            prog = p
        ultimo = st
        if s in ("completed", "failed"):
            break
        time.sleep(1.0)
    estado["vistos"] = vistos
    return ultimo


@pytest.mark.download
@pytest.mark.skipif(os.environ.get("CATALOG_LIVE_DOWNLOAD") != "1", reason="activa con CATALOG_LIVE_DOWNLOAD=1 (descarga un archivo real)")
def test_11_descarga_real_de_la_variante_mas_pequena(real_cs, estado, tmp_path, capsys):
    v, it = _elegir(estado), estado["item"]
    declarado = cj.parse_size(v["size"])
    with capsys.disabled():
        print(f"\n   → descargando «{v['filename']}» ({v['size']}) desde {it['source']} a {tmp_path}")
    r = real_cs.download(it["source"], v["variant_id"], tmp_path)
    assert isinstance(r, dict) and r.get("job_id"), f"download debe devolver {{'job_id': …}}, devolvió {r!r}"
    st = _seguir(real_cs, r["job_id"], estado, time.time() + TIMEOUT)
    with capsys.disabled():
        print(f"   → fases vistas: {estado['vistos']}")
    assert st and st["state"] == "completed", f"la descarga no completó: {st}"
    p = st.get("path")
    assert p, "job completado SIN 'path': Hub no sabe qué archivo comprobar"
    f = Path(p)
    assert f.name not in PLACEHOLDERS, f"el nombre «{f.name}» es un placeholder: el daemon NO está descargando de verdad (solo simula)"
    assert f.is_file(), f"el daemon dice completado pero NO existe el archivo: {p}"
    assert f.resolve().parent == tmp_path.resolve(), f"debe guardar dentro de dest_dir ({tmp_path}), guardó en {f.parent}"
    assert f.stat().st_size > 0, "archivo vacío"
    if declarado:
        assert f.stat().st_size >= 0.5 * declarado, f"tamaño real {f.stat().st_size} ≪ declarado {declarado} ({v['size']})"
    if f.suffix.lower() == ".zip":
        assert zipfile.is_zipfile(f), "el .zip está corrupto/incompleto"
    estado["file"], estado["status"] = f, st


@pytest.mark.download
@pytest.mark.skipif(os.environ.get("CATALOG_LIVE_DOWNLOAD") != "1", reason="activa con CATALOG_LIVE_DOWNLOAD=1")
def test_12_hashes_presentes_y_correctos(estado):
    if "file" not in estado:
        pytest.skip("depende de test_11")
    st, f = estado["status"], estado["file"]
    assert st.get("sha1") or st.get("crc32"), "sin sha1 ni crc32: Hub no puede verificar el archivo (recomendado por el contrato)"
    import hashlib, zlib
    data = f.read_bytes()
    if st.get("sha1"):
        assert hashlib.sha1(data).hexdigest().lower() == str(st["sha1"]).lower(), "sha1 NO coincide con el archivo"
    if st.get("crc32"):
        assert f"{zlib.crc32(data) & 0xffffffff:08x}" == str(st["crc32"]).lower().lstrip("0x").rjust(8, "0"), "crc32 NO coincide"


@pytest.mark.download
@pytest.mark.skipif(os.environ.get("CATALOG_LIVE_DOWNLOAD") != "1", reason="activa con CATALOG_LIVE_DOWNLOAD=1")
def test_13_cancelar_detiene_la_descarga(real_cs, estado, tmp_path):
    v, it = _elegir(estado), estado["item"]
    jid = real_cs.download(it["source"], v["variant_id"], tmp_path)["job_id"]
    t0 = time.time()
    while time.time() - t0 < 30 and real_cs.job_status(jid).get("state") == "queued":
        time.sleep(0.5)
    real_cs.job_cancel(jid)
    fin = time.time() + 20
    while time.time() < fin and real_cs.job_status(jid).get("state") in ("queued", "running"):
        time.sleep(0.5)
    st = real_cs.job_status(jid)
    assert st["state"] in ("failed", "completed"), f"tras cancelar sigue «{st['state']}» 20 s después"
    a = sum(x.stat().st_size for x in tmp_path.rglob("*") if x.is_file())
    time.sleep(2.5)
    b = sum(x.stat().st_size for x in tmp_path.rglob("*") if x.is_file())
    assert a == b, "tras cancelar el archivo sigue creciendo: el daemon no detuvo la transferencia"


def test_14_job_desconocido_da_error_rpc(real_cs):
    with pytest.raises(real_cs.RpcError):
        real_cs.job_status("job_que_no_existe_xyz")
