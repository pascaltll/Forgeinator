"""v2.15: recetas «compilar en contenedor» (GTA VCS), build nativo registrado como versión de Linux y «ejecutar en: sistema / contenedor»."""
import subprocess
import tomllib

import pytest

from test_v195 import juego, _t  # noqa: F401
from test_temas_y_fuzz import H, ui, sin_efectos_reales, estado_limpio  # noqa: F401
from test_v212 import _exe

pygame = pytest.importorskip("pygame")

SALIDA = """[deps] no CMake 3.21 or newer found: the build downloads one (cmake-4.4.5-linux-x86_64.tar.gz)
[deps] missing: pkg-config
[deps] missing: clang 19+ / lld / llvm
[deps] install them with:
    sudo dnf install pkgconf-pkg-config glslang ffmpeg-free-devel libX11-devel wayland-devel
l libXScrnSaver-devel clang lld llvm
[deps] missing: Vulkan headers (launcher)
[deps] missing: fonts (launcher)
[deps] install them with:
    sudo dnf install vulkan-headers vulkan-loader-devel freetype-devel fontconfig-devel
"""


def test_receta_se_encuentra_por_repo_o_id():
    from hub import recipes
    r = recipes.for_entry({"id": "x", "repo": "GothaMor/GTA-VCS-recomp"})
    assert r and r["container"]["image"] == "fedora:43" and r["output"]["exe"] == "build/vcs"
    assert recipes.for_entry({"id": "gta-vcs-recomp"})
    assert recipes.for_entry({"id": "otro", "repo": "a/b"}) is None
    assert recipes.container_name(r, {"id": "gta-vcs-recomp"}) == "hub-gta-vcs-recomp"


def test_parse_deps_descarta_lo_del_lanzador_grafico():
    from hub import recipes
    p = recipes.parse_deps(SALIDA)
    assert "ffmpeg-free-devel" in p and "clang" in p and "llvm" in p
    assert "vulkan-headers" not in p and "freetype-devel" not in p
    assert len(p) == len(set(p))


def test_enlace_al_iso_nunca_pisa_un_archivo_real(tmp_path):
    from hub import recipes
    rc = recipes.for_entry({"id": "gta-vcs-recomp"})
    src = tmp_path / "linux"
    src.mkdir()
    iso = tmp_path / "GTA_VCS.iso"
    iso.write_bytes(b"x")
    nm = rc["disc"]["name"]
    (src / nm).symlink_to("RUTA/TU.iso")          # enlace roto (el caso real)
    t = recipes.link_disc(rc, src, iso)
    assert t.is_symlink() and t.resolve() == iso.resolve()
    t.unlink()
    t.write_bytes(b"real")                          # un archivo de verdad no se toca
    recipes.link_disc(rc, src, iso)
    assert t.read_bytes() == b"real" and not t.is_symlink()
    with pytest.raises(OSError):
        recipes.link_disc(rc, src, tmp_path / "no.iso")


def test_fases_de_la_receta(tmp_path):
    from hub import recipes
    rc = recipes.for_entry({"id": "gta-vcs-recomp"})
    e = {"id": "gta-vcs-recomp", "repo": "gothamor/gta-vcs-recomp"}
    src = tmp_path / "linux"
    f1 = recipes.phase1(rc, e, src)
    assert [d.split()[0] for d, _ in f1] == ["Crear", "Preparar", "Comprobar"]
    assert "distrobox create --name hub-gta-vcs-recomp --image fedora:43" in f1[0][1][-1]
    assert f1[2][1][:4] == ["distrobox", "enter", "hub-gta-vcs-recomp", "--"] and "--check-deps" in f1[2][1][-1]
    f2 = recipes.phase2(rc, e, src, ["clang", "glslang"], tmp_path / "x.iso", lambda say: None)
    descs = [d for d, _ in f2]
    assert descs[0].startswith("Instalar 2 paquetes") and f2[0][1][-4:] == ["install", "-y", "clang", "glslang"]
    assert any("deps.py fetch" in d for d in descs) and any(d.startswith("Compilar") for d in descs)
    assert descs.index(next(d for d in descs if d.startswith("Compilar"))) < descs.index(next(d for d in descs if d.startswith("Traer")))
    assert callable(f2[-1][1]) and callable(next(a for d, a in f2 if d.startswith("Traer")))


