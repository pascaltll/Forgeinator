"""Sonidos de la interfaz, sintetizados por código (sin archivos, sin copyright): clics muy cortos, suaves y con el tono subiendo un poco al moverse,
más cálidos al aceptar y descendentes al volver. Pautas generales de sonido de interfaz: < 150 ms, ataque casi inmediato, caída exponencial,
poco grave, volumen bajo para no cansar. Si pones tu propio archivo en data/sounds/<nombre>.wav|ogg (nombres: move, confirm, back, tab, open, error)
sustituye al generado. Si el audio no está disponible, todo se queda en silencio sin molestar."""
import math
import struct
import sys
import time

RATE = 44100
NAMES = ("move", "confirm", "back", "tab", "open", "error")
EXTS = (".wav", ".ogg", ".mp3")


def tone(notes, ms, attack_ms=2.0, decay=7.0, harmonics=((1, 1.0), (2, 0.22), (3, 0.06)), gain=0.5):
    """Lista de muestras (-1..1). notes: [(f0, f1, inicio_ms)] — cada nota baja/sube de f0 a f1 durante `ms` y empieza en `inicio_ms`."""
    total = int(RATE * (max(s for _, _, s in notes) + ms) / 1000)
    out = [0.0] * total
    n = int(RATE * ms / 1000)
    att = max(1, int(RATE * attack_ms / 1000))
    for f0, f1, start in notes:
        i0, ph = int(RATE * start / 1000), 0.0
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * (1 - (1 - t) ** 2)          # el tono se asienta rápido (curva de salida)
            ph += 2 * math.pi * f / RATE
            env = min(1.0, (i + 1) / att) * math.exp(-decay * t)
            if i > n - 40:
                env *= (n - i) / 40.0                      # sin clic final
            s = sum(a * math.sin(h * ph) for h, a in harmonics)
            if i0 + i < total:
                out[i0 + i] += gain * env * s
    peak = max(1e-9, max(abs(v) for v in out))
    return [v / peak * 0.85 for v in out] if peak > 0.85 else out


def pcm(samples) -> bytes:
    return struct.pack("<%dh" % len(samples), *(int(max(-1.0, min(1.0, v)) * 32767) for v in samples))


# Timbres por tema (v2.32): mismos seis sonidos, otro carácter. (armónicos, factor de tono, factor de caída, factor de duración)
PROFILES = {
    "soft": (None, 1.0, 1.0, 1.0),                                                            # el de siempre
    "glass": (((1, 1.0), (2.76, 0.34), (5.4, 0.14)), 1.35, 0.6, 1.5),                        # campanilla de cristal: aguda y larga
    "chip": (((1, 1.0), (3, 0.33), (5, 0.2), (7, 0.14), (9, 0.11)), 0.9, 0.55, 0.9),         # onda casi cuadrada: 8 bits
    "wood": (((1, 1.0), (2, 0.5), (3.9, 0.12)), 0.55, 1.9, 0.8),                             # golpe seco y grave
    "silk": (((1, 1.0), (2, 0.12)), 0.85, 0.5, 1.7),                                          # suave y larga, casi sin armónicos (Onda)
    "click": (((1, 1.0), (3, 0.5), (6, 0.3)), 1.6, 2.2, 0.45),                                # tic corto y seco (Interruptor)
    "marimba": (((1, 1.0), (4, 0.35), (9.2, 0.1)), 0.8, 1.2, 1.0),                            # madera afinada que rebota (Cubo)
    "arcade": (((1, 1.0), (3, 0.5), (5, 0.3), (7, 0.2)), 1.25, 0.8, 0.75),                    # pitido agudo de recreativa (Neón)
    "blip": (((1, 1.0), (3, 0.4)), 0.6, 1.6, 0.6),                                            # pitido grave de terminal (Fósforo)
}


