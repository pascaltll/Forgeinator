"""Compilar para Linux en un contenedor (distrobox) y elegir dónde se ejecuta (sistema / contenedor). Parte de la clase UI (hub/ui.py); ver _adopt."""
# flake8: noqa: F821


class RecipesMixin:
    # ── qué ofrece la ficha ──
    def recipe_of(self, e):
        c = self._rcp.get(e["id"], 0)
        if c == 0:
            c = recipes.for_entry(e)
            self._rcp[e["id"]] = c
        return c

    def _rcp_paths(self, e, lid):
        """(raíz del juego, carpeta linux/, ejecutable compilado o None) según la receta."""
        rc = self.recipe_of(e)
        root = osver.root_of(lid)
        if not rc or root is None:
            return root, None, None
        out = rc.get("output") or {}
        lin = Path(root) / "linux"
        return Path(root), lin, (lin / out["exe"] if out.get("exe") else None)

    def container_name_for(self, e, lid):
        """Contenedor de ESTE juego: el de su carpeta (.hub-versions.json) > el que elegiste en una carpeta sin versiones separadas > el de su receta > el de Ajustes."""
        rc = self.recipe_of(e)
        return (osver.container_of(lid) or (self.cfg.get("ctr_by_game") or {}).get(lid)
                or (recipes.container_name(rc, e) if rc else self.cfg.get("build_container", "fedora")))

    def ctr_names(self):
        """(nombres, ¿ya se consultó?) SIN bloquear la interfaz: `distrobox list` tarda ~1 s (hasta 20 s); si la caché tiene más de 60 s se renueva en un hilo."""
        t, v = build._CC.get("x", (0, []))
        if time.time() - t > 60 and not self.__dict__.get("_ctr_busy") and recipes.have_distrobox():
            self._ctr_busy = True

            def job():
                try:
                    build.refresh_containers()
                finally:
                    self._ctr_busy = False
            threading.Thread(target=job, daemon=True).start()
        return v, "x" in build._CC

    def test_container(self, e):
        """PROBAR: entra al contenedor y dice si de verdad se está dentro (archivo /run/.containerenv), con qué sistema y usuario, y si sudo funciona sin clave."""
        lid = self.inst(e)["launcher_id"]
        name = self.container_name_for(e, lid)
        if not name:
            self.toast("Este juego no tiene contenedor: elígelo primero")
            return
        script = ('echo "usuario: $(id -un)  ·  equipo: $(hostname)"; '
                  '. /etc/os-release 2>/dev/null; echo "sistema: $PRETTY_NAME"; '
                  'if [ -f /run/.containerenv ]; then echo "DENTRO DE UN CONTENEDOR: sí"; else echo "DENTRO DE UN CONTENEDOR: NO (estás en el sistema)"; fi; '
                  'if sudo -n true 2>/dev/null; then echo "sudo sin clave: sí"; else echo "sudo sin clave: NO (los paquetes pedirían contraseña)"; fi; '
                  'for c in dnf git python3 clang cmake; do command -v $c >/dev/null 2>&1 && echo "  $c: sí" || echo "  $c: no"; done; '
                  'echo "DISPLAY=$DISPLAY WAYLAND_DISPLAY=$WAYLAND_DISPLAY"')

        def run():
            import subprocess as sp
            r = sp.run(recipes.enter(name, script), capture_output=True, text=True, timeout=90, stdin=sp.DEVNULL, env=__import__("hub.proctree", fromlist=["x"]).clean_env())
            return (r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")).strip() + f"\n(código de salida {r.returncode})"

        def done(res, err):
            txt = res if err is None else f"No pude entrar en «{name}»: {err}"
            self._rcp_q.append(lambda: self.show_log(self._TextLog(f"Prueba del contenedor «{name}»", None, txt)))
            history.record(lid, "contenedor", err is None and "DENTRO DE UN CONTENEDOR: sí" in (res or ""), (txt or "").replace("\n", " | ")[:280])
        self.work(f"Probando «{name}»…", run, done)

    def container_command(self, e):
        """COMANDO…: escribe (con el teclado en pantalla) un comando que se ejecuta DENTRO del contenedor; la salida se ve en DESCARGAS y se puede cancelar."""
        lid = self.inst(e)["launcher_id"]
        name = self.container_name_for(e, lid)
        if not name:
            self.toast("Este juego no tiene contenedor: elígelo primero")
            return

        def go(t):
            t = recipes.fix_command(t)
            if not t:
                return
            try:
                cwd = osver.folders(lid)["dir"] or None
            except (OSError, ValueError, KeyError):
                cwd = None
            job = cmdjob.CmdJob("COMANDO EN CONTENEDOR", e["name"], [(f"En «{name}»: {t[:60]}", recipes.enter(name, t, cwd))], e)
            self.builds.append(job)
            job.start(lambda ok: history.record(lid, "contenedor", ok, "comando: " + t[:120]))
            self.toast("Ejecutando dentro del contenedor… mira DESCARGAS")
        self.osk(f"Comando para ejecutar dentro de «{name}» (sudo funciona ahí; ej.: sudo dnf install -y clang)", go, "sudo dnf install -y ")

    def restart_container(self, e):
        lid = self.inst(e)["launcher_id"]
        name = self.container_name_for(e, lid)
        if not name:
            self.toast("Este juego no tiene contenedor")
            return

        def go():
            job = cmdjob.CmdJob("REINICIAR CONTENEDOR", e["name"], [(f"Detener «{name}» (se arranca solo al volver a entrar)", ["distrobox", "stop", "--yes", name])], e)
            self.builds.append(job)
            job.start()
            self.toast("Deteniendo el contenedor… mira DESCARGAS")
        self.confirm("REINICIAR EL CONTENEDOR", f"Detiene «{name}» y todo lo que tenga en marcha (una compilación que no responde a CANCELAR, por ejemplo). "
                     "No borra nada: se vuelve a arrancar solo la próxima vez. Si el juego está abierto dentro, se cerrará. ¿Seguir?", go)

    def ctr_ok(self, name):
        """True/False si el contenedor existe; None si aún no se sabe (o es «el sistema»)."""
        if not name:
            return None
        names, known = self.ctr_names()
        return (name in names) if known else None

    def linux_branch(self, e, inf, x0, y, colw):
        """Rama LINUX: método (release/AppImage · compilar en contenedor) y dónde se abre (sistema · contenedor)."""
        lid = inf["launcher_id"]
        st = self.os_state(lid)
        rc = self.recipe_of(e)
        root, lin, exe = self._rcp_paths(e, lid)
        mt = osver.linux_methods(lid) if st.get("split") else {"active": "release", "release": bool(st.get("linux")), "built": False}
        have = exe is not None and exe.is_file()
        view = self.ver_view.get(e["id"]) or mt["active"]
        choose = bool(rc and lin is not None) or mt["built"]
        if not (choose or (st.get("linux") and st.get("split") and recipes.have_distrobox())):
            return y
        self.text("LINUX", x0, self.cy(y), 17, DIM, True)
        y += self.n(28)
        y = self.versions_line(e, lid, x0, y, colw)
        if choose:
            self.text("Método:", x0, self.cy(y) + self.n(36), 18, DIM, anchor="ml")
            lw = self.font(18).size("Método:")[0] + self.n(16)
            hw = (colw - lw - self.n(8)) // 2
            bl = "COMPILAR (contenedor)" + (" · ya hay un build" if have and not mt["built"] else "")
            self.button("lm_release", (x0 + lw, y, hw, self.n(72)), "RELEASE (AppImage)", lambda: self.set_linux_view(e, "release"), "seg" if view == "release" else "normal", 18,
                        enabled=mt["release"], mark=view == "release")
            self.button("lm_built", (x0 + lw + hw + self.n(8), y, hw, self.n(72)), bl, lambda: self.set_linux_view(e, "built"), "seg" if view == "built" else "normal", 16, mark=view == "built")
            y += self.n(84)
        if view == "built" and rc and lin is not None:
            name = recipes.container_name(rc, e)
            bjob = next((b for b in self.builds if getattr(b, "label", "") == "COMPILAR EN CONTENEDOR" and b.state in ("queued", "running") and b.entry["id"] == e["id"]), None)
            busy = bjob is not None
            built = mt["active"] == "built"
            if built:
                msg = f"Compilado en «{name}». Para actualizar, recompila."
            elif have:
                msg = "Ya está compilado: regístralo y JUGAR lo abre."
            else:
                msg = f"Primera vez: se compila en «{name}» (unos minutos). Después, JUGAR."
            self.text(msg, x0, self.cy(y), 16, DIM, False, colw)
            y += self.n(34) if len(msg) < 110 else self.n(56)
            if have and not built:
                self.button("rcp_attach", (x0, y, colw, self.n(72)), "USAR EL JUEGO YA COMPILADO (" + str(exe.relative_to(root)) + ")", lambda: self.recipe_attach(e), "primary", 18, enabled=not busy)
                y += self.n(84)
            lab = "RECOMPILAR EN EL CONTENEDOR" if built or have else "COMPILAR EL JUEGO EN UN CONTENEDOR"
            if busy:
                self.button("rcp_cancel", (x0, y, colw, self.n(72)), "COMPILANDO… (mira DESCARGAS)  ·  PULSA AQUÍ PARA CANCELAR", lambda: self.build_x(bjob), "danger", 18)
            else:
                self.button("rcp_build", (x0, y, colw, self.n(72)), lab, lambda: self.recipe_start(e), "normal", 18)
            y += self.n(84)
        elif view == "release" and st.get("linux"):
            self.text("Usa la release descargada (AppImage o binario).", x0, self.cy(y), 16, DIM, False, colw)
            y += self.n(34)
        if view == mt["active"] and st.get("linux") and st.get("split") and recipes.have_distrobox():
            on = osver.in_container(lid)
            cont = self.container_name_for(e, lid)
            self.text("Abrir en:", x0, self.cy(y) + self.n(36), 18, DIM, anchor="ml")
            lw = self.font(18).size("Abrir en:")[0] + self.n(16)
            hw = (colw - lw - self.n(8)) // 2
            self.button("run_sys", (x0 + lw, y, hw, self.n(72)), "EL SISTEMA", lambda: self.set_run_container(e, False), "seg" if not on else "normal", 18, mark=not on)
            self.button("run_ctr", (x0 + lw + hw + self.n(8), y, hw, self.n(72)), "CONTENEDOR", lambda: self.set_run_container(e, True), "seg" if on else "normal", 18, mark=on)
            y += self.n(84)
            okc = self.ctr_ok(cont)
            est = "no existe" if okc is False else "listo" if okc else "sin comprobar"
            self.text(f"Contenedor: «{cont or 'ninguno'}» · {est}", x0, self.cy(y) + self.n(30), 18, ERR if okc is False else TXT, True, colw - self.n(330), anchor="ml")
            self.button("go_ctr", (x0 + colw - self.n(310), y, self.n(310), self.n(72)), "ADMINISTRAR", lambda: self.more_tab.__setitem__(e["id"], "compilar"),
                        "primary" if okc is False else "normal", 17)
            y += self.n(88)
        return y

    def container_card(self, e, inf, x0, y, colw):
        """v2.87: UN solo sitio para el contenedor del juego: cuál es, si existe, y CAMBIAR/CREAR · PROBAR · COMANDO… · REINICIAR."""
        if not recipes.have_distrobox():
            self.text("Este equipo no tiene distrobox: no hay contenedores que gestionar.", x0 + self.n(8), self.cy(y), 18, DIM, False, colw)
            return y + self.n(44)
        lid = inf["launcher_id"]
        cont = self.container_name_for(e, lid)
        okc = self.ctr_ok(cont)
        pad = self.n(24)
        px, inner = x0 + pad, colw - 2 * pad
        h = 18 + 34 + 36 + 86 + 86 + 36
        p = pygame.Rect(x0, y, colw, self.n(h))
        self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
        yy = y + self.n(18)
        self.text("CONTENEDOR DE ESTE JUEGO", px, self.cy(yy), 18, DIM, True)
        yy += self.n(34)
        est = "no existe: elige otro o crea uno" if okc is False else "listo" if okc else "sin comprobar"
        self.text(f"«{cont or 'ninguno'}» · {est}", px, self.cy(yy), 21, ERR if okc is False else OK if okc else TXT, True, inner)
        yy += self.n(44)
        bw = (inner - self.n(14)) // 2
        self.button("bcont", (px, yy, bw, self.n(72)), "CAMBIAR O CREAR", lambda: self.pick_container(e), "primary" if (okc is False or not cont) else "normal", 19)
        self.button("ctr_test", (px + bw + self.n(14), yy, bw, self.n(72)), "PROBAR", lambda: self.test_container(e), "normal", 19)
        yy += self.n(86)
        self.button("ctr_cmd", (px, yy, bw, self.n(72)), "COMANDO…", lambda: self.container_command(e), "normal", 19)
        self.button("ctr_stop", (px + bw + self.n(14), yy, bw, self.n(72)), "REINICIAR", lambda: self.restart_container(e), "normal", 19)
        yy += self.n(86)
        self.text("Sirve para compilar. Dónde se abre el juego se elige en JUGAR.", px, self.cy(yy), 16, DIM, False, inner)
        return p.bottom + self.n(24)

    def versions_line(self, e, lid, x0, y, colw):
        """«Linux v0.3.0 · Windows v0.2.4 · última v0.3.0»: cada versión instalada por separado. Un juego con las dos puede tener una al día y la otra no."""
        try:
            vs = osver.versions(lid)
        except (OSError, ValueError, KeyError):
            return y
        if not vs:
            return y
        last = (self.rel_for(e) or {}).get("tag", "")
        parts = [f"{k} {v or '?'}" + (" ✓" if last and v == last else " (antigua)" if last and v else "") for k, v in vs.items()]
        self.text("Instalado:  " + "   ·   ".join(parts) + (f"   ·   última: {last}" if last else ""), x0, self.cy(y), 16, DIM, False, colw)
        return y + self.n(30)

    def set_linux_view(self, e, which):
        """Nivel 2 de la rama Linux: ver las opciones de un método. Si ya existe y no es el activo, pasa a ser el que abren JUGAR y Steam."""
        lid = self.inst(e)["launcher_id"]
        self.ver_view[e["id"]] = which
        mt = osver.linux_methods(lid)
        if mt[which] and mt["active"] != which:
            try:
                osver.set_linux_method(lid, which)
            except (OSError, ValueError) as ex:
                self.toast(f"No pude cambiar de método: {ex}")
                return
            self._osv.pop(lid, None)
            self.libchk.pop(lid, None)
            self.toast("JUGAR y Steam abrirán ahora " + ("el juego compilado por Hub" if which == "built" else "la release de Linux"))

    def set_win_runner(self, e, runner):
        lid = self.inst(e)["launcher_id"]
        if runner == osver.windows_runner(lid):
            return
        if runner == "proton" and not shutil.which("umu-run"):
            self.toast("Falta umu-run (en Bazzite viene instalado)")
            return
        if runner == "own" and not self.own_info(lid):
            self.toast("No encuentro el .exe de este juego de Windows")
            return
        if runner == "wine" and not osver.find_wine():
            self.toast("No hay Wine en el sistema, ni en Bottles, Lutris o GE-Proton: instala un runner en Bottles o usa Proton")
            return
        try:
            osver.set_windows_runner(lid, runner)
        except (OSError, ValueError) as ex:
            self.toast(f"No pude cambiarlo: {ex}")
            return
        self._osv.pop(lid, None)
        self._own_c = {}
        extra = ""
        if runner == "own":                       # el .toml del launcher debe abrir windows/hub-run.sh (en un checkout propio apuntaba a otro sitio)
            try:
                bo = launchlog.binary_of(lid)
                fo = osver.folders(lid)
                hr = osver.root_of(lid) / "windows" / osver.RUNNER
                if bo is None or Path(bo).resolve() != hr.resolve():
                    old = install.repair_run(lid, Path(fo["dir"]), os.path.relpath(hr, fo["dir"]), force=True)
                    extra = " · el launcher ahora abre hub-run.sh" if old else " · OJO: no pude fijar hub-run.sh en el .toml del launcher"
            except (OSError, ValueError, KeyError) as ex:
                extra = f" · no pude revisar el .toml ({ex})"
        self.toast("Windows se abrirá con " + {"wine": "Wine", "own": "tu Wine propio"}.get(runner, "Proton") + extra)

    def set_own_game(self, e, game):
        lid = self.inst(e)["launcher_id"]
        oi = self.own_info(lid)
        if not oi or game == oi["cfg"].get("game"):
            return
        osver.set_own(lid, game=game, mode="direct")
        self._own_c = {}
        self.toast("JUGAR abrirá " + ownwine.GAMES[game][1] + " directamente, sin el launcher")

    def set_own_mode(self, e, mode):
        lid = self.inst(e)["launcher_id"]
        oi = self.own_info(lid)
        if not oi or mode == oi["cfg"].get("mode"):
            return
        osver.set_own(lid, mode=mode)
        self._own_c = {}
        self.toast("JUGAR abrirá " + ("el launcher" if mode == "launcher" else ownwine.GAMES[oi["cfg"]["game"]][1] + " directamente"))

    def pick_own_wine(self, e):
        """Elige el ejecutable de tu Wine (p. ej. ~/wine-11.21/loader/wine). Debe ser ejecutable y llamarse wine*."""
        lid = self.inst(e)["launcher_id"]
        oi = self.own_info(lid)
        cur = ownwine.expand(oi["cfg"]["binary"]) if oi and oi["cfg"]["binary"] else ""
        start = Path(cur).parent if cur and Path(cur).parent.is_dir() else Path.home()

        def chosen(p):
            p = Path(p)
            if not os.access(p, os.X_OK) or "wine" not in p.name.lower():
                self.toast("Ese archivo no parece un Wine (debe ser ejecutable y llamarse wine…)")
                return
            try:
                osver.set_own(lid, binary=str(p))
            except (OSError, ValueError) as ex:
                self.toast(f"No pude guardarlo: {ex}")
                return
            self._own_c = {}
            self.toast(f"Wine propio: {p}")
        found = ownwine.list_wines()
        try:
            ownwine.WINES_HOME.mkdir(exist_ok=True)
        except OSError:
            pass

        def setw(p):
            try:
                osver.set_own(lid, binary=str(p))
            except (OSError, ValueError) as ex:
                self.toast(f"No pude guardarlo: {ex}")
                return
            self._own_c = {}
            self.toast(f"Wine propio: {p}")
        opts = [(("✓ " if str(w) == cur else "") + n, (lambda w=w: setw(w))) for n, w in found]
        opts.append(("BUSCAR OTRO ARCHIVO…", lambda: self.open_picker("Elige tu Wine (el ejecutable «wine»)", start, None, chosen)))
        self.modal = {"kind": "choice", "title": "Tu Wine propio", "prev": None,
                      "msg": f"Guarda cada versión en su carpeta dentro de {ownwine.WINES_HOME} (por ejemplo wine-11.21/bin/wine) y aparecerá aquí sola. "
                             + (f"Encontrados: {len(found)}." if found else "Todavía no hay ninguno."), "options": opts}
        self.focus = None

    def own_build(self, e, game=None):
        """COMPILAR: `GoWLauncher.exe --build <juego>` con tu Wine, en DESCARGAS. Al terminar bien se quita el aviso de recompilar."""
        lid = self.inst(e)["launcher_id"]
        oi = self.own_info(lid)
        if not oi:
            return
        try:
            steps = ownwine.build_steps(oi["win"], oi["w"], game)
        except OSError as ex:
            self.toast(str(ex))
            return
        def done(ok):
            def fin():
                if ok:
                    rr = osver.root_of(lid)
                    mm = osver.meta(rr)
                    ww = mm.get("windows") or {}
                    ww["rebuild"] = False
                    mm["windows"] = ww
                    osver._save_meta(rr, mm)
                    self.toast("Compilado: ya puedes jugar")
                else:
                    self.toast("La compilación terminó con avisos: mira el REGISTRO en DESCARGAS")
                self._own_c = {}
            self._rcp_q.append(fin)
        job = cmdjob.CmdJob("COMPILAR (WINE PROPIO)", e["name"], steps, e)
        self.builds.append(job)
        job.expected = 240
        job.probe = lambda: ownwine.build_progress(oi["win"], oi["w"])
        job.start(done)
        self.toast("Compilando… míralo en DESCARGAS")

    # ── elegir distrobox / dónde ejecutar ──
    def runtime_of(self, e):
        """Receta de ejecución del juego: la escrita a mano (hub/recipes) o, para CUALQUIER juego instalado, la deducida de su release
        (distribución con la que se compiló) o de las bibliotecas que le faltan al sistema. Se recalcula cada 10 s."""
        c = self.__dict__.setdefault("_rcp_rt", {})
        hit = c.get(e["id"])
        if hit and time.time() - hit[0] < 10.0:
            return hit[1]
        rt = recipes.runtime_for(e)
        if not rt:
            try:
                inf = self.inst(e)
                if inf["installed"]:
                    lid = inf["launcher_id"]
                    t = launchlog._toml(lid)
                    rt = recipes.runtime_guess(e, osver.folders(lid)["dir"], str((t.get("update") or {}).get("asset") or ""), self.libchk.get(lid) or ())
            except (OSError, ValueError, KeyError):
                rt = None
        c[e["id"]] = (time.time(), rt)
        return rt

    def _linux_elf(self, lid):
        """El ejecutable de Linux de verdad (no el envoltorio .sh), para mirar qué bibliotecas pide."""
        try:
            t = launchlog._toml(lid)
            d = Path(osver.folders(lid)["dir"])
            for x in list((t.get("update") or {}).get("executables") or []) + [str((t.get("run") or {}).get("exe") or "")]:
                p = d / x
                if x and p.is_file() and not x.endswith(".sh"):
                    with open(p, "rb") as f:
                        if f.read(4) == b"\x7fELF":
                            return str(p)
            x = install.find_executable(d)
            return str(d / x) if x else None
        except (OSError, ValueError, KeyError):
            return None

    def prepare_container(self, e):
        """Crea el distrobox que pide la release (p. ej. Ubuntu 26.04), instala sus paquetes y deja el juego abriéndose dentro."""
        rt = self.runtime_of(e)
        lid = self.inst(e)["launcher_id"]
        if not rt or not recipes.have_distrobox():
            self.toast("Este juego no tiene receta de contenedor (o falta distrobox)")
            return
        name, r = recipes.runtime_name(rt, e), rt["runtime"]
        if any(b.state in ("queued", "running") and getattr(b, "label", "") == "CONTENEDOR" and b.entry["id"] == e["id"] for b in self.builds):
            self.toast("Ya está en marcha: mira DESCARGAS")
            return

        def go():
            try:
                cwd = osver.folders(lid)["dir"] or None
            except (OSError, ValueError, KeyError):
                cwd = None
            job = cmdjob.CmdJob("CONTENEDOR", e["name"], recipes.runtime_steps(rt, e, cwd, self._linux_elf(lid)), e)

            def done(ok):
                def fin():
                    if not ok:
                        self.toast("El contenedor terminó con avisos: mira el REGISTRO en DESCARGAS")
                        return
                    try:
                        osver.set_container(lid, name)
                        if osver.in_container(lid):
                            osver.set_in_container(lid, False)
                        osver.set_in_container(lid, True, name)
                    except (OSError, ValueError) as ex:
                        self.toast(f"Contenedor listo, pero no pude fijarlo en el juego: {ex}")
                        return
                    self._osv.pop(lid, None)
                    self.libchk.pop(lid, None)
                    self.toast(f"Listo: el juego se abre dentro de «{name}»")
                self._rcp_q.append(fin)
            self.builds.append(job)
            job.start(done)
            self.toast("Preparando el contenedor… mira DESCARGAS (la primera vez tarda varios minutos)")
        self.confirm("PREPARAR CONTENEDOR", f"Crea el distrobox «{name}» con {r.get('image')}" + (f" ({r['why']})" if r.get("why") else "") + " e instala dentro "
                     + (f"{len(r.get('packages') or [])} paquetes que pide este juego. " if r.get("packages") else "las bibliotecas que le falten al juego (las busca solo). ")
                     + 
                     "No toca tu sistema (Bazzite). Si ya existe, solo añade lo que falte. ¿Seguir?", go)

    def toggle_skip_launcher(self, e):
        lid = self.inst(e)["launcher_id"]
        on = not osver.windows_skip_launcher(lid)
        try:
            osver.set_windows_skip_launcher(lid, on)
        except (OSError, ValueError) as ex:
            self.toast(f"No pude cambiarlo: {ex}")
            return
        self._osv.pop(lid, None)
        self.toast("JUGAR abre el juego directo (ajústalo con config.cfg o sus opciones)" if on else "JUGAR abre otra vez el launcher del juego")

    def pick_proton(self, e):
        """Elige con qué Proton se abre ESTE juego (o automático)."""
        lid = self.inst(e)["launcher_id"]
        found = osver.list_protons()
        if not found:
            self.toast("No hay Proton en compatibilitytools.d: umu-run descargará uno la primera vez")
            return

        def pick(path, name):
            try:
                osver.set_windows_proton(lid, path)
            except (OSError, ValueError) as ex:
                self.toast(f"No pude fijar el Proton: {ex}")
                return
            self._osv.pop(lid, None)
            self.toast("Proton de este juego: " + (name or "automático"))
        opts = [("AUTOMÁTICO (" + Path(osver.proton_path()).name + ")", lambda: pick("", ""))]
        opts += [(n, (lambda p=p, n=n: pick(p, n))) for n, p in found[:7]]
        self.modal = {"kind": "choice", "title": "Proton de este juego", "prev": None,
                      "msg": "Se aplica solo a este juego. Si uno falla (p. ej. GE-Proton11 en algunos equipos), prueba otro; el prefijo no se toca.", "options": opts}
        self.focus = None

    def _fix_container(self, e, lid, n):
        """Fija el contenedor de ESTE juego (carpeta con versiones separadas → .hub-versions.json; si no, Ajustes de Hub) y re-envuelve si ya se abre dentro."""
        try:
            osver.set_container(lid, n)
            (self.cfg.get("ctr_by_game") or {}).pop(lid, None)
            if osver.in_container(lid):
                osver.set_in_container(lid, False)
                osver.set_in_container(lid, True, n)
        except OSError as ex:
            if "versiones separadas" not in str(ex):
                raise
            self.cfg.setdefault("ctr_by_game", {})[lid] = n      # carpeta sin linux/ y windows/: se recuerda aquí
        config.save_settings(self.cfg)
        self._osv.pop(lid, None)

    def pick_container(self, e):
        """Un solo selector para ESTE juego: contenedores que existen (el actual marcado), EL SISTEMA y CREAR UNO NUEVO. Sirve para abrirlo y para compilarlo."""
        lid = self.inst(e)["launcher_id"]

        def show(names):
            cur, on = self.container_name_for(e, lid), osver.in_container(lid)

            def pick(n):
                if n is None:
                    self.create_container(e)
                    return
                if n == "":
                    self.set_run_container(e, False)
                    return
                try:
                    self._fix_container(e, lid, n)
                except (OSError, ValueError) as ex:
                    self.toast(f"No pude fijar el contenedor: {ex}")
                    return
                self.toast(f"Contenedor de este juego: {n}" + ("" if on else " · para abrirlo ahí pulsa ABRIR EN → CONTENEDOR"))
            opts = [(("✓ " if n == cur else "") + n, (lambda n=n: pick(n))) for n in names]
            opts += [(("✓ " if not on else "") + "EL SISTEMA (abrir sin contenedor)", lambda: pick("")),
                     ("CREAR UN CONTENEDOR NUEVO (Fedora)", lambda: pick(None))]
            self.modal = {"kind": "choice", "title": "Contenedor de este juego", "prev": None,
                          "msg": f"Ahora: «{cur or 'ninguno'}» ({'se abre dentro' if on else 'se abre en el sistema'}). Se usa para abrirlo y para compilarlo."
                                 + ("" if names else "\nNo encuentro ningún distrobox: crea uno."), "options": opts}
            self.focus = None
        if not recipes.have_distrobox():
            self.toast("Falta distrobox: no hay contenedores en este equipo")
            return
        self.work("Buscando contenedores…", build.refresh_containers, lambda r, err: self._rcp_q.append(lambda: show(r or [])))

    def create_container(self, e):
        """Crea «hub-<juego>» (Fedora) y lo fija en el juego. Si el juego trae receta (paquetes que pide), usa la receta."""
        lid = self.inst(e)["launcher_id"]
        if self.runtime_of(e):
            self.prepare_container(e)
            return
        name, image = "hub-" + re.sub(r"[^a-z0-9]+", "-", lid.lower()).strip("-"), "fedora:latest"

        def go():
            job = cmdjob.CmdJob("CONTENEDOR", e["name"], [(f"Crear el contenedor «{name}» ({image})", ["bash", "-c", recipes.create_cmd(name, image)])], e)

            def done(ok):
                def fin():
                    build.refresh_containers()
                    if not ok:
                        self.toast("No se pudo crear el contenedor: mira el REGISTRO en DESCARGAS")
                        return
                    try:
                        self._fix_container(e, lid, name)
                    except (OSError, ValueError) as ex:
                        self.toast(f"Contenedor creado, pero no pude fijarlo en el juego: {ex}")
                        return
                    self.toast(f"Listo: «{name}» es el contenedor de este juego")
                self._rcp_q.append(fin)
            self.builds.append(job)
            job.start(done)
            self.toast("Creando el contenedor… mira DESCARGAS (la primera vez tarda unos minutos)")
        self.confirm("CREAR CONTENEDOR", f"Crea el distrobox «{name}» con {image}. Vacío: los paquetes que pida el juego se instalan dentro (con sudo, sin tocar Bazzite). ¿Seguir?", go)

    def toggle_run_container(self, e):
        self.set_run_container(e, not osver.in_container(self.inst(e)["launcher_id"]))

    def set_run_container(self, e, on):
        """Cambiar dónde se abre Linux. `distrobox list` tarda ~1 s: se comprueba en un hilo para no congelar la interfaz."""
        lid = self.inst(e)["launcher_id"]
        if on == osver.in_container(lid):
            return
        cont = self.container_name_for(e, lid)

        def job():
            if on and cont not in build.refresh_containers():
                self._rcp_q.append(lambda: self.toast(f"El distrobox «{cont}» no existe: elige otro en AVANZADO"))
                return
            try:
                osver.set_in_container(lid, on, cont)
            except (OSError, ValueError) as ex:
                self._rcp_q.append(lambda m=str(ex): self.toast(f"No pude cambiarlo: {m}"))
                return

            def done():
                self._osv.pop(lid, None)
                self.toast("Linux se abre " + (f"dentro de «{cont}»" if on else "en el sistema"))
            self._rcp_q.append(done)
        threading.Thread(target=job, daemon=True).start()

    # ── compilar ──
    def recipe_start(self, e):
        rc = self.recipe_of(e)
        lid = self.inst(e)["launcher_id"]
        root, lin, _ = self._rcp_paths(e, lid)
        if not rc or root is None:
            self.toast("Este juego no tiene receta")
            return
        if not recipes.have_distrobox():
            self.toast("No encuentro distrobox en este equipo")
            return
        iso = library.link_get(e["id"]) if (rc.get("disc") or {}).get("name") else None
        if (rc.get("disc") or {}).get("name") and not (iso and Path(iso).exists()):
            self.toast("Antes reconoce tu archivo del juego (ISO) en la ficha: la compilación lo lee")
            return
        st = self.os_state(lid)
        if not lin.is_dir():
            if st.get("split") or not any(Path(root).iterdir()):
                lin.mkdir(parents=True, exist_ok=True)
            else:
                self.toast("Reorganiza primero la carpeta del juego (linux/ y windows/)")
                return
        name = recipes.container_name(rc, e)
        msg = (f"Hub preparará el contenedor «{name}» ({(rc.get('container') or {}).get('image', 'fedora')}) y comprobará qué le falta al proyecto.\n"
               f"Código y compilación: {lin}\nTodavía NO se instala nada del proyecto: antes verás la lista y la aceptas.")

        def go():
            try:
                recipes.ensure_source(rc, e, lin, lambda s: print(f"[receta] {s}", file=sys.stderr, flush=True))
                link = recipes.link_disc(rc, lin, iso) if iso else None
            except OSError as ex:
                self.toast(f"No pude preparar el código: {ex}")
                return
            job = cmdjob.CmdJob("COMPILAR EN CONTENEDOR", e["name"], recipes.phase1(rc, e, lin), e)
            self.builds.append(job)
            self.dl_pulse = time.time()
            job.start(done=lambda ok, job=job: self._recipe_phase1_done(e, rc, lin, link, job, ok))
            self.toast("Preparando el contenedor… mira DESCARGAS")
        self.confirm("Compilar para Linux en un contenedor", msg, lambda: threading.Thread(target=go, daemon=True).start())

    def _recipe_phase1_done(self, e, rc, lin, iso_link, job, ok):
        if not ok:
            self._rcp_q.append(lambda: self.toast("Falló la preparación: abre el REGISTRO en DESCARGAS"))
            return
        pkgs = recipes.parse_deps("\n".join(job.log), (rc.get("deps") or {}).get("ignore_marker", "(launcher)"))
        self._rcp_q.append(lambda: self._recipe_ask(e, rc, lin, iso_link, pkgs))

    def _recipe_ask(self, e, rc, lin, iso_link, pkgs):
        name = recipes.container_name(rc, e)
        lst = ", ".join(pkgs) if pkgs else "ninguno (ya está todo)"
        msg = (f"Se instalarán DENTRO de «{name}» (no en Bazzite): {lst}\n\nDespués: {', '.join((rc.get('prepare') or {}).get('run', []))}; "
               f"compilar ({', '.join((rc.get('build') or {}).get('run', []))}) y dejar el juego listo. Tarda unos minutos.")
        self.confirm("¿Instalar en el contenedor y compilar?", msg, lambda: self._recipe_phase2(e, rc, lin, iso_link, pkgs))

    def _recipe_finish(self, e, rc, lin):
        out = rc.get("output") or {}
        lid = self.inst(e)["launcher_id"]

        def finish(say):
            osver.attach_linux_build(lid, out.get("exe", ""), out.get("cwd", "."), out.get("libs", ""), recipes.container_name(rc, e), rc.get("_file", ""))
            self._osv.pop(lid, None)
            self.libchk.pop(lid, None)
            say("Versión de Linux registrada; JUGAR y Steam la abren")
            self._rcp_q.append(lambda: self.toast(f"{e['name']}: versión de Linux lista"))
        return finish

    def _recipe_phase2(self, e, rc, lin, iso_link, pkgs):
        steps = recipes.phase2(rc, e, lin, pkgs, iso_link, self._recipe_finish(e, rc, lin))
        job = cmdjob.CmdJob("COMPILAR EN CONTENEDOR", e["name"], steps, e)
        self.builds.append(job)
        self.dl_pulse = time.time()
        job.start()
        self.toast("Compilando en el contenedor… mira DESCARGAS")

    def recipe_attach(self, e):
        """Ya compilaste a mano (linux/build/vcs): solo trae las bibliotecas que falten y registra la versión, sin recompilar."""
        rc = self.recipe_of(e)
        lid = self.inst(e)["launcher_id"]
        root, lin, exe = self._rcp_paths(e, lid)
        if not rc or exe is None or not exe.is_file():
            self.toast("No encuentro el ejecutable compilado")
            return
        out = rc.get("output") or {}
        name = recipes.container_name(rc, e)
        libs = lin / out["libs"] if out.get("libs") else None
        steps = []

        def pick_cont():             # `distrobox list` tarda ~1 s: se pregunta dentro del hilo del trabajo, no en el de la interfaz
            return name if name in build.refresh_containers() else self.cfg.get("build_container", "fedora")
        if libs:
            steps.append(("Traer del contenedor las bibliotecas que falten", lambda say: recipes.resolve_libs(exe, libs, pick_cont(), say)))
        steps.append(("Registrar la versión de Linux en Hub", self._recipe_finish_as(e, rc, pick_cont)))
        job = cmdjob.CmdJob("COMPILAR EN CONTENEDOR", e["name"], steps, e)
        self.builds.append(job)
        self.dl_pulse = time.time()
        job.start()
        self.toast("Registrando tu build… mira DESCARGAS")

    def _recipe_finish_as(self, e, rc, cont):
        out = rc.get("output") or {}
        lid = self.inst(e)["launcher_id"]

        def finish(say):
            osver.attach_linux_build(lid, out.get("exe", ""), out.get("cwd", "."), out.get("libs", ""), cont() if callable(cont) else cont, rc.get("_file", ""))
            self._osv.pop(lid, None)
            say("Versión de Linux registrada")
            self._rcp_q.append(lambda: self.toast(f"{e['name']}: JUGAR abre ahora la versión de Linux"))
        return finish
