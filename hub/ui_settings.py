"""Ajustes (y su sección Avanzado). Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class SettingsMixin:
    SET_CATS = (
        ("look", "Aspecto y control", "Tema, efectos, sonidos, teclado y mando"),
        ("play", "Al jugar", "Cómo se abren tus juegos, Steam y modo de energía"),
        ("files", "Mis juegos y archivos", "Carpeta de ROMs, qué hacer con tu archivo, descargas y carátulas"),
        ("catalog", "Catálogo", "Buscar y añadir proyectos, importar listas y tu servidor de catálogo"),
        ("github", "GitHub y actualizaciones", "Cuándo se buscan versiones nuevas (gasta cuota), sesión, token, cookies y navegador"),
        ("build", "Compilar", "Contenedor y registro de compilaciones"),
        ("maint", "Mantenimiento", "Actualizar Hub, papelera, pruebas, Doctor y registros"),
    )

    def draw_settings(self, body):
        """Ajustes por categorías: una página de categorías y, al entrar en una, sus opciones con una línea que explica qué hace cada una.
        «Todos los ajustes» (adv_open) muestra todo seguido, agrupado por categoría."""
        self.begin("settings", body)
        colw = min(self.W - self.n(80), self.n(1100))
        x0 = (self.W - colw) // 2
        y = self.n(20)
        page = getattr(self, "set_page", None)

        def setn(key, lo, hi, d):
            self.cfg[key] = max(lo, min(hi, int(self.cfg[key]) + d))
            config.save_settings(self.cfg)
            self.mgr.max_active, self.mgr.connections = self.cfg["max_active"], self.cfg["connections"]

        def num_row(key, label, lo, hi, desc=""):
            nonlocal y
            h = self.n(92 if desc else 72)
            r, foc = self.reg(f"set:{key}", (x0, y, colw, h), lambda: setn(key, lo, hi, 1) if self.cfg[key] < hi else setn(key, lo, hi, lo - hi),
                              adj=lambda d: setn(key, lo, hi, d))
            if self.offscreen(r):
                y += h + self.n(12)
                return
            self.rr(r, PANEL2 if foc else PANEL, 18)
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 22, max(2, self.n(3)))
            ty = r.centery - (self.n(12) if desc else 0)
            self.text(label, r.x + self.n(26), ty, 21, TXT, False, anchor="ml")
            if desc:
                self.text(desc, r.x + self.n(26), r.centery + self.n(18), 16, DIM, False, r.w - self.n(260), "ml")
            for dx, dn in ((self.n(150), "left"), (self.n(34), "right")):
                c = pygame.Rect(0, 0, self.n(54), self.n(44))
                c.center = (r.right - dx, r.centery)
                self.rr(c, PANEL2 if not foc else PANEL, 14)
                self.tri(c.centerx, c.centery, self.n(16), dn, ACC if (self.cfg[key] > lo if dn == "left" else self.cfg[key] < hi) else LINE)
            self.text(str(self.cfg[key]), r.right - self.n(92), r.centery, 26, TXT, True, anchor="c")
            y += h + self.n(12)

        def section(title):
            nonlocal y
            y += self.n(14)
            self.text(title.upper(), x0 + self.n(8), self.cy(y), 17, DIM, True)
            y += self.n(36)

        def act_row(key, label, cb, kind="normal", desc=""):
            nonlocal y
            h = self.n(92 if desc else 72)
            r, foc = self.reg(key, (x0, y, colw, h), cb)
            if self.offscreen(r):
                y += h + self.n(12)
                return
            self.rr(r, PANEL2 if foc else PANEL, 18 * RADK)
            if OUTLINE:
                self.rr(r, LINE, 18 * RADK, max(1, self.n(2)))
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 22 * RADK, max(3, self.n(3)))
            lab, sep, val = label.partition(": ")
            val = re.sub(r"\s*\((tocar|tocar para)[^)]*\)", "", val).strip()
            if not sep:
                lab, val = label, ""

            def soft(t):
                L = [c for c in t if c.isalpha()]
                if L and sum(c.isupper() for c in L) > 0.6 * len(L):
                    t = t[:1] + t[1:].lower()
                    for w, f in (("github", "GitHub"), ("roms", "ROMs"), ("steam", "Steam"), ("hub", "Hub"), ("json", "json"), ("es-de", "ES-DE"), ("apps.json", "apps.json"), ("jugar", "Jugar"), ("mb", "MB"), ("steamgriddb", "SteamGridDB"), ("thegamesdb", "TheGamesDB"), ("owner/repo", "owner/repo"), ("tdp", "TDP"), ("edge", "Edge")):
                        t = re.sub(r"\b" + re.escape(w) + r"\b", f, t, flags=re.I)
                return t
            lab, val = soft(lab), soft(val)
            cx = r.right - self.n(60)
            vw = 0
            if val:
                vw = min(self.font(19).size(val)[0], int(r.w * 0.45))
                self.text(val, cx, r.centery - (self.n(12) if desc else 0), 19, ACC, False, vw, "mr")
            ty = r.centery - (self.n(12) if desc else 0)
            self.text(lab, r.x + self.n(26), ty, 21, ERR if kind == "danger" else TXT, False, r.w - self.n(110) - vw, "ml")
            if desc:
                self.text(desc, r.x + self.n(26), r.centery + self.n(18), 16, DIM, False, r.w - self.n(110), "ml")
            self.chevron(r.right - self.n(34), r.centery, self.n(14), DIM, "right", 3)
            y += h + self.n(12)

        def block(h):
            """Reserva un bloque libre de alto h (para cuadrículas propias) y devuelve su y."""
            nonlocal y
            top = y
            y += h + self.n(12)
            return top, x0, colw
        act_row.block = block

        rows = {"look": self._set_look, "play": self._set_play, "files": self._set_files, "catalog": self._set_catalog,
                "github": self._set_github, "build": self._set_build, "maint": self._set_maint}
        if page in rows:                       # una categoría
            title = next(t for k, t, _ in self.SET_CATS if k == page)
            act_row("set_back", "‹ Ajustes", self.settings_back, desc="Volver a las categorías (también con B)")
            self.text(title, x0 + self.n(8), self.cy(y) + self.n(6), 30, TXT, True)
            y += self.n(56)
            rows[page](act_row, section, num_row)
            self.end()
            return
        if self.upd_ready:
            act_row("upd_top", f"ACTUALIZAR HUB: HAY UNA NUEVA, {self.upd_ready['ver']} · TOCAR PARA INSTALAR", self.update_hub, desc=f"Tienes la {config.VERSION}")
        if self.adv_open:                      # todos los ajustes seguidos (lo de siempre, agrupado)
            act_row("adv", "TODOS LOS AJUSTES: lista completa abierta  (tocar para volver a las categorías)", self.toggle_adv)
            for k, t, _ in self.SET_CATS:
                section(t)
                rows[k](act_row, section, num_row)
        else:
            for k, t, d in self.SET_CATS:
                act_row("cat:" + k, t, lambda k=k: self.settings_open(k), desc=d)
            act_row("adv", "TODOS LOS AJUSTES (lista completa)", self.toggle_adv, desc="Todo en una sola lista, por si no encuentras algo")
        y += self.n(10)
        info = [("Versión de Hub", config.VERSION + self._last_update_txt())] + ([("Canal", self.memo("chan_txt", self.channel_txt, 2.0)),
                ("Ajustes de este canal", str(config.CONF)), ("Registros de este canal", str(config.STATE))] if self.adv_open and config.CHANNEL else []) + ([("Descargas", self.cfg["downloads_dir"]), ("Biblioteca", self.cfg["library_dir"]), ("Carpetas vigiladas", ", ".join(self.cfg["watch_dirs"])),
                ("Juegos instalados en", str(config.GAMES_DIR)), ("Launcher", str(config.LAUNCHER)),
                ("GitHub", f"con sesión ({self.gh_login or 'token'})" if auth.token() else "sin sesión (límite de 60 consultas/h)"),
                ("Credenciales", str(auth.FILE) + " (fuera del proyecto)"),
                ("Catálogo", f"{len(self.entries)} juegos"), ("Datos" + (" (biblioteca común)" if config.CHANNEL else ""), str(config.DATA))] if self.adv_open else [])
        for k, v in info:
            self.text(k, x0 + self.n(10), self.cy(y), 18, DIM)
            self.text(v, x0 + self.n(280), self.cy(y), 18, TXT, maxw=colw - self.n(290))
            y += self.n(30)
        y += self.n(20)
        act_row("quit", "SALIR DE FORGEINATOR", lambda: setattr(self, "running", False), "danger")
        self.end()

    def settings_open(self, k):
        self.set_page, self.focus, self.reveal = k, None, True
        self.views.setdefault("settings", View()).off = 0

    def settings_back(self):
        k, self.set_page = getattr(self, "set_page", None), None
        self.focus, self.reveal = ("cat:" + k) if k else None, True

    # ── categorías ──
    def _set_look(self, act_row, section, num_row):
        cur = FAMILY
        pos = f"{THEME_ORDER.index(cur) + 1}/{len(THEME_ORDER)}" if cur in THEME_ORDER else f"Estudio {STUDIO_ORDER.index(cur) + 1}/{len(STUDIO_ORDER)}"
        self._theme_grid(act_row, cur, pos)
        act_row("fx", "EFECTOS: " + FX_LABEL.get(self.cfg.get("fx", "glass"), FX_LABEL["glass"]), self.toggle_fx,
                desc="Cristal: todo · Equilibrado: fondo quieto, sin destellos · Rendimiento: lo mínimo")
        yn = lambda k: "SÍ" if self.cfg.get(k) else "NO"      # noqa: E731
        act_row("a11y_rm", "MOVIMIENTO REDUCIDO: " + yn("reduce_motion"), lambda: self.toggle_a11y("reduce_motion"),
                desc="Sin fondo animado, entradas, fundidos, destellos ni latidos (en todos los temas)")
        act_row("a11y_hc", "ALTO CONTRASTE: " + yn("high_contrast"), lambda: self.toggle_a11y("high_contrast"),
                desc="Texto, bordes y foco más marcados; paneles opacos (en todos los temas)")
        act_row("a11y_lt", "TEXTO GRANDE: " + yn("large_text"), lambda: self.toggle_a11y("large_text"),
                desc="Toda la letra un 20 % más grande (en todos los temas)")
        act_row("sfx", "SONIDOS DE LA INTERFAZ: " + ("SÍ" if self.sfx.enabled else "NO"), self.toggle_sfx, desc="Clics al moverte y al elegir")
        act_row("sfxv", f"VOLUMEN DE LOS SONIDOS: {round(self.sfx.volume * 100)}%", self.cycle_sfx_volume)
        act_row("hap", "VIBRACIÓN AL MANTENER PULSADO UN JUEGO: " + ("SÍ" if self.cfg.get("haptics", True) else "NO"), self.toggle_haptics,
                desc="Mantén el dedo sobre un juego de Inicio: sale su menú (el mando vibra si puede)")
        act_row("kbd", "TECLADO: " + {"auto": "AUTOMÁTICO (Steam en Big Picture)", "steam": "STEAM", "hub": "DE HUB"}.get(self.cfg.get("keyboard", "auto"), "AUTOMÁTICO"),
                self.toggle_keyboard, desc="Qué teclado sale cuando hay que escribir")
        act_row("stick", "STICK IZQUIERDO PARA NAVEGAR: " + ("SÍ" if self.cfg.get("stick_nav", True) else "NO (solo cruceta)"), self.toggle_stick)

    def _theme_grid(self, act_row, cur, pos):
        """Temas a la vista (una miniatura por tema), y debajo las paletas y los fondos del tema elegido; un toque lo aplica."""
        names = list(THEME_ORDER)
        snames = list(STUDIO_ORDER)                        # v2.97: Estudio de temas (prueba), en su propia cuadrícula
        cols = 5 if self.W >= self.n(1100) else 4
        rows_n = -(-len(names) // cols)
        srows = -(-len(snames) // cols)
        gap = self.n(12)
        th = self.n(112)
        head = self.n(44)
        shead = self.n(56)
        fam = self._fam(cur)
        lays = fam.get("layouts") or []
        pal_h, bg_h, lay_h = self.n(100), self.n(78), self.n(72)
        foot = self.n(40)
        top, x0, colw = act_row.block(head + rows_n * (th + gap) + shead + srows * (th + gap) + self.n(36) + pal_h + gap + self.n(36) + bg_h + gap
                                      + ((self.n(36) + lay_h + gap) if lays else 0) + foot)
        self.text(f"Tema  ·  {pos}", x0 + self.n(6), self.cy(top) + self.n(8), 22, TXT, True)
        tw = (colw - (cols - 1) * gap) // cols
        tc = self.__dict__.setdefault("_studio_tiles", {})

        def tile_t(nm):
            if nm == cur:
                return theme_dict(cur, PAL, ANIM or "none", STUDIO_LAYOUT)
            if nm in THEMES:
                return THEMES[nm]
            if nm not in tc:
                tc[nm] = theme_dict(nm)
            return tc[nm]
        for i, nm in enumerate(names):
            r, foc = self.reg(f"theme:{nm}", (x0 + (i % cols) * (tw + gap), top + head + (i // cols) * (th + gap), tw, th), lambda nm=nm: self.pick_theme(nm))
            if self.offscreen(r):
                continue
            self._theme_tile(r, nm, tile_t(nm), nm == cur, foc)
        y = top + head + rows_n * (th + gap)
        t1 = "Estudio de temas  ·  prueba"
        self.text(t1, x0 + self.n(6), self.cy(y) + self.n(14), 20, TXT, True)
        sx = x0 + self.n(6) + self.font(20, True).size(t1)[0] + self.n(20)     # v3.04: medido (con letra grande se montaba)
        self.text("8 identidades del motor nuevo", sx, self.cy(y) + self.n(16), 16, DIM, False, max(self.n(60), x0 + colw - sx))
        y += shead
        for i, nm in enumerate(snames):
            r, foc = self.reg(f"theme:{nm}", (x0 + (i % cols) * (tw + gap), y + (i // cols) * (th + gap), tw, th), lambda nm=nm: self.pick_theme(nm))
            if self.offscreen(r):
                continue
            self._theme_tile(r, nm, tile_t(nm), nm == cur, foc)
        y += srows * (th + gap)
        self.text(f"Paleta  ·  {self._pal_label()}", x0 + self.n(6), self.cy(y) + self.n(4), 20, TXT, True)
        y += self.n(36)
        pals = fam["pals"]
        pw = min(self.n(210), (colw - (len(pals) - 1) * gap) // len(pals))
        for i, (pid, lab, _) in enumerate(pals):
            r, foc = self.reg(f"pal:{pid}", (x0 + i * (pw + gap), y, pw, pal_h), lambda pid=pid: self.pick_pal(pid))
            if self.offscreen(r):
                continue
            c = theme_dict(cur, pid)
            rad = max(6, int(12 * RADK * self.k))
            pygame.draw.rect(self.screen, c["BG"], r, border_radius=rad)
            sw = (r.w - self.n(24)) // 4
            for j, key in enumerate(("PANEL", "ACC", "TXT", "DIM")):
                pygame.draw.rect(self.screen, c[key], (r.x + self.n(12) + j * sw, r.y + self.n(12), sw - self.n(4), self.n(34)), border_radius=max(3, rad // 3))
            self.text(lab, r.centerx, r.bottom - self.n(20), 17, c["TXT"], True, r.w - self.n(10), "c")
            pygame.draw.rect(self.screen, c["LINE"], r, max(1, self.n(2)), border_radius=rad)
            if pid == PAL:
                pygame.draw.rect(self.screen, c["ACC"], r.inflate(self.n(4), self.n(4)), max(3, self.n(4)), border_radius=rad + 2)
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 18, max(3, self.n(4)))
        y += pal_h + gap
        self.text("Fondo", x0 + self.n(6), self.cy(y) + self.n(4), 20, TXT, True)
        y += self.n(36)
        bw = min(self.n(200), (colw - (len(fam["bgs"]) - 1) * gap) // len(fam["bgs"]))
        for i, bid in enumerate(fam["bgs"]):
            r, foc = self.reg(f"bg:{bid}", (x0 + i * (bw + gap), y, bw, bg_h), lambda bid=bid: self.pick_bg(bid))
            if self.offscreen(r):
                continue
            on = bid == (ANIM or "none")
            self.rr(r, ACC if on else PANEL2, 14 * RADK)
            self.text(themes_fam.ANIM_LABEL.get(bid, bid), r.centerx, r.centery, 19, ON_ACC if on else TXT, True, r.w - self.n(12), "c")
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 18, max(3, self.n(4)))
        y += bg_h + gap
        if lays:                                             # v2.97: solo las formas de Inicio que el preset declara compatibles
            self.text("Inicio", x0 + self.n(6), self.cy(y) + self.n(4), 20, TXT, True)
            y += self.n(36)
            lw = min(self.n(240), (colw - (len(lays) - 1) * gap) // len(lays))
            for i, lid_ in enumerate(lays):
                on = lid_ == STUDIO_LAYOUT
                self.button(f"lay:{lid_}", (x0 + i * (lw + gap), y, lw, lay_h), hubthemes.studio.LAYOUT_LABEL.get(lid_, lid_),
                            lambda lid_=lid_: self.pick_layout(lid_), "seg" if on else "normal", 18)
            y += lay_h + gap
        short = THEME_LABEL.get(cur, "").partition(" (")
        self.text(short[0].capitalize() + (" — " + short[2].rstrip(")") if short[2] else ""), x0 + self.n(6), self.cy(y) + self.n(6), 18, DIM, False, colw)

    def _theme_tile(self, r, nm, t, sel, foc):
        """Miniatura: fondo del tema, su panel, un botón de acento y una línea de texto, con el nombre debajo."""
        bg, pn, ac, tx = t["BG"], t["PANEL"], t["ACC"], t["TXT"]
        rad = max(6, int(14 * t.get("RADK", 1.0) * self.k))
        pygame.draw.rect(self.screen, bg, r, border_radius=rad)
        inner = r.inflate(-self.n(16), -self.n(40)).move(0, -self.n(8))
        pygame.draw.rect(self.screen, pn, inner, border_radius=max(4, rad // 2))
        if t.get("LAYOUT") == "side":
            pygame.draw.rect(self.screen, ac, (inner.x + self.n(6), inner.y + self.n(6), self.n(8), inner.h - self.n(12)), border_radius=3)
        bw = max(self.n(20), inner.w // 3)
        pygame.draw.rect(self.screen, ac, (inner.x + self.n(24), inner.y + self.n(10), bw, self.n(14)), border_radius=max(3, rad // 3))
        pygame.draw.rect(self.screen, tx, (inner.x + self.n(24), inner.y + self.n(34), inner.w - self.n(48), self.n(6)), border_radius=3)
        pygame.draw.rect(self.screen, t["DIM"], (inner.x + self.n(24), inner.y + self.n(48), (inner.w - self.n(48)) * 2 // 3, self.n(5)), border_radius=3)
        lab = THEME_LABEL.get(nm, nm).partition(" (")[0].capitalize()
        self.text(lab, r.centerx, r.bottom - self.n(18), 16, tx, True, r.w - self.n(10), "c")
        pygame.draw.rect(self.screen, t["LINE"], r, max(1, self.n(2)), border_radius=rad)
        if sel:
            pygame.draw.rect(self.screen, ac, r.inflate(self.n(4), self.n(4)), max(3, self.n(4)), border_radius=rad + 2)
            pygame.draw.circle(self.screen, ac, (r.right - self.n(18), r.top + self.n(18)), self.n(7))
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 18, max(3, self.n(4)))

    def _set_play(self, act_row, section, num_row):
        act_row("direct", "ARRANQUE DIRECTO (SIN LA PANTALLA DEL LAUNCHER): " + ("SÍ" if self.cfg.get("direct_play", True) else "NO"), self.toggle_direct_play,
                desc="Hub ya actualiza los juegos: se abren sin la comprobación, novedades ni cuenta atrás del launcher")
        act_row("viasteam", "CÓMO SE ABRE EL JUEGO: " + ("CON SU ACCESO DE STEAM" if self.cfg.get("play_via_steam", True) else "DESDE HUB"),
                self.toggle_via_steam, desc="Con su acceso, Big Picture muestra el juego con su nombre y arte, no como «Forgeinator»")
        act_row("splash", "PANTALLA DE CARGA AL ABRIR POR STEAM: " + ("SÍ" if self.cfg.get("steam_splash", True) else "NO"), self.toggle_steam_splash,
                desc="Hub muestra «Abriendo…» hasta que el juego aparece; si no aparece en 5 s, se cierra como antes")
        act_row("closeplay", "HUB AL EMPEZAR A JUGAR: " + ("SE CIERRA" if self.cfg.get("close_on_play", True) else "SE QUEDA ABIERTO"), self.toggle_close_on_play,
                desc="Cerrar Hub libera memoria y batería mientras juegas")
        act_row("power", "MODO DE ENERGÍA: " + self.power_label(), self.cycle_power_mode, desc="Ahorro: menos fps y sin animaciones (automático con TDP ≤ 9 W o batería baja)")
        act_row("proton_def", "PROTON POR DEFECTO (JUEGOS DE WINDOWS): " + (Path(self.cfg.get("proton_default")).name if self.cfg.get("proton_default") else "AUTOMÁTICO (" + Path(self.memo("proton", osver.proton_path, 10.0)).name + ")"),
                self.cycle_proton_default, desc="Para los juegos nuevos; cada juego puede elegir el suyo en su ficha → LANZAR. Cada toque pasa al siguiente instalado")
        act_row("steamprep", "AÑADIR TODO A STEAM", lambda: self.go_tab("steam"), desc="Accesos, iconos y arte de todos tus juegos en Steam")

    def _set_files(self, act_row, section, num_row):
        act_row("romdir", "CARPETA DE ROMS: " + (", ".join(self.cfg.get("rom_dirs") or [str(r) for r in self.roms_roots()]) or "(sin definir)"), self.set_rom_dirs,
                desc="Dónde están tus copias de los juegos (estilo ES-DE: una subcarpeta por consola)")
        act_row("store", "AL RECONOCER TU ARCHIVO: " + {"ask": "PREGUNTAR", "copy": "COPIAR a tu biblioteca", "move": "MOVER a tu biblioteca", "link": "SOLO ENLAZAR"}[
            self.cfg.get("esde_store", "ask") if self.cfg.get("esde_store", "ask") in ("ask", "copy", "move", "link") else "ask"], self.toggle_store_mode,
                desc="Si lo guarda en tu carpeta de ROMs; el juego siempre recibe un enlace dentro de su carpeta")
        act_row("remotes", "BIBLIOTECAS REMOTAS: " + self._remote_txt(),
                lambda: self.remote_cancel() if getattr(self, "_rdl", None) and self._rdl.get("busy") else self.remotes_menu(),
                desc="WebDAV, Samba, SFTP, FTP o cualquier remoto de rclone con carpetas por sistema (como ES-DE). Durante una descarga: tocar = cancelar")
        act_row("plugins", "COMPLEMENTOS: " + self._plugins_txt(), self.plugins_menu,
                desc="Conectores extra instalables desde un zip (servidores con API propia). Activar, desactivar, quitar")
        section("Descargas")
        num_row("max_active", "Descargas simultáneas", 1, 5)
        num_row("connections", "Conexiones por descarga", 1, 8, desc="Más conexiones suele ir más rápido; algunos servidores lo limitan")
        act_row("retnav", "VOLVER A HUB AL DETECTAR UNA DESCARGA: " + ("SÍ" if self.cfg.get("return_to_hub", True) else "NO"), self.toggle_return,
                desc="Cuando bajas algo en el navegador, Hub vuelve delante")
        section("Carátulas")
        act_row("covers", "DESCARGAR CARÁTULAS FALTANTES: " + self._covers_txt(), self.covers_batch, desc="SteamGridDB y libretro (consolas), 4 a la vez; lo que no existe no se repite")
        act_row("k_sgdb", "CLAVE DE STEAMGRIDDB: " + ("guardada" if self.memo("k_sgdb", sgdb.key) else "falta"), lambda: self.osk(
            "Clave de SteamGridDB (steamgriddb.com → Preferences → API)", lambda t: (sgdb.save_key(t), self.toast("Clave guardada")) if t.strip() else None, ""),
                desc="Necesaria para buscar carátulas y arte")
        act_row("k_tgdb", "CLAVE DE THEGAMESDB: " + ("guardada" if self.memo("k_tgdb", artsrc.tgdb_key) else "falta"), self.art_tgdb_key)

    def _set_catalog(self, act_row, section, num_row):
        act_row("go_search", "BUSCAR PROYECTOS EN GITHUB", lambda: self.go_tab("search"), desc="Busca un juego y crea su tarjeta con lo que diga el repositorio")
        act_row("add_repo", "AÑADIR REPOSITORIO", lambda: self.osk("Repositorio de GitHub", self.add_repo, "", "ej.: z3xox/Tenkaichi3Decomp"), desc="Pega owner/repo o la URL de GitHub")
        act_row("addgame", "AÑADIR JUEGO DESDE EL NAVEGADOR", self.add_game_flow, desc="Abre GitHub para que elijas el repositorio")
        section("Listas de juegos")
        act_row("idx", "ACTUALIZAR LISTA DE PROYECTOS" + ("  · trabajando…" if self._idx_busy else ""), self.update_index,
                desc="awesome-decomp-games: ~1100 listos para jugar + ~1000 solo código")
        for lab, url in catalog.PRESETS:
            act_row("preset:" + url, "IMPORTAR CATÁLOGO: " + lab, lambda url=url: self.import_list(url))
        act_row("imp_url", "IMPORTAR LISTA DE JUEGOS (URL)", lambda: self.osk("URL de la lista (https://…/apps.json)", self.import_list, "https://"), desc="Un apps.json de GithubLauncher o Quiver")
        act_row("imp_file", "IMPORTAR LISTA DE JUEGOS (ARCHIVO)", lambda: self.open_picker("Elige un .json", self._first_dir(), {".json"}, self.import_list))
        section("Servidor de catálogo")
        act_row("catauto", "ARRANCAR EL SERVICIO CON HUB: " + ("SÍ" if self.cfg.get("catalog_autostart", True) else "NO"), self.toggle_cat_autostart,
                desc="Tu servidor que busca y descarga tus copias de los juegos")

    def _set_github(self, act_row, section, num_row):
        section("Actualizaciones (cada consulta gasta cuota de GitHub)")
        st = ghstats.S
        act_row("gh_use", f"CONSULTAS DE ESTA SESIÓN: {st['calls']}", self.gh_check,
                desc=f"{st['notmod']} sin cambios (gratis) · {st['errors']} con error · tocar para ver tu cuota y los detalles")
        act_row("chk", "COMPROBAR AHORA LAS ACTUALIZACIONES DE TUS JUEGOS", self.check_all, desc="Una consulta por juego instalado (con caché de 6 h y ETag casi siempre gratis)")
        act_row("chk_start", "COMPROBAR AL ARRANCAR HUB: " + ("SÍ" if self.cfg.get("check_on_start", False) else "NO"), lambda: self.toggle_cfg("check_on_start", False, "Comprobar al arrancar"),
                desc="Busca versiones nuevas de lo instalado unos segundos después de abrir Hub (usa consultas de GitHub)")
        act_row("fetch_open", "CONSULTAR GITHUB AL ABRIR UNA FICHA: " + ("SÍ" if self.cfg.get("fetch_on_open", True) else "NO"), lambda: self.toggle_cfg("fetch_on_open", True, "Consultar al abrir una ficha"),
                desc="Con NO, la ficha usa lo guardado y tú pulsas REFRESCAR cuando quieras")
        act_row("lchk", "EL LAUNCHER COMPRUEBA ACTUALIZACIONES AL ABRIR CADA JUEGO: " + ("SÍ" if self.cfg.get("launcher_checks", True) else "NO"), self.toggle_launcher_checks,
                desc="Una consulta a GitHub por cada arranque de juego. NO lo apaga para TODOS los juegos (se recuerda el ajuste de cada uno y vuelve con SÍ)")
        section("Sesión")
        act_row("gh_login", "SESIÓN DE GITHUB: " + (f"iniciada como {self.gh_login or '…'}" if auth.token() else "INICIAR (código en pantalla)"), self.gh_login_flow,
                desc="Con sesión, 5000 consultas por hora en vez de 60")
        act_row("gh_tok", "PEGAR TOKEN DE ACCESO DE GITHUB", self.gh_paste_token)
        act_row("gh_test", "COMPROBAR SESIÓN Y LÍMITES", self.gh_check, desc="Cuántas consultas te quedan y cuántas ha hecho Hub")
        act_row("gh_cookies", "COOKIES DE GITHUB: " + ("guardadas" + (f" ({ghcookies.user()})" if ghcookies.user() else "") if ghcookies.saved() else "sin importar"),
                self.gh_cookies_import, desc="El .json de Cookie-Editor, para entrar ya con sesión en el navegador")
        act_row("gh_web", "ABRIR GITHUB CON TU SESIÓN", self.gh_web_login, desc="Entra en el navegador con las cookies guardadas (o impórtalas)")
        act_row("gh_open", "ABRIR UN PROYECTO DE GITHUB", lambda: self.osk("Proyecto de GitHub (owner/repo o URL)", self.open_repo_web, "", "ej.: HarbourMasters/Shipwright"),
                desc="Pega owner/repo o una URL; se abre en el navegador elegido")
        if ghcookies.saved():
            act_row("gh_cookies_del", "BORRAR COOKIES GUARDADAS", self.gh_cookies_forget, "danger")
        if self.memo("gh_stored", auth.stored):
            act_row("gh_out", "CERRAR SESIÓN DE GITHUB", self.gh_logout, "danger", desc="Borra las credenciales guardadas en este equipo")
        section("Navegador")
        act_row("browser", "NAVEGADOR: " + self.cfg.get("browser", "auto").upper()[:60], self.browser_menu, desc="Con cuál se abren las páginas de los proyectos")
        act_row("hbinst", "NAVEGADOR DE HUB: " + ("INSTALADO" if self._hb_ok else "INSTALAR (~150 MB)"), lambda: self.install_hub_browser(ask=True))
        act_row("hblvl", "COMPATIBILIDAD GRÁFICA DEL NAVEGADOR: " + hubbrowser.LEVELS[min(int(self.cfg.get("browser_level", 0)), 2)][0], self.toggle_hblevel,
                desc="Bájala si el navegador se queda en negro o se cuelga")
        act_row("bzoom", f"ZOOM DEL NAVEGADOR: {UI.zoom}", self.toggle_zoom)

    def _set_build(self, act_row, section, num_row):
        act_row("cont", f"CONTENEDOR DE COMPILACIÓN: {self.cfg.get('build_container', 'fedora') or '(sistema)'}", self.set_container,
                desc="El distrobox donde se compilan los ports que no traen build de Linux")
        act_row("blog", "COMPILACIONES REGISTRADAS: " + self.memo("blog", buildlog.summary, 5.0), self.show_buildlog)

    def _set_maint(self, act_row, section, num_row):
        if config.CHANNEL:                     # v3.15: estable y dev conviviendo
            act_row("chan", "CANAL: " + self.memo("chan_txt", self.channel_txt, 2.0), self.switch_channel,
                    desc="Solo la copia activa ajusta los atajos de Steam y la apariencia del QAM. Biblioteca común; ajustes separados")
        if config.CHANNEL == "stable":
            act_row("upd", f"ACTUALIZAR HUB (versión {config.VERSION}): llega desde el QAM (releases de GitHub)", self.update_hub)
        else:
            act_row("upd", f"ACTUALIZAR HUB (versión {config.VERSION}): " + (f"HAY UNA NUEVA, {self.upd_ready['ver']}" if self.upd_ready else "buscar zip en ~/Games/actualizaciones"),
                    self.update_hub)
        act_row("updauto", "ACTUALIZAR SOLO AL ABRIR HUB: " + ("SÍ" if self.cfg.get("auto_update", True) else "NO"), self.toggle_autoupdate)
        section("Papelera")
        ops = self.trash_ops()
        act_row("trash_r", "RESTAURAR LO ÚLTIMO BORRADO: " + (ops[-1]["label"] if ops else "nada que restaurar"), self.trash_restore_last)
        act_row("trash_e", f"VACIAR LA PAPELERA: {len(ops)} borrados" if ops else "VACIAR LA PAPELERA: vacía", self.trash_empty_ask, "danger")
        section("Pruebas y diagnóstico")
        act_row("tests_run", "EJECUTAR PRUEBAS DE HUB" + ("  · trabajando…" if any(b.state in ("queued", "running") and getattr(b, "label", "") == "PRUEBAS" for b in self.builds) else ""),
                self.run_tests, desc="Tarda unos minutos; el resultado sale en DESCARGAS")
        act_row("tests_last", "ÚLTIMO RESULTADO: " + self._tests_last_txt(), self.show_tests_report)
        act_row("doctor", "DOCTOR", self.run_doctor, desc="Comprueba pantalla, disco, launcher, red y duplicados")
        act_row("launchlogs", f"REGISTROS DE ARRANQUE: {self.memo("launchlogs", lambda: len(launchlog.reports()), 5.0)} guardados", self.send_launchlogs,
                desc="Junta los arranques fallidos en un archivo para enviármelo")
        act_row("report", "INFORME DE ERROR O SUGERENCIA: " + self._report_txt(), self.report_menu,
                desc="Vista previa con tokens, cookies y tu usuario tapados; se guarda como zip o se abre como issue de GitHub")
        act_row("showlog", "VER REGISTRO DE HUB", self.show_hublog, desc="hub.log: errores, coincidencias y mando")
        act_row("perf", "REGISTRAR RENDIMIENTO: " + ("SÍ" if self.perf.on else "NO"), self.toggle_perf, desc="Anota en hub.log los fotogramas lentos")
