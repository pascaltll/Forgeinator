"""v3.24 · E3: errores guardados con contexto, informe con los secretos tapados, zip e issue de GitHub por enlace."""
import json
import sys
import time
import urllib.parse
import zipfile
from pathlib import Path

import pytest

from hub import config, report

TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
OBSC = "Xk9_obscured_Pass_77"
COOKIE = "c00kieSessionValue_5566"
SGDB = "0123456789abcdef0123456789abcdef"
ENVSEC = "envSecretValue_4242"
PLAIN = "MiClaveDelNAS!2024"


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "home" / "carlitos"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(report.getpass, "getuser", lambda: "carlitos")
    monkeypatch.setattr(report.socket, "gethostname", lambda: "allyconsola")
    for k, sub in (("DATA", "data"), ("CONFIG", "conf"), ("STATE", "state"), ("LAUNCHER", "launcher")):
        d = tmp_path / sub
        d.mkdir()
        monkeypatch.setattr(config, k, d)
    (config.CONFIG / "credentials.json").write_text(json.dumps({"token": TOKEN, "login": "pascaltll"}))
    (config.CONFIG / "remotes-secrets.json").write_text(json.dumps({"r1": {"pass": OBSC}}))
    (config.DATA / "github-cookies.json").write_text(json.dumps([{"name": "user_session", "value": COOKIE}]))
    (config.LAUNCHER / "state").mkdir()
    (config.LAUNCHER / "state" / ".sgdb_key").write_text(SGDB + "\n")
    monkeypatch.setenv("MY_API_TOKEN", ENVSEC)
    report.CTX.clear()
    report._last_sig["sig"] = None
    log = [f"INFO arranque en {home}/Games/forgeinator y /var/home/carlitos/x",
           f"INFO usando {TOKEN} para github", f"INFO cookie del navegador {COOKIE}", f"INFO rclone pass {OBSC}",
           f"INFO sgdb {SGDB}", f"INFO env {ENVSEC}", "INFO webdav https://carlos:" + PLAIN + "@nas.local/dav",
           "INFO Authorization: Bearer abcdefghijklmnop1234", "INFO password=" + PLAIN, "INFO servidor 192.168.1.40, local 127.0.0.1",
           "INFO equipo allyconsola listo", "ERROR algo falló"]
    (config.STATE / "hub.log").write_text("\n".join(log) + "\n")
    return home


SECRETS = (TOKEN, OBSC, COOKIE, SGDB, ENVSEC, PLAIN, "abcdefghijklmnop1234", "192.168.1.40", "carlitos", "allyconsola")


def _boom():
    try:
        raise RuntimeError(f"fallo con {TOKEN} en /home/carlitos/Games")
    except RuntimeError:
        return sys.exc_info()


def _clean(text):
    for s in SECRETS:
        assert s not in text, s


def test_ningun_secreto_sale_en_el_informe_el_zip_ni_el_issue(env, tmp_path):
    report.CTX.update(pantalla="settings", tema="forja")
    p = report.record_crash(*_boom(), where="python", fatal=True)
    assert p and p.exists()
    rep = report.build("error", "Al abrir con mi token " + TOKEN + " se cerró")
    _clean(rep["md"])
    _clean(rep["title"])
    for v in rep["files"].values():
        _clean(v)
    assert "RuntimeError" in rep["md"] and "ERROR algo falló" in rep["md"]
    assert "~/Games/forgeinator" in rep["md"] and "/var/home/<usuario>/x" in rep["md"]
    assert "127.0.0.1" in rep["md"] and "<ip>" in rep["md"] and "<equipo>" in rep["md"]
    assert "pantalla = settings" in rep["md"] and "tema = forja" in rep["md"]
    z = report.save_zip(rep, tmp_path / "inf.zip")
    with zipfile.ZipFile(z) as zf:
        assert "informe.md" in zf.namelist()
        for n in zf.namelist():
            _clean(zf.read(n).decode())
    url = report.issue_url(rep)
    assert url.startswith("https://github.com/pascaltll/Forgeinator/issues/new?")
    _clean(urllib.parse.unquote(url))
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert q["labels"] == ["bug"] and q["title"][0].startswith("[Fallo] ")