def test_runner_es_sh_valido_y_tiene_los_dos_modos():
    from hub import recipes
    t = recipes.runner_text("build/vcs", "build", "build/lib", "hub-x")
    assert subprocess.run(["sh", "-n", "-c", t]).returncode == 0
    assert 'LD_LIBRARY_PATH="$HERE/build/lib' in t and "distrobox enter hub-x -- \"./vcs\"" in t and ".run-in-container" in t
    w = recipes.container_wrapper_text("/g/Game.AppImage", "fedora", "/g", True)
    assert subprocess.run(["sh", "-n", "-c", w]).returncode == 0 and "APPIMAGE_EXTRACT_AND_RUN=1" in w and "distrobox enter fedora" in w


def test_bibliotecas_que_faltan_se_detectan_con_ldd(tmp_path, monkeypatch):
    from hub import recipes
    b = tmp_path / "bin"
    b.mkdir()
    (b / "ldd").write_text("#!/bin/sh\necho '\tlibavcodec.so.61 => not found'\necho '\tlibc.so.6 => /lib/libc.so.6'\n")
    (b / "ldd").chmod(0o755)
    monkeypatch.setenv("PATH", f"{b}:/usr/bin:/bin")
    exe = tmp_path / "vcs"
    exe.write_bytes(b"x")
    assert recipes.missing_libs(exe, tmp_path / "lib") == ["libavcodec.so.61"]


def _con_linux_compilado(juego, tmp_path):
    from hub import osver
    d, toml = juego
    osver.attach_windows("sh", _exe(tmp_path), "proton")          # reorganiza: lo de Linux pasa a linux/
    lin = d / "linux"
    (lin / "build").mkdir(exist_ok=True)
    (lin / "build" / "vcs").write_bytes(b"\x7fELF")
    return d, toml, lin


def test_build_de_contenedor_se_registra_sin_tocar_windows(juego, tmp_path):
    from hub import osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    assert _t(toml)["update"]["type"] == "none"          # v3.00: Windows elegido a mano (.exe propio) no lo actualiza el launcher
    st = osver.attach_linux_build("sh", "build/vcs", "build", "build/lib", "hub-sh", "r.toml")
    t = _t(toml)
    assert st["active"] == "linux" and t["install_dir"].endswith("/linux") and t["run"]["exe"] == "hub-run.sh"
    assert t["update"]["type"] == "none", "un build compilado aquí no se actualiza con el archivo de Windows"
    assert (lin / "hub-run.sh").is_file() and (lin / "build" / "vcs").is_file()
    assert (d / "windows" / "hub-run.sh").is_file(), "Windows sigue ahí"
    assert osver.container_of("sh") == "hub-sh"
    osver.set_active("sh", "windows")
    t = _t(toml)
    assert t["update"]["type"] == "none" and t["install_dir"].endswith("/windows")
    assert (lin / "build" / "vcs").is_file()


def test_ejecutar_en_contenedor_build_propio_usa_marcador(juego, tmp_path):
    from hub import osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    osver.attach_linux_build("sh", "build/vcs", "build", "build/lib", "hub-sh")
    assert not osver.in_container("sh")
    osver.set_in_container("sh", True)
    assert osver.in_container("sh") and (lin / ".run-in-container").exists()
    osver.set_in_container("sh", False)
    assert not osver.in_container("sh") and not (lin / ".run-in-container").exists()


def test_ejecutar_en_contenedor_version_normal_usa_envoltorio_y_se_deshace(juego, tmp_path):
    from hub import osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    osver.set_active("sh", "linux")
    t0 = _t(toml)
    assert t0["run"]["exe"] == "SilentHillPC"
    osver.set_container("sh", "fedora")
    osver.set_in_container("sh", True)
    t = _t(toml)
    assert t["run"]["exe"] == "hub-container.sh" and t["run"]["type"] == "binary" and osver.in_container("sh")
    w = (lin / "hub-container.sh").read_text()
    assert "distrobox enter fedora" in w and "SilentHillPC" in w
    osver.set_in_container("sh", False)
    t = _t(toml)
    assert t["run"]["exe"] == "SilentHillPC" and not (lin / "hub-container.sh").exists() and not osver.in_container("sh")
    assert (lin / "SilentHillPC").exists(), "no se borró nada del juego"


