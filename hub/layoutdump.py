"""Descripción EN TEXTO de cómo se ve una pantalla de Hub a un tamaño dado (para pegarla en el chat sin capturas).
Registra cada texto y cada widget del fotograma y calcula: tamaño real de los botones en milímetros (ROG Ally: 7" 1920×1080 ≈ 315 ppi),
letra más pequeña, textos que se salen de la pantalla, textos que se pisan entre sí y caracteres que la fuente no tiene. Más un dibujo ASCII."""
import time

import pygame

PPI = 315.0                    # ROG Ally (7", 1920×1080)
MIN_TOUCH_MM = 7.0             # por debajo de esto un dedo falla a menudo (guía habitual: 7–9 mm)


def _mm(px, w):
    return px / (w / 1920.0) / PPI * 25.4      # a 1280×720 los píxeles son más grandes: el panel físico es el mismo


def capture(ui, frames=3):
    """Dibuja `frames` fotogramas y devuelve {'texts': [...], 'widgets': [...], 'size': (w,h)} del último."""
    rec = []
    orig = ui.text

    def text(s, x, y, size=22, color=None, bold=False, maxw=None, anchor="tl"):
        r = orig(s, x, y, size, color, bold, maxw, anchor)
        ox, oy = ui.screen.get_abs_offset() if hasattr(ui.screen, "get_abs_offset") else (0, 0)   # el cuerpo del prototipo se dibuja en una subsuperficie
        rec.append({"s": str(s), "px": max(13, int(size * ui.k)), "rect": pygame.Rect(r).move(ox, oy)})
        return r
    ui.text = text
    try:
        for _ in range(frames):
            rec.clear()
            ui.frame()
            time.sleep(0.004)
    finally:
        del ui.text
    wd = [{"key": w.key, "rect": pygame.Rect(w.rect)} for w in ui.widgets if getattr(w, "rect", None) is not None]
    return {"texts": list(rec), "widgets": wd, "size": ui.screen.get_size()}


def analyze(ui, cap):
    W, H = cap["size"]
    scr = pygame.Rect(0, 0, W, H)
    small = sorted((round(_mm(min(w["rect"].w, w["rect"].h), W), 1), w["key"]) for w in cap["widgets"] if w["rect"].w > 0 and w["rect"].h > 0)
    small = [t for t in small if t[0] < MIN_TOUCH_MM]
    texts = [t for t in cap["texts"] if t["s"].strip()]
    out = [t for t in texts if t["rect"].right > W + 2 or t["rect"].x < -2]      # (lo que queda bajo/encima por el scroll es normal: solo se mira el eje X)
    pisa = []
    texts = [t for t in texts if t["rect"].centery < H - ui.n(ui.FH)]      # lo que queda bajo la barra inferior es contenido desplazado, no un choque
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if a["s"] == b["s"] or "Más abajo" in (a["s"], b["s"]):   # la píldora «Más abajo» flota sobre el contenido a propósito
                continue
            ov = a["rect"].clip(b["rect"])
            if ov.w > 3 and ov.h > a["rect"].h * 0.35 and ov.w * ov.h > 0.25 * min(a["rect"].w * a["rect"].h, b["rect"].w * b["rect"].h):
                pisa.append((a["s"][:28], b["s"][:28]))
    miss = {}
    for t in texts:
        for ch in t["s"]:
            if ord(ch) > 127 and not ui.has_glyph(ch):
                miss[ch] = miss.get(ch, 0) + 1
    return {"min_text_px": min((t["px"] for t in texts), default=0), "min_text_mm": round(_mm(min((t["px"] for t in texts), default=0), W), 1),
            "n_widgets": len(cap["widgets"]), "small_targets": small, "offscreen": [t["s"][:30] for t in out], "overlaps": pisa, "missing_glyphs": miss}


def ascii_map(cap, cols=100):
    """Rejilla de caracteres: cada widget se rellena con la inicial de su clave; los textos se marcan con '.'."""
    W, H = cap["size"]
    rows = max(8, int(cols * H / W * 0.5))
    g = [[" "] * cols for _ in range(rows)]

    def cells(r):
        return (max(0, int(r.x * cols / W)), max(0, int(r.y * rows / H)), min(cols, max(int(r.right * cols / W), int(r.x * cols / W) + 1)),
                min(rows, max(int(r.bottom * rows / H), int(r.y * rows / H) + 1)))
    for t in cap["texts"]:
        x0, y0, x1, y1 = cells(t["rect"])
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                g[yy][xx] = "."
    for w in sorted(cap["widgets"], key=lambda w: -w["rect"].w * w["rect"].h):
        x0, y0, x1, y1 = cells(w["rect"])
        ch = (str(w["key"]).split(":")[-1][:1] or "#").upper()
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                edge = yy in (y0, y1 - 1) or xx in (x0, x1 - 1)
                if edge or g[yy][xx] == " ":
                    g[yy][xx] = "#" if edge and (yy in (y0, y1 - 1)) else ("|" if edge else ch.lower())
    return "\n".join("".join(r).rstrip() for r in g)


def report(ui, name, with_ascii=False):
    cap = capture(ui)
    a = analyze(ui, cap)
    W, H = cap["size"]
    lines = [f"### {name} · {W}×{H} · escala {ui.k:.2f}",
             f"- widgets: {a['n_widgets']} · letra mínima: {a['min_text_px']} px (≈{a['min_text_mm']} mm)",
             f"- botones por debajo de {MIN_TOUCH_MM:g} mm: " + (", ".join(f"{k}={mm}mm" for mm, k in a["small_targets"][:8]) or "ninguno"),
             f"- textos fuera de pantalla: {a['offscreen'][:6] or 'ninguno'}",
             f"- textos que se pisan: {a['overlaps'][:6] or 'ninguno'}",
             f"- caracteres que la fuente NO tiene: {a['missing_glyphs'] or 'ninguno'}"]
    if with_ascii:
        lines += ["```", ascii_map(cap), "```"]
    return "\n".join(lines), a
