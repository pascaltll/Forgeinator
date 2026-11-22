"""v2.90 · motor de temas, fase A: el motor reproduce EXACTAMENTE los temas del Hub y los publica en appearance.json."""
import json, sys
from pathlib import Path
import pytest
from conftest import HUB_SRC  # noqa: E402
sys.path.insert(0, str(HUB_SRC))
from hub import themes_fam as tf
from hub.themes import legacy, publish
PAIRS = [(f, p[0]) for f, fam in tf.FAMILIES.items() for p in fam["pals"]]


def _legacy_dicts():
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from hub import ui
    return ui._LEG


def test_catalogo_completo():
    assert len(PAIRS) == 59 and len(legacy.FAMILIES) == 15 and tuple(legacy.ORDER) == tuple(tf.ORDER)
    assert legacy.LEGACY == tf.LEGACY


@pytest.mark.parametrize("fam,pal", PAIRS)
def test_build_identico_a_themes_fam(fam, pal):
    leg = _legacy_dicts()
    for bg in (None, "__x__", *tf.FAMILIES[fam]["bgs"]):
        assert legacy.build(fam, pal, bg) == tf.build(leg, fam, pal, bg), (fam, pal, bg)


def test_nombres_antiguos_y_desconocidos():
    leg = _legacy_dicts()
    for n in ("dark", "light", "aurora", "pixel", "retro16", "no-existe", None):
        assert legacy.normalize(n) == tf.normalize(n)
        assert legacy.build(n) == tf.build(leg, n)
    assert legacy.normalize("cristal", "no-hay") == tf.normalize("cristal", "no-hay")


@pytest.mark.parametrize("fam,pal", PAIRS)
def test_contraste_del_motor(fam, pal):
    assert legacy.check_contrast(legacy.build(fam, pal)) == [], (fam, pal)


def test_contraste_detecta_color_malo():
    c = dict(legacy.build("limpio", "oscuro")); c["TXT"] = c["BG"]
    assert legacy.check_contrast(c)


def test_apariencia_conserva_tipografia_sonido_inicio():
    a = legacy.appearance("pixel", "gameboy")
    assert a["typography"]["font"] == "vt323" and a["audio"]["profile"] == "chip"
    assert a["layout"]["home"] == "slots" and a["geometry"]["outline"] is True
    assert len(a["colors"]) >= 11 and "ON_ACC" in a["colors"]
    t = legacy.appearance("fosforo")
    assert t["typography"]["font"] and t["motion"]["options"]


def test_catalogo_para_la_pantalla_de_personalizar():
    cat = legacy.catalog()
    assert [c["id"] for c in cat] == list(tf.ORDER)
    assert sum(len(c["palettes"]) for c in cat) == 59
    assert all(c["backgrounds"] and c["palettes"][0]["colors"]["ACC"] for c in cat)


def test_publicar_appearance_json(tmp_path):
    d = publish.publish(tmp_path / "appearance.json", "neon", "lima", "stars")
    j = json.loads((tmp_path / "appearance.json").read_text())
    assert j == json.loads(json.dumps(d)) and j["family"] == "neon" and j["motion"]["background"] == "stars"


def test_hub_publica_al_cambiar_de_tema(tmp_path, monkeypatch):
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from hub import ui, config
    monkeypatch.setattr(config, "DATA", tmp_path)
    class U:  # solo lo que usa _publish_look
        cfg = {"theme": "cristal"}
        _pal = lambda s: "aurora"
        _bg = lambda s: "silk"
        _layout = lambda s: None
        _ar_load_last = ui.UI._ar_load_last
    ui.UI._publish_look(U())
    j = json.loads((tmp_path / "appearance.json").read_text())
    assert j["family"] == "cristal" and j["palette"] == "aurora"