def test_cmdjob_ejecuta_pasos_en_python_y_avisa_si_fallan():
    from hub import cmdjob
    vistos = []
    j = cmdjob.CmdJob("X", "t", [("uno", lambda say: vistos.append(1) or say("hola")), ("dos", ["true"])])
    j.run()
    assert j.state == "done" and vistos == [1] and any("hola" in ln for ln in j.log)

    def mal(say):
        raise OSError("falta algo")
    j = cmdjob.CmdJob("X", "t", [("malo", mal), ("bien", ["true"])])
    j.run()
    assert j.state == "error" and "malo" in j.error


def test_ficha_es_un_arbol_solo_se_ve_la_rama_elegida(H, ui, juego, monkeypatch, tmp_path):
    from test_temas_y_fuzz import run
    from test_v212 import _ficha
    from hub import recipes, osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    monkeypatch.setattr(recipes, "have_distrobox", lambda: True)
    monkeypatch.setattr(recipes, "for_entry", lambda e: next(r for r in recipes.load_all() if "build" in r))
    e = _ficha(H, ui, juego, monkeypatch, [], [], installed=True)

    def teclas():
        ui._osv.clear()
        run(ui, 4)
        return {w.key for w in ui.widgets}
    ui._rcp.clear()
    ui.more_open.add(e["id"])
    ui.more_tab[e["id"]] = "juego"
    # rama WINDOWS (es la activa): con qué se abre; nada de Linux
    ks = teclas()
    assert {"wr_proton", "wr_wine"} <= ks and not ({"os_linux", "os_windows"} & ks) and "winlocal" not in ks and "adv" not in ks, "lo técnico ya no está en el árbol: va en MÁS OPCIONES → AVANZADO"
    assert not ({"lm_release", "lm_built", "run_sys", "run_ctr", "rcp_build", "rcp_attach"} & ks)
    ui.more_tab[e["id"]] = "archivo"
    ui.more_tab[e["id"]] = "archivo"
    assert "winlocal" in teclas(), "v2.70: elegir un .exe está en MÁS OPCIONES → ARCHIVO"
    ui.more_tab[e["id"]] = "juego"
    # rama LINUX: método y dónde se abre; nada de Windows
    osver.set_active("sh", "linux")
    ks = teclas()
    assert {"lm_release", "lm_built", "run_sys", "run_ctr"} <= ks and not ({"wr_proton", "wr_wine", "rcp_build"} & ks)
    # mirar el método «compilar»: ya hay un build sin registrar
    ui.set_linux_view(e, "built")
    ks = teclas()
    assert {"rcp_attach", "rcp_build"} <= ks and "run_ctr" not in ks, "«Abrir en» solo para el método activo"
    osver.attach_linux_build("sh", "build/vcs", "build", "build/lib", "hub-sh")
    ks = teclas()
    assert "rcp_attach" not in ks and {"rcp_build", "run_ctr"} <= ks


def test_metodos_de_linux_no_se_pisan_y_se_puede_volver(juego, tmp_path):
    from hub import osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    osver.set_active("sh", "linux")
    assert osver.linux_methods("sh") == {"active": "release", "release": True, "built": False}
    osver.set_container("sh", "fedora")
    osver.set_in_container("sh", True)                       # la release se abría en el contenedor
    osver.attach_linux_build("sh", "build/vcs", "build", "build/lib", "hub-sh")
    assert osver.linux_methods("sh") == {"active": "built", "release": True, "built": True}
    assert _t(toml)["run"]["exe"] == "hub-run.sh" and not (lin / "hub-container.sh").exists()
    osver.set_linux_method("sh", "release")
    t = _t(toml)
    assert t["run"]["exe"] == "SilentHillPC" and t["update"]["type"] == "github-archive" and osver.linux_methods("sh")["active"] == "release"
    osver.set_linux_method("sh", "built")
    assert _t(toml)["run"]["exe"] == "hub-run.sh" and _t(toml)["update"]["type"] == "none"
    assert (lin / "SilentHillPC").exists() and (lin / "build" / "vcs").exists()


