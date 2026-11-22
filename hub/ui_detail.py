"""Ficha de un juego y página del repositorio. Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class DetailMixin:
    def draw_detail(self, body):
        e = self.entry(self.detail)
        rel = self.rel_for(e)
        inf = self.inst(e)
        v = self.begin("detail", body)
        colw = min(self.W - self.n(80), self.n(1200))
        x0 = (self.W - colw) // 2
        inner = colw - self.n(48)
        y = self.n(18)
        in_set = e["id"] in self.more_open
        self.button("back", (x0, y, self.n(230) if in_set else self.n(170), self.n(72)), "‹ A LA FICHA" if in_set else "‹ ATRÁS",
                    (lambda: self.more_open.discard(e["id"])) if in_set else (lambda: setattr(self, "detail", None)), size=20)
        y += self.n(90)
        # ═══ TRES PASOS: archivo del juego → descargar → jugar ═══
        req = e.get("requires") or {}
        lk = library.link_get(e["id"])
        mr = self.match_res.get(e["id"])
        det = self.detected.get(e["id"])
        needs_file = bool(roms.req_lines(req)) or (e["platform"] or "").strip().lower() not in ("", "pc")
        file_ok = bool(mr.get("ok")) if (mr and "ok" in mr) else bool(lk)
        sers = (req.get("serials") or []) if isinstance(req, dict) else []
        if len(sers) >= 2:                      # v2.66: port con VARIOS discos (God of War PSP): el paso 1 está listo cuando están todos enlazados
            dlk = library.disc_links(e["id"])
            dok = {sx: bool(dlk.get(sx) and Path(dlk[sx]).exists()) for sx in sers}
            file_ok = all(dok.values())
        busy_hash = bool(mr and mr.get("busy"))
        more = e["id"] in self.more_open
        assets = (rel or {}).get("assets") or []
        wlist = (rel or {}).get("win_assets") or []
        osv = self.asset_view(e, inf, assets, wlist)
        dls = [d for d in self.mgr.list() if d.meta.get("install") == e["id"] and d.state in ("queued", "active", "paused", "error")]
        lat = self.rel.get(self.rk(e)) or rel
        has_upd = bool(inf["installed"] and lat and lat.get("tag") and inf["version"] and lat["tag"] != inf["version"] and rel is lat and not self.frozen(e))
        step = 1 if (needs_file and not file_ok) else (2 if (not inf["installed"] or has_upd) else 3)
        mode = self.cfg.get("file_mode", "local")
        self.cat_refresh_health()
        alldead = bool(self.cat_health) and all(v == "DEAD" for v in self.cat_health.values())
        if not more:
            # ═══ CABECERA: carátula + título + datos + estado (v2.73) ═══
            gname = gamedict.game_name(e)
            kind = self.media_kind(e)
            pad = self.n(24)
            cw = max(self.n(170), min(self.n(230), int(colw * 0.21)))
            chh = int(cw * 1.36)
            rx = x0 + pad + cw + self.n(30)
            rw = x0 + colw - pad - rx
            nl = len(self.wrap(e["notes"], 19, rw, False, 3)) if e.get("notes") else 0
            hh = max(chh, 56 + 46 + nl * 26 + 22 + 48) + 2 * pad
            hero = pygame.Rect(x0, y, colw, hh)
            self.rr((hero.x, self.cy(hero.y), hero.w, hero.h), PANEL, 24)
            cr = pygame.Rect(x0 + pad, self.cy(y + pad), cw, hh - 2 * pad)
            self.thumb(e, cr)
            ty = y + pad
            self.text(e["name"], rx, self.cy(ty) + self.n(22), 38, TXT, True, rw, anchor="ml")
            ty += self.n(56)
            cx_ = rx
            for lab, bg, fg in ((e["platform"], ACC, (255, 255, 255)), (("Juego: " + gname) if gname else "", PANEL2, TXT), (e["repo"], BG, DIM)):
                if lab and cx_ < x0 + colw - pad - self.n(120):
                    cx_ = self.chip(cx_, self.cy(ty), self.fit(lab, 16, x0 + colw - pad - cx_ - self.n(30), True), bg, fg) + self.n(10)
            ty += self.n(46)
            if e.get("notes"):
                self.para(e["notes"], rx, self.cy(ty), 19, rw, DIM, False, 3)
                ty += self.n(nl * 26 + 14)
            hbtn_inst = step == 2 and not dls
            hbtn_play = bool(inf["installed"]) or step == 3
            hbtn = hbtn_inst or hbtn_play
            sy = y + hh - pad - self.n(40) - (self.n(86) if hbtn else 0)
            cx_ = rx
            if needs_file:
                col_ = OK if file_ok else WARN
                c0 = cx_
                ok_t = f"{sum(dok.values())} de {len(sers)} discos" if len(sers) >= 2 else ("Archivo reconocido" if file_ok else "Falta tu archivo")
                cx_ = self.chip(cx_, self.cy(sy), ok_t, BG, col_, 16, left=self.n(50)) + self.n(10)
                self.draw_media_icon(c0 + self.n(25), self.cy(sy) + self.n(17), self.n(10), kind, file_ok)
                if file_ok and len(sers) < 2:                                    # v2.76: el archivo reconocido se puede cambiar desde la ficha
                    self.button("chg_file_h", (cx_, sy - self.n(2), self.n(120), self.n(40)), "CAMBIAR", lambda: self.pick_file(e), "normal", 15)
                    cx_ += self.n(132)
            cx_ = self.chip(cx_, self.cy(sy), ("Instalado " + (inf["version"] or "")).strip() if inf["installed"] else "No instalado", BG, OK if inf["installed"] else DIM, 16,
                            dot=OK if inf["installed"] else LINE) + self.n(10)
            if inf["installed"] and lat and lat.get("tag") and inf["version"]:
                if has_upd:
                    self.chip(cx_, self.cy(sy), "Actualización " + lat["tag"], BG, WARN, 16, dot=WARN)
                elif lat["tag"] == inf["version"]:
                    self.chip(cx_, self.cy(sy), "Al día", BG, OK, 16, dot=OK)
            if hbtn:
                by = y + hh - pad - self.n(72)
                bxr = x0 + colw - pad
                pw = self.n(300) if not hbtn_inst else self.n(200)
                bwid = self.n(300)
                if hbtn_play:
                    self.button("play", (bxr - pw, by, pw, self.n(72)), "JUGAR", lambda: self.play(e), "ok" if step == 3 else "normal", 26 if step == 3 else 22, enabled=inf["installed"])
                if hbtn_inst:
                    ix = bxr - (pw + self.n(14) if hbtn_play else 0) - bwid
                    if osv == "windows" and wlist:
                        wl = "ACTUALIZAR WINDOWS" if (has_upd and self.os_state(inf["launcher_id"]).get("windows")) else \
                            ("REINSTALAR WINDOWS" if self.os_state(inf["launcher_id"]).get("windows") else ("AÑADIR WINDOWS" if inf["installed"] else "INSTALAR WINDOWS"))
                        self.button("install", (ix, by, bwid, self.n(72)), wl + " · PROTON", lambda: self.install_windows_dl(e, fresh=not inf["installed"]), "primary", 18)
                    else:
                        self.button("install", (ix, by, bwid, self.n(72)), "ACTUALIZAR" if has_upd else ("REINSTALAR" if inf["installed"] else "INSTALAR"),
                                    lambda: self.do_install(e), "primary", 24, enabled=bool(assets))
                    if not e["repo"] or self.rk(e) in self.loading or not (rel and rel.get("tag")):
                        why = "Sin repositorio: no hay descargas" if not e["repo"] else ("Consultando GitHub…" if self.rk(e) in self.loading else ((rel or {}).get("error") or "Sin datos todavía"))
                        self.text(why, rx, self.cy(by) + self.n(36), 17, WARN, False, max(self.n(100), ix - rx - self.n(14)), anchor="ml")
            y = hero.bottom + self.n(18)
            nest_ = self.layout_bad(inf) if inf["installed"] else ""
            if nest_:                                     # v2.76: la actualización dejó la versión nueva dentro de una subcarpeta (BT4/BT3): el juego no arranca
                bh = self.n(112)
                br = pygame.Rect(x0, self.cy(y), colw, bh)
                self.rr(br, PANEL, 20)
                self.rr(br, WARN, 20, max(2, self.n(3)))
                self.text("La carpeta del juego quedó mal después de actualizar", x0 + self.n(28), self.cy(y) + self.n(32), 22, WARN, True, colw - self.n(420))
                self.text(f"La versión nueva está dentro de «{nest_}/». Reparar la sube un nivel; tus datos (partidas, mods, gamedata) no se tocan.",
                          x0 + self.n(28), self.cy(y) + self.n(70), 17, DIM, False, colw - self.n(420))
                self.button("repair_dir", (x0 + colw - self.n(360), y + self.n(20), self.n(330), self.n(72)), "REPARAR CARPETA", lambda: self.repair_dir(e, inf), "primary", 22)
                y += bh + self.n(18)
            oi_ = self.own_info(inf["launcher_id"]) if inf["installed"] else None
            cards_ = bool(oi_ and oi_["cfg"]["profile"] == "gow" and osver.windows_runner(inf["launcher_id"]) == "own")
            if cards_:
                y = self._own_cards_main(e, oi_, x0, y, colw)         # v2.75: lo que se juega a diario (qué juego abrir) está en la ficha
            h1 = 104 + (80 if needs_file else 0)
            h2 = 104 + (50 if dls else 0)
            h3 = 104
            show = [1] if (step == 1 and not (cards_ and len(sers) >= 2)) else ([2] if (step == 2 and dls) else [])      # v2.75: el panel solo sale para el archivo o una descarga en curso
            ph = 20 + 34 + sum({1: h1, 2: h2, 3: h3}[i] for i in show) + 12 * (len(show) - 1) + 20
            if show:
                pnl = pygame.Rect(x0, y, colw, self.n(ph))
                self.rr((pnl.x, self.cy(pnl.y), pnl.w, pnl.h), PANEL, 22)
                px, yy = x0 + self.n(24), y + self.n(20)
                self.text(f"SIGUIENTE PASO  ·  {step} DE 3", px, self.cy(yy), 18, DIM, True)
                for i_, lab_ in enumerate(("ARCHIVO", "INSTALAR", "JUGAR"), 1):          # tres puntos: hecho / el que toca / pendiente
                    dx = px + inner - self.n(46) * (3 - i_) - self.n(14)
                    pygame.draw.circle(self.screen, OK if i_ < step else (ACC if i_ == step else LINE), (dx, self.cy(yy) + self.n(10)), self.n(8))
                yy += self.n(34)
                bwid = self.n(330)

                def card(i, top, hh, title, status, scol):
                    r = pygame.Rect(px, self.cy(top), inner, self.n(hh))
                    self.rr(r, PANEL2 if step == i else BG, 16)
                    if step == i:
                        self.rr(r, ACC, 16, max(2, self.n(3)))
                    done = (i == 1 and (file_ok or not needs_file)) or (i == 2 and inf["installed"] and not has_upd) or (i == 3 and False)
                    c = (px + self.n(40), self.cy(top) + self.n(52))
                    pygame.draw.circle(self.screen, OK if done else (ACC if step == i else LINE), c, self.n(22))
                    if done:
                        self.check(c[0], c[1], self.n(16), ON_ACC)
                    else:
                        self.text(str(i), c[0], c[1], 22, ON_ACC if step == i else DIM, True, anchor="c")
                    self.text(title, px + self.n(84), self.cy(top) + self.n(36), 26, TXT, True, inner - self.n(84) - bwid - self.n(30))
                    self.text(status, px + self.n(84), self.cy(top) + self.n(72), 19, scol, maxw=inner - self.n(84) - bwid - self.n(30))
                    return pygame.Rect(px + inner - bwid - self.n(16), top + self.n(16), bwid, self.n(72))

                # paso 1 · archivo
                if not needs_file:
                    st1, c1 = "Este juego no necesita un archivo tuyo", OK
                elif busy_hash:
                    st1, c1 = f"Calculando hash… {self.progress.get(e['id'], 0) * 100:.0f}%", WARN
                elif len(sers) >= 2:
                    st1 = f"{sum(dok.values())} de {len(sers)} discos  ·  " + "   ".join(("✓ " if dok[sx] else "✗ ") + ownwine.disc_label(sx) for sx in sers)
                    c1 = OK if file_ok else WARN
                elif file_ok:
                    st1, c1 = "Listo: " + Path((mr or {}).get("path") or lk).name, OK
                elif mr and mr.get("ok") is False:
                    st1, c1 = "No coincide: " + Path(mr.get("path") or "?").name + (f" ({mr['how']})" if mr.get("how") else ""), WARN
                elif det:
                    st1, c1 = "Detectado en descargas: " + Path(det).name, WARN
                else:
                    lines = roms.req_lines(req)
                    st1, c1 = (lines[0] if lines else "Falta el archivo de tu copia del juego"), DIM
                if 1 in show:
                    rb = card(1, yy, h1, "Archivo del juego", st1, c1)
                    if needs_file:
                        first = step == 1
                        if mode == "server":
                            self.button("rsrv", rb, "BUSCAR EN MI SERVIDOR" + (" (caído)" if alldead else ""), lambda: self.cat_open(e), "primary" if first else "normal", 17, enabled=not alldead)
                        else:
                            self.button("rlib", rb, "BUSCAR EN MI EQUIPO", lambda: self.rom_search(e), "primary" if first else "normal", 18)
                        sy = yy + self.n(104)
                        sw = (inner - self.n(32)) // 3
                        self.button("mode_local", (px + self.n(16), sy, sw, self.n(72)), "EN MI EQUIPO", lambda: (self.cfg.__setitem__("file_mode", "local"), config.save_settings(self.cfg)),
                                    "seg" if mode == "local" else "normal", 17)
                        self.button("mode_server", (px + self.n(16) + sw + self.n(8), sy, sw, self.n(72)), "EN MI SERVIDOR", lambda: (self.cfg.__setitem__("file_mode", "server"), config.save_settings(self.cfg)),
                                    "seg" if mode == "server" else "normal", 17)
                        self.button("pick", (px + self.n(16) + 2 * (sw + self.n(8)), sy, sw - self.n(8), self.n(72)), "ELEGIR ARCHIVO…", lambda: self.pick_file(e), "normal", 17)
                    yy += self.n(h1) + self.n(12)
                # paso 2 · descargar
                if 2 in show:
                    if inf["installed"] and not has_upd:
                        st2, c2 = f"Instalada: {inf['version'] or 'sí'}", OK
                    elif not e["repo"]:
                        st2, c2 = "Sin repositorio: no hay descargas (mira AJUSTES DEL JUEGO)", WARN
                    elif self.rk(e) in self.loading:
                        st2, c2 = "Consultando GitHub…", DIM
                    elif rel and rel.get("tag"):
                        a0 = assets[min(self.sel_asset.get(e["id"], 0), max(0, len(assets) - 1))] if assets else None
                        w0 = wlist[min(self.sel_win.get(e["id"], 0), len(wlist) - 1)] if wlist else None
                        if osv == "windows" and w0:
                            st2 = f"{'Actualizar a' if has_upd else 'Versión'} {rel['tag']} · {w0['name']} · {fmt_size(w0['size'])} (Windows, con Proton)"
                            c2 = WARN if has_upd else TXT
                        else:
                            st2 = (f"{'Actualizar a' if has_upd else 'Versión'} {rel['tag']}" + (f" · {a0['name']} · {fmt_size(a0['size'])}" if a0 else
                                   (f" · solo Windows: {wlist[0]['name']} · {fmt_size(wlist[0]['size'])} (con Proton)" if wlist else " · sin build para Linux (mira AJUSTES DEL JUEGO)")))
                            c2 = WARN if has_upd or not a0 else TXT
                    else:
                        st2, c2 = (rel or {}).get("error") or "Sin datos todavía", WARN
                    rb = card(2, yy, 104, "Descargar e instalar", st2, c2)
                    label = "ACTUALIZAR" if has_upd else ("REINSTALAR" if inf["installed"] else "INSTALAR")
                    if osv == "windows" and wlist:   # elegiste (o es la única) la versión de Windows: se descarga ese build y se abre con Proton
                        wl = "ACTUALIZAR WINDOWS" if (has_upd and self.os_state(inf["launcher_id"]).get("windows")) else \
                            ("REINSTALAR WINDOWS" if self.os_state(inf["launcher_id"]).get("windows") else ("AÑADIR WINDOWS" if inf["installed"] else "INSTALAR WINDOWS"))
                        self.button("install", rb, wl + " · PROTON", lambda: self.install_windows_dl(e, fresh=not inf["installed"]), "primary" if step == 2 else "normal", 19)
                    else:
                        self.button("install", rb, label, lambda: self.do_install(e), "primary" if step == 2 else "normal", 22, enabled=bool(assets))
                    if dls:
                        d = dls[0]
                        bar = pygame.Rect(px + self.n(84), self.cy(yy) + self.n(92), inner - self.n(84) - self.n(24), self.n(12))
                        self.rr(bar, BG if step != 2 else PANEL, 6)
                        self.rr((bar.x, bar.y, int(bar.w * d.progress), bar.h), ERR if d.state == "error" else ACC, 6)
                        self.text(("Error: " + d.error) if d.state == "error" else f"{'Pausada' if d.state == 'paused' else 'Descargando'} {d.progress * 100:.0f}%  ·  {fmt_size(d.speed)}/s",
                                  px + self.n(84), self.cy(yy) + self.n(128), 17, ERR if d.state == "error" else DIM, maxw=inner - self.n(120))
                    yy += self.n(h2) + self.n(12)
                # paso 3 · jugar
                if 3 in show:
                    rb = card(3, yy, 104, "Jugar", "Todo listo" if inf["installed"] else "Disponible cuando esté instalado", OK if inf["installed"] else DIM)
                    self.button("play", rb, "JUGAR", lambda: self.play(e), "ok", 24, enabled=inf["installed"])
                y = pnl.bottom + self.n(18)
            if inf["installed"]:
                st_ = self.os_state(inf["launcher_id"])
                self.rr((x0, self.cy(y), colw, self.n(84)), PANEL, 20)
                self.text("SE ABRE ASÍ", x0 + self.n(24), self.cy(y) + self.n(22), 15, DIM, True)
                self.text(self.play_summary(e, inf, st_).replace("JUGAR y Steam abren ahora: ", ""), x0 + self.n(24), self.cy(y) + self.n(54), 21, TXT, True, colw - self.n(260))
                self.button("how_edit", (x0 + colw - self.n(210), y + self.n(8), self.n(194), self.n(68)), "CAMBIAR", lambda: (self.more_open.add(e["id"]), self.more_tab.__setitem__(e["id"], "jugar")), "normal", 18)
                y += self.n(100)
            y = self._folders_row(e, inf, x0, y, colw, draw=False)     # solo mantiene el enlace al archivo; la lista de rutas está en MÁS OPCIONES → AVANZADO
            if inf["installed"] and self.via_steam_ok():
                sc = self.steam_shortcut(inf["launcher_id"], e["name"])
                if sc:
                    self.text(f"JUGAR lo abre con su acceso de Steam «{sc['name']}»: en Big Picture sale con su nombre y su arte.", x0, self.cy(y), 16, OK, False, colw)
                else:
                    self.text("Sin acceso en Steam: se verá como «Forgeinator». Ajustes → AÑADIR TODO A STEAM para que salga con su nombre.", x0, self.cy(y), 16, WARN, False, colw)
                y += self.n(32)
            miss = self.libs_for(inf["launcher_id"]) if inf["installed"] else []
            if miss:
                self.text("Faltan bibliotecas del sistema: " + ", ".join(miss[:5]) + (" …" if len(miss) > 5 else "") + "  ·  el juego no arrancará así",
                          x0, self.cy(y), 18, ERR, True, colw)
                y += self.n(40)
            lrep = launchlog.latest(inf["launcher_id"]) if inf["installed"] else None
            if lrep:
                self.button("launchlog", (x0, y, colw, self.n(64)), f"EL ÚLTIMO ARRANQUE FALLÓ ({time.strftime('%d/%m %H:%M', time.localtime(lrep.stat().st_mtime))})  ·  VER EL REGISTRO",
                            lambda: self.show_launchlog(e), "normal", 17)
                y += self.n(78)
            if inf["installed"]:                      # v3.02: tarjeta VERSIONES (qué hay, qué está instalado, qué abre JUGAR)
                y = self.versions_card(e, inf, rel, x0, y, colw)
            self.button("more", (x0, y, colw, self.n(72)), "AJUSTES DEL JUEGO ›   archivo, cómo se juega, versiones, Steam y arte, compilar, borrar…",
                        lambda: (self.more_open.add(e["id"]), self.more_tab.__setitem__(e["id"], self.more_tab_for(e, step))), "normal", 18)
            y += self.n(90)
            self.cur.nh = max(self.cur.nh, y + self.n(40))
            self.end()
            return

        # ═══ AJUSTES DEL JUEGO (v2.74): menú a la izquierda, un solo apartado a la derecha ═══
        bk = self.build_kind(e)
        cont = self.cfg.get("build_container", "fedora")
        tab = self.more_tab_for(e, step)
        thr = pygame.Rect(x0, self.cy(y), self.n(48), self.n(64))
        self.thumb(e, thr)
        self.text(e["name"], x0 + self.n(66), self.cy(y) + self.n(22), 28, TXT, True, colw - self.n(80), anchor="ml")
        self.text("Ajustes del juego", x0 + self.n(66), self.cy(y) + self.n(50), 17, DIM)
        y += self.n(80)
        secs = [t for t in self.TABS if t[0] != "compilar" or e["repo"] or (bk and bk[0] in ("win", "src")) or recipes.have_distrobox()]
        mw, gapc = self.n(290), self.n(24)
        for i_, (k_, lab_) in enumerate(secs):
            self.button("tab_" + k_, (x0, y + i_ * self.n(82), mw, self.n(72)), lab_, lambda k_=k_: self.more_tab.__setitem__(e["id"], k_),
                        "seg" if k_ == tab else "normal", 16)
        menu_bottom = y + len(secs) * self.n(82)
        x0, colw = x0 + mw + gapc, colw - mw - gapc          # el contenido ocupa la columna derecha
        inner = colw - self.n(48)
        px = x0 + self.n(24)
        if tab == "archivos":
            req = e.get("requires") or {}
            lines = roms.req_lines(req) or ["Datos: Este catálogo no trae el dato exacto. Mira el README del proyecto para saber qué archivo pide."]
            kind = self.media_kind(e)
            lk = library.link_get(e["id"])
            mr = self.match_res.get(e["id"])
            det = self.detected.get(e["id"])
            busy = bool(mr and mr.get("busy"))
            ok = bool((mr or {}).get("ok", bool(lk))) if ((mr or lk) and not busy) else False
            pad = self.n(24)
            cw = max(self.n(200), min(self.n(300), int(colw * 0.27)))
            chh = int(cw * 1.34)   # (se alarga abajo hasta la altura de la columna derecha)
            rx = x0 + pad + cw + self.n(30)
            rw = colw - (rx - x0) - pad
            kw = self.n(190)
            rows = []
            for ln in lines:
                k_, _, v_ = ln.partition(": ")
                rows.append((k_, v_, self.wrap(v_, 19, max(self.n(100), rw - kw))))
            rows_h = sum(max(1, len(r[2])) * 26 + 10 for r in rows)
            msg = self.roms_msg.get(e["id"])
            right_h = 30 + 52 + rows_h + 18 + 136 + 18 + (32 if msg else 0) + 86 + 86 + 30
            h = max(chh, right_h) + 2 * pad
            chh = h - 2 * pad
            p = pygame.Rect(x0, y, colw, h)
            self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
            # columna izquierda: carátula + insignia del tipo de medio (disco / cartucho)
            cr = pygame.Rect(x0 + pad, self.cy(y + pad), cw, chh)
            self.thumb(e, cr)
            bc = (cr.right - self.n(20), cr.bottom - self.n(20))
            pygame.draw.circle(self.screen, PANEL, bc, self.n(40))
            self.draw_media_icon(bc[0], bc[1], self.n(24), kind, ok)
            # columna derecha
            yy = y + pad
            self.text("ARCHIVO DEL JUEGO", rx, self.cy(yy), 17, DIM, True)
            yy += self.n(30)
            self.text("Lo que pide este juego", rx, self.cy(yy), 26, TXT, True, rw)
            yy += self.n(52)
            for k_, v_, wl in rows:
                self.text(k_, rx, self.cy(yy) + self.n(2), 17, DIM, True, kw - self.n(12))
                for i_, ln in enumerate(wl or [""]):
                    self.text(ln, rx + kw, self.cy(yy) + i_ * self.n(26), 19, TXT)
                yy += max(1, len(wl)) * self.n(26) + self.n(10)
            yy += self.n(18)
            # tarjeta de estado: icono grande con ✓ cuando está reconocido
            sc = pygame.Rect(rx, self.cy(yy), rw, self.n(136))
            self.rr(sc, BG, 18)
            bad = bool(mr and not busy and not ok)
            self.rr(sc, OK if ok else (WARN if (bad or busy) else LINE), 18, max(2, self.n(3 if ok else 2)))
            self.draw_media_icon(sc.x + self.n(76), sc.centery, self.n(44), kind, ok)
            tx, tw = sc.x + self.n(150), rw - self.n(170)
            if busy:
                self.text(f"Calculando hash… {self.progress.get(e['id'], 0) * 100:.0f}%", tx, sc.y + self.n(46), 22, WARN, True, tw, anchor="ml")
                self.text("Comprobando que es la edición correcta", tx, sc.y + self.n(88), 17, DIM, False, tw, anchor="ml")
            elif ok:
                nm_ = Path((mr or {}).get("path") or lk).name
                self.text("Archivo reconocido", tx, sc.y + self.n(38), 22, OK, True, tw, anchor="ml")
                self.text(nm_, tx, sc.y + self.n(76), 18, TXT, False, tw, anchor="ml")
                how = ((f"({mr['how']})" if mr and mr.get("how") else "") + (f"  ID {mr['disc']['id']}" if mr and mr.get("disc") else "")).strip()
                if how:
                    self.text(how, tx, sc.y + self.n(106), 16, DIM, False, tw, anchor="ml")
            elif bad:
                self.text("No coincide con lo que pide el juego", tx, sc.y + self.n(38), 21, WARN, True, tw, anchor="ml")
                self.text(Path(mr.get("path") or lk or "").name, tx, sc.y + self.n(76), 18, TXT, False, tw, anchor="ml")
            else:
                self.text("Falta tu archivo", tx, sc.y + self.n(38), 22, TXT, True, tw, anchor="ml")
                self.text("Elígelo o deja la vigilancia activa y lo reconozco por hash/serial.", tx, sc.y + self.n(76), 17, DIM, False, tw, anchor="ml")
            if det and not ok:
                self.text("Detectado en descargas: " + Path(det).name, tx, sc.y + self.n(112), 17, WARN, False, tw, anchor="ml")
            yy += self.n(136 + 18)
            watching = bool(self.watch and self.watch["eid"] == e["id"])
            bw = (rw - 2 * self.n(14)) // 3
            self.button("watch", (rx, yy, bw, self.n(72)), "VIGILANDO… (parar)" if watching else "VIGILAR DESCARGAS",
                        lambda: self.toggle_watch(e), "ok" if watching else "normal", 18)
            self.button("usedet", (rx + bw + self.n(14), yy, bw, self.n(72)), "USAR DETECTADO", lambda: self.check_file(e, det), size=18, enabled=bool(det))
            self.button("rrd", (rx + 2 * (bw + self.n(14)), yy, bw, self.n(72)), "LEER DATOS DEL README", lambda: self.readme_hints(e), "normal", 16, enabled=bool(e["repo"]))
            yy += self.n(86)
            half = (rw - self.n(14)) // 2
            self.button("chg_file", (rx, yy, half, self.n(72)), "CAMBIAR ARCHIVO…" if ok else "ELEGIR ARCHIVO…", lambda: self.pick_file(e), "primary" if not ok else "normal", 18)
            self.button("rdir", (rx + half + self.n(14), yy, half, self.n(72)), "CARPETA DE ROMS", self.set_rom_dirs, size=18)
            yy += self.n(86)
            self.cat_refresh_health()
            if msg:
                self.text(msg, rx, self.cy(yy - self.n(4)), 17, WARN, maxw=rw)
            y = self._discs_panel(e, x0, p.bottom + self.n(16), colw) + self.n(24)
            if inf["installed"]:
                loc = ((self.os_state(inf["launcher_id"]).get("meta") or {}).get("windows") or {})
                wop, y = self.fold_row(e, "winexe", "¿YA TIENES EL JUEGO DE WINDOWS?", x0, y, colw, default=bool(loc.get("local")))
                if wop:
                    self.text(f"Usa tu carpeta: {loc['local']}  (no se copia nada)" if loc.get("local") else "Ábrelo con Proton o Wine sin copiar nada.",
                              x0 + self.n(8), self.cy(y), 16, DIM, False, colw)
                    y += self.n(28)
                    self.button("winlocal", (x0, y, colw, self.n(72)), "CAMBIAR EL .EXE (ELEGIR OTRO)" if loc.get("local") else "ELEGIR UN .EXE DE WINDOWS QUE YA TENGO",
                                lambda: self.pick_windows_exe(e), "normal", 18)
                    y += self.n(90)
        vopen = False
        if tab == "archivos":
            vopen, y = self.fold_row(e, "ver", "VERSIONES", x0, y, colw, default=bool(not inf["installed"] or has_upd))
        if tab == "archivos" and vopen:
            # v2.71: tarjetas «instalada → disponible», builds con icono de sistema, acciones agrupadas y repositorio al final
            shown = wlist if osv == "windows" else assets
            both = bool(assets and wlist)
            picked = self.rk(e) in self.rel_sel
            alt = None
            if not shown and rel and rel.get("tag"):      # en esta release no hay builds de lo que miras: ¿otra release sí?
                key = "windows" if osv == "windows" else "linux"
                alt = next((r for r in (self.rel_sum.get(self.rk(e)) or []) if r["tag"] != rel["tag"] and r[key]), None)
            hint_rel = alt is not None
            idx = min((self.sel_win if osv == "windows" else self.sel_asset).get(e["id"], 0), max(0, len(shown) - 1))
            dls = [d for d in self.mgr.list() if d.meta.get("install") == e["id"] and d.state in ("queued", "active", "paused", "error")]
            bk = self.build_kind(e)
            kt = {"linux": "Publica build para Linux x86_64.", "generic": "Hay un build, pero el nombre no dice si es de Linux: revisa antes de instalar.",
                  "win": "Solo publica builds de Windows: elige WINDOWS · PROTON, o compílalo desde el código (pestaña COMPILAR).",
                  "src": "No publica builds: se puede compilar desde el código (pestaña COMPILAR).",
                  "norepo": "Sin repositorio: usa DEFINIR REPOSITORIO (abajo)."}.get(bk[0] if bk else "", "")
            gap = self.n(14)

            # ── panel A · instalada → disponible ──
            ha = 18 + 34 + 128 + 14 + 30 + (38 if kt else 0) + 14
            pa = pygame.Rect(x0, y, colw, self.n(ha))
            self.rr((pa.x, self.cy(pa.y), pa.w, pa.h), PANEL, 22)
            px, yy = pa.x + self.n(24), y + self.n(18)
            self.text("VERSIÓN", px, self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            cwid = (inner - gap) // 2
            ver_i = inf["version"] or "instalada"
            if not e["repo"]:
                tag, sub, tcol = "—", "Sin repositorio: no hay descargas.", DIM
            elif self.rk(e) in self.loading:
                tag, sub, tcol = "…", "Consultando GitHub…", DIM
            elif rel and rel.get("tag"):
                tag = rel["tag"]
                sub = f"{rel['published']}  ·  " + ("elegida por ti" if picked else "la última publicada") + ("  ·  sin conexión" if rel.get("stale") else "")
                tcol = TXT
            else:
                tag, sub, tcol = "—", (rel or {}).get("error") or "Sin datos todavía", WARN
            differs = bool(inf["installed"] and inf["version"] and rel and rel.get("tag") and rel["tag"] != inf["version"])
            same = bool(inf["installed"] and rel and rel.get("tag") and rel["tag"] == inf["version"])
            for i_, (lab, val, subt, border, vcol) in enumerate((("INSTALADA", ver_i if inf["installed"] else "No instalada", "en este equipo" if inf["installed"] else "pulsa INSTALAR arriba",
                                                                 OK if inf["installed"] else LINE, TXT if inf["installed"] else DIM),
                                                                ("DISPONIBLE", tag, sub, WARN if differs else (OK if same else LINE), tcol))):
                r = pygame.Rect(px + i_ * (cwid + gap), self.cy(yy), cwid, self.n(128))
                self.rr(r, BG, 18)
                self.rr(r, border, 18, max(2, self.n(2)))
                self.text(lab, r.x + self.n(20), r.y + self.n(20), 15, DIM, True)
                self.text(val, r.x + self.n(20), r.y + self.n(44), 28, vcol, True, r.w - self.n(40))
                self.text(subt, r.x + self.n(20), r.y + self.n(88), 16, DIM, False, r.w - self.n(40))
                if i_ == 0 and inf["installed"]:
                    c = (r.right - self.n(36), r.y + self.n(36))
                    pygame.draw.circle(self.screen, OK, c, self.n(18))
                    self.check(c[0], c[1], self.n(18), (255, 255, 255))
                if i_ == 1 and (differs or same):
                    lab2 = "ACTUALIZACIÓN" if differs else "AL DÍA"
                    wch = self.font(14, True).size(lab2)[0] + self.n(24)
                    cr = pygame.Rect(r.right - wch - self.n(16), r.y + self.n(18), wch, self.n(28))
                    self.rr(cr, WARN if differs else OK, 14)
                    self.text(lab2, cr.centerx, cr.centery, 14, (20, 20, 22), True, anchor="c")
            if differs:                                    # flecha entre las dos tarjetas
                self.chevron(px + cwid + gap // 2, self.cy(yy) + self.n(64), self.n(26), WARN, "right", 4)
            yy += self.n(128 + 14)
            if e["repo"]:
                t0 = self.rel_t.get(self.rk(e))
                if self.rk(e) in self.loading:
                    age = "consultando GitHub…"
                elif t0:
                    m = max(0, int((time.time() - t0) // 60))
                    age = "datos de hace " + (f"{m} min" if m < 90 else f"{m // 60} h" if m < 2880 else f"{m // 1440} días") + " (guardados; REFRESCAR los actualiza)"
                else:
                    age = "datos de esta sesión"
                self.text(age, px, self.cy(yy), 17, DIM, maxw=inner)
            yy += self.n(30)
            if kt:
                self.text(kt, px, self.cy(yy), 19, bk[2], True, inner)
            y = pa.bottom + self.n(16)

            # ── panel B · builds ──
            if e["repo"]:
                hb = 18 + 34 + (80 if both else 0) + (68 * len(shown[:5]) if shown else 44 + (40 if hint_rel else 0)) + (34 if (osv == "windows" and shown) else 0) \
                    + len(dls) * 56 + 86 + 14
                pb = pygame.Rect(x0, y, colw, self.n(hb))
                self.rr((pb.x, self.cy(pb.y), pb.w, pb.h), PANEL, 22)
                px, yy = pb.x + self.n(24), y + self.n(18)
                self.text("BUILDS DE " + ("WINDOWS" if osv == "windows" else "LINUX") + " EN ESTA RELEASE", px, self.cy(yy), 18, DIM, True)
                yy += self.n(34)
                if both:
                    sw2 = (inner - self.n(8)) // 2
                    self.button("av_linux", (px, yy, sw2, self.n(68)), f"LINUX ({len(assets)})", lambda: self.asset_os.__setitem__(e["id"], "linux"), "seg" if osv == "linux" else "normal", 18, mark=osv == "linux")
                    self.button("av_windows", (px + sw2 + self.n(8), yy, sw2, self.n(68)), f"WINDOWS · PROTON ({len(wlist)})", lambda: self.asset_os.__setitem__(e["id"], "windows"),
                                "seg" if osv == "windows" else "normal", 18, mark=osv == "windows")
                    yy += self.n(80)
                if shown:
                    sel_map = self.sel_win if osv == "windows" else self.sel_asset
                    for i, a_ in enumerate(shown[:5]):
                        r, foc = self.reg(f"{'w' if osv == 'windows' else ''}asset:{i}", (px, yy, inner, self.n(60)), lambda i=i: sel_map.__setitem__(e["id"], i))
                        self.rr(r, PANEL2 if (foc or i == idx) else BG, 14)
                        self.rr(r, TXT if foc else (ACC if i == idx else LINE), 14, 2)
                        self.draw_os_icon(r.x + self.n(38), r.centery, self.n(17), a_["class"]["os"], i == idx)
                        self.text(a_["name"], r.x + self.n(76), r.centery - self.n(13), 20, TXT, True, r.w - self.n(360))
                        tags = f"{a_['class']['os']} · {a_['class']['arch']}" + ("  ·  INSTALADOR (se abre con Proton)" if a_["class"].get("kind") == "instalador" else "") + ("  ·  recomendado" if i == 0 else "") + ("  ·  sha256" if a_.get("sha256") else "")
                        self.text(tags, r.x + self.n(76), r.centery + self.n(15), 15, DIM)
                        self.text(fmt_size(a_["size"]), r.right - self.n(56), r.centery, 20, DIM, anchor="mr")
                        if i == idx:
                            self.check(r.right - self.n(28), r.centery, self.n(18), ACC)
                        yy += self.n(68)
                else:
                    if rel and rel.get("tag"):
                        self.text("Sin build para este sistema en las releases: puedes compilarlo (pestaña COMPILAR).", px, self.cy(yy), 19, WARN, maxw=inner)
                    yy += self.n(44)
                    if hint_rel:
                        self.text(f"La release {alt['tag']} sí trae {alt['windows'] if osv == 'windows' else alt['linux']} build(s) de {'Windows' if osv == 'windows' else 'Linux'}: pulsa ELEGIR OTRA RELEASE.",
                                  px, self.cy(yy - self.n(8)), 18, ACC, True, inner)
                        yy += self.n(40)
                if osv == "windows" and shown:
                    inst_ = any(x["class"].get("kind") == "instalador" for x in shown)
                    self.text("Los .exe «Setup» se descargan y se abren con Proton; luego eliges el .exe instalado. No se usan los .msi." if inst_ else
                              "Los .exe instaladores y .msi no se usan: solo builds empaquetados (zip/7z/tar). Se abren con Proton (umu-run).", px, self.cy(yy), 16, DIM, False, inner)
                    yy += self.n(34)
                for d in dls:
                    frac = d.progress
                    self.text(("Error: " + d.error) if d.state == "error" else f"{'Pausada' if d.state == 'paused' else 'Descargando'} {frac * 100:.0f}%  ·  {fmt_size(d.speed)}/s",
                              px, self.cy(yy), 19, ERR if d.state == "error" else TXT, maxw=inner)
                    yy += self.n(26)
                    bar = pygame.Rect(px, self.cy(yy), inner, self.n(12))
                    self.rr(bar, BG, 6)
                    self.rr((bar.x, bar.y, int(bar.w * frac), bar.h), ACC, 6)
                    yy += self.n(30)
                hw = (inner - gap) // 2
                self.button("pick_rel", (px, yy, hw, self.n(72)), "ELEGIR OTRA RELEASE" + (" (elegida)" if picked else ""), lambda: self.pick_release(e), size=17)
                self.button("peek", (px + hw + gap, yy, hw, self.n(72)), "VER QUÉ TRAE EL ARCHIVO", lambda: self.peek_asset(e, shown[idx] if shown else None), size=17, enabled=bool(shown))
                y = pb.bottom + self.n(16)

            # ── panel C · acciones ──
            fz = (self.cfg.get("frozen") or {}).get(e["id"]) if inf["installed"] else None
            hc = 18 + 34 + 86 + 86 + (86 if inf["installed"] else 0) + 4
            pc = pygame.Rect(x0, y, colw, self.n(hc))
            self.rr((pc.x, self.cy(pc.y), pc.w, pc.h), PANEL, 22)
            px, yy = pc.x + self.n(24), y + self.n(18)
            self.text("ACCIONES", px, self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            bw = (inner - gap) // 2
            hw2 = (inner - self.n(14)) // 2                       # v2.98: vuelve «PÁGINA DEL PROYECTO» (estaba en v2.44 y se perdió)
            self.button("page", (px, yy, hw2, self.n(72)), "PÁGINA DEL PROYECTO", lambda: self.open_page(e), size=18)
            self.button("refresh", (px + hw2 + self.n(14), yy, hw2, self.n(72)), "REFRESCAR LAS VERSIONES", lambda: self.fetch(e, True), size=18)
            yy += self.n(86)
            self.button("quiver", (px, yy, inner, self.n(72)), "BUSCAR EN QUIVER (build de Linux con SHA-256 verificado)", lambda: self.quiver_open(e), size=18)
            if inf["installed"]:
                yy += self.n(86)
                self.button("freeze", (px, yy, inner, self.n(72)),
                            (f"ACTUALIZACIONES CONGELADAS en {fz.get('tag') or 'esta versión'} · tocar para descongelar" if fz else
                             f"CONGELAR EN {inf['version'] or 'ESTA VERSIÓN'}: sin avisos ni actualizaciones"), lambda: self.toggle_freeze(e),
                            "ok" if fz else "normal", 17, mark=bool(fz))
            y = pc.bottom + self.n(16)

            # ── panel D · repositorio y avisos ──
            hd = 18 + 34 + 40 + 86 + 76 + 14
            pd = pygame.Rect(x0, y, colw, self.n(hd))
            self.rr((pd.x, self.cy(pd.y), pd.w, pd.h), PANEL, 22)
            px, yy = pd.x + self.n(24), y + self.n(18)
            self.text("REPOSITORIO", px, self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            self.text(e["repo"] or "sin definir", px, self.cy(yy), 22, TXT if e["repo"] else WARN, True, inner)
            yy += self.n(40)
            self.button("s_gh", (px, yy, bw, self.n(72)), "BUSCAR REPO EN GITHUB", lambda: self.search_github(e), size=16)
            self.button("s_set", (px + bw + gap, yy, bw, self.n(72)), "DEFINIR REPOSITORIO",
                        lambda: self.osk(f"Repositorio de GitHub para «{self.search_name(e)}»", lambda t: self.set_repo(e, t), e["repo"], "owner/repo o URL de GitHub"), size=16)
            yy += self.n(86)
            self.button("g_fetch", (px, yy, bw, self.n(72)), "CONSULTAR GITHUB AL ABRIR: " + ("SÍ" if self.cfg.get("fetch_on_open", True) else "NO"),
                        lambda: self.toggle_cfg("fetch_on_open", True, "Consultar GitHub al abrir una ficha"), "normal", 16)
            self.button("g_lchk", (px + bw + gap, yy, bw, self.n(72)), "LAUNCHER COMPRUEBA AL JUGAR: " + ("SÍ" if self.cfg.get("launcher_checks", True) else "NO"),
                        self.toggle_launcher_checks, "normal", 16)
            y = pd.bottom + self.n(24)

        elif tab == "jugar":
            if not inf["installed"]:
                self.text("Instala el juego para elegir cómo se abre.", x0 + self.n(8), self.cy(y), 19, DIM, False, colw)
                y += self.n(40)
            else:
                y0 = y
                y = self._os_row(e, inf, rel, x0, y, colw)
                if y == y0:
                    self.rr((x0, self.cy(y), colw, self.n(120)), PANEL, 22)
                    self.text("SE ABRE ASÍ", x0 + self.n(24), self.cy(y) + self.n(22), 16, DIM, True)
                    self.text(self.play_summary(e, inf, self.os_state(inf["launcher_id"])).replace("JUGAR y Steam abren ahora: ", ""), x0 + self.n(24), self.cy(y) + self.n(52), 22, TXT, True, colw - self.n(48))
                    self.text("Este juego solo tiene una forma de abrirse. Si tienes la versión de Windows, ponla en ARCHIVO Y DISCOS.", x0 + self.n(24), self.cy(y) + self.n(88), 16, DIM, False, colw - self.n(48))
                    y += self.n(136)

        elif tab == "steam":
            sp = self._setup_of(e, inf)
            if sp:
                self.button("setup", (x0, y, colw, self.n(72)), f"CONFIGURAR EL JUEGO  ·  abre {Path(sp).name} (prepara tu disco)", lambda: self.run_setup(e), "normal", 18)
                y += self.n(88)
            y = self.draw_launcher_panel(e, inf, x0, y, colw, px, inner)

        elif tab == "compilar":
            # panel compilar localmente
            cont = self.container_name_for(e, inf["launcher_id"])       # v2.80: el contenedor de ESTE juego
            okc = self.ctr_ok(cont)
            y = self.container_card(e, inf, x0, y, colw)                # v2.87: el contenedor se gestiona SOLO aquí
            dest = config.GAMES_DIR / e.get("folder", e["id"])
            cmd = (e.get("build") or {}).get("cmd") or "(se detecta al clonar: CMake, Meson, Cargo o Makefile)"
            t1 = self.wrap(f"Clona el repositorio y lo compila en «{cont or 'sistema'}»; después queda registrado.", 19, inner)
            t2 = self.wrap("Comando: " + cmd, 18, inner, max_lines=3)
            bj = next((b for b in reversed(self.builds) if b.entry["id"] == e["id"]), None)
            h = 18 + 34 + len(t1) * 26 + 8 + len(t2) * 24 + (34 if bj else 0) + 112 + 86
            p = pygame.Rect(x0, y, colw, self.n(h))
            self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
            yy = y + self.n(18)
            self.text("COMPILAR DESDE EL CÓDIGO", px, self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            for ln in t1:
                self.text(ln, px, self.cy(yy), 19, DIM)
                yy += self.n(26)
            yy += self.n(8)
            for ln in t2:
                self.text(ln, px, self.cy(yy), 18, TXT)
                yy += self.n(24)
            if bj:
                self.text(f"Última compilación: {bj.stage}" + (f" — {bj.error}" if bj.error else ""), px, self.cy(yy + self.n(6)), 19,
                          ERR if bj.state == "error" else OK if bj.state == "done" else WARN, True, inner)
                yy += self.n(34)
            yy += self.n(10)
            bw = (inner - self.n(14)) // 2
            want = bool(bk and bk[0] in ("win", "src"))
            self.button("bplan", (px, yy, bw, self.n(72)), "VER PLAN DE COMPILAR", lambda: self.build_plan(e), "primary" if want else "normal", 19, enabled=bool(e["repo"]))
            self.button("build", (px + bw + self.n(14), yy, bw, self.n(72)), "COMPILAR", lambda: self.start_build(e), size=20, enabled=bool(e["repo"]))
            yy += self.n(86)
            self.button("bcmd", (px, yy, inner, self.n(72)), "EDITAR COMANDO", lambda: self.edit_build_cmd(e), size=20)
            y = p.bottom + self.n(24)

            # panel port a Linux (IA)
            pj = next((b for b in reversed(self.builds) if b.entry["id"] == e["id"] and getattr(b, "label", "") == "PORT A LINUX"), None)
            pt = self.wrap("Para repos que solo traen código/builds de Windows. Hub clona una copia aparte, detecta qué APIs de Windows usa y "
                           "prepara un informe (PORTING_BRIEF.md) con el distrobox «" + (cont or "sistema") + "». Pega el prompt en tu chat de Claude "
                           "(plan Pro) o deja que Claude Code lo intente solo en local. Nunca toca la carpeta del juego instalado.", 19, inner)
            h = 18 + 34 + len(pt) * 26 + (34 if pj else 0) + 108
            p = pygame.Rect(x0, y, colw, self.n(h))
            self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
            yy = y + self.n(18)
            self.text("PORTAR A LINUX CON IA", px, self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            for ln in pt:
                self.text(ln, px, self.cy(yy), 19, DIM)
                yy += self.n(26)
            if pj:
                self.text(f"Último port: {pj.stage}" + (f" — {pj.error}" if pj.error else ""), px, self.cy(yy + self.n(6)), 19,
                          ERR if pj.state == "error" else OK if pj.state == "done" else WARN, True, inner)
                yy += self.n(34)
            yy += self.n(10)
            bw = (inner - 2 * self.n(14)) // 3
            want_p = bool(bk and bk[0] in ("win", "src"))
            self.button("pbrief", (px, yy, bw, self.n(72)), "INFORME DE PORT", lambda: self.start_port(e, "brief"), "primary" if want_p else "normal", 20, enabled=bool(e["repo"]))
            self.button("pcopy", (px + bw + self.n(14), yy, bw, self.n(72)), "COPIAR PROMPT PARA CLAUDE", lambda: self.port_copy(e), size=18)
            self.button("pagent", (px + 2 * (bw + self.n(14)), yy, bw, self.n(72)), "CLAUDE CODE LOCAL", lambda: self.port_run(e), size=20, enabled=bool(e["repo"]))
            y = p.bottom + self.n(24)

        elif tab == "diagnostico":
            y = self._adv_panel(e, inf, x0, y, colw)
            dz = pygame.Rect(x0, y, colw, self.n(132))
            self.rr((dz.x, self.cy(dz.y), dz.w, dz.h), PANEL, 22)
            self.rr((dz.x, self.cy(dz.y), dz.w, dz.h), (126, 44, 48), 22, max(2, self.n(2)))
            self.text("Borrar este juego", px, self.cy(y + self.n(18)), 22, TXT, True)
            self.text("Va a la papelera de Hub y se puede restaurar desde Ajustes. Antes eliges qué se borra.", px, self.cy(y + self.n(52)), 18, DIM, maxw=inner - self.n(330))
            self.button("del", (px + inner - self.n(300), y + self.n(30), self.n(300), self.n(72)), "BORRAR…", lambda: self.open_delete(e), "danger", 20)
            y = dz.bottom
        self.cur.nh = max(self.cur.nh, y + self.n(40), menu_bottom + self.n(40))
        self.end()

    def draw_repo(self, body):
        rv = self.rview
        info, rel = rv["info"] or {}, rv["rel"] or {}
        self.begin("repo", body)
        colw = min(self.W - self.n(80), self.n(1200))
        x0 = (self.W - colw) // 2
        inner = colw - self.n(48)
        y = self.n(18)
        self.button("rback", (x0, y, self.n(170), self.n(72)), "‹ ATRÁS", lambda: setattr(self, "rview", None), size=20)
        y += self.n(90)
        self.text(rv["repo"], x0, self.cy(y), 34, TXT, True, colw)
        y += self.n(50)
        if rv["loading"]:
            self.text("Consultando GitHub…", x0, self.cy(y), 22, DIM)
            self.end()
            return
        if rv["err"]:
            self.text(rv["err"], x0, self.cy(y), 22, WARN, True, colw)
            self.end()
            return
        if info.get("description"):
            y += self.para(info["description"], x0, self.cy(y), 21, colw, DIM) - self.cy(y)
        hl = roms.req_lines(roms.merge_requires({}, rv.get("hints") or {}))
        if hl:
            self.text("Lo que pide el README (se guardará en la tarjeta):", x0, self.cy(y + self.n(6)), 18, DIM, True)
            y += self.n(34)
            for ln in hl:
                self.text(ln, x0, self.cy(y), 19, TXT, maxw=colw)
                y += self.n(26)
            y += self.n(8)
        bits = [f"★ {info['stars']}", f"{info['forks']} forks", info["license"] or "sin licencia", f"actualizado {info['updated']}", info["language"]]
        self.text("   ·   ".join(b for b in bits if b), x0, self.cy(y + self.n(4)), 19, TXT)
        y += self.n(36)
        warn = []
        if info["archived"]:
            warn.append("ARCHIVADO: ya no recibe cambios")
        if info["fork"]:
            warn.append("es un FORK de otro repositorio")
        if warn:
            self.text(" · ".join(warn), x0, self.cy(y), 19, WARN, True, colw)
            y += self.n(32)
        if info["topics"]:
            self.text("Temas: " + ", ".join(info["topics"][:10]), x0, self.cy(y), 18, DIM, maxw=colw)
            y += self.n(32)
        # build
        assets = rel.get("assets") or []
        if rel.get("tag"):
            kind = ("Publica build para Linux x86_64" if assets and assets[0]["class"]["os"] == "linux" else
                    "Hay build, pero no dice si es de Linux" if assets else
                    "Solo builds de Windows: habría que compilar" if rel.get("has_windows") else "Sin builds: habría que compilar")
            kc = OK if assets and assets[0]["class"]["os"] == "linux" else WARN
            self.text(f"Última release {rel['tag']} ({rel['published']}) — {kind}", x0, self.cy(y), 19, kc, True, colw)
        else:
            self.text("Sin releases publicadas: habría que compilar desde el código", x0, self.cy(y), 19, WARN, True, colw)
        y += self.n(44)

        # panel de decisión
        d = self.repo_dupes()
        lines = []
        if d["exact"]:
            lines.append(("Ya está en tu catálogo como: " + ", ".join(e["name"] for e in d["exact"][:3]), WARN))
        if d["launcher"]:
            lines.append((f"Ya hay un juego del launcher con este repo (id {d['launcher']})", WARN))
        if d["similar"] and not d["exact"]:
            lines.append(("Parecido a: " + ", ".join(e["name"] for e in d["similar"][:3]) + " (¿es el mismo juego?)", WARN))
        if not lines:
            lines.append(("No está en tu catálogo todavía.", OK))
        ph = 18 + 34 + 26 * len(lines) + 12 + 70 + 14 + 78
        p = pygame.Rect(x0, y, colw, self.n(ph))
        self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
        px, yy = p.x + self.n(24), y + self.n(18)
        self.text("TARJETA QUE SE CREARÁ", px, self.cy(yy), 18, DIM, True)
        yy += self.n(34)
        for t, c in lines:
            self.text(t, px, self.cy(yy), 19, c, True, inner)
            yy += self.n(26)
        yy += self.n(12)
        bw2 = (inner - self.n(14)) // 2
        self.button("rname", (px, yy, bw2, self.n(70)), "NOMBRE: " + rv["name"], lambda: self.osk("Nombre de la tarjeta", lambda t: rv.__setitem__("name", t.strip() or rv["name"]), rv["name"]),
                    size=19)
        self.button("rplat", (px + bw2 + self.n(14), yy, bw2, self.n(70)), "PLATAFORMA: " + (rv["platform"] or "(vacía)"),
                    lambda: self.osk("Plataforma", lambda t: rv.__setitem__("platform", t.strip()), rv["platform"], "ej.: PlayStation 2, Nintendo 64, PC"), size=19)
        yy += self.n(84)
        bw3 = (inner - 2 * self.n(14)) // 3
        if d["exact"]:
            self.button("ropen", (px, yy, bw3, self.n(70)), "ABRIR ESA TARJETA", lambda: (setattr(self, "rview", None), setattr(self, "tab", "games"), self.open_detail(d["exact"][0])), "primary", 20)
            self.button("rvar", (px + bw3 + self.n(14), yy, bw3, self.n(70)), "AÑADIR COMO VARIANTE", lambda: self.ask_variant(d["exact"][0]), size=19)
        else:
            self.button("rthis", (px, yy, bw3, self.n(70)), "ESTE · CREAR TARJETA" if not (d["similar"] or d["launcher"]) else "ESTE (AUNQUE SE PAREZCA)",
                        self.add_from_repo, "primary", 20)
            if d["similar"]:
                self.button("rvar", (px + bw3 + self.n(14), yy, bw3, self.n(70)), "ES VARIANTE DE «" + d["similar"][0]["name"][:18] + "»",
                            lambda: self.ask_variant(d["similar"][0]), size=17)
        self.button("rweb", (px + 2 * (bw3 + self.n(14)), yy, bw3, self.n(70)), "ABRIR EN EL NAVEGADOR",
                    lambda: self.open_url(info.get("html_url") or f"https://github.com/{rv['repo']}"), size=19)
        y = p.bottom + self.n(24)
        # README
        if rv["readme"]:
            lines = self.wrap(rv["readme"], 18, inner, max_lines=70)
            hh = 18 + 34 + 24 * len(lines) + 20
            pr = pygame.Rect(x0, y, colw, self.n(hh))
            self.rr((pr.x, self.cy(pr.y), pr.w, pr.h), PANEL, 22)
            yy = y + self.n(18)
            self.text("README (resumen)", x0 + self.n(24), self.cy(yy), 18, DIM, True)
            yy += self.n(34)
            for ln in lines:
                self.text(ln, x0 + self.n(24), self.cy(yy), 18, DIM)
                yy += self.n(24)
            y = pr.bottom
        self.cur.nh = max(self.cur.nh, y + self.n(40))
        self.end()

    def _os_row(self, e, inf, rel, x0, y, colw):
        """Árbol de decisiones: 1) ¿Linux o Windows? 2) solo las opciones de la rama elegida:
        Linux → método (release/AppImage · compilar en contenedor) → dónde se abre (sistema · contenedor);
        Windows → con qué (Proton · Wine) → .exe propio. Lo técnico va en «AVANZADO»."""
        if not inf["installed"]:
            return y
        lid = inf["launcher_id"]
        st = self.os_state(lid)
        wa = (rel or {}).get("win_assets") or []
        act = st["active"] if st["split"] else "linux"
        if st["split"] or st["windows"] or wa:
            self.text("VERSIÓN DE ESTE JUEGO", x0, self.cy(y), 18, ACC, True)
            y += self.n(30)
            self.text(self.play_summary(e, inf, st), x0, self.cy(y), 19, TXT, True, colw)
            y += self.n(40)
        if act == "windows" and st["windows"]:          # v3.02: elegir Linux/Windows está en la tarjeta VERSIONES de la ficha; aquí, solo CÓMO se abre
            y = self.windows_branch(e, inf, st, x0, y, colw)
        else:
            y = self.linux_branch(e, inf, x0, y, colw)
        return y

    def fold_row(self, e, key, label, x0, y, colw, default=False):
        """v2.89: encabezado plegable. Escribe «abierto/cerrado» (no solo color) y devuelve (abierto, y_siguiente)."""
        k = (e["id"], key)
        op = self.fold_state.get(k, default)
        self.button(f"fold:{e['id']}:{key}", (x0, y, colw, self.n(72)), f"{'▾' if op else '▸'}  {label}      {'abierto' if op else 'cerrado'}",
                    lambda: self.fold_state.__setitem__(k, not op), "seg" if op else "normal", 17)
        return op, y + self.n(86)

    TABS = (("jugar", "JUGAR"), ("archivos", "ARCHIVOS Y VERSIONES"), ("compilar", "COMPILAR Y CONTENEDOR"), ("steam", "STEAM Y ARTE"), ("diagnostico", "DIAGNÓSTICO Y BORRAR"))
    TAB_ALIAS = {"juego": "jugar", "archivo": "archivos", "versiones": "archivos", "avanzado": "diagnostico", "lanzar": "steam"}     # nombres de antes de v2.86

    def more_tab_for(self, e, step):
        """Pestaña abierta en «Más opciones»: la elegida o, si no, la que toca según el paso en que vas."""
        t = self.more_tab.get(e["id"])
        t = self.TAB_ALIAS.get(t, t)
        if t in {k for k, _ in self.TABS}:
            return t
        return {1: "archivos", 2: "archivos"}.get(step, "jugar")

    def more_tabs(self, e, x0, y, colw, tab):
        """Barra de pestañas de «Más opciones»: una sola agrupación visible a la vez."""
        n = len(self.TABS)
        gap = self.n(8)
        bw = (colw - gap * (n - 1)) // n
        for i, (k, lab) in enumerate(self.TABS):
            self.button("tab_" + k, (x0 + i * (bw + gap), y, bw, self.n(72)), lab, lambda k=k: self.more_tab.__setitem__(e["id"], k),
                        "seg" if k == tab else "normal", 15)
        return y + self.n(88)

    def _setup_of(self, e, inf):
        """Configurador del port, mirado una vez cada 5 s por juego (no en cada fotograma)."""
        if not inf["installed"]:
            return ""
        c = self.__dict__.setdefault("_setup_c", {})
        hit = c.get(e["id"])
        if hit and time.time() - hit[0] < 5.0:
            return hit[1]
        try:
            sp = install.setup_exe(osver.folders(inf["launcher_id"])["dir"])
        except (OSError, ValueError, KeyError):
            sp = ""
        c[e["id"]] = (time.time(), sp)
        return sp

    def _adv_panel(self, e, inf, x0, y, colw):
        """AVANZADO: dónde está cada cosa, registro de Proton y distrobox de este juego."""
        lid = inf["launcher_id"]
        if inf["installed"]:
            self.text("DÓNDE ESTÁ CADA COSA", x0 + self.n(8), self.cy(y), 17, DIM, True)
            y += self.n(34)
            y = self._folders_row(e, inf, x0, y, colw)
            lrep = launchlog.latest(lid)
            self.text("REGISTROS", x0 + self.n(8), self.cy(y), 17, DIM, True)
            y += self.n(34)
            if lrep:
                self.button("launchlog", (x0, y, colw, self.n(64)), f"VER EL REGISTRO DEL ÚLTIMO ARRANQUE FALLIDO  ·  {time.strftime('%d/%m %H:%M', time.localtime(lrep.stat().st_mtime))}",
                            lambda: self.show_launchlog(e), "normal", 17)
                y += self.n(76)
            else:
                self.text("Sin arranques fallidos guardados.", x0 + self.n(8), self.cy(y), 16, DIM)
                y += self.n(30)
            self.button("hist", (x0, y, colw, self.n(64)), "HISTORIAL  ·  qué configuraciones funcionaron y cuáles fallaron",
                        lambda: self.show_history(e), "normal", 17)
            y += self.n(76)
            self.button("diag", (x0, y, colw, self.n(64)), "EXPORTAR DIAGNÓSTICO  ·  todos los registros en un archivo (~/diag-….md)",
                        lambda: self.export_diag(e), "primary", 17)
            y += self.n(76)
            st = self.os_state(lid)
            if st.get("windows"):
                on = osver.proton_log(lid)
                self.button("protonlog", (x0, y, colw, self.n(64)), "REGISTRO DE PROTON: " + ("SÍ  ·  proton-logs/steam-0.log, dentro de la carpeta del juego" if on else "NO"),
                            lambda: self.toggle_proton_log(e), "seg" if on else "normal", 17, mark=on)
                y += self.n(76)
            if recipes.have_distrobox() and self.runtime_of(e):
                r = self.runtime_of(e)["runtime"]
                self.button("prep_ctr", (x0, y, colw, self.n(64)), f"PREPARAR CONTENEDOR {str(r.get('image', '')).upper()} PARA ESTE JUEGO (lo crea e instala lo que pide)",
                            lambda: self.prepare_container(e), "normal", 17)
                y += self.n(76)
        else:
            self.text("Instala el juego para ver sus rutas y opciones técnicas.", x0 + self.n(8), self.cy(y), 18, DIM)
            y += self.n(40)
        return y + self.n(14)

    def windows_branch(self, e, inf, st, x0, y, colw):
        """Rama WINDOWS: con qué se abre (Proton / Wine) y de dónde sale el .exe."""
        lid = inf["launcher_id"]
        loc = (st.get("meta") or {}).get("windows") or {}
        rn = osver.windows_runner(lid)
        self.text("WINDOWS", x0, self.cy(y), 17, DIM, True)
        y += self.n(28)
        y = self.versions_line(e, lid, x0, y, colw)
        self.text("Proton, Wine y tu Wine propio abren LA MISMA carpeta windows/ y el mismo .exe: cambiar de uno a otro no descarga nada.", x0, self.cy(y), 15, DIM, False, colw)
        y += self.n(30)
        self.text("Abrir con:", x0, self.cy(y) + self.n(36), 18, DIM, anchor="ml")
        lw = self.font(18).size("Abrir con:")[0] + self.n(16)
        oi = self.own_info(lid)
        k = 3 if (oi or rn == "own") else 2
        hw = (colw - lw - self.n(8) * (k - 1)) // k
        self.button("wr_proton", (x0 + lw, y, hw, self.n(72)), "PROTON", lambda: self.set_win_runner(e, "proton"), "seg" if rn == "proton" else "normal", 18, mark=rn == "proton")
        self.button("wr_wine", (x0 + lw + hw + self.n(8), y, hw, self.n(72)), "WINE", lambda: self.set_win_runner(e, "wine"), "seg" if rn == "wine" else "normal", 18, mark=rn == "wine")
        if k == 3:
            self.button("wr_own", (x0 + lw + 2 * (hw + self.n(8)), y, hw, self.n(72)), "WINE PROPIO", lambda: self.set_win_runner(e, "own"), "seg" if rn == "own" else "normal", 18, mark=rn == "own")
        y += self.n(84)
        self.text({"proton": "Proton (GE-Proton con umu-run): lo más compatible con juegos modernos.",
                   "wine": "Wine del sistema: más simple y ligero; algunos juegos necesitan Proton.",
                   "own": "Tu Wine compilado (con su prefijo y sus DLL de DXVK/VKD3D); Hub no lo instala ni lo actualiza."}[rn], x0, self.cy(y), 16, DIM, False, colw)
        y += self.n(28)
        if rn == "proton":
            fx = osver.windows_proton(lid)
            self.button("wr_pver", (x0, y, colw, self.n(64)), "VERSIÓN DE PROTON: " + (Path(fx).name if fx else "automático (" + Path(osver.proton_path()).name + ")") + "   ›",
                        lambda: self.pick_proton(e), "normal", 17)
            y += self.n(76)
        if osver.launcher_pair(lid)[1] or osver.windows_skip_launcher(lid):
            sk = osver.windows_skip_launcher(lid)
            self.button("wr_skiplau", (x0, y, colw, self.n(64)), "SALTAR EL LAUNCHER (abrir el juego directo): " + ("SÍ" if sk else "NO"),
                        lambda: self.toggle_skip_launcher(e), "seg" if sk else "normal", 17, mark=sk)
            y += self.n(76)
        if rn == "own" and oi and oi.get("custom"):      # v2.76: tu script de arranque editado a mano manda sobre lo que se elija aquí
            ch = self.n(150)
            cr_ = pygame.Rect(x0, self.cy(y), colw, ch)
            self.rr(cr_, PANEL, 18)
            self.rr(cr_, WARN, 18, max(2, self.n(3)))
            self.text("Este juego arranca con TU script (hub-run.sh editado a mano)", x0 + self.n(24), self.cy(y) + self.n(30), 20, WARN, True, colw - self.n(48))
            self.text("Hub no lo reescribe, así que el Wine y el prefijo de abajo no se aplican a ese script. Si prefieres que mande Hub, tu script se guarda como hub-run.sh.mio.",
                      x0 + self.n(24), self.cy(y) + self.n(62), 16, DIM, False, colw - self.n(48))
            self.button("own_hubscript", (x0 + self.n(24), y + self.n(90), self.n(420), self.n(48)), "USAR EL SCRIPT DEL HUB", lambda: self.use_hub_script(e), "normal", 16)
            y += ch + self.n(14)
        if rn == "own" and oi:
            y = self._own_panel(e, oi, x0, y, colw)
        if loc.get("local"):
            self.text(f"Usa tu carpeta: {loc['local']}  (no se copia nada)", x0, self.cy(y), 16, DIM, False, colw)
            y += self.n(28)
        self.text("Si es un instalador o lanzador, la primera vez prepara el juego (compila, extrae tu ISO) y después deja jugar.", x0, self.cy(y), 16, DIM, False, colw)
        return y + self.n(36)

    def chip(self, x, y, text, bg, fg, size=16, dot=None, left=0):
        """Pastilla redondeada con texto (y un punto de color opcional). Devuelve su borde derecho. y en pantalla."""
        f = self.font(size, True)
        tw = f.size(self.sane(text))[0]
        lead = left or (self.n(26) if dot else self.n(14))
        r = pygame.Rect(x, y, tw + lead + self.n(14), self.n(34))
        self.rr(r, bg, 17)
        if dot and not left:
            pygame.draw.circle(self.screen, dot, (r.x + self.n(16), r.centery), self.n(5))
        self.text(text, r.x + lead, r.centery, size, fg, True, anchor="ml")
        return r.right

    def draw_os_icon(self, cx, cy, s, os_name, on):
        """Icono de sistema hecho con formas: Windows (cuatro cuadros) o terminal (Linux/otros)."""
        sc = self.screen
        col = ACC if on else (150, 154, 164)
        if "win" in str(os_name).lower():
            g = max(2, s // 8)
            q = s - g // 2
            for dx in (0, 1):
                for dy in (0, 1):
                    pygame.draw.rect(sc, col, pygame.Rect(cx - s + dx * (q + g), cy - s + dy * (q + g), q, q), border_radius=2)
        else:
            r = pygame.Rect(cx - s, cy - int(s * 0.8), s * 2, int(s * 1.6))
            pygame.draw.rect(sc, col, r, border_radius=max(3, s // 4))
            k = max(2, s // 6)
            pygame.draw.lines(sc, (20, 20, 22), False, [(cx - int(s * 0.55), cy - int(s * 0.3)), (cx - int(s * 0.1), cy), (cx - int(s * 0.55), cy + int(s * 0.3))], k)
            pygame.draw.line(sc, (20, 20, 22), (cx + int(s * 0.05), cy + int(s * 0.35)), (cx + int(s * 0.55), cy + int(s * 0.35)), k)

    DISC_EXT = {"iso", "cue", "bin", "chd", "cso", "pbp", "gcm", "rvz", "wbfs", "img", "mdf", "nrg", "ciso", "gdi", "cdi"}

    def media_kind(self, e):
        """«disc» (CD/DVD/UMD…) o «cart» (cartucho) según los formatos que pide el port; sin dato, por los seriales (discos) o cartucho."""
        req = e.get("requires") or {}
        fm = {str(x).lower().lstrip(".") for x in (req.get("formats") or [])}
        if fm & self.DISC_EXT:
            return "disc"
        if fm:
            return "cart"
        return "disc" if req.get("serials") else "cart"

    def draw_media_icon(self, cx, cy, s, kind, ok):
        """Icono de disco o de cartucho, hecho con formas (sin glifos de fuente); con insignia verde ✓ si el archivo está reconocido."""
        sc = self.screen
        if kind == "disc":
            col = (222, 227, 236) if ok else (112, 114, 122)
            pygame.draw.circle(sc, col, (cx, cy), s)
            pygame.draw.circle(sc, (150, 160, 178) if ok else (84, 86, 92), (cx, cy), int(s * 0.74), max(1, int(s * 0.05)))
            pygame.draw.circle(sc, PANEL, (cx, cy), int(s * 0.30))
            pygame.draw.circle(sc, col, (cx, cy), int(s * 0.13))
            pygame.draw.arc(sc, (255, 255, 255) if ok else (140, 142, 150), pygame.Rect(cx - int(s * 0.88), cy - int(s * 0.88), int(s * 1.76), int(s * 1.76)), 0.5, 1.2, max(2, int(s * 0.08)))
        else:
            w, hh = int(s * 1.5), int(s * 1.9)
            body = pygame.Rect(cx - w // 2, cy - hh // 2, w, hh)
            pygame.draw.rect(sc, (86, 90, 102) if ok else (66, 68, 74), body, border_radius=max(3, int(s * 0.14)))
            lab = pygame.Rect(body.x + int(w * 0.14), body.y + int(hh * 0.10), int(w * 0.72), int(hh * 0.46))
            pygame.draw.rect(sc, ACC if ok else LINE, lab, border_radius=max(2, int(s * 0.08)))
            pygame.draw.rect(sc, (255, 255, 255) if ok else (120, 122, 130), pygame.Rect(lab.x + int(lab.w * 0.12), lab.y + int(lab.h * 0.18), int(lab.w * 0.5), max(2, int(lab.h * 0.12))), border_radius=2)
            pygame.draw.rect(sc, (26, 26, 28), pygame.Rect(body.x + int(w * 0.16), body.bottom - int(hh * 0.22), int(w * 0.68), int(hh * 0.18)))
            for i in range(5):
                pygame.draw.line(sc, (190, 160, 70) if ok else (90, 90, 96), (body.x + int(w * (0.22 + 0.14 * i)), body.bottom - int(hh * 0.20)), (body.x + int(w * (0.22 + 0.14 * i)), body.bottom - int(hh * 0.06)), max(1, int(s * 0.05)))
        if ok:
            bc = (cx + int(s * 0.80), cy + int(s * 0.80))
            pygame.draw.circle(sc, PANEL, bc, int(s * 0.52))
            pygame.draw.circle(sc, OK, bc, int(s * 0.42))
            self.check(bc[0], bc[1], int(s * 0.5), (255, 255, 255), 3)

    def _discs_panel(self, e, x0, y, colw):
        """v2.42: puertos que piden VARIOS discos (serials): uno por ID, con su botón. Devuelve el y de debajo del panel (o el mismo y si no aplica)."""
        sers = (e.get("requires") or {}).get("serials") or []
        if len(sers) < 2:
            return y
        dl = library.disc_links(e["id"])
        h = 20 + 34 + len(sers) * 84 + 30
        self.rr((x0, self.cy(y), colw, self.n(h)), PANEL, 22)
        px, inner, yy = x0 + self.n(24), colw - self.n(48), y + self.n(20)
        self.text(f"ESTE PORT PIDE {len(sers)} DISCOS: ENLAZA CADA UNO", px, self.cy(yy), 18, DIM, True)
        yy += self.n(34)
        hw = (inner - self.n(8)) // 2
        for s in sers:
            p = dl.get(s)
            ok = bool(p and Path(p).exists())
            self.draw_media_icon(px + self.n(40), self.cy(yy) + self.n(36), self.n(24), "disc", ok)
            self.text(ownwine.disc_label(s), px + self.n(96), self.cy(yy) + self.n(22), 18, TXT, True, anchor="ml", maxw=hw - self.n(96))
            self.text(Path(p).name[:40] if ok else "Falta este disco", px + self.n(96), self.cy(yy) + self.n(52), 16, OK if ok else WARN, False, hw - self.n(96), anchor="ml")
            self.button("disc_" + s, (px + hw + self.n(8), yy, hw, self.n(72)), "CAMBIAR EL ISO" if ok else "ELEGIR EL ISO", lambda s=s: self.pick_disc(e, s), "normal", 18)
            yy += self.n(84)
        self.text("Hub reconoce cada archivo por su ID y los deja enlazados junto al juego (Linux y Windows).", px, self.cy(yy - self.n(4)), 16, DIM, False, inner)
        return y + self.n(h)

    def own_info(self, lid):
        """Datos de «Wine propio» (God of War PSP) cacheados 3 s: la ficha se dibuja 45 veces por segundo. None si el juego no es compatible."""
        c = self.__dict__.setdefault("_own_c", {})
        hit = c.get(lid)
        if hit and time.time() - hit[0] < 3:
            return hit[1]
        info = None
        try:
            r = osver.root_of(lid)
            w = (osver.meta(r).get("windows") or {}) if r else {}
            if r and ownwine.supported(r / "windows", w):
                cf = ownwine.cfg(w, "gow" if ownwine.available(r / "windows", w) else "generic")
                info = {"cfg": cf, "win": r / "windows", "w": w, "wine_ok": ownwine.wine_ok(cf) if cf["binary"] else False, "rebuild": bool(w.get("rebuild")),
                        "custom": ownwine.is_custom(r / "windows")}
                if cf["profile"] == "gow":
                    b = ownwine.base_dir(r / "windows", w)
                    tried = self.__dict__.setdefault("_disc_tried", set())
                    if lid not in tried and not all(ownwine.disc_of(r / "windows", g) for g in ownwine.GAMES):
                        tried.add(lid)                    # v2.68: una vez por sesión, busca el disco que falte (el del launcher.json o junto al otro)
                        ownwine.note_disc(r / "windows", None)
                    info.update({"built": {g: ownwine.built(b, g) for g in ownwine.GAMES}, "disc": {g: bool(ownwine.disc_of(r / "windows", g)) for g in ownwine.GAMES},
                                 "disc_name": {g: Path(ownwine.disc_of(r / "windows", g)).name for g in ownwine.GAMES}})
        except OSError:
            info = None
        c[lid] = (time.time(), info)
        return info

    def _own_cards_main(self, e, oi, x0, y, colw):
        """God of War PSP en la ficha: modo (launcher / juego directo) y una fila por juego con estado, ISO y compilar."""
        cf = oi["cfg"]
        g, md = cf["game"], cf["mode"]
        self.text("JUEGOS", x0 + self.n(8), self.cy(y), 17, DIM, True)
        bw0 = self.n(250)
        for i_, (k_, lab_) in enumerate((("launcher", "EL LAUNCHER"), ("direct", "UN JUEGO DIRECTO"))):
            self.button("own_m_" + k_[0], (x0 + colw - (2 - i_) * (bw0 + self.n(8)) + self.n(8), y - self.n(8), bw0, self.n(52)), lab_, lambda k_=k_: self.set_own_mode(e, k_),
                        "seg" if md == k_ else "normal", 15, mark=md == k_)
        y += self.n(54)
        pad = self.n(14)
        for n_, (gg, (did, nm)) in enumerate(ownwine.GAMES.items(), 1):
            sel = md == "direct" and g == gg
            built_, disc_ = oi["built"][gg], oi["disc"][gg]
            ok_ = built_ and disc_
            ch = self.n(132)
            r = pygame.Rect(x0, self.cy(y), colw, ch)
            self.rr(r, PANEL2 if sel else PANEL, 18)
            self.rr(r, ACC if sel else (OK if ok_ else LINE), 18, max(2, self.n(3 if sel else 2)))
            cr = pygame.Rect(r.x + pad, r.y + pad, self.n(70), ch - 2 * pad)
            self.thumb(e, cr)
            self.text(str(n_), cr.x + self.n(8), cr.y + self.n(4), 22, (255, 255, 255), True)
            bc = (cr.right - self.n(4), cr.bottom - self.n(4))
            pygame.draw.circle(self.screen, PANEL2 if sel else PANEL, bc, self.n(26))
            self.draw_media_icon(bc[0], bc[1], self.n(15), "disc", disc_)
            tx = cr.right + self.n(22)
            self.text(nm, tx, r.y + self.n(32), 22, TXT, True, self.n(330), anchor="ml")
            for k_, (good, txt_) in enumerate(((built_, "Compilado" if built_ else "Sin compilar"), (disc_, "Disco listo" if disc_ else "Falta el disco"))):
                yy_ = r.y + self.n(68) + k_ * self.n(28)
                pygame.draw.circle(self.screen, OK if good else WARN, (tx + self.n(7), yy_), self.n(6))
                self.text(txt_, tx + self.n(22), yy_, 17, OK if good else WARN, False, self.n(300), anchor="ml")
            bx = tx + self.n(360)
            bws = [("own_" + gg, "SE ABRE ESTE" if sel else "ABRIR ESTE", lambda gg=gg: self.set_own_game(e, gg), "seg" if sel else "normal", True)] if md == "direct" else []
            bws += [("own_iso_" + gg, "ISO" if disc_ else "ELEGIR ISO", lambda did=did: self.pick_disc(e, did), "normal", True),
                    ("own_build_" + gg, "RECOMPILAR" if built_ else "COMPILAR", lambda gg=gg: self.own_build(e, gg), "normal", oi["wine_ok"])]
            avail = r.right - pad - bx
            bw_ = (avail - self.n(10) * (len(bws) - 1)) // len(bws)
            for j_, (key_, lab_, cb_, kd_, en_) in enumerate(bws):
                self.button(key_, (bx + j_ * (bw_ + self.n(10)), y + (ch - self.n(64)) // 2, bw_, self.n(64)), lab_, cb_, kd_, 16, enabled=en_, mark=(kd_ == "seg"))
            y += self.n(132 + 12)
        return y + self.n(6)

    def _own_panel(self, e, oi, x0, y, colw):
        cf = oi["cfg"]
        wb = ownwine.expand(cf["binary"]) if cf["binary"] else ""
        self.text(("Wine: " + wb) if wb else "Wine: sin elegir", x0, self.cy(y), 16, DIM if oi["wine_ok"] else WARN, False, colw)
        y += self.n(26)
        self.text("Prefijo: " + (ownwine.expand(cf["prefix"]) if cf["prefix"] else "el del juego (proton-prefix)") + "  ·  se cambia en windows/hub-run.sh", x0, self.cy(y), 16, DIM, False, colw)
        y += self.n(32)
        self.button("own_wine", (x0, y, colw, self.n(72)), "CAMBIAR EL WINE…" if wb else "ELEGIR EL WINE (…/bin/wine o loader/wine)", lambda: self.pick_own_wine(e), "normal", 18)
        y += self.n(84)
        if cf["profile"] != "gow":
            self.text("Se abre el .exe de este juego con ese Wine. Para añadir overrides de DLL o variables, edita windows/hub-run.sh.", x0, self.cy(y), 16, DIM, False, colw)
            return y + self.n(32)
        g, md = cf["game"], cf["mode"]
        self.text("CÓMO SE ABRE", x0, self.cy(y), 16, DIM, True)
        y += self.n(30)
        bw0 = (colw - self.n(8)) // 2
        self.button("own_m_l", (x0, y, bw0, self.n(72)), "EL LAUNCHER", lambda: self.set_own_mode(e, "launcher"), "seg" if md == "launcher" else "normal", 18, mark=md == "launcher")
        self.button("own_m_d", (x0 + bw0 + self.n(8), y, bw0, self.n(72)), "UN JUEGO DIRECTO", lambda: self.set_own_mode(e, "direct"), "seg" if md == "direct" else "normal", 18, mark=md == "direct")
        y += self.n(80)
        self.text("Abre GoWLauncher.exe con tu Wine y eliges el juego ahí." if md == "launcher" else "Salta el launcher y arranca el juego que marques con «SE ABRE ESTE» (necesita estar compilado y con su ISO).",
                  x0, self.cy(y), 16, DIM, False, colw)
        y += self.n(40)
        self.text("JUEGOS", x0, self.cy(y), 16, DIM, True)
        y += self.n(30)
        hw = (colw - self.n(40) - self.n(8)) // 2
        pad = self.n(20)
        for n_, (gg, (did, nm)) in enumerate(ownwine.GAMES.items(), 1):
            sel = md == "direct" and g == gg
            built_, disc_ = oi["built"][gg], oi["disc"][gg]
            ok_ = built_ and disc_
            ch = self.n(216)
            r = pygame.Rect(x0, self.cy(y), colw, ch)
            self.rr(r, PANEL2 if sel else BG, 18)
            self.rr(r, ACC if sel else (OK if ok_ else LINE), 18, max(2, self.n(3 if sel else 2)))
            pad = self.n(18)
            # columna izquierda: carátula del juego + insignia de disco (con ✓ cuando está compilado y con su ISO)
            cw_ = self.n(132)
            cr = pygame.Rect(x0 + pad, r.y + pad, cw_, ch - 2 * pad)
            self.thumb(e, cr)
            sh = pygame.Surface((cr.w, cr.h), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 0 if ok_ else 90), sh.get_rect(), border_radius=self.n(14))
            self.screen.blit(sh, cr)
            self.text(str(n_), cr.x + self.n(14), cr.y + self.n(8), 26, (255, 255, 255), True)
            bc = (cr.right - self.n(8), cr.bottom - self.n(8))
            pygame.draw.circle(self.screen, PANEL2 if sel else BG, bc, self.n(40))
            self.draw_media_icon(bc[0], bc[1], self.n(24), "disc", disc_)
            if ok_:
                pass          # el ✓ verde ya lo trae el icono cuando hay disco; «compilado» va en el estado
            # columna derecha
            rx = cr.right + self.n(26)
            rw = x0 + colw - pad - rx
            sw = self.n(230) if md == "direct" else 0
            self.text(nm, rx, r.y + pad + self.n(24), 24, TXT, True, rw - sw - self.n(10), anchor="ml")
            if md == "direct":
                self.button("own_" + gg, (rx + rw - sw, y + pad, sw, self.n(52)), "SE ABRE ESTE" if sel else "ABRIR ESTE", lambda gg=gg: self.set_own_game(e, gg),
                            "seg" if sel else "normal", 16, mark=sel)
            sy = r.y + pad + self.n(74)
            for k_, (good, txt_) in enumerate(((built_, "Compilado" if built_ else "Sin compilar"),
                                                (disc_, ("Disco: " + oi["disc_name"][gg]) if disc_ else "Falta el disco"))):
                px_ = rx + (0 if k_ == 0 else self.n(190))
                pygame.draw.circle(self.screen, OK if good else WARN, (px_ + self.n(7), sy), self.n(6))
                self.text(txt_, px_ + self.n(22), sy, 17, OK if good else WARN, False, (self.n(160) if k_ == 0 else rw - self.n(212)), anchor="ml")
            by = y + pad + self.n(100)
            bw_ = (rw - self.n(8)) // 2
            self.button("own_iso_" + gg, (rx, by, bw_, self.n(64)), "CAMBIAR EL ISO" if disc_ else f"ELEGIR ISO USA ({did})", lambda did=did: self.pick_disc(e, did), "normal", 16)
            self.button("own_build_" + gg, (rx + bw_ + self.n(8), by, bw_, self.n(64)), ("RECOMPILAR" if built_ else "COMPILAR") + "  ·  ~4 MIN",
                        lambda gg=gg: self.own_build(e, gg), "normal", 16, enabled=oi["wine_ok"])
            y += self.n(216 + 16)
        if oi["rebuild"]:
            self.text("El proyecto se actualizó: hay que compilar otra vez (~4 min; el toolchain ya está).", x0, self.cy(y), 16, WARN, False, colw)
            y += self.n(28)
        self.text("Una edición PSN (NPUG...) o europea no sirve: hace falta el ISO USA.", x0, self.cy(y), 16, DIM, False, colw)
        return y + self.n(32)

    def play_summary(self, e, inf, st):
        lid = inf["launcher_id"]
        act = st["active"] if st["split"] else "linux"
        if act == "windows":
            how = "WINDOWS con " + {"wine": "Wine", "own": "tu Wine propio"}.get(osver.windows_runner(lid), "Proton")
        else:
            built = osver.linux_methods(lid)["active"] == "built" if st["split"] else False
            how = "LINUX · " + ("compilado por Hub" if built else "release") + " · " + (f"dentro del contenedor «{self.container_name_for(e, lid)}»" if osver.in_container(lid) else "en el sistema")
        return "JUGAR y Steam abren ahora: " + how


    def versions_card(self, e, inf, rel, x0, y, colw):
        """v3.02: UNA tarjeta para «qué versiones hay, cuál está instalada y cuál abre JUGAR». Una fila por sistema: qué es, en qué estado está
        (escrito, no solo color) y una sola acción. Sustituye al «¿Dónde quieres jugar?» repetido y al interruptor de builds de otra pestaña."""
        lid = inf["launcher_id"]
        st = self.os_state(lid)
        assets = (rel or {}).get("assets") or []
        wa = (rel or {}).get("win_assets") or []
        lin_assets = [a for a in assets if (a.get("class") or {}).get("os") != "windows"]
        if not (wa or st["windows"]):
            return y                                   # solo hay Linux: no hay nada que elegir
        act = st["active"] if st["split"] else "linux"
        tag = (rel or {}).get("tag") or ""
        dls = [d for d in self.mgr.list() if d.state in ("queued", "active", "paused")]
        rows = []
        # ── Linux ──
        dl_l = next((d for d in dls if d.meta.get("install") == e["id"]), None)
        if st["linux"]:
            ver = inf["version"] if act == "linux" else ""
            built = st["split"] and osver.linux_methods(lid)["active"] == "built"
            lst = ("compilada aquí" if built else "instalada") + (f" · {ver}" if ver else "")
            lact = ("ACTIVA", None) if act == "linux" else ("USAR", lambda: self.choose_os(e, "linux"))
        elif dl_l:
            lst, lact = f"descargando {dl_l.progress * 100:.0f}%", ("…", None)
        else:
            lst = "sin instalar" + (f" · {tag}" if lin_assets else " · no hay build en esta release")
            lact = ("INSTALAR", (lambda: (self.asset_os.__setitem__(e["id"], "linux"), self.do_install(e)))) if lin_assets else ("—", None)
        rows.append(("os_linux", "LINUX", "nativo", lst, lact, act == "linux"))
        # ── Windows ──
        w0 = wa[min(self.sel_win.get(e["id"], 0), len(wa) - 1)] if wa else None
        is_setup = bool(w0 and (w0.get("class") or {}).get("kind") == "instalador")
        dl_w = next((d for d in dls if d.meta.get("install_win") == e["id"] or d.meta.get("install_setup") == e["id"]), None)
        if st["windows"]:
            wst, wact = "instalada", (("ACTIVA", None) if act == "windows" else ("USAR", lambda: self.choose_os(e, "windows")))
        elif self.win_installed(e, lid):
            wst, wact = "instalada · falta elegir su .exe", ("ELEGIR .EXE", lambda: self.choose_os(e, "windows"))
        elif dl_w:
            wst, wact = f"descargando {'el instalador ' if is_setup else ''}{dl_w.progress * 100:.0f}%", ("…", None)
        elif is_setup and self._setup_on_disk(e, w0):
            wst, wact = "instalador descargado · sin instalar", ("ABRIR INSTALADOR", lambda: self.install_windows_dl(e))
        elif w0:
            wst = f"sin instalar · {tag} · {'instalador' if is_setup else 'paquete'} {fmt_size(w0['size'])}"
            wact = ("INSTALAR", lambda: self.install_windows_dl(e, fresh=not inf["installed"]))
        else:
            wst, wact = "sin build de Windows en esta release", ("—", None)
        rows.append(("os_windows", "WINDOWS", "con Proton" if osver.windows_runner(lid) != "wine" else "con Wine", wst, wact, act == "windows"))

        rh, gap = self.n(84), self.n(10)
        h = self.n(64) + len(rows) * (rh + gap)
        p = pygame.Rect(x0, y, colw, h)
        self.rr((p.x, self.cy(p.y), p.w, p.h), PANEL, 22)
        px, inner = x0 + self.n(24), colw - self.n(48)
        self.text("VERSIONES DE ESTE JUEGO", px, self.cy(y) + self.n(30), 17, DIM, True, anchor="ml")
        self.text("JUGAR abre: " + ("Windows" if act == "windows" else "Linux"), x0 + colw - self.n(24), self.cy(y) + self.n(30), 18, TXT, True, anchor="mr")
        yy = y + self.n(56)
        bw = self.n(250)
        for key, name, how, state, (alab, acb), on in rows:
            r = pygame.Rect(px, self.cy(yy), inner, rh)
            self.rr(r, BG, 16)
            self.rr(r, ACC if on else LINE, 16, max(2, self.n(3 if on else 1)))
            self.text(name, r.x + self.n(20), r.y + self.n(28), 21, TXT, True, anchor="ml")
            self.text(how, r.x + self.n(20), r.y + self.n(60), 15, DIM, anchor="ml")
            self.text(state, r.x + self.n(240), r.centery, 18, OK if on else TXT, on, inner - bw - self.n(260), anchor="ml")
            self.button(key, (r.right - bw - self.n(10), yy + self.n(8), bw, rh - self.n(16)), alab, acb or (lambda: None),
                        "seg" if on else ("primary" if alab in ("INSTALAR", "ABRIR INSTALADOR", "ELEGIR .EXE") else "normal"), 18, enabled=acb is not None)
            yy += rh + gap
        return p.bottom + self.n(16)

    def _os_row_main(self, e, inf, rel, x0, y, colw):
        """Nivel 1 del árbol: ¿Linux o Windows?"""
        st = self.os_state(inf["launcher_id"])
        wa = (rel or {}).get("win_assets") or []
        if not (wa or st["windows"]):
            return y
        act = st["active"] if st["split"] else "linux"
        self.text("¿Dónde quieres jugar?", x0, self.cy(y) + self.n(36), 18, DIM, anchor="ml")
        lw = self.font(18).size("¿Dónde quieres jugar?")[0] + self.n(16)
        bw = (colw - lw - self.n(8)) // 2
        built = osver.linux_methods(inf["launcher_id"])["active"] == "built" if st["split"] else False
        ll = "LINUX · " + ("compilado aquí" if built and st["linux"] else "listo" if st["linux"] else "sin instalar")
        self.button("os_linux", (x0 + lw, y, bw, self.n(72)), ll, lambda: self.choose_os(e, "linux"), "seg" if act == "linux" else "normal", 18,
                    enabled=st["linux"], mark=act == "linux")
        wl = "WINDOWS · " + ("listo" if st["windows"] else "elegir .exe" if self.win_installed(e, inf["launcher_id"]) else "descargar")
        self.button("os_windows", (x0 + lw + bw + self.n(8), y, bw, self.n(72)), wl, lambda: self.choose_os(e, "windows"),
                    "seg" if act == "windows" else "normal", 18, mark=act == "windows")
        y += self.n(84)
        return y

    def _folders_row(self, e, inf, x0, y, colw, draw=True):
        """Dónde está cada cosa: carpeta del juego (la versión elegida), carpeta de trabajo y tu archivo."""
        if not inf["installed"]:
            return y
        st = self.os_state(inf["launcher_id"])
        if not st.get("dir"):
            return y
        lk = library.link_get(e["id"])
        if lk:
            self.auto_place(e, inf)
        if not draw:
            return y
        rows = [("Juego", st["dir"]), ("Carpeta de trabajo", st["cwd"] + ("" if st["cwd"] == st["dir"] else "   (distinta de la del juego)"))]
        if lk:
            rows.append(("Tu archivo", str(lk)))
        req = e.get("requires") or {}
        if req.get("place"):
            rows.append(("Lo enlaza en", f"{st['dir']}/{req['place']}" + ("   (según su README)" if req.get("place_from") == "readme" else "")))
        elif req.get("rom_dest") or library.rom_dest_for(e):
            rows.append(("Lo enlaza en", str(library.rom_dest_for(e)) + "   (carpeta fija que pide el port)"))
        for k, v in rows:
            self.text(k + ":", x0, self.cy(y), 16, DIM, True)
            self.text(v, x0 + self.n(200), self.cy(y), 16, WARN if "distinta" in v else DIM, False, colw - self.n(200))
            y += self.n(28)
        return y + self.n(8)
