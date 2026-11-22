"""v2.30: vigía del arranque por Steam, contenedores de ejecución con apt (GoW PS2) e instaladores .run."""
import stat
from pathlib import Path

import pytest

from hub import github, install, launchwatch, recipes


# ── vigía ──
def _clock(seq):
    t = {"now": 0.0}
    it = iter(seq)
    last = {"v": False}

    def alive():
        try:
            last["v"] = next(it)
        except StopIteration:
            pass
        return last["v"]
    return alive, (lambda s: t.__setitem__("now", t["now"] + s)), (lambda: t["now"])


def test_vigia_nunca_abre():
    a, sl, now = _clock([False])
    assert launchwatch.watch("x", "X", a, sl, now)[0] == "never"


def test_vigia_se_cierra_enseguida():
    a, sl, now = _clock([False, False, True, True, True, False])
    v, s = launchwatch.watch("x", "X", a, sl, now)
    assert v == "died" and s < 10


def test_vigia_aguanta_abierto():
    a, sl, now = _clock([False, True])
    assert launchwatch.watch("x", "X", a, sl, now)[0] == "ok"


# ── recetas ──
def test_receta_de_ejecucion_de_gow_usa_apt_y_ubuntu_2604():
    e = {"id": "gow-native-pc", "repo": "Vnnc1/gow-native-pc"}
    rt = recipes.runtime_for(e)
    assert rt and recipes.for_entry(e) is None, "no es una receta de compilar: la ficha no debe ofrecer «compilar en contenedor»"
    st = recipes.runtime_steps(rt, e, Path("/tmp/x"))
    assert "ubuntu:26.04" in st[0][1][-1] and "hub-gow-native-pc" in st[0][1][-1]
    cmd = st[1][1][-1]
    assert "apt-get install -y" in cmd and "dnf" not in cmd and "qml6-module-qtquick-controls" in cmd and "libsdl2-2.0-0" in cmd and "clang" in cmd


def test_gestor_de_paquetes_por_imagen():
    assert recipes.pm_of("ubuntu:26.04") == "apt" and recipes.pm_of("docker.io/library/debian:13") == "apt"
    assert recipes.pm_of("fedora:43") == "dnf" and recipes.pm_of("ubuntu:26.04", "dnf") == "dnf"


def test_la_receta_de_gta_sigue_con_dnf():
    e = {"id": "gta-vcs-recomp", "repo": "gothamor/gta-vcs-recomp"}
    rc = recipes.for_entry(e)
    assert rc and recipes.runtime_for(e) is None
    assert recipes.phase1(rc, e, Path("/tmp/x"))[1][1][-1] == "sudo dnf install -y git python3"


def test_parse_deps_entiende_apt():
    txt = "[deps] missing: foo\ninstall them with:\n  sudo apt-get install -y libfoo-dev \\\n    libbar-dev\n\n"
    assert recipes.parse_deps(txt) == ["libfoo-dev", "libbar-dev"]


# ── .run ──
def _mk(p, body):
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return p


def test_run_estilo_makeself(tmp_path):
    a = _mk(tmp_path / "juego.run", 'while [ $# -gt 0 ]; do [ "$1" = --target ] && { mkdir -p "$2"; echo ok > "$2/start-linux.sh"; exit 0; }; shift; done; exit 3\n')
    d = tmp_path / "out"
    install.extract(a, d)
    assert (d / "start-linux.sh").is_file() and not (d / ".hub-run-tmp").exists() and not (d / ".hub-run-home").exists()


def test_run_con_destino_por_argumento(tmp_path):
    a = _mk(tmp_path / "gow.run", '[ "$1" = --noexec ] && exit 2\n[ -e "$1" ] && exit 4\nmkdir -p "$1/launcher" && echo x > "$1/launcher/gow"\n')
    d = tmp_path / "out"
    (d).mkdir()
    (d / "mio.txt").write_text("no me pises")
    install.extract(a, d)
    assert (d / "launcher" / "gow").is_file() and (d / "mio.txt").read_text() == "no me pises"


def test_run_que_falla_lo_dice(tmp_path):
    a = _mk(tmp_path / "malo.run", "echo roto >&2; exit 1\n")
    with pytest.raises(OSError, match="no pude extraer"):
        install.extract(a, tmp_path / "o")


def test_run_se_reconoce_pero_se_prefiere_el_tar():
    assert github.classify("gow-native-pc-linux-x86_64-ubuntu26.04-experimental.run")["kind"] == "run"
