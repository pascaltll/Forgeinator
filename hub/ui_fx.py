"""Efectos de la interfaz (v2.32): fondo animado por tema, destello al pulsar, halo del foco y salto del icono al cambiar de sección.
Todo es barato a propósito (copias pequeñas ya preparadas; nada por píxel) y se apaga con EFECTOS: RENDIMIENTO. Parte de la clase UI."""
# flake8: noqa: F821
import math
import random


class FxMixin:
    # ── fondo animado ────────────────────────────────────────
    def _soft_dot(self, rad, col, peak):
        sm = pygame.Surface((rad * 4, rad * 4), pygame.SRCALPHA)
        for k in range(rad * 2, 0, -1):
            pygame.draw.circle(sm, (*col, int(peak * (1 - k / (rad * 2)) ** 2)), (rad * 2, rad * 2), k)
        return sm

    def _big_glow(self, col, d, peak=72):
        sm = pygame.Surface((64, 64), pygame.SRCALPHA)
        for r in range(32, 0, -1):
            pygame.draw.circle(sm, (*col, int(peak * (1 - r / 32) ** 1.7)), (32, 32), r)
        return pygame.transform.smoothscale(sm, (int(d * 1.5), d))

    def draw_anim(self):
        """aurora/drift = luces grandes que derivan · stars = estrellas que parpadean · embers = ascuas que suben · motes = motas que flotan
        gridrun = la rejilla avanza hacia ti · scanbar = barrido de tubo · shapes = figuras que cruzan."""
        W, H, t = self.W, self.H, time.time()
        # v3.09: factores del tema (identidades del Estudio). Los heredados no traen MOTION: 1, 1, 1 y se dibujan exactamente como antes.
        mo = MOTION or {}
        spd, ik, dn = float(mo.get("speed", 1.0)), float(mo.get("intensity", 1.0)), float(mo.get("density", 1.0))
        fk = min(1.0, ik)                       # en mezclas de color no se pasa del color pleno
        if spd != 1.0:
            t *= spd

        def cnt(n):
            return n if dn == 1.0 else max(1, int(round(n * dn)))
        st = self.__dict__.get("_anim")
        key = (ANIM, W, H, ACC, BG, spd, ik, dn)
        if not st or st["key"] != key:
            rnd = random.Random(7)
            st = self._anim = {"key": key, "p": [(rnd.random(), rnd.random(), rnd.random(), rnd.random()) for _ in range(70)], "spr": {}}
            sp = st["spr"]
            if ANIM == "aurora":
                for i, col in enumerate(((40, 230, 160), (120, 90, 255), (40, 170, 230))):
                    sp[i] = self._big_glow(col, int(H * (0.9 + 0.15 * i)))
            elif ANIM == "drift":
                cols = [o[3] for o in (ORBS or ())][:3] or [ACC]
                for i, col in enumerate(cols + [ACC]):
                    sp[i] = self._big_glow(col, int(H * (0.7 + 0.12 * i)), 46)
            elif ANIM == "embers":
                for i, rad in enumerate((3, 5, 8)):
                    sp[i] = self._soft_dot(max(2, self.n(rad)), (255, 140 + 30 * i, 40), 120)
            elif ANIM == "motes":
                light = sum(BG) > 380
                col = tuple(int(a * 0.5 + b * 0.5) for a, b in zip(ACC, TXT)) if not light else tuple(int(c * 0.6) for c in ACC)
                for i, rad in enumerate((4, 7, 11)):
                    sp[i] = self._soft_dot(max(2, self.n(rad)), col, 70 if not light else 46)
            elif ANIM == "scanbar":
                bh = max(8, H // 5)
                b = pygame.Surface((W, bh), pygame.SRCALPHA)
                for y in range(bh):
                    pygame.draw.line(b, (*ACC, int(26 * math.sin(math.pi * y / bh) ** 2)), (0, y), (W, y))
                sp[0] = b
        sp, P = st["spr"], st["p"]
        if ANIM in ("aurora", "drift"):
            for i, s in sp.items():
                x = W * (0.5 + 0.42 * math.sin(t * 0.07 * (i + 1) + i * 2.1)) - s.get_width() / 2
                y = H * (0.25 + 0.2 * math.sin(t * 0.05 * (i + 2) + i) + (0.35 if ANIM == "drift" and i % 2 else 0)) - s.get_height() / 2
                if ik != 1.0:
                    s.set_alpha(min(255, int(255 * ik)))
                self.screen.blit(s, (int(x), int(y)))
        elif ANIM == "stars":
            for i, (a, b, c, d) in enumerate(P[:cnt(len(P))]):
                k = 0.5 + 0.5 * math.sin(t * (0.6 + 2.2 * c) + d * 6.28)
                s = max(2, self.n(2 + 3 * (i % 3 == 0)))
                v = int(70 + 185 * k)
                col = (v, v, min(255, v + 40)) if i % 7 else ACC
                if fk != 1.0:
                    col = tuple(int(bb + (cc - bb) * fk) for bb, cc in zip(BG, col))
                pygame.draw.rect(self.screen, col, (int(a * W), int(b * H), s, s))
        elif ANIM in ("embers", "motes"):
            n, sp_k, sway = (46, 1.0, 26) if ANIM == "embers" else (34, 0.35, 40)
            for i, (a, b, c, d) in enumerate(P[:cnt(n)]):
                life = (t * (0.03 + 0.05 * c) * sp_k + b) % 1.0
                x = W * a + self.n(sway) * math.sin(t * (0.5 + c) * sp_k + d * 6.28)
                s = sp[i % 3]
                s.set_alpha(min(255, int(255 * math.sin(math.pi * life) * (0.35 + 0.65 * d) * ik)) if ik != 1.0 else
                            int(255 * math.sin(math.pi * life) * (0.35 + 0.65 * d)))
                self.screen.blit(s, (int(x), int(H * (1.05 - 1.1 * life))))
        elif ANIM == "gridrun":
            hz = int(H * 0.60)
            for i in range(9):
                f = ((i / 9.0) + t * 0.11) % 1.0
                y = hz + int((H - hz) * f ** 2.3)
                col = tuple(int(b + (l - b) * (0.25 + 0.75 * f) * fk) for b, l in zip(BG, LINE)) if fk != 1.0 else \
                    tuple(int(b + (l - b) * (0.25 + 0.75 * f)) for b, l in zip(BG, LINE))
                pygame.draw.line(self.screen, col, (0, y), (W, y), max(1, self.n(2)))
            k = (0.6 + 0.4 * math.sin(t * 1.3)) * fk
            pygame.draw.line(self.screen, tuple(int(b + (a - b) * k) for b, a in zip(BG, ACC)), (0, hz), (W, hz), max(2, self.n(3)))
        elif ANIM == "scanbar":
            b = sp[0]
            if ik != 1.0:
                b.set_alpha(min(255, int(255 * ik)))
            self.screen.blit(b, (0, int((t * 0.12 % 1.0) * (H + b.get_height())) - b.get_height()))
        elif ANIM == "silk":                       # cintas de seda: varias líneas finas por cinta, desfasadas, que ondulan
            wv = max(2, self.n(2))
            for i in range(4):
                base = H * (0.50 + 0.10 * i)
                amp = H * (0.05 + 0.012 * i)
                for j in range(cnt(6)):
                    k = (0.10 + 0.07 * (j / 5.0) + 0.03 * i) * fk
                    col = tuple(int(b + (a - b) * k) for b, a in zip(BG, ACC))
                    pts = [(x, int(base + amp * math.sin(x / W * (5.0 + i) + t * (0.35 + 0.08 * i) + j * 0.22) + 0.6 * amp * math.sin(x / W * 11 - t * 0.2 + i)))
                           for x in range(0, W + 1, max(8, W // 40))]
                    pygame.draw.lines(self.screen, col, False, pts, wv)
        elif ANIM == "cubes":                      # cubos de contorno que suben despacio (dos cuadrados desplazados dan el volumen)
            for i, (a, b, c, d) in enumerate(P[:cnt(26)]):
                life = (t * (0.02 + 0.04 * c) + b) % 1.0
                sz = self.n(14 + 46 * c)
                x = int(W * a + self.n(14) * math.sin(t * (0.4 + c) + d * 6.28))
                y = int(H * (1.05 - 1.1 * life))
                k = (0.18 + 0.5 * d) * math.sin(math.pi * life) * fk
                col = tuple(int(bb + (aa - bb) * k) for bb, aa in zip(BG, ACC))
                w = max(1, self.n(2))
                o = max(2, sz // 4)
                pygame.draw.rect(self.screen, col, (x, y, sz, sz), w)
                pygame.draw.rect(self.screen, col, (x + o, y - o, sz, sz), w)
                for dx, dy in ((0, 0), (sz, 0), (0, sz), (sz, sz)):
                    pygame.draw.line(self.screen, col, (x + dx, y + dy), (x + dx + o, y + dy - o), w)
        elif ANIM == "spincube":                   # un cubo de líneas que gira despacio a la derecha
            cx, cy, R = int(W * 0.78), int(H * 0.5), H * 0.30
            ay, ax = t * 0.35, 0.45 + 0.25 * math.sin(t * 0.21)
            vs = []
            for sx in (-1, 1):
                for sy in (-1, 1):
                    for sz in (-1, 1):
                        x1, z1 = sx * math.cos(ay) - sz * math.sin(ay), sx * math.sin(ay) + sz * math.cos(ay)
                        y1, z2 = sy * math.cos(ax) - z1 * math.sin(ax), sy * math.sin(ax) + z1 * math.cos(ax)
                        f = 3.2 / (3.2 + z2 * 0.5)
                        vs.append((cx + int(x1 * R * 0.5 * f), cy + int(y1 * R * 0.5 * f)))
            col = tuple(int(b + (a - b) * 0.30 * fk) for b, a in zip(BG, ACC))
            col2 = tuple(int(b + (a - b) * 0.14 * fk) for b, a in zip(BG, ACC))
            for i in range(8):
                for j in range(i + 1, 8):
                    if bin(i ^ j).count("1") == 1:
                        pygame.draw.line(self.screen, col if (i ^ j) != 2 else col2, vs[i], vs[j], max(2, self.n(3)))
        elif ANIM == "diag":                       # bandas diagonales que desfilan (trama cacheada y desplazada: cuesta un blit)
            per = max(40, self.n(120))
            if "diag" not in sp:
                sf = pygame.Surface((W + 2 * per, H), pygame.SRCALPHA)
                col = (*LINE, min(255, int(26 * ik)))
                for x in range(-H, W + 2 * per, per):
                    pygame.draw.polygon(sf, col, [(x, H), (x + per // 2, H), (x + per // 2 + H, 0), (x + H, 0)])
                sp["diag"] = sf
            self.screen.blit(sp["diag"], (-int((t * 18) % per), 0))
        elif ANIM == "shapes":
            col = tuple(int(b + (l - b) * 0.16 * fk) for b, l in zip(BG, LINE))
            w = max(2, self.n(4))
            for i, (a, b, c, d) in enumerate(P[:cnt(7)]):
                sz = self.n(90 + 160 * c)
                x = int(((a + t * 0.012 * (0.5 + d)) % 1.2 - 0.1) * W)
                y = int(((b + t * 0.008 * (0.5 + c) * (1 if i % 2 else -1)) % 1.2 - 0.1) * H)
                if i % 3 == 0:
                    pygame.draw.circle(self.screen, col, (x, y), sz // 2, w)
                elif i % 3 == 1:
                    pygame.draw.rect(self.screen, col, (x - sz // 2, y - sz // 2, sz, sz), w)
                else:
                    pygame.draw.polygon(self.screen, col, [(x, y - sz // 2), (x + sz // 2, y + sz // 2), (x - sz // 2, y + sz // 2)], w)

    # ── al pulsar ────────────────────────────────────────────
    def fire(self, w):
        """Ejecuta la acción de un control y deja un destello donde estaba (onda + chispas del color del tema)."""
        try:
            if self.fx_level() >= 2 and not self.reduced_motion() and getattr(w, "rect", None) is not None:   # v3.09: solo calidad alta
                rnd = random.Random()
                r = pygame.Rect(w.rect)
                self.__dict__.setdefault("_bursts", []).append(
                    {"t": time.time(), "r": r, "p": [(rnd.uniform(0, 6.283), rnd.uniform(0.5, 1.0), rnd.random()) for _ in range(12)]})
                del self._bursts[:-6]
        except Exception:  # noqa: BLE001  (un efecto nunca impide la acción)
            pass
        return w.cb()

    # ── fundido entre temas ──────────────────────────────────
    def _xfade_start(self):
        """Guarda lo que hay en pantalla; draw_fx lo funde hacia el tema nuevo en ~0,35 s (nunca con «rendimiento»)."""
        try:
            if self.cfg.get("fx") != "perf" and not self.reduced_motion() and self.screen is not None:
                self.__dict__["_xfade"] = (self.screen.copy(), time.time())
        except Exception:  # noqa: BLE001
            self.__dict__.pop("_xfade", None)

    def _draw_xfade(self):
        xf = self.__dict__.get("_xfade")
        if not xf:
            return
        img, t0 = xf
        f = (time.time() - t0) / 0.35
        if f >= 1 or self.cfg.get("fx") == "perf" or img.get_size() != self.screen.get_size():
            self.__dict__.pop("_xfade", None)
            return
        img.set_alpha(int(255 * (1 - f) ** 1.6))
        self.screen.set_clip(None)
        self.screen.blit(img, (0, 0))

    def draw_fx(self):
        self._draw_xfade()
        bs = self.__dict__.get("_bursts")
        if not bs:
            return
        now, D = time.time(), 0.42
        bs[:] = [b for b in bs if now - b["t"] < D]
        if self.cfg.get("fx") == "perf" or self.fx_level() < 2 or self.reduced_motion():
            bs.clear()
            return
        self.screen.set_clip(None)
        col = FOCUS or ACC
        for b in bs:
            f = (now - b["t"]) / D
            e = 1 - (1 - f) ** 3                                  # sale rápido y frena
            r = b["r"]
            g = int(self.n(26) * e)
            ring = pygame.Surface((r.w + 2 * g + 8, r.h + 2 * g + 8), pygame.SRCALPHA)
            rad = max(0, int(min(18 * RADK * self.k + g, (r.h + 2 * g) / 2)))
            pygame.draw.rect(ring, (*col, int(170 * (1 - f))), (4, 4, r.w + 2 * g, r.h + 2 * g), max(2, self.n(3)), border_radius=rad)
            self.screen.blit(ring, (r.x - g - 4, r.y - g - 4))
            dot = self._fx_dot(ACC)
            dot.set_alpha(int(255 * (1 - f) ** 1.5))
            reach = max(r.w, r.h) * 0.5 + self.n(70)
            for ang, sp, _ in b["p"]:
                d = reach * sp * e
                self.screen.blit(dot, (int(r.centerx + math.cos(ang) * d * (r.w / max(r.w, r.h) * 0.6 + 0.4)) - dot.get_width() // 2,
                                       int(r.centery + math.sin(ang) * d * 0.7) - dot.get_height() // 2))

    def _fx_dot(self, col):
        c = self.__dict__.setdefault("_fxdot", {})
        k = (col, self.k)
        if k not in c:
            c.clear()
            c[k] = self._soft_dot(max(2, self.n(4)), col, 230)
        return c[k]

    # ── halo del foco ────────────────────────────────────────
    def glow(self, r, rad=16):
        """Resplandor suave que late alrededor del control enfocado (un anillo difuminado, en caché por tamaño)."""
        if self.cfg.get("fx") == "perf" or not self.show_focus:
            return
        m = self.n(26)
        col = FOCUS or ACC
        c = self.__dict__.setdefault("_glow_c", {})
        key = (r.w // 6, r.h // 6, col, self.k)
        g = c.get(key)
        if g is None:
            if len(c) > 48:
                c.clear()
            sw, sh = max(8, (r.w + 2 * m) // 6), max(8, (r.h + 2 * m) // 6)
            sm = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(sm, (*col, 255), (m // 6, m // 6, max(2, sw - m // 3), max(2, sh - m // 3)), max(2, m // 9), border_radius=max(1, int(rad * self.k) // 6 + 2))
            sm = pygame.transform.smoothscale(pygame.transform.smoothscale(sm, (max(4, sw // 2), max(4, sh // 2))), (sw, sh))
            g = c[key] = pygame.transform.smoothscale(sm, (r.w + 2 * m, r.h + 2 * m))
        g.set_alpha(96 if self.reduced_motion() else int(70 + 55 * math.sin(time.time() * 3.2)))      # movimiento reducido: halo fijo, sin latido
        self.screen.blit(g, (r.x - m, r.y - m))

    # ── salto del icono de la sección ────────────────────────
    def tab_hop(self, key, sel):
        """Píxeles que sube el icono de la barra lateral justo después de elegir su sección (un rebote corto)."""
        st = self.__dict__.setdefault("_hop", {"cur": None, "t": 0.0})
        if sel and st["cur"] != key:
            st["cur"], st["t"] = key, time.time()
        if not sel or self.cfg.get("fx") == "perf" or self.reduced_motion():
            return 0
        f = (time.time() - st["t"]) / 0.38
        if f >= 1:
            return 0
        return int(self.n(9) * math.sin(math.pi * f) * (1 - f * 0.4))

    # ── pantalla de espera: mientras el juego arranca, una tarjeta con su portada y una barra que va y viene (v2.38, con el estilo del tema) ──
    WAIT_TXT = {"fosforo": ("> LANZANDO_", "no apagues el terminal"), "pixel": ("CARGANDO…", "pulsa START cuando salga la ventana"),
                "neon": ("INSERT COIN…", "la partida está por empezar"), "tinta": ("Abriendo el libro…", "un momento, pasamos página"),
                "bloque": ("ABRIENDO", "UN MOMENTO"), "tarjeta": ("Leyendo la tarjeta…", "no la retires"), "cubo": ("Montando el cubo…", "casi listo"),
                "onda": ("Abriendo…", "las cintas se acomodan"), "brasa": ("Encendiendo la fragua…", "el hierro ya está al rojo")}

    def draw_wait(self):
        pr = getattr(self, "play_pr", None)
        sw = getattr(self, "steam_wait", None)
        sc = getattr(self, "steam_cover", None) if getattr(self, "exit_at", 0) else None     # v2.50: también mientras Hub tapa hasta que salga el launcher
        if not (pr or sw or sc):
            return
        now = time.time()
        age = now - (self.play_t if pr else sw["t"] if sw else sc.get("w0", sc.get("t0", now) - 1.0))
        e = self.entry(getattr(self, "play_eid", "")) or {"id": self.play_id, "name": self.play_name, "platform": ""}
        self.screen.set_clip(None)
        key = ("_wait_bd2", self.W, self.H, BG)
        ov = self._tc.get(key)
        if ov is None:
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            ov.fill((*BG, 255))      # v2.50: opaco del todo: no se ve el botón pulsado ni la ficha detrás
            self._tc[key] = ov
        a = 1.0 if self.reduced_motion() else min(1.0, age / 0.12)    # entra con un fundido corto (sin él con movimiento reducido)
        ov.set_alpha(int(255 * a))
        self.screen.blit(ov, (0, 0))
        cw, ch = min(self.W - self.n(80), self.n(980)), self.n(400)
        card = pygame.Rect((self.W - cw) // 2, (self.H - ch) // 2 + int((1 - a) * self.n(30)), cw, ch)
        self.rr(card, PANEL, 26 * RADK)
        if OUTLINE or GLASS:
            self.rr(card, LINE, 26 * RADK, max(2, self.n(3)))
        cov = pygame.Rect(card.x + self.n(34), card.y + self.n(34), int((ch - self.n(68)) * 0.7), ch - self.n(68))
        self._hl_art(e, cov, int(16 * RADK * self.k))
        self.rr(cov, ACC, 16 * RADK, max(2, self.n(3)))
        tx = cov.right + self.n(36)
        tw = card.right - tx - self.n(34)
        head, hint = self.WAIT_TXT.get(FAMILY, ("Abriendo el juego…", "un momento"))
        if sw or sc:
            hint = "Steam está abriendo el juego…"
        elif getattr(self, "play_win", False):
            hint = "Proton arranca; la primera vez tarda"
        elif self.cfg.get("close_on_play", True):
            hint = "Hub se cierra cuando el juego arranque"
        self.text(head.upper() if FONT in ("mono", "vt323") else head, tx, card.y + self.n(50), 22, ACC, True, tw)
        self.para(self._hl_title(e), tx, card.y + self.n(92), 38, tw, TXT, True, 3)
        plat = self._hl_plat(e)
        if plat:
            self.text(plat, tx, card.y + self.n(238), 20, DIM, False, tw)
        bar = pygame.Rect(tx, card.bottom - self.n(110), tw, self.n(14))
        pygame.draw.rect(self.screen, LINE, bar, border_radius=self.n(7))
        seg = int(bar.w * 0.3)
        pos = (math.sin(now * 2.2) * 0.5 + 0.5) * (bar.w - seg)
        pygame.draw.rect(self.screen, ACC, (bar.x + int(pos), bar.y, seg, bar.h), border_radius=self.n(7))
        self.text(hint, tx, card.bottom - self.n(62), 18, DIM, False, tw)

    # ── fondo animado: se compone a ~20 fps y se reutiliza; mientras toca/anima una transición no se recompone (v2.39) ──
    def draw_bg(self):
        """Fondo del tema (+ animación). Las luces grandes son blits alfa de media pantalla: en la Ally cuestan decenas de ms. La animación es lenta,
        así que se compone en una superficie opaca como mucho 20 veces por segundo y el resto de fotogramas solo copia esa superficie; en los
        ~0,5 s siguientes a una pulsación (destello, entrada de la pantalla) no se recompone: el fotograma del toque queda libre."""
        amb = self.ambient()
        if not (ANIM and self.fx_level() >= 2 and not self.reduced_motion()):     # v3.09: fondo animado solo en calidad alta
            self.screen.blit(amb, (0, 0))
            return
        if ANIM not in ("aurora", "drift"):      # v2.43: solo los brillos grandes (varios blits alfa de pantalla entera) merecen caché;
            self.screen.blit(amb, (0, 0))         # figuras, cubos, rejillas, estrellas… cuestan <1,5 ms: se dibujan cada fotograma (fluido)
            self.draw_anim()
            return
        now = time.time()
        key = (self.W, self.H, ANIM, ACC, BG, id(amb))
        c = self.__dict__.get("_bgc")
        fresh = c is not None and c["key"] == key
        busy = now - getattr(self, "t_act", 0) < 0.5 or bool(self.__dict__.get("_bursts"))
        if not fresh or (now - c["t"] >= 0.033 and not busy) or now - c["t"] >= 0.2:
            surf = c["s"] if fresh else pygame.Surface((self.W, self.H)).convert()
            real = self.screen
            self.screen = surf
            try:
                surf.blit(amb, (0, 0))
                self.draw_anim()
            finally:
                self.screen = real
            self._bgc = {"key": key, "t": now, "s": surf}
            self.bg_composed = getattr(self, "bg_composed", 0) + 1
        self.screen.blit(self._bgc["s"], (0, 0))
