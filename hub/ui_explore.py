"""Explorar: consolas, lista de juegos y búsqueda. Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class ExploreMixin:
    def draw_explore(self, body):
        self.begin("explore", body)
        pad, gap = self.n(48), self.n(24)
        y = self.n(30)
        self.text("Explorar", pad, self.cy(y), 40, TXT, True)

        def go_q(t):
            self.filter, self.query, self.explore, self.focus, self.reveal = "Todos", t.strip(), "list", None, True
        sw = min(self.n(520), self.W - 2 * pad - self.n(300))
        self.button("search_all", (self.W - pad - sw, y - self.n(10), sw, self.n(72)), "Buscar juego o proyecto…",
                    lambda: self.osk("Buscar juego o proyecto (nombre, alias o repo)", go_q, ""), "normal", 20, pill=True)
        y += self.n(86)
        cnt, ins, n_solo = {}, {}, 0
        for e in self.entries:
            if "solo-codigo" in (e.get("tags") or []):
                n_solo += 1
                continue
            if e["platform"]:
                cnt[e["platform"]] = cnt.get(e["platform"], 0) + 1
                ins[e["platform"]] = ins.get(e["platform"], 0) + (1 if self.inst(e)["installed"] else 0)
        plats = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
        cols = 3 if self.W < self.n(2000) else 4
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ch = self.n(150)

        def go(f):
            self.filter, self.query, self.explore, self.focus, self.reveal = f, "", "list", None, True
        n_ins = sum(ins.values())
        n_upd = sum(1 for e in self.entries if "solo-codigo" not in (e.get("tags") or []) and self.inst(e)["installed"] and self.inst(e)["version"]
                    and (self.rel.get(self.rk(e)) or {}).get("tag") not in (None, "", self.inst(e)["version"]))
        n_lin = sum(1 for e in self.entries if "solo-codigo" not in (e.get("tags") or []) and (self.build_kind(e) or ("",))[0] == "linux")
        cx = pad
        for lab, f, n in ((f"Instalados · {n_ins}", "Instalados", n_ins), (f"Con actualización · {n_upd}", "Con actualización", n_upd),
                          (f"Con versión de Linux · {n_lin}", "Build Linux", n_lin)):
            if not n:                                   # un filtro vacío solo estorba (v2.26)
                continue
            w = self.font(19, True).size(lab)[0] + self.n(56)
            self.button(f"chip:{f}", (cx, y, w, self.n(72)), lab, lambda f=f: go(f), "normal", 19, pill=True, enabled=n > 0)
            cx += w + self.n(12)
        y += self.n(96) if cx > pad else 0
        items = [(p, f"{n} juego{'s' if n != 1 else ''}" + (f" · {ins[p]} instalado{'s' if ins[p] != 1 else ''}" if ins[p] else ""), p) for p, n in plats]
        items.insert(0, ("Todos los juegos", f"{len(self.entries) - n_solo} en el catálogo", "Todos"))
        if n_solo:
            items.append(("Solo código", f"{n_solo} sin release: hay que compilarlos", "Solo código"))
        for k, (t, sub, f) in enumerate(items):
            self.tile(f"cat:{f}", (pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + gap) + (self.enter(k, "cats") if k < 14 else 0), cw, ch), t, sub, lambda f=f: go(f), self.tint(t, 0.30, 0.45),
                      logo=platformart.logo(t, self.n(44), self.n(170)) if f not in ("Todos", "Solo código") else None)
        y += ((len(items) + cols - 1) // cols) * (ch + gap) + self.n(16)
        self.text("Tu biblioteca", pad, self.cy(y), 28, TXT, True)
        y += self.n(54)
        self.tile("x_lib", (pad, y, self.W - 2 * pad, self.n(130)), "Mi biblioteca de ROMs", "Qué juegos puedes usar con lo que ya tienes", lambda: self.go_tab("library"), None, big=26)
        self.end()

    def visible_entries(self):
        """Lista filtrada de (entrada, instalado, hay_update, release). Se guarda mientras no cambie nada de lo que depende
        (filtro, búsqueda, caché de instalados, releases conocidas, catálogo): con ~1100 juegos recalcularla en cada fotograma pesaba."""
        key = (self.filter, self.query, getattr(self, "_inst_c", None), len(self.rel), id(self.entries), len(self.entries))
        vc = getattr(self, "_vis_c", None)
        if vc and vc[0] == key:
            return vc[1]
        res = self._visible_entries()
        self._vis_c = (key, res)
        return res

    def _visible_entries(self):
        out = []
        for e in self.entries:
            i = self.inst(e)
            rel = self.rel.get(self.rk(e)) or {}
            upd = bool(i["installed"] and i["version"] and rel.get("tag") and rel["tag"] != i["version"]) and not self.frozen(e)
            solo = "solo-codigo" in (e.get("tags") or [])
            if self.filter == "Solo código":
                if not solo:
                    continue
            elif solo and not i["installed"]:
                continue                          # «Solo código» (sin release: hay que compilarlo) solo se ve en su propia lista, salvo lo ya instalado
            if self.filter == "Instalados" and not i["installed"] or self.filter == "Con actualización" and not upd:
                continue
            if self.filter == "Build Linux" and (self.build_kind(e) or ("",))[0] != "linux":
                continue
            if self.filter not in ("Todos", "Instalados", "Con actualización", "Build Linux", "Solo código") and e["platform"] != self.filter:
                continue
            if self.query and not gamedict.match(e, self.query):
                continue
            out.append((e, i, upd, rel))
        return out

    def draw_games(self, body):
        self.begin("games", body)
        pad, gap = self.n(40), self.n(18)
        y = self.n(18)
        cnt = {}
        for e in self.entries:
            if e["platform"] and "solo-codigo" not in (e.get("tags") or []):
                cnt[e["platform"]] = cnt.get(e["platform"], 0) + 1
        plats = [p for p, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))]
        title = {"Todos": "Todos los juegos", "Instalados": "Instalados", "Con actualización": "Con actualización", "Build Linux": "Con build para Linux", "Solo código": "Solo código (sin release)"}.get(self.filter, self.filter)
        self.button("back_cats", (pad, y, self.n(230), self.n(72)), "‹ Consolas", lambda: (setattr(self, "explore", "cats"), setattr(self, "query", ""), setattr(self, "focus", None)), "normal", 19, pill=True)
        self.text(title + (f" · «{self.query}»" if self.query else ""), pad + self.n(250), self.cy(y + self.n(36)), 28, TXT, True, anchor="ml")
        self.button("search", (self.W - pad - self.n(230), y, self.n(230), self.n(72)),
                    (f"× {self.query[:12]}" if self.query else "Buscar…"),
                    (lambda: setattr(self, "query", "")) if self.query else (lambda: self.osk("Buscar juego", lambda t: setattr(self, "query", t.strip()), self.query)), "normal", 19, pill=True)
        y += self.n(98)
        vis = self.visible_entries()
        mode = (SCREENS or {}).get("explore")
        if mode in ("shelf", "shelf_big") and self.filter == "Todos" and not self.query:   # v3.06: Flow y Showcase: una fila por consola
            return self._games_shelves(vis, pad, gap, y, mode == "shelf_big")
        if mode == "mosaic":                         # v3.06: Glass
            return self._games_mosaic(vis, pad, gap, y)
        if mode == "text":                           # v3.07: Terminal
            return self._games_text(vis, pad, gap, y)
        if mode == "index":                          # v3.08: Editorial
            return self._games_index(vis, pad, gap, y)
        if mode == "blocks":                         # v3.08: Brutalist
            return self._games_blocks(vis, pad, gap, y)
        if mode == "numbered":                       # v3.07: Arcade
            return self._games_posters(vis, pad, gap, y, "posters", numbered=True)
        if mode in ("posters", "big", "shelf", "shelf_big"):   # v3.05: Minimal (y Showcase/Flow con filtro o búsqueda): catálogo de portadas
            return self._games_posters(vis, pad, gap, y, "big" if mode in ("big", "shelf_big") else "posters")
        cols = max(2, int((self.W - 2 * pad + gap) // self.n(380)))
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ch = self.n(158)
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            self.cur.nh = max(self.cur.nh, y + self.n(120))
        self.enter(0, ("list", self.filter))
        vistas = {}
        for i, (e, inf, upd, rel) in enumerate(vis):
            cx, cyy = pad + (i % cols) * (cw + gap), y + (i // cols) * (ch + gap) + (self.enter(i, ("list", self.filter)) if i < 14 else 0)
            n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1          # dos fichas con el mismo id no pueden compartir foco: la segunda lleva #1…
            r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (cx, cyy, cw, ch), lambda e=e: self.open_detail(e))
            if not r.colliderect(self.cur.rect):
                continue
            self.rr(r, PANEL2 if foc else PANEL, 22 * RADK)
            if OUTLINE:
                self.rr(r, LINE, 22 * RADK, max(1, self.n(2)))
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 26 * RADK, max(2, self.n(3)))
            tw = self.n(92)
            self.thumb(e, (r.x + self.n(12), r.y + self.n(12), tw, r.h - self.n(24)), foc)
            tx = r.x + self.n(12) + tw + self.n(16)
            iw = r.right - tx - self.n(16)
            ty = self.para(e["name"], tx, r.y + self.n(14), 22, iw, TXT, True, 2)
            gname = gamedict.game_name(e)
            self.text(" · ".join(filter(None, [e["platform"], gname])) or e["repo"], tx, r.bottom - self.n(78), 16, DIM, maxw=iw)
            if inf["installed"] and upd:
                lab, col = f"ACTUALIZAR → {rel['tag']}", WARN
            elif inf["installed"]:
                lab, col = "INSTALADO " + inf["version"], OK
            elif self.build_kind(e):
                _, lab, col = self.build_kind(e)
            else:
                lab, col = "", DIM                      # v2.27: «no instalado» es lo normal; la insignia solo cuando dice algo
            if lab:
                pill = pygame.Rect(tx, r.bottom - self.n(50), iw, self.n(34))
                self.rr(pill, tuple(int(c * 0.22 + b * 0.78) for c, b in zip(col, PANEL2 if foc else PANEL)), 17)
                self.text(lab, pill.centerx, pill.centery, 16, col, True, pill.w - self.n(16), "c")
        self.end()

    def _games_posters(self, vis, pad, gap, y, mode, numbered=False):
        """v3.05: Explorar como catálogo de portadas verticales con el nombre debajo. «posters» (Minimal): 4–7 columnas, sobrio;
        «big» (Showcase): 3–5 columnas, portadas grandes. Mismas claves (card:…) que la lista de siempre: mando, toque y foco no cambian."""
        target = self.n(230) if mode == "posters" else self.n(320)
        lo, hi = (4, 7) if mode == "posters" else (3, 5)
        cols = max(lo, min(hi, int((self.W - 2 * pad + gap) // target)))
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ph = int(cw * 1.38)
        ch = ph + self.n(96 if mode == "big" else 84)
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            self.cur.nh = max(self.cur.nh, y + self.n(120))
        self.enter(0, ("list", self.filter))
        vistas = {}
        for i, (e, inf, upd, rel) in enumerate(vis):
            cx, cyy = pad + (i % cols) * (cw + gap), y + (i // cols) * (ch + gap) + (self.enter(i, ("list", self.filter)) if i < 14 else 0)
            n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1
            r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (cx, cyy, cw, ch), lambda e=e: self.open_detail(e))
            if not r.colliderect(self.cur.rect):
                continue
            self._poster_tile(e, inf, upd, rel, r, foc, ph, mode == "big")
            if numbered:                                  # v3.07 Arcade: número de casilla, como el Inicio de casillas
                lab = f"{i + 1:02d}"
                tw_ = self.font(22, True).size(lab)[0] + self.n(18)
                badge = pygame.Rect(r.x + self.n(4), r.y + self.n(4), tw_, self.n(34))
                pygame.draw.rect(self.screen, ACC, badge)
                self.text(lab, badge.centerx, badge.centery, 22, ON_ACC, True, anchor="c")
        self.end()

    def _poster_tile(self, e, inf, upd, rel, r, foc, ph, big=False):
        """Portada vertical + nombre + una línea de estado (v3.05/3.06: catálogo, estantes)."""
        self.rr(r, PANEL2 if foc else PANEL, 18 * RADK)
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 22 * RADK, max(2, self.n(3)))
        m = self.n(10)
        self.thumb(e, (r.x + m, r.y + m, r.w - 2 * m, ph - m), foc)
        self.para(e["name"], r.x + self.n(14), r.y + ph + self.n(10), 20 if big else 18, r.w - self.n(28), TXT, True, 2)
        if inf["installed"] and upd:
            lab, col = f"Actualizar → {rel['tag']}", WARN
        elif inf["installed"]:
            lab, col = "Instalado " + (inf["version"] or ""), OK
        else:
            lab, col = (e["platform"] or ""), DIM
        self.text(lab.strip(), r.x + self.n(14), r.bottom - self.n(22), 15, col, inf["installed"], r.w - self.n(28), anchor="ml")

    def _games_shelves(self, vis, pad, gap, y, big):
        """v3.06 (Flow, Showcase): Explorar por estantes, una fila por consola (las que más juegos tienen, primero). Si no caben todos,
        la última casilla es «VER TODOS (n)» y abre esa consola. Solo se desplaza en vertical: mando y toque como siempre."""
        target = self.n(300) if big else self.n(240)
        cols = max(3, min(7, int((self.W - 2 * pad + gap) // target)))
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ph = int(cw * 1.38)
        ch = ph + self.n(96 if big else 84)
        groups = {}
        for t in vis:
            groups.setdefault(t[0]["platform"] or "Otros", []).append(t)
        vistas = {}
        for plat, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            self.text(f"{plat}  ·  {len(items)}", pad + self.n(6), self.cy(y) + self.n(18), 22 if big else 20, TXT, True, anchor="ml")
            y += self.n(46)
            show = items if len(items) <= cols else items[:cols - 1]
            for i, (e, inf, upd, rel) in enumerate(show):
                n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1
                r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (pad + i * (cw + gap), y, cw, ch), lambda e=e: self.open_detail(e))
                if r.colliderect(self.cur.rect):
                    self._poster_tile(e, inf, upd, rel, r, foc, ph, big)
            if len(items) > cols:
                r, foc = self.reg(f"shelf:{plat}", (pad + (cols - 1) * (cw + gap), y, cw, ch),
                                  lambda p=plat: (setattr(self, "filter", p), setattr(self, "focus", None), setattr(self, "reveal", True)))
                if r.colliderect(self.cur.rect):
                    self.rr(r, PANEL2 if foc else PANEL, 18 * RADK)
                    if foc:
                        self.glow(r)
                        self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 22 * RADK, max(2, self.n(3)))
                    self.text("VER TODOS", r.centerx, r.centery - self.n(16), 22, TXT, True, r.w - self.n(20), "c")
                    self.text(f"{len(items)} juegos", r.centerx, r.centery + self.n(18), 17, DIM, False, r.w - self.n(20), "c")
            y += ch + self.n(30)
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            y += self.n(120)
        self.cur.nh = max(self.cur.nh, y)
        self.end()

    def _games_text(self, vis, pad, gap, y):
        """v3.07 (Terminal): catálogo de texto, una línea por juego (nº · nombre · consola · estado), agrupado por consola."""
        rh = self.n(72)                                   # 7,2 mm o más en el Ally
        w = self.W - 2 * pad
        groups = {}
        for t in vis:
            groups.setdefault(t[0]["platform"] or "otros", []).append(t)
        vistas, k = {}, 0
        for plat, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            self.text(f"== {plat.upper()} ({len(items)}) ==", pad + self.n(6), self.cy(y) + self.n(18), 18, ACC, True, anchor="ml")
            y += self.n(44)
            for e, inf, upd, rel in items:
                k += 1
                n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1
                r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (pad, y, w, rh), lambda e=e: self.open_detail(e))
                y += rh + self.n(6)
                if not r.colliderect(self.cur.rect):
                    continue
                self.rr(r, PANEL2 if foc else PANEL, 4)
                if foc:
                    self.rr(r.inflate(self.n(6), self.n(6)), FOCUS or TXT, 4, max(2, self.n(3)))
                st, col = (("ACTUALIZAR " + rel["tag"], WARN) if inf["installed"] and upd else
                           ("INSTALADO " + (inf["version"] or ""), OK) if inf["installed"] else ("--", DIM))
                self.text(("> " if foc else "  ") + f"{k:03d}", r.x + self.n(14), r.centery, 18, ACC if foc else DIM, True, anchor="ml")
                self.text(e["name"], r.x + self.n(110), r.centery, 19, TXT, foc, int(w * 0.52), anchor="ml")
                self.text(e["platform"] or "", r.x + self.n(110) + int(w * 0.54), r.centery, 16, DIM, False, int(w * 0.16), anchor="ml")
                self.text(st.strip(), r.right - self.n(16), r.centery, 16, col, True, int(w * 0.22), anchor="mr")
            y += self.n(18)
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            y += self.n(120)
        self.cur.nh = max(self.cur.nh, y)
        self.end()

    def _games_index(self, vis, pad, gap, y):
        """v3.08 (Editorial): índice de revista. Título de sección grande por consola con su número de juegos y una línea; filas con
        portada pequeña, nombre en grande y una línea de datos; separador fino entre filas (sin cajas)."""
        rh = self.n(104)
        w = self.W - 2 * pad
        groups = {}
        for t in vis:
            groups.setdefault(t[0]["platform"] or "Otros", []).append(t)
        vistas = {}
        for plat, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            self.text(plat, pad + self.n(4), self.cy(y) + self.n(26), 34, TXT, True, int(w * 0.7), anchor="ml")
            self.text(f"{len(items)} {'juego' if len(items) == 1 else 'juegos'}", pad + w - self.n(4), self.cy(y) + self.n(30), 17, DIM, False, anchor="mr")
            y += self.n(58)
            pygame.draw.line(self.screen, TXT, (pad, self.cy(y)), (pad + w, self.cy(y)), max(2, self.n(2)))
            y += self.n(8)
            for e, inf, upd, rel in items:
                n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1
                r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (pad, y, w, rh), lambda e=e: self.open_detail(e))
                y += rh
                if not r.colliderect(self.cur.rect):
                    continue
                if foc:
                    self.rr(r, PANEL2, 8 * RADK)
                    self.rr(r.inflate(self.n(6), self.n(6)), FOCUS or TXT, 10 * RADK, max(2, self.n(3)))
                tw_ = int((r.h - self.n(20)) / 1.38)
                self.thumb(e, (r.x + self.n(8), r.y + self.n(10), tw_, r.h - self.n(20)), foc)
                tx = r.x + self.n(8) + tw_ + self.n(22)
                self.text(e["name"], tx, r.y + self.n(36), 24, TXT, True, r.right - tx - self.n(260), anchor="ml")
                gname = gamedict.game_name(e)
                self.text(" · ".join(filter(None, [e["platform"], gname])) or e["repo"], tx, r.y + self.n(72), 16, DIM, False, r.right - tx - self.n(260), anchor="ml")
                st, col = ((f"Actualizar a {rel['tag']}", WARN) if inf["installed"] and upd else
                           (f"Instalado {inf['version'] or ''}", OK) if inf["installed"] else ("", DIM))
                if st:
                    self.text(st.strip(), r.right - self.n(12), r.centery, 17, col, True, self.n(240), anchor="mr")
                pygame.draw.line(self.screen, LINE, (r.x, r.bottom - 1), (r.right, r.bottom - 1), 1)
            y += self.n(30)
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            y += self.n(120)
        self.cur.nh = max(self.cur.nh, y)
        self.end()

    def _games_blocks(self, vis, pad, gap, y):
        """v3.08 (Brutalist): bloques geométricos con número gigante; uno de cada cinco ocupa dos columnas. Portada pequeña a la derecha."""
        cols = max(3, min(5, int((self.W - 2 * pad + gap) // self.n(300))))
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        bh = self.n(220)
        row, col_ = 0, 0
        vistas = {}
        bottom = y
        for i, (e, inf, upd, rel) in enumerate(vis):
            span = 2 if (i % 5 == 0 and cols >= 3) else 1
            if col_ + span > cols:
                row, col_ = row + 1, 0
            rx, ry = pad + col_ * (cw + gap), y + row * (bh + gap)
            w_ = span * cw + (span - 1) * gap
            col_ += span
            if col_ >= cols:
                row, col_ = row + 1, 0
            n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1
            r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (rx, ry, w_, bh), lambda e=e: self.open_detail(e))
            bottom = max(bottom, ry + bh)
            if not r.colliderect(self.cur.rect):
                continue
            fill = ACC if (span == 2 and not foc) else (PANEL2 if foc else PANEL)
            pygame.draw.rect(self.screen, fill, r)
            pygame.draw.rect(self.screen, TXT if foc else LINE, r, max(3, self.n(4 if foc else 3)))
            ink = on_color(fill) if fill == ACC else TXT
            self.text(f"{i + 1:02d}", r.x + self.n(18), r.y + self.n(54), 64 if span == 2 else 54, ink, True, anchor="ml")
            cov = int(bh * 0.55)
            self.thumb(e, (r.right - cov - self.n(16), r.y + self.n(16), int(cov / 1.38), cov), foc)
            self.para(e["name"].upper(), r.x + self.n(18), r.y + bh - self.n(96), 20, r.w - self.n(36), ink, True, 2)
            st = ("ACTUALIZAR" if inf["installed"] and upd else "INSTALADO" if inf["installed"] else (e["platform"] or "").upper())
            self.text(st, r.x + self.n(18), r.bottom - self.n(22), 15, ink if fill == ACC else (OK if inf["installed"] else DIM), True, r.w - self.n(36), anchor="ml")
            if foc:
                self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 0, max(3, self.n(4)))
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            bottom += self.n(120)
        self.cur.nh = max(self.cur.nh, bottom + self.n(20))
        self.end()

    def _games_mosaic(self, vis, pad, gap, y):
        """v3.06 (Glass): mosaico de portadas de tamaños distintos (1 de cada 6, al doble). Nombre sobre la portada, como el Inicio de Cristal."""
        cols = max(5, min(8, int((self.W - 2 * pad + gap) // self.n(200))))
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        chh = int(cw * 1.38)
        occ = set()
        vistas = {}
        row = 0
        bottom = y
        for i, (e, inf, upd, rel) in enumerate(vis):
            big = i % 6 == 0 and cols >= 4
            span = 2 if big else 1
            while True:                                       # primera casilla libre (para la grande, 2×2 libre)
                cands = [c for c in range(cols - span + 1) if all((row + dr, c + dc) not in occ for dr in range(span) for dc in range(span))]
                if cands:
                    c0 = cands[0]
                    break
                row += 1
            for dr in range(span):
                for dc in range(span):
                    occ.add((row + dr, c0 + dc))
            rx, ry = pad + c0 * (cw + gap), y + row * (chh + gap)
            w_, h_ = span * cw + (span - 1) * gap, span * chh + (span - 1) * gap
            n = vistas[e["id"]] = vistas.get(e["id"], -1) + 1
            r, foc = self.reg(f"card:{e['id']}" + (f"#{n}" if n else ""), (rx, ry, w_, h_), lambda e=e: self.open_detail(e))
            bottom = max(bottom, ry + h_)
            if not r.colliderect(self.cur.rect):
                continue
            self.thumb(e, r, foc)
            sh = pygame.Rect(r.x, r.bottom - self.n(70 if big else 58), r.w, self.n(70 if big else 58))
            self.rr(sh, PANEL, 0, a=170 if GLASS else None)
            self.text(e["name"], r.x + self.n(12), sh.y + self.n(20), 20 if big else 16, TXT, True, r.w - self.n(24), anchor="ml")
            lab, col = ((f"Actualizar → {rel['tag']}", WARN) if inf["installed"] and upd else ("Instalado", OK) if inf["installed"] else (e["platform"] or "", DIM))
            self.text(lab, r.x + self.n(12), sh.y + sh.h - self.n(16), 14, col, False, r.w - self.n(24), anchor="ml")
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(8), self.n(8)), FOCUS or TXT, 22 * RADK, max(2, self.n(3)))
        if not vis:
            self.text("Nada que mostrar con este filtro.", self.W // 2, self.cy(y + self.n(60)), 24, DIM, anchor="mid")
            bottom += self.n(120)
        self.cur.nh = max(self.cur.nh, bottom + self.n(20))
        self.end()

    def draw_search(self, body):
        self.begin("search", body)
        colw = min(self.W - self.n(80), self.n(1200))
        x0 = (self.W - colw) // 2
        y = self.n(18)
        q = self.sq
        self.button("sq", (x0, y, colw, self.n(78)), f"Juego:  {q}" if q else "Toca aquí y escribe el nombre del juego",
                    lambda: self.osk("Nombre del juego", self.run_search, self.sq), "primary" if not q else "normal", 24)
        y += self.n(98)
        x = x0
        for suf in ("recomp", "decomp", "port", "nativo", ""):
            lab = suf or "sin sufijo"
            w = self.font(19, True).size(lab)[0] + self.n(50)
            self.button(f"suf:{suf}", (x, y, w, self.n(72)), lab, lambda suf=suf: (setattr(self, "ssuf", suf), self.run_search()),
                        "primary" if self.ssuf == suf else "normal", 19)
            x += w + self.n(12)
        y += self.n(90)
        g = self.n(14)
        bw = (colw - 3 * g) // 4
        full = (self.sq + " " + self.ssuf).strip()
        self.button("s_br", (x0, y, bw, self.n(72)), "BUSCAR EN GITHUB", lambda: self.open_url(
            f"https://github.com/search?q={urllib.parse.quote_plus(full)}&type=repositories"), size=17, enabled=bool(self.sq))
        self.button("s_web2", (x0 + bw + g, y, bw, self.n(72)), "GITHUB (YO MISMO)", lambda: self.open_url(GH_SEARCH), size=17)
        self.button("s_goo", (x0 + 2 * (bw + g), y, bw, self.n(72)), "BUSCAR EN GOOGLE", lambda: self.search_google(self.sq), size=17, enabled=bool(self.sq))
        self.button("s_paste", (x0 + 3 * (bw + g), y, bw, self.n(72)), "PEGAR URL / REPO", self.paste_repo, size=17)
        y += self.n(92)
        if self.clip_repo:
            r, foc = self.reg("clipban", (x0, y, colw, self.n(84)), lambda: self.open_repo(self.clip_repo))
            self.rr(r, (28, 70, 52) if not foc else (40, 100, 70), 16)
            if foc:
                self.rr(r, TXT, 16, 3)
            self.text("Repositorio copiado", r.x + self.n(24), r.y + self.n(12), 17, OK, True)
            self.text(self.clip_repo, r.x + self.n(24), r.y + self.n(38), 24, TXT, True, r.w - self.n(260))
            self.text("USAR ESTE ›", r.right - self.n(24), r.centery, 22, TXT, True, anchor="mr")
            y += self.n(102)
        if self.sbusy:
            self.text("Buscando en GitHub…", x0, self.cy(y), 22, DIM)
            y += self.n(40)
        elif self.serr:
            self.text(self.serr, x0, self.cy(y), 21, WARN, True, colw)
            y += self.n(40)
        elif self.sres is not None and not self.sres:
            self.text("Sin resultados. Prueba otro sufijo o el navegador.", x0, self.cy(y), 21, DIM)
            y += self.n(40)
        elif self.sres is None:
            self.text("Escribe el nombre del juego: Hub busca repositorios de GitHub y tú eliges cuál es. "
                      + ("" if auth.token() else "(Sin sesión de GitHub: máximo ~10 búsquedas por minuto)"), x0, self.cy(y), 19, DIM, maxw=colw)
        known = {e["repo"].lower() for e in self.entries}
        for i, it in enumerate(self.sres or []):
            r, foc = self.reg(f"sr:{i}", (x0, y, colw, self.n(108)), lambda it=it: self.open_repo(it["full_name"]))
            self.rr(r, PANEL2 if foc else PANEL, 16)
            self.rr(r, ACC if foc else LINE, 16, max(2, self.n(3 if foc else 1)))
            self.text(it["full_name"], r.x + self.n(22), r.y + self.n(12), 23, TXT, True, r.w - self.n(420))
            dsc = self.wrap(it["description"] or "(sin descripción)", 17, r.w - self.n(420), max_lines=2)
            for k, ln in enumerate(dsc):
                self.text(ln, r.x + self.n(22), r.y + self.n(46 + 24 * k), 17, DIM)
            meta = f"★ {it['stars']}   {it['language']}   {it['updated']}"
            self.text(meta, r.right - self.n(22), r.y + self.n(16), 18, DIM, anchor="tr")
            tags = []
            if it["full_name"].lower() in known:
                tags.append(("YA EN TU CATÁLOGO", OK))
            if it["archived"]:
                tags.append(("ARCHIVADO", WARN))
            if it["fork"]:
                tags.append(("FORK", DIM))
            tx = r.right - self.n(22)
            for lab, col in tags:
                tw = self.font(15, True).size(lab)[0] + self.n(24)
                pr = pygame.Rect(tx - tw, r.y + self.n(60), tw, self.n(30))
                self.rr(pr, BG, 15)
                self.text(lab, pr.centerx, pr.centery, 15, col, True, anchor="c")
                tx -= tw + self.n(8)
            y += self.n(120)
        self.cur.nh = max(self.cur.nh, y + self.n(30))
        self.end()
