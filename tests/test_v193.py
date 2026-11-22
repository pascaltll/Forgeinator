"""v1.93: pruebas aisladas del mando real, Inicio del Prototipo (dónde están tus archivos + fila de plataformas),
cruceta por columnas (barra lateral ≠ contenido) y aviso de bibliotecas que faltan antes de lanzar."""
import os
import stat
import types

import pytest

from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio, run  # noqa: F401

pygame = pytest.importorskip("pygame")


# ── el mando real no entra en las pruebas ────────────────────
def test_las_pruebas_no_leen_el_mando_real(ui):
    """En el Ally, Hub lee el mando de /dev/input: tocarlo (o la deriva del stick) mientras corrían las pruebas abría menús y fallaban."""
    assert os.environ.get("HUB_NO_PAD") == "1" and ui.no_pad and ui.sdlc is None


def test_sin_hub_no_pad_si_arranca_el_mando(H, monkeypatch):
    llamadas = []
    monkeypatch.setenv("HUB_NO_PAD", "0")
    monkeypatch.setattr(H.gamepad, "start", lambda *a, **k: llamadas.append(1))
    u = H.UI()
    try:
        assert llamadas == [1] and not u.no_pad
    finally:
        u.running = False


# ── Inicio del Prototipo ─────────────────────────────────────
@pytest.fixture
def con_instalados(ui, monkeypatch):
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda e: dict(real(e), installed=True, version="1.0", launcher_id=e["id"], dir="/tmp/x") if ui.entries.index(e) < 3 else real(e))
    ui._inst_c = None
    ui._hp_c = (None,)
    ui.set_look(theme="prototipo", fx="glass")
    ui.go_tab("home")
    run(ui, 4)
    return ui


def test_inicio_prototipo_tiene_interruptor_y_plataformas(con_instalados):
    ui = con_instalados
    ks = {str(w.key) for w in ui.widgets}
    assert {"hm_local", "hm_server", "hero"} <= ks
    plats = [k for k in ks if k.startswith("hp:")]
    assert plats, "falta la fila de plataformas"
    orden, cnt, ins = ui.home_platforms()
    assert ins[orden[0]] >= max(ins.values()), "primero las plataformas donde tienes juegos"


def test_interruptor_cambia_donde_se_buscan_los_archivos(con_instalados):
    ui = con_instalados
    ui.cfg["file_mode"] = "local"
    ui.focus = "hm_server"
    ui.act("A")
    assert ui.cfg["file_mode"] == "server"
    ui.focus = "hm_local"
    ui.act("A")
    assert ui.cfg["file_mode"] == "local"


def test_tocar_una_plataforma_abre_explorar_filtrado(con_instalados):
    ui = con_instalados
    pl = ui.home_platforms()[0][0]
    ui.focus = "hp:" + pl
    ui.act("A")
    assert (ui.tab, ui.explore, ui.filter) == ("games", "list", pl)


def test_cruceta_del_inicio_prototipo(con_instalados):
    ui = con_instalados
    ui.focus = "hero"
    ui.act("UP")
    assert ui.focus in ("hm_local", "hm_server"), "arriba del héroe está el interruptor, no la barra lateral"
    ui.act("DOWN")
    assert ui.focus == "hero"
    ui.act("DOWN")
    assert str(ui.focus).startswith("hp:")
    ui.act("DOWN")
    assert str(ui.focus).startswith("home:"), "de las plataformas a «Mis juegos» sin saltarse la fila"


def test_desde_la_barra_lateral_arriba_abajo_sigue_en_la_barra(ui):
    ui.set_look(theme="prototipo", fx="perf")
    ui.go_tab("home")
    run(ui, 3)
    ui.focus = "tab:home"
    ui.act("DOWN")
    assert ui.focus == "tab:games"


# ── bibliotecas que faltan ───────────────────────────────────
def _juego(tmp_path, monkeypatch, toml):
    from hub import config
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    (config.LAUNCHER / "games").mkdir(parents=True)
    (config.LAUNCHER / "bin").mkdir()
    d = tmp_path / "SilentHill"
    d.mkdir()
    b = d / "SilentHillPC"
    b.write_bytes(b"\x7fELF")
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    (config.LAUNCHER / "games" / "sh.toml").write_text(toml.replace("@DIR@", str(d)))
    play = config.LAUNCHER / "bin" / "play"
    play.write_text("#!/bin/sh\n")
    return b


