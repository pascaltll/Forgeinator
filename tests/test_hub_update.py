"""v1.81: actualización por zip (bin/hub-update): instala, verifica, hace copia y vuelve atrás si falla."""
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from conftest import HUB_SRC

UPD = HUB_SRC / "bin" / "hub-update"

INSTALLER_OK = '''#!/usr/bin/env bash
set -e
[ -n "${FORCE:-}" ] || exit 1
mkdir -p "$HUB_DIR/hub"
echo "VALUE = 'nuevo'" > "$HUB_DIR/hub/mod.py"
echo "%s" > "$HUB_DIR/VERSION"
'''
INSTALLER_BAD_SYNTAX = INSTALLER_OK.replace("VALUE = 'nuevo'", "def (((")
INSTALLER_FAIL = "#!/usr/bin/env bash\necho roto >&2\nexit 3\n"


@pytest.fixture
def env(tmp_path):
    home, dest = tmp_path / "home", tmp_path / "hub"
    (dest / "hub").mkdir(parents=True)
    (dest / "data").mkdir()
    (dest / "main.py").write_text("print('hola')\n")
    (dest / "hub" / "mod.py").write_text("VALUE = 'viejo'\n")
    (dest / "VERSION").write_text("1.80\n")
    (dest / "data" / "mis_datos.json").write_text("{}")
    (home / "Games" / "actualizaciones").mkdir(parents=True)
    e = dict(os.environ, HOME=str(home), HUB_DIR=str(dest), HUB_UPDATE_DIRS="")
    return home, dest, e


def run(env, *args):
    return subprocess.run([sys.executable, str(UPD), *args], env=env[2], capture_output=True, text=True)


def mkzip(home, ver, installer, sums="ok", name=None, extra=None):
    d = home / "Games" / "actualizaciones"
    sh = f"install-hub-v{ver}.sh"
    z = d / (name or f"recomp-hub-update-v{ver}.zip")
    with zipfile.ZipFile(z, "w") as f:
        f.writestr(sh, installer)
        if sums == "ok":
            f.writestr("SHA256SUMS", f"{hashlib.sha256(installer.encode()).hexdigest()}  {sh}\n")
        elif sums == "bad":
            f.writestr("SHA256SUMS", f"{'0' * 64}  {sh}\n")
        for n, c in (extra or {}).items():
            f.writestr(n, c)
    return z


def test_instala_el_zip_mas_nuevo_y_guarda_todo(env):
    home, dest, _ = env
    z = mkzip(home, "1.81", INSTALLER_OK % "1.81")
    r = run(env)
    assert r.returncode == 0 and "1.80 → 1.81" in r.stdout, r.stdout + r.stderr
    assert (dest / "VERSION").read_text().strip() == "1.81"
    assert "nuevo" in (dest / "hub" / "mod.py").read_text()
    assert (dest / "data" / "mis_datos.json").exists()                       # los datos no se tocan
    assert list((dest / "data" / "backups").glob("hub-1.80-*.tgz"))
    assert not z.exists() and (home / "Games" / "actualizaciones" / "aplicadas" / z.name).exists()
    assert json.loads((dest / "data" / "update.json").read_text())["ok"] is True


def test_al_dia_no_hace_nada(env):
    home, dest, _ = env
    mkzip(home, "1.80", INSTALLER_OK % "1.80")
    r = run(env)
    assert "al día" in r.stdout and "viejo" in (dest / "hub" / "mod.py").read_text()


def test_elige_la_version_mas_alta_numericamente(env):
    home, dest, _ = env
    mkzip(home, "1.9", INSTALLER_OK % "1.9")
    mkzip(home, "1.100", INSTALLER_OK % "1.100")
    run(env)
    assert (dest / "VERSION").read_text().strip() == "1.100"


def test_si_el_instalador_falla_vuelve_atras(env):
    home, dest, _ = env
    mkzip(home, "1.81", INSTALLER_FAIL)
    r = run(env)
    assert r.returncode == 2 and "restauré" in r.stdout
    assert (dest / "VERSION").read_text().strip() == "1.80" and "viejo" in (dest / "hub" / "mod.py").read_text()
    assert json.loads((dest / "data" / "update.json").read_text())["ok"] is False


def test_si_el_codigo_nuevo_no_compila_vuelve_atras(env):
    home, dest, _ = env
    mkzip(home, "1.81", INSTALLER_BAD_SYNTAX % "1.81")
    r = run(env)
    assert r.returncode == 2
    assert "viejo" in (dest / "hub" / "mod.py").read_text() and (dest / "VERSION").read_text().strip() == "1.80"


def test_sha_incorrecto_no_cambia_nada(env):
    home, dest, _ = env
    z = mkzip(home, "1.81", INSTALLER_OK % "1.81", sums="bad")
    r = run(env)
    assert r.returncode == 2 and "SHA-256" in r.stdout
    assert (dest / "VERSION").read_text().strip() == "1.80" and z.exists()


def test_zip_sin_sums_avisa_pero_instala(env):
    home, dest, _ = env
    mkzip(home, "1.81", INSTALLER_OK % "1.81", sums="none")
    r = run(env)
    assert "no trae SHA256SUMS" in r.stdout and (dest / "VERSION").read_text().strip() == "1.81"


def test_rechaza_nombres_peligrosos(env):
    home, dest, _ = env
    mkzip(home, "1.81", INSTALLER_OK % "1.81", sums="none", extra={"../fuera.txt": "x"})
    r = run(env)
    assert r.returncode == 2 and "peligroso" in r.stdout
    assert not (home / "Games" / "fuera.txt").exists() and (dest / "VERSION").read_text().strip() == "1.80"


def test_deja_los_tests_en_hub_test_sh(env):
    home, dest, _ = env
    mkzip(home, "1.81", INSTALLER_OK % "1.81", extra={"install-hub-tests-v26.sh": "#!/bin/bash\necho t\n"})
    run(env)
    assert (home / "Games" / "hub_test.sh").read_text().startswith("#!/bin/bash")


def test_auto_respeta_el_ajuste_y_es_silencioso(env):
    home, dest, _ = env
    mkzip(home, "1.81", INSTALLER_OK % "1.81")
    (dest / "data" / "settings.json").write_text(json.dumps({"auto_update": False}))
    r = run(env, "--auto")
    assert r.stdout == "" and (dest / "VERSION").read_text().strip() == "1.80"
    (dest / "data" / "settings.json").write_text(json.dumps({"auto_update": True}))
    r = run(env, "--auto")
    assert "✓ Forgeinator" in r.stdout and (dest / "VERSION").read_text().strip() == "1.81"


def test_sh_suelto_y_check_y_rollback(env):
    home, dest, _ = env
    d = home / "Games" / "actualizaciones"
    (d / "install-hub-v1.81.sh").write_text(INSTALLER_OK % "1.81")
    assert "Instalaría" in run(env, "--check").stdout and (dest / "VERSION").read_text().strip() == "1.80"
    run(env)
    assert (dest / "VERSION").read_text().strip() == "1.81"
    r = run(env, "--rollback")
    assert "Restaurado" in r.stdout and (dest / "VERSION").read_text().strip() == "1.80"
    assert "viejo" in (dest / "hub" / "mod.py").read_text()
