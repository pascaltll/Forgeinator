"""Inicio con disposición propia por tema (v2.37). Cada tema elige cómo se representan «Tus juegos» con THEMES[...]["HOME"] (y HOMEV, la variante):
grid · hero (el de Prototipo) · posters · orbs · xmb · slots · coverflow · switch · list · blocks. Parte de la clase UI (ui.py la adopta, ver _adopt):
los métodos usan los mismos nombres globales que ui.py. Cada renderizador recibe `inst` = [(entrada, estado, hay_actualización, release)] y devuelve la y siguiente."""
# flake8: noqa: F821
import math
import re


class HomeLayoutsMixin:
    # ── utilidades comunes ───────────────────────────────────
    def _hl_grad(self, e, size):
        key = ("_hlg", e["name"], size)
        c = self._tc
        if key not in c:
            base = self.tint(e["name"])
            base = tuple(base) if base else ACC
            sur = pygame.Surface(size, pygame.SRCALPHA)
            for yy in range(size[1]):
                t = yy / max(1, size[1])
                pygame.draw.line(sur, (*[int(v * (0.95 - 0.35 * t)) for v in base], 255), (0, yy), (size[0], yy))
            c[key] = sur
        return c[key]

    def _hl_art(self, e, r, rad=14, circle=False):
        """Portada (o degradado del juego) recortada con esquinas redondas o en círculo; se guarda hecha."""
        size = (max(2, r.w), max(2, r.h))
        cov = self.cover(e, size)
        key = ("_hla", e["id"], size, int(rad), circle, cov is not None)
        c = self._tc
        if key not in c:
            sur = pygame.Surface(size, pygame.SRCALPHA)
            sur.blit(cov if cov is not None else self._hl_grad(e, size), (0, 0))
            m = pygame.Surface(size, pygame.SRCALPHA)
            if circle:
                pygame.draw.circle(m, (255, 255, 255, 255), (size[0] // 2, size[1] // 2), min(size) // 2)
            else:
                pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, *size), border_radius=int(rad))
            sur.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            c[key] = sur
        self.screen.blit(c[key], r.topleft)

    def _hl_reg(self, e, upd, rect):
        return self.reg(f"home:{e['id']}", rect, lambda e=e: self.play(e), True, None,
                        (lambda e=e: self.do_install(e)) if upd else None, lambda e=e: self.open_detail(e))

    def _hl_focus(self, r, foc, rad=22):
        if foc:
            self.glow(r)
            self.rr(r.inflate(self.n(10), self.n(10)), FOCUS or TXT, rad + 4, max(3, self.n(4)))

    def _hl_mark(self, r, upd, inside=14):
        cc = (r.right - self.n(inside + 12), r.y + self.n(inside + 12))
        pygame.draw.circle(self.screen, ACC if upd else OK, cc, self.n(inside))
        if upd:
            self.tri(cc[0], cc[1] - self.n(2), self.n(15), "up", ON_ACC)
            pygame.draw.rect(self.screen, ON_ACC, (cc[0] - self.n(3), cc[1] + self.n(1), self.n(6), self.n(7)))
        else:
            self.check(cc[0], cc[1], self.n(15), (10, 40, 22), 4)

    def _hl_band(self, size, bh, rad):
        """Degradado oscuro en la base de una tesela, con las esquinas de abajo redondeadas como la portada (se guarda hecho)."""
        key = ("_hlb", size, bh, int(rad))
        c = self._tc
        if key not in c:
            sur = pygame.Surface(size, pygame.SRCALPHA)
            for yy in range(bh):
                pygame.draw.line(sur, (0, 0, 0, int(200 * (yy / bh) ** 1.2)), (0, size[1] - bh + yy), (size[0], size[1] - bh + yy))
            m = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, *size), border_radius=int(rad))
            sur.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            c[key] = sur
        return c[key]

    @staticmethod
    def _hl_title(e):
        """Nombre del juego (diccionario) y no el del proyecto: «The Legend of Zelda: Ocarina of Time» en vez de «Ship of Harkinian»."""
        return gamedict.game_name(e) or e["name"]

    @staticmethod
    def _hl_plat(e):
        t = (esde.system_for(e.get("platform") or "") or (e.get("platform") or "")).upper()
        t = re.sub(r"PLAYSTATION\s*PORTABLE", "PSP", t)
        t = re.sub(r"PLAYSTATION\s*(\d)", r"PS\1", t)
        return t.replace("PLAYSTATION", "PS1")[:10]

    def _hl_start(self, inst):
        """Índice del juego en foco (o el último jugado, o el primero): las disposiciones que se desplazan se centran en él."""
        f = self.focus or ""
        for k, t in enumerate(inst):
            if f == f"home:{t[0]['id']}":
                return k
        lp = (self.cfg.get("last_played") or {}).get("id")
        return next((k for k, t in enumerate(inst) if t[0]["id"] == lp), 0)

    @staticmethod
    def _hl_roman(n):
        out = ""
        for v, s in ((40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
            while n >= v:
                out += s
                n -= v
        return out

    def _hl_leader(self, x1, x2, y, col):
        step = self.n(11)
        for x in range(int(x1), int(x2), step):
            pygame.draw.circle(self.screen, col, (x, int(y)), max(1, self.n(1.6)))

    # ── despachador ──────────────────────────────────────────
    def _home_custom(self, inst, pad, gap, y):
        v = HOMEV
        fn = {"posters": lambda: self._home_posters(inst, pad, gap, y, shelf=(v == "shelf")),
              "orbs": lambda: self._home_orbs(inst, pad, gap, y, glow=(v == "glow")),
              "mosaic": lambda: self._home_mosaic(inst, pad, gap, y),
              "xmb": lambda: self._home_xmb(inst, pad, gap, y),
              "slots": lambda: self._home_slots(inst, pad, gap, y, v or "card"),
              "coverflow": lambda: self._home_coverflow(inst, pad, gap, y),
              "switch": lambda: self._home_switch(inst, pad, gap, y),
              "list": lambda: self._home_grouped(inst, pad, gap, y) if v == "score" else self._home_list(inst, pad, gap, y, v or "dock"),
              "blocks": lambda: self._home_blocks(inst, pad, gap, y)}.get(HOME)
        return fn() if fn else y

    # ── posters: portadas verticales con el nombre debajo (shelf = con balda) ──
    def _home_posters(self, inst, pad, gap, y, shelf=False):
        cols = 5 if self.W < self.n(2000) else 7
        cw = (self.W - 2 * pad - (cols - 1) * gap) // cols
        ch, lh = int(cw * 1.45), self.n(70)
        rad = int(12 * RADK * self.k)
        for k, (e, i, upd, rel) in enumerate(inst):
            r, foc = self._hl_reg(e, upd, (pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + lh + gap), cw, ch))
            if self.offscreen(r):
                continue
            self._hl_art(e, r, rad)
            if OUTLINE:
                self.rr(r, LINE, 12 * RADK, max(1, self.n(2)))
            self._hl_mark(r, upd, 11)
            self._hl_focus(r, foc, 14)
            self.para(self._hl_title(e), r.x + self.n(2), r.bottom + self.n(8), 19, r.w, TXT, True, 2)
        rows = -(-len(inst) // cols)
        if shelf:
            for rw in range(rows):
                by = y + rw * (ch + lh + gap) + ch + lh - self.n(4)
                bar = pygame.Rect(pad - self.n(14), self.cy(by), self.W - 2 * pad + self.n(28), self.n(9))
                pygame.draw.rect(self.screen, LINE, bar, border_radius=self.n(3))
                pygame.draw.rect(self.screen, ACC, (bar.x, bar.y, bar.w, max(2, self.n(2))), border_radius=self.n(2))
        return y + rows * (ch + lh + gap)

    # ── orbs: burbujas redondas ──────────────────────────────
    def _home_orbs(self, inst, pad, gap, y, glow=False):
        d = self.n(176)
        cols = max(1, (self.W - 2 * pad + gap) // (d + gap))
        cell_w = (self.W - 2 * pad - (cols - 1) * gap) / cols
        lh = self.n(70)
        for k, (e, i, upd, rel) in enumerate(inst):
            cx0 = pad + (k % cols) * (cell_w + gap) + cell_w / 2
            r, foc = self._hl_reg(e, upd, (int(cx0 - d / 2), y + (k // cols) * (d + lh + gap), d, d))
            if self.offscreen(r):
                continue
            if glow:
                self.glow(r.inflate(self.n(30), self.n(30)))
            self._hl_art(e, r, circle=True)
            pygame.draw.circle(self.screen, ACC if glow else LINE, r.center, d // 2 + self.n(3), max(2, self.n(4 if glow else 3)))
            self._hl_mark(r.inflate(-self.n(30), -self.n(30)), upd, 11)
            if foc:
                pygame.draw.circle(self.screen, FOCUS or TXT, r.center, d // 2 + self.n(10), max(3, self.n(4)))
            self.text(self._hl_title(e), r.centerx, r.bottom + self.n(24), 19, TXT, True, int(cell_w) - self.n(8), "c")
        rows = -(-len(inst) // cols)
        return y + rows * (d + lh + gap)

    # ── xmb: fila de portadas verticales que se desplaza; la enfocada crece y muestra su nombre ──
    def _home_xmb(self, inst, pad, gap, y):
        f = self._hl_start(inst)
        sh, bigh, step = self.n(180), self.n(262), self.n(138)
        sw, bigw = int(sh * 0.7), int(bigh * 0.7)
        ax, cy = int(self.W * 0.28), y + self.n(146)
        rad = int(16 * RADK * self.k)
        for k, (e, i, upd, rel) in enumerate(inst):
            dx = (k - f) * step
            dx += (bigw - sw) // 2 + self.n(26) if k > f else -((bigw - sw) // 2 + self.n(26)) if k < f else 0
            w_, h_ = (bigw, bigh) if k == f else (sw, sh)
            r, foc = self._hl_reg(e, upd, (ax + dx - w_ // 2, cy - h_ // 2, w_, h_))
            if r.right < -self.n(40) or r.x > self.W + self.n(40):
                continue
            self._hl_art(e, r, rad)
            self.rr(r, ACC if k == f else LINE, 16 * RADK, max(2, self.n(3 if k == f else 2)))
            if k == f:
                self.glow(r)
                self._hl_mark(r, upd, 12)
                self.text(self._hl_title(e), r.x, r.bottom + self.n(14), 30, TXT, True, self.W - r.x - self.n(40))
                self.text((self._hl_plat(e) + ("  ·  actualización " + rel["tag"] if upd else "  ·  A para jugar")).strip(), r.x, r.bottom + self.n(54), 18, DIM)
        return y + self.n(370)

    # ── slots: casillas densas numeradas (tarjeta de memoria / niveles / cartuchos) ──
    def _home_slots(self, inst, pad, gap, y, v="card"):
        cols = 7 if self.W < self.n(2000) else 9
        g = self.n(16)
        cw = (self.W - 2 * pad - (cols - 1) * g) // cols
        ch = int(cw * (1.5 if v == "cart" else 1.42))
        lh = self.n(66)
        rad = 0 if v in ("level", "cart") else int(10 * RADK * self.k)
        for k, (e, i, upd, rel) in enumerate(inst):
            r, foc = self._hl_reg(e, upd, (pad + (k % cols) * (cw + g), y + (k // cols) * (ch + lh + g), cw, ch))
            if self.offscreen(r):
                continue
            pygame.draw.rect(self.screen, PANEL2, r, border_radius=rad)
            ins = r.inflate(-self.n(14), -self.n(14))
            if v == "cart":
                ins = pygame.Rect(ins.x, ins.y + self.n(30), ins.w, ins.h - self.n(30))
            self._hl_art(e, ins, max(0, rad - 4))
            pygame.draw.rect(self.screen, LINE, r, max(2, self.n(4 if v == "level" else 3 if v == "cart" else 2)), border_radius=rad)
            if v == "card":
                n_ = self.n(18)                       # esquina cortada, como una tarjeta de memoria
                pygame.draw.polygon(self.screen, BG, [(r.right - n_, r.y), (r.right, r.y), (r.right, r.y + n_)])
                pygame.draw.line(self.screen, LINE, (r.right - n_, r.y), (r.right, r.y + n_), max(2, self.n(2)))
            lab = {"card": f"SLOT {k + 1:02d}", "level": f"NIVEL {k + 1}", "cart": f"{k + 1:02d}"}[v]
            self.text(lab, r.x + self.n(10), r.y + (self.n(18) if v == "cart" else self.n(8)), 15, ACC, True, anchor="ml" if v == "cart" else "tl")
            self._hl_mark(r, upd, 9)
            self._hl_focus(r, foc, 12)
            self.text(self._hl_title(e), r.x + self.n(2), r.bottom + self.n(10), 17, TXT, True, r.w - self.n(4))
            self.text(self._hl_plat(e), r.x + self.n(2), r.bottom + self.n(34), 14, DIM, False, r.w - self.n(4))
        rows = -(-len(inst) // cols)
        return y + rows * (ch + lh + g)

    # ── coverflow: carátula central grande y las demás se alejan a los lados ──
    def _home_coverflow(self, inst, pad, gap, y):
        f = self._hl_start(inst)
        cw, chh = self.n(262), self.n(344)
        sw, sh = self.n(184), self.n(240)
        cx, cy = self.W // 2, y + self.n(210)
        rad = int(14 * RADK * self.k)
        for dist, k in sorted(((abs(k - f), k) for k in range(len(inst))), reverse=True):
            e, i, upd, rel = inst[k]
            d = k - f
            w, h = (cw, chh) if d == 0 else (sw, sh)
            x = cx + (0 if d == 0 else (1 if d > 0 else -1) * (self.n(196) + (abs(d) - 1) * self.n(150)))
            r, foc = self._hl_reg(e, upd, (x - w // 2, cy - h // 2, w, h))
            if r.right < -self.n(40) or r.x > self.W + self.n(40):
                continue
            self._hl_art(e, r, rad)
            self.rr(r, ACC if d == 0 else LINE, 14 * RADK, max(2, self.n(4 if d == 0 else 2)))
            if d == 0:
                self.glow(r)
                self._hl_mark(r, upd, 12)
                self.text(self._hl_title(e), cx, r.bottom + self.n(30), 30, TXT, True, self.W - 2 * pad, "c")
                self.text(self._hl_plat(e) + ("  ·  actualización " + rel["tag"] if upd else ""), cx, r.bottom + self.n(66), 18, DIM, False, None, "c")
        return y + self.n(470)

    # ── switch: portadas altas sobre una repisa; la enfocada se eleva, con su ficha de plataforma y sombra ──
    def _home_switch(self, inst, pad, gap, y):
        w_, h_ = self.n(200), self.n(284)
        cols = max(1, (self.W - 2 * pad + gap) // (w_ + gap))
        lh = self.n(78)
        rad = int(22 * RADK * self.k)
        lift = self.n(14)
        for k, (e, i, upd, rel) in enumerate(inst):
            x = pad + (k % cols) * (w_ + gap)
            yy = y + lift + (k // cols) * (h_ + lh + gap)
            r, foc = self._hl_reg(e, upd, (x, yy, w_, h_))
            if self.offscreen(r):
                continue
            d = r.move(0, -lift) if foc else r
            sh = d.move(self.n(2), self.n(10 if foc else 6)).inflate(-self.n(6), 0)
            pygame.draw.rect(self.screen, tuple(int(c * (0.70 if foc else 0.82)) for c in BG), sh, border_radius=rad)
            self._hl_art(e, d, rad)
            plat = self._hl_plat(e)
            if plat:
                pw = self.font(15, True).size(plat)[0] + self.n(18)
                chip = pygame.Rect(d.x + self.n(10), d.bottom - self.n(36), pw, self.n(26))
                pygame.draw.rect(self.screen, (0, 0, 0), chip, border_radius=self.n(13))
                self.text(plat, chip.centerx, chip.centery, 15, (255, 255, 255), True, anchor="c")
            self._hl_mark(d, upd, 12)
            if foc:
                pygame.draw.rect(self.screen, FOCUS or ACC, d.inflate(self.n(12), self.n(12)), max(4, self.n(6)), border_radius=rad + 4)
            ty = r.bottom + self.n(14)
            self.para(self._hl_title(e), r.x + self.n(4), ty, 20, r.w - self.n(8), TXT, True, 2)
        rows = -(-len(inst) // cols)
        return y + lift + rows * (h_ + lh + gap)

    # ── list: filas. dock (Quiver) · term (Fósforo) · score (Neón) · index (Tinta) ──
    def _home_list(self, inst, pad, gap, y, v="dock"):
        rh = {"dock": 80, "term": 56, "score": 84, "index": 66}.get(v, 80)
        rh = self.n(rh)
        w = self.W - 2 * pad
        for k, (e, i, upd, rel) in enumerate(inst):
            r, foc = self._hl_reg(e, upd, (pad, y + k * (rh + self.n(8)), w, rh))
            if self.offscreen(r):
                continue
            plat = self._hl_plat(e)
            tail = ("↑ " + rel["tag"] + "  " if upd else "") + plat
            if v == "dock":
                self.rr(r, PANEL2 if foc else PANEL, 14 * RADK)
                if OUTLINE:
                    self.rr(r, LINE, 14 * RADK, max(1, self.n(2)))
                th = pygame.Rect(r.x + self.n(12), r.y + self.n(10), rh - self.n(20), rh - self.n(20))
                self._hl_art(e, th, int(8 * RADK * self.k))
                self.text(self._hl_title(e), th.right + self.n(18), r.centery, 24, TXT, True, w - self.n(300), "ml")
                self.text(tail, r.right - self.n(54), r.centery, 17, DIM, False, self.n(240), "mr")
                self.chevron(r.right - self.n(30), r.centery, self.n(11), DIM, "right", 3)
                self._hl_focus(r, foc, 14)
            elif v == "term":
                if foc:
                    pygame.draw.rect(self.screen, ACC, r)
                col = ON_ACC if foc else TXT
                self.text(f"{'>' if foc else ' '} {k + 1:02d}  {self._hl_title(e).upper()}", r.x + self.n(12), r.centery, 22, col, True, w - self.n(260), "ml")
                self.text(f"[{tail}]", r.right - self.n(12), r.centery, 20, ON_ACC if foc else DIM, False, self.n(300), "mr")
                if not foc:
                    self._hl_leader(r.x + self.n(24) + self.font(22, True).size(f"  {k + 1:02d}  {self._hl_title(e).upper()}")[0] + self.n(14),
                                    r.right - self.n(24) - self.font(20).size(f"[{tail}]")[0], r.centery + self.n(6), LINE)
            elif v == "score":
                self.rr(r, PANEL2 if foc else PANEL, 14 * RADK)
                self.rr(r, ACC if foc else LINE, 14 * RADK, max(2, self.n(3 if foc else 2)))
                self.text(f"{k + 1:02d}", r.x + self.n(28), r.centery, 40, ACC, True, anchor="ml")
                self.text(self._hl_title(e).upper(), r.x + self.n(120), r.centery, 28, TXT, True, w - self.n(430), "ml")
                self.text(tail, r.right - self.n(30), r.centery, 20, ACC if upd else DIM, True, self.n(260), "mr")
                if foc:
                    self.glow(r)
            else:  # index (Tinta)
                num = self._hl_roman(k + 1) + "."
                self.text(num, r.x + self.n(8), r.centery, 24, ACC if foc else DIM, False, self.n(80), "ml")
                nx = r.x + self.n(96)
                self.text(self._hl_title(e), nx, r.centery, 30, TXT, foc, w - self.n(380), "ml")
                tw_ = self.font(30, foc).size(self._hl_title(e))[0]
                pw_ = self.font(20).size(tail)[0]
                self._hl_leader(nx + min(tw_, w - self.n(380)) + self.n(14), r.right - pw_ - self.n(24), r.centery + self.n(10), LINE)
                self.text(tail, r.right - self.n(8), r.centery, 20, ACC if upd else DIM, False, self.n(300), "mr")
                pygame.draw.line(self.screen, ACC if foc else LINE, (r.x, r.bottom), (r.right, r.bottom), max(1, self.n(3 if foc else 1)))
                if foc:
                    self.tri(r.x - self.n(6), r.centery, self.n(16), "right", ACC)
        return y + len(inst) * (rh + self.n(8)) + self.n(8)

    # ── blocks: bloques brutalistas con número gigante ──
    def _home_blocks(self, inst, pad, gap, y):
        cols = 2
        cw = (self.W - 2 * pad - gap) // cols
        ch = self.n(196)
        for k, (e, i, upd, rel) in enumerate(inst):
            r, foc = self._hl_reg(e, upd, (pad + (k % cols) * (cw + gap), y + (k // cols) * (ch + gap), cw, ch))
            if self.offscreen(r):
                continue
            pygame.draw.rect(self.screen, ACC if foc else PANEL, r)
            col = ON_ACC if foc else TXT
            self.text(f"{k + 1:02d}", r.x + self.n(24), r.y + self.n(14), 84, col, True)
            th = pygame.Rect(r.right - self.n(170), r.y + self.n(18), self.n(150), r.h - self.n(36))
            self._hl_art(e, th, 0)
            pygame.draw.rect(self.screen, LINE, th, max(3, self.n(4)))
            self.para(self._hl_title(e), r.x + self.n(24), r.y + self.n(112), 26, r.w - self.n(230), col, True, 2)
            pw = self.font(16, True).size(self._hl_plat(e) or "—")[0] + self.n(20)
            tag = pygame.Rect(r.x + self.n(24 + 110), r.y + self.n(30), pw, self.n(30))
            pygame.draw.rect(self.screen, LINE, tag)
            self.text(self._hl_plat(e) or "—", tag.centerx, tag.centery, 16, BG if sum(LINE) < 200 else TXT, True, anchor="c")
            pygame.draw.rect(self.screen, LINE, r, max(4, self.n(6)))
            if foc:
                pygame.draw.rect(self.screen, FOCUS or TXT, r.inflate(self.n(14), self.n(14)), max(3, self.n(4)))
        rows = -(-len(inst) // cols)
        return y + rows * (ch + gap)

    # ── mosaic: bento de cristal — el último juego en grande y el resto en teselas altas ──
    def _home_mosaic(self, inst, pad, gap, y):
        cols = 6 if self.W < self.n(2000) else 8
        u = (self.W - 2 * pad - (cols - 1) * gap) // cols
        uh = int(u * 1.3)
        lp = (self.cfg.get("last_played") or {}).get("id")
        bi = next((k for k, t in enumerate(inst) if t[0]["id"] == lp), 0)
        order = [bi] + [k for k in range(len(inst)) if k != bi]
        bw, bh = (3, 2) if len(inst) > 1 else (2, 2)
        occ = set()
        pos = {}
        for n_, k in enumerate(order):
            w_, h_ = (bw, bh) if n_ == 0 else (1, 1)
            r_ = 0
            while k not in pos:
                for c_ in range(cols - w_ + 1):
                    cells = {(r_ + a, c_ + b) for a in range(h_) for b in range(w_)}
                    if not cells & occ:
                        occ |= cells
                        pos[k] = (c_, r_, w_, h_)
                        break
                r_ += 1
        rad = int(18 * RADK * self.k)
        bottom = 0
        for k, (e, i, upd, rel) in enumerate(inst):
            c_, r_, w_, h_ = pos[k]
            rect = (pad + c_ * (u + gap), y + r_ * (uh + gap), w_ * u + (w_ - 1) * gap, h_ * uh + (h_ - 1) * gap)
            r, foc = self._hl_reg(e, upd, rect)
            bottom = max(bottom, rect[1] + rect[3])          # coordenadas de contenido (r ya está desplazado por el scroll)
            if self.offscreen(r):
                continue
            self._hl_art(e, r, rad)
            self.screen.blit(self._hl_band(r.size, self.n(110 if w_ > 1 else 78), rad), r.topleft)
            pygame.draw.rect(self.screen, LINE, r, max(1, self.n(2)), border_radius=rad)
            self._hl_mark(r, upd, 11 if w_ == 1 else 14)
            if w_ > 1:
                self.text(self._hl_title(e), r.x + self.n(22), r.bottom - self.n(88), 34, (255, 255, 255), True, r.w - self.n(44))
                self.text((self._hl_plat(e) + ("  ·  actualización " + rel["tag"] if upd else "  ·  A para jugar")).strip(), r.x + self.n(22), r.bottom - self.n(40), 18, (225, 225, 235), False, r.w - self.n(44))
            else:
                self.para(self._hl_title(e), r.x + self.n(10), r.bottom - self.n(58), 17, r.w - self.n(20), (255, 255, 255), True, 2)
            self._hl_focus(r, foc, 18)
        return max(bottom, y) + gap + self.n(10)

    # ── grouped: lista numerada con cabecera por plataforma (Neón) ──
    def _home_grouped(self, inst, pad, gap, y):
        groups = {}
        for t in inst:
            groups.setdefault(self._hl_plat(t[0]) or "OTROS", []).append(t)
        rh, hh = self.n(76), self.n(58)
        w = self.W - 2 * pad
        yy = y
        for plat, items in sorted(groups.items()):
            self.text(plat, pad + self.n(6), self.cy(yy) + hh // 2, 30, ACC, True, anchor="ml")
            tw_ = self.font(30, True).size(plat)[0]
            pygame.draw.line(self.screen, LINE, (pad + tw_ + self.n(28), self.cy(yy) + hh // 2), (pad + w - self.n(70), self.cy(yy) + hh // 2), max(2, self.n(3)))
            self.text(str(len(items)), pad + w - self.n(6), self.cy(yy) + hh // 2, 24, DIM, True, anchor="mr")
            yy += hh
            for k, (e, i, upd, rel) in enumerate(items):
                r, foc = self._hl_reg(e, upd, (pad, yy, w, rh))
                yy += rh + self.n(8)
                if self.offscreen(r):
                    continue
                self.rr(r, PANEL2 if foc else PANEL, 14 * RADK)
                self.rr(r, ACC if foc else LINE, 14 * RADK, max(2, self.n(3 if foc else 2)))
                self.text(f"{k + 1:02d}", r.x + self.n(26), r.centery, 34, ACC, True, anchor="ml")
                self.text(self._hl_title(e).upper(), r.x + self.n(100), r.centery, 26, TXT, True, w - self.n(400), "ml")
                self.text(("↑ " + rel["tag"]) if upd else (e["name"] if e["name"] != self._hl_title(e) else ""), r.right - self.n(30), r.centery, 20, ACC if upd else DIM, bool(upd), self.n(420), "mr")
                if foc:
                    self.glow(r)
            yy += self.n(10)
        return yy