def test_windows_con_proton_o_wine_reescribe_el_lanzador_sin_tocar_el_prefijo(juego, tmp_path):
    from hub import osver
    d, toml = juego
    osver.attach_windows("sh", _exe(tmp_path), "proton")
    (d / "proton-prefix").mkdir(exist_ok=True)
    (d / "proton-prefix" / "partida.sav").write_text("x")
    assert osver.windows_runner("sh") == "proton"
    osver.set_windows_runner("sh", "wine")
    r = (d / "windows" / "hub-run.sh").read_text()
    assert "exec wine" in r and "umu-run" not in r and osver.windows_runner("sh") == "wine"
    osver.set_windows_runner("sh", "proton")
    assert "umu-run" in (d / "windows" / "hub-run.sh").read_text()
    assert (d / "proton-prefix" / "partida.sav").read_text() == "x"
    with pytest.raises(ValueError):
        osver.set_windows_runner("sh", "otro")


def test_runner_wine_de_un_build_descargado_es_sh_valido():
    from hub import osver
    t = osver.runner_text("Game/game.exe", "/p/GE", "wine")
    assert subprocess.run(["sh", "-n", "-c", t]).returncode == 0 and 'exec wine "$HERE/Game/game.exe"' in t


def test_flujo_de_botones_compilar_con_confirmaciones(H, ui, juego, monkeypatch, tmp_path):
    import time
    from test_temas_y_fuzz import run
    from test_v212 import _ficha
    from hub import recipes, cmdjob, library
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    monkeypatch.setattr(recipes, "have_distrobox", lambda: True)
    rc = next(r for r in recipes.load_all() if "build" in r)
    monkeypatch.setattr(recipes, "for_entry", lambda e: rc)
    e = _ficha(H, ui, juego, monkeypatch, [], [], installed=True)
    ui._rcp.clear()
    toasts = []
    monkeypatch.setattr(ui, "toast", lambda m: toasts.append(m))
    monkeypatch.setattr(library, "link_get", lambda eid: None)
    ui.recipe_start(e)
    assert toasts and "ISO" in toasts[-1] and not ui.builds
    iso = tmp_path / "GTA_VCS.iso"
    iso.write_bytes(b"x")
    monkeypatch.setattr(library, "link_get", lambda eid: str(iso))
    monkeypatch.setattr(recipes, "ensure_source", lambda *a, **k: None)
    jobs = []

    def fake_start(self, done=None):
        jobs.append(self)
        if self.steps and self.steps[0][0].startswith("Crear"):
            self.log.extend(SALIDA.splitlines())
            if done:
                done(True)
    monkeypatch.setattr(cmdjob.CmdJob, "start", fake_start)
    ui.recipe_start(e)
    assert ui.modal and "contenedor" in ui.modal["title"].lower()
    ui.modal["cb"]()
    for _ in range(100):
        if jobs:
            break
        time.sleep(0.02)
    assert jobs and jobs[0].label == "COMPILAR EN CONTENEDOR"
    run(ui, 2)                                   # el hilo dejó su petición para el hilo principal
    assert ui.modal and "Instalar" in ui.modal["title"] and "ffmpeg-free-devel" in ui.modal["msg"] and "vulkan-headers" not in ui.modal["msg"]
    ui.modal["cb"]()
    assert len(jobs) == 2 and jobs[1].steps[0][0].startswith("Instalar")
    assert (lin / rc["disc"]["name"]).is_symlink()


def test_ruido_conocido_no_es_un_error_de_arranque():
    from hub import launchlog
    ruido = ("ERROR: ld.so: object '/home/x/.local/share/Steam/ubuntu12_32/gameoverlayrenderer.so' from LD_PRELOAD cannot be preloaded (wrong ELF class: ELFCLASS32): ignored.\n"
             "ATTENTION: default value of option vk_xwayland_wait_ready overridden by environment.\n"
             "pid 790565 != 790493, skipping destruction (fork without exec?)\n"
             "[Gamescope WSI] Atom of T was wrong type. Expected XCB_ATOM_CARDINAL.\n")
    assert not launchlog.real_errors(ruido)
    assert launchlog.real_errors(ruido + "error while loading shared libraries: libavcodec.so.61: cannot open shared object file\n")
    assert "gameoverlayrenderer" not in launchlog.quiet(ruido)


