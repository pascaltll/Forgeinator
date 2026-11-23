"""Ventanas modales: confirmar, elegir, teclado, archivos, registros. Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class ModalMixin:
    def draw_modal(self):
        m = self.modal
        if m["kind"] == "confirm":
            pw, lines = min(self.W - self.n(80), self.n(900)), None
            lines = self.wrap(m["msg"], 21, pw - self.n(60))
            ph = self.n(150 + 30 * len(lines) + 90)
            p = pygame.Rect(0, 0, pw, ph)
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text(m["title"], p.x + self.n(30), p.y + self.n(24), 26, TXT, True, pw - self.n(60))
            yy = p.y + self.n(80)
            for ln in lines:
                self.text(ln, p.x + self.n(30), yy, 21, DIM)
                yy += self.n(30)
            bw = (pw - self.n(90)) // 2
            self.button("m:no", (p.x + self.n(30), p.bottom - self.n(98), bw, self.n(74)), "CANCELAR", self.close_modal, size=22)
            self.button("m:yes", (p.x + self.n(60) + bw, p.bottom - self.n(98), bw, self.n(74)), "ACEPTAR",
                        lambda: (self.close_modal(), m["cb"]()), "primary", 22)
        elif m["kind"] == "osk" and m.get("steam"):
            pw = min(self.W - self.n(40), self.n(1280))
            p = pygame.Rect(0, 0, pw, self.n(282))
            p.midtop = (self.W // 2, self.n(24))   # arriba: el teclado de Steam ocupa la parte baja
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text(m["title"], p.x + self.n(30), p.y + self.n(20), 24, TXT, True, pw - self.n(60))
            box = pygame.Rect(p.x + self.n(30), p.y + self.n(66), pw - self.n(60), self.n(64))
            self.rr(box, BG, 12)
            self.rr(box, ACC, 12, 2)
            s = m["text"]
            while s and self.font(24).size(s)[0] > box.w - self.n(40):
                s = s[1:]
            self.text(s if m["text"] else m.get("hint", ""), box.x + self.n(18), box.centery, 24, TXT if m["text"] else DIM, anchor="ml")
            if m["text"] and int(self.t * 2) % 2 == 0:
                cx = box.x + self.n(18) + self.font(24).size(s)[0] + 3
                pygame.draw.rect(self.screen, ACC, (cx, box.y + self.n(14), self.n(3), box.h - self.n(28)))
            self.text("Escribe con el teclado de Steam (si no aparece, pulsa TECLADO DE STEAM). Intro = aceptar.", p.x + self.n(30), box.bottom + self.n(14), 17, DIM, maxw=pw - self.n(60))
            yy = box.bottom + self.n(52)
            specials = [("TECLADO DE STEAM", 3, self.steam_kb_open, "primary"),
                        ("PEGAR", 2, lambda: self._osk_paste(m), "normal"),
                        ("TECLADO DE HUB", 3, lambda: m.__setitem__("steam", False), "normal"),
                        ("CANCELAR", 2, self.close_modal, "normal"),
                        ("ACEPTAR", 2, lambda: self._osk_ok(m), "ok")]
            unit = (pw - self.n(60) - self.n(8) * (len(specials) - 1)) / sum(x[1] for x in specials)
            xx = p.x + self.n(30)
            for i, (lab, wd, cb, kind) in enumerate(specials):
                w = int(unit * wd)
                self.button(f"ks:{i}", (xx, yy, w, self.n(76)), lab, cb, kind, 18)
                xx += w + self.n(8)
        elif m["kind"] == "osk":
            pw = min(self.W - self.n(40), self.n(1280))
            p = pygame.Rect(0, 0, pw, min(self.H - self.n(20), self.n(740)))
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text(m["title"], p.x + self.n(30), p.y + self.n(20), 24, TXT, True, pw - self.n(60))
            box = pygame.Rect(p.x + self.n(30), p.y + self.n(66), pw - self.n(60), self.n(64))
            self.rr(box, BG, 12)
            self.rr(box, ACC, 12, 2)
            shown = m["text"] if m["text"] else m.get("hint", "")
            tw = self.font(24).size(m["text"])[0]
            s = m["text"]
            while s and self.font(24).size(s)[0] > box.w - self.n(40):
                s = s[1:]
            self.text(s if m["text"] else shown, box.x + self.n(18), box.centery, 24, TXT if m["text"] else DIM, anchor="ml")
            if m["text"] and int(self.t * 2) % 2 == 0:
                cx = box.x + self.n(18) + self.font(24).size(s)[0] + 3
                pygame.draw.rect(self.screen, ACC, (cx, box.y + self.n(14), self.n(3), box.h - self.n(28)))
            del tw
            rows = ["1234567890", "qwertyuiop", "asdfghjkl/", "zxcvbnm.-_", ":?=&%+#~@!"]
            kw = (pw - self.n(60) - 9 * self.n(8)) // 10
            yy = box.bottom + self.n(18)
            for ri, row in enumerate(rows):
                off = 0
                for ci, ch in enumerate(row):
                    c = ch.upper() if m["shift"] and ch.isalpha() else ch
                    self.button(f"k:{ri}:{ci}", (p.x + self.n(30) + off + ci * (kw + self.n(8)), yy, kw, self.n(76)), c,
                                lambda c=c: m.__setitem__("text", m["text"] + c), size=24)
                yy += self.n(84)
            specials = [("MAYÚS", 2, lambda: m.__setitem__("shift", not m["shift"]), "primary" if m["shift"] else "normal"),
                        ("ESPACIO", 3, lambda: m.__setitem__("text", m["text"] + " "), "normal"),
                        ("PEGAR", 2, lambda: self._osk_paste(m), "normal"),
                        ("BORRAR", 2, lambda: m.__setitem__("text", m["text"][:-1]), "normal"),
                        ("CANCELAR", 2, self.close_modal, "normal"),
                        ("ACEPTAR", 2, lambda: self._osk_ok(m), "primary")]
            unit = (pw - self.n(60) - self.n(8) * (len(specials) - 1)) / sum(s[1] for s in specials)
            xx = p.x + self.n(30)
            for i, (lab, wd, cb, kind) in enumerate(specials):
                w = int(unit * wd)
                self.button(f"ks:{i}", (xx, yy, w, self.n(76)), lab, cb, kind, 19)
                xx += w + self.n(8)
        elif m["kind"] == "device" and self.device:
            pw = min(self.W - self.n(80), self.n(900))
            p = pygame.Rect(0, 0, pw, self.n(460))
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text("Iniciar sesión en GitHub", p.x + self.n(30), p.y + self.n(24), 26, TXT, True, pw - self.n(60))
            self.text("1. En tu móvil u ordenador abre:", p.x + self.n(30), p.y + self.n(84), 20, DIM)
            self.text(self.device["url"], p.x + self.n(30), p.y + self.n(114), 26, ACC, True, pw - self.n(60))
            self.text("2. Escribe este código:", p.x + self.n(30), p.y + self.n(170), 20, DIM)
            self.text(self.device["code"], p.centerx, p.y + self.n(205), 64, TXT, True, anchor="mid")
            self.text("Esperando a que lo autorices…", p.x + self.n(30), p.y + self.n(300), 20, WARN)
            bw = (pw - self.n(90)) // 2
            self.button("dv:open", (p.x + self.n(30), p.bottom - self.n(98), bw, self.n(74)), "ABRIR EN EL NAVEGADOR", lambda: self.open_url(self.device["url"]), size=19)
            self.button("dv:x", (p.x + self.n(60) + bw, p.bottom - self.n(98), bw, self.n(74)), "CANCELAR",
                        lambda: (self.device.__setitem__("cancel", True) if self.device else None, self.close_modal()), size=20)
        elif m["kind"] == "choice":
            compact = bool(m.get("compact"))      # v2.85: menú pequeño junto al dedo (mantener pulsado un juego)
            pw = min(self.W - self.n(80), self.n(470 if compact else 1000))
            lines = []
            for part in m["msg"].split("\n"):
                lines += self.wrap(part, 20, pw - self.n(60)) or [""]
            if len(lines) > 16:
                lines = lines[:15] + ["… (hay más; el plan completo se guarda al compilar)"]
            allopts = m["options"]
            head = self.n(66 + 28 * len(lines) + 4) if compact else self.n(78 + 28 * len(lines) + 16)
            row = self.n(78) if compact else self.n(84)
            ph = min(head + row * len(allopts) + self.n(24 + (20 if compact else 0)), self.H - self.n(40))
            p = pygame.Rect(0, 0, pw, ph)
            p.center = (self.W // 2, self.H // 2)
            if compact and m.get("at"):
                p.center = m["at"]
                p.clamp_ip(pygame.Rect(0, 0, self.W, self.H).inflate(-self.n(32), -self.n(32)))
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            scrolls = head + row * len(allopts) + self.n(24) > ph
            self.text(m["title"] + (f"  ({len(allopts)} opciones)" if scrolls else ""), p.x + self.n(30), p.y + self.n(24), 26, TXT, True, pw - self.n(60))
            yy = p.y + self.n(78)
            for ln in lines:
                self.text(ln, p.x + self.n(30), yy, 20, DIM, maxw=pw - self.n(60))
                yy += self.n(28)
            lv = pygame.Rect(p.x + self.n(10), p.y + head, pw - self.n(20), ph - head - self.n(12))
            v = self.begin("choice", lv)
            if not m.get("_v"):
                m["_v"], v.off, v.vel = True, 0, 0
            for i, (lab, cb) in enumerate(allopts):
                self.button(f"ch:{i}", (p.x + self.n(30), i * row + self.n(6), pw - self.n(76), self.n(72)), lab, lambda cb=cb: (self.close_modal(), cb()), "primary" if i == 0 else "normal", 21)
            self.end(PANEL, arrows=True)
        elif m["kind"] == "delete":
            now = time.time()
            pw = min(self.W - self.n(80), self.n(1000))
            lines = []
            for part in m["msg"].split("\n"):
                lines += self.wrap(part, 20, pw - self.n(60)) or [""]
            notes = [ln for t in m["notes"] for ln in self.wrap(t, 18, pw - self.n(60))]
            rows = m["items"]
            ph = self.n(110 + 28 * len(lines) + 96 * len(rows) + 24 * len(notes) + 30 + 66 + 36)
            p = pygame.Rect(0, 0, pw, ph)
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.rr(p, (150, 52, 56), 20, max(2, self.n(2)))
            self.text(m["title"], p.x + self.n(30), p.y + self.n(24), 26, TXT, True, pw - self.n(60))
            bw = (pw - self.n(90)) // 2
            by = p.bottom - self.n(30) - self.n(66)
            self.button("del:no", (p.x + self.n(30), by, bw, self.n(72)), "CANCELAR", self.close_modal, "primary", 22)   # primero: es el foco inicial
            anyc = any(it["checked"] for it in rows)
            armed = bool(m["armed"]) and now - m["armed"] <= 5.0
            if m["armed"] and not armed:
                m["armed"] = 0.0
            if not anyc:
                lab, en, kind, cb = "NADA SELECCIONADO", False, "normal", None
            elif now - m["opened"] < 1.0:
                lab, en, kind, cb = "ESPERA…", False, "normal", None
            elif not armed:
                lab, en, kind = "BORRAR", True, "normal"
                cb = lambda: m.__setitem__("armed", time.time())  # noqa: E731
            else:
                lab, en, kind = f"PULSA OTRA VEZ PARA CONFIRMAR ({int(5 - (now - m['armed'])) + 1})", True, "danger"
                cb = lambda: m["go"](m) if time.time() - m["armed"] >= 0.8 else None  # noqa: E731  (el doble toque rápido no cuenta)
            self.button("del:go", (p.x + self.n(60) + bw, by, bw, self.n(72)), lab, cb or (lambda: None), kind, 19 if armed else 22, enabled=en)
            yy = p.y + self.n(78)
            for ln in lines:
                self.text(ln, p.x + self.n(30), yy, 20, DIM, maxw=pw - self.n(60))
                yy += self.n(28)
            yy += self.n(12)
            for i, it in enumerate(rows):
                rc = pygame.Rect(p.x + self.n(30), yy, pw - self.n(60), self.n(84))
                self.button(f"del:{i}", rc, "", lambda it=it: it.__setitem__("checked", not it["checked"]), "normal", 20)
                box = pygame.Rect(0, 0, self.n(36), self.n(36))
                box.center = (rc.x + self.n(36), rc.centery)
                self.rr(box, ACC if it["checked"] else BG, 9)
                self.rr(box, TXT if it["checked"] else DIM, 9, max(2, self.n(2)))
                if it["checked"]:
                    self.check(box.centerx, box.centery, self.n(20), TXT, 4)
                self.text(it["label"], rc.x + self.n(76), rc.y + self.n(14), 22, TXT, True, rc.w - self.n(260))
                ps = it["paths"]
                self.text((str(ps[0][0]) + (f"  (+{len(ps) - 1})" if len(ps) > 1 else "")) if ps else "Solo quita la tarjeta; no toca archivos", rc.x + self.n(76), rc.y + self.n(50), 16, DIM, maxw=rc.w - self.n(260))
                sz = it.get("size")
                self.text("calculando…" if sz is None else (fmt_size(sz[0]) + ("+" if not sz[1] else "") if ps else ""), rc.right - self.n(24), rc.centery, 20, DIM, anchor="mr")
                yy += self.n(96)
            for ln in notes:
                self.text(ln, p.x + self.n(30), yy, 18, WARN, maxw=pw - self.n(60))
                yy += self.n(24)
        elif m["kind"] == "info":
            e = self.entry(m["eid"])
            pw, ph = min(self.W - self.n(60), self.n(1300)), self.H - self.n(60)
            p = pygame.Rect(0, 0, pw, ph)
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text("FICHA: qué juego/archivo necesita", p.x + self.n(30), p.y + self.n(18), 24, TXT, True, pw - self.n(260))
            self.text(e["name"] if e else "", p.x + self.n(30), p.y + self.n(54), 18, DIM, maxw=pw - self.n(260))
            self.button("in:x", (p.right - self.n(30) - self.n(170), p.y + self.n(18), self.n(170), self.n(50)), "CERRAR", self.close_modal, size=18)
            bh, g = self.n(58), self.n(12)
            bw = (pw - self.n(60) - 3 * g) // 4
            by = p.bottom - self.n(30) - 2 * bh - g
            eid = m["eid"]
            acts = [("PEGAR TEXTO COPIADO", lambda: self.info_paste(eid)), ("EDITAR REGIÓN", lambda: self.info_edit(eid, "region", "Región requerida", "ej.: NTSC-U (USA)")),
                    ("EDITAR VERSIÓN / DISCO", lambda: self.info_edit(eid, "version", "Versión o disco requerido", "ej.: Disc 1, Rev 1, Greatest Hits")),
                    ("EDITAR FORMATOS", lambda: self.info_edit(eid, "formats", "Formatos (separados por espacio)", "ej.: .iso .bin .chd")),
                    ("EDITAR NOTA", lambda: self.info_edit(eid, "note", "Nota sobre el archivo requerido", "")),
                    ("ABRIR PROYECTO", lambda: self.open_page(e) if e else None),
                    ("BORRAR FICHA", lambda: self.confirm("¿Borrar los datos de la ficha?", "Se borran región, versión, formatos, serial, hashes y frases de esta tarjeta (no toca tus archivos).",
                                                          lambda: (self.info_clear(eid), self.open_info(eid))))]
            for i, (lab, cb) in enumerate(acts):
                self.button(f"in:{i}", (p.x + self.n(30) + (i % 4) * (bw + g), by + (i // 4) * (bh + g), bw, bh), lab, cb, size=15)
            lv = pygame.Rect(p.x + self.n(20), p.y + self.n(90), pw - self.n(40), by - p.y - self.n(100))
            self.begin("info", lv)
            yy = self.n(4)
            req = (e or {}).get("requires") or {}
            lines = roms.req_lines(req)
            if not lines:
                self.text("Todavía no hay datos. Pulsa PEGAR TEXTO COPIADO tras copiar el texto de la página del proyecto, o edita los campos.", lv.x + self.n(10), self.cy(yy), 20, WARN, maxw=lv.w - self.n(30))
                yy += self.n(40)
            for ln in lines:
                for part in self.wrap(ln, 22, lv.w - self.n(40)):
                    self.text(part, lv.x + self.n(10), self.cy(yy), 22, TXT, True)
                    yy += self.n(30)
                yy += self.n(6)
            if req.get("snippets"):
                yy += self.n(10)
                self.text("Frases del README / de lo que copiaste:", lv.x + self.n(10), self.cy(yy), 19, ACC, True)
                yy += self.n(32)
                for sn in req["snippets"]:
                    for part in self.wrap("• " + sn, 18, lv.w - self.n(40)):
                        self.text(part, lv.x + self.n(10), self.cy(yy), 18, DIM)
                        yy += self.n(25)
                    yy += self.n(6)
            self.cur.nh = max(self.cur.nh, yy + self.n(20))
            self.end()
        elif m["kind"] == "log":
            b = m["job"]
            pw, ph = min(self.W - self.n(60), self.n(1300)), self.H - self.n(80)
            p = pygame.Rect(0, 0, pw, ph)
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text(f"{b.title} — {getattr(b, 'stage', '')}" if getattr(b, "stage", "") else b.title, p.x + self.n(30), p.y + self.n(18), 24, TXT, True, pw - self.n(260))
            self.text(str(getattr(b, "logfile", "") or "hub.log (líneas [trabajo])"), p.x + self.n(30), p.y + self.n(54), 15, DIM, maxw=pw - self.n(260))
            self.button("lg:x", (p.right - self.n(30) - self.n(170), p.y + self.n(14), self.n(170), self.n(66)), "CERRAR", self.close_modal, size=18)
            quiet, follow = m.get("quiet", True), m.get("follow", True)
            src = list(b.log)
            shown = logview.lines(src, quiet, 1500)
            ocultas = len(src) - len(logview.lines(src, True)) if quiet else 0
            tb = getattr(b, "actions", None) or [("lg:copy", "COPIAR", self.log_copy), ("lg:save", "GUARDAR", self.log_save),
                  ("lg:noise", "RUIDO: OCULTO" if quiet else "RUIDO: VISIBLE", self.log_noise),
                  ("lg:top", "AL PRINCIPIO", lambda: self.log_jump(False)), ("lg:end", "AL FINAL", lambda: self.log_jump(True))]
            gap = self.n(10)
            bw = (pw - self.n(60) - gap * (len(tb) - 1)) // len(tb)
            for i, (k, lab, cb) in enumerate(tb):
                self.button(k, (p.x + self.n(30) + i * (bw + gap), p.y + self.n(98), bw, self.n(66)), lab, cb, "normal", 16)
            self.text(f"{len(shown)} líneas" + ((" · 1 línea de ruido oculta" if ocultas == 1 else f" · {ocultas} líneas de ruido ocultas") if ocultas else ""), p.x + self.n(30), p.y + self.n(75), 14, DIM)
            lv = pygame.Rect(p.x + self.n(20), p.y + self.n(182), pw - self.n(40), ph - self.n(202))
            v = self.begin("log", lv)
            yy = 0
            for ln in shown:
                for part in self.wrap(ln.replace("\t", "    ") or " ", 16, lv.w - self.n(40)):
                    self.text(part, lv.x + self.n(10), self.cy(yy), 16, ERR if ln.startswith("ERROR") else TXT)
                    yy += self.n(21)
            v.nh = yy + self.n(10)
            if b.state == "running" and follow and not (self.touch and self.touch["drag"]):
                v.off = 1e9
            self.end()
        elif m["kind"] == "picker":
            pw, ph = min(self.W - self.n(60), self.n(1300)), self.H - self.n(80)
            p = pygame.Rect(0, 0, pw, ph)
            p.center = (self.W // 2, self.H // 2)
            self.rr(p, PANEL, 20)
            self.rr(p, LINE, 20, 1)
            self.text(m["title"], p.x + self.n(30), p.y + self.n(18), 24, TXT, True, pw - self.n(60))
            self.text(str(m["dir"]), p.x + self.n(30), p.y + self.n(54), 18, DIM, maxw=pw - self.n(60))
            qx = p.x + self.n(30)
            ex = lambda d: Path(os.path.expandvars(str(d))).expanduser()  # noqa: E731
            quick = []
            rd = self.rom_dir_for(m.get("plat"))
            if rd:
                quick.append(("ROMS " + rd.name.upper(), rd))
            try:
                dd = ex(self.cfg.get("downloads_dir") or config.path("downloads_dir"))
                if dd.is_dir():
                    quick.append(("DESCARGAS", dd))
            except Exception:  # noqa: BLE001
                pass
            quick.append(("INICIO", Path.home()))
            quick += [(ex(d).name.upper() or "?", ex(d)) for d in self.cfg["watch_dirs"] if ex(d).is_dir()]
            seen_q, qq = set(), []
            for lab, d in quick:
                if d not in seen_q:
                    seen_q.add(d)
                    qq.append((lab, d))
            right = p.right - self.n(30)
            bw = self.n(150)
            for k, (key, lab, fn) in enumerate((("q:up", "‹ SUBIR", lambda: (m.__setitem__("dir", m["dir"].parent), self._list_dir())),
                                                ("q:srt", "A–Z" if m.get("sort", "az") == "az" else "RECIENTES",
                                                 lambda: (m.__setitem__("sort", "recent" if m.get("sort", "az") == "az" else "az"), self._list_dir())),
                                                ("q:flt", "FILTRAR" if not m.get("filt") else "QUITAR FILTRO", lambda: self._picker_filter(m)),
                                                ("q:x", "CERRAR", self.close_modal))):
                w = bw + (self.n(60) if key == "q:flt" and m.get("filt") else 0)
                right -= w
                self.button(key, (right, p.y + self.n(76), w, self.n(72)), lab, fn, size=17)
                right -= self.n(10)
            for i, (lab, d) in enumerate(qq[:4]):
                w = self.font(17, True).size(lab)[0] + self.n(40)
                if qx + w > right - self.n(10):
                    break
                self.button(f"q:{i}", (qx, p.y + self.n(76), w, self.n(72)), lab, lambda d=d: (m.__setitem__("dir", d), self._list_dir()), size=17)
                qx += w + self.n(10)
            lv = pygame.Rect(p.x + self.n(20), p.y + self.n(160), pw - self.n(40), ph - self.n(180) - self.n(84))
            self.begin("picker", lv)
            yy = 0
            if not m["items"]:
                self.text("(carpeta vacía)", lv.centerx, self.cy(self.n(40)), 21, DIM, anchor="mid")
            for kind, _, path, size in m["items"]:
                def go(path=path, kind=kind):
                    if kind == 0:
                        m["dir"] = path
                        self._list_dir()
                    else:
                        self.close_modal()
                        m["cb"](path)
                r, foc = self.reg(f"f:{path.name}", (lv.x, yy, lv.w - self.n(70), self.n(72)), go)
                self.rr(r, PANEL2 if foc else BG, 10)
                if foc:
                    self.rr(r, ACC, 10, 2)
                self.text(("[carpeta] " if kind == 0 else "") + path.name, r.x + self.n(18), r.centery, 21, ACC if kind == 0 else TXT, kind == 0,
                          r.w - self.n(190), "ml")
                if kind:
                    self.text(fmt_size(size), r.right - self.n(18), r.centery, 19, DIM, anchor="mr")
                yy += self.n(80)
            self.cur.nh = max(self.cur.nh, yy)
            self.end(PANEL, arrows=True)
            pv, page = self.views["picker"], max(self.n(80), lv.h - self.n(80))
            lt = m.get("letters") or []
            if lt:                                   # v2.76: índice A–Z al borde derecho (solo las letras que existen); L1/R1 saltan de letra con el mando
                sx, sw_ = lv.right - self.n(52), self.n(52)
                cell = max(self.n(30), min(self.n(46), lv.h // len(lt)))
                top = int(pv.off // max(1, self.n(80)))
                cur = max([L for L, i in lt if i <= top] or [lt[0][0]], key=lambda L: dict(lt)[L])
                for k_, (L, i_) in enumerate(lt):
                    if k_ * cell + cell > lv.h:
                        break
                    self.button(f"az:{L}", (sx, lv.y + k_ * cell, sw_, cell), L, lambda i_=i_: self.picker_jump(i_), "chipsel" if L == cur else "ghost", 17, focus=False)
            by = lv.bottom + self.n(8)
            bw2 = (lv.w - self.n(20)) // 3
            self.button("pg:up", (lv.x, by, bw2, self.n(72)), "PÁG. ANTERIOR", lambda: setattr(pv, "off", max(0, pv.off - page)), size=18)
            self.text(f"{len(m['items'])} elementos" + (f" · filtro «{m['filt']}»" if m.get("filt") else ""), lv.centerx, by + self.n(36), 18, DIM, anchor="mid")
            self.button("pg:dn", (lv.right - bw2, by, bw2, self.n(72)), "PÁG. SIGUIENTE", lambda: setattr(pv, "off", min(max(0, pv.h - lv.h), pv.off + page)), size=18)