def synth(profile: str = "soft") -> dict:
    """Los seis sonidos (bytes PCM 16 bit mono 44,1 kHz) con el timbre pedido."""
    har, pk, dk, mk = PROFILES.get(profile) or PROFILES["soft"]

    def T(notes, ms, attack_ms=2.0, decay=7.0, harmonics=((1, 1.0),), gain=0.5):
        return tone([(a * pk, b * pk, s * mk) for a, b, s in notes], ms * mk, attack_ms, decay * dk, har or harmonics, gain)
    S = {
        "move": T([(1180, 1560, 0)], 45, decay=6.5, harmonics=((1, 1.0), (2, 0.18)), gain=0.55),                      # tic suave que sube un poco
        "tab": T([(880, 1170, 0)], 70, decay=5.5, harmonics=((1, 1.0), (2, 0.3), (4, 0.08)), gain=0.55),
        "confirm": T([(660, 700, 0), (990, 1040, 55)], 95, decay=5.0, harmonics=((1, 1.0), (2, 0.28), (3, 0.1)), gain=0.5),  # dos notas, sube
        "back": T([(760, 520, 0), (560, 420, 40)], 85, decay=5.5, harmonics=((1, 1.0), (2, 0.2)), gain=0.5),               # dos notas, baja
        "open": T([(520, 780, 0)], 110, attack_ms=6, decay=4.0, harmonics=((1, 1.0), (2, 0.25), (3, 0.08)), gain=0.5),
        "error": T([(240, 200, 0), (240, 200, 70)], 70, attack_ms=3, decay=5.0, harmonics=((1, 1.0), (3, 0.3)), gain=0.5),
    }
    return {k: pcm(v) for k, v in S.items()}


class Sfx:
    MIN_GAP = {"move": 0.035}          # no se amontonan al mantener pulsada una dirección
    DEFAULT_GAP = 0.06

    def __init__(self, enabled=True, volume=0.5, folder=None):
        self.enabled, self.volume, self.folder = bool(enabled), float(volume), folder
        self.sounds, self.ok, self.tried, self.last, self.played = {}, False, False, {}, 0
        self.profile = "soft"

    def set_profile(self, name):
        """Cambia el timbre (lo pide el tema). Se regenera en un hilo; tus archivos de data/sounds siguen mandando."""
        name = name if name in PROFILES else "soft"
        if name == self.profile:
            return
        self.profile = name
        if self.tried and self.ok:
            import threading
            threading.Thread(target=self._init, daemon=True).start()

    def warm(self):
        """Prepara los sonidos en un hilo al arrancar (así el primero no provoca un tirón)."""
        if self.enabled and not self.tried:
            import threading
            self.tried = True
            threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        """Abre el mezclador la primera vez que hace falta; si falla (sin audio), se queda mudo para siempre."""
        self.tried = True
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(RATE, -16, 1, 512)
                pygame.mixer.init(RATE, -16, 1, 512)
            gen = synth(self.profile)
            for name in NAMES:
                snd = self._custom(pygame, name) or pygame.mixer.Sound(buffer=gen[name])
                self.sounds[name] = snd
            self.ok = True
        except Exception as ex:  # noqa: BLE001
            print(f"[sonido] desactivado: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            self.ok = False

    def _custom(self, pygame, name):
        if not self.folder:
            return None
        for ext in EXTS:
            p = self.folder / (name + ext)
            if p.is_file():
                try:
                    return pygame.mixer.Sound(str(p))
                except Exception as ex:  # noqa: BLE001
                    print(f"[sonido] no pude cargar {p.name}: {ex}", file=sys.stderr, flush=True)
        return None

    def play(self, name):
        if not self.enabled or self.volume <= 0:
            return False
        if not self.tried:
            self._init()
        snd = self.sounds.get(name) if self.ok else None      # si el hilo de arranque aún no terminó, ese sonido se salta
        now = time.monotonic()
        if snd is None or now - self.last.get(name, 0) < self.MIN_GAP.get(name, self.DEFAULT_GAP):
            return False
        self.last[name] = now
        try:
            snd.set_volume(max(0.0, min(1.0, self.volume)))
            snd.play()
            self.played += 1
            return True
        except Exception:  # noqa: BLE001
            return False

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, float(v)))