LDD = "\tlinux-vdso.so.1 (0x0)\n\tlibjpeg.so.8 => not found\n\tlibSDL2-2.0.so.0 => /usr/lib64/libSDL2-2.0.so.0 (0x0)\n\tlibbundled.so.1 => not found\n"
TOML = 'id = "sh"\nname = "Silent Hill"\ninstall_dir = "@DIR@"\n\n[run]\ntype = "binary"\nexe = "SilentHillPC"\ncwd = "."\n'


@pytest.fixture
def ldd_falso(monkeypatch):
    from hub import launchlog as L
    L._LIBS.clear()
    monkeypatch.setattr(L.shutil, "which", lambda n: "/usr/bin/ldd" if n == "ldd" else None)
    monkeypatch.setattr(L, "_run", lambda cmd, timeout=6: LDD if cmd[0] == "ldd" else "")
    return L


def test_binario_del_toml_que_escribe_hub(tmp_path, monkeypatch):
    """El informe buscaba «exec=», pero Hub escribe [run] exe = … → nunca miraba el binario ni ldd."""
    from hub import launchlog as L
    b = _juego(tmp_path, monkeypatch, TOML)
    assert L.binary_of("sh") == b
    assert L.binary_of("no-existe") is None


def test_bibliotecas_que_faltan_sin_las_que_trae_el_port(tmp_path, monkeypatch, ldd_falso):
    b = _juego(tmp_path, monkeypatch, TOML)
    (b.parent / "lib").mkdir()
    (b.parent / "lib" / "libbundled.so.1").write_bytes(b"")
    assert ldd_falso.missing_libs(b) == ["libjpeg.so.8"]
    assert any("libjpeg.so.8" in ln for ln in ldd_falso.diagnose("sh"))


def test_jugar_avisa_antes_de_lanzar_y_deja_lanzar_igual(H, ui, tmp_path, monkeypatch, ldd_falso):
    _juego(tmp_path, monkeypatch, TOML)
    lanzados = []
    monkeypatch.setattr(H.subprocess, "Popen", lambda *a, **k: lanzados.append(a) or types.SimpleNamespace(pid=4242, poll=lambda: None), raising=False)
    monkeypatch.setattr(ui, "inst", lambda e: {"installed": True, "launcher_id": "sh", "version": "1", "dir": "x"})
    ui.libs_ok.discard("sh")
    ui.cfg["libs_ok"] = []
    monkeypatch.setattr(H.config, "save_settings", lambda s: None)
    ui.play_pr = ui.exit_at = None
    e = {"id": "sh", "name": "Silent Hill"}
    try:
        ui.play(e)
        assert ui.modal and ui.modal["title"] == "Faltan bibliotecas del sistema" and "libjpeg.so.8" in ui.modal["msg"]
        assert not lanzados, "no se lanza a ciegas"
        dict(ui.modal["options"])["LANZAR DE TODOS MODOS"]()
        assert lanzados and ui.modal is None
    finally:
        ui.play_pr = None
        ui.game_pids.clear()
        ui.cfg["libs_ok"] = []


def test_la_ficha_muestra_el_aviso(H, ui, tmp_path, monkeypatch, ldd_falso):
    ui.set_look(theme="dark", fx="perf")
    e = ui.entries[0]
    real = ui.inst
    monkeypatch.setattr(ui, "inst", lambda x: dict(real(x), installed=True, version="1.0", launcher_id="sh", dir="/tmp/x") if x is e else real(x))
    ui._inst_c = None
    ui.libchk["sh"] = ["libjpeg.so.8"]
    ui.cfg["libs_ok"] = []
    textos = []
    orig = ui.text
    monkeypatch.setattr(ui, "text", lambda s, *a, **k: (textos.append(str(s)), orig(s, *a, **k))[1])
    ui.go_tab("games")
    ui.open_detail(e)
    run(ui, 3)
    ui.libchk.pop("sh", None)
    assert any("Faltan bibliotecas del sistema: libjpeg.so.8" in t for t in textos)