def test_informe_omite_el_ruido_y_conserva_lo_importante(tmp_path, monkeypatch):
    from hub import launchlog, config
    monkeypatch.setattr(config, "LAUNCHER", tmp_path / "l")
    monkeypatch.setattr(launchlog, "dir_", lambda: tmp_path)
    out = tmp_path / "g-20260101-000000.out"
    out.write_text("ERROR: ld.so: object '/x/gameoverlayrenderer.so' from LD_PRELOAD cannot be preloaded (wrong ELF class: ELFCLASS32): ignored.\n" * 5
                   + "Segmentation fault (core dumped)\n")
    md = launchlog.report("g", "G", 139, 3.0, out)
    t = md.read_text()
    assert "Segmentation fault" in t and "gameoverlayrenderer" not in t and "5 líneas de ruido" in t


def test_cambiar_donde_se_abre_no_bloquea_la_interfaz(H, ui, juego, monkeypatch, tmp_path):
    """El log real mostró fotogramas de ~1 s: `distrobox list` se ejecutaba en el hilo principal al pulsar el botón."""
    import threading
    import time
    from test_temas_y_fuzz import run
    from test_v212 import _ficha
    from hub import build, osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    osver.set_container("sh", "hub-sh")
    e = _ficha(H, ui, juego, monkeypatch, [], [], installed=True)
    quien = []

    def lento():
        quien.append(threading.current_thread() is threading.main_thread())
        time.sleep(0.3)
        return ["hub-sh"]
    monkeypatch.setattr(build, "containers", lento)
    toasts = []
    monkeypatch.setattr(ui, "toast", lambda m: toasts.append(m))
    t0 = time.time()
    ui.set_run_container(e, True)
    assert time.time() - t0 < 0.15, "la pulsación debe volver al instante"
    for _ in range(100):
        run(ui, 1)
        if any("dentro de" in t for t in toasts):
            break
        time.sleep(0.02)
    assert osver.in_container("sh") and quien == [False] and any("dentro de" in t for t in toasts)


def test_envoltorio_conserva_el_appimage_en_ejecutables(juego, tmp_path):
    from hub import osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    osver.set_active("sh", "linux")
    osver.set_container("sh", "fedora")
    osver.set_in_container("sh", True)
    ex = _t(toml)["update"]["executables"]
    assert ex[0] == "hub-container.sh" and "SilentHillPC" in ex, "una actualización debe poder marcar ejecutable el binario nuevo"


def test_envoltorio_limpia_el_entorno_de_steam_y_se_regenera_sin_apuntarse_a_si_mismo(juego, tmp_path):
    from hub import osver
    d, toml, lin = _con_linux_compilado(juego, tmp_path)
    osver.set_active("sh", "linux")
    osver.set_in_container("sh", True, "fedora")
    w1 = (lin / "hub-container.sh").read_text()
    assert "unset LD_PRELOAD LD_LIBRARY_PATH" in w1 and "SilentHillPC" in w1
    (lin / "hub-container.sh").write_text("#!/bin/sh\n# viejo\n")        # un envoltorio creado por una versión anterior
    osver.set_in_container("sh", True, "fedora")
    w2 = (lin / "hub-container.sh").read_text()
    assert "unset LD_PRELOAD" in w2 and "SilentHillPC" in w2 and w2.count("hub-container.sh") == 0, "no puede apuntarse a sí mismo"
    osver.set_in_container("sh", False)
    assert _t(toml)["run"]["exe"] == "SilentHillPC"


def test_runner_de_build_propio_tambien_limpia_el_entorno():
    from hub import recipes
    t = recipes.runner_text("build/vcs", "build", "build/lib", "hub-x")
    assert t.index("unset LD_PRELOAD LD_LIBRARY_PATH") < t.index("distrobox enter")
