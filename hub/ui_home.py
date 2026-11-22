"""Inicio: héroe «Continuar», dónde están tus archivos, plataformas y tus juegos. Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class HomeMixin:
    def _gradient(self, size, c1, c2):
        key = ("_grad", size, c1, c2)
        c = self._tc
        if key not in c:
            sur = pygame.Surface(size).convert()
            for x in range(size[0]):
                t = x / max(1, size[0] - 1)
                pygame.draw.line(sur, tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)), (x, 0), (x, size[1]))
            c[key] = sur
        return c[key]

    def _home_side(self, inst, pad, gap, y):
        """Inicio del prototipo: héroe «Continuar» con el último juego + «Mis juegos» en tarjetas verticales con insignia de plataforma."""
        self._home_upd = sum(1 for t in inst if t[2])
        lp = self.cfg.get("last_played") or {}
        hero = next((t for t in inst if t[0]["id"] == lp.get("id")), inst[0])
        e, i, upd, rel = hero
        self._hero_e = e
        y = self._home_where(pad, y)
        hw, hh = self.W - 2 * pad, self.n(290)
        r, foc = self.reg("hero", (pad, y, hw, hh), lambda e=e: self.play(e), True, None, None, lambda e=e: self.open_detail(e))
        base = self.tint(e["name"])
        base = tuple(base) if base else ACC
        cov = self.cover(e, (hw, hh))
        if cov is not None:
            self.screen.blit(cov, r)
        else:
            self.screen.blit(pygame.transform.smoothscale(self._gradient((64, 8), tuple(int(c * .55) for c in base), tuple(int(c * .85) for c in base)), r.size), r)
        self.rr(r, LINE, 24, max(1, self.n(2)))
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 28, max(3, self.n(4)))
        sub = "Continuar" + (f" · {self.ago(lp['t'])}" if lp.get("id") == e["id"] and lp.get("t") else "")
        self.text(sub, r.x + self.n(40), r.y + self.n(52), 22, (255, 255, 255))
        self.para(e["name"], r.x + self.n(40), r.y + self.n(80), 44, r.w - self.n(80), (255, 255, 255), True, 2)
        bw, bh = self.n(150), self.n(54)
        pr = pygame.Rect(r.x + self.n(40), r.bottom - bh - self.n(26), bw, bh)
        self.rr(pr, ACC, 16)
        lw = self.font(24, True).size("Jugar")[0]
        self.tri(pr.centerx - lw // 2 - self.n(8), pr.centery, self.n(20), "right", ON_ACC)
        self.text("Jugar", pr.centerx + self.n(14), pr.centery, 24, ON_ACC, True, anchor="c")
        y += hh + self.n(30)
        y = self._home_plats(pad, gap, y)
        self.text("Mis juegos", pad, self.cy(y), 32, TXT, True)
        self.text("lo instalado, listo para jugar", pad + self.font(32, True).size("Mis juegos")[0] + self.n(16), self.cy(y) + self.n(8), 19, DIM)
        y += self.n(58)
        cw, ch = self.n(196), self.n(262)
        cols = max(1, (self.W - 2 * pad + gap) // (cw + gap))
        for k, (e, i, upd, rel) in enumerate(inst):
            cx, cyy = pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + self.n(44) + gap)
            self._home_card(e, i, upd, rel, (cx, cyy, cw, ch))
        return y + ((len(inst) + cols - 1) // cols) * (ch + self.n(44) + gap) + self.n(10)

    def set_file_mode(self, m):
        self.cfg["file_mode"] = m
        config.save_settings(self.cfg)
        self.toast("Tus archivos de juego se buscarán " + ("en tu servidor de catálogo" if m == "server" else "en este equipo"))

    def _home_where(self, pad, y):
        """Arriba a la derecha: dónde buscar tus archivos de juego (el mismo ajuste que la ficha: «EN MI EQUIPO / EN MI SERVIDOR»)."""
        mode = self.cfg.get("file_mode", "local")
        bw, bh = self.n(230), self.n(72)   # ≥ 7 mm en el Ally (lo comprueba test_v191)
        x0 = self.W - pad - 2 * bw - self.n(8)
        self.text("Tus archivos:", x0 - self.n(14), self.cy(y) + bh // 2, 19, DIM, anchor="mr")
        self.button("hm_local", (x0, y, bw, bh), "En mi equipo", lambda: self.set_file_mode("local"), "seg" if mode == "local" else "normal", 19, mark=mode == "local")
        self.button("hm_server", (x0 + bw + self.n(8), y, bw, bh), "En mi servidor", lambda: self.set_file_mode("server"), "seg" if mode == "server" else "normal", 19,
                    mark=mode == "server")
        return y + bh + self.n(20)

    def home_platforms(self):
        """Plataformas del catálogo ordenadas por juegos instalados y luego por tamaño (cacheado por catálogo + instalados)."""
        key = (id(self.entries), len(self.entries), getattr(self, "_inst_c", None) is not None)
        if getattr(self, "_hp_c", (None,))[0] != key:
            cnt, ins = {}, {}
            for e in self.entries:
                pl = e.get("platform")
                if pl:
                    cnt[pl] = cnt.get(pl, 0) + 1
                    ins[pl] = ins.get(pl, 0) + (1 if self.inst(e)["installed"] else 0)
            self._hp_c = (key, sorted(cnt, key=lambda p: (-ins[p], -cnt[p], p)), cnt, ins)
        return self._hp_c[1:]

    def explore_platform(self, plat):
        self.go_tab("games")
        self.filter, self.query, self.explore, self.focus, self.reveal = plat, "", "list", None, True

    def _home_plats(self, pad, gap, y):
        """Fila de plataformas: logos de las consolas de tu catálogo; tocar una abre Explorar filtrado. Solo las que caben (sin scroll lateral)."""
        order, cnt, ins = self.home_platforms()
        if not order:
            return y
        self.text("Plataformas", pad, self.cy(y), 28, TXT, True)
        y += self.n(50)
        tw, th, g = self.n(176), self.n(96), self.n(16)
        n = max(1, min(len(order), (self.W - 2 * pad + g) // (tw + g)))
        for k, pl in enumerate(order[:n]):
            r, foc = self.reg(f"hp:{pl}", (pad + k * (tw + g), y, tw, th), lambda pl=pl: self.explore_platform(pl), True)
            self.rr(r, (240, 243, 247), 16)
            lg = platformart.logo(pl, self.n(40), tw - self.n(28))
            if lg is not None:
                self.screen.blit(lg, lg.get_rect(center=(r.centerx, r.y + self.n(38))))
            else:
                self.text((esde.system_for(pl) or pl).upper()[:10], r.centerx, r.y + self.n(38), 20, (20, 24, 30), True, r.w - self.n(16), "c")
            sub = f"{cnt[pl]} juego{'s' if cnt[pl] != 1 else ''}" + (f" · {ins[pl]} tuyo{'s' if ins[pl] != 1 else ''}" if ins[pl] else "")
            self.text(sub, r.centerx, r.bottom - self.n(18), 15, (70, 76, 86), False, r.w - self.n(12), "c")
            if foc:
                self.glow(r)
                self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 22, max(3, self.n(4)))
        return y + th + self.n(34)

    def _home_card(self, e, i, upd, rel, rect):
        r, foc = self.reg(f"home:{e['id']}", rect, lambda e=e: self.play(e), True, None,
                          (lambda e=e: self.do_install(e)) if upd else None, lambda e=e: self.open_detail(e))
        base = self.tint(e["name"])
        base = tuple(base) if base else ACC
        cov = self.cover(e, r.size)
        if cov is not None:
            self.screen.blit(cov, r)
        else:
            col = pygame.Surface(r.size, pygame.SRCALPHA)
            for yy in range(r.h):
                t = yy / r.h
                pygame.draw.line(col, (*[int(c * (0.95 - 0.35 * t)) for c in base], 255), (0, yy), (r.w, yy))
            self.screen.blit(artgen._round(col, int(22 * self.k)) if hasattr(artgen, "_round") else col, r)
        shade = pygame.Surface((r.w, self.n(90)), pygame.SRCALPHA)
        for yy in range(shade.get_height()):
            pygame.draw.line(shade, (0, 0, 0, int(170 * yy / shade.get_height())), (0, yy), (r.w, yy))
        self.screen.blit(shade, (r.x, r.bottom - shade.get_height()))
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, 26, max(3, self.n(4)))
        lg = platformart.logo(e.get("platform") or "", self.n(24), self.n(96))
        if lg is not None:
            pr = pygame.Rect(r.x + self.n(12), r.y + self.n(12), lg.get_width() + self.n(18), lg.get_height() + self.n(12))
            self.rr(pr, (240, 243, 247), 8)
            self.screen.blit(lg, lg.get_rect(center=pr.center))
        else:
            plat = (esde.system_for(e.get("platform") or "") or (e.get("platform") or "?")).upper()[:6]
            bw = self.font(15, True).size(plat)[0] + self.n(22)
            pr = pygame.Rect(r.x + self.n(12), r.y + self.n(12), bw, self.n(28))
            self.rr(pr, (0, 0, 0), 8)
            self.text(plat, pr.centerx, pr.centery, 15, (255, 255, 255), True, anchor="c")
        cc = (r.right - self.n(26), r.y + self.n(26))
        pygame.draw.circle(self.screen, ACC if upd else OK, cc, self.n(15))
        if upd:
            self.tri(cc[0], cc[1] - self.n(2), self.n(16), "up", ON_ACC)
            pygame.draw.rect(self.screen, ON_ACC, (cc[0] - self.n(3), cc[1] + self.n(1), self.n(6), self.n(8)))
        else:
            self.check(cc[0], cc[1], self.n(16), (10, 40, 22), 4)
        self.para(e["name"], r.x + self.n(14), r.bottom - self.n(68), 21, r.w - self.n(28), (255, 255, 255), True, 2)
        self.text(str(i.get("launcher_id") or e["id"]), r.x + self.n(4), r.bottom + self.n(8), 15, DIM, maxw=r.w)

    def draw_home(self, body):
        self.begin("home", body)
        pad, gap = self.n(48), self.n(24)
        inst = []
        for e in self.entries:
            i = self.inst(e)
            if i["installed"]:
                rel = self.rel.get(self.rk(e)) or {}
                upd = bool(i["version"] and rel.get("tag") and rel["tag"] != i["version"]) and not self.frozen(e)
                inst.append((e, i, upd, rel))
        y = self.n(30)
        n_upd = sum(1 for t in inst if t[2])
        if HOME == "hero" and inst:
            y = self._home_side(inst, pad, gap, y)
            inst = []                                  # ya dibujados; abajo solo queda «Más»
        elif HOME not in ("grid", "hero") and inst:
            self.text("Tus juegos", pad, self.cy(y), 40, TXT, True)
            y = self._home_custom(inst, pad, gap, y + self.n(70))
            inst = []
        else:
            self.text("Tus juegos", pad, self.cy(y), 40, TXT, True)
            y += self.n(70)
        cols = 3 if self.W < self.n(2000) else 4
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ch = self.n(230)
        if not inst and not n_upd and not any(self.inst(e)["installed"] for e in self.entries):
            self.text("Todavía no tienes juegos instalados.", pad, self.cy(y), 26, DIM)
            y += self.n(60)
            self.tile("empty_go", (pad, y, cw * 2 + gap, self.n(150)), "Explorar juegos", "Elige una consola y descarga tu primer port", lambda: self.go_tab("games"), ACC, big=30)
            y += self.n(180)
        for k, (e, i, upd, rel) in enumerate(inst):
            cx, cyy = pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + gap)
            self.tile(f"home:{e['id']}", (cx, cyy, cw, ch), e["name"], e["platform"] or "", lambda e=e: self.play(e), self.tint(e["name"]),
                      x=(lambda e=e: self.do_install(e)) if upd else None, y=lambda e=e: self.open_detail(e), badge=("Actualización " + rel["tag"]) if upd else "Jugar",
                      cover=self.cover(e, (cw, ch)))
        if inst:
            y += ((len(inst) + cols - 1) // cols) * (ch + gap)
        y += self.n(10)
        self.text("Más", pad, self.cy(y), 28, TXT, True)
        y += self.n(54)
        upd_n = n_upd
        n_act = sum(1 for d in self.mgr.list() + self.cjobs.list() if d.state in ("active", "queued", "waiting")) + sum(1 for b in self.builds if b.state in ("queued", "running"))
        tw = (self.W - 2 * pad - 3 * gap) // 4
        self.tile("go_steam", (pad + 3 * (tw + gap), y, tw, self.n(130)), "Añadir a Steam", "Iconos y arte de tus juegos", lambda: self.go_tab("steam"), None, big=24)
        self.tile("go_lib", (pad, y, tw, self.n(130)), "Mi biblioteca", "Tus ROMs y sus ports", lambda: self.go_tab("library"), None, big=26)
        self.tile("go_upd", (pad + tw + gap, y, tw, self.n(130)), "Actualizaciones" + (f" ({upd_n})" if upd_n else ""), "Buscar versiones nuevas", self.check_all, None, big=26)
        self.tile("go_dl", (pad + 2 * (tw + gap), y, tw, self.n(130)), "Descargas" + (f" ({n_act})" if n_act else ""), "Progreso y archivos recibidos", lambda: self.go_tab("downloads"), None, big=26)
        y += self.n(130) + gap
        self.end()
