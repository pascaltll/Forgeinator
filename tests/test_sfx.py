"""Sonidos de la interfaz: síntesis sana (cortos, sin clics, sin silencio), degradación si no hay audio y enganches en mando/táctil/ajustes."""
import math
import struct
import wave

import pytest

from hub import sfx


def samples(b):
    return struct.unpack("<%dh" % (len(b) // 2), b)


@pytest.fixture(scope="module")
def synth():
    return sfx.synth()


def test_estan_los_seis_sonidos(synth):
    assert set(synth) == set(sfx.NAMES) and all(len(v) > 0 and len(v) % 2 == 0 for v in synth.values())


@pytest.mark.parametrize("name,max_ms", [("move", 60), ("tab", 90), ("confirm", 160), ("back", 160), ("open", 160), ("error", 160)])
def test_son_cortos(synth, name, max_ms):
    ms = len(synth[name]) / 2 / sfx.RATE * 1000
    assert 20 <= ms <= max_ms, f"{name} dura {ms:.0f} ms"


def test_no_son_silencio_ni_saturan_ni_hacen_clic(synth):
    for name, b in synth.items():
        s = samples(b)
        pico = max(abs(v) for v in s) / 32767
        assert 0.15 <= pico <= 0.9, f"{name}: pico {pico:.2f}"
        assert abs(s[-1]) < 600, f"{name}: termina cortando en seco (clic)"
        assert abs(s[0]) < 3000, f"{name}: empieza con un salto"
        assert not any(math.isnan(v) for v in s)


def test_el_tono_de_mover_sube_y_el_de_volver_baja(synth):
    def freq(b, a, z):
        s = samples(b)[a:z]
        cruces = sum(1 for i in range(1, len(s)) if s[i - 1] < 0 <= s[i])
        return cruces * sfx.RATE / max(1, len(s))
    c, b = synth["confirm"], synth["back"]
    assert freq(c, 3000, 5200) > freq(c, 0, 1800), "aceptar: segunda nota más aguda"
    assert freq(b, 2500, 4500) < freq(b, 0, 1500), "volver: segunda nota más grave"


def test_la_sintesis_es_rapida():
    import time
    t = time.perf_counter()
    sfx.synth()
    assert time.perf_counter() - t < 1.5


class FakeSnd:
    def __init__(self):
        self.vol, self.n = None, 0

    def set_volume(self, v):
        self.vol = v

    def play(self):
        self.n += 1


def armado(**kw):
    s = sfx.Sfx(**kw)
    s.tried = s.ok = True
    s.sounds = {n: FakeSnd() for n in sfx.NAMES}
    return s


def test_desactivado_o_sin_volumen_no_suena():
    assert armado(enabled=False).play("move") is False
    assert armado(volume=0).play("move") is False


def test_aplica_el_volumen_y_cuenta_lo_reproducido():
    s = armado(volume=0.25)
    assert s.play("confirm") and s.sounds["confirm"].vol == 0.25 and s.sounds["confirm"].n == 1 and s.played == 1
    s.set_volume(7)
    assert s.volume == 1.0
    s.set_volume(-1)
    assert s.volume == 0.0


def test_no_se_amontonan_las_repeticiones_rapidas():
    s = armado()
    assert s.play("move") is True and s.play("move") is False
    assert s.sounds["move"].n == 1
    assert s.play("confirm") is True, "otro sonido distinto no se bloquea"


def test_nombre_desconocido_no_rompe():
    assert armado().play("no-existe") is False


def test_sin_audio_se_queda_mudo_y_no_lanza(monkeypatch, capsys):
    pygame = pytest.importorskip("pygame")

    def boom(*a, **k):
        raise pygame.error("no hay dispositivo de audio")
    monkeypatch.setattr(pygame.mixer, "init", boom)
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    s = sfx.Sfx()
    assert s.play("move") is False and s.ok is False and s.tried is True
    assert "[sonido] desactivado" in capsys.readouterr().err
    assert s.play("confirm") is False, "no reintenta en cada pulsación"


def test_un_archivo_tuyo_sustituye_al_generado(tmp_path):
    pygame = pytest.importorskip("pygame")
    w = wave.open(str(tmp_path / "move.wav"), "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(44100)
    w.writeframes(struct.pack("<%dh" % 4410, *([1000] * 4410)))     # 100 ms exactos
    w.close()
    (tmp_path / "back.ogg").write_bytes(b"esto no es un ogg")        # estropeado: se ignora y se usa el generado
    s = sfx.Sfx(folder=tmp_path)
    s._init()
    assert s.ok and abs(s.sounds["move"].get_length() - 0.1) < 0.01
    assert s.sounds["back"].get_length() < 0.2 and s.sounds["confirm"].get_length() > 0.1


@pytest.fixture(scope="module")
def _ui_unica():
    pytest.importorskip("pygame")
    import hub.ui as H
    u = H.UI()
    yield u
    u.running = False


@pytest.fixture()
def ui(_ui_unica):
    u = _ui_unica
    u.rec = []
    u.sfx = type("R", (), {"enabled": True, "volume": 0.5, "tried": True, "play": lambda self, n: u.rec.append(n) or True,
                           "set_volume": lambda self, v: setattr(self, "volume", v), "_init": lambda self: None})()
    u.go_tab("home")
    u.rec.clear()
    return u


def frames(u, n=3):
    for _ in range(n):
        u.frame()


@pytest.mark.ui
def test_mover_el_foco_suena_solo_si_cambia(ui):
    ui.go_tab("settings")
    frames(ui)
    ui.rec.clear()
    ui.act("DOWN")
    ui.act("DOWN")
    assert ui.rec == ["move", "move"]
    ui.rec.clear()
    for _ in range(40):                 # contra el borde: cuando el foco ya no cambia, no debe sonar
        ui.act("DOWN")
    movidas = len(ui.rec)
    ui.rec.clear()
    ui.act("DOWN")
    assert movidas < 40 and ui.rec == [], "al llegar al final el foco no cambia y no suena"


@pytest.mark.ui
def test_aceptar_y_volver_suenan_con_sus_sonidos(ui):
    ui.go_tab("settings")
    frames(ui)
    ui.act("DOWN")
    ui.rec.clear()
    w = next(w for w in ui.widgets if w.key == ui.focus)
    w.cb = lambda: None
    ui.act("A")
    assert ui.rec == ["confirm"]
    ui.rec.clear()
    ui.act("B")                         # en Ajustes no hay nada que cerrar: no debe sonar
    ui.go_tab("games")
    ui.explore = "list"
    ui.rec.clear()
    ui.act("B")
    assert ui.explore == "cats" and ui.rec == ["back"]


@pytest.mark.ui
def test_abrir_un_menu_suena_a_abrir_y_cerrarlo_a_volver(ui):
    ui.go_tab("settings")
    frames(ui)
    ui.act("DOWN")
    w = next(w for w in ui.widgets if w.key == ui.focus)
    w.cb = lambda: ui.confirm("¿Seguro?", "msg", lambda: None)
    ui.rec.clear()
    ui.act("A")
    assert ui.modal and ui.rec == ["open"]
    ui.rec.clear()
    ui.act("B")
    assert ui.modal is None and ui.rec == ["back"]


@pytest.mark.ui
def test_bumpers_cambian_de_seccion_con_sonido_de_pestana(ui):
    ui.rec.clear()
    ui.act("RB")
    assert ui.tab != "home" and ui.rec == ["tab"]


@pytest.mark.ui
def test_los_ajustes_de_sonido_se_guardan(ui, monkeypatch):
    from hub import config
    guardado = {}
    monkeypatch.setattr(config, "save_settings", lambda c: guardado.update(c))
    ui.sfx.enabled = True
    ui.toggle_sfx()
    assert ui.sfx.enabled is False and guardado["sounds"] is False
    ui.toggle_sfx()
    assert ui.sfx.enabled is True and guardado["sounds"] is True and "confirm" in ui.rec
    ui.sfx.volume = 0.5
    ui.cycle_sfx_volume()
    assert ui.sfx.volume == 0.75 and guardado["sound_volume"] == 0.75
    ui.cycle_sfx_volume()
    ui.cycle_sfx_volume()
    assert ui.sfx.volume == 0.25, "tras el máximo vuelve al mínimo"


@pytest.mark.ui
def test_ajustes_muestra_las_filas_de_sonido(ui):
    ui.go_tab("settings")
    ui.settings_open("look")          # v2.0: los sonidos están en «Aspecto y control»
    frames(ui)
    keys = [w.key for w in ui.widgets]
    assert "sfx" in keys and "sfxv" in keys
