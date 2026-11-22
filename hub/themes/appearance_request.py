"""Protocolo de peticiones de apariencia (v2.91). Quien personaliza (Theme Studio, otro chat, un script) escribe
`data/appearance-request.json`; el Hub la valida, la aplica y publica el resultado CONFIRMADO en `appearance.json` (clave `request`).
Python puro: la parte de aplicar vive en el Hub (UI.poll_appearance_request); aquí solo se valida y se decide.

Petición (schema_version 1):
  {"schema_version": 1, "request_id": "abc123", "changes": {"theme": "neon", "palette": "lima", "background": "stars"}}
  - `changes` admite solo theme · palette · background (todo opcional, al menos uno).
  - Un campo desconocido, un tema/paleta/fondo que no existe, o una paleta que no es del tema → la petición ENTERA se rechaza y no cambia nada.
Resultado (en appearance.json → "request"):
  {"id": "abc123", "status": "applied" | "rejected" | "duplicate", "errors": [...]}"""
from __future__ import annotations
import json
from pathlib import Path
from . import legacy, studio

REQUEST_SCHEMA = 1
ALLOWED = ("theme", "palette", "background", "layout")      # layout: solo identidades del Estudio («v3:…», v2.97)


def validate(req, current=None):
    """→ (ok, errores, cambios_limpios). `current` = (tema, paleta, fondo) actuales para completar lo que no se pide."""
    errs = []
    if not isinstance(req, dict):
        return False, ["la petición no es un objeto JSON"], {}
    if req.get("schema_version") != REQUEST_SCHEMA:
        errs.append(f"schema_version debe ser {REQUEST_SCHEMA}")
    rid = req.get("request_id")
    if not isinstance(rid, str) or not rid.strip() or len(rid) > 80:
        errs.append("request_id obligatorio (texto de 1 a 80 caracteres)")
    ch = req.get("changes")
    if not isinstance(ch, dict) or not ch:
        return False, errs + ["changes vacío o ausente"], {}
    for k in ch:
        if k not in ALLOWED:
            errs.append(f"campo no soportado: {k}")
    cur_t, cur_p, cur_b = current or (None, None, None)
    theme = ch.get("theme", cur_t)
    if "theme" in ch and (not isinstance(theme, str) or (theme not in legacy.FAMILIES and not studio.is_studio(theme))):
        errs.append(f"tema desconocido: {theme!r}")
        return False, errs, {}
    if studio.is_studio(theme):                    # identidad del Estudio: paletas, fondos y layouts que declara su preset
        if "palette" in ch and ch["palette"] not in studio.palettes(theme):
            errs.append(f"paleta {ch['palette']!r} no es compatible con {theme!r}")
        if "background" in ch and ch["background"] not in studio.backgrounds(theme):
            errs.append(f"fondo {ch['background']!r} no existe en {theme!r}")
        if "layout" in ch and ch["layout"] not in studio.layouts(theme):
            errs.append(f"layout {ch['layout']!r} no es compatible con {theme!r}")
        if errs:
            return False, errs, {}
        ok_ch = {k: ch[k] for k in ALLOWED if k in ch}
        pal = ok_ch.get("palette") or (cur_p if theme == cur_t else None)
        bad = legacy.check_contrast(studio.build(theme, pal))
        if bad:
            return False, [f"contraste insuficiente {a}/{b}={r}<{m}" for a, b, r, m in bad], {}
        return True, [], ok_ch
    if "layout" in ch:
        errs.append("layout solo se puede elegir en las identidades del Estudio (v3:…)")
    fam = legacy.normalize(theme)[0] if theme else None
    if "palette" in ch:
        ids = [p["id"] for p in legacy.FAMILIES[fam]["palettes"]] if fam else []
        if ch["palette"] not in ids:
            errs.append(f"paleta {ch['palette']!r} no es del tema {fam!r}")
    if "background" in ch:
        if not fam or ch["background"] not in legacy.FAMILIES[fam]["bgs"]:
            errs.append(f"fondo {ch['background']!r} no existe en el tema {fam!r}")
    if errs:
        return False, errs, {}
    ok_ch = {k: ch[k] for k in ALLOWED if k in ch}
    # colores: el tema y la paleta resultantes deben cumplir el contraste del Hub
    pal = ok_ch.get("palette") if "palette" in ok_ch else (cur_p if fam == legacy.normalize(cur_t)[0] else None)
    bad = legacy.check_contrast(legacy.build(fam, pal))
    if bad:
        return False, [f"contraste insuficiente {a}/{b}={r}<{m}" for a, b, r, m in bad], {}
    return True, [], ok_ch


def read(path):
    """Lee la petición; None si no existe; ('error', texto) si el JSON está roto."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as ex:
        return ("error", str(ex))
