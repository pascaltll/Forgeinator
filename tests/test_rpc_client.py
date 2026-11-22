"""Cliente JSON-RPC: todas las ramas de token(), _post(), call() y los envoltorios."""
import json
import sys

import pytest

from conftest import free_port
from fakes.daemon import FakeDaemon


# ── token() ─────────────────────────────────────────────────────────────────
def test_token_ok_y_recorta_espacios(cs):
    cs.TOKEN_FILE.write_text("  abc123\n")
    assert cs.token() == "abc123"


def test_token_ausente(cs):
    with pytest.raises(cs.TokenMissing) as e:
        cs.token()
    assert str(cs.TOKEN_FILE) in str(e.value)


@pytest.mark.parametrize("contenido", ["", "   ", "\n\n"])
def test_token_vacio(cs, contenido):
    cs.TOKEN_FILE.write_text(contenido)
    with pytest.raises(cs.TokenMissing, match="vacío"):
        cs.token()


def test_tokenmissing_es_tokenerror(cs):
    assert issubclass(cs.TokenMissing, cs.TokenError) and issubclass(cs.TokenError, cs.CatalogError)


# ── éxito y forma de la petición ────────────────────────────────────────────
def test_call_devuelve_result(daemon, cs):
    assert cs.call("health", start=False)[0]["source"] == "nas"


def test_peticion_es_jsonrpc_2_con_token_y_ids_crecientes(daemon, cs):
    cs.call("health", start=False)
    cs.call("health", start=False)
    a, b = daemon.bodies[-2:]
    assert a["jsonrpc"] == b["jsonrpc"] == "2.0" and a["method"] == "health" and a["params"] == {}
    assert b["id"] == a["id"] + 1
    assert daemon.headers[-1]["X-Catalog-Token"] == "SECRETO"
    assert "json" in daemon.headers[-1]["Content-Type"]


def test_result_null_es_valido(daemon, cs):
    daemon.results["job_cancel"] = None
    assert cs.call("job_cancel", {"job_id": "x"}, start=False) is None


# ── errores JSON-RPC ────────────────────────────────────────────────────────
@pytest.mark.parametrize("code,cls", [(-32601, "MethodNotFound"), (-32602, "InvalidParams"), (-32603, "ServiceError"),
                                      (-2, "ServiceError"), (-32001, "ServiceError"), (12345, "ServiceError")])
def test_codigos_de_error_mapean_a_su_clase(daemon, cs, code, cls):
    daemon.rpc_errors["search"] = (code, "mensaje del daemon", {"pista": 1})
    with pytest.raises(getattr(cs, cls)) as e:
        cs.search("x")
    assert e.value.code == code and e.value.message == "mensaje del daemon" and e.value.data == {"pista": 1}
    assert isinstance(e.value, cs.RpcError)


def test_error_menos_2_conserva_codigo_y_texto(daemon, cs):
    """El '-2' que ve el usuario: debe llegar íntegro a la UI."""
    daemon.rpc_errors["download"] = (-2, "No such file or directory: /x", None)
    with pytest.raises(cs.ServiceError) as e:
        cs.download("romsfun", "v1", "/x")
    assert e.value.code == -2 and "No such file" in str(e.value)


def test_error_que_no_es_dict(daemon, cs):
    daemon.raw = json.dumps({"jsonrpc": "2.0", "id": 1, "error": "roto"})
    with pytest.raises(cs.ServiceError) as e:
        cs.call("health", start=False)
    assert e.value.code is None and "roto" in e.value.message


def test_error_sin_message(daemon, cs):
    daemon.raw = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -5}})
    with pytest.raises(cs.ServiceError) as e:
        cs.call("health", start=False)
    assert e.value.code == -5 and e.value.message == ""


def test_error_jsonrpc_con_http_500_se_interpreta_como_rpc(daemon, cs):
    daemon.http_status = 500
    daemon.raw = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "interno"}})
    with pytest.raises(cs.ServiceError) as e:
        cs.call("health", start=False)
    assert e.value.code == -32603


# ── errores de transporte / HTTP ────────────────────────────────────────────
@pytest.mark.parametrize("status", [401, 403])
def test_http_401_403_es_tokenerror(daemon, cs, status):
    daemon.http_status = status
    with pytest.raises(cs.TokenError) as e:
        cs.call("health", start=False)
    assert str(status) in str(e.value) and not isinstance(e.value, cs.TokenMissing)


def test_token_distinto_es_401(daemon, cs):
    cs.TOKEN_FILE.write_text("OTRO")
    with pytest.raises(cs.TokenError, match="401"):
        cs.call("health", start=False)


