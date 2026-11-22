"""Descargas: tarjetas de progreso y archivos recibidos. Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class DownloadsMixin:
    @staticmethod
    def dl_ring_colors(bg):
        """Disco y pista del círculo de progreso. En temas oscuros, como siempre (el fondo oscurecido). v3.09: en temas CLAROS oscurecer
        el disco lo dejaba gris medio y el porcentaje (TXT oscuro) apenas se leía: ahí el disco es el fondo muy poco tintado hacia el texto
        y la pista, algo más; así el número y el arco se leen. Solo cambia este indicador."""
        if a11ymod.lum(bg) <= 0.4:
            return tuple(int(bg[i] * .55) for i in range(3)), tuple(int(bg[i] * .8 + 12) for i in range(3))
        return (tuple(int(bg[i] + (TXT[i] - bg[i]) * 0.06) for i in range(3)),
                tuple(int(bg[i] + (TXT[i] - bg[i]) * 0.18) for i in range(3)))

    def dl_card(self, key, x, y, w, h, title, status, scol, frac, sub="", main=None, onmain=None, x_lab="", onx=None, kind="normal", icon=""):
        """Tarjeta de descarga: anillo con el avance a la izquierda, texto, y dos acciones compactas abajo a la derecha.
        El fondo toma un matiz muy suave del estado (azul activa, verde lista, rojo fallo, ámbar pausa)."""
        r, foc = self.reg(key, (x, y, w, h), onmain or (lambda: None), x=onx)
        acts = [(a, b) for a, b in ((main, onmain), (x_lab, onx)) if a and b]       # v2.92: las mismas acciones, en el menú de pulsación larga
        self.__dict__.setdefault("_lp_actions", {})[key] = acts
        done = kind == "done"
        col = OK if done else ERR if kind == "error" else WARN if kind == "paused" else ACC if kind == "active" else DIM
        base = PANEL2 if foc else PANEL
        k = 0.10 if kind in ("active", "done", "error", "paused") else 0.0
        bg = tuple(int(base[i] * (1 - k) + col[i] * k) for i in range(3))
        self.rr(r, bg, 26 * (RADK if MAT else 1), a=150 if GLASS else None)      # v3.07: en el Estudio, el radio de la identidad
        if k:   # filo de color a la izquierda: se lee el estado de un vistazo
            pygame.draw.rect(self.screen, col, (r.x + self.n(2), r.y + self.n(30), self.n(5), r.h - self.n(60)), border_radius=3)
        self.ring(r, foc)
        rad = self.n(46)
        cx, cy = r.x + self.n(34) + rad, r.y + self.n(24) + rad
        disc, track = self.dl_ring_colors(bg)
        self.disc(cx, cy, rad - self.n(5), disc)
        self.ring_progress(cx, cy, rad, 1.0 if (done or kind == "error") else frac, col, track=track, th=max(4, self.n(6)))
        sz = self.n(26)
        g = icon or ("check" if done else "cross" if kind == "error" else "")
        if g:
            self.glyph(g, cx, cy, sz, col if g != "down" else TXT)
        elif kind in ("active", "paused"):
            self.text(f"{int(frac * 100)}%", cx, cy, 24, TXT, True, anchor="c")
        else:
            self.glyph("dots", cx, cy, sz, DIM)
        tx = r.x + self.n(34) + 2 * rad + self.n(26)
        self.text(title, tx, r.y + self.n(22), 24, TXT, True, r.right - tx - self.n(24))
        self.text(status, tx, r.y + self.n(60), 18, scol, maxw=r.right - tx - self.n(24))
        if sub:
            self.text(sub, tx, r.y + self.n(88), 16, DIM, maxw=r.right - tx - self.n(24))
        bw, bh = self.n(170), self.n(72)          # 7 mm o más en el Ally
        oy = r.y - self.cur.rect.y + int(self.cur.off) + r.h - bh - self.n(20)
        bx = r.right - self.n(24) - bw
        if x_lab:
            self.button(key + ":x", (bx, oy, bw, bh), x_lab, onx, "danger" if x_lab == "CANCELAR" else "normal", 17, focus=False, pill=True)
            bx -= bw + self.n(10)
        if main:
            self.button(key + ":m", (bx, oy, bw, bh), main, onmain, "primary" if kind in ("paused", "error") else "normal", 17, focus=False, pill=True)
            bx -= self.n(10)
        style = self.__dict__.get("_dl_bar")
        if style and kind in ("active", "paused"):
            if style == "big":                                              # v3.06: barra grande en las tarjetas anchas (Showcase, Flow)
                bar = pygame.Rect(tx, r.bottom - self.n(20) - bh // 2 - self.n(8), max(self.n(80), bx - tx - self.n(16)), self.n(16))
                self.rr(bar, tuple(int(bg[i] * .7) for i in range(3)), 8)
                if frac > 0:
                    self.rr((bar.x, bar.y, max(bar.h, int(bar.w * frac)), bar.h), col, 8)
            elif style == "segments":                                       # v3.07 Arcade: barra por bloques
                n_, gw = 20, self.n(3)
                bw_ = max(self.n(120), min(r.right - tx - self.n(24), bx - tx - self.n(16) if bx - tx > self.n(200) else r.right - tx - self.n(24)))
                by_ = r.y + self.n(118)
                sw = (bw_ - (n_ - 1) * gw) / n_
                on = int(round(frac * n_))
                for i in range(n_):
                    pygame.draw.rect(self.screen, col if i < on else tuple(int(bg[j] * .6) for j in range(3)),
                                     (int(tx + i * (sw + gw)), by_, max(2, int(sw)), self.n(12)))
            elif style == "thin":                                           # v3.08 Editorial: barra fina y sobria
                bar = pygame.Rect(tx, r.y + self.n(118), max(self.n(80), bx - tx - self.n(16)), max(2, self.n(4)))   # debajo de la línea de tamaño
                pygame.draw.rect(self.screen, LINE, bar)
                pygame.draw.rect(self.screen, col, (bar.x, bar.y, int(bar.w * frac), bar.h))
            elif style == "block":                                          # v3.08 Brutalist: indicador grueso con el % dentro
                bar = pygame.Rect(tx, r.y + self.n(112), r.right - tx - self.n(24), self.n(34))
                pygame.draw.rect(self.screen, BG, bar)
                pygame.draw.rect(self.screen, col, (bar.x, bar.y, int(bar.w * frac), bar.h))
                pygame.draw.rect(self.screen, TXT, bar, max(2, self.n(3)))
                self.text(f"{frac * 100:.0f}%", bar.x + self.n(10), bar.centery, 22, TXT if frac < 0.15 else on_color(col), True, anchor="ml")
            elif style == "ascii":                                          # v3.07 Terminal: barra de texto
                k = int(round(frac * 20))
                self.text(f"[{'#' * k}{'.' * (20 - k)}] {frac * 100:3.0f}%", tx, r.y + self.n(116), 18, col, True, max(self.n(80), bx - tx - self.n(16)), anchor="ml")
        return r

    def draw_downloads(self, body):
        self.begin("downloads", body)
        pad = self.n(48)
        items = sorted(reversed(self.mgr.list() + self.cjobs.list()), key=lambda d: {"waiting": 0, "active": 1, "paused": 2, "queued": 3, "error": 4}.get(d.state, 5))
        act = [d for d in items if d.state == "active"]
        queued = sum(1 for d in items if d.state == "queued")
        waiting = sum(1 for d in items if d.state == "waiting")
        speed = sum(d.speed for d in act)
        y = self.n(30)
        self.text("Descargas", pad, self.cy(y), 40, TXT, True)
        # resumen: tres cifras sueltas, sin cajas
        sx = pad
        for big, small in ((str(len(act)), "activas"), (str(queued), "en cola"), (fmt_size(speed) + "/s", "ahora")) + (((str(waiting), "te esperan"),) if waiting else ()):
            r1 = self.text(big, sx, self.cy(y + self.n(70)), 26, ACC if big not in ("0", "0 B") and not big.startswith("0 B") else DIM, True)
            r2 = self.text(small, r1.right + self.n(8), self.cy(y + self.n(76)), 17, DIM)
            sx = r2.right + self.n(28)
        self.button("clear", (self.W - pad - self.n(260), y, self.n(260), self.n(72)), "LIMPIAR TERMINADAS", lambda: (self.mgr.clear_finished(), self.cjobs.clear_finished()), size=17, pill=True)
        self.button("addurl", (self.W - pad - self.n(260) - self.n(300), y, self.n(286), self.n(72)), "AÑADIR POR URL", self.add_url_osk, "primary", 17, pill=True)
        y += self.n(130)
        gap = self.n(22)
        cw = (self.W - 2 * pad - gap) // 2
        ch = self.n(214)
        cells, fin = [], []   # (callable que dibuja en x,y): en curso / terminadas

        for a in list(self.dlw.active.values()):
            cells.append(lambda x, yy, a=a: self.dl_card("bw:" + a["name"], x, yy, cw, ch, a["name"], f"{fmt_size(a['size'])}  ·  {fmt_size(a['speed'])}/s", TXT, 0.0,
                                                          "Navegador · el tamaño total lo sabe el navegador", kind="active", icon="down"))
        for d in self.dlw.recent[:3]:
            fin.append(lambda x, yy, d=d: self.dl_card("bdone:" + str(d["path"]), x, yy, cw, ch, d["name"], f"Terminada · {fmt_size(d['size'])}", OK, 1.0,
                                                          str(d["path"].parent) if hasattr(d["path"], "parent") else "", onmain=lambda d=d: self.toast(f"Está en {d['path']}"), kind="done"))
        for b in reversed(self.builds):
            def bc(x, yy, b=b):
                col = ERR if b.state == "error" else OK if b.state == "done" else TXT
                lab = "CANCELAR" if b.state in ("queued", "running") else "QUITAR"
                fr, est = b.progress() if hasattr(b, "progress") else (0.0, False)
                run = b.state in ("queued", "running")
                stg = b.stage + (f" · {int(fr * 100)} %" + (" (estimado)" if est else "") if run and fr else "") + (f" · lleva {b.elapsed_text()}" if run and hasattr(b, "elapsed_text") else "")
                return self.dl_card(f"bd:{b.id}", x, yy, cw, ch, getattr(b, "label", "COMPILACIÓN").capitalize() + " · " + b.title,
                                    stg + (f" — {b.error}" if b.error else ""), col, fr if run else 0.0, (list(b.log)[-1][:90] if b.log else ""),
                                    "REGISTRO", lambda b=b: self.show_log(b), lab, lambda b=b: self.build_x(b),
                                    "error" if b.state == "error" else "done" if b.state == "done" else "active", icon="gear" if b.state in ("queued", "running") else "")
            (fin if b.state == "done" else cells).append(bc)
        for d in items:
            def dc(x, yy, d=d):
                phase = d.meta.get("phase", "")
                kind = d.state
                if d.state == "active":
                    if d.size:
                        st = f"{d.progress * 100:.0f}%  ·  {fmt_size(d.speed)}/s  ·  quedan {fmt_eta(d.eta())}"
                        sub = f"{fmt_size(d.done)} de {fmt_size(d.size)}  ·  faltan {fmt_size(max(0, d.size - d.done))}"
                    else:
                        st = f"{fmt_size(d.speed)}/s" if d.speed else "Descargando…"
                        sub = f"{fmt_size(d.done)} descargados  ·  el tamaño total aún no se sabe" if d.done else "Esperando el primer dato del servidor"
                    col = TXT
                elif d.state == "waiting":
                    st, col, sub, kind = "Esperando tu intervención", WARN, (d.meta.get("message") or "Haz lo que pide el servicio y se reanuda solo")[:110], "paused"
                elif d.state == "queued":
                    st, col, sub = "En cola", DIM, ""
                elif d.state == "paused":
                    st, col, sub = f"Pausada al {d.progress * 100:.0f}%", WARN, ""
                elif d.state == "error":
                    st, col, sub = (d.error or "Error").splitlines()[0][:110], ERR, ""
                elif d.state == "cancelled":
                    st, col, sub, kind = "Cancelada", DIM, "", "queued"
                else:
                    st = phase or "Completa"
                    col = ERR if phase.startswith("Error") else OK
                    kind = "error" if phase.startswith("Error") else "done"
                    sub = "SHA-256 verificado" if d.verified else ""
                main = {"active": "PAUSAR", "queued": "PAUSAR", "paused": "REANUDAR", "error": "REINTENTAR", "cancelled": "REINTENTAR", "done": "VER"}.get(d.state, "")
                if getattr(d, "catalog", False) and d.state != "done":
                    main = ""
                lab = "QUITAR" if d.state in ("done", "cancelled", "error") else "CANCELAR"
                return self.dl_card(f"dl:{d.id}", x, yy, cw, ch, d.meta.get("title") or d.name or d.url, st, col, d.progress, sub,
                                    main, lambda d=d: self.dl_main(d), lab, lambda d=d: self.dl_cancel(d), kind)
            (fin if d.state in ("done", "cancelled") else cells).append(dc)

        mode = (SCREENS or {}).get("downloads")
        cw0, ch0 = cw, ch

        def grid(lst, title):
            nonlocal y, cw, ch
            if not lst:
                return
            self.text(title, pad + self.n(8), self.cy(y), 20, DIM, True)
            y += self.n(44)
            if mode in ("rows", "wide", "proc", "table"):   # v3.05 Minimal · v3.06 Flow · v3.07 Terminal · v3.08 Editorial (tabla)
                cw, ch = self.W - 2 * pad, self.n({"rows": 150, "wide": 196, "proc": 160, "table": 150}[mode])
                self._dl_bar = {"wide": "big", "proc": "ascii", "table": "thin"}.get(mode)
                for c in lst:
                    c(pad, y)
                    y += ch + gap
                cw, ch = cw0, ch0
                self._dl_bar = None
                return
            if mode == "featured" and title == "En curso":   # v3.05 Showcase: la primera, protagonista; el resto, debajo
                cw, ch = self.W - 2 * pad, self.n(270)
                self._dl_bar = "big"
                lst[0](pad, y)
                self._dl_bar = None
                y += ch + gap
                cw, ch = cw0, ch0
                lst = lst[1:]
            self._dl_bar = {"segments": "segments", "blocks": "block"}.get(mode)   # v3.07 Arcade: bloques · v3.08 Brutalist: indicador grueso
            if mode in ("segments", "blocks"):
                ch = self.n(240 if mode == "segments" else 260)                                            # un poco más alta: la barra no se pega al texto
            for i, c in enumerate(lst):
                c(pad + (i % 2) * (cw + gap), y + (i // 2) * (ch + gap))
            self._dl_bar = None
            y += ((len(lst) + 1) // 2) * (ch + gap)
            ch = ch0
        grid(cells, "En curso")
        grid(fin, "Terminadas")
        cells = cells + fin
        if self.recv:
            self.text("Recibidos por tu navegador", pad + self.n(8), self.cy(y), 20, DIM, True)
            y += self.n(44)
            rcells = []
            for r_ in self.recv:
                p = Path(r_["path"])
                ago = int((time.time() - r_["mtime"]) // 60)
                sub = f"{p.parent}  ·  hace {ago} min" if ago < 120 else str(p.parent)
                rcells.append(lambda x, yy, r_=r_, p=p, sub=sub: self.dl_card(f"rv:{p}", x, yy, cw, self.n(130), p.name, fmt_size(r_["size"]), DIM, 1.0, sub,
                                                                              onmain=lambda r_=r_: self.recv_open(r_), kind="done", icon="file"))
            for i, c in enumerate(rcells):
                c(pad + (i % 2) * (cw + gap), y + (i // 2) * (self.n(130) + gap))
            y += ((len(rcells) + 1) // 2) * (self.n(130) + gap)
        if not cells and not self.recv:
            self.text("Nada descargándose", self.W // 2, self.cy(y + self.n(80)), 32, TXT, True, anchor="mid")
            self.text("Elige un juego y pulsa Instalar, o añade un enlace con «Añadir por URL».", self.W // 2, self.cy(y + self.n(130)), 21, DIM, anchor="mid")
        self.cur.nh = max(self.cur.nh, y + self.n(20))
        self.end()