def test_sugerencia_sin_registros(env):
    rep = report.build("idea", "Que se puedan ordenar los juegos por horas jugadas")
    assert rep["files"] == {} and "hub.log" not in rep["md"]
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(report.issue_url(rep)).query)
    assert q["labels"] == ["enhancement"] and q["title"][0].startswith("[Idea] Que se puedan")


def test_issue_largo_se_recorta_y_cierra_el_bloque(env):
    (config.STATE / "hub.log").write_text("\n".join(f"INFO línea {i} " + "x" * 80 for i in range(3000)))
    rep = report.build("error", "largo", log_lines=2000)
    url = report.issue_url(rep)
    assert len(url) <= report.URL_MAX
    body = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["body"][0]
    assert "recortado" in body and body.count("```") % 2 == 0
    assert len(rep["md"]) > len(body)              # el zip conserva el informe completo


def test_errores_guardados_avisos_y_limite(env, monkeypatch):
    assert report.unseen_fatal() is None
    e = _boom()
    assert report.record_crash(*e, where="fotograma", fatal=False)
    assert report.record_crash(*e, where="fotograma", fatal=False) is None     # misma pila: no se repite
    assert report.unseen_fatal() is None                                        # los de fotograma no avisan al arrancar
    time.sleep(0.01)
    assert report.record_crash(*e, fatal=True)
    r = report.unseen_fatal()
    assert r and r["fatal"] and r["version"] == config.VERSION
    report.mark_seen()
    assert report.unseen_fatal() is None
    monkeypatch.setattr(report, "MAX_CRASHES", 3)
    for i in range(6):
        report._last_sig["sig"] = None
        report.record_crash(*e, fatal=True)
        time.sleep(0.002)
    assert len(report.crashes()) == 3


def test_registrar_un_error_nunca_rompe(env, monkeypatch):
    monkeypatch.setattr(report, "crash_dir", lambda: Path("/proc/no/se/puede"))
    assert report.record_crash(*_boom()) is None


def test_redactor_no_tapa_texto_normal(env):
    r = report.Redactor()
    t = "Versión 3.24 · pantalla settings · keyboard ok · 1486 passed · /usr/lib/python3"
    assert r(t) == t


def test_interfaz_menu_vista_previa_zip_y_github(env, monkeypatch):
    from test_temas_y_fuzz import H, run  # noqa: F401
    import hub.ui as U
    ui = U.UI.__new__(U.UI)
    ui.cfg = dict(config.DEFAULT_SETTINGS)
    ui.modal = ui.focus = None
    ui._io_gen = 0
    ui.views = {}
    msgs, urls = [], []
    ui.toast = msgs.append
    ui.use_steam_kb = lambda: False
    ui.open_url = urls.append
    report.record_crash(*_boom(), fatal=True)
    ui.report_menu()
    opts = dict(ui.modal["options"])
    assert any("cerró el Hub" in k for k in opts) and "ENVIAR UNA SUGERENCIA" in opts
    ui.modal = None
    opts["INFORMAR DE UN ERROR"]()
    m = ui.modal
    assert m["kind"] == "osk"
    ui.modal = None
    m["cb"]("se colgó al cambiar de tema")
    t0 = time.time()
    while not (ui.modal and ui.modal.get("kind") == "log") and time.time() - t0 < 10:
        q = ui.__dict__.get("_uiq")
        while q:
            q.pop(0)()
        time.sleep(0.02)
    job = ui.modal["job"]
    assert [a[1] for a in job.actions][:2] == ["GUARDAR ZIP", "ABRIR ISSUE EN GITHUB"]
    assert "se colgó al cambiar de tema" in "\n".join(job.log)
    _clean("\n".join(job.log))
    ui.report_save()
    zips = list(env.glob("forgeinator-informe-*.zip"))
    assert zips and "Guardado en" in msgs[-1]
    ui.report_github()
    assert urls and urls[-1].startswith("https://github.com/pascaltll/Forgeinator/issues/new?")