@pytest.mark.parametrize("status", [404, 500, 502])
def test_http_error_sin_json_es_transporte(daemon, cs, status):
    daemon.http_status, daemon.raw = status, b"<html>fallo</html>"
    with pytest.raises(cs.TransportError, match=str(status)):
        cs.call("health", start=False)


def test_respuesta_no_json(daemon, cs):
    daemon.raw = "esto no es json"
    with pytest.raises(cs.TransportError, match="no es JSON"):
        cs.call("health", start=False)


@pytest.mark.parametrize("cuerpo,msg", [("[1,2]", "inválida"), ('"hola"', "inválida"), ("{}", "sin result ni error"), ('{"jsonrpc":"2.0","id":1}', "sin result ni error")])
def test_respuestas_jsonrpc_malformadas(daemon, cs, cuerpo, msg):
    daemon.raw = cuerpo
    with pytest.raises(cs.TransportError, match=msg):
        cs.call("health", start=False)


def test_timeout(daemon, cs):
    daemon.delay = 1.5
    with pytest.raises(cs.TransportError):
        cs.call("health", timeout=0.3, start=False)


def test_puerto_cerrado_sin_autoarranque(cs):
    cs.TOKEN_FILE.write_text("T")
    with pytest.raises(cs.TransportError):
        cs.call("health", start=False)


def test_puerto_cerrado_y_sin_service_py(cs):
    cs.TOKEN_FILE.write_text("T")
    with pytest.raises(cs.TransportError, match="service.py"):
        cs.call("health", start=True)


def test_sin_token_y_sin_autoarranque(daemon, cs):
    cs.TOKEN_FILE.unlink()
    with pytest.raises(cs.TokenMissing):
        cs.call("health", start=False)


def test_401_no_reintenta_ni_arranca_nada(daemon, cs):
    daemon.http_status = 401
    with pytest.raises(cs.TokenError):
        cs.call("health", start=True)
    assert len(daemon.headers) == 1      # una sola petición: 401 no es "servicio caído"


# ── envoltorios ─────────────────────────────────────────────────────────────
def test_search_solo_envia_params_opcionales_si_hay(daemon, cs):
    cs.search("Silent Hill")
    assert daemon.calls[-1] == ("search", {"query": "Silent Hill"})
    cs.search("Silent Hill", system="PlayStation", requires=["bin", "cue"])
    assert daemon.calls[-1][1] == {"query": "Silent Hill", "system": "PlayStation", "requires": ["bin", "cue"]}


def test_search_sin_query_es_invalid_params(daemon, cs):
    with pytest.raises(cs.InvalidParams):
        cs.search("")


def test_variants_params(daemon, cs):
    cs.variants("nas", "sh1")
    assert daemon.calls[-1] == ("variants", {"source": "nas", "item_id": "sh1"})
    cs.variants("nas", "sh1", requires="cue")
    assert daemon.calls[-1][1]["requires"] == "cue"


def test_download_envia_dest_dir_como_texto(daemon, cs, tmp_path):
    r = cs.download("nas", "v1", tmp_path)
    assert r["job_id"].startswith("job_") and daemon.calls[-1][1] == {"source": "nas", "variant_id": "v1", "dest_dir": str(tmp_path)}


def test_job_status_y_cancel(daemon, cs, tmp_path):
    jid = cs.download("nas", "v1", tmp_path)["job_id"]
    assert cs.job_status(jid)["state"] == "running"
    cs.job_cancel(jid)
    assert cs.job_status(jid)["state"] == "failed"
    with pytest.raises(cs.ServiceError) as e:
        cs.job_status("no-existe")
    assert e.value.code == -32001


def test_health_start_false(daemon, cs):
    assert {h["source"] for h in cs.health(start=False)} == {"nas", "viejo"}


# ── CLI ─────────────────────────────────────────────────────────────────────
def test_cli_health_y_search(daemon, cs, capsys):
    assert cs._main(["health"]) == 0
    assert "nas" in capsys.readouterr().out
    assert cs._main(["search", "Silent Hill", "PlayStation"]) == 0
    assert "Silent Hill" in capsys.readouterr().out
    assert cs._main(["variants", "nas", "sh1"]) == 0


def test_cli_uso_y_errores(daemon, cs, capsys):
    assert cs._main([]) == 2 and cs._main(["nada"]) == 2
    assert cs._main(["search"]) == 2 and cs._main(["variants", "x"]) == 2
    daemon.http_status = 401
    capsys.readouterr()
    assert cs._main(["health"]) == 1
    assert "TokenError" in capsys.readouterr().err
