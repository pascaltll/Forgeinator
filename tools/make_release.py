#!/usr/bin/env python3
"""Construye los archivos de una release de Forgeinator desde el árbol del repositorio:
  forgeinator-X.zip            app del QAM, canal ESTABLE (carpeta forgeinator/ con CHANNEL y qam-app.json esquema 1). Es lo que
                               instala y actualiza QAM Rail desde las releases de GitHub.
  install-hub-vX.sh            instalador autoextraíble (código + tests; data/ nunca)
  recomp-hub-update-vX.zip     el mismo instalador + SHA256SUMS: lo aplica la autoactualización desde ~/Games/actualizaciones
                               (canal dev y la instalación antigua de ~/Games/recomp-hub)
  SHA256SUMS                   sumas de todo lo anterior (QAM Rail no instala nada sin comprobarlas)
  forgeinator-dev-X.zip        con --dev: app del QAM, canal DEV (carpeta forgeinator-dev/). No se sube a GitHub: se instala a mano
                               desde el QAM («Instalar desde .zip») y luego se actualiza con los zip de ~/Games/actualizaciones.
Uso:  python3 tools/make_release.py [--out dist] [--version X] [--dev]   (la versión, por defecto, la de VERSION)
Solo biblioteca estándar; lo usan el flujo de GitHub Actions y quien quiera construir una release a mano."""
import argparse
import base64
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_TOP = {"data", "tests", "dist", "build", ".git", ".github"}
EOFM = "HUB_" + "EOF"        # el marcador de los heredoc (escrito así para que este archivo pueda ir dentro del instalador)
SKIP_ANY = {"__pycache__", "reports", ".venv", ".pytest_cache"}


def app_files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not (SKIP_ANY & set(p.relative_to(ROOT).parts))
                  and p.relative_to(ROOT).parts[0] not in SKIP_TOP and not p.name.endswith((".pyc", ".zip"))
                  and not p.name.startswith("install-hub"))


def test_files():
    t = ROOT / "tests"
    if not t.is_dir():
        return []
    return sorted(p for p in t.rglob("*") if p.is_file() and not (SKIP_ANY & set(p.relative_to(t).parts))
                  and not p.name.endswith((".pyc", ".xml")) and not p.name.startswith(".coverage"))


HEAD = r'''#!/usr/bin/env bash
# Forgeinator (antes Recomp Hub) -> instala en ~/Games/recomp-hub (o $HUB_DIR). No toca juegos, launcher ni Steam.
set -euo pipefail
DEST="${HUB_DIR:-$HOME/Games/recomp-hub}"
if [ -e "$DEST" ] && [ -z "${FORCE:-}" ]; then
  echo "Ya existe $DEST. Para reinstalar el codigo (data/ se conserva):  FORCE=1 bash $0"; exit 1
fi
mkdir -p "$DEST"/{bin,hub,catalog,assets}
[ -f "$DEST/CHANNEL" ] || mkdir -p "$DEST/data"     # v3.15: una copia con canal (app del QAM) no guarda datos en su carpeta
write() { mkdir -p "$(dirname "$DEST/$1")"; cat > "$DEST/$1"; }
writeb() { mkdir -p "$(dirname "$DEST/$1")"; base64 -d > "$DEST/$1"; }
'''
TAIL = r'''
if [ -f "$DEST/CHANNEL" ]; then   # v3.15: copia del QAM (estable o dev): su qam-app.json es el de su canal, no el del repositorio
  CHN="$(tr -dc 'a-z' < "$DEST/CHANNEL")"
  for cand in python3 /usr/bin/python3; do
    if command -v "$cand" >/dev/null 2>&1; then
      "$cand" "$DEST/tools/make_release.py" --manifest "$CHN" --version "$(cat "$DEST/VERSION")" > "$DEST/qam-app.json.tmp" \
        && mv -f "$DEST/qam-app.json.tmp" "$DEST/qam-app.json" || rm -f "$DEST/qam-app.json.tmp"
      break
    fi
  done
fi
chmod +x "$DEST/bin/hub" "$DEST/bin/forgeinator" "$DEST/bin/forgeinator-ctl" "$DEST/bin/hub-browser" "$DEST/bin/hub-update" "$DEST/bin/hub-tests" "$DEST/bin/hub-doctor" "$DEST/bin/hub-logs" "$DEST/bin/hub-archivo" "$DEST/main.py"
for cand in python3 /usr/bin/python3; do
  if command -v "$cand" >/dev/null 2>&1; then "$cand" -m py_compile "$DEST"/main.py "$DEST"/hub/*.py && echo "Sintaxis Python OK." || echo "AVISO: py_compile fallo."; break; fi
done
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
cat <<MSG

Instalado en: $DEST
  $DEST/bin/hub --list          (catalogo, sin interfaz)
  $DEST/bin/hub                 (interfaz: tactil + mando)
Para Steam: anade $DEST/bin/hub como juego no-Steam.
MSG
'''


def build_installer(out: Path) -> int:
    parts = [HEAD]
    entries = [(p.relative_to(ROOT).as_posix(), p) for p in app_files()] + [("tests/" + p.relative_to(ROOT / "tests").as_posix(), p) for p in test_files()]
    for rel, p in entries:
        if p.suffix.lower() in (".png", ".jpg"):
            b64 = base64.encodebytes(p.read_bytes()).decode()
            parts.append(f"\n# ── {rel} ──\nwriteb '{rel}' <<'{EOFM}'\n{b64}{EOFM}\n")
            continue
        body = p.read_text(encoding="utf-8")
        assert EOFM not in body, rel
        if body and not body.endswith("\n"):
            body += "\n"
        parts.append(f"\n# ── {rel} ──\nwrite '{rel}' <<'{EOFM}'\n{body}{EOFM}\n")
    parts.append(TAIL)
    out.write_text("".join(parts), encoding="utf-8")
    out.chmod(0o755)
    return len(entries)


DATA_DIRS = ["~/.local/share/forgeinator", "~/.config/forgeinator", "~/.local/state/forgeinator"]


def manifest(v: str, ch: str) -> dict:
    """qam-app.json (esquema 1 del estándar de apps del QAM) de cada canal."""
    dev = ch == "dev"
    m = {
        "schema": 1,
        "id": "forgeinator-dev" if dev else "forgeinator",
        "name": "Forgeinator 3000 Dev" if dev else "Forgeinator 3000",
        "version": v,
        "group": "Juegos",
        "description": ("Canal de desarrollo: versiones de prueba. Comparte la biblioteca con la estable; ajustes aparte." if dev else
                        "Forja ports sueltos en juegos jugables."),
        "launch": "bin/forgeinator",
        "launch_options": "",
        "install": "install.sh",
        "data_dirs": DATA_DIRS,
        "keep": [],
        "status": "bin/forgeinator --qam-status",
        "actions": [{"label": "Abrir", "args": ""}],
        "art": {"capsule": "assets/brand/steam-capsule.png", "header": "assets/brand/steam-header.png", "hero": "assets/brand/steam-hero.png",
                "logo": "assets/brand/steam-logo.png", "icon": "assets/brand/icon-256.png"},
        "min_qam_rail": "0.50.0",
    }
    if not dev:
        m["update"] = {"provider": "github-release", "repo": "pascaltll/Forgeinator", "asset": "forgeinator-[0-9]*.zip",
                       "checksum": "SHA256SUMS", "channel": "stable"}
    return m


INSTALL_SH = """#!/usr/bin/env bash
# Forgeinator 3000 · lo ejecuta QAM Rail tras copiar la app (como usuario, sin sudo, sin red). Idempotente.
set -u
D="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
chmod +x "$D"/bin/* "$D/main.py" "$D/install.sh" 2>/dev/null
PY=""
for c in python3 "$HOME/miniforge3/bin/python3" "$HOME/miniconda3/bin/python3" /usr/bin/python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import pygame' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Falta pygame-ce para la interfaz. Instálalo con:  pip install --user --break-system-packages pygame-ce" >&2
  exit 1
fi
"$PY" -m py_compile "$D"/main.py "$D"/hub/*.py || { echo "El código no compila (descarga dañada)" >&2; exit 1; }
find "$D" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
echo "Forgeinator $(cat "$D/VERSION") ($(cat "$D/CHANNEL")) listo · biblioteca: ~/.local/share/forgeinator"
"""


def build_app_zip(out: Path, v: str, ch: str) -> Path:
    top = "forgeinator-dev" if ch == "dev" else "forgeinator"
    z = out / f"{top}-{v}.zip"
    entries = [(p.relative_to(ROOT).as_posix(), p) for p in app_files() if p.relative_to(ROOT).as_posix() not in ("qam-app.json", "CHANNEL", "VERSION")]
    entries += [("tests/" + p.relative_to(ROOT / "tests").as_posix(), p) for p in test_files()]
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for rel, p in entries:
            zi = zipfile.ZipInfo.from_file(p, f"{top}/{rel}")
            zi.compress_type = zipfile.ZIP_DEFLATED
            if rel.startswith("bin/") or rel == "main.py":
                zi.external_attr = (0o100755 << 16)
            f.writestr(zi, p.read_bytes())
        f.writestr(f"{top}/CHANNEL", ch + "\n")
        f.writestr(f"{top}/VERSION", v + "\n")
        f.writestr(f"{top}/qam-app.json", json.dumps(manifest(v, ch), indent=2, ensure_ascii=False) + "\n")
        zi = zipfile.ZipInfo(f"{top}/install.sh")
        zi.external_attr = (0o100755 << 16)
        zi.compress_type = zipfile.ZIP_DEFLATED
        f.writestr(zi, INSTALL_SH)
    return z


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="dist")
    ap.add_argument("--version")
    ap.add_argument("--dev", action="store_true", help="además, forgeinator-dev-X.zip (canal dev, para instalar a mano en el QAM)")
    ap.add_argument("--manifest", choices=("stable", "dev"), help="solo imprime el qam-app.json de ese canal (lo usa el instalador)")
    a = ap.parse_args()
    v = a.version or (ROOT / "VERSION").read_text().strip()
    if a.manifest:
        print(json.dumps(manifest(v, a.manifest), indent=2, ensure_ascii=False))
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    inst = out / f"install-hub-v{v}.sh"
    n = build_installer(inst)
    z = out / f"recomp-hub-update-v{v}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        f.write(inst, inst.name)
        f.writestr("SHA256SUMS", f"{hashlib.sha256(inst.read_bytes()).hexdigest()}  {inst.name}\n")
    app = build_app_zip(out, v, "stable")
    made = [inst, z, app]
    if a.dev:
        made.append(build_app_zip(out, v, "dev"))
    (out / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in made), encoding="utf-8")
    print(f"{inst} ({n} archivos) · " + " · ".join(str(p) for p in made[1:]) + f" · {out / 'SHA256SUMS'}")


if __name__ == "__main__":
    main()
